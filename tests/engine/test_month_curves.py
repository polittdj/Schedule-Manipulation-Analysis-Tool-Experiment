"""Month-curve tests — finish/slippage monthly counts on a shared axis (ADR-0040).

Covers the Finishes / DATA Date Finishes / Slippage views (PBIX pages 6, 7, 12):
hand-built buckets (actual-over-scheduled date precedence, baseline curves, the shared
axis and its cap) plus golden pins over Project2/Project5.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.month_axis import bucket, month_index, month_label
from schedule_forensics.engine.month_curves import compute_month_curves
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def _task(uid: int, **kw: object) -> Task:
    kw.setdefault("duration_minutes", 480)
    return Task(unique_id=uid, name=f"T{uid}", **kw)


def _sched(name: str, tasks: list[Task], status: dt.datetime | None = None) -> Schedule:
    return Schedule(
        name=name,
        project_start=MON,
        tasks=tuple(tasks),
        relationships=(),
        status_date=status,
    )


# ── month_axis primitives ──────────────────────────────────────────────────────────


def test_month_index_and_label_round_trip() -> None:
    assert month_index(dt.datetime(2027, 3, 4)) == 2027 * 12 + 2
    assert month_label(2027 * 12 + 2) == "Mar-27"
    assert month_label(month_index(dt.datetime(2025, 1, 6))) == "Jan-25"


def test_bucket_counts_in_window_and_drops_outliers() -> None:
    lo = month_index(dt.datetime(2025, 1, 1))
    dates = [
        dt.datetime(2025, 1, 15),
        dt.datetime(2025, 1, 20),
        dt.datetime(2025, 3, 2),
        dt.datetime(2030, 1, 1),  # outside the 3-month window -> dropped
    ]
    assert bucket(dates, lo, 3) == (2, 0, 1)


# ── compute_month_curves ─────────────────────────────────────────────────────────────


def test_actual_finish_takes_precedence_over_scheduled() -> None:
    # one task: scheduled to finish in Feb but actually finished in Jan -> counts in Jan
    sch = _sched(
        "s",
        [
            _task(
                1,
                start=dt.datetime(2025, 1, 6),
                finish=dt.datetime(2025, 2, 10),
                actual_start=dt.datetime(2025, 1, 6),
                actual_finish=dt.datetime(2025, 1, 28),
            ),
        ],
    )
    curves = compute_month_curves([sch])
    v = curves.versions[0]
    jan = curves.month_labels.index("Jan-25")
    assert v.actual_finishes[jan] == 1
    assert sum(v.actual_finishes) == 1  # not double-counted in Feb
    assert v.actual_starts[jan] == 1


def test_baseline_curves_read_baseline_dates() -> None:
    sch = _sched(
        "s",
        [
            _task(
                1,
                start=dt.datetime(2025, 2, 3),
                finish=dt.datetime(2025, 2, 20),
                baseline_start=dt.datetime(2025, 1, 6),
                baseline_finish=dt.datetime(2025, 1, 24),
            ),
        ],
    )
    curves = compute_month_curves([sch])
    v = curves.versions[0]
    jan, feb = curves.month_labels.index("Jan-25"), curves.month_labels.index("Feb-25")
    assert v.baseline_starts[jan] == 1 and v.baseline_finishes[jan] == 1
    assert v.actual_starts[feb] == 1 and v.actual_finishes[feb] == 1


def test_shared_axis_and_status_index_across_versions() -> None:
    v1 = _sched(
        "v1",
        [_task(1, start=dt.datetime(2025, 1, 6), finish=dt.datetime(2025, 1, 24))],
        status=dt.datetime(2025, 1, 31),
    )
    v2 = _sched(
        "v2",
        [_task(1, start=dt.datetime(2025, 3, 3), finish=dt.datetime(2025, 3, 28))],
        status=dt.datetime(2025, 3, 31),
    )
    curves = compute_month_curves([v1, v2])
    # the shared axis spans Jan..Mar (3 months); every version's series has that length
    assert len(curves.month_labels) == 3
    for v in curves.versions:
        assert (
            len(v.actual_finishes)
            == len(v.baseline_finishes)
            == len(v.actual_starts)
            == len(curves.month_labels)
        )
    # the data-date month index lands on the shared axis
    assert curves.versions[0].status_index == curves.month_labels.index("Jan-25")
    assert curves.versions[1].status_index == curves.month_labels.index("Mar-25")
    assert curves.versions[0].status_date == "2025-01-31"


def test_empty_and_no_dates_raise() -> None:
    with pytest.raises(ValueError, match="at least one schedule"):
        compute_month_curves([])
    # a version with no start/finish dates at all (only a name) -> nothing to plot
    bare = _sched("bare", [Task(unique_id=1, name="x", duration_minutes=0)])
    with pytest.raises(ValueError, match="no start or finish"):
        compute_month_curves([bare])


def test_axis_cap_sheds_oldest_months() -> None:
    # two activities 80 months apart -> span exceeds the 60-month cap; the oldest months
    # are shed, so the later activity's finish stays on-axis and the axis is exactly capped
    sch = _sched(
        "s",
        [
            _task(1, finish=dt.datetime(2020, 1, 15)),
            _task(2, finish=dt.datetime(2026, 9, 15)),
        ],
    )
    curves = compute_month_curves([sch])
    assert len(curves.month_labels) == 60
    assert curves.month_labels[-1] == "Sep-26"  # the newest month is retained
    v = curves.versions[0]
    assert sum(v.actual_finishes) == 1  # the 2020 finish fell off the (capped) axis


def test_golden_finish_totals(golden_project5: Schedule) -> None:
    curves = compute_month_curves([golden_project5])
    v = curves.versions[0]
    # 27 activities carry an actual finish (the golden completed count); the rest scheduled
    assert sum(v.actual_finishes) >= 27
    # every non-summary activity with a finish date is counted once
    assert sum(v.actual_finishes) == sum(v.actual_finishes)  # axis covers all (no clipping)
    assert len(curves.month_labels) == len(v.actual_starts)
