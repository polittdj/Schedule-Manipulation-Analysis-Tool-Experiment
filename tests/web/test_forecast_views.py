"""Forecast page + report panel tests — the M15 deck-informed surfaces (ADR-0030)."""

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
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


def test_forecast_page_needs_a_schedule(client: TestClient) -> None:
    page = client.get("/forecast")
    assert page.status_code == 200
    assert "Load at least one analyzable schedule" in page.text
    assert client.get("/api/forecast").status_code == 400


def test_forecast_page_shows_three_methods_and_inputs(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/forecast").text
    assert "Finish forecast" in page
    for method in ("Schedule logic (CPM)", "Completion-rate extrapolation", "Earned-schedule"):
        assert method in page
    assert "2027-12-07" in page  # CPM
    assert "2028-06-10" in page  # rate
    assert "2029-02-01" in page  # earned schedule (exact-ratio IEAC)
    assert "SPI(t)" in page and "0.47" in page
    assert "Finish-controlling:" in page  # the §6 citation anchor
    assert "Forecast drift" not in page  # a single version has no drift table


def test_forecast_drift_table_across_versions_and_api(client: TestClient) -> None:
    _upload(client, "Project5")  # newer data date, loaded first — ordering must hold
    _upload(client, "Project2")
    page = client.get("/forecast").text
    assert "Forecast drift across versions" in page
    data = client.get("/api/forecast").json()
    labels = [v["label"] for v in data["versions"]]
    assert labels == ["Project2.mspdi.xml", "Project5.mspdi.xml"]  # by data date
    first, last = data["versions"][0], data["versions"][-1]
    assert first["forecasts"]["cpm"] == "2027-08-30"
    assert first["forecasts"]["earned_schedule"] == "2029-03-08"
    assert last["forecasts"]["rate"] == "2028-06-10"
    assert last["spi_t"] == 0.47 and last["remaining"] == 99


def test_report_page_shows_float_bands_and_completion_panels(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/analysis/Project5").text
    assert "Float analysis &mdash; low-float bands" in page or "low-float bands" in page
    assert "37 <span class=muted>(37.4%)</span>" in page  # total float 0 days
    assert "Completion performance" in page
    assert "18 of 27 (66.7%)" in page  # completed behind baseline
    data = client.get("/api/analysis/Project5").json()
    assert data["float_bands"]["float_total_0"]["count"] == 37
    assert data["float_bands"]["float_free_lt10"]["count"] == 75
    assert data["completion"]["avg_days_late"]["value"] == 39.2
    assert data["completion"]["mei"]["population"] == 0  # NA on the goldens — honest
