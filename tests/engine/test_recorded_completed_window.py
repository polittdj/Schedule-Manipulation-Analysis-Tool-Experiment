"""R-55 / ADR-0476: a COMPLETED activity occupies exactly its RECORDED window.

ADR-0391 made a recorded ``actual_start`` a forward FLOOR and named the half it left open: a
completed activity's finish stayed ``start + duration``, so work that ran longer or shorter than
planned computed a finish the file itself contradicts. On ``Hard_File_updated3`` twenty-one
completed activities were scheduled PAST their recorded finish (worst +38 d) and on
``_24hr`` fifty were — and because a floor can only push work later, no amount of flooring can
fix an activity that finished EARLY.

The oracle is MS Project's own export, not our judgement: across six progressed goldens the
stored ``Finish`` equals ``ActualFinish`` on **2,289 of 2,289** completed activities and the
stored ``Start`` equals ``ActualStart`` on **2,601 of 2,601** started ones (measured 2026-09-08),
so pinning both ends of a completed activity reproduces the reference tool by construction.

Work still IN PROGRESS deliberately keeps the floor: its start is a record but its finish is a
forecast, and pinning an out-of-sequence in-progress start pulls the network EARLIER — measured
at 136 days on ``Large_Test_File`` UID 1489 (95 % complete) when the pin was applied to every
started task. Understating a slip is the one direction Law 2 forbids.

Red first (pristine engine, 2026-09-08) — completed activities scheduled PAST their recorded
finish: updated2 13, updated3 21, updated3_24hr 50, Large_Test_File 11; landing ON the record:
20 / 20 / 35 / 665. After: 0 / 0 / 0 / 0 past, 32 / 40 / 88 / 680 on it.
"""

from __future__ import annotations

import datetime as dt
import gzip
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import (
    compute_cpm,
    datetime_to_offset,
    is_recorded_complete,
    offset_to_datetime,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)  # the project start, a Monday
DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _pair(*, planned_days: int, ran_days: int, complete: float = 100.0) -> Schedule:
    """A → B, where A was PLANNED for ``planned_days`` and actually ran ``ran_days``.

    A starts on the project start, so no floor is in play: only the recorded FINISH can put A's
    finish anywhere other than ``start + planned``.
    """
    finish = MON + dt.timedelta(days=ran_days * 7 // 5 or ran_days)
    a = Task(
        unique_id=1,
        name="A",
        duration_minutes=planned_days * DAY,
        percent_complete=complete,
        actual_start=MON,
        start=MON,
        actual_finish=finish if complete >= 100.0 else None,
        finish=finish if complete >= 100.0 else None,
    )
    b = Task(unique_id=2, name="B", duration_minutes=DAY)
    return Schedule(
        name="s",
        project_start=MON,
        tasks=(a, b),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _out_of_sequence(
    *, percent: float, actual_finish: dt.datetime | None, calendar_uid: int | None = None
) -> Schedule:
    """P (unstarted, 5 d) → Q, where Q claims it began on the PROJECT START — two working weeks
    before P can hand off. Q's treatment is the whole question: a completed Q is a record and is
    pinned back to it; a Q still running keeps the logic date, because pinning an out-of-sequence
    in-progress start is what pulled Large_Test_File UID 1489 back 136 days.

    No committed fixture expresses a part-complete activity carrying an ``ActualFinish``
    (measured: 0 across every MSPDI golden), so this rig is the only oracle for that branch.
    """
    p = Task(unique_id=1, name="P", duration_minutes=5 * DAY)
    q = Task(
        unique_id=2,
        name="Q",
        duration_minutes=2 * DAY,
        percent_complete=percent,
        actual_start=MON,
        start=MON,
        actual_finish=actual_finish,
        calendar_uid=calendar_uid,
    )
    cals = (
        (
            Calendar(
                uid=7,
                name="24x7",
                working_minutes_per_day=1440,
                work_weekdays=(0, 1, 2, 3, 4, 5, 6),
            ),
        )
        if calendar_uid is not None
        else ()
    )
    return Schedule(
        name="oos",
        project_start=MON,
        tasks=(p, q),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
        calendars=cals,
    )


def test_a_completed_activity_that_ran_long_finishes_when_it_finished() -> None:
    s = _pair(planned_days=5, ran_days=12)
    r = compute_cpm(s)
    recorded = datetime_to_offset(MON, s.task_by_id(1).actual_finish, s.calendar)
    assert r.timings[1].early_finish == recorded, "the record, not start + duration"
    assert r.timings[1].early_finish > 5 * DAY  # what the pristine engine returned
    assert 1 in r.actual_finish_driven


def test_a_completed_activity_that_ran_short_finishes_when_it_finished() -> None:
    """The case a FLOOR can never reach: the recorded finish is EARLIER than start + duration."""
    s = _pair(planned_days=10, ran_days=2)
    r = compute_cpm(s)
    recorded = datetime_to_offset(MON, s.task_by_id(1).actual_finish, s.calendar)
    assert r.timings[1].early_finish == recorded
    assert r.timings[1].early_finish < 10 * DAY  # what the pristine engine returned
    assert 1 in r.actual_finish_driven


def test_the_successor_starts_from_the_recorded_handoff() -> None:
    """Not a tautology: the assertion is against the RECORD, so it fails on any engine that
    hands B a computed predecessor finish (the pristine engine gave B ``5 * DAY``)."""
    s = _pair(planned_days=5, ran_days=12)
    r = compute_cpm(s)
    recorded = datetime_to_offset(MON, s.task_by_id(1).actual_finish, s.calendar)
    assert r.timings[2].early_start == recorded
    assert r.timings[2].early_finish == recorded + DAY


def test_work_still_in_progress_keeps_the_floor_even_carrying_both_actuals() -> None:
    """The UID-1489 guard. Q reports 40 % yet carries an ``ActualFinish`` as well as an
    ``ActualStart`` — the completeness test is what separates it from a record, and without it
    Q is pinned back two working weeks and the network with it."""
    s = _out_of_sequence(percent=40.0, actual_finish=MON + dt.timedelta(days=1))
    r = compute_cpm(s)
    assert r.timings[1].early_finish == 5 * DAY
    assert r.timings[2].early_start == 5 * DAY, (
        "an out-of-sequence in-progress start must not pull back"
    )
    assert r.timings[2].early_finish == 7 * DAY
    assert 2 not in r.actual_finish_driven and 2 not in r.actual_start_driven
    assert r.actual_finish_driven == ()


def test_a_completed_activity_out_of_sequence_is_pinned_back_to_its_record() -> None:
    """The other half of the same rig: once Q is COMPLETE its window is history, so it sits
    where it happened even though logic would place it later."""
    s = _out_of_sequence(percent=100.0, actual_finish=MON + dt.timedelta(days=1))
    r = compute_cpm(s)
    assert r.timings[2].early_start == 0, "a completed activity begins when it began"
    assert r.timings[2].early_finish == datetime_to_offset(
        MON, s.task_by_id(2).actual_finish, s.calendar
    )
    assert 2 in r.actual_finish_driven


def test_a_completed_activity_needs_all_three_records_before_it_is_pinned() -> None:
    """100 % with no ``ActualFinish`` is a claim, not a record — it keeps the computed finish."""
    s = _pair(planned_days=5, ran_days=12)
    a = s.task_by_id(1).model_copy(update={"actual_finish": None})
    s = s.model_copy(update={"tasks": (a, s.task_by_id(2))})
    assert not is_recorded_complete(s.task_by_id(1)), "100 % plus a start is not a record"
    r = compute_cpm(s)
    assert r.timings[1].early_finish == 5 * DAY
    assert r.actual_finish_driven == ()


def test_the_recorded_finish_is_disclosed_apart_from_unsupported_dates() -> None:
    """A transcribed measurement is evidence, not a date logic cannot support: merging it into
    ``date_driven`` would emit a false manipulation signal on every progressed schedule."""
    s = _pair(planned_days=5, ran_days=12)
    r = compute_cpm(s)
    assert 1 in r.actual_finish_driven
    assert 1 not in r.date_driven
    assert not set(r.actual_finish_driven) & set(r.date_driven)


def test_an_own_calendar_completed_activity_is_pinned_too() -> None:
    """The execution-plan branch carries the same rule as the project-axis fast path."""
    s = _pair(planned_days=5, ran_days=12)
    a = s.task_by_id(1).model_copy(update={"calendar_uid": 7})
    s = s.model_copy(
        update={
            "tasks": (a, s.task_by_id(2)),
            "calendars": (
                Calendar(
                    uid=7,
                    name="24x7",
                    working_minutes_per_day=1440,
                    work_weekdays=(0, 1, 2, 3, 4, 5, 6),
                ),
            ),
        }
    )
    r = compute_cpm(s)
    assert r.timings[1].early_finish_wall == s.task_by_id(1).actual_finish
    assert 1 in r.actual_finish_driven
    # the backward pass must retreat by the RECORDED span too: retreating by the plan's legs
    # makes the start slack and the finish slack disagree and sinks finished work into
    # spurious negative float (the fast path's failure mode, on the task's own calendar)
    assert r.timings[1].total_float >= 0, r.timings[1]
    assert r.timings[1].late_finish - r.timings[1].early_finish == (
        r.timings[1].late_start - r.timings[1].early_start
    ), "a recorded window's start slack and finish slack must agree"


def test_an_own_calendar_completed_activity_out_of_sequence_is_pinned_too() -> None:
    """The execution-plan branch must PIN, not floor: on its own 24x7 calendar Q still belongs
    at the instant it began, not at its predecessor's handoff."""
    s = _out_of_sequence(percent=100.0, actual_finish=MON + dt.timedelta(days=1), calendar_uid=7)
    r = compute_cpm(s)
    assert r.timings[2].early_start_wall == MON
    assert r.timings[2].early_finish_wall == s.task_by_id(2).actual_finish
    assert 2 in r.actual_finish_driven


def test_contradictory_records_never_produce_a_finish_before_the_start() -> None:
    """Forensic input is not clean input. An activity whose recorded finish PRECEDES its
    recorded start must not be emitted as a negative-duration window; the record is ordered at
    the start. No committed fixture carries inverted actuals (measured: 0), so this is the only
    oracle for the guard."""
    s = _pair(planned_days=5, ran_days=12)
    began, ended = MON + dt.timedelta(days=28), s.task_by_id(1).actual_finish
    assert ended < began, "the fixture must actually invert the record"
    a = s.task_by_id(1).model_copy(update={"actual_start": began, "start": began})
    s = s.model_copy(update={"tasks": (a, s.task_by_id(2))})
    r = compute_cpm(s)
    assert r.timings[1].early_start == datetime_to_offset(MON, began, s.calendar)
    assert r.timings[1].early_finish == r.timings[1].early_start, (
        "ordered at the start, never before it"
    )
    assert r.timings[2].early_start >= r.timings[1].early_finish


def test_a_recorded_reschedule_of_remaining_work_cannot_move_a_completed_finish() -> None:
    """ADR-0309's resume floor is a rule about REMAINING work. An activity reported complete has
    none, so a contradictory ``Resume``/``Stop`` pair may not push its finish off the record.
    No committed fixture pairs a completed activity with ``resume > stop`` (measured: 0)."""
    s = _pair(planned_days=5, ran_days=12)
    recorded = s.task_by_id(1).actual_finish
    a = s.task_by_id(1).model_copy(
        update={
            "stop": MON + dt.timedelta(days=3),
            "resume": MON + dt.timedelta(days=30),
            "remaining_duration_minutes": 5 * DAY,
        }
    )
    s = s.model_copy(update={"tasks": (a, s.task_by_id(2))})
    r = compute_cpm(s)
    assert r.timings[1].early_finish == datetime_to_offset(MON, recorded, s.calendar)
    assert 1 not in r.date_driven


# --- the corpus: MS Project's own stored dates -------------------------------------------------

_CORPUS = [
    # rel, completed activities, landing ON the recorded finish (floor)
    ("fuse_hardfile/Hard_File_updated2.mspdi.xml.gz", 34, 32),
    ("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz", 42, 40),
    ("fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz", 91, 88),
    ("fuse_ltf/Large_Test_File.mspdi.xml.gz", 699, 680),
]


@cache
def _load(rel: str) -> tuple[Schedule, object]:
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    sch = parse_mspdi_text(text)
    return sch, compute_cpm(sch)


@pytest.mark.parametrize(("rel", "n_completed", "on_record_floor"), _CORPUS)
def test_no_completed_activity_is_scheduled_past_the_date_it_finished(
    rel: str, n_completed: int, on_record_floor: int
) -> None:
    sch, res = _load(rel)
    completed = [
        t
        for t in sch.tasks
        if not t.is_summary
        and t.is_active
        and t.percent_complete >= 100.0
        and t.actual_start is not None
        and t.actual_finish is not None
    ]
    assert len(completed) == n_completed
    past, on_record = [], 0
    for t in completed:
        tm = res.timing(t.unique_id)
        ef = tm.early_finish_wall or offset_to_datetime(
            sch.project_start, tm.early_finish, sch.calendar
        )
        if ef.date() > t.actual_finish.date():
            past.append((t.unique_id, (ef.date() - t.actual_finish.date()).days))
        elif ef.date() == t.actual_finish.date():
            on_record += 1
    assert past == [], f"{len(past)} completed activities scheduled past their record: {past[:5]}"
    assert on_record >= on_record_floor, (
        f"{on_record} landed on the record, floor {on_record_floor}"
    )


@pytest.mark.parametrize(
    "rel",
    [
        "fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
        "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
        "fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz",
    ],
)
def test_the_hard_file_family_never_reads_later_than_ms_project(rel: str) -> None:
    """Pristine: 13 / 31 / 68 activities finished LATER than the stored date. The remaining
    disagreement on these files is entirely engine-EARLY — UID 403's leveling split (R-60) and
    the day-boundary milestones; R-56's material / cost spans are read since ADR-0487."""
    sch, res = _load(rel)
    late = []
    for t in sch.tasks:
        if t.is_summary or not t.is_active or t.finish is None:
            continue
        tm = res.timing(t.unique_id)
        ef = tm.early_finish_wall or offset_to_datetime(
            sch.project_start, tm.early_finish, sch.calendar
        )
        if ef.date() > t.finish.date():
            late.append((t.unique_id, (ef.date() - t.finish.date()).days))
    assert late == [], f"{len(late)} activities read later than MS Project: {late[:5]}"


def test_dcma12_never_injects_its_delay_into_work_that_has_already_finished() -> None:
    """A recorded-complete activity is immovable, so DCMA-12 must not choose it as the activity
    it delays: the finish could not move, and the check would report a broken critical path for a
    reason that has nothing to do with logic continuity.

    Project2 is the corpus case and the reason the filter is ``is_recorded_complete`` rather than
    ``percent_complete >= 100``: its lowest-UID critical candidate, UID 26, IS recorded-complete,
    so the target moves to UID 29 while the verdict stays PASS. Red-first: with the filter removed
    the target is UID 26 again.
    """
    from schedule_forensics.engine.cpm import is_recorded_complete
    from schedule_forensics.engine.metrics._common import CheckStatus
    from schedule_forensics.engine.metrics.dcma14 import compute_dcma14

    sch, res = _load("project2_5/Project2.mspdi.xml")
    by = {t.unique_id: t for t in sch.tasks}
    candidates = [
        tid
        for tid in res.critical_path
        if tid in by
        and by[tid].duration_minutes > 0
        and not by[tid].is_summary
        and by[tid].is_active
    ]
    assert min(candidates) == 26, "the corpus premise: UID 26 is the lowest-UID critical candidate"
    assert is_recorded_complete(by[26]), "and it is recorded-complete, so it cannot absorb a delay"
    movable = [tid for tid in candidates if not is_recorded_complete(by[tid])]
    assert min(movable) == 29, "the target the check must use instead"
    assert len(candidates) - len(movable) == 2, "exactly two of the 43 candidates are immovable"
    assert compute_dcma14(sch, res)["DCMA12"].status is CheckStatus.PASS
