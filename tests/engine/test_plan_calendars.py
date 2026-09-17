"""``plan_calendars`` — every calendar the base pass runs anything on (R-59, ADR-0504).

``off_project_calendars`` reads a task's OWN ``calendar_uid`` and never sees the crew calendar a
WORK booking is scheduled on (ADR-0474) or the intersection a task calendar meets a crew calendar
on (ADR-0503), so the ``/analysis`` disclosure built on it named task calendars only under a
multi-calendar result. ``plan_calendars`` reads the engine's OWN execution plans — the calendars
total float is measured on (``axes``), the calendars execution legs run on (``legs``), the tasks
whose duration is elapsed — so a leg the plan builder drops is not listed and a leg it keeps is
listed on exactly the calendar object it runs on. These pins are the listing's, not any timing's:
the function changes no computed number.

Red first (2026-09-17, pristine ADR-0503 tree): ``plan_calendars`` does not exist — this module
cannot import.
"""

from __future__ import annotations

import datetime as dt
import gzip
import re
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

from schedule_forensics.engine.cpm import (
    CalendarUse,
    _plan_shapes,
    off_project_calendars,
    plan_calendars,
)
from schedule_forensics.importers.mspdi import _ELAPSED_DURATION_FORMATS, parse_mspdi_text
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
NS = "{http://schemas.microsoft.com/project}"
MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday

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
#: an early start the 16-hour crew cuts into: 05:00-12:00 + 13:00-17:00
EARLY = Calendar(
    uid=6, name="Early", working_minutes_per_day=660, day_segments=((300, 720), (780, 1020))
)
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)

CREW_16 = Resource(unique_id=2, name="Customer Service Team", calendar_uid=11)
CREW_24 = Resource(unique_id=3, name="Content Developer", calendar_uid=10)
CREW_STD_COPY = Resource(unique_id=7, name="Crew on the project pattern", calendar_uid=16)
CREW_NO_CAL = Resource(unique_id=8, name="Crew the file names no calendar for")
MATERIAL = Resource(unique_id=9, name="Cleaning", type=ResourceType.MATERIAL)

CALENDARS = (STANDARD, STANDARD_COPY, CAL_16, SAT_CAL, EARLY, CAL_24)
RESOURCES = (CREW_16, CREW_24, CREW_STD_COPY, CREW_NO_CAL, MATERIAL)


def _schedule(*tasks: Task) -> Schedule:
    return Schedule(
        name="crews and task calendars",
        project_start=MON,
        calendar=STANDARD,
        calendars=CALENDARS,
        resources=RESOURCES,
        tasks=tasks,
    )


def _assign(resource: Resource, work: int = 480, units: float = 1.0, **kw: object) -> Assignment:
    return Assignment(resource_id=resource.unique_id, work_minutes=work, units=units, **kw)  # type: ignore[arg-type]


def _task(uid: int, *crews: Resource, cal: Calendar | None = None, **kw: object) -> Task:
    return Task(
        unique_id=uid,
        name=f"task {uid}",
        duration_minutes=480,
        calendar_uid=None if cal is None else cal.uid,
        resource_assignments=tuple(_assign(c) for c in crews),
        **kw,  # type: ignore[arg-type]
    )


def _by_uid(uses: tuple[CalendarUse, ...]) -> dict[int, tuple[int, ...]]:
    return {use.calendar.uid: use.task_uids for use in uses}


# --- the hole the row names ----------------------------------------------------------------


def test_a_crew_calendar_the_task_does_not_carry_is_listed_off_project_calendars_misses_it() -> (
    None
):
    """R-59's defect in one schedule: a project-calendar task booked on a 16-hour crew runs its
    leg on the crew's calendar (ADR-0474), which ``off_project_calendars`` cannot see."""
    sch = _schedule(_task(1, CREW_16))
    plans = plan_calendars(sch)
    assert off_project_calendars(sch) == ()  # the task carries no calendar of its own
    assert plans.axes == ()  # its float is measured on the project calendar
    assert _by_uid(plans.legs) == {11: (1,)}
    assert plans.legs[0].calendar is CAL_16  # the registered object, not a copy
    assert not plans.legs[0].derived
    assert plans.elapsed == ()
    assert plans.population == 1
    assert plans.touched == (1,)


def test_a_task_calendar_is_the_axis_and_its_leg_runs_on_what_the_crew_shares() -> None:
    """A 24-hour task calendar under a 16-hour crew (Hard_File UID 14): the float axis is the
    task's own calendar, the leg is the crew's calendar itself (ADR-0503's identity case)."""
    plans = plan_calendars(_schedule(_task(1, CREW_16, cal=CAL_24)))
    assert _by_uid(plans.axes) == {10: (1,)}
    assert plans.axes[0].calendar is CAL_24
    assert _by_uid(plans.legs) == {11: (1,)}
    assert plans.legs[0].calendar is CAL_16


def test_a_derived_intersection_is_named_with_both_names_and_never_as_a_parent() -> None:
    """``Standard+Sat.`` meets the 16-hour crew (Hard_File UID 94): the leg runs on a calendar no
    file carries — uid -2, both names — and the listing must say so rather than name a parent."""
    plans = plan_calendars(_schedule(_task(1, CREW_16, cal=SAT_CAL)))
    assert _by_uid(plans.axes) == {12: (1,)}  # the slack axis stays the TASK calendar (ADR-0474)
    (use,) = plans.legs
    assert use.derived
    assert use.calendar.uid == -2
    assert use.calendar.name == "Standard+Sat. ∩ 16 Hour Work Days"
    assert use.calendar is not SAT_CAL and use.calendar is not CAL_16
    assert use.task_uids == (1,)


def test_two_derived_calendars_are_two_entries_by_object_not_one_by_uid() -> None:
    """Every derived calendar shares uid -2, so a uid-keyed dedup would fold two different
    intersections into one line; the listing dedups by OBJECT and orders derived entries by name
    after the registered ones."""
    plans = plan_calendars(
        _schedule(_task(1, CREW_16, cal=SAT_CAL), _task(2, CREW_16, cal=EARLY), _task(3, CREW_24))
    )
    names = [use.calendar.name for use in plans.legs]
    assert names == [
        "24 Hours",  # registered, uid 10, first
        "Early ∩ 16 Hour Work Days",  # derived, by name
        "Standard+Sat. ∩ 16 Hour Work Days",
    ]
    assert [use.derived for use in plans.legs] == [False, True, True]
    assert [use.task_uids for use in plans.legs] == [(3,), (2,), (1,)]


def test_deduplicated_by_object_and_ordered_registered_by_uid() -> None:
    """Two tasks on one crew share one line; a task booked TWICE on the same crew counts once;
    registered calendars are ordered by uid whatever the task order."""
    twice = _task(4, CREW_16).model_copy(
        update={"resource_assignments": (_assign(CREW_16, 240), _assign(CREW_16, 240, 0.5))}
    )
    plans = plan_calendars(_schedule(_task(9, CREW_16), _task(1, CREW_24), twice))
    assert _by_uid(plans.legs) == {10: (1,), 11: (4, 9)}
    assert [use.calendar.uid for use in plans.legs] == [10, 11]
    assert plans.touched == (1, 4, 9)


def test_a_same_pattern_crew_and_the_project_calendar_are_never_listed() -> None:
    """A crew on a copy of the project pattern runs its leg on the project calendar for the plan
    builder too — nothing to disclose, and the project calendar itself is never a line."""
    plans = plan_calendars(_schedule(_task(1, CREW_STD_COPY), _task(2)))
    assert plans.axes == () and plans.legs == () and plans.elapsed == ()
    assert plans.population == 2
    assert plans.touched == ()


def test_legs_the_plan_builder_drops_are_not_listed() -> None:
    """The listing reads the plans, never the assignments: a milestone's booking, a zero-work
    booking and a booking under ``IgnoreResourceCalendar`` (no task calendar) run no leg."""
    milestone = _task(1, CREW_16).model_copy(update={"duration_minutes": 0})
    zero_work = _task(2, CREW_16).model_copy(
        update={"resource_assignments": (_assign(CREW_16, 0),)}
    )
    ignoring = _task(3, CREW_16, ignore_resource_calendar=True)
    plans = plan_calendars(_schedule(milestone, zero_work, ignoring))
    assert plans.legs == () and plans.axes == ()
    assert plans.population == 3 and plans.touched == ()


def test_a_task_calendar_the_crew_cannot_intersect_is_the_leg_itself() -> None:
    """Under ``IgnoreResourceCalendar``, for a MATERIAL booking (ADR-0487) and for a crew the file
    names no calendar for, the leg is the TASK calendar (ADR-0503's rule) — listed as itself, not
    as a derived calendar and never as the crew's."""
    ignoring = _task(1, CREW_16, cal=SAT_CAL, ignore_resource_calendar=True)
    material = _task(2, cal=SAT_CAL).model_copy(
        update={
            "resource_assignments": (
                _assign(MATERIAL, 60, start=MON, finish=MON + dt.timedelta(hours=9)),
            )
        }
    )
    unknown_crew = _task(3, CREW_NO_CAL, cal=SAT_CAL)
    plans = plan_calendars(_schedule(ignoring, material, unknown_crew))
    assert _by_uid(plans.axes) == {12: (1, 2, 3)}
    assert _by_uid(plans.legs) == {12: (1, 2, 3)}
    assert plans.legs[0].calendar is SAT_CAL and not plans.legs[0].derived


def test_an_elapsed_duration_is_counted_and_its_crew_is_not_listed() -> None:
    """An elapsed task runs round the clock whatever its crew (Hard_File UID 146 on the Content
    Developer): the crew's calendar is honoured nowhere, so it is not a calendar in use."""
    plans = plan_calendars(_schedule(_task(1, CREW_16, duration_is_elapsed=True)))
    assert plans.elapsed == (1,)
    assert plans.legs == () and plans.axes == ()
    assert plans.touched == (1,)


def test_inactive_and_summary_tasks_are_outside_the_population() -> None:
    """The scheduled population is ADR-0128's: an inactive task and a summary rollup are never in
    the network, so their bookings disclose nothing and they are not counted."""
    plans = plan_calendars(
        _schedule(
            _task(1, CREW_16, is_active=False),
            _task(2, CREW_16, is_summary=True),
            _task(3),
        )
    )
    assert plans.legs == () and plans.axes == () and plans.elapsed == ()
    assert plans.population == 1


# --- real-golden anchors, expectations derived from the file's own fields --------------------


def _text(rel: str) -> str:
    path = GOLDEN / rel
    raw = path.read_bytes()
    return (
        gzip.decompress(raw).decode("utf-8-sig")
        if path.suffix == ".gz"
        else raw.decode("utf-8-sig")
    )


@cache
def _hard_file() -> tuple[Schedule, ET.Element]:
    text = _text("fuse_hardfile/Hard_File.mspdi.xml.gz")
    return parse_mspdi_text(text), ET.fromstring(text)


def _minutes(iso: str | None) -> int:
    m = re.fullmatch(r"PT(\d+)H(\d+)M(\d+)S", iso or "PT0H0M0S")
    assert m, iso
    return int(m[1]) * 60 + int(m[2])


def _xml_expectation(root: ET.Element, registered: set[int]) -> dict[str, object]:
    """What Hard_File's OWN fields say, independent of the engine: per REGISTERED crew calendar
    (the importer registers a crew's calendar only when its pattern differs from the project's —
    the premise the caller asserts first), the tasks with a WORK booking on a crew carrying it;
    the tasks carrying their own calendar; the elapsed tasks; the scheduled population."""

    def txt(el: ET.Element, tag: str) -> str | None:
        return el.findtext(NS + tag)

    project_cal = txt(root, "CalendarUID")
    resources = {
        txt(r, "UID"): (txt(r, "Type"), txt(r, "CalendarUID")) for r in root.iter(NS + "Resource")
    }
    bookings: dict[str, list[tuple[str, int, float]]] = {}
    for a in root.iter(NS + "Assignment"):
        bookings.setdefault(txt(a, "TaskUID") or "", []).append(
            (txt(a, "ResourceUID") or "", _minutes(txt(a, "Work")), float(txt(a, "Units") or 0))
        )
    scheduled: list[int] = []
    own: dict[int, list[int]] = {}
    elapsed: list[int] = []
    per_crew_cal: dict[int, list[int]] = {}
    for el in root.iter(NS + "Task"):
        uid = txt(el, "UID")
        if uid is None or txt(el, "Active") != "1" or txt(el, "Summary") == "1":
            continue
        scheduled.append(int(uid))
        task_cal = txt(el, "CalendarUID")
        if int(txt(el, "DurationFormat") or 0) in _ELAPSED_DURATION_FORMATS:
            elapsed.append(int(uid))  # still booked below: the caller subtracts it, by name
        elif task_cal not in (None, "-1", project_cal):
            own.setdefault(int(task_cal), []).append(int(uid))
        if _minutes(txt(el, "Duration")) <= 0 or txt(el, "IgnoreResourceCalendar") == "1":
            continue
        for rid, work, units in bookings.get(uid, []):
            rtype, rcal = resources.get(rid, (None, None))
            if rtype != "1" or work <= 0 or units <= 0 or rcal in (None, "-1", project_cal):
                continue
            if int(rcal) not in registered:  # a crew on the project pattern (calendars 4 / 5 / 7)
                continue
            per_crew_cal.setdefault(int(rcal), []).append(int(uid))
    return {
        "population": len(scheduled),
        "own": {k: tuple(sorted(set(v))) for k, v in own.items()},
        "elapsed": tuple(elapsed),
        "per_crew_cal": {k: tuple(sorted(set(v))) for k, v in per_crew_cal.items()},
    }


def test_hard_file_names_the_three_crew_calendars_off_project_calendars_cannot_see() -> None:
    """The row's witness, expectations read off the XML: Customer Service Team (calendar 3),
    Content Developer (6) and Logistics (8) are honoured on the bookings and named by nothing on
    the page before ADR-0504; UID 94 runs on the derived ``Standard+Sat. ∩ Customer Service
    Team``; UID 146 is elapsed and its crew is not honoured on it."""
    sch, root = _hard_file()
    # the premise the XML derivation rests on: the registry carries the project calendar and
    # the off-pattern calendars only (the three same-pattern crews' calendars 4 / 5 / 7 are not
    # registered, so their bookings run on the project calendar)
    assert [c.uid for c in sch.calendars] == [1, 3, 6, 8, 10, 12]
    xml = _xml_expectation(root, {c.uid for c in sch.calendars})
    plans = plan_calendars(sch)
    assert plans.population == xml["population"] == 110

    per_crew = dict(xml["per_crew_cal"])  # type: ignore[call-overload]
    assert set(per_crew) == {3, 6, 8}
    # UID 94 carries Standard+Sat. (12) and its crew is the 16-hour team: its leg is the DERIVED
    # calendar, not the crew's; UID 146 is elapsed: its crew is honoured on nothing
    assert 94 in per_crew[3] and 146 in per_crew[6] and xml["elapsed"] == (146,)
    expected_legs = {
        3: tuple(u for u in per_crew[3] if u != 94),
        6: tuple(u for u in per_crew[6] if u != 146),
        8: per_crew[8],
    }
    registered = {use.calendar.uid: use.task_uids for use in plans.legs if not use.derived}
    assert registered == expected_legs
    assert [len(v) for v in registered.values()] == [25, 18, 1]
    (derived,) = [use for use in plans.legs if use.derived]
    assert derived.calendar.name == "Standard+Sat. ∩ Customer Service Team"
    assert derived.task_uids == (94,)
    assert [use.calendar.uid for use in plans.legs] == [3, 6, 8, -2]

    assert _by_uid(plans.axes) == xml["own"] == {10: (14,), 12: (94,)}
    assert plans.elapsed == xml["elapsed"] == (146,)

    # the hole, stated: the page's old source names the task calendars and none of the crews
    assert [c.uid for c in off_project_calendars(sch)] == [10, 12]
    assert not {3, 6, 8} & {c.uid for c in off_project_calendars(sch)}


def test_large_test_file_counts_activities_not_legs() -> None:
    """A task with several bookings on one calendar is one activity on that calendar. The
    operator's master IMS assigns 138 activities the ``ZIN Project Calendar``; 73 of them carry
    crew legs that run on ZIN itself (their crews restrict nothing it works, so the intersection
    is ZIN by identity) — 183 legs over the 73 — and the other 65 run a one-leg plan on ZIN. The
    listing must carry the 138 once each, and every crew-leg task among them."""
    sch = parse_mspdi_text(_text("fuse_ltf/Large_Test_File.mspdi.xml.gz"))
    plans = plan_calendars(sch)
    (zin,) = [use for use in plans.legs if use.calendar.name == "ZIN Project Calendar"]
    (zin_axis,) = [use for use in plans.axes if use.calendar is zin.calendar]
    # the shape map covers EVERY task; the listing's population is the CPM's (active,
    # non-summary — ADR-0128): summary UID 5334 carries a ZIN material leg and is never scheduled
    scheduled = {t.unique_id for t in sch.tasks if t.is_active and not t.is_summary}
    crew_legs_by_task = {
        uid: sum(1 for leg in shape.legs if leg.calendar is zin.calendar)
        for uid, shape in _plan_shapes(sch).items()
        if uid in scheduled and shape is not None and not shape.elapsed
    }
    crew_leg_tasks = {uid for uid, n in crew_legs_by_task.items() if n}
    crew_legs = sum(crew_legs_by_task.values())
    on_zin = sorted(
        t.unique_id
        for t in sch.tasks
        if t.is_active and not t.is_summary and t.calendar_uid == zin.calendar.uid
    )
    assert len(zin.task_uids) == len(set(zin.task_uids))  # once each, never once per leg
    assert list(zin.task_uids) == on_zin == list(zin_axis.task_uids)
    assert crew_leg_tasks <= set(zin.task_uids)
    assert len(crew_leg_tasks) < crew_legs  # the dedup has something to dedup
