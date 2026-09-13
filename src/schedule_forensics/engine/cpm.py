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
* **Resource calendars honored** (ADR-0474). MS Project schedules an assignment on the
  RESOURCE's calendar (intersected with the task's own calendar unless the task ignores
  resource calendars), so a task whose crew works 16-hour or 24-hour days finishes on that
  calendar. Each such task carries an *execution plan* — one leg per work-resource
  assignment ``(calendar, span)`` where the span is the task duration scaled by
  ``min(1, (work / units) / duration)`` — and starts at the earliest leg's first working
  instant, finishes at the latest leg's finish, with the retreat / float axis on the
  latest-finishing ("primary") leg. A task calendar intersected with a resource calendar
  is approximated: a 24-hour task calendar yields the resource calendar exactly; any other
  task calendar wins (documented; two Hard_File activities). A same-pattern resource
  calendar changes nothing and stays on the integer fast path.
* **A material / cost booking's RECORDED span honored** (ADR-0487, R-56): MS Project spreads
  a MATERIAL or COST booking over a span that no stored quantity determines (measured on
  Hard_File_updated3 — UID 302's two non-work bookings, 1 unit at 100 % and 0.15 units at
  0.06 %, share one 36 h span; at UID 385 the 1-unit / 100 % booking spans 24 h and the
  2.5-unit / 0.06 % booking 125 h), so the file's recorded
  assignment window (``Assignment.start`` / ``finish``) is read as a leg of the execution
  plan and the task finishes where the reference tool finishes it; the task is disclosed on
  :attr:`CPMResult.booking_span_driven`. A WORK booking's window is never read — the engine
  reproduces it (ADR-0474). updated3's project finish: 13 days early → exact.
* **Leveling delay honored** (ADR-0474): MS Project's stored resource-leveling delay is
  ELAPSED time added after the task's own calendar first admits it (Hard_File UID 403:
  Friday 08:00 + 25 d 7 h → the stored Tuesday 15:00). Delayed UniqueIDs are reported on
  :attr:`CPMResult.leveling_driven` — a stored scheduling input, not an unsupported date.
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
  UniqueIDs join :attr:`CPMResult.date_driven`, the same disclosure ADR-0034 uses. A floored
  task's total float is the smaller of its start slack and its finish slack (ADR-0463): the
  floor moves the finish, so ``LS - ES`` alone overstated the float by the floor's gap.
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
  ``date_driven`` (a recorded actual is evidence, not an unsupported date). The floor applies
  under a constraint pin as well (CPM-03, ADR-0467): a started Must-Start-On / Must-Finish-On
  task is scheduled at its actual start, not at its constraint date — MS Project's own rule
  (its stored Start equals the Actual Start on every started task in the corpus, constraint
  or not); before ADR-0467 the pin branch skipped the floor and understated such a finish.
* **A COMPLETED activity occupies exactly its RECORDED WINDOW** (ADR-0476, closing the
  half ADR-0391 named and left): 100% complete with both actuals present, its early start
  is PINNED at ``actual_start`` and its early finish PINNED at ``actual_finish``. Completed
  work is history, not a forecast — ``start + duration`` is a *prediction of* a span the
  file already measured, and predicting a fact is how a completed activity came to land 36
  days after the date its own file says it finished. Measured on the corpus that licenses
  the rule: MS Project's stored ``Finish`` equals ``ActualFinish`` on **2,289 of 2,289**
  completed activities across six progressed goldens, and stored ``Start`` equals
  ``ActualStart`` on **2,601 of 2,601** started ones, so the pin reproduces the reference
  tool's own dates by construction rather than by fitting. Pinned UniqueIDs are reported on
  :attr:`CPMResult.actual_finish_driven`, the sibling of ``actual_start_driven``.
  **Deliberately a FLOOR, not a pin, for work still IN PROGRESS:** its start is recorded but
  its finish is a forecast, and pinning an out-of-sequence in-progress start lets the
  network pull EARLIER — measured at **136 days** on Large_Test_File UID 1489 (95% complete)
  when the pin was applied to every started task. Understating a slip is the one direction
  a forensic delay tool must never be wrong in (Law 2), so in-progress work keeps ADR-0391's
  floor. The two halves must also ship TOGETHER: pinning a completed start while leaving its
  finish at ``start + duration`` moved Large_Test_File UID 7113 from exact to 85 days early.
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
import weakref
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import NamedTuple

from schedule_forensics.engine.summary_logic import (
    SummaryLogicExplosion,
    lower_summary_relationships,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.resource import ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task, TaskType

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
    #: UniqueIDs whose early FINISH is their RECORDED ``actual_finish`` because the activity is
    #: complete (ADR-0476) — a transcribed measurement rather than a computed forecast. The
    #: sibling of :attr:`actual_start_driven`, and disclosed separately for the same reason:
    #: neither is an unsupported date, and merging either into ``date_driven`` would emit a
    #: false manipulation signal on every progressed schedule.
    actual_finish_driven: tuple[int, ...] = ()
    #: UniqueIDs whose early start carries MS Project's stored resource-LEVELING DELAY
    #: (ADR-0474): elapsed time the reference tool itself adds before the task may start.
    #: Reported separately — a stored scheduling input, neither an unsupported date
    #: (``date_driven``) nor evidence of work begun (``actual_start_driven``).
    leveling_driven: tuple[int, ...] = ()
    #: UniqueIDs whose early FINISH a MATERIAL / COST booking's RECORDED span decides
    #: (ADR-0487): MS Project spreads such a booking over a window no stored quantity
    #: determines, the file records the window, and the engine reads it as the task's primary
    #: execution leg. A stored scheduling input read like the leveling delay — neither an
    #: unsupported date (``date_driven``) nor evidence of work begun.
    booking_span_driven: tuple[int, ...] = ()
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


# --- per-calendar lookup structures, found by object identity ------------------------------


class _Ruler:
    """The lookup structures every calendar-arithmetic helper in this module consumes, built
    ONCE per ``Calendar`` OBJECT and found by identity (:func:`_ruler`).

    The model stores a calendar's pattern as tuples, so the helpers were scanning tuples or
    rebuilding sets on every call; the memo that first replaced those scans (an ``lru_cache``
    keyed on the frozen model) paid a full-model ``__hash__`` + ``__eq__`` on EVERY lookup —
    measured at ~1.1 µs, on ~400 day tests per solve of a leveled golden — which, with the
    per-solve rebuild of the execution plans, took ``compute_cpm`` on Project2 from 1.3 ms to
    3.7 ms and the SRA's thousand solves past the browser proof's caption wait (ADR-0474's
    latency follow-up, pinned by ``tests/perf/test_perf_regression.py``). Purely a
    lookup-structure change: the same members give the same answers, and the counting loops
    keep the model's own tuple (``holiday_seq``) so even a duplicated holiday counts exactly as
    it always did. The entry dies with its calendar (a weakref finalizer), so nothing outlives
    the schedule that owns it, and every hit re-checks the ``id`` against a weak reference so a
    recycled address can never serve a stale ruler."""

    __slots__ = (
        "_segments",
        "advances",
        "counts",
        "declared_segments",
        "extra",
        "holiday_seq",
        "holidays",
        "is_24x7",
        "mpd",
        "owner",
        "retreats",
        "wdpw",
        "weekdays",
    )

    def __init__(self, cal: Calendar) -> None:
        self.owner: weakref.ref[Calendar] = weakref.ref(cal)
        self.mpd: int = cal.working_minutes_per_day
        self.weekdays: frozenset[int] = frozenset(cal.work_weekdays)
        self.wdpw: int = len(self.weekdays)  # the model refuses duplicate weekdays
        self.holidays: frozenset[dt.date] = frozenset(cal.holidays)
        self.holiday_seq: tuple[dt.date, ...] = cal.holidays
        self.extra: frozenset[dt.date] = frozenset(cal.working_days)
        self.is_24x7: bool = self.mpd >= 1440 and len(cal.work_weekdays) == 7 and not cal.holidays
        self.declared_segments: tuple[tuple[int, int], ...] = cal.day_segments
        self._segments: dict[int, tuple[tuple[int, int], ...]] = {}
        #: Memos of the three day-walking cores — ``[d0, d1)`` working-day counts and the
        #: k-th working day after / before a day. A solve asks the same questions of the same
        #: dates over and over (every stored date projects from the project start; the SRA's
        #: thousand passes revisit the same working days), and each answer is a pure function of
        #: the calendar. Bounded by :data:`_MEMO_CAP` (cleared, never evicted piecemeal).
        self.counts: dict[tuple[dt.date, dt.date], int] = {}
        self.advances: dict[tuple[dt.date, int], dt.date] = {}
        self.retreats: dict[tuple[dt.date, int], dt.date] = {}

    def is_working_day(self, day: dt.date) -> bool:
        """:meth:`Calendar.is_working_day`: a working weekday that is not a holiday."""
        return day.weekday() in self.weekdays and day not in self.holidays

    def is_worked(self, day: dt.date) -> bool:
        """:meth:`Calendar.is_worked`: honouring the extra ``working_days`` exceptions too."""
        return day in self.extra or (day.weekday() in self.weekdays and day not in self.holidays)

    def segments(self, day_start_tod: int) -> tuple[tuple[int, int], ...]:
        """The calendar's intraday working blocks as minutes-from-midnight, memoized per day
        start. Falls back to one contiguous block anchored at ``day_start_tod`` (the project
        start's time of day — the engine's existing single-block convention) when the source
        declared no segments; a 24-hour day is the whole day."""
        got = self._segments.get(day_start_tod)
        if got is not None:
            return got
        if self.declared_segments:
            got = self.declared_segments
        elif self.mpd >= 1440:
            got = ((0, 1440),)
        else:
            start = day_start_tod if day_start_tod + self.mpd <= 1440 else 0
            got = ((start, start + self.mpd),)
        self._segments[day_start_tod] = got
        return got


_RULERS: dict[int, _Ruler] = {}
#: Entries a ruler's date memo may hold before it is cleared (a cap, not an eviction policy —
#: a full memo on a 2 000-task, 100-holiday schedule is a few thousand entries).
_MEMO_CAP = 65_536


def _ruler(cal: Calendar) -> _Ruler:
    """The :class:`_Ruler` of ``cal`` — by object identity, built on first sight."""
    key = id(cal)
    hit = _RULERS.get(key)
    if hit is not None and hit.owner() is cal:
        return hit
    made = _Ruler(cal)
    _RULERS[key] = made
    weakref.finalize(cal, _RULERS.pop, key, None)
    return made


def _count_working_days(calendar: Calendar, d0: dt.date, d1: dt.date) -> int:
    """Number of working days in the half-open range ``[d0, d1)`` (requires ``d0 <= d1``).

    Full-weeks arithmetic + a short (<7-day) remainder loop, then subtract the holidays
    that fall on a working weekday inside the range — O(weeks-of-remainder + holidays),
    not O(days). Equivalent to the day-by-day count (see ``test_cpm_date_equivalence``).
    """
    return _count_working_days_r(_ruler(calendar), d0, d1)


def _count_working_days_r(r: _Ruler, d0: dt.date, d1: dt.date) -> int:
    total = (d1 - d0).days
    if total <= 0:
        return 0
    memo = r.counts
    key = (d0, d1)
    hit = memo.get(key)
    if hit is not None:
        return hit
    workdays = r.weekdays
    full_weeks, remainder = divmod(total, 7)
    count = full_weeks * r.wdpw
    w0 = d0.weekday()
    # the remainder days are d0+full_weeks*7+i for i in [0,remainder); weekday == (w0+i)%7
    count += sum(1 for i in range(remainder) if (w0 + i) % 7 in workdays)
    # a holiday only ever removed a day that was otherwise a working weekday
    if r.holiday_seq:
        count -= sum(1 for h in r.holiday_seq if d0 <= h < d1 and h.weekday() in workdays)
    if len(memo) >= _MEMO_CAP:
        memo.clear()
    memo[key] = count
    return count


def datetime_to_offset(start: dt.datetime, target: dt.datetime, calendar: Calendar) -> int:
    """Signed working-minute offset of ``target`` from ``start``.

    ``start`` is assumed to sit at a working-day start. The date contributes whole
    working days; the intraday term is ``(target_time - start_time)`` clamped to
    ``[0, working_minutes_per_day]``. A target on a non-working day contributes no
    intraday minutes (ADR-0010, H-CONSTRAINT-DATETIME).
    """
    r = _ruler(calendar)
    per_day = r.mpd
    start_tod = start.hour * 60 + start.minute
    target_tod = target.hour * 60 + target.minute
    target_day = target.date()
    intraday = min(max(target_tod - start_tod, 0), per_day) if r.is_working_day(target_day) else 0
    if target_day >= start.date():
        return _count_working_days_r(r, start.date(), target_day) * per_day + intraday
    return -_count_working_days_r(r, target_day, start.date()) * per_day + intraday


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
    r = _ruler(calendar)
    nxt = day + dt.timedelta(days=1)
    while not r.is_working_day(nxt.date()):
        nxt += dt.timedelta(days=1)
    return nxt


def _advance_working_days(start_day: dt.date, k: int, calendar: Calendar) -> dt.date:
    """The working day ``k`` working-days after ``start_day`` (which must be a working day).

    Week-jump + short remainder step, then compensate for any working-weekday holidays the
    jump passed over (each pushes the result one more working day; the newly-traversed span
    may add more, so it iterates — but only over holidays, never day-by-day). Equivalent to
    applying ``_next_working_day`` ``k`` times (see ``test_cpm_date_equivalence``).
    """
    return _advance_working_days_r(start_day, k, _ruler(calendar))


def _advance_working_days_r(start_day: dt.date, k: int, r: _Ruler) -> dt.date:
    if k <= 0:
        return start_day
    memo = r.advances
    key = (start_day, k)
    hit = memo.get(key)
    if hit is not None:
        return hit
    workdays = r.weekdays
    wdpw = r.wdpw
    holidays = r.holiday_seq
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
        needed = (
            sum(1 for h in holidays if cur < h <= nxt and h.weekday() in workdays)
            if holidays
            else 0
        )
        cur = nxt
    if len(memo) >= _MEMO_CAP:
        memo.clear()
    memo[key] = cur
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
    r = _ruler(calendar)
    per_day = r.mpd
    day = start
    while not r.is_working_day(day.date()):
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
    target_date = _advance_working_days_r(day.date(), advance, r)
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
    r = _ruler(calendar)
    per_day = r.mpd
    quotient, remainder = divmod(minutes, per_day)
    if remainder:
        return offset_to_datetime(start, minutes, calendar)
    day = start
    while not r.is_working_day(day.date()):
        day = _next_working_day(day, calendar)
    target_date = _advance_working_days_r(day.date(), quotient, r)
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


#: One execution leg of a task: the calendar a work-resource assignment (or the task itself)
#: consumes its working time on, and the working minutes it consumes there.
_Leg = tuple[Calendar, int]
#: A task's execution legs, PRIMARY (latest-finishing) leg first: the task starts at the
#: earliest leg's first working instant and finishes at the latest leg's finish.
_Plan = tuple[_Leg, ...]


class _Exec(NamedTuple):
    """How an off-fast-path task executes: its legs, and the calendar its SLACK is measured on
    — the task's OWN calendar (the 24/7 calendar for an elapsed duration), else the project
    calendar. MS Project measures Total Slack on the task calendar even when the assignment
    runs on a resource calendar (Hard_File UID 178: ES Mon 17:00 → LS Tue 13:00 is 240 project
    minutes, the stored slack; the crew's 16-hour calendar would read 720). ``recorded`` says
    the PRIMARY leg is a material / cost booking's recorded span (ADR-0487) — the finish is
    then the file's, and the task is disclosed on ``CPMResult.booking_span_driven``."""

    legs: _Plan
    axis: Calendar
    recorded: bool = False


class _LegShape(NamedTuple):
    """One execution leg before the solve's durations are known: its calendar, the share of the
    task's EFFECTIVE duration it spans (1.0 = the whole task; above 1.0 only for a recorded
    material / cost span, ADR-0487), whether that calendar differs materially from the project
    calendar, and whether the leg IS a recorded span."""

    calendar: Calendar
    ratio: float
    off_pattern: bool
    recorded: bool = False


class _PlanShape(NamedTuple):
    """Everything about a task's execution plan that depends on the SCHEDULE alone — never on
    the durations of one solve (the SRA hands ``compute_cpm`` a fresh override map per
    iteration; the legs' spans scale with it, nothing else does)."""

    elapsed: bool
    legs: tuple[_LegShape, ...]
    task_calendar: Calendar | None
    leveled: bool


class _ShapeContext(NamedTuple):
    schedule: Schedule
    project_key: tuple[object, ...]
    by_uid: dict[int, Calendar]
    same_pattern: dict[int, bool]  # id(calendar) → its pattern equals the project calendar's


def _same_pattern(cal: Calendar, ctx: _ShapeContext) -> bool:
    key = id(cal)
    got = ctx.same_pattern.get(key)
    if got is None:
        got = ctx.same_pattern[key] = cal.working_pattern_key() == ctx.project_key
    return got


def _task_shape(t: Task, ctx: _ShapeContext) -> _PlanShape | None:
    """The :class:`_PlanShape` of ``t``, or ``None`` when no duration can ever take it off the
    project calendar's integer fast path."""
    if t.duration_is_elapsed and t.duration_minutes > 0:
        return _PlanShape(True, (), None, False)
    task_cal = ctx.by_uid.get(t.calendar_uid) if t.calendar_uid is not None else None
    if task_cal is not None and _same_pattern(task_cal, ctx):
        task_cal = None
    legs: list[_LegShape] = []
    if t.resource_assignments and not t.ignore_resource_calendar and t.duration_minutes > 0:
        res_by_id = ctx.schedule.resources_by_id
        for a in t.resource_assignments:
            res = res_by_id.get(a.resource_id)
            if res is None:
                continue
            rcal = ctx.by_uid.get(res.calendar_uid) if res.calendar_uid is not None else None
            if rcal is None or _same_pattern(rcal, ctx):
                rcal = ctx.schedule.calendar
            leg_cal = rcal if task_cal is None or _is_24x7(task_cal) else task_cal
            if res.type is not ResourceType.WORK:
                # a MATERIAL / COST booking (ADR-0487): MS Project spreads it over a span no
                # stored quantity determines; the file RECORDS the span, and the engine reads
                # it as a leg — the booking's window on the crew's calendar — so the task
                # finishes where the reference tool finishes it. No window, no leg.
                if a.start is None or a.finish is None:
                    continue
                span = _recorded_span(leg_cal, a.start, a.finish)
                if span <= 0:
                    continue
                legs.append(
                    _LegShape(
                        leg_cal, span / t.duration_minutes, not _same_pattern(leg_cal, ctx), True
                    )
                )
                continue
            if a.work_minutes <= 0 or a.units <= 0:
                continue
            # a FIXED_UNITS assignment runs work / units of its calendar (it may end before
            # the task: Hard_File UID 200); a fixed-duration / fixed-work assignment spans
            # the whole task, its work contoured over it (Large Test File2: 78 of 117
            # fixed-work assignments with work / units below the duration span it exactly,
            # none span work / units)
            ratio = (
                min(1.0, (a.work_minutes / a.units) / t.duration_minutes)
                if t.task_type is TaskType.FIXED_UNITS
                else 1.0
            )
            legs.append(_LegShape(leg_cal, ratio, not _same_pattern(leg_cal, ctx)))
    # legs that all sit on the project pattern under no task calendar can never form a plan,
    # whatever the durations — unless one of them outspans the task (a recorded material /
    # cost span, ADR-0487): the fast path could not carry the task past its duration
    if legs and task_cal is None and not any(leg.off_pattern or leg.ratio > 1.0 for leg in legs):
        legs = []
    leveled = t.leveling_delay_minutes > 0
    if not legs and task_cal is None and not leveled:
        return None
    return _PlanShape(False, tuple(legs), task_cal, leveled)


_SHAPES: dict[int, tuple[weakref.ref[Schedule], dict[int, _PlanShape | None]]] = {}


def _plan_shapes(schedule: Schedule) -> dict[int, _PlanShape | None]:
    """UniqueID → :class:`_PlanShape` (``None`` = never off the fast path) for every task of
    ``schedule``, derived once per schedule OBJECT and found by identity — the same weakref
    discipline as :func:`_ruler`. Re-deriving the shapes per solve read every assignment and
    its resource's calendar pattern ~300 times per pass on Project2, the SRA's thousand passes
    included (ADR-0474's latency follow-up)."""
    key = id(schedule)
    hit = _SHAPES.get(key)
    if hit is not None and hit[0]() is schedule:
        return hit[1]
    ctx = _ShapeContext(
        schedule,
        schedule.calendar.working_pattern_key(),
        {c.uid: c for c in schedule.calendars},
        {},
    )
    shapes: dict[int, _PlanShape | None] = {
        t.unique_id: _task_shape(t, ctx) for t in schedule.tasks
    }
    _SHAPES[key] = (weakref.ref(schedule), shapes)
    weakref.finalize(schedule, _SHAPES.pop, key, None)
    return shapes


def _execution_plans(
    schedule: Schedule, tasks: list[Task], duration: Mapping[int, int]
) -> dict[int, _Exec]:
    """UniqueID → the execution plan of every task that does NOT run its whole duration on
    the project calendar's integer fast path (ADR-0322 task calendars, ADR-0474 resource
    calendars and leveling delays). ``duration`` is the effective working duration per task
    (the SRA / DCMA-12 overrides included) — a leg's span scales with it.

    * an elapsed duration → one leg on the 24/7 calendar;
    * work-resource assignments (unless the task ignores resource calendars): one leg per
      assignment on the resource's registered calendar (the project calendar when the
      resource carries none or a same-pattern one), spanning ``min(1, (work / units) /
      stored duration) x duration``; a task calendar intersects: a 24-hour task calendar
      yields the resource calendar, any other task calendar wins (approximation);
    * a MATERIAL / COST booking with a recorded window: one leg spanning that window on the
      crew's calendar — the span the file records, the one input it carries (ADR-0487);
    * a materially different task calendar with no such legs → one leg on it;
    * a leveling delay on a project-calendar task → one leg on the project calendar, so the
      delay's elapsed arithmetic runs segment-aware on the wall path.

    Legs that all sit on the project pattern (and no task calendar, no delay) stay on the
    fast path: the stored duration is then the span, exactly as before. The duration-free
    part of every plan is the task's :class:`_PlanShape`, derived once per schedule object.
    """
    shapes = _plan_shapes(schedule)
    ps = schedule.project_start
    tod0 = ps.hour * 60 + ps.minute
    out: dict[int, _Exec] = {}
    for t in tasks:
        uid = t.unique_id
        shape = shapes.get(uid, _FOREIGN)
        if shape is _FOREIGN:  # a task the schedule does not carry: derive it on the spot
            shape = _task_shape(
                t,
                _ShapeContext(
                    schedule,
                    schedule.calendar.working_pattern_key(),
                    {c.uid: c for c in schedule.calendars},
                    {},
                ),
            )
        if shape is None:
            continue
        dur = duration[uid]
        if shape.elapsed:
            out[uid] = _Exec(((_ELAPSED_CALENDAR, dur),), _ELAPSED_CALENDAR)
            continue
        legs: list[_Leg] = []
        # recorded legs by calendar IDENTITY and span — never by hashing the frozen Calendar
        # model on a solver the SRA calls a thousand times (ADR-0474's latency amendment)
        recorded: set[tuple[int, int]] = set()
        off_pattern = False
        for leg_cal, ratio, off, rec in shape.legs:
            span = round(ratio * dur)
            if span > 0:
                legs.append((leg_cal, span))
                off_pattern = off_pattern or off
                if rec:
                    recorded.add((id(leg_cal), span))
        task_cal = shape.task_calendar
        plan: _Plan
        if legs and (off_pattern or task_cal is not None or any(s > dur for _, s in legs)):
            plan = tuple(dict.fromkeys(legs))
        elif task_cal is not None:
            plan = ((task_cal, dur),)
        elif shape.leveled:
            plan = ((schedule.calendar, dur),)
        else:
            continue
        if len(plan) > 1:
            # primary leg first: the one finishing latest from the project start (stable, so
            # equal finishes keep the assignment order)
            plan = tuple(
                sorted(
                    plan,
                    key=lambda leg: _advance_wall(
                        _snap_to_working(ps, leg[0], tod0), leg[1], leg[0], tod0
                    ),
                    reverse=True,
                )
            )
        out[uid] = _Exec(
            plan,
            task_cal if task_cal is not None else schedule.calendar,
            (id(plan[0][0]), plan[0][1]) in recorded,
        )
    return out


#: Sentinel for a task absent from the schedule's shape map (never a real shape).
_FOREIGN = _PlanShape(False, (), None, False)


def execution_calendar_of(schedule: Schedule, task: Task) -> Calendar | None:
    """The calendar ``task``'s duration actually consumes when it differs from the project
    calendar's fast path — the 24/7 calendar for an elapsed duration, its own or its primary
    resource's calendar otherwise — else ``None``. The single public lookup consumers (the
    DCMA-12 delay injection) use to size a delay on the task's own axis."""
    plan = _execution_plans(schedule, [task], {task.unique_id: task.duration_minutes})
    ex = plan.get(task.unique_id)
    return None if ex is None else ex.legs[0][0]


def injected_finish_wall(
    schedule: Schedule, task: Task, timing: TaskTiming, extra_minutes: int
) -> dt.datetime | None:
    """The finish instant ``task`` would reach were its duration ``extra_minutes`` longer, run
    on its execution plan from its computed early start (every leg scales with the duration).
    ``None`` when the task runs on the integer fast path (no plan / no wall start) — the
    caller then reasons on the project axis."""
    ex = _execution_plans(
        schedule, [task], {task.unique_id: task.duration_minutes + extra_minutes}
    ).get(task.unique_id)
    if ex is None or timing.early_start_wall is None:
        return None
    ps = schedule.project_start
    return _plan_finish(timing.early_start_wall, ex.legs, ps.hour * 60 + ps.minute)


def _plan_snap(wall: dt.datetime, plan: _Plan, day_start_tod: int) -> dt.datetime:
    """The earliest instant at or after ``wall`` on which ANY leg of the plan can work — the
    task's start (MS Project: the earliest assignment start)."""
    if len(plan) == 1:  # the one-leg plan (a task calendar, an elapsed duration, a delay)
        return _snap_to_working(wall, plan[0][0], day_start_tod)
    return min(_snap_to_working(wall, c, day_start_tod) for c, _ in plan)


def _plan_finish(start: dt.datetime, plan: _Plan, day_start_tod: int) -> dt.datetime:
    """The task's finish from ``start``: every leg starts at its own calendar's first working
    instant at or after ``start``, consumes its span there; the latest leg finish wins."""
    if len(plan) == 1:
        c, span = plan[0]
        return _advance_wall(_snap_to_working(start, c, day_start_tod), span, c, day_start_tod)
    return max(
        _advance_wall(_snap_to_working(start, c, day_start_tod), span, c, day_start_tod)
        for c, span in plan
    )


def _plan_retreat(finish: dt.datetime, plan: _Plan, day_start_tod: int) -> dt.datetime:
    """The latest start from which every leg still finishes by ``finish``."""
    if len(plan) == 1:
        c, span = plan[0]
        return _retreat_wall(finish, span, c, day_start_tod)
    return min(_retreat_wall(finish, span, c, day_start_tod) for c, span in plan)


def _plan_scaled(plan: _Plan, minutes: int, duration: int) -> _Plan:
    """The plan's legs scaled to ``minutes`` of the ``duration`` they were built for (the
    remaining-work floor); a zero duration collapses onto the primary leg."""
    if duration <= 0:
        return ((plan[0][0], minutes),)
    return tuple((c, round(span * minutes / duration)) for c, span in plan)


def _day_segments_of(cal: Calendar, day_start_tod: int) -> tuple[tuple[int, int], ...]:
    """The calendar's intraday working blocks as minutes-from-midnight (see
    :meth:`_Ruler.segments`)."""
    return _ruler(cal).segments(day_start_tod)


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


def _is_worked_day(cal: Calendar, day: dt.date) -> bool:
    """Task-calendar working-day test, honoring extra ``working_days`` exceptions
    (set-based twin of :meth:`Calendar.is_worked` — identical answers, O(1) membership)."""
    return _ruler(cal).is_worked(day)


def _retreat_working_days(start_day: dt.date, k: int, calendar: Calendar) -> dt.date:
    """The working day ``k`` working-days BEFORE ``start_day`` — the backward mirror of
    :func:`_advance_working_days` (same full-weeks jump + short remainder + holiday
    make-up over the traversed span, which is ``[nxt, cur)`` going backward)."""
    return _retreat_working_days_r(start_day, k, _ruler(calendar))


def _retreat_working_days_r(start_day: dt.date, k: int, r: _Ruler) -> dt.date:
    if k <= 0:
        return start_day
    memo = r.retreats
    key = (start_day, k)
    hit = memo.get(key)
    if hit is not None:
        return hit
    workdays = r.weekdays
    wdpw = r.wdpw
    holidays = r.holiday_seq
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
        needed = (
            sum(1 for h in holidays if nxt <= h < cur and h.weekday() in workdays)
            if holidays
            else 0
        )
        cur = nxt
    if len(memo) >= _MEMO_CAP:
        memo.clear()
    memo[key] = cur
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
    return _shift_worked_days_r(_ruler(cal), day, n)


def _shift_worked_days_r(r: _Ruler, day: dt.date, n: int) -> dt.date:
    if not r.extra:
        if n == 0:
            return day
        if n > 0:
            return _advance_working_days_r(day, n, r)
        return _retreat_working_days_r(day, -n, r)
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    cur = day
    while remaining > 0:
        cur += dt.timedelta(days=step)
        if r.is_worked(cur):
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
    r = _ruler(cal)
    segments = r.segments(day_start_tod)
    mpd = r.mpd
    base = start.date()
    if not r.is_working_day(base):  # anchored starts are working days; defensive
        base = _shift_worked_days_r(r, base, 1)
    quotient, remainder = divmod(offset, mpd)  # floor division: negative offsets go backward
    if role == "finish" and offset != 0 and remainder == 0:
        # an exact multiple ENDS at the previous working day's last block (offset 0 stays
        # the project-start instant); same rule on the negative side — "-1 day, finish
        # role" is the end of the working day before that, not its start
        quotient, remainder = quotient - 1, mpd
    day = _advance_working_days_r(base, quotient, r) if quotient >= 0 else base
    if quotient < 0:
        cur, back = base, -quotient
        while back > 0:
            cur -= dt.timedelta(days=1)
            if r.is_working_day(cur):
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


def _recorded_span(cal: Calendar, start: dt.datetime, finish: dt.datetime) -> int:
    """Working minutes of ``cal`` inside the RECORDED window ``[start, finish]`` — the span a
    material / cost booking occupies (ADR-0487). Segment-aware at both ends (a 14:24 finish on
    a 08-12 / 13-17 day is 324 minutes into it, not 384: the contiguous projection ruler
    over-counts a lunch gap by its width, one hour late on Hard_File_updated3 UID 385), whole
    days by the ruler's count, elapsed time on a 24/7 calendar. 0 for an empty or inverted
    window."""
    if finish <= start:
        return 0
    r = _ruler(cal)
    if r.is_24x7:
        return int((finish - start).total_seconds() // 60)
    d0, d1 = start.date(), finish.date()
    worked_by = cal.intraday_worked_minutes
    start_tod = start.hour * 60 + start.minute
    finish_tod = finish.hour * 60 + finish.minute
    if d0 == d1:
        return worked_by(finish_tod) - worked_by(start_tod) if r.is_working_day(d0) else 0
    first = r.mpd - worked_by(start_tod) if r.is_working_day(d0) else 0
    middle = _count_working_days_r(r, d0 + dt.timedelta(days=1), d1) * r.mpd
    last = worked_by(finish_tod) if r.is_working_day(d1) else 0
    return first + middle + last


def _is_24x7(cal: Calendar) -> bool:
    return _ruler(cal).is_24x7


def _advance_wall(
    wall: dt.datetime, minutes: int, cal: Calendar, day_start_tod: int
) -> dt.datetime:
    """Consume ``minutes >= 0`` of working time on ``cal`` forward from ``wall``."""
    if minutes <= 0:
        return wall
    r = _ruler(cal)
    if r.is_24x7:
        return wall + dt.timedelta(minutes=minutes)
    segments = r.segments(day_start_tod)
    mpd = r.mpd
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    remaining = minutes
    if r.is_worked(day):
        available_today = mpd - _worked_before(segments, tod)
        if remaining <= available_today:
            new_tod = _tod_at_worked(segments, _worked_before(segments, tod) + remaining)
            return _at_minute(day, new_tod)
        remaining -= available_today
    quotient, part = divmod(remaining, mpd)
    if part == 0:
        quotient, part = quotient - 1, mpd
    day = _shift_worked_days_r(r, day, quotient + 1)
    tod = _tod_at_worked(segments, part)
    return _at_minute(day, tod)


def _retreat_wall(
    wall: dt.datetime, minutes: int, cal: Calendar, day_start_tod: int
) -> dt.datetime:
    """Consume ``minutes >= 0`` of working time on ``cal`` backward from ``wall``."""
    if minutes <= 0:
        return wall
    r = _ruler(cal)
    if r.is_24x7:
        return wall - dt.timedelta(minutes=minutes)
    segments = r.segments(day_start_tod)
    mpd = r.mpd
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    remaining = minutes
    if r.is_worked(day):
        available_today = _worked_before(segments, tod)
        if remaining <= available_today:
            new_tod = _tod_at_worked(segments, available_today - remaining)
            return _at_minute(day, new_tod)
        remaining -= available_today
    quotient, part = divmod(remaining, mpd)
    if part == 0:
        quotient, part = quotient - 1, mpd
    day = _shift_worked_days_r(r, day, -(quotient + 1))
    tod = _tod_at_worked(segments, mpd - part)
    return _at_minute(day, tod)


def _wall_minutes_between(a: dt.datetime, b: dt.datetime, cal: Calendar, day_start_tod: int) -> int:
    """SIGNED working minutes on ``cal`` from instant ``a`` to instant ``b`` (negative when
    ``b`` precedes ``a``). This is the float axis for an off-calendar task — MS Project
    measures a task's slack in its own calendar's working time."""
    if b < a:
        return -_wall_minutes_between(b, a, cal, day_start_tod)
    r = _ruler(cal)
    if r.is_24x7:
        return int((b - a).total_seconds() // 60)
    segments = r.segments(day_start_tod)
    mpd = r.mpd
    a_day, b_day = a.date(), b.date()
    a_worked = r.is_worked(a_day)
    a_intraday = _worked_before(segments, a.hour * 60 + a.minute) if a_worked else 0
    b_intraday = _worked_before(segments, b.hour * 60 + b.minute) if r.is_worked(b_day) else 0
    if a_day == b_day:
        return b_intraday - a_intraday
    # Full worked days STRICTLY between the two dates: the proven full-weeks arithmetic
    # (O(weeks + holidays), never a per-day walk — these spans can be months of slack)
    # plus the calendar's extra working days a weekday-minus-holiday count misses.
    lo, hi = a_day + dt.timedelta(days=1), b_day
    full_days_between = _count_working_days_r(r, lo, hi) if lo < hi else 0
    if r.extra:
        full_days_between += sum(
            1
            for d in r.extra
            if lo <= d < hi and (d.weekday() not in r.weekdays or d in r.holidays)
        )
    tail = mpd - a_intraday if a_worked else 0
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
    r = _ruler(cal)
    if r.is_24x7:
        return wall
    segments = r.segments(day_start_tod)
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    while True:
        if r.is_worked(day):
            for seg_start, seg_end in segments:
                if tod < seg_end:
                    new_tod = max(tod, seg_start)
                    return _at_minute(day, new_tod)
        day += dt.timedelta(days=1)
        tod = 0


def _snap_back_to_working(wall: dt.datetime, cal: Calendar, day_start_tod: int) -> dt.datetime:
    """The latest working instant on ``cal`` at or before ``wall`` at which work can END — a
    FINISH-role instant: the start of a working block (Monday 08:00) is the same grid point as
    the previous block's end (Friday 17:00), and MS Project writes a late finish as the latter
    (ADR-0474: a fast-path successor's late-start need arrives as a start-role instant)."""
    r = _ruler(cal)
    if r.is_24x7:
        return wall
    segments = r.segments(day_start_tod)
    day, tod = wall.date(), wall.hour * 60 + wall.minute
    while True:
        if r.is_worked(day):
            for seg_start, seg_end in reversed(segments):
                if tod > seg_start:
                    return _at_minute(day, min(tod, seg_end))
        day -= dt.timedelta(days=1)
        tod = 1440


def _working_pattern_key(cal: Calendar) -> tuple[object, ...]:
    """The calendar's material working pattern — :meth:`Calendar.working_pattern_key` (moved
    onto the model by ADR-0474 so the importer's registry can apply the same test)."""
    return cal.working_pattern_key()


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


def is_recorded_complete(task: Task) -> bool:
    """Is this activity's whole window a matter of RECORD (ADR-0476)?

    100% complete **and** carrying both actuals. All three are required: the percentage alone
    is a claim, and an activity reported complete with no ``ActualFinish`` has nothing to be
    pinned to. Tasks failing this keep ADR-0391's actual-start FLOOR and a computed finish.
    """
    return (
        task.percent_complete >= 100.0
        and task.actual_start is not None
        and task.actual_finish is not None
    )


def _actual_finish_bounds(schedule: Schedule, tasks: list[Task]) -> dict[int, int]:
    """Early-FINISH PINS from a COMPLETED activity's recorded ``actual_finish`` (ADR-0476).

    The fourth and last member of the stored-date family, and the only one that is a **pin in
    both directions**: :func:`_actual_start_bounds` may only push a task later, this one places
    a finished activity exactly where the file says it finished — earlier or later than logic.
    That is not a licence the others have, and it is granted for one reason: a completed
    activity's dates are not a schedule, they are a measurement. Its span is
    ``actual_finish - actual_start``, which is what the work *took*; ``duration_minutes`` is
    what it was *expected* to take, and the two differ on any activity that ran long or short.

    Applies only where :func:`is_recorded_complete` holds. Offsets clamp at the project start.
    An ``actual_finish`` at a day boundary or on a non-working instant cannot be represented
    exactly on the working-minute axis and lands on the previous working moment — a residual
    this pin exposes rather than creates, measured and named in ADR-0476.
    """
    pin: dict[int, int] = {}
    for task in tasks:
        finish = task.actual_finish  # bound locally: the narrowing must survive ``python -O``
        if finish is None or not is_recorded_complete(task):
            continue
        pin[task.unique_id] = max(
            datetime_to_offset(schedule.project_start, finish, schedule.calendar), 0
        )
    return pin


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


class _Network(NamedTuple):
    """The duration-free part of a solve: the scheduled activities, their lowered logic in
    topological order, and the stored-date bounds — every one a function of the schedule alone,
    so derived once per schedule OBJECT (the weakref discipline of :func:`_ruler`) and shared
    read-only by every solve of it. The SRA hands ``compute_cpm`` a fresh duration map a
    thousand times per request; before this, each pass re-lowered the summary logic, re-sorted
    the network and re-projected every stored date (ADR-0474's latency follow-up)."""

    tasks: list[Task]
    task_ids: list[int]
    order: list[int]
    preds: dict[int, list[_Link]]
    succs: dict[int, list[_Link]]
    task_by_id: dict[int, Task]
    stored_pin: dict[int, int]
    stored_floor: dict[int, int]
    actual_floor: dict[int, int]
    actual_finish_pin: dict[int, int]


_NETWORKS: dict[int, tuple[weakref.ref[Schedule], _Network]] = {}


def _network(schedule: Schedule) -> _Network:
    """The :class:`_Network` of ``schedule`` — by object identity, built on first sight. A
    schedule the engine refuses (a cycle, a summary-logic explosion) raises here every time
    and is never memoized."""
    key = id(schedule)
    hit = _NETWORKS.get(key)
    if hit is not None and hit[0]() is schedule:
        return hit[1]
    tasks = _scheduled_tasks(schedule)
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
    has_preds = frozenset(tid for tid in task_ids if preds[tid])
    stored_pin, stored_floor = _stored_date_bounds(schedule, tasks, has_preds)
    made = _Network(
        tasks,
        task_ids,
        order,
        preds,
        succs,
        {t.unique_id: t for t in tasks},
        stored_pin,
        stored_floor,
        _actual_start_bounds(schedule, tasks),
        _actual_finish_bounds(schedule, tasks),
    )
    _NETWORKS[key] = (weakref.ref(schedule), made)
    weakref.finalize(schedule, _NETWORKS.pop, key, None)
    return made


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

    # the network and the stored-date bounds depend on the schedule alone — derived once per
    # schedule object, read-only here (the SRA solves one object a thousand times)
    net = _network(schedule)
    task_ids, order, preds, succs = net.task_ids, net.order, net.preds, net.succs

    # ---- forward pass (ES >= 0 == project start; raised by SNET/FNET; pinned by MSO/MFO;
    # stored starts honored for unstarted manual / logic-unbound tasks — ADR-0034) ----
    stored_pin, stored_floor = net.stored_pin, net.stored_floor
    actual_floor = net.actual_floor
    actual_finish_pin = net.actual_finish_pin
    resume_ef_floor = _resume_bounds(schedule, tasks, duration_overrides)
    # Tasks executing on their OWN calendar(s) — a materially different task calendar, an
    # elapsed duration (== the 24/7 calendar), a work resource on another calendar, or a
    # leveling delay: dates advance in wall-clock arithmetic on the task's execution plan; float
    # is the primary leg's calendar minutes. Everything else stays on the integer project axis
    # (byte-identical fast path).
    exec_plan = _execution_plans(schedule, tasks, duration)
    task_by_id = net.task_by_id
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
    #: UIDs whose early FINISH was placed at their RECORDED actual finish because the activity
    #: is complete (ADR-0476). The sibling of ``actual_driven``: a transcribed measurement, not
    #: a computed forecast, and disclosed as such.
    actual_finish_driven: list[int] = []
    #: UIDs whose early start carries the stored leveling delay (ADR-0474).
    leveling_driven: list[int] = []
    #: UIDs whose finish a MATERIAL / COST booking's recorded span decides (ADR-0487).
    booking_span_driven: list[int] = []

    def _pred_finish_wall(p: int) -> dt.datetime:
        if p in exec_plan:
            return ef_wall[p]
        return _offset_to_wall(ps, early_finish[p], cal, role="finish")

    def _pred_start_wall(p: int) -> dt.datetime:
        if p in exec_plan:
            return es_wall[p]
        return _offset_to_wall(ps, early_start[p], cal, role="start")

    for tid in order:
        dur_s = duration[tid]
        if tid in exec_plan:
            ex = exec_plan[tid]
            plan, cal_t = ex.legs, ex.axis  # the legs, and the task's slack axis
            if ex.recorded:
                booking_span_driven.append(tid)
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
                else:  # FF / SF bound the FINISH; retreat the plan from it
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
                    drive = _plan_retreat(fin, plan, tod0)
                cands.append(drive)
            if tid in es_floor:
                # date-constraint floor from the RAW date (exact even inside a project void)
                if task.constraint_type is ConstraintType.SNET and task.constraint_date:
                    cands.append(task.constraint_date)
                elif task.constraint_type is ConstraintType.FNET and task.constraint_date:
                    cands.append(_plan_retreat(task.constraint_date, plan, tod0))
                else:
                    cands.append(_offset_to_wall(ps, es_floor[tid], cal, role="start"))
            logic_es_wall = _plan_snap(max(cands), plan, tod0)
            if task.leveling_delay_minutes > 0:
                # MS Project's resource-leveling delay: ELAPSED time added after the task's own
                # calendar first admits it, then the calendar admits it again (ADR-0474)
                delayed = logic_es_wall + dt.timedelta(minutes=task.leveling_delay_minutes)
                logic_es_wall = _plan_snap(delayed, plan, tod0)
                leveling_driven.append(tid)
            if tid in es_pin and task.constraint_date is not None:
                if task.constraint_type is ConstraintType.MSO:
                    es_w = _plan_snap(task.constraint_date, plan, tod0)
                else:  # MFO — pin the finish, derive the start
                    es_w = _plan_retreat(task.constraint_date, plan, tod0)
                pin_violation[tid] = _wall_minutes_between(logic_es_wall, es_w, cal_t, tod0)
            elif tid in stored_pin and task.start is not None:
                es_w = _plan_snap(max(task.start, ps), plan, tod0)
                if es_w != logic_es_wall:
                    date_driven.append(tid)
            elif tid in stored_floor and task.start is not None and task.start > logic_es_wall:
                es_w = _plan_snap(task.start, plan, tod0)
                date_driven.append(tid)
            else:
                es_w = logic_es_wall
            # work that has begun cannot begin earlier than it did (ADR-0391) — on the task's
            # OWN calendar, from the raw stored instant, and in EVERY branch above, the constraint
            # pin included (CPM-03, ADR-0467): MS Project schedules a started task at its Actual
            # Start whatever its constraint says. The stored-pin / stored-floor branches only ever
            # hold UNSTARTED tasks (_stored_date_bounds), so applying the floor after the chain is
            # byte-identical for them.
            if task.actual_start is not None:
                started_wall = _plan_snap(max(task.actual_start, ps), plan, tod0)
                # a completed activity is PINNED at its recorded start (its whole window is a
                # measurement — ADR-0476); anything still running keeps ADR-0391's FLOOR
                if started_wall > es_w or (started_wall != es_w and tid in actual_finish_pin):
                    es_w = started_wall
                    actual_driven.append(tid)
            ef_w = _plan_finish(es_w, plan, tod0)
            if tid in actual_finish_pin and task.actual_finish is not None:
                # completed: the finish is the RECORD, not ``start + duration`` (ADR-0476).
                # ``max`` keeps the window ordered when the start snapped past the raw instant.
                recorded_w = max(task.actual_finish, es_w)
                if recorded_w != ef_w:
                    actual_finish_driven.append(tid)
                ef_w = recorded_w
            # ADR-0309 resume floor, on the task's own calendar(s) from the raw stored dates
            if task.resume is not None and task.stop is not None and task.resume > task.stop:
                ov = duration_overrides or {}
                remaining = ov.get(tid, task.remaining_duration_minutes)
                if remaining is not None and remaining > 0:
                    resumed = _plan_finish(
                        max(task.resume, ps), _plan_scaled(plan, remaining, dur_s), tod0
                    )
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
        # work that has begun cannot begin earlier than it did (ADR-0391) — in EVERY branch, the
        # constraint pin included (CPM-03, ADR-0467; the pin's logic-vs-constraint violation is
        # measured above, before the floor)
        started_off = actual_floor.get(tid)
        # completed → PIN at the recorded start; still running → ADR-0391's FLOOR (ADR-0476)
        if started_off is not None and (
            started_off > es or (started_off != es and tid in actual_finish_pin)
        ):
            es = started_off
            actual_driven.append(tid)
        early_start[tid] = es
        ef = es + dur_s
        # in-progress work MS Project itself rescheduled: its remaining duration runs from the
        # stored Resume, so the finish floors there (ADR-0309). Logic may still push it later.
        finished_off = actual_finish_pin.get(tid)
        if finished_off is not None:
            # completed work sits at its RECORDED finish (ADR-0476); the ADR-0309 resume floor
            # is a rule about REMAINING work and cannot apply to an activity that has none
            recorded = max(finished_off, es)
            if recorded != ef:
                actual_finish_driven.append(tid)
            ef = recorded
        else:
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
    if exec_plan:
        if required_finish_offset is not None:
            target_wall = _offset_to_wall(ps, required_finish_offset, cal, role="finish")
        else:
            finish_cands = [t for t in task_ids if early_finish[t] == network_finish]
            target_wall = max(
                (
                    ef_wall[t]
                    if t in exec_plan
                    else _offset_to_wall(ps, early_finish[t], cal, role="finish")
                    for t in finish_cands
                ),
                default=_offset_to_wall(ps, network_finish, cal, role="finish"),
            )

    # ---- backward pass (LF capped at the backward target, and by SNLT/FNLT/MSO/MFO/deadline) ----
    late_finish: dict[int, int] = {}
    late_start: dict[int, int] = {}
    #: the late-start NEED a task presents to its predecessors on the project axis: its late
    #: start less its stored leveling delay (ADR-0474) — equal to ``late_start`` for every task
    #: without one
    ls_need: dict[int, int] = {}
    ls_wall: dict[int, dt.datetime] = {}
    lf_wall: dict[int, dt.datetime] = {}
    exec_slack: dict[int, int] = {}

    def _succ_ls_wall(s: int, lag: int) -> dt.datetime:
        # a successor's stored leveling delay sits between its predecessors' finish and its own
        # late start (MS Project: Hard_File UID 14 LF 11:00 = UID 141 LS 21:00 minus its 10 h)
        delay = dt.timedelta(minutes=task_by_id[s].leveling_delay_minutes)
        if lag == 0 and s in exec_plan:
            return ls_wall[s] - delay
        return _offset_to_wall(ps, late_start[s] - lag, cal, role="start") - delay

    def _succ_lf_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_plan:
            return lf_wall[s]
        return _offset_to_wall(ps, late_finish[s] - lag, cal, role="finish")

    # the one instant every off-fast-path task retreats from (``target_wall`` is set whenever a
    # plan exists; the fallback keeps the expression total) — derived once, not per task
    tw = (
        target_wall
        if target_wall is not None
        else (_offset_to_wall(ps, backward_target, cal, role="finish") if exec_plan else ps)
    )

    for tid in reversed(order):
        # ADR-0476: the backward pass must retreat by the SAME span the forward pass PLACED. A
        # recorded-complete activity occupies the window its file records, which is what the work
        # TOOK; ``duration_minutes`` is what it was expected to take, and on any activity that ran
        # long or short the two differ. Retreating by the planned duration makes ``LS - ES`` and
        # ``LF - EF`` disagree, and ``min()`` of the two then reports SPURIOUS NEGATIVE FLOAT on
        # work that is already finished — measured at -13 working days on a completed activity,
        # which also drags it onto the critical path and fails DCMA-12/13. Float in the past is
        # not a forecast; it must at least be self-consistent.
        dur_p = early_finish[tid] - early_start[tid] if tid in actual_finish_pin else duration[tid]
        if tid in exec_plan:
            plan, cal_t = exec_plan[tid].legs, exec_plan[tid].axis
            task = task_by_id[tid]
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
                    finish_needs.append(_plan_finish(task.constraint_date, plan, tod0))
            if task.deadline is not None:
                finish_needs.append(task.deadline)
            # MS Project's own backward pass: the late finish is the tightest finish need, the
            # late start retreats every leg from it (a start need tightens the start, and then
            # the finish follows it); total slack is the smaller of the start slack and the
            # finish slack, both measured on the task's slack axis (ADR-0474 — on a resource
            # calendar the two differ, and the stored slack is their minimum)
            lf_w = _snap_back_to_working(min(finish_needs), plan[0][0], tod0)
            if tid in actual_finish_pin:
                # the recorded span, on the task's own axis (ADR-0476) — never the plan's legs
                ls_w = _retreat_wall(
                    lf_w,
                    _wall_minutes_between(es_wall[tid], ef_wall[tid], cal_t, tod0),
                    cal_t,
                    tod0,
                )
            else:
                ls_w = _plan_retreat(lf_w, plan, tod0)
            if start_needs and min(start_needs) < ls_w:
                ls_w = min(start_needs)
                lf_w = min(lf_w, _plan_finish(ls_w, plan, tod0))
            slack = min(
                _wall_minutes_between(es_wall[tid], ls_w, cal_t, tod0),
                _wall_minutes_between(ef_wall[tid], lf_w, cal_t, tod0),
            )
            exec_slack[tid] = slack
            ls_wall[tid], lf_wall[tid] = ls_w, lf_w
            late_finish[tid] = _wall_to_offset(ps, lf_w, cal)
            late_start[tid] = _wall_to_offset(ps, ls_w, cal)
            ls_need[tid] = (
                _wall_to_offset(ps, ls_w - dt.timedelta(minutes=task.leveling_delay_minutes), cal)
                if task.leveling_delay_minutes > 0
                else late_start[tid]
            )
            continue
        bounds = [
            lf_upper_bound(rel, ls_need[s], late_finish[s], lag, dur_p)
            for s, rel, lag in succs[tid]
        ]
        if tid in lf_cap:
            bounds.append(lf_cap[tid])
        lf = min([backward_target, *bounds])
        late_finish[tid] = lf
        late_start[tid] = lf - dur_p
        ls_need[tid] = late_start[tid]

    def _succ_early_start_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_plan:
            return es_wall[s]
        return _offset_to_wall(ps, early_start[s] - lag, cal, role="start")

    def _succ_early_finish_wall(s: int, lag: int) -> dt.datetime:
        if lag == 0 and s in exec_plan:
            return ef_wall[s]
        return _offset_to_wall(ps, early_finish[s] - lag, cal, role="finish")

    timings: dict[int, TaskTiming] = {}
    for tid in task_ids:
        if tid in exec_plan:
            cal_t = exec_plan[tid].axis
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
                free = _wall_minutes_between(ef_wall[tid], tw, cal_t, tod0)
        else:
            # Total float is the smaller of start slack (LS - ES) and finish slack (LF - EF) —
            # MS Project's own rule. Identical for a contiguous task (EF == ES + duration); they
            # differ only when the ADR-0309 resume floor moved the finish past the logic finish,
            # and then the finish slack is the truth: the start can slip up to LS without moving
            # the floored finish, but the finish itself drives what follows (CPM-01, ADR-0463 —
            # golden EVM2 UID 20 read 10 working days of float and non-critical while MS Project
            # flags it Critical and its floored finish IS the network finish).
            total = min(late_start[tid] - early_start[tid], late_finish[tid] - early_finish[tid])
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
        actual_finish_driven=tuple(sorted(actual_finish_driven)),
        leveling_driven=tuple(sorted(leveling_driven)),
        booking_span_driven=tuple(sorted(booking_span_driven)),
        project_finish_wall=target_wall if required_finish_offset is None else None,
    )
