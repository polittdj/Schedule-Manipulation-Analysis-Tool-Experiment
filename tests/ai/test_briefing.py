"""Executive-briefing tests — the leadership forensic summary over the goldens (ADR-0121).

The briefing is rebuilt as a numbered, plain-English forensic Executive Summary (Bottom Line →
Performance → Critical Path Then & Now → Health Dashboard → Risks & Opportunities → Recommended
Actions → How to Verify). Every figure is engine-computed and every statement / table row is cited
(§6). Assertions here check the structure, the citation contract, and the headline facts — never a
number transcribed from an external report (fidelity: compute, don't transcribe).
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.ai.briefing import briefing_blocks, build_briefing
from schedule_forensics.ai.citations import assert_all_cited
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

TODAY = dt.date(2026, 6, 10)

#: the numbered section outline a single-version briefing always emits
_SINGLE_VERSION_HEADINGS = [
    "1. The Bottom Line",
    "1.1 The Story in Plain English",
    "1.2 The Single Most Important Number",
    "2. How the Project Has Performed",
    "2.1 What Has Been Accomplished",
    "2.2 What Is In Progress",
    "3. The Critical Path — Then and Now",
    "3.1 What Changed",
    "4. Schedule Health Dashboard",
    "5. Risks and Opportunities",
    "5.1 Risk Register",
    "5.2 Opportunities",
    "6. Recommended Actions",
    "6.1 If Nothing Is Done",
    "6.2 If Recommended Actions Are Implemented",
    "7. How to Verify Every Number",
    "7.1 Methodology",
    "7.2 Limitations",
]
_TOP_LEVEL_HEADINGS = [
    "1. The Bottom Line",
    "2. How the Project Has Performed",
    "3. The Critical Path — Then and Now",
    "4. Schedule Health Dashboard",
    "5. Risks and Opportunities",
    "6. Recommended Actions",
    "7. How to Verify Every Number",
]


def test_single_version_emits_the_full_numbered_outline(golden_project5) -> None:
    b = build_briefing([golden_project5], today=TODAY)
    assert [s.heading for s in b.sections] == _SINGLE_VERSION_HEADINGS
    for section in b.sections:
        assert_all_cited(section.statements)  # §6: every sentence carries file+UID+task


def test_every_table_row_is_cited(golden_project5) -> None:
    b = build_briefing([golden_project5], today=TODAY)
    tabled = [s for s in b.sections if s.table is not None]
    assert tabled  # the dashboard / accomplished / in-progress / risk / action tables exist
    for section in tabled:
        assert len(section.table.rows) == len(section.table.row_citations)
        assert all(cites for cites in section.table.row_citations)  # §6: never uncited


def test_header_metadata_banner_and_verdict(golden_project5) -> None:
    b = build_briefing([golden_project5], today=TODAY)
    assert b.title == "POLARIS — Executive Briefing"
    assert b.verdict in {"ON TRACK", "WATCH", "AT RISK"}
    meta_labels = [k for k, _ in b.meta_rows]
    assert meta_labels == [
        "Report date",
        "Schedule data date",
        "Source schedule",
        "Versions loaded",
        "Classification",
    ]
    banner_labels = [k for k, _ in b.banner]
    assert banner_labels == [
        "Status",
        "SPI (duration-based)",
        "Forecast finish",
        "Baseline finish",
        "Slip",
    ]
    assert dict(b.banner)["Status"] == b.verdict


def test_bottom_line_opens_in_one_sentence(golden_project5) -> None:
    b = build_briefing([golden_project5], today=TODAY)
    bottom = b.sections[0]
    assert bottom.heading == "1. The Bottom Line"
    assert "In one sentence:" in bottom.statements[0].text
    assert b.verdict in bottom.statements[0].text


def test_health_dashboard_has_the_four_indicators(golden_project5) -> None:
    b = build_briefing([golden_project5], today=TODAY)
    dash = next(s for s in b.sections if s.heading == "4. Schedule Health Dashboard")
    assert dash.table is not None and dash.table.headers == ("Indicator", "Reading", "Status")
    indicators = [row[0] for row in dash.table.rows]
    assert indicators == [
        "Task status",
        "Schedule slippage",
        "Schedule Performance Index",
        "DCMA-14 quality",
    ]


def test_two_versions_show_critical_path_then_and_now(golden_project2, golden_project5) -> None:
    b = build_briefing([golden_project5, golden_project2], today=TODAY)  # any load order
    headings = [s.heading for s in b.sections]
    # ordered oldest -> newest by data date; the cross-version "then and now" subsection appears
    assert "3.1 What Changed Between the Versions" in headings
    for top in _TOP_LEVEL_HEADINGS:
        assert top in headings
    for section in b.sections:
        assert_all_cited(section.statements)


def test_backend_rephrases_prose_but_keeps_citations(golden_project5) -> None:
    class Shout:
        name = "shout"
        is_local = True

        def is_available(self) -> bool:
            return True

        def list_models(self) -> tuple[str, ...]:
            return ()

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            text = prompt.split("STATEMENT: ", 1)[1].rsplit("\nREWRITE:", 1)[0]
            return text.upper()

    plain = build_briefing([golden_project5], today=TODAY)
    shouted = build_briefing([golden_project5], backend=Shout(), today=TODAY)
    for ps, ss in zip(plain.sections, shouted.sections, strict=True):
        for p, s in zip(ps.statements, ss.statements, strict=True):
            assert s.text == p.text.upper()  # rephrased
            assert s.citations == p.citations  # citations untouched
        assert ss.table == ps.table  # tables are engine data — the model never touches them


def test_to_text_renders_numbered_headings(golden_project5) -> None:
    text = build_briefing([golden_project5], today=TODAY).to_text()
    assert text.startswith("# POLARIS — Executive Briefing")
    assert "## 1. The Bottom Line" in text
    assert "### 7.1 Methodology" in text
    assert "Verdict:" in text


def test_briefing_blocks_render_word_structure(golden_project5) -> None:
    from schedule_forensics.reports.docx import DocTable, Heading, Paragraph, render_document

    blocks = briefing_blocks(build_briefing([golden_project5], today=TODAY))
    assert isinstance(blocks[0], Heading) and blocks[0].level == 0
    assert any(isinstance(b, Heading) and b.text == "1. The Bottom Line" for b in blocks)
    assert any(isinstance(b, DocTable) for b in blocks)  # at least one cited table
    assert any(isinstance(b, Paragraph) for b in blocks)
    data = render_document(blocks)  # serializes to deterministic .docx bytes
    assert data[:2] == b"PK"  # a real .docx (zip container)


def test_requires_at_least_one_schedule() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_briefing([])


def test_undated_schedule_reports_not_statused() -> None:
    sch = Schedule(
        name="solo",
        source_file="solo.xml",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480),),
    )
    b = build_briefing([sch], today=TODAY)
    assert dict(b.meta_rows)["Schedule data date"] == "not statused"
    for section in b.sections:
        assert_all_cited(section.statements)


def test_empty_scope_is_cited_and_says_nothing_to_brief() -> None:
    """An empty scope (a filter that matched nothing / summary-only files) yields a single cited
    section, not a crash on uncitable detail (regression for the session filter)."""
    start = dt.datetime(2025, 1, 6, 8, 0)
    empty = Schedule(
        name="empty", source_file="empty.xml", project_start=start, tasks=(), relationships=()
    )
    summary_only = Schedule(
        name="sumonly",
        source_file="sumonly.xml",
        project_start=start,
        tasks=(Task(unique_id=1, name="WBS", duration_minutes=4800, is_summary=True),),
        relationships=(),
    )
    for sch in (empty, summary_only):
        b = build_briefing([sch], today=TODAY)
        assert b.sections and all(s.statements for s in b.sections)
        for section in b.sections:
            assert_all_cited(section.statements)
        assert "nothing to brief" in b.sections[0].statements[0].text
