"""Year Trend / Phase page (D) — per-year activity distribution with selectable binning basis."""

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


def test_phases_in_nav(client: TestClient) -> None:
    assert '<a href="/phases">Year Phases</a>' in client.get("/").text


def test_phases_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    assert "Load a schedule" in c.get("/phases").text


def test_phases_renders_animated_stepper_table_and_basis_options(client: TestClient) -> None:
    page = client.get("/phases").text
    assert "Year Trend / Phase" in page
    # all four binning bases are offered (the operator's multiple options)
    for label in (
        "Scheduled / forecast finish",
        "Baseline finish",
        "Actual finish",
    ):
        assert label in page
    assert "<select name=basis" in page
    # the animated cross-version stepper (the new presentation) + the per-version detail table
    assert "id=phasesChart" in page and "/static/phases.js" in page
    assert "id=phasesPlay" in page  # the animation controls
    assert "<th scope=col>Year</th>" in page


def test_phases_basis_param_changes_binning(client: TestClient) -> None:
    finish = client.get("/phases?basis=finish").text
    start = client.get("/phases?basis=start").text
    # the selected option follows the query param
    assert "<option value=finish selected>" in finish or 'value="finish" selected' in finish
    assert "Binned by <b>Start</b>" in start
    assert 'data-basis="start"' in start  # the stepper fetches /api/phases on the same basis


def test_phases_api_returns_per_version_locked_axis(client: TestClient) -> None:
    data = client.get("/api/phases?basis=finish").json()
    assert data["basis"] == "finish" and data["versions"]
    assert data["max_total"] >= 1 and isinstance(data["years"], list)
    # every version's rows are aligned to the shared year axis (locked across the animation)
    for v in data["versions"]:
        assert len(v["rows"]) == len(data["years"])
    # an unknown basis falls back to finish (never errors)
    assert client.get("/api/phases?basis=bogus").json()["basis"] == "finish"


def test_phases_js_is_local(client: TestClient) -> None:
    js = client.get("/static/phases.js")
    assert js.status_code == 200 and "/api/phases" in js.text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", js.text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals


def test_phases_is_air_gapped(client: TestClient) -> None:
    text = client.get("/phases").text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
