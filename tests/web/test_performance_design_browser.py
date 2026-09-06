"""The /performance design cursor, RENDERED (ADR-0468): performance.js re-homes its own ◀ Prev /
caption / Next ▶ / ▶ Play into the masthead strip, a chip calls the same step the buttons call,
every step publishes its frame as ``data-frame`` on ``#perfGrid`` and syncs the chips + pill in the
same task (ADR-0466), and the re-homed buttons still drive the wall. The Hard_File pair as two
files (the page opens on the NEWEST, so the last chip is on).

Red-first (2026-09-06): the pristine page served no chips (count 0), no strip, no data-frame.
"""

from __future__ import annotations

import gzip
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

GOLDEN = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden" / "fuse_hardfile"

_STATE = """() => ({
  frame: document.getElementById('perfGrid').getAttribute('data-frame'),
  caption: document.getElementById('perfStep').textContent,
  on: [...document.querySelectorAll('#performanceCursor .cd-chip.on')].map(c => c.dataset.idx),
  pill: document.getElementById('performanceFrame').textContent,
  inStrip: ['perfPrev', 'perfStep', 'perfNext', 'perfPlay'].every(
    id => !!document.querySelector('#performanceMaster #' + id)),
  play: document.getElementById('perfPlay').textContent,
  playIsPrimary: document.getElementById('perfPlay').classList.contains('cd-play'),
  exports: [...new Set([...document.querySelectorAll('#perfGrid [data-export]')]
    .map(t => t.getAttribute('data-export')))],
  svgs: document.querySelectorAll('#g1Census svg').length,
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
    for name in ("Hard_File", "Hard_File_updated3"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        resp = client.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
        assert resp.status_code == 200
    server, url = _serve(app)
    yield url
    server.should_exit = True


def _open(p: Any, url: str) -> tuple[Any, Any, list[str]]:
    browser = p.chromium.launch(**chrome_kwargs())
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url + "/performance", wait_until="load")
    page.wait_for_function(  # a FUNCTION string (ADR-0466): an expression re-evals under CSP
        "() => document.getElementById('perfGrid').hasAttribute('data-frame')"
        " && document.querySelectorAll('#g1Census svg').length > 0",
        timeout=30_000,
    )
    return browser, page, errors


def test_the_stepper_lives_in_the_strip_and_a_chip_moves_the_wall(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served)
        assert page.locator("#performanceCursor .cd-chip").count() == 2
        s0 = page.evaluate(_STATE)
        assert s0["inStrip"] and s0["playIsPrimary"] and s0["svgs"] == 1
        assert s0["frame"] == "1" and s0["on"] == ["1"]  # the page opens on the newest file
        assert s0["caption"].startswith("file 2 of 2 — Hard_File_updated3")
        assert s0["pill"].startswith("v2 · Hard_File_updated3.mpp.xml · DD ")
        page.click('#performanceCursor .cd-chip[data-idx="0"]')
        s1 = page.evaluate(_STATE)  # the same task published the frame and synced the chips
        assert s1["frame"] == "0" and s1["on"] == ["0"]
        assert s1["caption"].startswith("file 1 of 2 — Hard_File")
        assert s1["pill"].startswith("v1 · Hard_File.mpp.xml · DD ")
        assert s1["exports"] == ["/export/xlsx/performance?file=Hard_File.mpp.xml"]
        page.click('#performanceCursor .cd-chip[data-idx="1"]')
        assert page.evaluate(_STATE)["frame"] == "1"
        browser.close()
    assert errors == []


def test_the_re_homed_buttons_still_drive_the_wall_and_the_cursor_follows(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served)
        page.click("#performanceMaster #perfNext")  # wraps: file 2 of 2 -> file 1 of 2
        s = page.evaluate(_STATE)
        assert s["frame"] == "0" and s["on"] == ["0"] and s["pill"].startswith("v1 ·")
        page.click("#performanceMaster #perfPrev")  # wraps back
        s = page.evaluate(_STATE)
        assert s["frame"] == "1" and s["on"] == ["1"] and s["pill"].startswith("v2 ·")
        page.click("#performanceMaster #perfPlay")  # one beat: file 1, then the chain runs
        s = page.evaluate(_STATE)
        assert s["frame"] == "0" and s["on"] == ["0"]
        assert s["play"] in ("⏸ Stop", "▶ Play")  # reduced-motion hosts stop after one frame
        page.click("#performanceMaster #perfPlay") if s["play"] == "⏸ Stop" else None
        assert page.evaluate(_STATE)["play"] == "▶ Play"
        browser.close()
    assert errors == []
