"""Critical Path Method engine -- forward + backward pass (trust-root, LAW 2).

The internal time axis is INTEGER WORKING MINUTES, measured as an offset from
``Schedule.project_start``. An integer working-minute axis makes the arithmetic
exact and hand-verifiable, and removes the end-of-day / start-of-next-day
boundary class of bugs by construction (the wall-clock conversion is a separate,
separately-tested concern -- see ``offset_to_datetime``).

Scope of this slice (documented, not silently limited -- see PHASE-COMPLETE-1.md):
  * Link types: all four (FS/SS/FF/SF) with lag/lead, in working minutes.
  * Scheduling: ASAP. Date constraints (SNET/SNLT/FNET/FNLT/MSO/MFO), ALAP, and
    deadlines are NOT yet honored. Rather than emit a silently-wrong schedule
    (forbidden in a forensic context -- LAW 2), the engine RAISES ``CPMError`` if
    a task carries one. They land in the next increment, which adds the
    calendar-aware datetime->offset conversion.
  * Total float MAY be negative when an earlier ``required_finish_offset`` is
    imposed -- this is how schedule pressure surfaces forensically, computed in
    exact integer minutes without a calendar walk.

Critical-path definition: ``total_float <= 0`` (matches MS Project once negative
float exists). Cited in docs/REFERENCES.md.

Link-type timing (P = predecessor, S = successor, L = lag, all working minutes):
  forward (lower bound on ES_S):  FS: EF_P+L   SS: ES_P+L   FF: EF_P+L-dur_S   SF: ES_P+L-dur_S
  backward (upper bound on LF_P): FS: LS_S-L   SS: LS_S-L+dur_P   FF: LF_S-L   SF: LF_S-L+dur_P
"""

from __future__ import annotations

import datetime as dt
from collections import deque
from dataclasses import dataclass

from schedule_forensics.schemas import (
    Calendar,
    ConstraintType,
    RelationType,
    Schedule,
    Task,
)


class CPMError(ValueError):
    """Raised when the network cannot be scheduled -- a logic cycle, or a date
    constraint/deadline that is not yet honored (refusing rather than emitting a
    silently-wrong schedule)."""


@dataclass(frozen=True)
class TaskTiming:
    """Computed schedule for one task, in working-minute offsets from start."""

    unique_id: int
    early_start: int
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int
    is_critical: bool


@dataclass(frozen=True)
class CPMResult:
    """The full forward/backward-pass result for a schedule."""

    timings: dict[int, TaskTiming]
    project_finish: int  # working-minute offset of the network's latest early finish
    critical_path: tuple[int, ...]  # unique_ids with total_float <= 0, in topo order


# An edge as carried through the engine: (predecessor_id, successor_id, type, lag).
_Edge = tuple[int, int, RelationType, int]
# A neighbour reference on one side of a link: (other_id, type, lag).
_Link = tuple[int, RelationType, int]


def _scheduled_tasks(schedule: Schedule) -> list[Task]:
    # Summary tasks are date rollups, not real activities -- excluded from the network.
    return [t for t in schedule.tasks if not t.is_summary]


def _es_lower_bound(rel: RelationType, es_p: int, ef_p: int, lag: int, dur_s: int) -> int:
    """Lower bound a predecessor link imposes on the successor's early start."""
    if rel is RelationType.FS:
        return ef_p + lag
    if rel is RelationType.SS:
        return es_p + lag
    if rel is RelationType.FF:
        return ef_p + lag - dur_s
    return es_p + lag - dur_s  # SF


def _lf_upper_bound(rel: RelationType, ls_s: int, lf_s: int, lag: int, dur_p: int) -> int:
    """Upper bound a successor link imposes on the predecessor's late finish."""
    if rel is RelationType.FS:
        return ls_s - lag
    if rel is RelationType.SS:
        return ls_s - lag + dur_p
    if rel is RelationType.FF:
        return lf_s - lag
    return lf_s - lag + dur_p  # SF


def _link_slack(rel: RelationType, es_p: int, ef_p: int, es_s: int, ef_s: int, lag: int) -> int:
    """Relationship slack for free-float: how far P may slip before this link binds.

    Reduces to the standard FS free float. For SS/FF/SF this is the slack measured
    at the link's governing event (reference tools vary on non-FS free float; total
    float -- the primary forensic signal -- is exact for every type)."""
    if rel is RelationType.FS:
        return es_s - (ef_p + lag)
    if rel is RelationType.SS:
        return es_s - (es_p + lag)
    if rel is RelationType.FF:
        return ef_s - (ef_p + lag)
    return ef_s - (es_p + lag)  # SF


def _topo_order(task_ids: list[int], edges: list[tuple[int, int]]) -> list[int]:
    """Kahn topological sort over precedence edges (pred -> succ). Raises on a cycle."""
    successors: dict[int, list[int]] = {tid: [] for tid in task_ids}
    indegree: dict[int, int] = dict.fromkeys(task_ids, 0)
    for pred, succ in edges:
        successors[pred].append(succ)
        indegree[succ] += 1
    queue: deque[int] = deque(sorted(tid for tid in task_ids if indegree[tid] == 0))
    order: list[int] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        ready: list[int] = []
        for succ in successors[node]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                ready.append(succ)
        queue.extend(sorted(ready))  # deterministic ordering
    if len(order) != len(task_ids):
        raise CPMError("schedule logic contains a cycle; cannot compute CPM")
    return order


def compute_cpm(schedule: Schedule, required_finish_offset: int | None = None) -> CPMResult:
    """Run the forward and backward passes and return per-task timings.

    ``required_finish_offset`` (working minutes) imposes an earlier project finish
    for the backward pass; when it is earlier than the network's own early finish,
    the driving chain shows negative total float.

    Raises ``CPMError`` if any scheduled task carries a date constraint other than
    ASAP, or a deadline (deferred -- see module docstring).
    """
    tasks = _scheduled_tasks(schedule)

    unsupported = [
        t.unique_id
        for t in tasks
        if t.constraint_type is not ConstraintType.ASAP or t.deadline is not None
    ]
    if unsupported:
        raise CPMError(
            "date constraints and deadlines are not yet honored by the CPM engine "
            "(deferred to the next increment, to avoid silently-wrong output); "
            f"affected task UniqueIDs: {unsupported}"
        )

    task_ids = [t.unique_id for t in tasks]
    id_set = set(task_ids)
    duration: dict[int, int] = {t.unique_id: t.duration_minutes for t in tasks}

    # All link types; ignore links touching summary tasks (excluded from the network).
    edges: list[_Edge] = [
        (r.predecessor_id, r.successor_id, r.type, r.lag_minutes)
        for r in schedule.relations
        if r.predecessor_id in id_set and r.successor_id in id_set
    ]
    order = _topo_order(task_ids, [(pred, succ) for pred, succ, _rel, _lag in edges])

    preds: dict[int, list[_Link]] = {tid: [] for tid in task_ids}
    succs: dict[int, list[_Link]] = {tid: [] for tid in task_ids}
    for pred, succ, rel, lag in edges:
        preds[succ].append((pred, rel, lag))
        succs[pred].append((succ, rel, lag))

    # ---- forward pass (ES floored at 0 == project start; ASAP) ----
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    for tid in order:
        dur_s = duration[tid]
        bounds = [
            _es_lower_bound(rel, early_start[p], early_finish[p], lag, dur_s)
            for p, rel, lag in preds[tid]
        ]
        es = max([0, *bounds])
        early_start[tid] = es
        early_finish[tid] = es + dur_s

    network_finish = max(early_finish.values(), default=0)
    backward_target = (
        required_finish_offset if required_finish_offset is not None else network_finish
    )

    # ---- backward pass (LF capped at the backward target) ----
    late_finish: dict[int, int] = {}
    late_start: dict[int, int] = {}
    for tid in reversed(order):
        dur_p = duration[tid]
        bounds = [
            _lf_upper_bound(rel, late_start[s], late_finish[s], lag, dur_p)
            for s, rel, lag in succs[tid]
        ]
        lf = min([backward_target, *bounds])
        late_finish[tid] = lf
        late_start[tid] = lf - dur_p

    timings: dict[int, TaskTiming] = {}
    for tid in task_ids:
        total = late_start[tid] - early_start[tid]
        if succs[tid]:
            free = min(
                _link_slack(
                    rel,
                    early_start[tid],
                    early_finish[tid],
                    early_start[s],
                    early_finish[s],
                    lag,
                )
                for s, rel, lag in succs[tid]
            )
        else:
            free = backward_target - early_finish[tid]
        timings[tid] = TaskTiming(
            unique_id=tid,
            early_start=early_start[tid],
            early_finish=early_finish[tid],
            late_start=late_start[tid],
            late_finish=late_finish[tid],
            total_float=total,
            free_float=free,
            is_critical=total <= 0,
        )

    critical_path = tuple(tid for tid in order if timings[tid].is_critical)
    return CPMResult(timings=timings, project_finish=network_finish, critical_path=critical_path)


def _next_working_day(day: dt.datetime, calendar: Calendar) -> dt.datetime:
    nxt = day + dt.timedelta(days=1)
    while nxt.date().weekday() not in calendar.work_weekdays or nxt.date() in calendar.holidays:
        nxt += dt.timedelta(days=1)
    return nxt


def offset_to_datetime(start: dt.datetime, minutes: int, calendar: Calendar) -> dt.datetime:
    """Convert a non-negative working-minute offset to a wall-clock datetime.

    ``start`` is assumed to sit at the beginning of a working day. Each working
    weekday contributes ``calendar.working_minutes_per_day`` contiguous minutes;
    weekends and holidays are skipped.
    """
    if minutes < 0:
        raise ValueError("offset_to_datetime: minutes must be >= 0")
    per_day = calendar.working_minutes_per_day
    day = start
    while day.date().weekday() not in calendar.work_weekdays or day.date() in calendar.holidays:
        day = _next_working_day(day, calendar)
    remaining = minutes
    while remaining > 0:
        if remaining <= per_day:
            return day + dt.timedelta(minutes=remaining)
        remaining -= per_day
        day = _next_working_day(day, calendar)
    return day
