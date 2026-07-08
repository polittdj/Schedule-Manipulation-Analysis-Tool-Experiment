"""Total-float histogram click-drill + universal visual explainers (operator 2026-07-08)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post(
        "/upload",
        files={
            "files": (
                "Project5.mspdi.xml",
                (GOLDEN / "Project5.mspdi.xml").read_bytes(),
                "text/xml",
            )
        },
    )
    return c


def test_histogram_panel_splits_chart_left_drill_right(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "hist-split" in page and "hist-left" in page and "hist-right" in page
    assert "floatHistDrill" in page
    assert "Click a bar" in page


def test_float_band_export_returns_band_members_with_custom_cols(client: TestClient) -> None:
    # band 1 = total float exactly 0 (the critical set); xlsx magic is PK
    r = client.get("/export/xlsx/float-band/Project5?band=1")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    # extra columns (standard + custom labels) ride the cols= param without error
    r2 = client.get("/export/xlsx/float-band/Project5?band=6&cols=start,finish,wbs")
    assert r2.status_code == 200 and r2.content[:2] == b"PK"
    assert client.get("/export/xlsx/float-band/Project5?band=99").status_code == 422
    assert client.get("/export/xlsx/float-band/Nope?band=1").status_code == 404


def test_histogram_js_carries_the_drill_and_matching_bands() -> None:
    js = (STATIC / "histogram.js").read_text(encoding="utf-8")
    assert "floatHistDrill" in js
    assert "/export/xlsx/float-band/" in js
    assert "data-band" in js  # every bar has a click target
    # the columns dropdown mirrors the Gantt's (standard + payload-discovered custom fields)
    assert "custom_field_labels" in js and "Columns" in js


def test_every_page_loads_the_visual_explainer_catalog(client: TestClient) -> None:
    for url in ("/", "/analysis/Project5", "/trend", "/ribbon", "/integrity"):
        page = client.get(url).text
        assert "/static/vizhints.js" in page, url
    js = (STATIC / "vizhints.js").read_text(encoding="utf-8")
    # the catalog format the operator asked for: what, example, interpretation, PM usefulness
    for token in ("WHAT: ", "EXAMPLE: ", "HOW TO READ: ", "PM USE: "):
        assert token in js
    # spot-check breadth: entries exist for visuals across many pages
    for key in (
        "dcma-14 checks",
        "total-float distribution",
        "s-curve",
        "schedule quality ribbon",
        "risk drivers",
        "resource loading",
        "schedule integrity",
        "mission control",
    ):
        assert key in js, key
