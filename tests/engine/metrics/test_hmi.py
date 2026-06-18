"""Hit or Miss Index (HMI) — period-over-period baseline execution (ADR-0087)."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.metrics import CheckStatus, compute_hmi
from schedule_forensics.engine.trend import compute_hmi_trend, order_versions
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

PREV = dt.datetime(2025, 1, 1, 8, 0)  # previous data date
NOW = dt.datetime(2025, 2, 1, 8, 0)  # current data date — period is (PREV, NOW]
IN = dt.datetime(2025, 1, 15, 8, 0)  # inside the period
EARLY = dt.datetime(2024, 12, 20, 8, 0)  # before the period
LATE = dt.datetime(2025, 3, 1, 8, 0)  # after the period


def _sched(tasks: list[Task], status: dt.datetime | None = NOW, name: str = "v") -> Schedule:
    return Schedule(
        name=name,
        source_file=f"{name}.mpp",
        project_start=PREV,
        status_date=status,
        tasks=tuple(tasks),
    )


def test_hit_is_baselined_and_completed_within_the_period() -> None:
    # baselined to finish this period AND actually completed this period -> hit, HMI 1.0
    t = Task(
        unique_id=1,
        name="hit",
        duration_minutes=480,
        baseline_finish=IN,
        percent_complete=100.0,
        actual_finish=dt.datetime(2025, 1, 20, 8, 0),
    )
    h = compute_hmi(_sched([t]), PREV)["hmi_tasks"]
    assert h.count == 1 and h.population == 1 and h.value == 1.0
    assert h.offender_uids == ()


def test_miss_is_baselined_this_period_but_not_completed() -> None:
    hit = Task(
        unique_id=1,
        name="hit",
        duration_minutes=480,
        baseline_finish=IN,
        percent_complete=100.0,
        actual_finish=dt.datetime(2025, 1, 20, 8, 0),
    )
    miss = Task(unique_id=2, name="miss", duration_minutes=480, baseline_finish=IN)  # not done
    h = compute_hmi(_sched([hit, miss]), PREV)["hmi_tasks"]
    assert h.count == 1 and h.population == 2 and h.value == 0.5
    assert h.offender_uids == (2,)  # the miss is cited


def test_activities_baselined_outside_the_period_are_excluded() -> None:
    # only IN-period baseline finishes form the population; EARLY/LATE are not "due this period"
    before = Task(unique_id=1, name="before", duration_minutes=480, baseline_finish=EARLY)
    after = Task(unique_id=2, name="after", duration_minutes=480, baseline_finish=LATE)
    due = Task(
        unique_id=3,
        name="due",
        duration_minutes=480,
        baseline_finish=IN,
        percent_complete=100.0,
        actual_finish=dt.datetime(2025, 1, 18, 8, 0),
    )
    h = compute_hmi(_sched([before, after, due]), PREV)["hmi_tasks"]
    assert h.population == 1 and h.count == 1  # only UID 3 is in the period


def test_finished_before_the_period_is_not_credited_here() -> None:
    # baselined to finish this period but the work actually landed in an EARLIER period:
    # Finish<=PrevTimeNow, so it is not a hit *here* (it was a hit in its own period) -> a miss.
    early_done = Task(
        unique_id=1,
        name="early",
        duration_minutes=480,
        baseline_finish=IN,
        percent_complete=100.0,
        actual_finish=EARLY,
    )
    h = compute_hmi(_sched([early_done]), PREV)["hmi_tasks"]
    assert h.count == 0 and h.population == 1 and h.value == 0.0
    assert h.offender_uids == (1,)


def test_tasks_and_milestones_are_scored_separately() -> None:
    task = Task(unique_id=1, name="t", duration_minutes=480, baseline_finish=IN)  # task miss
    ms = Task(
        unique_id=2,
        name="m",
        duration_minutes=0,
        is_milestone=True,
        baseline_finish=IN,
        percent_complete=100.0,
        actual_finish=dt.datetime(2025, 1, 10, 8, 0),
    )  # milestone hit
    out = compute_hmi(_sched([task, ms]), PREV)
    assert out["hmi_tasks"].count == 0 and out["hmi_tasks"].population == 1
    assert out["hmi_milestones"].count == 1 and out["hmi_milestones"].population == 1
    assert out["hmi_milestones"].value == 1.0


def test_na_without_a_previous_data_date_or_empty_period() -> None:
    t = Task(
        unique_id=1,
        name="t",
        duration_minutes=480,
        baseline_finish=IN,
        percent_complete=100.0,
        actual_finish=IN,
    )
    assert compute_hmi(_sched([t]), None)["hmi_tasks"].status is CheckStatus.NOT_APPLICABLE
    # non-advancing data date (now <= prev) -> NA
    assert compute_hmi(_sched([t]), NOW)["hmi_tasks"].status is CheckStatus.NOT_APPLICABLE
    # nothing baselined in the period -> NA (count 0 of 0)
    out_of = Task(unique_id=2, name="x", duration_minutes=480, baseline_finish=LATE)
    na = compute_hmi(_sched([out_of]), PREV)["hmi_tasks"]
    assert na.status is CheckStatus.NOT_APPLICABLE and na.population == 0


def test_hmi_trend_first_version_has_no_predecessor() -> None:
    # three monthly snapshots; each scored against the previous one's data date.
    def ver(label: str, status: dt.datetime, tasks: list[Task]) -> Schedule:
        return _sched(tasks, status=status, name=label)

    jan = ver("jan", dt.datetime(2025, 1, 1, 8, 0), [])
    feb = ver(
        "feb",
        dt.datetime(2025, 2, 1, 8, 0),
        [
            Task(
                unique_id=1,
                name="hit",
                duration_minutes=480,
                baseline_finish=IN,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 20, 8, 0),
            ),
            Task(unique_id=2, name="miss", duration_minutes=480, baseline_finish=IN),
        ],
    )
    mar = ver(
        "mar",
        dt.datetime(2025, 3, 1, 8, 0),
        [
            Task(
                unique_id=1,
                name="hit",
                duration_minutes=480,
                baseline_finish=dt.datetime(2025, 2, 15, 8, 0),
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 2, 20, 8, 0),
            ),
        ],
    )
    series = compute_hmi_trend(order_versions([mar, jan, feb]))  # unordered in -> ordered by date
    assert series.labels == ("jan.mpp", "feb.mpp", "mar.mpp")
    assert series.task_values[0] is None  # jan has no predecessor
    assert series.task_values[1] == 0.5  # feb: 1 hit of 2 due (vs jan's data date)
    assert series.task_values[2] == 1.0  # mar: 1 hit of 1 due (vs feb's data date)
    assert series.task_offenders[1] == (2,)


def test_hmi_trend_needs_at_least_two_versions() -> None:
    with pytest.raises(ValueError, match="at least two"):
        compute_hmi_trend([_sched([], name="solo")])
