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
    # phase 3: scopeFor honors an explicit stable-scope marker so a legend drawn INSIDE an svg that
    # is rebuilt every animation frame keeps its hidden set on the (surviving) host, not the svg.
    assert "data-series-scope" in body


def test_trend_charts_opt_into_the_toggle_and_tag_their_series() -> None:
    """A generic toggle can only hide a series the chart TAGGED. trend.js's legend() must emit
    data-series-toggle for its multi-series charts, and the multi-series draw must tag each mark
    with data-series — else the legend entries would toggle nothing."""
    trend = (_STATIC / "trend.js").read_text(encoding="utf-8")
    assert 'setAttribute("data-series-toggle"' in trend  # legend entries opt in
    assert "data-series-all" in trend  # the show-all/none control
    assert '"data-series": s.label' in trend  # the line / stacked series marks are tagged
    assert '"data-series": g.label' in trend  # the grouped-bar marks are tagged (phase 2)
    # every multi-series trend chart type opts in: the line chart + the stacked + the grouped bars
    assert "toggle: series.length > 1" in trend
    assert "toggle: segments.length > 1" in trend
    assert "toggle: groups.length > 1" in trend


def test_performance_charts_opt_into_the_toggle_and_mark_a_stable_scope() -> None:
    """performance.js (G1-G4 census/flow/index/burden) draws its legend INSIDE the svg and the
    master stepper rebuilds that svg every frame. It must: tag each series mark with data-series,
    emit data-series-toggle legend groups + a data-series-all control, and mark the stable host
    (monthFrame) with data-series-scope so the hidden set survives the redraw."""
    perf = (_STATIC / "performance.js").read_text(encoding="utf-8")
    assert 'setAttribute("data-series", name)' in perf  # line() and area() paths tag their series
    assert '"data-series": labels[ki]' in perf  # stacked bar segments are tagged
    assert '"data-series-toggle": it.key || it.label' in perf  # legend entries opt in
    assert '"data-series-all": "1"' in perf  # the show-all/none control
    # the stable scope marker on the host (the svg is transient across animation frames)
    assert 'setAttribute("data-series-scope", "1")' in perf


def test_cei_chart_opts_into_the_toggle_and_marks_a_stable_scope() -> None:
    """cei.js is the chart the operator named ("looking at CEI, I want to select ... milestones or
    tasks"). render() rebuilds the svg every auto-play frame, so it marks its host
    (ceiChart) with data-series-scope, tags both the grouped bars and the cumulative curves with
    data-series, and emits clickable legend toggles + an all/none control."""
    cei = (_STATIC / "cei.js").read_text(encoding="utf-8")
    assert 'setAttribute("data-series-scope", "1")' in cei  # the stable host scope
    assert '"data-series": sd[4]' in cei  # grouped bars tagged
    assert '"data-series": pair[2]' in cei  # cumulative (running-totals) curves tagged
    assert '"data-series-toggle": item[0]' in cei  # legend entries opt in
    assert '"data-series-all": "1"' in cei  # the show-all/none control


def test_margin_dashboard_opts_in_with_a_static_color_key_entry() -> None:
    """margin_dashboard.js (phase 3b) is render-once (no stepper) so it needs no data-series-scope
    marker, but its burndown legend MIXES clickable toggles with a static color-key: "Below
    requirement" is a per-month recoloring of the margin bars (a threshold state), not a separate
    series, so it opts OUT via static:true while the real series (margin bars, contingency,
    requirement line, planned depletion, corrective carets, band, erosion trend, zero-margin marker)
    are tagged and togglable."""
    margin = (_STATIC / "margin_dashboard.js").read_text(encoding="utf-8")
    assert '"data-series-toggle": it.key || it.label' in margin  # legend entries opt in
    assert '"data-series-all": "1"' in margin  # the show-all/none control
    assert "if (!it.static)" in margin  # the static color-key path (renders plain, no toggle)
    assert 'label: "Below requirement", static: true' in margin  # the one static entry
    # a representative set of the tagged series marks (bars, lines, markers)
    assert '"data-series": "Effective margin (wd)"' in margin
    assert '"data-series": "Contingency (days)"' in margin
    assert '"data-series": "NASA requirement"' in margin
    assert '"data-series": "Erosion trend"' in margin  # explicit key (label has a dynamic rate)
    # the zero-margin text label is tagged too (via setAttribute, not an attr literal)
    assert 'zt.setAttribute("data-series", "Zero-margin date")' in margin
