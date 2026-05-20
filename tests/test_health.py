"""Schedule health score — including the regression guard for the 'always-100' scoring bug."""

from __future__ import annotations

from app.health import assess_health
from app.metrics.base import MetricResult, ThresholdConfig
from app.models import Direction, Severity

_THRESHOLD = ThresholdConfig(5.0, Direction.AT_MOST, "x")


def _metric(metric_id: int, severity: Severity) -> MetricResult:
    return MetricResult(metric_id, f"m{metric_id}", severity, _THRESHOLD, 0, 1, ())


def test_health_all_pass_scores_100() -> None:
    health = assess_health([_metric(1, Severity.PASS), _metric(2, Severity.PASS)])
    assert health.score == 100.0
    assert health.metrics_failed == 0
    assert health.findings == ()


def test_health_is_not_always_100_when_a_metric_fails() -> None:
    # Regression guard: a failing metric MUST pull the score below 100 (the 'always-100' bug).
    health = assess_health(
        [_metric(1, Severity.PASS), _metric(2, Severity.FAIL), _metric(5, Severity.FAIL)]
    )
    assert health.score < 100.0
    assert health.score == 100.0 / 3  # one of three passed
    assert health.metrics_failed == 2
    assert health.findings == (2, 5)


def test_health_empty_scores_zero() -> None:
    health = assess_health([])
    assert health.score == 0.0
    assert health.metrics_run == 0
