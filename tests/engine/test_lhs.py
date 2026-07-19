"""Latin Hypercube sampling option (ADR-0271, issue #331 / Hulett #11).

LHS is a *variance-reduction* sampler bolted onto the SAME Gaussian-copula composition the
Monte-Carlo path already uses — so the correctness bar is threefold and this module pins each:

1. **The freeze holds.** ``sampling="mc"`` (the default) is byte-untouched: the plan is ``None``
   and the sampler runs the frozen Monte-Carlo statements. LHS is opt-in and never leaks into a
   default run.
2. **The stratification is real.** The plan places exactly one draw in every ``[k/N, (k+1)/N)``
   stratum per dimension (random-in-stratum or centered), on a DEDICATED, disjoint RNG stream, and
   it actually reduces the estimator variance — the whole point.
3. **The equality invariant survives.** ``compute_jcl``'s finish marginal stays byte-identical to
   ``compute_sra_ssi``'s under LHS for every correlation branch (independent, scalar single-factor,
   full matrix), because both engines share one sampler fed one identically-built plan.
"""

from __future__ import annotations

import datetime as dt
import math
import random
import statistics
from dataclasses import replace

import pytest

from schedule_forensics.engine.correlation import CorrelationSpec
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.jcl import JCLConfig, compute_jcl
from schedule_forensics.engine.sra import (
    RiskFactorTable,
    ScheduleRisk,
    SRAConfig,
    _lhs_plan,
    _lhs_seed,
    _phi,
    _phi_inv,
    _sample_triangular,
    compute_sra_ssi,
    factor_to_bc_wc,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, dur_days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _focus_net() -> Schedule:
    # 1(1d) -> 2(10d driver) -> 4(focus 1d); 1 -> 3(2d) -> 4. Deterministic focus finish = 12 days.
    return Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1), _task(2, 10), _task(3, 2), _task(4, 1)),
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


def _costed_net() -> Schedule:
    """The focus network with the driver cost-loaded, so ``compute_jcl`` accepts it."""
    tasks = tuple(
        _task(u, d, budgeted_cost=(1000.0 if u == 2 else 0.0))
        for u, d in ((1, 1), (2, 10), (3, 2), (4, 1))
    )
    return Schedule(
        name="S",
        project_start=MON,
        tasks=tasks,
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


def _two_uncertain() -> dict[int, tuple[int, int, int]]:
    """Tasks 2 AND 3 factored and un-risked → two genuinely uncertain activities (the minimum a
    correlation matrix needs; a risk-driven task is a point mass and would not enter the matrix)."""
    tbl = RiskFactorTable()
    return {2: factor_to_bc_wc(10 * DAY, 3, tbl), 3: factor_to_bc_wc(2 * DAY, 4, tbl)}


# ---------------------------------------------------------------------------------------
# 1. The freeze: "mc" is the default and is byte-untouched by the LHS code path
# ---------------------------------------------------------------------------------------


def test_default_sampling_is_mc_and_is_echoed() -> None:
    assert SRAConfig().sampling == "mc"
    s = _focus_net()
    tp = _two_uncertain()
    r = compute_sra_ssi(s, config=SRAConfig(iterations=64, seed=1, target_uid=4), three_point=tp)
    assert r.sampling == "mc"


def test_explicit_mc_equals_the_default_run_byte_for_byte() -> None:
    """Passing ``sampling="mc"`` explicitly must reproduce the default run exactly — the LHS branch
    is a pure add-on that never perturbs the Monte-Carlo statements."""
    s = _focus_net()
    tp = _two_uncertain()
    base = SRAConfig(iterations=128, seed=7, target_uid=4)
    default = compute_sra_ssi(s, config=base, three_point=tp)
    explicit = compute_sra_ssi(s, config=replace(base, sampling="mc"), three_point=tp)
    assert explicit.cdf == default.cdf


def test_unknown_sampling_value_is_treated_as_mc_never_crashes() -> None:
    """An out-of-vocabulary sampler string falls back to Monte-Carlo (fails safe, no plan built)."""
    s = _focus_net()
    tp = _two_uncertain()
    base = SRAConfig(iterations=64, seed=2, target_uid=4)
    mc = compute_sra_ssi(s, config=base, three_point=tp)
    weird = compute_sra_ssi(s, config=replace(base, sampling="nonsense"), three_point=tp)
    assert weird.cdf == mc.cdf


# ---------------------------------------------------------------------------------------
# 2. The plan primitive: stratification, independence, determinism, disjoint stream
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("centered", [False, True])
def test_plan_places_exactly_one_draw_per_stratum(centered: bool) -> None:
    plan = _lhs_plan(seed=7, iterations=10, n_columns=3, centered=centered)
    assert plan.iterations == 10
    assert len(plan.columns) == 3
    for col in plan.columns:
        assert len(col) == 10
        counts = [sum(1 for u in col if k / 10 <= u < (k + 1) / 10) for k in range(10)]
        assert counts == [1] * 10  # one and only one sample in each stratum


def test_centered_plan_uses_stratum_midpoints() -> None:
    plan = _lhs_plan(seed=3, iterations=8, n_columns=1, centered=True)
    assert sorted(plan.columns[0]) == [(k + 0.5) / 8 for k in range(8)]


def test_plan_columns_are_independent_permutations() -> None:
    plan = _lhs_plan(seed=7, iterations=10, n_columns=2, centered=True)
    order = [tuple(int(u * 10) for u in col) for col in plan.columns]
    assert order[0] != order[1]  # two dimensions are not the same permutation


def test_plan_is_deterministic() -> None:
    assert _lhs_plan(9, 20, 3, False) == _lhs_plan(9, 20, 3, False)


def test_plan_rng_stream_is_disjoint_from_the_iteration_seeds() -> None:
    """The plan draws from ``_lhs_seed(seed)`` — a distinct salt from the per-iteration
    ``seed`` / ``seed+i`` streams, so the plan can never coincide with an iteration's draws."""
    seed = 12345
    plan_first = random.Random(_lhs_seed(seed)).random()
    assert abs(random.Random(seed).random() - plan_first) > 1e-12
    assert all(abs(random.Random(seed + i).random() - plan_first) > 1e-12 for i in range(50))


# ---------------------------------------------------------------------------------------
# 3. The probit: finite at the clamped edges, and an exact Φ⁻¹ round-trip
# ---------------------------------------------------------------------------------------


def test_phi_inv_is_finite_at_the_clamped_bounds() -> None:
    lo, hi = _phi_inv(0.0), _phi_inv(1.0)
    assert math.isfinite(lo) and math.isfinite(hi)
    assert abs(lo + 7.0345) < 0.01 and abs(hi - 7.0345) < 0.01  # ≈ ±7.03, never ±inf


def test_phi_inv_round_trips_through_phi() -> None:
    for p in (1e-6, 0.1, 0.37, 0.5, 0.9, 1 - 1e-6):
        assert abs(_phi(_phi_inv(p)) - p) < 1e-9


# ---------------------------------------------------------------------------------------
# 4. Variance reduction — the whole point (deterministic, helper-level, non-flaky)
# ---------------------------------------------------------------------------------------


def test_lhs_estimator_variance_beats_monte_carlo() -> None:
    """Over a bank of seeds the LHS sample mean of a triangular marginal sits far tighter to the
    analytic mean than the plain Monte-Carlo mean at the same iteration count — the McKay-Beckman-
    Conover stratification guarantee, verified numerically before it was implemented (ADR-0271)."""
    low, mode, high = 3360.0, 4800.0, 6240.0  # a factor-3 spread on a 10-day task, in minutes
    truth = (low + mode + high) / 3.0
    n = 64
    seeds = range(1, 41)

    def mc_mean(seed: int) -> float:
        rng = random.Random(seed)
        return statistics.fmean(_sample_triangular(rng.random(), low, mode, high) for _ in range(n))

    def lhs_mean(seed: int) -> float:
        col = _lhs_plan(seed, n, 1, centered=False).columns[0]
        return statistics.fmean(_sample_triangular(u, low, mode, high) for u in col)

    mc_rmse = math.sqrt(statistics.fmean((mc_mean(s) - truth) ** 2 for s in seeds))
    lhs_rmse = math.sqrt(statistics.fmean((lhs_mean(s) - truth) ** 2 for s in seeds))
    assert lhs_rmse < mc_rmse  # strictly tighter
    assert mc_rmse / lhs_rmse > 5.0  # and by a wide margin (prototype measured ~45x)


# ---------------------------------------------------------------------------------------
# 5. LHS engages end-to-end: it changes the distribution, stays in-support, is deterministic
# ---------------------------------------------------------------------------------------


def test_lhs_run_differs_from_mc_but_stays_in_the_same_support() -> None:
    s = _focus_net()
    tp = _two_uncertain()
    base = SRAConfig(iterations=200, seed=1, target_uid=4)
    mc = compute_sra_ssi(s, config=base, three_point=tp)
    lhs = compute_sra_ssi(s, config=replace(base, sampling="lhs"), three_point=tp)
    assert lhs.sampling == "lhs"
    assert lhs.cdf != mc.cdf  # a genuinely different (stratified) draw sequence
    # same triangular support → the finish extremes cannot exceed the MC envelope's bounds
    assert lhs.p10 >= mc.deterministic_finish - 10 * DAY
    assert lhs.p90 <= mc.deterministic_finish + 10 * DAY


def test_lhs_run_is_deterministic() -> None:
    s = _focus_net()
    tp = _two_uncertain()
    cfg = SRAConfig(iterations=150, seed=5, target_uid=4, sampling="lhs")
    a = compute_sra_ssi(s, config=cfg, three_point=tp)
    b = compute_sra_ssi(s, config=cfg, three_point=tp)
    assert a.cdf == b.cdf


def test_centered_lhs_runs_and_reports_lhs() -> None:
    s = _focus_net()
    tp = _two_uncertain()
    cfg = SRAConfig(iterations=120, seed=1, target_uid=4, sampling="lhs", lhs_centered=True)
    r = compute_sra_ssi(s, config=cfg, three_point=tp)
    assert r.sampling == "lhs"
    assert r.p10 <= r.p50 <= r.p90  # a coherent distribution, no crash


# ---------------------------------------------------------------------------------------
# 6. Degenerate guard: all point-mass under LHS → no plan, no crash, deterministic finish
# ---------------------------------------------------------------------------------------


def test_all_point_mass_under_lhs_is_the_deterministic_finish() -> None:
    """With no uncertainty the plan degenerates to ``None`` and the run falls back to the frozen
    path — the simulated finish equals the CPM focus finish, and the requested sampler is still
    echoed truthfully."""
    s = _focus_net()
    cpm = compute_cpm(s)
    r = compute_sra_ssi(s, config=SRAConfig(iterations=32, seed=1, target_uid=4, sampling="lhs"))
    assert r.p10 == r.p50 == r.p90 == cpm.timings[4].early_finish == 12 * DAY
    assert r.sampling == "lhs"  # reports the requested sampler even though it degenerated to MC


# ---------------------------------------------------------------------------------------
# 7. LHS still widens under correlation (the copula composition is intact)
# ---------------------------------------------------------------------------------------


def test_lhs_matrix_widens_and_marks_the_mode() -> None:
    s = _focus_net()
    tp = _two_uncertain()
    base = SRAConfig(iterations=400, seed=1, target_uid=4, sampling="lhs")
    indep = compute_sra_ssi(s, config=base, three_point=tp)
    spec = CorrelationSpec(groups=(((2, 3), 0.6),))
    mat = compute_sra_ssi(s, config=replace(base, correlation_matrix=spec), three_point=tp)
    assert mat.correlation_matrix_applied and not mat.correlation_matrix_repaired
    assert mat.std_days >= indep.std_days  # positive correlation does not shrink the spread


# ---------------------------------------------------------------------------------------
# 8. The equality invariant: compute_jcl finish marginal == compute_sra_ssi under LHS
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("distribution", ["triangular", "pert"])
@pytest.mark.parametrize("correlation", [0.0, 0.3])
@pytest.mark.parametrize("centered", [False, True])
def test_jcl_finish_marginal_equals_ssi_under_lhs(
    distribution: str, correlation: float, centered: bool
) -> None:
    """The ADR-0269 equality pin under the LHS sampler: both engines build the plan from the same
    ``uids``/``three``/``prepared`` and consume it through the one shared sampler, so the finish
    distribution stays byte-identical across the independent (r=0) and scalar single-factor (r>0)
    branches, for triangular and pert, random and centered."""
    s = _costed_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl), 3: factor_to_bc_wc(2 * DAY, 4, tbl)}
    risks = [ScheduleRisk(id="R1", name="Late", probability=0.4, impact_days=5.0, affected=(3,))]
    cfg = SRAConfig(
        iterations=120,
        seed=3,
        target_uid=4,
        distribution=distribution,
        correlation=correlation,
        sampling="lhs",
        lhs_centered=centered,
        occurrence_mode="exact_overall",
    )
    ssi = compute_sra_ssi(s, config=cfg, three_point=tp, risks=risks)
    jcl = compute_jcl(s, config=cfg, three_point=tp, risks=risks)
    assert jcl.finish_cdf == ssi.cdf  # the FULL distribution, byte-identical under LHS
    assert jcl.sampling == ssi.sampling == "lhs"


def test_jcl_finish_marginal_equals_ssi_under_lhs_matrix() -> None:
    """The equality pin also holds under a full correlation MATRIX + LHS: LHS-then-Cholesky on the
    same prepared factor in both engines keeps the finish marginal byte-identical."""
    s = _costed_net()
    tp = _two_uncertain()
    spec = CorrelationSpec(groups=(((2, 3), 0.5),))
    cfg = SRAConfig(iterations=120, seed=3, target_uid=4, correlation_matrix=spec, sampling="lhs")
    ssi = compute_sra_ssi(s, config=cfg, three_point=tp)
    jcl = compute_jcl(s, config=cfg, three_point=tp)
    assert jcl.finish_cdf == ssi.cdf
    assert jcl.correlation_matrix_applied and ssi.correlation_matrix_applied
    assert jcl.sampling == "lhs"


def test_jcl_default_sampling_is_mc() -> None:
    s = _costed_net()
    r = compute_jcl(s, config=SRAConfig(iterations=32, seed=1, target_uid=4), jcl=JCLConfig())
    assert r.sampling == "mc"
