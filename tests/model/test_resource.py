"""Resource model tests."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from schedule_forensics.model.resource import AvailabilityPeriod, Resource, ResourceType


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


# ── ADR-0506 (R-63): the availability table and its one resolution rule ─────────────────────────


def _table() -> tuple[AvailabilityPeriod, ...]:
    return (
        AvailabilityPeriod(available_to=dt.datetime(2026, 8, 1, 23, 59), units=1.0),
        AvailabilityPeriod(
            available_from=dt.datetime(2026, 8, 2),
            available_to=dt.datetime(2026, 8, 31, 23, 59),
            units=2.0,
        ),
        AvailabilityPeriod(available_from=dt.datetime(2026, 10, 1), units=0.5),
    )


def test_availability_defaults_empty_and_units_at_is_none_without_a_table() -> None:
    r = Resource(unique_id=1, name="x", max_units=1.5)
    assert r.availability == ()
    assert r.units_at(dt.datetime(2026, 8, 2)) is None  # no table: the caller reads max_units


def test_units_at_is_the_latest_row_begun_by_the_instant_start_bound_inclusive() -> None:
    r = Resource(unique_id=1, name="x", availability=_table())
    assert r.units_at(dt.datetime(1999, 1, 1)) == 1.0  # an open start has always begun
    assert r.units_at(dt.datetime(2026, 8, 1, 23, 59)) == 1.0  # the minute before row two begins
    assert r.units_at(dt.datetime(2026, 8, 2, 0, 0)) == 2.0  # row two begins ON its start minute
    assert r.units_at(dt.datetime(2049, 6, 1)) == 0.5  # the last row, open-ended


def test_outside_every_row_the_latest_begun_row_governs_else_the_earliest() -> None:
    """A gap between rows (September, above) keeps the row that had begun — a table is a sequence
    of statements each in force until the next; before every row's start, the earliest row."""
    r = Resource(unique_id=1, name="x", availability=_table())
    assert r.units_at(dt.datetime(2026, 9, 15)) == 2.0
    future_only = Resource(
        unique_id=2,
        name="y",
        availability=(
            AvailabilityPeriod(available_from=dt.datetime(2027, 1, 1), units=3.0),
            AvailabilityPeriod(available_from=dt.datetime(2028, 1, 1), units=4.0),
        ),
    )
    assert future_only.units_at(dt.datetime(2026, 1, 1)) == 3.0


def test_availability_units_must_be_non_negative_and_the_row_is_frozen() -> None:
    with pytest.raises(ValidationError):
        AvailabilityPeriod(units=-0.5)
    row = AvailabilityPeriod(units=1.0)
    with pytest.raises(ValidationError):
        row.units = 2.0  # type: ignore[misc]
