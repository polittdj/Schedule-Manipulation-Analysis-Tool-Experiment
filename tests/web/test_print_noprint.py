"""ADR-0318 — under print media, every ``data-noprint``-marked control measures hidden.

The content pin (test_accessibility.py) proves the rule exists in the A5 block; this file is
the MEASURED half in real chromium: emulate print media on a contract page carrying the shared
``_shell_tools`` toolbars and the /analysis version chips, and read the computed styles — every
marked element ``display:none``, the panel content (h2) still printable, and flipping back to
screen media restores the controls. Single-theme per operator sub-answer 2 (the print block
forces black-on-white, overriding the theme tokens). Skip posture mirrors the other
vendored-chromium suites.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    import uvicorn

    state = SessionState()
    app = create_app(state)
    with TestClient(app) as c:
        data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    key = next(iter(state.schedules))
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", key
    server.should_exit = True


def test_marked_controls_measure_hidden_under_print_media(served: Any) -> None:
    """Every ``[data-noprint]`` on /analysis computes ``display:none`` under print media —
    and the page still prints its CONTENT (the panel h2 stays visible). Back on screen media
    the same controls measure visible again (the rule is print-scoped, not a screen hide).
    Able to fail: remove the A5 rule and the print-media list reads inline-flex."""
    from playwright.sync_api import sync_playwright

    base, key = served
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**chrome_kwargs())
        tab = browser.new_page(viewport={"width": 1280, "height": 900})
        # never networkidle on this app: heartbeat.js (3s) / sysmon.js (2s) never settle
        tab.goto(base + "/analysis/" + quote(key, safe=""), wait_until="load")
        tab.wait_for_selector(".sf-tools[data-noprint]", timeout=25000)

        marked = tab.evaluate("() => document.querySelectorAll('[data-noprint]').length")
        assert marked >= 5, marked  # the shared toolbars + the version chips are on this page

        tab.emulate_media(media="print")
        displays = tab.evaluate(
            "() => [...document.querySelectorAll('[data-noprint]')]"
            ".map(e => getComputedStyle(e).display)"
        )
        assert displays and all(d == "none" for d in displays), displays
        # the content itself still prints — a panel heading stays renderable
        h2 = tab.evaluate("() => getComputedStyle(document.querySelector('.panel h2')).display")
        assert h2 != "none"

        tab.emulate_media(media="screen")
        back = tab.evaluate(
            "() => [...document.querySelectorAll('.sf-tools[data-noprint]')]"
            ".map(e => getComputedStyle(e).display)"
        )
        assert back and all(d != "none" for d in back), back
        browser.close()
