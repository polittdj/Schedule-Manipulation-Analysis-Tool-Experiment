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


def test_effective_float_helpers_prefer_stored_msproject_values() -> None:
    """ADR-0080: when the source file carries MS Project's stored Total Slack / Critical flag,
    the float-based metrics score on those (what Acumen reads); otherwise the recomputed CPM
    float, with completed work excluded from Critical."""
    from schedule_forensics.engine.metrics._common import (
        effective_total_float,
        is_effective_critical,
    )

    base = Task(unique_id=1, name="x", duration_minutes=DAY, percent_complete=50.0)
    behind = base.model_copy(
        update={"stored_total_float_minutes": -480, "stored_is_critical": True}
    )
    assert effective_total_float(behind, 999) == -480.0  # stored wins over recomputed
    assert is_effective_critical(behind, 999) is True
    ahead = base.model_copy(update={"stored_total_float_minutes": 480, "stored_is_critical": False})
    assert effective_total_float(ahead, -999) == 480.0
    assert is_effective_critical(ahead, -999) is False  # stored False wins over recomputed crit
    # absent → fall back to recomputed float; Critical also excludes completed work
    assert effective_total_float(base, -240) == -240.0
    assert is_effective_critical(base, 0) is True
    done = Task(unique_id=2, name="y", duration_minutes=DAY, percent_complete=100.0)
    assert is_effective_critical(done, -5) is False


def test_negative_float_and_critical_use_stored_slack_when_present() -> None:
    """The operator's bug: on a progressed file the engine's recomputed float was non-negative
    (0 negative float) while MS Project / Acumen stored negative Total Slack. With the stored
    value present, Negative Float and Critical now match the source tool (ADR-0080)."""
    t1 = Task(unique_id=1, name="A", duration_minutes=DAY, percent_complete=50.0)
    # clean chain → recomputed float is 0 for task 2; the source stored it behind a constraint
    t2_stored = Task(
        unique_id=2,
        name="B",
        duration_minutes=DAY,
        percent_complete=50.0,
        stored_total_float_minutes=-2400,
        stored_is_critical=True,
    )
    rels = (Relationship(predecessor_id=1, successor_id=2),)
    q = compute_schedule_quality(
        Schedule(name="s", project_start=MON, tasks=(t1, t2_stored), relationships=rels)
    )
    assert q["negative_float"].count == 1 and q["negative_float"].offender_uids == (2,)
    assert 2 in q["critical"].offender_uids

    # control: identical schedule without stored values → recomputed float, no negative float
    t2_plain = Task(unique_id=2, name="B", duration_minutes=DAY, percent_complete=50.0)
    q2 = compute_schedule_quality(
        Schedule(name="s", project_start=MON, tasks=(t1, t2_plain), relationships=rels)
    )
    assert q2["negative_float"].count == 0


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


def test_insufficient_detail_is_ten_percent_of_project_calendar_span() -> None:
    """Acumen Insufficient Detail™ (Bible formula, ADR-0084): an activity's CURRENT (Original)
    duration in working days over the project's CALENDAR span (ProjectFinish - ProjectStart in
    days) exceeds 10%. Verified == Acumen's 43 on the Large Test File. The project span here is
    200 calendar days, so the 25-wd task (12.5%) offends and the 15-wd task (7.5%) does not."""
    span_end = MON + dt.timedelta(days=200)
    big = Task(unique_id=1, name="A", duration_minutes=25 * DAY, finish=MON + dt.timedelta(days=35))
    small = Task(unique_id=2, name="B", duration_minutes=15 * DAY, finish=span_end)
    q = compute_schedule_quality(
        Schedule(
            name="s",
            project_start=MON,
            tasks=(big, small),
            relationships=(Relationship(predecessor_id=1, successor_id=2),),
        )
    )
    assert q["insufficient_detail"].count == 1
    assert q["insufficient_detail"].offender_uids == (1,)


def test_insufficient_detail_uses_the_current_duration_not_baseline() -> None:
    """The Bible uses the current (Original) duration, NOT the baseline (ADR-0084): a task that
    grew during execution is judged on its grown duration. Here a 30-wd current duration over a
    200-day span is 15% (offends), though its 5-wd baseline would be only 2.5%."""
    span_end = MON + dt.timedelta(days=200)
    grew = Task(
        unique_id=1,
        name="A",
        duration_minutes=30 * DAY,
        baseline_duration_minutes=5 * DAY,
        finish=MON + dt.timedelta(days=42),
        percent_complete=100.0,
    )
    spacer = Task(unique_id=2, name="B", duration_minutes=DAY, finish=span_end)
    q = compute_schedule_quality(
        Schedule(
            name="s",
            project_start=MON,
            tasks=(grew, spacer),
            relationships=(Relationship(predecessor_id=1, successor_id=2),),
        )
    )
    assert q["insufficient_detail"].count == 1 and q["insufficient_detail"].offender_uids == (1,)
