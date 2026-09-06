"""JS-03 (WP6b, ADR-0467): typing in a drill panel's text filter keeps the caret in the filter.

Three drill panels (``ribbon_drill.js``, ``findings_drill.js``, ``driving_tiers.js``) rebuilt
their whole card — the filter input included — on every ``input`` event, so the element under
the caret was replaced by its own keystroke: the second character went to ``<body>``. Measured in
Chromium 2026-09-06: after typing ``ab`` the filter read ``a`` and ``document.activeElement`` was
BODY, on /ribbon and /integrity alike. The panels now hand focus and the caret back to the new
input after a rebuild the filter itself caused.

Red-first (2026-09-06): value ``a``, focused False, on both drills.
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

_STATE = """(sel) => { const i = document.querySelector(sel);
  return { value: i ? i.value : null, focused: document.activeElement === i,
           active: document.activeElement.tagName }; }"""


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
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert resp.status_code == 200
    server, url = _serve(app)
    yield url
    server.should_exit = True


@pytest.fixture(scope="module")
def served_hard() -> Any:
    """The Hard_File pair, whose target 155 renders the driving-tiers table on /driving-path."""
    import gzip

    app = create_app(SessionState())
    client = TestClient(app)
    for name in ("Hard_File", "Hard_File_updated"):
        packed = (GOLDEN.parent / "fuse_hardfile" / f"{name}.mspdi.xml.gz").read_bytes()
        data = gzip.decompress(packed)
        resp = client.post("/upload", files={"files": (f"{name}.mpp.xml", data, "text/xml")})
        assert resp.status_code == 200
    server, url = _serve(app)
    yield url
    server.should_exit = True


def _type_two(page: Any, selector: str) -> dict[str, Any]:
    page.click(selector)
    page.keyboard.type("ab", delay=60)
    state: dict[str, Any] = page.evaluate(_STATE, selector)
    return state


def _open(p: Any, url: str, path: str) -> tuple[Any, Any, list[str]]:
    browser = p.chromium.launch(**chrome_kwargs())
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url + path, wait_until="load")
    return browser, page, errors


def test_the_ribbon_drill_filter_keeps_focus_across_keystrokes(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served, "/ribbon")
        page.wait_for_selector(".rib-cell[data-metric]", timeout=15_000)
        cells = page.evaluate(
            "() => [...document.querySelectorAll('.rib-cell[data-metric]')]"
            ".map(c => [c.dataset.metric, c.textContent.trim()])"
        )
        metric = next(m for m, text in cells if text not in ("0", "—", ""))
        page.click(f".rib-cell[data-metric='{metric}']")
        page.wait_for_selector("#ribbonDrill input[type=search]", timeout=10_000)
        state = _type_two(page, "#ribbonDrill input[type=search]")
        browser.close()
    assert state["value"] == "ab" and state["focused"], state
    assert errors == []


def test_the_driving_tiers_filter_keeps_focus_across_keystrokes(served_hard: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served_hard, "/driving-path?target=155")
        page.wait_for_selector("#drivingTiers input[type=search]", timeout=15_000)
        state = _type_two(page, "#drivingTiers input[type=search]")
        browser.close()
    assert state["value"] == "ab" and state["focused"], state
    assert errors == []


def test_the_findings_drill_filter_keeps_focus_across_keystrokes(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served, "/integrity")
        page.wait_for_selector("a.cite-more[data-finding]", timeout=15_000)
        page.locator("a.cite-more[data-finding]").first.click()
        page.wait_for_selector("#findingsDrill input[type=search]", timeout=10_000)
        state = _type_two(page, "#findingsDrill input[type=search]")
        browser.close()
    assert state["value"] == "ab" and state["focused"], state
    assert errors == []
