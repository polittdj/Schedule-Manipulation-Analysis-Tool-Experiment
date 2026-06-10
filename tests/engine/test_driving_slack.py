"""Driving-slack tests — synthetic hand-verified slack + the SSI golden parity gate.

The golden gate reproduces the SSI MS Project add-on's Driving Slack for Project5 /
focus UID 143 exactly (107 UniqueIDs), keyed by UniqueID (`SSI-DRIVING-SLACK.md`).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from schedule_forensics.engine.driving_slack import (
    PathTier,
    compute_driving_slack,
    driving_path,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _net() -> Schedule:
    # Focus = 4(D). Driving path 2(B,1d) -> 3(C,3d) -> 4(D,1d); 1(A,2d) -> 4 with 2 days slack.
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
        Task(unique_id=3, name="C", duration_minutes=3 * DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=4),
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
    ]
    return Schedule(name="net", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def test_synthetic_driving_slack() -> None:
    results = compute_driving_slack(_net(), target_uid=4)
    assert set(results) == {1, 2, 3, 4}  # focus + its ancestors only
    assert results[4].driving_slack_minutes == 0 and results[4].on_driving_path
    assert results[2].driving_slack_minutes == 0 and results[3].driving_slack_minutes == 0
    assert results[1].driving_slack_minutes == 2 * DAY  # A may slip 2 days
    assert results[1].on_driving_path is False
    assert results[1].tier is PathTier.SECONDARY


def test_driving_path_is_ordered() -> None:
    results = compute_driving_slack(_net(), target_uid=4)
    assert driving_path(_net(), results) == (2, 3, 4)


def test_tier_thresholds_configurable() -> None:
    # A's 2-day slack lands beyond a 1-day tertiary ceiling.
    results = compute_driving_slack(_net(), target_uid=4, secondary_max_days=1, tertiary_max_days=1)
    assert results[1].tier is PathTier.BEYOND
    # Widen secondary to include it.
    results2 = compute_driving_slack(_net(), target_uid=4, secondary_max_days=5)
    assert results2[1].tier is PathTier.SECONDARY


def test_target_with_no_ancestors() -> None:
    results = compute_driving_slack(_net(), target_uid=2)  # B is a start task
    assert set(results) == {2}
    assert results[2].driving_slack_minutes == 0


def test_golden_ssi_driving_slack_parity(golden_project5: Schedule) -> None:
    case = json.loads((GOLDEN / "ssi_uid143" / "case.json").read_text())
    results = compute_driving_slack(golden_project5, target_uid=case["focus_task_uid"])

    expected = {int(uid): days for uid, days in case["driving_slack_days_by_uid"].items()}
    # exact, UniqueID-keyed: every traced task and no extras
    assert set(results) == set(expected)
    got_days = {uid: int(r.driving_slack_days) for uid, r in results.items()}
    assert got_days == expected
    # whole working days, no fractional drift
    assert all(r.driving_slack_minutes % DAY == 0 for r in results.values())

    focus = results[case["focus_task_uid"]]
    assert focus.driving_slack_minutes == 0 and focus.on_driving_path

    tiers = {tier: sum(1 for r in results.values() if r.tier is tier) for tier in PathTier}
    assert tiers[PathTier.DRIVING] == 36
    assert tiers[PathTier.SECONDARY] == 12  # 5/7/10-day groups
    assert tiers[PathTier.TERTIARY] == 12  # 12/16/20-day groups
    assert len(driving_path(golden_project5, results)) == 36
