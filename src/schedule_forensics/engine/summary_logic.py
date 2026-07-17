"""Logic on summary tasks — MS-Project-faithful scheduling + a best-practice flag (ADR-0043).

MS Project lets a planner attach predecessor/successor logic to a **summary** task.
Scheduling best practice (DCMA, PMI) says *don't* — logic belongs on the work, not the
roll-up — but real downloaded schedules do it, and MS Project honors it: a predecessor on
a summary delays **every child** of that summary, and a summary's successor is driven by
the summary's roll-up **finish** (its latest child). Our CPM otherwise drops summary tasks
from the network (they are date roll-ups, not work), so it would silently *ignore* that
logic and schedule the children far earlier than MS Project does — exactly the
"duration-bomb" divergence the operator's reference file exhibits (computed 2026-08 against
MS Project's 2027-02).

This module reproduces MS Project's behavior by **lowering** every summary-touching
relationship onto the summary's **leaf descendants**: each summary endpoint is replaced by
its non-summary descendants (the cross-product, relationship type and lag preserved). For
finish-to-start logic — the dominant case — this is exact: a summary predecessor's roll-up
finish is the max of its leaf finishes (every lowered FS edge contributes that max), and a
summary successor's start constrains every child (every lowered edge pins a child). The
lowered, leaf-only relationships feed the existing CPM unchanged.

The summary hierarchy is read from the **WBS code** (segment-prefix: ``6.1`` is the parent
of ``6.1.2`` but not of ``6.10``) — the only hierarchy signal the model carries. When a
schedule has **no** logic on any summary (the curated parity schedules, validated never to),
lowering is a no-op and returns the relationships unchanged, so the CPM is byte-identical
and parity is preserved.
"""

from __future__ import annotations

from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule

#: Defensive ceiling on the number of leaf edges a schedule's summary logic may lower to (audit-E).
#: A summary-to-summary relationship expands to a leaf CROSS-PRODUCT, so a sparse source network can
#: project a dense E'; past this ceiling the lowering is refused (fail loud) rather than silently
#: building a multi-hundred-thousand-edge network (a DoS/OOM hazard on a hostile or malformed file).
#: Set an order of magnitude above any realistic schedule — a test pins it above every committed
#: fixture's projected fan-out, so it NEVER fires on a real plan. It is NEVER used to truncate the
#: edge set (that would drop real logic and change CPM dates — a Law-2 break); it only refuses.
SUMMARY_EDGE_CEILING = 250_000


class SummaryLogicExplosion(ValueError):
    """A schedule's summary-to-summary logic would lower to a pathologically dense leaf network.

    Raised (not silently truncated) so the caller fails loud; ``engine.cpm`` re-raises it as a
    :class:`~schedule_forensics.engine.cpm.CPMError` so the web layer degrades to a disclosed 422
    rather than hanging, OOM-ing, or — worst of all — silently emitting a wrong-but-fast schedule.
    """


def _segments(wbs: str | None) -> list[str]:
    return [s for s in wbs.split(".")] if wbs else []


def _is_ancestor(ancestor_wbs: list[str], descendant_wbs: list[str]) -> bool:
    """True when ``ancestor_wbs`` is a strict segment-prefix of ``descendant_wbs``.

    Segment-wise so ``["6","1"]`` is an ancestor of ``["6","1","2"]`` but **not** of
    ``["6","10"]`` (a raw string prefix would wrongly match the latter)."""
    return (
        len(ancestor_wbs) < len(descendant_wbs)
        and descendant_wbs[: len(ancestor_wbs)] == ancestor_wbs
    )


def summary_leaf_descendants(schedule: Schedule) -> dict[int, tuple[int, ...]]:
    """Map each summary UID → its non-summary (leaf) descendant UIDs, via WBS prefix.

    Summaries with no WBS, or with no leaf descendants, map to an empty tuple."""
    summaries = [(t.unique_id, _segments(t.wbs)) for t in schedule.tasks if t.is_summary]
    leaves = [(t.unique_id, _segments(t.wbs)) for t in schedule.tasks if not t.is_summary]
    out: dict[int, tuple[int, ...]] = {}
    for suid, swbs in summaries:
        if not swbs:
            out[suid] = ()
            continue
        out[suid] = tuple(luid for luid, lwbs in leaves if _is_ancestor(swbs, lwbs))
    return out


def summaries_with_logic(schedule: Schedule) -> tuple[int, ...]:
    """Summary UIDs that participate in any relationship (as predecessor or successor).

    These are the "logic on summary tasks" best-practice violations the recommendations
    engine flags — sorted, deduplicated, citable."""
    summary_ids = {t.unique_id for t in schedule.tasks if t.is_summary}
    flagged = {
        uid
        for r in schedule.relationships
        for uid in (r.predecessor_id, r.successor_id)
        if uid in summary_ids
    }
    return tuple(sorted(flagged))


def lower_summary_relationships(schedule: Schedule) -> tuple[Relationship, ...]:
    """Relationships with every summary endpoint expanded to its leaf descendants.

    Pure leaf↔leaf relationships pass through unchanged; a relationship touching a summary
    is replaced by the cross-product of the two endpoints' leaf descendants (type and lag
    preserved), deduplicated and order-preserving. A schedule with no summary logic returns
    its relationships **unchanged** (a true no-op — parity-preserving)."""
    summary_ids = {t.unique_id for t in schedule.tasks if t.is_summary}
    if not any(
        r.predecessor_id in summary_ids or r.successor_id in summary_ids
        for r in schedule.relationships
    ):
        return schedule.relationships

    descendants = summary_leaf_descendants(schedule)

    def endpoints(uid: int) -> tuple[int, ...]:
        # a summary expands to its leaves; a leaf stands for itself
        return descendants[uid] if uid in summary_ids else (uid,)

    # Defensive guard (audit-E): project the fan-out from LENGTHS only (no edge objects built) and
    # FAIL LOUD past the ceiling instead of materializing — or silently truncating — a dense
    # summary-to-summary cross-product. Never fires on a real schedule (ceiling >> any fixture).
    projected = sum(
        len(endpoints(r.predecessor_id)) * len(endpoints(r.successor_id))
        for r in schedule.relationships
    )
    if projected > SUMMARY_EDGE_CEILING:
        raise SummaryLogicExplosion(
            f"summary logic would lower to ~{projected} leaf edges (> {SUMMARY_EDGE_CEILING}); "
            "the schedule's summary-to-summary logic is pathologically dense — review the network"
        )

    lowered: list[Relationship] = []
    seen: set[tuple[int, int, str, int]] = set()
    for r in schedule.relationships:
        for pred in endpoints(r.predecessor_id):
            for succ in endpoints(r.successor_id):
                if pred == succ:
                    continue  # a summary linked near its own descendant — no self-edge
                key = (pred, succ, str(r.type), r.lag_minutes)
                if key in seen:
                    continue
                seen.add(key)
                lowered.append(
                    Relationship(
                        predecessor_id=pred,
                        successor_id=succ,
                        type=r.type,
                        lag_minutes=r.lag_minutes,
                    )
                )
    return tuple(lowered)
