"""Schedule Risk Analysis (SRA) — a seeded, std-lib-only Monte-Carlo simulation.

This is a **separate, parity-isolated** analysis (ADR-0106). It never touches the
deterministic CPM/DCMA numbers: each iteration samples every activity's duration from
its distribution and *recomputes the network finish through the one trusted solver*,
:func:`schedule_forensics.engine.cpm.compute_cpm`, via its ``duration_overrides`` hook.
That single chokepoint is the guarantee of zero divergence from the gate-locked engine
(Law 2): with every activity fixed at its most-likely duration the simulation's finish
equals ``compute_cpm(schedule).project_finish`` exactly (enforced by a test).

Determinism (Law 2 / ADR-0005): one integer base seed; iteration ``i`` draws from its
own ``random.Random(seed + i)`` so results are reproducible regardless of order, and the
per-iteration draws are taken in ascending ``unique_id`` order. The std-lib Mersenne
Twister is documented as *not* matching NumPy-based commercial tools.

Inputs (all working minutes):

* **Manual** — a per-activity 3-point ``ActivityRisk`` (optimistic / most-likely /
  pessimistic); the analyst path (GAO/NASA elicited ranges).
* **Auto** — when an activity has no manual override, a triangular on its **remaining**
  duration with Min ``auto_low`` / Most-Likely ``auto_most_likely`` / Max ``auto_high``
  (Deltek Acumen "Realistic" 90/100/110). Completed work is fixed (no uncertainty).
  ``auto_used`` records whether any activity fell back to auto — the UI labels such a run
  a *screening placeholder, not SME-validated*.

Outputs (:class:`SRAResult`): the finish-date CDF/S-curve, P10/P50/P80/P90 + mean
(working-minute offsets *and* ISO dates), the deterministic finish and the percentile it
sits at, a histogram (PDF), and per-activity Criticality Index / duration sensitivity
(Spearman) / SSI, plus the UIDs carrying a hard constraint (they cap the distribution —
GAO "minimize date constraints").
"""

from __future__ import annotations

import bisect
import datetime as _dt
import math
import random
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from schedule_forensics.engine.correlation import (
    CorrelationSpec,
    PreparedCorrelation,
    prepare_correlation,
)
from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Finish-date histogram resolution (PDF bins over [min, max] of the simulated finishes). Finer bins
#: (operator: "the granularity of the data much more") give a smoother distribution on the charts.
_HISTOGRAM_BINS = 40


@dataclass(frozen=True)
class SRAConfig:
    """Run configuration for :func:`compute_sra`.

    ``iterations`` and ``seed`` fix the (reproducible) sample; ``auto_low`` /
    ``auto_most_likely`` / ``auto_high`` are the triangular multipliers applied to each
    un-overridden activity's **remaining** duration (Deltek Acumen "Realistic"
    90/100/110 default — right-skew toward overrun, the empirically defensible default).
    """

    iterations: int = 1000
    seed: int = 12345
    auto_low: float = 0.9
    auto_most_likely: float = 1.0
    auto_high: float = 1.10
    #: Duration distribution: ``"triangular"`` (default, inverse-CDF) or ``"pert"`` (Beta-PERT).
    distribution: str = "triangular"
    #: SSI path (ADR-0123): the focus event whose finish the simulation reports. ``None`` →
    #: project finish (back-compat with the legacy ``compute_sra``).
    target_uid: int | None = None
    #: SSI risk occurrence mode: ``"random_each"`` (independent Bernoulli per iteration) or
    #: ``"exact_overall"`` (exactly ``round(p*iterations)`` firings, scattered at random).
    occurrence_mode: str = "random_each"
    #: Whether the SSI risk register is factored into the run (SSI "Use Risk Registry Tasks").
    use_risk_register: bool = True
    #: Optional blanket correlation (0..1) between task duration distributions — a single-factor
    #: Gaussian copula (0 = independent, today's behaviour; 0.3-0.5 is the usual SRA range).
    correlation: float = 0.0
    #: Optional full pairwise/shared-driver correlation MATRIX (ADR-0270). ``None`` (default) →
    #: the scalar single-factor path above runs byte-identically. When supplied over ≥2
    #: uncertain activities it OVERRIDES the scalar ``correlation`` and drives a multivariate
    #: Gaussian copula (a distinct mode — the scalar path is never silently changed).
    correlation_matrix: CorrelationSpec | None = None
    #: Sampling mode (ADR-0271): ``"mc"`` (plain Monte-Carlo, the byte-frozen default) or
    #: ``"lhs"`` (Latin Hypercube — stratified draws for tighter convergence at the same
    #: iteration count). A distinct opt-in mode that composes with the correlation copula; the
    #: MC path is never silently changed. Marginals are exactly stratified only at zero
    #: correlation (LHS-then-Cholesky), and PERT falls back to the triangular inverse under LHS.
    sampling: str = "mc"
    #: LHS within-stratum placement: ``False`` = random (McKay-Beckman-Conover, the default);
    #: ``True`` = the stratum midpoint (biases tail percentiles low — opt-in, never a default).
    lhs_centered: bool = False


#: The default run config — a module-level singleton so it can be a keyword default
#: without evaluating a call in the signature (ruff B008).
_DEFAULT_CONFIG = SRAConfig()


@dataclass(frozen=True)
class ActivityRisk:
    """A manual 3-point duration override for one activity, in working minutes.

    The optimistic / most-likely / pessimistic minutes must satisfy
    ``optimistic <= most_likely <= pessimistic`` (the triangular's a <= m <= b).
    """

    unique_id: int
    optimistic_minutes: int
    most_likely_minutes: int
    pessimistic_minutes: int


@dataclass(frozen=True)
class ActivitySensitivity:
    """Per-activity sensitivity outputs from the simulation."""

    unique_id: int
    criticality_index: float  # fraction of iterations the activity was critical (TF <= 0)
    duration_sensitivity: float  # Spearman(sampled duration, project finish), [-1, 1]
    ssi: float  # Schedule Sensitivity Index = (sigma_dur * CI) / sigma_finish


@dataclass(frozen=True)
class RiskEvent:
    """A discrete risk driver (GAO/AACE/Hulett risk-driver method).

    A risk has a ``probability`` of occurring (0..1); when it occurs it applies a 3-point
    *multiplicative* triangular impact (``impact_low`` / ``impact_ml`` / ``impact_high`` —
    duration multipliers, e.g. ``1.0`` / ``1.1`` / ``1.3``) to the sampled duration of
    every activity it is mapped to (``affected``, by ``unique_id``). A single risk mapped
    to several activities correlates them automatically — the *shared-driver* correlation
    of the method, requiring no coefficient. Hulett: "If the probability is less than 100%
    it will occur in that percentage of iterations… the multiplicative factor selected
    multiplies the duration of all the activities to which the risk is assigned."
    """

    id: str
    name: str
    probability: float  # 0..1; values outside the range are clamped at use
    impact_low: float  # duration multiplier, optimistic (>= 0)
    impact_ml: float  # duration multiplier, most-likely (>= 0)
    impact_high: float  # duration multiplier, pessimistic (>= 0)
    affected: tuple[int, ...]  # unique_ids the multiplicative impact lands on


@dataclass(frozen=True)
class RiskDriver:
    """Per-risk simulation outputs — the risk-driver "tornado" contribution.

    ``hits`` is the count of iterations the risk occurred; ``mean_delta_days`` is the mean
    finish (in working days) over the iterations it occurred minus the mean over those it
    did not — its empirical schedule contribution. ``0.0`` when there is no contrast (it
    never occurred, always occurred, or both groups share the same mean finish).
    """

    id: str
    name: str
    probability: float
    hits: int
    mean_delta_days: float


@dataclass(frozen=True)
class SRAResult:
    """The full Monte-Carlo result (parity-isolated — never the deterministic numbers)."""

    iterations: int
    seed: int
    auto_used: bool  # True if any activity fell back to the auto triangular default
    deterministic_finish: int  # the compute_cpm finish offset (working minutes)
    deterministic_percentile: float  # fraction of iterations with finish <= deterministic
    # finish percentiles as integer working-minute offsets ...
    p10: int
    p50: int
    p80: int
    p90: int
    mean: float
    # ... and the same finishes as ISO dates (via the schedule calendar)
    deterministic_finish_date: str
    p10_date: str
    p50_date: str
    p80_date: str
    p90_date: str
    # the S-curve: (finish offset, cumulative probability) points
    cdf: tuple[tuple[int, float], ...]
    # the PDF: (bin_low_offset, bin_high_offset, count) bins
    histogram: tuple[tuple[int, int, int], ...]
    activities: tuple[ActivitySensitivity, ...]
    # UIDs of activities carrying a hard constraint — they cap the distribution (warn)
    constraints_flagged: tuple[int, ...] = field(default=())
    # discrete risk drivers, sorted by abs(mean_delta_days) desc then id (empty if no risks)
    risk_drivers: tuple[RiskDriver, ...] = field(default=())


# --------------------------------------------------------------------------------------
# Statistics primitives (std-lib only, documented rules)
# --------------------------------------------------------------------------------------


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    """The ``pct`` percentile of ``sorted_values`` (already ascending), linear interpolation.

    The NIST / Excel ``PERCENTILE.INC`` rule: rank ``r = pct/100 * (N - 1)`` (a 0-based
    index), interpolating linearly between the bracketing samples. ``pct`` in ``[0, 100]``.
    The interpolation rule is fixed and documented because commercial SRA tools differ at
    the tails (ADR-0106).
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("percentile of an empty sample")
    if n == 1:
        return float(sorted_values[0])
    rank = pct / 100.0 * (n - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return float(sorted_values[lo])
    frac = rank - lo
    return float(sorted_values[lo]) + frac * (float(sorted_values[hi]) - float(sorted_values[lo]))


def _average_ranks(values: Sequence[float]) -> list[float]:
    """Fractional (average) ranks of ``values`` — ties share the mean of their positions.

    The rank transform Spearman needs: equal values receive the average of the ranks they
    would occupy, so the correlation is well-defined under ties.
    """
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        # positions i..j (0-based) tie; average rank is the mean of the 1-based positions
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation of two equal-length series; 0.0 when either has zero variance."""
    n = len(xs)
    if n == 0 or n != len(ys):
        return 0.0
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    sxy = sxx = syy = 0.0
    for x, y in zip(xs, ys, strict=True):
        dx = x - mean_x
        dy = y - mean_y
        sxy += dx * dy
        sxx += dx * dx
        syy += dy * dy
    if sxx <= 0.0 or syy <= 0.0:  # a flat series has no defined correlation
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation = Pearson on the average-ranked series (handles ties)."""
    return _pearson(_average_ranks(xs), _average_ranks(ys))


# --------------------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------------------


def _sample_triangular(u: float, low: float, mode: float, high: float) -> float:
    """Inverse-CDF triangular sample for a uniform draw ``u`` in ``[0, 1)``.

    Standard closed-form inverse: the split point is ``c = (mode - low)/(high - low)``;
    below it the sample is ``low + sqrt(u (high-low)(mode-low))``, above it
    ``high - sqrt((1-u)(high-low)(high-mode))``. Degenerate (``low == high``) returns the
    point mass. Equivalent to ``random.Random.triangular`` but written explicitly so the
    arithmetic is auditable.
    """
    span = high - low
    if span <= 0.0:
        return low
    c = (mode - low) / span
    if u < c:
        return low + math.sqrt(u * span * (mode - low))
    return high - math.sqrt((1.0 - u) * span * (high - mode))


def _sample_beta_pert(rng: random.Random, low: float, mode: float, high: float) -> float:
    """A Beta-PERT sample in working minutes (Vose / @RISK PERT, shape lambda = 4).

    PERT fits a Beta to the 3-point estimate — ``alpha = 1 + 4(mode-low)/(high-low)``,
    ``beta = 1 + 4(high-mode)/(high-low)`` — scaled onto ``[low, high]``. Versus the triangular
    it concentrates mass near the mode and has lighter tails (the standard, less-pessimistic
    alternative the operator's SSI/Acumen tools offer). Degenerate (``low == high``) returns the
    point mass. Uses ``rng.betavariate`` directly (Beta has no elementary inverse CDF), so it draws
    its own RNG stream — reproducible for a fixed seed within the PERT choice.
    """
    span = high - low
    if span <= 0.0:
        return low
    alpha = 1.0 + 4.0 * (mode - low) / span
    beta = 1.0 + 4.0 * (high - mode) / span
    return low + rng.betavariate(alpha, beta) * span


def _sample_duration(
    rng: random.Random, config: SRAConfig, low: float, mode: float, high: float
) -> float:
    """Draw one 3-point sample under the configured distribution. The triangular path is byte-for-
    byte the prior behaviour (one ``rng.random()`` inverse-CDF draw); ``"pert"`` uses Beta-PERT."""
    if config.distribution == "pert":
        return _sample_beta_pert(rng, low, mode, high)
    return _sample_triangular(rng.random(), low, mode, high)


def _is_completed(task: Task) -> bool:
    """A completed activity carries no schedule uncertainty (use actuals — ADR-0106)."""
    return task.percent_complete >= 100.0 or task.actual_finish is not None


def _three_point(
    task: Task, config: SRAConfig, overrides: Mapping[int, ActivityRisk] | None
) -> tuple[float, float, float, bool]:
    """Resolve a task's (low, mode, high) duration in working minutes + whether auto applied.

    Manual ``ActivityRisk`` is honored verbatim. Otherwise the auto triangular is applied
    to the task's **remaining** duration (most-likely = remaining/own duration; min =
    ``auto_low`` x; max = ``auto_high`` x; mode = ``auto_most_likely`` x). Completed work
    is fixed at its own duration (a point mass — no uncertainty, not auto).
    """
    if overrides is not None and task.unique_id in overrides:
        risk = overrides[task.unique_id]
        return (
            float(risk.optimistic_minutes),
            float(risk.most_likely_minutes),
            float(risk.pessimistic_minutes),
            False,
        )
    if _is_completed(task):
        fixed = float(task.duration_minutes)
        return (fixed, fixed, fixed, False)
    remaining = (
        task.remaining_duration_minutes
        if task.remaining_duration_minutes is not None
        else task.duration_minutes
    )
    base = float(remaining)
    return (base * config.auto_low, base * config.auto_most_likely, base * config.auto_high, True)


# --------------------------------------------------------------------------------------
# The simulation
# --------------------------------------------------------------------------------------


def compute_sra(
    schedule: Schedule,
    cpm: CPMResult,
    *,
    config: SRAConfig = _DEFAULT_CONFIG,
    overrides: Mapping[int, ActivityRisk] | None = None,
    risks: Sequence[RiskEvent] = (),
) -> SRAResult:
    """Run the seeded Monte-Carlo SRA and return the :class:`SRAResult`.

    ``cpm`` is the deterministic :func:`compute_cpm` result for ``schedule`` (its
    ``project_finish`` is the deterministic anchor compared against the simulated CDF).
    ``overrides`` is the manual 3-point path; un-overridden activities use the auto
    triangular default (ADR-0106). Each iteration ``i`` samples durations from
    ``random.Random(config.seed + i)`` (draws ordered by ``unique_id``) and recomputes the
    finish via ``compute_cpm(schedule, duration_overrides=...)`` — the same trusted solver,
    so the simulation cannot diverge from the gate-locked engine (Law 2).

    ``risks`` adds discrete :class:`RiskEvent` drivers (GAO/AACE/Hulett method). Their RNG
    draws are taken *after* every per-activity duration draw of the iteration, so the
    duration draw sequence is unchanged — ``risks=()`` yields a byte-identical result to
    omitting the parameter (no extra draws are made). For each risk, in the given order, an
    occurrence is drawn (Bernoulli on the clamped probability); when it occurs a triangular
    impact factor multiplies the sampled duration of each affected activity (compounding if
    several risks hit one activity), correlating co-mapped activities automatically.
    """
    if config.iterations < 1:
        raise ValueError("SRAConfig.iterations must be >= 1")

    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    three_point: dict[int, tuple[float, float, float]] = {}
    auto_used = False
    for task in tasks:
        low, mode, high, was_auto = _three_point(task, config, overrides)
        three_point[task.unique_id] = (low, mode, high)
        auto_used = auto_used or was_auto

    uids = [t.unique_id for t in tasks]
    uid_set = set(uids)
    # only risks touching a present activity get RNG draws (an empty/dangling risk is inert)
    active_risks = [r for r in risks if any(uid in uid_set for uid in r.affected)]
    sampled_durations: dict[int, list[int]] = {uid: [] for uid in uids}
    critical_counts: dict[int, int] = dict.fromkeys(uids, 0)
    finishes: list[int] = []
    # per-active-risk occurrence flag for each iteration (parallel to ``finishes``)
    risk_occurred: list[list[bool]] = [[] for _ in active_risks]

    for i in range(config.iterations):
        rng = random.Random(config.seed + i)  # nosec B311 — simulation, not crypto
        overrides_i: dict[int, int] = {}
        for uid in uids:  # ascending unique_id order for reproducibility
            low, mode, high = three_point[uid]
            minutes = round(_sample_duration(rng, config, low, mode, high))
            minutes = max(minutes, 0)
            overrides_i[uid] = minutes
            sampled_durations[uid].append(minutes)
        # discrete risk drivers — drawn AFTER all duration draws so risks=() is unchanged
        for ridx, risk in enumerate(active_risks):
            prob = min(max(risk.probability, 0.0), 1.0)
            occurred = rng.random() < prob
            risk_occurred[ridx].append(occurred)
            if occurred:
                factor = _sample_duration(
                    rng,
                    config,
                    max(risk.impact_low, 0.0),
                    max(risk.impact_ml, 0.0),
                    max(risk.impact_high, 0.0),
                )
                for uid in risk.affected:
                    if uid in overrides_i:
                        overrides_i[uid] = max(0, round(overrides_i[uid] * factor))
        result = compute_cpm(schedule, duration_overrides=overrides_i)
        finishes.append(result.project_finish)
        for uid in uids:
            if result.timings[uid].total_float <= 0:
                critical_counts[uid] += 1

    return _build_result(
        schedule,
        cpm,
        config,
        auto_used,
        tasks,
        sampled_durations,
        critical_counts,
        finishes,
        active_risks,
        risk_occurred,
    )


def _risk_drivers(
    schedule: Schedule,
    risks: Sequence[RiskEvent],
    risk_occurred: Sequence[Sequence[bool]],
    finishes: Sequence[int],
) -> tuple[RiskDriver, ...]:
    """Per-risk :class:`RiskDriver` contributions, sorted by abs(delta) desc then id.

    ``mean_delta_days`` = (mean finish over the iterations the risk occurred minus the mean
    finish over those it did not) / working-minutes-per-day, rounded to 1dp; ``0.0`` when
    there is no contrast (never occurred, always occurred, or equal-mean groups).
    """
    if not risks:
        return ()
    wmpd = schedule.calendar.working_minutes_per_day or 480
    drivers: list[RiskDriver] = []
    for risk, occ in zip(risks, risk_occurred, strict=True):
        on = [float(f) for f, o in zip(finishes, occ, strict=True) if o]
        off = [float(f) for f, o in zip(finishes, occ, strict=True) if not o]
        hits = len(on)
        if on and off:
            delta = round((statistics.fmean(on) - statistics.fmean(off)) / wmpd, 1)
        else:
            delta = 0.0
        drivers.append(
            RiskDriver(
                id=risk.id,
                name=risk.name,
                probability=risk.probability,
                hits=hits,
                mean_delta_days=delta,
            )
        )
    drivers.sort(key=lambda d: (-abs(d.mean_delta_days), d.id))
    return tuple(drivers)


def _build_result(
    schedule: Schedule,
    cpm: CPMResult,
    config: SRAConfig,
    auto_used: bool,
    tasks: Sequence[Task],
    sampled_durations: Mapping[int, list[int]],
    critical_counts: Mapping[int, int],
    finishes: Sequence[int],
    risks: Sequence[RiskEvent] = (),
    risk_occurred: Sequence[Sequence[bool]] = (),
) -> SRAResult:
    """Assemble the :class:`SRAResult` from the collected iteration series."""
    n = len(finishes)
    finishes_f = [float(f) for f in finishes]
    # Spearman ranks the SAME finish series against every activity's sampled durations; the finish
    # ranks are identical each time, so compute them ONCE here instead of re-ranking (sort) the
    # finish vector per activity (audit-C — byte-identical: _pearson receives the same two rank
    # lists it does today, just without the redundant N-1 re-sorts).
    finish_ranks = _average_ranks(finishes_f)
    sorted_finishes = sorted(finishes)
    sorted_finishes_f = [float(f) for f in sorted_finishes]
    finish_sigma = statistics.pstdev(finishes_f) if n > 1 else 0.0

    p10 = round(_percentile(sorted_finishes_f, 10))
    p50 = round(_percentile(sorted_finishes_f, 50))
    p80 = round(_percentile(sorted_finishes_f, 80))
    p90 = round(_percentile(sorted_finishes_f, 90))
    mean = statistics.fmean(finishes_f)

    deterministic = cpm.project_finish
    # fraction of iterations finishing on or before the deterministic finish
    det_pct = bisect.bisect_right(sorted_finishes, deterministic) / n

    activities: list[ActivitySensitivity] = []
    for task in tasks:
        uid = task.unique_id
        durs = sampled_durations[uid]
        ci = critical_counts[uid] / n
        durs_f = [float(d) for d in durs]
        sensitivity = _pearson(
            _average_ranks(durs_f), finish_ranks
        )  # Spearman; finish ranks hoisted
        dur_sigma = statistics.pstdev(durs_f) if n > 1 else 0.0
        ssi = (dur_sigma * ci) / finish_sigma if finish_sigma > 0.0 else 0.0
        activities.append(
            ActivitySensitivity(
                unique_id=uid,
                criticality_index=ci,
                duration_sensitivity=sensitivity,
                ssi=ssi,
            )
        )

    cdf = _build_cdf(sorted_finishes, n)
    histogram = _build_histogram(sorted_finishes)
    constraints = tuple(t.unique_id for t in tasks if t.has_hard_constraint)
    risk_drivers = _risk_drivers(schedule, risks, risk_occurred, finishes)

    cal = schedule.calendar
    ps = schedule.project_start

    def _iso(offset: int) -> str:
        return offset_to_datetime(ps, max(offset, 0), cal).isoformat()

    return SRAResult(
        iterations=config.iterations,
        seed=config.seed,
        auto_used=auto_used,
        deterministic_finish=deterministic,
        deterministic_percentile=det_pct,
        p10=p10,
        p50=p50,
        p80=p80,
        p90=p90,
        mean=mean,
        deterministic_finish_date=_iso(deterministic),
        p10_date=_iso(p10),
        p50_date=_iso(p50),
        p80_date=_iso(p80),
        p90_date=_iso(p90),
        cdf=cdf,
        histogram=histogram,
        activities=tuple(activities),
        constraints_flagged=constraints,
        risk_drivers=risk_drivers,
    )


def _build_cdf(sorted_finishes: Sequence[int], n: int) -> tuple[tuple[int, float], ...]:
    """The empirical CDF as ``(finish offset, cumulative probability)`` points.

    One point per distinct finish value: its cumulative probability is the fraction of
    samples at or below it (a right-continuous step S-curve, deduplicated to the distinct
    breakpoints).
    """
    points: list[tuple[int, float]] = []
    idx = 0
    while idx < len(sorted_finishes):
        value = sorted_finishes[idx]
        # advance over the run of equal values; the last index + 1 is the count <= value
        while idx + 1 < len(sorted_finishes) and sorted_finishes[idx + 1] == value:
            idx += 1
        points.append((value, (idx + 1) / n))
        idx += 1
    return tuple(points)


def _build_histogram(sorted_finishes: Sequence[int]) -> tuple[tuple[int, int, int], ...]:
    """A fixed-width finish-date histogram (PDF) over ``[min, max]`` of the finishes.

    ``_HISTOGRAM_BINS`` equal-width bins; the last bin is closed on the right so the max
    sample lands in it. A degenerate (single distinct value) sample yields one bin holding
    every sample. Each bin is ``(low_offset, high_offset, count)``.
    """
    lo = sorted_finishes[0]
    hi = sorted_finishes[-1]
    if hi == lo:
        return ((lo, hi, len(sorted_finishes)),)
    width = (hi - lo) / _HISTOGRAM_BINS
    counts = [0] * _HISTOGRAM_BINS
    for value in sorted_finishes:
        b = int((value - lo) / width)
        if b >= _HISTOGRAM_BINS:  # the max value
            b = _HISTOGRAM_BINS - 1
        counts[b] += 1
    bins: list[tuple[int, int, int]] = []
    for b in range(_HISTOGRAM_BINS):
        bin_lo = round(lo + b * width)
        bin_hi = round(lo + (b + 1) * width)
        bins.append((bin_lo, bin_hi, counts[b]))
    return tuple(bins)


# ======================================================================================
# SSI Schedule Risk & Opportunity Analysis (ADR-0123) — a separate, parity-isolated path
# that mirrors SSI Tools' add-in. It reuses the same trusted ``compute_cpm`` chokepoint and the
# sampling/percentile/CDF primitives above; the legacy ``compute_sra``/``RiskEvent`` path is left
# byte-frozen. Validated against the operator's SSI exports: the BC/WC formula and the
# deterministic OAT swing reproduce SSI; the stochastic distribution is NOT bit-exact (std-lib RNG
# ≠ SSI's generator — ADR-0005/0106).
# ======================================================================================

#: Working minutes in one working day (480 = 8h). The presentation-boundary days conversion.
_MIN_PER_DAY = 480


@dataclass(frozen=True)
class RiskFactorTable:
    """The SSI "Risk Factors" table: ranking factor 1..5 → (% to subtract for Best Case,
    % to add for Worst Case). The default rows are SSI's (operator screenshot)."""

    rows: tuple[tuple[int, float, float], ...] = (
        (1, 50.0, 10.0),
        (2, 40.0, 20.0),
        (3, 30.0, 30.0),
        (4, 20.0, 40.0),
        (5, 10.0, 50.0),
    )

    def for_factor(self, factor: int) -> tuple[float, float]:
        """``(subtract%, add%)`` for a 1..5 factor (clamped into range)."""
        f = max(1, min(5, factor))
        for row_f, sub, add in self.rows:
            if row_f == f:
                return (sub, add)
        return (0.0, 0.0)


@dataclass(frozen=True)
class ScheduleRisk:
    """An SSI risk-register entry — a discrete risk/opportunity with an **additive** schedule
    impact in working days on its affected task(s).

    When it fires (per :class:`SRAConfig.occurrence_mode`) ``impact_days`` working days are added to
    each affected activity's sampled duration (SSI: a positive impact is a risk/delay, a negative
    one an opportunity/acceleration). A risk-bearing task carries **no** Best/Worst duration
    uncertainty in the run — the risk drives it instead (the SSI behaviour the operator confirmed).
    ``consequence_rating`` (1..5) is the operator's severity for the 5x5 matrix; ``None`` derives it
    from the ``|impact_days|`` band."""

    id: str
    name: str
    probability: float  # 0..1 occurrence probability
    impact_days: float  # additive working days when it fires (>=0 risk, <0 opportunity)
    affected: tuple[int, ...]
    consequence_rating: int | None = None


@dataclass(frozen=True)
class ProbabilisticBranch:
    """A Hulett **probabilistic branch** (ADR-0273): a discrete event that, when it fires (with
    ``probability`` per iteration), inserts a *rework* activity — a fragnet — onto an existing
    Finish-to-Start logic tie ``after_uid -> before_uid``, delaying everything downstream by the
    fragnet's sampled duration. Unlike a :class:`ScheduleRisk` (which adds days to an *existing*
    task), the branch is a NEW node on a chosen link, so it participates in merge bias — it only
    moves the finish when it becomes the driving path — and produces the bi-modal finish
    distribution (a spike at "no failure" + a shifted lump when the rework happens) the
    deterministic plan hides. The inserted activity carries its own 3-point duration
    ``(low, ml, high)`` in working minutes. A branch whose ``after_uid -> before_uid`` FS tie does
    not exist is inert (disclosed)."""

    id: str
    name: str
    probability: float  # 0..1 chance the branch fires each iteration
    after_uid: int  # the predecessor of the FS tie the fragnet is inserted onto
    before_uid: (
        int  # the successor of that tie (after_uid -> before_uid becomes after -> F -> before)
    )
    low: int  # inserted-activity Best-Case duration (working minutes)
    ml: int  # Most-Likely duration
    high: int  # Worst-Case duration


@dataclass(frozen=True)
class OATSensitivity:
    """A deterministic one-at-a-time sensitivity row (SSI "Sensitivity Analysis" export).

    With every other activity held at its Most-Likely (=remaining) duration, this one activity is
    forced to its Best Case then Worst Case and the **focus event finish** is re-solved.
    ``opportunity_days`` = baseline - finish_at_BC (how much earlier the focus could finish);
    ``risk_days`` = finish_at_WC - baseline (how much later); ``total_days`` = their sum. Working
    days throughout."""

    unique_id: int
    bc_minutes: int
    wc_minutes: int
    ml_minutes: int
    event_finish_bc: int
    event_finish_wc: int
    opportunity_days: float
    risk_days: float
    total_days: float


@dataclass(frozen=True)
class SSIRiskStat:
    """Per-risk outcome of an SSI run + its 5x5-matrix ratings."""

    id: str
    name: str
    probability: float
    impact_days: float
    hits: int  # iterations the risk fired
    mean_delta_days: float  # mean focus finish when it fired minus when it didn't (working days)
    probability_rating: int  # 1..5 from the occurrence band
    consequence_rating: int  # 1..5 (operator-entered or |impact_days| band)


@dataclass(frozen=True)
class SSIBranchStat:
    """Per-branch outcome of an SSI run (ADR-0273) — how often the rework fired and its impact."""

    id: str
    name: str
    probability: float  # the entered per-iteration firing probability
    applied: bool  # False if the after_uid -> before_uid FS tie was absent (branch inert)
    hits: int  # iterations the branch fired
    fired_fraction: float  # hits / iterations
    mean_fragnet_days: float  # mean sampled rework duration when it fired (working days)
    mean_delta_days: float  # mean focus finish when it fired minus when it didn't (working days)


@dataclass(frozen=True)
class BranchPlan:
    """One arm of a :class:`ConditionalBranch` (ADR-0274): an alternative/contingency **fragnet** —
    a new activity inserted onto an existing Finish-to-Start tie ``after_uid -> before_uid``, like
    a :class:`ProbabilisticBranch`'s rework node — carrying its own 3-point duration
    ``(low, ml, high)`` in working minutes. The two plans of a conditional branch are **mutually
    exclusive**: in a given iteration exactly one plan's fragnet takes a sampled duration and the
    other stays at its zero placeholder. A plan whose FS tie is absent makes the whole conditional
    inert (disclosed). ``low <= ml <= high`` (clamped at use)."""

    after_uid: int
    before_uid: int
    low: int
    ml: int
    high: int
    name: str = ""


@dataclass(frozen=True)
class ConditionalBranch:
    """A Hulett **conditional branch** (ADR-0274): contingency-plan switching. Each iteration a
    **condition** on a monitored activity decides which of two mutually-exclusive plans executes —
    the primary ``plan_a`` (condition NOT tripped, "stick with Plan A") or the contingency
    ``plan_b`` (tripped, "fall to Plan B"). The run reports **which plan wins how often**.

    Unlike a :class:`ProbabilisticBranch` (a fixed-probability coin flip that *adds* rework), the
    choice here is driven by the iteration's *realized* state, so the headline is "how often it
    fell to the fallback" and the finish distribution reflects the plan mix. Both plans are fragnets
    (see :class:`BranchPlan`); with both at their zero placeholder the augmented network is
    byte-identical to the base (verified against ``compute_cpm``).

    ``metric`` selects the monitored quantity, compared against ``threshold_minutes`` (working
    minutes — a *duration* for ``"duration"``, a finish *offset* for ``"finish"``):

    * ``"duration"`` — the sampled duration of ``monitor_uid`` this iteration (read pre-solve; one
      CPM solve per iteration, as today).
    * ``"finish"`` — the early-finish **offset** of ``monitor_uid`` on the *pre-contingency* network
      (read from one extra per-iteration probe solve). The monitor must be **upstream** of the
      branch, which makes its finish invariant to the plan fragnets (the no-circularity property
      verified before build); a finish-metric conditional therefore costs a second CPM solve per
      iteration, so it is off the page-load path.

    ``trip_when`` is ``"at_or_above"`` (default — fall to Plan B when the monitor runs **late**,
    the natural contingency trigger) or ``"below"`` (fall to Plan B when it runs early/short). A
    conditional whose monitor is absent, or **either** plan's FS tie is absent, is inert (disclosed,
    never silent)."""

    id: str
    name: str
    monitor_uid: int
    metric: str  # "duration" | "finish"
    threshold_minutes: int
    plan_a: BranchPlan  # primary — executes when the condition does NOT trip
    plan_b: BranchPlan  # contingency — executes when the condition trips
    trip_when: str = "at_or_above"  # "at_or_above" | "below"


@dataclass(frozen=True)
class SSIConditionalStat:
    """Per-conditional-branch outcome of an SSI run (ADR-0274) — which plan won how often + impact.

    ``plan_b_fraction`` is the reportable headline ("how often we fell to the contingency").
    ``mean_delta_days`` = mean focus finish when Plan B executed minus when Plan A executed (working
    days) — the empirical cost of falling to the fallback; ``0.0`` when one plan never executed."""

    id: str
    name: str
    monitor_uid: int
    metric: str
    threshold_minutes: int
    trip_when: str
    applied: bool  # False if the monitor or EITHER plan's FS tie was absent (conditional inert)
    plan_a_name: str
    plan_b_name: str
    plan_a_hits: int  # iterations Plan A executed (condition not tripped)
    plan_b_hits: int  # iterations Plan B executed (condition tripped)
    plan_a_fraction: float
    plan_b_fraction: float  # how often the plan fell to the contingency
    mean_a_finish_days: float  # mean focus finish (working days) over the Plan-A iterations
    mean_b_finish_days: float  # mean focus finish (working days) over the Plan-B iterations
    mean_delta_days: float  # mean_b_finish - mean_a_finish (cost of falling to Plan B)


@dataclass(frozen=True)
class SSIResult:
    """The SSI focus-event finish distribution + per-risk stats (parity-isolated, ADR-0123)."""

    iterations: int
    seed: int
    target_uid: int | None
    distribution: str
    occurrence_mode: str
    correlation: float
    used_risks: bool
    deterministic_finish: int  # the focus event's deterministic CPM finish (working-minute offset)
    deterministic_percentile: float
    p10: int
    p50: int
    p80: int
    p90: int
    mean: float
    std_days: float
    deterministic_finish_date: str
    p10_date: str
    p50_date: str
    p80_date: str
    p90_date: str
    mean_date: str
    cdf: tuple[tuple[int, float], ...]
    histogram: tuple[tuple[int, int, int], ...]
    # the finish-date spread in CALENDAR days (the std of the realigned finish dates) — the working-
    # day std_days converted to the basis SSI/MS-Project report dates in, so the two line up
    std_cal_days: float = 0.0
    # the same curves keyed by realigned ISO date for direct plotting (S-curve points + histogram
    # bin-centre counts): one S-curve point per distinct simulated finish (a dense, smooth curve)
    s_curve: tuple[tuple[str, float], ...] = field(default=())
    finish_hist: tuple[tuple[str, int], ...] = field(default=())
    risks: tuple[SSIRiskStat, ...] = field(default=())
    # correlation-matrix provenance (ADR-0270) — a full pairwise/shared-driver matrix drove
    # this run (else the scalar single-factor path); the entered matrix's smallest eigenvalue
    # (< 0 ⇒ was infeasible) and the Frobenius size of any repair, so the fix is never silent.
    correlation_matrix_applied: bool = False
    correlation_matrix_repaired: bool = False
    correlation_min_eigenvalue: float = 0.0
    correlation_frobenius_distance: float = 0.0
    #: the sampler that produced this run (ADR-0271): "mc" (Monte-Carlo) or "lhs" (Latin Hypercube)
    sampling: str = "mc"
    #: per-activity Criticality Index from THIS run (ADR-0272): (unique_id, fraction of iterations
    #: the activity was critical — total float <= 0), ascending uid. Already tallied per iteration
    #: for the run; surfaced here (was discarded) so the risk-critical Gantt tint can read it.
    criticality: tuple[tuple[int, float], ...] = ()
    #: per-probabilistic-branch outcomes (ADR-0273): fired fraction + mean rework magnitude + mean
    #: finish impact. Empty when no branches were supplied (the byte-frozen default).
    branches: tuple[SSIBranchStat, ...] = ()
    #: per-conditional-branch outcomes (ADR-0274, Hulett #9): which plan won how often + the mean
    #: finish delta of falling to the contingency. Empty when no conditionals were supplied.
    conditionals: tuple[SSIConditionalStat, ...] = ()


def factor_to_bc_wc(
    remaining_minutes: int, factor: int, table: RiskFactorTable, minutes_per_day: int = _MIN_PER_DAY
) -> tuple[int, int, int]:
    """``(BestCase, MostLikely, WorstCase)`` working minutes from a 0..5 ranking factor.

    SSI: *the current Remaining Duration is the Most Likely*. ``BC = ML*(1 - sub%/100)``,
    ``WC = ML*(1 + add%/100)`` with the per-factor percentages from ``table`` — validated to match
    SSI's stored Best/Worst Case durations exactly. **Factor 0 means NO duration uncertainty**: no
    Best/Worst case to calculate, so BC = ML = WC = the remaining duration (a point mass).
    ``minutes_per_day`` is unused by the maths (the ratio is unit-free) but documents the working
    basis. Rounded to whole working minutes."""
    ml = max(0, int(remaining_minutes))
    if factor <= 0:  # operator: factor 0 -> no Best/Worst, use the remaining duration as-is
        return (ml, ml, ml)
    sub, add = table.for_factor(factor)
    bc = max(0, round(ml * (1.0 - sub / 100.0)))
    wc = max(ml, round(ml * (1.0 + add / 100.0)))
    return (bc, ml, wc)


def _ml_minutes(task: Task) -> int:
    """The activity's Most-Likely duration basis = the engine's ML mode: a completed task's own
    duration, else its remaining duration (matching ``_three_point`` at ``auto_most_likely=1.0``,
    so an all-ML SSI run reproduces ``compute_cpm`` — the ADR-0106 equivalence)."""
    if _is_completed(task):
        return int(task.duration_minutes)
    rem = task.remaining_duration_minutes
    return int(rem if rem is not None else task.duration_minutes)


def _finish_of(result: CPMResult, target_uid: int | None) -> int:
    """The focus event's early finish (the SSI 'Flag for Analysis' target), else project finish."""
    if target_uid is None or target_uid not in result.timings:
        return result.project_finish
    return result.timings[target_uid].early_finish


def deterministic_margin_bounds(
    schedule: Schedule, target_uid: int | None, margin_uids: frozenset[int]
) -> tuple[int, int]:
    """``(D, E)``: the all-ML deterministic finish and the same solve with the margin zeroed.

    ``D`` reproduces :func:`compute_sra_ssi`'s ``deterministic_finish`` exactly — the identical
    ``{uid: _ml_minutes(t)}`` override map and :func:`_finish_of` read (the ADR-0106 all-ML
    equivalence; pinned by test). ``E`` re-solves that SAME network with every ``margin_uids``
    duration forced to 0, giving the zero-margin boundary of §7.3.3.2.3's stochastic margin
    tracking on the run's own axis (no cross-basis subtraction). Purely additive: two reads
    through the trusted CPM chokepoint; nothing existing calls or is changed by this (F3c,
    ADR-0254). With no margin activities ``E == D``.
    """
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}
    d = _finish_of(compute_cpm(schedule, duration_overrides=ml), target_uid)
    zeroed = dict(ml)
    zeroed.update({uid: 0 for uid in margin_uids if uid in ml})
    e = _finish_of(compute_cpm(schedule, duration_overrides=zeroed), target_uid)
    return d, e


def _phi(z: float) -> float:
    """Standard-normal CDF Φ(z) via ``math.erf`` (std-lib) — the Gaussian-copula link function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


#: Std-lib standard normal, reused for the probit (LHS, ADR-0271) — no third-party numerics.
_STD_NORMAL = statistics.NormalDist()


def _phi_inv(p: float) -> float:
    """Standard-normal inverse CDF (probit) via std-lib ``NormalDist.inv_cdf``; the input is
    clamped to ``[1e-12, 1-1e-12]`` so a stratum-edge draw of 0.0/1.0 maps to a finite ±7.03,
    never ±inf or a math-domain error (ADR-0271)."""
    return _STD_NORMAL.inv_cdf(min(1.0 - 1e-12, max(1e-12, p)))


def _lhs_seed(base_seed: int) -> int:
    """A disjoint integer transform of the base seed for the LHS plan's DEDICATED RNG stream — a
    different salt from the per-iteration ``seed+i`` streams and the ``_occurrence_schedule``
    stream, so the plan's draws cannot advance or coincide with them (no worse than plain MC)."""
    return (base_seed * 2246822519 ^ 0x5F3759DF) & 0x7FFFFFFF


@dataclass(frozen=True)
class LatinHypercubePlan:
    """A seeded Latin Hypercube plan (ADR-0271): ``columns`` is one stratified,
    independently-permuted [0, 1) sequence per sampling dimension, each of length ``iterations``.
    Built ONCE before the per-iteration loop on a dedicated RNG stream (RNG-free w.r.t. every
    ``random.Random(seed+i)`` stream), so it can never perturb the frozen Monte-Carlo path."""

    columns: tuple[tuple[float, ...], ...]
    iterations: int


def _lhs_plan(seed: int, iterations: int, n_columns: int, centered: bool) -> LatinHypercubePlan:
    """Build the seeded LHS plan: for each of ``n_columns`` dimensions, exactly one sample in each
    stratum ``[k/N, (k+1)/N)`` — random within the stratum (McKay-Beckman-Conover 1979) or the
    stratum midpoint when ``centered`` — then a std-lib Fisher-Yates shuffle so each dimension's
    permutation is independent. Deterministic, std-lib, fixed operation order (no set/dict traversal
    in the numeric path)."""
    rng = random.Random(_lhs_seed(seed))  # nosec B311 — simulation, not crypto
    columns: list[tuple[float, ...]] = []
    for _d in range(n_columns):
        col = [(k + (0.5 if centered else rng.random())) / iterations for k in range(iterations)]
        rng.shuffle(col)
        columns.append(tuple(col))
    return LatinHypercubePlan(columns=tuple(columns), iterations=iterations)


def _build_lhs_plan(
    config: SRAConfig,
    uids: Sequence[int],
    three: Mapping[int, tuple[int, int, int]],
    prepared: PreparedCorrelation | None,
) -> LatinHypercubePlan | None:
    """The run's LHS plan, or ``None`` to run plain Monte-Carlo (the byte-frozen default). The
    column count EXACTLY matches the shared sampler's per-iteration draw count for the active
    correlation branch, so plan column ↔ draw is a stable mapping. Returns ``None`` (→ the
    identical MC branch) when the mode is off or every activity is a point mass (ADR-0271)."""
    if config.sampling != "lhs":
        return None
    uncertain = [u for u in uids if three[u][2] > three[u][0]]
    if prepared is not None:
        n_columns = len(prepared.uids)  # matrix: N correlated normals
    elif max(0.0, min(1.0, config.correlation)) > 0.0:
        n_columns = 1 + len(uncertain)  # scalar single-factor: 1 common + D idiosyncratic
    else:
        n_columns = len(uncertain)  # independent: D stratified uniforms
    if n_columns == 0:
        return None
    return _lhs_plan(config.seed, config.iterations, n_columns, config.lhs_centered)


def _lhs_overrides(
    config: SRAConfig,
    uids: Sequence[int],
    three: Mapping[int, tuple[int, int, int]],
    prepared: PreparedCorrelation | None,
    plan: LatinHypercubePlan,
    iteration: int,
) -> dict[int, int]:
    """The Latin Hypercube branch of the shared sampler (ADR-0271): the plan's stratified columns
    replace the per-iteration RNG draws, walked by a cursor in the EXACT current draw order. The
    correlation composition is unchanged — only the SOURCE of the normals/uniforms differs
    (LHS-then-Cholesky). Duration dimensions only; the triangular inverse-CDF is used for every
    marginal, so ``distribution="pert"`` under LHS falls back to triangular (documented — there is
    no std-lib PERT inverse, mirroring the scalar-correlation quirk)."""
    overrides: dict[int, int] = {}
    cols = plan.columns
    if prepared is not None:  # matrix: z = probit of stratified uniforms, then x = L z
        n = len(prepared.uids)
        pos = {u: k for k, u in enumerate(prepared.uids)}
        z = [_phi_inv(cols[k][iteration]) for k in range(n)]
        x = [sum(prepared.chol[k][j] * z[j] for j in range(k + 1)) for k in range(n)]
        for u in uids:
            low, mode, high = three[u]
            if high <= low:  # point mass — no column consumed (matches the MC path)
                overrides[u] = round(low)
                continue
            uni = _phi(x[pos[u]])
            overrides[u] = max(
                0, round(_sample_triangular(uni, float(low), float(mode), float(high)))
            )
        return overrides
    r = max(0.0, min(1.0, config.correlation))
    if r > 0.0:  # scalar single-factor: common + idiosyncratic, both probit of stratified uniforms
        k_common, k_indep = math.sqrt(r), math.sqrt(1.0 - r)
        common = _phi_inv(cols[0][iteration])
        c = 1
        for u in uids:
            low, mode, high = three[u]
            if high <= low:
                overrides[u] = round(low)
                continue
            uni = _phi(k_common * common + k_indep * _phi_inv(cols[c][iteration]))
            c += 1
            overrides[u] = max(
                0, round(_sample_triangular(uni, float(low), float(mode), float(high)))
            )
        return overrides
    c = 0  # r == 0: the stratified uniform IS the copula uniform — no probit round-trip
    for u in uids:
        low, mode, high = three[u]
        if high <= low:
            overrides[u] = round(low)
            continue
        uni = cols[c][iteration]
        c += 1
        overrides[u] = max(0, round(_sample_triangular(uni, float(low), float(mode), float(high))))
    return overrides


def _iteration_duration_overrides(
    rng: random.Random,
    config: SRAConfig,
    uids: Sequence[int],
    three: Mapping[int, tuple[int, int, int]],
    prepared: PreparedCorrelation | None = None,
    *,
    plan: LatinHypercubePlan | None = None,
    iteration: int = 0,
) -> dict[int, int]:
    """One iteration's sampled duration overrides (working minutes), SHARED by
    :func:`compute_sra_ssi` and :func:`compute_jcl` so their finish marginals stay
    byte-identical (the ADR-0269 equality pin) — a single sampler, no drifting copies.

    ``prepared is None`` — the scalar single-factor Gaussian copula (byte-frozen, ADR-0106/
    0123): one shared ``common`` normal (only when ``config.correlation > 0``) plus one
    idiosyncratic normal per uncertain activity, in ascending-``unique_id`` order; a
    point-mass activity (``high <= low``) consumes NO draw. Reproduces the prior inline block
    statement-for-statement, including the deliberate quirk that a positive scalar correlation
    always samples via the triangular inverse-CDF even under ``distribution="pert"``.

    ``prepared`` set — the multivariate Gaussian copula (ADR-0270): N correlated normals from
    the prepared Cholesky factor (``x = L z``), one per uncertain activity, mapped through
    :func:`_phi` → the triangular inverse-CDF. A DISTINCT mode (N idiosyncratic draws, no
    common draw), never a silent reroute of the scalar path.

    ``plan`` set (ADR-0271) — Latin Hypercube: the same three correlation branches, but the
    per-iteration RNG draws are replaced by the stratified plan columns (delegated to
    :func:`_lhs_overrides`). ``plan is None`` (the default) runs the exact Monte-Carlo statements
    below, byte-for-byte, so every frozen run is untouched.
    """
    if plan is not None:
        return _lhs_overrides(config, uids, three, prepared, plan, iteration)
    overrides: dict[int, int] = {}
    if prepared is None:
        r = max(0.0, min(1.0, config.correlation))
        k_common, k_indep = math.sqrt(r), math.sqrt(1.0 - r)
        common = rng.gauss(0.0, 1.0) if r > 0.0 else 0.0
        for u in uids:
            low, mode, high = three[u]
            if high <= low:  # point mass — no draw
                overrides[u] = round(low)
                continue
            if r > 0.0:
                uni = _phi(k_common * common + k_indep * rng.gauss(0.0, 1.0))
                minutes = _sample_triangular(uni, float(low), float(mode), float(high))
            else:
                minutes = _sample_duration(rng, config, float(low), float(mode), float(high))
            overrides[u] = max(0, round(minutes))
        return overrides

    chol = prepared.chol
    n = len(prepared.uids)
    pos = {u: k for k, u in enumerate(prepared.uids)}
    z = [rng.gauss(0.0, 1.0) for _ in range(n)]  # N correlated draws, ascending-uid order
    x = [sum(chol[k][j] * z[j] for j in range(k + 1)) for k in range(n)]  # x = L z (unit variance)
    for u in uids:
        low, mode, high = three[u]
        if high <= low:  # point mass — no draw (identical to the scalar path)
            overrides[u] = round(low)
            continue
        uni = _phi(x[pos[u]])
        minutes = _sample_triangular(uni, float(low), float(mode), float(high))
        overrides[u] = max(0, round(minutes))
    return overrides


def _prob_rating(probability: float) -> int:
    """5x5-matrix likelihood rating 1..5 from an occurrence probability (SSI/▸DoD bands:
    1 <20%, 2 20-39%, 3 40-59%, 4 60-79%, 5 ≥80%)."""
    p = max(0.0, min(1.0, probability)) * 100.0
    if p >= 80.0:
        return 5
    if p >= 60.0:
        return 4
    if p >= 40.0:
        return 3
    if p >= 20.0:
        return 2
    return 1


_DAYS_PER_MONTH = 365.25 / 12.0  # 30.4375 calendar days/month (the Schedule-guideline conversion)


def _consequence_rating(impact_days: float) -> int:
    """5x5-matrix consequence rating 1..5 from a schedule-impact magnitude, following the NASA
    "Schedule" consequence guideline by converting the impact **days to calendar months**
    (365.25/12 = 30.44 days/month): <1 week -> 1; 1 week to <1 month -> 2; 1 to <3 months -> 3;
    3 to <=6 months -> 4; >6 months -> 5. (An opportunity's negative impact uses its magnitude.)"""
    days = abs(impact_days)
    if days < 7.0:  # < 1 week
        return 1
    if days < _DAYS_PER_MONTH:  # 1 week to < 1 month
        return 2
    if days < 3.0 * _DAYS_PER_MONTH:  # 1 to < 3 months
        return 3
    if days <= 6.0 * _DAYS_PER_MONTH:  # 3 to <= 6 months
        return 4
    return 5  # > 6 months


def _occurrence_schedule(
    active_risks: Sequence[ScheduleRisk], mode: str, iterations: int, seed: int
) -> list[list[bool]]:
    """Per-risk x per-iteration occurrence matrix, drawn on a stream **disjoint** from the
    per-iteration duration RNG (so the duration draws — and thus the ``correlation=0`` result — are
    independent of the risk mode). ``random_each``: independent Bernoulli per iteration.
    ``exact_overall``: exactly ``round(p*iterations)`` firings at random iteration indices."""
    out: list[list[bool]] = []
    for ridx, risk in enumerate(active_risks):
        p = max(0.0, min(1.0, risk.probability))
        rng = random.Random((seed * 2654435761 ^ (ridx + 1) * 40503) & 0x7FFFFFFF)  # nosec B311
        if mode == "exact_overall":
            k = round(p * iterations)
            fired = [False] * iterations
            for i in rng.sample(range(iterations), min(k, iterations)):
                fired[i] = True
        else:  # random_each (default)
            fired = [rng.random() < p for _ in range(iterations)]
        out.append(fired)
    return out


def _augment_with_branches(
    schedule: Schedule, branches: Sequence[ProbabilisticBranch]
) -> tuple[Schedule, dict[str, int]]:
    """Insert each probabilistic branch's rework fragnet into the network ONCE (ADR-0273),
    returning the augmented schedule + a ``{branch_id: fragnet_uid}`` map for the applied branches.

    For a branch whose ``after_uid -> before_uid`` **FS** tie exists, that tie is replaced by
    ``after_uid --FS0--> F --FS(original lag)--> before_uid`` where ``F`` is a new leaf activity
    with a **zero placeholder duration** — so with ``F`` left at 0 the augmented network is
    byte-identical to the base (the no-fire case; verified against ``compute_cpm``), and the
    Monte-Carlo toggles ``F``'s duration per iteration via ``duration_overrides`` (0 = didn't fire,
    sampled = fired). A branch whose FS tie is absent is dropped (inert — not in the returned
    map, disclosed upstream).
    Fragnet uids are assigned above every existing uid, so they cannot collide."""
    if not branches:
        return schedule, {}
    tasks = list(schedule.tasks)
    rels = list(schedule.relationships)
    next_uid = (max((t.unique_id for t in tasks), default=0)) + 1
    fragnet_uids: dict[str, int] = {}
    # Two+ branches on the SAME after->before tie CHAIN in series (after -> F1 -> F2 -> before),
    # each firing independently, so both rework events apply instead of the second going inert.
    # `chain_pred` tracks the current predecessor of before_uid for a tie so each next fragnet
    # inserts onto the live segment (`F1 -> before`), not the already-consumed original tie.
    chain_pred: dict[tuple[int, int], int] = {}
    for branch in branches:
        key = (branch.after_uid, branch.before_uid)
        pred = chain_pred.get(key, branch.after_uid)
        idx = next(
            (
                k
                for k, r in enumerate(rels)
                if r.predecessor_id == pred
                and r.successor_id == branch.before_uid
                and r.type == RelationshipType.FS
            ),
            None,
        )
        if idx is None:
            continue  # inert: no FS tie to insert the rework onto
        orig = rels.pop(idx)
        f_uid = next_uid
        next_uid += 1
        tasks.append(
            Task(unique_id=f_uid, name=branch.name or f"Rework {branch.id}", duration_minutes=0)
        )
        rels.append(
            Relationship(
                predecessor_id=pred,
                successor_id=f_uid,
                type=RelationshipType.FS,
                lag_minutes=0,
            )
        )
        rels.append(
            Relationship(
                predecessor_id=f_uid,
                successor_id=branch.before_uid,
                type=RelationshipType.FS,
                lag_minutes=orig.lag_minutes,
            )
        )
        chain_pred[key] = f_uid  # a later same-tie branch inserts after this fragnet
        fragnet_uids[branch.id] = f_uid
    aug = schedule.model_copy(update={"tasks": tuple(tasks), "relationships": tuple(rels)})
    return aug, fragnet_uids


def _branch_draws(
    branches: Sequence[ProbabilisticBranch], mode: str, iterations: int, seed: int
) -> tuple[list[list[bool]], list[list[float]]]:
    """Per-branch firing matrix + per-branch fragnet-duration uniforms (ADR-0273), each on a stream
    **disjoint** from the duration/correlation/LHS draws, the risk-occurrence draws, and each
    other — so branches never perturb the byte-frozen no-branch path and are reproducible.
    ``random_each``: independent Bernoulli per iteration; ``exact_overall``: exactly
    ``round(p*iterations)`` firings."""
    fired_all: list[list[bool]] = []
    uni_all: list[list[float]] = []
    for bidx, b in enumerate(branches):
        p = max(0.0, min(1.0, b.probability))
        rng = random.Random((seed * 2246822519 ^ (bidx + 1) * 0x9E3779B1) & 0x7FFFFFFF)  # nosec B311
        if mode == "exact_overall":
            k = round(p * iterations)
            fired = [False] * iterations
            for i in rng.sample(range(iterations), min(k, iterations)):
                fired[i] = True
        else:
            fired = [rng.random() < p for _ in range(iterations)]
        drng = random.Random((seed * 40503 ^ (bidx + 1) * 2654435761) & 0x7FFFFFFF)  # nosec B311
        uni = [drng.random() for _ in range(iterations)]
        fired_all.append(fired)
        uni_all.append(uni)
    return fired_all, uni_all


def _build_branch_stats(
    applied: Sequence[ProbabilisticBranch],
    iterations: int,
    mpd: int,
    fragnet_days: Sequence[Sequence[float]],
    fire_finish: Sequence[Sequence[int]],
    nofire_finish: Sequence[Sequence[int]],
) -> tuple[SSIBranchStat, ...]:
    """Per-branch outcome stats (ADR-0273): fired fraction, mean rework magnitude, and the mean
    finish delta (mean focus finish when the branch fired minus when it didn't, working days)."""
    stats: list[SSIBranchStat] = []
    for bidx, b in enumerate(applied):
        hits = len(fire_finish[bidx])
        mean_frag = statistics.fmean(fragnet_days[bidx]) if fragnet_days[bidx] else 0.0
        delta = (
            (statistics.fmean(fire_finish[bidx]) - statistics.fmean(nofire_finish[bidx])) / mpd
            if fire_finish[bidx] and nofire_finish[bidx]
            else 0.0
        )
        stats.append(
            SSIBranchStat(
                id=b.id,
                name=b.name,
                probability=max(0.0, min(1.0, b.probability)),
                applied=True,
                hits=hits,
                fired_fraction=hits / iterations if iterations else 0.0,
                mean_fragnet_days=round(mean_frag, 2),
                mean_delta_days=round(delta, 2),
            )
        )
    return tuple(stats)


def _augment_with_conditionals(
    schedule: Schedule, conditionals: Sequence[ConditionalBranch]
) -> tuple[Schedule, dict[str, tuple[int, int]]]:
    """Insert BOTH plan fragnets of each conditional branch into the network ONCE (ADR-0274),
    returning the augmented schedule + a ``{conditional_id: (plan_a_uid, plan_b_uid)}`` map for the
    APPLIED conditionals.

    Each plan is inserted exactly like a :func:`_augment_with_branches` rework node —
    ``after --FS0--> F --FS(orig lag)--> before`` with ``F`` a zero-placeholder leaf — so with both
    plan fragnets left at 0 the augmented network is byte-identical to the base (the no-fire case;
    verified against ``compute_cpm``). The Monte-Carlo then toggles exactly ONE plan's fragnet to a
    sampled duration per iteration. A conditional is **all-or-nothing**: if the monitor, or
    **either** plan's FS tie is missing, NEITHER plan is inserted and the conditional is dropped
    (inert — not in the returned map, disclosed upstream) so there is never a half-branch.
    Two plans on the SAME after->before tie chain in series (after -> Fa -> Fb -> before), so one
    firing per iteration still adds exactly that plan's duration. Fragnet uids are assigned above
    every existing uid, so they cannot collide."""
    if not conditionals:
        return schedule, {}
    tasks = list(schedule.tasks)
    rels = list(schedule.relationships)
    next_uid = (max((t.unique_id for t in tasks), default=0)) + 1
    # The monitor and plan endpoints must be SCHEDULED activities — non-summary AND active, the set
    # compute_cpm times and the sampler builds overrides over (non_summary == _scheduled_tasks).
    # Gating on the full task list instead let a summary/inactive monitor slip through as "applied",
    # then crash the finish-metric probe (`probe_timings[uid]` KeyError -> the whole SSI run aborts)
    # or read as 0 in the duration metric (a silent wrong plan mix reported applied=True). Gating on
    # the scheduled set makes such a conditional inert + disclosed instead, honoring the
    # never-silent contract (ADR-0274 hardening, audit M1).
    present = {t.unique_id for t in non_summary(schedule)}
    # a same-tie pair chains: `chain_pred` tracks the live predecessor of a tie across insertions,
    # so a second plan on the same tie inserts onto the live segment (Fa -> before), not the
    # already-consumed original tie. Shared across all conditionals (a later one sees a tie a prior
    # one consumed as gone -> inert, disclosed).
    chain_pred: dict[tuple[int, int], int] = {}

    def _tie_idx(after: int, before: int) -> int | None:
        pred = chain_pred.get((after, before), after)
        return next(
            (
                k
                for k, r in enumerate(rels)
                if r.predecessor_id == pred
                and r.successor_id == before
                and r.type == RelationshipType.FS
            ),
            None,
        )

    def _insert(plan: BranchPlan, cid: str) -> int:
        nonlocal next_uid
        key = (plan.after_uid, plan.before_uid)
        idx = _tie_idx(*key)
        if idx is None:  # pragma: no cover - the caller's all-or-nothing check guarantees the tie
            raise RuntimeError("conditional plan tie vanished before insertion")
        orig = rels.pop(idx)
        f_uid = next_uid
        next_uid += 1
        tasks.append(Task(unique_id=f_uid, name=plan.name or f"Plan {cid}", duration_minutes=0))
        rels.append(
            Relationship(
                predecessor_id=orig.predecessor_id,
                successor_id=f_uid,
                type=RelationshipType.FS,
                lag_minutes=0,
            )
        )
        rels.append(
            Relationship(
                predecessor_id=f_uid,
                successor_id=plan.before_uid,
                type=RelationshipType.FS,
                lag_minutes=orig.lag_minutes,
            )
        )
        chain_pred[key] = f_uid
        return f_uid

    plan_uids: dict[str, tuple[int, int]] = {}
    for cond in conditionals:
        # all-or-nothing: the monitor + all 4 plan endpoints must be scheduled activities AND both
        # plan ties must currently exist (chaining-aware). Any miss -> the conditional is inert.
        endpoints = (
            cond.monitor_uid,
            cond.plan_a.after_uid,
            cond.plan_a.before_uid,
            cond.plan_b.after_uid,
            cond.plan_b.before_uid,
        )
        if any(u not in present for u in endpoints):
            continue
        if _tie_idx(cond.plan_a.after_uid, cond.plan_a.before_uid) is None:
            continue
        if _tie_idx(cond.plan_b.after_uid, cond.plan_b.before_uid) is None:
            continue
        fa = _insert(cond.plan_a, cond.id)
        fb = _insert(cond.plan_b, cond.id)  # re-finds via chain_pred for the same-tie case
        plan_uids[cond.id] = (fa, fb)
    aug = schedule.model_copy(update={"tasks": tuple(tasks), "relationships": tuple(rels)})
    return aug, plan_uids


def _conditional_draws(
    conditionals: Sequence[ConditionalBranch], iterations: int, seed: int
) -> list[list[float]]:
    """Per-conditional per-iteration uniform for the CHOSEN plan's 3-point sample (ADR-0274), on a
    stream **disjoint** from the duration/correlation/LHS draws, the risk-occurrence draws, and the
    probabilistic-branch draws — so conditionals never perturb the byte-frozen no-conditional path
    and are reproducible. The *condition* (not a random draw) picks which plan runs; this uniform
    only samples that picked plan's rework duration via the triangular inverse-CDF."""
    out: list[list[float]] = []
    for cidx, _c in enumerate(conditionals):
        rng = random.Random((seed * 1900987 ^ (cidx + 1) * 0x27D4EB2F) & 0x7FFFFFFF)  # nosec B311
        out.append([rng.random() for _ in range(iterations)])
    return out


def _build_conditional_stats(
    applied: Sequence[ConditionalBranch],
    iterations: int,
    mpd: int,
    plan_a_finish: Sequence[Sequence[int]],
    plan_b_finish: Sequence[Sequence[int]],
) -> tuple[SSIConditionalStat, ...]:
    """Per-conditional outcome stats (ADR-0274): which plan won how often + the mean finish delta of
    falling to the contingency (mean Plan-B finish minus mean Plan-A finish, working days)."""
    stats: list[SSIConditionalStat] = []
    for cidx, c in enumerate(applied):
        a_fin = plan_a_finish[cidx]
        b_fin = plan_b_finish[cidx]
        a_hits, b_hits = len(a_fin), len(b_fin)
        mean_a = statistics.fmean(a_fin) / mpd if a_fin else 0.0
        mean_b = statistics.fmean(b_fin) / mpd if b_fin else 0.0
        delta = (mean_b - mean_a) if a_fin and b_fin else 0.0
        stats.append(
            SSIConditionalStat(
                id=c.id,
                name=c.name,
                monitor_uid=c.monitor_uid,
                metric=c.metric,
                threshold_minutes=c.threshold_minutes,
                trip_when=c.trip_when,
                applied=True,
                plan_a_name=c.plan_a.name or f"Plan {c.id}-A",
                plan_b_name=c.plan_b.name or f"Plan {c.id}-B",
                plan_a_hits=a_hits,
                plan_b_hits=b_hits,
                plan_a_fraction=a_hits / iterations if iterations else 0.0,
                plan_b_fraction=b_hits / iterations if iterations else 0.0,
                mean_a_finish_days=round(mean_a, 2),
                mean_b_finish_days=round(mean_b, 2),
                mean_delta_days=round(delta, 2),
            )
        )
    return tuple(stats)


def _conditional_trips(monitor_value: int, threshold: int, trip_when: str) -> bool:
    """Whether a conditional's condition trips (fall to Plan B). ``at_or_above`` trips when the
    monitored value is >= the threshold (the monitor ran late/long — the natural contingency
    trigger); ``below`` trips when it is < the threshold."""
    if trip_when == "below":
        return monitor_value < threshold
    return monitor_value >= threshold


def compute_sra_ssi(
    schedule: Schedule,
    *,
    config: SRAConfig = _DEFAULT_CONFIG,
    three_point: Mapping[int, tuple[int, int, int]] | None = None,
    risks: Sequence[ScheduleRisk] = (),
    branches: Sequence[ProbabilisticBranch] = (),
    conditionals: Sequence[ConditionalBranch] = (),
) -> SSIResult:
    """Run the SSI Monte-Carlo and return the focus-event :class:`SSIResult` (ADR-0123).

    ``three_point`` maps a ``unique_id`` to ``(BestCase, MostLikely, WorstCase)`` minutes for the
    activities that carry **duration uncertainty** (a Risk Ranking Factor or a manual Best/Worst);
    activities absent from it are a **point mass** at their ML (blank factor => no uncertainty). A
    **risk-affected** activity is always a point mass - the risk impact drives it, not a Best/Worst
    draw. Each iteration recomputes the finish through ``compute_cpm`` so the simulation
    can't diverge from the gate-locked engine; with everything point-mass at ML the reported finish
    equals ``compute_cpm``'s focus finish (the equivalence a test pins).

    ``config.correlation`` > 0 applies a single-factor **Gaussian copula** across the sampled
    activities (one shared normal per iteration), countering the central-limit cancelling of
    independent draws; it samples via the triangular inverse-CDF (the documented choice — the PERT
    quantile has no std-lib inverse), and at 0 the configured distribution is honoured exactly.

    ``conditionals`` adds Hulett **conditional branches** (ADR-0274, #9): each iteration a condition
    on a monitored activity picks one of two mutually-exclusive plan fragnets (primary Plan A vs
    contingency Plan B). Both plan fragnets are inserted up front as zero placeholders (byte-frozen
    when none apply). A ``metric="finish"`` conditional costs one extra ``compute_cpm`` probe solve
    per iteration to read the monitor's pre-contingency finish; ``metric="duration"`` ones read
    the sampled duration pre-solve and add no solve. Reports which plan won how often."""
    if config.iterations < 1:
        raise ValueError("SRAConfig.iterations must be >= 1")
    # Probabilistic branches (ADR-0273): insert each rework fragnet ONCE up front; the fragnet
    # activities are zero-duration leaves in the base/no-fire case (byte-frozen when no branch
    # applies) and are toggled to their sampled 3-point duration in the iterations they fire. The
    # whole Monte-Carlo then runs on this ONE augmented schedule via the duration_overrides hook.
    active_branches = [b for b in branches if b.probability > 0.0]
    schedule, fragnet_uids = _augment_with_branches(schedule, active_branches)
    applied_branches = [b for b in active_branches if b.id in fragnet_uids]
    # Conditional branches (ADR-0274): insert BOTH plan fragnets of each conditional ONCE, after the
    # probabilistic-branch augmentation (so #8's fragnet uids stay byte-identical). Both plans are
    # zero placeholders until a condition activates exactly one per iteration.
    schedule, cond_plan_uids = _augment_with_conditionals(schedule, conditionals)
    applied_conditionals = [c for c in conditionals if c.id in cond_plan_uids]
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    uids = [t.unique_id for t in tasks]
    uid_set = set(uids)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}
    # The deterministic anchor for the SSI distribution is the **all-ML run** finish (so the
    # simulation, the anchor and the percentile share one basis). Its DISPLAY date is realigned to
    # the focus task's STORED finish (the SSI "Current Finish") — pure-CPM offsets pack completed
    # work at the project start, so a constant correction puts the date axis back on the stored
    # dates (what the rest of the tool shows). Relative spacing + the OAT swing are unaffected.
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
            three[u] = (
                ml[u],
                ml[u],
                ml[u],
            )  # point mass (risk-driven, or no factor → no uncertainty)
        else:
            bc, mlv, wc = tp_in[u]
            three[u] = (max(0, int(bc)), int(mlv), max(int(bc), int(wc)))

    occ = _occurrence_schedule(active_risks, config.occurrence_mode, config.iterations, config.seed)
    mpd = schedule.calendar.working_minutes_per_day or _MIN_PER_DAY
    # the uncertain-duration activities (a point mass has high == low) — the correlation matrix,
    # when supplied, is prepared ONCE over exactly this set (ADR-0270, RNG-free); None → scalar.
    uncertain = [u for u in uids if three[u][2] > three[u][0]]
    prepared = prepare_correlation(uncertain, config.correlation_matrix)
    # the Latin Hypercube plan (ADR-0271), built ONCE off a dedicated RNG stream; None for the
    # frozen Monte-Carlo default. Shared identically with compute_jcl so the finish marginals match.
    plan = _build_lhs_plan(config, uids, three, prepared)

    # probabilistic-branch firing + fragnet-duration draws (ADR-0273), on streams disjoint from the
    # duration/risk draws; each fired iteration overrides its fragnet to a sampled 3-point duration.
    branch_fired, branch_uni = _branch_draws(
        applied_branches, config.occurrence_mode, config.iterations, config.seed
    )
    # conditional-branch chosen-plan uniforms (ADR-0274), on a stream disjoint from all the above.
    cond_uni = _conditional_draws(applied_conditionals, config.iterations, config.seed)
    # a finish-metric conditional reads the monitor's pre-contingency early finish → one extra probe
    # solve per iteration (with both plan fragnets at 0). Skipped entirely when every conditional is
    # duration-metric (or there are none), so the frozen no-conditional path adds no solve.
    needs_probe = any(c.metric == "finish" for c in applied_conditionals)

    finishes: list[int] = []
    critical_counts: dict[int, int] = dict.fromkeys(uids, 0)
    risk_occurred: list[list[bool]] = [[] for _ in active_risks]
    branch_fragnet_days: list[list[float]] = [[] for _ in applied_branches]
    branch_fire_finish: list[list[int]] = [[] for _ in applied_branches]
    branch_nofire_finish: list[list[int]] = [[] for _ in applied_branches]
    # per-conditional focus finishes split by which plan executed (for the "which plan wins" stats)
    cond_a_finish: list[list[int]] = [[] for _ in applied_conditionals]
    cond_b_finish: list[list[int]] = [[] for _ in applied_conditionals]

    for i in range(config.iterations):
        rng = random.Random(config.seed + i)  # nosec B311 — simulation, not crypto
        overrides = _iteration_duration_overrides(
            rng, config, uids, three, prepared, plan=plan, iteration=i
        )
        for ridx, risk in enumerate(active_risks):
            fired = occ[ridx][i]
            risk_occurred[ridx].append(fired)
            if fired:
                add = round(risk.impact_days * mpd)
                for u in risk.affected:
                    if u in overrides:
                        overrides[u] = max(0, overrides[u] + add)
        for bidx, branch in enumerate(applied_branches):
            if branch_fired[bidx][i]:  # fire → the fragnet takes a sampled 3-point rework duration
                dur = _sample_triangular(
                    branch_uni[bidx][i], float(branch.low), float(branch.ml), float(branch.high)
                )
                overrides[fragnet_uids[branch.id]] = max(0, round(dur))
                branch_fragnet_days[bidx].append(overrides[fragnet_uids[branch.id]] / mpd)
            # a non-fired branch leaves its fragnet at the 0 point-mass override (no delay)
        # conditional branches (ADR-0274): a probe solve (only if a finish-metric conditional is
        # present) reads each monitor's PRE-contingency finish — both plan fragnets are still at 0
        # here, so the monitor (upstream of its branch) sees its true finish. Then each condition
        # activates exactly one plan's fragnet; the other stays at its 0 placeholder.
        probe_timings = (
            compute_cpm(schedule, duration_overrides=overrides).timings if needs_probe else None
        )
        cond_took_b = [False] * len(applied_conditionals)
        for cidx, cond in enumerate(applied_conditionals):
            if cond.metric == "finish":
                if probe_timings is None:  # pragma: no cover - a finish metric implies needs_probe
                    raise RuntimeError("probe timings missing for a finish-metric conditional")
                monitor_value = probe_timings[cond.monitor_uid].early_finish
            else:  # duration: the monitor's realized sampled duration this iteration
                monitor_value = overrides.get(cond.monitor_uid, 0)
            trips = _conditional_trips(monitor_value, cond.threshold_minutes, cond.trip_when)
            cond_took_b[cidx] = trips
            chosen_plan = cond.plan_b if trips else cond.plan_a
            fa_uid, fb_uid = cond_plan_uids[cond.id]
            chosen_uid = fb_uid if trips else fa_uid
            dur = _sample_triangular(
                cond_uni[cidx][i],
                float(chosen_plan.low),
                float(chosen_plan.ml),
                float(chosen_plan.high),
            )
            overrides[chosen_uid] = max(0, round(dur))
            # the other plan's fragnet stays at its 0 point-mass override (not executed)
        result = compute_cpm(schedule, duration_overrides=overrides)
        fin = _finish_of(result, config.target_uid)
        finishes.append(fin)
        for bidx in range(len(applied_branches)):
            (branch_fire_finish if branch_fired[bidx][i] else branch_nofire_finish)[bidx].append(
                fin
            )
        for cidx in range(len(applied_conditionals)):
            (cond_b_finish if cond_took_b[cidx] else cond_a_finish)[cidx].append(fin)
        for u in uids:
            if result.timings[u].total_float <= 0:
                critical_counts[u] += 1

    branch_stats = _build_branch_stats(
        applied_branches,
        config.iterations,
        mpd,
        branch_fragnet_days,
        branch_fire_finish,
        branch_nofire_finish,
    )
    # disclose branches whose FS tie was absent (inert, never inserted) so they are never silent
    branch_stats += tuple(
        SSIBranchStat(
            id=b.id,
            name=b.name,
            probability=max(0.0, min(1.0, b.probability)),
            applied=False,
            hits=0,
            fired_fraction=0.0,
            mean_fragnet_days=0.0,
            mean_delta_days=0.0,
        )
        for b in active_branches
        if b.id not in fragnet_uids
    )

    conditional_stats = _build_conditional_stats(
        applied_conditionals, config.iterations, mpd, cond_a_finish, cond_b_finish
    )
    # disclose conditionals dropped for a missing monitor / plan tie (inert) so none is ever silent
    conditional_stats += tuple(
        SSIConditionalStat(
            id=c.id,
            name=c.name,
            monitor_uid=c.monitor_uid,
            metric=c.metric,
            threshold_minutes=c.threshold_minutes,
            trip_when=c.trip_when,
            applied=False,
            plan_a_name=c.plan_a.name or f"Plan {c.id}-A",
            plan_b_name=c.plan_b.name or f"Plan {c.id}-B",
            plan_a_hits=0,
            plan_b_hits=0,
            plan_a_fraction=0.0,
            plan_b_fraction=0.0,
            mean_a_finish_days=0.0,
            mean_b_finish_days=0.0,
            mean_delta_days=0.0,
        )
        for c in conditionals
        if c.id not in cond_plan_uids
    )

    return _build_ssi_result(
        schedule,
        config,
        finishes,
        active_risks,
        risk_occurred,
        mpd,
        ml_finish,
        anchor,
        prepared,
        critical_counts=critical_counts,
        branch_stats=branch_stats,
        conditional_stats=conditional_stats,
    )


def _latest_finish(tasks: Sequence[Task]) -> _dt.datetime | None:
    """The latest stored finish among ``tasks`` (the project completion), or ``None``."""
    stored = [t.finish for t in tasks if t.finish is not None]
    return max(stored) if stored else None


def stored_finish_correction(
    schedule: Schedule, target_uid: int | None, deterministic: int
) -> _dt.timedelta:
    """The constant date-axis correction the SSI result applies to every displayed date.

    Pure-CPM offsets pack completed work at the project start, so on a progressed schedule the
    naive conversion of the all-ML deterministic finish lands months before the STORED plan
    dates; ``_build_ssi_result`` realigns by the constant ``anchor - naive`` (the focus task's
    stored finish, else the latest stored finish — see the comment at the ``ml_finish`` solve).
    This additive helper exposes the SAME correction (same anchor selection, same naive
    conversion) so a caller converting OTHER offsets from the same run — the margin-sufficiency
    panel's zero-margin boundary E and threshold-percentile rows (audit F1, ADR-0256) — lands on
    the identical date axis as the result's own ``*_date`` fields (pinned by test). Zero when
    the schedule stores no finishes (an unprogressed pure-logic network needs no correction).
    """
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    focus = next((t for t in tasks if t.unique_id == target_uid), None)
    anchor = (
        focus.finish if focus is not None and focus.finish is not None else _latest_finish(tasks)
    )
    if anchor is None:
        return _dt.timedelta(0)
    naive = offset_to_datetime(schedule.project_start, max(deterministic, 0), schedule.calendar)
    return anchor - naive


def _build_ssi_result(
    schedule: Schedule,
    config: SRAConfig,
    finishes: Sequence[int],
    active_risks: Sequence[ScheduleRisk],
    risk_occurred: Sequence[Sequence[bool]],
    mpd: int,
    deterministic: int,
    anchor_date: _dt.datetime | None,
    prepared: PreparedCorrelation | None = None,
    critical_counts: Mapping[int, int] | None = None,
    branch_stats: tuple[SSIBranchStat, ...] = (),
    conditional_stats: tuple[SSIConditionalStat, ...] = (),
) -> SSIResult:
    n = len(finishes)
    sorted_f = sorted(finishes)
    sorted_ff = [float(x) for x in sorted_f]
    finishes_f = [float(x) for x in finishes]
    p10 = round(_percentile(sorted_ff, 10))
    p50 = round(_percentile(sorted_ff, 50))
    p80 = round(_percentile(sorted_ff, 80))
    p90 = round(_percentile(sorted_ff, 90))
    mean = statistics.fmean(finishes_f)
    std_days = (statistics.pstdev(finishes_f) / mpd) if n > 1 else 0.0
    det_pct = bisect.bisect_right(sorted_f, deterministic) / n
    cal = schedule.calendar
    ps = schedule.project_start
    # realign the pure-CPM date axis so the deterministic finish lands on the focus task's STORED
    # finish (completed work otherwise packs at the project start, shifting every date); a single
    # constant correction preserves the relative spacing of the distribution.
    naive_det = offset_to_datetime(ps, max(deterministic, 0), cal)
    correction = (anchor_date - naive_det) if anchor_date is not None else _dt.timedelta(0)

    def _cal_date(offset: float) -> _dt.date:
        return (offset_to_datetime(ps, max(round(offset), 0), cal) + correction).date()

    def iso(offset: float) -> str:
        return _cal_date(offset).isoformat()

    # the spread in CALENDAR days: std of the realigned finish dates (SSI/MS-Project report dates in
    # calendar days, the tool's std_days is working days — same distribution, different unit)
    std_cal_days = (
        round(statistics.pstdev([_cal_date(f).toordinal() for f in finishes_f]), 1)
        if n > 1
        else 0.0
    )

    rstats: list[SSIRiskStat] = []
    for risk, occ in zip(active_risks, risk_occurred, strict=True):
        on = [float(f) for f, o in zip(finishes, occ, strict=True) if o]
        off = [float(f) for f, o in zip(finishes, occ, strict=True) if not o]
        delta = (
            round((statistics.fmean(on) - statistics.fmean(off)) / mpd, 1) if on and off else 0.0
        )
        cons = (
            risk.consequence_rating
            if risk.consequence_rating is not None
            else _consequence_rating(risk.impact_days)
        )
        rstats.append(
            SSIRiskStat(
                id=risk.id,
                name=risk.name,
                probability=risk.probability,
                impact_days=risk.impact_days,
                hits=len(on),
                mean_delta_days=delta,
                probability_rating=_prob_rating(risk.probability),
                consequence_rating=cons,
            )
        )

    cdf = _build_cdf(sorted_f, n)
    histogram = _build_histogram(sorted_f)
    s_curve = tuple((iso(off), round(prob, 4)) for off, prob in cdf)
    finish_hist = tuple((iso((lo + hi) / 2.0), count) for lo, hi, count in histogram)
    # per-activity Criticality Index (ADR-0272): fraction of iterations the activity was critical,
    # ascending uid. Already tallied in the run loop; carried through instead of discarded.
    criticality = (
        tuple((uid, critical_counts[uid] / n) for uid in sorted(critical_counts))
        if critical_counts and n > 0
        else ()
    )
    return SSIResult(
        iterations=config.iterations,
        seed=config.seed,
        target_uid=config.target_uid,
        distribution=config.distribution,
        occurrence_mode=config.occurrence_mode,
        correlation=config.correlation,
        used_risks=bool(active_risks),
        deterministic_finish=deterministic,
        deterministic_percentile=det_pct,
        p10=p10,
        p50=p50,
        p80=p80,
        p90=p90,
        mean=mean,
        std_days=std_days,
        std_cal_days=std_cal_days,
        deterministic_finish_date=iso(deterministic),
        p10_date=iso(p10),
        p50_date=iso(p50),
        p80_date=iso(p80),
        p90_date=iso(p90),
        mean_date=iso(mean),
        cdf=cdf,
        histogram=histogram,
        s_curve=s_curve,
        finish_hist=finish_hist,
        risks=tuple(rstats),
        correlation_matrix_applied=prepared is not None,
        correlation_matrix_repaired=prepared.repaired if prepared is not None else False,
        correlation_min_eigenvalue=prepared.min_eig_raw if prepared is not None else 0.0,
        correlation_frobenius_distance=(
            prepared.frobenius_distance if prepared is not None else 0.0
        ),
        sampling=config.sampling,
        criticality=criticality,
        branches=branch_stats,
        conditionals=conditional_stats,
    )


def compute_oat_sensitivity(
    schedule: Schedule,
    *,
    three_point: Mapping[int, tuple[int, int, int]],
    target_uid: int | None = None,
    exclude_uids: frozenset[int] = frozenset(),
) -> tuple[OATSensitivity, ...]:
    """SSI's deterministic one-at-a-time sensitivity (NOT the Monte-Carlo Spearman tornado).

    Baseline = the focus finish with every activity at its ML (= remaining). For each activity that
    has a 3-point estimate (skipping ``exclude_uids`` — the risk-bearing tasks), re-solve the finish
    with just that activity forced to Best then Worst, and report the opportunity/risk day swing.
    Cost: 2*N ``compute_cpm`` solves — call it off the page-load path. Sorted by total desc."""
    tasks = sorted(non_summary(schedule), key=lambda t: t.unique_id)
    ml = {t.unique_id: _ml_minutes(t) for t in tasks}
    baseline = _finish_of(compute_cpm(schedule, duration_overrides=ml), target_uid)
    mpd = schedule.calendar.working_minutes_per_day or _MIN_PER_DAY
    out: list[OATSensitivity] = []
    for t in tasks:
        u = t.unique_id
        if u in exclude_uids or u not in three_point:
            continue
        bc, mlv, wc = three_point[u]
        f_bc = _finish_of(compute_cpm(schedule, duration_overrides={**ml, u: int(bc)}), target_uid)
        f_wc = _finish_of(compute_cpm(schedule, duration_overrides={**ml, u: int(wc)}), target_uid)
        opp = round((baseline - f_bc) / mpd, 1)
        risk = round((f_wc - baseline) / mpd, 1)
        out.append(
            OATSensitivity(
                unique_id=u,
                bc_minutes=int(bc),
                wc_minutes=int(wc),
                ml_minutes=int(mlv),
                event_finish_bc=f_bc,
                event_finish_wc=f_wc,
                opportunity_days=opp,
                risk_days=risk,
                total_days=round(opp + risk, 1),
            )
        )
    out.sort(key=lambda o: (-o.total_days, o.unique_id))
    return tuple(out)
