"""The offset-conversion precondition, enforced at the importer boundary (ADR-0312).

``engine.cpm.offset_to_datetime`` lays each working day's minutes out contiguously from
``project_start``'s time-of-day, so the model only holds while a full working day fits inside
the calendar day it starts in. ADR-0310 §5 declared the supported domain
(``start_time_of_day + working_minutes_per_day <= 1440``) and required an input outside it to be
normalised or rejected **at import** — not merely warned about, because a warning leaves the
inverse property broken internally while the page looks fine.

These tests assert the *property* (a rendered date is a working date; the offset ↔ datetime
round-trip is exact), not just that a helper was called — the property is what CC-01 is about,
and a presence check would pass on a helper that did nothing.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

import pytest

from schedule_forensics.engine.cpm import datetime_to_offset, offset_to_datetime
from schedule_forensics.importers._common import (
    ImporterError,
    anchored_project_start,
    modelled_shift_start,
)
from schedule_forensics.importers.json_schedule import parse_json_text, to_json_text
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.importers.xer import parse_xer
from schedule_forensics.model import Calendar, Schedule
from schedule_forensics.model.units import MINUTES_PER_CALENDAR_DAY

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"

#: A Monday, so a sweep long enough to cross a weekend actually does.
_MONDAY = dt.datetime(2026, 1, 5, 8, 0)

#: Wide enough to cross two weekends at every day length tested below.
_SWEEP = range(0, MINUTES_PER_CALENDAR_DAY * 12, 37)


def _minute_of_day(when: dt.datetime) -> int:
    return when.hour * 60 + when.minute


def _non_working_renders(start: dt.datetime, cal: Calendar) -> list[int]:
    """Offsets whose rendered instant falls on a date the calendar does not work."""
    return [k for k in _SWEEP if not cal.is_working_day(offset_to_datetime(start, k, cal).date())]


def _inverse_breaks(start: dt.datetime, cal: Calendar) -> list[int]:
    """Offsets for which ``datetime_to_offset(offset_to_datetime(k)) != k``."""
    return [
        k for k in _SWEEP if datetime_to_offset(start, offset_to_datetime(start, k, cal), cal) != k
    ]


# --- the domain itself -------------------------------------------------------------


@pytest.mark.parametrize("per_day", [480, 600, 720, 1200, 1440])
@pytest.mark.parametrize("start_tod", [0, 360, 420, 480, 720, 960, 1020, 1380])
def test_the_declared_domain_decides_verbatim_versus_normalised(
    per_day: int, start_tod: int
) -> None:
    """The full ``per_day`` x time-of-day grid Phase 3's exit criterion names. In-domain inputs
    are returned untouched with no note; out-of-domain inputs come back in-domain with one."""
    cal = Calendar(working_minutes_per_day=per_day)
    start = _MONDAY.replace(hour=start_tod // 60, minute=start_tod % 60)
    anchored, note = anchored_project_start(start, cal, source="test")
    if start_tod + per_day <= MINUTES_PER_CALENDAR_DAY:
        assert (anchored, note) == (start, None)
    else:
        assert note is not None
        assert _minute_of_day(anchored) + per_day <= MINUTES_PER_CALENDAR_DAY
        assert anchored.date() == start.date()


def test_the_domain_boundary_is_inclusive() -> None:
    """``start_tod + per_day == 1440`` is inside the domain ADR-0310 §5 declared."""
    cal = Calendar(working_minutes_per_day=480)
    start = _MONDAY.replace(hour=16, minute=0)
    assert anchored_project_start(start, cal, source="test") == (start, None)


def test_modelled_shift_start_reads_the_declared_segments() -> None:
    lunch = Calendar(working_minutes_per_day=480, day_segments=((480, 720), (780, 1020)))
    assert modelled_shift_start(lunch) == 480
    early = Calendar(working_minutes_per_day=600, day_segments=((420, 720), (750, 1050)))
    assert modelled_shift_start(early) == 420
    # no segments == the legacy single contiguous block, which Calendar.intraday_worked_minutes
    # already models as running from midnight; 0 is read from that contract, not invented
    assert modelled_shift_start(Calendar(working_minutes_per_day=1440)) == 0
    assert Calendar(working_minutes_per_day=1440).intraday_worked_minutes(1) == 1


# --- normalisation restores the property, which is the whole point -------------------


def test_a_continuous_operations_start_is_normalised_to_the_shift_start() -> None:
    cal = Calendar(name="24 Hours", working_minutes_per_day=MINUTES_PER_CALENDAR_DAY)
    normalised, note = anchored_project_start(_MONDAY, cal, source="test")
    assert normalised == dt.datetime(2026, 1, 5, 0, 0)
    assert note is not None and "08:00" in note and "00:00" in note


def test_normalisation_restores_the_working_date_and_inverse_properties() -> None:
    """The measured before/after — both invariants are broken outside the domain and whole
    inside it. This is the executable form of ADR-0310's claim about ``cpm.py:295``."""
    cal = Calendar(name="24 Hours", working_minutes_per_day=MINUTES_PER_CALENDAR_DAY)
    assert _non_working_renders(_MONDAY, cal), "expected the un-normalised start to be broken"
    assert _inverse_breaks(_MONDAY, cal), "expected the un-normalised start to break the inverse"

    normalised, _ = anchored_project_start(_MONDAY, cal, source="test")
    assert _non_working_renders(normalised, cal) == []
    assert _inverse_breaks(normalised, cal) == []


def test_normalisation_keeps_every_activity_on_the_same_working_day() -> None:
    """Only the time-of-day term moves: the whole-working-day count is a function of the offset
    and the calendar, never of the anchor's time of day. So the note's promise is checkable."""
    cal = Calendar(name="24 Hours", working_minutes_per_day=MINUTES_PER_CALENDAR_DAY)
    normalised, _ = anchored_project_start(_MONDAY, cal, source="test")
    for k in _SWEEP:
        before = offset_to_datetime(_MONDAY, k, cal)
        after = offset_to_datetime(normalised, k, cal)
        # same working day, and the un-normalised render is never EARLIER than the corrected one
        assert 0 <= (before - after).total_seconds() <= MINUTES_PER_CALENDAR_DAY * 60


def test_normalisation_is_idempotent() -> None:
    cal = Calendar(name="24 Hours", working_minutes_per_day=MINUTES_PER_CALENDAR_DAY)
    once, note = anchored_project_start(_MONDAY, cal, source="test")
    assert note is not None
    assert anchored_project_start(once, cal, source="test") == (once, None)


def test_a_calendar_with_no_schedulable_anchor_is_rejected() -> None:
    """A late shift start that cannot fit its own working day has no in-domain anchor at all,
    so the file is rejected rather than loaded with dates on non-working days."""
    cal = Calendar(name="Night shift", working_minutes_per_day=480, day_segments=((1320, 1440),))
    with pytest.raises(ImporterError) as exc:
        anchored_project_start(_MONDAY.replace(hour=22), cal, source="MSPDI")
    assert "Night shift" in str(exc.value) and "24-hour day" in str(exc.value)


def test_a_working_day_longer_than_a_calendar_day_is_rejected() -> None:
    cal = Calendar(name="Impossible", working_minutes_per_day=1500)
    with pytest.raises(ImporterError):
        anchored_project_start(_MONDAY, cal, source="XER")


# --- the committed corpus does not move ---------------------------------------------


def _committed_schedules() -> list[tuple[str, Schedule]]:
    out: list[tuple[str, Schedule]] = []
    for path in sorted(FIXTURES.rglob("*.xml")):
        head = path.read_text(encoding="utf-8", errors="ignore")[:400]
        if "<Project" in head:
            out.append((path.name, parse_mspdi(path)))
    for path in sorted(FIXTURES.rglob("*.xer")):
        out.append((path.name, parse_xer(str(path))))
    return out


def test_every_committed_schedule_is_already_inside_the_supported_domain() -> None:
    """The blast-radius bound: nothing in the corpus is normalised, so no committed figure can
    move. If this ever fails, a fixture has entered the class this ADR changes and its expected
    values must be re-derived rather than regenerated."""
    schedules = _committed_schedules()
    assert len(schedules) >= 12, "corpus discovery broke; the guard would pass vacuously"
    for name, sch in schedules:
        tod = _minute_of_day(sch.project_start)
        per_day = sch.calendar.working_minutes_per_day
        assert tod + per_day <= MINUTES_PER_CALENDAR_DAY, name
        assert sch.import_notes == (), name


# --- the importers carry it, and the note survives a save/reopen ---------------------


_MSPDI_24H = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Name>Continuous Ops</Name>
  <StartDate>2026-01-05T08:00:00</StartDate>
  <CalendarUID>1</CalendarUID>
  <Calendars><Calendar>
    <UID>1</UID><Name>24 Hours</Name><IsBaseCalendar>1</IsBaseCalendar>
    <WeekDays>{weekdays}</WeekDays>
  </Calendar></Calendars>
  <Tasks><Task>
    <UID>1</UID><ID>1</ID><Name>Continuous run</Name><OutlineLevel>1</OutlineLevel>
    <Duration>PT48H0M0S</Duration><Milestone>0</Milestone><Summary>0</Summary>
  </Task></Tasks>
</Project>
"""
_WORKING_DAY = (
    "<WeekDay><DayType>{d}</DayType><DayWorking>1</DayWorking>"
    "<WorkingTimes><WorkingTime><FromTime>00:00:00</FromTime>"
    "<ToTime>00:00:00</ToTime></WorkingTime></WorkingTimes></WeekDay>"
)


def _mspdi_24h() -> str:
    # MSPDI DayType 1..7 is Sunday..Saturday; 2..6 are Mon..Fri
    return _MSPDI_24H.format(weekdays="".join(_WORKING_DAY.format(d=d) for d in range(2, 7)))


def test_the_mspdi_importer_normalises_and_records_the_note() -> None:
    sch = parse_mspdi_text(_mspdi_24h(), source_file="continuous.xml")
    assert sch.calendar.working_minutes_per_day == MINUTES_PER_CALENDAR_DAY
    assert sch.project_start == dt.datetime(2026, 1, 5, 0, 0)
    assert len(sch.import_notes) == 1
    assert "24 Hours" in sch.import_notes[0]


def test_the_note_round_trips_through_the_json_save_format() -> None:
    sch = parse_mspdi_text(_mspdi_24h(), source_file="continuous.xml")
    reopened = parse_json_text(to_json_text(sch))
    assert reopened.project_start == sch.project_start
    assert reopened.import_notes == sch.import_notes  # not duplicated by the second pass


def test_the_note_never_names_the_file_or_an_activity() -> None:
    """Same CUI contract as ImporterError's message: it says what was interpreted, never what
    the file contains."""
    sch = parse_mspdi_text(_mspdi_24h(), source_file="continuous.xml")
    note = sch.import_notes[0]
    assert "continuous.xml" not in note
    assert "Continuous run" not in note


def test_a_rejected_json_schedule_is_not_laundered_through_the_strict_fallback() -> None:
    """``parse_json_text`` falls back to ``Schedule.model_validate`` when the friendly parse
    raises a plain ValueError — but an :class:`ImporterError` is re-raised first. Without that,
    an unschedulable file would bypass the precondition through the fallback."""
    doc = json.dumps(
        {
            "name": "unschedulable",
            "project_start": "2026-01-05T08:00:00",
            "calendar": {"name": "Impossible", "working_minutes_per_day": 1500},
            "tasks": [{"unique_id": 1, "name": "A", "duration_minutes": 480}],
        }
    )
    with pytest.raises(ImporterError) as exc:
        parse_json_text(doc)
    assert "Impossible" in str(exc.value)
