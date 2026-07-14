"""Acumen Fuse "Ribbon" schedule-quality metrics, calibrated to the reference exports.

Fuse's Ribbon Analysis reports a per-project matrix of schedule-quality metrics. Several are
the DCMA-14 counts the tool already computes; a few are Fuse-proprietary. This module assembles
the full ribbon for one schedule, computing the not-yet-covered ones and sourcing the rest from
the DCMA audit, every value calibrated against the operator's Fuse workbook export (validated in
docs/FUSE-VALIDATION.md):

* **Missing Logic** — non-summary activities missing a predecessor and/or successor (ALL, not
  just incomplete — Fuse counts completed open-ends too; this is the DCMA-01 superset).
* **Logic Density™** — link density = (2 * logic links among non-summary activities) /
  non-summary activities (each link is one predecessor end + one successor end). Rounded
  half-up to 2 dp to match Fuse (e.g. 2.625 -> 2.63).
* **Critical** — INCOMPLETE non-summary activities on the critical path.
* **Merge Hotspot** — activities with **more than two** predecessors (a merge point).
* **Hard Constraints / Negative Float / Number of Lags / Number of Leads** — the DCMA-05 / -07
  / -03 / -02 counts (these already match Fuse exactly).
* **Avg / Max Float** — mean and maximum total float (working days) over incomplete activities
  (tool-computed; shown for context).

* **Insufficient Detail™** — count of activities whose duration exceeds 10% of the project
  span, per the NASA Acumen metric library (the Bible): ``SUM((OriginalDuration /
  (ProjectFinish-ProjectStart) > 0.1) * 1)`` — Fuse-validated ENGINE==FUSE on the delivered
  exports (P2=1, P5=0; ADR-0151/0155). Sourced from :mod:`schedule_quality` (single formula).

Float Ratio™ remains deliberately left out pending its exact Fuse formula (docs/FUSE-VALIDATION.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from schedule_forensics.engine.metrics._common import (
    effective_total_float,
    is_effective_critical,
    non_summary,
)

if TYPE_CHECKING:  # type-only — avoids a metrics -> dcma_audit -> metrics import cycle
    from schedule_forensics.engine.cpm import CPMResult
    from schedule_forensics.engine.dcma_audit import ScheduleAudit
    from schedule_forensics.model.schedule import Schedule

#: A predecessor count strictly above this is a "merge hotspot".
_MERGE_HOTSPOT_MIN_PREDS = 2


@dataclass(frozen=True)
class RibbonMetrics:
    """One schedule's Fuse Ribbon metric row."""

    missing_logic: int
    logic_density: float
    critical: int
    hard_constraints: int
    negative_float: int
    number_of_lags: int
    number_of_leads: int
    merge_hotspot: int
    avg_float_days: float
    max_float_days: float
    insufficient_detail: int
    #: Size of the incomplete-activity float population ``avg_float_days`` / ``max_float_days`` are
    #: computed over. ``0`` means that population is empty (a fully-progressed schedule, every
    #: non-summary activity 100% complete) → both float figures degraded to a placeholder ``0.0``,
    #: not a real mean/max. Consumers render "—"/NA instead of the fabricated number (audit NEW-1).
    incomplete_float_count: int


def _round_half_up(value: float, places: int = 2) -> float:
    """Round half away from zero (Fuse's convention), not banker's rounding."""
    q = Decimal(10) ** -places
    return float(Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP))


def _audit_count(audit: ScheduleAudit, metric_id: str) -> int:
    for check in audit.checks:
        if check.metric_id == metric_id:
            return check.count
    return 0


def _audit_uids(audit: ScheduleAudit, metric_id: str) -> tuple[int, ...]:
    for check in audit.checks:
        if check.metric_id == metric_id:
            return tuple(c.unique_id for c in check.citations)
    return ()


def ribbon_offender_map(
    schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit
) -> dict[str, tuple[int, ...]]:
    """The activities "in question" behind each ribbon cell (operator 2026-07-08 click-drill).

    Keyed by the :class:`RibbonMetrics` attribute names. Counted metrics list exactly the
    counted offenders; the ratio/float metrics list the population that produces the figure —
    ``logic_density`` lists the open-ended activities diluting the density (the Missing-Logic
    set), and ``avg_float_days`` / ``max_float_days`` list the incomplete float population
    sorted float-descending, so the max-float task leads. Values are display-ordered, not a
    metric of their own — the counts in :func:`compute_ribbon` stay the Fuse-validated truth.
    """
    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality

    quality = compute_schedule_quality(schedule, cpm)
    tasks = non_summary(schedule)
    ns_ids = {t.unique_id for t in tasks}

    has_pred: set[int] = set()
    has_succ: set[int] = set()
    pred_count: dict[int, int] = {}
    lag_successors: set[int] = set()
    lead_successors: set[int] = set()
    for r in schedule.relationships:
        if r.predecessor_id in ns_ids and r.successor_id in ns_ids:
            has_pred.add(r.successor_id)
            has_succ.add(r.predecessor_id)
            pred_count[r.successor_id] = pred_count.get(r.successor_id, 0) + 1
            if r.lag_minutes > 0:
                lag_successors.add(r.successor_id)
            elif r.lag_minutes < 0:
                lead_successors.add(r.successor_id)

    missing = tuple(
        t.unique_id for t in tasks if t.unique_id not in has_pred or t.unique_id not in has_succ
    )
    critical = tuple(
        t.unique_id
        for t in tasks
        if t.percent_complete < 100.0
        and is_effective_critical(
            t, cpm.timings[t.unique_id].total_float if t.unique_id in cpm.timings else 0
        )
    )
    merge = tuple(
        t.unique_id for t in tasks if pred_count.get(t.unique_id, 0) > _MERGE_HOTSPOT_MIN_PREDS
    )
    per_day = schedule.calendar.working_minutes_per_day or 1
    float_pop = sorted(
        (
            (effective_total_float(t, cpm.timings[t.unique_id].total_float) / per_day, t.unique_id)
            for t in tasks
            if t.percent_complete < 100.0 and t.unique_id in cpm.timings
        ),
        key=lambda p: (-p[0], p[1]),
    )
    floats_desc = tuple(uid for _, uid in float_pop)
    return {
        "missing_logic": missing,
        "logic_density": missing,
        "critical": critical,
        "hard_constraints": _audit_uids(audit, "DCMA05"),
        "negative_float": _audit_uids(audit, "DCMA07"),
        "number_of_lags": tuple(sorted(lag_successors)),
        "number_of_leads": tuple(sorted(lead_successors)),
        "merge_hotspot": merge,
        "avg_float_days": floats_desc,
        "max_float_days": floats_desc,
        "insufficient_detail": quality["insufficient_detail"].offender_uids,
    }


def compute_ribbon(schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit) -> RibbonMetrics:
    """Assemble the Fuse Ribbon metrics for ``schedule`` (its CPM + DCMA audit)."""
    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality

    quality = compute_schedule_quality(schedule, cpm)
    tasks = non_summary(schedule)
    ns_ids = {t.unique_id for t in tasks}
    n = len(tasks)

    has_pred: set[int] = set()
    has_succ: set[int] = set()
    pred_count: dict[int, int] = {}
    links_among_ns = 0
    # Fuse's Ribbon "Number of Lags / Leads" counts the *activities* whose predecessors carry a
    # positive (lag) / negative (lead) offset, across ALL statuses — "planned, in-progress, OR
    # complete" (the Fuse metric guide). This differs from the DCMA-14 Lags/Leads checks, which
    # restrict to *incomplete* successors; on a progressed file the lags into already-finished
    # work are real and Fuse counts them, so the Ribbon must not inherit the DCMA filter (ADR-0081).
    lag_successors: set[int] = set()
    lead_successors: set[int] = set()
    for r in schedule.relationships:
        if r.predecessor_id in ns_ids and r.successor_id in ns_ids:
            links_among_ns += 1
            has_pred.add(r.successor_id)
            has_succ.add(r.predecessor_id)
            pred_count[r.successor_id] = pred_count.get(r.successor_id, 0) + 1
            if r.lag_minutes > 0:
                lag_successors.add(r.successor_id)
            elif r.lag_minutes < 0:
                lead_successors.add(r.successor_id)

    missing_logic = sum(
        1 for t in tasks if t.unique_id not in has_pred or t.unique_id not in has_succ
    )
    logic_density = _round_half_up(2 * links_among_ns / n) if n else 0.0
    # Acumen's "Critical" reads the source tool's STORED Critical flag when present (matching it
    # on progressed files); else pure-logic CPM critical, both excluding completed work (ADR-0080).
    critical = sum(
        1
        for t in tasks
        if t.percent_complete < 100.0
        and is_effective_critical(
            t, cpm.timings[t.unique_id].total_float if t.unique_id in cpm.timings else 0
        )
    )
    merge_hotspot = sum(1 for c in pred_count.values() if c > _MERGE_HOTSPOT_MIN_PREDS)

    # Avg/Max Float must score on the SAME float the Critical count and Acumen use: the source
    # tool's stored, progress-aware Total Slack when the file carries it (else recomputed CPM
    # float). Using the raw recomputed float here made Max Float (d) diverge from Acumen on
    # progressed files and blow up on open-ended activities (ADR-0010/0080).
    per_day = schedule.calendar.working_minutes_per_day or 1
    floats = [
        effective_total_float(t, cpm.timings[t.unique_id].total_float) / per_day
        for t in tasks
        if t.percent_complete < 100.0 and t.unique_id in cpm.timings
    ]
    avg_float = round(sum(floats) / len(floats), 1) if floats else 0.0
    max_float = round(max(floats), 1) if floats else 0.0

    return RibbonMetrics(
        missing_logic=missing_logic,
        logic_density=logic_density,
        critical=critical,
        hard_constraints=_audit_count(audit, "DCMA05"),
        negative_float=_audit_count(audit, "DCMA07"),
        number_of_lags=len(lag_successors),
        number_of_leads=len(lead_successors),
        merge_hotspot=merge_hotspot,
        avg_float_days=avg_float,
        max_float_days=max_float,
        insufficient_detail=quality["insufficient_detail"].count,
        incomplete_float_count=len(floats),
    )
