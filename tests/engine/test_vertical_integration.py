"""Vertical-integration engine tests — summary bars must envelope their WBS descendants.

Stored-date / WBS-hierarchy check (no CPM). A summary whose stored span does not bracket its detail
activities is flagged; summaries that aren't evaluable (no WBS, no dates, no dated children) skip.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics.vertical_integration import compute_vertical_integration
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _t(
    uid: int,
    wbs: str | None,
    start: dt.datetime | None,
    finish: dt.datetime | None,
    *,
    summary: bool = False,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=DAY,
        wbs=wbs,
        start=start,
        finish=finish,
        is_summary=summary,
    )


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks))


D = dt.datetime  # brevity


def test_consistent_rollup_is_clear() -> None:
    # summary "1" spans Jan 6-20; its two children sit inside that span
    sched = _sched(
        [
            _t(1, "1", D(2025, 1, 6, 8), D(2025, 1, 20, 17), summary=True),
            _t(2, "1.1", D(2025, 1, 6, 8), D(2025, 1, 10, 17)),
            _t(3, "1.2", D(2025, 1, 13, 8), D(2025, 1, 20, 17)),
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.count == 0
    assert vi.population == 1


def test_summary_finishing_before_a_child_is_flagged() -> None:
    # summary finishes Jan 15 but a child runs to Jan 20 → envelope violated
    sched = _sched(
        [
            _t(1, "1", D(2025, 1, 6, 8), D(2025, 1, 15, 17), summary=True),
            _t(2, "1.1", D(2025, 1, 6, 8), D(2025, 1, 20, 17)),
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.count == 1
    assert vi.offenders == (1,)
    assert vi.population == 1


def test_summary_starting_after_a_child_is_flagged() -> None:
    # summary starts Jan 10 but a child starts Jan 6 → envelope violated
    sched = _sched(
        [
            _t(1, "2", D(2025, 1, 10, 8), D(2025, 1, 20, 17), summary=True),
            _t(2, "2.1", D(2025, 1, 6, 8), D(2025, 1, 18, 17)),
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.count == 1
    assert vi.offenders == (1,)  # the summary (uid 1) is the offender


def test_nested_descendants_at_any_depth_count() -> None:
    # "1.2.3" is a descendant of "1" via prefix; the deep child overruns the summary finish
    sched = _sched(
        [
            _t(1, "1", D(2025, 1, 6, 8), D(2025, 1, 15, 17), summary=True),
            _t(2, "1.2.3", D(2025, 1, 6, 8), D(2025, 1, 25, 17)),
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.count == 1


def test_summary_without_dated_children_is_not_evaluable() -> None:
    sched = _sched(
        [
            _t(1, "1", D(2025, 1, 6, 8), D(2025, 1, 15, 17), summary=True),
            _t(2, "9.1", D(2025, 1, 6, 8), D(2025, 1, 25, 17)),  # different branch
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.population == 0
    assert vi.count == 0


def test_summary_without_stored_dates_is_skipped() -> None:
    sched = _sched(
        [
            _t(1, "1", None, None, summary=True),  # no stored dates
            _t(2, "1.1", D(2025, 1, 6, 8), D(2025, 1, 25, 17)),
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.population == 0


def test_no_wbs_means_nothing_to_evaluate() -> None:
    sched = _sched(
        [
            _t(1, None, D(2025, 1, 6, 8), D(2025, 1, 15, 17), summary=True),
            _t(2, None, D(2025, 1, 6, 8), D(2025, 1, 25, 17)),
        ]
    )
    vi = compute_vertical_integration(sched)
    assert vi.population == 0 and vi.count == 0
