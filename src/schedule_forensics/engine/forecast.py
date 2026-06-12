"""Finish-date forecasting — three independent answers to "when will it really end?" (M15).

The reference Power BI deck's forecasting page triangulates the project end date with
**three methods side by side** so an analyst can see whether logic, throughput, and
performance agree (a divergence is itself a finding):

1. **Schedule logic (CPM)** — the network's own computed finish (the date the plan
   claims, given its logic, durations, and calendar).
2. **Completion-rate extrapolation** — the throughput answer: at the historical pace of
   *activities actually completed per month*, how long do the to-go activities take?
3. **Earned-schedule IEAC(t)** — the performance answer: the standard Earned-Schedule
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
from schedule_forensics.model.schedule import Schedule

#: Average calendar days per month (365.25 / 12) — the rate method's month axis.
_DAYS_PER_MONTH = 365.25 / 12


@dataclass(frozen=True)
class FinishForecast:
    """One method's answer: the forecast finish date and the basis it was computed from."""

    method_id: str  # "cpm" | "rate" | "earned_schedule"
    name: str
    finish: dt.date | None  # None == inputs missing; never a fabricated date
    basis: str  # plain-language inputs (figures inline, verifiable)


@dataclass(frozen=True)
class ForecastSet:
    """The three forecasts plus the shared inputs the page shows alongside them."""

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
            f"the network's computed finish over {len(tasks)} activities",
        )
    ]

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


def _earned_schedule(schedule: Schedule) -> tuple[float | None, float | None, float | None]:
    """(SPI(t), ES, AT) on the working-minute axis — the same count-based Earned-Schedule
    construction as the SPI(t) metric (``metrics.evm._spi_t``): ES is the offset of the
    EV-th sorted baseline finish, AT the offset of the status date."""
    status_off = to_offset(schedule, schedule.status_date)
    if status_off is None or status_off <= 0:
        return None, None, None
    planned = sorted(
        off
        for t in non_summary(schedule)
        if (off := to_offset(schedule, t.baseline_finish)) is not None and off >= 0
    )
    ev = sum(1 for t in non_summary(schedule) if t.percent_complete >= 100.0)
    if ev <= 0 or not planned:
        return None, None, None
    es = float(planned[min(ev, len(planned)) - 1])
    return es / status_off, es, float(status_off)  # exact — callers round for display only
