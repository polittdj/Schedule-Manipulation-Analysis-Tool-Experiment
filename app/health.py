"""Schedule health / manipulation-indicator synthesis over the DCMA metrics.

A first-order integrity score: the share of *runnable* DCMA metrics that PASS. The DCMA
findings (leads, hard constraints, invalid dates, missed tasks, ...) are the classic indicators
of schedule manipulation or poor practice, so failing metrics are surfaced as findings.

This is an honest aggregation of the metric results, NOT a validated manipulation-detection
model. It does, however, carry the regression guard for the known "always-100" scoring bug: a
schedule with any failing metric must score below 100.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.metrics.base import MetricResult
from app.models import Severity


@dataclass(frozen=True, slots=True)
class HealthAssessment:
    metrics_run: int
    metrics_passed: int
    metrics_failed: int
    score: float  # 100 * passed / run; 0.0 when nothing ran
    findings: tuple[int, ...]  # metric_ids that failed (quality / manipulation indicators)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics_run": self.metrics_run,
            "metrics_passed": self.metrics_passed,
            "metrics_failed": self.metrics_failed,
            "score": self.score,
            "findings": list(self.findings),
        }


def assess_health(metrics: Sequence[MetricResult]) -> HealthAssessment:
    """Aggregate metric results into an integrity score and a list of failing-metric findings."""
    run = len(metrics)
    passed = sum(1 for m in metrics if m.severity == Severity.PASS)
    failed = sum(1 for m in metrics if m.severity == Severity.FAIL)
    findings = tuple(sorted(m.metric_id for m in metrics if m.severity == Severity.FAIL))
    # Derived from the actual pass count — never hard-coded — so findings always pull it below 100.
    score = 100.0 * passed / run if run else 0.0
    return HealthAssessment(
        metrics_run=run,
        metrics_passed=passed,
        metrics_failed=failed,
        score=score,
        findings=findings,
    )
