"""The Schedule-margin panel renders on the analysis page (graceful when no margin tasks)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def test_analysis_page_shows_schedule_margin_panel(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "Schedule margin" in page
    # The golden carries no margin-named activities, so the graceful note renders.
    if "No schedule-margin tasks found" in page:
        assert "name contains the word" in page
    else:
        # If the golden ever gains margin tasks, the headline stats render instead.
        assert "Total margin" in page and "Effective margin" in page
