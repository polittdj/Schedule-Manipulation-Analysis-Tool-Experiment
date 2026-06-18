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
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

_EXPECTED_FIELDS: dict[type[pydantic.BaseModel], set[str]] = {
    Task: {
        "unique_id",
        "name",
        "wbs",
        "duration_minutes",
        "duration_is_elapsed",
        "remaining_duration_minutes",
        "baseline_duration_minutes",
        "is_milestone",
        "is_summary",
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
        "actual_finish",
        "baseline_start",
        "baseline_finish",
        "cost",
        "actual_cost",
        "budgeted_cost",
        "resource_names",
        "resource_ids",
    },
    Relationship: {"predecessor_id", "successor_id", "type", "lag_minutes"},
    Resource: {"unique_id", "name", "type", "is_generic", "max_units", "standard_rate"},
    Calendar: {"name", "working_minutes_per_day", "work_weekdays", "holidays"},
    Schedule: {
        "name",
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
    },
}


def test_schema_version() -> None:
    assert model.SCHEMA_VERSION == "2.1.0"


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


@pytest.mark.parametrize("cls", list(_EXPECTED_FIELDS))
def test_models_are_frozen_strict_and_closed(cls: type[pydantic.BaseModel]) -> None:
    assert cls.model_config.get("frozen") is True
    assert cls.model_config.get("strict") is True
    assert cls.model_config.get("extra") == "forbid"


def test_public_api_exports() -> None:
    assert set(model.__all__) == {
        "SCHEMA_VERSION",
        "Calendar",
        "ConstraintType",
        "Relationship",
        "RelationshipType",
        "Resource",
        "ResourceType",
        "Schedule",
        "Task",
        "units",
    }
