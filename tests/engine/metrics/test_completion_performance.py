"""Completion-performance tests — hand-verified splits/averages/ratios + golden pins (M15)."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import compute_completion_performance
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _completed(uid: int, *, late_days: int, duration_days: int = 1, baseline_days: int = 1) -> Task:
    baseline_finish = dt.datetime(2025, 1, 10, 17, 0)
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=duration_days * DAY,
        baseline_duration_minutes=baseline_days * DAY,
        percent_complete=100.0,
        baseline_finish=baseline_finish,
        actual_start=MON,
        actual_finish=baseline_finish + dt.timedelta(days=late_days),
    )


def test_ahead_on_behind_split_averages_and_duration_ratios() -> None:
    tasks = [
        _completed(1, late_days=-2, duration_days=2, baseline_days=1),  # early; ran long
        _completed(2, late_days=0),  # on schedule; on duration
        _completed(3, late_days=4, duration_days=1, baseline_days=2),  # late; ran short
        Task(unique_id=4, name="todo", duration_minutes=DAY),  # incomplete — excluded
    ]
    cp = compute_completion_performance(Schedule(name="s", project_start=MON, tasks=tuple(tasks)))
    assert cp["completed_ahead"].count == 1 and cp["completed_ahead"].offender_uids == (1,)
    assert cp["completed_on_schedule"].count == 1
    assert cp["completed_behind"].count == 1 and cp["completed_behind"].offender_uids == (3,)
    assert cp["completed_ahead"].population == 3
    assert cp["avg_days_ahead"].value == 2.0
    assert cp["avg_days_late"].value == 4.0
    assert cp["avg_completion_variance"].value == 0.7  # (-2 + 0 + 4) / 3
    assert cp["longer_than_planned"].count == 1 and cp["longer_than_planned"].offender_uids == (1,)
    assert cp["shorter_than_planned"].count == 1
    assert cp["duration_ratio_min"].value == 0.5
    assert cp["duration_ratio_max"].value == 2.0
    assert cp["duration_ratio_avg"].value == 1.17  # (2 + 1 + 0.5) / 3


def test_mei_counts_milestones_only_and_cites_the_unfinished_due() -> None:
    status = dt.datetime(2025, 2, 28, 17, 0)
    due = dt.datetime(2025, 2, 1, 17, 0)
    tasks = [
        Task(  # due milestone, finished -> numerator
            unique_id=1,
            name="M-done",
            duration_minutes=0,
            is_milestone=True,
            percent_complete=100.0,
            baseline_finish=due,
            actual_finish=due,
        ),
        Task(  # due milestone, NOT finished -> offender
            unique_id=2,
            name="M-missed",
            duration_minutes=0,
            is_milestone=True,
            baseline_finish=due,
        ),
        Task(  # a finished normal activity must not leak into the milestone index
            unique_id=3,
            name="task",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=due,
            actual_start=MON,
            actual_finish=due,
        ),
    ]
    cp = compute_completion_performance(
        Schedule(name="s", project_start=MON, status_date=status, tasks=tuple(tasks))
    )
    assert cp["mei"].count == 1 and cp["mei"].population == 2
    assert cp["mei"].value == 0.5
    assert cp["mei"].offender_uids == (2,)


def test_mei_and_staleness_are_na_without_inputs() -> None:
    cp = compute_completion_performance(
        Schedule(
            name="s",
            project_start=MON,
            tasks=(Task(unique_id=1, name="A", duration_minutes=DAY),),
        )
    )
    assert cp["mei"].population == 0  # no status date -> NA shape, never fabricated
    assert cp["elapsed_since_last_finish"].population == 0


def test_staleness_share_of_elapsed_schedule() -> None:
    # 59 elapsed days, last actual finish 31 days in -> 28 quiet days = 47.5%
    status = dt.datetime(2025, 3, 6, 17, 0)
    tasks = [
        Task(
            unique_id=1,
            name="A",
            duration_minutes=DAY,
            percent_complete=100.0,
            actual_start=MON,
            actual_finish=dt.datetime(2025, 2, 6, 17, 0),
        ),
        Task(unique_id=2, name="B", duration_minutes=DAY),
    ]
    cp = compute_completion_performance(
        Schedule(name="s", project_start=MON, status_date=status, tasks=tuple(tasks))
    )
    stale = cp["elapsed_since_last_finish"]
    assert (stale.count, stale.population) == (28, 59)
    assert stale.value == 47.5


def test_golden_pins(golden_project2: Schedule, golden_project5: Schedule) -> None:
    p2 = compute_completion_performance(golden_project2)
    assert p2["completed_on_schedule"].count == 9  # matches Completed-On-Time (BFC basis)
    assert p2["completed_behind"].count == 11
    assert p2["avg_days_late"].value == 25.2
    assert p2["duration_ratio_max"].value == 3.33
    p5 = compute_completion_performance(golden_project5)
    assert p5["completed_behind"].count == 18 and p5["completed_behind"].population == 27
    assert p5["avg_completion_variance"].value == 26.1
    assert p5["elapsed_since_last_finish"].value == 11.2
