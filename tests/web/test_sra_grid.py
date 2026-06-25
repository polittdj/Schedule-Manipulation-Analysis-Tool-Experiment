"""SSI editable schedule grid + JSON Save/Load + Excel/Word export (ADR-0123).

The /sra page hosts an inline-editable grid (Risk Ranking Factor / Best-Worst days / focus radio per
task) fed by /api/sra/grid and batch-saved to /sra/grid; the SSI setup round-trips through
/sra/ssi/save + /sra/ssi/load; and /export/{fmt}/sra emits the six-table hand-out. These pin the
plumbing — the engine parity lives in tests/engine/test_sra_ssi.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _editable_uids(client: TestClient, n: int = 2) -> list[int]:
    rows = client.get("/api/sra/grid").json()["rows"]
    return [r["unique_id"] for r in rows if r["editable"]][:n]


def test_grid_panel_and_scripts_render(client: TestClient) -> None:
    page = client.get("/sra").text
    assert "Editable schedule grid" in page
    for token in (
        "id=ssiGrid",
        "id=ssiGridSave",
        "id=ssiGridReload",
        "id=ssiGridZoom",
        "/static/gantt.js",
        "/static/sra_grid.js",
        "/sra/ssi/save",
        "/export/xlsx/sra",
        "/export/docx/sra",
    ):
        assert token in page, token


def test_grid_feed_shape(client: TestClient) -> None:
    j = client.get("/api/sra/grid").json()
    assert j["rows"]
    keys = {
        "unique_id",
        "name",
        "outline_level",
        "start",
        "finish",
        "remaining_days",
        "factor",
        "bc_days",
        "wc_days",
        "has_risk",
        "is_focus",
        "editable",
        "is_summary",
    }
    assert keys <= set(j["rows"][0])
    # summary rows are not editable; leaf rows are
    assert any(r["editable"] for r in j["rows"])
    assert all(not r["editable"] for r in j["rows"] if r["is_summary"])


def test_grid_save_factor_autofills_bcwc_and_sets_focus(client: TestClient) -> None:
    uid = _editable_uids(client, 1)[0]
    r = client.post(
        "/sra/grid", data={"deltas": json.dumps([{"uid": uid, "factor": 5, "focus": True}])}
    )
    assert r.status_code == 200 and r.json()["saved"] == 1
    row = next(x for x in client.get("/api/sra/grid").json()["rows"] if x["unique_id"] == uid)
    assert row["factor"] == 5
    # factor 5 = subtract 10 / add 50 -> BC < remaining < WC (auto-filled from the factor table)
    assert row["bc_days"] is not None and row["wc_days"] is not None
    assert row["bc_days"] < row["remaining_days"] < row["wc_days"]
    assert row["is_focus"] is True
    # the SSI run now targets that focus event
    assert client.get("/api/sra/ssi?iterations=200").json()["target_uid"] == uid


def test_grid_save_manual_bcwc_overrides(client: TestClient) -> None:
    uid = _editable_uids(client, 1)[0]
    client.post(
        "/sra/grid", data={"deltas": json.dumps([{"uid": uid, "bc_days": 2.0, "wc_days": 11.0}])}
    )
    row = next(x for x in client.get("/api/sra/grid").json()["rows"] if x["unique_id"] == uid)
    assert row["bc_days"] == 2.0 and row["wc_days"] == 11.0


def test_grid_save_ignores_unknown_and_summary_uids(client: TestClient) -> None:
    summary = next(
        (r["unique_id"] for r in client.get("/api/sra/grid").json()["rows"] if r["is_summary"]),
        None,
    )
    deltas = [{"uid": 999999, "factor": 3}]
    if summary is not None:
        deltas.append({"uid": summary, "factor": 3})
    r = client.post("/sra/grid", data={"deltas": json.dumps(deltas)})
    assert r.status_code == 200 and r.json()["saved"] == 0


def test_setup_save_load_round_trip(client: TestClient) -> None:
    uids = _editable_uids(client, 2)
    client.post(
        "/sra/grid",
        data={"deltas": json.dumps([{"uid": uids[0], "factor": 4, "focus": True}])},
    )
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "Permit",
            "prob": "79",
            "impact_days": "100",
            "affected": str(uids[1]),
            "consequence": "",
        },
    )
    saved = client.get("/sra/ssi/save")
    assert saved.status_code == 200
    blob = json.loads(saved.content)
    assert blob["setup_version"] == 1 and blob["focus_uid"] == uids[0]
    assert blob["factors"][str(uids[0])] == 4 and len(blob["risks"]) == 1

    # wipe, then restore from the saved JSON
    fresh = TestClient(create_app(SessionState()))
    fresh.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    fresh.post("/sra/ssi/load", files={"setup": ("setup.json", saved.content, "application/json")})
    j = fresh.get("/api/sra/ssi?iterations=200").json()
    assert j["target_uid"] == uids[0]
    assert len(j["risks"]) == 1 and j["risks"][0]["name"] == "Permit"
    row = next(x for x in fresh.get("/api/sra/grid").json()["rows"] if x["unique_id"] == uids[0])
    assert row["factor"] == 4


def test_setup_load_drops_uids_unknown_to_the_active_schedule(client: TestClient) -> None:
    payload = {
        "setup_version": 1,
        "focus_uid": 999999,
        "factors": {"999999": 5},
        "risks": [
            {"id": "R1", "name": "x", "probability": 0.5, "impact_days": 5, "affected": [999999]}
        ],
    }
    client.post(
        "/sra/ssi/load",
        files={"setup": ("s.json", json.dumps(payload).encode(), "application/json")},
    )
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["target_uid"] is None  # unknown focus dropped
    assert j["risks"] == []  # risk on an unknown uid dropped


@pytest.mark.parametrize("fmt", ["xlsx", "docx"])
def test_export_emits_office_zip(client: TestClient, fmt: str) -> None:
    uid = _editable_uids(client, 1)[0]
    client.post(
        "/sra/grid", data={"deltas": json.dumps([{"uid": uid, "factor": 3, "focus": True}])}
    )
    r = client.get(f"/export/{fmt}/sra")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"  # an OOXML zip
    assert len(r.content) > 1000


def test_word_export_is_a_comprehensive_report_with_vector_charts(client: TestClient) -> None:
    """Operator: a full MS Word SRA report — PM summary then per-section detail with embedded
    graphics. The .docx is a narrative document (not the plain table dump), it carries the section
    headings + native vector drawings + the shaded 5x5 matrices, and it is byte-deterministic."""
    import io
    import xml.etree.ElementTree as ET
    import zipfile

    uid = _editable_uids(client, 1)[0]
    client.post(
        "/sra/grid", data={"deltas": json.dumps([{"uid": uid, "factor": 5, "focus": True}])}
    )
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "Permit",
            "prob": "79",
            "impact_days": "100",
            "affected": str(uid),
            "consequence": "",
        },
    )
    r = client.get("/export/docx/sra")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert zf.testzip() is None
    doc = zf.read("word/document.xml").decode()
    ET.fromstring(doc)  # well-formed
    for section in (
        "Executive summary",
        "Focus-finish results",
        "Duration sensitivity",
        "Risk / Opportunity register",
        "Risk Assessment Matrix",
        "Methodology",
    ):
        assert section in doc, section
    assert "<w:drawing>" in doc and "<w:shd " in doc  # a vector chart + a shaded matrix
    assert client.get("/export/docx/sra").content == r.content  # deterministic


@pytest.mark.parametrize("fmt", ["xlsx", "docx"])
def test_risk_registry_is_downloadable(client: TestClient, fmt: str) -> None:
    uid = _editable_uids(client, 1)[0]
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "Permit",
            "prob": "79",
            "impact_days": "100",
            "affected": str(uid),
            "consequence": "",
        },
    )
    r = client.get(f"/export/{fmt}/sra-registry")
    assert r.status_code == 200 and r.content[:2] == b"PK" and len(r.content) > 1000
    # the buttons are on the page
    page = client.get("/sra").text
    assert "/export/xlsx/sra-registry" in page and "Download SRA report (Word)" in page


def test_grid_and_export_need_a_schedule() -> None:
    c = TestClient(create_app(SessionState()))
    assert c.get("/api/sra/grid").status_code == 400
    assert c.get("/export/xlsx/sra").status_code == 400
    assert c.get("/export/docx/sra-registry").status_code == 400


def test_grid_supports_excel_column_paste_fill(client: TestClient) -> None:
    """Operator: copy a whole Risk Ranking Factor column from Excel / MS Project and paste it onto
    one cell to fill the column down across every task in one go (no per-cell entry)."""
    js = client.get("/static/sra_grid.js").text
    assert '"paste"' in js  # a paste handler on the grid
    assert 'getData("text")' in js  # reads the clipboard text
    assert 'var COLS = ["factor", "bc_days", "wc_days"]' in js  # fills down by column
    assert 'split("\\t")' in js  # tab-separated columns (an Excel block paste)
    # the panel tells the operator they can paste a column
    page = client.get("/sra").text
    assert "Paste from Excel" in page


def test_sra_grid_js_is_air_gapped(client: TestClient) -> None:
    js = client.get("/static/sra_grid.js").text
    urls = [u for u in re.findall(r"https?://[^\s\"')]+", js) if "www.w3.org" not in u]
    assert not urls, f"external URL in sra_grid.js: {urls}"
    assert not re.findall(r"""["'(]//[^\s"'<>)]+""", js)
