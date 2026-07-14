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


def test_save_json_round_trips_every_fidelity_field() -> None:
    """Audit C1: a Save .json round-trip must not silently drop ANY field the model carries.

    Builds a maximal Task/Schedule/Calendar with every field set to a non-default value and
    asserts field-by-field equality after ``parse_json_text(to_json_text(...))``. This guards
    the Acumen-parity ``stored_total_float_minutes`` / ``stored_is_critical``, the ADR-0128
    ``is_active`` flag, ``custom_fields`` / ``custom_field_labels`` (the group/filter population),
    and the calendar ``working_days`` / ``day_segments`` (SSI driving-slack inputs). If a future
    schema add is not wired into JSON I/O, this test fails loudly.
    """
    import datetime as dt

    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import ConstraintType, Task

    cal = Calendar(
        uid=3,
        name="Site",
        working_minutes_per_day=600,
        work_weekdays=(0, 1, 2, 3, 4, 5),
        holidays=(dt.date(2025, 1, 1), dt.date(2025, 7, 4)),
        working_days=(dt.date(2025, 1, 18),),
        day_segments=((480, 720), (780, 1020)),
    )
    task = Task(
        unique_id=7,
        name="Pour foundation",
        wbs="1.2.3",
        calendar_uid=42,
        outline_level=3,
        duration_minutes=4800,
        duration_is_elapsed=True,
        remaining_duration_minutes=2400,
        baseline_duration_minutes=4800,
        is_estimated_duration=True,
        is_milestone=False,
        is_summary=False,
        is_level_of_effort=True,
        is_active=False,
        is_manual=True,
        constraint_type=ConstraintType.MSO,
        constraint_date=dt.datetime(2025, 3, 1, 8, 0),
        deadline=dt.datetime(2025, 4, 1, 17, 0),
        percent_complete=50.0,
        physical_percent_complete=33.0,
        stored_total_float_minutes=-240,
        stored_is_critical=True,
        start=dt.datetime(2025, 2, 1, 8, 0),
        finish=dt.datetime(2025, 2, 10, 17, 0),
        actual_start=dt.datetime(2025, 2, 1, 8, 0),
        baseline_start=dt.datetime(2025, 1, 15, 8, 0),
        baseline_finish=dt.datetime(2025, 1, 25, 17, 0),
        cost=1000.0,
        actual_cost=400.0,
        budgeted_cost=900.0,
        resource_names=("Crew A",),
        resource_ids=(11,),
        custom_fields=(("CA-WBS", "X1"), ("Risk", "High")),
    )
    original = Schedule(
        name="maximal",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        status_date=dt.datetime(2025, 2, 5, 17, 0),
        calendar=cal,
        calendars=(cal,),
        custom_field_labels=("CA-WBS", "Risk"),
        tasks=(task,),
    )
    reread = parse_json_text(to_json_text(original))

    rt = reread.tasks[0]
    for field in (
        "wbs",
        "calendar_uid",
        "outline_level",
        "duration_minutes",
        "duration_is_elapsed",
        "remaining_duration_minutes",
        "baseline_duration_minutes",
        "is_estimated_duration",
        "is_level_of_effort",
        "is_active",
        "is_manual",
        "constraint_type",
        "constraint_date",
        "deadline",
        "percent_complete",
        "physical_percent_complete",
        "stored_total_float_minutes",
        "stored_is_critical",
        "start",
        "finish",
        "actual_start",
        "baseline_start",
        "baseline_finish",
        "cost",
        "actual_cost",
        "budgeted_cost",
        "resource_names",
        "resource_ids",
        "custom_fields",
    ):
        assert getattr(rt, field) == getattr(task, field), f"Task.{field} lost in round-trip"
    assert reread.custom_field_labels == ("CA-WBS", "Risk")
    assert reread.status_date == original.status_date
    rc = reread.calendar
    for field in (
        "uid",
        "working_minutes_per_day",
        "work_weekdays",
        "holidays",
        "working_days",
        "day_segments",
    ):
        assert getattr(rc, field) == getattr(cal, field), f"Calendar.{field} lost in round-trip"


def test_missing_project_start_raises_not_fabricated() -> None:
    """Audit M3: a friendly JSON with valid tasks but no project_start must raise (like MSPDI/
    XER), never silently fabricate a 2025-01-06 CPM anchor."""
    with pytest.raises(ImporterError, match="missing 'project_start'"):
        parse_json_text(
            '{"name": "x", "tasks": [{"unique_id": 1, "name": "A", "duration_minutes": 480}]}'
        )


def _maximal_schedule():  # type: ignore[no-untyped-def]
    """Every model field set to a NON-DEFAULT value, so any writer omission is visible."""
    import datetime as dt

    from schedule_forensics.model.assignment import Assignment
    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.resource import Resource, ResourceType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import ConstraintType, Task

    project_cal = Calendar(
        uid=3,
        name="Project 10h",
        working_minutes_per_day=600,
        work_weekdays=(0, 1, 2, 3, 4, 5),
        holidays=(dt.date(2026, 7, 3),),
        working_days=(dt.date(2026, 7, 4),),
        day_segments=((480, 720), (780, 1080)),
    )
    night = Calendar(uid=7, name="NightShift", working_minutes_per_day=480)
    task = Task(
        unique_id=11,
        name="Erect steel — 鉄骨",
        wbs="1.2.3",
        calendar_uid=7,
        outline_level=4,
        duration_minutes=4800,
        duration_is_elapsed=True,
        remaining_duration_minutes=2400,
        baseline_duration_minutes=4320,
        is_estimated_duration=True,
        is_milestone=False,
        is_summary=False,
        is_level_of_effort=True,
        is_active=False,
        is_manual=True,
        constraint_type=ConstraintType.SNLT,
        constraint_date=dt.datetime(2026, 8, 1, 8, 0),
        deadline=dt.datetime(2026, 9, 1, 17, 0),
        percent_complete=42.5,
        physical_percent_complete=37.5,
        stored_total_float_minutes=-480,
        stored_is_critical=True,
        start=dt.datetime(2026, 7, 6, 8, 0),
        finish=dt.datetime(2026, 7, 20, 17, 0),
        actual_start=dt.datetime(2026, 7, 6, 9, 30),
        actual_finish=dt.datetime(2026, 7, 21, 16, 45, 30),
        baseline_start=dt.datetime(2026, 7, 1, 8, 0),
        baseline_finish=dt.datetime(2026, 7, 15, 17, 0),
        cost=-125.5,
        actual_cost=99.25,
        budgeted_cost=1000.0,
        work_minutes=1920,
        actual_work_minutes=840,
        resource_names=("Crane", "Crew A"),
        resource_ids=(21,),
        resource_assignments=(
            Assignment(resource_id=21, work_minutes=960, units=0.5, remaining_work_minutes=180),
        ),
        custom_fields=(("CA-WBS", "X.1"), ("Text20", "note")),
        notes="Constraint added per CE direction 7/1; see change log.",
    )
    other = Task(unique_id=12, name="Follow-on", duration_minutes=480)
    # milestone/summary carriers: contradictory with the maximal task's flags, so they ride on
    # their own rows — the introspection guard unions the emitted keys across all tasks
    mile = Task(unique_id=13, name="Contract award", duration_minutes=0, is_milestone=True)
    summ = Task(unique_id=14, name="Phase rollup", duration_minutes=0, is_summary=True)
    return Schedule(
        name="Maximal",
        project_title="Maximal Program Title",
        project_start=dt.datetime(2026, 7, 1, 8, 0),
        project_finish=dt.datetime(2026, 12, 1, 17, 0),
        status_date=dt.datetime(2026, 7, 15, 17, 0),
        baseline_finish=dt.datetime(2026, 11, 1, 17, 0),
        calendar=project_cal,
        calendars=(project_cal, night),
        tasks=(task, other, mile, summ),
        relationships=(Relationship(predecessor_id=11, successor_id=12, lag_minutes=-30),),
        resources=(
            Resource(
                unique_id=21,
                name="Crane",
                type=ResourceType.MATERIAL,
                is_generic=True,
                max_units=2.5,
                standard_rate=180.0,
            ),
        ),
        custom_field_labels=("CA-WBS", "Text20"),
    )


#: Fields to_json_text deliberately does not write. `source_file` is a runtime citation label —
#: the loader re-stamps it from the file name on every open, so persisting it would be stale.
_WRITER_EXCLUDED_FIELDS: dict[str, set[str]] = {"Schedule": {"source_file"}}


def test_writer_covers_every_model_field_introspection_guard_qc_d5() -> None:
    """QC audit D5/D10 (ADR-0140): the writer must emit EVERY model field (bar the documented
    exclusions), checked by introspection — so adding a field to any model without a writer line
    fails THIS test instead of silently losing data on Save .json."""
    from schedule_forensics.model.assignment import Assignment
    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.resource import Resource
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    doc = json.loads(to_json_text(_maximal_schedule()))
    emitted = {
        "Schedule": set(doc),
        "Task": {k for t in doc["tasks"] for k in t},
        "Relationship": set(doc["relationships"][0]),
        "Calendar": set(doc["calendars"][0]),
        "Resource": set(doc["resources"][0]),
        "Assignment": set(doc["tasks"][0]["resource_assignments"][0]),
    }
    for model in (Schedule, Task, Relationship, Calendar, Resource, Assignment):
        excluded = _WRITER_EXCLUDED_FIELDS.get(model.__name__, set())
        missing = set(model.model_fields) - emitted[model.__name__] - excluded
        assert not missing, f"{model.__name__} fields not written by to_json_text: {missing}"


def test_maximal_round_trip_is_lossless_qc_d5() -> None:
    """QC audit D5/D9/D10: a maximally-populated schedule — TWO calendars (the project default is
    NOT calendars[0] by uid order), resources, schedule-level finish dates — round-trips with a
    model_dump identical to the original (source_file excluded: runtime label)."""
    original = _maximal_schedule()
    reopened = parse_json_text(to_json_text(original))
    a = original.model_dump(exclude={"source_file"})
    b = reopened.model_dump(exclude={"source_file"})
    assert a == b
    # the D5/D9 specifics, asserted explicitly for readability
    assert len(reopened.calendars) == 2 and reopened.tasks[0].calendar_uid == 7
    assert reopened.calendar.name == "Project 10h"  # never swapped for calendars[0]/uid order
    assert reopened.resources[0].max_units == 2.5
    assert reopened.project_finish is not None and reopened.baseline_finish is not None


def test_strict_identity_types_fail_loud_qc_d24() -> None:
    """QC audit D24: a fractional unique_id must raise, never truncate (identity corruption);
    a null/empty name falls back to the UID label instead of the literal 'None'/''."""
    with pytest.raises(ImporterError):
        parse_json_text(
            '{"name": "P", "project_start": "2026-01-05T08:00:00",'
            ' "tasks": [{"unique_id": 1.5, "name": "A", "duration_minutes": 480}]}'
        )
    sch = parse_json_text(
        '{"name": "P", "project_start": "2026-01-05T08:00:00",'
        ' "tasks": [{"unique_id": 7, "name": null, "duration_minutes": 480},'
        '           {"unique_id": 8, "name": "", "duration_minutes": 480}]}'
    )
    assert sch.tasks[0].name == "Task 7" and sch.tasks[1].name == "Task 8"


def test_parse_json_stamps_source_file_like_other_importers_qc_d24(tmp_path: Path) -> None:
    p = tmp_path / "myplan.json"
    p.write_text(
        '{"name": "P", "project_start": "2026-01-05T08:00:00",'
        ' "tasks": [{"unique_id": 1, "name": "A", "duration_minutes": 480}]}',
        encoding="utf-8",
    )
    assert parse_json(p).source_file == "myplan.json"
