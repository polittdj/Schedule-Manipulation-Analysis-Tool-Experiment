"""The /forecast design cursor, RENDERED (ADR-0464): drift.js re-homes its own ◀ Prev / label /
Next ▸ / ▶ Auto-play into the masthead strip, a chip clicks the existing Next until the chart shows
that version, the re-homed buttons still drive the chart, and the cursor (active chip + frame pill)
follows whichever control moved it. The two goldens as two versions (P2 then P5 by data date).

Red-first (2026-09-04): the pristine page served no chips (count 0) and no strip.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

GOLDEN = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden" / "project2_5"

_STATE = """() => ({
  frame: document.getElementById('driftChart').getAttribute('data-frame'),
  label: document.getElementById('driftLabel').textContent,
  on: [...document.querySelectorAll('#forecastCursor .cd-chip.on')].map(c => c.dataset.idx),
  pill: document.getElementById('forecastFrame').textContent,
  inStrip: ['prevDrift', 'driftLabel', 'nextDrift', 'driftPlay'].every(
    id => !!document.querySelector('#forecastMaster #' + id)),
  play: document.getElementById('driftPlay').textContent,
  playIsPrimary: document.getElementById('driftPlay').classList.contains('cd-play'),
  svgs: document.querySelectorAll('#driftChart svg').length,
})"""


def _serve(app: Any) -> tuple[Any, str]:
    import uvicorn

    port_sock = socket.socket()
    port_sock.bind(("127.0.0.1", 0))
    port = int(port_sock.getsockname()[1])
    port_sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def served() -> Any:
    app = create_app(SessionState())
    client = TestClient(app)
    for name in ("Project5", "Project2"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        assert (
            client.post(
                "/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}
            ).status_code
            == 200
        )
    server, url = _serve(app)
    yield url
    server.should_exit = True


def _open(url: str) -> tuple[Any, Any, list[str]]:
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(**chrome_kwargs())
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url + "/forecast", wait_until="load")
    page.wait_for_selector("#driftChart svg", timeout=20000)
    return pw, browser, errors


def test_the_stepper_lives_in_the_strip_and_a_chip_moves_the_frame(served: str) -> None:
    pw, browser, errors = _open(served)
    try:
        page = browser.contexts[0].pages[0]
        assert page.locator("#forecastCursor .cd-chip").count() == 2
        s0 = page.evaluate(_STATE)
        assert s0["inStrip"] and s0["playIsPrimary"] and s0["svgs"] == 1
        assert (
            s0["frame"] == "0" and s0["on"] == ["0"] and s0["label"].startswith("1 / 2 — Project2")
        )
        assert s0["pill"].startswith("v1 · Project2.mspdi.xml · DD ")
        page.click('#forecastCursor .cd-chip[data-idx="1"]')
        s1 = page.evaluate(_STATE)
        assert (
            s1["frame"] == "1" and s1["on"] == ["1"] and s1["label"].startswith("2 / 2 — Project5")
        )
        assert s1["pill"].startswith("v2 · Project5.mspdi.xml · DD ")
        page.click('#forecastCursor .cd-chip[data-idx="0"]')
        assert page.evaluate(_STATE)["frame"] == "0"
        assert errors == []
    finally:
        browser.close()
        pw.stop()


def test_the_re_homed_buttons_still_drive_the_chart_and_the_cursor_follows(served: str) -> None:
    pw, browser, errors = _open(served)
    try:
        page = browser.contexts[0].pages[0]
        page.click("#forecastMaster #prevDrift")  # wraps: 1 / 2 -> 2 / 2
        s = page.evaluate(_STATE)
        assert s["frame"] == "1" and s["on"] == ["1"] and s["pill"].startswith("v2 ·")
        page.click("#forecastMaster #nextDrift")  # wraps back
        s = page.evaluate(_STATE)
        assert s["frame"] == "0" and s["on"] == ["0"] and s["pill"].startswith("v1 ·")
        page.click("#forecastMaster #driftPlay")
        assert page.evaluate(_STATE)["play"] == "⏸ Stop"
        page.click("#forecastMaster #driftPlay")
        assert page.evaluate(_STATE)["play"] == "▶ Auto-play"
        assert errors == []
    finally:
        browser.close()
        pw.stop()
