"""Frozen header + header Reset, WBS-derived hierarchy, forecast rollup, globe (ADR-0188)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


# --- frozen header + Reset in the title bar -----------------------------------------


def test_header_is_frozen_and_carries_reset(client: TestClient) -> None:
    page = client.get("/").text
    assert "id=sfResetView" in page  # Reset rides in the always-visible header nav
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "position:sticky;top:0;z-index:110" in css  # the title bar stays while scrolling


def test_globe_has_no_wordmark_and_arcs_fit(client: TestClient) -> None:
    page = client.get("/").text
    assert "nasa-globe-text" not in page  # the NASA word is gone from the globe
    assert ">NASA<" not in page
    globe = (STATIC / "globe.js").read_text(encoding="utf-8")
    # the globe radius leaves headroom so the rocket arcs stay ENTIRELY inside the canvas:
    # apogee = R * (1 + 0.5) must be < size/2 -> R = 0.31 * size
    assert "R = size * 0.31" in globe
    assert "R * 0.5 * t" in globe
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "nasa-globe-text" not in css


# --- WBS-derived hierarchy on the Activities grid ------------------------------------


def test_activities_grid_derives_wbs_hierarchy_when_flat() -> None:
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    # flat-file detection + rollup construction + honest disclosure note
    assert "derivedMode" in js and "withWbsRollups" in js
    assert "__wbsRollup" in js and "wbs-rollup-note" in js
    assert "schedule data is invented" in js  # the honest-disclosure note text
    # real-summary files bypass the derivation entirely
    assert "hasRealSummaries" in js


def test_xer_outline_level_from_wbs_depth(client: TestClient) -> None:
    xer = (
        Path(__file__).resolve().parents[1] / "fixtures" / "xer" / "commercial_construction.xer"
    ).read_bytes()
    resp = client.post(
        "/upload", files={"files": ("commercial_construction.xer", xer, "text/plain")}
    )
    assert resp.status_code == 200
    data = client.get("/api/analysis/commercial_construction.xer").json()
    by_name = {a["name"]: a for a in data["activities"]}
    # wbs "CC.DESIGN" -> level 2; the root WBS band "CC" -> level 1
    assert by_name["Schematic Design"]["outline_level"] == 2
    assert by_name["Commercial Construction"]["outline_level"] == 1


# --- forecast: group-weighted rollup --------------------------------------------------


def test_forecast_group_rollup_panel_renders(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/forecast?group_field=WBS").text
    assert "Project rollup" in page
    assert "Group-weighted rollup" in page and "Top-down (whole project)" in page
    assert "weighted by its to-go activity count" in page  # the weighting basis is disclosed
    # without a grouping the rollup panel stays absent
    assert "Project rollup" not in client.get("/forecast").text
