"""WBS-breakdown tests — completion + Earned Schedule pivoted by WBS (ADR-0041, PBIX 8/9).

Hand-built groups (top-level segment rollup, ahead/behind, duration ratios, per-group
SPI(t)) plus golden reconciliation over Project5 (groups sum to the schedule totals).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import compute_wbs_breakdown
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def _task(uid: int, **kw: object) -> Task:
    kw.setdefault("duration_minutes", 480)
    return Task(unique_id=uid, name=f"T{uid}", **kw)


def _sched(tasks: list[Task], status: dt.datetime | None = None) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=(), status_date=status
    )


def test_groups_roll_up_to_top_level_segment_and_sort_numerically() -> None:
    s = _sched(
        [
            _task(1, wbs="2.1"),
            _task(2, wbs="2.3"),
            _task(3, wbs="10.1"),
            _task(4, wbs="1.5"),
            _task(5, wbs=None),  # -> "(none)"
        ]
    )
    groups = compute_wbs_breakdown(s)
    # numeric sort: 1, 2, 10, then "(none)" last
    assert [g.wbs for g in groups] == ["1", "2", "10", "(none)"]
    by = {g.wbs: g for g in groups}
    assert by["2"].total == 2  # 2.1 and 2.3 roll into "2"
    assert by["1"].total == 1 and by["10"].total == 1 and by["(none)"].total == 1


def test_alphanumeric_wbs_sorts_lexicographically_after_numeric() -> None:
    # mixed numeric + alpha top-level codes: numerics first (by value), then alpha
    # (lexicographic), then "(none)" last
    s = _sched(
        [
            _task(1, wbs="ENG.1"),
            _task(2, wbs="2.1"),
            _task(3, wbs="ADMIN.4"),
            _task(4, wbs=None),
        ]
    )
    assert [g.wbs for g in compute_wbs_breakdown(s)] == ["2", "ADMIN", "ENG", "(none)"]


def test_completion_split_and_duration_ratio_within_a_group() -> None:
    s = _sched(
        [
            # WBS "1": one early finisher, one late finisher, one to-go
            _task(
                1,
                wbs="1.1",
                percent_complete=100.0,
                duration_minutes=480,
                baseline_duration_minutes=960,  # actual shorter than baseline -> ratio 0.5
                baseline_finish=dt.datetime(2025, 1, 20, 17, 0),
                actual_finish=dt.datetime(2025, 1, 15, 17, 0),  # 5 days early
            ),
            _task(
                2,
                wbs="1.2",
                percent_complete=100.0,
                duration_minutes=960,
                baseline_duration_minutes=480,  # actual longer -> ratio 2.0
                baseline_finish=dt.datetime(2025, 1, 20, 17, 0),
                actual_finish=dt.datetime(2025, 1, 24, 17, 0),  # 4 days late
            ),
            _task(3, wbs="1.3", percent_complete=0.0),
        ]
    )
    g = compute_wbs_breakdown(s)[0]
    assert g.wbs == "1"
    assert g.total == 3 and g.completed == 2 and g.not_completed == 1
    assert g.completed_ahead == 1 and g.completed_behind == 1 and g.completed_on_schedule == 0
    assert g.avg_days_ahead == 5.0 and g.avg_days_late == 4.0
    assert g.avg_completion_variance == round((-5 + 4) / 2, 1)  # signed mean
    assert g.longer_than_planned == 1 and g.shorter_than_planned == 1
    assert g.duration_ratio_min == 0.5 and g.duration_ratio_max == 2.0
    assert g.duration_ratio_avg == round((0.5 + 2.0) / 2, 2)


def test_spi_t_per_group_present_when_completions_and_baseline_exist() -> None:
    status = dt.datetime(2025, 3, 1, 17, 0)
    s = _sched(
        [
            _task(
                1,
                wbs="1.1",
                percent_complete=100.0,
                baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
                actual_finish=dt.datetime(2025, 1, 8, 17, 0),
            ),
            _task(
                2, wbs="1.2", percent_complete=0.0, baseline_finish=dt.datetime(2025, 2, 20, 17, 0)
            ),
            # WBS "2": no completions -> SPI(t) None (never fabricated)
            _task(
                3, wbs="2.1", percent_complete=0.0, baseline_finish=dt.datetime(2025, 1, 9, 17, 0)
            ),
        ],
        status=status,
    )
    by = {g.wbs: g for g in compute_wbs_breakdown(s)}
    assert by["1"].spi_t is not None and 0.0 < by["1"].spi_t < 1.0  # behind (ES << AT)
    assert by["1"].earned_schedule_days is not None and by["1"].actual_time_days is not None
    assert by["2"].spi_t is None  # no completions in WBS 2
    assert by["2"].earned_schedule_days is None


def test_no_status_date_yields_no_earned_schedule() -> None:
    s = _sched(
        [
            _task(
                1,
                wbs="1.1",
                percent_complete=100.0,
                baseline_finish=dt.datetime(2025, 1, 8, 17, 0),
                actual_finish=dt.datetime(2025, 1, 8, 17, 0),
            )
        ]
    )
    g = compute_wbs_breakdown(s)[0]
    assert g.completed == 1
    assert g.spi_t is None and g.earned_schedule_days is None  # no data date -> AT undefined


def test_golden_groups_reconcile_to_schedule_totals(golden_project5: Schedule) -> None:
    groups = compute_wbs_breakdown(golden_project5)
    assert len(groups) == 22  # top-level WBS segments 1..22 in Project5
    assert sum(g.total for g in groups) == 126  # every non-summary activity is grouped once
    assert sum(g.completed for g in groups) == 27  # the golden completed count
    # actual time (AT) is the schedule-level basis — identical across every measured group
    ats = {g.actual_time_days for g in groups if g.actual_time_days is not None}
    assert len(ats) == 1
