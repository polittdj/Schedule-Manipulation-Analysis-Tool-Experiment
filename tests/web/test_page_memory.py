"""Per-page selection memory + universal Reset view + Gantt parity wiring (ADR-0186)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


# --- the layer is loaded by the shared layout on EVERY page --------------------------


def test_layout_loads_persist_and_taskinfo_everywhere(client: TestClient) -> None:
    _upload(client, "Project5")
    for path in ("/", "/path", "/trend", "/sra", "/evolution", "/groups", "/settings"):
        page = client.get(path).text
        # the layout cache-busts static URLs (?v=...), so match the src prefix only
        assert 'src="/static/persist.js' in page, path
        assert 'src="/static/taskinfo.js' in page, path


# --- the parity controls render on each Gantt page -----------------------------------


def test_path_page_gains_find_and_dates_on_bars(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/path").text
    assert "pathFind" in page and "pathBarDates" in page


def test_sra_grid_gains_showdone_find_and_dates_on_bars(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/sra").text
    assert "ssiShowDone" in page and "ssiFind" in page and "ssiBarDates" in page


def test_evolution_gains_dates_on_bars(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "evoBarDates" in page


def test_driving_path_corridor_gains_find_and_dates_on_bars() -> None:
    # the corridor panel only renders when a real driving corridor exists across versions
    # (which the golden pair doesn't produce), so assert on the template + script wiring
    app_src = (STATIC.parent / "app.py").read_text(encoding="utf-8")
    assert "dpFind" in app_src and "dpBarDates" in app_src
    dp_js = (STATIC / "driving_path.js").read_text(encoding="utf-8")
    assert "dpFind" in dp_js and "dpBarDates" in dp_js and "SFTaskInfo.openFrom" in dp_js


# --- the shared Task Information dialog is the single implementation -----------------


def test_task_info_dialog_lives_in_taskinfo_js_only() -> None:
    taskinfo = (STATIC / "taskinfo.js").read_text(encoding="utf-8")
    assert "SFTaskInfo" in taskinfo and "ti-overlay" in taskinfo and "openFrom" in taskinfo
    app_js = (STATIC / "app.js").read_text(encoding="utf-8")
    # app.js delegates — it must no longer carry its own copy of the dialog markup
    assert "ti-overlay" not in app_js
    assert "SFTaskInfo.open" in app_js
    for consumer in ("path.js", "driving_path.js", "sra_grid.js", "path_evolution.js"):
        assert "SFTaskInfo" in (STATIC / consumer).read_text(encoding="utf-8"), consumer


# --- persist.js contract -------------------------------------------------------------


def test_persist_js_contract() -> None:
    js = (STATIC / "persist.js").read_text(encoding="utf-8")
    # page-scoped keys, /groups excluded from query replay, reset button, restore event
    assert '"sf-qs:" + PATH' in js and '"sf-ui:" + PATH' in js
    assert '"/groups": true' in js
    assert "sfResetView" in js and "sf-restored" in js
    # the nav Target-UID / language forms stay server-side session state
    assert '"/target"' in js and '"/language"' in js


def test_reset_view_is_client_injected_not_server_marked(client: TestClient) -> None:
    # the button is injected by persist.js on every page; the server HTML stays clean of it
    _upload(client, "Project5")
    assert "sfResetView" not in client.get("/").text
