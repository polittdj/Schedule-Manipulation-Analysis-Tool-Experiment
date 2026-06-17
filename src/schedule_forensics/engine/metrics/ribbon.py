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

Insufficient Detail™ and Float Ratio™ are Fuse-proprietary formulas that did not match any
simple definition in calibration; they are deliberately left out pending the Fuse formula
(see docs/FUSE-VALIDATION.md), rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from schedule_forensics.engine.metrics._common import non_summary

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


def _round_half_up(value: float, places: int = 2) -> float:
    """Round half away from zero (Fuse's convention), not banker's rounding."""
    q = Decimal(10) ** -places
    return float(Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP))


def _audit_count(audit: ScheduleAudit, metric_id: str) -> int:
    for check in audit.checks:
        if check.metric_id == metric_id:
            return check.count
    return 0


def compute_ribbon(schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit) -> RibbonMetrics:
    """Assemble the Fuse Ribbon metrics for ``schedule`` (its CPM + DCMA audit)."""
    tasks = non_summary(schedule)
    ns_ids = {t.unique_id for t in tasks}
    n = len(tasks)

    has_pred: set[int] = set()
    has_succ: set[int] = set()
    pred_count: dict[int, int] = {}
    links_among_ns = 0
    for r in schedule.relationships:
        if r.predecessor_id in ns_ids and r.successor_id in ns_ids:
            links_among_ns += 1
            has_pred.add(r.successor_id)
            has_succ.add(r.predecessor_id)
            pred_count[r.successor_id] = pred_count.get(r.successor_id, 0) + 1

    missing_logic = sum(
        1 for t in tasks if t.unique_id not in has_pred or t.unique_id not in has_succ
    )
    logic_density = _round_half_up(2 * links_among_ns / n) if n else 0.0
    critical = sum(
        1
        for uid in cpm.critical_path
        if uid in schedule.tasks_by_id and schedule.tasks_by_id[uid].percent_complete < 100.0
    )
    merge_hotspot = sum(1 for c in pred_count.values() if c > _MERGE_HOTSPOT_MIN_PREDS)

    per_day = schedule.calendar.working_minutes_per_day or 1
    floats = [
        cpm.timings[t.unique_id].total_float / per_day
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
        number_of_lags=_audit_count(audit, "DCMA03"),
        number_of_leads=_audit_count(audit, "DCMA02"),
        merge_hotspot=merge_hotspot,
        avg_float_days=avg_float,
        max_float_days=max_float,
    )
