"""Critical Path Method engine -- forward + backward pass (trust-root, LAW 2).

The internal time axis is INTEGER WORKING MINUTES, measured as an offset from
``Schedule.project_start``. An integer working-minute axis makes the arithmetic
exact and hand-verifiable, and removes the end-of-day / start-of-next-day
boundary class of bugs by construction (the wall-clock conversion is a separate,
separately-tested concern -- see ``offset_to_datetime``).

Scope of this slice (documented, not silently limited -- see PHASE-COMPLETE-1.md):
  * Link types: Finish-to-Start with lag/lead. SS/FF/SF are deferred.
  * Scheduling: ASAP. The full date-constraint matrix (SNET/SNLT/FNET/FNLT/
    MSO/MFO) and deadlines are deferred.
  * Total float MAY be negative when an earlier ``required_finish_offset`` is
    imposed -- this is how schedule pressure surfaces forensically, and it is
    computed in exact integer minutes here without a calendar walk.

Critical-path definition: ``total_float <= 0`` (matches MS Project's behaviour
once negative float exists). Cited in docs/REFERENCES.md.
"""

from __future__ import annotations

import datetime as dt
from collections import deque
from dataclasses import dataclass

from schedule_forensics.schemas import Calendar, RelationType, Schedule, Task


class CPMError(ValueError):
    """Raised when the network cannot be scheduled (e.g., a logic cycle)."""


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


def _scheduled_tasks(schedule: Schedule) -> list[Task]:
    # Summary tasks are date rollups, not real activities -- excluded from the network.
    return [t for t in schedule.tasks if not t.is_summary]


def _topo_order(task_ids: list[int], fs_edges: list[tuple[int, int, int]]) -> list[int]:
    """Kahn topological sort over FS edges (pred -> succ). Raises on a cycle."""
    successors: dict[int, list[int]] = {tid: [] for tid in task_ids}
    indegree: dict[int, int] = dict.fromkeys(task_ids, 0)
    for pred, succ, _lag in fs_edges:
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
        # sort newly-ready nodes for deterministic ordering
        queue.extend(sorted(ready))
    if len(order) != len(task_ids):
        raise CPMError("schedule logic contains a cycle; cannot compute CPM")
    return order


def compute_cpm(schedule: Schedule, required_finish_offset: int | None = None) -> CPMResult:
    """Run the forward and backward passes and return per-task timings.

    ``required_finish_offset`` (working minutes) imposes an earlier project
    finish for the backward pass; when it is earlier than the network's own
    early finish, the driving chain shows negative total float.
    """
    tasks = _scheduled_tasks(schedule)
    task_ids = [t.unique_id for t in tasks]
    id_set = set(task_ids)
    duration: dict[int, int] = {t.unique_id: t.duration_minutes for t in tasks}

    # FS edges only (this slice); ignore links touching summary tasks.
    fs_edges: list[tuple[int, int, int]] = [
        (r.predecessor_id, r.successor_id, r.lag_minutes)
        for r in schedule.relations
        if r.type is RelationType.FS and r.predecessor_id in id_set and r.successor_id in id_set
    ]

    order = _topo_order(task_ids, fs_edges)
    preds: dict[int, list[tuple[int, int]]] = {tid: [] for tid in task_ids}
    succs: dict[int, list[tuple[int, int]]] = {tid: [] for tid in task_ids}
    for pred, succ, lag in fs_edges:
        preds[succ].append((pred, lag))
        succs[pred].append((succ, lag))

    # ---- forward pass ----
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    for tid in order:
        es = max((early_finish[p] + lag for p, lag in preds[tid]), default=0)
        early_start[tid] = es
        early_finish[tid] = es + duration[tid]

    network_finish = max(early_finish.values(), default=0)
    backward_target = (
        required_finish_offset if required_finish_offset is not None else network_finish
    )

    # ---- backward pass ----
    late_finish: dict[int, int] = {}
    late_start: dict[int, int] = {}
    for tid in reversed(order):
        lf = min((late_start[s] - lag for s, lag in succs[tid]), default=backward_target)
        late_finish[tid] = lf
        late_start[tid] = lf - duration[tid]

    timings: dict[int, TaskTiming] = {}
    for tid in task_ids:
        total = late_start[tid] - early_start[tid]
        if succs[tid]:
            free = min(early_start[s] - lag for s, lag in succs[tid]) - early_finish[tid]
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
