"""WBS breakdown view tests (PBIX pages 8, 9; ADR-0041)."""

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


def test_wbs_page_renders_both_pivots(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/wbs/Project5").text
    assert "Completion metrics by WBS" in page and "22 groups" in page
    assert "SPI(t) &amp; Earned Schedule by WBS" in page
    assert "id=wbsChart" in page and "/static/wbs.js" in page
    # the completion pivot headers
    for col in ("Total", "Done", "% comp", "Ahead", "Behind", "Dur avg"):
        assert col in page


def test_wbs_page_404_for_unknown_schedule(client: TestClient) -> None:
    assert client.get("/wbs/Nope").status_code == 404


def test_api_wbs_serves_grouped_series(client: TestClient) -> None:
    _upload(client, "Project5")
    data = client.get("/api/wbs/Project5").json()
    groups = data["groups"]
    assert len(groups) == 22
    assert [g["wbs"] for g in groups][:3] == ["1", "2", "3"]  # numeric order
    assert sum(g["total"] for g in groups) == 126
    assert sum(g["completed"] for g in groups) == 27
    # SPI(t) is present (a number) or null — never a fabricated 0 from an empty group
    for g in groups:
        assert g["spi_t"] is None or isinstance(g["spi_t"], (int, float))


def test_api_wbs_404_for_unknown(client: TestClient) -> None:
    assert client.get("/api/wbs/Nope").status_code == 404


def test_wbs_export_xlsx_and_docx(client: TestClient) -> None:
    _upload(client, "Project5")
    for fmt in ("xlsx", "docx"):
        resp = client.get(f"/export/{fmt}/wbs/Project5")
        assert resp.status_code == 200 and len(resp.content) > 0
    assert client.get("/export/pdf/wbs/Project5").status_code == 404
    assert client.get("/export/xlsx/wbs/Nope").status_code == 404


def test_dashboard_row_links_wbs(client: TestClient) -> None:
    _upload(client, "Project5")
    assert 'href="/wbs/Project5"' in client.get("/").text
