"""Critical-path evolution tests — entered/left/stayed, duration changes, finish move,
golden pins (M18 item 7, ADR-0044)."""

from __future__ import annotations

import datetime as dt
from itertools import pairwise

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.path_evolution import (
    _classify_entered,
    _classify_left,
    _links_touching,
    compute_path_evolution,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _chain(uids_durs: list[tuple[int, int]]) -> Schedule:
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=d * DAY) for u, d in uids_durs]
    rels = [
        Relationship(predecessor_id=a, successor_id=b) for (a, _), (b, _) in pairwise(uids_durs)
    ]
    return Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def _ev(schedules: list[Schedule]):
    cpms = [compute_cpm(s) for s in schedules]
    return compute_path_evolution(schedules, cpms)


def test_first_version_has_no_change_fields() -> None:
    ev = _ev([_chain([(1, 2), (2, 3)])])
    s = ev.snapshots[0]
    assert s.entered == () and s.left == () and s.stayed == ()
    assert s.finish_delta_days is None
    assert set(s.critical) == {1, 2}  # a single chain is all-critical


def test_entered_and_stayed_when_path_extends() -> None:
    v1 = _chain([(1, 2), (2, 3)])  # critical {1,2}
    v2 = _chain([(1, 2), (2, 3), (3, 1)])  # critical {1,2,3}
    ev = _ev([v1, v2])
    s = ev.snapshots[1]
    assert set(s.critical) == {1, 2, 3}
    assert s.entered == (3,)
    assert set(s.stayed) == {1, 2}
    assert s.left == ()
    assert s.finish_delta_days > 0  # extending the path pushes the finish later


def test_left_when_a_critical_task_is_removed() -> None:
    v1 = _chain([(1, 2), (2, 3), (3, 1)])  # critical {1,2,3}
    v2 = _chain([(1, 2), (2, 3)])  # task 3 gone -> critical {1,2}
    ev = _ev([v1, v2])
    s = ev.snapshots[1]
    assert set(s.critical) == {1, 2}
    assert s.left == (3,)  # was critical, now absent
    assert s.entered == ()
    assert s.finish_delta_days < 0  # removing a critical task pulls the finish in


def test_duration_change_on_path_is_flagged() -> None:
    v1 = _chain([(1, 2), (2, 3)])
    v2 = _chain([(1, 2), (2, 5)])  # task 2's duration changed, still critical
    ev = _ev([v1, v2])
    s = ev.snapshots[1]
    assert s.duration_changed == (2,)
    assert s.finish_delta_days > 0  # a longer critical task pushes the finish later


def test_empty_and_mismatched_inputs_raise() -> None:
    with pytest.raises(ValueError, match="at least one"):
        compute_path_evolution([], [])
    sch = _chain([(1, 1)])
    with pytest.raises(ValueError, match="parallel"):
        compute_path_evolution([sch, sch], [compute_cpm(sch)])


def test_golden_pins(golden_project2: Schedule, golden_project5: Schedule) -> None:
    ev = _ev([golden_project2, golden_project5])
    first, second = ev.snapshots
    assert first.finish_delta_days is None
    assert len(first.critical) == 43 and len(second.critical) == 37
    # P2 -> P5 slips 99 calendar days (the known Net Finish Impact)
    assert second.finish_delta_days == 99
    assert len(second.left) == 6 and len(second.stayed) == 37 and second.entered == ()
    # clean golden pair: no shortened-on-path, no removed logic
    assert second.shortened_on_path == () and second.removed_logic_count == 0
    # M18 follow-up: every 'left' activity is attributed a reason (no entered on this pair)
    assert first.entered_changes == () and first.left_changes == ()
    assert {c.uid for c in second.left_changes} == set(second.left)
    assert {c.reason for c in second.left_changes} <= {"completed", "gained_float"}


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or ())
    )


def test_entered_attribution_reasons() -> None:
    """Each 'entered the path' reason code (M18 follow-up): new / duration / constraint /
    logic / slack-consumed."""

    def reason(uid: int, prior: Schedule, cur: Schedule) -> str:
        return _classify_entered(
            uid, cur, prior, _links_touching(cur), _links_touching(prior)
        ).reason

    a = Task(unique_id=1, name="A", duration_minutes=DAY)
    # NEW — the activity did not exist in the prior version
    assert (
        reason(9, _sched([a]), _sched([a, Task(unique_id=9, name="N", duration_minutes=DAY)]))
        == "new"
    )
    # DURATION increased
    assert (
        reason(
            2,
            _sched([Task(unique_id=2, name="B", duration_minutes=DAY)]),
            _sched([Task(unique_id=2, name="B", duration_minutes=3 * DAY)]),
        )
        == "duration_up"
    )
    # CONSTRAINT — a hard constraint was added
    assert (
        reason(
            3,
            _sched([Task(unique_id=3, name="C", duration_minutes=DAY)]),
            _sched(
                [
                    Task(
                        unique_id=3,
                        name="C",
                        duration_minutes=DAY,
                        constraint_type=ConstraintType.MFO,
                        constraint_date=MON,
                    )
                ]
            ),
        )
        == "constraint"
    )
    # LOGIC — a link was added on this activity (duration unchanged)
    d = Task(unique_id=4, name="D", duration_minutes=DAY)
    e = Task(unique_id=5, name="E", duration_minutes=DAY)
    assert (
        reason(5, _sched([d, e]), _sched([d, e], [Relationship(predecessor_id=4, successor_id=5)]))
        == "logic_added"
    )
    # SLACK CONSUMED — nothing about the activity changed (a slip elsewhere)
    assert (
        reason(
            6,
            _sched([Task(unique_id=6, name="F", duration_minutes=DAY)]),
            _sched([Task(unique_id=6, name="F", duration_minutes=DAY)]),
        )
        == "slack_consumed"
    )


def test_left_attribution_reasons() -> None:
    """Each 'left the path' reason code: removed / completed / duration / logic / gained-float."""

    def reason(uid: int, prior: Schedule, cur: Schedule) -> str:
        return _classify_left(uid, cur, prior, _links_touching(cur), _links_touching(prior)).reason

    # REMOVED — absent from the current version
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
            _sched([Task(unique_id=2, name="Z", duration_minutes=DAY)]),
        )
        == "removed"
    )
    # COMPLETED since the prior version
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
            _sched(
                [
                    Task(
                        unique_id=1,
                        name="A",
                        duration_minutes=DAY,
                        percent_complete=100.0,
                        actual_start=MON,
                        actual_finish=MON,
                    )
                ]
            ),
        )
        == "completed"
    )
    # DURATION shortened
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=3 * DAY)]),
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
        )
        == "duration_down"
    )
    # LOGIC removed from this activity
    p, q = (
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
    )
    assert (
        reason(2, _sched([p, q], [Relationship(predecessor_id=1, successor_id=2)]), _sched([p, q]))
        == "logic_removed"
    )
    # GAINED FLOAT — nothing about the activity changed
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
        )
        == "gained_float"
    )
