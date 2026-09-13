"""Schema-freeze guard (change control).

The domain model is the trust root the whole engine consumes. Any field
add/remove/rename must be a deliberate, reviewed change: update this test AND bump
``model.SCHEMA_VERSION`` in the same commit. If this test fails unexpectedly, an
importer or refactor changed the contract without going through change control.
"""

from __future__ import annotations

import pydantic
import pytest

from schedule_forensics import model
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.saved_view import (
    Criterion,
    GroupClause,
    Operand,
    SavedFilter,
    SavedGroup,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task, TaskType

_EXPECTED_FIELDS: dict[type[pydantic.BaseModel], set[str]] = {
    Task: {
        "unique_id",
        "name",
        "wbs",
        "calendar_uid",
        "outline_level",
        "outline_number",
        "duration_minutes",
        "duration_is_elapsed",
        "is_estimated_duration",
        "remaining_duration_minutes",
        "baseline_duration_minutes",
        "is_milestone",
        "is_summary",
        "is_level_of_effort",
        "is_active",
        "is_manual",
        "priority",
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
        "actual_finish",
        "baseline_start",
        "baseline_finish",
        "stop",
        "resume",
        "cost",
        "actual_cost",
        "budgeted_cost",
        "work_minutes",
        "actual_work_minutes",
        "baseline_work_minutes",
        "resource_names",
        "resource_ids",
        "resource_assignments",
        "task_type",
        "ignore_resource_calendar",
        "leveling_delay_minutes",
        "custom_fields",
        "notes",
    },
    # start / finish: the booking's recorded window (ADR-0487) — a MATERIAL / COST booking's
    # span, the one scheduling input the file carries for it; None when unrecorded
    Assignment: {
        "resource_id",
        "work_minutes",
        "units",
        "remaining_work_minutes",
        "start",
        "finish",
    },
    Relationship: {"predecessor_id", "successor_id", "type", "lag_minutes"},
    Resource: {
        "unique_id",
        "name",
        "type",
        "is_generic",
        "max_units",
        "standard_rate",
        "calendar_uid",
    },
    Calendar: {
        "uid",
        "name",
        "working_minutes_per_day",
        # project-level duration-scale properties (ADR-0354/0355): MPXJ-conformant duration
        # literals in saved filters; None = the source didn't provide them
        "declared_minutes_per_day",
        "minutes_per_week",
        "days_per_month",
        "work_weekdays",
        "holidays",
        "working_days",
        "day_segments",
    },
    Schedule: {
        "name",
        "project_title",
        "company",
        "source_file",
        "project_start",
        "project_finish",
        "status_date",
        "baseline_finish",
        "calendar",
        "calendars",
        "tasks",
        "relationships",
        "resources",
        "custom_field_labels",
        "custom_field_by_raw_name",
        "saved_filters",
        "saved_groups",
        "import_notes",
    },
    # IMP-03 (ADR-0467): the five saved-view models (MS Project filters / groups, ADR-0450's
    # surface) were outside the freeze — 6 of the 11 model classes were change-controlled.
    Operand: {"kind", "text", "field_enum", "value_type"},
    Criterion: {"operator", "field", "field_enum", "operands", "children"},
    SavedFilter: {
        "name",
        "criteria",
        "is_task_filter",
        "show_related_summary_rows",
        "prompt_count",
    },
    GroupClause: {"field", "field_enum", "ascending", "group_on", "interval", "start_at"},
    SavedGroup: {"name", "show_summary_tasks", "clauses"},
}


def test_schema_version() -> None:
    assert model.SCHEMA_VERSION == "2.12.0"


@pytest.mark.parametrize("cls", list(_EXPECTED_FIELDS))
def test_field_sets_are_frozen(cls: type[pydantic.BaseModel]) -> None:
    assert set(cls.model_fields) == _EXPECTED_FIELDS[cls]


def test_enum_members_are_frozen() -> None:
    assert {c.value for c in ConstraintType} == {
        "ASAP",
        "ALAP",
        "SNET",
        "SNLT",
        "FNET",
        "FNLT",
        "MSO",
        "MFO",
    }
    assert {t.value for t in RelationshipType} == {"FS", "SS", "FF", "SF"}
    assert {t.value for t in ResourceType} == {"WORK", "MATERIAL", "COST"}
    assert {t.value for t in TaskType} == {"FIXED_UNITS", "FIXED_DURATION", "FIXED_WORK"}


@pytest.mark.parametrize("cls", list(_EXPECTED_FIELDS))
def test_models_are_frozen_strict_and_closed(cls: type[pydantic.BaseModel]) -> None:
    assert cls.model_config.get("frozen") is True
    assert cls.model_config.get("strict") is True
    assert cls.model_config.get("extra") == "forbid"


def test_public_api_exports() -> None:
    assert set(model.__all__) == {
        "SCHEMA_VERSION",
        "Assignment",
        "Calendar",
        "ConstraintType",
        "Relationship",
        "RelationshipType",
        "Resource",
        "ResourceType",
        "Schedule",
        "Task",
        "TaskType",
        "units",
    }
