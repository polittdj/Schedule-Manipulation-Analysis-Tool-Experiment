"""DCMA Metric 2 — Leads (negative lag)."""

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
    value=0.0,
    direction=Direction.AT_MOST,
    source=(
        "DCMA 14-Point Schedule Assessment, Metric 2 (Leads): 0% — no negative lag (lead) permitted"
    ),
)


def run_leads(schedule: Schedule, options: MetricOptions | None = None) -> MetricResult:
    """Relations with negative lag (leads). Offender keyed by successor; ``value`` = lag minutes."""
    relations = schedule.relations
    if not relations:
        raise MetricError("leads metric requires at least one relation")
    names = {t.unique_id: t.name for t in schedule.tasks}

    offenders = [
        Offender(r.successor_id, names[r.successor_id], float(r.lag_minutes))
        for r in relations
        if r.lag_minutes < 0
    ]
    offenders.sort(key=lambda offender: (offender.unique_id, offender.value))
    numerator = len(offenders)
    denominator = len(relations)
    severity = evaluate_severity(100.0 * numerator / denominator, _THRESHOLD)
    return MetricResult(
        metric_id=2,
        metric_name="Leads (Negative Lag)",
        severity=severity,
        threshold=_THRESHOLD,
        numerator=numerator,
        denominator=denominator,
        offenders=tuple(offenders),
    )
