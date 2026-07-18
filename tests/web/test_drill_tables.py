"""Filter/columns/Excel drill tables across the app (ADR-0167).

Operator 2026-07-08: the ribbon metric drill, the Evolution "What-if" reverted-changes table, and
the Integrity finding-citation "(+N more)" expansion must all let the user filter by any field,
add standard/custom columns, and export exactly the selection to Excel — and the What-if runs on a
CHOSEN version pair (not just the latest two). These pin the server wiring + JS mechanics; the live
interactions were verified in Chromium.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


def _client(n_hardfile: int = 3) -> TestClient:
    """Three files loaded as ONE project's version history (a folder upload).

    The hard files and Project5 carry different document Titles, so loose they would be two
    separate Projects — and comparing across Projects is exactly the mixing ADR-0258 outlaws.
    The folder meta declares what this fixture always meant: one project, three versions."""
    hf = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    hfu = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated.mspdi.xml.gz").read_bytes()
    )
    p5 = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    c = TestClient(create_app(SessionState()))
    for name, data in (
        ("Hard_File.mpp.xml", hf),
        ("Hard_File_updated.mpp.xml", hfu),
        ("Project5.mpp.xml", p5),
    ):
        c.post(
            "/upload",
            files={"files": (name, data, "text/xml")},
            data={"file_meta": json.dumps([{"rel": f"History/{name}", "mtime": 1}])},
        )
    return c


def test_evolution_whatif_has_a_two_file_selector_when_more_than_two_loaded() -> None:
    page = _client().get("/evolution").text
    assert "name=cf_a" in page and "name=cf_b" in page
    assert "one pair you pick" in page  # runs on the chosen pair, not lumped across history


def test_whatif_table_and_export_route_are_wired() -> None:
    c = _client()
    # a pair that has reverted activities embeds the interactive table + whatif.js
    # Hard_File (idx0) -> Project5 (idx2) after date ordering has reverted changes
    body = c.get("/evolution?cf_a=0&cf_b=2").text
    assert "whatifTable" in body and "/static/whatif.js" in body
    js = (STATIC / "whatif.js").read_text(encoding="utf-8")
    assert 'type: "search"' in js  # the filter box
    assert "/export/xlsx/whatif" in js  # the Excel export
    # the export route exists and does not 500 for a valid pair
    r = c.get("/export/xlsx/whatif?a=Hard_File.mpp.xml&b=Project5.mpp.xml")
    assert r.status_code == 200


def test_whatif_added_to_critical_path_section_and_export() -> None:
    """Operator 2026-07-09: the What-if panel also lists work ADDED to the critical path between
    the chosen pair, with the engine's per-activity reason attribution, the same columns/filter/
    Excel drill pattern, and its own export route."""
    c = _client()
    body = c.get("/evolution?cf_a=0&cf_b=2").text
    assert "What-if: work added to the critical path" in body
    assert "whatifAddedTable" in body and "whatifAddedData" in body
    # exactly one script include drives both tables
    assert body.count("/static/whatif.js") == 1
    js = (STATIC / "whatif.js").read_text(encoding="utf-8")
    assert "whatifAddedTable" in js and "/export/xlsx/whatif-added" in js
    assert "why_entered" in js
    r = c.get("/export/xlsx/whatif-added?a=Hard_File.mpp.xml&b=Project5.mpp.xml")
    assert r.status_code == 200
    r404 = c.get("/export/xlsx/whatif-added?a=nope&b=Project5.mpp.xml")
    assert r404.status_code == 404


def test_integrity_findings_expose_view_all_citations_drill() -> None:
    c = _client()
    # Hard_File -> Project5 produces findings with > 4 citations -> the "view all" link + drill
    page = c.get("/integrity?a=0&b=2").text
    assert "cite-more" in page and "view all" in page
    assert "findingsDrill" in page and "/static/findings_drill.js" in page


def test_activities_export_resolves_by_label_or_key_and_selects_uids() -> None:
    c = _client()
    # the finding drill exports by the display label (source_file); the route resolves it to the key
    r = c.get("/export/xlsx/activities/Hard_File.mpp.xml?uids=155,187,188&cols=wbs")
    assert r.status_code == 200
    assert "spreadsheet" in r.headers.get("content-type", "")
    # an unknown file 404s, never 500s
    assert c.get("/export/xlsx/activities/nope.mpp.xml?uids=1").status_code == 404


def test_ribbon_and_findings_drills_have_filter_boxes() -> None:
    ribbon = (STATIC / "ribbon_drill.js").read_text(encoding="utf-8")
    assert "filterText" in ribbon and 'type: "search"' in ribbon
    findings = (STATIC / "findings_drill.js").read_text(encoding="utf-8")
    assert "filterText" in findings and "/export/xlsx/activities/" in findings
