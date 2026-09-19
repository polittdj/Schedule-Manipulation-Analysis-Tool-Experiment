"""The backward pass does not run THROUGH finished or started work (R-70).

MS Project derives a predecessor's late dates from the project finish, not from work that is
already done: on ``Hard_File_updated3`` UID 188's stored LateFinish is the project finish,
2026-12-12 17:00, while its only successor, the completed UID 291, is stored with a late start of
09-08 08:00 (its own record — every completed activity in the corpus stores LateStart =
ActualStart and LateFinish = ActualFinish, 8,644 of 8,644). The pre-R-70 engine bound 188 to
291's need and read 09-08, three months early, and 189 / 181 / 178 / 179 / 180 above it followed;
188's FreeSlack is stored equal to its TotalSlack — the completed successor anchors nothing.

A STARTED successor presents its REMAINING portion: the remaining work's late start (its late
finish less its remaining duration), never earlier than where that work is scheduled to resume
(its early finish less the same remaining). The witness is the logic-reestablished Hard_File
conversion: UID 188 (unstarted) is stored at 187's Resume, 08-17 17:00 — not at 187's record
(08-05, its LateStart) and not at the unfloored 08-12 13:00 — while 187 itself carries -3.5 days.
Across the 44-file corpus the floored form reproduces the stored late finish on every predecessor
of a started successor; the unfloored form misses the witness; "the record" and "resume alone"
are refuted by the 22 SS links they would wrongly bind.

Every expectation below was derived by hand from the calendars before the first run. Red first:
each dated assertion fails on the pre-R-70 engine by name; the controls are named as such.
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
MON_1700 = dt.datetime(2026, 7, 6, 17, 0)
TUE_0800 = dt.datetime(2026, 7, 7, 8, 0)
TUE_1700 = dt.datetime(2026, 7, 7, 17, 0)
WED_1700 = dt.datetime(2026, 7, 8, 17, 0)
THU_1700 = dt.datetime(2026, 7, 9, 17, 0)
FRI_1700 = dt.datetime(2026, 7, 10, 17, 0)
DAY = 480
#: MS Project's Standard calendar, 08:00-12:00 + 13:00-17:00
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))
#: a two-shift crew: 06:00-12:00 + 13:00-23:00, Monday to Friday (Hard_File's 16-hour crew)
CAL_16 = Calendar(
    uid=11,
    name="16 Hour Work Days",
    working_minutes_per_day=960,
    day_segments=((360, 720), (780, 1380)),
)
CREW_16 = Resource(unique_id=2, name="Crew", calendar_uid=11)


def _fs(*links: tuple[int, int]) -> tuple[Relationship, ...]:
    return tuple(Relationship(predecessor_id=p, successor_id=s) for p, s in links)


def _schedule(*tasks: Task, rels: tuple[Relationship, ...], crew: bool = False) -> Schedule:
    return Schedule(
        name="the backward pass past finished work",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16) if crew else (STANDARD,),
        resources=(CREW_16,) if crew else (),
        tasks=tasks,
        relationships=rels,
    )


#: A (one day, unstarted) → B, where B is RECORDED COMPLETE over Monday — finished before A even
#: starts (the row's out-of-sequence shape). D (five days, no logic) sets the network finish at
#: Friday 17:00 = minute 2,400. The pre-R-70 backward pass bound A to B's late start (B's late
#: finish is the target, 2,400, less its recorded one-day span = 1,920), so A read a late finish of
#: 1,920 and three days of float; MS Project reads the project finish and four days.
_A = Task(unique_id=1, name="A", duration_minutes=DAY)
_B_DONE = Task(
    unique_id=2,
    name="B (recorded complete)",
    duration_minutes=DAY,
    percent_complete=100.0,
    actual_start=MON,
    actual_finish=MON_1700,
    start=MON,
    finish=MON_1700,
)
_D = Task(unique_id=5, name="D", duration_minutes=5 * DAY)


def test_a_recorded_complete_successor_presents_no_late_need() -> None:
    """The row's mechanism: A's late finish is the backward target, not B's late start.
    Pre-R-70: late_finish 1,920 / total_float 1,440."""
    res = compute_cpm(_schedule(_A, _B_DONE, _D, rels=_fs((1, 2))))
    tm = res.timing(1)
    assert tm.late_finish == 2400
    assert tm.late_start == 2400 - DAY
    assert tm.total_float == 2400 - DAY  # four days: the project finish less A's finish


def test_a_recorded_complete_successor_is_not_a_free_float_anchor() -> None:
    """Hard_File_updated3 UID 188 stores FreeSlack == TotalSlack: with its only successor
    finished, its free float is measured to the project finish. Pre-R-70: -480 (B's recorded
    start is a day before A can finish)."""
    res = compute_cpm(_schedule(_A, _B_DONE, _D, rels=_fs((1, 2))))
    assert res.timing(1).free_float == 2400 - DAY


def test_the_chain_above_a_completed_successor_follows() -> None:
    """189 / 181 / 178 / 179 / 180 above updated3's 188: X → A → B(done). X's late finish is A's
    late start, 1,920 (pre-R-70: 1,440)."""
    x = Task(unique_id=9, name="X", duration_minutes=DAY)
    res = compute_cpm(_schedule(x, _A, _B_DONE, _D, rels=_fs((9, 1), (1, 2))))
    assert res.timing(9).late_finish == 2400 - DAY
    assert res.timing(9).total_float == 2400 - 2 * DAY


def test_a_completed_successor_among_live_ones_binds_nothing() -> None:
    """A → B(done) and A → C (unstarted, one day, late start Thursday 08:00 = 1,920 under D's
    finish): only C binds, and A's late finish is C's late start. Pre-R-70 the completed B
    bound tighter (1,920 too, by coincidence of this fixture's spans — so the pin is on the
    FREE float, which B no longer anchors: min over C only = C's early start 480 - A's finish
    480 = 0; pre-R-70 min(-480, 0) = -480)."""
    c = Task(unique_id=3, name="C", duration_minutes=DAY)
    res = compute_cpm(_schedule(_A, _B_DONE, c, _D, rels=_fs((1, 2), (1, 3))))
    assert res.timing(1).late_finish == 2400 - DAY
    assert res.timing(1).free_float == 0


#: A (one day) → S, a STARTED five-day activity that began on Monday (its actual start) and is
#: three days in (remaining two days = 960). The floor keeps S's early start at A's finish (an
#: out-of-sequence start is floored, never pinned — ADR-0391 / ADR-0476), so S occupies
#: 480 → 2,880 and its remaining portion sits at 1,920 → 2,880; the network finishes at 2,880.
_S_STARTED = Task(
    unique_id=4,
    name="S (started, two days remaining)",
    duration_minutes=5 * DAY,
    percent_complete=60.0,
    remaining_duration_minutes=2 * DAY,
    actual_start=MON,
    start=MON,
)


def test_a_started_successor_presents_its_remaining_portion() -> None:
    """A's late finish is the remaining portion's late start: S's late finish 2,880 less its
    remaining 960 = 1,920 — A may slip two days before it delays the work still to do.
    Pre-R-70 the engine handed A the whole task's late start, 2,880 - 2,400 = 480 (zero float)."""
    res = compute_cpm(_schedule(_A, _S_STARTED, rels=_fs((1, 4))))
    tm = res.timing(1)
    assert tm.late_finish == 2880 - 2 * DAY
    assert tm.total_float == 2880 - 2 * DAY - DAY


def test_the_remaining_portions_late_start_is_floored_where_it_resumes() -> None:
    """The logic-reestablished witness: S's remaining portion carries NEGATIVE slack (a
    successor T with a deadline of Tuesday 17:00 = 960 puts S's late finish at 480, so the
    remaining work's unfloored late start would be 480 - 960 = -480), but A's need is floored
    where the remaining work is scheduled — S's early finish 2,880 less 960 = 1,920. A keeps
    three days of float; the negative slack stays on S and T. Pre-R-70: A's late finish -1,920
    (S's late start 480 - 2,400) and a float of -2,400."""
    t = Task(unique_id=6, name="T", duration_minutes=DAY, deadline=TUE_1700)
    res = compute_cpm(_schedule(_A, _S_STARTED, t, rels=_fs((1, 4), (4, 6))))
    assert res.timing(6).total_float < 0 and res.timing(4).total_float < 0
    tm = res.timing(1)
    assert tm.late_finish == 2880 - 2 * DAY
    assert tm.total_float == 2880 - 2 * DAY - DAY


def test_a_started_successor_without_a_stored_remaining_reads_its_percent() -> None:
    """The MPXJ writer drops a zero RemainingDuration (the 99 %-complete activities of the
    24-hour snapshots carry none); with no stored remaining, the remainder of the planned
    duration by percent stands in: 60 % of five days done leaves 960."""
    s = _S_STARTED.model_copy(update={"remaining_duration_minutes": None})
    res = compute_cpm(_schedule(_A, s, rels=_fs((1, 4))))
    assert res.timing(1).late_finish == 2880 - 2 * DAY


def test_an_ff_link_to_a_started_successor_keeps_its_late_finish() -> None:
    """CONTROL (green before and after): a finish-to-finish need is the successor's late
    finish — the remaining work's finish IS the task's. Under a finish-to-finish link S's start
    is bound by nothing but its record, so S occupies 0 → 2,400 and A's late finish is 2,400."""
    rel = (Relationship(predecessor_id=1, successor_id=4, type=RelationshipType.FF),)
    res = compute_cpm(_schedule(_A, _S_STARTED, rels=rel))
    assert res.timing(4).early_finish == 2400
    assert res.timing(1).late_finish == 2400


def test_an_unstarted_successor_is_unchanged() -> None:
    """CONTROL (green before and after): the rule is about progress; an unstarted successor
    presents its late start as it always did."""
    c = Task(unique_id=3, name="C", duration_minutes=2 * DAY)
    res = compute_cpm(_schedule(_A, c, _D, rels=_fs((1, 3))))
    assert res.timing(1).late_finish == 2400 - 2 * DAY
    assert res.timing(1).free_float == 0


#: The witness's own shape — a crew successor on the wall path. A (Standard, one day) → S, a
#: 32-hour crew activity (two crew days) that started Monday 06:00 and has 16 crew hours left.
#: The floor puts S's early start at A's finish, Monday 17:00 (a working instant for the crew);
#: 32 crew hours from there: Monday 17:00-23:00 (6 h), Tuesday (16 h), Wednesday 06:00-12:00 (6 h)
#: and 13:00-17:00 (4 h) → Wednesday 17:00. Its remaining 16 hours retreat from that finish to
#: Tuesday 17:00 (4 h + 6 h on Wednesday, 6 h on Tuesday 17:00-23:00). D sets the target at
#: Friday 17:00; S's late finish is Friday 17:00 and the remaining portion's late start retreats
#: 16 h to Thursday 17:00 — the need A reads. Pre-R-70 A read the whole task's late start,
#: Friday 17:00 less 32 crew hours = Wednesday 17:00.
_S_CREW = Task(
    unique_id=7,
    name="S (crew, started, 16 h remaining)",
    duration_minutes=32 * 60,
    percent_complete=50.0,
    remaining_duration_minutes=16 * 60,
    actual_start=dt.datetime(2026, 7, 6, 6, 0),
    start=dt.datetime(2026, 7, 6, 6, 0),
    resource_assignments=(Assignment(resource_id=2, work_minutes=32 * 60, units=1.0),),
)


def test_a_crew_successors_remaining_portion_retreats_on_its_own_legs() -> None:
    """A's late finish is Thursday 17:00 — minute 1,920 of the Standard axis — and its float
    three days (pre-R-70: Wednesday 17:00, 1,440, two days)."""
    res = compute_cpm(_schedule(_A, _S_CREW, _D, rels=_fs((1, 7)), crew=True))
    assert res.timing(7).early_finish_wall == WED_1700
    assert res.timing(7).late_finish_wall == FRI_1700
    tm = res.timing(1)
    assert tm.late_finish == 1920
    assert tm.total_float == 1920 - DAY


#: The wall-path shape of the row: a crew activity whose only successor is FINISHED. A16 (the
#: crew, 16 h = one crew day, no predecessors) starts at the project start, Monday 08:00, and
#: finishes Monday 08:00-12:00 (4 h) + 13:00-23:00 (10 h) + Tuesday 06:00-08:00 (2 h) = Tuesday
#: 08:00. D sets the target at Friday 17:00. With B finished, A16's late finish is the target
#: instant itself and its late start retreats one crew day: Friday 17:00-13:00 (4 h), 12:00-06:00
#: (6 h), Thursday 23:00-17:00 (6 h) — Thursday 17:00. Pre-R-70 A16 retreated from B's late
#: start, the start-role rendering of minute 1,920 (Friday 08:00), nine crew hours earlier.
_A16 = Task(
    unique_id=8,
    name="A16 (crew)",
    duration_minutes=16 * 60,
    resource_assignments=(Assignment(resource_id=2, work_minutes=16 * 60, units=1.0),),
)


def test_a_crew_predecessor_of_a_completed_successor_retreats_from_the_target() -> None:
    res = compute_cpm(_schedule(_A16, _B_DONE, _D, rels=_fs((8, 2)), crew=True))
    tm = res.timing(8)
    assert tm.early_finish_wall == TUE_0800
    assert tm.late_finish_wall == FRI_1700
    assert tm.late_start_wall == THU_1700


def test_an_ss_link_into_a_started_successor_reads_its_remaining_portion() -> None:
    """A → S start-to-start, S started on Monday with two days of its five left. S occupies
    0 → 2,400 (its start is its record, the network finishes there); its remaining portion's
    late start is 2,400 - 960 = 1,440, so A's late finish is 1,440 + A's day = 1,920 and A
    keeps three days of float. Pre-R-70 the link handed A the whole task's late start, 0, and
    A read a late finish of 480 and zero float. Across the corpus the 22 start-to-start links
    into started work never bind — the pin is the synthetic positive the population lacks."""
    rel = (Relationship(predecessor_id=1, successor_id=4, type=RelationshipType.SS),)
    res = compute_cpm(_schedule(_A, _S_STARTED, rels=rel))
    assert res.timing(4).early_finish == 2400
    tm = res.timing(1)
    assert tm.late_finish == 1920
    assert tm.total_float == 1920 - DAY


def test_a_milestone_carries_a_started_crew_successors_remaining_instant() -> None:
    """A16 (the crew) → M (a milestone) → S_CREW (started, 16 h left) with D's Friday target.
    S starts at M's instant, Tuesday 08:00, and finishes Thursday 08:00 (4 h + 10 h Tuesday,
    16 h Wednesday, 2 h Thursday); its remaining portion's late start retreats 16 h from Friday
    17:00 to Thursday 17:00, later than where it resumes (Wednesday 08:00), so that is the need.
    M's binding need is S's — an instant the axis lost — so M carries Thursday 17:00 (R-67's
    carry, fed by R-70's need), and A16 retreats from it: late finish Thursday 17:00, late start
    one crew day earlier, Wednesday 17:00. A binding check that reads S's whole-task late start
    (Wednesday 17:00, minute 1,440) judges S non-binding, carries nothing, and hands A16 the
    minute's Friday 08:00 rendering — the battery's M11, red here by name."""
    m = Task(unique_id=9, name="M", duration_minutes=0, is_milestone=True)
    res = compute_cpm(_schedule(_A16, m, _S_CREW, _D, rels=_fs((8, 9), (9, 7)), crew=True))
    assert res.timing(7).early_finish_wall == dt.datetime(2026, 7, 9, 8, 0)
    assert res.timing(9).late_finish_wall == THU_1700
    tm = res.timing(8)
    assert tm.late_finish_wall == THU_1700
    assert tm.late_start_wall == WED_1700
