"""Edge-case unit tests for the manipulation detector & multi-version trend.

Targets: the trend's cpms-mismatch raise (manipulation.py 261); the deleted-task finding when the
removed activities were NOT on the prior critical path (branch 90->92, MEDIUM severity, no
on-path detail); and the deleted-logic citation de-dup when two removed links share a successor
(branch 115->113, the second link's successor already in `seen`).
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.recommendations import Severity
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(
    tasks: list[Task],
    rels: list[Relationship] | None = None,
    *,
    name: str = "s",
    source_file: str | None = None,
) -> Schedule:
    return Schedule(
        name=name,
        source_file=source_file,
        project_start=MON,
        tasks=tuple(tasks),
        relationships=tuple(rels or []),
    )


# --- manipulation.py:261 — trend raises when cpms do not parallel schedules ----------------------


def test_trend_across_versions_raises_when_cpms_do_not_parallel_schedules() -> None:
    s = _sched([Task(unique_id=1, name="T", duration_minutes=DAY)])
    cpm = compute_cpm(s)
    with pytest.raises(ValueError, match="cpms must parallel schedules"):
        trend_across_versions([s], cpms=[cpm, cpm])  # 1 schedule, 2 cpms


def test_trend_across_versions_emits_one_point_per_version() -> None:
    """Sanity / happy path proving the raise above is a real guard: a single version yields one
    TrendPoint carrying its completion counts."""
    s = _sched(
        [
            Task(unique_id=1, name="done", duration_minutes=DAY, percent_complete=100.0),
            Task(unique_id=2, name="wip", duration_minutes=DAY, percent_complete=50.0),
        ]
    )
    (point,) = trend_across_versions([s])
    assert point.version_index == 0
    assert point.completed == 1 and point.in_progress == 1


# --- manipulation.py branch 90->92 — deleted tasks NOT on the prior critical path ----------------


def test_deleted_task_off_the_critical_path_is_medium_severity_without_on_path_detail() -> None:
    """When the removed activities were NOT on the prior critical path, the `if on_path:` block is
    skipped (branch 90->92): the finding is MEDIUM severity and the detail omits the critical-path
    clause."""
    # prior: critical chain 1->2->3 (10 days total) PLUS a short parallel dangler 4 (1 day, lots
    # of float, not wired into the chain end) -> 4 is NOT on the critical path.
    prior = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=DAY * 4),
            Task(unique_id=2, name="B", duration_minutes=DAY * 4),
            Task(unique_id=3, name="C", duration_minutes=DAY * 4),
            Task(unique_id=4, name="D-spur", duration_minutes=DAY),  # tiny, off the path
        ],
        [
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
            Relationship(predecessor_id=1, successor_id=4),  # spur off task 1, never rejoins
        ],
        source_file="prior.mpp",
    )
    # current: the off-path spur (task 4) is removed; the critical chain is intact.
    current = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=DAY * 4),
            Task(unique_id=2, name="B", duration_minutes=DAY * 4),
            Task(unique_id=3, name="C", duration_minutes=DAY * 4),
        ],
        [
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ],
        source_file="current.mpp",
    )
    findings = detect_manipulation(current, prior)
    deleted = next(f for f in findings if f.metric_id == "MANIP_DELETED_TASK")
    assert deleted.severity is Severity.MEDIUM  # not on the critical path
    assert "critical path" not in deleted.detail  # the on_path clause was skipped
    assert any(c.unique_id == 4 for c in deleted.citations)


# --- manipulation.py branch 115->113 — two removed links share a successor (citation de-dup) ------


def test_deleted_logic_cites_a_shared_successor_once() -> None:
    """Two removed relationships pointing at the SAME successor cite that activity once: on the
    second link the successor is already in `seen`, so the `if ... not in seen` is False and the
    loop continues without re-citing (branch 115->113)."""
    # prior: two predecessors (1, 2) both feeding successor 3; plus task 4 to anchor.
    prior = _sched(
        [
            Task(unique_id=1, name="P1", duration_minutes=DAY),
            Task(unique_id=2, name="P2", duration_minutes=DAY),
            Task(unique_id=3, name="S", duration_minutes=DAY),
            Task(unique_id=4, name="X", duration_minutes=DAY),
        ],
        [
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
            Relationship(predecessor_id=4, successor_id=1),  # keep some surviving logic
        ],
        source_file="prior.mpp",
    )
    # current: BOTH links into successor 3 are removed (the 4->1 link survives).
    current = _sched(
        [
            Task(unique_id=1, name="P1", duration_minutes=DAY),
            Task(unique_id=2, name="P2", duration_minutes=DAY),
            Task(unique_id=3, name="S", duration_minutes=DAY),
            Task(unique_id=4, name="X", duration_minutes=DAY),
        ],
        [Relationship(predecessor_id=4, successor_id=1)],
        source_file="current.mpp",
    )
    logic = next(
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_DELETED_LOGIC"
    )
    # two links removed, both into UID 3 -> UID 3 cited exactly once (de-duplicated)
    succ_3_cites = [c for c in logic.citations if c.unique_id == 3]
    assert len(succ_3_cites) == 1
    assert "2 logic links removed" in logic.title  # both removals are still reported in the count
