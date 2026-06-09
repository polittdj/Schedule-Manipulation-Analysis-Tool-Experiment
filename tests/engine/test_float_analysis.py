"""Float-analysis tests — day-denominated per-task float, the schedule summary, and
the Acumen "Critical" parity sanity against the committed golden fixtures."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from schedule_forensics.engine.float_analysis import analyze_floats, summarize_floats
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _diamond() -> Schedule:
    # A(1d) -> {B(2d), C(4d)} -> D(1d); B carries 2 days of float.
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=2 * DAY),
        Task(unique_id=3, name="C", duration_minutes=4 * DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=4),
        Relationship(predecessor_id=3, successor_id=4),
    ]
    return Schedule(
        name="diamond", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels)
    )


def test_analyze_floats_days_and_criticality() -> None:
    floats = {f.unique_id: f for f in analyze_floats(_diamond())}
    assert floats[2].total_float_days == Decimal("2")
    assert floats[2].free_float_days == Decimal("2")
    assert floats[2].is_critical is False
    for uid in (1, 3, 4):
        assert floats[uid].total_float_days == Decimal("0")
        assert floats[uid].is_critical is True


def test_float_result_is_sorted_by_uid() -> None:
    floats = analyze_floats(_diamond())
    assert [f.unique_id for f in floats] == [1, 2, 3, 4]


def test_is_critical_incomplete_property() -> None:
    # A completed critical task is critical but not "critical-incomplete".
    tasks = [Task(unique_id=1, name="done", duration_minutes=DAY, percent_complete=100.0)]
    s = Schedule(name="s", project_start=MON, tasks=tuple(tasks))
    floats = analyze_floats(s)
    assert floats[0].is_critical is True
    assert floats[0].is_complete is True
    assert floats[0].is_critical_incomplete is False


def test_summary_counts() -> None:
    summary = summarize_floats(_diamond())
    assert summary.task_count == 4
    assert summary.critical_count == 3  # A, C, D
    assert summary.critical_incomplete_count == 3  # none complete
    assert summary.negative_float_count == 0
    assert summary.network_finish_days == Decimal("6")


@pytest.mark.parametrize(
    ("name", "critical_raw", "critical_incomplete", "finish_days"),
    [
        ("Project2", 43, 41, Decimal("391")),
        ("Project5", 37, 37, Decimal("462")),
    ],
)
def test_golden_critical_parity(
    name: str, critical_raw: int, critical_incomplete: int, finish_days: Decimal
) -> None:
    s = parse_mspdi(GOLDEN / f"{name}.mspdi.xml")
    summary = summarize_floats(s)
    assert summary.task_count == 126
    assert summary.critical_count == critical_raw
    # Acumen "Critical" metric excludes completed activities -> matches PARITY-TARGETS (41/37).
    assert summary.critical_incomplete_count == critical_incomplete
    assert summary.network_finish_days == finish_days
