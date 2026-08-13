"""The cross-version series — every loaded version reduced to one comparable row.

The multi-version pages each answer one question across the workbook (quality trend, critical-path
evolution, the animated S-curve). Nothing reduced the whole population to a single **series** that
says, version by version, *where the S-curve stood at that version's own data date and where the
schedule logic said the project would finish*. Without it a cross-version question ("across these
31 updates, is the project improving?") had no engine answer to cite, and the AI Q&A fact base —
which is built from the executive briefing — described only the newest version plus the latest
pair (ADR-0392).

Two figures per version, both engine-computed, neither imputed:

* **the S-curve point** — the cumulative share of the version's non-summary activities whose
  *baseline* finish (planned) and whose *current* finish (actual/forecast) fall on or before the
  version's own data date, using the S-curve's calendar-month grain. ``None`` when the version
  carries no data date: a version with no status point is reported as unreadable, never as 0%.
* **the schedule-logic finish** — that version's ``CPMResult.project_finish`` (ADR-0310: this is
  the network's computed finish, NOT a progress-aware forecast, and is labelled as such).

**Why this recomputes rather than reading :func:`compute_s_curve`.** The animated curve shares one
month axis across every version and caps it at 60 months, shedding the oldest months when a long
programme overruns the cap. A version whose data date falls in a shed month has ``status_index is
None`` and therefore no readable point on that axis — with 31 monthly updates over a multi-year
programme that silently drops the early versions from any series read off the axis. Evaluating each
version at its own data-date month needs no shared axis at all, so the cap cannot reach it.

The values are nonetheless **identical** to the animated curve's wherever that curve can be read:
``_cumulative_pct`` folds every pre-window finish into its running count, so the cumulative value
at a given month does not depend on where the axis starts.
``tests/engine/test_version_series.py::test_matches_the_s_curve_at_every_on_axis_status_month``
pins that equivalence — one definition of "the S-curve", two evaluation paths that must agree.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.month_axis import month_index as _ym
from schedule_forensics.engine.trend import order_versions
from schedule_forensics.model.schedule import Schedule

#: Gap movement (in percentage points) below which two versions are called unchanged. The curves
#: are rounded to 1 dp, so anything under a tenth of a point is rounding, not movement.
_FLAT_EPSILON = 0.05


@dataclass(frozen=True)
class VersionPoint:
    """One loaded version reduced to its comparable figures."""

    label: str
    status_date: dt.date | None  # the version's data date (None = not statused)
    activities: int  # non-summary activity count — the denominator of both percentages
    planned_pct: float | None  # cumulative % baseline-finished by the data date
    actual_pct: float | None  # cumulative % actually/forecast-finished by the data date
    complete_pct: float | None  # % of activities flagged complete in the file
    finish: dt.date | None  # this version's schedule-logic finish (CPM), if solved

    @property
    def gap_pct(self) -> float | None:
        """``actual - planned`` in percentage points; negative = behind plan. ``None`` when the
        version has no readable status point (never 0 — "no data date" is not "on plan")."""
        if self.planned_pct is None or self.actual_pct is None:
            return None
        return round(self.actual_pct - self.planned_pct, 1)

    @property
    def is_readable(self) -> bool:
        """True when this version has an S-curve point — it carries a data date AND has
        activities in scope to measure. Either absence makes the point unreadable, not zero."""
        return self.gap_pct is not None


@dataclass(frozen=True)
class VersionSeries:
    """Every loaded version as one ordered series (oldest → newest by data date)."""

    points: tuple[VersionPoint, ...]

    @property
    def readable(self) -> tuple[VersionPoint, ...]:
        """The versions that have an S-curve point to compare (see ``VersionPoint.is_readable``)."""
        return tuple(p for p in self.points if p.is_readable)

    @property
    def _gaps(self) -> list[float]:
        """The readable versions' gaps, oldest → newest. Narrowed here once so the trend
        properties below never have to re-assert what ``is_readable`` already guarantees."""
        return [p.gap_pct for p in self.points if p.gap_pct is not None]

    @property
    def gap_delta(self) -> float | None:
        """Change in the plan-vs-actual gap from the first readable version to the last, in
        percentage points. Positive = the gap closed (execution caught up on the plan);
        negative = the gap widened. ``None`` with fewer than two readable versions."""
        gaps = self._gaps
        if len(gaps) < 2:
            return None
        return round(gaps[-1] - gaps[0], 1)

    @property
    def direction(self) -> str:
        """The mechanical verdict on the gap: ``"narrowed"`` / ``"widened"`` / ``"unchanged"``,
        or ``"unreadable"`` when fewer than two versions carry a data date. This is arithmetic on
        the first and last readable points, not a judgement about the project."""
        delta = self.gap_delta
        if delta is None:
            return "unreadable"
        if delta > _FLAT_EPSILON:
            return "narrowed"
        if delta < -_FLAT_EPSILON:
            return "widened"
        return "unchanged"

    @property
    def steps(self) -> tuple[int, int, int]:
        """``(narrowed, widened, unchanged)`` counts over consecutive readable version pairs —
        the volatility behind the first-to-last verdict (a net-flat series can still be churning).
        """
        narrowed = widened = flat = 0
        for prev, cur in pairwise(self._gaps):
            move = cur - prev
            if move > _FLAT_EPSILON:
                narrowed += 1
            elif move < -_FLAT_EPSILON:
                widened += 1
            else:
                flat += 1
        return narrowed, widened, flat

    @property
    def finish_movement_days(self) -> int | None:
        """Calendar days the schedule-logic finish moved from the first version that has one to
        the last. Positive = the computed finish moved later. ``None`` with fewer than two."""
        finishes = [p.finish for p in self.points if p.finish is not None]
        if len(finishes) < 2:
            return None
        return (finishes[-1] - finishes[0]).days


def _cumulative_pct_at(dates: list[dt.datetime], through_month: int, total: int) -> float | None:
    """Share (0-100, 1 dp) of ``total`` whose date falls in or before month ``through_month``.

    The S-curve's own cumulative definition evaluated at a single month — see the module
    docstring on why this needs no shared axis to agree with :func:`compute_s_curve`.

    ``None`` when there is no population to measure (a filter scoped the version to nothing).
    Returning 0.0 there would report a gap of +0.0 — which reads as "exactly on plan" — for a
    version that was never measured at all (Law 2: "—" never 0).
    """
    if total <= 0:
        return None
    done = sum(1 for d in dates if _ym(d) <= through_month)
    return round(done / total * 100, 1)


def compute_version_series(
    schedules: Sequence[Schedule], cpms: Sequence[CPMResult] | None = None
) -> VersionSeries:
    """Reduce every loaded version to one comparable row, oldest → newest by data date.

    ``cpms`` (parallel to ``schedules`` as given, matched by object identity before ordering) adds
    each version's schedule-logic finish; omit it and the finish column is simply absent. A version
    with no data date still appears — with unreadable percentages, never fabricated zeroes.
    """
    if not schedules:
        return VersionSeries(())
    by_obj: dict[int, CPMResult] = {}
    if cpms is not None:
        by_obj = {id(s): c for s, c in zip(schedules, cpms, strict=True)}
    points: list[VersionPoint] = []
    for sch in order_versions(schedules):
        tasks = non_summary(sch)
        total = len(tasks)
        planned: float | None = None
        actual: float | None = None
        if sch.status_date is not None:
            through = _ym(sch.status_date)
            planned = _cumulative_pct_at(
                [t.baseline_finish for t in tasks if t.baseline_finish is not None], through, total
            )
            actual = _cumulative_pct_at(
                [t.finish for t in tasks if t.finish is not None], through, total
            )
        cpm = by_obj.get(id(sch))
        points.append(
            VersionPoint(
                label=sch.source_file or sch.name,
                status_date=sch.status_date.date() if sch.status_date else None,
                activities=total,
                planned_pct=planned,
                actual_pct=actual,
                complete_pct=(
                    round(sum(1 for t in tasks if t.is_complete) / total * 100, 1)
                    if total
                    else None
                ),
                finish=(
                    offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar).date()
                    if cpm is not None
                    else None
                ),
            )
        )
    return VersionSeries(tuple(points))
