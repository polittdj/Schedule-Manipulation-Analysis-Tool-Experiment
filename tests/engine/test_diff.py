"""Version-diff tests — golden P2→P5 structural delta + synthetic field/logic cases."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.diff import diff_versions
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _s(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


def test_golden_diff_p2_to_p5(golden_project2: Schedule, golden_project5: Schedule) -> None:
    d = diff_versions(golden_project2, golden_project5)
    assert d.prior_file == "Project2.mspdi.xml" and d.current_file == "Project5.mspdi.xml"
    assert d.added_tasks == () and d.deleted_tasks == ()  # identical UID set
    assert (
        len(d.changed_tasks) == 106
    )  # forecast dates / progress shifted as the data date advanced
    assert len(d.added_links) == 2 and d.removed_links == ()
    # the focus activity moved its forecast finish but its baseline did not (honest progress)
    td = d.task_diff(143)
    assert td is not None and td.changed("finish") is not None
    assert td.changed("baseline_finish") is None


def test_diff_added_and_deleted_tasks_by_uid() -> None:
    prior = _s([Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (1, 2, 3)])
    current = _s([Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (2, 3, 4)])
    d = diff_versions(prior, current)
    assert d.added_tasks == (4,) and d.deleted_tasks == (1,)


def test_diff_field_deltas() -> None:
    bf0 = dt.datetime(2025, 2, 1, 17, 0)
    prior = _s([Task(unique_id=1, name="A", duration_minutes=2 * DAY, baseline_finish=bf0)])
    current = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=5 * DAY,
                percent_complete=50.0,
                baseline_finish=dt.datetime(2025, 3, 1, 17, 0),
                constraint_type=ConstraintType.SNET,
                constraint_date=MON,
            )
        ]
    )
    d = diff_versions(prior, current)
    td = d.task_diff(1)
    assert td is not None
    dur = td.changed("duration_minutes")
    assert dur is not None and dur.before == 2 * DAY and dur.after == 5 * DAY
    assert td.changed("baseline_finish") is not None
    assert td.changed("percent_complete") is not None
    assert td.changed("constraint_type") is not None


def test_diff_logic_added_and_removed() -> None:
    tasks = [Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (1, 2, 3)]
    prior = _s(tasks, [Relationship(predecessor_id=1, successor_id=2)])
    current = _s(tasks, [Relationship(predecessor_id=2, successor_id=3)])
    d = diff_versions(prior, current)
    assert d.added_links == ((2, 3, RelationshipType.FS, 0),)
    assert d.removed_links == ((1, 2, RelationshipType.FS, 0),)
    assert d.changed_tasks == ()  # tasks themselves are unchanged
