"""Interactive-legend wiring (ADR-0276): the module is loaded app-wide and trend charts opt in.

The behavioural logic is exercised under node (test_legend_toggle_js.py); this pins the integration
seams a TestClient can see without a browser — the script is included on every page, the static file
serves and defines the coordinator, and trend.js actually emits the opt-in legend markup + tags its
series so the generic toggle has something to hide.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_legend_module_is_loaded_app_wide_and_serves(client: TestClient) -> None:
    assert "/static/legend_toggle.js" in client.get("/").text  # included in the base layout
    js = client.get("/static/legend_toggle.js")
    assert js.status_code == 200
    body = js.text
    assert "window.SFLegend" in body
    assert "data-series-toggle" in body and "data-series-all" in body


def test_trend_charts_opt_into_the_toggle_and_tag_their_series() -> None:
    """A generic toggle can only hide a series the chart TAGGED. trend.js's legend() must emit
    data-series-toggle for its multi-series charts, and the multi-series draw must tag each mark
    with data-series — else the legend entries would toggle nothing."""
    trend = (_STATIC / "trend.js").read_text(encoding="utf-8")
    assert 'setAttribute("data-series-toggle"' in trend  # legend entries opt in
    assert "data-series-all" in trend  # the show-all/none control
    assert '"data-series": s.label' in trend  # the series marks are tagged for hiding
    assert "toggle: series.length > 1" in trend  # only multi-series charts enable it
