"""The day-boundary spelling of a working-minute offset (ADR-0348, CC-01's rendering half).

The working axis is contiguous, so an offset that is an exact multiple of a working day names
one instant with two valid wall-clock spellings: the END of working day ``k-1`` and the START
of working day ``k``. ``offset_to_datetime`` always chooses the first. That is right for a
finish and one working day early for a start.

These tests pin all three rules the fix rests on:

* ``offset_to_start_datetime`` chooses the start spelling at the boundary and is *identical*
  to ``offset_to_datetime`` away from it;
* ``span_start_datetime`` keeps the end-of-day spelling for a **zero-duration** instant, which
  is both MS Project's own convention and what stops a milestone rendering its start after its
  finish;
* ``_elapsed_finish_offset`` — the one place the spelling is arithmetic and not display —
  measures elapsed wall-clock minutes from the true start instant.

The corpus oracle (MS Project's own stored dates) is exercised in
``tests/engine/test_day_boundary_corpus.py``.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import (
    _elapsed_finish_offset,
    datetime_to_offset,
    offset_to_datetime,
    offset_to_start_datetime,
    span_start_datetime,
)
from schedule_forensics.model.calendar import Calendar

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday 08:00
CAL = Calendar()  # standard 8h Mon-Fri, 480 working minutes per day


def test_a_day_boundary_offset_spells_the_start_of_the_next_working_day() -> None:
    """480 == the end of Monday == the start of Tuesday; the start role picks Tuesday."""
    assert offset_to_datetime(MON, 480, CAL) == dt.datetime(2025, 1, 6, 16, 0)  # Mon 16:00
    assert offset_to_start_datetime(MON, 480, CAL) == dt.datetime(2025, 1, 7, 8, 0)  # Tue 08:00
    # the two spellings are the same point on the working axis
    assert datetime_to_offset(MON, offset_to_start_datetime(MON, 480, CAL), CAL) == 480


def test_the_start_spelling_crosses_a_weekend_rather_than_landing_on_friday() -> None:
    """Friday's end and Monday's start are one instant; a start reads Monday."""
    fri_end = offset_to_datetime(MON, 480 * 5, CAL)
    mon_start = offset_to_start_datetime(MON, 480 * 5, CAL)
    assert fri_end == dt.datetime(2025, 1, 10, 16, 0)  # Fri 16:00
    assert mon_start == dt.datetime(2025, 1, 13, 8, 0)  # Mon 08:00 — three calendar days on
    assert (mon_start.date() - fri_end.date()).days == 3


def test_the_start_spelling_skips_a_holiday() -> None:
    cal = Calendar(holidays=(dt.date(2025, 1, 7),))  # the Tuesday
    assert offset_to_start_datetime(MON, 480, cal) == dt.datetime(2025, 1, 8, 8, 0)  # Wed


@pytest.mark.parametrize("minutes", [1, 120, 479, 481, 960 + 1, 1439, 2401])
def test_away_from_the_boundary_the_two_spellings_are_identical(minutes: int) -> None:
    """Only ``remainder == 0`` differs — everything else must be byte-identical."""
    assert offset_to_start_datetime(MON, minutes, CAL) == offset_to_datetime(MON, minutes, CAL)


def test_offset_zero_is_the_project_start_under_both_spellings() -> None:
    assert offset_to_start_datetime(MON, 0, CAL) == offset_to_datetime(MON, 0, CAL) == MON


def test_a_negative_offset_is_refused() -> None:
    with pytest.raises(ValueError, match="must be >= 0"):
        offset_to_start_datetime(MON, -1, CAL)


def test_a_one_day_task_spans_exactly_one_day() -> None:
    """The visible consequence: a 1-day bar drawn across 2 days was the defect."""
    start = span_start_datetime(MON, 480, 960, CAL).date()
    finish = offset_to_datetime(MON, 960, CAL).date()
    assert start == finish == dt.date(2025, 1, 7)  # the Tuesday it is worked


def test_a_zero_duration_instant_keeps_the_end_of_day_spelling() -> None:
    """A milestone has no beginning distinct from itself; MS Project spells it end-of-day."""
    assert span_start_datetime(MON, 480, 480, CAL) == dt.datetime(2025, 1, 6, 16, 0)


def test_a_milestone_never_renders_its_start_after_its_finish() -> None:
    for k in range(0, 11):
        offset = 480 * k
        start = span_start_datetime(MON, offset, offset, CAL)
        finish = offset_to_datetime(MON, offset, CAL)
        assert start <= finish, f"inverted span at offset {offset}"


@pytest.mark.parametrize(
    ("start_offset", "elapsed_minutes"),
    [(480, 120), (480, 240), (480, 480), (480, 720), (960, 120), (960, 240), (960, 480)],
)
def test_an_elapsed_finish_is_measured_from_the_true_start_instant(
    start_offset: int, elapsed_minutes: int
) -> None:
    """Elapsed durations ignore calendars: the finish is start + N *clock* minutes.

    Reading a boundary start as the previous day's 16:00 moved the clock origin by the whole
    non-working gap, landing every non-whole-day elapsed duration short by up to a working day.
    """
    true_start = offset_to_start_datetime(MON, start_offset, CAL)
    expected = datetime_to_offset(MON, true_start + dt.timedelta(minutes=elapsed_minutes), CAL)
    assert _elapsed_finish_offset(MON, CAL, start_offset, elapsed_minutes) == expected


def test_a_whole_elapsed_day_was_already_correct_and_stays_correct() -> None:
    """Whole 1440-minute durations agreed by coincidence — the fix must not move them."""
    for start_offset in (0, 480, 960, 1440):
        for whole in (1440, 2880, 4320):
            got = _elapsed_finish_offset(MON, CAL, start_offset, whole)
            true_start = offset_to_start_datetime(MON, start_offset, CAL)
            want = datetime_to_offset(MON, true_start + dt.timedelta(minutes=whole), CAL)
            assert got == want
