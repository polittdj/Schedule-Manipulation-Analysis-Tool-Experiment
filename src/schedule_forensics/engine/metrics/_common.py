"""Shared metric primitives — result record, thresholds, populations, helpers.

A :class:`MetricResult` is a single auditable metric: its numerator (``count``),
denominator (``population``), the measured ``value`` compared to a ``threshold`` in a
``direction``, the resulting :class:`CheckStatus`, and the offending UniqueIDs (so
every metric can cite file + UID + task name, §6). Internal durations stay in working
minutes; days conversion happens at the presentation boundary (`model.units`).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from schedule_forensics.engine.cpm import CPMResult, datetime_to_offset
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.model.units import MINUTES_PER_CALENDAR_DAY

#: The DCMA high-float / high-duration tripwire, in working DAYS. The minute value
#: depends on the schedule's calendar — use :func:`forty_four_days_min`.
FORTY_FOUR_DAYS = 44


def duration_days_axis(minutes: int, *, is_elapsed: bool, calendar_minutes_per_day: int) -> float:
    """Duration in DAYS on the right axis: elapsed durations ("edays") are wall-clock
    (1440 min/day, calendars ignored — MS Project semantics); working durations divide
    by the schedule calendar's working minutes per day."""
    per = 1440 if is_elapsed else calendar_minutes_per_day
    return minutes / per if per else 0.0


def forty_four_days_min(schedule: Schedule) -> int:
    """The DCMA "44 working days" tripwire in working minutes, on THIS schedule's
    calendar (44 x 480 for the standard 8-hour day; a 10-hour-day calendar tripwires
    at 44 x 600 — the threshold is defined in days, not minutes)."""
    return FORTY_FOUR_DAYS * schedule.calendar.working_minutes_per_day


class CheckStatus(StrEnum):
    """Outcome of evaluating a metric against its threshold."""

    PASS = "PASS"  # nosec B105  # status enum value, not a secret
    FAIL = "FAIL"
    NOT_APPLICABLE = "NA"  # no threshold, or denominator/input missing (never a fabricated 0)


class Direction(StrEnum):
    """Threshold comparison direction."""

    LE = "<="  # pass when value <= threshold
    GE = ">="  # pass when value >= threshold
    EQ = "=="  # pass when value == threshold


@dataclass(frozen=True)
class MetricResult:
    """One computed metric: numerator/denominator, measured value, threshold, status."""

    metric_id: str
    name: str
    count: int  # numerator
    population: int  # denominator
    value: float  # measured value compared to the threshold (percent / ratio / count)
    unit: str  # "%", "ratio", "count"
    status: CheckStatus
    threshold: float | None = None
    direction: Direction | None = None
    offender_uids: tuple[int, ...] = ()


def non_summary(schedule: Schedule) -> list[Task]:
    """Real schedulable activities — the population for every metric.

    Both **summary rollups** (date aggregations, never real work) and **inactive tasks**
    (``is_active=False``) are excluded. MS Project and Acumen Fuse drop inactive tasks from
    scheduling, rollups, and metric denominators, so a forensic parity tool must too; counting
    them would inflate DCMA / float / EVM populations versus the reference tools (ADR-0128).
    The forensic diff/manipulation layer reads ``schedule.tasks`` directly, so a task being
    *deactivated* between versions is still detected as a change."""
    return [t for t in schedule.tasks if not t.is_summary and t.is_active]


def is_incomplete(task: Task) -> bool:
    """DCMA convention: an activity is incomplete strictly below 100% complete."""
    return task.percent_complete < 100.0


def effective_total_float(task: Task, recomputed_minutes: float) -> float:
    """The total float to score a task on, in working minutes.

    Acumen Fuse reads MS Project's **stored, progress-aware** Total Slack; on a heavily
    progressed schedule that diverges from the engine's recomputed pure-logic CPM float
    (ADR-0010) — which is correct for forensic *path* analysis but makes the DCMA float-based
    counts disagree with Acumen. So when the source file carried a stored Total Slack we score
    on it (matching Acumen); otherwise we fall back to the recomputed float (ADR-0080)."""
    if task.stored_total_float_minutes is not None:
        return float(task.stored_total_float_minutes)
    return recomputed_minutes


def is_effective_critical(task: Task, recomputed_total_float: float) -> bool:
    """Whether a task counts as *Critical* for the Acumen "Critical" metric.

    Prefer MS Project's **stored** Critical flag — Acumen's "Critical" count is the number of
    activities the source tool flagged critical (verified == the golden 41/37 and the operator's
    progressed file). When the source carried no flag, fall back to pure-logic CPM critical,
    excluding completed work (a finished activity is no forward schedule risk — ADR-0010 §3)."""
    if task.stored_is_critical is not None:
        return task.stored_is_critical
    return recomputed_total_float <= 0 and is_incomplete(task)


def effective_critical_incomplete(schedule: Schedule, cpm: CPMResult) -> set[int]:
    """UIDs that count as *Critical* and are not done, on the effective basis.

    The one set the change metrics (Acumen §E SN03/SN04), the manipulation detectors (a
    deleted/deactivated task that WAS critical) and the trend's critical count score on. Each
    kept a private twin on pure-logic ``timing.is_critical`` while every other Critical figure
    went through :func:`is_effective_critical` — so on the golden P2→P5 pair the No-Longer-
    Critical membership carried the documented 96↔99 swap against Fuse. On the effective
    basis it is UID-exact (MAN-01, ADR-0463); a file without stored flags is unchanged."""
    by_id = schedule.tasks_by_id
    return {
        uid
        for uid, timing in cpm.timings.items()
        if is_effective_critical(by_id[uid], timing.total_float)
        and by_id[uid].percent_complete < 100.0
    }


def percent(count: int, population: int) -> float:
    """``100 * count / population`` (0.0 when the population is empty)."""
    return 100.0 * count / population if population else 0.0


def round_half_up(value: float, ndigits: int = 0) -> float:
    """Round half AWAY from zero at ``ndigits`` — the spreadsheet / Fuse convention for a displayed
    figure (QC audit D19; MF-08, ADR-0467). Plain ``round()`` is banker's rounding and sends an
    exact tie to the even digit (``0.125 -> 0.12``, ``12.5 -> 12``), which disagrees with the
    reference tools in the last displayed digit exactly where an analyst compares by eye — and a
    tie is common in a small population (1 of 8). Non-ties are unchanged."""
    quantum = Decimal(1).scaleb(-ndigits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


def acumen_whole_day_float(minutes: float, minutes_per_day: int) -> int:
    """Acumen Fuse's *Total Float* FIELD: the stored slack in WHOLE working days, rounded
    half-to-even — Python's ``round``, deliberately NOT :func:`round_half_up`.

    Measured, not assumed (ADR-0514, R-03): every Total Float that Fuse v8.11.0 displays in its
    detail grids for the operator's Large Test File pair — 3,637 activities across the two
    snapshots — reproduces from the stored slack under this rule, and the 196 exact half-day
    floats of the first snapshot split 118 with an odd integer part (513.5 → 514) and 78 with an
    even one (514.5 → 514, 24.5 → 24): half-away-from-zero misses the 78, truncation the 118
    (and 154.75 → 155). The DCMA "6. High Float" / "7. Negative Float" detail sets are UID-exact
    against the engine on both snapshots under this field, so the classifications READ it: a
    -0.5-day float is 0 (not negative) and a 44.5-day float is 44 (not high). The pins live in
    ``tests/parity/test_fuse_total_float_field_oracle.py`` and ``test_dcma14.py``; R-04's sweep
    of ``round()`` sites toward ``round_half_up`` must leave this helper's callers alone.
    ``minutes_per_day`` is the ACTIVITY's own day (:func:`activity_day_minutes` — R-75,
    ADR-0516), not the project's — the thresholds are defined in days."""
    return round(minutes / minutes_per_day)


def activity_day_minutes(
    schedule: Schedule, task: Task, by_uid: Mapping[int, Calendar] | None = None
) -> int:
    """The working minutes in ``task``'s OWN day — the divisor Acumen Fuse's *Total Float* field
    uses (R-75, ADR-0516): 1440 for an elapsed duration (its slack is wall-clock), the task's own
    calendar's day when it names one the schedule carries, else the project calendar's. NOT the
    crew's calendar and NOT the execution calendar the engine schedules the work on (ADR-0474 /
    ADR-0503) — measured on every Total Float Fuse displays for the operator's Hard_File series
    (771 grid rows over five snapshots): UID 14, on a "24 Hours" task calendar with a 16-hour
    crew, reads -3 for a stored -4,320 minutes (the crew's 960 would read -4); UID 94 on
    "Standard+Sat." (930) reads 2 for 2,190 (the task ∩ crew intersection's 870 would read 3);
    a task with no calendar of its own stays on the project day even when its crew works 24
    hours (24-hour file UID 13: -10 for -4,800, the crew's 1440 would read -3). No elapsed
    activity in the corpus carries a task calendar, so that order is stated, not measured.
    ``by_uid`` is the schedule's calendars keyed by uid, for callers that loop."""
    if task.duration_is_elapsed:
        return MINUTES_PER_CALENDAR_DAY
    if task.calendar_uid is not None:
        calendars = {c.uid: c for c in schedule.calendars} if by_uid is None else by_uid
        own = calendars.get(task.calendar_uid)
        if own is not None:
            return own.working_minutes_per_day
    return schedule.calendar.working_minutes_per_day


def acumen_total_float_field(task: Task, minutes: float, day_minutes: int) -> float:
    """Acumen Fuse's *Total Float* FIELD for one activity, in days of its own day
    (:func:`activity_day_minutes`): an ELAPSED activity's slack RAW in elapsed days — the
    24-hour Hard_File displays UID 146 at -13.333333333333334 for a stored -19,200 minutes where
    UID 14, on a "24 Hours" task calendar with the same -19,200, reads -13 — else the stored
    slack rounded half-to-even to whole days (:func:`acumen_whole_day_float`). The DCMA
    "6. High Float" / "7. Negative Float" classifications read this field (``> 44`` / ``< 0``);
    the elapsed activity's behaviour at a tie (-0.5 < x < 0, 44 < x < 44.5) is UNVERIFIED — no
    elapsed activity in the corpus sits there — so the field is implemented as it is displayed
    (R-75, ADR-0516)."""
    if task.duration_is_elapsed:
        return minutes / day_minutes
    return float(acumen_whole_day_float(minutes, day_minutes))


def to_offset(schedule: Schedule, when: dt.datetime | None) -> int | None:
    """Map a wall-clock date to the working-minute axis, or ``None`` if absent."""
    if when is None:
        return None
    return datetime_to_offset(schedule.project_start, when, schedule.calendar)


def evaluate(value: float, threshold: float | None, direction: Direction | None) -> CheckStatus:
    """PASS/FAIL against a threshold, or NOT_APPLICABLE when no threshold is set."""
    if threshold is None or direction is None:
        return CheckStatus.NOT_APPLICABLE
    if direction is Direction.LE:
        passed = value <= threshold
    elif direction is Direction.GE:
        passed = value >= threshold
    else:  # EQ
        passed = value == threshold
    return CheckStatus.PASS if passed else CheckStatus.FAIL
