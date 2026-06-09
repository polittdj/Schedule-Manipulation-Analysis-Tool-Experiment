"""Schedule-Quality (§A) tests — Acumen golden parity (P2/P5) + synthetic checks."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from schedule_forensics.engine.metrics import compute_schedule_quality
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_golden_schedule_quality_parity(project: str) -> None:
    case = json.loads((GOLDEN / "project2_5" / "case.json").read_text())[project]
    schedule = parse_mspdi(GOLDEN / "project2_5" / f"{project}.mspdi.xml")
    q = compute_schedule_quality(schedule)
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
