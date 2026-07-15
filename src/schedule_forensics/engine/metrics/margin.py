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

from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Operator convention: a margin activity's name contains this word (case-insensitive substring).
MARGIN_KEYWORD = "margin"

#: Handbook aliases a buffer activity may carry INSTEAD of "margin" — surfaced as *near-miss*
#: candidates (never auto-counted) so the operator can confirm a reserve the naming convention
#: would otherwise miss. "reserve" is the pre-NPR 7120.5 term for schedule margin; "contingency"
#: and "integrated return" appear on some programs. Conservative: only the operator's confirm
#: promotes one.
NEAR_MISS_KEYWORDS = ("reserve", "contingency", "integrated return")


def is_margin_task(task: Task) -> bool:
    """True iff ``task`` is a schedule-margin activity by the operator's naming convention.

    A margin task is any **non-summary** activity whose name contains "margin"
    (case-insensitive, substring). Summary rollups are excluded even when named "margin".
    """
    return not task.is_summary and MARGIN_KEYWORD in task.name.lower()


@dataclass(frozen=True)
class MarginCandidate:
    """One activity the operator can confirm/deny as schedule margin, with the deciding context.

    ``tier`` is ``"primary"`` when the name carries "margin" (the name-based default) or
    ``"near-miss"`` when it carries only a handbook alias (:data:`NEAR_MISS_KEYWORDS`).
    ``total_float_days`` is the CPM total float (``0`` ⇒ on the driving chain, so the buffer is
    actually protecting the finish); ``on_critical`` is ``total_float <= 0``.
    """

    unique_id: int
    name: str
    duration_days: float
    total_float_days: float
    on_critical: bool
    tier: str  # "primary" (name has "margin") | "near-miss" (a handbook alias only)


def margin_candidates(schedule: Schedule, cpm: CPMResult) -> tuple[MarginCandidate, ...]:
    """Every activity that could be schedule margin, for the operator's confirm/deny overlay UI.

    Primary candidates are the name-based default (:func:`is_margin_task`). Near-miss candidates
    carry a handbook alias (:data:`NEAR_MISS_KEYWORDS`) but NOT the word "margin", surfaced so the
    operator can confirm a buffer the naming convention would miss (nothing is auto-counted from the
    aliases).
    Each row carries the deciding context: buffer size (days, elapsed-aware), CPM total float
    (``0`` ⇒ on the driving chain), and whether it is currently critical. Primaries first, then
    near-misses; within each, largest buffer first.
    """
    wmpd = schedule.calendar.working_minutes_per_day or 480
    out: list[MarginCandidate] = []
    for t in non_summary(schedule):
        low = t.name.lower()
        primary = MARGIN_KEYWORD in low
        near = not primary and any(k in low for k in NEAR_MISS_KEYWORDS)
        if not (primary or near):
            continue
        timing = cpm.timings.get(t.unique_id)
        tf = timing.total_float if timing is not None else 0
        axis = 1440 if t.duration_is_elapsed else wmpd
        out.append(
            MarginCandidate(
                unique_id=t.unique_id,
                name=t.name,
                duration_days=round(t.duration_minutes / axis, 1),
                total_float_days=round(tf / wmpd, 1),
                on_critical=timing is not None and timing.total_float <= 0,
                tier="primary" if primary else "near-miss",
            )
        )
    out.sort(key=lambda c: (c.tier != "primary", -c.duration_days))
    return tuple(out)


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


def _select_margin(schedule: Schedule, margin_uids: frozenset[int] | None) -> list[Task]:
    """The margin activities: the operator's CONFIRMED overlay (``margin_uids``, per-version, set in
    the UI) when supplied, else the name-based default (:func:`is_margin_task`). Summary rollups are
    always excluded. ``margin_uids=None`` (the default) reproduces the name-based behavior exactly,
    so threading the overlay through the engine is behavior-preserving until the operator confirms a
    set.
    """
    if margin_uids is None:
        return [t for t in non_summary(schedule) if is_margin_task(t)]
    return [t for t in non_summary(schedule) if t.unique_id in margin_uids]


def compute_margin(
    schedule: Schedule, cpm: CPMResult, *, margin_uids: frozenset[int] | None = None
) -> MarginAnalysis:
    """Compute the schedule-margin analysis for ``schedule`` (``cpm`` is the as-built network).

    ``total_margin_days`` sums the margin activities' durations. ``effective_margin_days`` re-runs
    CPM with every margin task's duration overridden to 0 and measures how far the project finish
    pulls in (clamped at 0) — the buffer actually protecting the finish (handbook "effective
    margin"). Both convert minutes to days on the schedule's calendar (480-min fallback).

    ``margin_uids`` (optional) is the operator's confirmed margin-task set; ``None`` uses the
    name-based default (:func:`is_margin_task`).
    """
    margin = _select_margin(schedule, margin_uids)
    if not margin:
        return MarginAnalysis(0, 0.0, 0.0, 0, ())

    wmpd = schedule.calendar.working_minutes_per_day or 480

    tasks: list[MarginTask] = []
    for t in margin:
        timing = cpm.timings.get(t.unique_id)
        on_critical = timing is not None and timing.total_float <= 0
        # an elapsed margin task's minutes are wall-clock: "5 edays" is 5 days, not 15 (QC D21)
        axis = 1440 if t.duration_is_elapsed else wmpd
        tasks.append(
            MarginTask(
                unique_id=t.unique_id,
                name=t.name,
                duration_days=round(t.duration_minutes / axis, 1),
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


@dataclass(frozen=True)
class MarginPoint:
    """One version's schedule-margin headline figures, for the cross-version burndown.

    ``label`` identifies the submission (caller-supplied, e.g. the source filename); ``status_date``
    is its data date as an ISO string (or ``None``). ``total_margin_days`` and
    ``effective_margin_days`` are :class:`MarginAnalysis`'s totals for that version (working days).
    """

    label: str
    status_date: str | None
    total_margin_days: float
    effective_margin_days: float


def compute_margin_trend(
    versions: Sequence[tuple[str, str | None, Schedule, CPMResult]],
    *,
    margin_uids: frozenset[int] | None = None,
) -> tuple[MarginPoint, ...]:
    """Pack a schedule-margin burndown across versions, in the order the caller supplies.

    Each element is ``(label, status_date, schedule, cpm)``; :func:`compute_margin` runs per version
    and the totals are packed into a :class:`MarginPoint`. The order is preserved exactly (the
    caller orders — typically oldest -> newest by data date), so margin erosion reads left to right.

    ``margin_uids`` (optional) is the operator's confirmed margin-task set, applied to every version
    (margin-task UniqueIDs are stable across versions of one project); ``None`` = name-based.
    """
    points: list[MarginPoint] = []
    for label, status_date, schedule, cpm in versions:
        m = compute_margin(schedule, cpm, margin_uids=margin_uids)
        points.append(
            MarginPoint(
                label=label,
                status_date=status_date,
                total_margin_days=m.total_margin_days,
                effective_margin_days=m.effective_margin_days,
            )
        )
    return tuple(points)
