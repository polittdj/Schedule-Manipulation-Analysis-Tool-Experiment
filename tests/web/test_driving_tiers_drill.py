"""Driving-Path tiers: bold file banner + columnable/filterable/exportable tiers chart (#72).

Operator #72: on the Driving-Path page the driving-tier activities must be shown in one organized
chart the user can add standard/custom columns to, filter by any field, and export to Excel — plus
a bold banner naming the file the path was computed on (the path can differ between files). These
pin the server wiring + the export route + the JS mechanics; the live interaction (table renders,
filter narrows, columns dropdown, Excel link) was verified in Chromium.
"""

from __future__ import annotations

import gzip
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


def _client() -> TestClient:
    hf = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    hfu = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated.mspdi.xml.gz").read_bytes()
    )
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Hard_File.mpp.xml", hf, "text/xml")})
    c.post("/upload", files={"files": ("Hard_File_updated.mpp.xml", hfu, "text/xml")})
    return c


def test_driving_path_shows_bold_file_banner_and_tiers_drill() -> None:
    page = _client().get("/driving-path?target=155").text
    assert "dp-file-banner" in page  # the bold "computed on <file>" banner
    assert "id=drivingTiers" in page and "/static/driving_tiers.js" in page
    assert "drivingTiersData" in page  # embedded tier + slack rows


def test_driving_tiers_export_route_is_wired() -> None:
    c = _client()
    # resolves by the display label, exports a real xlsx, honours extra columns
    r = c.get("/export/xlsx/driving-tiers/Hard_File_updated.mpp.xml?target=155&cols=wbs")
    assert r.status_code == 200
    assert "spreadsheet" in r.headers.get("content-type", "")
    # no extra columns still works
    assert c.get("/export/xlsx/driving-tiers/Hard_File.mpp.xml?target=155").status_code == 200
    # unknown file 404s, an absent target 404s (never 500)
    assert c.get("/export/xlsx/driving-tiers/nope.xml?target=155").status_code == 404
    assert c.get("/export/xlsx/driving-tiers/Hard_File.mpp.xml?target=999999").status_code == 404


def test_driving_tiers_js_has_columns_filter_and_export() -> None:
    js = (STATIC / "driving_tiers.js").read_text(encoding="utf-8")
    assert 'type: "search"' in js  # the filter box
    assert "SFChecklist" in js and "Columns" in js  # the add-columns dropdown
    assert "/export/xlsx/driving-tiers/" in js  # the Excel export
    assert "sf-driving-tiers-cols" in js  # localStorage-persisted column choice
