"""EVM indices + baseline-compliance / Half-Step-Delay metrics (Acumen §C, M8).

Two single-schedule metric families that read the schedule's *baseline* and *actual*
dates against the status (data) date — the Acumen "Advanced / Industry Standards"
baseline-compliance panel (`docs/PLAN/PARITY-TARGETS.md §C`) and the EVM performance
indices (`docs/PLAN/METRICS-CATALOG.md §3`):

* :func:`compute_baseline_compliance` — *Forecast to be Finished/Started*, *Completed/
  Started On Time / Late*, *Not Completed / Not Started*, and *Baseline Finish/Start
  Compliance* (BFC / BSC). Validated against the golden P2/P5 exports: every **count**
  is exact and BFC (33% / 20%) is exact. BSC carries a documented +3pt residual
  (started-on-time ÷ forecast-to-be-started = 38% / 23% vs Acumen's 41% / 25% — a
  denominator quirk, ADR-0013) tracked to M9; the underlying counts are exact.
* :func:`compute_evm_indices` — SPI / CPI / TCPI (cost-based; **NOT_APPLICABLE** when
  the schedule carries no cost, never fabricated as a 0), CEI (Current Execution Index,
  finish & start = BFC / BSC), and SPI(t) (count-based Earned Schedule). BEI and CPLI
  are the DCMA-14 ribbon's #14 / #13 (see :mod:`.dcma14`) and are not duplicated here.

The forensic Net Finish Impact (-99 days, P2→P5) is a *version-pair* metric and lives
in :mod:`.change_metrics`, not here.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    Direction,
    MetricResult,
    evaluate,
    non_summary,
    percent,
    to_offset,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def _ratio_result(metric_id: str, name: str, count: int, population: int) -> MetricResult:
    """A percentage metric with no published pass/fail threshold (informational)."""
    return MetricResult(
        metric_id,
        name,
        count,
        population,
        round(percent(count, population), 1),
        "%",
        CheckStatus.NOT_APPLICABLE,
    )


def compute_baseline_compliance(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """Acumen §C baseline-compliance / Half-Step-Delay panel for one schedule.

    Population is the schedulable (non-summary) activities — the same denominator as the
    DCMA-14 ribbon and the Schedule-Quality summary. "Forecast to be Finished/Started"
    are the activities the **baseline** placed on/before the status date (the validated
    Acumen formula uses the baseline, not the live forecast — `PARITY-TARGETS.md §C`).
    """
    # Acumen measures baseline compliance over NORMAL activities only — milestones are excluded
    # (Bible inclusions: Milestone=false) — with strict "due" (baseline < now) and INT (date-only)
    # comparisons, validated against Acumen's report on the Large Test File (ADR-0083).
    tasks = [t for t in non_summary(schedule) if not t.is_milestone]
    n = len(tasks)
    status = schedule.status_date
    out: dict[str, MetricResult] = {}

    if status is None:
        # Without a data date the panel is undefined — never fabricate counts.
        for mid, nm in (
            ("forecast_to_be_finished", "Forecast to be Finished"),
            ("completed_on_time", "Completed On Time"),
            ("completed_late", "Completed Late"),
            ("not_completed", "Not Completed"),
            ("baseline_finish_compliance", "Baseline Finish Compliance"),
            ("forecast_to_be_started", "Forecast to be Started"),
            ("started_on_time", "Started On Time"),
            ("started_late", "Started Late"),
            ("not_started", "Not Started"),
            ("baseline_start_compliance", "Baseline Start Compliance"),
        ):
            out[mid] = MetricResult(mid, nm, 0, n, 0.0, "%", CheckStatus.NOT_APPLICABLE)
        return out

    def before(when: dt.datetime | None) -> bool:
        return when is not None and when < status

    # ---- finish side (Finish basis; INT date comparisons per the Bible formulas) ----
    fin_due = [t for t in tasks if before(t.baseline_finish)]
    # "Finish < now" — the activity has actually finished by the data date.
    finished = [t for t in fin_due if t.actual_finish is not None and t.actual_finish < status]
    on_time = [
        t
        for t in finished
        if t.actual_finish is not None
        and t.baseline_finish is not None
        and t.actual_finish.date() <= t.baseline_finish.date()
    ]
    late = [
        t
        for t in finished
        if t.actual_finish is not None
        and t.baseline_finish is not None
        and t.actual_finish.date() > t.baseline_finish.date()
    ]
    not_completed = [t for t in fin_due if t.percent_complete < 100.0]
    n_fin = len(fin_due)

    out["forecast_to_be_finished"] = _ratio_result(
        "forecast_to_be_finished", "Forecast to be Finished", n_fin, n
    )
    out["completed_on_time"] = _offender_ratio(
        "completed_on_time", "Completed On Time", on_time, n_fin
    )
    out["completed_late"] = _offender_ratio("completed_late", "Completed Late", late, n_fin)
    out["not_completed"] = _offender_ratio("not_completed", "Not Completed", not_completed, n_fin)
    out["baseline_finish_compliance"] = _ratio_result(
        "baseline_finish_compliance", "Baseline Finish Compliance", len(on_time), n_fin
    )

    # ---- start side ----
    start_due = [t for t in tasks if before(t.baseline_start)]
    started = [t for t in start_due if t.actual_start is not None and t.actual_start < status]
    s_on_time = [
        t
        for t in started
        if t.actual_start is not None
        and t.baseline_start is not None
        and t.actual_start.date() <= t.baseline_start.date()
    ]
    s_late = [
        t
        for t in started
        if t.actual_start is not None
        and t.baseline_start is not None
        and t.actual_start.date() > t.baseline_start.date()
    ]
    not_started = [t for t in start_due if t.actual_start is None]
    n_start = len(start_due)
    # Baseline Start Compliance — Acumen's Half-Step-Delay definition compares the actual START to
    # the baseline FINISH (not baseline start): the activity started before the baseline said it
    # would finish. This is asymmetric with Baseline Finish Compliance and is why a naive
    # start≤baseline-start ratio under-reports (the ADR-0013 residual). Validated 41/25 on the
    # goldens (== Acumen, residual resolved) and 22% on the Large Test File (ADR-0083).
    bsc_compliant = [
        t
        for t in started
        if t.actual_start is not None
        and t.baseline_finish is not None
        and t.actual_start.date() <= t.baseline_finish.date()
    ]

    out["forecast_to_be_started"] = _ratio_result(
        "forecast_to_be_started", "Forecast to be Started", n_start, n
    )
    out["started_on_time"] = _offender_ratio(
        "started_on_time", "Started On Time", s_on_time, n_start
    )
    out["started_late"] = _offender_ratio("started_late", "Started Late", s_late, n_start)
    out["not_started"] = _offender_ratio("not_started", "Not Started", not_started, n_start)
    out["baseline_start_compliance"] = _ratio_result(
        "baseline_start_compliance", "Baseline Start Compliance", len(bsc_compliant), n_start
    )
    return out


def _offender_ratio(metric_id: str, name: str, tasks: list[Task], population: int) -> MetricResult:
    """Percentage metric whose offenders are the citable activities behind the count."""
    uids = tuple(sorted(t.unique_id for t in tasks))
    return MetricResult(
        metric_id,
        name,
        len(uids),
        population,
        round(percent(len(uids), population), 1),
        "%",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=uids,
    )


def _na_index(metric_id: str, name: str) -> MetricResult:
    """A cost-based EVM index with no cost in the schedule — NA, never a fabricated 0."""
    return MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)


def compute_evm_indices(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """EVM performance indices for one schedule (`METRICS-CATALOG.md §3`).

    Cost-based indices (SPI, CPI, TCPI) are **NOT_APPLICABLE** unless the schedule is
    cost-loaded — the golden P2/P5 schedules are not, so they report NA rather than a
    fabricated value (Law 2). CEI(finish)/CEI(start) are the baseline-compliance ratios;
    SPI(t) is a count-based Earned-Schedule index derived from the baseline finish curve.
    """
    out: dict[str, MetricResult] = {}
    tasks = non_summary(schedule)
    total_budget = sum(t.budgeted_cost for t in tasks)

    if total_budget > 0:
        bcwp = sum(t.budgeted_cost * (t.percent_complete / 100.0) for t in tasks)
        bcws = _planned_value(schedule, tasks)
        acwp = sum(t.actual_cost or 0.0 for t in tasks)
        out["spi"] = _index("spi", "SPI", bcwp / bcws if bcws else None, 1.0)
        out["cpi"] = _index("cpi", "CPI", bcwp / acwp if acwp else None, 1.0)
        tcpi_denom = total_budget - acwp
        out["tcpi"] = _index(
            "tcpi", "TCPI", (total_budget - bcwp) / tcpi_denom if tcpi_denom else None, 1.0
        )
    else:
        out["spi"] = _na_index("spi", "SPI")
        out["cpi"] = _na_index("cpi", "CPI")
        out["tcpi"] = _na_index("tcpi", "TCPI")

    compliance = compute_baseline_compliance(schedule, cpm_result)
    out["cei_finish"] = _ratio_result(
        "cei_finish",
        "CEI (Finish)",
        compliance["completed_on_time"].count,
        compliance["forecast_to_be_finished"].count,
    )
    # CEI (Start) == Acumen's "Started On Time" % (actual start <= baseline START / forecast). This
    # is DISTINCT from Baseline Start Compliance, whose Half-Step-Delay numerator compares the start
    # to the baseline FINISH (ADR-0083) — so cei_start (38/23) and BSC (41/25) legitimately differ.
    out["cei_start"] = _ratio_result(
        "cei_start",
        "CEI (Start)",
        compliance["started_on_time"].count,
        compliance["forecast_to_be_started"].count,
    )
    out["spi_t"] = _spi_t(schedule, tasks)
    return out


def _planned_value(schedule: Schedule, tasks: list[Task]) -> float:
    """Cost-loaded BCWS: budget of activities the baseline placed on/before status."""
    status = schedule.status_date
    if status is None:
        return 0.0
    return sum(
        t.budgeted_cost
        for t in tasks
        if t.baseline_finish is not None and t.baseline_finish <= status
    )


def _index(metric_id: str, name: str, value: float | None, threshold: float) -> MetricResult:
    """Build an EVM index result; NA when the denominator was absent."""
    if value is None:
        return _na_index(metric_id, name)
    return MetricResult(
        metric_id,
        name,
        0,
        1,
        round(value, 2),
        "ratio",
        evaluate(value, threshold, Direction.GE),
        threshold,
        Direction.GE,
    )


@dataclass(frozen=True)
class EarnedSchedule:
    """The numeric core of a count-based Earned-Schedule SPI(t) calculation.

    ``es_minutes`` is the working-time offset of the EV-th planned (baseline) finish;
    ``at_minutes`` is the working time from project start to the status date; ``ev`` is
    the count of complete activities; ``planned_count`` the activities with a usable
    baseline finish. SPI(t) = ES / AT (< 1 == behind schedule).
    """

    es_minutes: float
    at_minutes: float
    ev: int
    planned_count: int

    @property
    def spi_t(self) -> float:
        return self.es_minutes / self.at_minutes


def earned_schedule(schedule: Schedule, tasks: Sequence[Task]) -> EarnedSchedule | None:
    """Earned-Schedule inputs for ``tasks``, or ``None`` when undefined (never fabricated).

    Shared by the schedule-level SPI(t) (:func:`compute_evm_indices`) and the per-WBS
    Earned-Schedule breakdown (``metrics/wbs_breakdown.py``). ES is a step function over
    the sorted baseline-finish offsets (count-based — no fractional earned schedule),
    capped at the last planned finish. Undefined (returns ``None``) when there is no
    positive status offset, no completions, or no planned baseline finishes.
    """
    status_off = to_offset(schedule, schedule.status_date)
    if status_off is None or status_off <= 0:
        return None
    planned = sorted(
        off
        for t in tasks
        if (off := to_offset(schedule, t.baseline_finish)) is not None and off >= 0
    )
    ev = sum(1 for t in tasks if t.percent_complete >= 100.0)
    if ev <= 0 or not planned:
        return None
    # ES is the offset of the EV-th planned finish (1-indexed), capped at the last one.
    es = float(planned[min(ev, len(planned)) - 1])
    return EarnedSchedule(
        es_minutes=es, at_minutes=float(status_off), ev=ev, planned_count=len(planned)
    )


def _spi_t(schedule: Schedule, tasks: list[Task]) -> MetricResult:
    """Count-based Earned-Schedule SPI(t) = Earned Schedule / Actual Time.

    Earned value (EV) = activities complete by the status date. Earned Schedule (ES) =
    the working-time offset of the EV-th planned (baseline) finish — a step function over
    the sorted baseline-finish offsets, not interpolated (this is a count-based index with
    no fractional earned schedule). SPI(t) = ES / AT, with AT = working time from project
    start to the status date. < 1 == behind schedule. No Acumen golden target exists for
    this index (informational; the golden schedules are not cost-loaded so the cost SPI is
    NA) — it is unit-tested on synthetic data.
    """
    es = earned_schedule(schedule, tasks)
    if es is None:
        return _na_index("spi_t", "SPI(t)")
    return MetricResult(
        "spi_t",
        "SPI(t)",
        es.ev,
        es.planned_count,
        round(es.spi_t, 2),
        "ratio",
        evaluate(es.spi_t, 1.0, Direction.GE),
        1.0,
        Direction.GE,
    )


# --------------------------------------------------------------------------------------
# Schedule variance in TIME (handbook §7.3.3.1 — SVt; Figs 7-12/7-13) — parity-isolated.
# Lightweight dataclasses (NOT MetricResult), kept out of the metric-dictionary coverage
# test and the Fuse ribbon, exactly like health_extra / logic_integrity / margin.
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivityVariance:
    """One completed activity's schedule variance in working days (actual - baseline finish)."""

    unique_id: int
    variance_days: float  # positive == finished LATER than the baseline (unfavorable)


@dataclass(frozen=True)
class ScheduleVariance:
    """Schedule variance in **time** (working days) — the handbook §7.3.3.1 view.

    ``svt_days`` is the project-level Earned-Schedule time variance ``(ES - AT)`` in working
    days (``>= 0`` ahead of plan / favorable, ``< 0`` behind / unfavorable); ``None`` when ES is
    undefined (no status date, no completions, or no baseline finishes). ``es_days`` / ``at_days``
    are its components. The per-activity block is the count of completed activities carrying both
    an actual and a baseline finish, their mean finish variance, and the latest finishers.
    """

    svt_days: float | None
    es_days: float | None
    at_days: float | None
    completed: int
    mean_activity_variance_days: float | None
    worst: tuple[ActivityVariance, ...]
    #: Per-activity START variance (actual_start minus baseline_start, working days) for every task
    #: that has STARTED and carries a baseline start — surfaces in-progress slippage on a file
    #: that has been statused but has few completions (operator 2026-07-08). Same sign convention
    #: (positive = started later than planned / unfavorable).
    started: int = 0
    mean_start_variance_days: float | None = None
    worst_start: tuple[ActivityVariance, ...] = ()
    #: How many non-summary tasks carry a baseline finish (so the panel can distinguish "no
    #: baseline at all" from "baselined plan, no progress statused yet").
    baselined: int = 0


def compute_schedule_variance(
    schedule: Schedule, tasks: Sequence[Task], *, worst_cap: int = 15
) -> ScheduleVariance:
    """Schedule variance in time for ``tasks`` (project SVt = ES - AT; per-activity finish slip).

    SVt reuses the canonical :func:`earned_schedule` (so it can never diverge from SPI(t)).
    Per-activity variance is the working-time difference between an activity's actual and baseline
    finish on the schedule calendar, in working days; positive means it finished later than planned.
    Both are parity-isolated (returned as plain dataclasses, never a ``MetricResult``).
    """
    wmpd = schedule.calendar.working_minutes_per_day or 480
    es = earned_schedule(schedule, tasks)
    if es is None:
        svt_days = es_days = at_days = None
    else:
        svt_days = round((es.es_minutes - es.at_minutes) / wmpd, 1)
        es_days = round(es.es_minutes / wmpd, 1)
        at_days = round(es.at_minutes / wmpd, 1)

    variances: list[ActivityVariance] = []
    start_variances: list[ActivityVariance] = []
    baselined = 0
    for t in tasks:
        if to_offset(schedule, t.baseline_finish) is not None:
            baselined += 1
        actual = to_offset(schedule, t.actual_finish)
        baseline = to_offset(schedule, t.baseline_finish)
        if actual is not None and baseline is not None:
            var_days = round((actual - baseline) / wmpd, 1)
            variances.append(ActivityVariance(unique_id=t.unique_id, variance_days=var_days))
        # START variance: any activity that has actually started + carries a baseline start —
        # so a statused-but-mostly-unfinished schedule still shows its in-progress slippage.
        a_start = to_offset(schedule, t.actual_start)
        b_start = to_offset(schedule, t.baseline_start)
        if a_start is not None and b_start is not None:
            sv_days = round((a_start - b_start) / wmpd, 1)
            start_variances.append(ActivityVariance(unique_id=t.unique_id, variance_days=sv_days))
    completed = len(variances)
    started = len(start_variances)
    mean_var = round(sum(v.variance_days for v in variances) / completed, 1) if completed else None
    mean_start = (
        round(sum(v.variance_days for v in start_variances) / started, 1) if started else None
    )
    # the latest finishers / starters first (largest positive variance), capped for the UI
    worst = tuple(sorted(variances, key=lambda v: v.variance_days, reverse=True)[:worst_cap])
    worst_start = tuple(
        sorted(start_variances, key=lambda v: v.variance_days, reverse=True)[:worst_cap]
    )
    return ScheduleVariance(
        svt_days=svt_days,
        es_days=es_days,
        at_days=at_days,
        completed=completed,
        mean_activity_variance_days=mean_var,
        worst=worst,
        started=started,
        mean_start_variance_days=mean_start,
        worst_start=worst_start,
        baselined=baselined,
    )
