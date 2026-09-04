"""CPM-01 (WP6, ADR-0463): a resume-floored finish reaches total float.

ADR-0309 floors an in-progress task's early finish at ``Resume + remaining`` when MS Project itself
rescheduled the remaining work (``Resume > Stop``). The project-axis backward pass derived the late
start from the late finish minus the STORED duration and total float was ``LS - ES`` — so the
floor's gap never reached the float: a task whose floored finish IS the network finish read as
10 working days of float and non-critical (golden EVM2, UID 20 — MS Project's own Critical flag is
Yes). Total float is the smaller of start slack (``LS - ES``) and finish slack (``LF - EF``),
MS Project's own rule: byte-identical for a contiguous task; it closes the gap for a floored one.
The execution-calendar branch already measured its slack from the floored finish; this pins both.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480
MON = dt.datetime(2026, 3, 2, 8, 0)
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _floored_chain() -> Schedule:
    """P (5d) -> X (5d, 80 %, stopped after 4d, remaining 1d resumed two weeks later) -> S (2d).

    X's logic finish is the end of day 10; its resume floor puts the finish at the end of day 19
    (a 9-day gap), and S runs from there — so X's floored finish drives the network finish."""
    p = Task(unique_id=1, name="P", duration_minutes=5 * DAY)
    x = Task(
        unique_id=2,
        name="X",
        duration_minutes=5 * DAY,
        percent_complete=80.0,
        remaining_duration_minutes=1 * DAY,
        actual_start=dt.datetime(2026, 3, 9, 8, 0),
        stop=dt.datetime(2026, 3, 12, 17, 0),
        resume=dt.datetime(2026, 3, 26, 8, 0),
    )
    s = Task(unique_id=3, name="S", duration_minutes=2 * DAY)
    return Schedule(
        name="floored",
        project_start=MON,
        status_date=dt.datetime(2026, 3, 16, 8, 0),
        tasks=(p, x, s),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def test_premise_the_resume_floor_moves_the_finish_past_the_logic_finish() -> None:
    cpm = compute_cpm(_floored_chain())
    x = cpm.timings[2]
    assert x.early_start == 5 * DAY
    assert x.early_finish == 19 * DAY  # resume (day 19 start) + 1 remaining day, not day 10
    assert cpm.project_finish == 21 * DAY  # S runs after the floored finish


def test_floored_task_total_float_is_its_finish_slack_and_it_is_critical() -> None:
    cpm = compute_cpm(_floored_chain())
    x = cpm.timings[2]
    assert x.late_finish == x.early_finish  # the floored finish IS the network's driver
    assert x.total_float == x.late_finish - x.early_finish == 0
    assert x.is_critical is True
    assert 2 in cpm.critical_path and 3 in cpm.critical_path


def test_the_predecessor_keeps_its_start_slack_against_the_floored_successor() -> None:
    """P can slip until X's late start without moving X's floored finish — 9 working days."""
    cpm = compute_cpm(_floored_chain())
    p = cpm.timings[1]
    assert p.total_float == 9 * DAY
    assert p.is_critical is False


def test_total_float_never_exceeds_finish_slack_on_the_project_axis() -> None:
    """For every project-axis task, ``LF - EF`` bounds the float (a floored task is the only way
    the two differ; a violated pin only lowers the float further)."""
    schedules = [_floored_chain()] + [
        parse_mspdi(GOLDEN / rel)
        for rel in (
            "project2_5/Project2.mspdi.xml",
            "project2_5/Project5.mspdi.xml",
            "evm/EVM2.mspdi.xml",
        )
    ]
    for sch in schedules:
        cpm = compute_cpm(sch)
        for uid, tm in cpm.timings.items():
            if tm.early_start_wall is not None:  # execution-calendar tasks carry their own slack
                continue
            finish_slack = tm.late_finish - tm.early_finish
            assert tm.total_float <= finish_slack, (sch.name, uid, tm.total_float, finish_slack)


def test_golden_evm2_uid20_is_critical_like_ms_project_says() -> None:
    """The Law-2 oracle: MS Project stored Critical = Yes on the resume-floored UID 20, whose
    floored finish the engine already reproduces to the day (ADR-0309)."""
    sch = parse_mspdi(GOLDEN / "evm" / "EVM2.mspdi.xml")
    task = sch.tasks_by_id[20]
    assert task.resume is not None and task.stop is not None and task.resume > task.stop
    assert task.stored_is_critical is True
    cpm = compute_cpm(sch)
    tm = cpm.timings[20]
    assert task.finish is not None
    assert offset_to_datetime(sch.project_start, tm.early_finish, sch.calendar).date() == (
        task.finish.date()
    )
    assert tm.early_finish - (tm.early_start + task.duration_minutes) == 10 * DAY  # the gap
    assert tm.total_float == 0
    assert tm.is_critical is True
    assert 20 in cpm.critical_path
