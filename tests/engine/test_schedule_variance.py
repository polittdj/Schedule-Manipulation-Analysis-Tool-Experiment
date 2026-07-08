"""Schedule-variance-in-time engine tests (handbook §7.3.3.1 — SVt = ES - AT).

SVt reuses the canonical ``earned_schedule`` so it cannot diverge from SPI(t); the per-activity
variance is the working-time finish slip (actual - baseline). Parity-isolated dataclasses, no CPM.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.metrics.evm import compute_schedule_variance, earned_schedule
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday
DAY = 480


def _task(uid: int, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=DAY, **kw)


def _sched(tasks: list[Task], status: dt.datetime | None = None) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks), status_date=status)


def test_svt_undefined_without_status_or_completions() -> None:
    sv = compute_schedule_variance(_sched([_task(1)]), [_task(1)])
    assert sv.svt_days is None
    assert sv.es_days is None and sv.at_days is None


def test_svt_matches_earned_schedule_components() -> None:
    # three baselined activities; two complete by a status date two weeks out
    tasks = [
        _task(1, baseline_finish=dt.datetime(2025, 1, 8, 17, 0), percent_complete=100.0),
        _task(2, baseline_finish=dt.datetime(2025, 1, 15, 17, 0), percent_complete=100.0),
        _task(3, baseline_finish=dt.datetime(2025, 1, 22, 17, 0), percent_complete=0.0),
    ]
    sched = _sched(tasks, status=dt.datetime(2025, 1, 20, 8, 0))
    ns = non_summary(sched)
    es = earned_schedule(sched, ns)
    assert es is not None
    sv = compute_schedule_variance(sched, ns)
    wmpd = sched.calendar.working_minutes_per_day or DAY
    assert sv.svt_days == round((es.es_minutes - es.at_minutes) / wmpd, 1)
    assert sv.es_days == round(es.es_minutes / wmpd, 1)
    assert sv.at_days == round(es.at_minutes / wmpd, 1)


def test_per_activity_variance_positive_when_late() -> None:
    # finished a week after baseline → positive (unfavorable) variance of 5 working days
    tasks = [
        _task(
            1,
            baseline_finish=dt.datetime(2025, 1, 8, 8, 0),
            actual_finish=dt.datetime(2025, 1, 15, 8, 0),
            percent_complete=100.0,
        )
    ]
    sched = _sched(tasks, status=dt.datetime(2025, 1, 16, 8, 0))
    sv = compute_schedule_variance(sched, non_summary(sched))
    assert sv.completed == 1
    assert sv.worst[0].unique_id == 1
    assert sv.worst[0].variance_days == 5.0  # Jan 8 → Jan 15 is 5 working days
    assert sv.mean_activity_variance_days == 5.0


def test_per_activity_variance_negative_when_early() -> None:
    tasks = [
        _task(
            1,
            baseline_finish=dt.datetime(2025, 1, 15, 8, 0),
            actual_finish=dt.datetime(2025, 1, 8, 8, 0),
            percent_complete=100.0,
        )
    ]
    sched = _sched(tasks, status=dt.datetime(2025, 1, 16, 8, 0))
    sv = compute_schedule_variance(sched, non_summary(sched))
    assert sv.worst[0].variance_days == -5.0


def test_activities_without_both_finishes_are_excluded() -> None:
    tasks = [
        _task(1, actual_finish=dt.datetime(2025, 1, 8, 8, 0)),  # no baseline
        _task(2, baseline_finish=dt.datetime(2025, 1, 8, 8, 0)),  # no actual
    ]
    sv = compute_schedule_variance(_sched(tasks), tasks)
    assert sv.completed == 0


def test_start_variance_surfaces_in_progress_slippage() -> None:
    """Operator 2026-07-08: a statused schedule with few completions still shows START variance
    (actual start minus baseline start) for every started task — so progress is visible before
    activities finish. The Hard_File pair has actual starts without finishes."""
    tasks = [
        _task(  # started 5 wd late, not finished
            1,
            baseline_start=dt.datetime(2025, 1, 6, 8, 0),
            actual_start=dt.datetime(2025, 1, 13, 8, 0),
            percent_complete=40.0,
        ),
        _task(  # not started, only baselined
            2,
            baseline_start=dt.datetime(2025, 1, 20, 8, 0),
            baseline_finish=dt.datetime(2025, 1, 24, 8, 0),
        ),
    ]
    sched = _sched(tasks, status=dt.datetime(2025, 1, 16, 8, 0))
    sv = compute_schedule_variance(sched, non_summary(sched))
    assert sv.started == 1
    assert sv.worst_start[0].unique_id == 1
    assert sv.worst_start[0].variance_days == 5.0  # Jan 6 → Jan 13 is 5 working days
    assert sv.mean_start_variance_days == 5.0
    assert sv.baselined == 1  # only task 2 carries a baseline finish


def test_baselined_but_unstatused_reports_no_progress_but_counts_baselines() -> None:
    """The baselined-plan case (operator's first Hard_File version): baseline dates present, no
    actuals — SVt undefined and zero started/completed, but the baseline count is surfaced so the
    panel can point the operator at the statused version."""
    tasks = [
        _task(
            1,
            baseline_start=dt.datetime(2025, 1, 6, 8, 0),
            baseline_finish=dt.datetime(2025, 1, 8, 8, 0),
        ),
        _task(
            2,
            baseline_start=dt.datetime(2025, 1, 9, 8, 0),
            baseline_finish=dt.datetime(2025, 1, 10, 8, 0),
        ),
    ]
    sv = compute_schedule_variance(_sched(tasks, status=dt.datetime(2025, 1, 16, 8, 0)), tasks)
    assert sv.svt_days is None and sv.completed == 0 and sv.started == 0
    assert sv.baselined == 2
    assert sv.worst == ()
    assert sv.mean_activity_variance_days is None


def test_worst_is_sorted_descending_and_capped() -> None:
    tasks = []
    for i in range(1, 21):
        tasks.append(
            _task(
                i,
                baseline_finish=dt.datetime(2025, 1, 8, 8, 0),
                actual_finish=MON + dt.timedelta(days=i),
                percent_complete=100.0,
            )
        )
    sched = _sched(tasks, status=dt.datetime(2025, 3, 1, 8, 0))
    sv = compute_schedule_variance(sched, non_summary(sched), worst_cap=5)
    assert len(sv.worst) == 5
    vals = [v.variance_days for v in sv.worst]
    assert vals == sorted(vals, reverse=True)  # largest (latest) first
