"""Per-change counterfactual EFFECT on a target activity (operator 2026-07-08, ADR-0162).

Reverting a removed predecessor link whose endpoints STAY critical must still show the finish
effect it hid — the case the path counterfactual misses and the AI previously answered "zero".
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.change_effects import compute_change_effects
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, dur_days: int, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=dur_days * DAY, **kw)


def _sched(tasks: list[Task], rels: list[Relationship]) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def test_restoring_a_removed_link_shows_the_hidden_slip() -> None:
    # prior: A(10d) -> B(10d) -> TARGET(0, milestone); C(30d) also -> TARGET.
    # current: the A->B link is REMOVED, so B can start at t0 and the chain A..B..TARGET no longer
    # governs — TARGET is pulled in. Restoring A->B pushes TARGET back out: the hidden slip.
    tasks = [
        _task(1, 10),  # A
        _task(2, 10),  # B
        _task(3, 30),  # C (a parallel driver)
        _task(4, 0, is_milestone=True),  # TARGET
    ]
    prior = _sched(
        tasks,
        [
            Relationship(predecessor_id=1, successor_id=2),  # A -> B  (removed in current)
            Relationship(predecessor_id=2, successor_id=4),  # B -> TARGET
            Relationship(predecessor_id=3, successor_id=4),  # C -> TARGET
        ],
    )
    current = _sched(
        tasks,
        [
            Relationship(predecessor_id=2, successor_id=4),  # B -> TARGET
            Relationship(predecessor_id=3, successor_id=4),  # C -> TARGET
        ],
    )
    report = compute_change_effects(prior, current, target_uid=4)
    assert report is not None
    assert report.target_uid == 4
    restore = [e for e in report.per_change if e.kind == "logic_restored"]
    assert len(restore) == 1
    # A->B restored makes the A(10)+B(10)=20d chain govern vs C's 30d — here 20 < 30, so no move.
    # Flip it: make A+B the longer chain to prove the effect is measured, not assumed.
    tasks2 = [_task(1, 25), _task(2, 25), _task(3, 30), _task(4, 0, is_milestone=True)]
    prior2 = _sched(
        tasks2,
        [
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=4),
            Relationship(predecessor_id=3, successor_id=4),
        ],
    )
    current2 = _sched(
        tasks2,
        [
            Relationship(predecessor_id=2, successor_id=4),
            Relationship(predecessor_id=3, successor_id=4),
        ],
    )
    r2 = compute_change_effects(prior2, current2, target_uid=4)
    assert r2 is not None
    link = next(e for e in r2.per_change if e.kind == "logic_restored")
    # current TARGET driven by max(B=25 from t0, C=30) = 30d; restored: A(25)+B(25)=50d governs.
    # 50 - 30 = 20 working days of hidden slip on the target and the project finish.
    assert link.target_finish_delta_days == 20
    assert link.project_finish_delta_days == 20
    assert 1 in link.citation_uids or 2 in link.citation_uids


def test_auto_target_is_the_last_critical_task_and_none_when_no_changes() -> None:
    tasks = [_task(1, 10), _task(2, 0, is_milestone=True)]
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    sch = _sched(tasks, rels)
    # identical prior/current → no changes → None
    assert compute_change_effects(sch, sch) is None
    # with a duration change and no explicit target, the report resolves an auto target
    prior = _sched([_task(1, 20), _task(2, 0, is_milestone=True)], rels)
    r = compute_change_effects(prior, sch)
    assert r is not None and r.target_is_last_critical
    cut = next(e for e in r.per_change if e.kind == "duration_restored")
    # restoring UID 1's duration 10→20 pushes the milestone out 10 working days
    assert cut.target_finish_delta_days == 10


def test_current_cpm_is_reused_when_supplied() -> None:
    tasks = [_task(1, 10), _task(2, 0, is_milestone=True)]
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    current = _sched(tasks, rels)
    prior = _sched([_task(1, 20), _task(2, 0, is_milestone=True)], rels)
    cpm = compute_cpm(current)
    r = compute_change_effects(prior, current, cpm, target_uid=2)
    assert r is not None and r.per_change


def test_relationship_type_is_preserved_in_the_key() -> None:
    # an FF link removed must be restored as FF, not silently coerced to FS
    tasks = [_task(1, 10), _task(2, 10), _task(3, 0, is_milestone=True)]
    prior = _sched(
        tasks,
        [
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FF),
            Relationship(predecessor_id=2, successor_id=3),
        ],
    )
    current = _sched(tasks, [Relationship(predecessor_id=2, successor_id=3)])
    r = compute_change_effects(prior, current, target_uid=3)
    assert r is not None
    assert any("FF" in e.label for e in r.per_change if e.kind == "logic_restored")
