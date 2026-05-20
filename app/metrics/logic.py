"""DCMA Metric 1 — Logic (missing predecessor/successor)."""

from __future__ import annotations

from app.exceptions import MetricError
from app.metrics.base import (
    MetricOptions,
    MetricResult,
    Offender,
    ThresholdConfig,
    evaluate_severity,
)
from app.models import Direction, Schedule

_THRESHOLD = ThresholdConfig(
    value=5.0,
    direction=Direction.AT_MOST,
    source=(
        "DCMA 14-Point Schedule Assessment, Metric 1 (Logic): "
        "<= 5% of tasks missing a predecessor and/or successor"
    ),
)


def run_missing_logic(schedule: Schedule, options: MetricOptions | None = None) -> MetricResult:
    """Tasks missing a predecessor and/or successor. Offender ``value`` = number of missing
    ends (1 or 2)."""
    options = options or MetricOptions()
    tasks = schedule.tasks
    if not tasks:
        raise MetricError("missing-logic metric requires at least one task")

    has_predecessor = dict.fromkeys((t.unique_id for t in tasks), False)
    has_successor = dict.fromkeys((t.unique_id for t in tasks), False)
    for relation in schedule.relations:
        has_successor[relation.predecessor_id] = True
        has_predecessor[relation.successor_id] = True

    open_start_ids = [uid for uid, ok in has_predecessor.items() if not ok]
    open_finish_ids = [uid for uid, ok in has_successor.items() if not ok]
    exempt_predecessor = (
        open_start_ids[0] if options.exclude_project_bookends and len(open_start_ids) == 1 else None
    )
    exempt_successor = (
        open_finish_ids[0]
        if options.exclude_project_bookends and len(open_finish_ids) == 1
        else None
    )

    offenders: list[Offender] = []
    for task in tasks:
        missing_pred = not has_predecessor[task.unique_id] and task.unique_id != exempt_predecessor
        missing_succ = not has_successor[task.unique_id] and task.unique_id != exempt_successor
        if missing_pred or missing_succ:
            offenders.append(
                Offender(task.unique_id, task.name, float(int(missing_pred) + int(missing_succ)))
            )

    offenders.sort(key=lambda offender: offender.unique_id)
    numerator = len(offenders)
    denominator = len(tasks)
    severity = evaluate_severity(100.0 * numerator / denominator, _THRESHOLD)
    return MetricResult(
        metric_id=1,
        metric_name="Logic (Missing Predecessor/Successor)",
        severity=severity,
        threshold=_THRESHOLD,
        numerator=numerator,
        denominator=denominator,
        offenders=tuple(offenders),
    )
