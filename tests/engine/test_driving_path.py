"""Driving-path-between-two-UIDs tests — the corridor A→B and its cross-version evolution.

Built on the driving-slack engine: the corridor is the slice of B's driving path that lies on a
logic route from A. These are hand-verified small networks plus the version-stepping diff.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.driving_path import (
    compute_driving_path_evolution,
    driving_path_between,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _net() -> Schedule:
    # Focus = 4(D). Driving path 2(B,1d) -> 3(C,3d) -> 4(D,1d); 1(A,2d) -> 4 carries 2 days slack.
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


def test_corridor_on_the_driving_path() -> None:
    # 2 drives 4 via 3 (the long leg); the corridor 2->4 is exactly (2, 3, 4).
    r = driving_path_between(_net(), 2, 4)
    assert r.drives and r.connected
    assert r.path == (2, 3, 4)
    assert r.length == 3
    assert r.source_slack_days == 0


def test_source_connected_but_not_driving() -> None:
    # 1 reaches 4 but with 2 days of slack — connected, does not drive: no corridor, slack reported.
    r = driving_path_between(_net(), 1, 4)
    assert r.connected and not r.drives
    assert r.path == ()
    assert r.source_slack_days == 2


def test_source_not_connected() -> None:
    # 4 is the sink; 1 is not reachable FROM 4, so there is no route 4 -> 1.
    r = driving_path_between(_net(), 4, 1)
    assert not r.connected and not r.drives
    assert r.path == ()
    assert r.source_slack_days is None


def test_intermediate_source_trims_the_corridor() -> None:
    # Starting at 3 (already on the driving path) yields just the tail (3, 4), not (2, 3, 4).
    r = driving_path_between(_net(), 3, 4)
    assert r.drives and r.path == (3, 4)


def test_source_equals_target_is_degenerate_single_node() -> None:
    r = driving_path_between(_net(), 4, 4)
    assert r.drives and r.path == (4,) and r.source_slack_days == 0


def test_absent_or_summary_endpoints_flagged_not_raised() -> None:
    s = _net()
    missing = driving_path_between(s, 2, 999)
    assert not missing.target_present and missing.path == ()
    missing_src = driving_path_between(s, 999, 4)
    assert not missing_src.source_present and not missing_src.connected and missing_src.path == ()


def test_corridor_uses_cached_cpm() -> None:
    s = _net()
    cpm = compute_cpm(s)
    assert driving_path_between(s, 2, 4, cpm_result=cpm).path == (2, 3, 4)


# --- cross-version evolution ----------------------------------------------------------------


def _version(longer_five: bool, *, source_file: str, status: dt.datetime) -> Schedule:
    """Two parallel legs from 2 to 4: via 3(C) and via 5(E). Swinging E's duration flips which
    leg drives — ``longer_five`` makes the 5 leg the driver, otherwise the 3 leg drives."""
    e_dur = 5 * DAY if longer_five else DAY
    tasks = [
        Task(unique_id=2, name="B", duration_minutes=DAY),
        Task(unique_id=3, name="C", duration_minutes=3 * DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
        Task(unique_id=5, name="E", duration_minutes=e_dur),
    ]
    rels = [
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
        Relationship(predecessor_id=2, successor_id=5),
        Relationship(predecessor_id=5, successor_id=4),
    ]
    return Schedule(
        name="net",
        project_start=MON,
        source_file=source_file,
        status_date=status,
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )


def test_evolution_tracks_corridor_change_across_versions() -> None:
    v1 = _version(False, source_file="v1.xml", status=dt.datetime(2025, 2, 1))
    v2 = _version(True, source_file="v2.xml", status=dt.datetime(2025, 3, 1))
    schedules = [v1, v2]
    cpms = [compute_cpm(s) for s in schedules]

    ev = compute_driving_path_evolution(schedules, cpms, 2, 4)
    assert ev.source_uid == 2 and ev.target_uid == 4
    assert len(ev.snapshots) == 2

    first = ev.snapshots[0]
    assert first.between.path == (2, 3, 4)  # via the long C leg
    assert first.change_note is None  # no prior
    assert first.names == ("B", "C", "D")
    assert first.status_date == "2025-02-01"

    second = ev.snapshots[1]
    # E lengthened so the 5 leg now drives; the 3 leg drops off the corridor.
    assert second.between.path == (2, 5, 4)
    assert second.entered == (5,) and second.left == (3,)
    assert set(second.stayed) == {2, 4}
    assert second.length_delta == 0


def test_evolution_notes_when_driving_status_flips() -> None:
    # v1: 1 carries slack to 4 (not driving). v2: drop B's leg so 1 -> 4 is the only route.
    v1 = _net()
    v1 = Schedule(
        name="net",
        project_start=MON,
        source_file="v1.xml",
        tasks=v1.tasks,
        relationships=v1.relationships,
    )
    v2_tasks = [
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
    ]
    v2 = Schedule(
        name="net",
        project_start=MON,
        source_file="v2.xml",
        tasks=tuple(v2_tasks),
        relationships=(Relationship(predecessor_id=1, successor_id=4),),
    )
    schedules = [v1, v2]
    cpms = [compute_cpm(s) for s in schedules]
    ev = compute_driving_path_evolution(schedules, cpms, 1, 4)
    assert not ev.snapshots[0].between.drives  # had slack
    assert ev.snapshots[1].between.drives  # now the sole driver
    assert ev.snapshots[1].change_note == "A now drives B"
    assert ev.snapshots[1].between.path == (1, 4)
