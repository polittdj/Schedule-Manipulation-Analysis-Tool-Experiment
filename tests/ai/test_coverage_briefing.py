"""Coverage for the briefing helpers (ADR-0121): the verdict heuristic's three arms, the §6
never-uncited finish-driver fallbacks, the working-day slip math, and the single-version
critical-path note / empty-findings arms."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.briefing import (
    _finish_drivers,
    _iso,
    _slip_phrase,
    _var_cell,
    _verdict,
    _workday_slip,
    build_briefing,
)
from schedule_forensics.engine.cpm import CPMResult, TaskTiming, offset_to_datetime
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480
TODAY = dt.date(2025, 6, 10)


def test_verdict_covers_all_three_arms() -> None:
    assert _verdict(slip=-2, spi=0.99, dcma_fails=0) == "ON TRACK"
    assert _verdict(slip=5, spi=0.97, dcma_fails=1) == "WATCH"  # small slip, healthy otherwise
    assert _verdict(slip=40, spi=0.97, dcma_fails=0) == "AT RISK"  # big slip
    assert _verdict(slip=3, spi=0.80, dcma_fails=0) == "AT RISK"  # low SPI
    assert _verdict(slip=3, spi=0.97, dcma_fails=4) == "AT RISK"  # behind + many DCMA fails
    assert _verdict(slip=None, spi=None, dcma_fails=0) == "WATCH"  # no baseline -> not "on track"


def test_finish_drivers_fall_back_to_first_rows_when_none_match_the_finish() -> None:
    """When NO timing's early finish equals the network finish, the first task rows anchor the
    citation so a statement is never uncited."""
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=DAY) for u in (10, 20, 30, 40)]
    sch = Schedule(name="s", source_file="s.mpp", project_start=MON, tasks=tuple(tasks))
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


def test_finish_drivers_anchor_on_the_file_when_no_tasks_exist() -> None:
    """A scope with zero tasks has no finish drivers and no ``tasks[:3]`` fallback, so the citation
    anchors on the file itself with a UID-0 reference — never uncited (§6)."""
    empty = Schedule(name="empty", source_file="empty.mpp", project_start=MON, tasks=())
    cpm = CPMResult(timings={}, project_finish=0, critical_path=())
    cites = _finish_drivers(empty, cpm)
    assert len(cites) == 1 and cites[0].unique_id == 0 and cites[0].source_file == "empty.mpp"


def test_workday_slip_math_and_none_without_baseline() -> None:
    sch = Schedule(
        name="s",
        source_file="s.mpp",
        project_start=MON,
        tasks=(Task(unique_id=1, name="A", duration_minutes=DAY),),
    )
    per_day = sch.calendar.working_minutes_per_day
    cpm = CPMResult(timings={}, project_finish=per_day * 10, critical_path=())
    assert _workday_slip(sch, cpm, None) is None  # no baseline to compare against
    baseline = offset_to_datetime(MON, per_day * 7, sch.calendar)
    assert _workday_slip(sch, cpm, baseline) == 3  # forecast 10 wd vs baseline 7 wd -> +3


def test_slip_phrase_and_var_cell_arms() -> None:
    assert "behind" in _slip_phrase(7) and _var_cell(7) == "+7 wd"
    assert "ahead" in _slip_phrase(-4) and _var_cell(-4) == "-4 wd"
    assert "on its baseline" in _slip_phrase(0) and _var_cell(0) == "on schedule"
    assert "no baseline" in _slip_phrase(None) and _var_cell(None) == "no baseline"


def test_iso_handles_missing_date() -> None:
    assert _iso(None) == "—"
    assert _iso(dt.datetime(2026, 3, 4, 9, 0)) == "2026-03-04"


def test_single_version_critical_path_note_explains_the_limitation() -> None:
    """One loaded version cannot show a baseline-vs-current critical path (MPP stores only the
    current Critical flag), so 3.1 states the limitation rather than inventing a comparison."""
    sch = Schedule(
        name="solo",
        source_file="solo.xml",
        project_start=MON,
        status_date=dt.datetime(2025, 3, 1, 8, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=DAY),),
    )
    b = build_briefing([sch], today=TODAY)
    note = next(s for s in b.sections if s.heading == "3.1 What Changed")
    assert "baseline-vs-current critical-path" in note.statements[0].text
    assert "Only one schedule version is loaded" in note.statements[0].text


def test_empty_findings_yield_no_table_but_cited_prose() -> None:
    """A schedule with no flagged risks/opportunities still emits the Risks & Recommended-Actions
    sections — with cited prose explaining there is nothing to flag, and no empty table."""
    sch = Schedule(
        name="solo",
        source_file="solo.xml",
        project_start=MON,
        tasks=(Task(unique_id=1, name="A", duration_minutes=DAY),),
    )
    b = build_briefing([sch], today=TODAY)
    risk = next(s for s in b.sections if s.heading == "5.1 Risk Register")
    actions = next(s for s in b.sections if s.heading == "6. Recommended Actions")
    for section in (risk, actions):
        assert section.statements and section.statements[0].citations
