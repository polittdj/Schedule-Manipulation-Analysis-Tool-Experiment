"""/integrity panel-contract behavior in a REAL browser (Mission Ops rank 6, ADR-0298).

Markup alone is not evidence (the round-4 latent-gap lesson): panelkit.js is a PER-PAGE include,
so a page can render the ⛶ / ⤓ buttons with no script to drive them. This module proves, in
real chromium:

* panelkit.js actually LOADS on /integrity (script element present + the delegated listener
  works), by clicking ⛶ ENLARGE on the verdict-band findings panel and reading ``.is-big``
  back off the panel (and the label flip to ⛶ SHRINK), then toggling back;
* the findings-drill citation card really renders: clicking a ``view all N`` link produces a
  ``.finding.cite-card`` inside #findingsDrill, severity-toned by the engine's own row;
* the verdict wash SURVIVES the jarvis theme's broad ``.panel`` override (the
  theme-override-clobbers-the-contract family): computed border-left is 3px in the band tone.

Skips unless playwright + the bundled chromium are present (same posture as
``test_compare_panelkit.py`` — the runtime stays stdlib-only, Law 1)."""

from __future__ import annotations

import gzip
import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden"
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
    hf = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    hfu = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated.mspdi.xml.gz").read_bytes()
    )
    p5 = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    with TestClient(app) as c:
        for name, data in (
            ("Hard_File.mpp.xml", hf),
            ("Hard_File_updated.mpp.xml", hfu),
            ("Project5.mpp.xml", p5),
        ):
            r = c.post(
                "/upload",
                files={"files": (name, data, "text/xml")},
                data={"file_meta": json.dumps([{"rel": f"History/{name}", "mtime": 1}])},
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


def test_panelkit_click_drill_card_and_jarvis_wash_on_integrity(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/integrity?a=0&b=2", wait_until="domcontentloaded")
        page.wait_for_selector(".panel.verdict-band [data-sf-big]", timeout=10000)

        # panelkit.js is genuinely on THIS page (cache-busted src → substring match)
        loaded = page.evaluate(
            "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
        )
        assert loaded, "panelkit.js script element missing on /integrity"

        # ONE real interaction: click ⛶ on the findings panel, read .is-big back
        btn = page.locator(".panel.verdict-band [data-sf-big]")
        assert btn.inner_text() == "⛶ ENLARGE"
        btn.click()
        page.wait_for_timeout(50)
        assert page.evaluate(
            "() => document.querySelector('.panel.verdict-band').classList.contains('is-big')"
        ), "click did not toggle .is-big — panelkit.js not driving /integrity"
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"
        btn.click()  # and back (never leave the page mutated for later assertions)
        page.wait_for_timeout(50)
        assert not page.evaluate(
            "() => document.querySelector('.panel.verdict-band').classList.contains('is-big')"
        )

        # the findings-drill citation card: click a real 'view all N' link, wait for the card
        page.locator("a.cite-more").first.click()
        page.wait_for_selector("#findingsDrill .finding.cite-card", timeout=10000)
        card = page.evaluate(
            """() => {
              const el = document.querySelector('#findingsDrill .finding.cite-card');
              const sev = [...el.classList].find(c => c.startsWith('sev-')) || '';
              return {sev: sev, cite: el.querySelector('p.cite').textContent,
                      rows: el.querySelectorAll('tbody tr').length,
                      h3: el.querySelector('h3').textContent};
            }"""
        )
        assert card["rows"] > 0, f"drill card rendered no activity rows: {card}"
        assert "SOURCE:" in card["cite"]
        assert "cited activities" in card["h3"]
        # tone (when present) is one of the engine's own severities — never an invented class
        assert card["sev"] in ("", "sev-HIGH", "sev-MEDIUM", "sev-LOW", "sev-INFO")

        # jarvis: the broad `.panel` override must NOT flatten the verdict band (computed style,
        # not markup — the standing rank-2/D1 lesson).
        page.evaluate("() => document.documentElement.setAttribute('data-theme','jarvis')")
        page.wait_for_timeout(100)
        probe = page.evaluate(
            """() => {
              const el = document.querySelector('.panel.verdict-band');
              const cs = getComputedStyle(el);
              const card = document.querySelector('#findingsDrill .finding.cite-card');
              const ccs = card ? getComputedStyle(card) : null;
              const edge = sel => { const el = document.querySelector(sel);
                return el ? getComputedStyle(el).borderLeftWidth : null; };
              return {w: cs.borderLeftWidth, bg: cs.backgroundImage, d: cs.display,
                      cardEdge: ccs && ccs.borderLeftWidth,
                      effectsEdge: edge('.panel.change-effects'),
                      cfEdge: edge('.panel.counterfactual')};
            }"""
        )
        assert probe["w"] == "3px", f"jarvis flattened the band edge: {probe}"
        assert "gradient" in probe["bg"], f"jarvis lost the verdict wash: {probe}"
        assert probe["d"] == "block", f"vb-stack lost block flow: {probe}"
        # the drill citation card keeps its 3px severity edge under jarvis too
        assert probe["cardEdge"] == "3px", f"jarvis flattened the drill card edge: {probe}"
        # the effect/counterfactual panels keep their app.css 3px tinted edges under jarvis's
        # broad .panel rule (the clobber this round's probe caught and hud.css now restores)
        assert probe["effectsEdge"] == "3px", f"jarvis flattened change-effects: {probe}"
        assert probe["cfEdge"] == "3px", f"jarvis flattened counterfactual: {probe}"
        browser.close()
