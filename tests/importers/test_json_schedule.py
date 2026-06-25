"""JSON schedule importer/exporter tests — friendly format, round-trip, errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schedule_forensics.importers import (
    ImporterError,
    parse_json,
    parse_json_text,
    supported_extensions,
    to_json_text,
)
from schedule_forensics.model.relationship import RelationshipType

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


def test_json_is_a_supported_extension() -> None:
    assert ".json" in supported_extensions()


def test_parse_friendly_json() -> None:
    text = json.dumps(
        {
            "name": "Mini",
            "project_start": "2026-01-05T08:00:00",
            "status_date": "2026-01-12T17:00:00",
            "calendars": [{"name": "5-day", "hours_per_day": 8}],
            "tasks": [
                {"unique_id": 1, "name": "A", "duration_minutes": 480, "resource_names": ["Bob"]},
                {"unique_id": 2, "name": "B", "duration_minutes": 960, "percent_complete": 50},
            ],
            "relationships": [
                {"predecessor_id": 1, "successor_id": 2, "type": "FS", "lag_minutes": 480}
            ],
        }
    )
    sch = parse_json_text(text)
    assert sch.name == "Mini" and len(sch.tasks) == 2
    assert sch.calendar.working_minutes_per_day == 480
    assert sch.tasks_by_id[1].resource_names == ("Bob",)
    assert sch.tasks_by_id[2].percent_complete == 50.0
    rel = sch.relationships[0]
    assert rel.predecessor_id == 1 and rel.successor_id == 2
    assert rel.type is RelationshipType.FS and rel.lag_minutes == 480


def test_task_level_predecessors() -> None:
    text = json.dumps(
        {
            "name": "P",
            "project_start": "2026-01-05T08:00:00",
            "tasks": [
                {"unique_id": 1, "name": "A", "duration_minutes": 480},
                {"unique_id": 2, "name": "B", "duration_minutes": 480, "predecessors": [1]},
                {
                    "unique_id": 3,
                    "name": "C",
                    "duration_minutes": 480,
                    "predecessors": [{"id": 2, "type": "SS", "lag_minutes": 240}],
                },
            ],
        }
    )
    sch = parse_json_text(text)
    pairs = {(r.predecessor_id, r.successor_id, r.type) for r in sch.relationships}
    assert (1, 2, RelationshipType.FS) in pairs
    assert (2, 3, RelationshipType.SS) in pairs


def test_round_trip_preserves_tasks_and_logic() -> None:
    sch = parse_json(EXAMPLE)
    again = parse_json_text(to_json_text(sch))
    assert len(again.tasks) == len(sch.tasks)
    assert len(again.relationships) == len(sch.relationships)
    assert again.status_date == sch.status_date
    assert again.tasks_by_id[2].actual_finish == sch.tasks_by_id[2].actual_finish


def test_bundled_example_loads() -> None:
    sch = parse_json(EXAMPLE)
    assert sch.name.startswith("House Build") and len(sch.tasks) == 9
    assert sch.status_date is not None


def test_invalid_json_and_missing_tasks_raise() -> None:
    with pytest.raises(ImporterError, match="not valid JSON"):
        parse_json_text("{ not json")
    with pytest.raises(ImporterError, match="tasks"):
        parse_json_text('{"name": "x"}')


def test_invalid_datetime_raises() -> None:
    with pytest.raises(ImporterError, match="invalid datetime"):
        parse_json_text(
            '{"name":"x","project_start":"2026-01-05T08:00:00",'
            '"tasks":[{"unique_id":1,"name":"A","duration_minutes":480,'
            '"baseline_finish":"not-a-date"}]}'
        )


def test_predecessor_entry_without_id_raises() -> None:
    with pytest.raises(ImporterError, match="predecessor"):
        parse_json_text(
            '{"name":"x","project_start":"2026-01-05T08:00:00",'
            '"tasks":[{"unique_id":1,"name":"A","duration_minutes":480},'
            '{"unique_id":2,"name":"B","duration_minutes":480,"predecessors":[{"type":"FS"}]}]}'
        )


def test_constraint_and_dates_survive_round_trip() -> None:
    text = json.dumps(
        {
            "name": "C",
            "project_start": "2026-01-05T08:00:00",
            "tasks": [
                {
                    "unique_id": 1,
                    "name": "Pinned",
                    "duration_minutes": 480,
                    "constraint_type": "MSO",
                    "constraint_date": "2026-01-06T08:00:00",
                    "baseline_start": "2026-01-06T08:00:00",
                }
            ],
        }
    )
    out = to_json_text(parse_json_text(text))
    assert '"constraint_type": "MSO"' in out and '"constraint_date"' in out
    reparsed = parse_json_text(out)
    assert str(reparsed.tasks_by_id[1].constraint_type) == "MSO"


def test_save_json_round_trips_resource_assignments() -> None:
    """ADR-0125: a Save -> reopen cycle keeps the per-resource work/units for the loading view."""
    import datetime as dt

    from schedule_forensics.model.assignment import Assignment
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    original = Schedule(
        name="rt-res",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        tasks=(
            Task(
                unique_id=1,
                name="Build",
                duration_minutes=480,
                resource_ids=(7,),
                resource_assignments=(Assignment(resource_id=7, work_minutes=960, units=0.5),),
            ),
        ),
    )
    reopened = parse_json_text(to_json_text(original))
    task = reopened.tasks_by_id[1]
    assert task.resource_ids == (7,)
    assert task.resource_assignments == (Assignment(resource_id=7, work_minutes=960, units=0.5),)


def test_save_json_round_trip_preserves_structure_and_costs() -> None:
    # the tool's own format must not silently demote milestones/summaries or drop WBS,
    # durations, costs, or the calendar's exact minute count on a Save -> reopen cycle
    import datetime as dt

    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    original = Schedule(
        name="rt",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Tens", working_minutes_per_day=600, work_weekdays=(0, 1, 2, 3)),
        tasks=(
            Task(unique_id=0, name="Root", duration_minutes=0, is_summary=True, wbs="1"),
            Task(
                unique_id=1,
                name="Build",
                duration_minutes=600,
                wbs="1.1",
                remaining_duration_minutes=300,
                baseline_duration_minutes=600,
                cost=1500.0,
                actual_cost=700.0,
                budgeted_cost=1400.0,
            ),
            Task(unique_id=2, name="Done", duration_minutes=0, is_milestone=True, wbs="1.2"),
            Task(unique_id=3, name="Hand-placed", duration_minutes=480, is_manual=True),
        ),
    )
    reread = parse_json_text(to_json_text(original))
    root, build, done = (reread.tasks_by_id[uid] for uid in (0, 1, 2))
    assert root.is_summary and done.is_milestone
    assert reread.tasks_by_id[3].is_manual is True  # MSP manual mode survives Save .json
    assert build.is_manual is False
    assert (build.wbs, build.remaining_duration_minutes, build.baseline_duration_minutes) == (
        "1.1",
        300,
        600,
    )
    assert (build.cost, build.actual_cost, build.budgeted_cost) == (1500.0, 700.0, 1400.0)
    assert reread.calendar.working_minutes_per_day == 600
    assert reread.calendar.work_weekdays == (0, 1, 2, 3)


def test_hours_per_day_rounds_not_truncates() -> None:
    sched = parse_json_text(
        '{"name": "c", "project_start": "2025-01-06T08:00", '
        '"calendars": [{"name": "odd", "hours_per_day": 2.05}], '
        '"tasks": [{"unique_id": 1, "name": "A", "duration_minutes": 60}]}'
    )
    assert sched.calendar.working_minutes_per_day == 123  # int() truncated this to 122


def test_save_json_round_trips_calendar_holidays() -> None:
    # imported calendars now carry holidays (ADR-0028) — the tool's own format must
    # round-trip them exactly, never silently drop a day off
    import datetime as dt

    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    original = Schedule(
        name="hol",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(
            name="Site",
            holidays=(dt.date(2025, 1, 20), dt.date(2025, 7, 4)),
        ),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480),),
    )
    reread = parse_json_text(to_json_text(original))
    assert reread.calendar.holidays == (dt.date(2025, 1, 20), dt.date(2025, 7, 4))
