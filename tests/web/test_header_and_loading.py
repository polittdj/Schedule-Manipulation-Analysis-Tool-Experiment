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
    assert "showLoading" in js and "loadOverlay" in js
    assert "exampleForm" in js
