"""Constraint-health engine tests — unsatisfied date constraints + deadline negative float.

Both compare the trusted CPM early dates against the activity's own imposed date, so a violation is
exactly the negative-float condition. Parity-isolated lightweight dataclasses.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics.constraint_health import compute_constraint_health
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday
DAY = 480


def _task(uid: int, dur_days: float = 1, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS)


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or [])
    )


def _check(schedule: Schedule, key: str) -> object:
    cpm = compute_cpm(schedule)
    return {c.key: c for c in compute_constraint_health(schedule, cpm).checks}[key]


# ── unsatisfied date constraint ──────────────────────────────────────────────────────────


def test_fnlt_violated_when_logic_finishes_after_the_cap() -> None:
    # 1 (10d) -> 2 (5d); 2 carries FNLT at day ~5, but logic finishes it at day 15
    t2 = _task(
        2, 5, constraint_type=ConstraintType.FNLT, constraint_date=dt.datetime(2025, 1, 10, 17, 0)
    )
    c = _check(_sched([_task(1, 10), t2], [_rel(1, 2)]), "unsatisfied_constraint")
    assert c.count == 1
    assert c.offenders == (2,)
    assert c.population == 1


def test_fnlt_satisfied_when_logic_finishes_before_the_cap() -> None:
    # the cap is far in the future → satisfied
    t2 = _task(
        2, 5, constraint_type=ConstraintType.FNLT, constraint_date=dt.datetime(2025, 6, 1, 17, 0)
    )
    c = _check(_sched([_task(1, 10), t2], [_rel(1, 2)]), "unsatisfied_constraint")
    assert c.count == 0
    assert c.population == 1


def test_snlt_violated_when_logic_starts_after_the_cap() -> None:
    # 1 (10d) -> 2; 2 must START no later than day ~3, but logic starts it at day 10
    t2 = _task(
        2, 1, constraint_type=ConstraintType.SNLT, constraint_date=dt.datetime(2025, 1, 8, 8, 0)
    )
    c = _check(_sched([_task(1, 10), t2], [_rel(1, 2)]), "unsatisfied_constraint")
    assert c.count == 1
    assert c.offenders == (2,)


def test_unconstrained_schedule_has_no_violations() -> None:
    c = _check(_sched([_task(1, 5), _task(2, 5)], [_rel(1, 2)]), "unsatisfied_constraint")
    assert c.count == 0
    assert c.population == 0  # no hard constraints in the network


def test_summary_constrained_task_excluded() -> None:
    t1 = _task(
        1,
        5,
        is_summary=True,
        constraint_type=ConstraintType.FNLT,
        constraint_date=dt.datetime(2025, 1, 7, 17, 0),
    )
    c = _check(_sched([t1]), "unsatisfied_constraint")
    assert c.population == 0  # summaries are not schedulable activities


# ── deadline negative float ──────────────────────────────────────────────────────────────


def test_deadline_breached_when_logic_finish_passes_it() -> None:
    t1 = _task(1, 10, deadline=dt.datetime(2025, 1, 10, 17, 0))  # logic finishes day 10 > deadline
    c = _check(_sched([t1]), "deadline_negative_float")
    assert c.count == 1
    assert c.offenders == (1,)
    assert c.population == 1


def test_deadline_met_when_logic_finish_is_before_it() -> None:
    t1 = _task(1, 3, deadline=dt.datetime(2025, 6, 1, 17, 0))
    c = _check(_sched([t1]), "deadline_negative_float")
    assert c.count == 0
    assert c.population == 1


def test_no_deadline_means_empty_population() -> None:
    c = _check(_sched([_task(1, 3)]), "deadline_negative_float")
    assert c.count == 0
    assert c.population == 0
