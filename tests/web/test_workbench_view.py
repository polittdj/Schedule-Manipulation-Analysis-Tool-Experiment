"""Metric Workbench view tests (ADR-0204) — the Acumen-style library + ribbon + drill + Excel."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_workbench_in_nav_and_needs_a_schedule(client: TestClient) -> None:
    assert 'href="/workbench"' in client.get("/").text
    assert "Load one or more schedules" in client.get("/workbench").text


def test_workbench_page_renders_the_library_and_scaffold(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/workbench").text
    assert "Metric Workbench" in page
    assert "wb-library" in page and "wb-pick" in page
    for fam in ("DCMA-14", "Schedule Quality", "Float"):
        assert fam in page
    assert "id=wbRibbon" in page and "/static/workbench.js" in page
    assert 'href="/export/xlsx/workbench"' in page  # ribbon Excel export


def test_api_workbench_matrix_is_chronological_and_validated(client: TestClient) -> None:
    # load newest first — the workbench must still order oldest -> newest
    _upload(client, "Project5")
    _upload(client, "Project2")
    d = client.get("/api/workbench").json()
    assert [v["label"] for v in d["versions"]] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    assert d["families"] == ["DCMA-14", "Schedule Quality", "Float"]
    assert len(d["metrics"]) == 21
    # High Float on the latest golden is the Acumen-validated 44.44% FAIL with 44 offenders
    latest = d["versions"][-1]["key"]
    cell = d["cells"]["DCMA06"][latest]
    assert round(cell["value"], 2) == 44.44 and cell["status"] == "FAIL" and cell["offenders"] == 44
    # an unscored split is NA, never a fabricated 0 PASS
    assert d["cells"]["DCMA04_SF"][latest]["status"] == "NA"


def test_api_workbench_drill_lists_offenders_with_group_fields(client: TestClient) -> None:
    _upload(client, "Project5")
    key = client.get("/api/workbench").json()["versions"][-1]["key"]
    dr = client.get(f"/api/workbench/drill?metric=DCMA06&file={key}").json()
    assert dr["metric"] == "DCMA06" and dr["metric_name"] == "High Float"
    assert len(dr["rows"]) == 44  # one row per offender
    assert dr["columns"] == ["Name", "Duration (d)", "% complete", "Start", "Finish"]
    # every available project field is offered for group-by / add-column, per row
    assert "WBS" in dr["fields"]
    assert all("fields" in r and "uid" in r for r in dr["rows"])
    assert "WBS" in dr["rows"][0]["fields"]


def test_workbench_drill_unknown_metric_is_422(client: TestClient) -> None:
    _upload(client, "Project5")
    key = client.get("/api/workbench").json()["versions"][-1]["key"]
    assert client.get(f"/api/workbench/drill?metric=NOPE&file={key}").status_code == 422


def test_export_workbench_ribbon_and_drill_to_excel(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    ribbon = client.get("/export/xlsx/workbench")
    assert ribbon.status_code == 200 and ribbon.content
    blob = b"".join(
        zipfile.ZipFile(io.BytesIO(ribbon.content)).read(n)
        for n in zipfile.ZipFile(io.BytesIO(ribbon.content)).namelist()
    )
    assert b"High Float" in blob and b"Project5" in blob and b"BEI" in blob

    key = client.get("/api/workbench").json()["versions"][-1]["key"]
    drill = client.get(f"/export/xlsx/workbench-drill/{key}?metric=DCMA06&cols=WBS")
    assert drill.status_code == 200 and drill.content
    dblob = b"".join(
        zipfile.ZipFile(io.BytesIO(drill.content)).read(n)
        for n in zipfile.ZipFile(io.BytesIO(drill.content)).namelist()
    )
    assert b"WBS" in dblob  # the added column made it into the export
