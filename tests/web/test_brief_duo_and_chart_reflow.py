"""Briefing sections 6+7 half-page duo + chart expand reflow (ADR-0163).

Operator 2026-07-08: (a) "6. Recommended Actions" takes half the Executive-Briefing page and
"7. How to Verify Every Number" the other half, with citations readable without sideways
scrolling; (b) expanding a chart REFORMATS it to the page space (design-size fonts) instead of
magnifying it. The live geometry was verified in Chromium; these pin the server render and the
vendored-JS mechanics so a refactor can't silently regress them.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File", "Hard_File_updated"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
    return c


def test_briefing_pairs_sections_6_and_7_in_a_half_page_duo(client: TestClient) -> None:
    page = client.get("/briefing").text
    assert "brief-duo" in page
    # the duo holds exactly the two operator-named sections, 6 left then 7 right
    duo = page.split("brief-duo", 1)[1]
    a = duo.find("Recommended Actions")
    b = duo.find("How to Verify")
    assert a != -1 and b != -1 and a < b
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ".brief-duo" in css
    assert "grid-template-columns: 1fr 1fr" in css  # true half/half partners


def test_chartframe_expand_reformats_instead_of_magnifying() -> None:
    js = (STATIC / "chartframe.js").read_text(encoding="utf-8")
    # expanded charts CONTAIN-FIT the viewport (ADR-0187): as large as fits BOTH dimensions
    assert "(availH * vbW) / vbH" in js and "fitW" in js
    assert "sf-reflow" in js  # reflow-aware charts are told to redraw at the new size
    # denied/absent Fullscreen API both fall back to the fixed maximize (headless/kiosk safety)
    assert "req.catch(maximize)" in js


def test_enlarged_mosaic_chart_releases_its_fixed_tile_height() -> None:
    """Operator 2026-07-15: on the Mission-wall pages (perfGrid G1-G5, etc.) every chart is a
    ``.mosaic .tile .chart-host`` clamped to a fixed 340/460/74vh height so the wall stays even.
    chartframe's ⤢ Enlarge CONTAIN-FITS the SVG to the viewport, but that fixed host height kept
    clamping it — the fitted (much taller) chart was clipped to a top strip, so only the tall
    data-date spike showed and the low-value months fell below the fold (the "tiny sliver" bug).
    The fix RELEASES the host height in both enlarge modes (real :fullscreen + the .cf-max
    maximize fallback). Pins the release rule and that it out-specifies the clamps it overrides."""
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    # the clamps we must override still exist (else this guard is testing nothing)
    assert ".mosaic .tile .chart-host { height: 340px" in css
    assert ".mosaic .tile.tile-wide .chart-host { height: 460px" in css
    # both enlarge modes release the host height so the contain-fit SVG shows in full
    for sel in (
        ".mosaic .tile .cf-frame:fullscreen .chart-host",
        ".mosaic .tile .cf-frame.cf-max .chart-host",
    ):
        assert sel in css, sel
    release = css.split(".mosaic .tile .cf-frame:fullscreen .chart-host", 1)[1][:160]
    assert "height: auto" in release and "overflow: visible" in release
    # the release must come AFTER the clamps (equal-specificity tiebreak) AND out-specify them
    # (…tile .cf-frame.cf-max .chart-host is one class deeper than …tile .chart-host)
    assert css.index(".mosaic .tile .cf-frame.cf-max .chart-host") > css.index(
        ".mosaic .tile .chart-host { height: 340px"
    )


def test_sra_and_progress_charts_render_one_to_one() -> None:
    sra = (STATIC / "sra.js").read_text(encoding="utf-8")
    # 1:1 pixel geometry: viewBox width == container px, so fonts stay design-size
    assert "function chartW(box)" in sra
    assert sra.count("chartW(box)") >= 5  # helper + the four charts (cdf/hist/sens/risk)
    assert 'window.addEventListener("sf-reflow"' in sra
    scurve = (STATIC / "scurve.js").read_text(encoding="utf-8")
    assert "box.clientWidth" in scurve
    assert 'window.addEventListener("sf-reflow"' in scurve
