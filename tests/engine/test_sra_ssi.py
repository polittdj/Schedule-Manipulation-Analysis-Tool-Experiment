"""SSI Schedule Risk & Opportunity Analysis engine (ADR-0123) — the parity-anchored SSI path.

Pins the DETERMINISTIC facts validated against the operator's SSI exports: the BC/WC formula
(ML = remaining), the all-ML == ``compute_cpm`` equivalence, focus-event targeting, the additive
risk model (a risk-bearing task carries no Best/Worst uncertainty), the occurrence modes, the
deterministic OAT sensitivity, and the optional correlation. The stochastic distribution is NOT
claimed bit-exact vs SSI's RNG (std-lib Mersenne Twister  !=  SSI's generator — ADR-0005/0106)."""

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
    tbl = RiskFactorTable()
    # factor 3 = subtract 30 / add 30 on a 10-day remaining duration
    assert factor_to_bc_wc(10 * DAY, 3, tbl) == (7 * DAY, 10 * DAY, 13 * DAY)
    # factor 5 = subtract 10 / add 50
    assert factor_to_bc_wc(10 * DAY, 5, tbl) == (round(9 * DAY), 10 * DAY, round(15 * DAY))
    # factor 1 = subtract 50 / add 10
    assert factor_to_bc_wc(10 * DAY, 1, tbl) == (5 * DAY, 10 * DAY, 11 * DAY)
    # ML is the REMAINING duration passed in (not any original) — the UID-35 regression
    assert factor_to_bc_wc(1711, 2, tbl) == (round(1711 * 0.6), 1711, round(1711 * 1.2))
    # factor 0 = NO uncertainty: BC = ML = WC = the remaining duration (operator: a 0 means "use
    # the remaining duration, there is no Best/Worst case", never clamp it up to 1)
    assert factor_to_bc_wc(10 * DAY, 0, tbl) == (10 * DAY, 10 * DAY, 10 * DAY)
    assert factor_to_bc_wc(1711, 0, tbl) == (1711, 1711, 1711)


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


# --- additive risk + risk-excludes-Best/Worst ----------------------------------------


def test_additive_risk_adds_working_days_to_the_affected_task() -> None:
    """A risk firing every iteration adds exactly impact_days x 480 minutes to its task."""
    s = _focus_net()
    risk = ScheduleRisk(id="R", name="r", probability=1.0, impact_days=5.0, affected=(2,))
    r = compute_sra_ssi(s, config=SRAConfig(iterations=20, target_uid=4), risks=[risk])
    # task 2 ML 10d + 5d impact → focus 4 finishes at 1+15+1 = 17 days, every iteration
    assert r.p10 == r.p50 == r.p90 == 17 * DAY
    assert r.risks[0].hits == 20


def test_a_risk_bearing_task_carries_no_best_worst_uncertainty() -> None:
    """SSI: a task with a risk does NOT also apply its Best/Worst duration uncertainty — the risk
    drives it. So even with a wide factor on task 2, a sure risk pins the finish (no spread)."""
    s = _focus_net()
    tbl = RiskFactorTable()
    tp = {2: factor_to_bc_wc(10 * DAY, 5, tbl)}  # a wide Best/Worst on the driver
    risk = ScheduleRisk(id="R", name="r", probability=1.0, impact_days=5.0, affected=(2,))
    r = compute_sra_ssi(
        s, config=SRAConfig(iterations=50, target_uid=4), three_point=tp, risks=[risk]
    )
    assert r.p10 == r.p90 == 17 * DAY  # no Best/Worst variance — the risk replaced it


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
        2: factor_to_bc_wc(10 * DAY, 3, tbl),  # driver: BC 7d / WC 13d
        3: factor_to_bc_wc(2 * DAY, 3, tbl),  # off-path: tiny swing, never reaches the focus
    }
    oat = compute_oat_sensitivity(s, three_point=tp, target_uid=4)
    by = {o.unique_id: o for o in oat}
    # the driver swings the focus both ways: BC pulls it in 3 wd, WC pushes it out 3 wd
    assert by[2].opportunity_days == 3.0 and by[2].risk_days == 3.0 and by[2].total_days == 6.0
    # the off-path task can't move the focus at all
    assert by[3].total_days == 0.0
    # sorted by total desc → the driver is first
    assert oat[0].unique_id == 2


def test_oat_excludes_listed_uids() -> None:
    s = _focus_net()
    tp = {2: factor_to_bc_wc(10 * DAY, 3, RiskFactorTable())}
    oat = compute_oat_sensitivity(s, three_point=tp, target_uid=4, exclude_uids=frozenset({2}))
    assert all(o.unique_id != 2 for o in oat)


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
