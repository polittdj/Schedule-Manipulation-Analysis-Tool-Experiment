"""NASA theme chrome — a 3D rotating wireframe Earth insignia (globe.js), CUI page-marking bars,
dotted chart grid.

Operator request: a transparent 3D Earth (continent outlines, see-through) rotating around a
STATIONARY "NASA" wordmark in the top-right — 3x the old meatball — which also doubles as the
page-wide AI status light (spins up + glows while the local model generates). Plus the CUI marking
top and bottom of every page and a dotted reading grid behind the charts. All assets stay
vendored/local (air-gap, Law 1)."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai import AIConfig, Classification
from schedule_forensics.web.app import SessionState, create_app

#: pages that render from an empty session (no upload needed) — the chrome must be on all of them
_PAGES = ("/", "/settings", "/help", "/trend", "/forecast")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_globe_js_is_served_and_local(client: TestClient) -> None:
    r = client.get("/static/globe.js")
    assert r.status_code == 200
    body = r.text
    assert "canvas" in body and "ai-thinking" in body  # draws the globe; reads the AI-status class
    # PERF: the globe must NOT animate perpetually (a forever-rAF pegged a CPU core on every page
    # and froze input on heavy pages). It spins only while the AI thinks, and pauses when hidden.
    assert 'host.classList.contains("ai-thinking")' in body  # the loop gate
    assert "document.hidden" in body  # paused when the tab is not visible
    assert "visibilitychange" in body  # redraw/resume when the tab returns
    # PERF: even WHILE thinking the spin is throttled (~15 fps) so it never pegs the CPU and
    # freezes a heavy page (the SRA grid) for the whole AI generation (the prior SRA "Ask freezes")
    assert "FRAME_MS" in body and "setTimeout(" in body  # each frame schedules the next on a timer
    # air-gap: the only absolute URL allowed is the SVG XML namespace (never dereferenced)
    externals = [u for u in re.findall(r"https?://[^\s\"'<>]+", body) if "www.w3.org" not in u]
    assert not externals, externals


def test_rotating_globe_on_every_page(client: TestClient) -> None:
    for path in _PAGES:
        page = client.get(path).text
        assert 'class="nasa-globe"' in page, path  # the 3D Earth insignia host
        assert "<canvas" in page, path
        assert 'class="nasa-globe-text">NASA<' in page, path  # the STATIONARY wordmark
        assert "/static/globe.js" in page, path


def test_globe_is_reduced_motion_safe_and_drives_ai_status(client: TestClient) -> None:
    js = client.get("/static/globe.js").text
    assert "prefers-reduced-motion" in js  # the rotation honours the OS pref (still globe)
    css = client.get("/static/base.css").text
    assert ".nasa-globe" in css and ".nasa-globe.ai-thinking" in css  # page-wide AI status light
    ask = client.get("/static/ask.js").text
    # ask.js drives the indicator: toggles .ai-thinking on the globe + shows a live elapsed timer
    assert "ai-thinking" in ask and "startWorking" in ask


def test_cui_marking_top_and_bottom_when_classified(client: TestClient) -> None:
    """CLASSIFIED (default) → the CUI control marking shows top AND bottom of every page."""
    for path in _PAGES:
        page = client.get(path).text
        assert page.count("Controlled Unclassified Information") >= 2, path
        assert page.count('class="cui-banner') >= 2, path
        assert "cui-banner cui" in page and "cui-banner cui bottom" in page, path


def test_cui_marking_reflects_unclassified_mode() -> None:
    """When the operator asserts UNCLASSIFIED, the bar drops the CUI controls marking."""
    state = SessionState(ai_config=AIConfig(classification=Classification.UNCLASSIFIED))
    client = TestClient(create_app(state))
    page = client.get("/").text
    assert "Unclassified • no CUI controls asserted" in page
    assert "cui-banner unclassified" in page
    assert "Controlled Unclassified Information" not in page


def test_dotted_reading_grid_behind_charts(client: TestClient) -> None:
    css = client.get("/static/base.css").text
    assert "--grid-dot" in css
    assert ".chart-host,.chart{background-image:radial-gradient(" in css


def test_nasa_command_banner_header(client: TestClient) -> None:
    css = client.get("/static/base.css").text
    assert "--nasa-blue:#0b3d91" in css
    assert "header{background:linear-gradient(95deg,var(--nasa-blue)" in css
