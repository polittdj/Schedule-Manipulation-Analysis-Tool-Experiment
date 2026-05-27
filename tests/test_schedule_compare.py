"""Tests for the field-by-field schedule diff (COM-vs-MPXJ validation primitive).

The diff is what gives ``scripts/validate_against_msp.py`` teeth: it must report a
real per-field disagreement (so a wrong COM enum/minute mapping cannot pass
silently) and stay quiet when two reads truly agree. Each test perturbs exactly
one thing and asserts exactly that difference (non-vacuous)."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.schedule_compare import diff_schedules
from schedule_forensics.schemas import ConstraintType, Relation, RelationType, Schedule, Task

START = dt.datetime(2025, 1, 6, 8, 0, 0)


def _task(uid: int, **over: object) -> Task:
    fields: dict[str, object] = {"unique_id": uid, "name": f"T{uid}", "duration_minutes": 480}
    fields.update(over)
    return Task(**fields)  # type: ignore[arg-type]


def _sched(tasks: list[Task], relations: tuple[Relation, ...] = (), **over: object) -> Schedule:
    fields: dict[str, object] = {
        "name": "P",
        "project_start": START,
        "tasks": tuple(tasks),
        "relations": relations,
    }
    fields.update(over)
    return Schedule(**fields)  # type: ignore[arg-type]


def test_identical_schedules_have_no_diff() -> None:
    a = _sched([_task(1), _task(2)], (Relation(predecessor_id=1, successor_id=2),))
    b = _sched([_task(1), _task(2)], (Relation(predecessor_id=1, successor_id=2),))
    assert diff_schedules(a, b) == []


def test_task_field_difference_is_reported_with_labels() -> None:
    a = _sched([_task(1, duration_minutes=480)])
    b = _sched([_task(1, duration_minutes=960)])
    diffs = diff_schedules(a, b, a_label="COM", b_label="MPXJ")
    assert diffs == ["task 1.duration_minutes: COM=480 MPXJ=960"]


def test_constraint_enum_difference_reported_as_value() -> None:
    # gotcha-10: a wrong ConstraintType code mapping would surface exactly here.
    a = _sched([_task(1, constraint_type=ConstraintType.SNET)])
    b = _sched([_task(1, constraint_type=ConstraintType.MSO)])
    diffs = diff_schedules(a, b)
    assert any("constraint_type" in d and "SNET" in d and "MSO" in d for d in diffs)


def test_task_present_in_one_side_only() -> None:
    a = _sched([_task(1), _task(2)])
    b = _sched([_task(1)])
    diffs = diff_schedules(a, b, a_label="COM", b_label="MPXJ")
    assert "task 2: present in COM only" in diffs


def test_schedule_level_field_difference() -> None:
    a = _sched([_task(1)], status_date=dt.datetime(2025, 3, 1))
    b = _sched([_task(1)], status_date=dt.datetime(2025, 4, 1))
    diffs = diff_schedules(a, b)
    assert any(d.startswith("schedule.status_date") for d in diffs)


def test_relation_type_and_lag_differences() -> None:
    rel_a = (Relation(predecessor_id=1, successor_id=2, type=RelationType.FS, lag_minutes=0),)
    rel_b = (Relation(predecessor_id=1, successor_id=2, type=RelationType.SS, lag_minutes=480),)
    a = _sched([_task(1), _task(2)], rel_a)
    b = _sched([_task(1), _task(2)], rel_b)
    diffs = diff_schedules(a, b)
    assert any("relation 1->2.type" in d and "FS" in d and "SS" in d for d in diffs)
    assert any("relation 1->2.lag_minutes" in d for d in diffs)


def test_relation_membership_difference() -> None:
    a = _sched([_task(1), _task(2)], (Relation(predecessor_id=1, successor_id=2),))
    b = _sched([_task(1), _task(2)], ())
    diffs = diff_schedules(a, b, a_label="COM", b_label="MPXJ")
    assert "relation 1->2: present in COM only" in diffs


def test_float_tolerance_suppresses_noise_but_reports_real_change() -> None:
    a = _sched([_task(1, percent_complete=50.0)])
    near = _sched([_task(1, percent_complete=50.0 + 1e-9)])
    assert diff_schedules(a, near) == []
    far = _sched([_task(1, percent_complete=51.0)])
    assert any("percent_complete" in d for d in diff_schedules(a, far))
