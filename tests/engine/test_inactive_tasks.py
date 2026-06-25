"""Inactive tasks (``is_active=False``) are excluded from the CPM and every metric population,
matching MS Project / Acumen Fuse (ADR-0128).

The golden parity files carry no inactive tasks, so the parity gate cannot exercise this — these
synthetic schedules pin the behavior directly. The forensic diff/manipulation layer is *not* part
of this exclusion (deactivating a task between versions must stay a detectable change), which is
covered by ``test_diff``/``test_manipulation`` and asserted here at the boundary.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.driving_slack import date_basis
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.metrics.dcma14 import compute_dcma14
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _schedule(*, c_active: bool) -> Schedule:
    """A → B → C chain where C's active flag is the variable under test."""
    a = Task(unique_id=1, name="A", duration_minutes=DAY)
    b = Task(unique_id=2, name="B", duration_minutes=DAY)
    c = Task(unique_id=3, name="C", duration_minutes=DAY, is_active=c_active)
    rels = (
        Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
        Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS),
    )
    return Schedule(name="s", project_start=MON, tasks=(a, b, c), relationships=rels)


def test_non_summary_excludes_inactive() -> None:
    active = {t.unique_id for t in non_summary(_schedule(c_active=True))}
    inactive = {t.unique_id for t in non_summary(_schedule(c_active=False))}
    assert active == {1, 2, 3}
    assert inactive == {1, 2}  # C dropped from the metric population


def test_cpm_network_excludes_inactive_and_drops_its_links() -> None:
    res = compute_cpm(_schedule(c_active=False))
    assert 3 not in res.timings  # the inactive task never enters the network…
    assert 3 not in res.critical_path  # …so it cannot appear on the critical path
    # the B→C link is dropped with C, so B (now the last real activity) drives the finish
    finish_with = compute_cpm(_schedule(c_active=True)).project_finish
    finish_without = res.project_finish
    assert finish_without < finish_with  # one fewer activity in the chain → earlier finish


def test_dcma_population_drops_inactive() -> None:
    full = compute_dcma14(_schedule(c_active=True))
    trimmed = compute_dcma14(_schedule(c_active=False))
    # DCMA-01 Logic runs over incomplete real activities; 3 active vs 2 when C is inactive
    assert full["DCMA01"].population == 3
    assert trimmed["DCMA01"].population == 2


def test_driving_slack_date_basis_excludes_inactive() -> None:
    # the as-scheduled date basis (the axis driving-slack runs on) omits the inactive task…
    es_off, ef_off = date_basis(_schedule(c_active=False), None)
    assert 3 not in es_off and 3 not in ef_off
    # …but includes it when active
    es_on, _ = date_basis(_schedule(c_active=True), None)
    assert 3 in es_on
