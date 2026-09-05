"""/forecast wears the Claude Design "09 Where it lands" layout (ADR-0464), functionality unchanged.

The artboard was recovered by EXECUTING the v2 canvas (npm-packed React/Babel, ``support.js``
patched to local paths, served over loopback because ``file://`` blocks the ``crossorigin``
scripts) and viewed in four themes: a ruler panel full width, a row of method cards, the drift
table beside a "Which to believe" block, and an S-curve panel that is /scurve's chart (not ported).
The page keeps every panel VERBATIM and re-arranges them into that order; the drift stepper's own
◀ Prev / label / Next ▶ / ▶ Auto-play are re-homed by ``drift.js`` into a masthead cursor strip
with one chip per version. The contract counts below were measured identical on the pristine
tree before this layout existed (panels 11 / 9, takes 5 / 4, chips 5 / 4, exports 3 / 2 …).

Red-first (2026-09-04): the pristine page served no strip, no chips, no rows, no reading block.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.chrome import _EXPLAINERS, _e
from web.test_ui_control_effect_census import _FAMILY

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _client(*names: str) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name in names:
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert resp.status_code == 200
    return client


@pytest.fixture(scope="module")
def pair() -> str:
    return _client("Project5", "Project2").get("/forecast").text


@pytest.fixture(scope="module")
def one() -> str:
    return _client("Project5").get("/forecast").text


def test_the_cursor_strip_serves_the_master_slot_and_one_chip_per_version(pair: str) -> None:
    assert pair.count("id=forecastCursor") == 1
    assert pair.count("<span id=forecastMaster class=cd-master></span>") == 1
    assert pair.count("id=forecastFrame") == 1
    chips = re.findall(r'class="cd-chip( on)?" data-idx="(\d+)" title="([^"]+)"', pair)
    assert [(bool(on), idx) for on, idx, _t in chips] == [(True, "0"), (False, "1")]  # oldest first
    assert [t for _on, _idx, t in chips] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    # the strip is the masthead: it precedes the first panel head
    assert pair.index("id=forecastCursor") < pair.index("<div class=panel-head>")


def test_the_design_rows_hold_the_verbatim_panels_in_the_design_order(pair: str) -> None:
    heads = [
        re.sub("<[^>]+>", "", h)
        for h in re.findall(r"<div class=panel-head><h2[^>]*>(.*?)</h2>", pair)
    ]
    assert [h.split(" &mdash;")[0] for h in heads] == [
        "How the forecasts are computed",  # the ruler — WHERE THE FINISH LANDS, full width
        "Finish forecast",  # the methods + inputs …
        "Forecast cards",  # … beside the Carnac cards (the mock's method-card row)
        "Forecast drift across versions",  # the stepper + table …
        "Execution metrics by field group",  # the route's own trailing panel, untouched
    ]
    markers = [
        "id=forecastCursor",
        "How the forecasts are computed",
        '<div class="cd-grid cd-grid-2">',
        "Finish forecast &mdash;",
        "Forecast cards &mdash;",
        '<div class="cd-grid cd-grid-12">',
        "Forecast drift across versions",
        '<section class="cd-block cd-read"><h2>How to read this</h2>',
        "/static/drift.js",
        "/static/panelkit.js",
    ]
    positions = [pair.index(m) for m in markers]
    assert positions == sorted(positions), list(zip(markers, positions, strict=True))
    assert pair.count('<div class="cd-grid cd-grid-2">') == 1
    assert pair.count('<div class="cd-grid cd-grid-12">') == 1


def test_the_reading_block_is_the_pages_own_explainer(pair: str) -> None:
    what, how, decide = _EXPLAINERS["Forecast"]
    for lead, text in (
        ("What it shows.", what),
        ("How to read it.", how),
        ("Why it matters.", decide),
    ):
        assert f"<b>{lead}</b> {_e(text)}" in pair


def test_a_single_version_keeps_the_rows_and_serves_no_cursor(one: str) -> None:
    for absent in ("id=forecastCursor", "cd-chip", "id=forecastMaster", "/static/drift.js"):
        assert absent not in one
    assert one.count('<div class="cd-grid cd-grid-2">') == 1
    assert '<div class="cd-grid cd-grid-12">' not in one  # no drift panel to pair the block with
    assert one.count('<section class="cd-block cd-read"><h2>How to read this</h2>') == 1


def test_the_chips_and_the_strip_carry_no_census_family_word(pair: str) -> None:
    family = re.compile(_FAMILY, re.IGNORECASE)
    strip = pair[
        pair.index("id=forecastCursor") : pair.index("</div>", pair.index("id=forecastCursor"))
    ]
    for attr in re.findall(r'(?:id|class)="?([^"\s>]+)', strip):
        assert not family.search(attr), attr


def test_nothing_the_contract_pins_moved(pair: str, one: str) -> None:
    """Measured on the pristine tree before the layout existed — identical after it."""
    for page, panels, takes, chips, exports, excel, enlarge in (
        (pair, 11, 5, 5, 3, 3, 5),
        (one, 9, 4, 4, 2, 2, 4),
    ):
        assert page.count("<div class=panel") == panels
        assert page.count("class=sf-take") == takes
        assert page.count("class=prov-chip") == chips
        assert page.count('data-export="/export/xlsx/forecast"') == exports
        assert page.count("⤓ EXCEL") == excel and page.count("⛶") == enlarge
        assert "▦ DATA" not in page and page.count("<form") == 5
        assert page.count("/static/panelkit.js") == 1
    for control in (
        "id=prevDrift",
        "id=nextDrift",
        "id=driftPlay",
        "id=driftChart",
        "id=driftLabel",
    ):
        assert pair.count(control) == 1 and control not in one
