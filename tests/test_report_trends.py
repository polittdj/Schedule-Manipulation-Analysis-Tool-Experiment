"""Trend-section coverage for the Excel and Word reports (tool-original extension).

The multi-version Trend Analysis must appear in both reports when a 2+ version
TrendReport is supplied (with the version-trajectory finish values traceable to
the report), and must be ABSENT when no trends (or a single-version report) is
passed -- so single-schedule reports are unchanged (backward compatible).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.analysis import analyze_schedule
from schedule_forensics.report_excel import build_excel_workbook
from schedule_forensics.report_word import build_word_document
from schedule_forensics.schemas import Relation, Schedule, Task
from schedule_forensics.trend_analysis import analyze_version_trends

_START = dt.datetime(2025, 1, 6, 8)


def _version(status: dt.datetime, dur2: int) -> Schedule:
    """A 1->2 FS chain; task 2's duration sets the finish (480 + dur2)."""
    return Schedule(
        name="V",
        project_start=_START,
        status_date=status,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=dur2),
        ),
        relations=(Relation(predecessor_id=1, successor_id=2),),
    )


def _two_version_trends() -> object:
    # finish 960 (2.0 working days) -> 2400 (5.0 working days): a 3-day slip.
    return analyze_version_trends(
        [
            _version(dt.datetime(2025, 1, 6, 17), 480),
            _version(dt.datetime(2025, 2, 3, 17), 1920),
        ]
    )


def _latest_analysis() -> object:
    return analyze_schedule(_version(dt.datetime(2025, 2, 3, 17), 1920))


def test_excel_trends_sheet_present_and_traceable() -> None:
    wb = build_excel_workbook(_latest_analysis(), trends=_two_version_trends())  # type: ignore[arg-type]
    assert "Trends" in wb.sheetnames
    values = {cell.value for row in wb["Trends"].iter_rows() for cell in row}
    assert "Version Trajectory" in values
    # the two trajectory finish-day values (2.0 and 5.0) are rendered, traceable
    # to the snapshots (H-DRIFT-1) -- openpyxl may store 2.0 as int 2.
    assert 2.0 in values or 2 in values
    assert 5.0 in values or 5 in values


def test_excel_trends_sheet_absent_without_multiversion_trends() -> None:
    analysis = _latest_analysis()
    assert "Trends" not in build_excel_workbook(analysis).sheetnames  # type: ignore[arg-type]
    single = analyze_version_trends([_version(dt.datetime(2025, 1, 6, 17), 480)])
    # a single-version report has nothing to trend -> no sheet
    assert "Trends" not in build_excel_workbook(analysis, trends=single).sheetnames  # type: ignore[arg-type]


def test_word_trend_section_present_with_multiversion() -> None:
    doc = build_word_document(_latest_analysis(), trends=_two_version_trends())  # type: ignore[arg-type]
    texts = [p.text for p in doc.paragraphs]
    assert any("Trend Analysis" in t for t in texts)
    assert any("Version trajectory" in t for t in texts)
    assert any("Finish drift" in t for t in texts)


def test_word_trend_section_absent_without_trends() -> None:
    doc = build_word_document(_latest_analysis())  # type: ignore[arg-type]
    assert not any("Trend Analysis" in p.text for p in doc.paragraphs)
