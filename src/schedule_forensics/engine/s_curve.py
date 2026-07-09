"""S-curve — cumulative planned vs actual progress across the loaded versions (animated view).

For each loaded version, on a shared calendar-month axis, two cumulative curves over the
schedule's non-summary activities:

* **planned** — the running share of activities whose *baseline* finish falls on or before
  each month (what the plan said would be done by then);
* **actual / forecast** — the running share whose *current* finish (actual where complete,
  otherwise the forecast/scheduled finish) falls on or before each month.

Plotted version by version it animates into the familiar lazy-S, with the actual curve lagging
(or leading) the plan — the data-date marker shows where actuals end and forecast begins. Every
count is computed from the loaded files; nothing is fabricated.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.month_axis import bucket as _bucket
from schedule_forensics.engine.month_axis import month_index as _ym
from schedule_forensics.engine.month_axis import month_label as _label
from schedule_forensics.model.schedule import Schedule

#: Hard cap on the shared month axis so a stray far-future date cannot explode the chart; over
#: the cap the oldest months are shed (their already-finished work is still counted into the
#: cumulative baseline, so the curve never loses progress — see ``_cumulative_pct``).
_MAX_MONTHS = 60


@dataclass(frozen=True)
class TrackedActivity:
    """Where ONE tracked activity's finishes land on the shared month axis for one version
    (operator 2026-07-09: visualize up to 20 chosen UIDs on the animated S-curve, beside the
    optional primary target). ``None`` indices mean absent this version or off-axis."""

    uid: int
    name: str
    finish_index: int | None  # month index of the current (forecast/actual) finish
    baseline_index: int | None  # month index of the baseline finish
    percent_complete: float | None  # None when the activity is absent this version


@dataclass(frozen=True)
class SCurveVersion:
    """One version's cumulative planned / actual curves over the shared month axis (percent)."""

    label: str
    status_index: int | None  # index of the data-date month on the shared axis (None = off-axis)
    status_date: str | None  # the exact data date (ISO) — shown even when it falls off the axis
    activities: int  # the non-summary activity count this version is normalized against
    planned: tuple[float, ...]  # cumulative % with a baseline finish on/before each month
    actual: tuple[float, ...]  # cumulative % with an actual/forecast finish on/before each month
    #: operator 2026-07-09: up to 20 operator-chosen activities marked on the curve.
    tracked: tuple[TrackedActivity, ...] = ()


@dataclass(frozen=True)
class SCurve:
    """The whole workbook's S-curve dataset: one shared month axis + per-version curves."""

    month_labels: tuple[str, ...]
    versions: tuple[SCurveVersion, ...]


def _cumulative_pct(dates: list[dt.datetime], lo: int, n: int, total: int) -> tuple[float, ...]:
    """Cumulative share (0-100) of ``total`` whose date falls on/before each of ``n`` months.

    Dates before the window are folded into the starting running count, so shedding the oldest
    months (the axis cap) never drops already-completed work from the cumulative curve.
    """
    if total <= 0:
        return tuple(0.0 for _ in range(n))
    counts = _bucket(dates, lo, n)
    running = sum(1 for d in dates if _ym(d) < lo)  # finished before the window opened
    out: list[float] = []
    for c in counts:
        running += c
        out.append(round(running / total * 100, 1))
    return tuple(out)


def compute_s_curve(schedules: Sequence[Schedule], track_uids: Sequence[int] = ()) -> SCurve:
    """Cumulative planned vs actual/forecast progress curves for ``schedules`` (oldest → newest).

    Requires at least one version with finish dates. The month axis is shared across versions so
    the per-version curves animate on one fixed scale.

    ``track_uids`` (operator 2026-07-09) marks up to 20 chosen activities on each version's
    curve (``SCurveVersion.tracked`` — the month of their current and baseline finishes), so
    the animated chart can visualize specific work moving against the curve. The caller caps
    the count; an unknown UID carries ``None`` positions (never fabricated).
    """
    if not schedules:
        raise ValueError("the S-curve needs at least one schedule version")
    per: list[tuple[Schedule, int, list[dt.datetime], list[dt.datetime]]] = []
    months: list[int] = []
    for sch in schedules:
        tasks = non_summary(sch)
        baseline = [t.baseline_finish for t in tasks if t.baseline_finish is not None]
        current = [t.finish for t in tasks if t.finish is not None]
        per.append((sch, len(tasks), baseline, current))
        months.extend(_ym(d) for d in (*baseline, *current))
    if not months:
        raise ValueError("no finish dates found in any loaded version (nothing to plot)")
    lo, hi = min(months), max(months)
    over = hi - lo + 1 - _MAX_MONTHS
    if over > 0:
        lo += over  # shed the oldest months; pre-window finishes still seed the cumulative
    n = hi - lo + 1

    versions: list[SCurveVersion] = []
    for sch, total, baseline, current in per:
        status = _ym(sch.status_date) if sch.status_date is not None else None

        def _on_axis(d: dt.datetime | None) -> int | None:
            if d is None:
                return None
            ym = _ym(d)
            return ym - lo if lo <= ym <= hi else None

        by_id = {t.unique_id: t for t in non_summary(sch)}
        tracked = tuple(
            TrackedActivity(
                uid=uid,
                name=by_id[uid].name if uid in by_id else f"UID {uid}",
                finish_index=_on_axis(by_id[uid].finish) if uid in by_id else None,
                baseline_index=_on_axis(by_id[uid].baseline_finish) if uid in by_id else None,
                percent_complete=by_id[uid].percent_complete if uid in by_id else None,
            )
            for uid in track_uids
        )
        versions.append(
            SCurveVersion(
                label=sch.source_file or sch.name,
                status_index=(status - lo) if status is not None and lo <= status <= hi else None,
                status_date=sch.status_date.date().isoformat() if sch.status_date else None,
                activities=total,
                planned=_cumulative_pct(baseline, lo, n, total),
                actual=_cumulative_pct(current, lo, n, total),
                tracked=tracked,
            )
        )
    return SCurve(
        month_labels=tuple(_label(m) for m in range(lo, hi + 1)),
        versions=tuple(versions),
    )
