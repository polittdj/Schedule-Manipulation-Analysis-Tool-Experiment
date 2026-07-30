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

_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    """TWO versions of the one golden Project (ADR-0262): the full wall is the ≥2-version
    rendering — below that the cross-version tiles degrade to a note instead of fetching
    their ≥2-version APIs (pinned in test_mission_one_version.py)."""
    c = TestClient(create_app(SessionState()))
    c.post(
        "/upload",
        files=[
            ("files", (name, (_GOLDEN_DIR / name).read_bytes(), "text/xml"))
            for name in ("Project2.mspdi.xml", "Project5.mspdi.xml")
        ],
    )
    return c


def test_mission_in_nav(client: TestClient) -> None:
    assert 'href="/mission"' in client.get("/").text  # Overview · Mission Control (ADR-0196)


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
    page = client.get("/mission").text
    assert "tile-expand" in page  # per-tile enlarge control
    assert "⛶ ENLARGE" in page  # the panel-contract label (Mission Ops rank 2)
    js = client.get("/static/mission.js").text
    assert "tile-expanded" in js and "SHRINK" in js  # contract vocabulary, panelkit.js's labels


# ── Mission Ops rank 2 (prototype 'ctl'): the panel contract on every tile ────────────────────────


def test_mission_tiles_carry_the_three_glyph_strip(client: TestClient) -> None:
    """Every live tile's actions are the exact panel-contract strip — ▦ DATA / ⤓ EXCEL /
    ⛶ ENLARGE — plus the 'Open NN →' chapter link. ⤓ follows the tile's data-export to an
    EXISTING /export endpoint (never a new computation), handled by panelkit.js delegation."""
    page = client.get("/mission").text
    assert page.count("▦ DATA") >= 9  # one per live tile (9 tiles at two versions)
    assert page.count("⤓ EXCEL") >= 9
    assert page.count("⛶ ENLARGE") >= 9
    for export in (
        "/export/xlsx/scurve",
        "/export/xlsx/cei",
        "/export/xlsx/forecast",
        "/export/xlsx/curves",
        "/export/xlsx/evolution",
        "/export/xlsx/trend",
    ):
        assert f'data-export="{export}"' in page, export
    # chapter links: 04 Evolution · 05 Trend/Curves · 06 Bow Wave/CEI · 09 S-Curve/Forecast
    for chapter_link in ("Open 04 &rarr;", "Open 05 &rarr;", "Open 06 &rarr;", "Open 09 &rarr;"):
        assert chapter_link in page, chapter_link
    assert "/static/panelkit.js" in page  # the ⤓ EXCEL handler (delegated, CSP-safe)


def test_mission_tiles_carry_provenance_chips(client: TestClient) -> None:
    """Each tile carries a SOURCE: file · DD date provenance chip, i18n-inert (filenames and
    dates are never machine-translated)."""
    page = client.get("/mission").text
    assert page.count("prov-chip") >= 9
    assert page.count("<span class=prov-chip data-no-i18n>SOURCE: ") >= 9
    assert " · DD " in page
    # the lifted Quality-Trend tiles read the same chip text from the host's data-prov stamp
    assert "data-prov=" in page
    js = client.get("/static/trend.js").text
    assert 'getAttribute("data-prov")' in js and "prov-chip" in js


def test_mission_tiles_carry_takeaway_sentences(client: TestClient) -> None:
    """Each live tile carries a one-line takeaway (.sf-take) — a complete sentence whose
    figures come only from the version manifest and the briefing's own banner."""
    page = client.get("/mission").text
    assert page.count("sf-take") >= 9  # one finding-sentence per live tile
    assert "loaded versions" in page  # the manifest count lives inside the sentences


def test_mission_verdict_band_quotes_the_briefing(client: TestClient) -> None:
    """The verdict band (gradient wash + 3px left edge) surfaces the EXISTING Executive
    Briefing verdict verbatim, links to /briefing, and shows the measured-to target chip."""
    page = client.get("/mission").text
    assert "verdict-band" in page and "Mission verdict" in page
    m = re.search(r"<div class=vb-verdict[^>]*>([^<]+)</div>", page)
    assert m is not None
    verdict = m.group(1)
    assert verdict in {"ON TRACK", "WATCH", "AT RISK", "N/A"}
    assert verdict in client.get("/briefing").text  # the SAME string the briefing renders
    assert 'href="/briefing"' in page  # Open the briefing →
    assert "MEASURED TO PROJECT FINISH" in page  # no session target set in this fixture


def test_mission_kpi_tiles_quote_the_briefing_banner(client: TestClient) -> None:
    """The ctl KPI tiles (2px colored top edge) restate the briefing banner's own
    label/value pairs verbatim — no figure is computed on this page."""
    page = client.get("/mission").text
    assert "ctl-kpis" in page and page.count("ctl-kpi") >= 5
    # ADR-0310 renamed the CPM tile: a pure-logic figure must not be labelled a forecast.
    for label in (
        "Status",
        "SPI (duration-based)",
        "Schedule-logic finish (CPM)",
        "Baseline finish",
        "Slip",
    ):
        assert label in page, label


def test_mission_overview_lines_animate_in_lockstep(client: TestClient) -> None:
    # the overview line charts mark their solid lines as drawable…
    for js in ("curves.js", "trend.js"):
        text = client.get(f"/static/{js}").text
        assert "sf-curve-line" in text and 'pathLength: "1"' in text, js
    # …and Play-all re-draws them each beat
    mjs = client.get("/static/mission.js").text
    assert "replayDraw" in mjs and "sf-draw" in mjs
    css = client.get("/static/app.css").text
    assert "@keyframes sf-draw" in css


def test_scurve_surfaces_the_data_date_during_animation(client: TestClient) -> None:
    data = client.get("/api/scurve").json()
    assert data["versions"], "expected at least one S-curve version"
    assert "status_date" in data["versions"][0]  # the exact data date is in the payload…
    js = client.get("/static/scurve.js").text
    assert "status_date" in js and "data date" in js  # …shown in the label + marker as it animates


def test_mission_bottom_charts_match_the_top_tiles(client: TestClient) -> None:
    """Operator: the big bottom charts (Critical-Path Evolution + Quality Trend) are now the SAME
    size as the top tiles (no full-width 'wide' tile) and carry the same attributes — enlarge, the
    Data toggle (underlying-data table), hover call-outs, and Play-all animation."""
    page = client.get("/mission").text
    assert "tile-wide" not in page  # no oversized bottom tiles — every tile is one grid cell
    assert "id=evoChart" in page and "id=trendCharts" in page  # both still on the wall
    # the Evolution tile now exposes an underlying-data table (Data toggle) — it had none before
    evo = client.get("/static/path_evolution.js").text
    assert "SFA11y.table(" in evo and "Critical path this version" in evo
    assert "bar.title = " in evo  # per-bar hover call-out (HTML title -> cf-tip, ADR-0187)
    # the Quality Trend tile's points now carry hover call-outs too (it had none before)
    trend = client.get("/static/trend.js").text
    assert 'svgEl("title"' in trend


def test_mission_is_air_gapped(client: TestClient) -> None:
    for path in ("/mission", "/static/mission.js"):
        text = client.get(path).text
        externals = [
            u
            for u in re.findall(r"https?://[^\s\"'<>]+", text)
            if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
        ]
        assert not externals, (path, externals)


def test_mission_quality_tiles_sit_in_the_main_grid_one_chart_per_visual(
    client: TestClient,
) -> None:
    """Operator 2026-07-09: the separate 'Quality Control' section left a mostly-empty row of
    dead space — Quality Offenders and Quality Trend now sit in the ONE mission grid next to
    Critical-Path Evolution, and on the wall trend.js lifts each quality-trend chart into its
    OWN tile (one graph per visual) instead of cramming ~15 charts into a single tile."""
    page = client.get("/mission").text
    assert "missionQcGrid" not in page
    assert ">Quality Control</h2>" not in page
    grid = page.split("id=missionGrid")[1]
    evo = grid.index("Critical-Path Evolution")
    offenders = grid.index("Quality Offenders")
    trend = grid.index("Quality Trend")
    assert evo < offenders < trend  # side by side, in order, in the same grid
    js = client.get("/static/trend.js").text
    assert "wallTile" in js  # the one-chart-per-tile splitter
    assert 'classList.contains("chart")' in js  # section headings are skipped, charts lifted
    assert "hostTile.hidden = true" in js  # the emptied host tile collapses away
