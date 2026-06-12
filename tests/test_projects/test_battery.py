"""The synthetic verification battery (TP1-TP4) — pinned to its generator and seeds.

Every expectation here is also the operator-facing manifest in ``docs/TEST-PROJECTS.md``:
the numbers MS Project + SSI / Acumen Fuse should reproduce on the same files. If an
engine change moves one of these, the manifest (and the understanding behind it) must
move with it — that is the point of the battery.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from schedule_forensics.engine.bow_wave import compute_bow_wave
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.driving_slack import PathTier, compute_driving_slack
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.metrics.completion_performance import (
    compute_completion_performance,
)
from schedule_forensics.engine.metrics.float_bands import compute_float_bands
from schedule_forensics.engine.trend import compute_quality_trend, order_versions
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model.schedule import Schedule

_REPO = Path(__file__).resolve().parent.parent.parent
FIXTURES = _REPO / "tests" / "fixtures" / "test_projects"
GENERATOR = _REPO / "tools" / "make_test_projects.py"

ALL_FILES = (
    "TP1_Library_Progressed.xml",
    "TP2_Bridge_4x10_Calendar.xml",
    "TP3_Outage_DCMA_Seeded.xml",
    "TP4_DataCenter_v1.xml",
    "TP4_DataCenter_v2.xml",
    "TP4_DataCenter_v3.xml",
    "TP4_DataCenter_v4.xml",
    "TP4_DataCenter_v5.xml",
)


def _load(name: str) -> Schedule:
    return parse_mspdi(FIXTURES / name)


def test_generator_is_deterministic_and_matches_the_committed_fixtures() -> None:
    """tools/make_test_projects.py regenerates the committed battery byte-identically."""
    spec = importlib.util.spec_from_file_location("make_test_projects", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations via sys.modules
    try:
        spec.loader.exec_module(module)
        generated = module.generate_all()
    finally:
        del sys.modules[spec.name]
    assert set(generated) == set(ALL_FILES)
    for name, xml in generated.items():
        assert (FIXTURES / name).read_text(encoding="utf-8") == xml, (
            f"{name} drifted from its generator — rerun python tools/make_test_projects.py"
        )


@pytest.mark.parametrize("name", ALL_FILES)
def test_every_battery_file_parses_and_solves(name: str) -> None:
    schedule = _load(name)
    cpm = compute_cpm(schedule)
    assert cpm.project_finish > 0


def test_tp1_driving_tiers_floor_ragged_minutes_onto_ssi_day_axis() -> None:
    """The #80 class, by construction: completed-chain raggedness must read DRIVING."""
    schedule = _load("TP1_Library_Progressed.xml")
    results = compute_driving_slack(schedule, 43, cpm_result=compute_cpm(schedule))
    tiers = Counter(r.tier for r in results.values())
    assert len(results) == 18
    assert tiers[PathTier.DRIVING] == 13
    assert tiers[PathTier.SECONDARY] == 1
    assert tiers[PathTier.TERTIARY] == 2
    assert tiers[PathTier.BEYOND] == 2
    # the completed design chain carries MINUTES of slack (ragged actual times) and
    # still classifies DRIVING — pre-ADR-0032 tiering would have dropped all three:
    for uid, minutes in ((11, 210), (12, 210), (13, 120)):
        assert results[uid].driving_slack_minutes == minutes
        assert results[uid].on_driving_path
        assert results[uid].tier is PathTier.DRIVING
    # exact band edges hold on the floored axis:
    assert results[39].driving_slack_days == Decimal("7")  # SECONDARY (<= 10)
    assert results[35].driving_slack_days == Decimal("20")  # TERTIARY boundary (== 20)


def test_tp1_completion_performance_populates_every_split() -> None:
    schedule = _load("TP1_Library_Progressed.xml")
    perf = compute_completion_performance(schedule)
    assert perf["completed_ahead"].count == 2
    assert perf["completed_on_schedule"].count == 2
    assert perf["completed_behind"].count == 1
    assert perf["mei"].value == 1.0


def test_tp2_calendar_imports_exactly_and_drives_the_day_math() -> None:
    schedule = _load("TP2_Bridge_4x10_Calendar.xml")
    cal = schedule.calendar
    assert cal.working_minutes_per_day == 600
    assert cal.work_weekdays == (0, 1, 2, 3)  # Mon-Thu
    assert len(cal.holidays) == 4
    cpm = compute_cpm(schedule)
    bands = compute_float_bands(schedule, cpm)
    assert bands["float_total_0"].count == 7
    assert bands["float_total_lt5"].count == 12
    assert bands["float_total_lt10"].count == 13
    # the 44-working-day tripwire is calendar-true: the exactly-44-day task (UID 13)
    # stays OUT of High Duration; the 45-day and 86-day tasks are the only offenders.
    high = next(c for c in audit_schedule(schedule).checks if c.name == "High Duration")
    offenders = {c.unique_id for c in high.citations}
    assert high.count == 2
    assert offenders == {14, 34}


def test_tp3_seeded_dcma_violations_register_with_the_seeded_counts() -> None:
    schedule = _load("TP3_Outage_DCMA_Seeded.xml")
    checks = {c.name: c for c in audit_schedule(schedule).checks}
    assert checks["Logic"].count == 4  # 14 (no pred, in progress), 32/33/42 (no succ)
    assert checks["Leads"].count == 2
    assert checks["Lags"].count == 3
    assert checks["FS Relationships"].value == 76.0  # 19 of 25 (< 90% -> FAIL)
    hard = checks["Hard Constraints"]
    assert hard.count == 2
    assert {c.unique_id for c in hard.citations} == {24, 41}
    negative = checks["Negative Float"]
    assert negative.count == 3  # the MFO-capped chain tail
    assert {c.unique_id for c in negative.citations} == {24, 28, 29}
    assert checks["High Duration"].count == 2  # 50-day and 60-day tasks
    assert checks["Invalid Dates"].count == 4  # 31 (actual after DD) + 3 stale forecasts
    assert checks["BEI"].value == 0.62  # 8 finished of 13 baselined to finish by the DD
    assert checks["Missed Activities"].count == 7


def test_tp4_series_orders_trends_and_flags_the_v4_manipulation() -> None:
    versions = [_load(f"TP4_DataCenter_v{i}.xml") for i in range(1, 6)]
    assert [s.source_file for s in order_versions(versions)] == [
        f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)
    ]
    assert compute_quality_trend(versions)
    assert len(compute_bow_wave(versions).snapshots) == 5

    honest = detect_manipulation(
        versions[2],
        versions[1],
        current_cpm=compute_cpm(versions[2]),
        prior_cpm=compute_cpm(versions[1]),
    )
    assert not {f.metric_id for f in honest} & {"MANIP_ACTUAL_ERASED", "MANIP_BASELINE_CHANGE"}

    v4 = detect_manipulation(
        versions[3],
        versions[2],
        current_cpm=compute_cpm(versions[3]),
        prior_cpm=compute_cpm(versions[2]),
    )
    by_id = {f.metric_id: f for f in v4}
    erased = by_id["MANIP_ACTUAL_ERASED"]
    rebaselined = by_id["MANIP_BASELINE_CHANGE"]
    assert [c.unique_id for c in erased.citations] == [19]
    assert [c.unique_id for c in rebaselined.citations] == [19]
