"""Click-to-highlight on the Path Analysis grid (operator): clicking a task's row/field/bar
highlights the whole row of fields + its Gantt bar; clicking off clears it. The behaviour lives in
the vendored path.js + app.css (CSP-safe); assert the served assets carry the selection logic."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_path_js_has_state_driven_click_selection(client: TestClient) -> None:
    js = client.get("/static/path.js").text
    assert "var selectedUid" in js  # module-level selection state (survives repaints)
    assert "pv-selected" in js and "pv-bar-selected" in js  # row + bar highlight classes
    # a delegated click resolves the clicked task from its row; re-applied on repaint via paintOne
    assert 'closest("tr[data-uid]")' in js
    assert "reskinSelection" in js
    # click-off (no task row) clears the selection
    assert "selectedUid = uid" in js


def test_selection_css_is_tokens_only_and_covers_frozen_columns(client: TestClient) -> None:
    css = client.get("/static/app.css").text
    assert ".path-grid tr.pv-selected td" in css
    # the sticky/frozen data columns need the explicit override or their opaque bg hides the shade
    assert ".path-grid tr.pv-selected td.sf-frozen-col" in css
    assert ".gantt-bar.pv-bar-selected" in css and ".g-ms.pv-bar-selected" in css
    # tokens-only (theme-safe), no hard-coded colors in the selection rules
    for rule in (
        ".path-grid tr.pv-selected td { background: color-mix(in srgb, var(--accent) 16%",
        "outline: 2px solid var(--accent)",
    ):
        assert rule in css
