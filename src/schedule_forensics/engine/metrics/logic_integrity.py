"""Logic-integrity checks — out-of-sequence progress and redundant logic links.

Two deterministic, forensically central schedule-construction checks the tool did not already
carry, computed from fields the model already has (relationships + actuals). Parity-isolated
lightweight dataclasses (NOT ``MetricResult``) — kept out of the Fuse-parity ribbon and the
gate-locked DCMA audit so they can never disturb either, exactly like ``health_extra``.

* **Out-of-sequence logic** — a finish-to-start successor that *recorded progress* before its
  predecessor finished: ``successor.actual_start`` precedes ``predecessor.actual_finish`` (or the
  predecessor has no recorded finish at all while the successor has already started). Restricted to
  FS links, where the rule is unambiguous (the dominant link type). This is the classic "broken
  logic / status override" signature: the team worked the network in an order the logic forbids.
* **Redundant logic** — a direct link ``A → C`` when a longer path ``A → … → C`` (length ≥ 2)
  already exists, so the direct link constrains nothing the network did not already imply. Redundant
  links clutter the logic, mask the true driving path, and are a common padding artifact. Only
  well-defined on an acyclic network, so it is reported as *not evaluated* on a cyclic graph (CPM
  would already refuse such a schedule) or on a network too large to close transitively in bounded
  time.

Sources: NASA Schedule Management Handbook Fig. 6-9 (improper / redundant logic, pp.170-172);
assessment Deck-1 slides 58-72 (Acumen metric-library names / definitions).
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.schedule import Schedule

#: cap the offender list carried to the UI (the activity / relationship grid is the full record)
_OFFENDER_CAP = 50
#: redundant-logic needs the transitive closure (O(V·E)); skip beyond these to bound runtime
_REDUNDANT_MAX_TASKS = 4000
_REDUNDANT_MAX_EDGES = 12000


@dataclass(frozen=True)
class LogicCheck:
    """One logic-integrity check: how many offend, which links (capped), and why it matters.

    ``offenders`` are human-readable directed-edge descriptors (``"pred→succ"``), already sorted.
    ``evaluated`` is ``False`` when the check was deliberately skipped (e.g. redundant logic on a
    cyclic or oversize network); ``count`` / ``population`` are then ``0`` and ``description`` says
    why. ``offender_uids`` are the raw activity UniqueIDs behind the offenders (for a UID-keyed
    drill-down, e.g. the Assessment-Scorecard ribbon); default empty for checks that don't surface
    them.
    """

    key: str
    label: str
    count: int
    population: int
    offenders: tuple[str, ...]
    description: str
    evaluated: bool = True
    offender_uids: tuple[int, ...] = ()
    #: What ``population`` counts — the UI's "of N <unit>" suffix must not call an
    #: activity-scoped population "links" (the dangling checks count activities).
    population_unit: str = "link(s)"


@dataclass(frozen=True)
class LogicIntegrity:
    """The full set of logic-integrity checks for one schedule."""

    checks: tuple[LogicCheck, ...]


def _topo_order(nodes: set[int], adj: dict[int, set[int]]) -> tuple[list[int], bool]:
    """Kahn topological order over ``adj`` (pred → succ). Returns ``(order, has_cycle)``.

    ``order`` lists every node with predecessors before successors; ``has_cycle`` is ``True`` when
    the network cannot be fully ordered (a cycle remains), in which case ``order`` is partial.
    """
    indeg: dict[int, int] = dict.fromkeys(nodes, 0)
    for src in adj:
        for dst in adj[src]:
            indeg[dst] += 1
    queue = sorted(n for n in nodes if indeg[n] == 0)
    order: list[int] = []
    while queue:
        node = queue.pop()
        order.append(node)
        new_ready: list[int] = []
        for dst in adj.get(node, ()):
            indeg[dst] -= 1
            if indeg[dst] == 0:
                new_ready.append(dst)
        if new_ready:
            queue.extend(sorted(new_ready))
            queue.sort()
    return order, len(order) != len(nodes)


def _out_of_sequence(schedule: Schedule, ns_ids: set[int]) -> LogicCheck:
    """FS successors that started before their predecessor finished (out-of-sequence progress)."""
    by_id = schedule.tasks_by_id
    fs_links = 0
    offenders: list[tuple[int, int]] = []
    for r in schedule.relationships:
        if r.type != RelationshipType.FS:
            continue
        if r.predecessor_id not in ns_ids or r.successor_id not in ns_ids:
            continue
        fs_links += 1
        pred = by_id[r.predecessor_id]
        succ = by_id[r.successor_id]
        # only progressed work can be out of sequence: the successor must have actually started
        if succ.actual_start is None:
            continue
        # violated if the predecessor has no recorded finish, or finished after the successor began
        if pred.actual_finish is None or succ.actual_start < pred.actual_finish:
            offenders.append((r.predecessor_id, r.successor_id))
    offenders.sort()
    # the raw activity UIDs behind the offending edges (both endpoints), sorted + deduplicated +
    # capped — so a scorecard/ribbon can drill from an out-of-sequence FAIL into the activities.
    offender_uids = tuple(sorted({u for pair in offenders for u in pair})[:_OFFENDER_CAP])
    return LogicCheck(
        key="out_of_sequence",
        label="Out-of-sequence logic (FS)",
        count=len(offenders),
        population=fs_links,
        offenders=tuple(f"{p}→{s}" for p, s in offenders[:_OFFENDER_CAP]),
        description=(
            "Finish-to-start successors that recorded progress before their predecessor finished "
            "(the successor's actual start precedes the predecessor's actual finish, or the "
            "predecessor has no recorded finish while the successor has already started) — work "
            "done in an order the logic forbids, a status-override / broken-logic signature."
        ),
        offender_uids=offender_uids,
    )


def _redundant_logic(ns_ids: set[int], edges: list[tuple[int, int]]) -> LogicCheck:
    """Direct links ``A→C`` made superfluous by an existing longer path ``A→…→C`` (length ≥ 2)."""
    desc_text = (
        "Direct links made superfluous because a longer path between the same two activities "
        "already exists, so the link constrains nothing the network did not already imply. "
        "Redundant logic clutters the model and masks the true driving path (Handbook Fig. 6-9)."
    )

    def _skipped(reason: str) -> LogicCheck:
        return LogicCheck(
            key="redundant_logic",
            label="Redundant logic links",
            count=0,
            population=0,
            offenders=(),
            description=f"{desc_text} Not evaluated: {reason}.",
            evaluated=False,
        )

    # distinct directed edges (parallel duplicates collapse to one for reachability)
    adj: dict[int, set[int]] = {}
    for a, c in edges:
        adj.setdefault(a, set()).add(c)
    distinct_edges = sum(len(s) for s in adj.values())

    if len(ns_ids) > _REDUNDANT_MAX_TASKS or distinct_edges > _REDUNDANT_MAX_EDGES:
        return _skipped("network too large to close transitively in bounded time")

    order, has_cycle = _topo_order(ns_ids, adj)
    if has_cycle:
        return _skipped("the network contains a logic cycle; resolve it first")

    # descendants reachable in >= 1 hop, built iteratively in reverse topological order (no
    # recursion, so a long chain can't overflow the stack); a successor's set is done before its
    descendants: dict[int, set[int]] = {}
    for node in reversed(order):
        acc: set[int] = set()
        for nxt in adj.get(node, ()):
            acc.add(nxt)
            acc |= descendants.get(nxt, set())
        descendants[node] = acc

    offenders: list[tuple[int, int]] = []
    for a in adj:
        succs = adj[a]
        for c in succs:
            # redundant iff some OTHER direct successor b of a can still reach c (path a→b→…→c ≥ 2)
            if any(c in descendants.get(b, ()) for b in succs if b != c):
                offenders.append((a, c))
    offenders.sort()
    return LogicCheck(
        key="redundant_logic",
        label="Redundant logic links",
        count=len(offenders),
        population=distinct_edges,
        offenders=tuple(f"{a}→{c}" for a, c in offenders[:_OFFENDER_CAP]),
        description=desc_text,
    )


def _dangling(schedule: Schedule, ns_ids: set[int]) -> tuple[LogicCheck, LogicCheck]:
    """Open Start / Open Finish — "Dangling Activities" per the NASA Acumen metric library.

    The Bible's definitions (``NASA Metrics_Complete_*.aft``, verbatim): **Open Start** —
    "Activities where only the predecessor(s) are either Finish-to-Finish or Start-to-Finish
    resulting in an open start to the activity"; **Open Finish** — "Activities where the only
    successor(s) are either Start-to-Finish or Start-to-Start resulting in an open finish to
    the activity". These catch what a blank-endpoint count (DCMA-01) is structurally blind
    to: a task can have a non-blank Predecessor AND Successor column and still dangle — an
    FF-only predecessor drives its finish but nothing drives its START; an SS-only successor
    hangs on its start while its FINISH drives nothing. Scoped to incomplete activities (the
    library's ribbon variant — "Remaining activities"; a finished activity's dangling end is
    no forward-schedule risk). A task with no links at all on that side is DCMA-01's
    missing-logic case, not a dangler.
    """
    by_id = schedule.tasks_by_id

    def _drives(other_uid: int) -> bool:
        # A link still ties this activity when its OTHER endpoint is a SUMMARY task —
        # summary logic lowers onto the summary's leaves (ADR-0043), so the tie is real.
        # An INACTIVE endpoint is off the network and ties nothing.
        other = by_id.get(other_uid)
        return other is not None and other.is_active

    pred_types: dict[int, set[RelationshipType]] = {}
    succ_types: dict[int, set[RelationshipType]] = {}
    for r in schedule.relationships:
        if r.successor_id in ns_ids and _drives(r.predecessor_id):
            pred_types.setdefault(r.successor_id, set()).add(r.type)
        if r.predecessor_id in ns_ids and _drives(r.successor_id):
            succ_types.setdefault(r.predecessor_id, set()).add(r.type)
    incomplete = sorted(uid for uid in ns_ids if by_id[uid].percent_complete < 100.0)
    open_start = tuple(
        uid
        for uid in incomplete
        if uid in pred_types and pred_types[uid] <= {RelationshipType.FF, RelationshipType.SF}
    )
    open_finish = tuple(
        uid
        for uid in incomplete
        if uid in succ_types and succ_types[uid] <= {RelationshipType.SS, RelationshipType.SF}
    )

    def _label(uid: int) -> str:
        return f"UID {uid} · {by_id[uid].name}"

    return (
        LogicCheck(
            key="open_start",
            label="Open start (dangling)",
            count=len(open_start),
            population=len(incomplete),
            offenders=tuple(_label(u) for u in open_start[:_OFFENDER_CAP]),
            description=(
                "Incomplete activities whose only predecessors are finish-to-finish or "
                "start-to-finish links — nothing drives the activity's START, so it hangs "
                "without a proper logical tie ('dangling activities', Acumen Open Start). "
                "Dangling logic distorts float and masks schedule risk even though the "
                "Predecessor column is not blank."
            ),
            offender_uids=open_start[:_OFFENDER_CAP],
            population_unit="incomplete activities",
        ),
        LogicCheck(
            key="open_finish",
            label="Open finish (dangling)",
            count=len(open_finish),
            population=len(incomplete),
            offenders=tuple(_label(u) for u in open_finish[:_OFFENDER_CAP]),
            description=(
                "Incomplete activities whose only successors are start-to-start or "
                "start-to-finish links — the activity's FINISH drives nothing downstream, so "
                "it can slip without consequence ('dangling activities', Acumen Open Finish). "
                "Dangling logic distorts float and masks schedule risk even though the "
                "Successor column is not blank."
            ),
            offender_uids=open_finish[:_OFFENDER_CAP],
            population_unit="incomplete activities",
        ),
    )


def compute_logic_integrity(schedule: Schedule) -> LogicIntegrity:
    """Compute the logic-integrity checks for ``schedule`` (relationships + actuals; no CPM)."""
    ns_ids = {t.unique_id for t in non_summary(schedule)}
    edges = [
        (r.predecessor_id, r.successor_id)
        for r in schedule.relationships
        if r.predecessor_id in ns_ids and r.successor_id in ns_ids
    ]
    open_start, open_finish = _dangling(schedule, ns_ids)
    return LogicIntegrity(
        checks=(
            _out_of_sequence(schedule, ns_ids),
            _redundant_logic(ns_ids, edges),
            open_start,
            open_finish,
        )
    )
