"""Critical Path Method engine — forward + backward pass (trust-root, Law 2: fidelity).

The internal time axis is **integer working minutes**, measured as an offset from
``Schedule.project_start``. An integer working-minute axis makes the arithmetic exact
and hand-verifiable, and removes the end-of-day / start-of-next-day boundary class of
bugs by construction (no binary-float drift — ADR-0005 determinism).

Scope of this engine (documented, not silently limited — Law 2):

* **Per-task calendars honored.** A task whose calendar's working pattern MATERIALLY
  differs from the project calendar (resolved via ``Schedule.calendars``), and every
  elapsed ("eday") duration — semantically a 24/7 calendar — consumes its duration in
  wall-clock arithmetic on its OWN calendar; its total/free float are measured in that
  calendar's working minutes (matching MS Project's stored Total Slack; display still
  divides by the project's minutes-per-day, as MS Project does). The canonical axis
  stays integer working minutes on the project calendar; the true wall instants ride on
  ``TaskTiming.*_wall`` because the axis cannot represent a date inside a project-
  calendar void. Cross-calendar link **lag** is applied on the PROJECT axis (documented
  approximation — both oracle files carry only zero lags; MS Project's own lag calendar
  on cross-calendar links is unpinned until an oracle exists).
* **Link types:** all four (FS / SS / FF / SF) with lag/lead, in working minutes.
* **Date constraints honored** (MS Project "honor constraint dates" mode):
  ``SNET`` / ``FNET`` are forward floors; ``SNLT`` / ``FNLT`` are backward caps;
  ``MSO`` / ``MFO`` **pin** the start / finish (forward pin + matching backward cap),
  and a pin VIOLATED by logic (predecessors push past the constraint) reports the
  violation as negative float on the pinned task itself — MS Project's own stored
  Total Slack semantics under its "honor constraint dates" mode, which this engine
  models unconditionally (an MSPDI ``HonorConstraints=0`` project is out of scope);
  a task ``deadline`` is a backward cap that can drive negative float.
* **Stored dates honored where logic does not bind** (ADR-0034): an UNSTARTED
  manually-scheduled task pins at its stored start (MS Project keeps it there), and an
  unstarted auto task with no predecessors floors at its stored start (a pure forward
  pass would pack every unlinked task to the project start — wrong for real
  sparse-logic files). The affected UniqueIDs are reported on
  :attr:`CPMResult.date_driven` and surfaced as a cited finding ("dates not supported
  by logic") — honored, never silently rescheduled.
* **A recorded progress-override reschedule is honored** (ADR-0309): this engine is
  pure-logic EXCEPT that an in-progress task whose source stores ``resume > stop`` has
  its remaining work floored at ``offset(resume) + remaining`` — MS Project's own
  recorded decision to move remaining work off the actual work, read rather than
  re-derived. It is therefore **conditionally progress-aware**: a file that records no
  reschedule (``resume == stop``, or either absent — every fixture without progress) is
  scheduled by logic alone and is byte-identical to the pre-ADR-0309 engine. Floored
  UniqueIDs join :attr:`CPMResult.date_driven`, the same disclosure ADR-0034 uses.
* **A recorded ACTUAL START is a floor** (ADR-0391): work that has begun cannot begin
  earlier than it did, so a started task's early start is
  ``max(logic_es, offset(actual_start))``. This closes the ADR-0108 understatement —
  a pure forward pass re-packs a late-started task at its logic start and brings the
  whole successor chain, including the project finish, back with it (measured on
  TP4 v5: 21 calendar days early; Acumen Fuse independently reports the later date).
  Like the two rules above it is a stored-date READ, not the data-date *inference*
  ADR-0108 twice reverted, and it needs no ``Stop``/``Resume``. Being a floor it can
  only push work LATER, never earlier, so a file with no actuals — or whose actuals
  agree with logic — is byte-identical to the pre-ADR-0391 engine. Floored UniqueIDs
  are reported on :attr:`CPMResult.actual_start_driven`, deliberately SEPARATE from
  ``date_driven`` (a recorded actual is evidence, not an unsupported date).
  **Still not anchored:** a completed task's actual FINISH. Its start is now honored,
  but its finish is still ``start + duration`` rather than the stored ``actual_finish``,
  so a completed activity that ran longer or shorter than planned still computes a
  finish that differs from the record — which is why consumers needing real per-task
  dates continue to read the stored ones first (``driving_slack.py``).
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
from functools import lru_cache

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
    #: Wall-clock instants for a task executing on its OWN calendar (a task calendar whose
    #: pattern differs from the project calendar, or an elapsed duration). ``None`` for
    #: project-calendar tasks (their integer offsets are exact). These carry dates the
    #: project axis cannot represent — e.g. a 24-hour-calendar finish inside a
    #: project-calendar void — and ``total_float``/``free_float`` for such tasks are
    #: working minutes of the TASK'S calendar between these instants (MS Project's own
    #: stored-slack basis; display still divides by the project's minutes-per-day).
    early_start_wall: dt.datetime | None = None
    early_finish_wall: dt.datetime | None = None
    late_start_wall: dt.datetime | None = None
    late_finish_wall: dt.datetime | None = None


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
    #: UniqueIDs whose early start was raised to their RECORDED ``actual_start``, because pure
    #: logic would otherwise schedule work before it demonstrably began (ADR-0391). Deliberately
    #: NOT merged into :attr:`date_driven`: that list drives a "dates not supported by logic"
    #: concern, and a recorded actual is evidence of what happened, not an unsupported date.
    #: This is the disclosure surface for "the schedule is anchored to reported progress".
    actual_start_driven: tuple[int, ...] = ()
    #: The true wall-clock instant of the network finish when an off-calendar task's
    #: finish is not exactly representable on the project axis (e.g. an elapsed task
    #: ending on a weekend). ``None`` when every task follows the project calendar —
    #: ``offset_to_datetime(project_finish)`` is then exact.
    project_finish_wall: dt.datetime | None = None

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
    (a Saturday-morning finish reads as Friday end-of-day for successors).

    The start instant is materialised with :func:`offset_to_start_datetime`: this is the one
    place the day-boundary spelling is *arithmetic* rather than display (ADR-0348). Reading a
    boundary start as the previous day's 16:00 rather than this day's 08:00 shifts the clock
    origin by the whole non-working gap, so every elapsed duration that is not a whole multiple
    of 1440 lands short — by up to a full working day."""
    start_dt = offset_to_start_datetime(project_start, max(start_offset, 0), calendar)
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


def offset_to_start_datetime(start: dt.datetime, minutes: int, calendar: Calendar) -> dt.datetime:
    """Resolve an offset that denotes the **beginning** of work (ADR-0348).

    The working axis is contiguous, so a day-boundary offset names one instant that has two
    equally valid wall-clock spellings: the **end** of working day ``k-1`` and the **start** of
    working day ``k``. :func:`offset_to_datetime` always chooses the first (``remainder == 0``
    takes the ``intraday = per_day`` branch), which is right for a finish and one working day
    early for a start — a 1-day task then draws a 2-day bar, and its start reads as the previous
    working day (the previous *Friday* across a weekend).

    This resolves the same instant the other way for offsets that carry a start role. Away from
    the boundary the two agree exactly, so it delegates; only the ``remainder == 0`` case differs.
    ``offset_to_datetime`` and the offsets themselves are deliberately untouched — the offset and
    its inverse are correct, and every finish-role site depends on the end-of-day spelling
    (ADR-0310: CC-01 is a *rendering* problem, not an arithmetic one).
    """
    if minutes < 0:
        raise ValueError("offset_to_start_datetime: minutes must be >= 0")
    per_day = calendar.working_minutes_per_day
    quotient, remainder = divmod(minutes, per_day)
    if remainder:
        return offset_to_datetime(start, minutes, calendar)
    day = start
    while day.date().weekday() not in calendar.work_weekdays or day.date() in calendar.holidays:
        day = _next_working_day(day, calendar)
    target_date = _advance_working_days(day.date(), quotient, calendar)
    return day + dt.timedelta(days=(target_date - day.date()).days)


def span_start_datetime(
    start: dt.datetime, early_start: int, early_finish: int, calendar: Calendar
) -> dt.datetime:
    """The wall-clock start of a task's span, for display beside its finish (ADR-0348).

    A task that consumes working time begins at the *start* spelling of its early start, so
    a one-day task draws a one-day bar on the day it is worked. A **zero-duration instant**
    (milestone) has no beginning distinct from the instant itself, and MS Project spells it
    with the end-of-day form — measured on the committed corpus, that form reproduces MSP's
    own stored date while the start form reads a working day late. Using the start form here
    would also render a milestone's start one working day *after* its finish.
    """
    if early_finish > early_start:
        return offset_to_start_datetime(start, max(early_start, 0), calendar)
    return offset_to_datetime(start, max(early_start, 0), calendar)


# --- per-task execution calendars (wall-clock arithmetic at calendar boundaries) ----------
#
# The canonical schedule axis stays INTEGER WORKING MINUTES on the project calendar. A task
# whose own working pattern differs (a "24 Hours" task calendar, or an elapsed "eday"
# duration — semantically a 24/7 calendar) consumes its duration in WALL-CLOCK arithmetic on
# its own calendar, and its float is measured in its own calendar's minutes (matching MS
# Project's stored Total Slack exactly; MSP then *displays* those minutes over the project's
# minutes-per-day). The project axis keeps every cross-task comparison exact; the wall
# instants carry the truth the axis cannot represent (a finish inside a project-calendar
# void). All helpers below are used ONLY for such off-calendar tasks — a schedule whose
# tasks all follow the project calendar never executes them (fast path unchanged).

#: The execution calendar of an ELAPSED duration: every minute of every day is working
#: time (MS Project "eday" semantics — calendars ignored).
_ELAPSED_CALENDAR = Calendar(
    uid=-1,
    name="Elapsed (24/7)",
    working_minutes_per_day=1440,
    work_weekdays=(0, 1, 2, 3, 4, 5, 6),
)


def _execution_calendars(schedule: Schedule, tasks: list[Task]) -> dict[int, Calendar]:
    """UniqueID → the calendar the task's duration actually consumes, for every task whose
    execution pattern MATERIALLY differs from the project calendar. Elapsed durations map to
    the 24/7 calendar; a ``calendar_uid`` resolving to a same-pattern calendar (or to nothing)
    stays on the project-calendar integer fast path."""
    project_key = _working_pattern_key(schedule.calendar)
    by_uid = {c.uid: c for c in schedule.calendars}
    out: dict[int, Calendar] = {}
    for t in tasks:
        if t.duration_is_elapsed and t.duration_minutes > 0:
            out[t.unique_id] = _ELAPSED_CALENDAR
            continue
        if t.calendar_uid is None:
            continue
        cal = by_uid.get(t.calendar_uid)
        if cal is not None and _working_pattern_key(cal) != project_key:
            out[t.unique_id] = cal
    return out


def execution_calendar_of(schedule: Schedule, task: Task) -> Calendar | None:
    """The calendar ``task``'s duration actually consumes when it differs from the project
    calendar (the 24/7 calendar for an elapsed duration), else ``None`` — the single public
    lookup consumers (e.g. the DCMA-12 delay injection) use to work on the task's own axis."""
    return _execution_calendars(schedule, [task]).get(task.unique_id)


def _day_segments_of(cal: Calendar, day_start_tod: int) -> tuple[tuple[int, int], ...]:
    """The calendar's intraday working blocks as minutes-from-midnight. Falls back to one
    contiguous block anchored at ``day_start_tod`` (the project start's time of day — the
    engine's existing single-block convention) when the source declared no segments; a
    24-hour day is the whole day."""
    if cal.day_segments:
        return cal.day_segments
    mpd = cal.working_minutes_per_day
    if mpd >= 1440:
        return ((0, 1440),)
    start = day_start_tod if day_start_tod + mpd <= 1440 else 0
    return ((start, start + mpd),)


def _worked_before(segments: tuple[tuple[int, int], ...], tod: int) -> int:
    """Working minutes of the day consumed strictly before minute-of-day ``tod``."""
    worked = 0
    for seg_start, seg_end in segments:
        if tod >= seg_end:
            worked += seg_end - seg_start
        elif tod > seg_start:
            worked += tod - seg_start
    return worked


def _tod_at_worked(segments: tuple[tuple[int, int], ...], k: int) -> int:
    """Minute-of-day after consuming ``k`` working minutes (0 → first block's start;
    a block-exact ``k`` → that block's end)."""
    for seg_start, seg_end in segments:
        span = seg_end - seg_start
        if k <= span:
            return seg_start + k
        k -= span
    return segments[-1][1]


@lru_cache(maxsize=64)
def _worked_day_sets(
    cal: Calendar,
) -> tuple[frozenset[dt.date], frozenset[dt.date], frozenset[int]]:
    """``(holidays, extra_working_days, work_weekdays)`` as FROZENSETS, memoized per calendar.

    The model stores these as tuples, so the day-stepping wall helpers below were doing an
    O(len(holidays)) scan per day stepped — measured as the dominant cost of the ADR-0322
    off-calendar paths inside the SRA Monte-Carlo (139 off-calendar tasks x ~2000 solves x
    day-walks over 100+ holidays; CI's coverage tracing multiplied it into hours). Purely a
    lookup-structure change: same members, same answers, O(1) membership. Safe to cache —
    ``Calendar`` is a frozen (hashable) model and the cache is small and bounded."""
    return frozenset(cal.holidays), frozenset(cal.working_days), frozenset(cal.work_weekdays)


def _is_worked_day(cal: Calendar, day: dt.date) -> bool:
    """Task-calendar working-day test, honoring extra ``working_days`` exceptions
    (set-based twin of :meth:`Calendar.is_worked` — identical answers, O(1) membership)."""
    holidays, extra_working, weekdays = _worked_day_sets(cal)
    return day in extra_working or (day.weekday() in weekdays and day not in holidays)


def _retreat_working_days(start_day: dt.date, k: int, calendar: Calendar) -> dt.date:
    """The working day ``k`` working-days BEFORE ``start_day`` — the backward mirror of
    :func:`_advance_working_days` (same full-weeks jump + short remainder + holiday
    make-up over the traversed span, which is ``[nxt, cur)`` going backward)."""
    if k <= 0:
        return start_day
    workdays = set(calendar.work_weekdays)
    wdpw = len(workdays)
    holidays = calendar.holidays
    cur = start_day
    needed = k
    while needed > 0:
        full_weeks, remainder = divmod(needed, wdpw)
        nxt = cur - dt.timedelta(days=full_weeks * 7)
        steps = remainder
        while steps > 0:
            nxt -= dt.timedelta(days=1)
            if nxt.weekday() in workdays:
                steps -= 1
        needed = sum(1 for h in holidays if nxt <= h < cur and h.weekday() in workdays)
        cur = nxt
    return cur


def _shift_worked_days(cal: Calendar, day: dt.date, n: int) -> dt.date:
    """The ``n``-th worked day after (``n>0``) / before (``n<0``) ``day`` on ``cal``,
    counting ``day`` itself as position 0.

    A calendar WITHOUT ``working_days`` exceptions (the overwhelmingly common case) uses
    the same full-weeks + holiday-adjust arithmetic as the long-proven
    :func:`_advance_working_days` — O(weeks + holidays), never O(days), because the
    off-calendar slack spans this walks can be months long (profiled: the day-stepping
    version dominated the SRA Monte-Carlo). The week-jump counts weekdays over the
    half-open traversed span, so a non-working start day is handled exactly. A calendar
    WITH extra working days keeps the exhaustive per-day step (extras break the weekly
    period; they are rare and few)."""
    holidays, extra_working, weekdays = _worked_day_sets(cal)
    if not extra_working:
        if n == 0:
            return day
        if n > 0:
            return _advance_working_days(day, n, cal)
        return _retreat_working_days(day, -n, cal)
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    cur = day
    while remaining > 0:
        cur += dt.timedelta(days=step)
        if cur in extra_working or (cur.weekday() in weekdays and cur not in holidays):
            remaining -= 1
    return cur


def _at_minute(day: dt.date, minute_of_day: int) -> dt.datetime:
    """Midnight of ``day`` plus ``minute_of_day`` — safe for minute 1440 (a 24-hour day's
    end instant is the NEXT day's midnight; ``dt.datetime(..., hour=24)`` would raise)."""
    return dt.datetime(day.year, day.month, day.day) + dt.timedelta(minutes=minute_of_day)


def _offset_to_wall(start: dt.datetime, offset: int, cal: Calendar, *, role: str) -> dt.datetime:
    """The wall-clock instant of a project-axis working-minute ``offset``, segment-aware.

    ``role="finish"``: the instant where minute ``offset`` ENDS — an exact multiple of the
    working day lands at the END of the previous working day's last block (offset 0 → the
    project start instant). ``role="start"``: where minute ``offset`` BEGINS — an exact
    multiple lands at the NEXT working day's first block start (so "end of 8/31" and
    "start of 10/1" — one grid point across a void — resolve by role)."""
    day_start_tod = start.hour * 60 + start.minute
    segments = _day_segments_of(cal, day_start_tod)
    mpd = cal.working_minutes_per_day
    base = start.date()
    if not cal.is_working_day(base):  # anchored starts are working days; defensive
        base = _shift_worked_days(cal, base, 1)
    quotient, remainder = divmod(offset, mpd)  # floor division: negative offsets go backward
    if role == "finish" and offset != 0 and remainder == 0:
        # an exact multiple ENDS at the previous working day's last block (offset 0 stays
        # the project-start instant); same rule on the negative side — "-1 day, finish
        # role" is the end of the working day before that, not its start
        quotient, remainder = quotient - 1, mpd
    day = _advance_working_days(base, quotient, cal) if quotient >= 0 else base
    if quotient < 0:
        cur, back = base, -quotient
        while back > 0:
            cur -= dt.timedelta(days=1)
            if cal.is_working_day(cur):
                back -= 1
        day = cur
    tod = _tod_at_worked(segments, remainder)
    return _at_minute(day, tod)


def _wall_to_offset(start: dt.datetime, wall: dt.datetime, cal: Calendar) -> int:
    """Project-axis working-minute offset of a wall instant — the CONTIGUOUS canonical
    ruler, i.e. exactly :func:`datetime_to_offset`.

    Deliberately asymmetric with :func:`_offset_to_wall` (the review-confirmed two-ruler
    rule): int→wall EXPANSION is day-segment-aware so an off-calendar task anchors at MS
    Project's true instant (an end-of-day offset expands to 17:00, not 16:00), but every
    wall→int PROJECTION must use the same contiguous intraday convention as the rest of
    the axis — constraint dates, stored pins, and the rendering path all measure
    ``clamp(tod - start_tod)``, and projecting with a different (segment-aware) ruler made
    the same instant carry two different offsets: a successor rendered BEFORE its
    predecessor's finish, and a same-instant SNET out-bound the link inside one ``max()``.
    The cost is bounded and conservative: a mid-day wall instant on a gapped calendar
    projects up to the gap width LATER than its true worked minutes (never earlier), one
    boundary per off-calendar link; the true instants still ride ``TaskTiming.*_wall``."""
    return datetime_to_offset(start, wall, cal)


def _is_24x7(cal: Calendar) -> bool:
    return cal.working_minutes_per_day >= 1440 and len(cal.work_weekdays) == 7 and not cal.holidays


def _advance_wall(
    wall: dt.datetime, minutes: int, cal: Calendar, day_start_tod: int
) -> dt.datetime:
    """Consume ``minutes >= 0`` of working time on ``cal`` forward from ``wall``."""
    if minutes <= 0:
        return wall
    if _is_24x7(cal):
        return wall + dt.timedelta(minutes=minutes)
    segments = _day_segments_of(cal, day_start_tod)
    mpd = cal.working_minutes_per_day
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    remaining = minutes
    if _is_worked_day(cal, day):
        available_today = mpd - _worked_before(segments, tod)
        if remaining <= available_today:
            new_tod = _tod_at_worked(segments, _worked_before(segments, tod) + remaining)
            return _at_minute(day, new_tod)
        remaining -= available_today
    quotient, part = divmod(remaining, mpd)
    if part == 0:
        quotient, part = quotient - 1, mpd
    day = _shift_worked_days(cal, day, quotient + 1)
    tod = _tod_at_worked(segments, part)
    return _at_minute(day, tod)


def _retreat_wall(
    wall: dt.datetime, minutes: int, cal: Calendar, day_start_tod: int
) -> dt.datetime:
    """Consume ``minutes >= 0`` of working time on ``cal`` backward from ``wall``."""
    if minutes <= 0:
        return wall
    if _is_24x7(cal):
        return wall - dt.timedelta(minutes=minutes)
    segments = _day_segments_of(cal, day_start_tod)
    mpd = cal.working_minutes_per_day
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    remaining = minutes
    if _is_worked_day(cal, day):
        available_today = _worked_before(segments, tod)
        if remaining <= available_today:
            new_tod = _tod_at_worked(segments, available_today - remaining)
            return _at_minute(day, new_tod)
        remaining -= available_today
    quotient, part = divmod(remaining, mpd)
    if part == 0:
        quotient, part = quotient - 1, mpd
    day = _shift_worked_days(cal, day, -(quotient + 1))
    tod = _tod_at_worked(segments, mpd - part)
    return _at_minute(day, tod)


def _wall_minutes_between(a: dt.datetime, b: dt.datetime, cal: Calendar, day_start_tod: int) -> int:
    """SIGNED working minutes on ``cal`` from instant ``a`` to instant ``b`` (negative when
    ``b`` precedes ``a``). This is the float axis for an off-calendar task — MS Project
    measures a task's slack in its own calendar's working time."""
    if b < a:
        return -_wall_minutes_between(b, a, cal, day_start_tod)
    if _is_24x7(cal):
        return int((b - a).total_seconds() // 60)
    segments = _day_segments_of(cal, day_start_tod)
    mpd = cal.working_minutes_per_day
    a_intraday = (
        _worked_before(segments, a.hour * 60 + a.minute) if _is_worked_day(cal, a.date()) else 0
    )
    b_intraday = (
        _worked_before(segments, b.hour * 60 + b.minute) if _is_worked_day(cal, b.date()) else 0
    )
    if a.date() == b.date():
        return b_intraday - a_intraday
    # Full worked days STRICTLY between the two dates: the proven full-weeks arithmetic
    # (O(weeks + holidays), never a per-day walk — these spans can be months of slack)
    # plus the calendar's extra working days a weekday-minus-holiday count misses.
    lo, hi = a.date() + dt.timedelta(days=1), b.date()
    full_days_between = _count_working_days(cal, lo, hi) if lo < hi else 0
    holidays, extra_working, weekdays = _worked_day_sets(cal)
    if extra_working:
        full_days_between += sum(
            1
            for d in extra_working
            if lo <= d < hi and (d.weekday() not in weekdays or d in holidays)
        )
    tail = mpd - a_intraday if _is_worked_day(cal, a.date()) else 0
    return tail + full_days_between * mpd + b_intraday


def _advance_wall_signed(
    wall: dt.datetime, minutes: int, cal: Calendar, day_start_tod: int
) -> dt.datetime:
    return (
        _advance_wall(wall, minutes, cal, day_start_tod)
        if minutes >= 0
        else _retreat_wall(wall, -minutes, cal, day_start_tod)
    )


def _snap_to_working(wall: dt.datetime, cal: Calendar, day_start_tod: int) -> dt.datetime:
    """The earliest working instant on ``cal`` at or after ``wall`` (a task cannot start
    inside its own calendar's non-working time)."""
    if _is_24x7(cal):
        return wall
    segments = _day_segments_of(cal, day_start_tod)
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    while True:
        if _is_worked_day(cal, day):
            for seg_start, seg_end in segments:
                if tod < seg_end:
                    new_tod = max(tod, seg_start)
                    return _at_minute(day, new_tod)
        day += dt.timedelta(days=1)
        tod = 0


def _working_pattern_key(cal: Calendar) -> tuple[object, ...]:
    """The fields that make a calendar's working pattern materially distinct — everything the
    date/float math consumes, and nothing cosmetic (``uid`` / ``name`` are identity, not pattern).
    Order-independent, so two calendars listing the same holidays in a different order compare
    equal (a purely re-ordered registry entry is not a real divergence)."""
    return (
        cal.working_minutes_per_day,
        tuple(sorted(cal.work_weekdays)),
        tuple(sorted(cal.holidays)),
        tuple(sorted(cal.working_days)),
        tuple(sorted(cal.day_segments)),
    )


def off_project_calendars(schedule: Schedule) -> tuple[Calendar, ...]:
    """Calendars carried by active, non-summary tasks whose working pattern MATERIALLY differs
    from the project calendar (ADR-0028's single-calendar model, superseded for the base pass).

    Historically a disclosure-only signal (the base CPM modelled one calendar). The base pass
    now HONORS these calendars — each listed calendar's tasks are scheduled in wall-clock
    arithmetic on their own calendar (see the module docstring) — so this listing now names
    the activities whose float axis is their own calendar's minutes, rather than flagging an
    approximation. The driving-slack / SSI path keeps its own per-calendar handling
    (ADR-0118); the two paths measure link float on different calendars by design (SSI parity
    counts a link's free float on the SUCCESSOR's calendar; the CPM measures a task's float
    on its OWN calendar, matching MS Project's stored slack).

    Deduplicated by ``uid`` and returned sorted by ``uid``. Fail-soft: a task whose ``calendar_uid``
    is absent from ``schedule.calendars`` cannot be compared and is skipped (never over-claims a
    divergence), and a task calendar whose pattern equals the project calendar is not reported.
    """
    project_key = _working_pattern_key(schedule.calendar)
    by_uid = {c.uid: c for c in schedule.calendars}
    out: dict[int, Calendar] = {}
    for task in schedule.tasks:
        if task.is_summary or not task.is_active or task.calendar_uid is None:
            continue
        cal = by_uid.get(task.calendar_uid)
        if cal is not None and _working_pattern_key(cal) != project_key:
            out.setdefault(cal.uid, cal)
    return tuple(out[uid] for uid in sorted(out))


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


def _actual_start_bounds(schedule: Schedule, tasks: list[Task]) -> dict[int, int]:
    """Early-START floors from a task's RECORDED ``actual_start`` (ADR-0391).

    The third member of the stored-date family, after :func:`_stored_date_bounds` (stored starts
    on *unstarted* tasks) and :func:`_resume_bounds` (a recorded reschedule of *remaining* work).
    This one honors the plainest fact a progressed file carries: **work that has begun cannot
    begin earlier than it did.** A pure forward pass ignores actuals, so a task that started three
    months late is re-packed at its logic early start and its whole successor chain — up to and
    including the project finish — comes back early. That is the ADR-0108 failure mode, and it
    understates the slip, the one direction a forensic delay tool must never be wrong in (Law 2).

    A **FLOOR, not a pin**: ``es = max(logic_es, offset(actual_start))``. It can only ever push a
    task LATER, never earlier, so it cannot manufacture a slip — a task whose logic start already
    sits at or after its actual start is byte-identical to the pre-ADR-0391 engine, and so is
    every schedule with no actuals at all. Out-of-sequence progress (work that began BEFORE its
    predecessors finished) keeps the logic start: the conservative reading, reporting the finish
    no earlier than the network supports.

    This is a stored-date READ, not the inference ADR-0108 twice reverted. Those attempts
    rescheduled every in-progress task's remaining work to the **data date**, which needs an
    ahead/behind judgement MS Project makes from internal state and does not export — so they
    moved finishes that were already correct. ``actual_start`` needs no judgement: it is a
    recorded instant, present in the file, and the engine simply stops scheduling work before it.
    Crucially it also needs no ``Stop``/``Resume``, which the synthetic battery cannot express.

    Applies to **started** tasks (``actual_start`` present) regardless of completion: a completed
    activity's start is a fact on the same footing. Offsets clamp at the project start (negative
    offsets are unrenderable) — the clamp :func:`_stored_date_bounds` already uses.
    """
    floor: dict[int, int] = {}
    for task in tasks:
        if task.actual_start is None:
            continue
        floor[task.unique_id] = max(
            datetime_to_offset(schedule.project_start, task.actual_start, schedule.calendar), 0
        )
    return floor


def _resume_bounds(
    schedule: Schedule, tasks: list[Task], duration_overrides: Mapping[int, int] | None
) -> dict[int, int]:
    """Early-FINISH floors for in-progress work MS Project has already rescheduled (ADR-0309).

    The sibling of :func:`_stored_date_bounds`, which honors stored dates on *unstarted* tasks.
    This honors them on *started* ones: MSPDI stores ``<Stop>`` (progress recorded through) and
    ``<Resume>`` (where the REMAINING duration restarts). When ``resume > stop`` MS Project has
    itself moved the remaining work off the actual work — the "progress override" reschedule — and
    the remaining duration runs from ``resume``, so the finish is
    ``offset(resume) + remaining_duration``. When ``resume == stop`` (the common case) remaining
    work is contiguous and nothing is floored, so a schedule with no rescheduled work is
    byte-identical to the pre-ADR-0309 engine.

    This is why ADR-0108's two reverted attempts failed: they floored EVERY in-progress task's
    remaining work at the data date, which over-corrects the tasks MS Project deliberately left
    alone (EVM1 UID 18 — 25% complete, ``resume == stop``, remaining work legitimately in the past)
    and so moved a finish that was already correct. The ahead/behind judgement ADR-0108 concluded
    "cannot be reverse-engineered safely from two data points" never had to be: MS Project records
    its own answer, and reading it is a stored-date read, not an inference (Law 2).

    A FLOOR, not a pin: logic may still push the finish later than ``resume`` (a predecessor that
    finishes after it), and the later of the two wins.

    The remaining term follows ``duration_overrides`` when one is supplied for the task, because
    **every** override producer in the codebase builds an incomplete task's override from its
    REMAINING duration (``sra._ml_minutes``, ``sra._three_point``, or 0 for a zeroed margin task) —
    so an override on an in-progress task *is* a remaining duration. Using the stored remaining
    instead would pin the finish at ``resume + stored_remaining`` regardless of the sampled value,
    which silently destroys the Monte-Carlo's upside variance on exactly the in-progress activities
    the SRA cares about (measured: it drove every one of 2000 iterations to finish on or before the
    deterministic date). The floor must breathe with the sample.
    """
    floor: dict[int, int] = {}
    ov = duration_overrides or {}
    for task in tasks:
        if task.resume is None or task.stop is None or task.resume <= task.stop:
            continue
        uid = task.unique_id
        remaining = ov.get(uid, task.remaining_duration_minutes)
        if remaining is None or remaining <= 0:
            continue  # nothing left to reschedule — an actual-only record, or zeroed margin
        off = max(datetime_to_offset(schedule.project_start, task.resume, schedule.calendar), 0)
        floor[uid] = off + remaining
    return floor


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
    actual_floor = _actual_start_bounds(schedule, tasks)
    resume_ef_floor = _resume_bounds(schedule, tasks, duration_overrides)
    # Tasks executing on their OWN calendar (a materially different task calendar, or an
    # elapsed duration == the 24/7 calendar): dates advance in wall-clock arithmetic on that
    # calendar; float is that calendar's working minutes. Everything else stays on the
    # integer project axis (byte-identical fast path).
    exec_cal = _execution_calendars(schedule, tasks)
    task_by_id: dict[int, Task] = {t.unique_id: t for t in tasks}
    ps, cal = schedule.project_start, schedule.calendar
    tod0 = ps.hour * 60 + ps.minute
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    es_wall: dict[int, dt.datetime] = {}
    ef_wall: dict[int, dt.datetime] = {}
    #: MSO/MFO pin-violation term (FIX: MS Project reports a violated pin as NEGATIVE slack —
    #: the amount logic pushes past the constraint), in the task's own float axis.
    pin_violation: dict[int, int] = {}
    date_driven: list[int] = []
    #: UIDs whose early start was raised to their RECORDED actual start (ADR-0391). Kept SEPARATE
    #: from ``date_driven``: that list feeds a "dates not supported by logic" CONCERN telling the
    #: analyst to tie the activity into the network, which would be a false signal about work
    #: that has demonstrably already started.
    actual_driven: list[int] = []

    def _pred_finish_wall(p: int) -> dt.datetime:
        if p in exec_cal:
            return ef_wall[p]
        return _offset_to_wall(ps, early_finish[p], cal, role="finish")

    def _pred_start_wall(p: int) -> dt.datetime:
        if p in exec_cal:
            return es_wall[p]
        return _offset_to_wall(ps, early_start[p], cal, role="start")

    for tid in order:
        dur_s = duration[tid]
        if tid in exec_cal:
            cal_t = exec_cal[tid]
            task = task_by_id[tid]
            # the pure logic+constraint early start, as a wall instant on the task's calendar
            cands: list[dt.datetime] = [ps]
            for p, rel, lag in preds[tid]:
                if rel is RelationshipType.FS:
                    drive = (
                        _pred_finish_wall(p)
                        if lag == 0
                        else _offset_to_wall(ps, early_finish[p] + lag, cal, role="finish")
                    )
                elif rel is RelationshipType.SS:
                    drive = (
                        _pred_start_wall(p)
                        if lag == 0
                        else _offset_to_wall(ps, early_start[p] + lag, cal, role="start")
                    )
                else:  # FF / SF bound the FINISH; retreat the duration on the task calendar
                    if rel is RelationshipType.FF:
                        fin = (
                            _pred_finish_wall(p)
                            if lag == 0
                            else _offset_to_wall(ps, early_finish[p] + lag, cal, role="finish")
                        )
                    else:
                        fin = (
                            _pred_start_wall(p)
                            if lag == 0
                            else _offset_to_wall(ps, early_start[p] + lag, cal, role="start")
                        )
                    drive = _retreat_wall(fin, dur_s, cal_t, tod0)
                cands.append(drive)
            if tid in es_floor:
                # date-constraint floor from the RAW date (exact even inside a project void)
                if task.constraint_type is ConstraintType.SNET and task.constraint_date:
                    cands.append(task.constraint_date)
                elif task.constraint_type is ConstraintType.FNET and task.constraint_date:
                    cands.append(_retreat_wall(task.constraint_date, dur_s, cal_t, tod0))
                else:
                    cands.append(_offset_to_wall(ps, es_floor[tid], cal, role="start"))
            logic_es_wall = _snap_to_working(max(cands), cal_t, tod0)
            if tid in es_pin and task.constraint_date is not None:
                if task.constraint_type is ConstraintType.MSO:
                    es_w = _snap_to_working(task.constraint_date, cal_t, tod0)
                else:  # MFO — pin the finish, derive the start
                    es_w = _retreat_wall(task.constraint_date, dur_s, cal_t, tod0)
                pin_violation[tid] = _wall_minutes_between(logic_es_wall, es_w, cal_t, tod0)
            elif tid in stored_pin and task.start is not None:
                es_w = _snap_to_working(max(task.start, ps), cal_t, tod0)
                if es_w != logic_es_wall:
                    date_driven.append(tid)
            elif tid in stored_floor and task.start is not None and task.start > logic_es_wall:
                es_w = _snap_to_working(task.start, cal_t, tod0)
                date_driven.append(tid)
            else:
                es_w = logic_es_wall
                # work that has begun cannot begin earlier than it did (ADR-0391) — on the
                # task's OWN calendar, from the raw stored instant
                if task.actual_start is not None:
                    started_wall = _snap_to_working(max(task.actual_start, ps), cal_t, tod0)
                    if started_wall > es_w:
                        es_w = started_wall
                        actual_driven.append(tid)
            ef_w = _advance_wall(es_w, dur_s, cal_t, tod0)
            # ADR-0309 resume floor, on the task's own calendar from the raw stored dates
            if task.resume is not None and task.stop is not None and task.resume > task.stop:
                ov = duration_overrides or {}
                remaining = ov.get(tid, task.remaining_duration_minutes)
                if remaining is not None and remaining > 0:
                    resumed = _advance_wall(max(task.resume, ps), remaining, cal_t, tod0)
                    if resumed > ef_w:
                        ef_w = resumed
                        date_driven.append(tid)
            es_wall[tid], ef_wall[tid] = es_w, ef_w
            early_start[tid] = _wall_to_offset(ps, es_w, cal)
            early_finish[tid] = _wall_to_offset(ps, ef_w, cal)
            continue
        bounds = [
            es_lower_bound(rel, early_start[p], early_finish[p], lag, dur_s)
            for p, rel, lag in preds[tid]
        ]
        if tid in es_floor:
            bounds.append(es_floor[tid])
        # the pure logic+constraint early start — computed even under a pin, so the
        # logic-vs-stored divergence the findings report is measurable
        logic_es = max([0, *bounds])
        if tid in es_pin:
            es = es_pin[tid]
            pin_violation[tid] = es - logic_es
        elif tid in stored_pin:
            es = stored_pin[tid]
            if es != logic_es:
                date_driven.append(tid)
        elif tid in stored_floor and stored_floor[tid] > logic_es:
            es = stored_floor[tid]
            date_driven.append(tid)
        else:
            es = logic_es
            # work that has begun cannot begin earlier than it did (ADR-0391)
            started_off = actual_floor.get(tid)
            if started_off is not None and started_off > es:
                es = started_off
                actual_driven.append(tid)
        early_start[tid] = es
        ef = es + dur_s
        # in-progress work MS Project itself rescheduled: its remaining duration runs from the
        # stored Resume, so the finish floors there (ADR-0309). Logic may still push it later.
        resume_ef = resume_ef_floor.get(tid)
        if resume_ef is not None and resume_ef > ef:
            ef = resume_ef
            date_driven.append(tid)
        early_finish[tid] = ef

    network_finish = max(early_finish.values(), default=0)
    backward_target = (
        required_finish_offset if required_finish_offset is not None else network_finish
    )
    # The backward target as a WALL INSTANT (needed only when off-calendar tasks exist): the
    # true latest finish instant. Monotonicity of the wall→offset projection means the
    # latest-wall task is among the max-offset tasks, so only those need their walls.
    target_wall: dt.datetime | None = None
    if exec_cal:
        if required_finish_offset is not None:
            target_wall = _offset_to_wall(ps, required_finish_offset, cal, role="finish")
        else:
            finish_cands = [t for t in task_ids if early_finish[t] == network_finish]
            target_wall = max(
                (
                    ef_wall[t]
                    if t in exec_cal
                    else _offset_to_wall(ps, early_finish[t], cal, role="finish")
                    for t in finish_cands
                ),
                default=_offset_to_wall(ps, network_finish, cal, role="finish"),
            )

    # ---- backward pass (LF capped at the backward target, and by SNLT/FNLT/MSO/MFO/deadline) ----
    late_finish: dict[int, int] = {}
    late_start: dict[int, int] = {}
    ls_wall: dict[int, dt.datetime] = {}
    lf_wall: dict[int, dt.datetime] = {}
    exec_slack: dict[int, int] = {}

    def _succ_ls_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_cal:
            return ls_wall[s]
        return _offset_to_wall(ps, late_start[s] - lag, cal, role="start")

    def _succ_lf_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_cal:
            return lf_wall[s]
        return _offset_to_wall(ps, late_finish[s] - lag, cal, role="finish")

    for tid in reversed(order):
        dur_p = duration[tid]
        if tid in exec_cal:
            cal_t = exec_cal[tid]
            task = task_by_id[tid]
            tw = (
                target_wall
                if target_wall is not None
                else _offset_to_wall(ps, backward_target, cal, role="finish")
            )
            finish_needs: list[dt.datetime] = [tw]
            start_needs: list[dt.datetime] = []
            for s, rel, lag in succs[tid]:
                if rel is RelationshipType.FS:
                    finish_needs.append(_succ_ls_wall(s, lag))
                elif rel is RelationshipType.FF:
                    finish_needs.append(_succ_lf_wall(s, lag))
                elif rel is RelationshipType.SS:
                    start_needs.append(_succ_ls_wall(s, lag))
                else:  # SF: the successor's finish is anchored to THIS task's start
                    start_needs.append(_succ_lf_wall(s, lag))
            if task.constraint_date is not None:
                if task.constraint_type in (ConstraintType.FNLT, ConstraintType.MFO):
                    finish_needs.append(task.constraint_date)
                elif task.constraint_type in (ConstraintType.SNLT, ConstraintType.MSO):
                    finish_needs.append(_advance_wall(task.constraint_date, dur_p, cal_t, tod0))
            if task.deadline is not None:
                finish_needs.append(task.deadline)
            slack = min(
                [_wall_minutes_between(ef_wall[tid], f, cal_t, tod0) for f in finish_needs]
                + [_wall_minutes_between(es_wall[tid], s0, cal_t, tod0) for s0 in start_needs]
            )
            exec_slack[tid] = slack
            lf_w = _advance_wall_signed(ef_wall[tid], slack, cal_t, tod0)
            ls_w = _advance_wall_signed(es_wall[tid], slack, cal_t, tod0)
            ls_wall[tid], lf_wall[tid] = ls_w, lf_w
            late_finish[tid] = _wall_to_offset(ps, lf_w, cal)
            late_start[tid] = _wall_to_offset(ps, ls_w, cal)
            continue
        bounds = [
            lf_upper_bound(rel, late_start[s], late_finish[s], lag, dur_p)
            for s, rel, lag in succs[tid]
        ]
        if tid in lf_cap:
            bounds.append(lf_cap[tid])
        lf = min([backward_target, *bounds])
        late_finish[tid] = lf
        late_start[tid] = lf - dur_p

    def _succ_early_start_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_cal:
            return es_wall[s]
        return _offset_to_wall(ps, early_start[s] - lag, cal, role="start")

    def _succ_early_finish_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_cal:
            return ef_wall[s]
        return _offset_to_wall(ps, early_finish[s] - lag, cal, role="finish")

    timings: dict[int, TaskTiming] = {}
    for tid in task_ids:
        if tid in exec_cal:
            cal_t = exec_cal[tid]
            total = exec_slack[tid]
            if succs[tid]:
                free_cands = []
                for s, rel, lag in succs[tid]:
                    if rel is RelationshipType.FS:
                        anchor, need = ef_wall[tid], _succ_early_start_wall(s, lag)
                    elif rel is RelationshipType.SS:
                        anchor, need = es_wall[tid], _succ_early_start_wall(s, lag)
                    elif rel is RelationshipType.FF:
                        anchor, need = ef_wall[tid], _succ_early_finish_wall(s, lag)
                    else:  # SF
                        anchor, need = es_wall[tid], _succ_early_finish_wall(s, lag)
                    free_cands.append(_wall_minutes_between(anchor, need, cal_t, tod0))
                free = min(free_cands)
            else:
                tw = (
                    target_wall
                    if target_wall is not None
                    else _offset_to_wall(ps, backward_target, cal, role="finish")
                )
                free = _wall_minutes_between(ef_wall[tid], tw, cal_t, tod0)
        else:
            total = late_start[tid] - early_start[tid]
            if succs[tid]:
                free = min(
                    link_slack(
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
        # a violated MSO/MFO pin reports the violation as negative slack (MS Project's own
        # stored Total Slack semantics — the pin holds the dates, the float carries the truth)
        violation = pin_violation.get(tid)
        if violation is not None and violation < total:
            total = violation
        timings[tid] = TaskTiming(
            unique_id=tid,
            early_start=early_start[tid],
            early_finish=early_finish[tid],
            late_start=late_start[tid],
            late_finish=late_finish[tid],
            total_float=total,
            free_float=free,
            is_critical=total <= 0,
            early_start_wall=es_wall.get(tid),
            early_finish_wall=ef_wall.get(tid),
            late_start_wall=ls_wall.get(tid),
            late_finish_wall=lf_wall.get(tid),
        )

    critical_path = tuple(tid for tid in order if timings[tid].is_critical)
    return CPMResult(
        timings=timings,
        project_finish=network_finish,
        critical_path=critical_path,
        date_driven=tuple(sorted(date_driven)),
        actual_start_driven=tuple(sorted(actual_driven)),
        project_finish_wall=target_wall if required_finish_offset is None else None,
    )
