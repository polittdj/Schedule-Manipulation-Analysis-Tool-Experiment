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
from schedule_forensics.web.help import field_help_payload, field_or_metric_doc, metric_doc


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


# --- the display-column glossary (float bands, trend counts, SRA fields) ---------------------


def test_glossary_fields_define_calc_and_use() -> None:
    """The non-engine display columns (float, status counts, 3-point + SRA fields) are explained
    by a separate glossary fed to the SAME call-out."""
    for key in (
        "total_float",
        "free_float",
        "completed",
        "in_progress",
        "optimistic_duration",
        "pessimistic_duration",
        "risk_ranking_factor",
        "bc_duration",
        "wc_duration",
        "opportunity_accelerate",
        "risk_of_delay",
        "total_sensitivity",
    ):
        doc = field_or_metric_doc(key)
        assert doc is not None and doc.definition and doc.formula and doc.use_case, key


def test_float_band_headers_carry_callouts(client: TestClient) -> None:
    key = re.search(r"/analysis/([^\"\s]+)", client.get("/").text).group(1)
    page = client.get(f"/analysis/{key}").text
    assert "Total float" in page and "Free float" in page
    assert "class=metric-th" in page and "Real-world use:" in page


def test_sra_field_help_is_emitted_for_the_js_tables(client: TestClient) -> None:
    """The SRA SSI run + OAT tables are built in JS, so the page ships a window.SF_FIELD_HELP map
    and sra_ssi.js renders the same hover call-out from it."""
    page = client.get("/sra").text
    assert "window.SF_FIELD_HELP" in page
    assert "opportunity_accelerate" in page and "total_sensitivity" in page
    js = client.get("/static/sra_ssi.js").text
    assert "function helpTh(" in js and "function headerRow(" in js
    assert "SF_FIELD_HELP" in js


def test_field_help_payload_shape() -> None:
    payload = field_help_payload(("bc_duration", "opportunity_accelerate", "not_a_real_key"))
    assert set(payload) == {"bc_duration", "opportunity_accelerate"}  # unknown keys dropped
    assert {"name", "definition", "formula", "use", "indicates"} <= set(payload["bc_duration"])
