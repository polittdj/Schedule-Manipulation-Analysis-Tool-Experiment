"""Elapsed-duration axis regressions (QC audit 2026-07-01, batch R2 / ADR-0139).

The parity goldens contain no elapsed activity and no non-480 calendar, so none of these defects
could fail the gate: D2 (the CPM backward pass fabricated negative float for a weekend-spanning
elapsed activity), D3 (DCMA-12 injected a working-minute delay into a wall-clock duration and
falsely FAILed), D13 (recommendations converted float days with a fixed 480), and D21 (a margin
task's elapsed duration displayed on the working axis). Each test here is the audit's minimal
reproduction, pinned.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics.margin import compute_margin
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

_FRIDAY = dt.datetime(2026, 1, 2, 8, 0)
_MONDAY = dt.datetime(2026, 1, 5, 8, 0)


def _elapsed(minutes: int, **kw) -> Task:  # type: ignore[no-untyped-def]
    return Task(unique_id=1, name="E", duration_minutes=minutes, duration_is_elapsed=True, **kw)


def test_weekend_spanning_elapsed_task_has_zero_not_negative_float_qc_d2() -> None:
    """D2: a lone, unconstrained 2-eday task starting Friday finishes Sunday; the lossy
    instant round-trip used to reconstruct its late start as Wednesday and fabricate TF=-480
    (false DCMA-07/CPLI failures). Float is now computed in cap space: TF must be 0."""
    t = compute_cpm(Schedule(name="d2", project_start=_FRIDAY, tasks=(_elapsed(2880),))).timings[1]
    assert t.total_float == 0
    assert t.late_start == t.early_start and t.late_finish == t.early_finish


def test_elapsed_chain_and_monday_control_keep_zero_float_qc_d2() -> None:
    sch = Schedule(
        name="d2x",
        project_start=_FRIDAY,
        tasks=(_elapsed(2880), Task(unique_id=2, name="N", duration_minutes=480)),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    assert {u: x.total_float for u, x in compute_cpm(sch).timings.items()} == {1: 0, 2: 0}
    mon = compute_cpm(Schedule(name="c", project_start=_MONDAY, tasks=(_elapsed(2880),)))
    assert mon.timings[1].total_float == 0


def test_genuinely_negative_elapsed_float_is_still_detected_qc_d2() -> None:
    """The fix must not mask REAL negative float: an FNLT a full working day before the
    finish still reports negative (cap space preserves constraint violations)."""
    sch = Schedule(
        name="neg",
        project_start=_FRIDAY,
        tasks=(
            _elapsed(
                2880,
                constraint_type=ConstraintType.FNLT,
                constraint_date=dt.datetime(2026, 1, 1, 17, 0),
            ),
        ),
    )
    assert compute_cpm(sch).timings[1].total_float < 0


def _dcma12(schedule: Schedule) -> str:
    audit = audit_schedule(schedule, compute_cpm(schedule))
    (check,) = [c for c in audit.checks if c.name == "Critical Path Test"]
    return str(check.status)


def test_dcma12_passes_a_perfect_elapsed_schedule_qc_d3() -> None:
    """D3: the 100-day test delay is injected on the task's OWN axis (wall-clock for an elapsed
    activity) with the expected finish movement computed exactly — a structurally perfect
    schedule whose tested critical activity is elapsed must PASS, weekend-spanning or not."""
    assert _dcma12(Schedule(name="m", project_start=_MONDAY, tasks=(_elapsed(1440),))) == "PASS"
    assert _dcma12(Schedule(name="f", project_start=_FRIDAY, tasks=(_elapsed(2880),))) == "PASS"


def test_recommendation_float_days_use_the_schedule_calendar_qc_d13() -> None:
    """D13: -600 minutes of deadline-driven float on a 600-min/day calendar is exactly -1.0
    working day (the fixed 480 reported -1.2 / +25% impact into the risk matrix)."""
    cal = Calendar(uid=0, name="TenHr", working_minutes_per_day=600)
    sch = Schedule(
        name="d13",
        project_start=_MONDAY,
        calendar=cal,
        tasks=(
            Task(
                unique_id=1,
                name="T",
                duration_minutes=1200,
                deadline=dt.datetime(2026, 1, 5, 18, 0),
            ),
        ),
    )
    quantified = [
        f for f in recommend(sch, current_cpm=compute_cpm(sch)) if f.float_days is not None
    ]
    assert quantified, "expected at least one quantified finding"
    assert quantified[0].float_days == -1.0
    assert quantified[0].impact_days == 1.0


def test_margin_task_elapsed_duration_displays_on_its_own_axis_qc_d21() -> None:
    """D21: a '5 eday' margin task is 5.0 days, not 15.0 (7200 wall-clock min / 480)."""
    sch = Schedule(
        name="d21",
        project_start=_MONDAY,
        tasks=(
            Task(
                unique_id=1,
                name="Schedule Margin",
                duration_minutes=7200,
                duration_is_elapsed=True,
            ),
        ),
    )
    margin = compute_margin(sch, compute_cpm(sch))
    assert margin.tasks and margin.tasks[0].duration_days == 5.0
