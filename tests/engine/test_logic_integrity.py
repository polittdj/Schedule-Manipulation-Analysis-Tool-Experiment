"""Logic-integrity engine tests — out-of-sequence progress and redundant logic.

Hand-verified synthetic networks. Both checks are parity-isolated (lightweight dataclasses, never
``MetricResult``) and need no CPM — out-of-sequence reads actuals, redundant logic reads the graph.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.metrics import logic_integrity
from schedule_forensics.engine.metrics.logic_integrity import compute_logic_integrity
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, dur_days: float = 1, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _rel(p: int, s: int, rtype: RelationshipType = RelationshipType.FS) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=rtype)


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or [])
    )


def _check(schedule: Schedule, key: str) -> logic_integrity.LogicCheck:
    by_key = {c.key: c for c in compute_logic_integrity(schedule).checks}
    return by_key[key]


# ── out-of-sequence ──────────────────────────────────────────────────────────────────────


def test_out_of_sequence_flags_successor_started_before_predecessor_finished() -> None:
    pred = _task(1, actual_start=MON, actual_finish=dt.datetime(2025, 1, 10, 8, 0))
    # successor started on the 8th — two days BEFORE the predecessor finished on the 10th
    succ = _task(2, actual_start=dt.datetime(2025, 1, 8, 8, 0))
    c = _check(_sched([pred, succ], [_rel(1, 2)]), "out_of_sequence")
    assert c.count == 1
    assert c.offenders == ("1→2",)
    assert c.population == 1


def test_in_sequence_progress_is_not_flagged() -> None:
    pred = _task(1, actual_start=MON, actual_finish=dt.datetime(2025, 1, 8, 8, 0))
    succ = _task(2, actual_start=dt.datetime(2025, 1, 9, 8, 0))  # started AFTER pred finished
    c = _check(_sched([pred, succ], [_rel(1, 2)]), "out_of_sequence")
    assert c.count == 0


def test_unstarted_successor_is_not_flagged() -> None:
    pred = _task(1, actual_start=MON)  # in progress, no finish
    succ = _task(2)  # not started
    c = _check(_sched([pred, succ], [_rel(1, 2)]), "out_of_sequence")
    assert c.count == 0


def test_successor_started_while_predecessor_unfinished_is_flagged() -> None:
    pred = _task(1, actual_start=MON)  # started, never finished
    succ = _task(2, actual_start=dt.datetime(2025, 1, 7, 8, 0))  # already started
    c = _check(_sched([pred, succ], [_rel(1, 2)]), "out_of_sequence")
    assert c.count == 1


def test_non_fs_links_are_excluded_from_out_of_sequence() -> None:
    pred = _task(1, actual_start=MON, actual_finish=dt.datetime(2025, 1, 10, 8, 0))
    succ = _task(2, actual_start=dt.datetime(2025, 1, 8, 8, 0))
    c = _check(_sched([pred, succ], [_rel(1, 2, RelationshipType.SS)]), "out_of_sequence")
    assert c.count == 0
    assert c.population == 0  # no FS links in the network


def test_summary_endpoints_excluded_from_out_of_sequence() -> None:
    pred = _task(1, is_summary=True, actual_finish=dt.datetime(2025, 1, 10, 8, 0))
    succ = _task(2, actual_start=dt.datetime(2025, 1, 8, 8, 0))
    c = _check(_sched([pred, succ], [_rel(1, 2)]), "out_of_sequence")
    assert c.count == 0
    assert c.population == 0


# ── redundant logic ──────────────────────────────────────────────────────────────────────


def test_redundant_link_over_a_chain_is_flagged() -> None:
    # 1→2→3 plus a direct 1→3 that the chain already implies
    sched = _sched([_task(1), _task(2), _task(3)], [_rel(1, 2), _rel(2, 3), _rel(1, 3)])
    c = _check(sched, "redundant_logic")
    assert c.count == 1
    assert c.offenders == ("1→3",)
    assert c.population == 3


def test_chain_without_shortcut_has_no_redundancy() -> None:
    sched = _sched([_task(1), _task(2), _task(3)], [_rel(1, 2), _rel(2, 3)])
    c = _check(sched, "redundant_logic")
    assert c.count == 0
    assert c.evaluated is True


def test_redundant_link_over_a_diamond_is_flagged() -> None:
    # 1→2→4, 1→3→4 (a diamond), plus a direct 1→4 implied by both legs
    sched = _sched(
        [_task(1), _task(2), _task(3), _task(4)],
        [_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4), _rel(1, 4)],
    )
    c = _check(sched, "redundant_logic")
    assert c.offenders == ("1→4",)


def test_parallel_independent_links_are_not_redundant() -> None:
    # a fan-out 1→2, 1→3, 1→4 with no path between the leaves is all necessary logic
    sched = _sched([_task(1), _task(2), _task(3), _task(4)], [_rel(1, 2), _rel(1, 3), _rel(1, 4)])
    c = _check(sched, "redundant_logic")
    assert c.count == 0


def test_redundant_skipped_on_oversize_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logic_integrity, "_REDUNDANT_MAX_TASKS", 2)
    sched = _sched([_task(1), _task(2), _task(3)], [_rel(1, 2), _rel(2, 3), _rel(1, 3)])
    c = _check(sched, "redundant_logic")
    assert c.evaluated is False
    assert c.count == 0
    assert "too large" in c.description


def test_redundant_skipped_on_cyclic_network(monkeypatch: pytest.MonkeyPatch) -> None:
    # raise the edge cap so the cycle (not size) is the reason it is skipped
    sched = _sched([_task(1), _task(2), _task(3)], [_rel(1, 2), _rel(2, 3), _rel(3, 1)])
    c = _check(sched, "redundant_logic")
    assert c.evaluated is False
    assert "cycle" in c.description


def test_long_chain_does_not_overflow_recursion() -> None:
    # a 1500-deep chain (well past Python's recursion limit) must close iteratively without error,
    # and the long-range shortcut 1→N is correctly flagged redundant
    n = 1500
    tasks = [_task(i) for i in range(1, n + 1)]
    rels = [_rel(i, i + 1) for i in range(1, n)]
    rels.append(_rel(1, n))
    c = _check(_sched(tasks, rels), "redundant_logic")
    assert c.count == 1
    assert c.offenders == (f"1→{n}",)
