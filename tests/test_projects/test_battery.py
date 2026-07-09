"""The synthetic verification battery (TP1-TP4) — pinned to its generator and seeds.

Every expectation here is also the operator-facing manifest in ``docs/TEST-PROJECTS.md``:
the numbers MS Project + SSI / Acumen Fuse should reproduce on the same files. If an
engine change moves one of these, the manifest (and the understanding behind it) must
move with it — that is the point of the battery.
"""

from __future__ import annotations

import datetime as dt
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


#: Task child-element order from a genuine MS Project export (Project2.mspdi.xml).
#: MSP's XML reader is sequence-sensitive: Active/Manual emitted at the tail were
#: IGNORED, so the operator's "New Tasks: Manually Scheduled" default took over and
#: the imported .mpp lost links (the TP1 4-task trace). Order is part of the contract.
_MSP_TASK_ORDER = [
    *("UID", "ID", "Name", "Active", "Manual", "Type", "IsNull", "WBS", "OutlineNumber"),
    *("OutlineLevel", "Priority", "Start", "Finish", "Duration", "DurationFormat"),
    *("Milestone", "Summary", "PercentComplete", "ActualStart", "ActualFinish"),
    *("RemainingDuration", "ConstraintType", "ConstraintDate", "PredecessorLink", "Baseline"),
]


@pytest.mark.parametrize("name", ALL_FILES)
def test_task_elements_follow_ms_projects_own_export_order(name: str) -> None:
    import xml.etree.ElementTree as ET

    rank = {tag: i for i, tag in enumerate(_MSP_TASK_ORDER)}
    root = ET.parse(FIXTURES / name).getroot()
    ns = "{http://schemas.microsoft.com/project}"
    for task in root.iter(f"{ns}Task"):
        tags = [child.tag.removeprefix(ns) for child in task]
        assert set(tags) <= set(_MSP_TASK_ORDER), (name, sorted(set(tags) - set(rank)))
        ranks = [rank[tag] for tag in tags]
        assert ranks == sorted(ranks), (name, tags)


@pytest.mark.parametrize("name", ALL_FILES)
def test_every_date_and_duration_is_sane_for_ms_project(name: str) -> None:
    """Summary rollups (incl. the UID-0 project row) must carry real dates: a top-down
    rollup once gave UID 0 a year-0001 baseline and a 4-million-hour duration, which
    MS Project rejected at import (the tool itself ignores summary dates — only this
    guard and the MSP round-trip see them)."""
    schedule = _load(name)
    lo, hi = dt.datetime(2026, 1, 1), dt.datetime(2028, 1, 1)
    max_minutes = 300 * 600  # < a 300-day task even on the 10-hour calendar
    for task in schedule.tasks:
        for value in (
            task.start,
            task.finish,
            task.actual_start,
            task.actual_finish,
            task.baseline_start,
            task.baseline_finish,
        ):
            assert value is None or lo <= value <= hi, (name, task.unique_id, value)
        assert task.duration_minutes <= max_minutes, (name, task.unique_id)
        assert (task.baseline_duration_minutes or 0) <= max_minutes, (name, task.unique_id)


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
    # the completed design chain carries sub-day MINUTES of slack (ragged actual times) and
    # still classifies DRIVING — pre-ADR-0032 tiering would have dropped all three. ADR-0116
    # removed the ADR-0045 span-snap; ADR-0117 makes the slack pass honor the calendar's lunch
    # break (08:00-12:00 + 13:00-17:00), so afternoon raggedness is no longer over-counted by
    # the lunch hour. Each task keeps its true sub-day slack and still floors onto SSI's day
    # axis as 0 days, so the DRIVING classification is unchanged:
    for uid, minutes in ((11, 300), (12, 300), (13, 180)):
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
    # the deck-DAX measures, adopted verbatim (ADR-0033) — hand-computed for TP1:
    # 8 actual starts + 5 actual finishes over 8 actual starts + 23 baseline finishes
    assert perf["epi"].value == 0.42
    # 23 scheduled start/finish pairs over 5 completed actual pairs
    assert perf["start_finish_ratio"].value == 4.6


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
    # Fuse counts ACTIVITIES, not links: both planted leads target UID 29 -> ONE offender
    # (operator-verified against the Fuse ribbon: Leads 1, Lags 3).
    leads = checks["Leads"]
    assert leads.count == 1
    assert [c.unique_id for c in leads.citations] == [29]
    assert checks["Lags"].count == 3
    assert checks["FS Relationships"].value == 76.0  # 19 of 25 (< 90% -> FAIL)
    hard = checks["Hard Constraints"]
    assert hard.count == 2
    assert {c.unique_id for c in hard.citations} == {24, 41}
    negative = checks["Negative Float"]
    assert negative.count == 3  # the MFO-capped chain tail
    assert {c.unique_id for c in negative.citations} == {24, 28, 29}
    assert checks["High Duration"].count == 2  # 50-day and 60-day tasks
    # 31 (actual finish after DD) + 4 stale stored forecasts (ADR-0176 Bible basis): 25/26/32
    # never started with both stored dates past, plus 14 — IN PROGRESS with its stored forecast
    # finish (02-27) two months behind the data date and no actual finish, which the old
    # recomputed-CPM rule (actual-start-only) could not see.
    assert checks["Invalid Dates"].count == 5
    assert {c.unique_id for c in checks["Invalid Dates"].citations} == {14, 25, 26, 31, 32}
    # BEI is Acumen "BEI - Value Tasks", cumulative (ADR-0176, corrects ADR-0089): complete AMONG
    # the baselined-due NORMAL tasks / NORMAL baselined-due — 7 of 12 = 0.58 (the 8th completion
    # is not yet baselined-due, so it no longer inflates the numerator; milestones AND summaries
    # excluded by type; no baseline-duration filter)
    assert checks["BEI"].value == 0.58
    assert checks["Missed Activities"].count == 7


def test_tp3_schedule_quality_matches_the_operators_fuse_ribbon() -> None:
    """The Fuse §A ribbon values the operator captured on 2026-06-12 — every row."""
    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality

    sq = compute_schedule_quality(_load("TP3_Outage_DCMA_Seeded.xml"))
    assert sq["missing_logic"].count == 8  # Fuse: 8 (38%)
    assert sq["logic_density"].value == 2.38
    assert sq["critical"].count == 5  # Fuse: 5 (42%)
    assert sq["hard_constraints"].count == 2
    assert sq["negative_float"].count == 3
    # Insufficient Detail™: the authoritative library's Bible formula (current Original duration /
    # project CALENDAR span > 10%, ADR-0084), which matches Acumen's Large-File report (43). The
    # operator RE-RAN TP3 through this library in Acumen and confirmed 9 (the earlier 2026-06-12
    # capture of 8 used an older library).
    assert sq["insufficient_detail"].count == 9
    assert sq["insufficient_detail"].offender_uids == (13, 14, 23, 24, 25, 26, 27, 29, 31)
    assert sq["number_of_lags"].count == 3  # Fuse: 3 (14%) — distinct activities
    assert sq["number_of_leads"].count == 1  # Fuse: 1 (5%) — both leads target UID 29
    assert sq["merge_hotspot"].count == 2


def test_tp4_cei_follows_the_completed_on_time_definition() -> None:
    """CEI (Finish) = completed_on_time / forecast_to_be_finished (metric dictionary):
    v4 must NOT get credit for an unplanned March-spillover finish (0.50, not 1.00)."""
    versions = [_load(f"TP4_DataCenter_v{i}.xml") for i in range(1, 6)]
    ceis = [s.cei for s in compute_bow_wave(versions).snapshots]
    assert ceis == [None, 0.67, 0.67, 0.5, 0.0]


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
