"""DCMA Metric 4 — Relationship Types (% Finish-to-Start)."""

from __future__ import annotations

from app.exceptions import MetricError
from app.metrics.base import (
    MetricOptions,
    MetricResult,
    Offender,
    ThresholdConfig,
    evaluate_severity,
)
from app.models import Direction, RelationType, Schedule

_THRESHOLD = ThresholdConfig(
    value=90.0,
    direction=Direction.AT_LEAST,
    source=(
        "DCMA 14-Point Schedule Assessment, Metric 4 (Relationship Types): "
        ">= 90% of relations are Finish-to-Start"
    ),
)


def run_relationship_types(
    schedule: Schedule, options: MetricOptions | None = None
) -> MetricResult:
    """Percentage of relations that are Finish-to-Start.

    For this AT_LEAST metric the numerator is the FS count (the "good" measure), while the
    offenders are the **non-FS** relations (the complement). Offender keyed by successor;
    ``value`` = the predecessor's UniqueID (so the exact non-FS relation is identifiable).
    """
    relations = schedule.relations
    if not relations:
        raise MetricError("relationship-types metric requires at least one relation")
    names = {t.unique_id: t.name for t in schedule.tasks}

    fs_count = sum(1 for r in relations if r.relation_type == RelationType.FS)
    offenders = [
        Offender(r.successor_id, names[r.successor_id], float(r.predecessor_id))
        for r in relations
        if r.relation_type != RelationType.FS
    ]
    offenders.sort(key=lambda offender: (offender.unique_id, offender.value))
    denominator = len(relations)
    severity = evaluate_severity(100.0 * fs_count / denominator, _THRESHOLD)
    return MetricResult(
        metric_id=4,
        metric_name="Relationship Types (% Finish-to-Start)",
        severity=severity,
        threshold=_THRESHOLD,
        numerator=fs_count,
        denominator=denominator,
        offenders=tuple(offenders),
    )
