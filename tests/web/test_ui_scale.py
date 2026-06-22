"""Page-wide rescale control (operator: "rescale the whole page" / change text size).

A header `#uiScale` selector drives `document.documentElement.style.zoom` via the vendored
theme.js (applied in <head> before paint, persisted in localStorage). CSS `zoom` scales text and
the px-based layout together, so it is the reliable whole-page rescale.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

THEME_JS = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "schedule_forensics"
    / "web"
    / "static"
    / "theme.js"
)


def test_header_carries_the_page_scale_control() -> None:
    client = TestClient(create_app(SessionState()))
    page = client.get("/").text
    assert "id=uiScale" in page
    # a sensible range of scale options, default 100%
    assert 'value="1"' in page and 'value="1.5"' in page and "175%" in page


def test_theme_js_applies_and_persists_the_scale() -> None:
    js = THEME_JS.read_text(encoding="utf-8")
    assert "sf-scale" in js  # localStorage key
    assert "style.zoom" in js  # whole-page rescale mechanism
    assert "uiScale" in js  # wires the header control
