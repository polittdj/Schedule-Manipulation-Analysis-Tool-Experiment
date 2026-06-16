"""Summary-task logic — MS-Project-faithful lowering + the best-practice flag (ADR-0043).

Covers the WBS hierarchy resolver, the relationship lowering (no-op when clean, expansion
when a summary carries logic, segment-prefix correctness), the summaries-with-logic flag,
and the end-to-end CPM effect: a predecessor on a summary pushes the summary's children out
the way MS Project does. Parity safety (goldens carry no summary logic) is pinned too.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm, datetime_to_offset
from schedule_forensics.engine.summary_logic import (
    lower_summary_relationships,
    summaries_with_logic,
    summary_leaf_descendants,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday
DAY = 480


def _task(uid: int, wbs: str, *, summary: bool = False, dur_days: int = 1) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        wbs=wbs,
        is_summary=summary,
        duration_minutes=0 if summary else dur_days * DAY,
    )


def _sched(tasks: list[Task], rels: list[Relationship]) -> Schedule:
    return Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


# ── hierarchy + lowering units ───────────────────────────────────────────────────────


def test_leaf_descendants_uses_segment_prefix_not_raw_prefix() -> None:
    tasks = [
        _task(1, "6", summary=True),
        _task(2, "6.1", summary=True),
        _task(3, "6.1.2"),  # under 6.1 and 6
        _task(4, "6.10.1"),  # under 6 but NOT under 6.1 (segment-wise)
        _task(5, "7.1"),  # unrelated
    ]
    d = summary_leaf_descendants(_sched(tasks, []))
    assert set(d[2]) == {3}  # 6.1 -> only 6.1.2, NOT 6.10.1
    assert set(d[1]) == {3, 4}  # 6 -> both leaves under it


def test_lowering_is_a_noop_without_summary_logic() -> None:
    tasks = [_task(1, "1.1"), _task(2, "1.2")]
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    sch = _sched(tasks, rels)
    # identical object returned — guarantees byte-for-byte CPM parity on clean schedules
    assert lower_summary_relationships(sch) is sch.relationships


def test_lowering_expands_summary_endpoints_to_leaves() -> None:
    tasks = [
        _task(1, "2.1"),  # predecessor leaf
        _task(10, "1", summary=True),
        _task(11, "1.1"),  # child leaf
        _task(12, "1.2"),  # child leaf
    ]
    rels = [Relationship(predecessor_id=1, successor_id=10, lag_minutes=5 * DAY)]
    lowered = lower_summary_relationships(_sched(tasks, rels))
    pairs = {(r.predecessor_id, r.successor_id, r.lag_minutes) for r in lowered}
    # the summary successor is replaced by BOTH its children, lag preserved
    assert pairs == {(1, 11, 5 * DAY), (1, 12, 5 * DAY)}


def test_summaries_with_logic_flags_only_linked_summaries() -> None:
    tasks = [
        _task(10, "1", summary=True),  # carries logic
        _task(11, "1.1"),
        _task(20, "2", summary=True),  # no logic
        _task(21, "2.1"),
    ]
    rels = [Relationship(predecessor_id=11, successor_id=10)]  # leaf -> summary 10
    assert summaries_with_logic(_sched(tasks, rels)) == (10,)


# ── end-to-end CPM effect ──────────────────────────────────────────────────────────────


def test_predecessor_on_summary_pushes_children_out() -> None:
    # P (5 working days) -> Summary S; child C (1 day) under S. MS Project starts C after P
    # finishes; our CPM must too (it would otherwise pack C at the project start).
    tasks = [
        _task(1, "2.1", dur_days=5),  # P
        _task(10, "1", summary=True),  # S
        _task(11, "1.1", dur_days=1),  # C, child of S
    ]
    rels = [Relationship(predecessor_id=1, successor_id=10, type=RelationshipType.FS)]
    sch = _sched(tasks, rels)
    cpm = compute_cpm(sch)
    # P finishes at offset 5 working days; C must start there (not at 0)
    p_finish = cpm.timings[1].early_finish
    assert p_finish == 5 * DAY
    assert cpm.timings[11].early_start == p_finish  # child pushed to after P
    assert cpm.timings[11].early_finish == 6 * DAY


def test_without_summary_logic_child_starts_at_project_start() -> None:
    # same tasks, but the logic is on the CHILD (leaf), not the summary -> C still after P
    tasks = [
        _task(1, "2.1", dur_days=5),
        _task(10, "1", summary=True),
        _task(11, "1.1", dur_days=1),
    ]
    # no relationship at all: C is unlinked -> starts at project start
    cpm = compute_cpm(_sched(tasks, []))
    assert cpm.timings[11].early_start == 0


def test_summary_to_summary_chain_accumulates_lag() -> None:
    # S1 -> S2 (FS, 10 wd). child of S1 takes 3 wd. child of S2 must start at 3+10 = 13 wd.
    tasks = [
        _task(10, "1", summary=True),
        _task(11, "1.1", dur_days=3),
        _task(20, "2", summary=True),
        _task(21, "2.1", dur_days=1),
    ]
    rels = [
        Relationship(
            predecessor_id=10, successor_id=20, type=RelationshipType.FS, lag_minutes=10 * DAY
        )
    ]
    cpm = compute_cpm(_sched(tasks, rels))
    assert cpm.timings[11].early_finish == 3 * DAY  # S1's only child
    assert cpm.timings[21].early_start == 13 * DAY  # after S1 finish (3) + 10 wd lag


def test_summary_without_wbs_has_no_descendants_and_self_edges_are_dropped() -> None:
    # a summary with no WBS code resolves to no descendants; a summary linked toward its own
    # child produces only cross-edges, never a self-loop, and duplicates are deduped
    tasks = [
        _task(10, "", summary=True),  # no WBS -> empty descendants
        _task(20, "3", summary=True),
        _task(21, "3.1"),
        _task(22, "3.2"),
    ]
    d = summary_leaf_descendants(_sched(tasks, []))
    assert d[10] == ()  # no WBS -> nothing
    # two relationships that lower to the same leaf edge collapse to one (dedup);
    # the summary->own-child link (20->21) yields only 22->21, not 21->21
    rels = [
        Relationship(predecessor_id=20, successor_id=21),
        Relationship(predecessor_id=22, successor_id=21),  # duplicate of one lowered edge
    ]
    lowered = lower_summary_relationships(_sched(tasks, rels))
    pairs = sorted((r.predecessor_id, r.successor_id) for r in lowered)
    assert pairs == [(22, 21)]  # 21->21 dropped (self), the duplicate collapsed


def test_goldens_carry_no_summary_logic(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    # parity safety: the curated schedules have no logic on summaries, so lowering is a
    # no-op and the CPM is unchanged (the validated parity numbers stand)
    assert summaries_with_logic(golden_project2) == ()
    assert summaries_with_logic(golden_project5) == ()
    assert lower_summary_relationships(golden_project5) is golden_project5.relationships


def test_datetime_offset_sanity() -> None:
    # guard the helper used above (one working day == DAY minutes on the default calendar)
    sch = _sched([_task(1, "1.1")], [])
    assert datetime_to_offset(sch.project_start, MON, sch.calendar) == 0
