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


def test_day_segments_and_lunch_aware_intraday() -> None:
    cal = Calendar(day_segments=((480, 720), (780, 1020)))  # 08:00-12:00 + 13:00-17:00
    assert cal.intraday_worked_minutes(600) == 120  # 10:00 -> 2h into the morning
    assert cal.intraday_worked_minutes(780) == 240  # 13:00 -> lunch over, morning only
    assert cal.intraday_worked_minutes(960) == 420  # 16:00 -> 4h + 3h (no lunch double-count)
    assert cal.intraday_worked_minutes(1020) == 480  # 17:00 -> full day
    # no segments: the legacy single contiguous block from day start
    assert Calendar().intraday_worked_minutes(600) == 480  # clamped to working_minutes_per_day
    assert Calendar().intraday_worked_minutes(120) == 120


def test_invalid_day_segment_rejected() -> None:
    with pytest.raises(ValidationError):
        Calendar(day_segments=((720, 480),))  # start >= end


def test_is_worked_and_extra_working_days() -> None:
    sat = dt.date(2025, 1, 11)  # a Saturday
    cal = Calendar(working_days=(sat,))
    assert cal.is_worked(sat) is True  # worked-exception day
    assert cal.is_working_day(sat) is False  # plain rule still says non-working
    assert cal.is_worked(dt.date(2025, 1, 13)) is True  # ordinary Monday
    # only the worked weekend/holiday counts as "extra" over a weekday-minus-holiday tally
    assert cal.extra_working_days_in(dt.date(2025, 1, 6), dt.date(2025, 1, 20)) == 1
    assert cal.extra_working_days_in(dt.date(2025, 1, 13), dt.date(2025, 1, 20)) == 0
