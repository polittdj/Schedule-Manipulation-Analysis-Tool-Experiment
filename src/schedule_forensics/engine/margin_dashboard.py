"""Executive margin/contingency dashboard — the NASA Margin & Contingency Burn-Down + the Margin
Erosion Trend (MET), across the loaded schedule versions.

This assembles, per loaded version (one status date each), the figures the operator's NASA
``MarginContingency_BurnDown`` reference workbook tracks, and projects the margin-erosion trend.
Nothing is fabricated: every figure is derived on the spot from the loaded schedules and the same
trusted CPM solver the rest of the tool uses.

Definitions (verbatim from the reference workbook, with the operator's two scope choices —
2026-07-14 — margin is measured **to the session-selected target milestone when one is set, else the
project finish**, and contingency counts the schedule **calendar's** non-working days, i.e. weekends
*and* holidays, not weekends only):

* **Effective margin (work days)** — the buffer actually protecting the target finish: zero every
  margin activity's duration, re-run CPM, and measure how far the target finish pulls in
  (:mod:`.metrics.margin`'s effective-margin method, re-anchored on the target). ``0`` when no
  margin sits on the target's driving path.
* **Zero-margin finish (E)** — the target finish in that zeroed re-solve (the NRO-SEM "Effective
  Margin Calculator" output). **Margin in calendar days (G)** = target finish (D) - zero-margin
  finish (E).
* **Contingency (unplanned) days** — the schedule calendar's non-working days from the status date
  through the target finish (weekends + holidays). No overlap with the work-day margin.
* **NASA margin requirement (O)** — the Gold-Rule guideline: ``days-to-go x 30/365`` (30 margin
  work-days per program year). Configurable rate; 30/yr is the NASA Schedule Management Handbook
  default.
* **Days-to-go minus margin (Q)** — calendar days from the status date to the zero-margin finish.
* **% total available (R)** = (effective margin + contingency) / days-to-go; **% effective (T)** =
  margin-calendar-days / days-to-go.
* **Trigger for action** — the actual effective margin has fallen below the NASA requirement line.

The **Margin Erosion Trend** fits a least-squares line to effective margin (work days) vs. status
date and extrapolates it to zero, giving an erosion rate (work days lost per month) and a projected
zero-margin date — with the fit's R² disclosed, never hidden.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.metrics.margin import is_margin_task
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule

#: NASA Gold-Rule default: 30 margin work-days per program year (Schedule Management Handbook).
_GOLD_RULE_DAYS_PER_YEAR = 30.0
_DAYS_PER_YEAR = 365.0
#: Mean calendar days per month, for expressing the erosion slope "per month".
_DAYS_PER_MONTH = 30.4368


def _finish_offset(cpm: CPMResult, target_uid: int | None) -> int:
    """The working-minute finish offset to measure margin to: the target activity's finish when
    ``target_uid`` is set and present in this version, else the whole-network project finish."""
    if target_uid is not None:
        timing = cpm.timings.get(target_uid)
        if timing is not None:
            return timing.early_finish
    return cpm.project_finish


def _nonworking_days(calendar: Calendar, start: dt.date, end: dt.date) -> int:
    """Schedule-calendar non-working days (weekends + holidays) in ``[start, end]`` inclusive —
    the contingency count. ``0`` when the target is on/before the status date."""
    if end <= start:
        return 0
    return sum(
        1
        for i in range((end - start).days + 1)
        if not calendar.is_working_day(start + dt.timedelta(days=i))
    )


@dataclass(frozen=True)
class MarginMonth:
    """One version's margin/contingency burn-down figures (a column of the reference workbook)."""

    label: str
    status_date: str | None  # C / TimeNow (ISO)
    target_name: str | None  # the milestone margin is measured to (None -> project finish)
    target_finish: str | None  # D (ISO)
    zero_margin_finish: str | None  # E (ISO)
    effective_margin_wd: float  # I — effective margin, work days (to the target)
    margin_cd: int  # G — target finish - zero-margin finish, calendar days
    contingency_wd: int  # J — calendar non-working days, status -> target
    total_available: float  # P = effective margin + contingency
    days_to_go: int  # Q — calendar days, status -> zero-margin finish
    nasa_rqmt_wd: float  # O — days-to-go x 30/365 (Gold Rule)
    pct_available: float | None  # R — total available / days-to-go (0..1)
    pct_effective: float | None  # T — margin calendar days / days-to-go (0..1)
    below_requirement: bool  # trigger: effective margin < the NASA requirement line


@dataclass(frozen=True)
class MarginDashboard:
    """The whole margin picture across versions + the erosion projection."""

    months: tuple[MarginMonth, ...]
    have_margin_tasks: bool  # False -> no activity named "margin"; the burn-down is empty
    #: Margin Erosion Trend (least-squares over effective margin vs status date):
    erosion_wd_per_month: float | None  # work days of margin lost per month (>0 = eroding)
    zero_margin_date: str | None  # projected date effective margin hits 0 (ISO), if eroding
    erosion_r2: float | None  # fit quality (disclosed), None when < 2 dated points


def _margin_month(
    label: str,
    schedule: Schedule,
    cpm: CPMResult,
    target_uid: int | None,
    gold_rule_per_year: float,
) -> MarginMonth:
    cal = schedule.calendar
    wmpd = cal.working_minutes_per_day or 480
    margin_tasks = [t for t in non_summary(schedule) if is_margin_task(t)]

    finish_asbuilt = _finish_offset(cpm, target_uid)
    if margin_tasks:
        zeroed = compute_cpm(schedule, duration_overrides={t.unique_id: 0 for t in margin_tasks})
        finish_zeroed = _finish_offset(zeroed, target_uid)
    else:
        finish_zeroed = finish_asbuilt
    effective_margin_wd = round(max(0, finish_asbuilt - finish_zeroed) / wmpd, 1)

    target_dt = offset_to_datetime(schedule.project_start, finish_asbuilt, cal)
    zero_dt = offset_to_datetime(schedule.project_start, finish_zeroed, cal)
    margin_cd = (target_dt.date() - zero_dt.date()).days

    status = schedule.status_date
    target_name = None
    if target_uid is not None:
        t = schedule.tasks_by_id.get(target_uid)
        target_name = t.name if t is not None else None

    contingency_wd = 0
    days_to_go = 0
    if status is not None:
        contingency_wd = _nonworking_days(cal, status.date(), target_dt.date())
        days_to_go = max(0, (zero_dt.date() - status.date()).days)

    total_available = round(effective_margin_wd + contingency_wd, 1)
    nasa_rqmt_wd = round(days_to_go * gold_rule_per_year / _DAYS_PER_YEAR, 1)
    pct_available = round(total_available / days_to_go, 4) if days_to_go else None
    pct_effective = round(margin_cd / days_to_go, 4) if days_to_go else None

    return MarginMonth(
        label=label,
        status_date=status.date().isoformat() if status is not None else None,
        target_name=target_name,
        target_finish=target_dt.date().isoformat(),
        zero_margin_finish=zero_dt.date().isoformat(),
        effective_margin_wd=effective_margin_wd,
        margin_cd=margin_cd,
        contingency_wd=contingency_wd,
        total_available=total_available,
        days_to_go=days_to_go,
        nasa_rqmt_wd=nasa_rqmt_wd,
        pct_available=pct_available,
        pct_effective=pct_effective,
        below_requirement=status is not None and effective_margin_wd < nasa_rqmt_wd,
    )


def _erosion(months: Sequence[MarginMonth]) -> tuple[float | None, str | None, float | None]:
    """Least-squares fit of effective margin (work days) vs. status date -> (work-days lost per
    month, projected zero-margin date ISO, R²). Requires ≥2 dated points; a flat/growing margin
    yields no zero-margin date (None)."""
    pts = [
        (dt.date.fromisoformat(m.status_date), m.effective_margin_wd)
        for m in months
        if m.status_date is not None
    ]
    if len(pts) < 2:
        return None, None, None
    x0 = pts[0][0]
    xs = [(d - x0).days for d, _ in pts]
    ys = [y for _, y in pts]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:  # all points share one status date — no trend
        return None, None, None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx  # work days of margin per calendar day
    intercept = my - slope * mx
    syy = sum((y - my) ** 2 for y in ys)
    r2 = round((sxy * sxy) / (sxx * syy), 3) if syy > 0 else None
    erosion_per_month = round(-slope * _DAYS_PER_MONTH, 2)

    zero_date: str | None = None
    if slope < 0:  # margin is eroding — extrapolate to zero
        x_zero = -intercept / slope
        zero_date = (x0 + dt.timedelta(days=round(x_zero))).isoformat()
    return erosion_per_month, zero_date, r2


def compute_margin_dashboard(
    versions: Sequence[tuple[str, Schedule, CPMResult]],
    target_uid: int | None = None,
    gold_rule_per_year: float = _GOLD_RULE_DAYS_PER_YEAR,
) -> MarginDashboard:
    """Build the burn-down + erosion trend across ``versions`` (given oldest -> newest).

    Each element is ``(label, schedule, cpm)``. Margin is measured to ``target_uid`` when it is set
    and present in a version, else that version's project finish (operator choice 2026-07-14). The
    Gold-Rule requirement rate defaults to 30 work-days/year. ``have_margin_tasks`` is False when no
    loaded version carries an activity named "margin" (the burn-down would be all zeros)."""
    months = tuple(
        _margin_month(label, sch, cpm, target_uid, gold_rule_per_year)
        for label, sch, cpm in versions
    )
    have_margin = any(is_margin_task(t) for _label, sch, _cpm in versions for t in non_summary(sch))
    erosion_pm, zero_date, r2 = _erosion(months)
    return MarginDashboard(
        months=months,
        have_margin_tasks=have_margin,
        erosion_wd_per_month=erosion_pm,
        zero_margin_date=zero_date,
        erosion_r2=r2,
    )
