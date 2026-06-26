"""Vertical-integration check — do summary (rollup) bars envelope the work beneath them?

An integrated master schedule is *vertically integrated* when every summary's date span covers all
the detail activities that roll up into it (the parent bar brackets its children). This check flags
summaries whose **stored** span does not envelope their WBS descendants: the summary starts after
its earliest descendant, or finishes before its latest — a rollup the file itself contradicts.

Hierarchy is derived from the WBS code (a descendant's WBS starts with the summary's WBS + "."), and
only **stored** dates are compared (the rollup the source file claims), so a violation is exactly
verifiable against the file — no CPM, no new schedule math. A summary with no WBS code, no stored
dates, or no dated descendants is *not evaluable* and is skipped (never a fabricated finding).

Parity-isolated lightweight dataclasses (NOT ``MetricResult``) — out of the Fuse ribbon and the
metric-dictionary coverage test, like ``health_extra`` / ``logic_integrity`` / ``constraint_health``
(presentation/structural, not a gate-locked figure).

Sources: NASA Schedule Management Handbook (vertical traceability / IMS-level integration,
Fig. 6-9); assessment Deck-1 (inconsistent vertical integration).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from schedule_forensics.model.schedule import Schedule

#: cap the offender list carried to the UI (the activity grid is the full record)
_OFFENDER_CAP = 50


@dataclass(frozen=True)
class VerticalIntegration:
    """The vertical-integration check for one schedule (summary-envelope consistency)."""

    count: int  # summaries whose stored span does not envelope their descendants
    population: int  # summaries that were evaluable (have a WBS code, stored dates, dated children)
    offenders: tuple[int, ...]  # the offending summary UniqueIDs (capped)
    description: str


_DESCRIPTION = (
    "Summary (rollup) activities whose stored date span does not envelope the detail activities "
    "beneath them — the summary starts after its earliest descendant or finishes before its latest "
    "(by WBS nesting). A parent bar that does not bracket its children is an inconsistently "
    "integrated rollup; the schedule's vertical traceability cannot be trusted."
)


def _dated(schedule: Schedule, *, summary: bool) -> list[tuple[int, str, dt.datetime, dt.datetime]]:
    """(uid, wbs, start, finish) for tasks of the requested kind that carry all three — concrete
    (non-None) tuples so the envelope comparison is fully typed."""
    out: list[tuple[int, str, dt.datetime, dt.datetime]] = []
    for t in schedule.tasks:
        if t.is_summary != summary or not t.is_active:  # inactive excluded (ADR-0128)
            continue
        wbs = (t.wbs or "").strip()
        if wbs and t.start is not None and t.finish is not None:
            out.append((t.unique_id, wbs, t.start, t.finish))
    return out


def compute_vertical_integration(schedule: Schedule) -> VerticalIntegration:
    """Flag summaries whose stored span does not envelope their WBS descendants (stored dates)."""
    leaves = _dated(schedule, summary=False)
    summaries = _dated(schedule, summary=True)

    offenders: list[int] = []
    evaluable = 0
    for uid, wbs, s_start, s_finish in summaries:
        prefix = wbs + "."
        kids = [(start, finish) for _u, w, start, finish in leaves if w.startswith(prefix)]
        if not kids:
            continue
        evaluable += 1
        earliest = min(start for start, _f in kids)
        latest = max(finish for _s, finish in kids)
        if s_start > earliest or s_finish < latest:
            offenders.append(uid)

    offenders.sort()
    return VerticalIntegration(
        count=len(offenders),
        population=evaluable,
        offenders=tuple(offenders[:_OFFENDER_CAP]),
        description=_DESCRIPTION,
    )
