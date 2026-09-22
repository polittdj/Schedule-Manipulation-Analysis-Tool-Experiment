"""The project axis IS working minutes, and BOTH directions must read it that way (R-77, ADR-0523).

``datetime_to_offset`` and ``offset_to_datetime`` were a CONTIGUOUS pair: the intraday term went in
as ``clamp(target_tod - start_tod, 0, minutes_per_day)`` and came back out as
``day_start_tod + intraday``. On a calendar that declares a lunch gap (08:00-12:00 + 13:00-17:00,
480 min/day) that bills the gap as worked -- 13:00 read as minute 300 where only 240 were worked --
and, worse, the round trip was LOSSY: a 17:00 finish saturated the clamp at offset 480 and expanded
back to 16:00. Measured over the 44-file corpus, 15,224 of 22,105 rendered finishes sat exactly one
gap early for that reason alone.

ADR-0322 refused a segment-aware read at any ONE site, because projecting wall->int segment-aware
while constraints, stored pins and the rendering still measured contiguously made a single instant
carry two offsets. The remedy is not to keep the asymmetry but to remove it: the PAIR moves
together, so there is one ruler again.

Two rules this file exists to hold, both of which the naive change got wrong:

* the segment-aware arithmetic fires ONLY when the source file DECLARED segments.
  ``_Ruler.segments`` re-anchors its fallback block to midnight whenever
  ``day_start_tod + minutes_per_day > 1440``, so routing an undeclared calendar through it
  silently re-bases every late-starting schedule;
* an offset landing exactly on an internal block boundary has TWO valid spellings -- the end
  of block i and the start of block i+1 are both "240 minutes worked". A FINISH takes the
  earlier, a START the later. This is ADR-0348's day-boundary rule one segment down.

Measured against MS Project's own stored slack over the 44-file corpus: stored Total Slack exact
10,610 -> 11,041 of 12,680, stored Free Slack exact 3,004 -> 3,094 of 3,315 with high 198 -> 134 and
low 113 -> 87. Rendered instants exact 22,453 -> 41,950 of 44,210. Three instants regress, all of
them ``Hard_File_updated4``'s UID 305 across that file's three copies: a completed milestone whose
13:00 instant MS Project spells with the LATER form even though it is a finish. No rule in the file
separates the two spellings -- 81 milestones spell a finish earlier and 3 spell it later, 306
non-milestones spell a start later and 81 milestones spell it earlier -- so the dominant convention
is taken per role and those three are a named, unfixed residual.
"""

from __future__ import annotations

import datetime as dt
import gzip
import pathlib
import xml.etree.ElementTree as ET

from schedule_forensics.engine.cpm import (
    compute_cpm,
    datetime_to_offset,
    offset_to_datetime,
    offset_to_start_datetime,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar

#: 08:00-12:00 + 13:00-17:00 with a 12:00-13:00 lunch -- the MS Project Standard day.
GAPPED = Calendar(day_segments=((480, 720), (780, 1020)))
#: the same 480-minute day with NO declared segments (the legacy single contiguous block).
PLAIN = Calendar()
MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday at the working-day start
NS = "{http://schemas.microsoft.com/project}"
_GOLDEN_ROOT = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "golden"
#: every committed MSPDI golden -- ELEVEN of the fifteen are gzipped, so a plain ``*.xml``
#: glob sees four and looks exhaustive (the population control is not vacuous).
_GOLDENS = tuple(
    sorted(list(_GOLDEN_ROOT.rglob("*.mspdi.xml")) + list(_GOLDEN_ROOT.rglob("*.mspdi.xml.gz")))
)


def _golden_text(path: pathlib.Path) -> str:
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode("utf-8")
    return path.read_text(encoding="utf-8")


# --- the projection: a wall instant reads the minutes actually WORKED ---------------------------


def test_an_afternoon_instant_projects_to_the_minutes_actually_worked() -> None:
    """13:00 on a 08-12 / 13-17 day is 240 worked minutes, not 300: the lunch hour is not work."""
    assert datetime_to_offset(MON, dt.datetime(2025, 1, 6, 13, 0), GAPPED) == 240
    assert datetime_to_offset(MON, dt.datetime(2025, 1, 6, 15, 0), GAPPED) == 360
    assert datetime_to_offset(MON, dt.datetime(2025, 1, 6, 17, 0), GAPPED) == 480


def test_a_morning_instant_is_untouched() -> None:
    """A CONTROL: before the gap the two rulers agree exactly, so nothing may move here."""
    assert datetime_to_offset(MON, dt.datetime(2025, 1, 6, 10, 0), GAPPED) == 120
    assert datetime_to_offset(MON, dt.datetime(2025, 1, 6, 12, 0), GAPPED) == 240


# --- the expansion: an offset spells MS Project's own instant -----------------------------------


def test_an_end_of_day_offset_expands_to_the_calendars_own_day_end() -> None:
    """A full day's offset is 17:00 -- the instant MS Project stores -- and never 16:00."""
    assert offset_to_datetime(MON, 480, GAPPED) == dt.datetime(2025, 1, 6, 17, 0)
    assert offset_to_datetime(MON, 960, GAPPED) == dt.datetime(2025, 1, 7, 17, 0)


def test_the_pair_is_a_true_inverse_away_from_a_block_boundary() -> None:
    """Projection then expansion returns the SAME instant. The contiguous pair was lossy by
    exactly the gap width at every day END -- a 17:00 finish saturated the clamp at 480 and came
    back as 16:00 -- which is where 15,224 of the corpus's 22,105 rendered finishes went.

    A BLOCK BOUNDARY is deliberately excluded: 12:00 and 13:00 are the same 240 worked minutes,
    so no single spelling can be the inverse of both. That ambiguity is the subject of
    :func:`test_a_block_boundary_spells_a_start_and_a_finish_differently`, not a defect here."""
    for hour, minute in ((8, 0), (9, 30), (11, 59), (14, 45), (16, 30), (17, 0)):
        inst = dt.datetime(2025, 1, 6, hour, minute)
        back = offset_to_datetime(MON, datetime_to_offset(MON, inst, GAPPED), GAPPED)
        assert back == inst, (inst, back)


def test_an_offset_survives_a_trip_through_the_wall_and_back() -> None:
    """A CONTROL: offset -> wall -> offset is the identity on BOTH rulers, because each is
    self-consistent. Only the wall round trip above discriminates them, so this must stay green
    on the pristine engine -- a test that goes red here is testing the wrong direction."""
    for off in (0, 1, 120, 239, 240, 345, 480, 481, 960, 1440):
        assert datetime_to_offset(MON, offset_to_datetime(MON, off, GAPPED), GAPPED) == off, off


# --- the internal block boundary carries two spellings ------------------------------------------


def test_a_block_boundary_spells_a_start_and_a_finish_differently() -> None:
    """240 worked minutes is BOTH 12:00 (the morning block's end) and 13:00 (the afternoon
    block's start). A finish takes the earlier spelling, a start the later one."""
    assert offset_to_datetime(MON, 240, GAPPED) == dt.datetime(2025, 1, 6, 12, 0)
    assert offset_to_start_datetime(MON, 240, GAPPED) == dt.datetime(2025, 1, 6, 13, 0)


def test_the_day_boundary_spelling_is_unchanged() -> None:
    """A CONTROL for ADR-0348: at the DAY boundary a finish is still the previous day's end and
    a start is still the next day's beginning. The segment rule must not disturb it."""
    assert offset_to_start_datetime(MON, 480, GAPPED) == dt.datetime(2025, 1, 7, 8, 0)
    assert offset_to_start_datetime(MON, 960, GAPPED) == dt.datetime(2025, 1, 8, 8, 0)
    assert offset_to_start_datetime(MON, 0, GAPPED) == dt.datetime(2025, 1, 6, 8, 0)


# --- the guard: an undeclared calendar is byte-identical -----------------------------------------


def _contiguous_offset(start: dt.datetime, target: dt.datetime, cal: Calendar) -> int:
    """The legacy contiguous projection, written out independently of the engine."""
    per_day = cal.working_minutes_per_day
    start_tod = start.hour * 60 + start.minute
    target_tod = target.hour * 60 + target.minute
    days = 0
    cursor = start.date()
    while cursor < target.date():
        cursor += dt.timedelta(days=1)
        if cursor.weekday() < 5:
            days += 1
    intraday = min(max(target_tod - start_tod, 0), per_day) if target.weekday() < 5 else 0
    return days * per_day + intraday


def _contiguous_expand(start: dt.datetime, minutes: int, cal: Calendar) -> dt.datetime:
    """The legacy contiguous expansion, written out independently of the engine."""
    per_day = cal.working_minutes_per_day
    quotient, remainder = divmod(minutes, per_day)
    if minutes == 0:
        advance, intraday = 0, 0
    elif remainder == 0:
        advance, intraday = quotient - 1, per_day
    else:
        advance, intraday = quotient, remainder
    day = start
    while day.weekday() >= 5:
        day += dt.timedelta(days=1)
    while advance > 0:
        day += dt.timedelta(days=1)
        if day.weekday() < 5:
            advance -= 1
    return day + dt.timedelta(minutes=intraday)


def test_a_calendar_with_no_declared_segments_is_byte_identical() -> None:
    """A CONTROL, and the reason the change is GUARDED rather than routed through
    ``_Ruler.segments``: that fallback re-anchors to MIDNIGHT once
    ``day_start_tod + minutes_per_day > 1440``, so an undeclared calendar with a late project
    start would be silently re-based -- 1,150 projection and 400 expansion divergences in a
    sweep of the naive change. Synthetic fixtures and P6 exports declare no segments and must
    not move by a single minute. The reference is written out here, independent of the engine."""
    for start_hour in (0, 8, 13, 17, 20, 23):
        start = dt.datetime(2025, 1, 6, start_hour, 0)
        for target_hour in range(24):
            target = dt.datetime(2025, 1, 6, target_hour, 0)
            assert datetime_to_offset(start, target, PLAIN) == _contiguous_offset(
                start, target, PLAIN
            ), (start, target)
        for off in (0, 1, 239, 480, 481, 960, 1441):
            assert offset_to_datetime(start, off, PLAIN) == _contiguous_expand(start, off, PLAIN), (
                start,
                off,
            )


def test_the_origin_is_offset_zero_whatever_the_project_start_time_of_day() -> None:
    """A project start is NOT required to sit at the calendar's first segment.

    ADR-0312's importer precondition bounds only ``start_tod + minutes_per_day <= 1440``, and
    inside that domain ``anchored_project_start`` returns the start **unchanged** — a 09:00 start
    on an 8-hour day is legal and passes through untouched. The contiguous pair read its own
    origin as 0 for every such start by construction (``clamp(tod - tod)``). A segment-aware pair
    anchored at the SEGMENTS instead of at the start reads that origin as 60, and on a declared
    24-hour day an 08:00 start as a whole **480** — an axis shifted by a working day, silently,
    on a legal file. So the intraday term is measured RELATIVE to the start's own worked position.

    The 44-file corpus cannot catch this: every one of its files starts at 08:00 on an
    08-12 / 13-17 calendar, where the start's worked position is 0 and the relative form is
    algebraically identical to the absolute one. That is also why this change moves no measured
    figure.
    """
    day24 = Calendar(
        working_minutes_per_day=1440,
        work_weekdays=(0, 1, 2, 3, 4, 5, 6),
        day_segments=((0, 1440),),
    )
    for cal in (GAPPED, PLAIN, day24):
        for hour in (0, 8, 9, 13, 17, 20):
            start = dt.datetime(2025, 1, 6, hour, 0)
            assert datetime_to_offset(start, start, cal) == 0, (cal.day_segments, hour)


def test_a_late_project_start_still_measures_its_own_working_day() -> None:
    """The same anchor, one step out: from a 09:00 start the morning block's remaining 180
    minutes are 180, and noon is where the morning ends — not 240, which is what an
    origin anchored at 08:00 would report."""
    start = dt.datetime(2025, 1, 6, 9, 0)
    assert datetime_to_offset(start, dt.datetime(2025, 1, 6, 12, 0), GAPPED) == 180
    assert datetime_to_offset(start, dt.datetime(2025, 1, 6, 13, 0), GAPPED) == 180
    assert datetime_to_offset(start, dt.datetime(2025, 1, 6, 14, 0), GAPPED) == 240


# --- the oracle: MS Project's own stored slack ---------------------------------------------------


def _golden_slack_census() -> tuple[tuple[int, int], tuple[int, int, int, int]]:
    tot_pop = tot_exact = 0
    fre_pop = fre_exact = fre_high = fre_low = 0
    for path in _GOLDENS:
        text = _golden_text(path)
        result = compute_cpm(parse_mspdi_text(text))
        for el in ET.fromstring(text).iter(f"{NS}Task"):
            raw_uid = el.findtext(f"{NS}UID")
            if raw_uid is None:
                continue
            timing = result.timings.get(int(raw_uid))
            if timing is None:
                continue
            stored_total = el.findtext(f"{NS}TotalSlack")
            if stored_total is not None:
                tot_pop += 1
                tot_exact += timing.total_float == round(int(stored_total) / 10)
            stored_free = el.findtext(f"{NS}FreeSlack")
            if stored_free is not None:
                value = round(int(stored_free) / 10)
                fre_pop += 1
                fre_exact += timing.free_float == value
                fre_high += timing.free_float > value
                fre_low += timing.free_float < value
    return (tot_pop, tot_exact), (fre_pop, fre_exact, fre_high, fre_low)


def test_the_goldens_move_toward_ms_projects_own_stored_slack() -> None:
    """The fifteen committed goldens against MS Project's stored TotalSlack / FreeSlack -- an
    oracle independent of the engine that produced the figures.

    Total slack exact 3,897 -> 4,098 of 4,559; free slack exact 1,034 -> 1,075 of 1,142 with high
    69 -> 40 and low 39 -> 27. The free-float residual falls on BOTH sides at once, so the gain is
    not one direction bought with the other.

    R-69 then took the total to 4,100 by giving a late START the start-role spelling of an
    internal block boundary on the WALL path too (the same rule this file established for the
    offset path). Free slack is unmoved -- not one of the 3,315 corpus free floats changed.
    """
    assert _GOLDENS and len(_GOLDENS) == 15, _GOLDENS
    total, free = _golden_slack_census()
    assert total == (4559, 4100)
    assert free == (1142, 1075, 40, 27)
