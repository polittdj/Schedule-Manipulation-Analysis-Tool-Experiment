"""The Metric Workbench catalog — a selectable library of the tool's **validated** metrics.

The Workbench (ADR-0204) lets the operator pick any metrics from this catalog and see each one
computed for every loaded schedule **independently**, laid out chronologically like Acumen Fuse.
This module is the single source of truth for *what is in the library*: it does **no new metric
math** (Law 2 — every figure must already be parity-validated), it only **aggregates** the numbers
the engine already computes into one uniform, offender-carrying row shape.

Sources aggregated (both already gate-locked against the golden Fuse/DCMA exports):

* :func:`schedule_forensics.engine.dcma_audit.audit_schedule` — the 16 DCMA-14 check lines, each
  with its value / status / threshold and the offending activities (``citations``).
* :func:`schedule_forensics.engine.metrics.ribbon.compute_ribbon` + ``ribbon_offender_map`` — the
  Fuse Schedule-Quality extras that are not DCMA-14 checks (Logic Density, Insufficient Detail,
  Merge Hotspot, Avg / Max Float), with the activity set behind each figure.

Each :class:`CatalogEntry` is stable metadata (id / name / family / unit / threshold direction /
one-line description); :func:`evaluate_catalog` returns a :class:`CatalogRow` per metric for one
schedule (value + status + the offender UIDs the drill panel lists). Families are expandable — EVM,
Completion (MEI), HMI, FEI/BRI and the float bands register the same way (tracked follow-ons).
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.dcma_audit import ScheduleAudit, audit_schedule
from schedule_forensics.engine.metrics._common import CheckStatus
from schedule_forensics.engine.metrics.ribbon import compute_ribbon, ribbon_offender_map
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class CatalogEntry:
    """Stable library metadata for one selectable metric (no per-schedule values)."""

    metric_id: str
    name: str
    family: str  # library grouping, e.g. "DCMA-14", "Schedule Quality", "Float"
    unit: str  # "%", "ratio", "count", "days"
    lower_is_better: bool | None  # None = neutral/informational (no pass/fail intent)
    threshold: float | None
    describe: str


@dataclass(frozen=True)
class CatalogRow:
    """One metric evaluated for one schedule — the Workbench ribbon cell + its drill set."""

    metric_id: str
    value: float
    unit: str
    status: str  # CheckStatus value: "PASS" | "FAIL" | "NA"
    offender_uids: tuple[int, ...]


#: The DCMA-14 library entries, in check order. Metadata mirrors help.py / the audit; values come
#: from :func:`audit_schedule` at evaluation time (never recomputed here).
_DCMA_ENTRIES: tuple[tuple[str, str, str, bool | None, float | None, str], ...] = (
    ("DCMA01", "Logic", "%", True, 5.0, "Activities missing a predecessor and/or successor."),
    ("DCMA02", "Leads", "count", True, 0.0, "Logic links with a negative lag (a lead)."),
    ("DCMA03", "Lags", "%", True, 5.0, "Logic links carrying a positive lag."),
    ("DCMA04_FS", "FS Relationships", "%", False, 90.0, "Share of links that are Finish-to-Start."),
    ("DCMA04_SSFF", "SS/FF Relationships", "%", None, None, "Start-Start / Finish-Finish share."),
    ("DCMA04_SF", "SF Relationships", "%", True, None, "Share of Start-to-Finish (rare; justify)."),
    ("DCMA05", "Hard Constraints", "%", True, 5.0, "Activities with a hard (must/no-later) date."),
    ("DCMA06", "High Float", "%", True, 5.0, "Incomplete activities, total float > 44 days."),
    ("DCMA07", "Negative Float", "%", True, 0.0, "Incomplete activities with total float < 0."),
    ("DCMA08", "High Duration", "%", True, 5.0, "Incomplete activities, duration > 44 days."),
    ("DCMA09", "Invalid Dates", "%", True, 0.0, "Forecast before, or actual after, the data date."),
    ("DCMA10", "Resources", "%", True, 5.0, "Real-duration activities with no resource/cost."),
    ("DCMA11", "Missed Activities", "%", True, 5.0, "Activities finishing later than baseline."),
    ("DCMA12", "Critical Path Test", "count", True, 0.0, "Broken-logic count from the slip test."),
    ("DCMA13", "CPLI", "ratio", False, 0.95, "Critical Path Length Index (finish realism)."),
    ("DCMA14", "BEI", "ratio", False, 0.95, "Baseline Execution Index (task throughput)."),
)

#: Fuse Schedule-Quality / Float entries that are NOT DCMA-14 checks — pulled from the ribbon.
#: (metric_id == the RibbonMetrics attribute; offenders from ribbon_offender_map).
_RIBBON_ENTRIES: tuple[tuple[str, str, str, str, bool | None, float | None, str], ...] = (
    (
        "logic_density",
        "Logic Density",
        "Schedule Quality",
        "ratio",
        None,
        None,
        "Logic links per activity (2x links / activities) — network richness.",
    ),
    (
        "insufficient_detail",
        "Insufficient Detail",
        "Schedule Quality",
        "count",
        True,
        None,
        "Activities whose duration exceeds 10% of the project span.",
    ),
    (
        "merge_hotspot",
        "Merge Hotspot",
        "Schedule Quality",
        "count",
        True,
        None,
        "Activities with more than two predecessors (merge-bias risk).",
    ),
    (
        "avg_float_days",
        "Avg Float (days)",
        "Float",
        "days",
        None,
        None,
        "Mean total float of the incomplete activities.",
    ),
    (
        "max_float_days",
        "Max Float (days)",
        "Float",
        "days",
        None,
        None,
        "Largest total float among the incomplete activities.",
    ),
)


def catalog_entries() -> tuple[CatalogEntry, ...]:
    """The full selectable library (stable metadata), DCMA-14 first then the ribbon extras."""
    entries = [
        CatalogEntry(mid, name, "DCMA-14", unit, lib, thr, desc)
        for mid, name, unit, lib, thr, desc in _DCMA_ENTRIES
    ]
    entries += [
        CatalogEntry(mid, name, family, unit, lib, thr, desc)
        for mid, name, family, unit, lib, thr, desc in _RIBBON_ENTRIES
    ]
    return tuple(entries)


def catalog_families() -> tuple[str, ...]:
    """Distinct family names in library order (for the left-hand grouped picker)."""
    seen: list[str] = []
    for e in catalog_entries():
        if e.family not in seen:
            seen.append(e.family)
    return tuple(seen)


def evaluate_catalog(
    schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit | None = None
) -> dict[str, CatalogRow]:
    """Every catalog metric evaluated for one schedule, keyed by ``metric_id``.

    No metric is recomputed here: DCMA rows read straight off :func:`audit_schedule`, and the
    ribbon extras read off :func:`compute_ribbon` (value) + ``ribbon_offender_map`` (offenders).
    A metric the audit does not emit for this file (e.g. an unscored relationship split) is
    reported ``NA`` with an empty offender set — never a fabricated 0. Pass a cached ``audit``
    (the per-schedule ``_Analysis.audit``) to skip the re-audit.
    """
    if audit is None:
        audit = audit_schedule(schedule, cpm)
    by_id = {c.metric_id: c for c in audit.checks}
    rows: dict[str, CatalogRow] = {}

    for mid, _name, unit, _lib, _thr, _desc in _DCMA_ENTRIES:
        check = by_id.get(mid)
        if check is None:
            rows[mid] = CatalogRow(mid, 0.0, unit, CheckStatus.NOT_APPLICABLE.value, ())
            continue
        rows[mid] = CatalogRow(
            mid,
            check.value,
            check.unit,
            check.status.value,
            tuple(c.unique_id for c in check.citations),
        )

    ribbon = compute_ribbon(schedule, cpm, audit)
    offenders = ribbon_offender_map(schedule, cpm, audit)
    for mid, _name, _family, unit, _lib, _thr, _desc in _RIBBON_ENTRIES:
        value = float(getattr(ribbon, mid))
        rows[mid] = CatalogRow(
            mid,
            value,
            unit,
            CheckStatus.NOT_APPLICABLE.value,  # the extras are informational (no threshold)
            tuple(offenders.get(mid, ())),
        )
    return rows
