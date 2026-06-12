"""The /export endpoints — every view downloads as Excel or Word (M18)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def _is_zip(content: bytes) -> bool:
    return zipfile.is_zipfile(io.BytesIO(content))


def test_analysis_exports_in_both_formats(client: TestClient) -> None:
    _upload(client, "Project5")
    for fmt, media in (("xlsx", XLSX_TYPE), ("docx", DOCX_TYPE)):
        r = client.get(f"/export/{fmt}/analysis/Project5")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(media)
        assert "attachment" in r.headers["content-disposition"]
        assert _is_zip(r.content)


def test_path_export_carries_the_trace_and_rejects_bad_targets(client: TestClient) -> None:
    _upload(client, "Project5")
    r = client.get("/export/xlsx/path/Project5", params={"target": 143})
    assert r.status_code == 200 and _is_zip(r.content)
    assert client.get("/export/xlsx/path/Project5", params={"target": 999999}).status_code == 422


def test_multi_version_exports(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    for view in ("trend", "cei", "forecast", "compare"):
        r = client.get(f"/export/xlsx/{view}")
        assert r.status_code == 200, view
        assert _is_zip(r.content), view


def test_exports_fail_politely_without_data(client: TestClient) -> None:
    assert client.get("/export/xlsx/trend").status_code == 400
    assert client.get("/export/xlsx/analysis/nope").status_code == 404
    assert client.get("/export/gif/trend").status_code == 404  # unknown format


def test_pages_carry_the_export_links(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    assert "/export/xlsx/analysis/" in client.get("/analysis/Project5").text
    assert "/export/xlsx/trend" in client.get("/trend").text
    assert "/export/xlsx/cei" in client.get("/cei").text
    assert "/export/xlsx/forecast" in client.get("/forecast").text
    assert "/export/xlsx/compare" in client.get("/compare").text
    assert "pathExport" in client.get("/path").text
