"""Path-counterfactual coverage — constraint reverts, link-only reverts, removed leavers,
the relationship-dedup guard, and the unsolvable (cyclic) revert.

Targets the still-uncovered paths in :func:`compute_path_counterfactual`: a leaver removed
from the schedule entirely is skipped; a hard-constraint change is reverted (reason
``constraint_removed``); a duration RAISE leaves the reason at the constraint code; an
added-only logic change is dropped; duplicate restored links are de-duplicated; and a
revert that reconnects prior logic into a cycle degrades to ``uncomputable`` rather than
claiming a finish. Every finish move is hand-checked against the reverted change.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.path_counterfactual import compute_path_counterfactual
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

START = dt.datetime(2026, 1, 5, 8, 0)  # a Monday
DAY = 480


def test_constraint_change_reverted_and_duration_raise_keeps_constraint_reason() -> None:
    """A leaver whose hard constraint was dropped (and whose duration was RAISED, not cut) is
    reverted with reason ``constraint_removed`` — the duration-raise leaves the reason at the
    constraint code because only a cut sets ``duration_cut`` (path_counterfactual.py 136-142,
    branch 133->135)."""

    def mk(name: str, a_min: int, a_con: ConstraintType, b_min: int) -> Schedule:
        a = Task(
            unique_id=1,
            name="A",
            duration_minutes=a_min,
            constraint_type=a_con,
            constraint_date=START if a_con is not ConstraintType.ASAP else None,
        )
        b = Task(unique_id=2, name="B", duration_minutes=b_min)
        c = Task(unique_id=3, name="C", duration_minutes=2 * DAY)
        return Schedule(
            name=name,
            source_file=f"{name}.xml",
            project_start=START,
            tasks=(a, b, c),
            relationships=(
                Relationship(predecessor_id=1, successor_id=3),
                Relationship(predecessor_id=2, successor_id=3),
            ),
        )

    prior = mk("v1", 10 * DAY, ConstraintType.SNLT, 5 * DAY)  # A drives C
    # B drives C in current → A leaves the path; A's constraint was dropped and duration raised.
    current = mk("v2", 11 * DAY, ConstraintType.ASAP, 14 * DAY)
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    assert pc is not None
    assert [r.uid for r in pc.reverted] == [1]
    rev = pc.reverted[0]
    assert rev.reason == "constraint_removed"
    assert any(ch == "constraint ASAP→SNLT restored" for ch in rev.changes)
    assert any("duration raised" in ch for ch in rev.changes)  # raise verb, not "cut"


def test_duration_cut_plus_constraint_change_keeps_duration_cut_reason() -> None:
    """A leaver whose duration was CUT *and* whose constraint changed keeps reason
    ``duration_cut`` — the constraint arm does not overwrite it because ``reason`` is already
    set (path_counterfactual.py branch 141->143). Both changes are still recorded."""

    def mk(name: str, a_min: int, a_con: ConstraintType, b_min: int) -> Schedule:
        a = Task(
            unique_id=1,
            name="A",
            duration_minutes=a_min,
            constraint_type=a_con,
            constraint_date=START if a_con is not ConstraintType.ASAP else None,
        )
        b = Task(unique_id=2, name="B", duration_minutes=b_min)
        c = Task(unique_id=3, name="C", duration_minutes=2 * DAY)
        return Schedule(
            name=name,
            source_file=f"{name}.xml",
            project_start=START,
            tasks=(a, b, c),
            relationships=(
                Relationship(predecessor_id=1, successor_id=3),
                Relationship(predecessor_id=2, successor_id=3),
            ),
        )

    prior = mk("v1", 11 * DAY, ConstraintType.SNLT, 5 * DAY)  # A drives C
    # A is CUT (11d -> 3d) and its constraint dropped → A leaves the path; B(14) now drives.
    current = mk("v2", 3 * DAY, ConstraintType.ASAP, 14 * DAY)
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    assert pc is not None
    assert [r.uid for r in pc.reverted] == [1]
    rev = pc.reverted[0]
    assert rev.reason == "duration_cut"  # the cut reason wins; constraint arm does NOT overwrite
    assert any("duration cut" in ch for ch in rev.changes)
    assert any(ch == "constraint ASAP→SNLT restored" for ch in rev.changes)  # still recorded


def test_added_only_logic_change_is_dropped_and_reason_stays_changed() -> None:
    """A leaver that only had a link ADDED (none removed) has that link dropped in the revert;
    with no removed link the reason stays the generic ``changed`` (path_counterfactual.py 150,
    branches 147->149 and 152->154)."""

    def mk(name: str, b_min: int, *, link_xa: bool) -> Schedule:
        x = Task(unique_id=9, name="X", duration_minutes=DAY)
        a = Task(unique_id=1, name="A", duration_minutes=10 * DAY)
        b = Task(unique_id=2, name="B", duration_minutes=b_min)
        c = Task(unique_id=3, name="C", duration_minutes=2 * DAY)
        rels = [
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ]
        if link_xa:
            rels.append(Relationship(predecessor_id=9, successor_id=1))
        return Schedule(
            name=name,
            source_file=f"{name}.xml",
            project_start=START,
            tasks=(x, a, b, c),
            relationships=tuple(rels),
        )

    prior = mk("v1", 5 * DAY, link_xa=False)  # A(10) drives C
    current = mk("v2", 14 * DAY, link_xa=True)  # B(14) drives C → A leaves; X→A link added to A
    pc = compute_path_counterfactual(prior, current, compute_cpm(prior), compute_cpm(current))
    assert pc is not None
    assert [r.uid for r in pc.reverted] == [1]
    rev = pc.reverted[0]
    assert rev.reason == "changed"  # only an ADDED link → not "logic_removed"
    assert rev.changes == ("logic 1 link(s) removed",)  # the added link is dropped in the revert


def test_leaver_removed_from_schedule_is_skipped() -> None:
    """An activity that was on the prior critical path but is entirely absent in the current
    version is skipped (not a 'changed' activity) — path_counterfactual.py 108."""

    prior = Schedule(
        name="v1",
        source_file="v1.xml",
        project_start=START,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=10 * DAY),
            Task(unique_id=4, name="D", duration_minutes=2 * DAY),
            Task(unique_id=2, name="B", duration_minutes=5 * DAY),
            Task(unique_id=3, name="C", duration_minutes=2 * DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=4),  # A→D→C is the prior driver
            Relationship(predecessor_id=4, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )
    current = Schedule(
        name="v2",
        source_file="v2.xml",
        project_start=START,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=DAY),  # cut → leaves, reverted
            Task(unique_id=2, name="B", duration_minutes=5 * DAY),
            Task(unique_id=3, name="C", duration_minutes=2 * DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )
    prior_cpm, current_cpm = compute_cpm(prior), compute_cpm(current)
    assert 4 in prior_cpm.critical_path and 4 not in current.tasks_by_id  # D dropped entirely
    pc = compute_path_counterfactual(prior, current, prior_cpm, current_cpm, target_uid=3)
    assert pc is not None
    # D (UID 4) was critical and removed → skipped, never reverted; A (cut) is the reverted leaver.
    assert [r.uid for r in pc.reverted] == [1]
    assert 4 not in {r.uid for r in pc.reverted}
    assert pc.finish_delta_days > 0  # restoring A's full duration pushes the finish back out


def test_duplicate_restored_links_are_deduplicated() -> None:
    """A prior version that carries a duplicate logic link touching a reverted activity yields
    two identical entries in the restore set; the dedup loop drops the second
    (path_counterfactual.py 207). The counterfactual still solves."""

    def mk(name: str, a_min: int, *, dup: bool) -> Schedule:
        a = Task(unique_id=1, name="A", duration_minutes=a_min)
        b = Task(unique_id=2, name="B", duration_minutes=5 * DAY)
        c = Task(unique_id=3, name="C", duration_minutes=2 * DAY)
        rels = [
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ]
        if dup:
            rels.append(Relationship(predecessor_id=1, successor_id=3))  # identical A→C
        return Schedule(
            name=name,
            source_file=f"{name}.xml",
            project_start=START,
            tasks=(a, b, c),
            relationships=tuple(rels),
        )

    prior = mk("v1", 10 * DAY, dup=True)  # A drives C, with a duplicate A→C link
    current = mk("v2", 3 * DAY, dup=False)  # A cut → B drives, A leaves and is reverted
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    assert pc is not None
    assert not pc.uncomputable
    assert [r.uid for r in pc.reverted] == [1]
    # restoring A's 10-day duration moves the finish out exactly the cut amount (10d - 3d = 7d).
    assert pc.finish_delta_days == 7


def test_revert_that_forms_a_cycle_is_uncomputable() -> None:
    """When restoring a reverted activity's prior links reconnects logic into a directed cycle,
    re-running CPM raises; the panel degrades to naming the activity with ``uncomputable=True``
    and no claimed finish (path_counterfactual.py 214-217)."""

    # Reverted set is exactly {A=1}. Restoring A→X(6) and Y(7)→A, plus the kept X→Y(6→7) link
    # (which does not touch A), closes the cycle A→X→Y→A. P(8) is a long predecessor of A so Y
    # carries slack and never enters the critical path (so it is not itself reverted).
    def prior_s() -> Schedule:
        return Schedule(
            name="v1",
            source_file="v1.xml",
            project_start=START,
            tasks=(
                Task(unique_id=1, name="A", duration_minutes=5 * DAY),
                Task(unique_id=3, name="C", duration_minutes=5 * DAY),
                Task(unique_id=5, name="E", duration_minutes=DAY),
                Task(unique_id=6, name="X", duration_minutes=DAY),
                Task(unique_id=7, name="Y", duration_minutes=DAY),
                Task(unique_id=8, name="P", duration_minutes=10 * DAY),
            ),
            relationships=(
                Relationship(predecessor_id=8, successor_id=1),  # P→A (backbone)
                Relationship(predecessor_id=1, successor_id=3),  # A→C
                Relationship(predecessor_id=1, successor_id=6),  # A→X (restored)
                Relationship(predecessor_id=7, successor_id=1),  # Y→A (restored)
            ),
        )

    def cur_s() -> Schedule:
        return Schedule(
            name="v2",
            source_file="v2.xml",
            project_start=START,
            tasks=(
                Task(unique_id=1, name="A", duration_minutes=5 * DAY),
                Task(unique_id=3, name="C", duration_minutes=5 * DAY),
                Task(unique_id=5, name="E", duration_minutes=40 * DAY),  # E now drives → A leaves
                Task(unique_id=6, name="X", duration_minutes=DAY),
                Task(unique_id=7, name="Y", duration_minutes=DAY),
                Task(unique_id=8, name="P", duration_minutes=10 * DAY),
            ),
            relationships=(
                Relationship(predecessor_id=8, successor_id=1),  # P→A
                Relationship(predecessor_id=1, successor_id=3),  # A→C
                Relationship(predecessor_id=6, successor_id=7),  # X→Y (kept; closes the cycle)
            ),
        )

    prior, current = prior_s(), cur_s()
    pc = compute_path_counterfactual(prior, current, compute_cpm(prior), compute_cpm(current))
    assert pc is not None
    assert pc.uncomputable is True
    assert 1 in {r.uid for r in pc.reverted}  # A is named even though its finish is unclaimable
    # the panel degrades: no counterfactual finish is asserted (it equals the actual placeholder).
    assert pc.finish_delta_days == 0
    assert pc.counterfactual_finish == pc.actual_finish
