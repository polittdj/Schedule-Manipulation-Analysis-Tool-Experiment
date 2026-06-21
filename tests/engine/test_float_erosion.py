"""Float-erosion-by-WBS engine tests (handbook Figs 7-34/7-35).

Groups CPM total float by top-level WBS; per-group min/avg float, critical count, and a stoplight
on the minimum float. Progress-aware float (stored Total Slack preferred). Parity-isolated.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics.float_erosion import (
    _LOW_FLOAT_DAYS,
    compute_float_erosion,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, dur_days: float = 1, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS)


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or [])
    )


def _by_wbs(schedule: Schedule) -> dict[str, object]:
    cpm = compute_cpm(schedule)
    return {g.wbs: g for g in compute_float_erosion(schedule, cpm).groups}


def test_groups_by_top_level_wbs() -> None:
    # 7.1 and 7.3 collapse to "7"; 8.1 to "8"
    sched = _sched([_task(1, wbs="7.1"), _task(2, wbs="7.3"), _task(3, wbs="8.1")])
    groups = _by_wbs(sched)
    assert set(groups) == {"7", "8"}
    assert groups["7"].count == 2
    assert groups["8"].count == 1


def test_critical_chain_is_red_with_zero_min_float() -> None:
    # a single FS chain is all critical (TF == 0) → min float 0 → not negative → amber, all critical
    sched = _sched([_task(1, wbs="1"), _task(2, wbs="1")], [_rel(1, 2)])
    g = _by_wbs(sched)["1"]
    assert g.min_float_days == 0.0
    assert g.status == "yellow"  # 0 is within [0, threshold]
    assert g.critical_count == 2


def test_slack_path_is_green() -> None:
    # 1 (25d, crit) drives 3; 2 (1d) also drives 3 → task 2 has ~24d float, well above threshold
    sched = _sched(
        [_task(1, 25, wbs="5"), _task(2, 1, wbs="6"), _task(3, 1, wbs="5")],
        [_rel(1, 3), _rel(2, 3)],
    )
    groups = _by_wbs(sched)
    assert groups["6"].status == "green"  # the 1-day parallel task carries lots of float
    assert groups["6"].min_float_days > _LOW_FLOAT_DAYS


def test_negative_float_is_red() -> None:
    # a deadline before the logical finish forces negative float on the chain → red
    sched = _sched(
        [_task(1, 10, wbs="2"), _task(2, 10, wbs="2", deadline=dt.datetime(2025, 1, 13, 17, 0))],
        [_rel(1, 2)],
    )
    g = _by_wbs(sched)["2"]
    assert g.min_float_days < 0
    assert g.status == "red"


def test_no_wbs_groups_under_none_and_sorts_last() -> None:
    sched = _sched([_task(1, wbs="3"), _task(2)])  # task 2 has no WBS
    fe_groups = [g.wbs for g in compute_float_erosion(sched, compute_cpm(sched)).groups]
    assert fe_groups == ["3", "(none)"]  # numeric first, "(none)" last


def test_stored_total_float_is_preferred() -> None:
    # a stored progress-aware Total Slack overrides the recomputed CPM float (Acumen parity)
    sched = _sched([_task(1, wbs="9", stored_total_float_minutes=40 * DAY)])
    g = _by_wbs(sched)["9"]
    assert g.min_float_days == 40.0  # 40 working days from the stored slack, not the CPM 0
    assert g.status == "green"


def test_project_min_float_is_the_global_minimum() -> None:
    sched = _sched(
        [_task(1, 10, wbs="1"), _task(2, 1, wbs="2"), _task(3, 1, wbs="1")],
        [_rel(1, 3), _rel(2, 3)],
    )
    fe = compute_float_erosion(sched, compute_cpm(sched))
    assert fe.min_float_days == 0.0  # the critical chain's zero float is the global min
    assert fe.low_float_threshold_days == _LOW_FLOAT_DAYS
