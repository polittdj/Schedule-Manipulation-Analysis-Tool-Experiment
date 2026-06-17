"""Critical-path counterfactual — revert the changes that took non-completed activities off
the path, re-run CPM, and report what the finish (and a target UID) would have been."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.path_counterfactual import compute_path_counterfactual
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

START = dt.datetime(2026, 1, 5, 8, 0)  # a Monday
DAY = 480  # working minutes per day (8h)


def _sched(name: str, a_minutes: int, *, a_complete: bool = False) -> Schedule:
    """A→C and B→C. A is the long driver in the prior; cutting A hands the path to B.

    UID 1 = A (variable duration), UID 2 = B (5 days), UID 3 = C (2 days, the target).
    """
    a = Task(
        unique_id=1,
        name="A",
        duration_minutes=a_minutes,
        percent_complete=100.0 if a_complete else 0.0,
        actual_start=START if a_complete else None,
        actual_finish=START + dt.timedelta(days=4) if a_complete else None,
    )
    b = Task(unique_id=2, name="B", duration_minutes=5 * DAY)
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


def test_counterfactual_restores_a_duration_cut_on_the_path() -> None:
    prior = _sched("v1", 10 * DAY)  # A (10d) drives C → A,C critical
    current = _sched("v2", 3 * DAY)  # A cut to 3d → B (5d) now drives C; A leaves the path
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    assert pc is not None
    # A (UID 1) left the path without completing and its duration changed → it is reverted
    assert [r.uid for r in pc.reverted] == [1]
    assert pc.reverted[0].reason == "duration_cut"
    assert any("duration" in ch for ch in pc.reverted[0].changes)
    assert not pc.gained_float  # nothing left the path "for free"
    # restoring A's 10-day duration pushes the finish back out (the cut had pulled it in)
    assert pc.finish_delta_days > 0
    assert pc.counterfactual_finish > pc.actual_finish
    # the target activity (C) finishes later in the counterfactual too
    assert pc.target_uid == 3 and pc.target_name == "C"
    assert pc.target_delta_days is not None and pc.target_delta_days > 0
    assert pc.target_counterfactual_finish > pc.target_actual_finish  # type: ignore[operator]


def test_completed_activity_is_excluded_from_the_revert() -> None:
    prior = _sched("v1", 10 * DAY)
    current = _sched("v2", 3 * DAY, a_complete=True)  # A is now 100% complete
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    # A was the only activity that left the path; completed work is never reverted → no result
    assert pc is None


def test_no_target_still_reports_the_project_finish_counterfactual() -> None:
    prior = _sched("v1", 10 * DAY)
    current = _sched("v2", 3 * DAY)
    pc = compute_path_counterfactual(prior, current, compute_cpm(prior), compute_cpm(current))
    assert pc is not None
    assert pc.target_uid is None and pc.target_delta_days is None
    assert pc.finish_delta_days > 0  # the project-finish counterfactual stands on its own


def _chain(name: str, *, link_ab: bool) -> Schedule:
    """A(10d) → B(2d) → C(2d, target). Dropping the A→B link takes B (and C) off the path."""
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=10 * DAY),
        Task(unique_id=2, name="B", duration_minutes=2 * DAY),
        Task(unique_id=3, name="C", duration_minutes=2 * DAY),
    )
    rels = [Relationship(predecessor_id=2, successor_id=3)]
    if link_ab:
        rels.insert(0, Relationship(predecessor_id=1, successor_id=2))
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=START,
        tasks=tasks,
        relationships=tuple(rels),
    )


def test_logic_removed_is_reverted_and_unchanged_leaver_is_gained_float() -> None:
    prior = _chain("v1", link_ab=True)  # A→B→C chain: A,B,C critical
    current = _chain("v2", link_ab=False)  # A→B removed: B no longer driven; B & C leave the path
    pc = compute_path_counterfactual(
        prior, current, compute_cpm(prior), compute_cpm(current), target_uid=3
    )
    assert pc is not None
    # B left because a link into it was removed → reverted (the link is restored)
    assert [r.uid for r in pc.reverted] == [2]
    assert pc.reverted[0].reason == "logic_removed"
    assert any("link" in ch for ch in pc.reverted[0].changes)
    # restoring the A→B link pushes the finish (and the target C) back out
    assert pc.finish_delta_days > 0
    assert pc.target_delta_days is not None and pc.target_delta_days > 0
    # C left the path unchanged (its own logic/duration are the same) → reported as gained float
    assert [g.uid for g in pc.gained_float] == [3]


def test_gained_float_only_returns_a_no_revert_explanation() -> None:
    # prior: A(10d)→C drives; current: B grows to 12d and drives, so A leaves UNCHANGED.
    def _two(name: str, b_minutes: int) -> Schedule:
        tasks = (
            Task(unique_id=1, name="A", duration_minutes=10 * DAY),
            Task(unique_id=2, name="B", duration_minutes=b_minutes),
            Task(unique_id=3, name="C", duration_minutes=2 * DAY),
        )
        return Schedule(
            name=name,
            source_file=f"{name}.xml",
            project_start=START,
            tasks=tasks,
            relationships=(
                Relationship(predecessor_id=1, successor_id=3),
                Relationship(predecessor_id=2, successor_id=3),
            ),
        )

    prior = _two("v1", 5 * DAY)  # A(10) drives C → A,C critical
    current = _two("v2", 12 * DAY)  # B(12) now drives C → A leaves, unchanged
    pc = compute_path_counterfactual(prior, current, compute_cpm(prior), compute_cpm(current))
    assert pc is not None
    assert pc.reverted == ()  # nothing to revert — the leaver was not itself changed
    assert [g.uid for g in pc.gained_float] == [1]
    assert pc.finish_delta_days == 0
