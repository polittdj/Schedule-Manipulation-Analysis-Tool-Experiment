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
    assert "/static/home.js" in client.get("/").text  # dropzone logic is the served static file
    home_js = client.get("/static/home.js").text
    assert "form.submit()" in home_js
    assert "fetch('/upload'" not in home_js and 'fetch("/upload"' not in home_js


def test_drag_drop_is_handled_window_wide_so_the_browser_does_not_open_the_file(
    client: TestClient,
) -> None:
    """Operator: dragging a file into the tool must open it in the tool, not make the browser
    navigate to the raw file. That requires preventing the default drag/drop on the WINDOW (not just
    the small zone) and feeding the dropped files into the upload form."""
    home_js = client.get("/static/home.js").text
    assert "window.addEventListener('dragover'" in home_js  # allow the drop anywhere
    assert "window.addEventListener('drop'" in home_js  # stop the browser opening the file
    assert "ev.preventDefault()" in home_js
    assert "input.files = files" in home_js  # the dropped files go onto the real form input


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


def test_dashboard_health_cards_wire_and_api(client: TestClient) -> None:
    """The Dashboard's per-schedule health cards (status mix, critical %, finish vs baseline,
    DCMA ribbon) load async from /api/dashboard and link into the report."""
    assert client.get("/api/dashboard").json()["cards"] == []  # nothing loaded yet
    client.post("/example")  # one schedule loaded
    home = client.get("/").text
    assert "Schedule health" in home
    assert "id=dashboardHealth" in home and "/static/dashboard.js" in home
    cards = client.get("/api/dashboard").json()["cards"]
    assert len(cards) == 1
    c = cards[0]
    assert c["solvable"] is True
    for key in (
        "name",
        "key",
        "activities",
        "status_mix",
        "percent_complete",
        "critical_count",
        "critical_pct",
        "cpm_finish",
        "dcma",
    ):
        assert key in c, key
    assert {"complete", "in_progress", "planned"} <= set(c["status_mix"])
    assert c["dcma"] and all({"id", "name", "status"} <= set(d) for d in c["dcma"])
    assert all(d["status"] in ("PASS", "FAIL", "NA") for d in c["dcma"])


GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _upload_golden(client: TestClient, name: str) -> None:
    data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_schedules_listed_earliest_to_latest_data_date_everywhere(client: TestClient) -> None:
    """Every tab/visual must list versions oldest data date first, regardless of upload order.
    Project2's data date (May-26) precedes Project5's (Aug-26); uploading them in REVERSE must
    still surface Project2 before Project5 in the home 'Loaded schedules' table and the
    Dashboard health-card API."""
    _upload_golden(client, "Project5")  # later data date, uploaded FIRST
    _upload_golden(client, "Project2")  # earlier data date, uploaded SECOND

    # home 'Loaded schedules' table (server-rendered) lists the earlier version first
    home = client.get("/").text
    assert home.index("Project2.mspdi.xml") < home.index("Project5.mspdi.xml")

    # Dashboard health cards come back in ascending data-date order, not upload order
    cards = client.get("/api/dashboard").json()["cards"]
    dates = [c["data_date"] for c in cards]
    assert dates == sorted(dates), dates
    assert cards[0]["data_date"] < cards[1]["data_date"]


def test_download_missing_is_404(client: TestClient) -> None:
    assert client.get("/download/nope.json").status_code == 404


def test_download_filename_strips_header_injection_chars() -> None:
    from schedule_forensics.web.app import _safe_filename

    assert _safe_filename('a"b\\c\r\nd.json') == "abcd.json"  # quotes/backslash/CRLF removed


def test_favicon_is_served_and_linked(client: TestClient) -> None:
    # the unique app icon doubles as the browser-tab favicon (same bytes as the
    # desktop .ico — packaging tests assert the sync); strictly a local asset
    assert '<link rel=icon href="/static/favicon.ico">' in client.get("/").text
    resp = client.get("/static/favicon.ico")
    assert resp.status_code == 200
    assert resp.content[:4] == b"\x00\x00\x01\x00"  # ICO magic
