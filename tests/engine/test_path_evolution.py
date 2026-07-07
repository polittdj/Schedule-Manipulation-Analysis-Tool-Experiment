"""Critical-path evolution tests — entered/left/stayed, duration changes, finish move,
golden pins (M18 item 7, ADR-0044)."""

from __future__ import annotations

import datetime as dt
from itertools import pairwise

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.path_evolution import (
    _classify_entered,
    _classify_left,
    _links_touching,
    _PairContext,
    compute_path_evolution,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _chain(uids_durs: list[tuple[int, int]]) -> Schedule:
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=d * DAY) for u, d in uids_durs]
    rels = [
        Relationship(predecessor_id=a, successor_id=b) for (a, _), (b, _) in pairwise(uids_durs)
    ]
    return Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def _ev(schedules: list[Schedule]):
    cpms = [compute_cpm(s) for s in schedules]
    return compute_path_evolution(schedules, cpms)


def test_first_version_has_no_change_fields() -> None:
    ev = _ev([_chain([(1, 2), (2, 3)])])
    s = ev.snapshots[0]
    assert s.entered == () and s.left == () and s.stayed == ()
    assert s.finish_delta_days is None
    assert set(s.critical) == {1, 2}  # a single chain is all-critical


def test_entered_and_stayed_when_path_extends() -> None:
    v1 = _chain([(1, 2), (2, 3)])  # critical {1,2}
    v2 = _chain([(1, 2), (2, 3), (3, 1)])  # critical {1,2,3}
    ev = _ev([v1, v2])
    s = ev.snapshots[1]
    assert set(s.critical) == {1, 2, 3}
    assert s.entered == (3,)
    assert set(s.stayed) == {1, 2}
    assert s.left == ()
    assert s.finish_delta_days > 0  # extending the path pushes the finish later


def test_left_when_a_critical_task_is_removed() -> None:
    v1 = _chain([(1, 2), (2, 3), (3, 1)])  # critical {1,2,3}
    v2 = _chain([(1, 2), (2, 3)])  # task 3 gone -> critical {1,2}
    ev = _ev([v1, v2])
    s = ev.snapshots[1]
    assert set(s.critical) == {1, 2}
    assert s.left == (3,)  # was critical, now absent
    assert s.entered == ()
    assert s.finish_delta_days < 0  # removing a critical task pulls the finish in


def test_duration_change_on_path_is_flagged() -> None:
    v1 = _chain([(1, 2), (2, 3)])
    v2 = _chain([(1, 2), (2, 5)])  # task 2's duration changed, still critical
    ev = _ev([v1, v2])
    s = ev.snapshots[1]
    assert s.duration_changed == (2,)
    assert s.finish_delta_days > 0  # a longer critical task pushes the finish later


def test_empty_and_mismatched_inputs_raise() -> None:
    with pytest.raises(ValueError, match="at least one"):
        compute_path_evolution([], [])
    sch = _chain([(1, 1)])
    with pytest.raises(ValueError, match="parallel"):
        compute_path_evolution([sch, sch], [compute_cpm(sch)])


def test_golden_pins(golden_project2: Schedule, golden_project5: Schedule) -> None:
    ev = _ev([golden_project2, golden_project5])
    first, second = ev.snapshots
    assert first.finish_delta_days is None
    # ADR-0150: the path basis is the progress-aware EFFECTIVE critical set (stored Critical
    # flag first) — 41/4 are the Acumen-validated Critical counts (case.json; the pure-logic
    # CPM gave 43 on P2, and on the operator's progressed Large file collapsed to 2 of 33).
    assert len(first.critical) == 41 and len(second.critical) == 4
    # P2 -> P5 slips 148 calendar days (the Net Finish Impact on the authoritative file ADR-0112)
    assert second.finish_delta_days == 148
    assert len(second.left) == 38 and len(second.stayed) == 3 and second.entered == (131,)
    # the month-to-month "what got done on the path" record: exactly the left-with-reason
    # 'completed' set (4 activities on P2's path completed by P5)
    assert len(second.completed_on_path) == 4
    assert set(second.completed_on_path) == {
        c.uid for c in second.left_changes if c.reason == "completed"
    }
    # the authoritative P5 has 2 removed logic links and 1 new constraint-driven path entry
    assert second.shortened_on_path == () and second.removed_logic_count == 2
    # M18 follow-up: every 'left' activity is attributed a reason
    assert first.entered_changes == () and first.left_changes == ()
    assert {c.uid for c in second.left_changes} == set(second.left)
    assert {c.reason for c in second.left_changes} <= {"completed", "gained_float", "logic_removed"}
    # ADR-0057 — the detail (chip hover) is specific: completed cites progress %, and
    # gained_float quantifies the float-relevant movement vs the project finish.
    for c in second.left_changes:
        assert c.detail
        if c.reason == "completed":
            assert "%" in c.detail
        if c.reason == "gained_float":
            assert "project finish moved" in c.detail


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or ())
    )


def test_entered_attribution_reasons() -> None:
    """Each 'entered the path' reason code (M18 follow-up): new / duration / constraint /
    logic / slack-consumed."""

    def reason(uid: int, prior: Schedule, cur: Schedule) -> str:
        return _classify_entered(
            uid, cur, prior, _links_touching(cur), _links_touching(prior)
        ).reason

    a = Task(unique_id=1, name="A", duration_minutes=DAY)
    # NEW — the activity did not exist in the prior version
    assert (
        reason(9, _sched([a]), _sched([a, Task(unique_id=9, name="N", duration_minutes=DAY)]))
        == "new"
    )
    # DURATION increased
    assert (
        reason(
            2,
            _sched([Task(unique_id=2, name="B", duration_minutes=DAY)]),
            _sched([Task(unique_id=2, name="B", duration_minutes=3 * DAY)]),
        )
        == "duration_up"
    )
    # CONSTRAINT — a hard constraint was added
    assert (
        reason(
            3,
            _sched([Task(unique_id=3, name="C", duration_minutes=DAY)]),
            _sched(
                [
                    Task(
                        unique_id=3,
                        name="C",
                        duration_minutes=DAY,
                        constraint_type=ConstraintType.MFO,
                        constraint_date=MON,
                    )
                ]
            ),
        )
        == "constraint"
    )
    # LOGIC — a link was added on this activity (duration unchanged)
    d = Task(unique_id=4, name="D", duration_minutes=DAY)
    e = Task(unique_id=5, name="E", duration_minutes=DAY)
    assert (
        reason(5, _sched([d, e]), _sched([d, e], [Relationship(predecessor_id=4, successor_id=5)]))
        == "logic_added"
    )
    # SLACK CONSUMED — nothing about the activity changed (a slip elsewhere)
    assert (
        reason(
            6,
            _sched([Task(unique_id=6, name="F", duration_minutes=DAY)]),
            _sched([Task(unique_id=6, name="F", duration_minutes=DAY)]),
        )
        == "slack_consumed"
    )


def test_left_attribution_reasons() -> None:
    """Each 'left the path' reason code: removed / completed / duration / logic / gained-float."""

    def reason(uid: int, prior: Schedule, cur: Schedule) -> str:
        return _classify_left(uid, cur, prior, _links_touching(cur), _links_touching(prior)).reason

    # REMOVED — absent from the current version
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
            _sched([Task(unique_id=2, name="Z", duration_minutes=DAY)]),
        )
        == "removed"
    )
    # COMPLETED since the prior version
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
            _sched(
                [
                    Task(
                        unique_id=1,
                        name="A",
                        duration_minutes=DAY,
                        percent_complete=100.0,
                        actual_start=MON,
                        actual_finish=MON,
                    )
                ]
            ),
        )
        == "completed"
    )
    # DURATION shortened
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=3 * DAY)]),
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
        )
        == "duration_down"
    )
    # LOGIC removed from this activity
    p, q = (
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
    )
    assert (
        reason(2, _sched([p, q], [Relationship(predecessor_id=1, successor_id=2)]), _sched([p, q]))
        == "logic_removed"
    )
    # GAINED FLOAT — nothing about the activity changed
    assert (
        reason(
            1,
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
            _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
        )
        == "gained_float"
    )


# --- ADR-0057: reason specificity (the chip-hover detail) ------------------------------------


def _entered(uid: int, prior: Schedule, cur: Schedule, ctx: _PairContext | None = None):
    return _classify_entered(uid, cur, prior, _links_touching(cur), _links_touching(prior), ctx)


def _left(uid: int, prior: Schedule, cur: Schedule, ctx: _PairContext | None = None):
    return _classify_left(uid, cur, prior, _links_touching(cur), _links_touching(prior), ctx)


def test_duration_detail_is_quantified() -> None:
    """duration_up / duration_down cite the signed working-day delta, from→to, and percent."""
    up = _entered(
        2,
        _sched([Task(unique_id=2, name="B", duration_minutes=DAY)]),
        _sched([Task(unique_id=2, name="B", duration_minutes=3 * DAY)]),
    )
    assert up.reason == "duration_up"
    assert "+2wd" in up.detail and "1wd → 3wd" in up.detail and "+200%" in up.detail

    down = _left(
        1,
        _sched([Task(unique_id=1, name="A", duration_minutes=4 * DAY)]),
        _sched([Task(unique_id=1, name="A", duration_minutes=DAY)]),
    )
    assert down.reason == "duration_down"
    assert "-3wd" in down.detail and "4wd → 1wd" in down.detail and "-75%" in down.detail


def test_logic_added_detail_cites_the_predecessor_link() -> None:
    d = Task(unique_id=4, name="Design", duration_minutes=DAY)
    e = Task(unique_id=5, name="Build", duration_minutes=DAY)
    pc = _entered(
        5, _sched([d, e]), _sched([d, e], [Relationship(predecessor_id=4, successor_id=5)])
    )
    assert pc.reason == "logic_added"
    # an inbound predecessor link, naming the other endpoint + UID + type
    assert "←" in pc.detail and "Design" in pc.detail and "UID 4" in pc.detail and "FS" in pc.detail


def test_logic_removed_detail_cites_the_link() -> None:
    p = Task(unique_id=1, name="Procure", duration_minutes=DAY)
    q = Task(unique_id=2, name="Install", duration_minutes=DAY)
    pc = _left(2, _sched([p, q], [Relationship(predecessor_id=1, successor_id=2)]), _sched([p, q]))
    assert pc.reason == "logic_removed"
    assert "←" in pc.detail and "Procure" in pc.detail and "UID 1" in pc.detail


def test_logic_detail_caps_at_three_links() -> None:
    hub = Task(unique_id=10, name="Hub", duration_minutes=DAY)
    preds = [Task(unique_id=u, name=f"P{u}", duration_minutes=DAY) for u in range(1, 6)]
    rels = [Relationship(predecessor_id=u, successor_id=10) for u in range(1, 6)]
    pc = _entered(10, _sched([hub, *preds]), _sched([hub, *preds], rels))
    assert pc.reason == "logic_added"
    assert pc.detail.startswith("5 logic links added:") and "(+2 more)" in pc.detail


def test_slack_consumed_names_the_upstream_slip() -> None:
    """The unchanged activity that became critical names the upstream predecessor that slipped."""
    a = Task(unique_id=1, name="Pour Slab", duration_minutes=DAY)
    b = Task(unique_id=2, name="Inspect", duration_minutes=DAY)
    ctx = _PairContext(slip_days={1: 5, 2: 0}, cur_preds={2: (1,)}, finish_delta_days=5)
    pc = _entered(2, _sched([a, b]), _sched([a, b]), ctx)
    assert pc.reason == "slack_consumed"
    assert "Pour Slab" in pc.detail and "UID 1" in pc.detail and "5d later" in pc.detail


def test_slack_consumed_falls_back_to_the_largest_slip() -> None:
    """With no slipping predecessor, name the largest slip anywhere (honestly 'elsewhere')."""
    b = Task(unique_id=2, name="Inspect", duration_minutes=DAY)
    x = Task(unique_id=9, name="Far Away", duration_minutes=DAY)
    ctx = _PairContext(slip_days={2: 0, 9: 7}, cur_preds={}, finish_delta_days=7)
    pc = _entered(2, _sched([b, x]), _sched([b, x]), ctx)
    assert pc.reason == "slack_consumed"
    assert "Far Away" in pc.detail and "+7d" in pc.detail


def test_slack_consumed_stays_generic_without_context() -> None:
    """No movement context (the direct-call path) keeps the honest generic phrasing."""
    f = Task(unique_id=6, name="F", duration_minutes=DAY)
    pc = _entered(6, _sched([f]), _sched([f]))
    assert pc.reason == "slack_consumed" and "slip elsewhere" in pc.detail


def test_gained_float_quantifies_the_movement() -> None:
    a = Task(unique_id=1, name="A", duration_minutes=DAY)
    ctx = _PairContext(slip_days={1: 3}, cur_preds={}, finish_delta_days=99)
    pc = _left(1, _sched([a]), _sched([a]), ctx)
    assert pc.reason == "gained_float"
    assert "+3d" in pc.detail and "project finish moved +99d" in pc.detail


def test_completed_detail_cites_progress_and_finish() -> None:
    prior = _sched([Task(unique_id=1, name="A", duration_minutes=DAY)])
    cur = _sched(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_start=MON,
                actual_finish=MON,
            )
        ]
    )
    pc = _left(1, prior, cur)
    assert pc.reason == "completed"
    assert "100%" in pc.detail and "finished 2025-01-06" in pc.detail


def test_effective_basis_matches_stored_critical_flags(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    """Verification way 1 (ADR-0150): the evolution's critical set IS the source tool's
    stored, progress-aware Critical flag set — the Acumen-validated 41 (P2) / 4 (P5)."""
    from schedule_forensics.engine.path_evolution import effective_critical_set

    for sch, want in ((golden_project2, 41), (golden_project5, 4)):
        eff = effective_critical_set(sch, compute_cpm(sch))
        stored = {
            t.unique_id
            for t in sch.tasks
            if not t.is_summary and t.is_active and t.stored_is_critical
        }
        assert eff == stored and len(eff) == want


def test_targeted_evolution_uses_the_driving_path_to_the_focus() -> None:
    """With a focused UID the per-version path is the 0-driving-slack chain to it (the /path
    basis), not the float-critical set — a side branch with float stays off the path."""
    #  1 -> 2 -> 4 (main chain)  and  3 -> 4 (short side feeder with float)
    tasks = [
        Task(unique_id=1, name="T1", duration_minutes=5 * DAY),
        Task(unique_id=2, name="T2", duration_minutes=5 * DAY),
        Task(unique_id=3, name="T3", duration_minutes=1 * DAY),
        Task(unique_id=4, name="T4", duration_minutes=2 * DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=4),
        Relationship(predecessor_id=3, successor_id=4),
    ]
    sch = Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    ev = compute_path_evolution([sch], [compute_cpm(sch)], target_uid=4)
    assert set(ev.snapshots[0].critical) == {1, 2, 4}  # the driving chain; 3 has float
    # an unknown focus falls back to the effective critical set rather than erroring
    ev2 = compute_path_evolution([sch], [compute_cpm(sch)], target_uid=999)
    assert set(ev2.snapshots[0].critical) == {1, 2, 4}
