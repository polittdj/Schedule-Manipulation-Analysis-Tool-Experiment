"""Driving-path-between coverage — the ``status`` chip phrases, the ``_transition`` change
notes across versions, and the defensive input guards.

Targets :class:`DrivingPathSnapshot.status` (every state branch), :func:`_transition` (each
plain-English change note), and the two ``ValueError`` guards in
:func:`compute_driving_path_evolution`. The corridors are hand-verified small networks; the
cross-version transitions are driven through the public evolution function with real version
pairs where one endpoint or the connecting logic appears, disappears, or flips.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.driving_path import (
    DrivingPathBetween,
    DrivingPathSnapshot,
    _transition,
    compute_driving_path_evolution,
    driving_path_between,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _net() -> Schedule:
    """Focus 4(D). Driving corridor 2->3->4; 1->4 carries 2 days of slack."""
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
        Task(unique_id=3, name="C", duration_minutes=3 * DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=4),
        Relationship(predecessor_id=2, successor_id=4),
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
    ]
    return Schedule(name="net", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def _snapshot(between: DrivingPathBetween) -> DrivingPathSnapshot:
    """Wrap a corridor result in a snapshot so its ``status`` chip phrase can be read."""
    return DrivingPathSnapshot(
        label="v",
        status_date=None,
        between=between,
        names=(),
        entered=(),
        left=(),
        stayed=(),
        length_delta=None,
        change_note=None,
    )


# --- status chip phrases (DrivingPathSnapshot.status) ----------------------------------------


def test_status_phrase_driving_path() -> None:
    snap = _snapshot(driving_path_between(_net(), 2, 4))  # 2 drives 4 via 3
    assert snap.status == "driving path of 3 activities"


def test_status_phrase_connected_but_not_driving() -> None:
    snap = _snapshot(driving_path_between(_net(), 1, 4))  # 1 reaches 4 with 2 days slack
    assert snap.status == "connected — A holds 2d of slack to B (not driving)"


def test_status_phrase_no_logic_route() -> None:
    snap = _snapshot(driving_path_between(_net(), 4, 1))  # no route 4 -> 1
    assert snap.status == "no logic route A → B"


def test_status_phrase_target_absent() -> None:
    snap = _snapshot(driving_path_between(_net(), 2, 999))  # target not in schedule
    assert snap.status == "target activity absent"


def test_status_phrase_source_absent() -> None:
    snap = _snapshot(driving_path_between(_net(), 999, 4))  # source not in schedule
    assert snap.status == "source activity absent"


# --- _transition change notes ----------------------------------------------------------------


def _between(
    *,
    source_present: bool = True,
    target_present: bool = True,
    connected: bool = False,
    drives: bool = False,
    slack: int | None = None,
    path: tuple[int, ...] = (),
) -> DrivingPathBetween:
    return DrivingPathBetween(1, 2, path, source_present, target_present, connected, drives, slack)


def test_transition_target_appeared_and_removed() -> None:
    assert (
        _transition(_between(target_present=False), _between(target_present=True))
        == "target activity appeared"
    )
    assert (
        _transition(_between(target_present=True), _between(target_present=False))
        == "target activity removed"
    )


def test_transition_source_appeared_and_removed() -> None:
    assert (
        _transition(_between(source_present=False), _between(source_present=True))
        == "source activity appeared"
    )
    assert (
        _transition(_between(source_present=True), _between(source_present=False))
        == "source activity removed"
    )


def test_transition_driving_path_appeared_from_disconnected() -> None:
    # prior: not connected; cur: drives. The corridor materializes from nothing.
    note = _transition(
        _between(connected=False, drives=False),
        _between(connected=True, drives=True, path=(1, 2)),
    )
    assert note == "driving path appeared"


def test_transition_driving_path_broke_when_route_lost() -> None:
    # prior: drives; cur: no longer connected at all -> the path broke entirely.
    note = _transition(
        _between(connected=True, drives=True, path=(1, 2)),
        _between(connected=False, drives=False),
    )
    assert note == "driving path broke"


def test_transition_a_stopped_driving_but_still_connected() -> None:
    # prior: drives; cur: connected but carries slack -> stopped driving (route intact).
    note = _transition(
        _between(connected=True, drives=True, path=(1, 2)),
        _between(connected=True, drives=False, slack=3),
    )
    assert note == "A stopped driving B"


def test_transition_logic_route_lost_and_gained_without_driving() -> None:
    # connected (carrying slack) -> not connected: the route is lost without ever driving.
    lost = _transition(
        _between(connected=True, drives=False, slack=2),
        _between(connected=False, drives=False),
    )
    assert lost == "logic route A → B lost"
    # not connected -> connected (still carrying slack): the route is gained without driving.
    gained = _transition(
        _between(connected=False, drives=False),
        _between(connected=True, drives=False, slack=2),
    )
    assert gained == "logic route A → B gained"


def test_transition_none_when_state_unchanged() -> None:
    same = _between(connected=True, drives=True, path=(1, 2))
    assert _transition(same, same) is None


# --- transitions exercised end-to-end through the public evolution function ------------------


def test_evolution_reports_target_appearing_across_versions() -> None:
    """v1 has no target (4); v2 adds it as the sink driven by 2 — the note says it appeared."""
    v1_tasks = [
        Task(unique_id=2, name="B", duration_minutes=DAY),
        Task(unique_id=3, name="C", duration_minutes=3 * DAY),
    ]
    v1 = Schedule(
        name="net",
        project_start=MON,
        source_file="v1.xml",
        tasks=tuple(v1_tasks),
        relationships=(Relationship(predecessor_id=2, successor_id=3),),
    )
    v2 = _net()
    v2 = Schedule(
        name="net",
        project_start=MON,
        source_file="v2.xml",
        tasks=v2.tasks,
        relationships=v2.relationships,
    )
    schedules = [v1, v2]
    cpms = [compute_cpm(s) for s in schedules]
    ev = compute_driving_path_evolution(schedules, cpms, 2, 4)
    assert ev.snapshots[0].between.target_present is False
    assert ev.snapshots[1].change_note == "target activity appeared"


# --- defensive input guards ------------------------------------------------------------------


def test_empty_schedules_raises() -> None:
    with pytest.raises(ValueError, match="at least one schedule version"):
        compute_driving_path_evolution([], [], 1, 2)


def test_mismatched_cpms_raises() -> None:
    s = _net()
    with pytest.raises(ValueError, match="cpms must parallel schedules"):
        compute_driving_path_evolution([s, s], [compute_cpm(s)], 1, 2)
