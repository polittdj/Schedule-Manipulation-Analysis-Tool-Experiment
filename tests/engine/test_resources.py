"""Resource loading & over-allocation engine (ADR-0125).

Time-phases assignment work into a monthly load-vs-capacity histogram and flags months booked beyond
a resource's capacity. Deterministic, parity-isolated (plain dataclasses).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.resources import compute_resource_loading
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model import Assignment, Schedule, Task

DAY = 480
MON = dt.datetime(2026, 4, 6, 8, 0)  # a Monday
GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


def _task(uid: int, dur_days: float, assignments: tuple[Assignment, ...] = ()) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=int(dur_days * DAY),
        resource_assignments=assignments,
    )


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks))


def test_no_assignments_means_no_loading() -> None:
    sch = _sched([_task(1, 5)])
    rl = compute_resource_loading(sch, compute_cpm(sch))
    assert rl.resources == () and rl.has_work is False


def test_work_is_time_phased_and_totalled() -> None:
    a = (Assignment(resource_id=1, work_minutes=10 * DAY, units=1.0),)
    sch = _sched([_task(1, 10, a)])
    rl = compute_resource_loading(sch, compute_cpm(sch))
    assert rl.has_work is True
    assert len(rl.resources) == 1
    r = rl.resources[0]
    assert r.resource_id == 1 and r.task_count == 1
    # the totalled work survives the monthly bucketing (10 working days == 4800 min)
    assert round(r.total_work_minutes) == 10 * DAY


def test_over_allocation_is_flagged() -> None:
    # two full-time tasks on the same resource over the same span => 2x its daily capacity
    a = (Assignment(resource_id=1, work_minutes=22 * DAY, units=1.0),)
    sch = _sched([_task(1, 22, a), _task(2, 22, a)])
    rl = compute_resource_loading(sch, compute_cpm(sch))
    r = next(res for res in rl.resources if res.resource_id == 1)
    assert r.over_allocated_periods, "a doubly-booked resource must show over-allocated months"
    # the over-allocated month's booked load exceeds its capacity
    over = next(p for p in r.series if p.over_allocated)
    assert over.load_minutes > over.capacity_minutes


def test_golden_schedule_loads_without_error() -> None:
    sch = parse_mspdi(str(GOLDEN))
    rl = compute_resource_loading(sch, compute_cpm(sch))
    assert rl.has_work is True
    assert rl.resources and rl.periods
    # every resource's series is sorted and self-consistent
    for r in rl.resources:
        assert r.total_work_minutes >= 0
        assert all(p.capacity_minutes >= 0 for p in r.series)
