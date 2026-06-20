"""Edge-case unit tests for field-based grouping & filtering.

Targets the Resource 'any populated' rejection when a task carries no resource (grouping.py
106-107) and the custom-field de-duplication across schedules in available_fields_union (branch
79->78, where a label already collected is skipped). Asserts the real match results / field sets.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.grouping import available_fields_union, task_matches
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(tasks: list[Task], *, custom_labels: tuple[str, ...] = ()) -> Schedule:
    return Schedule(
        name="s",
        project_start=MON,
        tasks=tuple(tasks),
        relationships=(),
        custom_field_labels=custom_labels,
    )


# --- grouping.py:106-107 — Resource 'any populated' rejects a task with no resources ------------


def test_resource_any_populated_rejects_task_without_resources() -> None:
    """An empty Resource criterion means 'the Resource field is populated'. A task carrying no
    resource names fails it (grouping.py lines 106-107: `elif not names: return False`)."""
    no_resource = Task(unique_id=1, name="bare", duration_minutes=DAY, resource_names=())
    with_resource = Task(
        unique_id=2, name="staffed", duration_minutes=DAY, resource_names=("Alice",)
    )
    sch = _sched([no_resource, with_resource])
    criterion = [("Resource", "")]  # "" -> any populated value
    assert task_matches(sch, no_resource, criterion) is False  # no resources -> rejected
    assert task_matches(sch, with_resource, criterion) is True  # carries one -> accepted


def test_resource_specific_value_still_matches_when_carried() -> None:
    """Contrast (the `allowed` arm above line 106): a named-resource criterion matches only the
    task that actually carries that resource."""
    a = Task(unique_id=1, name="a", duration_minutes=DAY, resource_names=("Alice",))
    b = Task(unique_id=2, name="b", duration_minutes=DAY, resource_names=("Bob",))
    sch = _sched([a, b])
    criterion = [("Resource", "Alice")]
    assert task_matches(sch, a, criterion) is True
    assert task_matches(sch, b, criterion) is False


# --- grouping.py branch 79->78 — available_fields_union de-duplicates a shared custom field ------


def test_available_fields_union_deduplicates_a_custom_field_seen_in_two_schedules() -> None:
    """A custom field appearing in BOTH schedules is collected once (the `if label not in custom`
    is False on the second sighting -> branch 79->78 loops without appending)."""
    s1 = _sched(
        [Task(unique_id=1, name="T", duration_minutes=DAY)], custom_labels=("CA-WBS", "CAM")
    )
    s2 = _sched(
        [Task(unique_id=2, name="T", duration_minutes=DAY)],
        custom_labels=("CA-WBS", "Phase"),  # CA-WBS repeats; Phase is new
    )
    fields = available_fields_union([s1, s2])
    # CA-WBS appears exactly once despite being in both files
    assert fields.count("CA-WBS") == 1
    # first-seen custom order after the standard fields: CA-WBS, CAM (s1), then Phase (s2)
    custom_tail = fields[len(fields) - 3 :]
    assert custom_tail == ("CA-WBS", "CAM", "Phase")
