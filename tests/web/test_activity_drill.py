"""Shared activity drill (issue #331 follow-up): click a scorecard line or a churn-bar segment to
list the activities behind it, add columns, and export to Excel.

Pins the wiring — the generic `/api/activities/drill` endpoint + export, the `sf-drill` hooks the
scorecard rows / evolution + trend bar segments emit, and the regression guard that `_status_stack`
without a `drill` argument is unchanged (so the ~20 other callers are untouched).
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, _status_stack, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File_updated2", "Hard_File_updated3"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", xml, "text/xml")})
    return c


def _first_drill(html: str) -> tuple[str, str]:
    """The (uids, file) of the first sf-drill trigger on a page."""
    import re

    m = re.search(r'data-uids="([\d,]+)"[^>]*data-file="([^"]+)"', html)
    assert m, "no sf-drill trigger found"
    return m.group(1), m.group(2)


def test_scorecard_rows_emit_drill_hooks(client: TestClient) -> None:
    html = client.get("/scorecards").text
    assert "sf-drill" in html and "/static/drilldown.js" in html
    uids, _file = _first_drill(html)
    assert uids  # a failing scorecard check cites its offenders


def test_evolution_and_trend_bars_emit_drill_hooks(client: TestClient) -> None:
    evo = client.get("/evolution").text
    assert "stack-seg sf-drill" in evo and "/static/drilldown.js" in evo
    trend = client.get("/trend").text
    assert "stack-seg sf-drill" in trend and "Where the work stands" in trend


def test_activities_drill_api_returns_rows_and_fields(client: TestClient) -> None:
    uids, file = _first_drill(client.get("/scorecards").text)
    r = client.get("/api/activities/drill", params={"file": file, "uids": uids, "title": "T"})
    assert r.status_code == 200
    body = r.json()
    assert body["columns"] == ["Name", "Duration (d)", "% complete", "Start", "Finish"]
    assert body["rows"] and body["fields"]
    # every returned row carries a uid + a fields map (so add-column works client-side)
    for row in body["rows"]:
        assert "uid" in row and "fields" in row


def test_activities_drill_export(client: TestClient) -> None:
    uids, file = _first_drill(client.get("/scorecards").text)
    fields = client.get("/api/activities/drill", params={"file": file, "uids": uids}).json()[
        "fields"
    ]
    for fmt in ("xlsx", "docx"):
        r = client.get(
            f"/export/{fmt}/activities-drill",
            params={"file": file, "uids": uids, "title": "T", "cols": fields[0]},
        )
        assert r.status_code == 200 and len(r.content) > 0
    assert client.get("/export/csv/activities-drill").status_code == 404


def test_status_stack_without_drill_is_unchanged() -> None:
    """Regression guard: the default (no drill) render carries no sf-drill hook — the ~20 existing
    callers of _status_stack are untouched."""
    segs = [("A", 3, "--ok"), ("B", 1, "--bad")]
    plain = _status_stack("T", "d", segs, "foot")
    assert "sf-drill" not in plain and "data-uids" not in plain
    drilled = _status_stack("T", "d", segs, "foot", drill=[((1, 2, 3), "f.xml"), ((), "f.xml")])
    # only the segment with a non-empty UID set becomes clickable
    assert 'class="stack-seg sf-drill"' in drilled
    assert drilled.count("data-uids") == 2  # segment + legend key of the drillable segment


def test_reset_button_is_reinjected_into_toolbars() -> None:
    js = (STATIC / "persist.js").read_text(encoding="utf-8")
    assert "sf-reset-inline" in js and ".viz-controls" in js and "resetPage" in js


def test_drilldown_js_is_air_gap_safe() -> None:
    js = (STATIC / "drilldown.js").read_text(encoding="utf-8")
    assert "/api/activities/drill" in js
    assert "http://" not in js and "https://" not in js


def test_nav_rail_selects_can_shrink() -> None:
    """The rail-overflow fix: the console/apollo/jarvis nav-controls selects get min-width:0 so they
    fit the fixed-width rail instead of bleeding off the right edge."""
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert ".nav-controls select{max-width:100%;min-width:0;width:100%" in css
