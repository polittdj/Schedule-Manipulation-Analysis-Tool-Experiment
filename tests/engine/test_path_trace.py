"""Path-trace tests — ancestor reachability to a focus UID and deterministic ordering."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.path_trace import (
    ancestors_of,
    descendants_of,
    subschedule_to_target,
    topo_order,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def _sched(
    task_ids: list[int], edges: list[tuple[int, int]], summaries: tuple[int, ...] = ()
) -> Schedule:
    tasks = [
        Task(unique_id=u, name=f"T{u}", duration_minutes=480, is_summary=u in summaries)
        for u in task_ids
    ]
    rels = [Relationship(predecessor_id=p, successor_id=s) for p, s in edges]
    return Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def test_ancestors_transitive() -> None:
    # 1 -> 2 -> 4 ; 3 -> 4 ; 5 isolated. Ancestors of 4 = {1, 2, 3}.
    s = _sched([1, 2, 3, 4, 5], [(1, 2), (2, 4), (3, 4)])
    assert ancestors_of(s, 4) == frozenset({1, 2, 3})


def test_ancestors_excludes_target_and_descendants() -> None:
    s = _sched([1, 2, 3], [(1, 2), (2, 3)])
    assert ancestors_of(s, 1) == frozenset()  # 1 has no predecessor
    assert ancestors_of(s, 2) == frozenset({1})


def test_ancestors_diamond_dedups_shared_predecessor() -> None:
    # 1 -> {2, 3} -> 4: task 1 is reached via both 2 and 3 but counted once.
    s = _sched([1, 2, 3, 4], [(1, 2), (1, 3), (2, 4), (3, 4)])
    assert ancestors_of(s, 4) == frozenset({1, 2, 3})


def test_ancestors_ignores_links_touching_summary() -> None:
    # A link from a summary task (3) is not part of the activity network.
    s = _sched([1, 2, 3], [(1, 2), (3, 2)], summaries=(3,))
    assert ancestors_of(s, 2) == frozenset({1})


def test_ancestors_unknown_target_raises() -> None:
    s = _sched([1, 2], [(1, 2)])
    with pytest.raises(KeyError):
        ancestors_of(s, 999)


def test_ancestors_target_is_summary_raises() -> None:
    s = _sched([1, 2], [(1, 2)], summaries=(2,))
    with pytest.raises(KeyError):
        ancestors_of(s, 2)


def test_descendants_transitive_and_excludes_source() -> None:
    # 1 -> 2 -> 4 ; 3 -> 4 ; 5 isolated. Descendants of 1 = {2, 4} (4 reached via 2).
    s = _sched([1, 2, 3, 4, 5], [(1, 2), (2, 4), (3, 4)])
    assert descendants_of(s, 1) == frozenset({2, 4})
    assert descendants_of(s, 4) == frozenset()  # 4 is a sink


def test_descendants_diamond_dedups_shared_successor() -> None:
    s = _sched([1, 2, 3, 4], [(1, 2), (1, 3), (2, 4), (3, 4)])
    assert descendants_of(s, 1) == frozenset({2, 3, 4})


def test_descendants_ignores_links_touching_summary() -> None:
    s = _sched([1, 2, 3], [(1, 2), (1, 3)], summaries=(3,))
    assert descendants_of(s, 1) == frozenset({2})


def test_descendants_unknown_source_raises() -> None:
    s = _sched([1, 2], [(1, 2)])
    with pytest.raises(KeyError):
        descendants_of(s, 999)


def test_topo_order_deterministic() -> None:
    s = _sched([1, 2, 3, 4], [(1, 2), (1, 3), (2, 4), (3, 4)])
    assert topo_order(s, {1, 2, 3, 4}) == (1, 2, 3, 4)  # UID tie-break


def test_topo_order_subset_only() -> None:
    s = _sched([1, 2, 3, 4], [(1, 2), (2, 3), (3, 4)])
    assert topo_order(s, {2, 4, 3}) == (2, 3, 4)


def test_topo_order_cycle_raises() -> None:
    s = _sched([1, 2], [(1, 2), (2, 1)])
    with pytest.raises(ValueError, match="cycle"):
        topo_order(s, {1, 2})


def test_subschedule_to_target_keeps_target_and_its_drivers() -> None:
    # 1 -> 2 -> 4 ; 3 -> 4 ; 4 -> 6 (successor) ; 5 isolated. Endpoint 4 keeps {1,2,3,4}.
    s = _sched([1, 2, 3, 4, 5, 6], [(1, 2), (2, 4), (3, 4), (4, 6)])
    sub = subschedule_to_target(s, 4)
    assert {t.unique_id for t in sub.tasks} == {1, 2, 3, 4}  # drivers + target; no successor/orphan
    # only relationships among the kept set survive (the 4->6 successor edge is dropped)
    assert {(r.predecessor_id, r.successor_id) for r in sub.relationships} == {
        (1, 2),
        (2, 4),
        (3, 4),
    }
    assert sub.name == s.name and sub.project_start == s.project_start  # frame preserved


def test_subschedule_to_target_isolated_target_is_just_itself() -> None:
    s = _sched([1, 2, 3], [(1, 2)])
    sub = subschedule_to_target(s, 3)
    assert {t.unique_id for t in sub.tasks} == {3}
    assert sub.relationships == ()


def test_subschedule_to_target_unknown_target_raises() -> None:
    s = _sched([1, 2], [(1, 2)])
    with pytest.raises(KeyError):
        subschedule_to_target(s, 999)
