"""``off_project_calendars`` — the base-CPM single-calendar disclosure predicate (#26).

The base CPM solves on ONE schedule-level calendar (``schedule.calendar``, ADR-0028) and never
consults a task's ``calendar_uid``; the driving-slack / SSI path honors each task's own calendar
(ADR-0118). This helper answers "does the file assign some activities a materially-different
calendar?" so the /analysis page can disclose that its base-CPM dates/float are a single-calendar
approximation for those tasks. It is a disclosure signal only — it must change no computed number,
so these tests pin the predicate, not any timing.
"""

from __future__ import annotations

import datetime as dt
import gzip
from functools import cache
from pathlib import Path

from schedule_forensics.engine.cpm import off_project_calendars
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

# A calendar whose WORKING PATTERN differs from the Mon-Fri 8h default (round-the-clock, 7 days).
_CAL24 = Calendar(
    uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)


def _sched(tasks: tuple[Task, ...], calendars: tuple[Calendar, ...] = ()) -> Schedule:
    return Schedule(
        name="s",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard"),  # Mon-Fri 8h default, uid 0
        calendars=calendars,
        tasks=tasks,
    )


def test_active_task_on_a_different_calendar_is_reported() -> None:
    sch = _sched(
        (
            Task(unique_id=1, name="on project cal", duration_minutes=_DAY),
            Task(unique_id=2, name="round the clock", duration_minutes=_DAY, calendar_uid=10),
        ),
        calendars=(_CAL24,),
    )
    off = off_project_calendars(sch)
    assert [c.uid for c in off] == [10]
    assert off[0].name == "24 Hours"


def test_single_calendar_schedule_reports_nothing() -> None:
    sch = _sched(
        (
            Task(unique_id=1, name="A", duration_minutes=_DAY),
            Task(unique_id=2, name="B", duration_minutes=_DAY),
        )
    )
    assert off_project_calendars(sch) == ()


def test_second_calendar_with_the_same_working_pattern_is_not_reported() -> None:
    # A registry may carry a second calendar UID that is really the same working pattern; the base
    # CPM's single-calendar answer is EXACT for it, so it must not be flagged (no cry-wolf).
    twin = Calendar(
        uid=7, name="Standard (copy)"
    )  # identical Mon-Fri 8h pattern, different uid/name
    sch = _sched(
        (Task(unique_id=1, name="A", duration_minutes=_DAY, calendar_uid=7),),
        calendars=(twin,),
    )
    assert off_project_calendars(sch) == ()


def test_only_active_non_summary_tasks_count() -> None:
    # A summary rollup and an inactive task are out of the CPM network (ADR-0128), so a per-task
    # calendar on either cannot move a base-CPM number — neither triggers the disclosure.
    sch = _sched(
        (
            Task(
                unique_id=1,
                name="summary on cal24",
                duration_minutes=0,
                is_summary=True,
                calendar_uid=10,
            ),
            Task(
                unique_id=2,
                name="inactive on cal24",
                duration_minutes=_DAY,
                is_active=False,
                calendar_uid=10,
            ),
        ),
        calendars=(_CAL24,),
    )
    assert off_project_calendars(sch) == ()


def test_calendar_uid_absent_from_registry_is_failsoft() -> None:
    # A task whose calendar the importer could not parse into the registry can't be compared;
    # skip it rather than over-claim a divergence.
    sch = _sched(
        (Task(unique_id=1, name="dangling cal ref", duration_minutes=_DAY, calendar_uid=999),),
        calendars=(_CAL24,),  # registry has uid 10, NOT 999
    )
    assert off_project_calendars(sch) == ()


def test_result_is_deduplicated_and_sorted_by_uid() -> None:
    cal_a = Calendar(uid=20, name="Six-day", work_weekdays=(0, 1, 2, 3, 4, 5))
    sch = _sched(
        (
            Task(unique_id=1, name="t1", duration_minutes=_DAY, calendar_uid=10),
            Task(unique_id=2, name="t2 same off-cal", duration_minutes=_DAY, calendar_uid=10),
            Task(unique_id=3, name="t3 other off-cal", duration_minutes=_DAY, calendar_uid=20),
        ),
        calendars=(_CAL24, cal_a),
    )
    off = off_project_calendars(sch)
    assert [c.uid for c in off] == [10, 20]  # deduped (uid 10 once) and ascending by uid


# --- real-golden anchors --------------------------------------------------------------------


@cache
def _leveled() -> Schedule:
    raw = gzip.decompress(
        (GOLDEN / "ssi_uid152_leveled" / "Large_Test_File_Leveled.mspdi.xml.gz").read_bytes()
    )
    return parse_mspdi_text(raw.decode("utf-8-sig", errors="replace"))


def _project5() -> Schedule:
    text = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_text(
        encoding="utf-8-sig", errors="replace"
    )
    return parse_mspdi_text(text)


def test_real_multi_calendar_file_reports_its_off_project_calendar() -> None:
    # The operator's leveled master IMS runs on "Dynetics Standard" but assigns some activities the
    # "ZIN Project Calendar" (a different holiday set) — the base CPM solves all of them on the
    # project calendar, so the disclosure must fire and name ZIN.
    off = off_project_calendars(_leveled())
    names = {c.name for c in off}
    assert "ZIN Project Calendar" in names


def test_real_single_calendar_file_reports_nothing() -> None:
    assert off_project_calendars(_project5()) == ()
