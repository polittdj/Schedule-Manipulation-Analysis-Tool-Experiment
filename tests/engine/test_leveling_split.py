"""A leveling SPLIT is honoured inside the task the way the leveling delay is (ADR-0491, R-60).

MS Project's resource leveling can split a booking into pieces of work with zero-work gaps
between them. The split lives only in the file's timephased data: Hard_File_updated3's UID 403
(the save Acumen Fuse analysed, Revision 2) books 32 h as 14 h, then eight working days of
nothing, then 12 h, then 3.2 h of nothing, then 6 h — and MS Project finishes it 2026-11-05
09:12, twelve working days after the contiguous engine's 10-23 15:00. The vendored converter now
writes the MSPDI ``TimephasedData`` (``MSPDIWriter.setWriteTimephasedData``), the importer reads
each WORK booking's zero-work blocks as the boundaries of its ``work_pieces``, and the engine
carries every gap as WORKING minutes of the leg's calendar between the pieces — forward, on the
backward pass (MS Project's stored LateStart / TotalSlack for 403 retreat through the gaps in
working minutes), and scaled with the duration like every other leg quantity (the pieces
scale, the gaps do not: a gap is a calendar quantity, like the delay).

Red first: on the pristine tree ``Assignment`` refuses ``work_pieces`` (extra forbidden),
``WorkPiece`` does not exist and ``CPMResult`` carries no ``split_driven``.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import _offset_to_wall, compute_cpm
from schedule_forensics.model.assignment import Assignment, WorkPiece
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task, TaskType

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
MON_NOON = dt.datetime(2026, 7, 6, 12, 0)
WED_1300 = dt.datetime(2026, 7, 8, 13, 0)
WED_1700 = dt.datetime(2026, 7, 8, 17, 0)
THU_NOON = dt.datetime(2026, 7, 9, 12, 0)
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
CAL_24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=tuple(range(7))
)
CREW = Resource(unique_id=1, name="Crew")  # on the project pattern
CREW_24 = Resource(unique_id=2, name="Round-the-clock crew", calendar_uid=10)
MATERIAL = Resource(unique_id=3, name="Cleaning", type=ResourceType.MATERIAL)

#: one day of work booked as two half-days with two working days (960 min) between them
SPLIT = (
    WorkPiece(start=MON, finish=MON_NOON, work_minutes=240),
    WorkPiece(start=WED_1300, finish=WED_1700, work_minutes=240),
)


def _schedule(*tasks: Task, relationships: tuple[Relationship, ...] = ()) -> Schedule:
    return Schedule(
        name="leveling splits",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_24),
        resources=(CREW, CREW_24, MATERIAL),
        tasks=tasks,
        relationships=relationships,
    )


def _task(uid: int, *assignments: Assignment, duration: int = 480, **kw: object) -> Task:
    return Task(
        unique_id=uid,
        name=f"task {uid}",
        duration_minutes=duration,
        resource_assignments=assignments,
        **kw,  # type: ignore[arg-type]
    )


def _finish(sch: Schedule, uid: int, **kw: object) -> dt.datetime:
    tm = compute_cpm(sch, **kw).timing(uid)  # type: ignore[arg-type]
    return tm.early_finish_wall or _offset_to_wall(
        sch.project_start, tm.early_finish, sch.calendar, role="finish"
    )


# --- the gap is honoured inside the task ------------------------------------------------------


def test_a_split_bookings_gap_is_honoured_inside_the_task() -> None:
    """Half a day, two working days of nothing, half a day: the task finishes Wednesday 17:00
    (the contiguous engine finished it Monday 17:00), and says why."""
    sch = _schedule(_task(1, Assignment(resource_id=1, work_minutes=480, work_pieces=SPLIT)))
    assert _finish(sch, 1) == WED_1700
    assert compute_cpm(sch).split_driven == (1,)


def test_a_single_piece_changes_nothing() -> None:
    sch = _schedule(_task(1, Assignment(resource_id=1, work_minutes=480)))
    assert _finish(sch, 1) == dt.datetime(2026, 7, 6, 17, 0)
    assert compute_cpm(sch).split_driven == ()


def test_a_split_on_the_project_pattern_forms_a_plan() -> None:
    """Every leg on the project pattern, no task calendar, no delay — and still a plan: the fast
    path cannot carry a gap (the same rule that admits a recorded span, ADR-0487)."""
    sch = _schedule(_task(1, Assignment(resource_id=1, work_minutes=480, work_pieces=SPLIT)))
    assert compute_cpm(sch).timing(1).early_finish_wall == WED_1700


def test_the_gap_is_working_minutes_of_the_leg_calendar_not_elapsed_time() -> None:
    """The pieces were recorded Friday 08:00-12:00 and Tuesday 13:00-17:00: 960 working
    minutes apart, 4 days 1 hour of elapsed time. Scheduled from Monday instead (the project
    start), the task finishes Wednesday 17:00 — the gap travels with the work on the calendar,
    exactly as MS Project's stored LateStart retreats through it (the 403 shape below). An
    elapsed reading would finish Friday 17:00."""
    pieces = (
        WorkPiece(
            start=dt.datetime(2026, 7, 10, 8, 0),
            finish=dt.datetime(2026, 7, 10, 12, 0),
            work_minutes=240,
        ),
        WorkPiece(
            start=dt.datetime(2026, 7, 14, 13, 0),
            finish=dt.datetime(2026, 7, 14, 17, 0),
            work_minutes=240,
        ),
    )
    sch = _schedule(_task(1, Assignment(resource_id=1, work_minutes=480, work_pieces=pieces)))
    assert _finish(sch, 1) == dt.datetime(2026, 7, 8, 17, 0)


def test_the_backward_pass_retreats_through_the_gap() -> None:
    """A one-day successor makes the split task critical: its late start retreats from
    Wednesday 17:00 through the second piece, the 960-minute gap and the first piece to Monday
    08:00 — zero float. A retreat that skipped the gap would read Tuesday 17:00 and 960 minutes
    of float on a driving activity."""
    sch = _schedule(
        _task(1, Assignment(resource_id=1, work_minutes=480, work_pieces=SPLIT)),
        _task(2, Assignment(resource_id=1, work_minutes=480)),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    res = compute_cpm(sch)
    assert _finish(sch, 2) == dt.datetime(2026, 7, 9, 17, 0)
    assert res.timing(1).late_start_wall == MON
    assert res.timing(1).total_float == 0 and res.timing(1).is_critical


def test_the_pieces_scale_with_the_duration_and_the_gap_does_not() -> None:
    """The SRA hands the solver a duration per iteration. Doubled, each piece doubles (the gap
    sits after a full day instead of a half) while the gap keeps its 960 calendar minutes:
    Monday 17:00 + two days + one day = Thursday 17:00."""
    sch = _schedule(_task(1, Assignment(resource_id=1, work_minutes=480, work_pieces=SPLIT)))
    assert _finish(sch, 1, duration_overrides={1: 960}) == dt.datetime(2026, 7, 9, 17, 0)


def test_a_round_the_clock_gap_is_elapsed_time() -> None:
    """On a 24/7 crew a 26-hour gap is 26 hours: 480 min from Monday 08:00 → 16:00, the gap
    → Tuesday 18:00, the last 240 min → Tuesday 22:00."""
    pieces = (
        WorkPiece(start=MON, finish=dt.datetime(2026, 7, 6, 16, 0), work_minutes=480),
        WorkPiece(
            start=dt.datetime(2026, 7, 7, 18, 0),
            finish=dt.datetime(2026, 7, 7, 22, 0),
            work_minutes=240,
        ),
    )
    sch = _schedule(
        _task(1, Assignment(resource_id=2, work_minutes=720, work_pieces=pieces), duration=720)
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 7, 22, 0)


def test_a_material_bookings_pieces_are_inert() -> None:
    """A material booking's leg is its recorded window (ADR-0487), gaps included; its pieces
    add nothing and the task is not disclosed as split-driven."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480),
            Assignment(resource_id=3, start=MON, finish=THU_NOON, work_pieces=SPLIT),
        )
    )
    res = compute_cpm(sch)
    assert res.timing(1).early_finish_wall == THU_NOON
    assert res.booking_span_driven == (1,) and res.split_driven == ()


def test_a_gap_another_booking_works_through_is_that_bookings_own_contour() -> None:
    """Crew A is split around two working days; crew B works straight through them on a
    three-day fixed-duration task. MS Project's Duration already spans B's window (Large
    Test File2 UID 5308: one of eight bookings delayed three weeks inside a fixed 228-hour
    duration — honouring it read the task 17 days late), so A's gap is A's own contour, not
    the task's split: the task finishes at the duration, Wednesday 17:00, undisclosed."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480, work_pieces=SPLIT),
            Assignment(resource_id=2, work_minutes=1440, start=MON, finish=WED_1700),
            duration=1440,
            task_type=TaskType.FIXED_DURATION,
        )
    )
    res = compute_cpm(sch)
    assert res.timing(1).early_finish_wall == WED_1700 and res.split_driven == ()


def test_only_the_part_of_a_gap_nobody_works_is_the_tasks_split() -> None:
    """Crew B works Monday 13:00 → Tuesday 12:00, the first 480 of A's 960-minute gap; the
    other 480 is the task's split. A's leg: 240, 480 of nothing, 240 → Tuesday 17:00 (the whole
    gap would read Wednesday 17:00; none of it Monday 17:00)."""
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480, work_pieces=SPLIT),
            Assignment(
                resource_id=2,
                work_minutes=480,
                start=dt.datetime(2026, 7, 6, 13, 0),
                finish=dt.datetime(2026, 7, 7, 12, 0),
            ),
        )
    )
    res = compute_cpm(sch)
    assert res.timing(1).early_finish_wall == dt.datetime(2026, 7, 7, 17, 0)
    assert res.split_driven == (1,)


def test_a_gap_the_calendar_already_explains_is_no_gap() -> None:
    """Two pieces separated only by a lunch hour and a night (a two-day booking the writer
    happened to block per day): zero working minutes between them, no gap, no disclosure."""
    pieces = (
        WorkPiece(start=MON, finish=dt.datetime(2026, 7, 6, 17, 0), work_minutes=480),
        WorkPiece(
            start=dt.datetime(2026, 7, 7, 8, 0),
            finish=dt.datetime(2026, 7, 7, 17, 0),
            work_minutes=480,
        ),
    )
    sch = _schedule(
        _task(1, Assignment(resource_id=1, work_minutes=960, work_pieces=pieces), duration=960)
    )
    res = compute_cpm(sch)
    assert res.timing(1).early_finish == 960 and res.split_driven == ()


def test_the_resume_floor_carries_the_gaps_still_ahead() -> None:
    """Half done (the first piece), stopped Monday noon, resumed Tuesday 08:00 by the planner:
    the remaining 240 minutes run from the Resume with the split still ahead of them — 120
    worked, 840 of nothing (the gap's calendar length, unscaled), 120 more — Thursday 10:00. A
    scaled plan that dropped its gaps would read Tuesday 12:00 and lose to the ordinary leg's
    Wednesday 15:00."""
    pieces = (
        WorkPiece(start=MON, finish=MON_NOON, work_minutes=240),
        WorkPiece(
            start=dt.datetime(2026, 7, 6, 13, 0),
            finish=dt.datetime(2026, 7, 6, 15, 0),
            work_minutes=120,
        ),
        WorkPiece(
            start=dt.datetime(2026, 7, 8, 13, 0),
            finish=dt.datetime(2026, 7, 8, 15, 0),
            work_minutes=120,
        ),
    )
    sch = _schedule(
        _task(
            1,
            Assignment(resource_id=1, work_minutes=480, work_pieces=pieces),
            percent_complete=50,
            actual_start=MON,
            stop=MON_NOON,
            resume=dt.datetime(2026, 7, 7, 8, 0),
            remaining_duration_minutes=240,
        )
    )
    assert _finish(sch, 1) == dt.datetime(2026, 7, 9, 10, 0)


# --- the Hard_File_updated3 UID 403 shape, to the minute --------------------------------------


def test_the_updated3_403_shape_finishes_and_floats_where_ms_project_says() -> None:
    """UID 403 (Revision 2, the save Fuse analysed): 32 h at 100 % on the Standard calendar,
    admitted 2026-10-19 15:00; the file books 14 h → 10-21 12:00, nothing until 11-02 13:00,
    12 h → 11-03 17:00, nothing until 11-04 11:12, 6 h → 11-05 09:12. With the backward pass
    capped at MS Project's stored LateFinish (12-11 17:00) the late start is the stored
    11-25 13:48 and the total slack the stored 12,888 minutes — both retreat through the two
    gaps in working minutes."""
    pieces = (
        WorkPiece(
            start=dt.datetime(2026, 10, 19, 15, 0),
            finish=dt.datetime(2026, 10, 21, 12, 0),
            work_minutes=840,
        ),
        WorkPiece(
            start=dt.datetime(2026, 11, 2, 13, 0),
            finish=dt.datetime(2026, 11, 3, 17, 0),
            work_minutes=720,
        ),
        WorkPiece(
            start=dt.datetime(2026, 11, 4, 11, 12),
            finish=dt.datetime(2026, 11, 5, 9, 12),
            work_minutes=360,
        ),
    )
    sch = Schedule(
        name="403",
        project_start=dt.datetime(2026, 10, 19, 8, 0),
        calendar=STANDARD,
        calendars=(STANDARD,),
        resources=(CREW,),
        tasks=(
            _task(
                403,
                Assignment(resource_id=1, work_minutes=1920, work_pieces=pieces),
                duration=1920,
                constraint_type=ConstraintType.SNET,
                constraint_date=dt.datetime(2026, 10, 19, 15, 0),
            ),
        ),
    )
    # 40 working days from 10-19 08:00 to the stored LateFinish 12-11 17:00
    res = compute_cpm(sch, required_finish_offset=40 * 480)
    tm = res.timing(403)
    assert tm.early_start_wall == dt.datetime(2026, 10, 19, 15, 0)
    assert tm.early_finish_wall == dt.datetime(2026, 11, 5, 9, 12)
    assert tm.late_finish_wall == dt.datetime(2026, 12, 11, 17, 0)
    assert tm.late_start_wall == dt.datetime(2026, 11, 25, 13, 48)
    assert tm.total_float == 12888
    assert res.split_driven == (403,)
