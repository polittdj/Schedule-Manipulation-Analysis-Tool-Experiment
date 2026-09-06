"""IMP-06 (WP6b, ADR-0467): Save .json round-trips an EMPTY calendar registry as empty.

The writer emitted ``calendars: [project calendar]`` whenever ``Schedule.calendars`` was empty,
so a save re-opened with a one-entry registry the original never had — ``model_dump`` of the two
differed on ``calendars`` although the writer's contract is "every model field round-trips".

Red-first (2026-09-06): ``back.calendars`` had one entry; the dumps differed on ``calendars``.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.importers import parse_json_text, to_json_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)


def _dump(s: Schedule) -> dict[str, object]:
    return s.model_dump(exclude={"source_file"})


def test_an_empty_registry_reopens_empty_and_model_identical() -> None:
    tasks = (Task(unique_id=1, name="A", duration_minutes=480),)
    s = Schedule(name="x", project_start=MON, tasks=tasks)
    assert s.calendars == ()
    back = parse_json_text(to_json_text(s))
    assert back.calendars == ()
    assert _dump(back) == _dump(s)


def test_a_populated_registry_still_round_trips() -> None:
    night = Calendar(uid=3, name="Night", working_minutes_per_day=600)
    s = Schedule(
        name="x",
        project_start=MON,
        calendars=(Calendar(), night),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480, calendar_uid=3),),
    )
    back = parse_json_text(to_json_text(s))
    assert [c.uid for c in back.calendars] == [0, 3]
    assert _dump(back) == _dump(s)
