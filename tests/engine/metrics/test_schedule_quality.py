"""Schedule-Quality (§A) tests — Acumen golden parity (P2/P5) + synthetic checks."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from schedule_forensics.engine.metrics import compute_schedule_quality
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_golden_schedule_quality_parity(project: str, golden: Callable[[str], Schedule]) -> None:
    case = json.loads((GOLDEN / "project2_5" / "case.json").read_text())[project]
    q = compute_schedule_quality(golden(project))
    g = case["schedule_quality"]
    for key in (
        "missing_logic",
        "critical",
        "hard_constraints",
        "negative_float",
        "insufficient_detail",
        "number_of_lags",
        "number_of_leads",
        "merge_hotspot",
    ):
        assert q[key].count == g[key], f"{project} {key}: {q[key].count} != {g[key]}"
    assert q["logic_density"].value == g["logic_density"]


def test_merge_hotspot_threshold_is_three_predecessors() -> None:
    # task 5 has 3 predecessors (merge hotspot); task 4 has 2 (not).
    tasks = [Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in range(1, 6)]
    rels = [
        Relationship(predecessor_id=1, successor_id=4),
        Relationship(predecessor_id=2, successor_id=4),
        Relationship(predecessor_id=1, successor_id=5),
        Relationship(predecessor_id=2, successor_id=5),
        Relationship(predecessor_id=3, successor_id=5),
    ]
    q = compute_schedule_quality(
        Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    )
    assert q["merge_hotspot"].count == 1
    assert q["merge_hotspot"].offender_uids == (5,)


def test_logic_density_is_two_links_per_activity() -> None:
    tasks = [Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (1, 2)]
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    q = compute_schedule_quality(
        Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    )
    assert q["logic_density"].value == 1.0  # 2 * 1 link / 2 activities


def test_missing_logic_flags_open_ends() -> None:
    tasks = [Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (1, 2)]
    # task 1 has no predecessor, task 2 has no successor -> both flagged
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    q = compute_schedule_quality(
        Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    )
    assert q["missing_logic"].count == 2


def test_insufficient_detail_is_ten_percent_of_project_working_duration() -> None:
    """Fuse's Insufficient Detail™: baseline duration > 10% of the project's working
    duration, both in working days (decoded against the golden Fuse briefing and the
    operator's TP3 Fuse run). The same 30-day task offends in a 100-day project
    (30 > 10) but not in a 400-day one (30 < 40)."""
    long_task = Task(unique_id=1, name="A", duration_minutes=30 * DAY, percent_complete=0.0)
    rels = (Relationship(predecessor_id=1, successor_id=2),)
    q_small = compute_schedule_quality(
        Schedule(
            name="s",
            project_start=MON,
            tasks=(long_task, Task(unique_id=2, name="B", duration_minutes=70 * DAY)),
            relationships=rels,
        )
    )
    assert q_small["insufficient_detail"].count == 2  # 30 and 70 both > 10% of 100 wd
    q_big = compute_schedule_quality(
        Schedule(
            name="s",
            project_start=MON,
            tasks=(long_task, Task(unique_id=2, name="B", duration_minutes=370 * DAY)),
            relationships=rels,
        )
    )
    # project = 400 wd -> threshold 40: the 30-day task is fine, the 370-day one offends
    assert q_big["insufficient_detail"].count == 1
    assert q_big["insufficient_detail"].offender_uids == (2,)


def test_insufficient_detail_uses_the_baseline_duration_when_present() -> None:
    """A 5-day-planned task whose actual span stretched to 47 working days stays OUT —
    Fuse counted TP3's offenders on the baseline axis (the operator-verified set of 8)."""
    stretched = Task(
        unique_id=1,
        name="A",
        duration_minutes=47 * DAY,
        baseline_duration_minutes=5 * DAY,
        percent_complete=100.0,
    )
    spacer = Task(unique_id=2, name="B", duration_minutes=60 * DAY, percent_complete=0.0)
    q = compute_schedule_quality(
        Schedule(
            name="s",
            project_start=MON,
            tasks=(stretched, spacer),
            relationships=(Relationship(predecessor_id=1, successor_id=2),),
        )
    )
    # project ~107 wd -> threshold ~10.7: baseline 5 d stays out; the 60 d spacer counts
    assert q["insufficient_detail"].offender_uids == (2,)
