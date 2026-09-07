"""Resource calendars, task types and leveling delay in the base CPM (ADR-0474, R-44).

MS Project schedules an ASSIGNMENT on the resource's calendar: a two-day task whose crew works
24-hour days finishes sixteen wall-clock hours after it starts, not at the end of the second
project-calendar day. Hard_File (00_REFERENCE_INTAKE/mpp) carries crews on 16-hour and
24-hour calendars and twelve resource-leveled activities; the single-calendar engine read its
finish 42 days after MS Project's stored 2026-11-05. Every rule below was derived from that
file's stored Start / Finish / LateStart / LateFinish / TotalSlack (see
tests/parity/test_hard_file_stored_dates_oracle.py); these synthetic cases pin each rule in
isolation so a regression names the rule, not the file.

Red first (2026-09-07): every dated assertion here failed on the pre-ADR-0474 engine (no
``Resource.calendar_uid``, no plan, no leveling delay), by name.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import (
    _offset_to_wall,
    compute_cpm,
    execution_calendar_of,
    injected_finish_wall,
)
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task, TaskType

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
#: the project calendar: MS Project's Standard, 08:00-12:00 + 13:00-17:00
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
#: a round-the-clock crew calendar
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
#: a two-shift crew calendar: 06:00-12:00 + 13:00-23:00, Monday to Friday
CAL_16 = Calendar(
    uid=11,
    name="16 Hour Work Days",
    working_minutes_per_day=960,
    day_segments=((360, 720), (780, 1380)),
)
#: a crew calendar whose pattern equals the project's (the usual derived "Resource X" calendar)
CAL_SAME = Calendar(uid=12, name="Derived Standard", day_segments=((480, 720), (780, 1020)))

CREW_24 = Resource(unique_id=1, name="Content Developer", calendar_uid=10)
CREW_16 = Resource(unique_id=2, name="Customer Service Team", calendar_uid=11)
CREW_STD = Resource(unique_id=3, name="Customer Service Lead", calendar_uid=12)
MATERIAL_24 = Resource(unique_id=4, name="Cleaning", type=ResourceType.MATERIAL, calendar_uid=10)


def _schedule(*tasks: Task, relationships: tuple[Relationship, ...] = ()) -> Schedule:
    return Schedule(
        name="crew calendars",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_24, CAL_16, CAL_SAME),
        resources=(CREW_24, CREW_16, CREW_STD, MATERIAL_24),
        tasks=tasks,
        relationships=relationships,
    )


def _finish(sch: Schedule, uid: int) -> dt.datetime:
    """The finish instant: the wall for a plan task, the segment-aware finish-role instant of
    the project-axis offset for a fast-path task (17:00, MS Project's end of day)."""
    tm = compute_cpm(sch).timing(uid)
    return tm.early_finish_wall or _offset_to_wall(
        sch.project_start, tm.early_finish, sch.calendar, role="finish"
    )


def _assign(resource: Resource, work: int, units: float = 1.0) -> Assignment:
    return Assignment(resource_id=resource.unique_id, work_minutes=work, units=units)


# --- the crew's calendar carries the task ------------------------------------------------


def test_a_24_hour_crew_finishes_a_two_day_task_sixteen_hours_after_it_starts() -> None:
    """Two project days of duration (960 min) run round the clock: Monday 08:00 + 16 h."""
    plain = Task(unique_id=1, name="control", duration_minutes=960)
    crewed = plain.model_copy(update={"resource_assignments": (_assign(CREW_24, 960),)})
    assert _finish(_schedule(plain), 1) == dt.datetime(2026, 7, 7, 17, 0)
    assert _finish(_schedule(crewed), 1) == dt.datetime(2026, 7, 7, 0, 0)
    tm = compute_cpm(_schedule(crewed)).timing(1)
    assert tm.early_start_wall == MON and tm.early_finish_wall == dt.datetime(2026, 7, 7, 0, 0)


def test_a_16_hour_crew_uses_its_evening_shift() -> None:
    """960 min on 06:00-12:00 + 13:00-23:00 from Monday 08:00: 240 + 600 by 23:00, the last
    120 in Tuesday's 06:00-08:00 — MS Project's Hard_File UID 178 shape."""
    crewed = Task(
        unique_id=1,
        name="two shifts",
        duration_minutes=960,
        resource_assignments=(_assign(CREW_16, 960),),
    )
    assert _finish(_schedule(crewed), 1) == dt.datetime(2026, 7, 7, 8, 0)


def test_a_crew_on_the_project_pattern_stays_on_the_integer_fast_path() -> None:
    """A derived resource calendar with the project's own pattern changes nothing: no wall
    instants, byte-identical timings to the unassigned control."""
    plain = Task(unique_id=1, name="control", duration_minutes=960)
    crewed = plain.model_copy(update={"resource_assignments": (_assign(CREW_STD, 960),)})
    assert compute_cpm(_schedule(crewed)).timing(1) == compute_cpm(_schedule(plain)).timing(1)
    assert compute_cpm(_schedule(crewed)).timing(1).early_start_wall is None


def test_material_and_zero_work_assignments_do_not_schedule() -> None:
    """Only WORK resources with work booked carry a calendar; a material on a 24-hour
    calendar, or a crew booked at zero work, leaves the task on the project calendar."""
    material = Task(
        unique_id=1,
        name="m",
        duration_minutes=960,
        resource_assignments=(_assign(MATERIAL_24, 960),),
    )
    no_work = Task(
        unique_id=1, name="w", duration_minutes=960, resource_assignments=(_assign(CREW_24, 0),)
    )
    for task in (material, no_work):
        assert _finish(_schedule(task), 1) == dt.datetime(2026, 7, 7, 17, 0)
        assert compute_cpm(_schedule(task)).timing(1).early_start_wall is None


def test_ignore_resource_calendar_keeps_the_task_on_its_own_calendar() -> None:
    """MS Project's "Scheduling ignores resource calendars" — the crew's 24-hour calendar is
    not consulted."""
    crewed = Task(
        unique_id=1,
        name="ignore",
        duration_minutes=960,
        ignore_resource_calendar=True,
        resource_assignments=(_assign(CREW_24, 960),),
    )
    assert _finish(_schedule(crewed), 1) == dt.datetime(2026, 7, 7, 17, 0)


def test_a_24_hour_task_calendar_yields_the_crew_calendar() -> None:
    """The task's own 24-hour calendar intersected with a 16-hour crew IS the crew calendar
    (the only exact intersection the engine models; any other task calendar wins)."""
    crewed = Task(
        unique_id=1,
        name="both",
        duration_minutes=960,
        calendar_uid=10,
        resource_assignments=(_assign(CREW_16, 960),),
    )
    assert _finish(_schedule(crewed), 1) == dt.datetime(2026, 7, 7, 8, 0)
    other = Task(
        unique_id=1,
        name="task cal wins",
        duration_minutes=960,
        calendar_uid=11,
        resource_assignments=(_assign(CREW_24, 960),),
    )
    assert _finish(_schedule(other), 1) == dt.datetime(2026, 7, 7, 8, 0)


# --- how an assignment spreads over the task -----------------------------------------------


def test_fixed_units_assignments_run_work_over_units_and_the_slowest_crew_governs() -> None:
    """Hard_File UID 200: two 4-hour bookings on an 8-hour task — each crew runs its own
    work / units and the task finishes with the later one; a 24-hour crew booked for the
    full 8 h outlasts a Standard crew booked for 4 h."""
    half_and_half = Task(
        unique_id=1,
        name="200",
        duration_minutes=480,
        resource_assignments=(_assign(CREW_24, 240), _assign(CREW_STD, 240)),
    )
    assert _finish(_schedule(half_and_half), 1) == dt.datetime(2026, 7, 6, 12, 0)
    crew_governs = Task(
        unique_id=1,
        name="24h governs",
        duration_minutes=480,
        resource_assignments=(_assign(CREW_24, 480), _assign(CREW_STD, 240)),
    )
    assert _finish(_schedule(crew_governs), 1) == dt.datetime(2026, 7, 6, 16, 0)
    half_time = Task(
        unique_id=1,
        name="50%",
        duration_minutes=960,
        resource_assignments=(_assign(CREW_24, 480, units=0.5),),
    )
    assert _finish(_schedule(half_time), 1) == dt.datetime(2026, 7, 7, 0, 0)


@pytest.mark.parametrize("task_type", [TaskType.FIXED_DURATION, TaskType.FIXED_WORK])
def test_fixed_duration_and_fixed_work_assignments_span_the_whole_task(task_type: TaskType) -> None:
    """Large Test File2: a fixed-work booking below work / units still spans the task's
    duration (its work is contoured over it) — 240 min of work on a 960-min task runs 16 h."""
    crewed = Task(
        unique_id=1,
        name="contoured",
        duration_minutes=960,
        task_type=task_type,
        resource_assignments=(_assign(CREW_24, 240),),
    )
    assert _finish(_schedule(crewed), 1) == dt.datetime(2026, 7, 7, 0, 0)


def test_duration_overrides_scale_every_leg() -> None:
    """The SRA / DCMA-12 hook: a sampled duration stretches the crew's leg with it."""
    crewed = Task(
        unique_id=1,
        name="sampled",
        duration_minutes=960,
        resource_assignments=(_assign(CREW_24, 960),),
    )
    res = compute_cpm(_schedule(crewed), duration_overrides={1: 1920})
    assert res.timing(1).early_finish_wall == dt.datetime(2026, 7, 7, 16, 0)


def test_execution_calendar_and_injected_finish_follow_the_plan() -> None:
    """DCMA-12 sizes its 100-day probe on the crew's calendar and expects the finish the plan
    reaches with the longer duration."""
    crewed = Task(
        unique_id=1,
        name="probe",
        duration_minutes=960,
        resource_assignments=(_assign(CREW_24, 960),),
    )
    sch = _schedule(crewed)
    assert execution_calendar_of(sch, crewed) == CAL_24
    timing = compute_cpm(sch).timing(1)
    assert injected_finish_wall(sch, crewed, timing, 1440) == dt.datetime(2026, 7, 8, 0, 0)
    plain = Task(unique_id=1, name="control", duration_minutes=960)
    assert execution_calendar_of(_schedule(plain), plain) is None
    assert (
        injected_finish_wall(_schedule(plain), plain, compute_cpm(_schedule(plain)).timing(1), 1440)
        is None
    )


# --- leveling delay and the slack axis -------------------------------------------------------


def test_leveling_delay_is_elapsed_time_after_the_calendar_admits_the_task() -> None:
    """Hard_File UID 178: the predecessor finishes at 17:00, the delay is 72 h; MS Project
    admits the task at 08:00 the next working day and starts it 72 h after THAT (Tuesday
    08:00 + 72 h = Friday 08:00), and its late start reaches back through the delay so the
    predecessor stays critical."""
    a = Task(unique_id=1, name="A", duration_minutes=480)
    b = Task(unique_id=2, name="B", duration_minutes=480, leveling_delay_minutes=4320)
    sch = _schedule(a, b, relationships=(Relationship(predecessor_id=1, successor_id=2),))
    res = compute_cpm(sch)
    assert res.leveling_driven == (2,)
    assert res.timing(2).early_start_wall == dt.datetime(2026, 7, 10, 8, 0)
    assert res.timing(2).early_finish_wall == dt.datetime(2026, 7, 10, 17, 0)
    assert res.timing(1).total_float == 0 and res.timing(2).total_float == 0
    assert res.timing(1).late_finish == res.timing(1).early_finish


def test_slack_is_measured_on_the_task_calendar_not_the_crew_calendar() -> None:
    """Hard_File UID 178: ES Monday 17:00, LS Wednesday 08:00 on a 16-hour crew is 480
    project minutes of start slack (Tuesday) and 960 of finish slack (Tuesday 08:00 → Wednesday
    17:00), never the crew calendar's 1 920 — MS Project stores the smaller, on the task's
    calendar."""
    p = Task(unique_id=1, name="P", duration_minutes=480)
    x = Task(
        unique_id=2, name="X", duration_minutes=480, resource_assignments=(_assign(CREW_16, 480),)
    )
    q = Task(unique_id=3, name="Q", duration_minutes=1440)
    m = Task(unique_id=4, name="M", duration_minutes=0, is_milestone=True)
    sch = _schedule(
        p,
        x,
        q,
        m,
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=4),
            Relationship(predecessor_id=3, successor_id=4),
        ),
    )
    res = compute_cpm(sch)
    tx = res.timing(2)
    assert tx.early_start_wall == dt.datetime(2026, 7, 6, 17, 0)
    assert tx.early_finish_wall == dt.datetime(2026, 7, 7, 8, 0)
    assert tx.late_start_wall == dt.datetime(2026, 7, 8, 8, 0)
    assert tx.late_finish_wall == dt.datetime(2026, 7, 8, 17, 0)
    assert tx.total_float == 480
