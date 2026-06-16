"""Finish and slippage month curves — the deck's Finishes / DATA Date Finishes / Slippage
pages (PBIX pages 6, 7, 12; ADR-0040).

Three related monthly-count views over the non-summary activities, all on one shared
month axis so they overlay and compare cleanly:

* **Finishes** (deck p6) — for a single version, **actual** finishes vs **baseline**
  finishes per calendar month: where the work was planned to land vs where it actually
  did. The gap between the two curves is the slip, read month by month.
* **DATA Date Finishes** (deck p7) — the multi-version sibling: each loaded version
  (by data date) contributes a baseline-finish curve and an actual-finish curve, so the
  bow wave of slipped finishes is visible as the actual curves push right version over
  version.
* **Slippage** (deck p12) — per version, the **start** curve (count of activities by
  their current/forecast or actual start month) and the **finish** curve (by finish
  month). Start-curve and finish-curve drift across versions is the slippage signature.

Every count is computed from the loaded files on the spot — nothing is fabricated. The
axis spans the full data range across every version, capped to keep a stray far-future
date from exploding the chart (oldest months shed first). Counts use the activity's most
authoritative date: a started activity's **actual** start/finish where present, else its
current scheduled date; the baseline curves always read the baseline dates.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.month_axis import bucket, month_index, month_label
from schedule_forensics.model.schedule import Schedule

#: Hard cap on the axis length (months). Over the cap, the oldest months are shed first
#: — the project's later, more decision-relevant months stay on-axis.
_MAX_MONTHS = 60


@dataclass(frozen=True)
class VersionCurves:
    """One version's monthly start/finish curves over the shared month axis."""

    label: str  # the version label (source file or name)
    status_date: str | None  # the data date (ISO), if recorded
    status_index: int | None  # index of the data-date month on the shared axis (None = off-axis)
    baseline_finishes: tuple[int, ...]  # per month: baseline finishes
    actual_finishes: tuple[int, ...]  # per month: actual (else scheduled) finishes
    baseline_starts: tuple[int, ...]  # per month: baseline starts
    actual_starts: tuple[int, ...]  # per month: actual (else scheduled) starts


@dataclass(frozen=True)
class MonthCurves:
    """The workbook's finish/slippage dataset: one shared month axis + per-version curves."""

    month_labels: tuple[str, ...]
    versions: tuple[VersionCurves, ...]


def _finish_dates(sch: Schedule) -> list[dt.datetime]:
    """Each non-summary activity's most authoritative finish (actual, else scheduled)."""
    out: list[dt.datetime] = []
    for t in non_summary(sch):
        d = t.actual_finish if t.actual_finish is not None else t.finish
        if d is not None:
            out.append(d)
    return out


def _start_dates(sch: Schedule) -> list[dt.datetime]:
    """Each non-summary activity's most authoritative start (actual, else scheduled)."""
    out: list[dt.datetime] = []
    for t in non_summary(sch):
        d = t.actual_start if t.actual_start is not None else t.start
        if d is not None:
            out.append(d)
    return out


def _baseline_finish_dates(sch: Schedule) -> list[dt.datetime]:
    return [t.baseline_finish for t in non_summary(sch) if t.baseline_finish is not None]


def _baseline_start_dates(sch: Schedule) -> list[dt.datetime]:
    return [t.baseline_start for t in non_summary(sch) if t.baseline_start is not None]


def compute_month_curves(schedules: Sequence[Schedule]) -> MonthCurves:
    """Monthly start/finish curves for ``schedules`` (given oldest → newest by data date).

    Requires at least one schedule with at least one start or finish date. The month axis
    is shared across versions and spans the full data range, capped to ``_MAX_MONTHS``
    (oldest months shed first).
    """
    if not schedules:
        raise ValueError("the month-curve analysis needs at least one schedule version")

    per_version: list[
        tuple[list[dt.datetime], list[dt.datetime], list[dt.datetime], list[dt.datetime]]
    ] = []
    all_months: list[int] = []
    status_yms: list[int | None] = []
    for sch in schedules:
        bf = _baseline_finish_dates(sch)
        af = _finish_dates(sch)
        bs = _baseline_start_dates(sch)
        as_ = _start_dates(sch)
        per_version.append((bf, af, bs, as_))
        all_months.extend(month_index(d) for d in (*bf, *af, *bs, *as_))
        status_yms.append(month_index(sch.status_date) if sch.status_date is not None else None)

    if not all_months:
        raise ValueError("no start or finish dates found in any loaded version (nothing to plot)")

    lo, hi = min(all_months), max(all_months)
    over = hi - lo + 1 - _MAX_MONTHS
    if over > 0:
        lo += over  # shed the oldest months; keep the later, decision-relevant range
    n = hi - lo + 1

    versions: list[VersionCurves] = []
    for sch, (bf, af, bs, as_), status in zip(schedules, per_version, status_yms, strict=True):
        versions.append(
            VersionCurves(
                label=sch.source_file or sch.name,
                status_date=sch.status_date.date().isoformat() if sch.status_date else None,
                status_index=(status - lo) if status is not None and lo <= status <= hi else None,
                baseline_finishes=bucket(bf, lo, n),
                actual_finishes=bucket(af, lo, n),
                baseline_starts=bucket(bs, lo, n),
                actual_starts=bucket(as_, lo, n),
            )
        )

    return MonthCurves(
        month_labels=tuple(month_label(m) for m in range(lo, hi + 1)),
        versions=tuple(versions),
    )
