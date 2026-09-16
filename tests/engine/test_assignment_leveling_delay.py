"""A BOOKING's own leveling delay is honoured on that leg alone (ADR-0502, R-57).

MS Project can level ONE crew off a task without moving the task or its other crews: the delay
is stored per assignment (MSPDI ``Assignment/LevelingDelay``, tenths of a minute) and is
distinct from the task's own ``LevelingDelay`` that ADR-0474 already honours. The engine read
only the task's, so Hard_File UID 398's Technology Lead — a booking that is BOTH split
(ADR-0491, honoured) and delayed (not) — started with the task instead of 239 minutes after it.

The rule is on the SAME type axis as ADR-0474 / ADR-0501's span rule, and that is the whole
finding: a leg with its OWN span (``FIXED_UNITS``, ratio < 1) is PUSHED by its delay — it starts
late and still owes all of its work; a leg that SPANS THE TASK (ratio 1.0) ABSORBS it — the
delay lies inside the span it shares with the task, so the booking starts late and still ends
with the task. Measured over the goldens' 24 delayed bookings: 6 push (all Hard_File,
``FIXED_UNITS``), 18 absorb (all Large_Test_File, ``FIXED_WORK``), and on 16 of those 18 the
file's own ``Assignment/Finish`` IS its ``Task/Finish``. Adding the delay to an absorbing leg
instead cost Large_Test_File 93 of its 1,666 finishes-within-a-day — that regression was
measured before this rule was written, not after.

The delay runs in WORKING minutes of the leg's own calendar and the calendar then admits the
work again (a delay landing exactly on a segment end moves to the next segment), and the TASK's
start does not move: on all 17 goldens' tasks carrying a delayed booking, ``Task.Start`` is the
earliest booking's start, and every one of them also carries an undelayed booking.

Red first: on the pristine tree ``Assignment`` refuses ``leveling_delay_minutes`` (extra
forbidden) and ``CPMResult`` carries no ``assignment_leveling_driven``.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import _offset_to_wall, compute_cpm
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task, TaskType

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
CREW = Resource(unique_id=1, name="Crew")  # on the project pattern
CREW_24 = Resource(unique_id=2, name="Round-the-clock crew", calendar_uid=10)
MATERIAL = Resource(unique_id=3, name="Cleaning", type=ResourceType.MATERIAL)


def _schedule(*tasks: Task) -> Schedule:
    return Schedule(
        name="assignment leveling delays",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_24),
        resources=(CREW, CREW_24, MATERIAL),
        tasks=tasks,
    )


def _task(uid: int, *assignments: Assignment, duration: int = 960, **kw: object) -> Task:
    return Task(
        unique_id=uid,
        name=f"task {uid}",
        duration_minutes=duration,
        resource_assignments=assignments,
        **kw,  # type: ignore[arg-type]
    )


def _finish(sch: Schedule, uid: int) -> dt.datetime:
    tm = compute_cpm(sch).timing(uid)
    return tm.early_finish_wall or _offset_to_wall(
        sch.project_start, tm.early_finish, sch.calendar, role="finish"
    )


def _start(sch: Schedule, uid: int) -> dt.datetime:
    tm = compute_cpm(sch).timing(uid)
    return tm.early_start_wall or _offset_to_wall(
        sch.project_start, tm.early_start, sch.calendar, role="start"
    )


# --- a leg with its OWN span is PUSHED by its delay ---------------------------------------------


def test_a_delayed_booking_with_its_own_span_finishes_later_by_the_delay() -> None:
    """The same two-crew plan with and without the delay — only the delay differs, so only the
    delay can explain the move. The Standard crew owes 480 minutes: undelayed it runs Monday
    08:00-17:00 and finishes the task; leveled off 120 working minutes it starts Monday 10:00
    and runs into Tuesday 10:00."""
    crew24 = Assignment(resource_id=2, work_minutes=480)  # off-pattern, so a plan exists either way
    base = _schedule(_task(1, crew24, Assignment(resource_id=1, work_minutes=480), duration=960))
    delayed = _schedule(
        _task(
            1,
            crew24,
            Assignment(resource_id=1, work_minutes=480, leveling_delay_minutes=120),
            duration=960,
        )
    )
    assert _finish(base, 1) == dt.datetime(2026, 7, 6, 17, 0)
    assert compute_cpm(base).assignment_leveling_driven == ()
    assert _finish(delayed, 1) == dt.datetime(2026, 7, 7, 10, 0)
    assert compute_cpm(delayed).assignment_leveling_driven == (1,)


def test_the_delay_does_not_move_the_task_start() -> None:
    """MS Project's Task.Start is the EARLIEST booking's start, so an undelayed crew still
    starts the task on Monday morning even while its co-crew waits (measured on all 17 goldens'
    tasks that carry a delayed booking)."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480, leveling_delay_minutes=120),
            Assignment(resource_id=2, work_minutes=480),
            duration=960,
        )
    )
    assert _start(sch, 1) == MON


def test_an_undelayed_booking_is_untouched() -> None:
    """The control: the same plan with no delay stays exactly where it was."""
    sch = _schedule(
        _task(1, Assignment(resource_id=1, work_minutes=480), duration=960),
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 7, 17, 0)
    assert compute_cpm(sch).assignment_leveling_driven == ()


def test_the_delay_is_working_minutes_of_the_legs_own_calendar() -> None:
    """A round-the-clock crew's 120-minute delay is 120 minutes of ITS calendar, not of the
    project's: it starts Monday 10:00, where the same delay on Standard reaches Monday 13:00."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=2, work_minutes=480, leveling_delay_minutes=120),
            duration=960,
        )
    )
    # 24/7: Mon 10:00 + 480 = Mon 18:00
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 18, 0)


def test_the_delay_skips_the_weekend_because_it_is_working_minutes() -> None:
    """Five working days of delay on Standard is a calendar quantity, not elapsed time: it lands
    the crew on the FOLLOWING Monday. Elapsed, the same 2,400 minutes would be Wednesday 00:00."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=2, work_minutes=480),  # off-pattern co-crew: Mon 16:00
            Assignment(resource_id=1, work_minutes=240, leveling_delay_minutes=2400),
            duration=960,
        )
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 13, 12, 0)


# --- a leg that SPANS THE TASK ABSORBS its delay -------------------------------------------------


def test_a_task_spanning_leg_absorbs_its_delay() -> None:
    """A FIXED_WORK booking spans the whole task (ADR-0474 ratio 1.0), so its delay lies INSIDE
    that span: the booking starts late and still ends with the task. Adding the delay here is
    the double-count that cost Large_Test_File 93 finishes-within-a-day."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=2, work_minutes=480, leveling_delay_minutes=120),
            duration=960,
            task_type=TaskType.FIXED_WORK,
        )
    )
    # the 24/7 leg spans the task's 960 minutes from Monday 08:00, delay absorbed
    assert _finish(sch, 1) == dt.datetime(2026, 7, 7, 0, 0)
    assert compute_cpm(sch).assignment_leveling_driven == ()


def test_a_fixed_units_leg_whose_work_outruns_the_duration_also_absorbs() -> None:
    """The axis is the RATIO, not the type name: a FIXED_UNITS booking whose work / units
    reaches the duration is clamped to ratio 1.0 and spans the task, so it absorbs too."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=2, work_minutes=2000, leveling_delay_minutes=120),
            duration=960,
        )
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 7, 0, 0)
    assert compute_cpm(sch).assignment_leveling_driven == ()


# --- the disclosure names only the leg that PLACES the finish -------------------------------------


def test_a_delay_on_an_earlier_finishing_leg_is_not_disclosed() -> None:
    """Hard_File_updated2 UID 398's class: the delayed crew still finishes before its co-crew,
    so the task's finish is not the delay's doing and the disclosure must not claim it is."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=2, work_minutes=240, leveling_delay_minutes=60),
            Assignment(resource_id=1, work_minutes=480),
            duration=960,
        )
    )
    res = compute_cpm(sch)
    # the 24/7 crew waits an hour and works four: Mon 09:00 -> 13:00; the Standard crew runs
    # Mon 08:00 -> 17:00 and is what finishes the task
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 17, 0)
    assert res.assignment_leveling_driven == ()


def test_a_material_bookings_delay_is_never_read() -> None:
    """A MATERIAL / COST leg IS its recorded window (ADR-0487), which already embeds whatever
    delay MS Project applied — reading the delay there would double-count the same wait."""
    sch = _schedule(
        _task(
            1,
            Assignment(
                resource_id=3,
                work_minutes=0,
                start=MON,
                finish=dt.datetime(2026, 7, 8, 17, 0),
                leveling_delay_minutes=480,
            ),
            duration=960,
        )
    )
    res = compute_cpm(sch)
    assert _finish(sch, 1) == dt.datetime(2026, 7, 8, 17, 0)
    assert res.booking_span_driven == (1,) and res.assignment_leveling_driven == ()


# --- two crews differing ONLY in their delay are two legs ----------------------------------------


def test_two_bookings_alike_but_for_the_delay_are_not_deduped() -> None:
    """The plan de-dupes legs by (calendar, span, gaps); the delay joined that identity in
    ADR-0502, or the leveled crew would collapse onto its unleveled twin and vanish."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480),
            Assignment(resource_id=1, work_minutes=480, leveling_delay_minutes=120),
            duration=960,
        )
    )
    # deduped, the leveled twin would vanish and the task would finish Mon 17:00
    assert _finish(sch, 1) == dt.datetime(2026, 7, 7, 10, 0)
    assert compute_cpm(sch).assignment_leveling_driven == (1,)
