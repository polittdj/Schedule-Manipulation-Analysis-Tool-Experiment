"""JCL — Joint Cost-&-Schedule Confidence Level (FICSM) by cost co-sampling (ADR-0269).

A **parity-isolated** extension of the SSI Monte-Carlo (ADR-0123): the duration dimension
replicates :func:`schedule_forensics.engine.sra.compute_sra_ssi`'s draw discipline *exactly*
(same per-iteration ``random.Random(seed + i)``, ascending-``unique_id`` draws, point-mass
rules, Gaussian-copula option, additive risks from the same disjoint occurrence stream, the
same trusted ``compute_cpm(duration_overrides=…)`` chokepoint and stored-finish date-axis
realignment) — so the joint sample's finish marginal is **identical** to the SSI S-curve on
the same inputs (a test pins the equivalence; one story, no second truth).

The cost dimension rides the *same* sampled durations (NASA CEH v4.0 App. J / Hulett
integrated cost-schedule risk). Per iteration::

    EAC_i = Σ_completed final_u
          + Σ_incomplete ( spent_u + (TI_u + TD_u · d_u,i / d_u,ML) · m_u,i )

* a **completed** task contributes its recorded ``actual_cost`` (else its ``budgeted_cost``)
  as a fixed point estimate — the cost mirror of "completed work carries no uncertainty";
* an **incomplete** task's remaining budget ``rem_u = budgeted_cost · (1 - pc/100)`` splits
  into a **time-dependent** share ``τ`` (default 1.0 — a labor-dominant screening default)
  burning at the ML rate over the **sampled** remaining duration, and a time-independent
  remainder; a milestone / zero-ML-remaining task is wholly time-independent (no burn rate
  exists — never divide by zero, never fabricate);
* ``m_u,i`` is the optional FICSM **cost-estimating uncertainty** triangular (default
  1/1/1 = off; a defensible range must be elicited — GAO), drawn per incomplete costed task
  in ascending-uid order **after** every duration draw of the iteration, so enabling it
  never perturbs the duration stream (the ``risks=()`` discipline of ADR-0106/0123).

JCL = P(finish ≤ target date AND EAC ≤ target cost); SCL / CCL are the same-target
marginals, and the elementary invariant **JCL ≤ min(SCL, CCL)** is test-pinned. A schedule
that is not cost-loaded (the EVM gate: non-summary ``Σ budgeted_cost > 0`` fails) raises
``ValueError`` — a duration-only run is an SCL and must never be labeled JCL (ADR-0106).
"""

from __future__ import annotations

import datetime as _dt
import math
import random
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from schedule_forensics.engine.correlation import PreparedCorrelation, prepare_correlation
from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.sra import (
    _DEFAULT_CONFIG,
    ScheduleRisk,
    SRAConfig,
    _build_cdf,
    _finish_of,
    _is_completed,
    _iteration_duration_overrides,
    _latest_finish,
    _ml_minutes,
    _occurrence_schedule,
    _percentile,
    _sample_triangular,
)
from schedule_forensics.model.schedule import Schedule

#: Finish-percentile grid (5..95 step 5) the iso-confidence frontier is evaluated on.
_FRONTIER_GRID: tuple[int, ...] = tuple(range(5, 100, 5))


@dataclass(frozen=True)
class JCLConfig:
    """The cost-side configuration of a JCL run (the schedule side is :class:`SRAConfig`).

    ``target_date`` / ``target_cost`` default (``None``) to the run's deterministic all-ML
    finish date and deterministic EAC. ``td_share`` is the time-dependent share τ of every
    remaining budget (1.0 = labor-dominant screening default, labeled in the UI).
    ``cost_low/ml/high`` are the FICSM cost-estimating-uncertainty triangular multipliers
    (1/1/1 = off — a defensible range must be elicited, GAO). ``confidence`` is the
    frontier's joint confidence target (NPR 7120.5F policy anchor 0.70).
    """

    target_date: _dt.date | None = None
    target_cost: float | None = None
    td_share: float = 1.0
    cost_low: float = 1.0
    cost_ml: float = 1.0
    cost_high: float = 1.0
    confidence: float = 0.70


#: Module-level default (keyword-default without a call in the signature — ruff B008).
_DEFAULT_JCL = JCLConfig()


@dataclass(frozen=True)
class JCLResult:
    """The joint (finish, cost) Monte-Carlo result (parity-isolated — ADR-0269)."""

    iterations: int
    seed: int
    target_uid: int | None
    # ---- the schedule marginal (identical to the SSI run on the same inputs; test-pinned)
    deterministic_finish: int  # all-ML finish (working-minute offset)
    deterministic_finish_date: str  # … realigned ISO date
    finish_p10_date: str
    finish_p50_date: str
    finish_p80_date: str
    finish_p90_date: str
    # the finish CDF in working-minute offsets — byte-identical to the SSI run's ``cdf`` on
    # the same inputs (the ADR-0269 equivalence pin asserts the full distribution equal)
    finish_cdf: tuple[tuple[int, float], ...]
    # ---- the cost marginal (EAC distribution, currency units of the source file)
    deterministic_eac: float  # all-ML, multipliers-off EAC = AC + (BAC - EV)
    cost_p10: float
    cost_p50: float
    cost_p80: float
    cost_p90: float
    cost_mean: float
    cost_std: float
    cost_min: float
    cost_max: float
    # the cost S-curve: (EAC, cumulative probability) points, one per distinct value
    cost_cdf: tuple[tuple[float, float], ...]
    # ---- the joint statement
    target_date: str  # ISO date the JCL is stated against
    target_cost: float
    confidence: float  # the frontier's joint-confidence target (0..1)
    scl: float  # P(finish ≤ target_date)
    ccl: float  # P(EAC ≤ target_cost)
    jcl: float  # P(both) — the Joint Confidence Level
    # quadrant shares at the targets (fractions; sum to 1.0)
    q_both: float
    q_date_only: float
    q_cost_only: float
    q_neither: float
    # the joint sample: one (realigned ISO finish date, EAC) point per iteration
    points: tuple[tuple[str, float], ...]
    # iso-confidence frontier at ``confidence``: (ISO date, min EAC achieving it jointly);
    # empty when no gridpoint reaches the target. Costs are non-increasing along the grid.
    frontier: tuple[tuple[str, float], ...]
    # ---- provenance (the cost model's constant parts, for the panel/export)
    sunk_total: float  # Σ completed finals + incomplete actuals to date
    remaining_ti_total: float  # Σ time-independent remaining budget
    remaining_td_total: float  # Σ time-dependent remaining budget
    completed_count: int
    incomplete_costed_count: int  # incomplete tasks carrying remaining budget
    td_share: float
    cost_uncertainty_on: bool
    # correlation-matrix provenance (ADR-0270), mirroring SSIResult — a full pairwise/shared-
    # driver matrix drove the shared duration sampler (else the scalar path), plus the entered
    # matrix's smallest eigenvalue and the Frobenius size of any feasibility repair.
    correlation_matrix_applied: bool = False
    correlation_matrix_repaired: bool = False
    correlation_min_eigenvalue: float = 0.0
    correlation_frobenius_distance: float = 0.0


def cost_loaded_total(schedule: Schedule) -> float:
    """The EVM cost-loaded gate's total: non-summary ``Σ budgeted_cost`` (never negative)."""
    return sum(t.budgeted_cost for t in non_summary(schedule))


@dataclass(frozen=True)
class _CostEntry:
    """One incomplete task's constant cost parts (the per-iteration variable is d_u,i)."""

    unique_id: int
    spent: float  # actuals to date (0 when unrecorded)
    ti: float  # time-independent remaining budget
    td: float  # time-dependent remaining budget (burns over the sampled duration)
    ml_minutes: int  # the burn-rate denominator; 0 == wholly time-independent


def compute_jcl(
    schedule: Schedule,
    *,
    config: SRAConfig = _DEFAULT_CONFIG,
    three_point: Mapping[int, tuple[int, int, int]] | None = None,
    risks: Sequence[ScheduleRisk] = (),
    jcl: JCLConfig = _DEFAULT_JCL,
) -> JCLResult:
    """Run the joint cost-&-schedule Monte-Carlo and return the :class:`JCLResult`.

    The schedule inputs (``config``, ``three_point``, ``risks``) are the SSI model's,
    unchanged — pass the same values the ``/api/sra/ssi`` run uses and the finish marginal
    here equals that run exactly. Raises ``ValueError`` when the schedule is not
    cost-loaded (Law 2: no fabricated cost figures, ever).
    """
    if config.iterations < 1:
        raise ValueError("SRAConfig.iterations must be >= 1")
    if cost_loaded_total(schedule) <= 0.0:
        raise ValueError(
            "schedule is not cost-loaded (no budgeted cost) — JCL is undefined; "
            "a duration-only run is a schedule confidence level (SCL)"
        )

    # ---- the SSI duration dimension, replicated verbatim (equivalence test-pinned) ----
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    uids = [t.unique_id for t in tasks]
    uid_set = set(uids)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}
    ml_finish = _finish_of(compute_cpm(schedule, duration_overrides=ml), config.target_uid)
    focus = next((t for t in tasks if t.unique_id == config.target_uid), None)
    anchor = (
        focus.finish if focus is not None and focus.finish is not None else _latest_finish(tasks)
    )
    tp_in = dict(three_point or {})
    active_risks = [
        r for r in risks if config.use_risk_register and any(u in uid_set for u in r.affected)
    ]
    risk_uids = {u for r in active_risks for u in r.affected}

    three: dict[int, tuple[int, int, int]] = {}
    for u in uids:
        if u in risk_uids or u not in tp_in:
            three[u] = (ml[u], ml[u], ml[u])  # point mass (risk-driven, or no uncertainty)
        else:
            bc, mlv, wc = tp_in[u]
            three[u] = (max(0, int(bc)), int(mlv), max(int(bc), int(wc)))

    occ = _occurrence_schedule(active_risks, config.occurrence_mode, config.iterations, config.seed)
    mpd = schedule.calendar.working_minutes_per_day or 480
    # the correlation matrix (ADR-0270) is prepared ONCE over the uncertain-duration set and fed
    # to the SAME shared sampler the SSI engine uses, so the finish marginals stay byte-identical
    # (the ADR-0269 pin); None → the scalar single-factor path (the byte-frozen default).
    uncertain = [u for u in uids if three[u][2] > three[u][0]]
    prepared = prepare_correlation(uncertain, config.correlation_matrix)

    # ---- the cost model's constant parts (ADR-0269) ----
    tau = max(0.0, min(1.0, jcl.td_share))
    c_low = max(0.0, jcl.cost_low)
    c_ml = max(c_low, jcl.cost_ml)
    c_high = max(c_ml, jcl.cost_high)
    cost_uncertainty_on = not (c_low == 1.0 and c_ml == 1.0 and c_high == 1.0)

    completed_total = 0.0
    completed_count = 0
    entries: list[_CostEntry] = []
    for t in tasks:  # ascending unique_id — the cost-multiplier draw order
        if _is_completed(t):
            completed_total += t.actual_cost if t.actual_cost is not None else t.budgeted_cost
            completed_count += 1
            continue
        pc = max(0.0, min(100.0, t.percent_complete))
        rem = t.budgeted_cost * (1.0 - pc / 100.0)
        spent = t.actual_cost if t.actual_cost is not None else 0.0
        d_ml = ml[t.unique_id]
        if d_ml <= 0:  # no burn rate exists — wholly time-independent
            ti, td = rem, 0.0
        else:
            ti, td = (1.0 - tau) * rem, tau * rem
        entries.append(_CostEntry(t.unique_id, spent, ti, td, d_ml))
    incomplete_costed = sum(1 for e in entries if e.ti + e.td > 0.0)
    spent_total = sum(e.spent for e in entries)

    # deterministic EAC: every ratio 1, every multiplier 1 → AC + (BAC - EV), τ-independent.
    # The float association mirrors the per-iteration sum exactly, so an all-point-mass run
    # produces costs bit-identical to this value (the equivalence test relies on it).
    deterministic_eac = completed_total + sum(e.spent + (e.ti + e.td) for e in entries)

    finishes: list[int] = []
    costs: list[float] = []
    for i in range(config.iterations):
        rng = random.Random(config.seed + i)  # nosec B311 — simulation, not crypto
        overrides = _iteration_duration_overrides(rng, config, uids, three, prepared)
        for ridx, risk in enumerate(active_risks):
            if occ[ridx][i]:
                add = round(risk.impact_days * mpd)
                for u in risk.affected:
                    if u in overrides:
                        overrides[u] = max(0, overrides[u] + add)
        # cost draws come AFTER every duration draw (and consume the same per-iteration
        # stream only when the multipliers are on) — the duration stream is untouched.
        cost = completed_total
        for e in entries:
            m = 1.0
            if cost_uncertainty_on and e.ti + e.td > 0.0:
                m = _sample_triangular(rng.random(), c_low, c_ml, c_high)
            ratio = (overrides[e.unique_id] / e.ml_minutes) if e.ml_minutes > 0 else 1.0
            cost += e.spent + (e.ti + e.td * ratio) * m
        result = compute_cpm(schedule, duration_overrides=overrides)
        finishes.append(_finish_of(result, config.target_uid))
        costs.append(cost)

    return _build_jcl_result(
        schedule,
        config,
        jcl,
        finishes,
        costs,
        deterministic=ml_finish,
        anchor_date=anchor,
        deterministic_eac=deterministic_eac,
        sunk_total=completed_total + spent_total,
        ti_total=sum(e.ti for e in entries),
        td_total=sum(e.td for e in entries),
        completed_count=completed_count,
        incomplete_costed=incomplete_costed,
        tau=tau,
        cost_uncertainty_on=cost_uncertainty_on,
        prepared=prepared,
    )


def _cost_cdf(sorted_costs: Sequence[float], n: int) -> tuple[tuple[float, float], ...]:
    """The empirical cost CDF — one ``(EAC, cumulative probability)`` point per distinct
    value (the float twin of the finish CDF builder; same right-continuous step rule)."""
    points: list[tuple[float, float]] = []
    idx = 0
    while idx < len(sorted_costs):
        value = sorted_costs[idx]
        while idx + 1 < len(sorted_costs) and sorted_costs[idx + 1] == value:
            idx += 1
        points.append((round(value, 2), round((idx + 1) / n, 4)))
        idx += 1
    return tuple(points)


def _build_jcl_result(
    schedule: Schedule,
    config: SRAConfig,
    jcl: JCLConfig,
    finishes: Sequence[int],
    costs: Sequence[float],
    *,
    deterministic: int,
    anchor_date: _dt.datetime | None,
    deterministic_eac: float,
    sunk_total: float,
    ti_total: float,
    td_total: float,
    completed_count: int,
    incomplete_costed: int,
    tau: float,
    cost_uncertainty_on: bool,
    prepared: PreparedCorrelation | None = None,
) -> JCLResult:
    """Assemble the :class:`JCLResult` from the joint iteration series."""
    n = len(finishes)
    cal = schedule.calendar
    ps = schedule.project_start
    # the same stored-finish date-axis realignment as the SSI result (ADR-0123): a single
    # constant correction puts the pure-CPM offsets back on the schedule's stored dates.
    naive_det = offset_to_datetime(ps, max(deterministic, 0), cal)
    correction = (anchor_date - naive_det) if anchor_date is not None else _dt.timedelta(0)

    def _cal_date(offset: float) -> _dt.date:
        return (offset_to_datetime(ps, max(round(offset), 0), cal) + correction).date()

    finish_dates = [_cal_date(f) for f in finishes]
    sorted_ff = sorted(float(f) for f in finishes)
    sorted_costs = sorted(costs)

    target_date = jcl.target_date if jcl.target_date is not None else _cal_date(deterministic)
    # comparisons use the UNROUNDED default (a 2dp round-down must not flip a boundary
    # cost's ≤-target verdict); only the displayed field is rounded.
    target_cost = jcl.target_cost if jcl.target_cost is not None else deterministic_eac
    confidence = max(0.01, min(0.99, jcl.confidence))

    both = date_ok_only = cost_ok_only = neither = 0
    for d, c in zip(finish_dates, costs, strict=True):
        date_ok = d <= target_date
        cost_ok = c <= target_cost
        if date_ok and cost_ok:
            both += 1
        elif date_ok:
            date_ok_only += 1
        elif cost_ok:
            cost_ok_only += 1
        else:
            neither += 1
    scl = (both + date_ok_only) / n
    ccl = (both + cost_ok_only) / n
    jcl_level = both / n

    # iso-confidence frontier: for each finish-percentile gridpoint date d, the k-th
    # smallest EAC among the iterations finishing ≤ d, where k = ceil(confidence · n) —
    # the minimum cost c with P(finish ≤ d AND cost ≤ c) ≥ confidence (skip when the
    # date alone cannot reach the target). Costs are non-increasing along the grid.
    k = math.ceil(confidence * n)
    frontier: list[tuple[str, float]] = []
    seen_dates: set[str] = set()
    for pct in _FRONTIER_GRID:
        d = _cal_date(_percentile(sorted_ff, float(pct)))
        iso = d.isoformat()
        if iso in seen_dates:
            continue
        seen_dates.add(iso)
        subset = sorted(c for fd, c in zip(finish_dates, costs, strict=True) if fd <= d)
        if len(subset) >= k:
            frontier.append((iso, round(subset[k - 1], 2)))

    return JCLResult(
        iterations=config.iterations,
        seed=config.seed,
        target_uid=config.target_uid,
        deterministic_finish=deterministic,
        deterministic_finish_date=_cal_date(deterministic).isoformat(),
        finish_p10_date=_cal_date(_percentile(sorted_ff, 10)).isoformat(),
        finish_p50_date=_cal_date(_percentile(sorted_ff, 50)).isoformat(),
        finish_p80_date=_cal_date(_percentile(sorted_ff, 80)).isoformat(),
        finish_p90_date=_cal_date(_percentile(sorted_ff, 90)).isoformat(),
        finish_cdf=_build_cdf(sorted(finishes), n),
        deterministic_eac=round(deterministic_eac, 2),
        cost_p10=round(_percentile(sorted_costs, 10), 2),
        cost_p50=round(_percentile(sorted_costs, 50), 2),
        cost_p80=round(_percentile(sorted_costs, 80), 2),
        cost_p90=round(_percentile(sorted_costs, 90), 2),
        cost_mean=round(statistics.fmean(costs), 2),
        cost_std=round(statistics.pstdev(costs), 2) if n > 1 else 0.0,
        cost_min=round(sorted_costs[0], 2),
        cost_max=round(sorted_costs[-1], 2),
        cost_cdf=_cost_cdf(sorted_costs, n),
        target_date=target_date.isoformat(),
        target_cost=round(target_cost, 2),
        confidence=confidence,
        scl=round(scl, 4),
        ccl=round(ccl, 4),
        jcl=round(jcl_level, 4),
        q_both=round(both / n, 4),
        q_date_only=round(date_ok_only / n, 4),
        q_cost_only=round(cost_ok_only / n, 4),
        q_neither=round(neither / n, 4),
        points=tuple(
            (d.isoformat(), round(c, 2)) for d, c in zip(finish_dates, costs, strict=True)
        ),
        frontier=tuple(frontier),
        sunk_total=round(sunk_total, 2),
        remaining_ti_total=round(ti_total, 2),
        remaining_td_total=round(td_total, 2),
        completed_count=completed_count,
        incomplete_costed_count=incomplete_costed,
        td_share=tau,
        cost_uncertainty_on=cost_uncertainty_on,
        correlation_matrix_applied=prepared is not None,
        correlation_matrix_repaired=prepared.repaired if prepared is not None else False,
        correlation_min_eigenvalue=prepared.min_eig_raw if prepared is not None else 0.0,
        correlation_frobenius_distance=(
            prepared.frobenius_distance if prepared is not None else 0.0
        ),
    )
