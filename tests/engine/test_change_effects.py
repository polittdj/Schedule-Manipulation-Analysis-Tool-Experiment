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


def test_reschedule_artifact_constraints_are_flagged_and_date_only_moves_revert() -> None:
    """Operator 2026-07-09 (updated2→updated3 investigation): MS Project's 'reschedule
    uncompleted work' stamps SNET-at-data-date constraints on pushed incomplete tasks. Those
    reverts are REAL (still measured) but flagged is_reschedule_artifact so the UI clusters
    them; a deliberate SNET at any other date is NOT flagged; and a DATE-only constraint move
    (same type, new date) triggers a revert at all (it previously slipped through)."""
    from schedule_forensics.model.task import ConstraintType

    status = dt.datetime(2025, 2, 3, 17, 0)
    rels = [Relationship(predecessor_id=1, successor_id=4)]

    def _cur_task(uid: int, ctype: ConstraintType, cdate: dt.datetime | None) -> Task:
        return Task(
            unique_id=uid,
            name=f"T{uid}",
            duration_minutes=5 * DAY,
            constraint_type=ctype,
            constraint_date=cdate,
        )

    prior = Schedule(
        name="S",
        project_start=MON,
        tasks=(
            _task(1, 5),  # ASAP → SNET@status (artifact)
            _task(2, 5),  # ASAP → SNET@other date (deliberate)
            _cur_task(3, ConstraintType.SNET, MON),  # SNET date-only move → status (artifact)
            _task(4, 0, is_milestone=True),
            _task(5, 5, percent_complete=100.0),  # COMPLETE: ASAP → SNET@status (NOT an artifact)
        ),
        relationships=tuple(rels),
    )
    complete_snet = Task(
        unique_id=5,
        name="T5",
        duration_minutes=5 * DAY,
        percent_complete=100.0,
        constraint_type=ConstraintType.SNET,
        constraint_date=status,
    )
    current = Schedule(
        name="S",
        project_start=MON,
        status_date=status,
        tasks=(
            _cur_task(1, ConstraintType.SNET, status),
            _cur_task(2, ConstraintType.SNET, dt.datetime(2025, 3, 10, 8, 0)),
            _cur_task(3, ConstraintType.SNET, status),
            _task(4, 0, is_milestone=True),
            complete_snet,
        ),
        relationships=tuple(rels),
    )
    r = compute_change_effects(prior, current, target_uid=4)
    assert r is not None
    con = {e.citation_uids[0]: e for e in r.per_change if e.kind == "constraint_restored"}
    assert set(con) == {1, 2, 3, 5}  # the date-only move on UID 3 IS reverted
    assert con[1].is_reschedule_artifact is True
    assert con[2].is_reschedule_artifact is False  # deliberate date ≠ data date
    assert con[3].is_reschedule_artifact is True
    # MS Project only reschedules UNCOMPLETED work: SNET@data-date on a 100%-complete task is a
    # deliberate edit, never the statusing artifact.
    assert con[5].is_reschedule_artifact is False
    # labels state direction plainly: now <current> → was <prior>
    assert "now SNET 2025-02-03 → was ASAP" in con[1].label
    assert "was SNET 2025-01-06" in con[3].label
    # artifact reverts are measured LAST (deferred behind every real change)
    kinds = [e.is_reschedule_artifact for e in r.per_change]
    assert kinds == sorted(kinds)  # all False rows precede all True rows


def test_measurement_cap_starves_artifacts_not_real_changes() -> None:
    """The 2026-07-09 forensic re-audit's one confirmed engine issue: on a pair whose diff
    exceeds ``_MAX_CHANGE_EFFECTS``, the cap previously starved whatever came last in detection
    order — which could be DELIBERATE changes while zero-effect statusing artifacts consumed
    slots (Hard_File→updated3 read '35 artifacts' instead of the true 44 while real edits went
    unmeasured). Artifact reverts now run last: every genuine change is measured, only artifact
    rows are capped, and the capped-artifact count is disclosed separately."""
    from schedule_forensics.engine.change_effects import _MAX_CHANGE_EFFECTS
    from schedule_forensics.model.task import ConstraintType

    status = dt.datetime(2025, 2, 3, 17, 0)
    n_genuine = 5
    n_artifacts = _MAX_CHANGE_EFFECTS  # genuine + artifacts exceeds the cap by n_genuine

    prior_tasks: list[Task] = []
    cur_tasks: list[Task] = []
    # UIDs 1..5: real duration changes, detected BEFORE the constraint sweep
    for uid in range(1, n_genuine + 1):
        prior_tasks.append(_task(uid, 10))
        cur_tasks.append(_task(uid, 5))
    # UIDs 101..160: artifact-pattern constraint stamps (ASAP → SNET at the data date, incomplete)
    for uid in range(101, 101 + n_artifacts):
        prior_tasks.append(_task(uid, 5))
        cur_tasks.append(
            Task(
                unique_id=uid,
                name=f"T{uid}",
                duration_minutes=5 * DAY,
                constraint_type=ConstraintType.SNET,
                constraint_date=status,
            )
        )
    prior = Schedule(name="S", project_start=MON, tasks=tuple(prior_tasks))
    current = Schedule(name="S", project_start=MON, status_date=status, tasks=tuple(cur_tasks))
    r = compute_change_effects(prior, current, target_uid=1)
    assert r is not None
    genuine = [e for e in r.per_change if not e.is_reschedule_artifact]
    artifacts = [e for e in r.per_change if e.is_reschedule_artifact]
    assert len(genuine) == n_genuine  # every real change measured — none starved
    assert len(r.per_change) == _MAX_CHANGE_EFFECTS
    assert len(artifacts) == _MAX_CHANGE_EFFECTS - n_genuine
    assert r.skipped_capped == n_genuine  # the overflow is artifact rows only…
    assert r.skipped_capped_artifacts == n_genuine  # …and disclosed as artifact-pattern
    # the disclosed artifact total (measured + capped) is the true detected count
    assert len(artifacts) + r.skipped_capped_artifacts == n_artifacts
    # ADR-0369: every capped change is disclosed by IDENTITY too, not count-only
    assert len(r.skipped_capped_labels) == r.skipped_capped
    assert all("constraint" in lb for lb in r.skipped_capped_labels)


def test_sub_day_effects_carry_exact_minutes_and_days_keep_rounding() -> None:
    """Audit F1 (2026-08-07): ``round()`` maps a true sub-day effect — even exactly half a day,
    via round-half-even — to 0 working days, which the page rendered "no effect". The int-day
    fields keep their legacy rounding (pinned here, unchanged contract for every consumer); the
    NEW ``*_minutes`` fields carry the exact truth the presentation renders as "<1 wd"."""
    # (cut_minutes, legacy_rounded_days) — derived from round(minutes/480): 240 is EXACTLY half
    # a working day and round-half-even sends it to 0 (not 1); 241 crosses to 1; 60/235 round 0.
    for cut, days in ((60, 0), (235, 0), (240, 0), (241, 1)):
        rels = [Relationship(predecessor_id=1, successor_id=2)]
        prior = _sched(
            [
                Task(unique_id=1, name="T1", duration_minutes=10 * DAY + cut),
                _task(2, 0, is_milestone=True),
            ],
            rels,
        )
        current = _sched([_task(1, 10), _task(2, 0, is_milestone=True)], rels)
        r = compute_change_effects(prior, current, target_uid=2)
        assert r is not None
        e = next(x for x in r.per_change if x.kind == "duration_restored")
        # restoring the prior (longer) duration pushes the milestone out exactly `cut` minutes
        assert e.target_finish_delta_minutes == cut
        assert e.project_finish_delta_minutes == cut
        assert e.target_finish_delta_days == days
        assert e.project_finish_delta_days == days
        # single measured change → the aggregate carries the same exact minutes
        assert r.aggregate_target_finish_delta_minutes == cut
        assert r.aggregate_project_finish_delta_minutes == cut
        assert r.aggregate_target_finish_delta_days == days


def test_sub_day_negative_effect_keeps_sign_in_minutes() -> None:
    # current RAISED the duration by 240 min: reverting pulls the milestone IN — negative minutes
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    prior = _sched([_task(1, 10), _task(2, 0, is_milestone=True)], rels)
    current = _sched(
        [
            Task(unique_id=1, name="T1", duration_minutes=10 * DAY + 240),
            _task(2, 0, is_milestone=True),
        ],
        rels,
    )
    r = compute_change_effects(prior, current, target_uid=2)
    assert r is not None
    e = next(x for x in r.per_change if x.kind == "duration_restored")
    assert e.target_finish_delta_minutes == -240
    assert e.target_finish_delta_days == 0  # legacy round-half-even pinned (unchanged)
    assert r.aggregate_target_finish_delta_minutes == -240


def test_duration_label_shows_sub_day_durations_exactly() -> None:
    """Audit F7: the floor-divided label rendered a 240→60 min cut as "cut 0→0 wd". A fractional
    side now renders 2-dp days with the exact minutes riding along; whole-day pairs keep the old
    label text verbatim (the true-positive twin)."""
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    prior = _sched(
        [Task(unique_id=1, name="T1", duration_minutes=240), _task(2, 0, is_milestone=True)], rels
    )
    current = _sched(
        [Task(unique_id=1, name="T1", duration_minutes=60), _task(2, 0, is_milestone=True)], rels
    )
    r = compute_change_effects(prior, current, target_uid=2)
    assert r is not None
    e = next(x for x in r.per_change if x.kind == "duration_restored")
    assert "0→0 wd" not in e.label
    assert e.label == "restore UID 1 duration (cut 0.12→0.5 wd (60→240 min))"
    # whole-day twin: the pre-fix label text is preserved byte-for-byte
    prior2 = _sched([_task(1, 20), _task(2, 0, is_milestone=True)], rels)
    current2 = _sched([_task(1, 10), _task(2, 0, is_milestone=True)], rels)
    r2 = compute_change_effects(prior2, current2, target_uid=2)
    assert r2 is not None
    e2 = next(x for x in r2.per_change if x.kind == "duration_restored")
    assert e2.label == "restore UID 1 duration (cut 10→20 wd)"


def test_sub_day_lag_label_does_not_collapse_to_zero_days() -> None:
    # a removed FS link carrying a 240-min lag: the old label floor-divided it to "(lag +0d)"
    tasks = [_task(1, 10), _task(2, 10), _task(3, 0, is_milestone=True)]
    current = _sched(tasks, [Relationship(predecessor_id=2, successor_id=3)])
    prior = _sched(
        tasks,
        [
            Relationship(predecessor_id=1, successor_id=2, lag_minutes=240),
            Relationship(predecessor_id=2, successor_id=3),
        ],
    )
    r = compute_change_effects(prior, current, target_uid=3)
    assert r is not None
    link = next(e for e in r.per_change if e.kind == "logic_restored")
    assert "(lag +0d)" not in link.label
    assert "+240 min" in link.label
    # whole-day-lag twin keeps the old byte-identical form
    prior2 = _sched(
        tasks,
        [
            Relationship(predecessor_id=1, successor_id=2, lag_minutes=2 * DAY),
            Relationship(predecessor_id=2, successor_id=3),
        ],
    )
    r2 = compute_change_effects(prior2, current, target_uid=3)
    assert r2 is not None
    link2 = next(e for e in r2.per_change if e.kind == "logic_restored")
    assert "(lag +2d)" in link2.label


def test_target_unavailable_returns_a_disclosed_sentinel_not_none() -> None:
    """Audit F2 (ADR-0369): an unresolvable target used to return None — indistinguishable from
    "no changes detected" — so /integrity omitted the panel silently. The sentinel report names
    the failed target, carries NO measurement (per_change empty, aggregate_solved False), and
    the no-changes case still returns None (the contract every caller relies on)."""
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    prior = _sched([_task(1, 20), _task(2, 0, is_milestone=True)], rels)
    current = _sched([_task(1, 10), _task(2, 0, is_milestone=True)], rels)
    r = compute_change_effects(prior, current, target_uid=999)  # UID 999 does not exist
    assert r is not None
    assert r.target_unavailable is True
    assert r.target_uid == 999 and r.target_name == ""
    assert r.per_change == () and r.aggregate_solved is False
    assert r.actual_target_finish == ""
    # true-positive twin: a resolvable target measures normally, flag off
    ok = compute_change_effects(prior, current, target_uid=2)
    assert ok is not None and ok.target_unavailable is False and ok.per_change
    # and the no-changes contract is unchanged: identical pair → None (never a sentinel)
    assert compute_change_effects(current, current, target_uid=2) is None


def test_unsolvable_revert_labels_are_disclosed() -> None:
    """Audit F2 (ADR-0369): the skip COUNT was disclosed but not WHICH change — the labels
    tuple carries the same plain-English text a measured row would have carried."""
    tasks = [_task(1, 10), _task(2, 10), _task(3, 0, is_milestone=True)]
    prior = _sched(tasks, [Relationship(predecessor_id=1, successor_id=2)])
    current = _sched(tasks, [Relationship(predecessor_id=2, successor_id=1)])
    # diff: removed 1→2, added 2→1. Restoring 1→2 onto current (which has 2→1) closes a logic
    # cycle → that revert is unsolvable; dropping the added 2→1 measures fine.
    r = compute_change_effects(prior, current, target_uid=3)
    assert r is not None
    assert r.skipped_unsolvable == 1
    assert r.skipped_unsolvable_labels == ("restore removed FS link 1→2",)
    assert len(r.skipped_unsolvable_labels) == r.skipped_unsolvable
    measured = [e.label for e in r.per_change]
    assert "remove added FS link 2→1" in measured  # the solvable twin was measured, not listed


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
