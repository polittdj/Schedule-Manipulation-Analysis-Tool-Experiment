"""Regression pins for the Gantt control fixes (operator 2026-07-17).

Three operator-reported problems, fixed and browser-verified (Playwright) at build time; these
are the CI string pins so an edit cannot silently revert them:

  1. Task bars were invisible and the pane would not scroll right — the timeline column collapsed
     under table-layout:fixed because it was never sized. Fixed in the shared colresize.js.
  2. The initial view now lands on the data date, ~1 inch to the right of the frozen data columns.
  3. The "Scale" zoom is a +/- button pair, not a drag slider.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def test_colresize_sizes_the_timeline_column(client: TestClient) -> None:
    js = client.get("/static/colresize.js").text
    # under table-layout:fixed an unsized .g-head collapses -> bars clipped + no horizontal scroll
    assert 'classList.contains("g-head")' in js
    assert "table.style.tableLayout" in js
    assert 'th.style.width = w + "px"' in js  # the timeline column is given an explicit width


def test_analysis_lands_on_the_data_date(client: TestClient) -> None:
    js = client.get("/static/app.js").text
    assert "ONE_INCH_PX" in js
    assert "function scrollToDataDate()" in js  # the initial-load positioning helper
    assert "scrollToDataDate();" in js  # …and it is actually invoked on load


def test_scale_control_is_plus_minus_buttons_not_a_slider(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=zoomOut" in page and "id=zoomIn" in page  # the +/- button pair
    assert "id=vizZoom type=hidden" in page  # the px/day value carrier (read by pxPerDay)
    assert "id=vizZoom type=range" not in page  # the drag slider is gone
    js = client.get("/static/app.js").text
    assert "function stepZoom(" in js
    assert 'getElementById("zoomIn")' in js and 'getElementById("zoomOut")' in js
