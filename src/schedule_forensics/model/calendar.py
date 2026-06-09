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

    name: str = "Standard"
    working_minutes_per_day: int = Field(default=MINUTES_PER_DAY, gt=0)
    work_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)  # date.weekday(): Mon=0 .. Sun=6
    holidays: tuple[dt.date, ...] = ()

    @model_validator(mode="after")
    def _validate_weekdays(self) -> Self:
        if not self.work_weekdays:
            raise ValueError("work_weekdays must not be empty")
        if any(d < 0 or d > 6 for d in self.work_weekdays):
            raise ValueError("work_weekdays must each be in 0..6 (Mon..Sun)")
        if len(set(self.work_weekdays)) != len(self.work_weekdays):
            raise ValueError("work_weekdays must not contain duplicates")
        return self

    @property
    def working_days_per_week(self) -> int:
        """Number of working weekdays (5 for the standard Mon-Fri calendar)."""
        return len(self.work_weekdays)

    def is_working_day(self, day: dt.date) -> bool:
        """True iff ``day`` is a working weekday and not a holiday."""
        return day.weekday() in self.work_weekdays and day not in self.holidays
