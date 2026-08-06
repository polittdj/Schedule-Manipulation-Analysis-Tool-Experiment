"""SSI Schedule Risk & Opportunity Analysis engine (ADR-0123) — the parity-anchored SSI path.

Pins the DETERMINISTIC facts validated against the operator's SSI exports: the BC/WC formula
(ML = remaining), the all-ML == ``compute_cpm`` equivalence, focus-event targeting, the
duration-REPLACING risk model (ADR-0359 — a fired risk's impact replaces the affected
activity's duration, and the activity samples its own Best/Worst when the risk does not fire),
the occurrence modes, the deterministic OAT sensitivity, and the optional correlation. The
stochastic distribution is NOT claimed bit-exact vs SSI's RNG (std-lib Mersenne Twister !=
SSI's generator — ADR-0005/0106)."""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import replace

from schedule_forensics.engine.correlation import CorrelationSpec
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.sra import (
    RiskFactorTable,
    ScheduleRisk,
    SRAConfig,
    _consequence_rating,
    _occurrence_schedule,
    _prob_rating,
    compute_oat_sensitivity,
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
    # 1(1d) -> 2(10d, the driver) -> 4(focus, 1d);  1 -> 3(2d, off-path) -> 4.
    # deterministic finish of the focus task 4 = 1+10+1 = 12 days.
    return Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1), _task(2, 10), _task(3, 2), _task(4, 1)),
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


# --- BC/WC formula (the headline parity anchor) --------------------------------------


def test_factor_to_bc_wc_matches_the_ssi_formula() -> None:
    """ADR-0307: the first table column is the Best Case **as a % of** the ML, not a % to subtract.

    These are not the code's own arithmetic restated — they are SSI's OWN stored Best/Worst Case
    durations, read off the reference ``00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp`` (fields
    ``Best Case Duration``/``Worst Case Duration``, populated on 919 activities). The corrected
    rule reproduces 852/919 exactly; the previous ``ML*(1 - sub%/100)`` reproduced 140, every one
    of them factor 1 — the degenerate band where ``1 - 0.50 == 0.50`` makes both rules agree.
    """
    tbl = RiskFactorTable()
    # factor 3: BC = 30% OF the ML / WC = +30% (SSI stored, UID 6640: 115h18m -> 34h33m36s)
    assert factor_to_bc_wc(10 * DAY, 3, tbl) == (3 * DAY, 10 * DAY, 13 * DAY)
    # factor 5: BC = 10% OF the ML / WC = +50% (SSI stored, UID 6872: 8h02m -> 0h48m)
    assert factor_to_bc_wc(10 * DAY, 5, tbl) == (1 * DAY, 10 * DAY, round(15 * DAY))
    # factor 4: BC = 20% OF the ML / WC = +40% (SSI stored, UID 166: 17h35m -> 3h31m12s)
    assert factor_to_bc_wc(10 * DAY, 4, tbl) == (2 * DAY, 10 * DAY, 14 * DAY)
    # factor 1 is the degenerate band — the old and new rules agree here, which is exactly why the
    # inversion survived: a validation drawn from factor-1 rows passes under either reading
    assert factor_to_bc_wc(10 * DAY, 1, tbl) == (5 * DAY, 10 * DAY, 11 * DAY)
    # ML is the REMAINING duration passed in (not any original) — the UID-35 regression
    assert factor_to_bc_wc(1711, 2, tbl) == (round(1711 * 0.4), 1711, round(1711 * 1.2))
    # factor 0 = NO uncertainty: BC = ML = WC = the remaining duration (operator: a 0 means "use
    # the remaining duration, there is no Best/Worst case", never clamp it up to 1)
    assert factor_to_bc_wc(10 * DAY, 0, tbl) == (10 * DAY, 10 * DAY, 10 * DAY)
    assert factor_to_bc_wc(1711, 0, tbl) == (1711, 1711, 1711)
    # the Best Case can never exceed the Most Likely
    for f in range(0, 6):
        bc, ml, wc = factor_to_bc_wc(1711, f, tbl)
        assert bc <= ml <= wc


def test_ssi_factor_ladder_widens_the_spread_and_holds_the_mean() -> None:
    """The property that makes the ladder meaningful — and that the inverted rule destroyed.

    Under SSI's real rule a higher Risk Ranking Factor widens the Best/Worst *spread* while the
    triangular mean stays a constant 0.8667*ML. Under the old inverted rule every factor produced
    the SAME 0.6*ML spread and the factor merely slid the mean later (0.8667 -> 1.1333*ML), which
    is what biased the reference run's focus finish ~143 calendar days late.
    """
    tbl = RiskFactorTable()
    ml = 100 * DAY
    spreads, means = [], []
    for f in range(1, 6):
        bc, mlv, wc = factor_to_bc_wc(ml, f, tbl)
        spreads.append(wc - bc)
        means.append((bc + mlv + wc) / 3.0)
    # the spread widens monotonically with the factor
    assert spreads == sorted(spreads) and spreads[0] < spreads[-1]
    # ...while the mean is held constant across every band
    assert all(abs(m - means[0]) <= 1.0 for m in means)
    assert math.isclose(means[0], 0.8667 * ml, rel_tol=1e-3)


def test_a_completed_activity_carries_no_duration_uncertainty() -> None:
    """ADR-0307: finished work is a recorded fact, never a forecast.

    MSPDI omits ``<RemainingDuration>`` on a 100%-complete task, so the web layer's
    ``rem if rem is not None else duration`` fallback handed the FULL original duration to
    ``factor_to_bc_wc`` and the run then re-randomised work that had already happened. SSI never
    does this: of the 634 100%-complete leaves in the reference SRA Large Test File2.mpp, ZERO
    carry a stored Best/Worst Case, while all 919 incomplete factor-bearing ones do.
    """

    def _net(driver: Task) -> Schedule:
        return Schedule(
            name="S",
            project_start=MON,
            tasks=(_task(1, 1), driver, _task(3, 2), _task(4, 1)),
            relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
        )

    cfg = SRAConfig(iterations=200, seed=7, target_uid=4)
    # a caller hands the completed driver a wide Best/Worst anyway — the engine must ignore it
    wide = {2: (1 * DAY, 10 * DAY, 40 * DAY)}
    done = compute_sra_ssi(_net(_task(2, 10, percent_complete=100.0)), config=cfg, three_point=wide)
    assert done.std_days == 0.0, "a completed activity must not inject variance"
    assert done.p10 == done.p90 == done.deterministic_finish
    # and the same spread on an INCOMPLETE driver still does move the finish (guard is not a no-op)
    live = _task(2, 10, percent_complete=0.0, remaining_duration_minutes=10 * DAY)
    assert compute_sra_ssi(_net(live), config=cfg, three_point=wide).std_days > 0.0


def test_a_register_risk_never_delays_completed_work() -> None:
    """ADR-0308: the ADR-0307 point-mass guard alone did NOT stop the register.

    A risk targeting a completed activity still had its impact added to that activity's duration:
    a 50%-probability 20-day risk on a completed driver produced std 9.99 wd and moved P90 by 20
    working days on work that had already finished. The impact is now skipped, and because a risk
    that fires but moves nothing must never be silent, the stat is flagged ``applied=False``.
    """

    def _net(driver: Task) -> Schedule:
        return Schedule(
            name="S",
            project_start=MON,
            tasks=(_task(1, 1), driver, _task(3, 2), _task(4, 1)),
            relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
        )

    risk = (ScheduleRisk(id="r", name="risk", probability=0.5, impact_days=20.0, affected=(2,)),)
    cfg = SRAConfig(iterations=200, seed=3, target_uid=4, use_risk_register=True)
    done = compute_sra_ssi(_net(_task(2, 10, percent_complete=100.0)), config=cfg, risks=risk)
    assert done.std_days == 0.0, "a risk must not delay an activity that is already complete"
    assert done.p90 == done.deterministic_finish
    assert done.risks[0].applied is False, "an inert risk must disclose itself, never fire silently"
    assert done.risks[0].hits > 0, "it still fired — the hit count is real, the impact is not"
    # the guard is not a blanket no-op: the same risk on live work still moves the finish
    live = _task(2, 10, percent_complete=0.0, remaining_duration_minutes=10 * DAY)
    hot = compute_sra_ssi(_net(live), config=cfg, risks=risk)
    assert hot.std_days > 0.0 and hot.risks[0].applied is True


def test_factor_zero_is_a_point_mass_no_spread() -> None:
    """A factor-0 task carries no Best/Worst spread, so it contributes no duration uncertainty to
    the focus finish — the simulated finish equals the deterministic finish."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 0, tbl)}  # the driver ranked 0 -> no uncertainty
    r = compute_sra_ssi(s, config=SRAConfig(iterations=50, target_uid=4), three_point=tp)
    assert r.p10 == r.p50 == r.p90 == 12 * DAY  # no spread at all


def test_factor_table_clamps_out_of_range() -> None:
    tbl = RiskFactorTable()
    assert tbl.for_factor(0) == tbl.for_factor(1)
    assert tbl.for_factor(9) == tbl.for_factor(5)


# --- equivalence + focus targeting ---------------------------------------------------


def test_all_point_mass_equals_compute_cpm_focus_finish() -> None:
    """No factors and no risks => every activity is a point mass at ML, so the simulated focus
    finish == the deterministic focus finish (the ADR-0106 trusted-solver equivalence)."""
    s = _focus_net()
    cpm = compute_cpm(s)
    cfg = SRAConfig(iterations=10, target_uid=4)
    r = compute_sra_ssi(s, config=cfg)
    assert r.deterministic_finish == cpm.timings[4].early_finish == 12 * DAY
    assert r.p10 == r.p50 == r.p90 == r.deterministic_finish
    assert r.deterministic_percentile == 1.0  # the whole mass sits at the deterministic value


def test_target_uid_none_reports_project_finish() -> None:
    s = _focus_net()
    cpm = compute_cpm(s)
    r = compute_sra_ssi(s, config=SRAConfig(iterations=5, target_uid=None))
    assert r.deterministic_finish == cpm.project_finish == 12 * DAY


# --- risk replaces the affected duration (ADR-0359) ----------------------------------


def test_a_fired_risk_replaces_the_affected_tasks_duration_with_its_impact() -> None:
    """SSI semantics (ADR-0359, measured on SSI's own 2026-08-06 Sensitivity export): a fired
    risk's impact REPLACES the affected activity's duration — it does not stack on the ML. The
    committed R/O rows pin it: a 321-wd impact on a 16.52-wd-ML task slips the focus 304.48 wd
    (= impact - ML), not 321.

    The discriminator here is deliberately an impact SMALLER than the ML: under replacement the
    focus finish lands EARLIER than the deterministic 12 d (1+5+1 = 7 d), which the old
    ``ML + impact`` arithmetic (1+15+1 = 17 d) can never produce."""
    s = _focus_net()
    risk = ScheduleRisk(id="R", name="r", probability=1.0, impact_days=5.0, affected=(2,))
    r = compute_sra_ssi(s, config=SRAConfig(iterations=20, target_uid=4), risks=[risk])
    assert r.p10 == r.p50 == r.p90 == 7 * DAY
    assert r.risks[0].hits == 20


def test_two_fired_risks_on_one_task_replace_with_their_summed_impacts() -> None:
    """Two risks firing on the same activity in one iteration replace its duration with the SUM
    of their impacts (5+3 = 8 d → focus 1+8+1 = 10 d) — not the last one to fire, and never
    stacked on the ML (which would give 1+18+1 = 20 d)."""
    s = _focus_net()
    risks = [
        ScheduleRisk(id="R1", name="a", probability=1.0, impact_days=5.0, affected=(2,)),
        ScheduleRisk(id="R2", name="b", probability=1.0, impact_days=3.0, affected=(2,)),
    ]
    r = compute_sra_ssi(s, config=SRAConfig(iterations=10, target_uid=4), risks=risks)
    assert r.p10 == r.p50 == r.p90 == 10 * DAY


def test_a_risk_bearing_task_samples_its_best_worst_when_the_risk_does_not_fire() -> None:
    """SSI lists the R/O tasks in its OWN Sensitivity export as duration rows too (ADR-0359):
    a risk-affected activity keeps its Best/Worst sampling in the iterations the risk does NOT
    fire; a fired risk then replaces the draw outright.

    Two halves, each a discriminator: a sure-fire risk pins the finish (the replacement wins
    every iteration, wide factor notwithstanding), while a never-fire risk leaves the factor's
    spread fully alive — the old point-mass forcing produced zero spread there."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 5, tbl)}  # a wide Best/Worst on the driver
    sure = ScheduleRisk(id="R", name="r", probability=1.0, impact_days=5.0, affected=(2,))
    r = compute_sra_ssi(
        s, config=SRAConfig(iterations=50, target_uid=4), three_point=tp, risks=[sure]
    )
    assert r.p10 == r.p90 == 7 * DAY  # replaced every iteration — no Best/Worst variance
    never = ScheduleRisk(id="R", name="r", probability=0.0, impact_days=5.0, affected=(2,))
    r2 = compute_sra_ssi(
        s, config=SRAConfig(iterations=50, target_uid=4), three_point=tp, risks=[never]
    )
    assert r2.std_days > 0.0, "not-fired iterations must sample the activity's Best/Worst"
    assert r2.risks[0].hits == 0


def test_use_risk_register_false_drops_the_risk() -> None:
    s = _focus_net()
    risk = ScheduleRisk(id="R", name="r", probability=1.0, impact_days=5.0, affected=(2,))
    r = compute_sra_ssi(
        s, config=SRAConfig(iterations=5, target_uid=4, use_risk_register=False), risks=[risk]
    )
    assert r.p50 == 12 * DAY and not r.used_risks  # back to the un-risked deterministic finish


# --- occurrence modes ----------------------------------------------------------------


def test_occurrence_modes_exact_vs_random() -> None:
    risks = [ScheduleRisk(id="R", name="r", probability=0.25, impact_days=1.0, affected=(2,))]
    exact = _occurrence_schedule(risks, "exact_overall", 100, 7)
    assert sum(exact[0]) == 25  # exactly round(0.25 * 100)
    rand = _occurrence_schedule(risks, "random_each", 100, 7)
    assert 10 <= sum(rand[0]) <= 40  # close to 25, varies (seeded → deterministic count)
    # the occurrence stream is disjoint from the duration RNG: the mode never shifts a no-risk run
    s = _focus_net()
    a = compute_sra_ssi(
        s, config=SRAConfig(iterations=50, target_uid=4, occurrence_mode="random_each")
    )
    b = compute_sra_ssi(
        s, config=SRAConfig(iterations=50, target_uid=4, occurrence_mode="exact_overall")
    )
    assert a.p50 == b.p50


# --- deterministic OAT sensitivity ---------------------------------------------------


def test_oat_sensitivity_ranks_the_driver_above_the_off_path_task() -> None:
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {
        2: factor_to_bc_wc(10 * DAY, 3, tbl),  # driver: BC 3d / WC 13d (ADR-0307: BC = 30% OF ML)
        3: factor_to_bc_wc(2 * DAY, 3, tbl),  # off-path: tiny swing, never reaches the focus
    }
    oat = compute_oat_sensitivity(s, three_point=tp, target_uid=4)
    by = {o.unique_id: o for o in oat}
    # the driver swings the focus both ways: BC pulls it in 7 wd (12 -> 5), WC pushes it out 3 wd.
    # ADR-0307 corrected the Best Case from 70% to 30% OF the ML, so the OPPORTUNITY side of the
    # swing widens from 3 to 7 wd; the risk side is unchanged because the WC rule was always right.
    assert by[2].opportunity_days == 7.0 and by[2].risk_days == 3.0 and by[2].total_days == 10.0
    # the off-path task can't move the focus at all
    assert by[3].total_days == 0.0
    # sorted by total desc → the driver is first
    assert oat[0].unique_id == 2


def test_oat_excludes_listed_uids() -> None:
    s = _focus_net()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, RiskFactorTable())}
    oat = compute_oat_sensitivity(s, three_point=tp, target_uid=4, exclude_uids=frozenset({2}))
    assert all(o.unique_id != 2 for o in oat)


def test_oat_emits_a_fired_alone_risk_row_with_replace_semantics() -> None:
    """The register contributes R/O rows to the OAT tornado (ADR-0359), exactly as SSI's
    Sensitivity export ranks them: the risk fired ALONE, its impact REPLACING the affected
    activity's remaining duration. Impact 20 d on the 10-d driver → focus 1+20+1 = 22 d,
    a 10-wd slip over the 12-d baseline (the old additive arithmetic would say 20)."""
    s = _focus_net()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, RiskFactorTable())}
    risk = ScheduleRisk(id="R9", name="storm", probability=0.4, impact_days=20.0, affected=(2,))
    oat = compute_oat_sensitivity(s, three_point=tp, target_uid=4, risks=[risk])
    ro = [o for o in oat if o.risk_id is not None]
    assert len(ro) == 1
    row = ro[0]
    assert row.risk_id == "R9" and row.risk_name == "storm" and row.unique_id == 2
    assert row.opportunity_days == 0.0 and row.risk_days == 10.0 and row.total_days == 10.0
    # the affected activity ALSO keeps its own duration row — SSI lists both
    assert any(o.unique_id == 2 and o.risk_id is None for o in oat)
    # rows stay one ranked list: the 10-wd R/O row sorts with (here, level with) the driver's own
    assert [o.total_days for o in oat] == sorted((o.total_days for o in oat), reverse=True)


# --- correlation ---------------------------------------------------------------------


def test_correlation_widens_the_focus_distribution() -> None:
    """A blanket correlation makes the activity durations move together, so the focus finish spread
    is wider than the independent (CLT-cancelling) case."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {1: factor_to_bc_wc(1 * DAY, 3, tbl), 2: factor_to_bc_wc(10 * DAY, 3, tbl)}
    indep = compute_sra_ssi(
        s, config=SRAConfig(iterations=400, seed=1, target_uid=4, correlation=0.0), three_point=tp
    )
    corr = compute_sra_ssi(
        s, config=SRAConfig(iterations=400, seed=1, target_uid=4, correlation=0.6), three_point=tp
    )
    assert corr.std_days > indep.std_days


# --- correlation MATRIX (ADR-0270) ---------------------------------------------------


def test_correlation_matrix_widens_and_is_a_distinct_mode() -> None:
    """A full matrix (a shared-driver group at 0.6 over the two drivers) widens the spread like
    the scalar blanket does, BUT is a DISTINCT mode: the multivariate copula draws N idiosyncratic
    normals (no shared common draw), so its distribution differs from the scalar r=0.6 run."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {1: factor_to_bc_wc(1 * DAY, 3, tbl), 2: factor_to_bc_wc(10 * DAY, 3, tbl)}
    base = SRAConfig(iterations=400, seed=1, target_uid=4)
    indep = compute_sra_ssi(s, config=base, three_point=tp)
    spec = CorrelationSpec(groups=(((1, 2), 0.6),))
    mat = compute_sra_ssi(s, config=replace(base, correlation_matrix=spec), three_point=tp)
    scalar = compute_sra_ssi(s, config=replace(base, correlation=0.6), three_point=tp)
    assert mat.std_days > indep.std_days  # correlation widens the finish distribution
    assert mat.correlation_matrix_applied and not mat.correlation_matrix_repaired
    assert mat.cdf != scalar.cdf  # distinct mode — not a silent reroute of the scalar path


def test_correlation_matrix_infeasible_is_repaired_and_surfaced() -> None:
    """Three tasks each mutually correlated at -0.6 is infeasible (smallest eigenvalue -0.2); the
    run repairs to the nearest valid matrix and SURFACES the raw min-eigenvalue + repair size."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {u: factor_to_bc_wc(d * DAY, 3, tbl) for u, d in ((1, 1), (2, 10), (3, 2))}
    spec = CorrelationSpec(groups=(((1, 2, 3), -0.6),))
    r = compute_sra_ssi(
        s,
        config=SRAConfig(iterations=200, seed=1, target_uid=4, correlation_matrix=spec),
        three_point=tp,
    )
    assert r.correlation_matrix_applied and r.correlation_matrix_repaired
    assert math.isclose(r.correlation_min_eigenvalue, -0.2, abs_tol=1e-6)  # entered infeasibility
    assert r.correlation_frobenius_distance > 0.0  # a real repair happened


def test_correlation_matrix_falls_back_when_under_two_uncertain() -> None:
    """A matrix needs >=2 uncertain activities; with only one, prepare returns None and the run is
    byte-identical to the no-matrix (scalar) run — the freeze holds under a supplied-but-inert
    spec."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl)}  # only task 2 is uncertain (N=1)
    base = SRAConfig(iterations=150, seed=2, target_uid=4)
    plain = compute_sra_ssi(s, config=base, three_point=tp)
    spec = CorrelationSpec(pairs=((2, 3, 0.5),))  # references task 3 (a point mass) -> inert
    withspec = compute_sra_ssi(s, config=replace(base, correlation_matrix=spec), three_point=tp)
    assert withspec.cdf == plain.cdf  # byte-identical -> fell back to the scalar path
    assert not withspec.correlation_matrix_applied


def test_s_curve_is_dense_dated_and_monotonic() -> None:
    """The SSI result carries a realigned-date cumulative S-curve (one point per distinct simulated
    finish, so it is dense and smooth) and a dated finish-date histogram for direct plotting."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 5, tbl)}  # a wide driver -> the focus finish spreads out
    r = compute_sra_ssi(s, config=SRAConfig(iterations=600, seed=3, target_uid=4), three_point=tp)
    assert len(r.s_curve) > 5  # many distinct finish values -> a smooth curve, not a few steps
    probs = [p for _date, p in r.s_curve]
    assert probs == sorted(probs) and probs[-1] == 1.0  # cumulative, ends at 100%
    assert all(len(d) == 10 and d[4] == "-" for d, _p in r.s_curve)  # ISO YYYY-MM-DD dates
    assert sum(c for _d, c in r.finish_hist) == 600  # every iteration lands in a histogram bin


# --- Criticality Index from the SSI run (ADR-0272) -----------------------------------


def test_ssi_criticality_index_ranks_the_driver_over_the_off_path() -> None:
    """The SSI run now SURFACES the per-activity Criticality Index (fraction of iterations the
    activity was critical) it already tallies — the risk-critical Gantt tint reads it. The 10-day
    driver on the focus path is critical (nearly) every iteration; the short off-path task almost
    never is."""
    s = _focus_net()
    tbl = RiskFactorTable()
    # both the driver (2) and the off-path task (3) carry a factor-3 spread → genuine uncertainty
    tp = {2: factor_to_bc_wc(10 * DAY, 3, tbl), 3: factor_to_bc_wc(2 * DAY, 3, tbl)}
    r = compute_sra_ssi(s, config=SRAConfig(iterations=400, seed=1, target_uid=4), three_point=tp)
    ci = dict(r.criticality)
    assert set(ci) == {1, 2, 3, 4}  # every non-summary activity carries a CI
    assert all(0.0 <= v <= 1.0 for v in ci.values())  # a valid fraction
    assert tuple(u for u, _ in r.criticality) == (1, 2, 3, 4)  # ascending uid, stable order
    assert ci[2] > 0.95  # the 10-day driver is on the focus path essentially always
    assert ci[3] < 0.05  # the 2-day off-path task cannot overtake a 10-day path


def test_ssi_criticality_is_deterministic_for_a_seed() -> None:
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 4, tbl)}
    cfg = SRAConfig(iterations=200, seed=5, target_uid=4)
    a = compute_sra_ssi(s, config=cfg, three_point=tp)
    b = compute_sra_ssi(s, config=cfg, three_point=tp)
    assert a.criticality == b.criticality  # same seed → byte-identical CI


def test_ssi_criticality_all_point_mass_is_the_deterministic_critical_path() -> None:
    """With no uncertainty the CI is 1.0 for every activity on the deterministic critical path
    (1→2→4) and 0.0 for the off-path task — a clean 0/1 split, no spread."""
    s = _focus_net()
    r = compute_sra_ssi(s, config=SRAConfig(iterations=16, seed=1, target_uid=4))
    ci = dict(r.criticality)
    assert ci[1] == ci[2] == ci[4] == 1.0  # the focus path is critical every iteration
    assert ci[3] == 0.0  # the off-path task never is


# --- 5x5 matrix ratings --------------------------------------------------------------


def test_probability_and_consequence_ratings() -> None:
    assert [_prob_rating(p) for p in (0.10, 0.20, 0.40, 0.60, 0.79, 0.80, 0.95)] == [
        1,
        2,
        3,
        4,
        4,
        5,
        5,
    ]
    # the NASA Schedule guideline: impact days -> calendar months (30.44 d/mo)
    # <1wk=1, 1wk-<1mo=2, 1-<3mo=3, 3-<=6mo=4, >6mo=5
    assert [_consequence_rating(d) for d in (6.0, 7.0, 20.0, 31.0, 90.0, 100.0, 183.0)] == [
        1,  # 6 days < 1 week
        2,  # 1 week
        2,  # < 1 month
        3,  # 1 month (>= 30.44)
        3,  # < 3 months (< 91.3)
        4,  # ~3.3 months (3 to <= 6)
        5,  # > 6 months (> 182.6)
    ]


def test_risk_stats_carry_ratings_and_occurrence_band() -> None:
    s = _focus_net()
    risk = ScheduleRisk(id="R1", name="permit", probability=0.79, impact_days=200.0, affected=(2,))
    r = compute_sra_ssi(s, config=SRAConfig(iterations=100, target_uid=4, seed=2), risks=[risk])
    rs = r.risks[0]
    assert rs.probability_rating == 4 and rs.consequence_rating == 5  # 79% band, 200d (>6mo) impact
    assert 60 <= rs.hits <= 95  # ~79 of 100 (seeded)
