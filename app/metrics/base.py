"""Shared types and the severity helper for DCMA metrics.

Result types are frozen stdlib dataclasses (computed by trusted code; immutability only).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Direction, Severity


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    """A single, cited DCMA threshold. ``value`` is a percentage (e.g. 5.0 == 5%)."""

    value: float
    direction: Direction
    source: str


@dataclass(frozen=True, slots=True)
class Offender:
    """A flagged item; ``value`` is metric-specific (see docs/dcma-metrics.md)."""

    unique_id: int
    name: str
    value: float


@dataclass(frozen=True, slots=True)
class MetricOptions:
    """Tunable knobs. ``exclude_project_bookends`` exempts a lone open start/finish from the
    missing-logic metric (DCMA convention); default is the strict literal count."""

    exclude_project_bookends: bool = False


@dataclass(frozen=True, slots=True)
class MetricResult:
    """The outcome of one metric. ``numerator``/``denominator`` define the measured
    percentage that ``severity`` was derived from."""

    metric_id: int
    metric_name: str
    severity: Severity
    threshold: ThresholdConfig
    numerator: int
    denominator: int
    offenders: tuple[Offender, ...]
    # Index/ratio metrics (e.g. CPLI) report a directly-measured value instead of a count
    # percentage; ``None`` for the count-based metrics.
    measured: float | None = None

    @property
    def percentage(self) -> float:
        if self.denominator == 0:
            return 0.0
        return 100.0 * self.numerator / self.denominator


def evaluate_severity(measured_percentage: float, threshold: ThresholdConfig) -> Severity:
    """Map a measured percentage to PASS/FAIL against a single cited threshold.

    DCMA metrics are binary against one threshold; emitting WARN would require a second,
    uncited threshold (i.e. invented fidelity), so WARN is never produced here. See
    FIDELITY-DECISION-dcma-severity.md.
    """
    if threshold.direction == Direction.AT_MOST:
        return Severity.PASS if measured_percentage <= threshold.value else Severity.FAIL
    return Severity.PASS if measured_percentage >= threshold.value else Severity.FAIL
