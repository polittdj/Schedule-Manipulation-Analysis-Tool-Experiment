"""The DCMA overview float tip must never outlive its row (operator report 2026-07-27).

The overview tooltip (``.dcma-tip-float``) is ``position:fixed`` on ``<body>`` at z-index
10000 so the chart frame's overflow can't clip it — which also means nothing between it and
the viewport can occlude it, including the fixed nav rail (z-index 110). The operator
screenshotted "DCMA 14 — BEI" stranded over the rail.

How it strands — MEASURED, because the first theory did not survive the browser: the hover
path self-heals in chromium (scrolling under a stationary pointer synthesizes a mousemove, so
``mouseleave`` fires and hides the tip — a mutation with the scroll-guard removed still passed
a hover-scroll probe). The reachable stuck path is FOCUS: the rows are ``tabindex=0``, a
click/tap focuses one and shows the tip instantly, and neither wheel- nor touch-scroll fires
``blur`` — the tip stays pinned to the viewport while the page scrolls under it. (Touch input
is the same path with no synthetic mouse events at all.) A second, degenerate path: a row
measuring 0x0 anchors the tip at the clamps' floor — the viewport's top-left corner, over the
rail.

The executable facts:

* a FOCUS-shown tip hides on the first scroll (this bites: without the document-level
  scroll-hide the tip provably survives, since blur/mouseleave never fire);
* while showing, the tip's box sits clear of the fixed nav rail.

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this module (ADR-0418) (same posture as
``test_axis_titles_visual.py`` — the runtime stays stdlib-only, Law 1)::

    pip install playwright
    python -m pytest tests/web/test_float_tip_scroll.py -q -s
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

TIP_VISIBLE = (
    "() => [...document.querySelectorAll('.dcma-tip-float')].some(n => n.style.display === 'block')"
)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        payload = (GOLDEN / "Project2.mspdi.xml").read_bytes()
        r = c.post("/upload", files={"files": ("Project2.mspdi.xml", payload, "text/xml")})
        assert r.status_code == 200

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_focus_shown_tip_hides_on_scroll_and_stays_off_the_rail(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        # short viewport so the page genuinely scrolls; wide enough for the fixed rail (>=761px)
        page = browser.new_page(viewport={"width": 1280, "height": 620})
        page.goto(served + "/analysis/Project2", wait_until="domcontentloaded")
        page.wait_for_selector(".dcma-ov-row", timeout=10000)

        # FOCUS the last row from the keyboard — the pointer never touches it, so the
        # mouseenter/mouseleave pair that self-heals the hover path is out of the picture,
        # exactly like a touch tap. Focus shows the tip immediately (no hover-intent delay).
        row = page.locator(".dcma-ov-row").last
        row.scroll_into_view_if_needed()
        row.focus()
        page.wait_for_function(TIP_VISIBLE, timeout=4000)

        # While showing: the tip must sit CLEAR of the fixed nav rail (never paint over it).
        clear_of_rail = page.evaluate(
            """() => {
              const tip = [...document.querySelectorAll('.dcma-tip-float')]
                .find(n => n.style.display === 'block');
              const h = document.querySelector('header');
              if (!tip || !h || getComputedStyle(h).position !== 'fixed') return true;
              return tip.getBoundingClientRect().left >= h.getBoundingClientRect().right;
            }"""
        )
        assert clear_of_rail, "float tip painted over the fixed nav rail"

        # FACT: the first scroll hides a focus-shown tip. Without the document-level
        # scroll-hide this fails — blur never fires (focus is untouched by scrolling) and
        # mouseleave can't fire (the pointer was never over the row).
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(150)
        assert not page.evaluate(TIP_VISIBLE), "focus-shown float tip survived a scroll"
        browser.close()
