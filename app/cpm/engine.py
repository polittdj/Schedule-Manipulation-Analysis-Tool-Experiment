"""Critical Path Method engine.

Works entirely in integer working-minute offsets from the schedule's project start, so the
arithmetic is exact and the end-of-day / start-of-next-day boundary ambiguity never enters
the computation. Durations and lags are working-time minutes. Assumes a single shared
calendar for the offset axis; cross-calendar arithmetic is out of scope (see
FIDELITY-DECISION-cpm-engine.md). Tasks schedule as-soon-as-possible, but date constraints
(SNET/SNLT/FNET/FNLT/MSO/MFO) and deadlines are honored under MS Project's default "honor
constraint dates" behaviour, which can drive negative float. ALAP is not yet supported.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterable
from datetime import datetime

from app.cpm.calendar_math import working_minutes_between
from app.cpm.result import CPMResult, TaskTiming
from app.exceptions import CPMError
from app.models import Calendar, ConstraintType, Relation, RelationType, Schedule


def _topological_order(task_ids: Iterable[int], relations: tuple[Relation, ...]) -> list[int]:
    """Kahn's algorithm; ready-queue tie-broken by ascending unique_id for determinism.
    Raises CPMError if the logic graph contains a cycle."""
    indegree: dict[int, int] = dict.fromkeys(task_ids, 0)
    adjacency: dict[int, list[int]] = {uid: [] for uid in indegree}
    for relation in relations:
        adjacency[relation.predecessor_id].append(relation.successor_id)
        indegree[relation.successor_id] += 1

    ready = [uid for uid, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    order: list[int] = []
    while ready:
        uid = heapq.heappop(ready)
        order.append(uid)
        for successor in adjacency[uid]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)

    if len(order) != len(indegree):
        cyclic = sorted(set(indegree) - set(order))
        raise CPMError(f"schedule logic contains a cycle involving tasks {cyclic}")
    return order


def compute_cpm(schedule: Schedule) -> CPMResult:
    """Run the forward and backward passes and return per-task timings + the critical path."""
    duration: dict[int, int] = {t.unique_id: t.duration_minutes for t in schedule.tasks}
    if not duration:
        raise CPMError("cannot run CPM on a schedule with no tasks")

    incoming: dict[int, list[Relation]] = {uid: [] for uid in duration}
    outgoing: dict[int, list[Relation]] = {uid: [] for uid in duration}
    for relation in schedule.relations:
        outgoing[relation.predecessor_id].append(relation)
        incoming[relation.successor_id].append(relation)

    order = _topological_order(duration.keys(), schedule.relations)

    # Map tasks; convert deadlines and constraint dates to working-minute offsets.
    task_map = {task.unique_id: task for task in schedule.tasks}
    calendars = {c.calendar_id: c for c in schedule.calendars}

    alap = sorted(uid for uid, t in task_map.items() if t.constraint_type == ConstraintType.ALAP)
    if alap:
        raise CPMError(f"ALAP constraints are not supported by the scheduler (tasks {alap})")

    deadline_offsets: dict[int, int] = {
        uid: _to_offset(calendars[t.calendar_id], schedule.project_start, t.deadline)
        for uid, t in task_map.items()
        if t.deadline is not None
    }
    constraint_offsets: dict[int, int] = {
        uid: _to_offset(calendars[t.calendar_id], schedule.project_start, t.constraint_date)
        for uid, t in task_map.items()
        if t.constraint_date is not None
    }

    # Forward pass: earliest start/finish.
    es: dict[int, int] = {}
    ef: dict[int, int] = {}
    for uid in order:
        earliest = 0
        for relation in incoming[uid]:
            pred = relation.predecessor_id
            lag = relation.lag_minutes
            if relation.relation_type == RelationType.FS:
                candidate = ef[pred] + lag
            elif relation.relation_type == RelationType.SS:
                candidate = es[pred] + lag
            elif relation.relation_type == RelationType.FF:
                candidate = ef[pred] + lag - duration[uid]
            else:  # SF
                candidate = es[pred] + lag - duration[uid]
            earliest = max(earliest, candidate)
        constraint = task_map[uid].constraint_type
        if constraint == ConstraintType.ASAP:
            start = earliest
        else:
            start = _apply_early_constraint(
                constraint, constraint_offsets[uid], earliest, duration[uid]
            )
        es[uid] = start
        ef[uid] = start + duration[uid]

    project_finish = max(ef.values())

    # Backward pass: latest start/finish.
    ls: dict[int, int] = {}
    lf: dict[int, int] = {}
    for uid in reversed(order):
        if not outgoing[uid]:
            latest = project_finish
        else:
            candidates: list[int] = []
            for relation in outgoing[uid]:
                succ = relation.successor_id
                lag = relation.lag_minutes
                if relation.relation_type == RelationType.FS:
                    candidates.append(ls[succ] - lag)
                elif relation.relation_type == RelationType.SS:
                    candidates.append(ls[succ] - lag + duration[uid])
                elif relation.relation_type == RelationType.FF:
                    candidates.append(lf[succ] - lag)
                else:  # SF
                    candidates.append(lf[succ] - lag + duration[uid])
            latest = min(candidates)
        if uid in deadline_offsets:
            latest = min(latest, deadline_offsets[uid])
        constraint = task_map[uid].constraint_type
        if constraint != ConstraintType.ASAP:
            latest = _apply_late_constraint(
                constraint, constraint_offsets[uid], latest, duration[uid]
            )
        lf[uid] = latest
        ls[uid] = latest - duration[uid]

    # Slack + critical path (outputs ordered by unique_id for determinism).
    timings: list[TaskTiming] = []
    critical_path: list[int] = []
    for uid in sorted(duration):
        total_slack = ls[uid] - es[uid]
        free_slack = _free_slack(uid, es, ef, outgoing[uid], project_finish)
        timings.append(
            TaskTiming(
                unique_id=uid,
                early_start=es[uid],
                early_finish=ef[uid],
                late_start=ls[uid],
                late_finish=lf[uid],
                total_slack=total_slack,
                free_slack=free_slack,
            )
        )
        if total_slack <= 0:  # <= 0 (not == 0) so negative-float tasks are critical too
            critical_path.append(uid)

    return CPMResult(
        project_start=schedule.project_start,
        project_finish=project_finish,
        timings=tuple(timings),
        critical_path=tuple(critical_path),
    )


def _free_slack(
    uid: int,
    es: dict[int, int],
    ef: dict[int, int],
    outgoing: list[Relation],
    project_finish: int,
) -> int:
    """Free slack: how far a task can slip without delaying any successor's early dates.
    Uses successor *early* dates (distinct from total slack, which uses late dates)."""
    if not outgoing:
        return project_finish - ef[uid]
    gaps: list[int] = []
    for relation in outgoing:
        succ = relation.successor_id
        lag = relation.lag_minutes
        if relation.relation_type == RelationType.FS:
            gaps.append(es[succ] - (ef[uid] + lag))
        elif relation.relation_type == RelationType.SS:
            gaps.append(es[succ] - (es[uid] + lag))
        elif relation.relation_type == RelationType.FF:
            gaps.append(ef[succ] - (ef[uid] + lag))
        else:  # SF
            gaps.append(ef[succ] - (es[uid] + lag))
    return min(gaps)


def _to_offset(calendar: Calendar, project_start: datetime, when: datetime) -> int:
    """A datetime as a working-minute offset from project start (0 if at/before start)."""
    if when <= project_start:
        return 0
    return working_minutes_between(calendar, project_start, when)


def _apply_early_constraint(
    constraint: ConstraintType, offset: int, logic_early_start: int, duration: int
) -> int:
    """Earliest start after honoring a constraint (MS Project 'honor constraint dates' mode).
    Late-only constraints (SNLT/FNLT) do not move the early dates."""
    if constraint == ConstraintType.SNET:
        return max(logic_early_start, offset)
    if constraint == ConstraintType.FNET:
        return max(logic_early_start, offset - duration)
    if constraint == ConstraintType.MSO:
        return offset  # pin the start
    if constraint == ConstraintType.MFO:
        return offset - duration  # pin the finish
    return logic_early_start


def _apply_late_constraint(
    constraint: ConstraintType, offset: int, logic_late_finish: int, duration: int
) -> int:
    """Latest finish after honoring a constraint. Early-only constraints (SNET/FNET) do not
    move the late dates; hard constraints can tighten LF below EF and cause negative float."""
    if constraint == ConstraintType.FNLT:
        return min(logic_late_finish, offset)
    if constraint == ConstraintType.SNLT:
        return min(logic_late_finish, offset + duration)  # LS <= offset
    if constraint == ConstraintType.MSO:
        return offset + duration  # pin LS = offset
    if constraint == ConstraintType.MFO:
        return offset  # pin LF
    return logic_late_finish
