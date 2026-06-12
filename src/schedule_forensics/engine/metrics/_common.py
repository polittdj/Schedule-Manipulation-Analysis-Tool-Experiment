"""Shared metric primitives — result record, thresholds, populations, helpers.

A :class:`MetricResult` is a single auditable metric: its numerator (``count``),
denominator (``population``), the measured ``value`` compared to a ``threshold`` in a
``direction``, the resulting :class:`CheckStatus`, and the offending UniqueIDs (so
every metric can cite file + UID + task name, §6). Internal durations stay in working
minutes; days conversion happens at the presentation boundary (`model.units`).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum

from schedule_forensics.engine.cpm import datetime_to_offset
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

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
    """Real activities (summary rollups are excluded from every metric population)."""
    return [t for t in schedule.tasks if not t.is_summary]


def is_incomplete(task: Task) -> bool:
    """DCMA convention: an activity is incomplete strictly below 100% complete."""
    return task.percent_complete < 100.0


def percent(count: int, population: int) -> float:
    """``100 * count / population`` (0.0 when the population is empty)."""
    return 100.0 * count / population if population else 0.0


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
