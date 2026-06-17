"""Schedule Quality Ribbon view — Fuse-style per-schedule metric matrix."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLD = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_ribbon_empty_state(client: TestClient) -> None:
    assert "Load one or more schedules" in client.get("/ribbon").text


def test_ribbon_lists_metrics_per_schedule(client: TestClient) -> None:
    data = (GOLD / "Project2.mspdi.xml").read_bytes()
    client.post("/upload", files={"files": ("Project2.mspdi.xml", data, "text/xml")})
    page = client.get("/ribbon").text
    assert "Schedule Quality Ribbon" in page
    # the ribbon columns are present
    for col in ("Missing Logic", "Logic Density", "Critical", "Merge Hotspot", "Number of Leads"):
        assert col in page
    # Project2's Fuse-validated values appear (Missing Logic 6, Logic Density 2.79)
    assert "Project2" in page and ">6<" in page and "2.79" in page
    # linked in the nav
    assert 'href="/ribbon"' in page
