"""Calendar model tests."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from schedule_forensics.model.calendar import Calendar


def test_default_is_standard_eight_hour_mon_fri() -> None:
    c = Calendar()
    assert c.name == "Standard"
    assert c.working_minutes_per_day == 480
    assert c.work_weekdays == (0, 1, 2, 3, 4)
    assert c.holidays == ()
    assert c.working_days_per_week == 5


def test_working_minutes_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Calendar(working_minutes_per_day=0)


def test_empty_weekdays_rejected() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        Calendar(work_weekdays=())


def test_out_of_range_weekday_rejected() -> None:
    with pytest.raises(ValidationError, match="must each be in"):
        Calendar(work_weekdays=(0, 7))


def test_negative_weekday_rejected() -> None:
    with pytest.raises(ValidationError, match="must each be in"):
        Calendar(work_weekdays=(-1, 0))


def test_duplicate_weekday_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicates"):
        Calendar(work_weekdays=(0, 0, 1))


def test_is_working_day() -> None:
    c = Calendar()  # Mon-Fri, no holidays
    assert c.is_working_day(dt.date(2026, 6, 1))  # Monday
    assert not c.is_working_day(dt.date(2026, 6, 6))  # Saturday
    assert not c.is_working_day(dt.date(2026, 6, 7))  # Sunday


def test_holiday_is_not_a_working_day() -> None:
    holiday = dt.date(2026, 7, 3)  # a Friday
    c = Calendar(holidays=(holiday,))
    assert holiday.weekday() == 4  # would otherwise be a working day
    assert not c.is_working_day(holiday)
    assert c.is_working_day(dt.date(2026, 7, 2))  # the Thursday before


def test_six_day_week() -> None:
    c = Calendar(work_weekdays=(0, 1, 2, 3, 4, 5))
    assert c.working_days_per_week == 6
    assert c.is_working_day(dt.date(2026, 6, 6))  # Saturday now working
