"""Resource loading & over-allocation (ADR-0125).

Time-phases each task's resource :class:`~schedule_forensics.model.assignment.Assignment` work
across the task's CPM span and buckets it by calendar month, per resource. A resource's monthly
**capacity** is ``max_units x working-minutes-per-day x working-days-in-the-month``; any month whose
booked work exceeds that capacity is **over-allocated**. All derived (never stored on the model);
parity-isolated (plain dataclasses, never a ``MetricResult``); std-lib only.

Work is distributed uniformly across the working days in a task's span (early start -> early finish
from the CPM), which is the standard "even-spread" resource histogram when the source file does not
carry a time-phased work contour. Tasks/resources with no recorded work contribute nothing (the page
then falls back to an assignment-count read).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model import Schedule
from schedule_forensics.model.calendar import Calendar


@dataclass(frozen=True)
class ResourcePeriod:
    """One month of a resource's load against its capacity (both in working minutes)."""

    period: str  # "YYYY-MM"
    load_minutes: float
    capacity_minutes: float

    @property
    def over_allocated(self) -> bool:
        return self.capacity_minutes > 0 and self.load_minutes > self.capacity_minutes + 1e-6


@dataclass(frozen=True)
class ResourceLoad:
    """A single resource's time-phased loading summary."""

    resource_id: int
    name: str
    type: str
    max_units: float
    total_work_minutes: float
    task_count: int
    peak_load_minutes: float
    peak_period: str | None
    over_allocated_periods: tuple[str, ...]
    series: tuple[ResourcePeriod, ...]


@dataclass(frozen=True)
class ResourceLoading:
    """The whole-schedule resource-loading result for the Resources page."""

    periods: tuple[str, ...]  # every month across the loaded resources, sorted
    resources: tuple[ResourceLoad, ...]  # sorted by total work desc
    has_work: bool  # any assignment carried recorded work (else a count-only fallback applies)
    working_minutes_per_day: int


def _is_working(cal: Calendar, day: dt.date) -> bool:
    return day.weekday() in cal.work_weekdays and day not in cal.holidays


def _period_working_days(cal: Calendar, lo: dt.date, hi: dt.date) -> dict[str, int]:
    """Working-day count per "YYYY-MM" across [lo, hi] (inclusive)."""
    out: dict[str, int] = {}
    day = lo
    guard = 0
    while day <= hi and guard < 200_000:
        guard += 1
        if _is_working(cal, day):
            key = f"{day.year:04d}-{day.month:02d}"
            out[key] = out.get(key, 0) + 1
        day += dt.timedelta(days=1)
    return out


def compute_resource_loading(schedule: Schedule, cpm: CPMResult) -> ResourceLoading:
    """Per-resource monthly work load vs capacity, with over-allocated months flagged."""
    cal = schedule.calendar
    wmpd = cal.working_minutes_per_day or 480
    ps = schedule.project_start
    by_id = schedule.resources_by_id

    # per resource: month -> booked work minutes, and the set of tasks it appears on
    load: dict[int, dict[str, float]] = {}
    tasks_seen: dict[int, set[int]] = {}
    any_work = False
    lo: dt.date | None = None
    hi: dt.date | None = None

    for task in non_summary(schedule):
        if not task.resource_assignments:
            continue
        timing = cpm.timings.get(task.unique_id)
        if timing is None:
            continue
        sd = offset_to_datetime(ps, timing.early_start, cal).date()
        fd = offset_to_datetime(ps, max(timing.early_finish, timing.early_start), cal).date()
        lo = sd if lo is None else min(lo, sd)
        hi = fd if hi is None else max(hi, fd)
        wdays = [
            sd + dt.timedelta(days=i)
            for i in range((fd - sd).days + 1)
            if _is_working(cal, sd + dt.timedelta(days=i))
        ] or [sd]
        n = len(wdays)
        for a in task.resource_assignments:
            tasks_seen.setdefault(a.resource_id, set()).add(task.unique_id)
            if a.work_minutes <= 0:
                continue
            any_work = True
            per_day = a.work_minutes / n
            res_load = load.setdefault(a.resource_id, {})
            for day in wdays:
                key = f"{day.year:04d}-{day.month:02d}"
                res_load[key] = res_load.get(key, 0.0) + per_day

    period_wd = _period_working_days(cal, lo, hi) if lo is not None and hi is not None else {}

    resources: list[ResourceLoad] = []
    for rid, tasks in tasks_seen.items():
        res = by_id.get(rid)
        name = res.name if res is not None else f"Resource {rid}"
        rtype = str(res.type) if res is not None else "WORK"
        max_units = (res.max_units if res is not None and res.max_units is not None else 1.0) or 1.0
        months = load.get(rid, {})
        series = []
        for period in sorted(set(months) | (set(period_wd) & set(months))):
            cap = max_units * wmpd * period_wd.get(period, 0)
            series.append(ResourcePeriod(period, months.get(period, 0.0), cap))
        over = tuple(p.period for p in series if p.over_allocated)
        peak = max(series, key=lambda p: p.load_minutes, default=None)
        resources.append(
            ResourceLoad(
                resource_id=rid,
                name=name,
                type=rtype,
                max_units=max_units,
                total_work_minutes=sum(months.values()),
                task_count=len(tasks),
                peak_load_minutes=peak.load_minutes if peak else 0.0,
                peak_period=peak.period if peak else None,
                over_allocated_periods=over,
                series=tuple(series),
            )
        )

    resources.sort(key=lambda r: (-r.total_work_minutes, r.name))
    all_periods = sorted({p.period for r in resources for p in r.series})
    return ResourceLoading(
        periods=tuple(all_periods),
        resources=tuple(resources),
        has_work=any_work,
        working_minutes_per_day=wmpd,
    )
