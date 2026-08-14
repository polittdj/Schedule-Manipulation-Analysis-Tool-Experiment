"""The JCL joint statement is pinned to its own joint sample (the 2026-08-14 batteries).

The first mutation batteries ever aimed at ``engine/jcl.py``: 45 mutant specs across three
rounds — 16 lead-designed, 14 independently workflow-designed, 3 written to prove this
module's own teeth, then 12 adversarial mutants designed specifically to survive the first
closure revision (two attackers independently produced the same multi-risk edit, so 44
distinct) — every one run sandboxed, import-origin canaried, instrument md5-restored
between mutants, against ``test_jcl`` + ``test_jcl_web`` (plus ``test_lhs`` /
``test_sra_view`` for survivor confirmation). TWENTY distinct mutants survived some
revision of that suite and are closed HERE by name; the twenty-first survivor class
(``sampling`` passthrough) needed no closure — ``test_lhs.py`` pins it (measured). The
closed families:

* the scl / ccl marginal definitions, the quadrant counters and shares — re-derived from
  the run's own ``points``;
* the frontier: ``k = ceil(confidence * n)`` at a genuinely FRACTIONAL ``confidence * n``,
  k-minimality, the full 5..95 grid walked to P95, grid-date dedup, and the
  ``len(subset) >= k`` skip rule;
* the default cost target compared UNROUNDED, on fixtures whose EAC is inexact at 2dp;
* the ``iterations >= 1`` gate, its precedence over the cost gate, and the lower-side
  clamps (the confidence and td_share floors);
* the fired-risk loop: the ADR-0308 completed-task guard, multi-risk impact SUMMING
  before the ADR-0359 replacement, the ``max(0, ·)`` opportunity floor, and the
  risk-to-COST coupling (cost burns the post-replacement duration — the joint coupling
  itself);
* the exact draw stream: interior tau, ascending-uid multiplier order (the swap's EAC
  delta asserted past 2dp rounding), and the ``spent + (ti + td)`` float association at
  NONZERO actuals (bit-identity at the raw default targets);
* the completion predicate shared with the duration model, ``sunk_total`` keeping
  unbudgeted actuals, the provenance echoes (seed / target_uid / iterations),
  ``cost_p80`` as PERCENTILE.INC of the sample, the cost-CDF step reaching 1.0, and the
  stored-finish realignment (the anchor on the focus AND the latest-stored fallback).

Each test re-derives its claim from the run's own joint sample, replays the engine's
exact draw stream by hand, or builds a fixture MEASURED to make the rule's boundary
observable — proven red against every closed mutant BY NAME, green intact, and scoped
(this module alone does not re-kill the mutants the older tests already own). Fixture
seeds are explicit wherever a liveness or margin precondition depends on the sampled
shape. The one KNOWN live JCL defect — the session's branches feed the SSI run but not
``compute_jcl`` — is the strict xfail in ``tests/web/test_jcl_web.py`` (JCL-BR-01,
ADR-0401).
"""

from __future__ import annotations

import datetime as dt
import math
import random

import pytest

from schedule_forensics.engine.cpm import offset_to_datetime
from schedule_forensics.engine.jcl import _FRONTIER_GRID, JCLConfig, compute_jcl
from schedule_forensics.engine.sra import (
    RiskFactorTable,
    ScheduleRisk,
    SRAConfig,
    _percentile,
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


def _costed_net(budgets: dict[int, float] | None = None) -> Schedule:
    """The SSI test network — 1(1d) -> 2(10d driver) -> 4(focus 1d); 1 -> 3(2d) -> 4."""
    b = budgets if budgets is not None else {2: 1000.0}
    tasks = tuple(
        _task(u, d, budgeted_cost=b.get(u, 0.0)) for u, d in ((1, 1), (2, 10), (3, 2), (4, 1))
    )
    return Schedule(
        name="S",
        project_start=MON,
        tasks=tasks,
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


def _rich_inputs() -> tuple[dict[int, tuple[int, int, int]], list[ScheduleRisk]]:
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl), 3: factor_to_bc_wc(2 * DAY, 4, tbl)}
    risks = [
        ScheduleRisk(id="R1", name="Late castings", probability=0.4, impact_days=5.0, affected=(3,))
    ]
    return tp, risks


# --- the joint statement re-derived from its own sample -------------------------------


def test_levels_and_quadrants_rederive_from_the_joint_sample() -> None:
    """scl / ccl / jcl and all four quadrant shares must equal the same counts re-derived
    from the run's own ``points`` — the marginals are (both+one_side)/n, never both/n, and
    the date-only / cost-only counters are not interchangeable. The FICSM cost multipliers
    are ON (0.7/1.0/1.4) so cost carries a driver independent of the finish date — without
    them cost is a monotone function of the critical driver's sampled duration and the
    late-but-cheap quadrant is STRUCTURALLY empty (measured: cost_only == 0 at every
    multipliers-off target probed), which would leave the swap mutants invisible."""
    s = _costed_net(budgets={1: 100.0, 2: 1000.0, 3: 50.0, 4: 25.0})
    tp, risks = _rich_inputs()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=200, seed=12345, target_uid=4),
        three_point=tp,
        risks=risks,
        jcl=JCLConfig(
            target_date=dt.date(2025, 1, 20),
            target_cost=1150.0,
            cost_low=0.7,
            cost_ml=1.0,
            cost_high=1.4,
        ),
    )
    n = r.iterations
    # the re-derivation compares 2dp-rounded point costs against the target: prove no point
    # sits close enough to the boundary for that rounding to blur the classification
    assert all(abs(c - r.target_cost) > 0.01 for _, c in r.points)
    both = sum(1 for d, c in r.points if d <= r.target_date and c <= r.target_cost)
    date_only = sum(1 for d, c in r.points if d <= r.target_date and c > r.target_cost)
    cost_only = sum(1 for d, c in r.points if d > r.target_date and c <= r.target_cost)
    neither = n - both - date_only - cost_only
    # the fixture genuinely populates all four quadrants — and asymmetrically, or the
    # date-only/cost-only SWAP would be invisible to the equality assertions below
    assert both > 0 and date_only > 0 and cost_only > 0 and neither > 0
    assert date_only != cost_only
    assert r.jcl == round(both / n, 4) == r.q_both
    assert r.scl == round((both + date_only) / n, 4)
    assert r.ccl == round((both + cost_only) / n, 4)
    assert r.q_date_only == round(date_only / n, 4)
    assert r.q_cost_only == round(cost_only / n, 4)
    assert r.q_neither == round(neither / n, 4)


def test_frontier_k_rounds_up_when_confidence_times_n_is_fractional() -> None:
    """iterations=115 at P70 makes confidence*n = 80.5: k must be ceil = 81. A floored k
    (80) picks the 80th-smallest EAC, whose joint probability 80/115 < 0.70 — the frontier
    would claim a confidence it does not achieve; the (k+1)-th cost would achieve it but
    not MINIMALLY. The re-derivation takes exactly the ceil-k-th smallest sampled EAC among
    iterations finishing on or before each frontier date (2dp rounding is monotonic, so the
    k-th smallest of the rounded costs IS the rounded k-th smallest raw cost), and re-checks
    the achieved joint share."""
    s = _costed_net()
    tp, risks = _rich_inputs()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=115, seed=12345, target_uid=4),
        three_point=tp,
        risks=risks,
        jcl=JCLConfig(confidence=0.70),
    )
    n = r.iterations
    assert (r.confidence * n) % 1 != 0  # the fixture genuinely exercises the rounding edge
    assert r.frontier
    assert len({iso for iso, _ in r.frontier}) == len(r.frontier)  # grid dates deduplicated
    k = math.ceil(r.confidence * n)
    rank_step_seen = False
    for iso, cost in r.frontier:
        subset = sorted(c for d, c in r.points if d <= iso)
        assert len(subset) >= k
        assert cost == subset[k - 1]  # exactly the minimum cost achieving the confidence
        rank_step_seen = rank_step_seen or subset[k - 2] != subset[k - 1]
        joint = sum(1 for d, c in r.points if d <= iso and c <= cost) / n
        assert joint >= r.confidence - 1e-9
    # the k-1/k order statistics differ at some gridpoint, or a floored k could hide here
    assert rank_step_seen


def test_default_cost_target_compares_unrounded_and_displays_rounded() -> None:
    """EAC = 999 x (1 - 33.4/100) = 665.334: the DISPLAYED deterministic EAC and target are
    rounded to 665.33, but the ≤-comparison must use the raw value — an all-point-mass run
    is 100% confident at its own default targets. Rounding the comparison target down to
    665.33 would turn every iteration's 665.334 into a cost overrun (ccl = 0)."""
    t1 = _task(1, 5, budgeted_cost=999.0, percent_complete=33.4)
    s = Schedule(name="S", project_start=MON, tasks=(t1, _task(2, 1)), relationships=(_rel(1, 2),))
    r = compute_jcl(s, config=SRAConfig(iterations=20))
    assert r.deterministic_eac == 665.33  # displayed: rounded
    assert r.target_cost == 665.33  # displayed: rounded
    assert r.ccl == 1.0 and r.jcl == 1.0  # compared: raw 665.334 <= 665.334
    assert r.q_neither == 0.0 and r.q_cost_only == 0.0


# --- gates and guards -----------------------------------------------------------------


def test_zero_iterations_is_refused_as_input_validation() -> None:
    """iterations=0 must be refused by the explicit >=1 gate with its own ValueError —
    never allowed to run zero iterations and die downstream in the statistics."""
    with pytest.raises(ValueError, match="iterations must be >= 1"):
        compute_jcl(_costed_net(), config=SRAConfig(iterations=0))


def test_completed_task_cannot_be_delayed_by_a_fired_risk() -> None:
    """ADR-0308 inside compute_jcl's own risk loop: a risk affecting ONLY a completed task
    must change nothing — the run equals the risk-free run exactly, and stays equal to the
    SSI run (whose own guard is separately pinned) on the same inputs."""
    t1 = _task(
        1,
        10,
        percent_complete=100.0,
        actual_start=MON,
        actual_finish=MON + dt.timedelta(days=14),
    )
    t2 = _task(2, 2, budgeted_cost=500.0)
    s = Schedule(name="S", project_start=MON, tasks=(t1, t2), relationships=(_rel(1, 2),))
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(2 * DAY, 4, tbl)}
    risk = [ScheduleRisk(id="R9", name="Ghost", probability=1.0, impact_days=15.0, affected=(1,))]
    cfg = SRAConfig(iterations=60, occurrence_mode="exact_overall")
    with_risk = compute_jcl(s, config=cfg, three_point=tp, risks=risk)
    without = compute_jcl(s, config=cfg, three_point=tp, risks=())
    assert with_risk.finish_cdf == without.finish_cdf  # the fired risk touched nothing
    assert with_risk.points == without.points
    ssi = compute_sra_ssi(s, config=cfg, three_point=tp, risks=risk)
    assert with_risk.finish_cdf == ssi.cdf  # and the SSI equivalence still holds


def test_fired_risk_drives_the_cost_burn_exactly() -> None:
    """The joint coupling, hand-exact: a certain risk (p=1.0) REPLACES the costed driver's
    sampled duration with 12d, so EVERY iteration's EAC is BAC x (12d / 10d ML) = 1,200.00
    and the finish collapses to a single point — the cost burns over the SAME post-risk
    duration the finish uses. Computing cost from the pre-risk sampled duration (or adding
    instead of replacing) scatters the EACs."""
    s = _costed_net()  # only task 2 costed, BAC 1000, ML 10d
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl)}  # genuine spread the replacement overrides
    risk = [
        ScheduleRisk(id="R2", name="Rebaseline", probability=1.0, impact_days=12.0, affected=(2,))
    ]
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=50, target_uid=4, occurrence_mode="exact_overall"),
        three_point=tp,
        risks=risk,
    )
    assert r.cost_min == r.cost_max == 1200.0  # 1000 x (5760 / 4800), every iteration
    assert all(c == 1200.0 for _, c in r.points)
    assert len(r.finish_cdf) == 1  # the replacement made the finish a point mass too


# --- exact replays of the draw stream -------------------------------------------------


def test_interior_td_share_burns_only_the_td_slice() -> None:
    """tau = 0.4 exactly: EAC = 0.6 x BAC + 0.4 x BAC x (sampled/ML) — replayed against the
    engine's own iteration-0 draw. The tau=0 and tau=1 endpoints are pinned elsewhere; an
    endpoint-preserving distortion of the split (e.g. tau squared) only shows here."""
    s = _costed_net()
    tbl = RiskFactorTable()
    bc, ml, wc = factor_to_bc_wc(10 * DAY, 3, tbl)
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=1, seed=777, target_uid=4),
        three_point={2: (bc, ml, wc)},
        jcl=JCLConfig(td_share=0.4),
    )
    rng = random.Random(777)
    minutes = max(0, round(_sample_triangular(rng.random(), float(bc), float(ml), float(wc))))
    expected = 0.6 * 1000.0 + 0.4 * 1000.0 * (minutes / ml)
    assert r.points[0][1] == round(expected, 2)
    assert r.remaining_ti_total == 600.0 and r.remaining_td_total == 400.0
    assert r.td_share == 0.4


def test_cost_multipliers_draw_in_ascending_uid_order() -> None:
    """Two costed uncertain tasks, multipliers ON: after the two duration draws (ascending
    uid), the engine draws m for uid 2 THEN uid 3 from the same stream — replayed by hand.
    Reversing the multiplier draw order swaps the m assignments and moves the EAC."""
    s = _costed_net(budgets={2: 1000.0, 3: 500.0})
    tbl = RiskFactorTable()
    bc2, ml2, wc2 = factor_to_bc_wc(10 * DAY, 3, tbl)
    bc3, ml3, wc3 = factor_to_bc_wc(2 * DAY, 4, tbl)
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=1, seed=42, target_uid=4),
        three_point={2: (bc2, ml2, wc2), 3: (bc3, ml3, wc3)},
        jcl=JCLConfig(cost_low=0.8, cost_ml=1.0, cost_high=1.3),
    )
    rng = random.Random(42)
    d2 = max(0, round(_sample_triangular(rng.random(), float(bc2), float(ml2), float(wc2))))
    d3 = max(0, round(_sample_triangular(rng.random(), float(bc3), float(ml3), float(wc3))))
    m2 = _sample_triangular(rng.random(), 0.8, 1.0, 1.3)
    m3 = _sample_triangular(rng.random(), 0.8, 1.0, 1.3)
    assert m2 != m3  # the draws genuinely differ, so a swapped order cannot hide
    expected = 1000.0 * (d2 / ml2) * m2 + 500.0 * (d3 / ml3) * m3
    swapped = 1000.0 * (d2 / ml2) * m3 + 500.0 * (d3 / ml3) * m2
    assert abs(expected - swapped) > 0.05  # ... and the swap moves the EAC past 2dp rounding
    assert r.points[0][1] == round(expected, 2)


# --- the cost CDF, the clamps, the provenance, the realignment ------------------------


def test_cost_cdf_is_the_right_continuous_step_reaching_one() -> None:
    """The cost CDF re-derived from the run's own points: one step per distinct EAC at
    cumulative count/n, and the last step lands exactly on (cost_max, 1.0). Distinct
    sampled minutes are ~0.21 apart in EAC on this fixture, so 2dp rounding cannot merge
    genuinely distinct values (asserted before the equality)."""
    s = _costed_net()
    tbl = RiskFactorTable()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=40, seed=12345, target_uid=4),
        three_point={2: factor_to_bc_wc(10 * DAY, 3, tbl)},
    )
    n = r.iterations
    costs = sorted(c for _, c in r.points)
    assert len(set(costs)) == len(r.cost_cdf)  # 2dp did not merge distinct values here
    expected: list[tuple[float, float]] = []
    seen = 0
    for v in sorted(set(costs)):
        seen += sum(1 for c in costs if c == v)
        expected.append((v, round(seen / n, 4)))
    assert r.cost_cdf == tuple(expected)
    assert r.cost_cdf[-1] == (r.cost_max, 1.0)


def test_lower_side_clamps_floor_confidence_and_td_share() -> None:
    """The clamp test's other half: negative confidence floors to 0.01 and negative
    td_share to 0.0 (which makes the EAC duration-independent even under spread)."""
    s = _costed_net()
    tp, _ = _rich_inputs()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=30, target_uid=4),
        three_point=tp,
        jcl=JCLConfig(td_share=-2.0, confidence=-0.5),
    )
    assert r.confidence == 0.01
    assert r.td_share == 0.0
    assert r.cost_std == 0.0 and r.cost_min == r.cost_max  # the floor genuinely binds
    # at the floored tau the driver's budget is wholly TI — it still counts as costed
    # (the population predicate is ti+td > 0, not td > 0)
    assert r.incomplete_costed_count == 1


def test_provenance_echoes_the_run_inputs() -> None:
    """seed / target_uid / iterations are the reproducibility disclosure a re-run depends
    on — they must echo the config that actually produced the run."""
    r = compute_jcl(_costed_net(), config=SRAConfig(iterations=33, seed=777, target_uid=4))
    assert r.seed == 777
    assert r.target_uid == 4
    assert r.iterations == 33


def test_dates_realign_to_the_stored_finish_anchor() -> None:
    """ADR-0123 realignment inside _build_jcl_result: with the focus task carrying a STORED
    finish, every reported date is shifted so the deterministic finish lands on it — the
    deterministic date IS the stored date by construction (anchor = naive + correction),
    independent of the calendar arithmetic. Zeroing the correction strands the dates on the
    pure-CPM axis (2025-01-21 here). Every other engine fixture stores no finish, so this
    is the only engine-level test where the correction is non-zero."""
    anchor = dt.datetime(2025, 1, 24, 16, 0)
    tasks = (
        _task(1, 1),
        _task(2, 10, budgeted_cost=1000.0),
        _task(3, 2),
        _task(4, 1, finish=anchor),
    )
    s = Schedule(
        name="S",
        project_start=MON,
        tasks=tasks,
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )
    r = compute_jcl(s, config=SRAConfig(iterations=10, target_uid=4))
    assert r.deterministic_finish == 12 * DAY  # the CPM offset itself is untouched
    assert r.deterministic_finish_date == "2025-01-24"  # ... but the date axis is anchored
    assert r.finish_p50_date == "2025-01-24"
    assert r.target_date == "2025-01-24"  # the default target rides the realigned axis
    assert r.scl == 1.0


# --- the adversarial round's closures (population holes the 33-mutant battery missed) --


def test_gate_order_iterations_before_cost_gate() -> None:
    """A call violating BOTH gates gets the iterations message — input validation runs
    before the domain gate, so a zero-iteration request is never re-labeled a cost problem."""
    s = Schedule(
        name="S", project_start=MON, tasks=(_task(1, 1), _task(2, 2)), relationships=(_rel(1, 2),)
    )
    with pytest.raises(ValueError, match="iterations must be >= 1"):
        compute_jcl(s, config=SRAConfig(iterations=0))


def test_multiple_fired_risks_sum_before_replacing() -> None:
    """Two certain risks on the SAME activity: their impacts SUM (3d + 4d) and the sum
    replaces the sampled duration — finish collapses to 1+7+1 = 9d and the cost burns
    BAC x (7d/10d) = 700.00 every iteration, still equal to the SSI run. Last-one-wins
    (or overwrite) aggregation moves both."""
    s = _costed_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl)}
    risks = [
        ScheduleRisk(id="Ra", name="A", probability=1.0, impact_days=3.0, affected=(2,)),
        ScheduleRisk(id="Rb", name="B", probability=1.0, impact_days=4.0, affected=(2,)),
    ]
    cfg = SRAConfig(iterations=30, target_uid=4, occurrence_mode="exact_overall")
    r = compute_jcl(s, config=cfg, three_point=tp, risks=risks)
    assert r.finish_cdf == ((9 * DAY, 1.0),)
    assert r.cost_min == r.cost_max == 700.0
    assert r.finish_cdf == compute_sra_ssi(s, config=cfg, three_point=tp, risks=risks).cdf


def test_negative_summed_impact_floors_at_zero() -> None:
    """An opportunity risk (negative impact) can at most take the activity to ZERO
    remaining duration — never negative. With t2 floored to 0 the 1->3->4 path (4d)
    governs and the driver burns no TD cost; the SSI equality holds through the floor."""
    s = _costed_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl)}
    risks = [
        ScheduleRisk(id="RN", name="Windfall", probability=1.0, impact_days=-20.0, affected=(2,))
    ]
    cfg = SRAConfig(iterations=30, target_uid=4, occurrence_mode="exact_overall")
    r = compute_jcl(s, config=cfg, three_point=tp, risks=risks)
    assert r.finish_cdf == ((4 * DAY, 1.0),)
    assert r.cost_min == r.cost_max == 0.0
    assert r.finish_cdf == compute_sra_ssi(s, config=cfg, three_point=tp, risks=risks).cdf


def test_focus_event_finish_not_project_finish() -> None:
    """The joint sample's schedule coordinate is the FOCUS EVENT's per-iteration finish.
    With the focus on interior task 3 (its own chain is 1d + 2d = 3d) while the project
    finish is driven by the 10d driver, the deterministic focus finish is 3d and the
    distribution equals the SSI run aimed at the same focus — reading the project finish
    instead would ride the driver's axis."""
    s = _costed_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl), 3: factor_to_bc_wc(2 * DAY, 4, tbl)}
    cfg = SRAConfig(iterations=80, target_uid=3)
    r = compute_jcl(s, config=cfg, three_point=tp)
    assert r.deterministic_finish == 3 * DAY
    assert r.finish_cdf == compute_sra_ssi(s, config=cfg, three_point=tp).cdf


def test_anchor_falls_back_to_latest_stored_finish() -> None:
    """When the focus stores NO finish, the realignment anchor falls back to the latest
    stored finish anywhere in the schedule (here on non-focus t2, 2025-01-30) — bypassing
    the fallback strands the axis on pure-CPM dates (2025-01-21)."""
    tasks = (
        _task(1, 1),
        _task(2, 10, budgeted_cost=1000.0, finish=dt.datetime(2025, 1, 30, 12, 0)),
        _task(3, 2),
        _task(4, 1),
    )
    s = Schedule(
        name="S",
        project_start=MON,
        tasks=tasks,
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )
    r = compute_jcl(s, config=SRAConfig(iterations=10, target_uid=4))
    assert r.deterministic_finish_date == "2025-01-30"
    assert r.finish_p50_date == "2025-01-30"


def test_completed_predicate_and_sunk_total_include_unbudgeted_actuals() -> None:
    """The cost split uses the SAME completion predicate as the duration model (a stored
    actual_finish completes a task even at pc=80), and sunk_total keeps an incomplete
    task's actuals even when it carries NO budget: t1 contributes its 130 actual as a
    completed final; t2 (budget 0, actuals 250) contributes its spend and nothing else.
    EAC = 130 + 250 = sunk_total = 380."""
    t1 = _task(
        1,
        5,
        budgeted_cost=100.0,
        actual_cost=130.0,
        percent_complete=80.0,
        actual_start=MON,
        actual_finish=MON + dt.timedelta(days=7),
    )
    t2 = _task(2, 1, budgeted_cost=0.0, actual_cost=250.0, percent_complete=40.0)
    s = Schedule(name="S", project_start=MON, tasks=(t1, t2), relationships=(_rel(1, 2),))
    r = compute_jcl(s, config=SRAConfig(iterations=10))
    assert r.deterministic_eac == 380.0
    assert r.sunk_total == 380.0
    assert r.completed_count == 1
    assert r.incomplete_costed_count == 0  # actuals without remaining budget are not "costed"


def test_interior_tau_point_mass_costs_stay_bit_identical() -> None:
    """The documented float association: an all-point-mass run's iteration costs are
    BIT-IDENTICAL to the deterministic EAC even at interior tau with NONZERO actuals.
    ``spent + (ti + td)`` is the pinned association, and with spent = 0.0 any
    re-association is exact (0.0 + x carries no ulp) — the first fixture draft proved
    that by NOT killing the association mutant — so this fixture records a 0.01 spend
    at values where ``(spent + ti) + td`` genuinely differs in the last ulp. At the raw
    default targets ccl = jcl = 1.0 exactly; a re-associated deterministic EAC drifts
    one ulp and the unrounded ≤-comparison turns every iteration into a fabricated
    100% cost overrun."""
    t1 = _task(1, 5, budgeted_cost=2.26, actual_cost=0.01, percent_complete=30.0)
    s = Schedule(name="S", project_start=MON, tasks=(t1, _task(2, 1)), relationships=(_rel(1, 2),))
    r = compute_jcl(s, config=SRAConfig(iterations=15), jcl=JCLConfig(td_share=0.7))
    spent, rem = 0.01, 2.26 * (1.0 - 30.0 / 100.0)
    ti, td = (1.0 - 0.7) * rem, 0.7 * rem
    assert spent + (ti + td) != spent + ti + td  # the fixture genuinely exercises the ulp
    assert r.ccl == 1.0 and r.jcl == 1.0 and r.q_neither == 0.0
    assert r.cost_min == r.cost_max == r.deterministic_eac == 1.59


def test_cost_p80_is_percentile_inc_of_the_sample() -> None:
    """cost_p80 re-derived from the run's own points with the shared PERCENTILE.INC helper
    (2dp point rounding can skew the interpolation by at most a cent — the tolerance —
    while the p80/p81 rank step on this fixture is ~0.49, asserted discriminating)."""
    s = _costed_net()
    tbl = RiskFactorTable()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=40, seed=12345, target_uid=4),
        three_point={2: factor_to_bc_wc(10 * DAY, 3, tbl)},
    )
    costs = sorted(c for _, c in r.points)
    p80 = _percentile(costs, 80)
    assert abs(_percentile(costs, 81) - p80) > 0.1  # the fixture separates adjacent ranks
    assert abs(r.cost_p80 - p80) <= 0.02


def test_frontier_walks_the_whole_grid_to_p95() -> None:
    """The grid constant is 5..95 step 5 (data pin), and the frontier genuinely evaluates
    through P95: on a heavy-tailed fixture at 50% confidence, the frontier's date set
    equals the reachable distinct grid dates re-derived from the run's own finish CDF
    (PERCENTILE.INC over the reconstructed sample, the same skip rule len(subset) >= k),
    and the P95 gridpoint's date — distinct from P90's here — is present."""
    assert tuple(range(5, 100, 5)) == _FRONTIER_GRID
    s = _costed_net()
    r = compute_jcl(
        s,
        config=SRAConfig(iterations=90, seed=12345, target_uid=4),
        three_point={2: (4320, 4800, 16800)},
        jcl=JCLConfig(confidence=0.5),
    )
    n = r.iterations
    arr: list[float] = []
    for off, cum in r.finish_cdf:
        arr += [float(off)] * (round(cum * n) - len(arr))
    assert len(arr) == n  # the sample reconstructs exactly from the CDF
    k = math.ceil(r.confidence * n)

    def _grid_date(p: float) -> str:
        off = max(round(_percentile(arr, p)), 0)
        return offset_to_datetime(MON, off, s.calendar).date().isoformat()

    grid_dates = {_grid_date(float(p)) for p in _FRONTIER_GRID}
    expected = sorted(d for d in grid_dates if sum(1 for pd, _ in r.points if pd <= d) >= k)
    assert sorted(iso for iso, _ in r.frontier) == expected
    p90_d, p95_d = _grid_date(90.0), _grid_date(95.0)
    assert p95_d != p90_d  # the tail genuinely separates the last two gridpoints
    assert p95_d in {iso for iso, _ in r.frontier}
