"""Mission Control — the tiled visual wall (every chart on one page, expand + data + play-all).

Operator request: one page with smaller-scale versions of every visual, expandable to dive into
the underlying data and back, with all the animations advancing together, scoped by the session
Target UID and Groups & Filters."""

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


def test_mission_in_nav(client: TestClient) -> None:
    assert '<a href="/mission">Mission Control</a>' in client.get("/").text


def test_mission_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    page = c.get("/mission").text
    assert "Load a schedule" in page


def test_mission_hosts_every_chart_container(client: TestClient) -> None:
    page = client.get("/mission").text
    assert "id=missionGrid" in page
    for cid in (
        "scurveChart",
        "ceiChart",
        "driftChart",
        "qualBars",
        "finishesChart",
        "dataDateChart",
        "slippageChart",
        "trendCharts",
    ):
        assert f"id={cid}" in page, cid
    # the dedicated chart scripts + the wall driver are all loaded
    for js in (
        "scurve.js",
        "cei.js",
        "drift.js",
        "trend_drill.js",
        "curves.js",
        "trend.js",
        "mission.js",
    ):
        assert f"/static/{js}" in page, js
    # the master animation + per-tile data affordances are present
    assert "id=missionPlay" in page and "id=missionStep" in page
    assert "tile-data" in page


def test_mission_js_drives_playall_and_data_toggle(client: TestClient) -> None:
    js = client.get("/static/mission.js").text
    assert "Play all" in js and "stepAll" in js
    assert "show-data" in js and "tile-data" in js


def test_mission_includes_critical_path_evolution_animation(client: TestClient) -> None:
    page = client.get("/mission").text
    assert "id=evoChart" in page and "id=nextEvo" in page  # the evolution stepper tile
    assert "/static/path_evolution.js" in page
    assert "nextEvo" in client.get("/static/mission.js").text  # advanced by Play-all in lockstep


def test_mission_tiles_enlarge_and_shrink(client: TestClient) -> None:
    assert "tile-expand" in client.get("/mission").text  # per-tile enlarge control
    js = client.get("/static/mission.js").text
    assert "tile-expanded" in js and "Shrink" in js


def test_scurve_surfaces_the_data_date_during_animation(client: TestClient) -> None:
    data = client.get("/api/scurve").json()
    assert data["versions"], "expected at least one S-curve version"
    assert "status_date" in data["versions"][0]  # the exact data date is in the payload…
    js = client.get("/static/scurve.js").text
    assert "status_date" in js and "data date" in js  # …shown in the label + marker as it animates


def test_mission_is_air_gapped(client: TestClient) -> None:
    for path in ("/mission", "/static/mission.js"):
        text = client.get(path).text
        externals = [
            u
            for u in re.findall(r"https?://[^\s\"'<>]+", text)
            if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
        ]
        assert not externals, (path, externals)
