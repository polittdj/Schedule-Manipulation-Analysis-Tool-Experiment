"""Responsive / small-screen layout — a real phone/tablet view, CUI-safe (pure CSS, no network).

The tool still runs on the device itself (Law 1: loopback-only, never an off-loopback bind); this
just makes the existing UI usable on a narrow screen — a hamburger-collapsed nav, touch-sized
controls, stacked panels, and wide tables/Gantts that scroll inside their panel.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


def _client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_layout_has_a_collapsible_hamburger_nav() -> None:
    page = _client().get("/").text
    assert 'name=viewport content="width=device-width,initial-scale=1"' in page  # mobile viewport
    assert "id=navToggle class=nav-toggle" in page  # the CSS-only toggle checkbox
    assert "class=nav-burger" in page  # the hamburger label
    assert 'aria-label="Toggle navigation menu"' in page  # accessible name on the toggle


def test_mobile_css_collapses_nav_and_sizes_for_touch() -> None:
    css = _client().get("/static/base.css").text
    # the toggle is hidden on desktop (nav always visible there)
    assert ".nav-toggle,.nav-burger{display:none}" in css
    # the mobile breakpoint reveals the burger and shows the stacked menu only when checked (no JS)
    assert "@media (max-width:760px)" in css
    assert ".nav-toggle:checked ~ nav{display:flex}" in css
    assert "header nav{display:none" in css  # nav hidden behind the burger on small screens
    # touch targets: the burger and controls are at least ~40-44px tall
    assert "min-width:44px" in css and "min-height:44px" in css
    assert "header nav .linkbtn{min-height:40px}" in css  # header controls are touch-sized
    # wide tables / Gantts scroll inside their panel rather than pushing the whole page sideways
    assert ".panel{overflow-x:auto}" in css


def test_desktop_still_shows_the_full_nav() -> None:
    """Outside the breakpoint the nav and its groups render inline as before (no burger)."""
    page = _client().get("/").text
    assert "nav-group" in page and "nav-grp-label" in page  # the full handbook nav is present
