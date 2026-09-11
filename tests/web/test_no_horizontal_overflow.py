"""UI-03 / R-20 (ADR-0477): no page may scroll SIDEWAYS at rest, in any theme.

The sitewide control census found every page with a hint host scrolling horizontally at a
1440-px viewport — ``document.scrollingElement.scrollWidth`` 1719 on ``/`` and ``/driving-path``,
1734 / 1727 / 1720 (console+daylight / apollo / jarvis) on ``/evolution``, ``/standards`` and
``/scorecards``. Headless hides the scrollbar the operator sees, which is how it survived.

The cause was proven by EXPERIMENT, not by reading the stylesheet: injecting
``[data-sf-hint]::after{content:none}`` alone dropped all five pages to exactly 1440.
``visibility:hidden`` hides a box but keeps it in layout, and the hint bubble is up to 340 px
wide at ``position:absolute; left:0`` on hosts that are frequently right-aligned (the Reset-view
button ending every ``.viz-controls`` row) — a box whose right edge lands past the viewport
counts in the document's scrollable overflow even while invisible.

The remedy collapses only the RESTING box (``hud.css``, ``:not(:hover):not(:focus-visible)``),
so the shown bubble, its fade and its ``--sf-tip-delay`` are untouched. Both facts are pinned
here: the symptom (no overflow) AND the mechanism (the resting box has no width), because a
future rule that reintroduced the width while some other change happened to mask the scroll
would leave this module green over a live defect.

Measured and deliberately LEFT: a bubble anchored near the right edge still widens the document
WHILE it is open. Closing that needs edge-aware placement, not a size reset — its own row.

Red first (2026-09-08, pristine ``hud.css``): scrollWidth 1719 / 1734 / 1727 / 1720 against an
innerWidth of 1440, and the resting bubble measuring 340 px wide with 11 px of padding.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "test_projects"
VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
TARGET_UID = 26
VIEWPORT = {"width": 1440, "height": 900}
THEMES = ("console", "daylight", "apollo", "jarvis")
#: ``/scorecards`` joined the census with ADR-0484: its three-card grid holds four-column tables
#: that scrolled the document sideways in apollo (1527 px) before the tables laid out fixed.
ROUTES = (
    "/",
    f"/driving-path?source=11&target={TARGET_UID}",
    "/evolution",
    "/standards",
    "/scorecards",
)

#: scrollWidth, innerWidth, and how many hint hosts the page carries.
_PROBE = """() => ({
  sw: document.scrollingElement.scrollWidth,
  w: window.innerWidth,
  hints: document.querySelectorAll('[data-sf-hint]').length,
})"""

#: the computed box of the RESTING bubble on the right-most laid-out hint host.
_RESTING_BUBBLE = """() => {
  const n = [...document.querySelectorAll('[data-sf-hint]')];
  let best = null, edge = -1;
  for (const e of n) {
    const r = e.getBoundingClientRect();
    if (r.width && r.height && r.right > edge) { edge = r.right; best = e; }
  }
  if (!best) return null;
  const cs = getComputedStyle(best, '::after');
  return {maxWidth: cs.maxWidth, padLeft: cs.paddingLeft, borderWidth: cs.borderTopWidth};
}"""


def _load(client: TestClient) -> None:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
    meta = json.dumps(
        [
            {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(VERSIONS)
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    client.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False)


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

    app = create_app(SessionState())
    with TestClient(app) as c:
        _load(c)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_no_page_scrolls_sideways_in_any_theme(served: str) -> None:
    from playwright.sync_api import sync_playwright

    seen: list[tuple[str, str, int, int]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport=VIEWPORT)
        try:
            for theme in THEMES:
                for route in ROUTES:
                    page.goto(served + route, wait_until="load")
                    page.evaluate(
                        "t => document.documentElement.setAttribute('data-theme', t)", theme
                    )
                    # the virtual mouse SURVIVES goto(): park it off every hint host, or the
                    # measurement is of a HOVERED page and the resting state is never seen
                    page.mouse.move(0, 0)
                    page.wait_for_timeout(500)
                    r = page.evaluate(_PROBE)
                    seen.append((theme, route, int(r["sw"]), int(r["hints"])))
                    assert r["sw"] <= r["w"] + 1, (
                        f"{route} in {theme}: scrollWidth {r['sw']} > innerWidth {r['w']} "
                        f"({r['hints']} hint hosts)"
                    )
        finally:
            browser.close()
    # the population is part of the claim: a run that found no hint hosts proved nothing
    assert sum(h for _, _, _, h in seen) > 0, seen
    assert len(seen) == len(THEMES) * len(ROUTES)


def test_the_resting_hint_bubble_is_collapsed_not_merely_invisible(served: str) -> None:
    """The MECHANISM, pinned apart from the symptom: 340 px of hidden box is what did it."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport=VIEWPORT)
        try:
            page.goto(served + "/", wait_until="load")
            page.mouse.move(0, 0)
            page.wait_for_timeout(500)
            box = page.evaluate(_RESTING_BUBBLE)
            assert box is not None, "no laid-out hint host on / — the probe measured nothing"
            assert box["maxWidth"] == "0px", box
            assert box["padLeft"] == "0px", box
            assert box["borderWidth"] == "0px", box
        finally:
            browser.close()


def test_the_bubble_still_opens_on_hover(served: str) -> None:
    """The fix must not have bought a clean scrollbar with a dead tooltip. Hovers the FIRST
    hint host in the page chrome (never one inside the Gantt's own scroll container, whose
    reachability is theme-dependent on this page and was so before this change too)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport=VIEWPORT)
        try:
            page.goto(served + "/", wait_until="load")
            page.mouse.move(0, 0)
            page.wait_for_timeout(400)
            page.locator("[data-sf-hint]").first.hover()
            page.wait_for_timeout(2100)  # past --sf-tip-delay (1.5 s) plus the fade
            shown = page.evaluate(
                """() => {
                     const host = document.querySelector('[data-sf-hint]');
                     const cs = getComputedStyle(host, '::after');
                     return {vis: cs.visibility, op: cs.opacity, w: parseFloat(cs.width)};
                }"""
            )
            assert shown["vis"] == "visible" and shown["op"] == "1", shown
            assert shown["w"] > 100, shown
        finally:
            browser.close()
