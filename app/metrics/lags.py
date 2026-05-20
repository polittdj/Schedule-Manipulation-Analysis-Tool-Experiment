"""DCMA Metric 3 — Lags (positive lag)."""

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
        "DCMA 14-Point Schedule Assessment, Metric 3 (Lags): "
        "<= 5% of relations carrying positive lag"
    ),
)


def run_lags(schedule: Schedule, options: MetricOptions | None = None) -> MetricResult:
    """Relations with positive lag. Offender keyed by successor; ``value`` = lag minutes."""
    relations = schedule.relations
    if not relations:
        raise MetricError("lags metric requires at least one relation")
    names = {t.unique_id: t.name for t in schedule.tasks}

    offenders = [
        Offender(r.successor_id, names[r.successor_id], float(r.lag_minutes))
        for r in relations
        if r.lag_minutes > 0
    ]
    offenders.sort(key=lambda offender: (offender.unique_id, offender.value))
    numerator = len(offenders)
    denominator = len(relations)
    severity = evaluate_severity(100.0 * numerator / denominator, _THRESHOLD)
    return MetricResult(
        metric_id=3,
        metric_name="Lags (Positive Lag)",
        severity=severity,
        threshold=_THRESHOLD,
        numerator=numerator,
        denominator=denominator,
        offenders=tuple(offenders),
    )
