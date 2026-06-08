"""Driving slack to a focus UniqueID — the SSI MS Project add-on parity (§6.C, ADR-0011).

Given a user-chosen **target (focus) UniqueID**, this computes each driving activity's
**Driving Slack** — how many working days it can slip before it would delay the focus
task along its logic path. The method (matched bit-for-bit against the SSI golden export
for Project5 / UID 143, `docs/PLAN/SSI-DRIVING-SLACK.md`):

1. Trace the focus task's ancestors (its transitive predecessors — :mod:`.path_trace`).
2. Take each task's **as-scheduled** early start/finish from the schedule's stored
   ``start``/``finish`` (progress-aware — SSI runs inside MS Project and measures
   against the *progressed* schedule, honoring actuals and the data date). Where a task
   has no stored dates (hand-authored schedules), fall back to the CPM forward pass.
3. Anchor a backward pass at the focus: ``late_finish(focus) = early_finish(focus)``,
   then propagate the latest each ancestor may finish without delaying the focus.
4. ``driving_slack = late_finish - early_finish`` (working minutes → days). Tasks on the
   driving path have **0**; the rest are classified into the user's secondary/tertiary
   day-tiers (§6.C; defaults 0<secondary≤10, 10<tertiary≤20 — `PARITY-INPUTS.md`).

Using stored dates was the key to exact parity: without it, completed activities whose
actuals ran late (e.g. Project5 UID 8/13/14/16, +16 days) computed too much slack.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from schedule_forensics.engine.cpm import (
    CPMResult,
    compute_cpm,
    datetime_to_offset,
    lf_upper_bound,
)
from schedule_forensics.engine.path_trace import ancestors_of, topo_order
from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.units import MINUTES_PER_DAY, minutes_to_days

#: §6.C default day-thresholds the user may override at upload (`PARITY-INPUTS.md`).
DEFAULT_SECONDARY_MAX_DAYS = 10
DEFAULT_TERTIARY_MAX_DAYS = 20


class PathTier(StrEnum):
    """Driving-slack magnitude tier relative to the focus task (user-configurable bands)."""

    DRIVING = "DRIVING"  # driving slack <= 0 (on the driving/critical path to focus)
    SECONDARY = "SECONDARY"  # 0 < slack <= secondary_max_days
    TERTIARY = "TERTIARY"  # secondary_max_days < slack <= tertiary_max_days
    BEYOND = "BEYOND"  # slack > tertiary_max_days


@dataclass(frozen=True)
class DrivingSlackResult:
    """One driving activity's slack to the focus task."""

    unique_id: int
    driving_slack_minutes: int
    driving_slack_days: Decimal
    on_driving_path: bool  # driving_slack <= 0
    tier: PathTier


def _date_basis(
    schedule: Schedule, cpm_result: CPMResult | None
) -> tuple[dict[int, int], dict[int, int]]:
    """Per-task (early_start, early_finish) offsets from the as-scheduled stored dates,
    falling back to the CPM forward pass for any task missing them."""
    cal = schedule.calendar
    start = schedule.project_start
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    result = cpm_result
    for task in schedule.tasks:
        if task.is_summary:
            continue
        if task.start is not None and task.finish is not None:
            early_start[task.unique_id] = datetime_to_offset(start, task.start, cal)
            early_finish[task.unique_id] = datetime_to_offset(start, task.finish, cal)
        else:
            if result is None:
                result = compute_cpm(schedule)
            timing = result.timing(task.unique_id)
            early_start[task.unique_id] = timing.early_start
            early_finish[task.unique_id] = timing.early_finish
    return early_start, early_finish


def _classify(slack_minutes: int, secondary_max_days: int, tertiary_max_days: int) -> PathTier:
    if slack_minutes <= 0:
        return PathTier.DRIVING
    if slack_minutes <= secondary_max_days * MINUTES_PER_DAY:
        return PathTier.SECONDARY
    if slack_minutes <= tertiary_max_days * MINUTES_PER_DAY:
        return PathTier.TERTIARY
    return PathTier.BEYOND


def compute_driving_slack(
    schedule: Schedule,
    target_uid: int,
    *,
    secondary_max_days: int = DEFAULT_SECONDARY_MAX_DAYS,
    tertiary_max_days: int = DEFAULT_TERTIARY_MAX_DAYS,
    cpm_result: CPMResult | None = None,
) -> dict[int, DrivingSlackResult]:
    """Driving slack to ``target_uid`` for the focus task and each of its ancestors.

    Returns a UniqueID-keyed mapping covering the focus and every task that can drive
    it (tasks with no logic path to the focus are not included). Raises ``KeyError`` if
    ``target_uid`` is not a scheduled task, or ``ValueError`` on a cycle in the trace.
    """
    ancestors = ancestors_of(schedule, target_uid)
    trace = ancestors | {target_uid}
    early_start, early_finish = _date_basis(schedule, cpm_result)
    span = {uid: early_finish[uid] - early_start[uid] for uid in trace}

    successors: dict[int, list[tuple[int, RelationshipType, int]]] = {uid: [] for uid in trace}
    for rel in schedule.relationships:
        if rel.predecessor_id in trace and rel.successor_id in trace:
            successors[rel.predecessor_id].append((rel.successor_id, rel.type, rel.lag_minutes))

    order = topo_order(schedule, trace)
    late_finish: dict[int, int] = {}
    late_start: dict[int, int] = {}
    for uid in reversed(order):
        if uid == target_uid:
            late_finish[uid] = early_finish[uid]
        else:
            late_finish[uid] = min(
                lf_upper_bound(rel, late_start[succ], late_finish[succ], lag, span[uid])
                for succ, rel, lag in successors[uid]
            )
        late_start[uid] = late_finish[uid] - span[uid]

    results: dict[int, DrivingSlackResult] = {}
    for uid in trace:
        slack = late_finish[uid] - early_finish[uid]
        results[uid] = DrivingSlackResult(
            unique_id=uid,
            driving_slack_minutes=slack,
            driving_slack_days=minutes_to_days(slack),
            on_driving_path=slack <= 0,
            tier=_classify(slack, secondary_max_days, tertiary_max_days),
        )
    return results


def driving_path(schedule: Schedule, results: dict[int, DrivingSlackResult]) -> tuple[int, ...]:
    """The on-driving-path UniqueIDs (slack <= 0), in topological order to the focus."""
    on_path = [uid for uid, r in results.items() if r.on_driving_path]
    return topo_order(schedule, on_path)
