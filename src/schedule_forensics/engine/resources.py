"""Resource loading & over-allocation (ADR-0125).

Time-phases each task's resource :class:`~schedule_forensics.model.assignment.Assignment` work
across the task's CPM span and buckets it by **day / week / month** (selectable, ADR-0125/#74), per
resource. A resource's per-bucket **capacity** is ``max_units x working-minutes-per-day x
working-days-in-the-bucket``; any bucket whose booked work exceeds that capacity is
**over-allocated**. Each bucket also records the per-task work behind it (the click-a-bar drill).
All derived (never stored on the model); parity-isolated (plain dataclasses, never a
``MetricResult``); std-lib only.

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

#: Bucket granularities the loading histogram supports (operator #74).
GRANULARITIES = ("day", "week", "month")


def _bucket_key(day: dt.date, granularity: str) -> str:
    """Bucket a calendar day into a sortable period key for the chosen granularity.

    ``day`` -> ``YYYY-MM-DD``; ``week`` -> ISO ``YYYY-Www`` (Monday-start ISO week);
    ``month`` -> ``YYYY-MM``. Keys sort chronologically as plain strings within a granularity.
    """
    if granularity == "day":
        return day.isoformat()
    if granularity == "week":
        iso = day.isocalendar()
        return f"{iso[0]:04d}-W{iso[1]:02d}"
    return f"{day.year:04d}-{day.month:02d}"


@dataclass(frozen=True)
class ResourcePeriod:
    """One bucket of a resource's load against its capacity (both in working minutes)."""

    period: str  # "YYYY-MM" (month) / "YYYY-Www" (week) / "YYYY-MM-DD" (day)
    load_minutes: float
    capacity_minutes: float
    #: (task unique_id -> booked working minutes) driving this bucket — the click-a-bar drill.
    contributors: tuple[tuple[int, float], ...] = ()

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

    periods: tuple[str, ...]  # every bucket across the loaded resources, sorted
    resources: tuple[ResourceLoad, ...]  # sorted by total work desc
    has_work: bool  # any assignment carried recorded work (else a count-only fallback applies)
    working_minutes_per_day: int
    granularity: str = "month"  # the bucket size these periods use (day / week / month)


def _is_working(cal: Calendar, day: dt.date) -> bool:
    return day.weekday() in cal.work_weekdays and day not in cal.holidays


def _period_working_days(
    cal: Calendar, lo: dt.date, hi: dt.date, granularity: str
) -> dict[str, int]:
    """Working-day count per bucket across [lo, hi] (inclusive) at the chosen granularity."""
    out: dict[str, int] = {}
    day = lo
    guard = 0
    while day <= hi and guard < 2_000_000:
        guard += 1
        if _is_working(cal, day):
            key = _bucket_key(day, granularity)
            out[key] = out.get(key, 0) + 1
        day += dt.timedelta(days=1)
    return out


def compute_resource_loading(
    schedule: Schedule, cpm: CPMResult, granularity: str = "month"
) -> ResourceLoading:
    """Per-resource time-phased work load vs capacity, with over-allocated buckets flagged.

    ``granularity`` buckets the histogram by ``day`` / ``week`` / ``month`` (operator #74);
    capacity scales with the working days in each bucket, so over-allocation is consistent at
    every granularity. Each bucket also carries the per-task contributions behind it (the
    click-a-bar drill). Unknown granularities fall back to ``month``."""
    if granularity not in GRANULARITIES:
        granularity = "month"
    cal = schedule.calendar
    wmpd = cal.working_minutes_per_day or 480
    ps = schedule.project_start
    by_id = schedule.resources_by_id

    # per resource: bucket -> booked work minutes, and the set of tasks it appears on;
    # plus per resource: bucket -> {task uid -> booked minutes} for the click-a-bar drill.
    load: dict[int, dict[str, float]] = {}
    contrib: dict[int, dict[str, dict[int, float]]] = {}
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
            res_contrib = contrib.setdefault(a.resource_id, {})
            for day in wdays:
                key = _bucket_key(day, granularity)
                res_load[key] = res_load.get(key, 0.0) + per_day
                bucket_tasks = res_contrib.setdefault(key, {})
                bucket_tasks[task.unique_id] = bucket_tasks.get(task.unique_id, 0.0) + per_day

    period_wd = (
        _period_working_days(cal, lo, hi, granularity) if lo is not None and hi is not None else {}
    )

    resources: list[ResourceLoad] = []
    for rid, tasks in tasks_seen.items():
        res = by_id.get(rid)
        name = res.name if res is not None else f"Resource {rid}"
        rtype = str(res.type) if res is not None else "WORK"
        max_units = (res.max_units if res is not None and res.max_units is not None else 1.0) or 1.0
        months = load.get(rid, {})
        res_contrib = contrib.get(rid, {})
        series = []
        for period in sorted(set(months) | (set(period_wd) & set(months))):
            cap = max_units * wmpd * period_wd.get(period, 0)
            contributors = tuple(
                sorted(res_contrib.get(period, {}).items(), key=lambda kv: (-kv[1], kv[0]))
            )
            series.append(ResourcePeriod(period, months.get(period, 0.0), cap, contributors))
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
        granularity=granularity,
    )
