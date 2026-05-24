"""Multi-version trend analysis: how a schedule's health moves across status dates.

TOOL-ORIGINAL EXTENSION (parity-honesty rule, CLAUDE.md / LAW 2)
================================================================
The per-version *inputs* are reference-faithful -- each :class:`VersionSnapshot`
holds objective values from the frozen CPM engine and the DCMA-14 assessment
(``project_finish``, the critical-path size, the DCMA integrity score). But the
cross-version *trajectory* framing -- "the finish date slipped N working days
over the series", the float-erosion bands (delegated to :mod:`float_analysis`) --
is this tool's own analytical layer. Acumen Fuse / Steelray-SSI / MS Project
report each version's numbers; assembling them into a labeled trend across
status-dated versions is the extension. Every result therefore carries
``is_extension=True`` and must never be presented as reference-tool parity.

Method
------
Versions are ordered by absolute ``status_date`` (via
:func:`~schedule_forensics.version_matcher.order_versions`, which raises if any
version lacks one). Each version is analyzed once (:func:`analyze_schedule`) into
a :class:`VersionSnapshot`. The finish-date drift is ``last - first`` of the
working-day finish across the series (positive == the project got later). Per-task
total-float trends are delegated unchanged to
:func:`~schedule_forensics.float_analysis.analyze_float_trends`. Nothing is
fabricated: a version whose CPM cannot be computed contributes ``None`` finish /
band ``RED`` from the underlying analysis, and an empty input yields an empty
report (LAW 2, fail closed).
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.analysis import analyze_schedule
from schedule_forensics.exec_summary import health_band
from schedule_forensics.float_analysis import FloatTrend, FloatTrendResult, analyze_float_trends
from schedule_forensics.schemas import Schedule
from schedule_forensics.version_matcher import order_versions

_MINUTES_PER_DAY: float = 480.0

# Float-trend bands worst-first, for stable display ordering of the tally.
_BAND_ORDER: tuple[FloatTrend, ...] = (
    FloatTrend.CRITICAL,
    FloatTrend.SEVERE_EROSION,
    FloatTrend.ERODING,
    FloatTrend.STABLE,
    FloatTrend.IMPROVING,
)


@dataclass(frozen=True)
class VersionSnapshot:
    """One version's headline metrics, in chronological position (objective values)."""

    index: int  # 0-based chronological position (0 == earliest status_date)
    status_date: dt.datetime | None
    project_finish: int | None  # working-minute offset from project_start (None if no CPM)
    project_finish_days: float | None  # offset / 480.0
    health_score: float | None  # % of runnable DCMA metrics that PASS
    band: str  # GREEN / YELLOW / RED (from health_band)
    n_critical: int  # tasks on the critical path


@dataclass(frozen=True)
class TrendReport:
    """Bundle of multi-version trends (TOOL-ORIGINAL EXTENSION; ``is_extension=True``).

    ``snapshots`` is chronological (earliest first). ``finish_days_net_change`` is
    ``last - first`` working-day finish (positive == slip); ``None`` when either end
    has no computable finish. ``band_counts`` tallies the float-erosion bands across
    all tracked tasks. Empty (no snapshots, no trends) when given no versions.
    """

    snapshots: tuple[VersionSnapshot, ...]
    float_trends: tuple[FloatTrendResult, ...]
    finish_days_first: float | None
    finish_days_last: float | None
    finish_days_net_change: float | None
    band_counts: dict[str, int]
    is_extension: bool = True

    @property
    def n_versions(self) -> int:
        return len(self.snapshots)

    def worst_eroders(self, limit: int = 10) -> tuple[FloatTrendResult, ...]:
        """The most float-negative task trends (eroding/critical), worst first.

        Sorted by ``net_change_days`` ascending (largest float loss first), then by
        ``latest_float_days`` ascending (least slack first) as a tiebreaker. Only
        tasks that are CRITICAL or have lost float (``net_change_days < 0``) are
        included -- improving/stable tasks are not "eroders".
        """
        eroders = [
            t
            for t in self.float_trends
            if t.trend in (FloatTrend.CRITICAL, FloatTrend.SEVERE_EROSION, FloatTrend.ERODING)
            or t.net_change_days < 0
        ]
        eroders.sort(key=lambda t: (t.net_change_days, t.latest_float_days))
        return tuple(eroders[:limit])


def analyze_version_trends(schedules: Sequence[Schedule]) -> TrendReport:
    """Compose per-version snapshots + finish drift + float trends across the series.

    TOOL-ORIGINAL EXTENSION (see the module docstring): the returned report carries
    ``is_extension=True``. Orders versions by absolute ``status_date`` (raising
    ``VersionMatchError`` if any lacks one), analyzes each once, and delegates the
    per-task float trends to :func:`analyze_float_trends`. An empty input yields an
    empty report.
    """
    empty_counts = {band.value: 0 for band in _BAND_ORDER}
    if not schedules:
        return TrendReport((), (), None, None, None, empty_counts)

    ordered = order_versions(schedules)  # ascending status_date; raises if any missing
    snapshots: list[VersionSnapshot] = []
    for index, schedule in enumerate(ordered):
        analysis = analyze_schedule(schedule)
        finish = analysis.project_finish
        snapshots.append(
            VersionSnapshot(
                index=index,
                status_date=schedule.status_date,
                project_finish=finish,
                project_finish_days=(finish / _MINUTES_PER_DAY) if finish is not None else None,
                health_score=analysis.health_score,
                band=health_band(analysis).value,
                n_critical=len(analysis.critical_path),
            )
        )

    float_trends = analyze_float_trends(ordered)

    first_days = snapshots[0].project_finish_days
    last_days = snapshots[-1].project_finish_days
    net_change = (
        last_days - first_days if (first_days is not None and last_days is not None) else None
    )

    tally = Counter(t.trend.value for t in float_trends)
    band_counts = {band.value: tally.get(band.value, 0) for band in _BAND_ORDER}

    return TrendReport(
        snapshots=tuple(snapshots),
        float_trends=float_trends,
        finish_days_first=first_days,
        finish_days_last=last_days,
        finish_days_net_change=net_change,
        band_counts=band_counts,
    )
