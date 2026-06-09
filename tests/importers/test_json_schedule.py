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
