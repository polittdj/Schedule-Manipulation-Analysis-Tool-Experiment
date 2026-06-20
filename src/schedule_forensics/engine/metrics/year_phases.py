"""Per-year phase distribution — how the work spreads across calendar years (the Year view).

A lightweight, presentation-oriented breakdown (NOT a :class:`MetricResult`, like
``schedule_card`` / ``wbs_breakdown``): bin a schedule's real activities by a chosen **date
basis** — start / finish / baseline finish / actual finish — into calendar years, and split each
year into complete / in-progress / planned with a milestone count. This is the operator's "Year
Trend / Phase" view; the binning basis is the operator's choice (offered as multiple options in
the UI), since which date a year should be keyed on is a judgement call.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from schedule_forensics.model.schedule import Schedule

#: Selectable binning bases (key -> human label). ``finish`` is the default.
YEAR_BASES: dict[str, str] = {
    "finish": "Scheduled / forecast finish",
    "start": "Start",
    "baseline_finish": "Baseline finish",
    "actual_finish": "Actual finish",
}


@dataclass(frozen=True)
class YearPhaseRow:
    """One calendar year's activity makeup on the chosen date basis."""

    year: int
    total: int
    complete: int
    in_progress: int
    planned: int
    milestones: int


@dataclass(frozen=True)
class YearPhases:
    """The per-year phase breakdown for one schedule on one date basis."""

    basis: str
    undated: int  # non-summary activities with no date on the chosen basis (not binnable)
    rows: tuple[YearPhaseRow, ...]


def _basis_date(task: object, basis: str) -> dt.date | dt.datetime | None:
    if basis == "start":
        return getattr(task, "start", None)
    if basis == "baseline_finish":
        return getattr(task, "baseline_finish", None)
    if basis == "actual_finish":
        return getattr(task, "actual_finish", None)
    return getattr(task, "finish", None)


def compute_year_phases(schedule: Schedule, basis: str = "finish") -> YearPhases:
    """Bin ``schedule``'s non-summary activities into calendar years on ``basis``.

    An unknown ``basis`` falls back to ``finish``. Activities with no date on the chosen basis
    are counted in ``undated`` and left out of the year rows (never invented as year 0).
    """
    if basis not in YEAR_BASES:
        basis = "finish"
    buckets: dict[int, dict[str, int]] = {}
    undated = 0
    for task in schedule.tasks:
        if task.is_summary:
            continue
        when = _basis_date(task, basis)
        if when is None:
            undated += 1
            continue
        bucket = buckets.setdefault(
            when.year,
            {"total": 0, "complete": 0, "in_progress": 0, "planned": 0, "milestones": 0},
        )
        bucket["total"] += 1
        if task.is_milestone:
            bucket["milestones"] += 1
        pct = task.percent_complete or 0
        # robust "complete" (matches the path/grid views): a real .mpp/.xer may report a finished
        # activity at 99.x% while carrying an actual finish, so trust an actual finish too.
        if task.is_complete or task.actual_finish is not None:
            bucket["complete"] += 1
        elif 0 < pct < 100:
            bucket["in_progress"] += 1
        else:
            bucket["planned"] += 1
    rows = tuple(
        YearPhaseRow(
            year=year,
            total=b["total"],
            complete=b["complete"],
            in_progress=b["in_progress"],
            planned=b["planned"],
            milestones=b["milestones"],
        )
        for year, b in sorted(buckets.items())
    )
    return YearPhases(basis=basis, undated=undated, rows=rows)
