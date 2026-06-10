"""Cross-version quality trends — how each Schedule-Quality metric moves over versions.

Models the "Trend Analysis" section of an Acumen Fuse Diagnostic Executive Briefing: for
each §A Schedule-Quality metric, how the value develops across the loaded versions
(ordered by data date — the ProjectTimeNow pattern), with the best and worst version
named. ``MetricTrend.sentence()`` renders the briefing's phrasing ("Missing Logic:
increases over time with the best version being X (0) and the worst version being Y (3)").

Count-based metrics trend on their activity counts; Logic Density (a neutral ratio)
trends on its value and uses highest/lowest wording instead of best/worst.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics import compute_schedule_quality
from schedule_forensics.model.schedule import Schedule

#: §A metrics in briefing order; (metric_id, lower_is_better) — None = neutral (highest/lowest).
_TREND_METRICS: tuple[tuple[str, bool | None], ...] = (
    ("missing_logic", True),
    ("logic_density", None),
    ("critical", True),
    ("hard_constraints", True),
    ("negative_float", True),
    ("insufficient_detail", True),
    ("number_of_lags", True),
    ("number_of_leads", True),
    ("merge_hotspot", True),
)


@dataclass(frozen=True)
class MetricTrend:
    """One metric's movement across the version series (oldest → newest)."""

    metric_id: str
    name: str
    labels: tuple[str, ...]  # version labels, oldest first
    values: tuple[float, ...]  # the trended value per version (count, or value for ratios)
    lower_is_better: bool | None  # None = neutral metric (highest/lowest wording)

    @property
    def direction(self) -> str:
        """ "increases" / "decreases" / "remains constant" / "varies" (net first → last)."""
        if all(v == self.values[0] for v in self.values):
            return "remains constant"
        if self.values[-1] > self.values[0]:
            return "increases"
        if self.values[-1] < self.values[0]:
            return "decreases"
        return "varies"

    def _fmt(self, value: float) -> str:
        return f"{value:g}"

    def sentence(self) -> str:
        """The briefing sentence for this metric's trend."""
        if self.direction == "remains constant":
            return f"{self.name}: remains constant over time."
        lo_i = min(range(len(self.values)), key=lambda i: self.values[i])
        hi_i = max(range(len(self.values)), key=lambda i: self.values[i])
        if self.lower_is_better is None:
            return (
                f"{self.name}: {self.direction} over time with the highest version being "
                f"{self.labels[hi_i]} ({self._fmt(self.values[hi_i])}) and the lowest version "
                f"being {self.labels[lo_i]} ({self._fmt(self.values[lo_i])})."
            )
        best_i, worst_i = (lo_i, hi_i) if self.lower_is_better else (hi_i, lo_i)
        return (
            f"{self.name}: {self.direction} over time with the best version being "
            f"{self.labels[best_i]} ({self._fmt(self.values[best_i])}) and the worst version "
            f"being {self.labels[worst_i]} ({self._fmt(self.values[worst_i])})."
        )


def order_versions(schedules: Sequence[Schedule]) -> list[Schedule]:
    """Versions ordered for forensic comparison: by data date (oldest first), stably.

    Schedules without a status date keep their given (load) order, after the dated ones.
    """
    dated = [s for s in schedules if s.status_date is not None]
    undated = [s for s in schedules if s.status_date is None]
    dated.sort(key=lambda s: s.status_date or dt.datetime.min)
    return [*dated, *undated]


def _label(schedule: Schedule) -> str:
    return schedule.source_file or schedule.name


def compute_quality_trend(
    schedules: Sequence[Schedule],
    cpms: Sequence[CPMResult] | None = None,
) -> tuple[MetricTrend, ...]:
    """Per-metric Schedule-Quality trends across ``schedules`` (given oldest → newest).

    ``cpms`` (parallel to ``schedules``) avoids re-solving networks the caller already has.
    Requires at least two versions — a single snapshot has no trend.
    """
    if len(schedules) < 2:
        raise ValueError("a quality trend needs at least two schedule versions")
    if cpms is not None and len(cpms) != len(schedules):
        raise ValueError("cpms must parallel schedules")
    qualities = [
        compute_schedule_quality(s, cpms[i] if cpms is not None else None)
        for i, s in enumerate(schedules)
    ]
    labels = tuple(_label(s) for s in schedules)
    out: list[MetricTrend] = []
    for metric_id, lower_is_better in _TREND_METRICS:
        results = [q[metric_id] for q in qualities]
        values = tuple(
            float(r.value) if metric_id == "logic_density" else float(r.count) for r in results
        )
        out.append(
            MetricTrend(
                metric_id=metric_id,
                name=results[0].name,
                labels=labels,
                values=values,
                lower_is_better=lower_is_better,
            )
        )
    return tuple(out)
