"""Edge-case unit tests for the cross-version trend builders and the S-curve.

Targets the defensive raises and edge branches: the float-ratio trend's empty-series and
cpms-mismatch raises (trend.py 238/240), the quality trend's cpms-mismatch raise (trend.py 294),
the S-curve's zero-activity cumulative-percent guard (s_curve.py 60) and the >60-month axis-cap
shedding (s_curve.py 91). Each asserts the real error message / returned shape.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.s_curve import compute_s_curve
from schedule_forensics.engine.trend import (
    compute_float_ratio_trend,
    compute_quality_trend,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(
    name: str,
    tasks: list[Task],
    *,
    status_date: dt.datetime | None = None,
    project_start: dt.datetime = MON,
) -> Schedule:
    return Schedule(
        name=name,
        source_file=f"{name}.mpp",
        project_start=project_start,
        status_date=status_date,
        tasks=tuple(tasks),
        relationships=(),
    )


# --- trend.py:238 — float-ratio trend raises on an empty series ---------------------------------


def test_float_ratio_trend_raises_on_empty_series() -> None:
    with pytest.raises(ValueError, match="at least one schedule version"):
        compute_float_ratio_trend([])


# --- trend.py:240 — float-ratio trend raises when cpms do not parallel schedules ----------------


def test_float_ratio_trend_raises_when_cpms_do_not_parallel_schedules() -> None:
    s = _sched("v1", [Task(unique_id=1, name="T", duration_minutes=DAY)])
    cpm = compute_cpm(s)
    with pytest.raises(ValueError, match="cpms must parallel schedules"):
        compute_float_ratio_trend([s], cpms=[cpm, cpm])  # 1 schedule, 2 cpms


def test_float_ratio_trend_single_version_has_a_none_first_delta() -> None:
    """A one-version series yields one value and a None delta (no prior period) — the happy
    path that proves the empty/mismatch raises above are genuine guards, not the norm."""
    s = _sched(
        "v1",
        [
            Task(
                unique_id=1,
                name="T",
                duration_minutes=DAY,
                remaining_duration_minutes=DAY,
                stored_total_float_minutes=DAY,
            )
        ],
    )
    series = compute_float_ratio_trend([s])
    assert series.labels == ("v1.mpp",)
    assert series.deltas == (None,)  # first version has no predecessor period


# --- trend.py:294 — quality trend raises when cpms do not parallel schedules ---------------------


def test_quality_trend_raises_when_cpms_do_not_parallel_schedules() -> None:
    a = _sched("a", [Task(unique_id=1, name="T", duration_minutes=DAY)], status_date=MON)
    b = _sched(
        "b",
        [Task(unique_id=1, name="T", duration_minutes=DAY)],
        status_date=MON + dt.timedelta(days=1),
    )
    cpm = compute_cpm(a)
    with pytest.raises(ValueError, match="cpms must parallel schedules"):
        compute_quality_trend([a, b], cpms=[cpm])  # 2 schedules, 1 cpm


# --- s_curve.py:60 — a version with zero non-summary activities reads all-zero curves ------------


def test_s_curve_zero_activity_version_reads_all_zero_curves() -> None:
    """A version whose only task is a summary has 0 non-summary activities (total <= 0), so its
    cumulative curves are all zeros (s_curve.py line 60) — while a sibling version supplies the
    finish dates that build the shared axis (so the whole call doesn't raise)."""
    with_dates = _sched(
        "real",
        [
            Task(
                unique_id=1,
                name="T",
                duration_minutes=DAY,
                finish=MON,
                baseline_finish=MON,
            )
        ],
    )
    summary_only = _sched(
        "empty",
        [Task(unique_id=2, name="WBS", duration_minutes=DAY, is_summary=True)],
    )
    curve = compute_s_curve([with_dates, summary_only])
    empty_version = next(v for v in curve.versions if v.label == "empty.mpp")
    assert empty_version.activities == 0
    assert set(empty_version.planned) == {0.0}
    assert set(empty_version.actual) == {0.0}
    # the real version is non-trivial (it actually has finishes), confirming the axis is shared
    real_version = next(v for v in curve.versions if v.label == "real.mpp")
    assert real_version.activities == 1


# --- s_curve.py:91 — the >60-month span sheds the oldest months (axis cap) -----------------------


def test_s_curve_caps_the_month_axis_at_sixty_months_shedding_oldest() -> None:
    """A finish-date span exceeding the 60-month cap sheds the oldest months from the axis
    (s_curve.py line 91): the label count is exactly the cap, and the curve still reaches 100%
    because pre-window finishes seed the running cumulative."""
    far_future = MON + dt.timedelta(days=365 * 7)  # ~84 months out -> span > 60 months
    tasks = [
        # an early baseline+actual finish (before the shed window opens)
        Task(unique_id=1, name="early", duration_minutes=DAY, finish=MON, baseline_finish=MON),
        # a far-future finish so the raw span is > 60 months
        Task(
            unique_id=2,
            name="late",
            duration_minutes=DAY,
            finish=far_future,
            baseline_finish=far_future,
        ),
    ]
    sch = _sched("wide", tasks)
    curve = compute_s_curve([sch])
    assert len(curve.month_labels) == 60  # axis capped at _MAX_MONTHS
    version = curve.versions[0]
    # the early finish was shed off the front of the axis but still counts: the curve never
    # loses already-completed work, and by the last month both finishes are accounted (100%).
    assert version.actual[-1] == 100.0
    assert version.planned[-1] == 100.0
