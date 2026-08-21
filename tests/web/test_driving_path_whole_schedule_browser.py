"""/driving-path's complete-schedule default — RENDERED, with any loaded schedule selectable.

The source pins in ``test_driving_path_whole_schedule.py`` prove the wiring; this module proves
the rendered behavior (markup alone is not evidence — repo standing lesson):

* with no source/target, /driving-path boots into the COMPLETE schedule grid + Gantt of the
  active project's latest version — one row per activity;
* its default column set is IDENTICAL to /path's ("same columns by default", operator
  2026-08-21) — asserted by rendering BOTH pages and comparing header rows, not by retyping
  the list;
* the Schedule select offers every loaded schedule across projects, and switching to the OTHER
  project's file redraws the grid to that schedule's activities;
* clicking a row's UID starts a trace, exactly as on /path.

Skips only when the playwright PACKAGE is absent; browser resolution is
``tests/web/browser_chrome.py``'s decision (ADR-0406/0418).
"""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(n_tasks: int, status: str) -> bytes:
    tasks = "".join(
        f"<Task><UID>{i}</UID><Name>T{i}</Name>"
        f"<Start>2025-01-{5 + i:02d}T08:00:00</Start><Finish>2025-01-{6 + i:02d}T17:00:00</Finish>"
        f"<Duration>PT16H0M0S</Duration></Task>"
        for i in range(1, n_tasks + 1)
    )
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate><Tasks>{tasks}</Tasks></Project>"
    ).encode()


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        files = [
            ("files", ("ArtemisV1.xml", _mspdi(5, "2025-01-15T00:00:00"), "text/xml")),
            ("files", ("ApolloV1.xml", _mspdi(3, "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("ApolloV2.xml", _mspdi(3, "2025-02-10T00:00:00"), "text/xml")),
        ]
        rels = ["Artemis/ArtemisV1.xml", "Apollo/ApolloV1.xml", "Apollo/ApolloV2.xml"]
        meta = json.dumps([{"rel": r, "mtime": 1000 + i} for i, r in enumerate(rels)])
        assert c.post("/upload", files=files, data={"file_meta": meta}).status_code == 200

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_whole_schedule_default_any_loaded_schedule_and_path_column_parity(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1360, "height": 900})

        # /path's default header row is the column-parity ORACLE (never retyped by hand)
        page.goto(served + "/path", wait_until="domcontentloaded")
        page.wait_for_selector("#pathBody tr[data-uid]", timeout=10000)
        path_headers = page.locator(".path-grid thead tr").first.inner_text()

        page.goto(served + "/driving-path", wait_until="domcontentloaded")
        page.wait_for_selector("#pathBody tr[data-uid]", timeout=10000)

        # 1) the COMPLETE schedule of the ACTIVE project's latest (ApolloV2, 3 activities)
        status = page.locator("#pathStatus").inner_text()
        assert "complete schedule (no target selected)" in status, status
        assert page.locator("#pathBody tr[data-uid]").count() == 3
        assert page.locator("#pathSchedule").input_value() == "ApolloV2"

        # 2) same columns by default as "What drives the date" — header equality, both rendered
        dp_headers = page.locator(".path-grid thead tr").first.inner_text()
        assert dp_headers == path_headers, (dp_headers, path_headers)

        # 3) ANY loaded schedule is selectable: switch to the OTHER project's file and the
        #    grid redraws to its 5 activities
        options = page.eval_on_selector_all("#pathSchedule option", "els => els.map(e => e.value)")
        assert set(options) == {"ApolloV1", "ApolloV2", "ArtemisV1"}, options
        page.select_option("#pathSchedule", "ArtemisV1")
        page.wait_for_function(
            "() => document.querySelectorAll('#pathBody tr[data-uid]').length === 5",
            timeout=10000,
        )
        assert "complete schedule" in page.locator("#pathStatus").inner_text()

        # 4) a UID click traces the driving paths to that activity, in the SWITCHED schedule
        page.locator('#pathBody tr[data-uid="5"] .pv-uid').click()
        page.wait_for_function(
            "() => document.getElementById('pathStatus').textContent.includes('to UID 5')",
            timeout=10000,
        )

        # 5) the A→B corridor form is still the page's own control bar, alongside the workspace
        assert page.locator('form[action="/driving-path"]').count() == 1

        browser.close()
