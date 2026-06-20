"""Per-year phase distribution tests — binning by a chosen date basis into calendar years."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics.year_phases import YEAR_BASES, compute_year_phases
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def _task(uid: int, **kw: object) -> Task:
    kw.setdefault("duration_minutes", 480)
    return Task(unique_id=uid, name=f"T{uid}", **kw)


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks), relationships=())


def test_bins_by_finish_year_with_status_splits() -> None:
    s = _sched(
        [
            _task(0, is_summary=True, finish=dt.datetime(2024, 5, 1, 17, 0)),  # summary skipped
            _task(1, finish=dt.datetime(2024, 5, 1, 17, 0), percent_complete=100.0),
            _task(2, finish=dt.datetime(2024, 9, 1, 17, 0), percent_complete=40.0),
            _task(3, finish=dt.datetime(2025, 2, 1, 17, 0)),  # planned 0%
            _task(4, finish=dt.datetime(2025, 3, 1, 17, 0), is_milestone=True, duration_minutes=0),
        ]
    )
    yp = compute_year_phases(s, "finish")
    assert yp.basis == "finish" and yp.undated == 0
    by_year = {r.year: r for r in yp.rows}
    assert set(by_year) == {2024, 2025}
    assert (by_year[2024].total, by_year[2024].complete, by_year[2024].in_progress) == (2, 1, 1)
    assert (by_year[2025].total, by_year[2025].planned, by_year[2025].milestones) == (2, 2, 1)


def test_basis_switch_changes_the_binning() -> None:
    s = _sched(
        [
            _task(
                1,
                start=dt.datetime(2023, 6, 1, 8, 0),
                finish=dt.datetime(2025, 6, 1, 17, 0),
                baseline_finish=dt.datetime(2024, 6, 1, 17, 0),
            )
        ]
    )
    assert compute_year_phases(s, "start").rows[0].year == 2023
    assert compute_year_phases(s, "finish").rows[0].year == 2025
    assert compute_year_phases(s, "baseline_finish").rows[0].year == 2024


def test_actual_finish_basis_and_undated_count() -> None:
    s = _sched(
        [
            _task(
                1,
                finish=dt.datetime(2025, 1, 1, 17, 0),
                actual_finish=dt.datetime(2025, 1, 2, 17, 0),
            ),
            _task(
                2, finish=dt.datetime(2025, 1, 1, 17, 0)
            ),  # no actual finish → undated on this basis
        ]
    )
    yp = compute_year_phases(s, "actual_finish")
    assert yp.undated == 1
    assert [r.year for r in yp.rows] == [2025]
    assert yp.rows[0].total == 1 and yp.rows[0].complete == 1


def test_unknown_basis_falls_back_to_finish() -> None:
    s = _sched([_task(1, finish=dt.datetime(2026, 1, 1, 17, 0))])
    yp = compute_year_phases(s, "nonsense")
    assert yp.basis == "finish" and yp.rows[0].year == 2026


def test_bases_catalog_is_complete() -> None:
    assert set(YEAR_BASES) == {"finish", "start", "baseline_finish", "actual_finish"}


def test_golden_project5_year_rows_reconcile(golden_project5: Schedule) -> None:
    yp = compute_year_phases(golden_project5, "finish")
    binned = sum(r.total for r in yp.rows)
    # every non-summary activity is either binned by year or counted undated (none invented)
    activities = sum(1 for t in golden_project5.tasks if not t.is_summary)
    assert binned + yp.undated == activities
    for r in yp.rows:
        assert r.complete + r.in_progress + r.planned == r.total
