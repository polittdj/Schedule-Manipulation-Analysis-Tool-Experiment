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
import math
import random
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Finish-date histogram resolution (PDF bins over [min, max] of the simulated finishes).
_HISTOGRAM_BINS = 20


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
) -> SRAResult:
    """Run the seeded Monte-Carlo SRA and return the :class:`SRAResult`.

    ``cpm`` is the deterministic :func:`compute_cpm` result for ``schedule`` (its
    ``project_finish`` is the deterministic anchor compared against the simulated CDF).
    ``overrides`` is the manual 3-point path; un-overridden activities use the auto
    triangular default (ADR-0106). Each iteration ``i`` samples durations from
    ``random.Random(config.seed + i)`` (draws ordered by ``unique_id``) and recomputes the
    finish via ``compute_cpm(schedule, duration_overrides=...)`` — the same trusted solver,
    so the simulation cannot diverge from the gate-locked engine (Law 2).
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
    sampled_durations: dict[int, list[int]] = {uid: [] for uid in uids}
    critical_counts: dict[int, int] = dict.fromkeys(uids, 0)
    finishes: list[int] = []

    for i in range(config.iterations):
        rng = random.Random(config.seed + i)  # nosec B311 — simulation, not crypto
        overrides_i: dict[int, int] = {}
        for uid in uids:  # ascending unique_id order for reproducibility
            low, mode, high = three_point[uid]
            minutes = round(_sample_triangular(rng.random(), low, mode, high))
            minutes = max(minutes, 0)
            overrides_i[uid] = minutes
            sampled_durations[uid].append(minutes)
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
    )


def _build_result(
    schedule: Schedule,
    cpm: CPMResult,
    config: SRAConfig,
    auto_used: bool,
    tasks: Sequence[Task],
    sampled_durations: Mapping[int, list[int]],
    critical_counts: Mapping[int, int],
    finishes: Sequence[int],
) -> SRAResult:
    """Assemble the :class:`SRAResult` from the collected iteration series."""
    n = len(finishes)
    finishes_f = [float(f) for f in finishes]
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
        sensitivity = _spearman(durs_f, finishes_f)
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
