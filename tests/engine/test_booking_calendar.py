"""The calendar a booking is scheduled on — one public rule (ADR-0492, R-46).

ADR-0474 gave the plan builder its rule for a leg's calendar: the resource's own calendar when
the file carries one and the task does not ignore resource calendars, the task's calendar when
it has one that is neither the project pattern nor 24x7, else the project calendar. The
planned-value proration (a baseline-cost block the status date falls inside) needs the same
calendar, so the rule is now ``cpm.booking_calendar`` and this module pins it: each branch on a
synthetic schedule, and its equivalence with the plan builder's own legs on every Hard_File
golden — the corpus where crews sit on 16-hour and 24-hour calendars.

Red first: on the pristine tree ``booking_calendar`` does not exist.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

from schedule_forensics.engine.cpm import (
    _plan_shapes,
    _recorded_span,
    booking_calendar,
    working_minutes_between,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 7, 6, 8, 0)
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
SAME_PATTERN = Calendar(uid=2, name="Standard (copy)", day_segments=((480, 720), (780, 1020)))
CAL_16 = Calendar(
    uid=3,
    name="16 hours",
    working_minutes_per_day=960,
    day_segments=((360, 480), (480, 720), (780, 1020), (1020, 1380)),
)
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
NIGHT = Calendar(uid=4, name="Night", day_segments=((1200, 1440),))
CREW = Resource(unique_id=1, name="Crew")  # no calendar of its own
CREW_16 = Resource(unique_id=2, name="Two shifts", calendar_uid=3)
CREW_24 = Resource(unique_id=3, name="Round the clock", calendar_uid=10)
CREW_COPY = Resource(unique_id=4, name="On a copy of the project pattern", calendar_uid=2)
GOLDENS = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"


def _sched(*tasks: Task) -> Schedule:
    return Schedule(
        name="booking calendars",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, SAME_PATTERN, CAL_16, CAL_24, NIGHT),
        resources=(CREW, CREW_16, CREW_24, CREW_COPY),
        tasks=tasks,
    )


def _task(uid: int, crew: int, **kw: object) -> Task:
    return Task(
        unique_id=uid,
        name=f"task {uid}",
        duration_minutes=480,
        resource_assignments=(Assignment(resource_id=crew, work_minutes=480),),
        **kw,  # type: ignore[arg-type]
    )


def _cal(sch: Schedule, uid: int) -> Calendar:
    t = sch.task_by_id(uid)
    return booking_calendar(sch, t, t.resource_assignments[0])


def test_the_resources_own_calendar_unless_the_task_ignores_it() -> None:
    sch = _sched(_task(1, 2), _task(2, 2, ignore_resource_calendar=True))
    assert _cal(sch, 1) is CAL_16
    assert _cal(sch, 2) is STANDARD


def test_a_task_calendar_that_is_neither_the_project_pattern_nor_24x7_meets_the_crews() -> None:
    """RE-PINNED 2026-09-17 (R-58, ADR-0503): the booking runs on the INTERSECTION of the task
    calendar and the crew's — the night calendar (20:00-24:00) over the 16-hour crew
    (06:00-12:00 + 13:00-23:00) is their common 20:00-23:00 — where ADR-0474 approximated it
    by the task calendar alone. A copy of the project pattern is still no task calendar at
    all, and a task that ignores resource calendars still keeps its own."""
    sch = _sched(
        _task(1, 2, calendar_uid=4),  # the night calendar over a 16-hour crew
        _task(2, 2, calendar_uid=2),  # a copy of the project pattern is no task calendar at all
        _task(3, 2, calendar_uid=4, ignore_resource_calendar=True),
    )
    common = _cal(sch, 1)
    assert common is not NIGHT and common is not CAL_16
    assert (
        common.working_pattern_key()
        == Calendar(
            uid=-2,
            name="Night ∩ 16 hours",
            working_minutes_per_day=180,
            day_segments=((1200, 1380),),
        ).working_pattern_key()
    )
    assert common.uid == -2 and common.name == "Night ∩ 16 hours"
    assert _cal(sch, 2) is CAL_16
    assert _cal(sch, 3) is NIGHT


def test_a_24x7_task_calendar_yields_to_the_crew() -> None:
    sch = _sched(_task(1, 2, calendar_uid=10), _task(2, 1, calendar_uid=10))
    assert _cal(sch, 1) is CAL_16
    assert _cal(sch, 2) is STANDARD


def test_no_resource_calendar_is_the_project_calendar() -> None:
    """A crew without a calendar of its own, a crew on a copy of the project pattern, and a
    resource the schedule does not carry all schedule on the project calendar."""
    sch = _sched(_task(1, 1), _task(2, 4), _task(3, 99))
    assert _cal(sch, 1) is STANDARD
    assert _cal(sch, 2) is STANDARD
    assert _cal(sch, 3) is STANDARD


def test_working_minutes_between_is_the_recorded_span() -> None:
    """The public name the planned-value proration measures a block with IS the plan builder's
    recorded-span ruler (segment-aware, elapsed on a 24x7 calendar)."""
    a, b = MON + dt.timedelta(hours=4), MON + dt.timedelta(days=1, hours=6)
    assert working_minutes_between(STANDARD, a, b) == _recorded_span(STANDARD, a, b) == 540
    assert working_minutes_between(CAL_24, a, b) == 26 * 60
    assert working_minutes_between(STANDARD, b, a) == 0


def _kept_bookings(sch: Schedule, t: Task) -> list[tuple[Assignment, Calendar]]:
    """The bookings the plan builder turns into legs, in its order (its skip rules re-stated:
    an unknown resource; a non-work booking with no recorded window or an empty span; a work
    booking with no work or no units)."""
    out: list[tuple[Assignment, Calendar]] = []
    for a in t.resource_assignments:
        res = sch.resources_by_id.get(a.resource_id)
        if res is None:
            continue
        cal = booking_calendar(sch, t, a)
        if res.type is not ResourceType.WORK:
            if a.start is None or a.finish is None or _recorded_span(cal, a.start, a.finish) <= 0:
                continue
        elif a.work_minutes <= 0 or a.units <= 0:
            continue
        out.append((a, cal))
    return out


def test_the_rule_is_the_plan_builders_on_every_hard_file_golden() -> None:
    """For every task the plan builder gives legs, the i-th leg's calendar has the working
    pattern ``booking_calendar`` returns for the i-th kept booking; for a task whose legs it
    dropped (all on the project pattern under no task calendar), every kept booking's calendar
    IS the project pattern. Off-pattern crews must be among the compared legs (the positive
    control — a corpus with none could not refute a rule that always answered 'project')."""
    compared = off_pattern = 0
    for path in sorted(GOLDENS.glob("*.mspdi.xml.gz")):
        sch = parse_mspdi_text(gzip.decompress(path.read_bytes()).decode("utf-8"))
        shapes = _plan_shapes(sch)
        project_key = sch.calendar.working_pattern_key()
        for t in sch.tasks:
            if (
                t.is_summary
                or t.duration_is_elapsed
                or t.ignore_resource_calendar
                or t.duration_minutes <= 0
            ):
                continue
            kept = _kept_bookings(sch, t)
            if not kept:
                continue
            shape = shapes.get(t.unique_id)
            if shape is None or not shape.legs:
                for _a, cal in kept:
                    assert cal.working_pattern_key() == project_key, (path.name, t.unique_id)
                    compared += 1
                continue
            assert len(shape.legs) == len(kept), (path.name, t.unique_id)
            for leg, (_a, cal) in zip(shape.legs, kept, strict=True):
                assert leg.calendar.working_pattern_key() == cal.working_pattern_key(), (
                    path.name,
                    t.unique_id,
                )
                compared += 1
                off_pattern += leg.off_pattern
    assert compared > 100 and off_pattern > 10, (compared, off_pattern)
