"""Schedule Risk Analysis (Monte-Carlo) engine tests — ADR-0106.

Hand-verified synthetic networks. The headline gate is **equivalence**: with every draw
forced to the most-likely duration the simulation's finish equals the canonical
``compute_cpm`` finish, so the parity-isolated SRA can never diverge from the trusted
solver (Law 2). The rest cover determinism, the triangular sampler, criticality index,
percentile monotonicity, and the auto/manual input paths.

The time axis is integer working minutes from ``project_start`` (480 == one day);
``project_start`` is a Monday 08:00 so the standard Mon-Fri calendar is exercised.
Iterations are kept modest (200-500) for speed.
"""

from __future__ import annotations

import datetime as dt
import statistics

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.sra import (
    ActivityRisk,
    SRAConfig,
    _percentile,
    _sample_triangular,
    _spearman,
    compute_sra,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480


def _task(uid: int, dur_days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _rel(p: int, s: int, rtype: RelationshipType = RelationshipType.FS) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=rtype, lag_minutes=0)


def _sched(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


def _linear_chain() -> Schedule:
    # 2d -> 3d -> 1d == 6-day deterministic finish, single critical path.
    return _sched([_task(1, 2), _task(2, 3), _task(3, 1)], [_rel(1, 2), _rel(2, 3)])


def _two_path_network() -> Schedule:
    # Start(1d) -> long(10d) -> End(1d); Start(1d) -> short(1d) -> End(1d).
    return _sched(
        [_task(1, 1), _task(2, 10), _task(3, 1), _task(4, 1)],
        [_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)],
    )


# --- the equivalence gate (Law 2: no divergence from the trusted solver) ----------


def test_equivalence_most_likely_matches_compute_cpm() -> None:
    """With every draw pinned to the most-likely duration, the simulated finish == the
    deterministic ``compute_cpm`` finish, and the SRAResult carries that finish."""
    s = _linear_chain()
    cpm = compute_cpm(s)
    # auto_low == auto_high == 1.0 collapses every triangular to its mode (= own duration
    # for the not-started tasks here), so every iteration reproduces the deterministic run.
    cfg = SRAConfig(iterations=200, auto_low=1.0, auto_most_likely=1.0, auto_high=1.0)
    r = compute_sra(s, cpm, config=cfg)
    assert r.deterministic_finish == cpm.project_finish
    assert r.p10 == r.p50 == r.p80 == r.p90 == cpm.project_finish
    assert r.mean == float(cpm.project_finish)
    # the whole distribution is the single deterministic value
    assert r.deterministic_percentile == 1.0
    assert r.cdf == ((cpm.project_finish, 1.0),)


def test_duration_overrides_at_most_likely_equals_plain_cpm() -> None:
    """The ``compute_cpm`` override hook with each task at its own duration == plain CPM."""
    s = _linear_chain()
    plain = compute_cpm(s)
    overrides = {t.unique_id: t.duration_minutes for t in s.tasks}
    overridden = compute_cpm(s, duration_overrides=overrides)
    assert overridden.project_finish == plain.project_finish
    assert overridden.critical_path == plain.critical_path
    for uid in (1, 2, 3):
        assert overridden.timings[uid] == plain.timings[uid]


# --- determinism ------------------------------------------------------------------


def test_same_seed_identical_result() -> None:
    s = _two_path_network()
    cpm = compute_cpm(s)
    cfg = SRAConfig(iterations=300, seed=42)
    a = compute_sra(s, cpm, config=cfg)
    b = compute_sra(s, cpm, config=cfg)
    assert a == b


def test_different_seed_differs_but_valid() -> None:
    s = _two_path_network()
    cpm = compute_cpm(s)
    a = compute_sra(s, cpm, config=SRAConfig(iterations=300, seed=1))
    b = compute_sra(s, cpm, config=SRAConfig(iterations=300, seed=2))
    assert a != b  # different draws
    # both are valid distributions with spread (auto default is active)
    for r in (a, b):
        assert r.p10 <= r.p50 <= r.p90
        assert r.p90 > r.p10


# --- the triangular sampler -------------------------------------------------------


def test_triangular_sampler_mean_converges() -> None:
    """Inverse-CDF triangular draws have mean ≈ (a + m + b) / 3 (a skewed example)."""
    import random

    a, m, b = 100.0, 200.0, 500.0
    rng = random.Random(7)
    draws = [_sample_triangular(rng.random(), a, m, b) for _ in range(20000)]
    expected = (a + m + b) / 3.0
    assert abs(statistics.fmean(draws) - expected) < 5.0
    assert all(a <= d <= b for d in draws)


def test_triangular_degenerate_point_mass() -> None:
    assert _sample_triangular(0.3, 250.0, 250.0, 250.0) == 250.0


# --- criticality index ------------------------------------------------------------


def test_criticality_index_picks_the_longer_path() -> None:
    """On two parallel paths the (much) longer path is critical ≈ always; the short
    off-path activity ≈ never."""
    s = _two_path_network()
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=400))
    ci = {a.unique_id: a.criticality_index for a in r.activities}
    assert ci[2] > 0.95  # the 10-day path activity
    assert ci[3] < 0.05  # the 1-day off-path activity
    # the longer path also drives the finish (high duration sensitivity)
    sens = {a.unique_id: a.duration_sensitivity for a in r.activities}
    assert sens[2] > sens[3]


# --- percentiles ------------------------------------------------------------------


def test_percentiles_monotonic_and_in_range() -> None:
    s = _two_path_network()
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=400))
    assert r.p10 <= r.p50 <= r.p80 <= r.p90
    lo = r.histogram[0][0]
    hi = r.histogram[-1][1]
    for p in (r.p10, r.p50, r.p80, r.p90):
        assert lo <= p <= hi


def test_percentile_rule_linear_interpolation() -> None:
    """The documented PERCENTILE.INC rule: rank = p/100 * (N-1), linearly interpolated."""
    values = [0.0, 10.0, 20.0, 30.0, 40.0]  # N == 5
    assert _percentile(values, 0) == 0.0
    assert _percentile(values, 100) == 40.0
    assert _percentile(values, 50) == 20.0  # rank 2.0
    assert _percentile(values, 25) == 10.0  # rank 1.0
    assert _percentile(values, 10) == pytest.approx(4.0)  # rank 0.4 -> 0 + 0.4*10
    assert _percentile([5.0], 73) == 5.0  # single sample


def test_percentile_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        _percentile([], 50)


# --- auto vs manual input paths ---------------------------------------------------


def test_auto_default_applied_and_spreads() -> None:
    """No overrides -> auto triangular default fires (auto_used) and the finish spreads."""
    s = _linear_chain()
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=400))
    assert r.auto_used is True
    assert r.p90 > r.p10  # the 90/100/110 default produces a real distribution
    # deterministic finish sits below P50 of the right-skewed distribution (GAO pattern)
    assert r.deterministic_percentile < 0.6


def test_manual_override_respected_and_no_auto() -> None:
    """A manual ActivityRisk on every activity -> auto is not used and the ranges drive it."""
    s = _linear_chain()
    cpm = compute_cpm(s)
    overrides = {
        t.unique_id: ActivityRisk(
            unique_id=t.unique_id,
            optimistic_minutes=t.duration_minutes,
            most_likely_minutes=t.duration_minutes,
            pessimistic_minutes=t.duration_minutes * 3,  # wide, deliberate overrun range
        )
        for t in s.tasks
    }
    r = compute_sra(s, cpm, config=SRAConfig(iterations=400), overrides=overrides)
    assert r.auto_used is False
    # every range starts at the deterministic duration and only inflates -> finish >= det
    assert r.p10 >= cpm.project_finish
    assert r.p90 > cpm.project_finish


def test_partial_override_marks_auto_used() -> None:
    """One manual activity + the rest on auto -> auto_used stays True (the run is mixed)."""
    s = _linear_chain()
    cpm = compute_cpm(s)
    overrides = {
        1: ActivityRisk(
            unique_id=1, optimistic_minutes=DAY, most_likely_minutes=DAY, pessimistic_minutes=DAY
        )
    }
    r = compute_sra(s, cpm, config=SRAConfig(iterations=200), overrides=overrides)
    assert r.auto_used is True


# --- completed work, constraints, structure ---------------------------------------


def test_completed_activity_is_fixed_no_uncertainty() -> None:
    """A 100%-complete activity carries no uncertainty (fixed duration, CI from logic)."""
    s = _sched(
        [_task(1, 2, percent_complete=100.0), _task(2, 3)],
        [_rel(1, 2)],
    )
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=200))
    # the completed predecessor never varies; only the open successor spreads the finish
    sens = {a.unique_id: a.duration_sensitivity for a in r.activities}
    assert sens[1] == 0.0  # flat (fixed) series -> zero correlation
    assert sens[2] > 0.5


def test_constraints_flagged() -> None:
    """Hard-constraint activities are reported (they cap the simulated distribution)."""
    s = _sched(
        [
            _task(1, 2),
            _task(2, 3, constraint_type=ConstraintType.FNLT, constraint_date=MON),
        ],
        [_rel(1, 2)],
    )
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=100))
    assert r.constraints_flagged == (2,)


def test_cdf_and_histogram_shape() -> None:
    s = _two_path_network()
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=400))
    # CDF is monotone non-decreasing in offset and in cumulative probability, ending at 1.0
    offsets = [pt[0] for pt in r.cdf]
    probs = [pt[1] for pt in r.cdf]
    assert offsets == sorted(offsets)
    assert probs == sorted(probs)
    assert probs[-1] == pytest.approx(1.0)
    # the histogram counts cover every sample
    assert sum(b[2] for b in r.histogram) == r.iterations


def test_iso_dates_present_and_ordered() -> None:
    s = _linear_chain()
    cpm = compute_cpm(s)
    r = compute_sra(s, cpm, config=SRAConfig(iterations=300))
    # ISO 8601 finish dates are emitted and ordered with their percentiles
    for iso in (r.p10_date, r.p50_date, r.p90_date, r.deterministic_finish_date):
        dt.datetime.fromisoformat(iso)
    assert r.p10_date <= r.p50_date <= r.p90_date


def test_zero_iterations_rejected() -> None:
    s = _linear_chain()
    cpm = compute_cpm(s)
    with pytest.raises(ValueError, match="iterations"):
        compute_sra(s, cpm, config=SRAConfig(iterations=0))


# --- the statistics primitives ----------------------------------------------------


def test_spearman_perfect_and_ties() -> None:
    assert _spearman([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]) == pytest.approx(1.0)
    assert _spearman([1.0, 2.0, 3.0], [30.0, 20.0, 10.0]) == pytest.approx(-1.0)
    # ties -> average ranks; a flat series has no defined correlation -> 0.0
    assert _spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) == 0.0
    # mismatched / empty lengths guard to 0.0
    assert _spearman([], []) == 0.0
    assert _spearman([1.0], [1.0, 2.0]) == 0.0
