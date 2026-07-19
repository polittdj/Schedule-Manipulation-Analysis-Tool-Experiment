"""Conditional branching for the SSI Monte-Carlo (ADR-0274, Hulett #9).

A conditional branch switches between a primary Plan A and a contingency Plan B based on a
CONDITION evaluated on a monitored activity each iteration (unlike #8's fixed-probability coin
flip). These pin: the freeze (no conditional == byte-identical to the frozen run), the
duration-metric and finish-metric switching (each activating exactly one plan fragnet), the
"which plan wins how often" fractions, plans on different ties + merge bias, the trip_when
direction, inert disclosure (missing monitor / plan tie), and determinism. The switching
mechanism was verified against the trusted ``compute_cpm`` before build (scratchpad prototype).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.sra import (
    BranchPlan,
    ConditionalBranch,
    ProbabilisticBranch,
    SRAConfig,
    compute_sra_ssi,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, dur_days: float) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY))


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _focus_net() -> Schedule:
    # 1(1d) -> 2(MONITOR 10d) -> 4(focus 1d); 1 -> 3(2d) -> 4.  Deterministic focus finish = 12 d.
    return Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1), _task(2, 10), _task(3, 2), _task(4, 1)),
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


def _plan(after: int, before: int, days: float, name: str = "") -> BranchPlan:
    d = int(days * DAY)
    return BranchPlan(after_uid=after, before_uid=before, low=d, ml=d, high=d, name=name)


def _cond(
    monitor: int,
    metric: str,
    threshold_days: float,
    plan_a: BranchPlan,
    plan_b: BranchPlan,
    **kw: object,
) -> ConditionalBranch:
    return ConditionalBranch(
        id=str(kw.get("id", "C1")),
        name=str(kw.get("name", "Contingency")),
        monitor_uid=monitor,
        metric=metric,
        threshold_minutes=int(threshold_days * DAY),
        plan_a=plan_a,
        plan_b=plan_b,
        trip_when=str(kw.get("trip_when", "at_or_above")),
    )


# --- the freeze --------------------------------------------------------------------------


def test_no_conditionals_is_byte_identical() -> None:
    """Passing no conditionals (the default) leaves the run byte-frozen (empty stream, no probe)."""
    s = _focus_net()
    cfg = SRAConfig(iterations=100, seed=1, target_uid=4)
    a = compute_sra_ssi(s, config=cfg)
    b = compute_sra_ssi(s, config=cfg, conditionals=())
    assert a.cdf == b.cdf
    assert a.conditionals == () == b.conditionals


def test_conditionals_do_not_perturb_the_probabilistic_branch_stream() -> None:
    """A conditional augments the network with its own fragnets but must not shift the #8 branch /
    duration / risk RNG streams: a run with a branch is byte-identical whether or not an
    *independent, always-Plan-A* conditional is also present (the conditional's own draws are on a
    disjoint stream and its point-mass fragnets consume no duration draw)."""
    s = _focus_net()
    cfg = SRAConfig(iterations=200, seed=5, target_uid=4)
    br = ProbabilisticBranch(
        id="B1", name="Rework", probability=0.5, after_uid=2, before_uid=4, low=0, ml=0, high=0
    )
    # a conditional that always sticks with Plan A (threshold huge; never trips) on the 1->3 tie,
    # off the driving path — it cannot change the finish, so only the streams could betray drift.
    never = _cond(
        2, "duration", 999, _plan(1, 3, 0, "A"), _plan(1, 3, 0, "B"), trip_when="at_or_above"
    )
    base = compute_sra_ssi(s, config=cfg, branches=[br])
    with_cond = compute_sra_ssi(s, config=cfg, branches=[br], conditionals=[never])
    assert base.cdf == with_cond.cdf  # branch/duration streams untouched
    assert base.branches == with_cond.branches


# --- duration-metric switching -----------------------------------------------------------


def test_duration_metric_switches_plans_and_splits_the_finish() -> None:
    """Monitor uid 2 ~ triangular(5,10,15) d; trip to Plan B (8 d) when its sampled duration >= 10,
    else stick with Plan A (2 d), both on the driving 2->4 tie. Every iteration takes exactly one
    plan, so the focus finish falls in two disjoint regimes: A => mon+4 d in [9,14); B => mon+10 d
    in [20,25]. The gap (14,20) is empty — the conditional-switch signature."""
    s = _focus_net()
    c = _cond(2, "duration", 10, _plan(2, 4, 2, "keep-A"), _plan(2, 4, 8, "fall-B"))
    r = compute_sra_ssi(
        s,
        config=SRAConfig(iterations=600, seed=1, target_uid=4),
        three_point={2: (5 * DAY, 10 * DAY, 15 * DAY)},
        conditionals=[c],
    )
    finishes = {off for off, _p in r.cdf}
    assert all(f < 14 * DAY or f >= 20 * DAY for f in finishes)  # disjoint regimes, empty gap
    assert any(f < 14 * DAY for f in finishes) and any(f >= 20 * DAY for f in finishes)  # both seen
    cs = r.conditionals[0]
    assert cs.applied and cs.id == "C1"
    assert cs.plan_a_hits + cs.plan_b_hits == 600  # exactly one plan per iteration
    assert 0.4 < cs.plan_b_fraction < 0.6  # symmetric triangular => ~half fall to the contingency
    assert abs(cs.plan_a_fraction + cs.plan_b_fraction - 1.0) < 1e-9
    assert cs.mean_delta_days > 0  # falling to B finishes later (bigger monitor AND bigger plan)


def test_point_mass_monitor_makes_the_choice_deterministic() -> None:
    """A monitor with no duration uncertainty (point mass at 10 d) always compares equal to the
    threshold, so at_or_above trips every iteration => Plan B 100% of the time."""
    s = _focus_net()
    c = _cond(2, "duration", 10, _plan(2, 4, 2), _plan(2, 4, 8))
    r = compute_sra_ssi(s, config=SRAConfig(iterations=50, seed=2, target_uid=4), conditionals=[c])
    cs = r.conditionals[0]
    assert cs.plan_b_fraction == 1.0 and cs.plan_a_hits == 0
    assert r.p10 == r.p50 == r.p90 == 20 * DAY  # 12 base -> 2->Fb(8)->4 => 10+8+... = 20 d


# --- finish-metric switching (probe solve) -----------------------------------------------


def test_finish_metric_uses_the_probe_solve() -> None:
    """The finish-metric reads the monitor's PRE-contingency early finish via a probe solve. ef[2] =
    1 d (task 1) + monitor; trip when ef[2] >= 11 d <=> monitor >= 10 d — the same split as the
    duration test, confirming the probe reads the monitor finish correctly and the plan fragnets
    (downstream) don't perturb it."""
    s = _focus_net()
    c = _cond(2, "finish", 11, _plan(2, 4, 2), _plan(2, 4, 8))
    r = compute_sra_ssi(
        s,
        config=SRAConfig(iterations=600, seed=1, target_uid=4),
        three_point={2: (5 * DAY, 10 * DAY, 15 * DAY)},
        conditionals=[c],
    )
    finishes = {off for off, _p in r.cdf}
    assert all(f < 14 * DAY or f >= 20 * DAY for f in finishes)  # same disjoint regimes
    cs = r.conditionals[0]
    assert cs.applied and cs.metric == "finish"
    assert 0.4 < cs.plan_b_fraction < 0.6


# --- plans on DIFFERENT ties + merge bias ------------------------------------------------


def test_plans_on_different_ties_respect_merge_bias() -> None:
    """Plan A on the driving 2->4 tie (5 d), Plan B on the SHORT 3->4 tie (3 d). With the monitor a
    point mass at 10 d and trip_when=below threshold 10 d never trips (10 !< 10), so Plan A is taken
    every iteration => finish 12+5 = 17 d. (Its counterpart: were B taken, the 3-path 1+2+3+1 = 7 d
    stays hidden behind the 12 d driver — merge bias — but here A always wins.)"""
    s = _focus_net()
    c = _cond(
        2, "duration", 10, _plan(2, 4, 5, "drive-A"), _plan(3, 4, 3, "slack-B"), trip_when="below"
    )
    r = compute_sra_ssi(s, config=SRAConfig(iterations=40, seed=1, target_uid=4), conditionals=[c])
    cs = r.conditionals[0]
    assert cs.applied and cs.plan_a_hits == 40 and cs.plan_b_hits == 0
    assert r.p10 == r.p50 == r.p90 == 17 * DAY  # Plan A on the driver: 12 + 5


def test_trip_when_below_flips_the_choice() -> None:
    """trip_when='below' falls to Plan B when the monitor runs SHORT. Point-mass monitor 10 d,
    threshold 12 d => 10 < 12 => trips => Plan B every iteration."""
    s = _focus_net()
    c = _cond(2, "duration", 12, _plan(2, 4, 2), _plan(2, 4, 8), trip_when="below")
    r = compute_sra_ssi(s, config=SRAConfig(iterations=30, seed=3, target_uid=4), conditionals=[c])
    cs = r.conditionals[0]
    assert cs.plan_b_fraction == 1.0 and cs.plan_a_hits == 0


# --- inert disclosure + determinism ------------------------------------------------------


def test_missing_plan_tie_makes_the_conditional_inert() -> None:
    """A conditional whose Plan A tie does not exist is never inserted (all-or-nothing); the finish
    is unchanged and the conditional is reported applied=False (never silent)."""
    s = _focus_net()
    base = compute_sra_ssi(s, config=SRAConfig(iterations=50, seed=1, target_uid=4))
    c = _cond(2, "duration", 10, _plan(99, 4, 5), _plan(2, 4, 8))  # no 99->4 tie
    r = compute_sra_ssi(s, config=SRAConfig(iterations=50, seed=1, target_uid=4), conditionals=[c])
    assert r.cdf == base.cdf  # inert -> byte-identical to no conditional
    cs = r.conditionals[0]
    assert cs.applied is False and cs.plan_a_hits == 0 and cs.plan_b_hits == 0


def test_missing_monitor_makes_the_conditional_inert() -> None:
    s = _focus_net()
    base = compute_sra_ssi(s, config=SRAConfig(iterations=40, seed=1, target_uid=4))
    c = _cond(777, "duration", 10, _plan(2, 4, 5), _plan(2, 4, 8))  # monitor 777 absent
    r = compute_sra_ssi(s, config=SRAConfig(iterations=40, seed=1, target_uid=4), conditionals=[c])
    assert r.cdf == base.cdf
    assert r.conditionals[0].applied is False


def test_conditional_is_deterministic_for_a_seed() -> None:
    s = _focus_net()
    c = _cond(2, "duration", 10, _plan(2, 4, 2), _plan(2, 4, 8))
    cfg = SRAConfig(iterations=200, seed=7, target_uid=4)
    tp = {2: (5 * DAY, 10 * DAY, 15 * DAY)}
    a = compute_sra_ssi(s, config=cfg, three_point=tp, conditionals=[c])
    b = compute_sra_ssi(s, config=cfg, three_point=tp, conditionals=[c])
    assert a.cdf == b.cdf
    assert a.conditionals == b.conditionals


def test_two_conditionals_on_the_same_tie_both_apply() -> None:
    """Two conditionals whose plans share the 2->4 tie both insert (chaining in series), neither
    inert. With both monitors point-mass-tripping to their Plan B, the finish adds BOTH contingency
    plans: 12 + 8 (C1-B) + 4 (C2-B) = 24 d."""
    s = _focus_net()
    c1 = _cond(2, "duration", 10, _plan(2, 4, 1, "a1"), _plan(2, 4, 8, "b1"), id="C1")
    c2 = _cond(2, "duration", 10, _plan(2, 4, 1, "a2"), _plan(2, 4, 4, "b2"), id="C2")
    r = compute_sra_ssi(
        s, config=SRAConfig(iterations=20, seed=1, target_uid=4), conditionals=[c1, c2]
    )
    assert {cs.id for cs in r.conditionals} == {"C1", "C2"}
    assert all(cs.applied for cs in r.conditionals)
    assert r.p50 == 24 * DAY  # 12 base + 8 + 4, both contingencies chained
