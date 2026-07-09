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
    # the export href forwards the active trace options so it matches the panel (ADR-0174)
    assert "ignore_constraints=" in js and "ignore_leveling=" in js


def _xlsx_rows(content: bytes) -> list[list[str]]:
    """Read the first worksheet of a render_xlsx() workbook as rows of cell strings — std-lib only
    (openpyxl is deliberately NOT a dependency; the tool writes xlsx with zipfile+xml, inline
    strings, native numbers, no shared-string table)."""
    import io
    import xml.etree.ElementTree as ET
    import zipfile

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    root = ET.fromstring(xml)
    for el in root.iter():
        el.tag = el.tag.rsplit("}", 1)[-1]  # strip the spreadsheetml namespace
    rows: list[list[str]] = []
    for row in root.iter("row"):
        cells: list[str] = []
        for c in row.iter("c"):
            t = c.find("is/t")  # inline string
            v = c.find("v")  # native number / value
            cells.append(t.text or "" if t is not None else (v.text or "" if v is not None else ""))
        rows.append(cells)
    return rows


def test_driving_tiers_export_honours_trace_options_matching_the_panel() -> None:
    """ADR-0174: when 'Ignore constraints' is active, the tiers Excel export must be computed on the
    SAME re-solved network the on-screen panel shows — not the stored network. Pins per-UID
    tier+slack parity between the embedded panel rows and the exported rows."""
    import json
    import re

    c = _client()
    target = 155
    # the panel embed (drivingTiersData) with the option active
    page = c.get(f"/driving-path?target={target}&ignore_constraints=1").text
    m = re.search(r"id=drivingTiersData>(.*?)</script>", page, re.S)
    assert m, "panel embed present"
    embed = json.loads(m.group(1).replace("\\u003c", "<"))
    assert embed["ignore_constraints"] == 1
    panel = {row["uid"]: round(float(row["slack"]), 1) for row in embed["rows"]}
    file_label = embed["file"]

    # the export with the SAME option
    r = c.get(f"/export/xlsx/driving-tiers/{file_label}?target={target}&ignore_constraints=1")
    assert r.status_code == 200
    rows = _xlsx_rows(r.content)
    header = rows[0]
    ui, si = header.index("UID"), header.index("Slack (d)")
    exported = {
        int(row[ui]): round(float(row[si]), 1) for row in rows[1:] if row and row[ui].strip()
    }
    # same UID membership AND same slack per UID: export == panel under the trace option
    assert exported == panel
