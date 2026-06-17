"""Animated S-curve view — cumulative planned vs actual/forecast progress (operator request)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_scurve_needs_a_schedule(client: TestClient) -> None:
    assert "Load a schedule" in client.get("/scurve").text
    assert client.get("/api/scurve").status_code == 400


def test_scurve_page_has_stepper_and_chart_frame(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/scurve").text
    assert "S-Curve" in page and "cumulative progress" in page
    # the animation controls + the chart frame (full-screen/zoom) host
    assert "id=prevScurve" in page and "id=nextScurve" in page and "id=scurvePlay" in page
    assert "id=scurveChart" in page and "chart-host" in page
    assert "/static/scurve.js" in page
    # the S-Curve is linked in the nav
    assert 'href="/scurve"' in page


def test_api_scurve_returns_cumulative_curves(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    data = client.get("/api/scurve").json()
    assert data["months"] and len(data["versions"]) == 2
    for v in data["versions"]:
        assert len(v["planned"]) == len(data["months"])
        assert len(v["actual"]) == len(data["months"])
        # cumulative percentages are non-decreasing and bounded to 100
        assert v["planned"] == sorted(v["planned"]) and v["planned"][-1] <= 100.0
        assert v["actual"] == sorted(v["actual"]) and v["actual"][-1] <= 100.0
        assert "activities" in v
