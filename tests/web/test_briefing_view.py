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
