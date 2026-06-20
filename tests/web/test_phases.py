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


def test_phases_renders_chart_table_and_basis_options(client: TestClient) -> None:
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
    # the stacked bar chart + the year table both render
    assert "Activities per year by phase" in page
    assert "<th scope=col>Year</th>" in page


def test_phases_basis_param_changes_binning(client: TestClient) -> None:
    finish = client.get("/phases?basis=finish").text
    start = client.get("/phases?basis=start").text
    # the selected option follows the query param
    assert "<option value=finish selected>" in finish or 'value="finish" selected' in finish
    assert "Binned by <b>Start</b>" in start


def test_phases_is_air_gapped(client: TestClient) -> None:
    text = client.get("/phases").text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
