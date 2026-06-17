"""The Diagnostic Brief — cited outlier narrative over the loaded versions (M18)."""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from pathlib import Path

import pytest

from schedule_forensics.ai.brief import DiagnosticBrief, brief_blocks, build_brief
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.reports.docx import Block, render_document

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "test_projects"
TODAY = dt.date(2026, 6, 12)


def _load(name: str) -> Schedule:
    return parse_mspdi(FIXTURES / name)


@pytest.fixture(scope="module")
def tp4_brief() -> DiagnosticBrief:
    versions = [_load(f"TP4_DataCenter_v{i}.xml") for i in range(1, 6)]
    cpms = [compute_cpm(s) for s in versions]
    return build_brief(versions, cpms, today=TODAY)


def _all_text(brief: DiagnosticBrief) -> str:
    return " ".join(p.text for s in brief.sections for p in s.paragraphs)


def test_brief_tells_the_tp4_story(tp4_brief: DiagnosticBrief) -> None:
    text = _all_text(tp4_brief)
    # the planted manipulation is narrated and cited to UID 19
    assert "actual date erased" in text
    assert "baseline dates changed" in text
    cited_uids = {
        c.unique_id for s in tp4_brief.sections for p in s.paragraphs for c in p.citations
    }
    assert 19 in cited_uids
    # the progress-up / finish-out contradiction is called out
    assert "opposite directions" in text
    # the falling CEI series is narrated with its numbers
    assert "0.50" in text and "0.00" in text


def test_brief_has_trends_and_risk_recovery_sections(tp4_brief: DiagnosticBrief) -> None:
    """Operator request: in addition to the existing content, a high-level trends-over-time
    summary plus risks, opportunities, and concrete recovery suggestions."""
    headings = [s.heading for s in tp4_brief.sections]
    assert "Trends over time" in headings
    assert "Risks, opportunities, and recovery plan" in headings
    trends = next(s for s in tp4_brief.sections if s.heading == "Trends over time")
    assert trends.paragraphs and any("computed finish moved" in p.text for p in trends.paragraphs)
    risk = next(
        s for s in tp4_brief.sections if s.heading == "Risks, opportunities, and recovery plan"
    )
    assert risk.paragraphs
    blob = " ".join(p.text for p in risk.paragraphs)
    assert "Recovery:" in blob or "Recovery focus" in blob  # actionable recovery guidance
    # the new sections obey §6 too (covered broadly elsewhere, pinned here for the new content)
    for p in (*trends.paragraphs, *risk.paragraphs):
        assert p.citations


def test_single_version_brief_trends_note_is_cited() -> None:
    schedule = _load("TP1_Library_Progressed.xml")
    brief = build_brief([schedule], [compute_cpm(schedule)], today=TODAY)
    trends = next(s for s in brief.sections if s.heading == "Trends over time")
    assert (
        trends.paragraphs
        and "only one schedule version is loaded" in trends.paragraphs[0].text.lower()
    )
    assert trends.paragraphs[0].citations


def test_brief_finish_table_covers_every_version(tp4_brief: DiagnosticBrief) -> None:
    story = next(s for s in tp4_brief.sections if s.heading == "The finish story")
    assert story.table is not None
    assert len(story.table.rows) == 5
    # the engine CPM recomputes v5 from logic (stored dates diverge intraday): 06-26
    assert story.table.rows[-1][2] == "2026-06-26"


def test_every_brief_paragraph_is_cited(tp4_brief: DiagnosticBrief) -> None:
    """The §6 rule applies to the brief verbatim: no claim without its anchors."""
    for section in tp4_brief.sections:
        for paragraph in section.paragraphs:
            assert paragraph.citations, (section.heading, paragraph.text[:80])


def test_brief_works_for_a_single_version() -> None:
    schedule = _load("TP1_Library_Progressed.xml")
    brief = build_brief([schedule], [compute_cpm(schedule)], today=TODAY)
    text = _all_text(brief)
    # the dangling 70-day-float procurement task raises a question
    assert "total float" in text
    # the wide three-method forecast disagreement raises a question
    assert "disagree" in text
    for section in brief.sections:
        for paragraph in section.paragraphs:
            assert paragraph.citations


def test_brief_blocks_render_as_a_word_document(tp4_brief: DiagnosticBrief) -> None:
    blocks = brief_blocks(tp4_brief)
    blob = render_document([b for b in blocks if isinstance(b, Block)])
    doc = zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml").decode()
    assert "Diagnostic Brief" in doc
    assert "Questions the data raises" in doc
    assert "UID 19" in doc  # citations travel into the Word export
