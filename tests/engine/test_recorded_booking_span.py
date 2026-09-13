"""A MATERIAL / COST booking occupies the span the file records for it (ADR-0487, R-56).

MS Project spreads a material or cost booking over a window that no stored quantity determines
— measured on Hard_File_updated3: UID 302's two non-work bookings, 1 unit at 100 % and 0.15
units at 0.06 %, share one 36-hour span; at UID 385 the 1-unit / 100 % booking spans 24 h and
the 2.5-unit / 0.06 % booking 125 h; no stored quantity or rate reproduces both — and
the task finishes where that window ends (both heads of the file's 13-day project-finish
gap). The MSPDI records each booking's ``Start`` / ``Finish``; the engine reads that window as
a leg of the task's execution plan, exactly as it reads a stored leveling delay, and discloses
the task on ``CPMResult.booking_span_driven``. A WORK booking's window is NEVER read: the
engine reproduces it from work / units / calendar (ADR-0474).

Red first: on the pristine tree ``Assignment`` refuses a window (extra forbidden) and
``CPMResult`` carries no ``booking_span_driven``.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import _offset_to_wall, _recorded_span, compute_cpm
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
WED_NOON = dt.datetime(2026, 7, 8, 12, 0)
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
CAL_16 = Calendar(
    uid=11,
    name="16 Hour Work Days",
    working_minutes_per_day=960,
    day_segments=((360, 720), (780, 1380)),
)
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
CREW = Resource(unique_id=1, name="Crew")  # on the project pattern
CREW_16 = Resource(unique_id=2, name="Customer Service Team", calendar_uid=11)
MATERIAL = Resource(unique_id=3, name="Cleaning", type=ResourceType.MATERIAL)
COST = Resource(unique_id=4, name="AI Token Time", type=ResourceType.COST)
MATERIAL_24 = Resource(
    unique_id=5, name="Round-the-clock material", type=ResourceType.MATERIAL, calendar_uid=10
)


def _schedule(*tasks: Task) -> Schedule:
    return Schedule(
        name="recorded spans",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16, CAL_24),
        resources=(CREW, CREW_16, MATERIAL, COST, MATERIAL_24),
        tasks=tasks,
    )


def _finish(sch: Schedule, uid: int, **kw: object) -> dt.datetime:
    tm = compute_cpm(sch, **kw).timing(uid)  # type: ignore[arg-type]
    return tm.early_finish_wall or _offset_to_wall(
        sch.project_start, tm.early_finish, sch.calendar, role="finish"
    )


def _task(uid: int, *assignments: Assignment, duration: int = 480) -> Task:
    return Task(
        unique_id=uid,
        name=f"task {uid}",
        duration_minutes=duration,
        resource_assignments=assignments,
    )


# --- the recorded window is the leg --------------------------------------------------------


def test_a_material_bookings_recorded_window_carries_the_task_past_its_work() -> None:
    """One day of crew work, a cleaning booking recorded Monday 08:00 → Wednesday 12:00: the
    task finishes Wednesday noon (MS Project's stored finish), and says why."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480),
            Assignment(resource_id=3, start=MON, finish=WED_NOON),
        )
    )
    assert _finish(sch, 1) == WED_NOON
    assert compute_cpm(sch).booking_span_driven == (1,)


def test_a_cost_booking_counts_the_same_way() -> None:
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480),
            Assignment(resource_id=4, start=MON, finish=WED_NOON),
        )
    )
    assert _finish(sch, 1) == WED_NOON and compute_cpm(sch).booking_span_driven == (1,)


def test_the_leg_needs_no_off_pattern_crew_to_form_a_plan() -> None:
    """Every leg on the project pattern, and still a plan: the recorded span exceeds the
    duration, and only that keeps the task off the fast path (the ratio > 1 rule)."""
    sch = _schedule(_task(1, Assignment(resource_id=3, start=MON, finish=WED_NOON)))
    assert _finish(sch, 1) == WED_NOON


def test_without_a_recorded_window_a_material_booking_changes_nothing() -> None:
    sch = _schedule(
        _task(1, Assignment(resource_id=1, work_minutes=480), Assignment(resource_id=3))
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 17, 0)
    assert compute_cpm(sch).booking_span_driven == ()


def test_a_window_shorter_than_the_work_never_shortens_the_task() -> None:
    """The latest leg finishes the task. A two-shift crew (a plan forms) with 960 min of work
    ends Tuesday 08:00; a material window recorded Monday 08:00-12:00 is a shorter leg, not
    the primary one, so the finish is the crew's and the task is NOT disclosed as span-driven
    (a rig with only project-pattern legs cannot see this: the fast path drops them all)."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=2, work_minutes=960),
            Assignment(resource_id=3, start=MON, finish=dt.datetime(2026, 7, 6, 12, 0)),
            duration=960,
        )
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 7, 8, 0)
    assert compute_cpm(sch).booking_span_driven == ()


def test_a_work_bookings_window_is_never_read() -> None:
    """A WORK booking recorded over three days for one day of work: the engine reproduces the
    booking from work / units / calendar (ADR-0474) and the recorded window is inert."""
    sch = _schedule(
        _task(1, Assignment(resource_id=1, work_minutes=480, start=MON, finish=WED_NOON))
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 17, 0)
    assert compute_cpm(sch).booking_span_driven == ()


def test_the_leg_scales_with_the_duration_like_every_other_leg() -> None:
    """The SRA hands the solver a duration per iteration; the recorded leg keeps its
    proportion (2.5 x the duration here): 960 → 2,400 min on the project calendar = Friday."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480),
            Assignment(resource_id=3, start=MON, finish=WED_NOON),
        )
    )
    assert _finish(sch, 1, duration_overrides={1: 960}) == dt.datetime(2026, 7, 10, 17, 0)


def test_a_round_the_clock_material_window_is_elapsed_time() -> None:
    """A material on a 24/7 calendar recorded Monday 08:00 → Wednesday 00:00 (40 h) ends the
    task at midnight Wednesday, an instant the project calendar cannot represent."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480),
            Assignment(resource_id=5, start=MON, finish=dt.datetime(2026, 7, 8, 0, 0)),
        )
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 8, 0, 0)


# --- the Hard_File UID 385 shape, to the minute -------------------------------------------


def test_the_hard_file_385_shape_finishes_at_the_recorded_instant() -> None:
    """UID 385: 5,664 min of duration, a 16-hour crew at 100 % for 4,224 min, a cleaning
    booking recorded Monday 08:00 → the third Monday after at 14:24. The window holds 7,524
    working minutes — segment-aware at both ends: 14:24 is 324 minutes into a 08-12 / 13-17
    day, not 384 — and the contiguous projection ruler's 7,584 lands one lunch gap late, at
    15:24 (measured on the golden before this rule shipped)."""
    finish = dt.datetime(2026, 7, 27, 14, 24)
    sch = _schedule(
        _task(
            385,
            Assignment(resource_id=2, work_minutes=4224),
            Assignment(resource_id=3, start=MON, finish=finish),
            duration=5664,
        )
    )
    assert _recorded_span(STANDARD, MON, finish) == 7524
    assert _finish(sch, 385) == finish
    assert compute_cpm(sch).booking_span_driven == (385,)


def test_recorded_span_arithmetic() -> None:
    mon, fri = MON, dt.datetime(2026, 7, 10, 8, 0)
    assert _recorded_span(STANDARD, mon, mon.replace(hour=12)) == 240  # a morning
    assert _recorded_span(STANDARD, mon, mon.replace(hour=14, minute=24)) == 324  # across lunch
    assert (
        _recorded_span(STANDARD, fri, dt.datetime(2026, 7, 13, 12, 0)) == 720
    )  # a weekend between
    assert (
        _recorded_span(STANDARD, dt.datetime(2026, 7, 11, 10, 0), dt.datetime(2026, 7, 13, 12, 0))
        == 240
    )
    assert _recorded_span(CAL_16, mon, dt.datetime(2026, 7, 7, 6, 24)) == 864  # 240 + 600 + 24
    assert (
        _recorded_span(CAL_24, dt.datetime(2026, 7, 11, 0, 0), dt.datetime(2026, 7, 12, 12, 0))
        == 2160
    )
    assert _recorded_span(STANDARD, mon.replace(hour=12), mon) == 0  # inverted
