"""Float Ratio™ — average activity total float per day of remaining work (Acumen Bible formula).

The Deltek Acumen Fuse "Float Ratio™" metric, taken verbatim from the NASA Acumen metric library
(the "Bible", ``<Metric Name="Float Ratio™">``). It answers *how much breathing room does the
remaining work have, relative to how much work is left* — the average, across the live activities,
of each activity's total float divided by its remaining duration. A higher ratio means more float
per day of remaining duration (a looser, lower-risk schedule); a ratio near zero means the work is
running out of room.

The Bible carries two algebraic forms of the same idea, and this module computes **both**:

* the canonical, threshold-bearing definition — the *mean of the per-activity ratios*::

      Float Ratio = AVERAGE(TotalFloat / RemainingDuration)

* an aggregate form some library entries use — the *ratio of the means* (equivalently
  ``sum(TotalFloat) / sum(RemainingDuration)``)::

      Float Ratio (aggregate) = AVERAGE(TotalFloat) / AVERAGE(RemainingDuration)

Population (the Bible's ``PrimaryFilter``): **Normal** activities (non-summary, non-milestone,
non-hammock) that are **Planned or In-Progress** — completed work is excluded (it has no remaining
duration and carries no forward risk). Total float is read from the source tool's stored,
progress-aware value when present (matching Acumen — :func:`effective_total_float`), otherwise the
engine's recomputed CPM float. Float and remaining duration are both converted to working **days**
on the schedule's own calendar before dividing, so the ratio is unit-consistent even with elapsed
durations; activities with no remaining duration are skipped (division guard).

Bible interpretation bands (informational — Float Ratio is not a DCMA pass/fail check): ``< 0.1``
very tight, ``0.1-0.3`` tight, ``0.3-0.6`` healthy, ``> 0.6`` generous (check for missing logic).
The offenders cited are the activities in the very-tight band (ratio ``< 0.1``).
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    duration_days_axis,
    effective_total_float,
    non_summary,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: The Bible's lowest ("Low") band edge — activities below this are very tight (cited as offenders).
_LOW_BAND = 0.1


def _float_ratio_population(schedule: Schedule) -> list[Task]:
    """Normal, planned-or-in-progress activities (the Bible's Float Ratio filter).

    Non-summary, non-milestone, non-level-of-effort (hammock), and **incomplete** — completed
    work is excluded (it has no remaining duration and poses no forward risk)."""
    return [
        t
        for t in non_summary(schedule)
        if not t.is_milestone and not t.is_level_of_effort and not t.is_complete
    ]


def _remaining_minutes(task: Task) -> int:
    """Remaining duration in working minutes — the stored value, else duration scaled by % left."""
    if task.remaining_duration_minutes is not None:
        return task.remaining_duration_minutes
    return round(task.duration_minutes * (100.0 - task.percent_complete) / 100.0)


def _scored(schedule: Schedule, result: CPMResult) -> list[tuple[Task, float, float]]:
    """``(task, total_float_days, remaining_days)`` for each scorable activity in the population.

    Activities with no remaining duration (the division guard) or no available float (no stored
    value and absent from the CPM result) are skipped — they cannot contribute a ratio."""
    per_day = schedule.calendar.working_minutes_per_day or 1
    out: list[tuple[Task, float, float]] = []
    for t in _float_ratio_population(schedule):
        remaining_days = duration_days_axis(
            _remaining_minutes(t),
            is_elapsed=t.duration_is_elapsed,
            calendar_minutes_per_day=per_day,
        )
        if remaining_days <= 0:
            continue
        if t.stored_total_float_minutes is None and t.unique_id not in result.timings:
            continue
        recomputed = (
            float(result.timings[t.unique_id].total_float) if t.unique_id in result.timings else 0.0
        )
        float_days = effective_total_float(t, recomputed) / per_day
        out.append((t, float_days, remaining_days))
    return out


def _na(metric_id: str, name: str) -> MetricResult:
    return MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)


def compute_float_ratio(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """Float Ratio™ over the normal planned/in-progress population — both Bible forms.

    Returns ``float_ratio`` (the canonical mean-of-ratios, threshold-bearing) and
    ``float_ratio_aggregate`` (the ratio-of-means). Both are single-snapshot and informational
    (no pass/fail threshold); ``population`` is the activity count averaged (NA when it is zero,
    e.g. a fully complete or milestone-only scope). ``offender_uids`` on the primary cut are the
    very-tight activities (per-activity ratio ``< 0.1``)."""
    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    scored = _scored(schedule, result)
    count = len(scored)
    if count == 0:
        return {
            "float_ratio": _na("float_ratio", "Float Ratio"),
            "float_ratio_aggregate": _na("float_ratio_aggregate", "Float Ratio (aggregate)"),
        }
    mean_of_ratios = sum(tf / rd for _, tf, rd in scored) / count
    total_float_days = sum(tf for _, tf, _ in scored)
    total_remaining_days = sum(rd for _, _, rd in scored)
    aggregate = total_float_days / total_remaining_days if total_remaining_days else 0.0
    tight = tuple(sorted(t.unique_id for t, tf, rd in scored if tf / rd < _LOW_BAND))
    return {
        "float_ratio": MetricResult(
            "float_ratio",
            "Float Ratio",
            count,
            count,
            round(mean_of_ratios, 2),
            "ratio",
            CheckStatus.NOT_APPLICABLE,
            offender_uids=tight,
        ),
        "float_ratio_aggregate": MetricResult(
            "float_ratio_aggregate",
            "Float Ratio (aggregate)",
            count,
            count,
            round(aggregate, 2),
            "ratio",
            CheckStatus.NOT_APPLICABLE,
        ),
    }
