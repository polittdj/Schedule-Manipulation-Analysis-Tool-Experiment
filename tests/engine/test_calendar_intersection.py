"""A task calendar meeting a crew calendar is their INTERSECTION (ADR-0503, R-58).

MS Project schedules a WORK booking during the times that are working on BOTH the task's
calendar and the resource's, unless the task ignores resource calendars. ADR-0474 approximated
that: a 24-hour task calendar yielded the crew calendar exactly, any other task calendar won
outright. Hard_File UID 94 — an 8-hour task on ``Standard+Sat.`` (07:00-12:00, 12:30-19:00,
19:30-23:30, Monday to Saturday) with the 16-hour Customer Service Team (06:00-12:00 +
13:00-23:00, Monday to Friday) — showed the cost: the task calendar alone resumed at 12:30 and
finished 16:30 where MS Project resumes at the crew's 13:00 and finishes 17:00, and on the
``updated`` snapshot it put the late finish on a Saturday the crew never works.

Every rule below is pinned on a synthetic schedule so a regression names the rule, not the
file; the real witness is pinned in ``tests/parity/test_r58_calendar_intersection_oracle.py``.

Red first (2026-09-17, pristine ADR-0502 tree): ``_calendar_intersection`` does not exist, and
every dated assertion here that depends on the crew's blocks, weekdays, holidays or extras
fails by name against the task-calendar-alone reading.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import (
    _calendar_intersection,
    _offset_to_wall,
    _plan_shapes,
    booking_calendar,
    compute_cpm,
    execution_calendar_of,
)
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
FRI = dt.datetime(2026, 7, 10, 8, 0)
SAT = dt.date(2026, 7, 11)
TUE = dt.date(2026, 7, 7)

#: the project calendar: MS Project's Standard, 08:00-12:00 + 13:00-17:00
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
#: a copy of the project pattern — the usual derived "Resource X" calendar
STANDARD_COPY = Calendar(uid=16, name="Derived Standard", day_segments=((480, 720), (780, 1020)))
#: Hard_File's 16-hour crew: 06:00-12:00 + 13:00-23:00, Monday to Friday
CAL_16 = Calendar(
    uid=11,
    name="16 Hour Work Days",
    working_minutes_per_day=960,
    day_segments=((360, 720), (780, 1380)),
)
#: Hard_File's ``Standard+Sat.``: 07:00-12:00, 12:30-19:00, 19:30-23:30, Monday to Saturday
SAT_CAL = Calendar(
    uid=12,
    name="Standard+Sat.",
    working_minutes_per_day=930,
    work_weekdays=(0, 1, 2, 3, 4, 5),
    day_segments=((420, 720), (750, 1140), (1170, 1410)),
)
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
#: a night shift, 20:00-24:00, Monday to Friday
NIGHT = Calendar(uid=4, name="Night", working_minutes_per_day=240, day_segments=((1200, 1440),))
#: core hours inside the Standard day: 09:00-11:00 + 14:00-16:00
INSIDE = Calendar(
    uid=5, name="Core hours", working_minutes_per_day=240, day_segments=((540, 660), (840, 960))
)
#: the 16-hour crew with a Tuesday off
CAL_16_HOL = CAL_16.model_copy(update={"uid": 13, "name": "16 h, Tuesday off", "holidays": (TUE,)})
#: ``Standard+Sat.`` with the same Tuesday off
SAT_CAL_HOL = SAT_CAL.model_copy(
    update={"uid": 17, "name": "Sat., Tuesday off", "holidays": (TUE,)}
)
#: the Standard pattern plus one worked Saturday
STD_SAT_EXTRA = Calendar(
    uid=14,
    name="Standard + a Saturday",
    day_segments=((480, 720), (780, 1020)),
    working_days=(SAT,),
)
#: the 16-hour crew that also works that Saturday
CAL_16_SAT = CAL_16.model_copy(
    update={"uid": 15, "name": "16 h + a Saturday", "working_days": (SAT,)}
)

CREW_16 = Resource(unique_id=2, name="Customer Service Team", calendar_uid=11)
CREW_24 = Resource(unique_id=3, name="Content Developer", calendar_uid=10)
CREW_16_HOL = Resource(unique_id=5, name="Crew with Tuesday off", calendar_uid=13)
CREW_16_SAT = Resource(unique_id=6, name="Crew working the Saturday", calendar_uid=15)
CREW_STD_COPY = Resource(unique_id=7, name="Crew on the project pattern", calendar_uid=16)
CREW_NO_CAL = Resource(unique_id=8, name="Crew the file names no calendar for")
MATERIAL = Resource(unique_id=9, name="Cleaning", type=ResourceType.MATERIAL)

CALENDARS = (
    STANDARD,
    STANDARD_COPY,
    CAL_16,
    SAT_CAL,
    CAL_24,
    NIGHT,
    INSIDE,
    CAL_16_HOL,
    SAT_CAL_HOL,
    STD_SAT_EXTRA,
    CAL_16_SAT,
)
RESOURCES = (CREW_16, CREW_24, CREW_16_HOL, CREW_16_SAT, CREW_STD_COPY, CREW_NO_CAL, MATERIAL)


def _schedule(*tasks: Task, relationships: tuple[Relationship, ...] = ()) -> Schedule:
    return Schedule(
        name="task and crew calendars",
        project_start=MON,
        calendar=STANDARD,
        calendars=CALENDARS,
        resources=RESOURCES,
        tasks=tasks,
        relationships=relationships,
    )


def _assign(resource: Resource, work: int, units: float = 1.0) -> Assignment:
    return Assignment(resource_id=resource.unique_id, work_minutes=work, units=units)


def _task(uid: int, cal: Calendar, crew: Resource, work: int = 480, **kw: object) -> Task:
    return Task(
        unique_id=uid,
        name=f"task {uid}",
        duration_minutes=work,
        calendar_uid=cal.uid,
        resource_assignments=(_assign(crew, work),),
        **kw,  # type: ignore[arg-type]
    )


def _finish(sch: Schedule, uid: int) -> dt.datetime:
    tm = compute_cpm(sch).timing(uid)
    return tm.early_finish_wall or _offset_to_wall(
        sch.project_start, tm.early_finish, sch.calendar, role="finish"
    )


def _leg_cal(sch: Schedule, uid: int) -> Calendar:
    cal = execution_calendar_of(sch, sch.task_by_id(uid))
    assert cal is not None
    return cal


# --- the four intersections ----------------------------------------------------------------


def test_the_common_afternoon_begins_at_the_crews_13_00_hard_file_uid_94s_shape() -> None:
    """Eight hours from Monday 08:00 on ``Standard+Sat.`` alone: 08:00-12:00 and 12:30-16:30.
    On its intersection with the 16-hour crew: 08:00-12:00 and 13:00-17:00 — MS Project's
    17:00, the instant Hard_File stores for UID 94."""
    sch = _schedule(_task(1, SAT_CAL, CREW_16))
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 17, 0)
    common = _leg_cal(sch, 1)
    assert common.uid == -2 and common.name == "Standard+Sat. ∩ 16 Hour Work Days"
    assert common.work_weekdays == (0, 1, 2, 3, 4)
    assert common.day_segments == ((420, 720), (780, 1140), (1170, 1380))
    assert common.working_minutes_per_day == 870


def test_a_weekday_the_crew_does_not_work_is_not_worked() -> None:
    """Two project days of work from Friday 08:00: the task calendar alone works the Saturday
    (finish Saturday 08:30); the crew never does, so the work resumes Monday 07:00 and finishes
    at 09:30 — 810 common minutes on the Friday, 150 on the Monday."""
    sch = _schedule(
        _task(1, SAT_CAL, CREW_16, 960, constraint_type=ConstraintType.SNET, constraint_date=FRI)
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 13, 9, 30)


def test_a_holiday_of_either_calendar_is_a_holiday_of_the_intersection() -> None:
    """Two days of work from Monday 08:00 with Tuesday off on ONE side: the Monday yields 810
    common minutes, the Tuesday nothing, the Wednesday the last 150 — whichever calendar
    carries the holiday."""
    crew_off = _schedule(_task(1, SAT_CAL, CREW_16_HOL, 960))
    task_off = _schedule(_task(1, SAT_CAL_HOL, CREW_16, 960))
    assert _finish(crew_off, 1) == dt.datetime(2026, 7, 8, 9, 30)
    assert _finish(task_off, 1) == dt.datetime(2026, 7, 8, 9, 30)
    assert _leg_cal(crew_off, 1).holidays == (TUE,)
    assert _leg_cal(task_off, 1).holidays == (TUE,)


def test_an_extra_working_day_survives_only_when_both_calendars_work_it() -> None:
    """The task calendar works one Saturday; two days of work from the Friday finish on that
    Saturday only if the crew works it too — otherwise on the Monday. When the crew does, the
    task calendar restricts nothing the crew works and stands for the intersection ITSELF."""
    crew_off = _schedule(
        _task(
            1,
            STD_SAT_EXTRA,
            CREW_16,
            960,
            constraint_type=ConstraintType.SNET,
            constraint_date=FRI,
        )
    )
    both = _schedule(
        _task(
            1,
            STD_SAT_EXTRA,
            CREW_16_SAT,
            960,
            constraint_type=ConstraintType.SNET,
            constraint_date=FRI,
        )
    )
    assert _finish(crew_off, 1) == dt.datetime(2026, 7, 13, 17, 0)
    assert _leg_cal(crew_off, 1).working_days == ()
    assert _finish(both, 1) == dt.datetime(2026, 7, 11, 17, 0)
    assert _leg_cal(both, 1) is STD_SAT_EXTRA


# --- when one calendar IS the intersection ----------------------------------------------------


def test_a_calendar_the_other_restricts_nothing_of_stands_for_the_intersection_by_identity() -> (
    None
):
    """A 24-hour task calendar yields the crew's calendar OBJECT (ADR-0474's exact case, and
    Hard_File UID 14); a task calendar inside a 24-hour crew keeps its own object; core hours
    inside the project pattern keep theirs; and a Monday-to-Saturday task calendar over a crew
    on the project's Monday-to-Friday pattern yields the PROJECT calendar object — the crew's
    pattern lies inside the task's, so the crew IS the intersection. Identity matters: the
    rulers, the same-pattern test and the plan's dedup key all work by object, and a disclosure
    names the object. The last case had no pin on the first pass and its shortcut survived the
    battery (M06b, 2026-09-17) — this is the pin that killed it."""
    sch = _schedule(
        _task(1, CAL_24, CREW_16),
        _task(2, SAT_CAL, CREW_24),
        _task(3, INSIDE, CREW_STD_COPY),
        _task(4, SAT_CAL, CREW_STD_COPY),
    )
    assert _leg_cal(sch, 1) is CAL_16
    assert _leg_cal(sch, 2) is SAT_CAL
    assert _leg_cal(sch, 3) is INSIDE
    assert _leg_cal(sch, 4) is STANDARD
    assert _finish(sch, 4) == dt.datetime(2026, 7, 6, 17, 0)
    tod0 = MON.hour * 60 + MON.minute
    assert _calendar_intersection(CAL_24, CAL_16, tod0) is CAL_16
    assert _calendar_intersection(SAT_CAL, CAL_24, tod0) is SAT_CAL
    assert _calendar_intersection(SAT_CAL, SAT_CAL, tod0) is SAT_CAL


def test_calendars_with_no_common_working_time_fall_back_to_the_task_calendar() -> None:
    """A night shift under a day crew shares no working minute. MS Project refuses to schedule
    such a booking; the engine keeps ADR-0474's reading — the task calendar — rather than
    invent a calendar. UNVERIFIED against the reference tool: no witness in the corpus."""
    sch = _schedule(_task(1, NIGHT, CREW_STD_COPY))
    assert _leg_cal(sch, 1) is NIGHT
    assert _finish(sch, 1) == dt.datetime(2026, 7, 8, 0, 0)  # two nights of 240 minutes


# --- what is NOT intersected -----------------------------------------------------------------


def test_a_material_booking_and_a_crew_without_a_calendar_keep_the_task_calendar() -> None:
    """A MATERIAL resource has no calendar to intersect with (its leg is its recorded window,
    ADR-0487, measured on the task calendar); a WORK crew the file names no calendar for (an
    XER, an older Save) has an UNKNOWN one — nothing to intersect with either, so the task
    calendar governs, as ADR-0474 had it: 16:30, not 17:00."""
    material = Task(
        unique_id=1,
        name="material",
        duration_minutes=480,
        calendar_uid=SAT_CAL.uid,
        resource_assignments=(
            Assignment(
                resource_id=MATERIAL.unique_id,
                units=1.0,
                start=MON,
                finish=dt.datetime(2026, 7, 7, 17, 0),
            ),
        ),
    )
    unknown = _task(2, SAT_CAL, CREW_NO_CAL)
    sch = _schedule(material, unknown)
    assert booking_calendar(sch, material, material.resource_assignments[0]) is SAT_CAL
    assert _plan_shapes(sch)[1].legs[0].calendar is SAT_CAL  # type: ignore[union-attr]
    assert _leg_cal(sch, 2) is SAT_CAL
    assert _finish(sch, 2) == dt.datetime(2026, 7, 6, 16, 30)


def test_a_task_that_ignores_resource_calendars_keeps_its_own() -> None:
    sch = _schedule(_task(1, SAT_CAL, CREW_16, ignore_resource_calendar=True))
    assert _leg_cal(sch, 1) is SAT_CAL
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 16, 30)


# --- one object per pair, never in the registry -----------------------------------------------


def test_the_intersection_is_one_object_per_calendar_pair_and_never_enters_the_registry() -> None:
    """The plan builder and ``booking_calendar`` (the planned-value proration's rule) hand out
    the SAME derived object for the same pair, the registry the pages list is untouched, and
    a second task on the same pair shares it."""
    t1, t2 = _task(1, SAT_CAL, CREW_16), _task(2, SAT_CAL, CREW_16)
    sch = _schedule(t1, t2)
    first = booking_calendar(sch, t1, t1.resource_assignments[0])
    assert first is booking_calendar(sch, t1, t1.resource_assignments[0])
    assert first is _leg_cal(sch, 1)
    assert first is _leg_cal(sch, 2)
    assert first.uid == -2
    assert all(c is not first for c in sch.calendars)
    assert [c.uid for c in sch.calendars] == [c.uid for c in CALENDARS]


# --- the axis and the backward pass -----------------------------------------------------------


def test_the_slack_axis_stays_the_task_calendar_not_the_intersection() -> None:
    """ADR-0474: MS Project measures a task's slack on the TASK's calendar even when the
    booking runs on another. From Monday 08:00 to a late start of Thursday 15:30 is 3,210
    minutes of ``Standard+Sat.`` and 3,000 of the intersection; the stored figure is the
    former (Hard_File UID 94: 6,360 and 2,190, both on the task calendar)."""
    sch = _schedule(
        _task(1, SAT_CAL, CREW_16),
        Task(unique_id=2, name="successor", duration_minutes=480),
        Task(unique_id=3, name="the long pole", duration_minutes=2400),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    tm = compute_cpm(sch).timing(1)
    assert tm.late_start_wall == dt.datetime(2026, 7, 9, 15, 30)
    assert tm.late_finish_wall == dt.datetime(2026, 7, 10, 8, 0)
    assert tm.total_float == 3210


def test_the_late_finish_snaps_back_on_the_intersection_not_the_task_calendar() -> None:
    """Hard_File_updated UID 94's shape: the successor's late start less its elapsed leveling
    delay lands on the weekend; the task calendar alone would write the late finish as
    Saturday 23:30, the crew never works Saturdays, and MS Project stores Friday 23:00."""
    sch = _schedule(
        _task(1, SAT_CAL, CREW_16),
        Task(
            unique_id=2, name="leveled successor", duration_minutes=480, leveling_delay_minutes=1440
        ),
        Task(unique_id=3, name="the long pole", duration_minutes=2880),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    res = compute_cpm(sch)
    assert res.timing(2).late_start_wall == dt.datetime(2026, 7, 13, 8, 0)
    assert res.timing(1).late_finish_wall == dt.datetime(2026, 7, 10, 23, 0)
