"""The cross-version series (ADR-0392) — every loaded version as one comparable row.

The load-bearing test here is :func:`test_matches_the_s_curve_at_every_on_axis_status_month`: the
series recomputes each version's S-curve point instead of reading it off the animated curve's
shared, 60-month-capped axis, so the two paths MUST agree wherever the animated curve can be read.
If they ever diverge, the tool would quote two different numbers for "the S-curve" — the analyst's
page and the AI's fact base — which is the parity failure Law 2 exists to prevent.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.s_curve import compute_s_curve
from schedule_forensics.engine.version_series import (
    VersionPoint,
    VersionSeries,
    compute_version_series,
)
from schedule_forensics.model.schedule import Schedule

#: Anchored INSIDE golden Project5's own date window (2026-03 → 2028-01). A data date outside the
#: schedule's dates is off the animated curve's axis by construction, which made the equivalence
#: assertion below iterate zero times — the "compared >= 2" guard is what caught it.
_FIRST_DATA_DATE = dt.datetime(2026, 4, 15)


def _versions(base: Schedule, n: int, *, statused: bool = True) -> list[Schedule]:
    """``n`` clones of ``base``, one per month, oldest first — a synthetic update series."""
    out = []
    for i in range(n):
        out.append(
            base.model_copy(
                update={
                    "name": f"v{i + 1:02d}.mpp",
                    "source_file": f"v{i + 1:02d}.mpp",
                    "status_date": (
                        _FIRST_DATA_DATE + dt.timedelta(days=30 * i) if statused else None
                    ),
                }
            )
        )
    return out


def test_matches_the_s_curve_at_every_on_axis_status_month(golden_project5: Schedule) -> None:
    """One definition of "the S-curve", two evaluation paths — they must agree exactly."""
    versions = _versions(golden_project5, 8)
    sc = compute_s_curve(versions)
    series = compute_version_series(versions)
    assert len(series.points) == len(sc.versions) == 8

    compared = 0
    for point, curve in zip(series.points, sc.versions, strict=True):
        assert point.label == curve.label  # both order oldest -> newest
        if curve.status_index is None:  # off the capped axis: the curve has no readable point
            continue
        assert point.planned_pct == curve.planned[curve.status_index]
        assert point.actual_pct == curve.actual[curve.status_index]
        compared += 1
    assert compared >= 2, "the equivalence claim needs on-axis versions to be tested against"


def test_the_axis_cap_cannot_blind_the_series(golden_project5: Schedule) -> None:
    """The reason the series recomputes: a data date in a month the 60-month axis SHED still has
    a readable point here, where the animated curve reports ``status_index is None``."""
    # a data date far enough before the project's own dates that the shared axis cannot reach it
    early = golden_project5.model_copy(
        update={
            "name": "ancient.mpp",
            "source_file": "ancient.mpp",
            "status_date": dt.datetime(1990, 1, 1),
        }
    )
    versions = [early, *_versions(golden_project5, 3)]
    assert compute_s_curve(versions).versions[0].status_index is None  # off-axis, unreadable there
    point = compute_version_series(versions).points[0]
    assert point.label == "ancient.mpp"
    assert point.planned_pct is not None and point.actual_pct is not None


def test_an_empty_population_is_unreadable_never_on_plan(golden_project5: Schedule) -> None:
    """A version a filter scoped to nothing has no measurement — not a gap of +0.0, which would
    read as "exactly on plan" for a version that was never measured (Law 2)."""
    empty = golden_project5.model_copy(
        update={
            "name": "scoped-out.mpp",
            "source_file": "scoped-out.mpp",
            "tasks": (),
            "status_date": _FIRST_DATA_DATE,
        }
    )
    point = compute_version_series([empty, *_versions(golden_project5, 2)]).points[0]
    assert point.label == "scoped-out.mpp"
    assert point.activities == 0
    assert (point.planned_pct, point.actual_pct, point.gap_pct) == (None, None, None)
    assert point.complete_pct is None
    assert not point.is_readable


def test_a_version_with_no_data_date_is_unreadable_never_zero(golden_project5: Schedule) -> None:
    """Law 2: "no data date" is reported as unreadable, never as 0% (which reads as "on plan")."""
    series = compute_version_series(_versions(golden_project5, 3, statused=False))
    assert [p.planned_pct for p in series.points] == [None, None, None]
    assert [p.gap_pct for p in series.points] == [None, None, None]
    assert series.readable == ()
    assert series.direction == "unreadable"
    assert series.gap_delta is None


def _point(label: str, gap: float | None) -> VersionPoint:
    """A hand-built row whose gap is exactly ``gap`` (planned pinned at 50%)."""
    return VersionPoint(
        label=label,
        status_date=dt.date(2026, 4, 15) if gap is not None else None,
        activities=100,
        planned_pct=50.0 if gap is not None else None,
        actual_pct=round(50.0 + gap, 1) if gap is not None else None,
        complete_pct=None,
        finish=None,
    )


@pytest.mark.parametrize(
    ("gaps", "delta", "direction", "steps"),
    [
        # first -5 -> last -20: the gap WIDENED by 15 points; every step widened it
        ([-5.0, -10.0, -15.0, -20.0], -15.0, "widened", (0, 3, 0)),
        # first -20 -> last -5: NARROWED by 15; every step narrowed it
        ([-20.0, -15.0, -10.0, -5.0], 15.0, "narrowed", (3, 0, 0)),
        # net flat, but churning underneath — the step counts are what expose that
        ([-10.0, -2.0, -18.0, -10.0], 0.0, "unchanged", (2, 1, 0)),
        # movement under the rounding epsilon is not movement
        ([-10.0, -10.0], 0.0, "unchanged", (0, 0, 1)),
    ],
)
def test_direction_and_steps_read_the_gap_movement(
    gaps: list[float], delta: float, direction: str, steps: tuple[int, int, int]
) -> None:
    """The verdict is arithmetic on the first and last readable gap; the step counts expose the
    churn behind it (a net-flat series can still be swinging wildly)."""
    series = VersionSeries(tuple(_point(f"v{i}", g) for i, g in enumerate(gaps)))
    assert series.gap_delta == delta
    assert series.direction == direction
    assert series.steps == steps


def test_unreadable_versions_drop_out_of_the_verdict_without_breaking_it() -> None:
    """A version with no data date is skipped by the trend, not counted as a zero gap."""
    series = VersionSeries((_point("a", -5.0), _point("b", None), _point("c", -15.0)))
    assert len(series.points) == 3 and len(series.readable) == 2
    assert series.gap_delta == -10.0  # a -> c, ignoring the undated b entirely
    assert series.direction == "widened"
    assert series.steps == (0, 1, 0)


def test_the_real_series_produces_one_step_per_consecutive_pair(golden_project5: Schedule) -> None:
    series = compute_version_series(_versions(golden_project5, 6))
    assert len(series.readable) == 6
    assert sum(series.steps) == 5
    assert series.direction in {"narrowed", "widened", "unchanged"}


def test_the_finish_series_moves_with_the_cpm_finish(golden_project5: Schedule) -> None:
    """Passing CPMs adds each version's schedule-logic finish and the first→last movement."""
    versions = _versions(golden_project5, 4)
    cpms = [compute_cpm(v) for v in versions]
    series = compute_version_series(versions, cpms)
    assert all(p.finish is not None for p in series.points)
    first, last = series.points[0].finish, series.points[-1].finish
    assert first is not None and last is not None
    assert series.finish_movement_days == (last - first).days

    without = compute_version_series(versions)  # cpms are optional
    assert all(p.finish is None for p in without.points)
    assert without.finish_movement_days is None


def test_every_loaded_version_appears_exactly_once(golden_project5: Schedule) -> None:
    """The whole point: a 31-version workbook yields 31 rows, not the newest plus a pair."""
    versions = _versions(golden_project5, 31)
    series = compute_version_series(versions, [compute_cpm(v) for v in versions])
    assert len(series.points) == 31
    assert [p.label for p in series.points] == [f"v{i:02d}.mpp" for i in range(1, 32)]
    assert len({p.label for p in series.points}) == 31


def test_an_empty_workbook_is_an_empty_series() -> None:
    series = compute_version_series([])
    assert series.points == ()
    assert series.direction == "unreadable"
    assert series.steps == (0, 0, 0)
    assert series.finish_movement_days is None


def test_cpms_must_be_parallel_to_the_schedules(golden_project5: Schedule) -> None:
    """A mismatched cpms list is a programming error, not a silently-dropped finish column."""
    versions = _versions(golden_project5, 3)
    with pytest.raises(ValueError):
        compute_version_series(versions, [compute_cpm(versions[0])])
