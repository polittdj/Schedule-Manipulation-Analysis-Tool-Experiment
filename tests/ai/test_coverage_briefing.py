"""Coverage for the briefing helpers: the verdict not-applicable arm plus the §6
never-uncited fallbacks (no finish driver matches, an empty scope, a worst-version trend
with no offenders)."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.briefing import (
    _finish_drivers,
    _trend_section,
    _verdict,
    _workbook_section,
)
from schedule_forensics.engine.cpm import CPMResult, TaskTiming
from schedule_forensics.engine.dcma_audit import CheckStatus
from schedule_forensics.engine.trend import MetricTrend
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480
TODAY = dt.date(2025, 6, 10)


def test_verdict_covers_all_three_statuses() -> None:
    assert "target state" in _verdict(CheckStatus.PASS)
    assert "Improvements are required" in _verdict(CheckStatus.FAIL)
    assert "Not applicable" in _verdict(CheckStatus.NOT_APPLICABLE)


# --- briefing.py:99 — finish-driver fallback to the first rows when nothing controls the finish --


def test_finish_drivers_fall_back_to_first_rows_when_none_match_the_finish() -> None:
    """When NO timing's early finish equals the network finish, the first task rows anchor the
    citation so a statement is never uncited (briefing.py line 99)."""
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=DAY) for u in (10, 20, 30, 40)]
    sch = Schedule(name="s", source_file="s.mpp", project_start=MON, tasks=tuple(tasks))
    # all tasks finish at DAY, but the network finish is far later -> nothing matches -> fallback.
    timings = {
        t.unique_id: TaskTiming(
            unique_id=t.unique_id,
            early_start=0,
            early_finish=DAY,
            late_start=0,
            late_finish=DAY,
            total_float=0,
            free_float=0,
            is_critical=True,
        )
        for t in tasks
    }
    cpm = CPMResult(timings=timings, project_finish=DAY * 999, critical_path=())
    cites = _finish_drivers(sch, cpm)
    assert {c.unique_id for c in cites} == {10, 20, 30}  # the first THREE rows, never empty


# --- briefing.py:142 — an empty scope anchors the lede on the files themselves -------------------


def test_workbook_section_anchors_on_files_when_no_finish_drivers_exist() -> None:
    """A scope that matched no activities (zero tasks) has no finish drivers at all — even the
    ``tasks[:3]`` fallback is empty — so the workbook lede anchors on the files themselves with a
    UID-0 citation, never uncited (briefing.py line 142)."""
    empty = Schedule(name="empty", source_file="empty.mpp", project_start=MON, tasks=())
    cpm = CPMResult(timings={}, project_finish=0, critical_path=())
    section = _workbook_section([empty], [cpm], TODAY)
    (statement,) = section.statements
    assert statement.citations  # §6: the lede carries a citation even with nothing in scope
    cite = statement.citations[0]
    assert cite.unique_id == 0  # the file-level anchor
    assert cite.source_file == "empty.mpp"


# --- briefing.py:155 — a worst-version trend with no offenders borrows the finish drivers --------


def test_trend_section_borrows_finish_drivers_when_worst_version_has_no_offenders(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    """A trended metric can have a worst version (``worst_index`` set) yet no offending activities
    in it (``worst_offender_uids`` empty) — the trend statement then borrows that version's finish
    drivers so it stays cited (briefing.py line 155)."""
    tasks = [Task(unique_id=5, name="finisher", duration_minutes=DAY)]
    a = Schedule(name="a", source_file="a.mpp", project_start=MON, tasks=tuple(tasks))
    b = Schedule(name="b", source_file="b.mpp", project_start=MON, tasks=tuple(tasks))
    timings = {
        5: TaskTiming(
            unique_id=5,
            early_start=0,
            early_finish=DAY,
            late_start=0,
            late_finish=DAY,
            total_float=0,
            free_float=0,
            is_critical=True,
        )
    }
    cpm = CPMResult(timings=timings, project_finish=DAY, critical_path=(5,))

    trend = MetricTrend(
        metric_id="critical",
        name="Critical",
        labels=("a.mpp", "b.mpp"),
        values=(1.0, 2.0),  # varies → not "remains constant"
        lower_is_better=True,
        worst_index=1,  # there IS a worst version ...
        worst_offender_uids=(),  # ... but it has no offending activities -> finish-driver fallback
        offenders_by_version=((), ()),
    )
    monkeypatch.setattr(
        "schedule_forensics.ai.briefing.compute_quality_trend", lambda *_a, **_k: (trend,)
    )
    section = _trend_section([a, b], [cpm, cpm])
    (statement,) = section.statements
    assert statement.citations  # §6: cited via the worst version's finish drivers
    assert {c.unique_id for c in statement.citations} == {5}
