"""CPM working-time date math (E6/E7) must match the old day-by-day loops EXACTLY.

CPM is the trust root: a one-day drift here would move every reported date, slack and slip.
The verbatim pre-optimization implementations are kept below as the reference oracle, and the
optimized ``_count_working_days`` / ``_advance_working_days`` / ``offset_to_datetime`` are swept
over thousands of randomized calendars (random work-week shapes, 0-30 holidays), spans and
offsets. Any divergence fails the gate."""

from __future__ import annotations

import datetime as dt
import random

from schedule_forensics.engine.cpm import (
    _advance_working_days,
    _count_working_days,
    offset_to_datetime,
)
from schedule_forensics.model.calendar import Calendar

# --- verbatim pre-optimization reference implementations (the oracle) ---------------------


def _ref_next_working_day(day: dt.datetime, calendar: Calendar) -> dt.datetime:
    nxt = day + dt.timedelta(days=1)
    while nxt.date().weekday() not in calendar.work_weekdays or nxt.date() in calendar.holidays:
        nxt += dt.timedelta(days=1)
    return nxt


def _ref_count_working_days(calendar: Calendar, d0: dt.date, d1: dt.date) -> int:
    count = 0
    cur = d0
    while cur < d1:
        if cur.weekday() in calendar.work_weekdays and cur not in calendar.holidays:
            count += 1
        cur += dt.timedelta(days=1)
    return count


def _ref_offset_to_datetime(start: dt.datetime, minutes: int, calendar: Calendar) -> dt.datetime:
    per_day = calendar.working_minutes_per_day
    day = start
    while day.date().weekday() not in calendar.work_weekdays or day.date() in calendar.holidays:
        day = _ref_next_working_day(day, calendar)
    remaining = minutes
    while remaining > per_day:
        remaining -= per_day
        day = _ref_next_working_day(day, calendar)
    return day + dt.timedelta(minutes=remaining)


# --- randomized fixtures ------------------------------------------------------------------


def _random_calendar(rng: random.Random) -> Calendar:
    weekdays = tuple(sorted(rng.sample(range(7), rng.randint(1, 7))))
    per_day = rng.choice([240, 480, 600, 720, 960])
    base = dt.date(2025, 1, 1)
    holidays = tuple(
        {base + dt.timedelta(days=rng.randint(-1500, 1500)) for _ in range(rng.randint(0, 30))}
    )
    return Calendar(
        name="r", working_minutes_per_day=per_day, work_weekdays=weekdays, holidays=holidays
    )


def test_count_working_days_matches_the_day_by_day_oracle() -> None:
    rng = random.Random(20260610)
    base = dt.date(2025, 6, 1)
    for _ in range(2000):
        cal = _random_calendar(rng)
        d0 = base + dt.timedelta(days=rng.randint(-1500, 1500))
        d1 = d0 + dt.timedelta(days=rng.randint(0, 1500))  # contract: d0 <= d1
        assert _count_working_days(cal, d0, d1) == _ref_count_working_days(cal, d0, d1)


def test_advance_working_days_matches_repeated_next_working_day() -> None:
    rng = random.Random(424242)
    base = dt.date(2025, 3, 3)
    for _ in range(1500):
        cal = _random_calendar(rng)
        day = base + dt.timedelta(days=rng.randint(-1000, 1000))
        while day.weekday() not in cal.work_weekdays or day in cal.holidays:
            day += dt.timedelta(days=1)  # align to a working day, as the callers do
        k = rng.randint(0, 800)
        ref = dt.datetime.combine(day, dt.time(8, 0))
        for _ in range(k):
            ref = _ref_next_working_day(ref, cal)
        assert _advance_working_days(day, k, cal) == ref.date()


def test_offset_to_datetime_matches_the_day_by_day_oracle() -> None:
    rng = random.Random(13579)
    base = dt.datetime(2025, 6, 2, 8, 0)
    for _ in range(2000):
        cal = _random_calendar(rng)
        start = base + dt.timedelta(days=rng.randint(-1000, 1000))
        minutes = rng.randint(0, 1_000_000)
        assert offset_to_datetime(start, minutes, cal) == _ref_offset_to_datetime(
            start, minutes, cal
        )
