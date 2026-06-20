"""Activity scatter plot on the analysis page (handbook/deck visual type — float vs duration).

Pure presentation over the per-activity rows the grid already serves (/api/analysis/<name>), so it
adds no engine numbers and keeps the air-gap."""

from __future__ import annotations

import re
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


def test_analysis_page_hosts_the_scatter(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=scatterChart" in page and 'data-name="Project5"' in page
    assert "/static/scatter.js" in page


def test_scatter_data_source_carries_float_and_duration(client: TestClient) -> None:
    data = client.get("/api/analysis/Project5").json()
    acts = data["activities"]
    assert acts, "expected activity rows to plot"
    a = acts[0]
    for field in ("total_float_days", "duration_days", "is_critical", "is_milestone", "is_summary"):
        assert field in a, field


def test_scatter_js_is_local(client: TestClient) -> None:
    js = client.get("/static/scatter.js")
    assert js.status_code == 200 and "/api/analysis/" in js.text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", js.text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
