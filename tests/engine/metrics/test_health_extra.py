"""Extra structural health checks (handbook Fig. 6-9) — deterministic counts over known inputs."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics.health_extra import compute_health_checks
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def _counts(sch: Schedule) -> dict[str, int]:
    cpm = compute_cpm(sch)
    return {c.key: c.count for c in compute_health_checks(sch, cpm).checks}


def test_milestone_duration_zero_duration_and_missing_fields() -> None:
    tasks = (
        Task(unique_id=1, name="normal", duration_minutes=480, wbs="A", baseline_finish=MON),
        Task(
            unique_id=2,
            name="ms-dur",
            duration_minutes=480,
            is_milestone=True,
            wbs="A",
            baseline_finish=MON,
        ),
        Task(unique_id=3, name="zero", duration_minutes=0, wbs="A", baseline_finish=MON),
        Task(unique_id=4, name="bare", duration_minutes=480),  # no wbs, no baseline finish
    )
    counts = _counts(Schedule(name="s", project_start=MON, tasks=tasks, relationships=()))
    assert counts["milestone_with_duration"] == 1  # UID 2
    assert counts["zero_duration_task"] == 1  # UID 3 (the milestone is excluded)
    assert counts["missing_wbs"] == 1  # UID 4 only
    assert counts["missing_baseline_finish"] == 1  # UID 4 only


def test_hidden_duration_from_oversized_lag() -> None:
    tasks = (
        Task(unique_id=1, name="pred", duration_minutes=480, wbs="A", baseline_finish=MON),
        Task(unique_id=2, name="lagged", duration_minutes=480, wbs="A", baseline_finish=MON),
    )
    # 300 > 0.35 * 480 (168) → the lag hides real duration inside the relationship
    rels = (Relationship(predecessor_id=1, successor_id=2, lag_minutes=300),)
    assert (
        _counts(Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels))[
            "hidden_duration"
        ]
        == 1
    )


def test_critical_merge_hotspot() -> None:
    # 1,2,3 → 4 ; UID 4 is the sink (critical) with three predecessors
    tasks = tuple(
        Task(unique_id=u, name=f"T{u}", duration_minutes=480, wbs="A", baseline_finish=MON)
        for u in (1, 2, 3, 4)
    )
    rels = tuple(Relationship(predecessor_id=p, successor_id=4) for p in (1, 2, 3))
    assert (
        _counts(Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels))[
            "critical_merge_hotspot"
        ]
        >= 1
    )


def test_estimated_duration_flags_placeholders_excluding_milestones() -> None:
    tasks = (
        Task(
            unique_id=1,
            name="est",
            duration_minutes=480,
            wbs="A",
            baseline_finish=MON,
            is_estimated_duration=True,
        ),
        Task(  # an estimated milestone is excluded (a zero-duration event, not a placeholder)
            unique_id=2,
            name="est-ms",
            duration_minutes=0,
            is_milestone=True,
            wbs="A",
            baseline_finish=MON,
            is_estimated_duration=True,
        ),
        Task(unique_id=3, name="firm", duration_minutes=480, wbs="A", baseline_finish=MON),
    )
    counts = _counts(Schedule(name="s", project_start=MON, tasks=tasks, relationships=()))
    assert counts["estimated_duration"] == 1  # UID 1 only


def test_clean_schedule_has_zero_offenders() -> None:
    tasks = (
        Task(unique_id=1, name="a", duration_minutes=480, wbs="A", baseline_finish=MON),
        Task(unique_id=2, name="b", duration_minutes=480, wbs="A", baseline_finish=MON),
    )
    rels = (Relationship(predecessor_id=1, successor_id=2),)
    counts = _counts(Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels))
    for key in (
        "milestone_with_duration",
        "zero_duration_task",
        "missing_wbs",
        "hidden_duration",
        "estimated_duration",
    ):
        assert counts[key] == 0, key
