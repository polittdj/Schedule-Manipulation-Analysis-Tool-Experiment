"""Total-float distribution histogram on the analysis page (handbook §6.3.2.5.2.2 visual type).

Pure presentation over the per-activity rows the grid already serves (/api/analysis/<name>), binned
client-side — no engine numbers, keeps the air-gap."""

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


def test_analysis_page_hosts_the_histogram(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=floatHist" in page and 'data-name="Project5"' in page
    assert "/static/histogram.js" in page
    assert "Total-float distribution" in page


def test_histogram_js_is_local_and_a11y(client: TestClient) -> None:
    js = client.get("/static/histogram.js")
    assert js.status_code == 200
    assert "/api/analysis/" in js.text
    assert "SFA11y.label" in js.text and "SFA11y.table" in js.text  # accessible name + data table
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", js.text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
