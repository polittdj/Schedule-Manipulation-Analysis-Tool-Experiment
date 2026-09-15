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
    Direction,
    compute_baseline_compliance,
    compute_evm_indices,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.resource import Resource
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

    # Baseline Start Compliance now exact (41% / 25%) — the Half-Step-Delay definition compares the
    # actual START to the baseline FINISH, resolving the former ADR-0013 residual (ADR-0083).
    assert round(c["baseline_start_compliance"].value) == g["baseline_start_compliance_pct"]


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


def test_on_time_execution_thresholds_score_pass_fail() -> None:
    """ADR-0161: the on-time execution indices score against the DCMA-derived 95% bar; their late
    mirrors against 5%; the informational counts stay N/A. On the 1/3-on-time case above BFC/CEI
    fall well short of 95% -> FAIL, while the informational counts carry no threshold."""
    status = dt.datetime(2025, 2, 1, 17, 0)
    bf = dt.datetime(2025, 1, 10, 17, 0)
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
    ]
    c = compute_baseline_compliance(_sched(tasks, status_date=status))
    assert c["baseline_finish_compliance"].threshold == 95.0
    assert c["baseline_finish_compliance"].status is CheckStatus.FAIL  # 33% < 95%
    assert c["completed_on_time"].status is CheckStatus.FAIL
    assert c["completed_late"].threshold == 5.0
    assert c["completed_late"].status is CheckStatus.FAIL  # 33% late > 5%
    # informational counts carry no threshold and stay N/A by design
    assert c["forecast_to_be_finished"].threshold is None
    assert c["not_completed"].status is CheckStatus.NOT_APPLICABLE
    # a schedule delivering every due activity on time -> PASS at the 95% bar
    good = compute_baseline_compliance(_sched([tasks[0], tasks[2]], status_date=status))
    assert good["baseline_finish_compliance"].value == 50.0  # 1 of 2 due on time (task 3 open)
    # and an all-on-time set passes
    on_time_only = [
        Task(
            unique_id=i,
            name=f"t{i}",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=bf,
            actual_finish=dt.datetime(2025, 1, 9, 17, 0),
        )
        for i in range(1, 21)
    ]
    passing = compute_baseline_compliance(_sched(on_time_only, status_date=status))
    assert passing["baseline_finish_compliance"].value == 100.0
    assert passing["baseline_finish_compliance"].status is CheckStatus.PASS


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
    # CEI (Finish) == Baseline Finish Compliance (both completed-on-time / forecast-to-be-finished).
    assert e["cei_finish"].value == c["baseline_finish_compliance"].value
    # CEI (Start) == "Started On Time" % (start <= baseline START), which is DISTINCT from Baseline
    # Start Compliance (start <= baseline FINISH, the Half-Step-Delay definition) — ADR-0083.
    assert e["cei_start"].value == c["started_on_time"].value
    assert e["cei_start"].value != c["baseline_start_compliance"].value


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
    # (BAC-BCWP)/(BAC-0) = 50/100 = 0.5 — only half the planned efficiency is still needed,
    # which is COMFORTABLE, so it passes. This line asserted FAIL until MF-01 (ADR-0410):
    # the old assertion pinned the inverted direction, not a measured truth.
    assert e["tcpi"].status is CheckStatus.PASS


def test_tcpi_passes_low_and_fails_high_as_its_published_definition_states() -> None:
    """MF-01 (ADR-0410): TCPI is INVERTED relative to SPI/CPI, and was scored as if it were not.

    TCPI = (BAC - EV) / (BAC - AC) is the cost efficiency the REMAINING work must achieve.
    Above 1.0 the programme must outperform its own plan to land on budget — bad news; at or
    below 1.0 it has room — good news. `help.py` publishes exactly that ("pass <= 1.0 …
    > 1.0 requires better-than-planned performance"), while the engine evaluated every index
    with `Direction.GE`, so a programme that could NOT afford its remaining work reported
    PASS and a comfortable one reported FAIL — the worst direction to be wrong in for an
    affordability figure quoted in testimony.
    """
    overspent = compute_evm_indices(
        _sched(
            [
                Task(
                    unique_id=1,
                    name="overspent",
                    duration_minutes=DAY,
                    percent_complete=20.0,
                    budgeted_cost=1000.0,
                    actual_cost=500.0,
                )
            ]
        )
    )["tcpi"]
    # 20% earned for half the budget: the rest must run at 1.6x planned efficiency.
    assert overspent.value == 1.6
    assert overspent.status is CheckStatus.FAIL
    assert overspent.direction is Direction.LE
    assert overspent.threshold == 1.0

    comfortable = compute_evm_indices(
        _sched(
            [
                Task(
                    unique_id=1,
                    name="comfortable",
                    duration_minutes=DAY,
                    percent_complete=80.0,
                    budgeted_cost=1000.0,
                    actual_cost=200.0,
                )
            ]
        )
    )["tcpi"]
    assert comfortable.value == 0.25
    assert comfortable.status is CheckStatus.PASS


def test_spi_and_cpi_keep_the_higher_is_better_direction() -> None:
    """The other half of MF-01: fixing TCPI must not flip its neighbours through the shared
    `_index` helper — SPI and CPI really are 'higher is better' and stay GE 1.0."""
    e = compute_evm_indices(
        _sched(
            [
                Task(
                    unique_id=1,
                    name="t",
                    duration_minutes=DAY,
                    percent_complete=80.0,
                    budgeted_cost=1000.0,
                    actual_cost=200.0,
                    baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
                )
            ],
            status_date=dt.datetime(2025, 1, 9, 17, 0),
        )
    )
    assert e["cpi"].direction is Direction.GE and e["cpi"].status is CheckStatus.PASS
    assert e["spi"].direction is Direction.GE


def test_spi_t_acumen_rules_in_progress_zero_and_zero_span_excluded() -> None:
    """ADR-0176 — the Acumen per-activity SPI(t) reverse-engineered rules, each proven against
    the Fuse Metric History on the Hard_File series (parity-pinned in fuse_hardfile):
    completed = baseline span / actual span (calendar); a STARTED-incomplete activity dilutes
    the average with a 0 term (blank ActualFinish in the Fuse formula); a zero-span completion
    (milestone) and a never-started activity contribute nothing."""
    status = MON + dt.timedelta(days=20)
    tasks = [
        # completed on baseline pace: 5d baselined, 5d actual -> 1.0
        Task(
            unique_id=1,
            name="on-pace",
            duration_minutes=5 * DAY,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=5),
            actual_start=MON,
            actual_finish=MON + dt.timedelta(days=5),
            percent_complete=100.0,
        ),
        # completed at half pace: 5d baselined, 10d actual -> 0.5
        Task(
            unique_id=2,
            name="half-pace",
            duration_minutes=5 * DAY,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=5),
            actual_start=MON,
            actual_finish=MON + dt.timedelta(days=10),
            percent_complete=100.0,
        ),
        # started, incomplete -> contributes a 0 term (dilutes)
        Task(
            unique_id=3,
            name="in-progress",
            duration_minutes=5 * DAY,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=5),
            actual_start=MON + dt.timedelta(days=6),
            percent_complete=40.0,
        ),
        # zero-span completion (milestone-like) -> EXCLUDED entirely
        Task(
            unique_id=4,
            name="ms",
            duration_minutes=0,
            is_milestone=True,
            baseline_start=MON,
            baseline_finish=MON,
            actual_start=MON,
            actual_finish=MON,
            percent_complete=100.0,
        ),
        # never started -> contributes nothing
        Task(
            unique_id=5,
            name="future",
            duration_minutes=5 * DAY,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=5),
        ),
    ]
    r = compute_evm_indices(_sched(tasks, status_date=status))["spi_t_acumen"]
    # (1.0 + 0.5 + 0) / 3 = 0.5 — milestone and unstarted excluded
    assert r.value == 0.5
    assert r.population == 3
    # without a status date the in-progress term cannot be assessed; completions still average
    r2 = compute_evm_indices(_sched(tasks))["spi_t_acumen"]
    assert r2.value == 0.75 and r2.population == 2


# --- ADR-0473: time-phased BCWS and the CPI/TCPI actuals disclosure ---------------------------


def test_bcws_accrues_each_budget_linearly_over_its_baseline_span() -> None:
    """The planned value of an activity straddling the status date is the elapsed share of its
    baseline span (working time), not all-or-nothing at its baseline finish: a 10-day, 1,000-unit
    activity baselined to run days 0-10 contributes 400 at a status date 4 working days in. The
    former step function read 0 for it — 12,400 where Fuse read 16,000 on the operator's
    Hard_File_updated (the multi-project oracle pins the real file; this pins the rule)."""
    status = MON + dt.timedelta(days=4)  # Friday 08:00 — 4 working days elapsed
    tasks = [
        Task(  # baselined to finish before status: the whole budget
            unique_id=1,
            name="done-plan",
            duration_minutes=2 * DAY,
            budgeted_cost=500.0,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=1, hours=9),
        ),
        Task(  # straddles the status date: 4 of 10 working days -> 40 %
            unique_id=2,
            name="straddle",
            duration_minutes=10 * DAY,
            budgeted_cost=1000.0,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=11, hours=9),
        ),
        Task(  # baselined to start after status: nothing yet
            unique_id=3,
            name="future",
            duration_minutes=5 * DAY,
            budgeted_cost=700.0,
            baseline_start=MON + dt.timedelta(days=14),
            baseline_finish=MON + dt.timedelta(days=18, hours=9),
        ),
    ]
    from schedule_forensics.engine.metrics.evm import _planned_value

    sched = _sched(tasks, status_date=status)
    assert _planned_value(sched, tasks) == pytest.approx(500.0 + 400.0)


def test_cpi_and_tcpi_disclose_started_budgeted_activities_with_no_actual_cost() -> None:
    """R-01 (ADR-0473): ACWP is the library's sum(ACWPAC) — a blank actual is a 0 term — and the
    figure is not fabricated away; instead the started, budgeted activities carrying no actual
    cost ride CPI and TCPI as count / population / offender UIDs, so a CPI flattered by an
    unrecorded spend is never shown without saying so."""
    status = MON + dt.timedelta(days=10)
    tasks = [
        Task(  # started, budgeted, actual recorded
            unique_id=1,
            name="booked",
            duration_minutes=5 * DAY,
            budgeted_cost=1000.0,
            actual_cost=600.0,
            percent_complete=50.0,
            actual_start=MON,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=4, hours=9),
        ),
        Task(  # started, budgeted, NO actual cost — the disclosed case
            unique_id=2,
            name="unbooked",
            duration_minutes=5 * DAY,
            budgeted_cost=1000.0,
            percent_complete=50.0,
            actual_start=MON,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=4, hours=9),
        ),
        Task(  # not started: a missing actual is nothing spent, not a disclosure
            unique_id=3,
            name="unstarted",
            duration_minutes=5 * DAY,
            budgeted_cost=1000.0,
            baseline_start=MON + dt.timedelta(days=14),
            baseline_finish=MON + dt.timedelta(days=18, hours=9),
        ),
    ]
    e = compute_evm_indices(_sched(tasks, status_date=status))
    assert e["cpi"].value == 1.67  # 1000 earned / 600 spent — the blank read as 0
    assert e["cpi"].count == 1 and e["cpi"].population == 2
    assert e["cpi"].offender_uids == (2,)
    assert e["tcpi"].count == 1 and e["tcpi"].offender_uids == (2,)
    assert e["spi"].offender_uids == ()  # SPI has no ACWP term — nothing to disclose


# --- ADR-0492 (R-46): BCWS is the file's own time-phased baseline cost -----------------------

_STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
_CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
_CREW = Resource(unique_id=1, name="Crew")  # on the project pattern
_CREW_24 = Resource(unique_id=2, name="Round-the-clock crew", calendar_uid=10)
TUE_1700 = MON + dt.timedelta(days=1, hours=9)


def _cost_sched(tasks: list[Task], status: dt.datetime) -> Schedule:
    return Schedule(
        name="s",
        project_start=MON,
        calendar=_STANDARD,
        calendars=(_STANDARD, _CAL_24),
        resources=(_CREW, _CREW_24),
        tasks=tuple(tasks),
        status_date=status,
    )


def test_bcws_is_the_bookings_recorded_baseline_cost_where_the_file_carries_it() -> None:
    """R-46 (ADR-0492): the Bible's PV (BCWS) is ``sum(BCWSPV)`` — each activity's BCWS as MS
    Project stores it, its bookings' time-phased baseline cost through the status date. Where the
    file carries that series (an MSPDI booking's Type-5 blocks) the engine sums it: a block
    finishing on or before the status date counts whole, one starting at or after it counts
    nothing. Task 2's crew front-loads the same 6,000 budget over the same six-day baseline span
    as task 1 (a 16-hour day — Hard_File_updated UID 187's shape), so 4,800 of it is planned by
    Tuesday 17:00 where the project-calendar proration reads 2,000 (Fuse's 16,000 ribbon against
    the engine's 16,150); task 1 (no series) keeps the linear rule; task 3 (no series, baselined
    before the status date) contributes whole."""
    from schedule_forensics.engine.metrics.evm import _planned_value
    from schedule_forensics.model.assignment import Assignment, CostPiece

    bl_start, bl_finish = MON, MON + dt.timedelta(days=7, hours=9)  # Mon .. next Mon 17:00
    h = dt.timedelta(hours=1)
    pieces = (
        CostPiece(start=MON, finish=MON + 9 * h, cost=1600.0),  # Mon 08:00-17:00
        CostPiece(start=MON + 9 * h, finish=MON + 15 * h, cost=1200.0),  # Mon 17:00-23:00
        CostPiece(start=MON + 22 * h, finish=MON + 24 * h, cost=400.0),  # Tue 06:00-08:00
        CostPiece(start=MON + 24 * h, finish=TUE_1700, cost=1600.0),  # finishes AT the status
        CostPiece(start=TUE_1700, finish=TUE_1700 + 6 * h, cost=1200.0),  # starts AT it
    )
    tasks = [
        Task(
            unique_id=1,
            name="linear",
            duration_minutes=6 * DAY,
            budgeted_cost=6000.0,
            baseline_start=bl_start,
            baseline_finish=bl_finish,
        ),
        Task(
            unique_id=2,
            name="front-loaded",
            duration_minutes=6 * DAY,
            budgeted_cost=6000.0,
            baseline_start=bl_start,
            baseline_finish=bl_finish,
            resource_assignments=(
                Assignment(resource_id=1, work_minutes=6 * DAY, baseline_cost_pieces=pieces),
            ),
        ),
        Task(
            unique_id=3,
            name="done-plan",
            duration_minutes=DAY,
            budgeted_cost=800.0,
            baseline_start=MON,
            baseline_finish=MON + 9 * h,
        ),
    ]
    sched = _cost_sched(tasks, TUE_1700)
    assert _planned_value(sched, [tasks[0]]) == pytest.approx(2000.0)
    assert _planned_value(sched, [tasks[1]]) == pytest.approx(4800.0)
    assert _planned_value(sched, [tasks[2]]) == pytest.approx(800.0)
    assert _planned_value(sched, tasks) == pytest.approx(7600.0)


def test_a_straddling_block_is_prorated_in_working_minutes_of_the_bookings_calendar() -> None:
    """The writer merges equal days into one block (Hard_File_updated3 UID 270: three project
    days, one block, 4,800); a block the status date falls inside contributes the share of ITS
    working time that has elapsed, on the calendar the booking is scheduled on (ADR-0474's
    rule). One Monday-08:00-to-Wednesday-17:00 block of 3,000 on a project-pattern crew is two
    of three days (2,000) by Tuesday 17:00; on a round-the-clock crew it is 33 of 57 hours
    (1,736.84). Elapsed time would read the first as 1,736.84 too — the calendar is the ruler."""
    from schedule_forensics.engine.metrics.evm import _planned_value
    from schedule_forensics.model.assignment import Assignment, CostPiece

    wed_1700 = MON + dt.timedelta(days=2, hours=9)
    block = CostPiece(start=MON, finish=wed_1700, cost=3000.0)

    def task(uid: int, crew: int) -> Task:
        return Task(
            unique_id=uid,
            name=f"t{uid}",
            duration_minutes=3 * DAY,
            budgeted_cost=3000.0,
            baseline_start=MON,
            baseline_finish=wed_1700,
            resource_assignments=(
                Assignment(resource_id=crew, work_minutes=3 * DAY, baseline_cost_pieces=(block,)),
            ),
        )

    on_pattern, round_the_clock = task(1, 1), task(2, 2)
    sched = _cost_sched([on_pattern, round_the_clock], TUE_1700)
    assert _planned_value(sched, [on_pattern]) == pytest.approx(2000.0)
    assert _planned_value(sched, [round_the_clock]) == pytest.approx(3000.0 * 33 / 57)


def test_the_budget_no_booking_carries_accrues_linearly_beside_the_recorded_series() -> None:
    """A task's baseline cost can exceed what its bookings' series carry (Hard_File_updated2 /
    updated3 UID 257: 800 of baseline cost and no assignment series — a booking baselined and
    since removed); the uncarried remainder accrues by the linear rule over the task's baseline
    span while the series counts by its blocks. A series that exceeds the task's baseline cost
    stands as recorded — nothing is subtracted: the file's arithmetic, not the tool's."""
    from schedule_forensics.engine.metrics.evm import _planned_value
    from schedule_forensics.model.assignment import Assignment, CostPiece

    tue_1700 = MON + dt.timedelta(days=1, hours=9)  # a two-day baseline span, Mon .. Tue
    monday = CostPiece(start=MON, finish=MON + dt.timedelta(hours=9), cost=600.0)

    def task(uid: int, budget: float) -> Task:
        return Task(
            unique_id=uid,
            name=f"t{uid}",
            duration_minutes=2 * DAY,
            budgeted_cost=budget,
            baseline_start=MON,
            baseline_finish=tue_1700,
            resource_assignments=(
                Assignment(resource_id=1, work_minutes=2 * DAY, baseline_cost_pieces=(monday,)),
            ),
        )

    part, over = task(1, 1000.0), task(2, 500.0)
    status = MON + dt.timedelta(days=1)  # Tuesday 08:00: one of the two working days elapsed
    sched = _cost_sched([part, over], status)
    assert _planned_value(sched, [part]) == pytest.approx(600.0 + 0.5 * 400.0)
    assert _planned_value(sched, [over]) == pytest.approx(600.0)


def test_a_block_the_calendar_sees_no_working_time_in_is_measured_by_elapsed_time() -> None:
    """The writer's calendar and the rule's can differ (R-58's approximation): a block that the
    booking's calendar sees no working time in — a Saturday block on a Monday-to-Friday crew —
    cannot be prorated in working minutes, so it is measured by elapsed time, the only ruler
    left: 4 of 9 hours by Saturday noon. The whole block counts once the status date passes it."""
    from schedule_forensics.engine.metrics.evm import _planned_value
    from schedule_forensics.model.assignment import Assignment, CostPiece

    sat_0800 = MON + dt.timedelta(days=5)
    block = CostPiece(start=sat_0800, finish=sat_0800 + dt.timedelta(hours=9), cost=900.0)
    task = Task(
        unique_id=1,
        name="weekend",
        duration_minutes=DAY,
        budgeted_cost=900.0,
        baseline_start=MON,
        baseline_finish=MON + dt.timedelta(days=7, hours=9),
        resource_assignments=(
            Assignment(resource_id=1, work_minutes=DAY, baseline_cost_pieces=(block,)),
        ),
    )
    noon = _cost_sched([task], sat_0800 + dt.timedelta(hours=4))
    assert _planned_value(noon, [task]) == pytest.approx(900.0 * 4 / 9)
    after = _cost_sched([task], MON + dt.timedelta(days=7))
    assert _planned_value(after, [task]) == pytest.approx(900.0)


def test_spi_t_acumen_counts_started_work_without_a_baseline_as_a_zero_term() -> None:
    """R-47 (ADR-0495) — the population is every STARTED activity with a non-zero actual span,
    baseline or not: the Bible formula evaluates a blank baseline as 0, so an unbaselined
    member dilutes the average exactly like an in-progress one (Large Test File UID 7260, File2
    UIDs 7262 / 7551 — Fuse's Record Count 717 / 726 and its 8.22 / 8.14 prove it); a zero-span
    completion stays excluded whether or not it is baselined (File UID 7183); a never-started
    activity contributes nothing. The members whose term the file cannot know are disclosed by
    UID, the way CPI discloses its blank actuals (ADR-0473)."""
    status = MON + dt.timedelta(days=20)
    tasks = [
        Task(
            unique_id=1,
            name="on-pace",
            duration_minutes=5 * DAY,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=5),
            actual_start=MON,
            actual_finish=MON + dt.timedelta(days=5),
            percent_complete=100.0,
        ),
        Task(
            unique_id=2,
            name="half-pace",
            duration_minutes=5 * DAY,
            baseline_start=MON,
            baseline_finish=MON + dt.timedelta(days=5),
            actual_start=MON,
            actual_finish=MON + dt.timedelta(days=10),
            percent_complete=100.0,
        ),
        # started, incomplete, NO baseline -> a 0 term (Large Test File UID 7260)
        Task(
            unique_id=3,
            name="in-progress-unbaselined",
            duration_minutes=5 * DAY,
            actual_start=MON + dt.timedelta(days=6),
            percent_complete=40.0,
        ),
        # completed, NO baseline, a positive actual span -> a 0 term (File2 UIDs 7262 / 7551)
        Task(
            unique_id=4,
            name="complete-unbaselined",
            duration_minutes=5 * DAY,
            actual_start=MON,
            actual_finish=MON + dt.timedelta(days=5),
            percent_complete=100.0,
        ),
        # completed, NO baseline, zero span -> EXCLUDED (File UID 7183)
        Task(
            unique_id=5,
            name="ms-unbaselined",
            duration_minutes=0,
            is_milestone=True,
            actual_start=MON,
            actual_finish=MON,
            percent_complete=100.0,
        ),
        # never started, NO baseline -> contributes nothing
        Task(unique_id=6, name="future-unbaselined", duration_minutes=5 * DAY),
    ]
    r = compute_evm_indices(_sched(tasks, status_date=status))["spi_t_acumen"]
    # (1.0 + 0.5 + 0 + 0) / 4 = 0.375 -> 0.38 (half-up); the milestone and the unstarted excluded
    assert r.value == 0.38
    assert r.count == 4 and r.population == 4
    assert r.offender_uids == (3, 4)
    # without a status date the in-progress term cannot be assessed; the unbaselined completion
    # still dilutes: (1.0 + 0.5 + 0) / 3
    r2 = compute_evm_indices(_sched(tasks))["spi_t_acumen"]
    assert r2.value == 0.5 and r2.population == 3 and r2.offender_uids == (4,)
