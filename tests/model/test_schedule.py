"""Schedule model tests — composition, referential integrity, UID-keyed access."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_START = dt.datetime(2026, 1, 1, 8, 0)


def _task(uid: int, name: str = "t", minutes: int = 480) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=minutes)


def test_minimal_defaults() -> None:
    s = Schedule(name="P", project_start=_START, tasks=(_task(1),))
    assert s.source_file is None
    assert s.project_finish is None
    assert s.status_date is None
    assert s.relationships == ()
    assert s.resources == ()
    assert s.calendars == ()
    assert isinstance(s.calendar, Calendar)  # default factory
    assert s.calendar.working_minutes_per_day == 480


def test_full_construction_with_logic_and_resources() -> None:
    s = Schedule(
        name="Project5",
        source_file="Project5.mpp",
        project_start=_START,
        status_date=dt.datetime(2026, 3, 1),
        tasks=(_task(2, "NTP", 0), _task(3, "Build")),
        relationships=(Relationship(predecessor_id=2, successor_id=3),),
        resources=(Resource(unique_id=10, name="Crew A"),),
    )
    assert s.source_file == "Project5.mpp"
    assert len(s.tasks) == 2
    assert s.relationships[0].predecessor_id == 2


def test_duplicate_task_uid_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate Task"):
        Schedule(name="P", project_start=_START, tasks=(_task(1), _task(1)))


def test_relationship_predecessor_must_exist() -> None:
    with pytest.raises(ValidationError, match="predecessor 9 is not a task"):
        Schedule(
            name="P",
            project_start=_START,
            tasks=(_task(1), _task(2)),
            relationships=(Relationship(predecessor_id=9, successor_id=2),),
        )


def test_relationship_successor_must_exist() -> None:
    with pytest.raises(ValidationError, match="successor 9 is not a task"):
        Schedule(
            name="P",
            project_start=_START,
            tasks=(_task(1), _task(2)),
            relationships=(Relationship(predecessor_id=1, successor_id=9),),
        )


def test_duplicate_resource_uid_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate Resource"):
        Schedule(
            name="P",
            project_start=_START,
            tasks=(_task(1),),
            resources=(Resource(unique_id=5, name="a"), Resource(unique_id=5, name="b")),
        )


def test_tasks_by_id_mapping() -> None:
    s = Schedule(name="P", project_start=_START, tasks=(_task(2, "a"), _task(3, "b")))
    mapping = s.tasks_by_id
    assert set(mapping) == {2, 3}
    assert mapping[3].name == "b"


def test_tasks_by_id_is_immutable() -> None:
    s = Schedule(name="P", project_start=_START, tasks=(_task(2),))
    with pytest.raises(TypeError):
        s.tasks_by_id[99] = _task(99)  # type: ignore[index]


def test_task_by_id_found_and_missing() -> None:
    s = Schedule(name="P", project_start=_START, tasks=(_task(2, "a"),))
    assert s.task_by_id(2).name == "a"
    with pytest.raises(KeyError):
        s.task_by_id(999)


def test_resource_lookups() -> None:
    s = Schedule(
        name="P",
        project_start=_START,
        tasks=(_task(1),),
        resources=(Resource(unique_id=10, name="Crew A"),),
    )
    assert set(s.resources_by_id) == {10}
    assert s.resource_by_id(10).name == "Crew A"
    with pytest.raises(KeyError):
        s.resource_by_id(404)


def test_predecessors_and_successors_of() -> None:
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=3),
    )
    s = Schedule(
        name="P",
        project_start=_START,
        tasks=(_task(1), _task(2), _task(3)),
        relationships=rels,
    )
    assert {r.successor_id for r in s.successors_of(1)} == {2, 3}
    assert {r.predecessor_id for r in s.predecessors_of(3)} == {1, 2}
    assert s.successors_of(3) == ()


def test_frozen() -> None:
    s = Schedule(name="P", project_start=_START, tasks=(_task(1),))
    with pytest.raises(ValidationError):
        s.name = "Q"  # type: ignore[misc]


def test_tasks_by_id_is_cached() -> None:
    # the UID map is built once and reused (hot path); the model is frozen so it cannot stale
    s = Schedule(name="P", project_start=_START, tasks=(_task(2, "a"), _task(3, "b")))
    assert s.tasks_by_id is s.tasks_by_id
    assert s.resources_by_id is s.resources_by_id


def test_cache_does_not_perturb_hash_or_equality() -> None:
    a = Schedule(name="P", project_start=_START, tasks=(_task(2),))
    b = Schedule(name="P", project_start=_START, tasks=(_task(2),))
    before = hash(a)
    _ = a.tasks_by_id  # prime the cache
    assert hash(a) == before  # cache lives outside the field-driven hash
    assert a == b and hash(a) == hash(b)  # equality/hash ignore the non-field cache


def test_model_copy_rebuilds_the_cache_from_updated_fields() -> None:
    s = Schedule(name="P", project_start=_START, tasks=(_task(2, "a"),))
    _ = s.tasks_by_id  # prime with {2}
    changed = s.model_copy(update={"tasks": (_task(7, "z"),)})
    assert set(changed.tasks_by_id) == {7}  # never inherits the stale {2} map
    same = s.model_copy(update={"source_file": "x.mpp"})
    assert set(same.tasks_by_id) == {2} and same.source_file == "x.mpp"
