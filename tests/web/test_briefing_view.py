"""The /briefing page's readability reformat (M18) — cards, cited tables, print-ready."""

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


def test_briefing_renders_cards_and_cited_tables(client: TestClient) -> None:
    page = client.get("/briefing").text
    assert "brief-cards" in page  # the side-by-side project cards grid
    assert "brief-lede" in page  # the workbook summary lede
    assert "DCMA check" in page and "Verdict" in page  # the quality verdict table
    assert "Oldest → newest" in page  # the cross-version trend table
    # every quality/trend table row ends in a citation cell (UID present)
    assert page.count("class=cite") > 10
    for label in ("Start", "Completion", "Activities", "Milestones"):
        assert f"<td>{label}</td>" in page  # the project profile strip


def test_briefing_single_version_still_renders(client: TestClient) -> None:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    page = c.get("/briefing")
    assert page.status_code == 200
    assert "brief-cards" in page.text and "DCMA check" in page.text
    assert "Trend Analysis" not in page.text  # one version: no trend section
