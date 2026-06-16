"""EVM / baseline-compliance tests — Acumen §C golden parity + synthetic edge cases.

The golden test reproduces `PARITY-TARGETS.md §C` exactly for every count and for
Baseline Finish Compliance; Baseline Start Compliance carries a documented residual
(ADR-0013) and is asserted at the engine's computed value, with the Acumen golden
recorded in `case.json` for the M9 calibration.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from schedule_forensics.engine.metrics import (
    CheckStatus,
    compute_baseline_compliance,
    compute_evm_indices,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(tasks: list[Task], **kw: object) -> Schedule:
    return Schedule(name="s", project_start=MON, tasks=tuple(tasks), **kw)


@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_golden_baseline_compliance_parity(project: str, golden: Callable[[str], Schedule]) -> None:
    case = json.loads((GOLDEN / "project2_5" / "case.json").read_text())[project]
    c = compute_baseline_compliance(golden(project))
    g = case["baseline_compliance"]

    # every §C count is exact
    for key in (
        "forecast_to_be_finished",
        "completed_on_time",
        "completed_late",
        "not_completed",
        "forecast_to_be_started",
        "started_on_time",
        "started_late",
        "not_started",
    ):
        assert c[key].count == g[key], f"{project} {key}: {c[key].count} != {g[key]}"

    # finish + start counts reconcile to the forecast-to-be totals
    assert (
        c["completed_on_time"].count + c["completed_late"].count + c["not_completed"].count
        == c["forecast_to_be_finished"].count
    )
    assert (
        c["started_on_time"].count + c["started_late"].count + c["not_started"].count
        == c["forecast_to_be_started"].count
    )

    # Baseline Finish Compliance is exact (33% / 20%)
    assert round(c["baseline_finish_compliance"].value) == g["baseline_finish_compliance_pct"]

    # Baseline Start Compliance: documented residual (ADR-0013) — engine = started-on-time /
    # forecast-to-be-started; golden uses a different denominator. Counts above are exact.
    engine_bsc = round(c["baseline_start_compliance"].value)
    assert engine_bsc == (38 if project == "Project2" else 23)
    assert engine_bsc != g["baseline_start_compliance_pct"]  # the tracked delta


def test_baseline_compliance_no_status_date_is_na() -> None:
    c = compute_baseline_compliance(_sched([Task(unique_id=1, name="A", duration_minutes=DAY)]))
    assert all(r.status is CheckStatus.NOT_APPLICABLE for r in c.values())
    assert c["forecast_to_be_finished"].count == 0


def test_completed_on_time_late_and_not_completed() -> None:
    status = dt.datetime(2025, 2, 1, 17, 0)
    bf = dt.datetime(2025, 1, 10, 17, 0)  # baselined to finish before status -> "due"
    tasks = [
        Task(
            unique_id=1,
            name="ontime",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=bf,
            actual_finish=dt.datetime(2025, 1, 9, 17, 0),
        ),
        Task(
            unique_id=2,
            name="late",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=bf,
            actual_finish=dt.datetime(2025, 1, 15, 17, 0),
        ),
        Task(unique_id=3, name="open", duration_minutes=DAY, baseline_finish=bf),
        # not due (baseline finish after status) -> excluded from the panel entirely
        Task(
            unique_id=4,
            name="future",
            duration_minutes=DAY,
            baseline_finish=dt.datetime(2025, 3, 1, 17, 0),
        ),
    ]
    c = compute_baseline_compliance(_sched(tasks, status_date=status))
    assert c["forecast_to_be_finished"].count == 3
    assert c["completed_on_time"].count == 1
    assert c["completed_late"].count == 1
    assert c["not_completed"].count == 1
    assert round(c["baseline_finish_compliance"].value) == 33  # 1/3


def test_started_on_time_late_not_started() -> None:
    status = dt.datetime(2025, 2, 1, 17, 0)
    bs = dt.datetime(2025, 1, 10, 8, 0)
    tasks = [
        Task(
            unique_id=1,
            name="ontime",
            duration_minutes=DAY,
            baseline_start=bs,
            actual_start=dt.datetime(2025, 1, 8, 8, 0),
            percent_complete=50.0,
        ),
        Task(
            unique_id=2,
            name="late",
            duration_minutes=DAY,
            baseline_start=bs,
            actual_start=dt.datetime(2025, 1, 14, 8, 0),
            percent_complete=50.0,
        ),
        Task(unique_id=3, name="notstarted", duration_minutes=DAY, baseline_start=bs),
    ]
    c = compute_baseline_compliance(_sched(tasks, status_date=status))
    assert c["forecast_to_be_started"].count == 3
    assert c["started_on_time"].count == 1
    assert c["started_late"].count == 1
    assert c["not_started"].count == 1
    assert c["not_started"].offender_uids == (3,)


def test_evm_indices_na_without_cost(golden_project5: Schedule) -> None:
    e = compute_evm_indices(golden_project5)
    assert e["spi"].status is CheckStatus.NOT_APPLICABLE
    assert e["cpi"].status is CheckStatus.NOT_APPLICABLE
    assert e["tcpi"].status is CheckStatus.NOT_APPLICABLE


def test_evm_indices_cost_loaded() -> None:
    status = dt.datetime(2025, 2, 1, 17, 0)
    bf = dt.datetime(2025, 1, 10, 17, 0)
    tasks = [
        Task(
            unique_id=1,
            name="done",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=bf,
            budgeted_cost=100.0,
            actual_cost=120.0,
        ),
        Task(
            unique_id=2,
            name="half",
            duration_minutes=DAY,
            percent_complete=50.0,
            baseline_finish=bf,
            budgeted_cost=100.0,
            actual_cost=40.0,
        ),
    ]
    e = compute_evm_indices(_sched(tasks, status_date=status))
    # BCWP = 100 + 50 = 150; BCWS (baselined due) = 200; SPI = 0.75
    assert e["spi"].value == 0.75 and e["spi"].status is CheckStatus.FAIL
    # CPI = 150 / 160 = 0.94
    assert e["cpi"].value == 0.94
    # TCPI = (200 - 150) / (200 - 160) = 1.25
    assert e["tcpi"].value == 1.25


def test_cei_equals_baseline_compliance(golden_project2: Schedule) -> None:
    c = compute_baseline_compliance(golden_project2)
    e = compute_evm_indices(golden_project2)
    assert e["cei_finish"].value == c["baseline_finish_compliance"].value
    assert e["cei_start"].value == c["baseline_start_compliance"].value


@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_cei_golden_values(project: str, golden: Callable[[str], Schedule]) -> None:
    """CEI re-verification (ADR-0052): pin the single-schedule EVM CEI numerator/denominator
    and the resulting percentage against the recorded golden, for both projects.

    CEI (Finish) = completed_on_time / forecast_to_be_finished (= Baseline Finish Compliance,
    exact vs Acumen). CEI (Start) = started_on_time / forecast_to_be_started — its value
    equals Acumen's own "Started On Time" % exactly (38 / 23); the separately-reported
    "Baseline Start Compliance" headline (41 / 25) is a different denominator (ADR-0013).
    """
    case = json.loads((GOLDEN / "project2_5" / "case.json").read_text())[project]
    g = case["cei"]
    e = compute_evm_indices(golden(project))

    cf, cs = e["cei_finish"], e["cei_start"]
    # numerator (count) and denominator (population) are the exact §C counts
    assert (cf.count, cf.population) == (g["cei_finish_count"], g["cei_finish_population"])
    assert (cs.count, cs.population) == (g["cei_start_count"], g["cei_start_population"])
    # the percentages are pinned to one decimal (33.3/19.6 finish, 37.9/22.9 start)
    assert cf.value == g["cei_finish_value"]
    assert cs.value == g["cei_start_value"]
    # CEI (Start)'s value rounds to Acumen's "Started On Time" % (the engine is right there);
    # only the separate BSC headline carries the tracked +3pt denominator residual
    acumen_started_on_time_pct = 38 if project == "Project2" else 23
    assert round(cs.value) == acumen_started_on_time_pct


def test_spi_t_behind_schedule_and_na() -> None:
    # behind: only the earliest-planned activity is complete at a late status date
    status = dt.datetime(2025, 3, 1, 17, 0)
    tasks = [
        Task(
            unique_id=1,
            name="early",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
            actual_finish=dt.datetime(2025, 1, 8, 17, 0),
        ),
        Task(
            unique_id=2,
            name="mid",
            duration_minutes=DAY,
            percent_complete=0.0,
            baseline_finish=dt.datetime(2025, 1, 20, 17, 0),
        ),
        Task(
            unique_id=3,
            name="late",
            duration_minutes=DAY,
            percent_complete=0.0,
            baseline_finish=dt.datetime(2025, 2, 20, 17, 0),
        ),
    ]
    e = compute_evm_indices(_sched(tasks, status_date=status))
    assert e["spi_t"].status is CheckStatus.FAIL  # earned schedule << actual time
    assert 0.0 < e["spi_t"].value < 1.0
    # no completions -> NA (never a fabricated 0)
    e2 = compute_evm_indices(
        _sched(
            [
                Task(
                    unique_id=1,
                    name="A",
                    duration_minutes=DAY,
                    baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
                )
            ],
            status_date=status,
        )
    )
    assert e2["spi_t"].status is CheckStatus.NOT_APPLICABLE


def test_spi_t_all_planned_complete_caps_at_last_finish() -> None:
    # every baselined activity is complete -> earned schedule caps at the last planned finish
    status = dt.datetime(2025, 3, 1, 17, 0)
    tasks = [
        Task(
            unique_id=1,
            name="a",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
            actual_finish=dt.datetime(2025, 1, 8, 17, 0),
        ),
        Task(
            unique_id=2,
            name="b",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=dt.datetime(2025, 1, 20, 17, 0),
            actual_finish=dt.datetime(2025, 1, 20, 17, 0),
        ),
    ]
    e = compute_evm_indices(_sched(tasks, status_date=status))
    assert e["spi_t"].status is CheckStatus.FAIL  # ES capped < actual time (status far out)
    assert 0.0 < e["spi_t"].value < 1.0


def test_evm_cost_loaded_without_status_or_actuals_is_na() -> None:
    # budget present but no status date -> BCWS = 0 and ACWP = 0 -> SPI/CPI/TCPI all NA
    tasks = [
        Task(
            unique_id=1,
            name="x",
            duration_minutes=DAY,
            percent_complete=50.0,
            budgeted_cost=100.0,
            baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
        ),
    ]
    e = compute_evm_indices(_sched(tasks))  # no status_date
    assert e["spi"].status is CheckStatus.NOT_APPLICABLE  # BCWS = 0
    assert e["cpi"].status is CheckStatus.NOT_APPLICABLE  # ACWP = 0
    assert e["tcpi"].status is CheckStatus.FAIL  # (BAC-BCWP)/(BAC-0) = 50/100 = 0.5
