"""S-curve — cumulative planned vs actual/forecast progress over a shared month axis."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.s_curve import compute_s_curve
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def _task(uid: int, baseline: dt.datetime | None, finish: dt.datetime | None, pct: float) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=480,
        percent_complete=pct,
        baseline_finish=baseline,
        finish=finish,
        actual_finish=finish if pct >= 100.0 else None,
    )


def _d(y: int, m: int) -> dt.datetime:
    return dt.datetime(y, m, 15, 17, 0)


def test_s_curve_is_cumulative_monotone_and_reaches_full() -> None:
    # four activities: baseline finishes Jan..Apr 2026; actuals lag by a month
    tasks = (
        _task(1, _d(2026, 1), _d(2026, 2), 100.0),
        _task(2, _d(2026, 2), _d(2026, 3), 100.0),
        _task(3, _d(2026, 3), _d(2026, 4), 0.0),
        _task(4, _d(2026, 4), _d(2026, 5), 0.0),
    )
    sch = Schedule(
        name="v1",
        source_file="v1.xml",
        project_start=_d(2026, 1),
        status_date=_d(2026, 3),
        tasks=tasks,
    )
    sc = compute_s_curve([sch])
    assert len(sc.versions) == 1
    v = sc.versions[0]
    assert v.activities == 4
    # both curves are non-decreasing (cumulative)
    assert list(v.planned) == sorted(v.planned)
    assert list(v.actual) == sorted(v.actual)
    # planned reaches 100% (every activity has a baseline finish on-axis)
    assert v.planned[-1] == 100.0 and v.actual[-1] == 100.0
    # the actual curve lags the plan: at the baseline-finish months it is at or below planned
    assert all(a <= p for a, p in zip(v.actual, v.planned, strict=True))
    assert any(a < p for a, p in zip(v.actual, v.planned, strict=True))
    # the data-date month (Mar) is located on the axis
    assert v.status_index is not None and sc.month_labels[v.status_index] == "Mar-26"


def test_s_curve_spans_versions_on_one_shared_axis() -> None:
    a = Schedule(
        name="v1",
        source_file="v1.xml",
        project_start=_d(2026, 1),
        tasks=(_task(1, _d(2026, 1), _d(2026, 2), 100.0),),
    )
    b = Schedule(
        name="v2",
        source_file="v2.xml",
        project_start=_d(2026, 1),
        tasks=(_task(1, _d(2026, 1), _d(2026, 6), 0.0),),  # the finish slipped to June
    )
    sc = compute_s_curve([a, b])
    assert len(sc.versions) == 2
    # one shared axis: every version's curves have the same length as the labels
    assert all(len(v.planned) == len(sc.month_labels) for v in sc.versions)
    assert all(len(v.actual) == len(sc.month_labels) for v in sc.versions)
    # the shared axis spans the earliest baseline finish (Jan) to v2's slipped finish (Jun)
    assert sc.month_labels[0] == "Jan-26" and sc.month_labels[-1] == "Jun-26"


def test_s_curve_needs_a_finish_date() -> None:
    empty = Schedule(name="v", project_start=_d(2026, 1), tasks=(_task(1, None, None, 0.0),))
    with pytest.raises(ValueError, match="no finish dates"):
        compute_s_curve([empty])
    with pytest.raises(ValueError, match="at least one"):
        compute_s_curve([])


def test_tracked_uids_marked_on_the_curve() -> None:
    """Operator 2026-07-09: tracked UIDs carry their current + baseline finish months per
    version so the animated chart can mark specific activities; absent UIDs carry None."""
    import datetime as dt

    from schedule_forensics.model.task import Task

    def t(uid: int, finish: str, baseline: str | None = None, pct: float = 0.0) -> Task:
        return Task(
            unique_id=uid,
            name=f"T{uid}",
            duration_minutes=480,
            finish=dt.datetime.fromisoformat(finish),
            baseline_finish=dt.datetime.fromisoformat(baseline) if baseline else None,
            percent_complete=pct,
        )

    sch = Schedule(
        name="v1",
        project_start=dt.datetime(2026, 1, 5, 8),
        status_date=dt.datetime(2026, 2, 28, 17),
        tasks=(
            t(1, "2026-02-10T17:00", "2026-01-20T17:00", pct=100.0),
            t(2, "2026-04-15T17:00", "2026-03-15T17:00"),
        ),
    )
    sc = compute_s_curve([sch], track_uids=[1, 2, 99])
    tracked = {tr.uid: tr for tr in sc.versions[0].tracked}
    months = list(sc.month_labels)
    assert months[tracked[1].finish_index] == "Feb-26"
    assert months[tracked[1].baseline_index] == "Jan-26"
    assert tracked[1].percent_complete == 100.0
    assert months[tracked[2].finish_index] == "Apr-26"
    assert tracked[99].finish_index is None and tracked[99].percent_complete is None
