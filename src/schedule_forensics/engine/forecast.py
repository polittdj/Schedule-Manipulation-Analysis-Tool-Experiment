"""Finish-date forecasting — independent answers to "when will it really end?" (M15).

The reference Power BI deck's forecasting page triangulates the project end date with
**methods side by side** so an analyst can see whether logic, the source schedule,
throughput, and performance agree (a divergence is itself a finding):

1. **Schedule logic (CPM)** — the network's own computed finish (the date the plan
   claims, given its logic, durations, and calendar). This is the engine's *pure-logic*
   finish; it does NOT floor in-progress remaining work at the data date, so on an
   out-of-sequence / progressed schedule it can read *earlier* than the source tool's
   progress-aware finish (the standing ADR-0108 gap; audit F-02).
2. **As-scheduled (stored dates)** — the latest *stored* finish the source tool wrote
   into the file (its progress-aware forecast). Surfaced alongside the CPM finish so a
   disagreement between the two (e.g. TP4 v5: stored 2026-07-17 vs CPM 2026-06-26) is
   visible to the analyst rather than hidden. ``None`` if the file carries no dates.
3. **Completion-rate extrapolation** — the throughput answer: at the historical pace of
   *activities actually completed per month*, how long do the to-go activities take?
4. **Earned-schedule IEAC(t)** — the performance answer: the standard Earned-Schedule
   estimate ``IEAC(t) = AT + (PD - ES) / SPI(t)`` on the working-time axis (the same ES
   machinery as the SPI(t) metric).

The reference deck's DAX is not extractable (XPress9-compressed DataModel); these are
the documented reconstructions (ADR-0030). A method whose inputs are missing reports
**no date** (never fabricated): rate needs a status date + completions, IEAC(t) needs
baselines + a positive SPI(t). Everything cites the finish-controlling activities (§6).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import is_incomplete, non_summary, to_offset
from schedule_forensics.engine.metrics.evm import earned_schedule
from schedule_forensics.model.schedule import Schedule

#: Average calendar days per month (365.25 / 12) — the rate method's month axis.
_DAYS_PER_MONTH = 365.25 / 12


@dataclass(frozen=True)
class FinishForecast:
    """One method's answer: the forecast finish date and the basis it was computed from."""

    method_id: str  # "cpm" | "as_scheduled" | "rate" | "earned_schedule"
    name: str
    finish: dt.date | None  # None == inputs missing; never a fabricated date
    basis: str  # plain-language inputs (figures inline, verifiable)


@dataclass(frozen=True)
class ForecastSet:
    """The method forecasts plus the shared inputs the page shows alongside them."""

    as_of: dt.date | None  # the status (data) date the forecasts run from
    completed_count: int
    remaining_count: int  # incomplete (to-go) activities
    rate_per_month: float | None  # historical completions per calendar month
    spi_t: float | None
    planned_finish: dt.date | None  # latest baseline finish (the PD anchor)
    forecasts: tuple[FinishForecast, ...]
    citation_uids: tuple[int, ...]  # the finish-controlling activities (§6 anchor)


def compute_finish_forecasts(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> ForecastSet:
    """The three-method finish forecast for one schedule (see module docstring)."""
    cpm = cpm_result if cpm_result is not None else compute_cpm(schedule)
    tasks = non_summary(schedule)
    status = schedule.status_date
    completed = [t for t in tasks if not is_incomplete(t)]
    remaining = [t for t in tasks if is_incomplete(t)]

    cpm_finish = offset_to_datetime(
        schedule.project_start, cpm.project_finish, schedule.calendar
    ).date()
    forecasts: list[FinishForecast] = [
        FinishForecast(
            "cpm",
            "Schedule logic (CPM)",
            cpm_finish,
            f"the network's pure-logic computed finish over {len(tasks)} activities",
        )
    ]

    # --- as-scheduled: the source tool's stored (progress-aware) finish ----------------
    # Pure-logic CPM does not floor in-progress remaining work at the data date (ADR-0108),
    # so it can understate a slip; the latest STORED finish is the source tool's
    # progress-aware answer. Surfacing both makes the disagreement visible (audit F-02).
    stored_finishes = [t.finish for t in tasks if t.finish is not None]
    as_scheduled = max(stored_finishes).date() if stored_finishes else None
    as_basis = (
        "the latest finish stored in the source file (its progress-aware forecast); may "
        "exceed the pure-logic CPM finish on out-of-sequence / in-progress schedules (ADR-0108)"
        if as_scheduled is not None
        else "the file carries no stored finish dates"
    )
    forecasts.append(
        FinishForecast("as_scheduled", "As-scheduled (stored dates)", as_scheduled, as_basis)
    )

    # --- completion-rate extrapolation -------------------------------------------------
    rate: float | None = None
    rate_finish: dt.date | None = None
    rate_basis = "needs a status date and at least one completed activity"
    if status is not None and completed:
        elapsed_months = (status.date() - schedule.project_start.date()).days / _DAYS_PER_MONTH
        if elapsed_months > 0:
            rate = len(completed) / elapsed_months
            months_to_go = len(remaining) / rate if rate > 0 else None
            if months_to_go is not None:
                rate_finish = status.date() + dt.timedelta(
                    days=round(months_to_go * _DAYS_PER_MONTH)
                )
                rate_basis = (
                    f"{len(completed)} completed over {elapsed_months:.1f} months "
                    f"({rate:.1f}/month) -> {len(remaining)} to go"
                )
    forecasts.append(
        FinishForecast("rate", "Completion-rate extrapolation", rate_finish, rate_basis)
    )

    # --- earned-schedule IEAC(t) --------------------------------------------------------
    spi_t, es, at = _earned_schedule(schedule)
    planned_offsets = [
        off for t in tasks if (off := to_offset(schedule, t.baseline_finish)) is not None
    ]
    planned_finish: dt.date | None = None
    es_finish: dt.date | None = None
    es_basis = "needs a status date, baselines, and completed work (SPI(t) > 0)"
    if planned_offsets:
        pd_off = max(planned_offsets)
        planned_finish = offset_to_datetime(
            schedule.project_start, pd_off, schedule.calendar
        ).date()
        if spi_t is not None and spi_t > 0 and es is not None and at is not None:
            # the forecast divides by the EXACT ratio; only the displayed SPI(t) rounds
            # (a 2-decimal SPI(t) shifted the golden P5 forecast by 9 days)
            ieac_off = round(at + max(0.0, pd_off - es) / (es / at))
            es_finish = offset_to_datetime(
                schedule.project_start, ieac_off, schedule.calendar
            ).date()
            es_basis = f"IEAC(t) = AT + (PD - ES) / SPI(t) with SPI(t) {spi_t:.2f}"
    forecasts.append(
        FinishForecast("earned_schedule", "Earned-schedule IEAC(t)", es_finish, es_basis)
    )

    by_id = schedule.tasks_by_id
    drivers = tuple(
        uid
        for uid, t in sorted(cpm.timings.items())
        if t.early_finish == cpm.project_finish and uid in by_id
    ) or tuple(t.unique_id for t in schedule.tasks[:3])
    return ForecastSet(
        as_of=status.date() if status is not None else None,
        completed_count=len(completed),
        remaining_count=len(remaining),
        rate_per_month=round(rate, 2) if rate is not None else None,
        spi_t=round(spi_t, 2) if spi_t is not None else None,
        planned_finish=planned_finish,
        forecasts=tuple(forecasts),
        citation_uids=drivers,
    )


@dataclass(frozen=True)
class CarnacSummary:
    """The deck's *Carnac* forecast KPI cards for one version (PBIX page 13; ADR-0042).

    Ten headline figures over the latest schedule, every one reused from the CPM and the
    three-method :class:`ForecastSet` (no new forecasting math). A figure whose inputs are
    missing reads ``None`` (the view shows "—") — never a fabricated value.
    """

    earliest_start: dt.date | None  # earliest activity start
    latest_finish: dt.date  # the CPM computed finish
    project_duration_days: float | None  # working days, earliest start -> CPM finish
    forecasted_end: dt.date | None  # completion-rate extrapolation finish
    estimated_end_es: dt.date | None  # earned-schedule IEAC(t) finish
    avg_tasks_per_month: float | None  # historical completion rate
    remaining_duration_days: float | None  # working days, data date -> CPM finish (to-go span)
    spi_t: float | None  # count-based Earned-Schedule SPI(t) (the deck's "SPI 2")
    earned_schedule_days: float | None  # Earned Schedule in working days
    to_go_count: int  # activities still to complete (the deck's "Tasks Completion Forecast")


def compute_carnac_summary(
    schedule: Schedule, cpm: CPMResult, forecasts: ForecastSet
) -> CarnacSummary:
    """The Carnac KPI cards for one version, derived from the CPM + the forecast set.

    Pulls the method finishes from ``forecasts`` (CPM / as-scheduled / rate / earned-schedule) and
    computes the deck's remaining card values — earliest start, project + remaining
    duration (working days), and Earned Schedule in working days — from the stored dates
    and the same count-based Earned-Schedule construction as SPI(t). Nothing is recomputed
    that the forecast set already holds."""
    tasks = non_summary(schedule)
    per_day = schedule.calendar.working_minutes_per_day or 1
    cal, ps = schedule.calendar, schedule.project_start

    by_method = {f.method_id: f.finish for f in forecasts.forecasts}
    latest_finish = offset_to_datetime(ps, cpm.project_finish, cal).date()

    start_offsets = [off for t in tasks if (off := to_offset(schedule, t.start)) is not None]
    earliest_start: dt.date | None = None
    project_duration_days: float | None = None
    if start_offsets:
        lo = min(start_offsets)
        earliest_start = offset_to_datetime(ps, max(lo, 0), cal).date()
        project_duration_days = round(max(0, cpm.project_finish - lo) / per_day, 1)

    remaining_duration_days: float | None = None
    status_off = to_offset(schedule, schedule.status_date)
    if status_off is not None:
        remaining_duration_days = round(max(0, cpm.project_finish - status_off) / per_day, 1)

    es = earned_schedule(schedule, tasks)
    earned_schedule_days = round(es.es_minutes / per_day, 1) if es is not None else None

    return CarnacSummary(
        earliest_start=earliest_start,
        latest_finish=latest_finish,
        project_duration_days=project_duration_days,
        forecasted_end=by_method.get("rate"),
        estimated_end_es=by_method.get("earned_schedule"),
        avg_tasks_per_month=forecasts.rate_per_month,
        remaining_duration_days=remaining_duration_days,
        spi_t=forecasts.spi_t,
        earned_schedule_days=earned_schedule_days,
        to_go_count=forecasts.remaining_count,
    )


@dataclass(frozen=True)
class EstimatedGroupForecast:
    """A no-direct-history group's ESTIMATED finish (ADR-0189) — quantified, never silent.

    Operator 2026-07-10: groups with remaining work but no completion history must still be
    forecast, "even if you have to make some logical estimations and quantify them and note
    them using best industry practices and statistical analysis best practices." The method
    is standard partial pooling / credibility weighting (Bühlmann credibility, the
    empirical-Bayes shrinkage family): with ZERO group observations the credibility weight on
    the group's own history is Z = n/(n+k) = 0, so the estimate is the POOLED (project-wide)
    per-activity throughput — then adjusted by the group's OWN observed leading indicator
    (the start execution index, the NDIA PASEG-style start-anchored twin of BEI: work must
    start before it can finish, so demonstrated late starting discounts the borrowed rate;
    the adjustment only ever penalizes — undemonstrated speed is never credited). The
    uncertainty band is reference-class forecasting (Flyvbjerg's outside view): the P25/P75
    per-activity rates observed across the groups that DO have history bound the late/early
    finishes. Every figure carries this provenance in ``basis``.
    """

    group: str
    to_go: int
    sei: float | None  # the group's start execution index (the leading indicator used)
    pooled_rate_per_month: float  # borrowed per-group rate BEFORE the SEI adjustment
    adjustment: float  # min(1, SEI) floored at 0.25 — the applied discount (1.0 = none)
    finish: dt.date  # point estimate: to-go ÷ (pooled rate x adjustment)
    finish_early: dt.date | None  # reference-class P75 rate (needs ≥2 history groups)
    finish_late: dt.date | None  # reference-class P25 rate (needs ≥2 history groups)
    basis: str  # the quantified estimation statement, shown verbatim in the UI


@dataclass(frozen=True)
class GroupRollup:
    """The project forecast RECALCULATED bottom-up from per-group data points (ADR-0188/0189).

    Operator 2026-07-10: when the Forecast page groups the execution metrics by a field, the
    per-group figures should roll BACK UP into a project-level forecast — the group data
    points, weighted, re-answering "when will it really end?". Recalculations, coverage
    always disclosed:

    - **Group-weighted IEAC(t)** — each group's EXACT Earned-Schedule SPI(t) (the same
      count-based machinery as the top-down forecast) weighted by the group's TO-GO activity
      count, then the standard ``IEAC(t) = AT + (PD - ES) / SPI(t)`` re-run with the weighted
      index. Two coverages are reported: ``weighted_spi_t``/``ieac_finish`` over the DIRECTLY
      measured groups only, and ``weighted_spi_t_all``/``ieac_finish_all`` where no-history
      groups additionally contribute a credibility-weighted estimate (pooled exact SPI(t) x
      their start-index adjustment — ADR-0189, see :class:`EstimatedGroupForecast`).
    - **Bottleneck completion-rate finish** — each group's own throughput (completions per
      month) extrapolates ITS to-go count; no-history groups use their ESTIMATED rate; the
      project rolls up as the LATEST group finish (a project is done when its slowest group
      is done), flagged when the bottleneck comes from an estimated group.
    - ``unforecastable`` now holds ONLY the truly impossible cases: no data date, or a file
      with no completions anywhere (nothing to borrow from) — disclosed, never imputed.
    """

    field: str
    weight_basis: str  # plain-language weighting statement (shown verbatim in the UI)
    groups_total: int  # groups with any to-go work
    groups_used: int  # of those, groups contributing a DIRECT SPI(t) to the weighted index
    total_to_go: int
    covered_to_go: int  # to-go activities inside the directly-measured groups
    weighted_spi_t: float | None  # direct groups only
    weighted_spi_t_all: float | None  # direct + credibility-estimated groups (full coverage)
    ieac_finish: dt.date | None  # IEAC(t) with the direct-only weighted SPI(t)
    ieac_finish_all: dt.date | None  # IEAC(t) with the full-coverage weighted SPI(t)
    rate_finish: dt.date | None  # the bottleneck (latest) per-group rate extrapolation
    rate_limiting_group: str | None  # the group that sets the bottleneck finish
    rate_finish_is_estimated: bool  # the bottleneck comes from an ESTIMATED group
    estimated: tuple[EstimatedGroupForecast, ...]  # the quantified no-history estimates
    unforecastable: tuple[str, ...]  # only the truly impossible (see class docstring)


#: The floor on the start-index discount for estimated groups: a near-zero SEI must slow
#: the borrowed rate, not stretch the forecast toward infinity (disclosed in the basis).
_EST_ADJ_FLOOR = 0.25


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile of an ascending list (q in [0, 1])."""
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def compute_group_rollup(schedule: Schedule, field: str) -> GroupRollup | None:
    """Recalculate the project forecast from ``field``'s group data points (see GroupRollup).

    Returns ``None`` when the field yields no groups. Figures whose inputs are missing read
    ``None`` inside the rollup — direct measures are never fabricated, and the ADR-0189
    no-history estimates are explicitly quantified and labeled (see
    :class:`EstimatedGroupForecast`)."""
    # late import: field_forecast imports metrics that import this module's neighbors
    from schedule_forensics.engine.metrics.field_forecast import _groups, _sei, _sub_schedule

    groups = _groups(schedule, field)
    if not groups:
        return None
    status = schedule.status_date

    # (name, activities, completed, to_go, exact spi | None, sei | None)
    per_group: list[tuple[str, int, int, int, float | None, float | None]] = []
    for name, uids in sorted(groups.items()):
        sub = _sub_schedule(schedule, uids)
        tasks = non_summary(sub)
        completed = sum(1 for t in tasks if t.percent_complete >= 100.0)
        to_go = len(tasks) - completed
        es_g = earned_schedule(sub, tasks)
        # the EXACT ratio (es/at), not the 2-dp display value — same rule as IEAC(t) itself
        spi_g = (es_g.es_minutes / es_g.at_minutes) if es_g and es_g.at_minutes else None
        per_group.append((name, len(tasks), completed, to_go, spi_g, _sei(sub)))

    active = [g for g in per_group if g[3] > 0]
    total_to_go = sum(g[3] for g in active)
    direct = [g for g in active if g[2] > 0 and g[4] is not None and g[4] > 0]
    covered_to_go = sum(g[3] for g in direct)
    weighted_spi: float | None = None
    if covered_to_go > 0:
        weighted_spi = sum(g[4] * g[3] for g in direct if g[4] is not None) / covered_to_go

    # ---- shared pooled bases (the credibility Z=0 priors — ADR-0189) -------------------
    elapsed_months: float | None = None
    if status is not None:
        em = (status.date() - schedule.project_start.date()).days / _DAYS_PER_MONTH
        elapsed_months = em if em > 0 else None
    all_tasks = non_summary(schedule)
    total_activities = len(all_tasks)
    total_completed = sum(1 for t in all_tasks if t.percent_complete >= 100.0)
    pooled_per_activity_rate: float | None = None  # completions / (month x activity)
    if elapsed_months is not None and total_completed > 0 and total_activities > 0:
        pooled_per_activity_rate = total_completed / (elapsed_months * total_activities)
    exact_pooled_spi, es_all, at_all = _earned_schedule(schedule)
    pooled_spi = (es_all / at_all) if es_all is not None and at_all else None
    # reference class (Flyvbjerg's outside view): the per-activity rates the groups WITH
    # history actually demonstrated, bounding the estimates' late/early range
    history_rates = sorted(
        g[2] / (elapsed_months * g[1])
        for g in per_group
        if elapsed_months is not None and g[2] > 0 and g[1] > 0
    )
    del exact_pooled_spi  # display value; the exact ratio above is what the math uses

    # ---- per-group rate finishes: direct where demonstrated, estimated where not -------
    rate_finish: dt.date | None = None
    rate_limiting: str | None = None
    rate_is_estimated = False
    estimated: list[EstimatedGroupForecast] = []
    unforecastable: list[str] = []
    spi_terms_all: list[tuple[float, int]] = [(g[4], g[3]) for g in direct if g[4] is not None]

    def month_finish(months_to_go: float) -> dt.date:
        # callers gate on elapsed_months, which implies a status date; the fallback keeps
        # the type-checker honest without an assert (bandit B101)
        anchor = status.date() if status is not None else schedule.project_start.date()
        return anchor + dt.timedelta(days=round(months_to_go * _DAYS_PER_MONTH))

    for name, activities, completed, to_go, _spi_g, sei_g in active:
        finish_g: dt.date | None = None
        is_est = False
        if elapsed_months is not None and completed > 0:
            rate_g = completed / elapsed_months
            finish_g = month_finish(to_go / rate_g)
        elif elapsed_months is not None and pooled_per_activity_rate is not None:
            # ADR-0189 estimate: partial pooling (credibility Z = n/(n+k) = 0 with zero
            # group completions → the pooled per-activity rate), discounted by the group's
            # own demonstrated start index (penalize-only, floored — undemonstrated speed
            # is never credited), ranged by the reference class of history groups.
            is_est = True
            adjustment = 1.0 if sei_g is None else max(_EST_ADJ_FLOOR, min(1.0, sei_g))
            pooled_rate_g = pooled_per_activity_rate * activities
            est_rate = pooled_rate_g * adjustment
            finish_g = month_finish(to_go / est_rate)
            early: dt.date | None = None
            late: dt.date | None = None
            if len(history_rates) >= 2:
                hi_rate = _percentile(history_rates, 0.75) * activities * adjustment
                lo_rate = _percentile(history_rates, 0.25) * activities * adjustment
                if hi_rate > 0:
                    early = month_finish(to_go / hi_rate)
                if lo_rate > 0:
                    late = month_finish(to_go / lo_rate)
            sei_note = (
                f"discounted by its start execution index {sei_g:.2f} "
                f"(applied {adjustment:.2f}, floor {_EST_ADJ_FLOOR})"
                if sei_g is not None
                else "no start index observable — no discount applied"
            )
            estimated.append(
                EstimatedGroupForecast(
                    group=name,
                    to_go=to_go,
                    sei=round(sei_g, 2) if sei_g is not None else None,
                    pooled_rate_per_month=round(pooled_rate_g, 3),
                    adjustment=round(adjustment, 2),
                    finish=finish_g,
                    finish_early=early,
                    finish_late=late,
                    basis=(
                        "ESTIMATE — no completions in this group yet: borrowed the pooled "
                        f"per-activity throughput ({pooled_per_activity_rate:.3f}/activity-"
                        f"month x {activities} activities; credibility weight on the group's "
                        f"own history Z = 0), {sei_note}; the early/late range is the "
                        "P75/P25 of the per-activity rates the groups WITH history "
                        "demonstrated (reference-class bound)"
                    ),
                )
            )
            # the group also contributes an ESTIMATED SPI(t) term to the full-coverage
            # weighted index: the pooled exact SPI(t) under the same discount
            if pooled_spi is not None and pooled_spi > 0:
                spi_terms_all.append((pooled_spi * adjustment, to_go))
        else:
            # truly impossible: no data date / no elapsed time / no completions anywhere
            unforecastable.append(name)
        if finish_g is not None and (rate_finish is None or finish_g > rate_finish):
            rate_finish, rate_limiting, rate_is_estimated = finish_g, name, is_est

    weighted_spi_all: float | None = None
    to_go_all = sum(w for _v, w in spi_terms_all)
    if to_go_all > 0:
        weighted_spi_all = sum(v * w for v, w in spi_terms_all) / to_go_all

    # group-weighted IEAC(t): the project PD/ES/AT with each weighted index
    def ieac(spi: float | None) -> dt.date | None:
        if spi is None or spi <= 0:
            return None
        _spi_t, es, at = _earned_schedule(schedule)
        planned_offsets = [
            off
            for t in non_summary(schedule)
            if (off := to_offset(schedule, t.baseline_finish)) is not None
        ]
        if not planned_offsets or es is None or at is None:
            return None
        pd_off = max(planned_offsets)
        ieac_off = round(at + max(0.0, pd_off - es) / spi)
        return offset_to_datetime(schedule.project_start, ieac_off, schedule.calendar).date()

    return GroupRollup(
        field=field,
        weight_basis="each group's exact SPI(t) weighted by its to-go activity count",
        groups_total=len(active),
        groups_used=len(direct),
        total_to_go=total_to_go,
        covered_to_go=covered_to_go,
        weighted_spi_t=round(weighted_spi, 2) if weighted_spi is not None else None,
        weighted_spi_t_all=round(weighted_spi_all, 2) if weighted_spi_all is not None else None,
        ieac_finish=ieac(weighted_spi),
        ieac_finish_all=ieac(weighted_spi_all),
        rate_finish=rate_finish,
        rate_limiting_group=rate_limiting,
        rate_finish_is_estimated=rate_is_estimated,
        estimated=tuple(estimated),
        unforecastable=tuple(unforecastable),
    )


def _earned_schedule(schedule: Schedule) -> tuple[float | None, float | None, float | None]:
    """(SPI(t), ES, AT) on the working-minute axis — delegates to the canonical
    count-based Earned-Schedule helper (``metrics.evm.earned_schedule``) so the forecast,
    the SPI(t) metric, and the WBS breakdown share one definition. Exact floats; the
    IEAC(t) caller divides by the precise ratio and only rounds SPI(t) for display."""
    es = earned_schedule(schedule, non_summary(schedule))
    if es is None:
        return None, None, None
    return es.spi_t, es.es_minutes, es.at_minutes
