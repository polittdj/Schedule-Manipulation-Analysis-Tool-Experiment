"""Trends-animation package — Mission-Control-style controls on the dedicated chart pages.

Operator directives (this package): every Trends-page visual carries the wall's per-tile
controls (⛶ Enlarge, ▦ Data) plus — where multi-frame makes sense — a Prev / Play / Next
stepper; the multi-schedule OVERLAYS are replaced by ANIMATION through the loaded files
(one file per frame on the curves' date axis; a progressive reveal on a LOCKED version axis
for the version-indexed trend charts), every frame naming its file ("file X of N — name
(data date …)"); prefers-reduced-motion is honored; and a master Play-all / Step-all drives
every stepper in lockstep exactly like mission.js on the wall. All client-side over the
payloads the pages already serve (air-gap unchanged).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: the per-chart frame-stepper conventions shared by every animated chart script
_FRAME_MARKERS = (
    "sf-frame-prev",
    "sf-frame-next",
    "sf-frame-play",
    "sf-frame-label",
    '"file "',  # the provenance caption: "file X of N — <filename> (data date …)"
    "data date",
    "prefers-reduced-motion",  # Play advances one frame instead of running a timer
)

#: the wall's per-tile Enlarge conventions, reused verbatim so the pattern reads identically
_TILE_MARKERS = ("tile-expand", "tile-expanded", "Shrink")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_trend_charts_gain_steppers_enlarge_and_provenance(client: TestClient) -> None:
    """trend.js: version-indexed charts animate as a progressive reveal on a LOCKED axis
    (frame k shows files 1…k+1 — never one-file-per-frame, the x axis IS the versions),
    with the wall's Enlarge/Data toggles and the provenance frame label."""
    js = client.get("/static/trend.js").text
    for marker in _FRAME_MARKERS + _TILE_MARKERS:
        assert marker in js, marker
    assert "tile-data" in js and "show-data" in js  # the wall's per-chart Data toggle
    # progressive reveal on the locked version axis + the current frame's guide marker
    assert "sf-frame-layer" in js and "sfFrameGuide" in js
    assert "i <= k" in js  # frame k reveals versions 0…k (the axis itself is drawn once)
    # single-file charts state their source instead of animating
    assert '"Source: " + src' in js


def test_trend_page_master_play_all(client: TestClient) -> None:
    """trend.js wires a page-level master Play all / Step all (the mission.js pattern):
    one beat clicks every .sf-frame-next plus the quality drill-down's #qualNext."""
    js = client.get("/static/trend.js").text
    assert "sfPlayAll" in js and "sfStepAll" in js
    assert "Play all" in js and "Pause all" in js and "Step all" in js
    assert "qualNext" in js  # the existing drill stepper joins the beat
    assert 'querySelectorAll(".sf-frame-next")' in js


def test_curves_animate_one_file_per_frame(client: TestClient) -> None:
    """curves.js: the Data-Date Finishes and Slippage overlays are REPLACED by one-file-per-
    frame animation on axes held fixed across frames (date axis shared; count axis locked to
    every file's tallest point), keeping each file's palette color."""
    js = client.get("/static/curves.js").text
    for marker in _FRAME_MARKERS + _TILE_MARKERS:
        assert marker in js, marker
    assert "lockTop" in js  # the count axis is pinned across frames — movement is real
    assert "one file per frame" in js
    assert "PALETTE[k % PALETTE.length]" in js  # the frame keeps its file's color identity
    # the old always-on all-versions overlay series builders are gone
    assert "slipSeries" not in js
    assert "label: labels[k]" in js  # per-frame series are labeled by the frame's file
    # a single loaded file keeps the classic view and states its source
    assert '"Source: " + src' in js
    # the master pair rides the page's existing top control row
    assert "sfPlayAll" in js and "sfStepAll" in js


def test_margin_burndown_animates_on_locked_axes(client: TestClient) -> None:
    js = client.get("/static/margin.js").text
    for marker in _FRAME_MARKERS + _TILE_MARKERS:
        assert marker in js, marker
    assert "tile-data" in js and "show-data" in js
    assert "idx <= k" in js  # progressive reveal up to the frame's version
    assert "sf-frame-guide" in js  # the current frame marked on the locked axis


def test_scatter_gains_enlarge_and_visible_provenance(client: TestClient) -> None:
    """scatter.js: the tile-consistent ⛶ Enlarge control plus a visible 'Source: <schedule>'
    label read from the host's data-name (the same key the plot fetches)."""
    js = client.get("/static/scatter.js").text
    for marker in _TILE_MARKERS:
        assert marker in js, marker
    assert '"Source: " + name' in js
    assert 'getAttribute("data-name")' in js


def test_mission_master_drives_the_package_steppers(client: TestClient) -> None:
    """mission.js Play-all clicks every .sf-frame-next on the wall, so the new per-chart
    animations advance on the same beat as the wall's own steppers."""
    js = client.get("/static/mission.js").text
    assert 'querySelectorAll(".sf-frame-next")' in js


def test_app_css_carries_the_package_rules(client: TestClient) -> None:
    css = client.get("/static/app.css").text
    assert ".sf-chart-controls" in css and ".sf-frame-label" in css
    assert ".charts .chart.tile-expanded" in css  # a Trend-page chart grows to the full row
    assert ".sf-tilebox.tile-expanded" in css  # a standalone chart lifts to a viewport overlay
    assert ".show-data .sr-only" in css  # the per-chart Data reveal, off the wall


def test_frame_labels_have_their_provenance_fields_in_the_payloads(client: TestClient) -> None:
    """The frame captions read label + status_date per version — every animated chart's
    payload (/api/trend, /api/curves, /api/margin) already carries both, per version."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    for api in ("/api/trend", "/api/curves", "/api/margin"):
        versions = client.get(api).json()["versions"]
        assert len(versions) == 2, api
        for v in versions:
            assert v["label"], api
            assert "status_date" in v, api


def test_package_scripts_stay_air_gapped(client: TestClient) -> None:
    import re

    for name in ("trend.js", "curves.js", "margin.js", "scatter.js", "mission.js"):
        js = client.get(f"/static/{name}").text
        externals = [
            u
            for u in re.findall(r"https?://[^\s\"'<>]+", js)
            if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
        ]
        assert not externals, (name, externals)
