"""Task model tests."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from schedule_forensics.model.task import ConstraintType, Task


def test_minimal_defaults() -> None:
    t = Task(unique_id=2, name="Notice to proceed", duration_minutes=0)
    assert t.wbs is None
    assert t.remaining_duration_minutes is None
    assert t.baseline_duration_minutes is None
    assert t.is_milestone is False
    assert t.is_summary is False
    assert t.is_level_of_effort is False
    assert t.is_active is True
    assert t.constraint_type is ConstraintType.ASAP
    assert t.constraint_date is None
    assert t.deadline is None
    assert t.percent_complete == 0.0
    assert t.physical_percent_complete is None
    assert t.budgeted_cost == 0.0
    assert t.resource_names == ()
    assert t.resource_ids == ()


def test_required_fields() -> None:
    with pytest.raises(ValidationError):
        Task(unique_id=1, name="x")  # type: ignore[call-arg]  # missing duration_minutes
    with pytest.raises(ValidationError):
        Task(unique_id=1, duration_minutes=0)  # type: ignore[call-arg]  # missing name


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_minutes", -1),
        ("remaining_duration_minutes", -1),
        ("baseline_duration_minutes", -1),
        ("percent_complete", -0.1),
        ("percent_complete", 100.1),
        ("physical_percent_complete", 100.1),
        ("cost", -1.0),
        ("actual_cost", -1.0),
        ("budgeted_cost", -1.0),
    ],
)
def test_bounds_enforced(field: str, value: float) -> None:
    base = {"unique_id": 1, "name": "x", "duration_minutes": 0}
    base[field] = value
    with pytest.raises(ValidationError):
        Task(**base)  # type: ignore[arg-type]


def test_strict_rejects_wrong_types() -> None:
    with pytest.raises(ValidationError):
        Task(unique_id="1", name="x", duration_minutes=0)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Task(unique_id=1, name="x", duration_minutes=1.5)  # type: ignore[arg-type]


def test_constraint_type_members() -> None:
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


def test_progress_properties() -> None:
    not_started = Task(unique_id=1, name="x", duration_minutes=480, percent_complete=0.0)
    in_progress = Task(unique_id=2, name="x", duration_minutes=480, percent_complete=50.0)
    complete = Task(unique_id=3, name="x", duration_minutes=480, percent_complete=100.0)

    assert not_started.is_not_started and not not_started.is_in_progress
    assert not not_started.is_complete
    assert in_progress.is_in_progress and not in_progress.is_complete
    assert not in_progress.is_not_started
    assert complete.is_complete and not complete.is_in_progress


@pytest.mark.parametrize(
    ("constraint", "hard"),
    [
        (ConstraintType.MSO, True),
        (ConstraintType.MFO, True),
        (ConstraintType.SNLT, True),
        (ConstraintType.FNLT, True),
        (ConstraintType.ASAP, False),
        (ConstraintType.ALAP, False),
        (ConstraintType.SNET, False),
        (ConstraintType.FNET, False),
    ],
)
def test_has_hard_constraint(constraint: ConstraintType, hard: bool) -> None:
    t = Task(unique_id=1, name="x", duration_minutes=480, constraint_type=constraint)
    assert t.has_hard_constraint is hard


def test_full_field_population() -> None:
    when = dt.datetime(2026, 1, 5, 8, 0)
    t = Task(
        unique_id=143,
        name="Obtain certificate of occupancy",
        wbs="1.2.3",
        duration_minutes=480,
        remaining_duration_minutes=240,
        baseline_duration_minutes=480,
        is_milestone=False,
        is_summary=False,
        is_level_of_effort=False,
        is_active=True,
        constraint_type=ConstraintType.FNLT,
        constraint_date=when,
        deadline=when,
        percent_complete=50.0,
        physical_percent_complete=40.0,
        start=when,
        finish=when,
        actual_start=when,
        actual_finish=None,
        baseline_start=when,
        baseline_finish=when,
        cost=1000.0,
        actual_cost=400.0,
        budgeted_cost=1000.0,
        resource_names=("Crew A", "Inspector"),
        resource_ids=(10, 11),
    )
    assert t.unique_id == 143
    assert t.resource_names == ("Crew A", "Inspector")
    assert t.has_hard_constraint


def test_frozen_and_extra_forbidden() -> None:
    t = Task(unique_id=1, name="x", duration_minutes=0)
    with pytest.raises(ValidationError):
        t.name = "y"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        Task(unique_id=1, name="x", duration_minutes=0, bogus=1)  # type: ignore[call-arg]


def test_hashable_and_equality() -> None:
    a = Task(unique_id=1, name="x", duration_minutes=480)
    b = Task(unique_id=1, name="x", duration_minutes=480)
    c = Task(unique_id=1, name="x", duration_minutes=240)
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert len({a, b, c}) == 2
