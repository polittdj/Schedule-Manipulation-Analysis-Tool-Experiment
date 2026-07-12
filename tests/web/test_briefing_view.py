"""The /briefing page — the leadership forensic Executive Briefing (ADR-0121): a metadata header,
a verdict banner, the numbered sections, cited tables, and a Word/Excel hand-out export."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    return c


def test_briefing_renders_the_numbered_forensic_document(client: TestClient) -> None:
    page = client.get("/briefing").text
    assert "brief-doc" in page and "brief-banner" in page  # the document + the verdict banner
    assert "brief-meta" in page  # the metadata header (report date / data date / source / class)
    # the numbered sections tile into a full-width responsive card grid (operator: "use the entire
    # page space and keep it formatted"), with the Bottom Line spanning the top
    assert "brief-grid" in page and 'class="brief-card lead"' in page
    for heading in (
        "1. The Bottom Line",
        "2. How the Project Has Performed",
        "3. The Critical Path",
        "4. Schedule Health Dashboard",
        "5. Risks and Opportunities",
        "6. Recommended Actions",
        "7. How to Verify Every Number",
    ):
        assert heading in page
    # the verdict tints the banner, and a Word/Excel hand-out is offered
    assert any(v in page for v in ("verdict-on-track", "verdict-watch", "verdict-at-risk"))
    assert "/export/docx/briefing" in page and "/export/xlsx/briefing" in page
    # tables carry per-row citations (UID present)
    assert page.count("class=cite") > 8


def test_briefing_tables_are_never_column_crushed(client: TestClient) -> None:
    """Operator screenshot (2026-07-07): every briefing table rendered one character per line.

    Root cause was a pincer: ``td.cite`` was ``white-space: nowrap`` (an unbreakable, very wide
    citation column) while ADR-0150's containment override set ``word-break: break-word`` on the
    whole table — auto-layout gave the citation column its full unbreakable width and crushed
    every other column to its new one-character min-content width. Pin both halves of the fix:
    citations wrap in a bounded block, and no briefing-table rule reintroduces break-all/break-word
    (a wide table scrolls inside its card instead)."""
    page = client.get("/briefing").text
    css = client.get("/static/app.css").text
    # the layout override keeps containment but must NOT re-crush table cells
    assert ".brief-card{overflow-x:auto}" in page
    assert "word-break:break-word" not in page and "word-break: break-word" not in page
    assert ".brief-card th{white-space:nowrap}" in page  # headers never stack vertically
    # the citation column wraps inside a bounded block instead of forcing the table wide
    cite_rule = next(line for line in css.splitlines() if line.startswith(".brief-table td.cite"))
    assert "nowrap" not in cite_rule
    assert "max-width" in cite_rule


def test_briefing_single_version_still_renders(client: TestClient) -> None:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    page = c.get("/briefing")
    assert page.status_code == 200
    assert "brief-doc" in page.text and "1. The Bottom Line" in page.text
    # one version: the then-vs-now subsection states the single-version limitation
    assert "3.1 What Changed" in page.text
    assert "Only one schedule version is loaded" in page.text


def test_briefing_word_and_excel_exports(client: TestClient) -> None:
    docx = client.get("/export/docx/briefing")
    assert docx.status_code == 200
    assert docx.content[:2] == b"PK"  # a real .docx (zip container)
    assert "wordprocessingml" in docx.headers["content-type"]
    assert "executive-briefing.docx" in docx.headers["content-disposition"]
    xlsx = client.get("/export/xlsx/briefing")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


def test_briefing_tables_stay_readable(client: TestClient) -> None:
    """Operator report 2026-07-08: the citation column's nowrap let one long
    'Task (UID n, file.mpp)' string hog its half-width card and crush every other column to one
    character per line. Pins the three-part fix: citations WRAP, every table sits in a
    horizontal-scroll wrapper (a too-wide table scrolls instead of squeezing its neighbours),
    and many-column tables promote their card to the full grid row."""
    css = client.get("/static/app.css").text
    cite_rule = css.split(".brief-table td.cite")[1].split("}")[0]
    assert "nowrap" not in cite_rule and "overflow-wrap" in cite_rule
    assert ".brief-scroll" in css and ".brief-card.wide" in css
    page = client.get("/briefing").text
    assert "brief-scroll" in page  # every table is wrapped
    assert 'class="brief-card wide"' in page  # >=5-column tables take the full row


def test_briefing_chapter_12_page_shell(client: TestClient) -> None:
    """ADR-0210 — chapter 12 "The briefing": the verdict takeaway h1, the banner KPI strip, and
    the Action-items / Quality-snapshot bars — the executive synthesis, from the briefing's own
    verdict + banner + findings/audit. The cited briefing body survives beneath (outside the
    AI-swapped region so the header is stable)."""
    page = client.get("/briefing").text  # the fixture has loaded Project2 + Project5
    assert 'class="page-takeaway"' in page
    assert "Bottom line: the schedule is" in page
    assert 'class="ws-kpi"' in page
    assert "Action items by severity" in page and "Quality snapshot" in page
    assert 'class="stack-bar"' in page
    assert "CHAPTER 12 · THE BRIEFING" in page
    # the header sits OUTSIDE the AI-swapped briefing body
    assert page.index("page-takeaway") < page.index("id=briefingBody")
