"""Resource model tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schedule_forensics.model.resource import Resource, ResourceType


def test_defaults() -> None:
    r = Resource(unique_id=1, name="Crew A")
    assert r.type is ResourceType.WORK
    assert r.is_generic is False
    assert r.max_units is None
    assert r.standard_rate is None


def test_explicit_fields() -> None:
    r = Resource(
        unique_id=2,
        name="Steel",
        type=ResourceType.MATERIAL,
        is_generic=True,
        max_units=2.0,
        standard_rate=125.5,
    )
    assert r.type is ResourceType.MATERIAL
    assert r.is_generic is True
    assert r.max_units == 2.0
    assert r.standard_rate == 125.5


def test_resource_type_members() -> None:
    assert {t.value for t in ResourceType} == {"WORK", "MATERIAL", "COST"}


@pytest.mark.parametrize("field", ["max_units", "standard_rate"])
def test_negative_numeric_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        Resource(unique_id=1, name="x", **{field: -1.0})


def test_frozen_and_extra_forbidden() -> None:
    r = Resource(unique_id=1, name="x")
    with pytest.raises(ValidationError):
        r.name = "y"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        Resource(unique_id=1, name="x", bogus=1)  # type: ignore[call-arg]
