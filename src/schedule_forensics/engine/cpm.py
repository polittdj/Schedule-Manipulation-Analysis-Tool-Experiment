"""Critical Path Method engine — forward + backward pass (trust-root, Law 2: fidelity).

The internal time axis is **integer working minutes**, measured as an offset from
``Schedule.project_start``. An integer working-minute axis makes the arithmetic exact
and hand-verifiable, and removes the end-of-day / start-of-next-day boundary class of
bugs by construction (no binary-float drift — ADR-0005 determinism).

Scope of this engine (documented, not silently limited — Law 2):

* **Link types:** all four (FS / SS / FF / SF) with lag/lead, in working minutes.
* **Date constraints honored** (MS Project "honor constraint dates" mode):
  ``SNET`` / ``FNET`` are forward floors; ``SNLT`` / ``FNLT`` are backward caps;
  ``MSO`` / ``MFO`` **pin** the start / finish (forward pin + matching backward cap,
  so a pinned activity carries zero or — under successor pressure — negative float);
  a task ``deadline`` is a backward cap that can drive negative float.
* **Stored dates honored where logic does not bind** (ADR-0034): an UNSTARTED
  manually-scheduled task pins at its stored start (MS Project keeps it there), and an
  unstarted auto task with no predecessors floors at its stored start (a pure forward
  pass would pack every unlinked task to the project start — wrong for real
  sparse-logic files). The affected UniqueIDs are reported on
  :attr:`CPMResult.date_driven` and surfaced as a cited finding ("dates not supported
  by logic") — honored, never silently rescheduled.
* **Refused** (raises :class:`CPMError` rather than emit a silently-wrong schedule —
  Law 2): ``ALAP``. Its as-late-as-possible semantics are backward-pass-driven and
  interact subtly with float; it does not appear in the parity schedules and is out of
  scope for this engine.
* **Total float may be negative** (an imposed finish, or a violated cap / deadline /
  pin). The driving-slack analysis (M6) drives the backward pass to a target finish.

**Critical-path definition:** ``total_float <= 0`` (the pure CPM property of the
network). The Acumen "Critical" *metric* additionally excludes completed activities
(``percent_complete < 100``); that filter lives in :mod:`.float_analysis`, not here.

``datetime -> offset`` mapping: constraint/deadline datetimes convert to working
minutes at working-day granularity plus a clamped intraday term (``project_start`` is
assumed to sit at a working-day start). The precise "honor constraint dates" intraday
edge behavior is a defined model pending live MS Project validation (ADR-0010).
"""

from __future__ import annotations

import datetime as dt
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

from schedule_forensics.engine.summary_logic import (
    SummaryLogicExplosion,
    lower_summary_relationships,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

#: Constraints the engine refuses (fail loud rather than schedule wrongly — Law 2).
_REFUSED_CONSTRAINTS = frozenset({ConstraintType.ALAP})
#: Forward-floor / backward-cap date constraints.
_FLOOR_CAP_CONSTRAINTS = frozenset(
    {ConstraintType.SNET, ConstraintType.FNET, ConstraintType.SNLT, ConstraintType.FNLT}
)
#: Constraints that pin a task in time (forward pin + backward cap).
_PIN_CONSTRAINTS = frozenset({ConstraintType.MSO, ConstraintType.MFO})


class CPMError(ValueError):
    """The network cannot be scheduled — a logic cycle, a refused constraint, or a
    date constraint missing its ``constraint_date``. Raised instead of returning a
    silently-wrong schedule (Law 2)."""


@dataclass(frozen=True)
class TaskTiming:
    """Computed schedule for one task, in working-minute offsets from project start.

    ``total_float``/``free_float`` are working minutes (convert at the presentation
    boundary via :mod:`schedule_forensics.model.units`). ``is_critical`` is the pure
    CPM property ``total_float <= 0``.
    """

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
    """The full forward/backward-pass result for one schedule."""

    timings: Mapping[int, TaskTiming]
    project_finish: int  # working-minute offset of the network's latest early finish
    critical_path: tuple[int, ...]  # unique_ids with total_float <= 0, in topo order
    #: UniqueIDs whose forward dates come from their STORED start (manual pin or
    #: logic-unbound floor — ADR-0034), not from network logic: the schedule reproduces
    #: the source file, and these are the "dates not supported by logic" the findings cite.
    date_driven: tuple[int, ...] = ()

    def timing(self, unique_id: int) -> TaskTiming:
        """Timing for ``unique_id``; raises ``KeyError`` if the task is not scheduled."""
        return self.timings[unique_id]


# A neighbour reference on one side of a link: (other_id, type, lag_minutes).
_Link = tuple[int, RelationshipType, int]


def _scheduled_tasks(schedule: Schedule) -> list[Task]:
    """Real activities only — summary tasks (date rollups) and inactive tasks
    (``is_active=False``) never enter the CPM network. MS Project / Acumen exclude inactive
    tasks from scheduling, so their links drop with them (the network is keyed on this set) and
    they cannot appear on the critical path or in any derived float (ADR-0128)."""
    return [t for t in schedule.tasks if not t.is_summary and t.is_active]


def es_lower_bound(rel: RelationshipType, es_p: int, ef_p: int, lag: int, dur_s: int) -> int:
    """Lower bound a predecessor link imposes on the successor's early start."""
    if rel is RelationshipType.FS:
        return ef_p + lag
    if rel is RelationshipType.SS:
        return es_p + lag
    if rel is RelationshipType.FF:
        return ef_p + lag - dur_s
    return es_p + lag - dur_s  # SF


def lf_upper_bound(rel: RelationshipType, ls_s: int, lf_s: int, lag: int, dur_p: int) -> int:
    """Upper bound a successor link imposes on the predecessor's late finish."""
    if rel is RelationshipType.FS:
        return ls_s - lag
    if rel is RelationshipType.SS:
        return ls_s - lag + dur_p
    if rel is RelationshipType.FF:
        return lf_s - lag
    return lf_s - lag + dur_p  # SF


def link_slack(rel: RelationshipType, es_p: int, ef_p: int, es_s: int, ef_s: int, lag: int) -> int:
    """Relationship slack for free float: how far P may slip before this link binds.

    Reduces to the standard FS free float. For SS/FF/SF this is the slack at the
    link's governing event (reference tools vary on non-FS free float; total float —
    the primary forensic signal — is exact for every type).
    """
    if rel is RelationshipType.FS:
        return es_s - (ef_p + lag)
    if rel is RelationshipType.SS:
        return es_s - (es_p + lag)
    if rel is RelationshipType.FF:
        return ef_s - (ef_p + lag)
    return ef_s - (es_p + lag)  # SF


def _count_working_days(calendar: Calendar, d0: dt.date, d1: dt.date) -> int:
    """Number of working days in the half-open range ``[d0, d1)`` (requires ``d0 <= d1``).

    Full-weeks arithmetic + a short (<7-day) remainder loop, then subtract the holidays
    that fall on a working weekday inside the range — O(weeks-of-remainder + holidays),
    not O(days). Equivalent to the day-by-day count (see ``test_cpm_date_equivalence``).
    """
    total = (d1 - d0).days
    if total <= 0:
        return 0
    workdays = set(calendar.work_weekdays)
    full_weeks, remainder = divmod(total, 7)
    count = full_weeks * len(workdays)
    w0 = d0.weekday()
    # the remainder days are d0+full_weeks*7+i for i in [0,remainder); weekday == (w0+i)%7
    count += sum(1 for i in range(remainder) if (w0 + i) % 7 in workdays)
    # a holiday only ever removed a day that was otherwise a working weekday
    count -= sum(1 for h in calendar.holidays if d0 <= h < d1 and h.weekday() in workdays)
    return count


def datetime_to_offset(start: dt.datetime, target: dt.datetime, calendar: Calendar) -> int:
    """Signed working-minute offset of ``target`` from ``start``.

    ``start`` is assumed to sit at a working-day start. The date contributes whole
    working days; the intraday term is ``(target_time - start_time)`` clamped to
    ``[0, working_minutes_per_day]``. A target on a non-working day contributes no
    intraday minutes (ADR-0010, H-CONSTRAINT-DATETIME).
    """
    per_day = calendar.working_minutes_per_day
    start_tod = start.hour * 60 + start.minute
    target_tod = target.hour * 60 + target.minute
    on_working_day = (
        target.date().weekday() in calendar.work_weekdays and target.date() not in calendar.holidays
    )
    intraday = min(max(target_tod - start_tod, 0), per_day) if on_working_day else 0
    if target.date() >= start.date():
        return _count_working_days(calendar, start.date(), target.date()) * per_day + intraday
    return -_count_working_days(calendar, target.date(), start.date()) * per_day + intraday


def _elapsed_finish_offset(
    project_start: dt.datetime, calendar: Calendar, start_offset: int, minutes: int
) -> int:
    """An ELAPSED task's finish offset: wall-clock minutes from its start instant.

    MS Project elapsed durations ("1 eday") ignore both task and project calendars —
    the finish is start + N clock minutes, then mapped back onto the working axis
    (a Saturday-morning finish reads as Friday end-of-day for successors)."""
    start_dt = offset_to_datetime(project_start, max(start_offset, 0), calendar)
    return datetime_to_offset(project_start, start_dt + dt.timedelta(minutes=minutes), calendar)


def _elapsed_start_offset(
    project_start: dt.datetime, calendar: Calendar, finish_offset: int, minutes: int
) -> int:
    """The inverse: an elapsed task's latest start given a finish bound."""
    finish_dt = offset_to_datetime(project_start, max(finish_offset, 0), calendar)
    return datetime_to_offset(project_start, finish_dt - dt.timedelta(minutes=minutes), calendar)


def _next_working_day(day: dt.datetime, calendar: Calendar) -> dt.datetime:
    nxt = day + dt.timedelta(days=1)
    while nxt.date().weekday() not in calendar.work_weekdays or nxt.date() in calendar.holidays:
        nxt += dt.timedelta(days=1)
    return nxt


def _advance_working_days(start_day: dt.date, k: int, calendar: Calendar) -> dt.date:
    """The working day ``k`` working-days after ``start_day`` (which must be a working day).

    Week-jump + short remainder step, then compensate for any working-weekday holidays the
    jump passed over (each pushes the result one more working day; the newly-traversed span
    may add more, so it iterates — but only over holidays, never day-by-day). Equivalent to
    applying ``_next_working_day`` ``k`` times (see ``test_cpm_date_equivalence``).
    """
    if k <= 0:
        return start_day
    workdays = set(calendar.work_weekdays)
    wdpw = len(workdays)
    holidays = calendar.holidays
    cur = start_day
    needed = k
    while needed > 0:
        full_weeks, remainder = divmod(needed, wdpw)
        nxt = cur + dt.timedelta(days=full_weeks * 7)  # same weekday, full*wdpw weekdays on
        steps = remainder
        while steps > 0:
            nxt += dt.timedelta(days=1)
            if nxt.weekday() in workdays:
                steps -= 1
        # working-weekday holidays in (cur, nxt] did not actually advance us — make them up
        needed = sum(1 for h in holidays if cur < h <= nxt and h.weekday() in workdays)
        cur = nxt
    return cur


def offset_to_datetime(start: dt.datetime, minutes: int, calendar: Calendar) -> dt.datetime:
    """Convert a non-negative working-minute offset to a wall-clock datetime.

    ``start`` is assumed to sit at the beginning of a working day. Each working
    weekday contributes ``calendar.working_minutes_per_day`` contiguous minutes;
    weekends and holidays are skipped. Inverse of :func:`datetime_to_offset` on the
    working-time grid.
    """
    if minutes < 0:
        raise ValueError("offset_to_datetime: minutes must be >= 0")
    per_day = calendar.working_minutes_per_day
    day = start
    while day.date().weekday() not in calendar.work_weekdays or day.date() in calendar.holidays:
        day = _next_working_day(day, calendar)
    # Whole working days consumed, then the intraday remainder. An exact multiple of per_day
    # lands at the END of the last full day (the strict ``remaining > per_day`` boundary), so
    # one fewer day is advanced and the remainder is a full day's minutes.
    quotient, remainder = divmod(minutes, per_day)
    if minutes == 0:
        advance, intraday = 0, 0
    elif remainder == 0:
        advance, intraday = quotient - 1, per_day
    else:
        advance, intraday = quotient, remainder
    target_date = _advance_working_days(day.date(), advance, calendar)
    day += dt.timedelta(days=(target_date - day.date()).days)  # preserve time-of-day exactly
    return day + dt.timedelta(minutes=intraday)


def _topo_order(task_ids: list[int], edges: list[tuple[int, int]]) -> list[int]:
    """Kahn topological sort over precedence edges (pred -> succ). Raises on a cycle.

    Ties are broken by ascending UniqueID so the order — and thus the reported
    critical path — is deterministic (ADR-0005).
    """
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
        queue.extend(sorted(ready))
    if len(order) != len(task_ids):
        raise CPMError("schedule logic contains a cycle; cannot compute CPM")
    return order


def _constraint_bounds(
    schedule: Schedule, tasks: list[Task], duration: dict[int, int]
) -> tuple[dict[int, int], dict[int, int], dict[int, int]]:
    """Resolve date constraints + deadlines into working-minute offset bounds.

    Returns ``(es_floor, es_pin, lf_cap)``: ``es_floor`` raises the forward early
    start (SNET/FNET), ``es_pin`` forces it exactly (MSO/MFO), and ``lf_cap`` caps the
    backward late finish (SNLT/FNLT/MSO/MFO/deadline). Raises :class:`CPMError` for a
    refused constraint (ALAP) or a date constraint missing its ``constraint_date``.
    """
    refused = sorted(t.unique_id for t in tasks if t.constraint_type in _REFUSED_CONSTRAINTS)
    if refused:
        raise CPMError(
            "ALAP (as-late-as-possible) constraints are not supported by this engine "
            f"(refused rather than mis-scheduled — Law 2); affected UniqueIDs: {refused}"
        )

    es_floor: dict[int, int] = {}
    es_pin: dict[int, int] = {}
    lf_cap: dict[int, int] = {}
    for task in tasks:
        tid = task.unique_id
        ctype = task.constraint_type
        if ctype in _FLOOR_CAP_CONSTRAINTS or ctype in _PIN_CONSTRAINTS:
            if task.constraint_date is None:
                raise CPMError(f"task {tid} has constraint {ctype} but no constraint_date")
            off = datetime_to_offset(
                schedule.project_start, task.constraint_date, schedule.calendar
            )
            elapsed = task.duration_is_elapsed and duration[tid] > 0

            def _minus_dur(offset: int, *, _e: bool = elapsed, _d: int = duration[tid]) -> int:
                if _e:
                    return _elapsed_start_offset(
                        schedule.project_start, schedule.calendar, offset, _d
                    )
                return offset - _d

            def _plus_dur(offset: int, *, _e: bool = elapsed, _d: int = duration[tid]) -> int:
                if _e:
                    return _elapsed_finish_offset(
                        schedule.project_start, schedule.calendar, offset, _d
                    )
                return offset + _d

            if ctype is ConstraintType.SNET:
                es_floor[tid] = off
            elif ctype is ConstraintType.FNET:
                es_floor[tid] = _minus_dur(off)
            elif ctype is ConstraintType.SNLT:
                lf_cap[tid] = _plus_dur(off)
            elif ctype is ConstraintType.FNLT:
                lf_cap[tid] = off
            elif ctype is ConstraintType.MSO:  # must start on -> pin start
                es_pin[tid] = off
                lf_cap[tid] = _plus_dur(off)
            else:  # MFO — must finish on -> pin finish
                es_pin[tid] = _minus_dur(off)
                lf_cap[tid] = off
        if task.deadline is not None:
            d_off = datetime_to_offset(schedule.project_start, task.deadline, schedule.calendar)
            lf_cap[tid] = min(lf_cap.get(tid, d_off), d_off)
    return es_floor, es_pin, lf_cap


def _stored_date_bounds(
    schedule: Schedule, tasks: list[Task], has_preds: frozenset[int]
) -> tuple[dict[int, int], dict[int, int]]:
    """Stored-start offsets the forward pass honors on UNSTARTED tasks (ADR-0034).

    Real-world sparse-logic / template schedules carry dates network logic does not
    support: manually-scheduled tasks sit exactly where MS Project stored them, and an
    auto task without a single predecessor was hand-positioned (a pure forward pass packs
    them all at the project start — the operator's sparse-logic file computed 2026-08
    against MSP's 2027-03). Returns ``(pin, floor)``: an unstarted **manual** task PINS
    at its stored start (MSP keeps it there even against logic); an unstarted,
    **logic-unbound** auto task FLOORS there (logic/constraints may still push it later).
    Started work is untouched — actuals anchor the record — and the curated parity
    schedules' dates are logic-true, so neither rule fires on them (pinned by tests).
    Offsets clamp at the project start (negative offsets are unrenderable).
    """
    pin: dict[int, int] = {}
    floor: dict[int, int] = {}
    for task in tasks:
        if task.start is None or task.actual_start is not None or task.percent_complete > 0:
            continue
        off = max(datetime_to_offset(schedule.project_start, task.start, schedule.calendar), 0)
        if task.is_manual:
            pin[task.unique_id] = off
        elif task.unique_id not in has_preds and off > 0:
            floor[task.unique_id] = off
    return pin, floor


def compute_cpm(
    schedule: Schedule,
    *,
    required_finish_offset: int | None = None,
    duration_overrides: Mapping[int, int] | None = None,
) -> CPMResult:
    """Run the forward and backward passes and return per-task timings.

    ``required_finish_offset`` (working minutes from ``project_start``) imposes a
    project finish for the backward pass; when it is earlier than the network's own
    early finish, the driving chain shows negative total float (used by the M6
    driving-slack analysis). Raises :class:`CPMError` on a logic cycle or a refused /
    malformed constraint.

    ``duration_overrides`` (UniqueID → working-minute duration) substitutes the working
    duration of the listed tasks for this pass only — the **sole** hook the Monte-Carlo
    SRA engine (:mod:`schedule_forensics.engine.sra`) uses to recompute the network under
    sampled durations, so the simulation can never diverge from this trusted solver
    (Law 2). Everything else — calendars, lags, constraints, progress/remaining handling,
    summary logic — is unchanged. When ``None`` (the default) the result is byte-identical
    to the no-argument call.
    """
    tasks = _scheduled_tasks(schedule)

    def _effective_duration(task: Task) -> int:
        if duration_overrides is not None:
            return duration_overrides.get(task.unique_id, task.duration_minutes)
        return task.duration_minutes

    duration: dict[int, int] = {t.unique_id: _effective_duration(t) for t in tasks}
    es_floor, es_pin, lf_cap = _constraint_bounds(schedule, tasks, duration)

    task_ids = [t.unique_id for t in tasks]
    id_set = set(task_ids)
    # Logic attached to a SUMMARY task is honored the way MS Project does it: lowered onto
    # the summary's leaf descendants (ADR-0043). A no-op for schedules without summary
    # logic, so the leaf-only network — and parity — is unchanged. A pathologically dense
    # summary-to-summary cross-product fails loud (audit-E) as a CPMError so the web layer
    # degrades to a disclosed 422 instead of hanging/OOM-ing.
    try:
        relationships = lower_summary_relationships(schedule)
    except SummaryLogicExplosion as exc:
        raise CPMError(str(exc)) from exc
    edges = [
        (r.predecessor_id, r.successor_id, r.type, r.lag_minutes)
        for r in relationships
        if r.predecessor_id in id_set and r.successor_id in id_set
    ]
    order = _topo_order(task_ids, [(pred, succ) for pred, succ, _rel, _lag in edges])

    preds: dict[int, list[_Link]] = {tid: [] for tid in task_ids}
    succs: dict[int, list[_Link]] = {tid: [] for tid in task_ids}
    for pred, succ, rel, lag in edges:
        preds[succ].append((pred, rel, lag))
        succs[pred].append((succ, rel, lag))

    # ---- forward pass (ES >= 0 == project start; raised by SNET/FNET; pinned by MSO/MFO;
    # stored starts honored for unstarted manual / logic-unbound tasks — ADR-0034) ----
    has_preds = frozenset(tid for tid in task_ids if preds[tid])
    stored_pin, stored_floor = _stored_date_bounds(schedule, tasks, has_preds)
    elapsed_ids = {t.unique_id for t in tasks if t.duration_is_elapsed and t.duration_minutes > 0}
    ps, cal = schedule.project_start, schedule.calendar
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    date_driven: list[int] = []
    for tid in order:
        dur_s = duration[tid]
        # the pure logic+constraint early start — computed even under a pin, so the
        # logic-vs-stored divergence the findings report is measurable
        if tid in elapsed_ids:
            # FF/SF bound the FINISH; convert each to a start bound on the wall clock
            bounds = []
            for p, rel, lag in preds[tid]:
                if rel in (RelationshipType.FS, RelationshipType.SS):
                    bounds.append(es_lower_bound(rel, early_start[p], early_finish[p], lag, 0))
                else:
                    anchor = early_finish[p] if rel is RelationshipType.FF else early_start[p]
                    bounds.append(_elapsed_start_offset(ps, cal, anchor + lag, dur_s))
            if tid in es_floor:
                bounds.append(es_floor[tid])
            logic_es = max([0, *bounds])
        else:
            bounds = [
                es_lower_bound(rel, early_start[p], early_finish[p], lag, dur_s)
                for p, rel, lag in preds[tid]
            ]
            if tid in es_floor:
                bounds.append(es_floor[tid])
            logic_es = max([0, *bounds])
        if tid in es_pin:
            es = es_pin[tid]
        elif tid in stored_pin:
            es = stored_pin[tid]
            if es != logic_es:
                date_driven.append(tid)
        elif tid in stored_floor and stored_floor[tid] > logic_es:
            es = stored_floor[tid]
            date_driven.append(tid)
        else:
            es = logic_es
        early_start[tid] = es
        early_finish[tid] = (
            _elapsed_finish_offset(ps, cal, es, dur_s) if tid in elapsed_ids else es + dur_s
        )

    network_finish = max(early_finish.values(), default=0)
    backward_target = (
        required_finish_offset if required_finish_offset is not None else network_finish
    )

    # ---- backward pass (LF capped at the backward target, and by SNLT/FNLT/MSO/MFO/deadline) ----
    late_finish: dict[int, int] = {}
    late_start: dict[int, int] = {}
    for tid in reversed(order):
        dur_p = duration[tid]
        if tid in elapsed_ids:
            finish_caps = [backward_target]
            start_caps: list[int] = []
            for s, rel, lag in succs[tid]:
                if rel is RelationshipType.FS:
                    finish_caps.append(late_start[s] - lag)
                elif rel is RelationshipType.FF:
                    finish_caps.append(late_finish[s] - lag)
                elif rel is RelationshipType.SS:
                    start_caps.append(late_start[s] - lag)
                else:  # SF: the successor's finish is anchored to THIS task's start
                    start_caps.append(late_finish[s] - lag)
            if tid in lf_cap:
                finish_caps.append(lf_cap[tid])
            # Slack is computed in CAP SPACE — a finish cap and this task's early finish are both
            # working-grid offsets of the same event, so their difference IS the float. Never
            # round-trip the elapsed task's wall-clock instants through the working axis here:
            # that mapping is lossy across non-working time (a Sunday-08:00 finish reads back as
            # Friday 17:00), and reconstructing the late start from it fabricated NEGATIVE float
            # (and false DCMA-07/CPLI failures) for every weekend/holiday-spanning elapsed
            # activity (QC audit D2). late start/finish are then the early dates shifted by the
            # slack, keeping LS-ES == LF-EF on the working axis.
            slack_cands = [f - early_finish[tid] for f in finish_caps]
            slack_cands += [s0 - early_start[tid] for s0 in start_caps]
            slack = min(slack_cands)
            late_start[tid] = early_start[tid] + slack
            late_finish[tid] = early_finish[tid] + slack
        else:
            bounds = [
                lf_upper_bound(rel, late_start[s], late_finish[s], lag, dur_p)
                for s, rel, lag in succs[tid]
            ]
            if tid in lf_cap:
                bounds.append(lf_cap[tid])
            lf = min([backward_target, *bounds])
            late_finish[tid] = lf
            late_start[tid] = lf - dur_p

    timings: dict[int, TaskTiming] = {}
    for tid in task_ids:
        total = late_start[tid] - early_start[tid]
        if succs[tid]:
            free = min(
                link_slack(
                    rel, early_start[tid], early_finish[tid], early_start[s], early_finish[s], lag
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
    return CPMResult(
        timings=timings,
        project_finish=network_finish,
        critical_path=critical_path,
        date_driven=tuple(sorted(date_driven)),
    )
