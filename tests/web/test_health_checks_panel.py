"""The Structural Health Checks panel renders on the analysis page (stoplight per check)."""

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


def test_analysis_page_shows_structural_health_checks(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "Structural health checks" in page
    # a couple of the named checks render
    assert "Critical merge hotspots" in page and "Missing WBS" in page
