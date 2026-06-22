"""Executive-briefing tests — the Acumen-style diagnostic briefing over the goldens.

Counts asserted here are the validated golden values (126 normal activities; 20/27
complete; 3/2 in progress; 18 summaries). Dates are the ENGINE's computed values —
never copied from an external report (fidelity: compute, don't transcribe).
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.ai.briefing import build_briefing
from schedule_forensics.ai.citations import assert_all_cited
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

TODAY = dt.date(2026, 6, 10)


def test_briefing_two_golden_versions_full_structure(golden_project2, golden_project5) -> None:
    b = build_briefing([golden_project5, golden_project2], today=TODAY)  # any load order
    headings = [s.heading for s in b.sections]
    assert headings == [
        "Workbook Summary",
        "Trend Analysis",
        "Project2.mspdi.xml Project",
        "Project5.mspdi.xml Project",
        "Project2.mspdi.xml Schedule Quality Analysis",
        "Project5.mspdi.xml Schedule Quality Analysis",
    ]  # chronological by data date, regardless of the order given
    for section in b.sections:
        assert section.statements, section.heading
        assert_all_cited(section.statements)  # §6: every sentence carries file+UID+task


def test_briefing_workbook_summary_names_versions_and_window(
    golden_project2, golden_project5
) -> None:
    b = build_briefing([golden_project2, golden_project5], today=TODAY)
    text = b.sections[0].statements[0].text
    assert "2 schedule version(s)" in text
    assert "Project2.mspdi.xml" in text and "Project5.mspdi.xml" in text
    assert "Wednesday, June 10, 2026" in text  # report date, briefing style
    assert "earliest start date" in text and "latest completion date" in text


def test_briefing_project_summary_golden_counts(golden_project2, golden_project5) -> None:
    b = build_briefing([golden_project2, golden_project5], today=TODAY)
    p2 = next(s for s in b.sections if s.heading == "Project2.mspdi.xml Project")
    text = p2.statements[0].text
    # validated golden progress counts (and the briefing's percent style)
    assert "126 normal activities" in text
    assert "20 (15.9%) are complete" in text
    assert "3 (2.4%) are in progress" in text
    assert "103 (81.7%) are still planned" in text
    assert "18 summaries" in text
    # baseline variance sentence is present with a computed day count
    assert "baseline finish date" in p2.statements[1].text
    assert "behind schedule by" in p2.statements[1].text

    p5 = next(s for s in b.sections if s.heading == "Project5.mspdi.xml Project")
    assert "27 (21.4%) are complete" in p5.statements[0].text
    assert "2 (1.6%) are in progress" in p5.statements[0].text


def test_briefing_trend_section_uses_metric_sentences(golden_project2, golden_project5) -> None:
    b = build_briefing([golden_project2, golden_project5], today=TODAY)
    trend = next(s for s in b.sections if s.heading == "Trend Analysis")
    texts = [s.text for s in trend.statements]
    assert any(t.startswith("Missing Logic:") for t in texts)
    assert any("Critical: decreases over time" in t for t in texts)
    assert any(
        t
        == (
            "Hard Constraints: increases over time with the best version being"
            " Project2.mspdi.xml (0) and the worst version being Project5.mspdi.xml (1)."
        )
        for t in texts
    )


def test_briefing_quality_section_has_verdicts(golden_project2, golden_project5) -> None:
    b = build_briefing([golden_project2, golden_project5], today=TODAY)
    q5 = next(s for s in b.sections if "Project5" in s.heading and "Quality" in s.heading)
    texts = " ".join(s.text for s in q5.statements)
    assert "Improvements are required." in texts  # at least one failing check verdict
    assert "This is the target state." in texts  # at least one passing check verdict


def test_briefing_sections_carry_kinds_and_cited_tables(golden_project2, golden_project5) -> None:
    """The M18 readability reformat: lede / trend table / project cards / quality tables —
    every table row cited exactly like prose (§6)."""
    b = build_briefing([golden_project2, golden_project5], today=TODAY)
    by_kind = {s.kind for s in b.sections}
    assert by_kind == {"lede", "trend", "project", "quality"}
    for section in b.sections:
        if section.kind == "lede":
            assert section.table is None
            continue
        assert section.table is not None, section.heading
        assert len(section.table.rows) == len(section.table.row_citations)
        assert all(cites for cites in section.table.row_citations)  # §6: never uncited
    trend = next(s for s in b.sections if s.kind == "trend")
    assert trend.table is not None
    assert trend.table.headers == ("Metric", "Oldest → newest", "Trend")
    assert len(trend.table.rows) == len(trend.statements)  # one row per trended metric
    project = next(s for s in b.sections if s.kind == "project")
    assert project.table is not None and project.table.headers == ()
    labels = [row[0] for row in project.table.rows]
    for expected in ("Start", "Completion", "Activities", "Complete", "Milestones"):
        assert expected in labels
    quality = next(s for s in b.sections if s.kind == "quality")
    assert quality.table is not None
    assert quality.table.headers == ("DCMA check", "Count", "Value", "Verdict")
    assert len(quality.table.rows) == len(quality.statements)  # one row per applicable check


def test_briefing_single_version_skips_trend(golden_project5) -> None:
    b = build_briefing([golden_project5], today=TODAY)
    assert [s.heading for s in b.sections] == [
        "Workbook Summary",
        "Project5.mspdi.xml Project",
        "Project5.mspdi.xml Schedule Quality Analysis",
    ]


def test_briefing_backend_rephrases_but_keeps_citations(golden_project5) -> None:
    class Shout:
        name = "shout"
        is_local = True

        def is_available(self) -> bool:
            return True

        def list_models(self) -> tuple[str, ...]:
            return ()

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            return prompt.upper()

    plain = build_briefing([golden_project5], today=TODAY)
    shouted = build_briefing([golden_project5], backend=Shout(), today=TODAY)
    for ps, ss in zip(plain.sections, shouted.sections, strict=True):
        for p, s in zip(ps.statements, ss.statements, strict=True):
            assert s.text == p.text.upper()  # rephrased
            assert s.citations == p.citations  # citations untouched


def test_briefing_to_text_renders_headings(golden_project5) -> None:
    text = build_briefing([golden_project5], today=TODAY).to_text()
    assert text.startswith("# Schedule Forensics — Diagnostic Executive Briefing")
    assert "## Workbook Summary" in text and "## Project5.mspdi.xml Project" in text


def test_briefing_requires_at_least_one_schedule() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_briefing([])


def test_briefing_handles_undated_schedule() -> None:
    sch = Schedule(
        name="solo",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480),),
    )
    b = build_briefing([sch], today=TODAY)
    assert "not statused" in b.sections[1].statements[0].text


def test_briefing_on_empty_scope_is_cited_and_says_nothing_to_brief() -> None:
    """An empty scope (a filter that matched nothing / summary-only files) must yield a single
    cited lede, not crash on uncitable trend/quality sentences (regression for the filter)."""
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
