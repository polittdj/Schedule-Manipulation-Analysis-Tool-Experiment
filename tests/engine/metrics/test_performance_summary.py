"""Performance Analysis Summary metrics (operator 2026-07-10, ADR-0182) — the engine side of
the PerformanceAnalysisSummary workbook recreation: G1 monthly census, G2/G3 bow-wave flow +
index curves, G4 workoff burden (with the negative backlog mirror), G5 duration ratio, and the
G6/G7 to-go quad ingredients. Synthetic schedule, every count hand-checkable."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics.performance_summary import (
    activity_flow,
    duration_ratio,
    month_axis,
    to_go_snapshot,
    work_to_go_census,
    workoff_burden,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480
JAN = dt.datetime(2025, 1, 6, 8, 0)
FEB = dt.datetime(2025, 2, 3, 8, 0)
MAR = dt.datetime(2025, 3, 3, 8, 0)
APR = dt.datetime(2025, 4, 7, 8, 0)
DD = dt.datetime(2025, 2, 28, 17, 0)  # data date: end of February


def _sched() -> Schedule:
    """Jan..Apr 2025. UID 1 done on plan in Jan; UID 2 started 40 days late (Feb baseline,
    started/finished Mar+); UID 3 not started, baseline Feb (past due), now forecast Apr;
    UID 4 not started, baseline Mar, forecast Apr (future delayed); UID 5 a summary."""
    tasks = (
        Task(  # completed exactly per baseline, January
            unique_id=1,
            name="OnPlan",
            duration_minutes=5 * DAY,
            baseline_duration_minutes=10 * DAY,
            percent_complete=100.0,
            baseline_start=JAN,
            baseline_finish=JAN + dt.timedelta(days=4),
            actual_start=JAN,
            actual_finish=JAN + dt.timedelta(days=4),
            start=JAN,
            finish=JAN + dt.timedelta(days=4),
        ),
        Task(  # baselined Feb 3, started Mar 15 (40 days late), finished Mar 20 (late 41d)
            unique_id=2,
            name="LateStarter",
            duration_minutes=5 * DAY,
            baseline_duration_minutes=5 * DAY,
            percent_complete=100.0,
            baseline_start=FEB,
            baseline_finish=dt.datetime(2025, 2, 7, 17, 0),
            actual_start=dt.datetime(2025, 3, 15, 8, 0),
            actual_finish=dt.datetime(2025, 3, 20, 17, 0),
            start=dt.datetime(2025, 3, 15, 8, 0),
            finish=dt.datetime(2025, 3, 20, 17, 0),
        ),
        Task(  # past-due baseline (Feb ≤ DD), not started, forecast April
            unique_id=3,
            name="PastDue",
            duration_minutes=5 * DAY,
            baseline_start=FEB,
            baseline_finish=dt.datetime(2025, 2, 7, 17, 0),
            start=APR,
            finish=APR + dt.timedelta(days=4),
        ),
        Task(  # future baseline (Mar > DD), forecast April (delayed a month)
            unique_id=4,
            name="FutureDelayed",
            duration_minutes=5 * DAY,
            baseline_start=MAR,
            baseline_finish=dt.datetime(2025, 3, 7, 17, 0),
            start=APR,
            finish=APR + dt.timedelta(days=4),
        ),
        Task(
            unique_id=5,
            name="Summary",
            duration_minutes=0,
            is_summary=True,
            start=JAN,
            finish=APR + dt.timedelta(days=4),
        ),
    )
    return Schedule(name="S", project_start=JAN, status_date=DD, tasks=tasks)


def test_month_axis_spans_all_dates() -> None:
    axis = month_axis(_sched())
    assert [m.isoformat()[:7] for m in axis] == ["2025-01", "2025-02", "2025-03", "2025-04"]


def test_g1_census_counts_active_completed_togo_and_longest_path() -> None:
    c = work_to_go_census(_sched(), critical_uids=frozenset({3, 4}))
    rows = {m.month: m for m in c.months}
    assert c.status_month == "2025-02"
    jan = rows["2025-01"]
    # UID 1 active (its span) + summary active
    assert jan.normal == 1 and jan.summaries == 1 and jan.milestones == 0
    assert jan.tm_completed == 1 and jan.tm_to_go == 0 and jan.lp_tm == 0
    apr = rows["2025-04"]
    # UIDs 3 and 4 forecast in April (+ the summary), both to-go, both on the longest path
    assert apr.normal == 2 and apr.tm_to_go == 2 and apr.normal_to_go == 2
    assert apr.lp_tm == 2 and apr.lp_normal == 2 and apr.tm_completed == 0
    mar = rows["2025-03"]
    assert mar.tm_completed == 1  # UID 2's actual span sits in March


def test_g2_flow_counts_and_late_buckets() -> None:
    f = activity_flow(_sched())
    rows = {m.month: m for m in f.months}
    feb, mar, apr = rows["2025-02"], rows["2025-03"], rows["2025-04"]
    # baselined: UID 2 and 3 in Feb, UID 4 in Mar
    assert feb.baselined_starts == 2 and mar.baselined_starts == 1
    # actual starts: UID 1 Jan, UID 2 Mar
    assert rows["2025-01"].actual_starts == 1 and mar.actual_starts == 1
    # UID 2 started 40 days after baseline → the 31-60 bucket, at its ACTUAL month (March)
    assert mar.started_late_60 == 1 and mar.started_late_30 == 0 and mar.started_late_over == 0
    assert mar.finished_late_60 == 1
    # scheduled starts land where the current dates sit (UIDs 3+4 → April)
    assert apr.scheduled_starts == 2


def test_g3_bei_hmi_curves_stop_at_the_data_date() -> None:
    f = activity_flow(_sched())
    rows = {m.month: m for m in f.months}
    jan, feb = rows["2025-01"], rows["2025-02"]
    # January: 1 baselined start (UID 1), 1 actual → BEI-starts 1.0; hit in its month → HMI 1.0
    assert jan.bei_starts == 1.0 and jan.hmi_starts == 1.0
    # February: cumulative 3 baselined starts, still 1 actual → 0.33; both Feb-due starts missed
    assert feb.bei_starts == 0.33 and feb.hmi_starts == 0.0
    assert feb.hmi_starts_roll3 == 0.5  # average of the two defined monthly values
    # after the data date no index is fabricated
    assert rows["2025-03"].bei_starts is None and rows["2025-04"].hmi_finishes is None
    assert feb.cum_baselined_starts == 3 and feb.cum_actual_starts == 1


def test_g4_workoff_burden_categories_and_negative_backlog_mirror() -> None:
    b = workoff_burden(_sched())
    rows = {m.month: m for m in b.months}
    jan, feb, mar, apr = (rows[k] for k in ("2025-01", "2025-02", "2025-03", "2025-04"))
    assert jan.s_bl_plan == 1  # UID 1 started in its baseline month
    assert mar.s_workoff == 1  # UID 2 burned its Feb baseline in March
    # UID 3 (past-due baseline) forecast April; UID 4 (future baseline, slipped) also April
    assert apr.s_past_due == 1 and apr.s_delayed == 1
    # the un-started backlog mirrors NEGATIVE at the baselined months (UID 3 Feb, UID 4 Mar)
    assert feb.s_backlog == -1 and mar.s_backlog == -1 and jan.s_backlog == 0
    # finishes categorize independently (UID 2 finished March vs Feb baseline → workoff)
    assert mar.f_workoff == 1 and apr.f_past_due == 1 and apr.f_delayed == 1


_LATE_KEYS = (
    "started_late_30",
    "started_late_60",
    "started_late_over",
    "finished_late_30",
    "finished_late_60",
    "finished_late_over",
)


def test_g2_late_bucket_uids_match_the_counts_they_accompany() -> None:
    # the late-bucket BARS are click-to-drill: each carries the exact activity IDs it counts.
    f = activity_flow(_sched())
    rows = {m.month: m for m in f.months}
    mar = rows["2025-03"]
    # UID 2 is the only late activity (40+ days past its Feb baseline, landing in March)
    assert mar.started_late_60_uids == (2,) and mar.finished_late_60_uids == (2,)
    for m in f.months:
        for k in _LATE_KEYS:
            assert len(getattr(m, f"{k}_uids")) == getattr(m, k)


_BURDEN_KEYS = (
    "s_bl_plan",
    "s_early",
    "s_workoff",
    "s_past_due",
    "s_delayed",
    "s_backlog",
    "f_bl_plan",
    "f_early",
    "f_workoff",
    "f_past_due",
    "f_delayed",
    "f_backlog",
)


def test_g4_burden_category_uids_match_the_counts_they_accompany() -> None:
    # the workoff-burden BARS are click-to-drill: each category carries the activities it counts.
    b = workoff_burden(_sched())
    rows = {m.month: m for m in b.months}
    jan, feb, mar, apr = (rows[k] for k in ("2025-01", "2025-02", "2025-03", "2025-04"))
    assert jan.s_bl_plan_uids == (1,)  # UID 1 started in its baseline month
    assert mar.s_workoff_uids == (2,)  # UID 2 burned its Feb baseline in March
    assert apr.s_past_due_uids == (3,) and apr.s_delayed_uids == (4,)
    # backlog is a NEGATIVE count mirrored below the axis; its UID list carries |count| activities
    assert feb.s_backlog_uids == (3,) and mar.s_backlog_uids == (4,)
    assert mar.f_workoff_uids == (2,)
    for m in b.months:
        for k in _BURDEN_KEYS:
            assert len(getattr(m, f"{k}_uids")) == abs(getattr(m, k))


def test_g5_duration_ratio_scurve_and_exclusions() -> None:
    d = duration_ratio(_sched())
    # completed normal tasks: UID 1 (5d actual vs 10d baseline → 0.5), UID 2 (5 vs 5 → 1.0)
    assert d.n == 2 and d.n_excluded == 0
    assert [p.drm for p in d.points] == [0.5, 1.0]
    assert d.points[0].uid == 1 and d.points[0].cum_prob == 0.5
    assert d.points[1].cum_prob == 1.0
    assert d.drm_min == 0.5 and d.drm_max == 1.0 and d.drm_avg == 0.75
    assert d.bins and sum(b.count for b in d.bins) == 2  # middle-70% of n=2 keeps both
    # a completed task without a baseline duration is excluded and DISCLOSED, never imputed
    sch2 = _sched().model_copy(
        update={
            "tasks": (
                *_sched().tasks,
                Task(
                    unique_id=6,
                    name="NoBaseline",
                    duration_minutes=DAY,
                    percent_complete=100.0,
                    actual_start=JAN,
                    actual_finish=JAN + dt.timedelta(days=1),
                ),
            )
        }
    )
    d2 = duration_ratio(sch2)
    assert d2.n == 2 and d2.n_excluded == 1


def test_g6_g7_to_go_snapshot_ratios_and_critical_share() -> None:
    s = to_go_snapshot(_sched(), critical_uids=frozenset({3, 4}))
    # after the Feb-28 DD the baseline has 1 start (UID 4, Mar) and 1 finish remaining
    assert s.baselined_to_start_remaining == 1 and s.baselined_to_finish_remaining == 1
    # to-go: UIDs 3 and 4 have not started / not finished
    assert s.scheduled_to_start_to_go == 2 and s.scheduled_to_finish_to_go == 2
    assert s.start_ratio == 2.0 and s.finish_ratio == 2.0  # twice the baseline's remaining work
    assert s.tm_to_go == 2 and s.critical_to_go == 2 and s.critical_share == 1.0
    # with no status date the remaining-baseline denominators are undefined → ratios None
    s2 = to_go_snapshot(_sched().model_copy(update={"status_date": None}), frozenset())
    assert s2.start_ratio is None and s2.finish_ratio is None
