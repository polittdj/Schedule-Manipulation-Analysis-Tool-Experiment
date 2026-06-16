"""Critical-Path Evolution view tests (M18 item 7, ADR-0044)."""

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


def test_evolution_needs_two_versions(client: TestClient) -> None:
    assert "at least two analyzable versions" in client.get("/evolution").text
    _upload(client, "Project5")
    assert "at least two analyzable versions" in client.get("/evolution").text
    assert client.get("/api/evolution").status_code == 400


def test_evolution_page_has_stepper_controls(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "Critical-Path Evolution" in page
    assert "id=prevEvo" in page and "id=nextEvo" in page and "id=evoPlay" in page
    assert "id=evoChart" in page and "/static/path_evolution.js" in page


def test_api_evolution_serves_per_version_snapshots(client: TestClient) -> None:
    _upload(client, "Project5")  # load order reversed on purpose
    _upload(client, "Project2")
    data = client.get("/api/evolution").json()
    snaps = data["snapshots"]
    assert [s["label"] for s in snaps] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    first, second = snaps
    assert first["finish_delta_days"] is None  # no prior version
    assert len(first["critical"]) == 43 and len(second["critical"]) == 37
    assert second["finish_delta_days"] == 99  # the known P2->P5 slip
    assert len(second["left"]) == 6 and second["entered"] == []
    # critical UIDs carry display names; the "left" ones resolve from the prior version
    assert all(str(u) in second["names"] for u in second["critical"])
    assert all(str(u) in second["names"] for u in second["left"])


def test_evolution_export_xlsx_and_docx(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    for fmt in ("xlsx", "docx"):
        resp = client.get(f"/export/{fmt}/evolution")
        assert resp.status_code == 200 and len(resp.content) > 0
    assert client.get("/export/pdf/evolution").status_code == 404


def test_dashboard_and_nav_link_evolution(client: TestClient) -> None:
    # nav links it unconditionally; the dashboard body row appears with >= 2 versions
    _upload(client, "Project2")
    home = client.get("/").text
    assert 'href="/evolution">Critical-Path Evolution</a>' in home  # nav
    assert "Critical-path evolution &rarr;" not in home  # body row not yet (one version)
    _upload(client, "Project5")
    assert "Critical-path evolution &rarr;" in client.get("/").text
