"""Schedule-card profile tests — activity makeup + primary-constraint distribution.

The deck's *Metrics* page (PBIX page 1). Golden counts are the validated values used
across the suite (126 normal activities; 18 summaries excluding the UID-0 project row;
Project5 27 complete / 2 in progress).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import (
    compute_activity_makeup,
    compute_constraint_distribution,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def _task(uid: int, **kw: object) -> Task:
    kw.setdefault("duration_minutes", 480)
    return Task(unique_id=uid, name=f"T{uid}", **kw)


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks), relationships=())


def test_activity_makeup_on_golden_project5(golden_project5: Schedule) -> None:
    m = compute_activity_makeup(golden_project5)
    assert m.total == 126 and m.normal == 126 and m.milestones == 0
    assert m.summaries == 18  # excludes the UID-0 project row
    assert (m.complete, m.in_progress, m.planned) == (27, 2, 97)
    assert m.complete + m.in_progress + m.planned == m.total


def test_activity_makeup_counts_milestones_and_status_splits() -> None:
    s = _sched(
        [
            _task(0, is_summary=True),  # MS Project project row — not counted as a summary
            _task(1, is_summary=True),  # a real WBS summary
            _task(2, is_milestone=True, duration_minutes=0, percent_complete=100.0),
            _task(3, percent_complete=50.0),
            _task(4),  # planned (0%)
        ]
    )
    m = compute_activity_makeup(s)
    assert m.total == 3  # summaries excluded from the population
    assert m.summaries == 1  # UID-0 excluded, UID-1 counted
    assert m.milestones == 1 and m.normal == 2
    assert (m.complete, m.in_progress, m.planned) == (1, 1, 1)


def test_constraint_distribution_on_golden_project5(golden_project5: Schedule) -> None:
    rows = compute_constraint_distribution(golden_project5)
    assert [(r.constraint_type, r.count) for r in rows] == [("ASAP", 121), ("SNET", 5)]
    assert round(rows[0].percent, 1) == 96.0 and round(rows[1].percent, 1) == 4.0
    assert sum(r.count for r in rows) == 126  # every non-summary activity is classified


def test_constraint_distribution_orders_by_count_then_name() -> None:
    s = _sched(
        [
            _task(1, constraint_type=ConstraintType.MFO, constraint_date=MON),
            _task(2, constraint_type=ConstraintType.MFO, constraint_date=MON),
            _task(3, constraint_type=ConstraintType.SNET, constraint_date=MON),
            _task(4),  # ASAP
        ]
    )
    rows = compute_constraint_distribution(s)
    # MFO (2) leads; ASAP and SNET tie at 1 -> alphabetical (ASAP before SNET)
    assert [(r.constraint_type, r.count) for r in rows] == [
        ("MFO", 2),
        ("ASAP", 1),
        ("SNET", 1),
    ]
    assert rows[0].percent == 50.0


def test_all_asap_schedule_is_a_single_full_row() -> None:
    rows = compute_constraint_distribution(_sched([_task(1), _task(2)]))
    assert len(rows) == 1
    assert rows[0].constraint_type == "ASAP" and rows[0].percent == 100.0
