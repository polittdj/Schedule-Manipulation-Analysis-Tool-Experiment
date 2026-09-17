"""A zero-duration task sits exactly where its driving predecessor finished (ADR-0505, R-64).

MS Project schedules on wall-clock instants. A milestone after a crew-calendar activity that
finishes at 08:00 sits at 08:00 (Hard_File UID 181, stored 2026-08-04 08:00, after UID 178's
16-hour crew); after one that finishes at 23:00 it sits at 23:00 (Hard_File_updated2 UID 387,
stored 2026-08-24 23:00 on the Standard project calendar); and its own crew-calendar successor
starts from that instant. The engine's project axis is integer working minutes of the project
calendar, on which Monday 17:00 and Tuesday 08:00 are the SAME minute. A project-axis milestone
kept only the minute, and a crew successor was started from that minute's end-of-day rendering:
Hard_File UID 189 began Monday 17:00 where MS Project begins it Tuesday 08:00, and the chain
189 → 188 → 187 → 184 → 148 → 384 → 385 → 386 → 387 → 400 → … → 404 sat fifteen hours, then one
working day, early. That chain was registered as R-64 with a WRONG mechanism ("milestone 387
hangs on an external predecessor link, UID -65535"): no external, cross-project or unresolved
link exists in any of the 44 files of the corpus (11,979 links across the 15 goldens, 21,609
across the 29 ``.mpp`` conversions), and -65535 is the ``ResourceUID`` of MS Project's
unassigned-work placeholder on the milestone's own assignment.

Red first: every dated assertion below fails on the pre-ADR-0505 engine by name — the crew
successor starts Monday 17:00, and the milestone carries no instant.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import _offset_to_wall, compute_cpm
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
TUE_0800 = dt.datetime(2026, 7, 7, 8, 0)
TUE_1700 = dt.datetime(2026, 7, 7, 17, 0)
MON_1700 = dt.datetime(2026, 7, 6, 17, 0)
MON_2300 = dt.datetime(2026, 7, 6, 23, 0)
#: the project calendar: MS Project's Standard, 08:00-12:00 + 13:00-17:00
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
#: a two-shift crew calendar: 06:00-12:00 + 13:00-23:00, Monday to Friday (Hard_File's)
CAL_16 = Calendar(
    uid=11,
    name="16 Hour Work Days",
    working_minutes_per_day=960,
    day_segments=((360, 720), (780, 1380)),
)
CREW_16 = Resource(unique_id=2, name="Customer Service Team", calendar_uid=11)


def _crew(uid: int, name: str, work: int) -> Task:
    """A crew activity: ``work`` minutes of one 16-hour crew at 100 % (its leg IS the task)."""
    return Task(
        unique_id=uid,
        name=name,
        duration_minutes=work,
        resource_assignments=(Assignment(resource_id=2, work_minutes=work, units=1.0),),
    )


def _schedule(*tasks: Task, links: tuple[tuple[int, int], ...]) -> Schedule:
    return Schedule(
        name="a milestone between crews",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16),
        resources=(CREW_16,),
        tasks=tasks,
        relationships=tuple(Relationship(predecessor_id=p, successor_id=s) for p, s in links),
    )


#: A (Standard, one day) → B (the crew, 8 h: Monday 17:00-23:00 and Tuesday 06:00-08:00)
#: → M (a milestone) → C (the crew again, 8 h).
_A = Task(unique_id=1, name="A", duration_minutes=480)
_B = _crew(2, "B", 480)
_M = Task(unique_id=3, name="M", duration_minutes=0, is_milestone=True)
_C = _crew(4, "C", 480)


def test_a_milestone_after_a_crew_finish_sits_at_the_crews_instant() -> None:
    """B ends Tuesday 08:00 on its crew calendar (Hard_File UID 178's shape); the milestone
    sits there, as MS Project stores UID 181 — not at Monday 17:00, the same project-axis
    minute's end-of-day rendering. Its float stays the axis's, so its late walls are None."""
    res = compute_cpm(_schedule(_A, _B, _M, links=((1, 2), (2, 3))))
    assert res.timing(2).early_finish_wall == TUE_0800
    tm = res.timing(3)
    assert tm.early_start_wall == TUE_0800 and tm.early_finish_wall == TUE_0800
    assert tm.late_start_wall is None and tm.late_finish_wall is None
    # the integer axis is untouched: the milestone's minute is its driver's
    assert tm.early_start == tm.early_finish == res.timing(2).early_finish


def test_the_crew_successor_of_that_milestone_starts_there_not_the_evening_before() -> None:
    """The row's mechanism: MS Project starts Hard_File UID 189 at 08:00 Tuesday, the pre-
    ADR-0505 engine at Monday 17:00 (six evening hours plus two morning hours earlier — the
    whole 08-04 08:00 → 17:00 shift). C runs 08:00-12:00 and 13:00-17:00 on its crew."""
    res = compute_cpm(_schedule(_A, _B, _M, _C, links=((1, 2), (2, 3), (3, 4))))
    assert res.timing(4).early_start_wall == TUE_0800
    assert res.timing(4).early_finish_wall == TUE_1700


def test_a_milestone_at_a_crew_instant_outside_the_project_day_is_not_snapped() -> None:
    """Six crew hours from Monday 17:00 end at 23:00 — an instant the Standard calendar does
    not work. MS Project leaves the milestone there (Hard_File_updated2 UID 387 is stored at
    2026-08-24 23:00 on the Standard calendar); the crew successor starts at its own next
    working instant, Tuesday 06:00. The pre-ADR-0505 engine started it Monday 17:00."""
    b = _crew(2, "B", 360)
    res = compute_cpm(_schedule(_A, b, _M, _C, links=((1, 2), (2, 3), (3, 4))))
    assert res.timing(2).early_finish_wall == MON_2300
    assert res.timing(3).early_start_wall == MON_2300
    assert res.timing(4).early_start_wall == dt.datetime(2026, 7, 7, 6, 0)
    # the network's finish instant is the crew's, before and after: C is a finish candidate
    assert res.project_finish_wall == res.timing(4).early_finish_wall


def test_the_latest_driving_instant_wins_a_tie_on_the_project_axis() -> None:
    """A finishes Monday 17:00 on the project calendar, B Tuesday 08:00 on its crew — one
    project-axis minute, two instants. MS Project's early start is the max over instants."""
    res = compute_cpm(_schedule(_A, _B, _M, _C, links=((1, 2), (1, 3), (2, 3), (3, 4))))
    assert res.timing(3).early_start_wall == TUE_0800
    assert res.timing(4).early_start_wall == TUE_0800


def test_a_carried_instant_travels_through_a_chain_of_milestones() -> None:
    """Hard_File's 184 → 148 shape: a milestone driven by a carried milestone carries the
    same instant, and the crew successor of the SECOND milestone starts there."""
    m2 = Task(unique_id=5, name="M2", duration_minutes=0, is_milestone=True)
    res = compute_cpm(_schedule(_A, _B, _M, m2, _C, links=((1, 2), (2, 3), (3, 5), (5, 4))))
    assert res.timing(5).early_start_wall == TUE_0800
    assert res.timing(4).early_start_wall == TUE_0800


def test_a_lagged_driver_keeps_the_project_axis_rendering() -> None:
    """A lag is a quantity of the integer axis; the milestone then carries nothing and its
    crew successor starts where the axis renders the lagged minute (the ADR-0474 rule). A
    CONTROL — green on the pre-ADR-0505 engine by construction, like the two below it."""
    sch = Schedule(
        name="lagged",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16),
        resources=(CREW_16,),
        tasks=(_A, _B, _M, _C),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3, lag_minutes=60),
            Relationship(predecessor_id=3, successor_id=4),
        ),
    )
    res = compute_cpm(sch)
    assert res.timing(3).early_start_wall is None
    rendered = _offset_to_wall(MON, res.timing(3).early_finish, STANDARD, role="finish")
    assert res.timing(4).early_start_wall == rendered


def test_a_milestone_among_project_calendar_activities_carries_nothing() -> None:
    """The control for every single-calendar file: with no wall-path driver the milestone
    keeps its integer minute only, and its project-calendar successor is byte-identical."""
    d = Task(unique_id=6, name="D", duration_minutes=480)
    res = compute_cpm(_schedule(_A, _M, d, links=((1, 3), (3, 6))))
    assert res.timing(3).early_start_wall is None and res.timing(3).early_finish_wall is None
    assert res.timing(6).early_start_wall is None
    assert res.timing(6).early_start == res.timing(3).early_finish == 480
    assert res.project_finish_wall is None


def test_a_project_calendar_successor_of_a_carried_milestone_is_untouched() -> None:
    """A project-calendar activity after the milestone reads the integer minute as before:
    it snaps to its own next working instant, Tuesday 08:00, from either rendering."""
    d = Task(unique_id=6, name="D", duration_minutes=480)
    res = compute_cpm(_schedule(_A, _B, _M, d, links=((1, 2), (2, 3), (3, 6))))
    assert res.timing(6).early_start_wall is None
    assert res.timing(6).early_start == res.timing(3).early_finish
    assert _offset_to_wall(MON, res.timing(6).early_start, STANDARD, role="start") == TUE_0800


def test_a_start_to_start_successor_reads_the_carried_instant() -> None:
    """SS from a milestone carried at Monday 23:00: the crew successor starts at its next
    working instant, Tuesday 06:00. The pre-ADR-0505 engine read the milestone's START-role
    rendering, Tuesday 08:00 (a link from a milestone at Tuesday 08:00 is a control: both
    renderings agree there)."""
    b = _crew(2, "B", 360)
    sch = Schedule(
        name="ss",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16),
        resources=(CREW_16,),
        tasks=(_A, b, _M, _C),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
            Relationship(predecessor_id=3, successor_id=4, type=RelationshipType.SS),
        ),
    )
    assert compute_cpm(sch).timing(4).early_start_wall == dt.datetime(2026, 7, 7, 6, 0)


def test_the_predecessor_on_its_own_calendar_has_no_free_float_into_its_milestone() -> None:
    """A task on its OWN 16-hour calendar (its slack axis, ADR-0474) ends Monday 23:00 and
    the milestone sits there: zero free float — not the two axis hours (Tuesday 06:00-08:00)
    to the minute's start-role rendering, which the pre-ADR-0505 engine measured. A CREW
    task is a control here: its slack axis is the project calendar, on which the two
    instants are the same minute either way."""
    own = Task(unique_id=2, name="B", duration_minutes=360, calendar_uid=11)
    res = compute_cpm(_schedule(_A, own, _M, links=((1, 2), (2, 3))))
    assert res.timing(2).early_finish_wall == MON_2300
    assert res.timing(3).early_start_wall == MON_2300
    assert res.timing(2).free_float == 0


# --- the other drivers a milestone can tie with, and the two conditions that gate the carry ---

MON_1600 = dt.datetime(2026, 7, 6, 16, 0)


def _schedule_rel(*tasks: Task, rels: tuple[Relationship, ...]) -> Schedule:
    return Schedule(
        name="a milestone between crews",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16),
        resources=(CREW_16,),
        tasks=tasks,
        relationships=rels,
    )


def test_a_start_no_earlier_than_date_that_ties_the_crew_instant_wins() -> None:
    """The crew finishes Monday 23:00, the milestone may not start before Tuesday 08:00 —
    one project-axis minute, and MS Project sits the milestone at the constraint. Its crew
    successor starts Tuesday 08:00, not at the crew's next instant (06:00), and the network's
    finish instant is the milestone's, not the crew's."""
    from schedule_forensics.model.task import ConstraintType

    b = _crew(2, "B", 360)
    m = _M.model_copy(update={"constraint_type": ConstraintType.SNET, "constraint_date": TUE_0800})
    res = compute_cpm(_schedule(_A, b, m, links=((1, 2), (2, 3))))
    assert res.timing(2).early_finish_wall == MON_2300
    assert res.timing(3).early_start_wall == TUE_0800
    assert res.project_finish_wall == TUE_0800
    res = compute_cpm(_schedule(_A, b, m, _C, links=((1, 2), (2, 3), (3, 4))))
    assert res.timing(4).early_start_wall == TUE_0800


def test_a_manual_milestones_stored_start_that_ties_the_crew_instant_wins() -> None:
    """A manually scheduled milestone PINS at its stored start (ADR-0034); when that start is
    the same project-axis minute as the crew's Monday 23:00 finish, the stored instant is
    the milestone's, and its crew successor starts there."""
    b = _crew(2, "B", 360)
    m = _M.model_copy(update={"is_manual": True, "start": TUE_0800, "finish": TUE_0800})
    res = compute_cpm(_schedule(_A, b, m, _C, links=((1, 2), (2, 3), (3, 4))))
    assert res.timing(3).early_start_wall == TUE_0800
    assert res.timing(4).early_start_wall == TUE_0800


def test_a_completed_milestones_recorded_instant_that_ties_the_crew_instant_wins() -> None:
    """A completed milestone sits at its recorded instant (ADR-0476); recorded at Tuesday
    08:00 after a crew finish at Monday 23:00 — one axis minute — the record is the instant."""
    b = _crew(2, "B", 360)
    m = _M.model_copy(
        update={"actual_start": TUE_0800, "actual_finish": TUE_0800, "percent_complete": 100.0}
    )
    res = compute_cpm(_schedule(_A, b, m, _C, links=((1, 2), (2, 3), (3, 4))))
    assert res.timing(3).early_start_wall == TUE_0800
    assert res.timing(4).early_start_wall == TUE_0800


def test_a_completed_milestone_recorded_with_a_span_carries_nothing() -> None:
    """A zero-duration task recorded as finishing after it started has a window, not an
    instant: the carry needs ``finish == start`` on the axis and stands down. A CONTROL on
    the pre-ADR-0505 engine (nothing is carried there); it exists for the mutant that drops
    the condition."""
    m = _M.model_copy(
        update={
            "actual_start": TUE_0800,
            "actual_finish": dt.datetime(2026, 7, 7, 12, 0),
            "percent_complete": 100.0,
        }
    )
    res = compute_cpm(_schedule(_A, _B, m, links=((1, 2), (2, 3))))
    assert res.timing(3).early_start_wall is None and res.timing(3).early_finish_wall is None


def test_a_working_activity_recorded_with_no_span_carries_nothing() -> None:
    """The carry is a rule about ZERO-duration tasks. A one-day activity whose record has it
    finishing at its start (data noise: ADR-0476 pins the window as recorded) is not a
    milestone, and carrying its driver's instant as its FINISH would be a false date. A
    CONTROL on the pre-ADR-0505 engine; it exists for the mutant that drops the condition."""
    d = Task(
        unique_id=6,
        name="D",
        duration_minutes=480,
        actual_start=TUE_0800,
        actual_finish=TUE_0800,
        percent_complete=100.0,
    )
    res = compute_cpm(_schedule(_A, _B, d, links=((1, 2), (2, 6))))
    assert res.timing(6).early_start_wall is None and res.timing(6).early_finish_wall is None


def test_a_start_to_start_driver_hands_the_milestone_its_start_instant() -> None:
    """SS INTO the milestone from the crew activity that runs Monday 17:00 → Tuesday 08:00:
    the milestone carries the crew's START, Monday 17:00 — not its finish."""
    res = compute_cpm(
        _schedule_rel(
            _A,
            _B,
            _M,
            rels=(
                Relationship(predecessor_id=1, successor_id=2),
                Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.SS),
            ),
        )
    )
    assert res.timing(2).early_start_wall == MON_1700
    assert res.timing(3).early_start_wall == MON_1700


def test_a_finish_to_finish_link_into_the_milestone_measures_no_free_float() -> None:
    """FF from a task on its own 16-hour calendar (its slack axis) ending Monday 23:00 into
    the milestone carried there: zero free float on that axis, not the two hours to the
    minute's start-role rendering."""
    own = Task(unique_id=2, name="B", duration_minutes=360, calendar_uid=11)
    res = compute_cpm(
        _schedule_rel(
            _A,
            own,
            _M,
            rels=(
                Relationship(predecessor_id=1, successor_id=2),
                Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FF),
            ),
        )
    )
    assert res.timing(2).early_finish_wall == MON_2300
    assert res.timing(3).early_finish_wall == MON_2300
    assert res.timing(2).free_float == 0
