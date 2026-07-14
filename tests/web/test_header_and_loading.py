"""Header report-page names + the file-loading indicator.

Operator: (1) make the report-page names in the header larger / easily identifiable; (2) the moment
files are told to load, show a visual indicator so the tool clearly isn't stuck while it imports.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


def _client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_header_nav_names_are_larger_and_semibold() -> None:
    css = _client().get("/static/base.css").text
    # the report-page names render larger (13px) + semibold so each page is easy to identify
    assert "header nav a{margin-right:14px;color:var(--ink);font-size:13px;font-weight:600}" in css


def test_dashboard_shows_a_loading_indicator_on_import() -> None:
    c = _client()
    home = c.get("/").text
    # the overlay markup is on the dashboard, hidden until an import starts
    assert "id=loadOverlay" in home and "load-overlay" in home
    assert "Loading your project" in home  # the reassuring "not stuck" message
    assert "id=exampleForm" in home  # the example import triggers the same indicator
    # the overlay + spinner are styled, and reduced-motion stops the spin
    css = c.get("/static/base.css").text
    assert ".load-overlay{" in css and "@keyframes sf-spin" in css
    assert ".load-spinner{animation:none}" in css  # prefers-reduced-motion safe
    # home.js reveals the overlay the instant an upload OR the example import is submitted
    js = c.get("/static/home.js").text
    assert "overlay(true)" in js and "loadOverlay" in js  # the overlay is unhidden on import
    assert "exampleForm" in js


def test_loading_overlay_is_reset_when_the_page_is_reshown() -> None:
    """The overlay must never survive a Back-navigation / BFCache restore (operator bug report).

    ``showLoading()`` unhides the overlay and the page then navigates away; nothing else hides it.
    A history traversal that revives the dashboard from the browser's back-forward cache restores
    the DOM exactly as it was left — overlay up, covering the page forever. home.js therefore
    re-hides the overlay (and clears the busy dropzone + any revived file selection) on
    ``pageshow``, which fires on both normal loads (no-op) and every BFCache/history restore.
    """
    js = _client().get("/static/home.js").text
    assert "pageshow" in js  # the restore-aware event, not just DOMContentLoaded
    assert "overlay(false)" in js  # the overlay is actively re-hidden (ov.hidden = !show)
    assert "dz.classList.remove('busy')" in js  # the dropzone busy state is cleared too
