"""CPM-03 (WP6b, ADR-0467): the ADR-0391 actual-start floor applies under a constraint pin too.

The CPM rulebook says a started task's early start is ``max(logic_es, offset(actual_start))``
without condition, but both forward passes applied that floor only in the no-pin branch: a
started task under a Must-Start-On / Must-Finish-On pin was scheduled at its CONSTRAINT date
even when it demonstrably began later, understating its finish and everything downstream (the
ADR-0108 direction a forensic tool must never be wrong in). MS Project's own rule is the oracle:
on all 240 started tasks in the fixture corpus the stored Start equals the Actual Start whatever
the constraint says (measured 2026-09-06), and no golden carries a started MSO/MFO task, so the
corpus is byte-identical by construction.

Red-first (2026-09-06): A's early start read the MSO date (offset 0), not its actual start.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm, datetime_to_offset
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2026, 3, 2, 8, 0)  # the project start, a Monday
LATE = dt.datetime(2026, 3, 16, 8, 0)  # two working weeks later
DAY = 480
ROUND_THE_CLOCK = Calendar(
    uid=7, name="24x7", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)


def _schedule(
    constraint: ConstraintType,
    constraint_date: dt.datetime,
    actual_start: dt.datetime,
    *,
    calendar_uid: int | None = None,
) -> Schedule:
    a = Task(
        unique_id=1,
        name="A",
        duration_minutes=5 * DAY,
        constraint_type=constraint,
        constraint_date=constraint_date,
        actual_start=actual_start,
        start=actual_start,  # MS Project's own answer: a started task starts when it started
        percent_complete=50.0,
        calendar_uid=calendar_uid,
    )
    b = Task(unique_id=2, name="B", duration_minutes=5 * DAY)
    return Schedule(
        name="s",
        project_start=MON,
        tasks=(a, b),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
        calendars=(ROUND_THE_CLOCK,),
    )


def test_a_started_task_under_a_must_start_on_pin_starts_when_it_started() -> None:
    s = _schedule(ConstraintType.MSO, MON, LATE)
    r = compute_cpm(s)
    late_off = datetime_to_offset(MON, LATE, s.calendar)
    assert late_off == 10 * DAY
    assert r.timings[1].early_start == late_off, r.timings[1]
    assert r.timings[1].early_finish == late_off + 5 * DAY
    assert r.timings[2].early_start >= r.timings[1].early_finish  # the successor follows the truth
    assert 1 in r.actual_start_driven and 1 not in r.date_driven


def test_a_started_task_under_a_must_finish_on_pin_starts_when_it_started() -> None:
    # the MFO pins the FINISH at Friday 17:00 of the first week; the task began two weeks later
    s = _schedule(ConstraintType.MFO, dt.datetime(2026, 3, 6, 17, 0), LATE)
    r = compute_cpm(s)
    assert r.timings[1].early_start == datetime_to_offset(MON, LATE, s.calendar)
    assert 1 in r.actual_start_driven


def test_the_floor_never_moves_a_pinned_start_earlier() -> None:
    # started BEFORE the pin (out of sequence with the constraint): the pin holds — a floor can
    # only push work later, never earlier (ADR-0391's conservative reading)
    s = _schedule(ConstraintType.MSO, LATE, MON)
    r = compute_cpm(s)
    assert r.timings[1].early_start == datetime_to_offset(MON, LATE, s.calendar)
    assert 1 not in r.actual_start_driven


def test_the_execution_calendar_pass_applies_the_same_floor() -> None:
    # a task on its own 24x7 calendar takes the wall-clock (execution-calendar) branch
    s = _schedule(ConstraintType.MSO, MON, LATE, calendar_uid=7)
    r = compute_cpm(s)
    assert r.timings[1].early_start == datetime_to_offset(MON, LATE, s.calendar)
    assert 1 in r.actual_start_driven
    assert r.timings[2].early_start >= r.timings[1].early_finish
