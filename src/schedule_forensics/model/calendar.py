"""Working-time calendar — converts between wall-clock dates and working minutes.

This slice models a single contiguous working block of ``working_minutes_per_day`` on
each working weekday, minus ``holidays``. Multi-shift calendars, lunch breaks, and
per-task calendars are deferred (the engine's CPM, M5, consumes this). The default is
the standard 8-hour, Monday-Friday calendar (``working_minutes_per_day == 480``), which
is also the canonical duration axis (see :mod:`schedule_forensics.model.units`).
"""

from __future__ import annotations

import datetime as dt
from typing import Self

from pydantic import Field, model_validator

from schedule_forensics.model._base import StrictFrozenModel
from schedule_forensics.model.units import MINUTES_PER_DAY


class Calendar(StrictFrozenModel):
    """A working-time definition for offset ↔ wall-clock conversion."""

    #: Source CalendarUID (MSPDI ``<Calendar><UID>``); 0 for the synthesized default. Lets a
    #: per-task calendar be resolved from ``Schedule.calendars`` (driving-slack parity, ADR-0118).
    uid: int = 0
    name: str = "Standard"
    working_minutes_per_day: int = Field(default=MINUTES_PER_DAY, gt=0)
    work_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)  # date.weekday(): Mon=0 .. Sun=6
    holidays: tuple[dt.date, ...] = ()
    #: Extra WORKING dates (MSPDI ``DayWorking=1`` exceptions): normally-non-working days
    #: (a weekend or a holiday) that this calendar marks as working — e.g. a worked Saturday or
    #: a holiday recovered as a work day. Honored by the driving-slack parity path (ADR-0118).
    working_days: tuple[dt.date, ...] = ()
    #: Intraday working blocks as ``(start, end)`` minutes-from-midnight, e.g.
    #: ``((480, 720), (780, 1020))`` for 08:00-12:00 + 13:00-17:00 (a 12:00-13:00 lunch).
    #: Empty = the legacy single contiguous block (no intraday gap). Populated by the MSPDI
    #: importer from the calendar's real working times; consumed by the SSI driving-slack
    #: parity path so an afternoon finish is not over-counted by the lunch hour (ADR-0117).
    day_segments: tuple[tuple[int, int], ...] = ()

    @model_validator(mode="after")
    def _validate_weekdays(self) -> Self:
        if not self.work_weekdays:
            raise ValueError("work_weekdays must not be empty")
        if any(d < 0 or d > 6 for d in self.work_weekdays):
            raise ValueError("work_weekdays must each be in 0..6 (Mon..Sun)")
        if len(set(self.work_weekdays)) != len(self.work_weekdays):
            raise ValueError("work_weekdays must not contain duplicates")
        if any(not (0 <= s < e <= 1440) for s, e in self.day_segments):
            raise ValueError("each day segment must be 0 <= start < end <= 1440 minutes")
        return self

    def intraday_worked_minutes(self, minute_of_day: int) -> int:
        """Working minutes elapsed from day-start to ``minute_of_day``, honoring lunch breaks.

        Uses :attr:`day_segments` when defined (so 16:00 with a 12:00-13:00 lunch is 420,
        not 480); falls back to a single contiguous block of ``working_minutes_per_day`` from
        the first segment / midnight when no segments are declared.
        """
        if not self.day_segments:
            return max(0, min(minute_of_day, self.working_minutes_per_day))
        worked = 0
        for start, end in self.day_segments:
            if minute_of_day >= end:
                worked += end - start
            elif minute_of_day > start:
                worked += minute_of_day - start
        return worked

    @property
    def working_days_per_week(self) -> int:
        """Number of working weekdays (5 for the standard Mon-Fri calendar)."""
        return len(self.work_weekdays)

    def is_working_day(self, day: dt.date) -> bool:
        """True iff ``day`` is a working weekday and not a holiday."""
        return day.weekday() in self.work_weekdays and day not in self.holidays

    def is_worked(self, day: dt.date) -> bool:
        """Like :meth:`is_working_day` but also counts ``working_days`` exceptions (a worked
        weekend / a holiday recovered as a work day). Used only by the driving-slack parity path
        so the broader engine's single-calendar model (ADR-0028) is unchanged."""
        return day in self.working_days or self.is_working_day(day)

    def extra_working_days_in(self, start: dt.date, end: dt.date) -> int:
        """Count of ``working_days`` exceptions in ``[start, end)`` that a plain weekday-minus-
        holiday count would miss (a worked weekend, or a holiday recovered as a work day)."""
        return sum(
            1
            for d in self.working_days
            if start <= d < end and (d.weekday() not in self.work_weekdays or d in self.holidays)
        )
