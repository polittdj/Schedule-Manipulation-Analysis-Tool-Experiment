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
from schedule_forensics.engine.metrics import (
    compute_cei,
    compute_hmi,
    compute_schedule_quality,
)
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
    worst_index: int | None = None  # index of the worst version (None: constant or neutral)
    worst_offender_uids: tuple[int, ...] = ()  # the worst version's offending activities
    #: offending activity UIDs PER version (oldest → newest, parallel to ``values``) — the
    #: per-metric drill-down (M18 item 8). Empty per version for neutral ratios (no offenders).
    offenders_by_version: tuple[tuple[int, ...], ...] = ()

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


@dataclass(frozen=True)
class HMISeries:
    """Hit or Miss Index across consecutive version pairs (oldest → newest).

    Each version is scored against the period since its **predecessor's** data date
    (``ProjectPreviousTimeNow``); the first version has no predecessor, so its entries are ``None``.
    Values are the period HMI (hits ÷ baselined-due-this-period); ``None`` also marks a version with
    no due activities in the period. Offenders are the misses per version (parallel to the values).
    """

    labels: tuple[str, ...]
    task_values: tuple[float | None, ...]
    milestone_values: tuple[float | None, ...]
    task_offenders: tuple[tuple[int, ...], ...]
    milestone_offenders: tuple[tuple[int, ...], ...]


def compute_hmi_trend(schedules: Sequence[Schedule]) -> HMISeries:
    """HMI per version, each scored over the period since the previous version's data date.

    ``schedules`` must be ordered oldest → newest (use :func:`order_versions`). Needs at least two
    versions — HMI is inherently period-over-period.
    """
    if len(schedules) < 2:
        raise ValueError("an HMI trend needs at least two schedule versions")
    labels = tuple(_label(s) for s in schedules)
    task_vals: list[float | None] = []
    ms_vals: list[float | None] = []
    task_off: list[tuple[int, ...]] = []
    ms_off: list[tuple[int, ...]] = []
    for i, sch in enumerate(schedules):
        prev_now = schedules[i - 1].status_date if i > 0 else None
        hmi = compute_hmi(sch, prev_now)
        task, milestone = hmi["hmi_tasks"], hmi["hmi_milestones"]
        task_vals.append(task.value if task.population else None)
        ms_vals.append(milestone.value if milestone.population else None)
        task_off.append(task.offender_uids)
        ms_off.append(milestone.offender_uids)
    return HMISeries(
        labels=labels,
        task_values=tuple(task_vals),
        milestone_values=tuple(ms_vals),
        task_offenders=tuple(task_off),
        milestone_offenders=tuple(ms_off),
    )


@dataclass(frozen=True)
class CEISeries:
    """Current Execution Index across consecutive version pairs (oldest → newest).

    Each version is scored against the period since its **predecessor's** data date: of the
    activities the *prior* schedule forecast to finish in the period, how many actually finished by
    this version's data date. The first version has no predecessor, so its entries are ``None``
    (matching Acumen's single-period N/A). Offenders are the misses per version.
    """

    labels: tuple[str, ...]
    task_values: tuple[float | None, ...]
    milestone_values: tuple[float | None, ...]
    task_offenders: tuple[tuple[int, ...], ...]
    milestone_offenders: tuple[tuple[int, ...], ...]
    # variant cuts (ADR-0101), parallel to the versions: task starts, the critical-path subset, and
    # the early-completion-credited "adjusted" task finish. None on the first version / when empty.
    start_values: tuple[float | None, ...] = ()
    critical_values: tuple[float | None, ...] = ()
    adjusted_values: tuple[float | None, ...] = ()


def compute_cei_trend(schedules: Sequence[Schedule]) -> CEISeries:
    """CEI per version, each scored over the period since the previous version's data date.

    ``schedules`` must be ordered oldest → newest (use :func:`order_versions`). Needs at least two
    versions — CEI is inherently period-over-period (prior forecast vs current actuals).
    """
    if len(schedules) < 2:
        raise ValueError("a CEI trend needs at least two schedule versions")
    labels = tuple(_label(s) for s in schedules)
    task_vals: list[float | None] = []
    ms_vals: list[float | None] = []
    task_off: list[tuple[int, ...]] = []
    ms_off: list[tuple[int, ...]] = []
    start_vals: list[float | None] = []
    crit_vals: list[float | None] = []
    adj_vals: list[float | None] = []

    def _v(result: object) -> float | None:
        return result.value if result.population else None  # type: ignore[attr-defined]

    for i, sch in enumerate(schedules):
        if i == 0:
            for lst in (task_vals, ms_vals, start_vals, crit_vals, adj_vals):
                lst.append(None)
            task_off.append(())
            ms_off.append(())
            continue
        cei = compute_cei(schedules[i - 1], sch)
        task, milestone = cei["cei_tasks"], cei["cei_milestones"]
        task_vals.append(_v(task))
        ms_vals.append(_v(milestone))
        start_vals.append(_v(cei["cei_task_starts"]))
        crit_vals.append(_v(cei["cei_critical"]))
        adj_vals.append(_v(cei["cei_tasks_adjusted"]))
        task_off.append(task.offender_uids)
        ms_off.append(milestone.offender_uids)
    return CEISeries(
        labels=labels,
        task_values=tuple(task_vals),
        milestone_values=tuple(ms_vals),
        task_offenders=tuple(task_off),
        milestone_offenders=tuple(ms_off),
        start_values=tuple(start_vals),
        critical_values=tuple(crit_vals),
        adjusted_values=tuple(adj_vals),
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
        worst_index: int | None = None
        worst_offenders: tuple[int, ...] = ()
        offenders_by_version = tuple(r.offender_uids for r in results)
        if lower_is_better is not None and any(v != values[0] for v in values):
            worst_index = max(range(len(values)), key=lambda i: values[i])
            if not lower_is_better:
                worst_index = min(range(len(values)), key=lambda i: values[i])
            worst_offenders = offenders_by_version[worst_index]
        out.append(
            MetricTrend(
                metric_id=metric_id,
                name=results[0].name,
                labels=labels,
                values=values,
                lower_is_better=lower_is_better,
                worst_index=worst_index,
                worst_offender_uids=worst_offenders,
                offenders_by_version=offenders_by_version,
            )
        )
    return tuple(out)
