"""Elapsed durations ("1 eday") ignore calendars — MS Project semantics (M18 bug fix).

The operator's Project2(Duration Bomb).mpp: UID 171 is "1 eday" starting Friday
6/12/2026 08:00 and finishing Saturday 6/13 08:00 in MS Project — but the engine
treated its 1440 minutes as WORKING minutes (3 working days) and pushed the finish to
6/16. Elapsed durations consume wall-clock time: weekends and holidays included, both
task and project calendars ignored.
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.importers.json_schedule import parse_json_text, to_json_text
from schedule_forensics.importers.mspdi import parse_mspdi_text

_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <Name>elapsed</Name>
  <StartDate>2026-06-12T08:00:00</StartDate>
  <StatusDate>2026-06-12T08:00:00</StatusDate>
  <Tasks>
    <Task><UID>1</UID><Name>Curing (1 eday)</Name>
      <Start>2026-06-12T08:00:00</Start><Finish>2026-06-13T08:00:00</Finish>
      <Duration>PT24H0M0S</Duration><DurationFormat>8</DurationFormat>
      <Baseline><Number>0</Number><Start>2026-06-12T08:00:00</Start>
      <Finish>2026-06-13T08:00:00</Finish><Duration>PT24H0M0S</Duration></Baseline>
    </Task>
    <Task><UID>2</UID><Name>Next working task</Name>
      <Start>2026-06-15T08:00:00</Start><Finish>2026-06-15T17:00:00</Finish>
      <Duration>PT8H0M0S</Duration><DurationFormat>7</DurationFormat>
      <PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type>
      <LinkLag>0</LinkLag><LagFormat>7</LagFormat></PredecessorLink>
    </Task>
    <Task><UID>3</UID><Name>Long elapsed (30 edays)</Name>
      <Start>2026-06-12T08:00:00</Start><Finish>2026-07-12T08:00:00</Finish>
      <Duration>PT720H0M0S</Duration><DurationFormat>8</DurationFormat>
      <Baseline><Number>0</Number><Start>2026-06-12T08:00:00</Start>
      <Finish>2026-07-12T08:00:00</Finish><Duration>PT720H0M0S</Duration></Baseline>
    </Task>
  </Tasks>
</Project>"""


def test_importer_flags_elapsed_duration_formats() -> None:
    s = parse_mspdi_text(_XML, source_file="elapsed.xml")
    assert s.tasks_by_id[1].duration_is_elapsed
    assert s.tasks_by_id[3].duration_is_elapsed
    assert not s.tasks_by_id[2].duration_is_elapsed


def test_one_eday_from_friday_finishes_that_day_and_frees_monday() -> None:
    """The operator's UID-171 case: 1 eday over a weekend is NOT 3 working days."""
    s = parse_mspdi_text(_XML, source_file="elapsed.xml")
    cpm = compute_cpm(s)
    finish_dt = offset_to_datetime(s.project_start, cpm.timings[1].early_finish, s.calendar)
    # wall-clock finish Saturday 08:00 maps to Friday end-of-day on the working axis
    assert finish_dt.date().isoformat() == "2026-06-12"
    # the successor occupies Monday (its start offset equals Friday-EOD == Monday-SOD
    # on the working axis; the finish proves where the work actually lands)
    succ_finish = offset_to_datetime(s.project_start, cpm.timings[2].early_finish, s.calendar)
    assert succ_finish.date().isoformat() == "2026-06-15"  # Monday, exactly like MSP


def test_thirty_edays_is_thirty_calendar_days_not_ninety_working() -> None:
    s = parse_mspdi_text(_XML, source_file="elapsed.xml")
    cpm = compute_cpm(s)
    finish_dt = offset_to_datetime(s.project_start, cpm.timings[3].early_finish, s.calendar)
    # 30 elapsed days from 6/12 land mid-July (7/12 is a Sunday -> Friday 7/10 EOD on
    # the working axis), nowhere near the ~90-working-day October a working-minute
    # reading would produce
    assert finish_dt.date().isoformat() == "2026-07-10"


def test_high_duration_compares_elapsed_tasks_on_the_elapsed_axis() -> None:
    """30 edays = 90 working-day-equivalents, but it is NOT a >44-day high-duration
    offender: the duration the scheduler typed is 30 days of wall-clock time."""
    s = parse_mspdi_text(_XML, source_file="elapsed.xml")
    high = next(c for c in audit_schedule(s).checks if c.name == "High Duration")
    assert 3 not in {c.unique_id for c in high.citations}


def test_elapsed_flag_round_trips_through_json() -> None:
    s = parse_mspdi_text(_XML, source_file="elapsed.xml")
    again = parse_json_text(to_json_text(s))
    assert again.tasks_by_id[1].duration_is_elapsed
    assert not again.tasks_by_id[2].duration_is_elapsed
