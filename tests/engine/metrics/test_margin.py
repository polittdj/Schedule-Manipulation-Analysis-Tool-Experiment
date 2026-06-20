"""Schedule-margin metrics — buffer activities identified by the operator naming convention.

Synthetic networks verify: effective margin == its duration when margin drives the finish; 0 when
margin sits on a path with slack (still counted in total); case-insensitive substring name match;
summary exclusion; the all-zeros empty case; and total == sum of durations.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics.margin import (
    MARGIN_KEYWORD,
    compute_margin,
    is_margin_task,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480  # working minutes in one 8-hour day


def _sched(tasks: tuple[Task, ...], rels: tuple[Relationship, ...] = ()) -> Schedule:
    return Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels)


def test_keyword_is_lowercase_margin() -> None:
    assert MARGIN_KEYWORD == "margin"


def test_is_margin_task_substring_and_case_insensitive() -> None:
    assert is_margin_task(
        Task(unique_id=1, name="USA Schedule MARGIN: Pre-Ship", duration_minutes=0)
    )
    assert is_margin_task(Task(unique_id=2, name="margin", duration_minutes=0))
    assert is_margin_task(Task(unique_id=3, name="Reserve Margin Buffer", duration_minutes=0))
    assert not is_margin_task(Task(unique_id=4, name="Integration", duration_minutes=0))


def test_summary_task_named_margin_is_excluded() -> None:
    assert not is_margin_task(
        Task(unique_id=1, name="Margin Rollup", duration_minutes=480, is_summary=True)
    )


def test_margin_on_driving_chain_effective_equals_its_duration() -> None:
    # A (1d) -> MARGIN (2d) -> B (1d), serial: zeroing MARGIN pulls the finish in by 2 days.
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="Schedule MARGIN", duration_minutes=2 * DAY),
        Task(unique_id=3, name="B", duration_minutes=DAY),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
    )
    sch = _sched(tasks, rels)
    m = compute_margin(sch, compute_cpm(sch))
    assert m.count == 1
    assert m.total_margin_days == 2.0
    assert m.effective_margin_days == 2.0  # zeroing it pulls the finish in by its full duration
    assert m.on_critical_count == 1
    assert m.tasks[0].unique_id == 2
    assert m.tasks[0].on_critical is True
    assert m.tasks[0].duration_days == 2.0


def test_margin_off_critical_path_effective_zero_but_counted() -> None:
    # Long driving chain A(5d)->B(5d) (finish 10d); a parallel short MARGIN(1d) branch off A has
    # slack, so zeroing it does not move the finish: effective == 0, but it counts toward total.
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=5 * DAY),
        Task(unique_id=2, name="B", duration_minutes=5 * DAY),
        Task(unique_id=3, name="MARGIN reserve", duration_minutes=DAY),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=1, successor_id=3),
    )
    sch = _sched(tasks, rels)
    cpm = compute_cpm(sch)
    m = compute_margin(sch, cpm)
    assert m.count == 1
    assert m.total_margin_days == 1.0  # counted in total
    assert m.effective_margin_days == 0.0  # protects nothing — finish unchanged
    assert m.on_critical_count == 0
    assert m.tasks[0].on_critical is False


def test_total_is_sum_of_margin_durations() -> None:
    # Two parallel margin activities (2d + 3d) both feeding a 1d sink; total == 5d.
    tasks = (
        Task(unique_id=1, name="MARGIN one", duration_minutes=2 * DAY),
        Task(unique_id=2, name="schedule margin two", duration_minutes=3 * DAY),
        Task(unique_id=3, name="Sink", duration_minutes=DAY),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=3),
    )
    sch = _sched(tasks, rels)
    m = compute_margin(sch, compute_cpm(sch))
    assert m.count == 2
    assert m.total_margin_days == 5.0
    # sorted by duration desc: the 3-day margin (UID 2) comes first
    assert [t.unique_id for t in m.tasks] == [2, 1]
    assert [t.duration_days for t in m.tasks] == [3.0, 2.0]


def test_no_margin_schedule_is_all_zeros() -> None:
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
    )
    rels = (Relationship(predecessor_id=1, successor_id=2),)
    sch = _sched(tasks, rels)
    m = compute_margin(sch, compute_cpm(sch))
    assert m.count == 0
    assert m.total_margin_days == 0.0
    assert m.effective_margin_days == 0.0
    assert m.on_critical_count == 0
    assert m.tasks == ()
