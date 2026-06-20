"""NASA theme chrome — rotating meatball insignia, CUI page-marking bars, dotted chart grid.

Operator request: a NASA-based, professional look on every page — the meatball logo rotating in
the top-right corner, the CUI warning marking required by NASA standards at the top and bottom of
each page, and a light dotted reading grid behind the charts. All assets stay vendored/local
(air-gap, Law 1)."""

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


def test_meatball_svg_is_served_and_local(client: TestClient) -> None:
    r = client.get("/static/nasa-meatball.svg")
    assert r.status_code == 200
    body = r.text
    assert "<svg" in body and "NASA" in body
    # air-gap: the only absolute URL allowed is the SVG XML namespace (never dereferenced)
    externals = [u for u in re.findall(r"https?://[^\s\"'<>]+", body) if "www.w3.org" not in u]
    assert not externals, externals


def test_rotating_logo_on_every_page(client: TestClient) -> None:
    for path in _PAGES:
        page = client.get(path).text
        assert 'class="nasa-logo"' in page, path
        assert "/static/nasa-meatball.svg" in page, path


def test_logo_rotation_animation_defined_and_reduced_motion_safe(client: TestClient) -> None:
    css = client.get("/static/base.css").text
    assert "@keyframes nasa-spin" in css
    assert ".nasa-logo img" in css and "animation:nasa-spin" in css
    # the global reduced-motion block neutralizes every animation (so the spin honors the OS pref)
    assert "@media (prefers-reduced-motion: reduce)" in css


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
