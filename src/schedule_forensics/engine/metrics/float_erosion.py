"""Float-erosion by WBS — where the schedule's buffer is thinning (handbook Figs 7-34/7-35).

The handbook's float-erosion view groups total float by WBS so an analyst can see *which* part of
the program is consuming its buffer before the project-level margin is hit. This module computes the
**current** per-top-level-WBS float summary: the smallest and average total float in each group, how
many of its activities are critical, and a stoplight on the group's minimum float.

Total float is read **progress-aware** via :func:`effective_total_float` (the source tool's stored
Total Slack when present, else the recomputed CPM float), so the numbers agree with the rest of the
tool's float-based metrics (Acumen parity, ADR-0080). Parity-isolated lightweight dataclasses (NOT
``MetricResult``) — out of the Fuse ribbon and the metric-dictionary coverage test, like
``health_extra`` / ``logic_integrity`` / ``margin``.

Sources: NASA Schedule Management Handbook Figs 7-34/7-35 (float erosion by WBS / IMS level);
assessment Deck-1 (float-erosion stoplight). The cross-version current-vs-prior comparison is a
follow-on; this is the single-schedule snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics._common import (
    effective_total_float,
    is_effective_critical,
    non_summary,
)
from schedule_forensics.engine.metrics.wbs_breakdown import _top_level
from schedule_forensics.model.schedule import Schedule

#: a group whose minimum total float is at/below this many working days is "thin" (yellow); below
#: zero is "eroded" (red). 10 working days (two weeks) is the near-critical screening band.
_LOW_FLOAT_DAYS = 10.0


@dataclass(frozen=True)
class WBSFloat:
    """One top-level-WBS group's float-erosion figures (total float in working days)."""

    wbs: str
    count: int
    min_float_days: float
    avg_float_days: float
    critical_count: int
    status: str  # "red" (min < 0) | "yellow" (0 <= min <= threshold) | "green" (min > threshold)


@dataclass(frozen=True)
class FloatErosion:
    """The per-WBS float-erosion snapshot for one schedule."""

    groups: tuple[WBSFloat, ...]
    min_float_days: float | None  # project-wide minimum total float (None: no activities)
    low_float_threshold_days: float  # the yellow band ceiling, for the UI to state


def _status(min_float_days: float) -> str:
    if min_float_days < 0:
        return "red"
    if min_float_days <= _LOW_FLOAT_DAYS:
        return "yellow"
    return "green"


def compute_float_erosion(schedule: Schedule, cpm: CPMResult) -> FloatErosion:
    """Per-top-level-WBS total-float summary for ``schedule`` (progress-aware float; CPM-derived).

    Activities group by their top-level WBS segment (``"7.3"`` → ``"7"``; no code → ``"(none)"``),
    matching ``wbs_breakdown``. Each group reports its minimum and average total float in working
    days, its critical-activity count, and a stoplight on the minimum float.
    """
    per_day = schedule.calendar.working_minutes_per_day or 480
    groups: dict[str, list[float]] = {}
    crit: dict[str, int] = {}
    for task in non_summary(schedule):
        timing = cpm.timings.get(task.unique_id)
        recomputed = float(timing.total_float) if timing is not None else 0.0
        tf_days = effective_total_float(task, recomputed) / per_day
        key = _top_level(task.wbs)
        groups.setdefault(key, []).append(tf_days)
        if is_effective_critical(task, recomputed):
            crit[key] = crit.get(key, 0) + 1

    def sort_key(label: str) -> tuple[int, float, str]:
        if label == "(none)":
            return (2, 0.0, "")
        try:
            return (0, float(label), "")
        except ValueError:
            return (1, 0.0, label)

    out: list[WBSFloat] = []
    for wbs in sorted(groups, key=sort_key):
        floats = groups[wbs]
        lo = min(floats)
        out.append(
            WBSFloat(
                wbs=wbs,
                count=len(floats),
                min_float_days=round(lo, 1),
                avg_float_days=round(sum(floats) / len(floats), 1),
                critical_count=crit.get(wbs, 0),
                status=_status(lo),
            )
        )
    project_min = round(min(min(v) for v in groups.values()), 1) if groups else None
    return FloatErosion(
        groups=tuple(out),
        min_float_days=project_min,
        low_float_threshold_days=_LOW_FLOAT_DAYS,
    )
