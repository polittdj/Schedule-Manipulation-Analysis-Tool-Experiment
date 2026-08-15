"""/compare panel-contract behavior in a REAL browser (Mission Ops rank 5, ADR-0298).

Markup alone is not evidence (the round-4 latent-gap lesson): panelkit.js is a PER-PAGE
include, so a page can render the ⛶ / ⤓ buttons with no script to drive them. This module
proves, in real chromium:

* panelkit.js actually LOADS on /compare (script element present + the delegated listener
  works), by clicking ⛶ ENLARGE on a shelled panel and reading ``.is-big`` back off the
  panel (and the label flip to ⛶ SHRINK), then toggling back;
* the manipulation-signals panel's verdict wash SURVIVES the jarvis theme's broad
  ``.panel`` override (the theme-override-clobbers-the-contract family): computed
  border-left is 3px in the band tone and the background carries the gradient.

Skips unless playwright + the bundled chromium are present (same posture as
``test_float_tip_scroll.py`` — the runtime stays stdlib-only, Law 1)."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# build-agnostic (TEST-01, ADR-0406): the FIRST vendored chromium, whatever build the
# container ships — a chromium bump must never silently skip this module again
_PW_CHROMES = sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome"))
CHROME = _PW_CHROMES[0] if _PW_CHROMES else Path("/opt/pw-browsers/absent/chrome")

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason=f"bundled chromium not at {CHROME}")


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
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
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


def test_panelkit_click_toggles_is_big_and_jarvis_keeps_the_verdict_wash(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/compare", wait_until="domcontentloaded")
        page.wait_for_selector(".panel.verdict-band [data-sf-big]", timeout=10000)

        # panelkit.js is genuinely on THIS page (cache-busted src → substring match)
        loaded = page.evaluate(
            "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
        )
        assert loaded, "panelkit.js script element missing on /compare"

        # ONE real interaction: click ⛶ on the signals panel, read .is-big back
        btn = page.locator(".panel.verdict-band [data-sf-big]")
        assert btn.inner_text() == "⛶ ENLARGE"
        btn.click()
        page.wait_for_timeout(50)
        assert page.evaluate(
            "() => document.querySelector('.panel.verdict-band').classList.contains('is-big')"
        ), "click did not toggle .is-big — panelkit.js not driving /compare"
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"
        btn.click()  # and back (never leave the page mutated for later assertions)
        page.wait_for_timeout(50)
        assert not page.evaluate(
            "() => document.querySelector('.panel.verdict-band').classList.contains('is-big')"
        )

        # jarvis: the broad `.panel` override must NOT flatten the verdict band (computed style,
        # not markup — the standing rank-2/D1 lesson). vb-watch/at-risk → a 3px tinted edge.
        page.evaluate("() => document.documentElement.setAttribute('data-theme','jarvis')")
        page.wait_for_timeout(100)
        probe = page.evaluate(
            """() => {
              const el = document.querySelector('.panel.verdict-band');
              const cs = getComputedStyle(el);
              return {w: cs.borderLeftWidth, c: cs.borderLeftColor, bg: cs.backgroundImage,
                      d: cs.display};
            }"""
        )
        assert probe["w"] == "3px", f"jarvis flattened the band edge: {probe}"
        assert "gradient" in probe["bg"], f"jarvis lost the verdict wash: {probe}"
        # the stacked-panel modifier holds in jarvis too (table keeps normal block flow)
        assert probe["d"] == "block", f"vb-stack lost block flow: {probe}"
        # the edge is TONED (--warn/--bad resolve to a real color, not the default accent);
        # resolving the token in-page keeps the assertion theme-agnostic
        toned = page.evaluate(
            """() => {
              const el = document.querySelector('.panel.verdict-band');
              const cls = [...el.classList];
              const tok = cls.includes('vb-at-risk') ? '--bad'
                        : cls.includes('vb-watch') ? '--warn' : '--ok';
              const want = getComputedStyle(el).getPropertyValue(tok).trim();
              const probe = document.createElement('div');
              probe.style.color = want;
              document.body.appendChild(probe);
              const wantRgb = getComputedStyle(probe).color;
              probe.remove();
              return {edge: getComputedStyle(el).borderLeftColor, want: wantRgb};
            }"""
        )
        assert toned["edge"] == toned["want"], f"band edge not severity-toned: {toned}"
        browser.close()
