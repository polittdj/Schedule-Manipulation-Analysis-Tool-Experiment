"""Relationship model tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schedule_forensics.model.relationship import Relationship, RelationshipType


def test_defaults() -> None:
    r = Relationship(predecessor_id=1, successor_id=2)
    assert r.type is RelationshipType.FS
    assert r.lag_minutes == 0
    assert not r.is_lead
    assert not r.is_lag


def test_explicit_type_and_lag() -> None:
    r = Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.SS, lag_minutes=480)
    assert r.type is RelationshipType.SS
    assert r.lag_minutes == 480
    assert r.is_lag
    assert not r.is_lead


def test_negative_lag_is_a_lead() -> None:
    r = Relationship(predecessor_id=1, successor_id=2, lag_minutes=-240)
    assert r.is_lead
    assert not r.is_lag


def test_self_loop_rejected() -> None:
    with pytest.raises(ValidationError, match="self-referential"):
        Relationship(predecessor_id=7, successor_id=7)


def test_relationship_type_members() -> None:
    assert {t.value for t in RelationshipType} == {"FS", "SS", "FF", "SF"}


def test_frozen() -> None:
    r = Relationship(predecessor_id=1, successor_id=2)
    with pytest.raises(ValidationError):
        r.lag_minutes = 5  # type: ignore[misc]


def test_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        Relationship(predecessor_id=1, successor_id=2, bogus=1)  # type: ignore[call-arg]


def test_strict_no_coercion() -> None:
    with pytest.raises(ValidationError):
        Relationship(predecessor_id="1", successor_id=2)  # type: ignore[arg-type]


def test_hashable_and_equal() -> None:
    a = Relationship(predecessor_id=1, successor_id=2)
    b = Relationship(predecessor_id=1, successor_id=2)
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1
