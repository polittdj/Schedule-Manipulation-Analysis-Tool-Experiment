"""A zero-duration task's LATE instant is carried from the need that binds it (R-67, the backward
mirror of ADR-0505's carried early instant).

MS Project keeps a milestone's late start / late finish as ONE wall instant, wherever the tightest
successor need falls: Hard_File UID 147's stored LateStart is SATURDAY 2026-08-01 13:00 — UID
178's late start less its 72 elapsed hours of leveling delay — and Hard_File_updated3_24hr UID
155's is its DEADLINE, 11-05 17:00. The engine's project axis is integer working minutes of the
project calendar, on which a Saturday instant is the Friday-17:00 / Monday-08:00 minute; a
milestone kept only the minute, and a crew-calendar PREDECESSOR reading the minute's start-role
rendering (Monday 08:00) took its late finish two crew hours after the stored Friday 23:00 (UID
157) — and UID 94, one link higher, inherited 150 minutes of slack on its own calendar (6,510
where MS Project stores 6,360). On the 24-hour snapshot the 24-hour crew below the deadline read
11-06 08:00 for 11-05 17:00 and the chain down to milestone 156 inherited fifteen crew hours.

The rule: a fast-path zero-duration task whose binding need is an instant the axis LOST — a
wall-path successor's late start less its elapsed delay, another carried milestone's instant, or
(on a file with wall-path tasks) the raw instant of a binding deadline / date constraint or the
backward target — carries the EARLIEST such instant on ``TaskTiming.late_start_wall`` /
``late_finish_wall`` (its integer offsets untouched), a wall-path predecessor retreats from it,
and a milestone whose EARLY instant is carried measures its own slack between its two instants
on the project calendar (the axis's contiguous projection of a mid-day instant drifts by the
lunch gap: Hard_File UID 404 read 9,420 where MS Project stores 9,480).

Red first: every dated assertion below fails on the pre-R-67 engine by name — the milestone
carries no late instant, the crew predecessor retreats from the rendering, the milestone's slack
is the axis's. The controls are named as such in their docstrings.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday
TUE_0800 = dt.datetime(2026, 7, 7, 8, 0)
TUE_1500 = dt.datetime(2026, 7, 7, 15, 0)
TUE_2100 = dt.datetime(2026, 7, 7, 21, 0)
WED_1600 = dt.datetime(2026, 7, 8, 16, 0)
WED_1700 = dt.datetime(2026, 7, 8, 17, 0)
WED_2100 = dt.datetime(2026, 7, 8, 21, 0)
THU_0800 = dt.datetime(2026, 7, 9, 8, 0)
THU_1200 = dt.datetime(2026, 7, 9, 12, 0)
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


def _crew(uid: int, name: str, work: int, **extra: object) -> Task:
    """A crew activity: ``work`` minutes of one 16-hour crew at 100 % (its leg IS the task)."""
    return Task(
        unique_id=uid,
        name=name,
        duration_minutes=work,
        resource_assignments=(Assignment(resource_id=2, work_minutes=work, units=1.0),),
        **extra,  # type: ignore[arg-type]
    )


def _schedule(*tasks: Task, rels: tuple[Relationship, ...]) -> Schedule:
    return Schedule(
        name="a milestone between crews, backward",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16),
        resources=(CREW_16,),
        tasks=tasks,
        relationships=rels,
    )


def _fs(*links: tuple[int, int]) -> tuple[Relationship, ...]:
    return tuple(Relationship(predecessor_id=p, successor_id=s) for p, s in links)


#: A (Standard, one day) → B (the crew, 8 h: Monday 17:00-23:00 + Tuesday 06:00-08:00) → M (a
#: milestone, carried at Tuesday 08:00) → C (the crew again, 8 h). D (Standard, 2.5 days) runs
#: beside them from A and sets the network finish at Thursday 12:00, so C's late finish is
#: Thursday 12:00 and its late start WEDNESDAY 21:00 — an instant the Standard axis does not have.
_A = Task(unique_id=1, name="A", duration_minutes=480)
_B = _crew(2, "B", 480)
_M = Task(unique_id=3, name="M", duration_minutes=0, is_milestone=True)
_C = _crew(4, "C", 480)
_D = Task(unique_id=5, name="D", duration_minutes=1200)


def test_a_milestone_before_a_crew_successor_carries_the_crews_late_start() -> None:
    """C's late start is Wednesday 21:00 on its crew; M sits there (its early instant is
    Tuesday 08:00, carried by ADR-0505). The pre-R-67 engine left M's late walls None."""
    res = compute_cpm(_schedule(_A, _B, _M, _C, _D, rels=_fs((1, 2), (2, 3), (3, 4), (1, 5))))
    assert res.timing(4).late_start_wall == WED_2100
    tm = res.timing(3)
    assert tm.late_start_wall == WED_2100 and tm.late_finish_wall == WED_2100
    assert tm.early_start_wall == TUE_0800
    # the integer axis is untouched: Wednesday 21:00 projects to the end-of-Wednesday minute
    assert tm.late_finish == tm.late_start == 1440
    # the carry is a rule about ZERO-duration tasks: the Standard activities keep no late wall
    assert res.timing(1).late_finish_wall is None and res.timing(5).late_finish_wall is None


def test_the_crew_predecessor_of_that_milestone_retreats_from_the_instant() -> None:
    """The row's mechanism: B's late finish is Wednesday 21:00 (Hard_File UID 157's Friday
    23:00 shape), not the minute's start-role rendering, Thursday 08:00, two crew hours later.
    Its slack on the project calendar is the smaller of the start and finish slack: 720, not
    960 (UID 157: 2,760 where the pre-R-67 engine read 2,880)."""
    res = compute_cpm(_schedule(_A, _B, _M, _C, _D, rels=_fs((1, 2), (2, 3), (3, 4), (1, 5))))
    tm = res.timing(2)
    assert tm.late_finish_wall == WED_2100
    assert tm.total_float == 720


def test_a_carried_milestone_measures_its_slack_between_its_instants() -> None:
    """B runs 14 crew hours and ends Tuesday 15:00; M carries that instant, and its late
    instant is Wednesday 21:00. Its slack is the working time between the two on the project
    calendar — 600 minutes — not the difference of the axis's contiguous projections, 540 (a
    mid-day instant projects up to the lunch gap late: Hard_File UID 404, 9,420 vs 9,480)."""
    b = _crew(2, "B", 840)
    res = compute_cpm(_schedule(_A, b, _M, _C, _D, rels=_fs((1, 2), (2, 3), (3, 4), (1, 5))))
    tm = res.timing(3)
    assert tm.early_start_wall == TUE_1500 and tm.late_finish_wall == WED_2100
    assert tm.total_float == 600


def test_a_deadline_bound_milestone_carries_the_deadline_to_its_crew_predecessor() -> None:
    """M has no successor; its late finish is its DEADLINE, Wednesday 17:00 — the raw instant,
    which MS Project stores as the milestone's late start (Hard_File_updated3_24hr UID 155).
    B retreats from it: late finish Wednesday 17:00, slack 480 — not from the minute's
    start-role rendering, Thursday 08:00 (the 24-hour crew UID 146 read fifteen hours late)."""
    m = _M.model_copy(update={"deadline": WED_1700})
    res = compute_cpm(_schedule(_A, _B, m, _D, rels=_fs((1, 2), (2, 3), (1, 5))))
    assert res.timing(3).late_finish_wall == WED_1700
    assert res.timing(2).late_finish_wall == WED_1700
    assert res.timing(2).total_float == 480


def test_the_finish_milestone_carries_the_networks_finish_instant() -> None:
    """M is the last task after a crew that ends Tuesday 15:00: its late instant is the
    network's finish instant, its own. The pre-R-67 engine left the late walls None."""
    b = _crew(2, "B", 840)
    res = compute_cpm(_schedule(_A, b, _M, rels=_fs((1, 2), (2, 3))))
    tm = res.timing(3)
    assert tm.late_finish_wall == TUE_1500 and tm.late_start_wall == TUE_1500
    assert res.project_finish_wall == TUE_1500
    assert tm.total_float == 0 and res.timing(2).total_float == 0


def test_a_leveling_delayed_crew_successor_hands_the_milestone_its_need_once() -> None:
    """C carries 24 elapsed hours of leveling delay: its late-start NEED is Tuesday 21:00
    (Wednesday 21:00 less the delay — ADR-0474's candidate), M sits there, and B retreats from
    it (late finish Tuesday 21:00, slack 240). The delay is subtracted once — a second
    subtraction would put M at Monday 21:00 and B's slack below zero."""
    c = _crew(4, "C", 480, leveling_delay_minutes=1440)
    res = compute_cpm(_schedule(_A, _B, _M, c, _D, rels=_fs((1, 2), (2, 3), (3, 4), (1, 5))))
    assert res.timing(4).late_start_wall == WED_2100
    assert res.timing(3).late_finish_wall == TUE_2100
    assert res.timing(2).late_finish_wall == TUE_2100
    assert res.timing(2).total_float == 240


def test_a_carried_late_instant_travels_through_a_chain_of_milestones() -> None:
    """Hard_File's 184 → 148 shape, backward: a milestone whose binding successor is a carried
    milestone carries the same instant, and the crew predecessor of the FIRST retreats from it."""
    m2 = Task(unique_id=6, name="M2", duration_minutes=0, is_milestone=True)
    res = compute_cpm(
        _schedule(_A, _B, _M, m2, _C, _D, rels=_fs((1, 2), (2, 3), (3, 6), (6, 4), (1, 5)))
    )
    assert res.timing(6).late_finish_wall == WED_2100
    assert res.timing(3).late_finish_wall == WED_2100
    assert res.timing(2).late_finish_wall == WED_2100


def test_a_finish_to_finish_predecessor_reads_the_carried_late_instant() -> None:
    """FF from B into M: B's finish need is M's late instant, Wednesday 21:00 — not the
    finish-role rendering of M's late minute (Wednesday 17:00)."""
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FF),
        Relationship(predecessor_id=3, successor_id=4),
        Relationship(predecessor_id=1, successor_id=5),
    )
    res = compute_cpm(_schedule(_A, _B, _M, _C, _D, rels=rels))
    assert res.timing(3).late_finish_wall == WED_2100
    assert res.timing(2).late_finish_wall == WED_2100


def test_the_earliest_binding_instant_wins_a_tie_on_the_project_axis() -> None:
    """Two successors bind M's late finish on the same axis minute: C's Wednesday 21:00 (the
    crew) and E's Thursday 08:00 (a half-day Standard activity whose late start is that
    minute's start-role rendering). MS Project's late finish is the min over instants."""
    e = Task(unique_id=7, name="E", duration_minutes=240)
    res = compute_cpm(
        _schedule(_A, _B, _M, _C, _D, e, rels=_fs((1, 2), (2, 3), (3, 4), (3, 7), (1, 5)))
    )
    assert res.timing(3).late_finish == 1440 == res.timing(7).late_start
    assert res.timing(3).late_finish_wall == WED_2100
    assert res.timing(2).late_finish_wall == WED_2100


def test_a_non_binding_lagged_successor_does_not_block_the_carry() -> None:
    """Only the needs that BIND the milestone's late finish decide its instant. F (a Standard
    two-hour activity linked with a lag) needs M later than C does, so the lag rule — a lagged
    BINDING link leaves the rendering in charge — must not fire on it: M still carries C's
    Wednesday 21:00. The mutant that drops the binding check survived the first battery; this
    pin exists for it."""
    f = Task(unique_id=8, name="F", duration_minutes=120)
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
        Relationship(predecessor_id=3, successor_id=8, lag_minutes=60),
        Relationship(predecessor_id=1, successor_id=5),
    )
    res = compute_cpm(_schedule(_A, _B, _M, _C, _D, f, rels=rels))
    assert res.timing(8).late_start > res.timing(3).late_finish + 60  # F does not bind
    assert res.timing(3).late_finish_wall == WED_2100
    assert res.timing(2).late_finish_wall == WED_2100


# --- controls: green on the pre-R-67 engine by construction; they exist for the mutants ---


def test_a_non_binding_crew_successor_does_not_make_a_rendering_bound_milestone_carry() -> None:
    """E (Standard, a full day, late start Wednesday 13:00) binds M's late finish; C (the crew,
    late start Wednesday 21:00) does not. The binding need is a rendering the axis already has,
    so M carries nothing — C's later instant is not a reason to. A CONTROL; it exists for the
    mutant that drops the binding check."""
    e = Task(unique_id=7, name="E", duration_minutes=480)
    res = compute_cpm(
        _schedule(_A, _B, _M, _C, _D, e, rels=_fs((1, 2), (2, 3), (3, 4), (3, 7), (1, 5)))
    )
    assert res.timing(4).late_start_wall == WED_2100
    assert res.timing(3).late_finish == res.timing(7).late_start == 1200
    assert res.timing(3).late_finish_wall is None


def test_a_lagged_binding_link_keeps_the_project_axis_rendering() -> None:
    """A lag is a quantity of the integer axis: with M → C lagged, M carries nothing and B
    retreats from the rendering of the lagged minute (Wednesday 16:00). A CONTROL."""
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4, lag_minutes=60),
        Relationship(predecessor_id=1, successor_id=5),
    )
    res = compute_cpm(_schedule(_A, _B, _M, _C, _D, rels=rels))
    assert res.timing(3).late_finish_wall is None
    assert res.timing(2).late_finish_wall == WED_1600


def test_a_milestone_bound_by_a_project_calendar_successor_only_carries_nothing() -> None:
    """The binding need is a Standard activity's late start — a rendering the axis already
    has — so nothing is carried and B retreats from it as before (Wednesday 12:00, the crew's
    last morning instant at or before the rendered Wednesday 13:00). A CONTROL."""
    e = Task(unique_id=7, name="E", duration_minutes=480)
    res = compute_cpm(_schedule(_A, _B, _M, _D, e, rels=_fs((1, 2), (2, 3), (3, 7), (1, 5))))
    assert res.timing(3).late_finish_wall is None
    assert res.timing(2).late_finish_wall == dt.datetime(2026, 7, 8, 12, 0)


def test_a_deadline_bound_milestone_on_a_single_calendar_file_carries_nothing() -> None:
    """With no wall-path task in the file, no consumer can read a milestone's instant and the
    fast-path sentinel holds: the late walls stay None and the slack is the axis's. A CONTROL —
    it exists for the mutant that drops the file gate."""
    m = _M.model_copy(update={"deadline": WED_1700})
    sch = Schedule(
        name="single calendar",
        project_start=MON,
        calendar=STANDARD,
        tasks=(_A, m, _D),
        relationships=_fs((1, 3), (1, 5)),
    )
    res = compute_cpm(sch)
    tm = res.timing(3)
    assert tm.late_start_wall is None and tm.late_finish_wall is None
    assert tm.early_start_wall is None
    assert tm.total_float == 960
