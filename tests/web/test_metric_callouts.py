"""Hover call-outs on metric column headers across the report tables (operator request).

Every documented metric in a report header gets a focus/hover call-out from the in-tool dictionary
that defines the metric, shows how it is calculated, and gives a real-world example of how it is
used. The DCMA-14 audit already had this on its check names; this extends it to the Schedule
Quality Ribbon and the Completion-performance tables via the shared ``_metric_help_cell`` helper.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.help import metric_doc


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/example")
    return c


def test_report_column_metrics_have_a_real_world_use() -> None:
    """The metrics that show up as report column headers each carry a concrete 'how it's used'."""
    for mid in (
        "missing_logic",
        "logic_density",
        "critical",
        "negative_float",
        "number_of_lags",
        "merge_hotspot",
        "completed_ahead",
        "completed_behind",
        "mei",
        "epi",
        "duration_ratio_avg",
    ):
        doc = metric_doc(mid)
        assert doc is not None and doc.use_case, mid


def test_ribbon_headers_carry_definition_calculation_and_use(client: TestClient) -> None:
    page = client.get("/ribbon").text
    assert "class=metric-th" in page  # the positioned header cell
    assert 'class="dcma-tip mtip"' in page  # the call-out element (reuses the DCMA tooltip styling)
    assert "How it&#39;s calculated:" in page  # the calculation line
    assert "Real-world use:" in page  # the real-world example line


def test_completion_panel_headers_carry_callouts(client: TestClient) -> None:
    key = re.search(r"/analysis/([^\"\s]+)", client.get("/").text).group(1)
    page = client.get(f"/analysis/{key}").text
    assert "class=metric-th" in page and "Real-world use:" in page


def test_metric_help_styling_is_served(client: TestClient) -> None:
    css = client.get("/static/app.css").text
    assert "th.metric-th" in css  # the header positioning context for the absolute tooltip
