"""Edge-case unit tests for the structural recommender.

Targets: the finish-driver citation helper, both arms — finish drivers found AND the
summary-only `tasks[:3]` fallback (recommendations.py 117-122); the DCMA fallback wiring when a
failed check carries no per-activity offenders (133-135 — BEI/DCMA14 fails with empty offenders);
and the driving-path finding's empty-on-path guard (337). Assertions check the real citations.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from schedule_forensics.engine.cpm import CPMResult, TaskTiming, compute_cpm
from schedule_forensics.engine.driving_slack import DrivingSlackResult, PathTier
from schedule_forensics.engine.recommendations import (
    _driving_path_findings,
    _finish_driver_citations,
    recommend,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
NOW = MON + dt.timedelta(days=30)
DAY = 480


def _sched(
    tasks: list[Task],
    *,
    status_date: dt.datetime | None = None,
    source_file: str | None = "s.mpp",
) -> Schedule:
    return Schedule(
        name="s",
        source_file=source_file,
        project_start=MON,
        status_date=status_date,
        tasks=tuple(tasks),
        relationships=(),
    )


# --- recommendations.py:117-119 — finish drivers found (the normal arm) --------------------------


def test_finish_driver_citations_cite_the_finish_controlling_activity() -> None:
    """When a task's early finish equals the network finish, that activity is cited as the finish
    driver (recommendations.py lines 117-119, the non-fallback arm)."""
    sch = _sched([Task(unique_id=7, name="finisher", duration_minutes=DAY)])
    cpm = compute_cpm(sch)
    cites = _finish_driver_citations(sch, cpm)
    assert {c.unique_id for c in cites} == {7}
    assert all(c.source_file == "s.mpp" for c in cites)


# --- recommendations.py:120-122 — the tasks[:3] fallback when nothing controls the finish --------


def test_finish_driver_citations_fall_back_to_the_first_rows() -> None:
    """If NO timing's early finish equals the network finish (e.g. a degenerate/summary-only
    network), the first task rows anchor the citation — a finding can never be uncited
    (recommendations.py lines 120-122)."""
    tasks = [
        Task(unique_id=10, name="a", duration_minutes=DAY, is_summary=True),
        Task(unique_id=20, name="b", duration_minutes=DAY, is_summary=True),
        Task(unique_id=30, name="c", duration_minutes=DAY, is_summary=True),
        Task(unique_id=40, name="d", duration_minutes=DAY, is_summary=True),
    ]
    sch = _sched(tasks)
    # A hand-built CPMResult whose project_finish matches NO task's early_finish -> forces fallback.
    timings = {
        t.unique_id: TaskTiming(
            unique_id=t.unique_id,
            early_start=0,
            early_finish=DAY,  # all finish at DAY ...
            late_start=0,
            late_finish=DAY,
            total_float=0,
            free_float=0,
            is_critical=True,
        )
        for t in tasks
    }
    # ... but the network finish is far later, so no task's early_finish matches it
    cpm = CPMResult(timings=timings, project_finish=DAY * 999, critical_path=())
    cites = _finish_driver_citations(sch, cpm)
    # fallback cites the first THREE task rows (10, 20, 30), never empty
    assert {c.unique_id for c in cites} == {10, 20, 30}


# --- recommendations.py:133-135 — a failed DCMA check with no offenders uses the fallback --------


def test_dcma_finding_with_no_offenders_borrows_the_finish_driver_fallback() -> None:
    """BEI (DCMA14) can fail with EMPTY offenders: baselined-due tasks that are < 100% complete
    yet carry an actual finish drag BEI below threshold without producing citable offenders. The
    recommender then borrows the finish-driver fallback so the finding stays cited (lines
    133-135) — the §6 never-uncited invariant."""
    # 5 Normal tasks, all baselined-due by NOW, each <100% but WITH an actual finish -> BEI fails,
    # offender_uids is empty (offenders require actual_finish is None).
    tasks = [
        Task(
            unique_id=u,
            name=f"T{u}",
            duration_minutes=DAY,
            baseline_finish=MON,
            actual_finish=MON,
            percent_complete=50.0,
        )
        for u in range(1, 6)
    ]
    findings = recommend(_sched(tasks, status_date=NOW))
    bei = next(f for f in findings if f.metric_id == "DCMA14")
    # the finding exists, is a high-severity concern, and is CITED despite zero native offenders
    assert bei.citations  # §6: never uncited — the fallback supplied a citation
    assert all(c.source_file == "s.mpp" for c in bei.citations)


# --- recommendations.py:337 — driving-path finding returns [] when nothing is on the path --------


def test_driving_path_findings_empty_when_no_activity_is_on_the_driving_path(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """If the driving-slack trace reports NO on-driving-path activities, the opportunity finding is
    suppressed (recommendations.py lines 336-337). We force that all-False result to exercise the
    guard — the production trace always keeps the target on-path, so this defensive branch needs a
    stubbed slack result."""
    sch = _sched([Task(unique_id=5, name="focus", duration_minutes=DAY)])

    def _all_off_path(schedule: Schedule, target_uid: int) -> dict[int, DrivingSlackResult]:
        return {
            target_uid: DrivingSlackResult(
                unique_id=target_uid,
                driving_slack_minutes=DAY * 10,
                driving_slack_days=Decimal(10),
                on_driving_path=False,  # nothing is on the path
                tier=PathTier.BEYOND,
            )
        }

    monkeypatch.setattr(
        "schedule_forensics.engine.recommendations.compute_driving_slack", _all_off_path
    )
    assert _driving_path_findings(sch, target_uid=5) == []
