"""/portfolio panel-contract behavior in a REAL browser (Mission Ops rank 7).

Markup alone is not evidence (the round-4 latent-gap lesson): panelkit.js is a PER-PAGE include,
so a page can render the ⛶ / ⤓ buttons with no script to drive them. This module proves, in
real chromium:

* panelkit.js actually LOADS on /portfolio (script element present + the delegated listener
  works), by clicking ⛶ ENLARGE on the ledger panel and reading ``.is-big`` back off the panel
  (and the label flip to ⛶ SHRINK), then toggling back;
* every class this page NEWLY applies survives the jarvis theme's broad rules as a COMPUTED
  style (the theme-override-clobbers-the-contract family, incl. round 6's promotion trap):
  the ``.ctl-kpi.k-edge`` tile really paints a 3px LEFT edge (and a plain 1px top), the
  ``.sf-pill`` chips keep their 20px pill radius, and the per-row ``.prov-chip`` renders at
  its 8px mono size inside the summary row.

Skips unless playwright + the bundled chromium are present (same posture as
``test_integrity_panelkit.py`` — the runtime stays stdlib-only, Law 1)."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

# build-agnostic (TEST-01, ADR-0406): the FIRST vendored chromium, whatever build the
# container ships — a chromium bump must never silently skip this module again
_PW_CHROMES = sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome"))
CHROME = _PW_CHROMES[0] if _PW_CHROMES else Path("/opt/pw-browsers/absent/chrome")

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason=f"bundled chromium not at {CHROME}")

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str, status: str) -> bytes:
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>{_TASK}</Project>"
    ).encode()


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
        r = c.post(
            "/upload",
            files=[
                ("files", ("a.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
                ("files", ("b.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
                ("files", ("c.xml", _mspdi("Beta", "2025-01-10T00:00:00"), "text/xml")),
            ],
        )
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


def test_panelkit_click_and_jarvis_probe_on_portfolio(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/portfolio", wait_until="domcontentloaded")
        page.wait_for_selector(".panel[data-export] [data-sf-big]", timeout=10000)

        # panelkit.js is genuinely on THIS page (cache-busted src → substring match)
        loaded = page.evaluate(
            "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
        )
        assert loaded, "panelkit.js script element missing on /portfolio"

        # ONE real interaction: click ⛶ on the ledger panel, read .is-big back
        btn = page.locator(".panel[data-export] [data-sf-big]")
        assert btn.inner_text() == "⛶ ENLARGE"
        btn.click()
        page.wait_for_timeout(50)
        assert page.evaluate(
            "() => document.querySelector('.panel[data-export]').classList.contains('is-big')"
        ), "click did not toggle .is-big — panelkit.js not driving /portfolio"
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"
        btn.click()  # and back
        page.wait_for_timeout(50)
        assert not page.evaluate(
            "() => document.querySelector('.panel[data-export]').classList.contains('is-big')"
        )

        # jarvis: probe the COMPUTED styles of every class this page newly applies (broad
        # `.panel` / `button` / `h2` theme rules must not flatten the contract).
        page.evaluate("() => document.documentElement.setAttribute('data-theme','jarvis')")
        page.wait_for_timeout(100)
        probe = page.evaluate(
            """() => {
              const cs = sel => { const el = document.querySelector(sel);
                return el ? getComputedStyle(el) : null; };
              const kpi = cs('.ctl-kpi.k-edge'), pill = cs('.sf-pill'),
                    chip = cs('details summary .prov-chip'), head = cs('.panel-head h2'),
                    tools = cs('.panel[data-export] .sf-tools button');
              return {kpiLeft: kpi && kpi.borderLeftWidth, kpiTop: kpi && kpi.borderTopWidth,
                      pillRadius: pill && pill.borderTopLeftRadius,
                      pillBorder: pill && pill.borderTopWidth,
                      chipFont: chip && chip.fontSize, chipVisible: chip && chip.display,
                      headCase: head && head.textTransform,
                      toolsShown: tools && tools.display};
            }"""
        )
        assert probe["kpiLeft"] == "3px", f"jarvis flattened the k-edge left edge: {probe}"
        assert probe["kpiTop"] == "1px", f"k-edge kept ctl's top edge under jarvis: {probe}"
        assert probe["pillRadius"] == "20px", f"jarvis flattened the pill radius: {probe}"
        assert probe["pillBorder"] == "1px", f"pill lost its border under jarvis: {probe}"
        assert probe["chipFont"] == "8px", f"prov chip lost its 8px mono under jarvis: {probe}"
        assert probe["chipVisible"] != "none", f"prov chip hidden under jarvis: {probe}"
        assert probe["headCase"] == "uppercase", f"panel-head h2 lost the contract: {probe}"
        assert probe["toolsShown"] != "none", f"sf-tools hidden under jarvis: {probe}"
        browser.close()
