"""JCL joint cost-&-schedule confidence engine (ADR-0269) — equivalence, cost math, gates.

The two load-bearing guarantees pinned here:

1. **Finish-marginal equivalence** — ``compute_jcl``'s finish distribution is byte-identical
   to ``compute_sra_ssi``'s on the same inputs (same seed/draw discipline), including with
   factors, additive risks, correlation, PERT, and a focus event. The football chart's
   schedule axis IS the SSI S-curve; there is no second truth.
2. **Exact cost arithmetic** — hand-computed EAC figures (Law 2: a fast wrong number is
   worthless); the cost dimension never perturbs the duration stream (enabling the cost
   multipliers leaves the finish CDF unchanged).
"""

from __future__ import annotations

import datetime as dt
import random

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.jcl import JCLConfig, compute_jcl
from schedule_forensics.engine.sra import (
    RiskFactorTable,
    ScheduleRisk,
    SRAConfig,
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


def _costed_net(**cost_kw: dict[int, float]) -> Schedule:
    """The SSI test network — 1(1d) -> 2(10d driver) -> 4(focus 1d); 1 -> 3(2d) -> 4 —
    with per-uid budgeted costs from ``budgets`` (default: only the driver carries cost)."""
    budgets = cost_kw.get("budgets", {2: 1000.0})
    tasks = tuple(
        _task(u, d, budgeted_cost=budgets.get(u, 0.0)) for u, d in ((1, 1), (2, 10), (3, 2), (4, 1))
    )
    return Schedule(
        name="S",
        project_start=MON,
        tasks=tasks,
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


# --- the cost-loaded gate -------------------------------------------------------------


def test_uncosted_schedule_raises_never_fabricates() -> None:
    s = Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1), _task(2, 10)),
        relationships=(_rel(1, 2),),
    )
    with pytest.raises(ValueError, match="not cost-loaded"):
        compute_jcl(s)


# --- all-point-mass equivalence (deterministic anchors) -------------------------------


def test_all_point_mass_costs_and_finish_are_deterministic() -> None:
    """No uncertainty anywhere => every iteration's finish equals the CPM focus finish and
    every iteration's EAC equals the deterministic EAC = AC + (BAC - EV) — so at the
    default targets SCL = CCL = JCL = 1.0 and the whole cloud is one point."""
    s = _costed_net(budgets={1: 100.0, 2: 1000.0, 3: 50.0, 4: 25.0})
    cpm = compute_cpm(s)
    r = compute_jcl(s, config=SRAConfig(iterations=25, target_uid=4))
    assert r.deterministic_finish == cpm.timings[4].early_finish == 12 * DAY
    assert r.deterministic_eac == 1175.0
    assert r.cost_min == r.cost_max == r.cost_p50 == 1175.0
    assert r.cost_std == 0.0
    assert r.scl == r.ccl == r.jcl == 1.0
    assert (r.q_both, r.q_date_only, r.q_cost_only, r.q_neither) == (1.0, 0.0, 0.0, 0.0)
    assert len(r.points) == 25
    assert all(p == (r.deterministic_finish_date, 1175.0) for p in r.points)


# --- the SSI finish-marginal equivalence pin (the headline guarantee) -----------------


def _rich_inputs() -> tuple[dict[int, tuple[int, int, int]], list[ScheduleRisk]]:
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl), 3: factor_to_bc_wc(2 * DAY, 4, tbl)}
    risks = [
        ScheduleRisk(id="R1", name="Late castings", probability=0.4, impact_days=5.0, affected=(3,))
    ]
    return tp, risks


@pytest.mark.parametrize("distribution", ["triangular", "pert"])
@pytest.mark.parametrize("correlation", [0.0, 0.3])
@pytest.mark.parametrize("target_uid", [4, None])
def test_finish_marginal_equals_the_ssi_run(
    distribution: str, correlation: float, target_uid: int | None
) -> None:
    s = _costed_net()
    tp, risks = _rich_inputs()
    cfg = SRAConfig(
        iterations=120,
        target_uid=target_uid,
        distribution=distribution,
        correlation=correlation,
        occurrence_mode="exact_overall",
    )
    ssi = compute_sra_ssi(s, config=cfg, three_point=tp, risks=risks)
    jcl = compute_jcl(s, config=cfg, three_point=tp, risks=risks)
    assert jcl.finish_cdf == ssi.cdf  # the FULL distribution, byte-identical
    assert jcl.deterministic_finish == ssi.deterministic_finish
    assert (jcl.finish_p10_date, jcl.finish_p50_date) == (ssi.p10_date, ssi.p50_date)
    assert (jcl.finish_p80_date, jcl.finish_p90_date) == (ssi.p80_date, ssi.p90_date)
    assert jcl.deterministic_finish_date == ssi.deterministic_finish_date


def test_cost_multipliers_never_perturb_the_duration_stream() -> None:
    """Turning the FICSM cost-estimating uncertainty ON must leave the finish CDF
    byte-identical (the multiplier draws come after every duration draw) — only the cost
    marginal may change."""
    s = _costed_net()
    tp, risks = _rich_inputs()
    cfg = SRAConfig(iterations=100, target_uid=4)
    off = compute_jcl(s, config=cfg, three_point=tp, risks=risks)
    on = compute_jcl(
        s,
        config=cfg,
        three_point=tp,
        risks=risks,
        jcl=JCLConfig(cost_low=0.9, cost_ml=1.0, cost_high=1.3),
    )
    assert on.finish_cdf == off.finish_cdf
    assert on.cost_uncertainty_on and not off.cost_uncertainty_on
    assert on.cost_std > off.cost_std  # the driver's TD cost now carries extra spread


# --- exact cost arithmetic (hand-computed; Law 2) -------------------------------------


def test_single_iteration_cost_reproduced_by_hand() -> None:
    """One iteration, one uncertain costed task: EAC = BAC x (sampled minutes / ML minutes),
    replaying the engine's exact draw (seed + 0, one triangular inverse-CDF draw)."""
    s = _costed_net()  # only task 2 costed (BAC 1000), 10d remaining
    tbl = RiskFactorTable()
    bc, ml, wc = factor_to_bc_wc(10 * DAY, 3, tbl)  # 3360 / 4800 / 6240 minutes
    cfg = SRAConfig(iterations=1, seed=777, target_uid=4)
    r = compute_jcl(s, config=cfg, three_point={2: (bc, ml, wc)})

    rng = random.Random(777)  # the engine's iteration-0 stream (correlation 0: no gauss)
    minutes = max(0, round(_sample_triangular(rng.random(), float(bc), float(ml), float(wc))))
    expected_cost = 0.0 + (0.0 + 1000.0 * (minutes / ml)) * 1.0
    assert r.points[0][1] == round(expected_cost, 2)
    assert r.cost_p50 == round(expected_cost, 2)
    # and the finish is the trusted solver's finish under that exact override
    cpm = compute_cpm(s, duration_overrides={1: DAY, 2: minutes, 3: 2 * DAY, 4: DAY})
    assert r.deterministic_finish == 12 * DAY
    assert r.finish_cdf == (((cpm.timings[4].early_finish), 1.0),)


def test_progress_actuals_and_completion_shape_the_eac() -> None:
    """Deterministic EAC = completed finals + incomplete (spent + remaining budget):
    completed-with-actuals uses the actual; completed-without falls back to budget;
    in-progress contributes actuals-to-date + BAC x (1 - pc)."""
    t1 = _task(
        1,
        1,
        budgeted_cost=100.0,
        actual_cost=130.0,
        percent_complete=100.0,
        actual_start=MON,
        actual_finish=MON + dt.timedelta(days=1),
    )
    t2 = _task(2, 10, budgeted_cost=1000.0, actual_cost=700.0, percent_complete=50.0)
    t3 = _task(3, 2, budgeted_cost=50.0, percent_complete=100.0)  # complete, no actual cost
    t4 = _task(4, 1, budgeted_cost=25.0)
    s = Schedule(
        name="S",
        project_start=MON,
        tasks=(t1, t2, t3, t4),
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )
    r = compute_jcl(s, config=SRAConfig(iterations=5, target_uid=4))
    # 130 (actual final) + 50 (budget fallback) + [700 + 500] (in-progress) + 25 (not started)
    assert r.deterministic_eac == 1405.0
    assert r.sunk_total == 130.0 + 50.0 + 700.0
    assert r.completed_count == 2
    assert r.incomplete_costed_count == 2


def test_td_share_zero_makes_cost_time_independent() -> None:
    """τ = 0 => remaining budget never scales with the sampled duration: the EAC is a
    constant even under duration uncertainty (and equals the deterministic EAC)."""
    s = _costed_net()
    tp, _ = _rich_inputs()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=60, target_uid=4),
        three_point=tp,
        jcl=JCLConfig(td_share=0.0),
    )
    assert r.cost_std == 0.0
    assert r.cost_min == r.cost_max == r.deterministic_eac == 1000.0
    assert r.remaining_td_total == 0.0 and r.remaining_ti_total == 1000.0
    assert r.td_share == 0.0


def test_zero_duration_task_cost_is_time_independent() -> None:
    """A costed milestone (zero ML remaining) has no burn rate — its budget is wholly
    time-independent even at τ = 1 (never a divide-by-zero, never fabricated)."""
    tasks = (
        _task(1, 1, budgeted_cost=10.0),
        _task(2, 0, budgeted_cost=500.0, is_milestone=True),
    )
    s = Schedule(name="S", project_start=MON, tasks=tasks, relationships=(_rel(1, 2),))
    r = compute_jcl(s, config=SRAConfig(iterations=10))
    assert r.remaining_ti_total == 500.0  # the milestone's budget
    assert r.remaining_td_total == 10.0
    assert r.deterministic_eac == 510.0


# --- the joint statement --------------------------------------------------------------


def test_quadrants_sum_to_one_and_jcl_bounded_by_marginals() -> None:
    s = _costed_net(budgets={1: 100.0, 2: 1000.0, 3: 50.0, 4: 25.0})
    tp, risks = _rich_inputs()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=200, target_uid=4),
        three_point=tp,
        risks=risks,
        jcl=JCLConfig(target_date=dt.date(2025, 1, 22), target_cost=1180.0),
    )
    assert abs((r.q_both + r.q_date_only + r.q_cost_only + r.q_neither) - 1.0) < 5e-4
    assert r.jcl <= min(r.scl, r.ccl) + 1e-9  # a joint event is a subset of each marginal
    assert r.jcl >= r.scl + r.ccl - 1.0 - 1e-9  # ... and at least the Fréchet lower bound
    assert r.q_both == r.jcl
    assert 0.0 < r.jcl < 1.0  # the chosen targets genuinely split this distribution


def test_frontier_points_achieve_the_confidence_and_costs_never_increase() -> None:
    s = _costed_net()
    tp, risks = _rich_inputs()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=150, target_uid=4),
        three_point=tp,
        risks=risks,
        jcl=JCLConfig(confidence=0.70),
    )
    assert r.frontier  # this distribution reaches P70 within the grid
    n = r.iterations
    prev_cost = None
    for iso, cost in r.frontier:
        joint = sum(1 for d, c in r.points if d <= iso and c <= cost) / n
        assert joint >= 0.70 - 1e-9
        if prev_cost is not None:
            assert cost <= prev_cost + 1e-9  # a later date never needs MORE cost
        prev_cost = cost


def test_config_clamps_are_applied() -> None:
    s = _costed_net()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=5),
        jcl=JCLConfig(td_share=7.0, cost_low=1.4, cost_ml=0.5, cost_high=0.2, confidence=3.0),
    )
    assert r.td_share == 1.0
    assert r.cost_uncertainty_on  # 1.4/1.4/1.4 after ordering-coercion is still not 1/1/1
    assert r.confidence == 0.99


def test_use_risk_register_false_matches_the_ssi_run_without_risks() -> None:
    s = _costed_net()
    tp, risks = _rich_inputs()
    cfg = SRAConfig(iterations=80, target_uid=4, use_risk_register=False)
    ssi = compute_sra_ssi(s, config=cfg, three_point=tp, risks=risks)
    jcl = compute_jcl(s, config=cfg, three_point=tp, risks=risks)
    assert jcl.finish_cdf == ssi.cdf
