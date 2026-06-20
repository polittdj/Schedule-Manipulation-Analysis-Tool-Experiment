"""Schedule-margin metrics — the buffer activities that protect the project finish.

Schedule margin (a.k.a. schedule reserve) is explicit buffer time the planner inserts to absorb
risk before a committed milestone; the NASA Schedule Management Handbook treats it as a managed,
visible activity rather than hidden float. By operator convention this tool identifies a margin
activity by name: any non-summary task whose name contains the word "margin" (case-insensitive,
substring) — e.g. "USA Schedule MARGIN: Pre-Ship".

Two figures matter. **Total margin** is just the sum of those activities' durations — how much
buffer is nominally in the schedule. **Effective margin** is the buffer that is actually
protecting the finish: zero the duration of every margin task and re-run CPM; the amount the
project finish pulls in is the margin that was on the driving chain (margin sitting on a path with
slack protects nothing and contributes 0 to the effective figure). The single trusted CPM solver
(:func:`compute_cpm`, via its ``duration_overrides`` hook) does the re-run, so the figure can never
diverge from the engine (Law 2).

Lightweight dataclasses (NOT :class:`MetricResult`) — this stays out of the Fuse-parity ribbon and
the metric-dictionary coverage test, like :mod:`.health_extra`.
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Operator convention: a margin activity's name contains this word (case-insensitive substring).
MARGIN_KEYWORD = "margin"


def is_margin_task(task: Task) -> bool:
    """True iff ``task`` is a schedule-margin activity by the operator's naming convention.

    A margin task is any **non-summary** activity whose name contains "margin"
    (case-insensitive, substring). Summary rollups are excluded even when named "margin".
    """
    return not task.is_summary and MARGIN_KEYWORD in task.name.lower()


@dataclass(frozen=True)
class MarginTask:
    """One schedule-margin activity: its identity, buffer size, and whether it drives the finish."""

    unique_id: int
    name: str
    duration_days: float
    on_critical: bool


@dataclass(frozen=True)
class MarginAnalysis:
    """The schedule-margin picture for one schedule: totals, criticality, and the activities."""

    count: int
    total_margin_days: float
    effective_margin_days: float
    on_critical_count: int
    tasks: tuple[MarginTask, ...]


def compute_margin(schedule: Schedule, cpm: CPMResult) -> MarginAnalysis:
    """Compute the schedule-margin analysis for ``schedule`` (``cpm`` is the as-built network).

    ``total_margin_days`` sums the margin activities' durations. ``effective_margin_days`` re-runs
    CPM with every margin task's duration overridden to 0 and measures how far the project finish
    pulls in (clamped at 0) — the buffer actually protecting the finish (handbook "effective
    margin"). Both convert minutes to days on the schedule's calendar (480-min fallback).
    """
    margin = [t for t in non_summary(schedule) if is_margin_task(t)]
    if not margin:
        return MarginAnalysis(0, 0.0, 0.0, 0, ())

    wmpd = schedule.calendar.working_minutes_per_day or 480

    tasks: list[MarginTask] = []
    for t in margin:
        timing = cpm.timings.get(t.unique_id)
        on_critical = timing is not None and timing.total_float <= 0
        tasks.append(
            MarginTask(
                unique_id=t.unique_id,
                name=t.name,
                duration_days=round(t.duration_minutes / wmpd, 1),
                on_critical=on_critical,
            )
        )

    total_margin_days = round(sum(mt.duration_days for mt in tasks), 1)
    on_critical_count = sum(1 for mt in tasks if mt.on_critical)

    finish_without = compute_cpm(
        schedule, duration_overrides={t.unique_id: 0 for t in margin}
    ).project_finish
    effective_margin_days = round(max(0, cpm.project_finish - finish_without) / wmpd, 1)

    tasks.sort(key=lambda mt: mt.duration_days, reverse=True)
    return MarginAnalysis(
        count=len(tasks),
        total_margin_days=total_margin_days,
        effective_margin_days=effective_margin_days,
        on_critical_count=on_critical_count,
        tasks=tuple(tasks),
    )
