"""Every started activity's remaining work is scheduled from where the file says it resumes (R-73,
ADR-0517) — ``Finish = Resume + RemainingDuration`` on its execution calendar, MS Project's own
rule, which the corpus reproduces from the file alone on 1,111 of the 1,149 started activities that
store a remaining (the 38 misses are four split bookings and one minute of the model's grid).

The pre-R-73 engine ran a started activity that was NOT out of sequence for its WHOLE planned
duration from its recorded start (ADR-0391's floor, ADR-0309's floor only where the file recorded a
reschedule), so an actual portion that ran long or short landed the finish off the stored instant:
Large_Test_File UID 4616 (99 %, 13 h left) finished 106 days early, 5505 43 days early, 7378 three
days late, and the 24Hour_Calendar file's UID 17 (98 %, 20 h left) 64 days late — that file's
project finish with it. ADR-0513 had measured the general model and held it back for one reason:
the contiguous projection ruler (``datetime_to_offset``) reads an after-lunch Resume up to the
lunch gap LATER, so EVM1 UID 18's 15:00 Resume carried that golden's finish across midnight. The
axis is working minutes, and ``start + duration`` on it counts them exactly; the stored Resume is
therefore read SEGMENT-AWARE (``_stored_instant_offset`` — 15:00 on a 08-12 / 13-17 day is minute
360, not 420) and the remaining added on the axis. That read is only ever a floor under ``max()``
against the link bounds, so it can never place a restart before a linked predecessor's finish — not
a second ruler for the network's ordering (ADR-0322's trap).

The remaining is the STORED one (or the SRA's override, which is a remaining — the
``_resume_bounds`` rule); an absent element is MPXJ's dropped zero, and such an activity keeps
``actual_start + duration``, which IS its stored finish on every such activity in the corpus (EVM1
UID 17 and the 24-hour snapshot's 267 / 302 / 385 store ActualDuration == Duration). The backward
pass retreats by the remaining, so the total float is the finish slack — MS Project's TotalSlack on
started work; an in-sequence started successor anchors its predecessor's free float at its RECORD
(ADR-0512: EVM1 UID 17 stores 0 against UID 18's actual start, not the 360 its remaining portion
would give); a recorded reschedule (Resume > Stop) that moves the finish past the record's own plan
is disclosed as ADR-0309 disclosed it, and contiguous progress resuming where it stopped is not.

Every expectation below was derived by hand from the calendars before the first run. Red first:
each dated assertion fails on the pre-R-73 engine by name; the controls are named as such.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 7, 6, 8, 0)  # a Monday, the project start
MON_1200 = dt.datetime(2026, 7, 6, 12, 0)
NEXT_MON = dt.datetime(2026, 7, 13, 8, 0)  # minute 2,400: the second week's Monday 08:00
NEXT_MON_1500 = dt.datetime(2026, 7, 13, 15, 0)
NEXT_MON_1700 = dt.datetime(2026, 7, 13, 17, 0)
NEXT_TUE_1300 = dt.datetime(2026, 7, 14, 13, 0)
NEXT_TUE_1700 = dt.datetime(2026, 7, 14, 17, 0)
NEXT_WED_1700 = dt.datetime(2026, 7, 15, 17, 0)
THIRD_MON = dt.datetime(2026, 7, 20, 8, 0)  # minute 4,800
DAY = 480
#: MS Project's Standard calendar, 08:00-12:00 + 13:00-17:00
STANDARD = Calendar(uid=1, name="Standard", day_segments=((480, 720), (780, 1020)))


def _link(p: int, s: int, rel: RelationshipType = RelationshipType.FS) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=rel, lag_minutes=0)


def _schedule(*tasks: Task, rels: tuple[Relationship, ...]) -> Schedule:
    return Schedule(
        name="started work resumes its remaining",
        project_start=MON,
        calendar=STANDARD,
        calendars=(STANDARD,),
        tasks=tasks,
        relationships=rels,
    )


#: A (five days: Monday 07-06 08:00 → Friday 17:00, minute 2,400) → S, a three-day activity
#: (1,440) that began ON its logic start, the next Monday 08:00 (minute 2,400 — in sequence), and
#: is 50 % done with two days (960) left after THREE days of work: it stopped Wednesday 07-15 17:00
#: (minute 3,840) and resumes there (Resume == Stop, contiguous progress). Pre-R-73 the whole plan
#: ran from the record: 2,400 → 3,840. MS Project: Resume + remaining, 3,840 → 4,800 (Friday 07-17
#: 17:00) — the actual portion ran long, and the finish is a day and a half later than the plan.
_A = Task(unique_id=1, name="A", duration_minutes=5 * DAY)
_S = Task(
    unique_id=2,
    name="S (started in sequence, ran long, two days left)",
    duration_minutes=3 * DAY,
    percent_complete=50.0,
    remaining_duration_minutes=2 * DAY,
    actual_start=NEXT_MON,
    start=NEXT_MON,
    stop=NEXT_WED_1700,
    resume=NEXT_WED_1700,
)
#: D holds the network finish at minute 4,800 (ten days from the project start) where a test needs
#: a late finish that is not the activity's own early finish.
_D = Task(unique_id=9, name="D (ten days)", duration_minutes=10 * DAY)


def test_a_started_activity_finishes_at_its_resume_plus_remaining() -> None:
    """The row's mechanism. Pre-R-73: (2,400, 3,840), the project finishing Wednesday."""
    res = compute_cpm(_schedule(_A, _S, rels=(_link(1, 2),)))
    s = res.timing(2)
    assert (s.early_start, s.early_finish) == (2400, 4800)
    assert res.project_finish == 4800
    # contiguous progress resuming where it stopped is neither an unsupported date nor a floored
    # start: no disclosure
    assert 2 not in res.date_driven and 2 not in res.actual_start_driven


def test_an_actual_portion_that_ran_short_lands_the_finish_earlier_than_the_plan() -> None:
    """S is 75 % done with ONE day (480) left after one day of work (stopped and resuming Monday
    07-13 17:00, minute 2,880): Resume + remaining, 2,880 → 3,360 (Tuesday 17:00), a day EARLIER
    than the plan's 3,840. With D holding the network finish at 4,800, S's late finish is 4,800 and
    its late start is its RECORD, 2,400 (R-71, ADR-0531, re-pinned 2026-09-24 from 4,320 — the
    remaining portion's late start, which is the need S presents upstream, not S's own late start;
    MS Project stores LateStart = ActualStart on 1,159 of 1,159 started activities). Its total
    float is the finish slack, 1,440 — MS Project's TotalSlack on started work (StartSlack 0 and
    TotalSlack == FinishSlack on every started activity of the corpus) — not a start slack.
    Pre-R-73: (3,840, 3,360, 960)."""
    s = _S.model_copy(
        update={
            "percent_complete": 75.0,
            "remaining_duration_minutes": DAY,
            "stop": NEXT_MON_1700,
            "resume": NEXT_MON_1700,
        }
    )
    res = compute_cpm(_schedule(_A, s, _D, rels=(_link(1, 2),)))
    tm = res.timing(2)
    assert (tm.early_start, tm.early_finish) == (2400, 3360)
    assert (tm.late_start, tm.late_finish) == (2400, 4800)
    assert tm.total_float == 1440 and not tm.is_critical


def test_an_after_lunch_resume_is_read_in_working_minutes_not_on_the_contiguous_ruler() -> None:
    """EVM1 UID 18's shape with a finish the plan would miss: S is a FIVE-day activity (2,400)
    begun the next Monday 08:00, 25 % done with 18 h (1,080) left, stopped and resuming that Monday
    15:00 — 360 working minutes into the day (08:00-12:00 and 13:00-15:00), minute 2,760. Resume +
    remaining: 2,760 + 1,080 = 3,840, Wednesday 07-15 17:00 — 2 h Monday, all of Tuesday and all of
    Wednesday, MS Project's own arithmetic. The contiguous ruler reads 15:00 as minute 420 (2,820),
    and 2,820 + 1,080 = 3,900 is Thursday 09:00: the finish across midnight that held the general
    model back in ADR-0513. Pre-R-73 the whole five days ran from the record: 4,800."""
    s = _S.model_copy(
        update={
            "duration_minutes": 5 * DAY,
            "percent_complete": 25.0,
            "remaining_duration_minutes": 18 * 60,
            "stop": NEXT_MON_1500,
            "resume": NEXT_MON_1500,
        }
    )
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (2400, 3840)
    assert res.project_finish == 3840


def test_a_predecessors_free_float_anchors_at_the_record_and_its_late_finish_at_the_restart() -> (
    None
):
    """EVM1 UID 17 → 18 on the fixture above (S 25 % done, resuming Monday 15:00, 18 h left; A five
    days before it). A's free float is measured to S's RECORD — S began the minute A finished, so
    0, MS Project's stored FreeSlack on UID 17 — not to S's restart (which would read 360). A's late
    finish is the need S's REMAINING portion presents (R-70): S's late finish is the network finish,
    3,840, less its remaining 1,080 — minute 2,760 — so A's total float is 360, UID 17's stored
    TotalSlack. Pre-R-73 S finished at 4,800 and A read 1,320 of float (its free float 0 either
    way: a CONTROL on the anchor, discriminated by the battery's restart-anchor mutant)."""
    s = _S.model_copy(
        update={
            "duration_minutes": 5 * DAY,
            "percent_complete": 25.0,
            "remaining_duration_minutes": 18 * 60,
            "stop": NEXT_MON_1500,
            "resume": NEXT_MON_1500,
        }
    )
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    a = res.timing(1)
    assert a.free_float == 0
    assert (a.late_finish, a.total_float) == (2760, 360)
    # R-71 (ADR-0531, 2026-09-24): S's own late start is its record, 2,400 (was pinned at the
    # need, 2,760 — which A's late finish above still carries); S's float is its finish slack
    assert res.timing(2).late_start == 2400 and res.timing(2).total_float == 0


def test_an_absent_remaining_is_the_dropped_zero_and_keeps_the_plan_from_the_record() -> None:
    """CONTROL (green before and after): EVM1 UID 17's shape — 99 % complete, the MPXJ writer
    dropped its zero RemainingDuration, and Stop and Resume sit at its ACTUAL START. Its stored
    finish is ``actual_start + duration`` (ActualDuration == Duration on every such activity in
    the corpus), and reading the absent element as the percent-derived remainder (1 % of three days,
    14 minutes from the Resume) would finish it the morning it began — the battery's mutant."""
    s = _S.model_copy(
        update={
            "percent_complete": 99.0,
            "remaining_duration_minutes": None,
            "stop": NEXT_MON,
            "resume": NEXT_MON,
        }
    )
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (2400, 3840)
    assert 2 not in res.date_driven


def test_the_stored_remaining_is_read_not_the_percent_derived_remainder() -> None:
    """MS Project's RemainingDuration can disagree with the percent: S is 50 % complete yet stores
    the WHOLE three days (1,440) as remaining, resuming Tuesday 07-14 17:00 (minute 3,360): 3,360 +
    1,440 = 4,800. The percent's remainder (720) would read 4,080; pre-R-73 the plan read 3,840."""
    s = _S.model_copy(
        update={
            "remaining_duration_minutes": 3 * DAY,
            "stop": NEXT_TUE_1700,
            "resume": NEXT_TUE_1700,
        }
    )
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    assert res.timing(2).early_finish == 4800


def test_an_sra_override_is_the_remaining_and_runs_from_the_restart() -> None:
    """Every override producer builds an in-progress task's override from its REMAINING (the
    ADR-0309 rule): one day sampled runs from S's restart, 3,840 → 4,320 (Thursday 17:00). Pre-R-73
    the override was the span from the record: 2,400 → 2,880."""
    res = compute_cpm(_schedule(_A, _S, rels=(_link(1, 2),)), duration_overrides={2: DAY})
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (2400, 4320)


def test_a_recorded_reschedule_is_disclosed_only_where_it_moves_the_finish_past_the_plan() -> None:
    """Two recorded reschedules (Resume > Stop). The first moves S's remaining two days to the third
    Monday 08:00 (minute 4,800): 4,800 → 5,760, past the plan's 3,840 — ADR-0309's floor, disclosed
    on ``date_driven`` (a CONTROL: the floor disclosed it before R-73 too). The second records one
    day worked (stopped Monday 17:00) and the remaining FOUR HOURS (240) resuming Tuesday 13:00 —
    minute 2,880 + 240 = 3,120, after the lunch break — so the finish, 3,360, lies BEFORE the plan:
    MS Project's own remaining is what shortened it, and nothing is disclosed. Pre-R-73 the second
    read the plan's 3,840 (the contiguous floor, 3,180 + 240 = 3,420, did not bind)."""
    moved = _S.model_copy(update={"stop": NEXT_TUE_1700, "resume": THIRD_MON})
    res = compute_cpm(_schedule(_A, moved, rels=(_link(1, 2),)))
    assert res.timing(2).early_finish == 5760
    assert 2 in res.date_driven
    shortened = _S.model_copy(
        update={"remaining_duration_minutes": 240, "stop": NEXT_MON_1700, "resume": NEXT_TUE_1300}
    )
    res = compute_cpm(_schedule(_A, shortened, rels=(_link(1, 2),)))
    assert res.timing(2).early_finish == 3360
    assert 2 not in res.date_driven


def test_a_finish_to_finish_need_binds_the_remaining_of_an_in_sequence_activity() -> None:
    """P (two days: Monday 08:00 → Tuesday 17:00, minute 960) → S FINISH-TO-FINISH: S, three days,
    began at the project start (the whole-task FF bound, 960 - 1,440, lies before its record — in
    sequence), is 83 % done with four hours (240) left, stopped and resuming Monday 12:00 (minute
    240). The remaining may not end before P's finish: the need on the remaining is 960 - 240 = 720,
    later than the Resume, so the four hours run 720 → 960 and S finishes WITH P. Pre-R-73 the whole
    three days ran from the record: 1,440."""
    p = Task(unique_id=3, name="P (two days)", duration_minutes=2 * DAY)
    s = Task(
        unique_id=4,
        name="S (FF successor, four hours left)",
        duration_minutes=3 * DAY,
        percent_complete=83.0,
        remaining_duration_minutes=240,
        actual_start=MON,
        start=MON,
        stop=MON_1200,
        resume=MON_1200,
    )
    res = compute_cpm(_schedule(p, s, rels=(_link(3, 4, RelationshipType.FF),)))
    assert (res.timing(4).early_start, res.timing(4).early_finish) == (0, 960)
    assert res.timing(4).early_finish >= res.timing(3).early_finish


def test_a_source_recording_neither_resume_nor_stop_is_unchanged() -> None:
    """CONTROL (green before and after): a P6 export or a synthetic fixture records no restart; the
    placement stays ``actual_start + duration`` — the row's oracle is MS Project's, and a file that
    carries no restart cannot be read as one."""
    s = _S.model_copy(update={"stop": None, "resume": None})
    res = compute_cpm(_schedule(_A, s, rels=(_link(1, 2),)))
    assert (res.timing(2).early_start, res.timing(2).early_finish) == (2400, 3840)
