"""Extra structural health checks (NASA Schedule Management Handbook Fig. 6-9; assessment decks).

Deterministic checks the tool did not already carry, computed from fields the model already has —
kept OUT of the Fuse-parity ribbon and the gate-locked DCMA audit so they cannot disturb either.
Each returns a count plus the offending UniqueIDs (capped) and a plain-English reason, so the
analyst sees not just "how many" but "which" and "why it matters". Lightweight dataclasses (NOT
``MetricResult``) — the metric-dictionary coverage test is intentionally untouched.

Sources: Deck-1 slides 58-72 (Acumen metric-library names/definitions); Handbook pp.170-172.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics._common import is_effective_critical, non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

# PROVENANCE (audit F-14, swept against the delivered handbooks 2026-07-08, ADR-0153): lag
# SCRUTINY is NASA-sourced — PPC Handbook NASA/SP-2016-3424 p.136 (lead/lag values are not
# schedule margin) and §3.4.3.2B p.145 (validate that "lag values are accurate"); its Fig. 3.4-3
# health check counts positive/negative lags per relationship type. No delivered handbook
# publishes a NUMERIC lag-to-duration ratio or a merge/diverge link count, so the two values
# below remain in-repo design choices, documented as such.
#: more than this many predecessors (or successors) on one activity is a merge / diverge hotspot
_HOTSPOT_MIN_LINKS = 2
#: a predecessor lag longer than this fraction of the activity's duration "hides" real duration
_HIDDEN_DURATION_FRACTION = 0.35
#: cap the offender list carried to the UI (the page's grid is the full record)
_OFFENDER_CAP = 50


@dataclass(frozen=True)
class HealthCheck:
    """One structural health check: how many offend, which (capped), and why it matters."""

    key: str
    label: str
    count: int
    population: int
    offenders: tuple[int, ...]
    description: str


@dataclass(frozen=True)
class HealthChecks:
    """The full set of extra structural health checks for one schedule."""

    checks: tuple[HealthCheck, ...]


def _total_float(cpm: CPMResult, uid: int) -> int:
    timing = cpm.timings.get(uid)
    return timing.total_float if timing is not None else 0


def compute_health_checks(schedule: Schedule, cpm: CPMResult) -> HealthChecks:
    """Compute the extra structural health checks for ``schedule`` (CPM gives criticality)."""
    tasks = non_summary(schedule)
    ns_ids = {t.unique_id for t in tasks}
    n = len(tasks)

    pred_count: dict[int, int] = {}
    succ_count: dict[int, int] = {}
    incoming_lag: dict[int, list[int]] = {}
    for r in schedule.relationships:
        if r.predecessor_id in ns_ids and r.successor_id in ns_ids:
            succ_count[r.predecessor_id] = succ_count.get(r.predecessor_id, 0) + 1
            pred_count[r.successor_id] = pred_count.get(r.successor_id, 0) + 1
            incoming_lag.setdefault(r.successor_id, []).append(r.lag_minutes)

    def critical(t: Task) -> bool:
        return is_effective_critical(t, _total_float(cpm, t.unique_id))

    specs: list[tuple[str, str, Callable[[Task], bool], str]] = [
        (
            "critical_merge_hotspot",
            "Critical merge hotspots",
            lambda t: critical(t) and pred_count.get(t.unique_id, 0) > _HOTSPOT_MIN_LINKS,
            "Critical activities with more than two predecessors — a delay in any feeder hits the "
            "critical path; a fragile convergence point.",
        ),
        (
            "critical_diverge_hotspot",
            "Critical diverge hotspots",
            lambda t: critical(t) and succ_count.get(t.unique_id, 0) > _HOTSPOT_MIN_LINKS,
            "Critical activities driving more than two successors — a slip here fans out across "
            "many downstream paths.",
        ),
        (
            "loe_on_critical_path",
            "Level-of-effort on the critical path",
            lambda t: t.is_level_of_effort and critical(t),
            "Level-of-effort (support) tasks should never be on the critical path — the handbook "
            "says the critical path cannot include LOE; their presence signals broken logic.",
        ),
        (
            "milestone_with_duration",
            "Milestones with duration",
            lambda t: (
                t.is_milestone and max(t.baseline_duration_minutes or 0, t.duration_minutes) > 0
            ),
            "Milestones are zero-duration events; a milestone carrying duration is mis-typed and "
            "distorts counts and logic.",
        ),
        (
            "zero_duration_task",
            "Zero-duration tasks (non-milestone)",
            lambda t: not t.is_milestone and t.duration_minutes == 0,
            "Non-milestone activities with zero duration are usually mis-typed milestones or "
            "placeholders and should be reviewed.",
        ),
        (
            "hidden_duration",
            "Hidden duration (lag > 35% of duration)",
            lambda t: (
                t.duration_minutes > 0
                and any(
                    lag > _HIDDEN_DURATION_FRACTION * t.duration_minutes
                    for lag in incoming_lag.get(t.unique_id, [])
                )
            ),
            "A predecessor lag longer than 35% of the activity's duration hides real work inside a "
            "relationship, where it escapes status and risk — model it as an activity instead.",
        ),
        (
            "estimated_duration",
            "Estimated (placeholder) durations",
            lambda t: t.is_estimated_duration and not t.is_milestone,
            "Activities whose duration is still flagged 'Estimated' in MS Project are placeholders "
            "the planner has not firmed up — an under-developed estimate that should be replaced "
            "with a basis-backed duration before the schedule is relied upon.",
        ),
        (
            "missing_wbs",
            "Missing WBS",
            lambda t: not (t.wbs or "").strip(),
            "Activities with no WBS code drop out of WBS rollups and traceability — every activity "
            "should map to the work-breakdown structure.",
        ),
        (
            "missing_baseline_finish",
            "Missing baseline finish",
            lambda t: t.baseline_finish is None,
            "Without a baseline finish an activity can't be measured for execution (BEI, variance) "
            "— the schedule is not fully baselined.",
        ),
    ]

    checks: list[HealthCheck] = []
    for key, label, predicate, desc in specs:
        offs = [t.unique_id for t in tasks if predicate(t)]
        checks.append(
            HealthCheck(
                key=key,
                label=label,
                count=len(offs),
                population=n,
                offenders=tuple(offs[:_OFFENDER_CAP]),
                description=desc,
            )
        )
    return HealthChecks(checks=tuple(checks))
