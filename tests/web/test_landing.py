"""Landing-page tests (M-UI) — professional open/import dashboard: example, .json, download."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_landing_is_a_professional_open_import_dashboard(client: TestClient) -> None:
    page = client.get("/").text
    assert "id=dropzone" in page  # drag-and-drop zone
    assert ">Load example<" in page  # one-click example
    assert (
        'accept=".json,.xml,.mspdi,.xer,.mpp,.mpt"' in page
    )  # Open .json AND Import .xml/.xer/.mpp
    assert ".mpp" in page and ".json" in page and ".xer" in page  # supported formats shown


def test_dropzone_uses_native_form_submit_not_fetch(client: TestClient) -> None:
    # W2 regression guard: a fetch() POST auto-follows the 303 on a hidden request, swallowing
    # both the single-file jump to /analysis/... and the one-shot import flash. The dropzone must
    # submit the real <form> so the browser follows the redirect itself.
    page = client.get("/").text
    assert "form.submit()" in page
    assert "fetch('/upload'" not in page and 'fetch("/upload"' not in page


def test_load_example_opens_a_full_report(client: TestClient) -> None:
    redirect = client.post("/example", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"].startswith("/analysis/")
    report = client.post("/example").text  # follows the redirect to the report
    assert "DCMA-14 audit" in report and "AI narrative" in report and "id=viz" in report
    assert client.get("/healthz").json()["loaded"] >= 1


def test_open_json_file(client: TestClient) -> None:
    data = EXAMPLE.read_bytes()
    assert (
        client.post("/upload", files={"files": ("plan.json", data, "application/json")}).status_code
        == 200
    )
    assert client.get("/healthz").json()["loaded"] == 1
    # the loaded schedule is listed with an Open report + Save .json action
    home = client.get("/").text
    assert "Open report" in home and "Save .json" in home


def test_save_json_round_trips(client: TestClient) -> None:
    client.post("/example")
    key = "House Build (example)"
    resp = client.get("/download/" + urllib.parse.quote(key) + ".json")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    body = resp.text
    assert body.strip().startswith("{") and '"tasks"' in body
    # the downloaded file re-imports
    reopened = client.post(
        "/upload", files={"files": ("again.json", body.encode(), "application/json")}
    )
    assert reopened.status_code == 200


def test_download_missing_is_404(client: TestClient) -> None:
    assert client.get("/download/nope.json").status_code == 404


def test_download_filename_strips_header_injection_chars() -> None:
    from schedule_forensics.web.app import _safe_filename

    assert _safe_filename('a"b\\c\r\nd.json') == "abcd.json"  # quotes/backslash/CRLF removed
