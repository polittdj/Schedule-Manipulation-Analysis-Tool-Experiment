"""Driving slack to a focus UniqueID — the SSI MS Project add-on parity (§6.C, ADR-0011).

Given a user-chosen **target (focus) UniqueID**, this computes each driving activity's
**Driving Slack** — how many working days it can slip before it would delay the focus
task along its logic path. The method (matched bit-for-bit against the SSI golden export
for Project5 / UID 143, `docs/PLAN/SSI-DRIVING-SLACK.md`):

1. Trace the focus task's ancestors (its transitive predecessors — :mod:`.path_trace`).
2. Take each task's **as-scheduled** start/finish from the schedule's stored ``start``/
   ``finish`` (progress-aware — SSI runs inside MS Project and measures against the
   *progressed* schedule). The working-minute conversion honors the calendar's true intraday
   hours (a lunch break is not over-counted — ADR-0117). Where a task has no stored dates
   (hand-authored schedules), fall back to the CPM forward pass.
3. Accumulate slack along the driving direction: ``slack(focus) = 0`` and, for each ancestor,
   ``slack = min over successor links of (the link's free float + that successor's slack)``.
   Each link's free float is counted on the **successor's own calendar** — so on a
   multi-calendar file a predecessor's slack is measured in the successor's working days,
   honoring per-task calendars and worked-weekend exceptions (ADR-0118). On a single-calendar
   schedule this is identical to the late-finish backward pass (raw spans, no snap — ADR-0116).
4. Tasks on the driving path have slack **0**; the rest are classified into the user's
   secondary/tertiary day-tiers (§6.C; defaults 0<secondary≤10, 10<tertiary≤20).

Using stored dates was the key to exact parity: without it, completed activities whose
actuals ran late (e.g. Project5 UID 8/13/14/16, +16 days) computed too much slack. On the
operator's leveled Large Test File (focus UID 152, 783 activities) the method reproduces the
SSI Directional Path export to the working day for all 783 (driving path 61/61 exact).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from schedule_forensics.engine.cpm import (
    CPMResult,
    _count_working_days,
    compute_cpm,
    datetime_to_offset,
)
from schedule_forensics.engine.path_trace import ancestors_of, descendants_of, topo_order
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.units import minutes_to_days


def _stored_offset(project_start: dt.datetime, target: dt.datetime, calendar: Calendar) -> int:
    """Working-minute offset of a stored date, honoring intraday gaps (a lunch break).

    The engine's :func:`datetime_to_offset` models the day as one contiguous block, so an
    afternoon finish (after the 12:00-13:00 lunch) is over-counted by the lunch hour - which
    accumulates through the driving-slack backward pass and flips whole-day slack across day
    boundaries on a progressed schedule with ragged actual times (ADR-0117). When the calendar
    carries real intraday segments, count the intraday term through them; otherwise defer to the
    legacy contiguous conversion so nothing else changes.
    """
    if not calendar.day_segments or target < project_start:
        return datetime_to_offset(project_start, target, calendar)
    # sources write a cosmetic -1-second day boundary (16:59:59.99 = 17:00); round to the minute
    target = (target + dt.timedelta(seconds=30)).replace(second=0, microsecond=0)
    whole_days = _count_working_days(
        calendar, project_start.date(), target.date()
    ) + calendar.extra_working_days_in(project_start.date(), target.date())
    base = whole_days * calendar.working_minutes_per_day
    if not calendar.is_worked(target.date()):
        return base
    return base + calendar.intraday_worked_minutes(target.hour * 60 + target.minute)


#: §6.C default day-thresholds the user may override at upload (`PARITY-INPUTS.md`).
#: PROVENANCE (audit F-14; ADR-0153 sweep + ADR-0154 re-sweep against the delivered NASA
#: Schedule Management Handbook Rev 2, 2024-03-15): the primary/secondary/tertiary PATH-TIER
#: PRACTICE is NASA-sourced — SMH Rev 2 p.118 ("common practice to track the primary, secondary,
#: and tertiary critical paths, at a minimum") and p.123/Fig. 6-12 p.183; PPC Handbook
#: NASA/SP-2016-3424 p.125 + §3.4.3.2D p.151; SOPI 6.0 p.37; SRB SP-20230001306. The DAY VALUES
#: are DELIBERATELY project-defined per the SMH itself — Rev 2 p.118: near-critical paths are
#: isolated by "some minimum threshold value of total float" set "by the P/p management" — so
#: operator-overridable defaults are the handbook-conformant design, not a gap. Defaults: 10 d
#: aligns the secondary band with the PPC Fig. 3.4-3 health screen ("Tasks Less than or equal
#: to 10 days Total Slack", p.138); 20 d is this tool's tertiary convention.
DEFAULT_SECONDARY_MAX_DAYS = 10
DEFAULT_TERTIARY_MAX_DAYS = 20


class PathDirection(StrEnum):
    """Which way the trace runs from the focus task (SSI Directional Path Tool semantics)."""

    PREDECESSORS = "predecessors"  # what DRIVES the focus (default — the classic driving path)
    SUCCESSORS = "successors"  # what the focus DRIVES (the forward ripple)
    BOTH = "both"  # union of the two traces (the focus counted once, slack 0)


class PathTier(StrEnum):
    """Driving-slack magnitude tier relative to the focus task (user-configurable bands).

    Tiers classify on SSI's axis — **whole working days** (slack floored to days): real
    schedules carry minutes of time-of-day raggedness in their stored dates, and a chain
    SSI shows at "0 days" of driving slack must read DRIVING here too, not fall out over
    a 30-minute offset (the operator's 4-vs-66 driving-task discrepancy)."""

    DRIVING = "DRIVING"  # slack < 1 working day (displays as 0 days — the driving path)
    SECONDARY = "SECONDARY"  # 0 < whole days <= secondary_max_days
    TERTIARY = "TERTIARY"  # secondary_max_days < whole days <= tertiary_max_days
    BEYOND = "BEYOND"  # whole days > tertiary_max_days


@dataclass(frozen=True)
class DrivingSlackResult:
    """One driving activity's slack to the focus task."""

    unique_id: int
    driving_slack_minutes: int
    driving_slack_days: Decimal
    on_driving_path: bool  # < 1 whole working day of slack (SSI's "0 days")
    tier: PathTier


def date_basis(
    schedule: Schedule, cpm_result: CPMResult | None
) -> tuple[dict[int, int], dict[int, int]]:
    """Per-task (early_start, early_finish) offsets from the as-scheduled stored dates,
    falling back to the CPM forward pass for any task missing them.

    This is the axis the slack math runs on — and the axis the Path Analysis page must
    DISPLAY: on real progressed files the pure CPM packs completed work at the project
    start (logic alone doesn't reproduce actuals), so grid dates and Gantt bars drawn
    from CPM timings put finished tasks far from where the file says they ran."""
    cal = schedule.calendar
    start = schedule.project_start
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    result = cpm_result
    for task in schedule.tasks:
        if (
            task.is_summary or not task.is_active
        ):  # inactive tasks are out of the network (ADR-0128)
            continue
        if task.start is not None and task.finish is not None:
            early_start[task.unique_id] = _stored_offset(start, task.start, cal)
            early_finish[task.unique_id] = _stored_offset(start, task.finish, cal)
        else:
            if result is None:
                result = compute_cpm(schedule)
            timing = result.timing(task.unique_id)
            early_start[task.unique_id] = timing.early_start
            early_finish[task.unique_id] = timing.early_finish
    return early_start, early_finish


def _classify(
    slack_minutes: int, secondary_max_days: int, tertiary_max_days: int, minutes_per_day: int
) -> PathTier:
    """Tier a slack against the user's day bands on SSI's whole-working-day axis."""
    whole_days = _whole_days(slack_minutes, minutes_per_day)
    if whole_days <= 0:
        return PathTier.DRIVING
    if whole_days <= secondary_max_days:
        return PathTier.SECONDARY
    if whole_days <= tertiary_max_days:
        return PathTier.TERTIARY
    return PathTier.BEYOND


def _whole_days(slack_minutes: int, minutes_per_day: int) -> int:
    """Slack in whole working days, floored — the day-granular axis SSI displays.

    Sub-day slack (time-of-day raggedness in real stored dates) reads 0 days; the curated
    goldens' slacks are exact day multiples, so their values are unchanged (parity-safe).
    """
    return slack_minutes // minutes_per_day


def strip_constraints(schedule: Schedule) -> Schedule:
    """A copy of ``schedule`` with every task constraint removed (ASAP, no date).

    Powers the SSI-style "Ignore constraints" trace option: the CPM recomputed on this copy
    shows the pure-logic network with no date pins. The original schedule is never mutated."""
    from schedule_forensics.model.task import ConstraintType

    tasks = tuple(
        t.model_copy(update={"constraint_type": ConstraintType.ASAP, "constraint_date": None})
        if t.constraint_type is not ConstraintType.ASAP or t.constraint_date is not None
        else t
        for t in schedule.tasks
    )
    return schedule.model_copy(update={"tasks": tasks})


def compute_driving_slack(
    schedule: Schedule,
    target_uid: int,
    *,
    secondary_max_days: int = DEFAULT_SECONDARY_MAX_DAYS,
    tertiary_max_days: int = DEFAULT_TERTIARY_MAX_DAYS,
    cpm_result: CPMResult | None = None,
    direction: PathDirection = PathDirection.PREDECESSORS,
    ignore_constraints: bool = False,
    ignore_leveling_delay: bool = False,
) -> dict[int, DrivingSlackResult]:
    """Driving slack between ``target_uid`` and its trace, in the chosen ``direction``.

    PREDECESSORS (default) covers the focus and every task that can drive it — the classic
    driving path. SUCCESSORS covers every task the focus can drive, with the SAME slack
    semantics measured along the forward links (the propagation is symmetric: each task's
    slack is the minimum link free-float + accumulated slack back to the focus). BOTH is the
    union of the two traces. Tasks with no logic path to/from the focus are not included.
    Raises ``KeyError`` if ``target_uid`` is not a scheduled task, or ``ValueError`` on a
    cycle in the trace.

    ``ignore_constraints`` re-traces on a constraint-stripped copy (pure logic, no date pins);
    ``ignore_leveling_delay`` traces on the RECOMPUTED CPM dates instead of the stored ones —
    the recomputed network contains no resource-leveling delays (SSI: "pretend that all
    activities have a 0 day leveling delay"), so both options measure the un-pinned logic.
    Either option implies pure-CPM date arithmetic; the default trace keeps honoring the
    source tool's stored dates (the parity-validated behavior).
    """
    if ignore_constraints:
        stripped = strip_constraints(schedule)
        inner = compute_driving_slack(
            stripped,
            target_uid,
            secondary_max_days=secondary_max_days,
            tertiary_max_days=tertiary_max_days,
            cpm_result=None,  # the stripped network needs its own CPM
            direction=direction,
            ignore_leveling_delay=True,  # stored dates carry the pins — must use pure CPM
        )
        return inner
    if direction is PathDirection.BOTH:
        back = compute_driving_slack(
            schedule,
            target_uid,
            secondary_max_days=secondary_max_days,
            tertiary_max_days=tertiary_max_days,
            cpm_result=cpm_result,
            direction=PathDirection.PREDECESSORS,
            ignore_leveling_delay=ignore_leveling_delay,
        )
        fwd = compute_driving_slack(
            schedule,
            target_uid,
            secondary_max_days=secondary_max_days,
            tertiary_max_days=tertiary_max_days,
            cpm_result=cpm_result,
            direction=PathDirection.SUCCESSORS,
            ignore_leveling_delay=ignore_leveling_delay,
        )
        return {**fwd, **back}  # focus appears once (slack 0 on both sides)

    forward = direction is PathDirection.SUCCESSORS
    related = (
        descendants_of(schedule, target_uid) if forward else ancestors_of(schedule, target_uid)
    )
    trace = related | {target_uid}
    project_cal = schedule.calendar
    per_day = project_cal.working_minutes_per_day
    ps = schedule.project_start
    tasks_by_id = schedule.tasks_by_id
    cal_by_uid = {c.uid: c for c in schedule.calendars}

    def cal_for(uid: int) -> Calendar:
        cuid = tasks_by_id[uid].calendar_uid
        return project_cal if cuid is None else cal_by_uid.get(cuid, project_cal)

    # Project-calendar offsets (lunch-/working-day-aware) with a CPM fallback for tasks the
    # source never dated — these feed links on the project calendar and any undated task.
    early_start, early_finish = date_basis(schedule, cpm_result)

    def endpoint(uid: int, *, finish: bool, cal: Calendar) -> int:
        """Offset of a task's start/finish on ``cal``: the stored datetime measured on that
        calendar when present (so a non-project successor calendar is honored), else the
        project-calendar offset from ``date_basis`` (the CPM fallback for undated tasks).
        In ``ignore_leveling_delay`` mode the stored dates are skipped entirely — the trace
        runs on the recomputed pure-logic CPM offsets (no leveling delay, no pins)."""
        if not ignore_leveling_delay:
            when = tasks_by_id[uid].finish if finish else tasks_by_id[uid].start
            if when is not None:
                return _stored_offset(ps, when, cal)
        return early_finish[uid] if finish else early_start[uid]

    successors: dict[int, list[tuple[int, RelationshipType, int]]] = {uid: [] for uid in trace}
    for link in schedule.relationships:
        if link.predecessor_id in trace and link.successor_id in trace:
            successors[link.predecessor_id].append((link.successor_id, link.type, link.lag_minutes))

    # SSI total slack along the driving direction = min over successor links of
    # (the link's free float + the successor's slack). Each link's free float is counted on the
    # SUCCESSOR's own calendar, so on a multi-calendar file a predecessor's slack to the focus is
    # measured in the successor's working days — reproducing the SSI MS Project add-on exactly
    # (ADR-0118: leveled Large Test File, focus 152, 783/783; the driving path stays 61/61).
    # For a single-calendar schedule every link uses the project calendar and this is identical
    # to the late-finish backward pass (raw spans, no snap — ADR-0116), so the curated goldens
    # are unchanged. The Path page still DISPLAYS the true stored dates (date_basis unchanged).
    predecessors: dict[int, list[tuple[int, RelationshipType, int]]] = {uid: [] for uid in trace}
    for link in schedule.relationships:
        if link.predecessor_id in trace and link.successor_id in trace:
            predecessors[link.successor_id].append(
                (link.predecessor_id, link.type, link.lag_minutes)
            )

    order = topo_order(schedule, trace)
    slack_minutes: dict[int, int] = {}
    # SUCCESSORS: propagate FORWARD from the focus — a descendant's slack is the minimum over
    # its in-trace predecessor links of (link free float - lag + the predecessor's slack); the
    # same link-gap arithmetic as the backward pass, mirrored (endpoint/calendar rules unchanged).
    walk = order if forward else tuple(reversed(order))
    for uid in walk:
        if uid == target_uid:
            slack_minutes[uid] = 0
            continue
        best: int | None = None
        links = (
            [(p, rel, lag, p, uid) for p, rel, lag in predecessors[uid]]
            if forward
            else [(succ, rel, lag, uid, succ) for succ, rel, lag in successors[uid]]
        )
        for other, rel, lag, pred_uid, succ_uid in links:
            cal = cal_for(succ_uid)
            if rel is RelationshipType.FS:  # successor start - predecessor finish
                free = endpoint(succ_uid, finish=False, cal=cal) - endpoint(
                    pred_uid, finish=True, cal=cal
                )
            elif rel is RelationshipType.SS:  # successor start - predecessor start
                free = endpoint(succ_uid, finish=False, cal=cal) - endpoint(
                    pred_uid, finish=False, cal=cal
                )
            elif rel is RelationshipType.FF:  # successor finish - predecessor finish
                free = endpoint(succ_uid, finish=True, cal=cal) - endpoint(
                    pred_uid, finish=True, cal=cal
                )
            else:  # SF: successor finish - predecessor start
                free = endpoint(succ_uid, finish=True, cal=cal) - endpoint(
                    pred_uid, finish=False, cal=cal
                )
            candidate = free - lag + slack_minutes[other]
            if best is None or candidate < best:
                best = candidate
        slack_minutes[uid] = best if best is not None else 0

    results: dict[int, DrivingSlackResult] = {}
    for uid in trace:
        slack = slack_minutes[uid]
        results[uid] = DrivingSlackResult(
            unique_id=uid,
            driving_slack_minutes=slack,
            driving_slack_days=minutes_to_days(slack, minutes_per_day=per_day),
            # SSI's day axis: anything under one working day of slack IS the driving path
            on_driving_path=_whole_days(slack, per_day) <= 0,
            tier=_classify(slack, secondary_max_days, tertiary_max_days, per_day),
        )
    return results


def driving_path(schedule: Schedule, results: dict[int, DrivingSlackResult]) -> tuple[int, ...]:
    """The on-driving-path UniqueIDs (under one whole day of slack), topologically ordered."""
    on_path = [uid for uid, r in results.items() if r.on_driving_path]
    return topo_order(schedule, on_path)
