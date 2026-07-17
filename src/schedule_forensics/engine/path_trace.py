"""Logic-path tracing to a target (focus) UniqueID.

Pure graph operations over a schedule's logic network, keyed by UniqueID: which
activities drive a chosen focus task, and a deterministic topological order over an
induced sub-network. The numeric driving-slack lives in :mod:`.driving_slack`; this
module answers "which tasks, in what order".
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from schedule_forensics.model.schedule import Schedule


def _scheduled_ids(schedule: Schedule) -> set[int]:
    """UniqueIDs of the real activities in the CPM network — the same population the solver uses.

    Excludes summary rollups AND inactive tasks (``is_active=False``), mirroring
    ``cpm._scheduled_tasks`` and ``driving_slack.date_basis`` (ADR-0128: MS Project / Acumen drop
    inactive tasks from the network). Without the ``is_active`` guard, ancestors_of/descendants_of
    traversed THROUGH inactive tasks, producing a driving path/slack SSI would not — a Law-2 parity
    break — or a KeyError on an undated inactive task (audit ADR-0250)."""
    return {t.unique_id for t in schedule.tasks if not t.is_summary and t.is_active}


def ancestors_of(schedule: Schedule, target_uid: int) -> frozenset[int]:
    """Every scheduled task with a directed logic path **to** ``target_uid``.

    These are exactly the activities that can drive the focus task (its predecessors,
    transitively). The target itself is **excluded**. Raises ``KeyError`` if
    ``target_uid`` is not a scheduled (non-summary) task.
    """
    scheduled = _scheduled_ids(schedule)
    if target_uid not in scheduled:
        raise KeyError(target_uid)
    incoming: dict[int, list[int]] = {uid: [] for uid in scheduled}
    for rel in schedule.relationships:
        if rel.predecessor_id in scheduled and rel.successor_id in scheduled:
            incoming[rel.successor_id].append(rel.predecessor_id)
    seen: set[int] = set()
    stack = [target_uid]
    while stack:
        node = stack.pop()
        for pred in incoming[node]:
            if pred not in seen:
                seen.add(pred)
                stack.append(pred)
    return frozenset(seen)


def subschedule_to_target(schedule: Schedule, target_uid: int) -> Schedule:
    """``schedule`` restricted to ``target_uid`` and every activity that drives it.

    The kept population is :func:`ancestors_of` (the target's transitive predecessors) plus
    the target itself; relationships are kept only among the kept tasks, and the project frame
    (name, dates, status date, calendar, custom-field labels) is preserved — so every existing
    engine analysis runs over the sub-network unchanged, treating the target as the schedule's
    endpoint. Mirrors :func:`schedule_forensics.engine.grouping.filter_schedule`. Raises
    ``KeyError`` if ``target_uid`` is not a scheduled (non-summary) task.
    """
    kept = set(ancestors_of(schedule, target_uid))
    kept.add(target_uid)
    tasks = tuple(t for t in schedule.tasks if t.unique_id in kept)
    rels = tuple(
        r for r in schedule.relationships if r.predecessor_id in kept and r.successor_id in kept
    )
    return schedule.model_copy(update={"tasks": tasks, "relationships": rels})


def descendants_of(schedule: Schedule, source_uid: int) -> frozenset[int]:
    """Every scheduled task with a directed logic path **from** ``source_uid``.

    These are the activities ``source_uid`` can drive (its successors, transitively) — the
    mirror of :func:`ancestors_of`. The source itself is **excluded**. Raises ``KeyError``
    if ``source_uid`` is not a scheduled (non-summary) task.
    """
    scheduled = _scheduled_ids(schedule)
    if source_uid not in scheduled:
        raise KeyError(source_uid)
    outgoing: dict[int, list[int]] = {uid: [] for uid in scheduled}
    for rel in schedule.relationships:
        if rel.predecessor_id in scheduled and rel.successor_id in scheduled:
            outgoing[rel.predecessor_id].append(rel.successor_id)
    seen: set[int] = set()
    stack = [source_uid]
    while stack:
        node = stack.pop()
        for succ in outgoing[node]:
            if succ not in seen:
                seen.add(succ)
                stack.append(succ)
    return frozenset(seen)


def topo_order(schedule: Schedule, uids: Iterable[int]) -> tuple[int, ...]:
    """Topological order of the sub-network induced by ``uids`` (predecessor before
    successor), ties broken by ascending UniqueID for determinism. Raises
    ``ValueError`` on a cycle within the subset.
    """
    nodes = set(uids)
    successors: dict[int, list[int]] = {uid: [] for uid in nodes}
    indegree: dict[int, int] = dict.fromkeys(nodes, 0)
    for rel in schedule.relationships:
        if rel.predecessor_id in nodes and rel.successor_id in nodes:
            successors[rel.predecessor_id].append(rel.successor_id)
            indegree[rel.successor_id] += 1
    queue: deque[int] = deque(sorted(uid for uid in nodes if indegree[uid] == 0))
    order: list[int] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        ready: list[int] = []
        for succ in successors[node]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                ready.append(succ)
        queue.extend(sorted(ready))
    if len(order) != len(nodes):
        raise ValueError("cycle within the traced sub-network; cannot order")
    return tuple(order)
