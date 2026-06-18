"""Field-based grouping & filtering (ADR-0090)."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.grouping import (
    MAX_FIELDS,
    available_fields,
    field_value,
    filter_schedule,
    group_values,
    select,
    task_matches,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, **kw: object) -> Task:
    kw.setdefault("duration_minutes", DAY)
    return Task(unique_id=uid, name=f"T{uid}", **kw)  # type: ignore[arg-type]


def _sched(
    tasks: list[Task], rels: tuple[Relationship, ...] = (), labels: tuple[str, ...] = ()
) -> Schedule:
    return Schedule(
        name="g",
        source_file="g.mpp",
        project_start=MON,
        status_date=MON + dt.timedelta(days=30),
        tasks=tuple(tasks),
        relationships=rels,
        custom_field_labels=labels,
    )


def _grouped() -> Schedule:
    tasks = [
        _task(1, custom_fields=(("CA-WBS", "4.1.4.1"), ("CAM", "Chris")), resource_names=("Eng",)),
        _task(
            2, custom_fields=(("CA-WBS", "4.1.4.1"), ("CAM", "Dana")), resource_names=("Eng", "QA")
        ),
        _task(3, custom_fields=(("CA-WBS", "4.1.5.2"),), resource_names=("QA",)),
        _task(4, wbs="X", is_milestone=True, duration_minutes=0),
    ]
    rels = (
        Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),  # within 4.1.4.1
        Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS),  # crosses groups
    )
    return _sched(tasks, rels, labels=("CA-WBS", "CAM"))


def test_field_value_prefers_custom_then_standard() -> None:
    s = _grouped()
    by = {t.unique_id: t for t in s.tasks}
    assert field_value(s, by[1], "CA-WBS") == "4.1.4.1"  # custom field
    assert field_value(s, by[4], "Activity Type") == "Milestone"  # standard
    assert field_value(s, by[1], "Activity Type") == "Normal"
    assert field_value(s, by[1], "Resource") == "Eng"
    assert field_value(s, by[3], "CA-WBS") == "4.1.5.2"
    assert field_value(s, by[3], "CAM") is None  # unset custom field


def test_available_fields_lists_standard_then_custom() -> None:
    fields = available_fields(_grouped())
    assert fields[: len(("WBS",))] == ("WBS",)  # standard come first
    assert "Activity Type" in fields and "Resource" in fields
    assert fields[-2:] == ("CA-WBS", "CAM")  # custom labels last, in declared order


def test_task_matches_is_an_AND_across_criteria() -> None:
    s = _grouped()
    by = {t.unique_id: t for t in s.tasks}
    assert task_matches(s, by[1], [("CA-WBS", "4.1.4.1"), ("CAM", "Chris")])
    assert not task_matches(s, by[2], [("CA-WBS", "4.1.4.1"), ("CAM", "Chris")])  # CAM differs
    # Resource is multi-valued: a criterion matches when the task carries that resource
    assert task_matches(s, by[2], [("Resource", "QA")])
    assert not task_matches(s, by[1], [("Resource", "QA")])
    # an empty value just requires the field to be populated
    assert task_matches(s, by[1], [("CAM", "")])
    assert not task_matches(s, by[3], [("CAM", "")])


def test_select_returns_matching_uids_and_caps_field_count() -> None:
    s = _grouped()
    assert select(s, [("CA-WBS", "4.1.4.1")]) == (1, 2)
    with pytest.raises(ValueError, match="at most 5"):
        select(s, [("WBS", "x")] * (MAX_FIELDS + 1))


def test_filter_schedule_keeps_subset_and_internal_relationships_only() -> None:
    s = _grouped()
    sub = filter_schedule(s, [("CA-WBS", "4.1.4.1")])
    assert {t.unique_id for t in sub.tasks} == {1, 2}
    # 1->2 is internal (kept); 2->3 crosses out of the group (dropped)
    assert len(sub.relationships) == 1
    assert sub.relationships[0].predecessor_id == 1 and sub.relationships[0].successor_id == 2
    # project frame + custom-field labels are preserved for the downstream engine
    assert sub.status_date == s.status_date and sub.custom_field_labels == s.custom_field_labels


def test_filter_schedule_empty_selection_yields_no_tasks() -> None:
    sub = filter_schedule(_grouped(), [("CA-WBS", "nope")])
    assert sub.tasks == () and sub.relationships == ()


def test_group_values_splits_a_field_into_per_value_uid_groups() -> None:
    s = _grouped()
    assert group_values(s, "CA-WBS") == {"4.1.4.1": (1, 2), "4.1.5.2": (3,)}
    # Resource expands: a task with two resources lands in both groups, values sorted
    assert group_values(s, "Resource") == {"Eng": (1, 2), "QA": (2, 3)}
