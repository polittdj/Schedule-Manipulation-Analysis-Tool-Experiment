"""Out-of-sequence progress resumes its REMAINING work, not its whole duration (R-72, ADR-0513).

A started activity whose logic start lies PAST its recorded actual start — its predecessors
finish after it began — was re-spanned for its FULL duration from that logic start: ADR-0391's
floor cannot bind (the logic start is the later instant) and ``start + duration`` ran from it.
On ``Hard_File_updated_with_logic_reestablished`` UID 187 (60 %, 48 crew hours left, started
08-05 out of sequence) that read 120 crew hours from its predecessor 188's 08-17 17:00 finish to
08-27 08:00, where MS Project resumes the remaining 48 h there and finishes 08-20 17:00 — and
the need 188 read from it (R-70) sat four days late, so the chain 94 … 188 carried +4 days for
a stored 0. MS Project keeps the actual portion where the record puts it (Start = ActualStart on
every started activity in the 44-file corpus) and schedules the REMAINING work from ``Resume``:
``Finish = Resume + RemainingDuration`` on the task's own calendar reproduces the stored finish
of 1,009 of the corpus's 1,051 started activities from the file alone.

The rule: such an activity starts at its RECORD; its remaining portion starts at the later of
the stored Resume and the link bounds evaluated for the remaining (an FF / SF need retreats the
remaining, not the whole task — Large_Test_File UID 1489's ten FF links from finished work read
its whole-task start 26 days before its Resume and its finish 26 days early, ADR-0476's
"136-day swing" being the FULL-duration re-span from a pinned start; a constraint on the start
binds nothing once the work has begun — UID 4581's SNET lies after its actual start and MS
Project resumes its work at the status date); the finish is that restart plus the remaining on
the task's own legs. The backward pass retreats such an activity by the remaining it was placed
with; a start-type (SS / SF) successor need binds NO started predecessor, whose start is a
record (UID 5535's SS successor bound its late finish to 2027-07-02 where the file stores
11-05); a predecessor's free float anchors where the remaining work starts.

Every expectation below was derived by hand from the calendars before the first run. Red first:
each dated assertion fails on the pre-R-72 engine by name; the controls are named as such.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday, the project start
MON_1700 = dt.datetime(2026, 7, 6, 17, 0)
TUE_1700 = dt.datetime(2026, 7, 7, 17, 0)
WED_1700 = dt.datetime(2026, 7, 8, 17, 0)
NEXT_MON = dt.datetime(2026, 7, 13, 8, 0)
NEXT_TUE = dt.datetime(2026, 7, 14, 8, 0)
NEXT_WED = dt.datetime(2026, 7, 15, 8, 0)
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


def _link(
    p: int, s: int, rel: RelationshipType = RelationshipType.FS, lag: int = 0
) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=rel, lag_minutes=lag)


def _schedule(*tasks: Task, rels: tuple[Relationship, ...], crew: bool = False) -> Schedule:
    return Schedule(
        name="out-of-sequence progress",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD, CAL_16) if crew else (STANDARD,),
        resources=(CREW_16,) if crew else (),
        tasks=tasks,
        relationships=rels,
    )


#: A (five days from the project start: Monday 08:00 → Friday 17:00, minute 2,400) → S, which
#: began on that same Monday OUT OF SEQUENCE (its actual start is the project start), is 60 %
#: done with two days (960) left, stopped Wednesday 17:00 (minute 1,440) and has its remaining
#: work resuming there (Resume == Stop, the common record). Pre-R-72 the floor did not bind (the
#: logic start, 2,400, lies past the actual start, 0) and S was re-spanned for its full five days
#: from A's finish: 2,400 → 4,800, the project finishing a Friday later. R-72: S starts at its
#: record (0) and its remaining two days start where the later of A's finish (2,400) and the
#: Resume (1,440) puts them — 2,400 → 3,360, Tuesday 07-14 17:00.
_A = Task(unique_id=1, name="A", duration_minutes=5 * DAY)
_S = Task(
    unique_id=2,
    name="S (started out of sequence, two days left)",
    duration_minutes=5 * DAY,
    percent_complete=60.0,
    remaining_duration_minutes=2 * DAY,
    actual_start=MON,
    start=MON,
    stop=WED_1700,
    resume=WED_1700,
)


def test_an_out_of_sequence_activity_resumes_its_remaining_from_the_logic_it_waited_for() -> None:
    """The row's mechanism. Pre-R-72: (2,400, 4,800), project finish 4,800, S not disclosed."""
    res = compute_cpm(_schedule(_A, _S, rels=(_link(1, 2),)))
    s = res.timing(2)
    assert (s.early_start, s.early_finish) == (0, 3360)
    assert res.project_finish == 3360
    assert 2 in res.actual_start_driven  # the start is the record
    assert 2 not in res.date_driven  # logic, not the stored Resume, placed the remaining


def test_the_stored_resume_places_the_remaining_when_it_lies_past_the_logic() -> None:
    """MS Project rescheduled S's remaining work to the next Wednesday 08:00 (minute 3,360,
    past A's finish): the remaining two days run 3,360 → 4,320 and the reschedule is disclosed
    as ADR-0309's. Pre-R-72: (2,400, 4,800) — the resume floor (3,360 + 960 = 4,320) sat below
    the full re-span and never bound."""
    s2 = _S.model_copy(update={"resume": NEXT_WED})
    res = compute_cpm(_schedule(_A, s2, rels=(_link(1, 2),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (0, 4320)
    assert 2 in res.date_driven and 2 in res.actual_start_driven


def test_the_backward_pass_retreats_the_remaining_and_the_predecessor_reads_its_start() -> None:
    """S's late finish is the network finish, 3,360; its late start retreats the REMAINING,
    2,400, and its float is its finish slack, 0. A's late finish is the remaining portion's
    late start (R-70's need), 2,400 — A is critical. Pre-R-72: S 2,400 → 4,800 and A read a
    late finish of 4,800 - 960 = 3,840 and three days of float."""
    res = compute_cpm(_schedule(_A, _S, rels=(_link(1, 2),)))
    s, a = res.timing(2), res.timing(1)
    assert (s.late_start, s.late_finish, s.total_float) == (2400, 3360, 0)
    assert (a.late_finish, a.total_float) == (2400, 0)
    assert a.is_critical and s.is_critical


#: Large_Test_File UID 1489's shape: A → S FINISH-TO-FINISH, S a three-day activity begun on the
#: Monday with one day (480) left, and a Resume (the status date's next working instant, the
#: next Tuesday 08:00 = minute 2,880) LATER than the need the FF link puts on the remaining.
_S_FF = Task(
    unique_id=3,
    name="S (FF successor, one day left)",
    duration_minutes=3 * DAY,
    percent_complete=66.0,
    remaining_duration_minutes=DAY,
    actual_start=MON,
    start=MON,
    stop=NEXT_TUE,
    resume=NEXT_TUE,
)


def test_an_ff_need_is_evaluated_for_the_remaining_and_the_resume_still_wins() -> None:
    """The FF need on the remaining is A's finish less one day, 1,920; the Resume, 2,880, is
    later, so the remaining day runs 2,880 → 3,360 — Resume + remaining, the stored finish of
    UID 1489. Pre-R-72 the FF bound was evaluated for the WHOLE task (2,400 - 1,440 = 960),
    the floor did not bind, and S read 960 → 2,400: 26 days early on the golden."""
    res = compute_cpm(_schedule(_A, _S_FF, rels=(_link(1, 3, RelationshipType.FF),)))
    assert (res.timing(3).early_start, res.timing(3).early_finish) == (0, 3360)
    assert 3 in res.date_driven


def test_an_ff_need_retreats_the_remaining_not_the_whole_task() -> None:
    """With the Resume early (Monday 17:00, 480) the FF need decides: the remaining day must
    end no earlier than A's finish, so it runs 1,920 → 2,400 and S finishes WITH A. A restart
    evaluated for the whole task (960) would end the remaining at 1,440, before A's finish —
    the FF link violated. Pre-R-72 the finish read 2,400 too (960 + 1,440), the start 960."""
    s = _S_FF.model_copy(update={"stop": MON_1700, "resume": MON_1700})
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 3, RelationshipType.FF),)))
    assert (res.timing(3).early_start, res.timing(3).early_finish) == (0, 2400)
    assert res.timing(3).early_finish >= res.timing(1).early_finish


def test_an_ss_need_bounds_the_remaining_portion() -> None:
    """B (two days, no logic, 0 → 960) → S start-to-start with a one-day lag: the remaining may
    not start before 480; the Resume, Tuesday 17:00 (960), is later and decides: 960 → 1,920.
    Pre-R-72: the lag put S's start at 480, past its record, and the full five days ran from
    there to 2,880."""
    b = Task(unique_id=4, name="B", duration_minutes=2 * DAY)
    s = _S.model_copy(update={"stop": TUE_1700, "resume": TUE_1700})
    res = compute_cpm(_schedule(b, s, rels=(_link(4, 2, RelationshipType.SS, DAY),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (0, 1920)


def test_a_constraint_on_the_start_binds_nothing_once_the_work_has_begun() -> None:
    """UID 4581's shape: S carries a Start-No-Earlier-Than of the next Monday (2,400) and no
    predecessors. Pre-R-72 the constraint floored the start past the record and the full five
    days ran 2,400 → 4,800; MS Project keeps the start at the actual start and resumes the
    remaining at the Resume (1,440): 0 → 2,400, the stored Finish on the golden."""
    s = _S.model_copy(update={"constraint_type": ConstraintType.SNET, "constraint_date": NEXT_MON})
    res = compute_cpm(_schedule(s, rels=()))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (0, 2400)
    assert res.project_finish == 2400


def test_a_start_type_need_binds_no_started_predecessor() -> None:
    """Large_Test_File UID 5535's shape. P is started (four days, half done, two left, its logic
    start AT its record — not out of sequence, so its placement is unchanged: 0 → 1,920) with a
    start-to-start successor U (one day, deadline Wednesday 17:00 → late start 960) and a
    finish-to-start successor W (one day, late start 4,320 under D's finish at 4,800). MS
    Project derives P's late finish from W alone — P's start is a record and cannot slip toward
    U's need — so P's late finish is 4,320 and its float 2,400. Pre-R-72 the SS need bound P's
    late finish to U's late start plus P's duration, 2,880, and P read 960 of float."""
    p = Task(
        unique_id=5,
        name="P (started, at its record)",
        duration_minutes=4 * DAY,
        percent_complete=50.0,
        remaining_duration_minutes=2 * DAY,
        actual_start=MON,
        start=MON,
        stop=TUE_1700,
        resume=TUE_1700,
    )
    u = Task(unique_id=6, name="U", duration_minutes=DAY, deadline=WED_1700)
    w = Task(unique_id=7, name="W", duration_minutes=DAY)
    d = Task(unique_id=8, name="D", duration_minutes=10 * DAY)
    res = compute_cpm(_schedule(p, u, w, d, rels=(_link(5, 6, RelationshipType.SS), _link(5, 7))))
    assert (res.timing(5).early_start, res.timing(5).early_finish) == (0, 1920)
    assert (res.timing(6).late_start, res.timing(7).late_start) == (960, 4320)
    assert (res.timing(5).late_finish, res.timing(5).total_float) == (4320, 2400)


def test_a_predecessors_free_float_anchors_where_the_remaining_work_starts() -> None:
    """With S's remaining rescheduled to the next Wednesday (3,360), A may slip two days before
    it delays the work still to do: free float 960, equal to its total float. An anchor at S's
    START — its record, minute 0, before A even finishes — would read -2,400. Pre-R-72 A's free
    float was 0 (S's whole re-span began at A's finish)."""
    s2 = _S.model_copy(update={"resume": NEXT_WED})
    res = compute_cpm(_schedule(_A, s2, rels=(_link(1, 2),)))
    assert res.timing(1).free_float == 960
    assert res.timing(1).total_float == 960


def test_an_absent_remaining_reads_the_percent_derived_remainder() -> None:
    """The MPXJ writer drops a zero RemainingDuration; with no stored remaining the remainder of
    the planned duration by percent stands in: 40 % of five days is 960 — the same placement.
    Pre-R-72: (2,400, 4,800)."""
    s = _S.model_copy(update={"remaining_duration_minutes": None})
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (0, 3360)


def test_an_sra_override_is_the_remaining() -> None:
    """Every override producer builds an in-progress task's override from its REMAINING (the
    ADR-0309 rule): one day sampled runs 2,400 → 2,880 from the restart. Pre-R-72 the override
    was the span from the logic start — the same finish, 2,880, from a start of 2,400 (a
    CONTROL on the finish; the start is the pin)."""
    res = compute_cpm(_schedule(_A, _S, rels=(_link(1, 2),)), duration_overrides={2: DAY})
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (0, 2880)


def test_a_source_recording_neither_resume_nor_stop_is_unchanged() -> None:
    """CONTROL (green before and after): a P6 export or a synthetic fixture records no restart;
    the placement stays the pre-R-72 one — the row's oracle is MS Project's, and a file that
    carries no reschedule cannot be read as one."""
    s = _S.model_copy(update={"stop": None, "resume": None})
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (2400, 4800)
    assert 2 not in res.actual_start_driven


#: The witness's own shape on the wall path. Z (Standard, five days: Monday 07-06 08:00 → Friday
#: 17:00) → A (Standard, one day: Monday 07-13 08:00 → 17:00, minute 2,880) → S, a 120-hour crew
#: activity (the 16-hour calendar) that began Tuesday 07-07 06:00 OUT OF SEQUENCE, is 60 % done
#: with 48 crew hours left, stopped Friday 07-10 17:00 and has its remaining work resuming at
#: A's finish, Monday 07-13 17:00 — exactly UID 187 after 188. The tail: Monday 17:00-23:00
#: (6 h), Tuesday (16 h), Wednesday (16 h), Thursday 06:00-12:00 (6 h) and 13:00-17:00 (4 h) →
#: Thursday 07-16 17:00 (187's 08-20 17:00). Pre-R-72 the full 120 h ran from Monday 17:00: 70 h
#: by Friday 23:00, 118 h by the next Wednesday, 2 h more → Thursday 07-23 08:00 (187's 08-27
#: 08:00). A's late finish is the need S presents (R-70): S's late finish is the network finish,
#: its remaining retreats 48 h from it to Monday 07-13 17:00 — minute 2,880 of the Standard axis
#: — so A is critical; pre-R-72 the need sat days later. (An actual start BEFORE the project
#: start would clamp to it — the axis renders no negative offset — so S begins the day after.)
_Z = Task(unique_id=11, name="Z (five days)", duration_minutes=5 * DAY)
_A1 = Task(unique_id=10, name="A (one day)", duration_minutes=DAY)
_S_CREW = Task(
    unique_id=9,
    name="S (crew, started out of sequence, 48 h left)",
    duration_minutes=120 * 60,
    percent_complete=60.0,
    remaining_duration_minutes=48 * 60,
    actual_start=dt.datetime(2026, 7, 7, 6, 0),
    start=dt.datetime(2026, 7, 7, 6, 0),
    stop=dt.datetime(2026, 7, 10, 17, 0),
    resume=dt.datetime(2026, 7, 13, 17, 0),
    resource_assignments=(Assignment(resource_id=2, work_minutes=120 * 60, units=1.0),),
)


def test_the_witness_shape_resumes_its_tail_on_the_crews_own_legs() -> None:
    res = compute_cpm(_schedule(_Z, _A1, _S_CREW, rels=(_link(11, 10), _link(10, 9)), crew=True))
    s = res.timing(9)
    assert s.early_start_wall == dt.datetime(2026, 7, 7, 6, 0)
    assert s.early_finish_wall == dt.datetime(2026, 7, 16, 17, 0)
    assert res.project_finish_wall == dt.datetime(2026, 7, 16, 17, 0)
    assert 9 in res.actual_start_driven and 9 not in res.date_driven
    a = res.timing(10)
    assert (a.early_finish, a.late_finish, a.total_float) == (2880, 2880, 0)
    assert s.late_start_wall == dt.datetime(2026, 7, 13, 17, 0) and s.total_float == 0


#: A finish-to-finish need on the wall path. A10 (Standard, ten days: Monday 07-06 08:00 → Friday
#: 07-17 17:00) → S FINISH-TO-FINISH: the crew activity again (120 h, 48 h left), begun Tuesday
#: 07-07 06:00 out of sequence, stopped and resuming Friday 07-10 17:00. The need on the TAIL is
#: A10's finish less 48 crew hours — Friday 13:00-17:00 (4 h) and 06:00-12:00 (6 h), Thursday
#: (16 h), Wednesday (16 h), Tuesday 17:00-23:00 (6 h) → Tuesday 07-14 17:00 — later than the
#: Resume, so the tail runs 07-14 17:00 → 07-17 17:00 and S finishes WITH A10. A restart that
#: retreated the WHOLE plan from the need (07-08 08:00, 120 h before A10's finish) would let the
#: Resume decide (07-10 17:00) and end the tail Wednesday 07-15 17:00, two days before the finish
#: the link demands — the battery's M06, red here by name. Pre-R-72 the whole plan ran from that
#: 07-08 08:00 and, by construction of the bound, finished with A10 too: the start is the pin.
_A10 = Task(unique_id=12, name="A10 (ten days)", duration_minutes=10 * DAY)
_S_CREW_FF = _S_CREW.model_copy(
    update={
        "unique_id": 13,
        "stop": dt.datetime(2026, 7, 10, 17, 0),
        "resume": dt.datetime(2026, 7, 10, 17, 0),
    }
)


def test_a_wall_path_ff_need_retreats_the_tail_not_the_whole_plan() -> None:
    res = compute_cpm(
        _schedule(_A10, _S_CREW_FF, rels=(_link(12, 13, RelationshipType.FF),), crew=True)
    )
    s, a = res.timing(13), res.timing(12)
    assert s.early_start_wall == dt.datetime(2026, 7, 7, 6, 0)
    assert s.early_finish_wall == dt.datetime(2026, 7, 17, 17, 0)
    assert a.early_finish == 4800  # Friday 07-17 17:00 on the Standard axis
    assert s.early_finish_wall >= dt.datetime(2026, 7, 17, 17, 0)
    assert 13 in res.actual_start_driven and 13 not in res.date_driven


def test_a_wall_path_resume_past_the_logic_places_the_tail() -> None:
    """The witness shape with the crew's actual work running ON past A's finish: it stopped
    Tuesday 07-14 06:00 and resumes there (Resume == Stop — MS Project resumes where the work
    stopped, which is later than the logic allows; ADR-0309's floor, which needs Resume > Stop,
    does not reach this shape). The tail runs from Tuesday 06:00 — Tuesday (16 h), Wednesday
    (16 h), Thursday (16 h) → Thursday 07-16 23:00 — and the stored instant, not logic, placed
    it. A restart that read the logic alone would resume Monday 17:00 and finish Thursday 17:00
    (the battery's M09); pre-R-72 the full 120 h ran from Monday 17:00."""
    s = _S_CREW.model_copy(
        update={"stop": dt.datetime(2026, 7, 14, 6, 0), "resume": dt.datetime(2026, 7, 14, 6, 0)}
    )
    res = compute_cpm(_schedule(_Z, _A1, s, rels=(_link(11, 10), _link(10, 9)), crew=True))
    assert res.timing(9).early_start_wall == dt.datetime(2026, 7, 7, 6, 0)
    assert res.timing(9).early_finish_wall == dt.datetime(2026, 7, 16, 23, 0)
    assert 9 in res.date_driven and 9 in res.actual_start_driven


def test_a_start_type_need_binds_no_started_crew_predecessor() -> None:
    """UID 5535's shape on the wall path. P is a started crew activity AT its record (32 crew hours
    planned from Monday 08:00), 50 % done with 16 crew hours left, stopped and resuming Tuesday
    17:00 — its remaining runs Tuesday 17:00-23:00 (6 h), Wednesday 06:00-12:00 (6 h) and
    13:00-17:00 (4 h) → Wednesday 07-08 17:00 (R-73, ADR-0517: Resume + remaining on the crew's
    legs; the pre-R-73 engine ran the whole 32 h from the record, 14 h Monday, 16 h Tuesday, 2
    h → Wednesday 08:00). It has a start-to-start successor U (one day, deadline Tuesday 17:00
    → late start Tuesday 08:00) and a finish-to-start successor W (one day; late start 4,320 =
    Friday 07-17 08:00 under D's finish at 4,800). P's late finish is W's late start — its
    start is a record and cannot slip toward U's need — and its float on the project axis is
    the finish slack, Thursday 07-09 through Thursday 07-16, six days: 2,880 (its start slack,
    to the late start the 16-hour tail retreats from Friday 08:00 — Thursday 07-16 08:00 — is
    3,840). With the start need kept (pre-R-72, the battery's M13) P's late start was pulled to
    Tuesday 08:00, its late finish to Thursday 07-09 08:00, and its float read 480."""
    p = Task(
        unique_id=14,
        name="P (crew, started at its record)",
        duration_minutes=32 * 60,
        percent_complete=50.0,
        remaining_duration_minutes=16 * 60,
        actual_start=MON,
        start=MON,
        stop=TUE_1700,
        resume=TUE_1700,
        resource_assignments=(Assignment(resource_id=2, work_minutes=32 * 60, units=1.0),),
    )
    u = Task(unique_id=15, name="U", duration_minutes=DAY, deadline=TUE_1700)
    w = Task(unique_id=16, name="W", duration_minutes=DAY)
    d = Task(unique_id=17, name="D", duration_minutes=10 * DAY)
    res = compute_cpm(
        _schedule(p, u, w, d, rels=(_link(14, 15, RelationshipType.SS), _link(14, 16)), crew=True)
    )
    assert res.timing(14).early_finish_wall == dt.datetime(2026, 7, 8, 17, 0)
    assert (res.timing(15).late_start, res.timing(16).late_start) == (480, 4320)
    assert res.timing(14).late_finish_wall == dt.datetime(2026, 7, 17, 8, 0)
    assert res.timing(14).late_start_wall == dt.datetime(2026, 7, 16, 8, 0)
    assert res.timing(14).total_float == 2880


def test_a_crew_predecessors_free_float_anchors_where_the_remaining_work_starts() -> None:
    """A16 (the crew, one crew day: Monday 08:00 → Tuesday 07-07 08:00) → S, started out of
    sequence at the project start with its remaining two days rescheduled to the next Wednesday
    08:00 (minute 3,360): A16 may slip six working days, 2,880, before it delays the work still to
    do — its free float equals its total float. An anchor at S's START, its record at minute 0,
    would read -480 (the battery's M15); pre-R-72 the anchor was S's logic start, A16's own
    finish, and the free float read 0."""
    a16 = Task(
        unique_id=18,
        name="A16 (crew)",
        duration_minutes=16 * 60,
        resource_assignments=(Assignment(resource_id=2, work_minutes=16 * 60, units=1.0),),
    )
    s = _S.model_copy(update={"resume": NEXT_WED})
    res = compute_cpm(_schedule(a16, s, rels=(_link(18, 2),), crew=True))
    assert res.timing(18).early_finish_wall == dt.datetime(2026, 7, 7, 8, 0)
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (0, 4320)
    assert res.timing(18).free_float == 2880
    assert res.timing(18).total_float == 2880


def test_a_crew_predecessors_free_float_anchors_at_a_crew_successors_restart() -> None:
    """The wall-path anchor on both sides. A16 (the crew, one crew day: Monday 08:00 → Tuesday
    07-07 08:00) → S, the crew activity begun at the project start OUT OF SEQUENCE (its Monday
    06:00 record clamps to the project start), stopped Tuesday 17:00 with its remaining 48 h
    resuming Wednesday 07-08 06:00 — later than A16's finish, so the restart is the Resume.
    A16 may slip one project day, 480, before it delays that work; its free float equals its
    total float (S's need on A16 is the restart, R-70). An anchor at S's START — its record,
    Monday 08:00, before A16 even finishes — would read -480 (the battery's M15); pre-R-72 the
    anchor was S's logic start, A16's own finish, and the free float read 0."""
    a16 = Task(
        unique_id=19,
        name="A16 (crew)",
        duration_minutes=16 * 60,
        resource_assignments=(Assignment(resource_id=2, work_minutes=16 * 60, units=1.0),),
    )
    s = _S_CREW.model_copy(
        update={
            "unique_id": 20,
            "actual_start": dt.datetime(2026, 7, 6, 6, 0),
            "start": dt.datetime(2026, 7, 6, 6, 0),
            "stop": TUE_1700,
            "resume": dt.datetime(2026, 7, 8, 6, 0),
        }
    )
    res = compute_cpm(_schedule(a16, s, rels=(_link(19, 20),), crew=True))
    assert res.timing(19).early_finish_wall == dt.datetime(2026, 7, 7, 8, 0)
    assert res.timing(20).early_start_wall == MON
    assert res.timing(20).early_finish_wall == dt.datetime(2026, 7, 10, 23, 0)
    assert res.timing(19).free_float == 480
    assert res.timing(19).total_float == 480
