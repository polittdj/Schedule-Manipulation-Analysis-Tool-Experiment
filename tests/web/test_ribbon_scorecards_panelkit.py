"""/ribbon + /scorecards panel-contract behavior in a REAL browser (Mission Ops rank 8).

Markup alone is not evidence (the round-4 latent-gap lesson): panelkit.js is a PER-PAGE
include, so a page can render the ⛶ / ⤓ buttons with no script to drive them. This module
proves, in real chromium, on EACH converted page:

* panelkit.js actually LOADS (script element present + the delegated listener works), by
  clicking ⛶ ENLARGE and reading ``.is-big`` back off the panel (and the label flip);
* the PROMOTION CENSUS holds — no element gained ``.panel`` in the conversion (the counts were
  pinned to the pre-conversion render of this same fixture pair: 4 on /ribbon, 5 on
  /scorecards), so nothing new competes with jarvis's broad ``.panel`` rule. /ribbon's baseline
  is **5** since R-50 (ADR-0499) added the Metric History variants matrix by design; the count
  alone was never the whole claim, so every panel advertising ⛶ is now proved click-driven by
  name rather than merely counted;
* the jarvis probe (computed styles, never markup): the ribbon row-label keeps its 3px LEFT
  edge, a colored count cell keeps a non-transparent status tint, and the threshold tooltip
  rides the EXISTING mechanism (tooltips.js promotes the cell's ``title=`` to
  ``data-sf-hint`` — never a second tooltip system).

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this module (ADR-0418) (same posture as
``test_integrity_panelkit.py`` — the runtime stays stdlib-only, Law 1)."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")


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
        for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
            r = c.post("/upload", files={"files": (name, (GOLD / name).read_bytes(), "text/xml")})
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


def _prove_panelkit_click(page: Any, panel_sel: str) -> None:
    """ONE real interaction: panelkit.js is on THIS page and its delegated listener drives it."""
    loaded = page.evaluate(
        "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
    )
    assert loaded, f"panelkit.js script element missing ({page.url})"
    btn = page.locator(f"{panel_sel} [data-sf-big]")
    assert btn.inner_text() == "⛶ ENLARGE"
    btn.click()
    page.wait_for_timeout(50)
    assert page.evaluate(
        f"() => document.querySelector('{panel_sel}').classList.contains('is-big')"
    ), f"click did not toggle .is-big — panelkit.js not driving {page.url}"
    assert btn.inner_text() == "⛶ SHRINK"
    assert btn.get_attribute("aria-pressed") == "true"
    btn.click()  # and back (never leave the page mutated for later assertions)
    page.wait_for_timeout(50)
    assert not page.evaluate(
        f"() => document.querySelector('{panel_sel}').classList.contains('is-big')"
    )


def test_panelkit_click_census_and_jarvis_probe_on_ribbon(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/ribbon", wait_until="domcontentloaded")
        page.wait_for_selector("td.rib-row-label", timeout=10000)

        # Promotion census: the panel-contract conversion added ZERO .panel elements
        # (pre-conversion count 4). RE-DERIVED 2026-09-16: R-50 (ADR-0499) added ONE by design —
        # the Metric History variants matrix — so the baseline is 5. The count alone was never
        # the whole claim and is weaker now that the page carries two matrices, so every panel
        # that advertises the ⛶ affordance is proved CLICK-DRIVEN below, by name, not counted.
        assert page.evaluate("() => document.querySelectorAll('.panel').length") == 5

        # both matrices carry the ⛶ affordance and BOTH are proved click-driven by name — the
        # ribbon panel is addressed as the one that is NOT the variants panel, because the two
        # now share the same data-export (one workbook, all measures)
        _prove_panelkit_click(
            page, '.panel[data-export="/export/xlsx/ribbon"]:not(#metricHistoryVariants)'
        )
        _prove_panelkit_click(page, "#metricHistoryVariants")
        # exactly the panels proved above advertise ⛶ — a third one appearing must force a
        # decision here rather than riding along unproved
        assert page.evaluate("() => document.querySelectorAll('.panel [data-sf-big]').length") == 2

        # jarvis probe — computed styles, never markup (the standing rank-2/D1 lesson)
        page.evaluate("() => document.documentElement.setAttribute('data-theme','jarvis')")
        page.wait_for_timeout(100)
        probe = page.evaluate(
            """() => {
              const label = document.querySelector('td.rib-row-label');
              const cell = document.querySelector('td.rib-cell.rib-pass,'
                + 'td.rib-cell.rib-warn, td.rib-cell.rib-fail');
              const lcs = getComputedStyle(label), ccs = cell && getComputedStyle(cell);
              return {edge: lcs.borderLeftWidth,
                      bg: ccs && ccs.backgroundColor,
                      hint: cell && (cell.getAttribute('data-sf-hint')
                            || cell.getAttribute('title') || ''),
                      head: !!document.querySelector('.panel-head h2')};
            }"""
        )
        assert probe["edge"] == "3px", f"jarvis flattened the row-label edge: {probe}"
        assert probe["bg"] not in (None, "rgba(0, 0, 0, 0)"), (
            f"jarvis lost the status tint: {probe}"
        )
        # the threshold tooltip rides the EXISTING mechanism: tooltips.js has promoted the
        # cell's title= into data-sf-hint (or left the native title) — one tooltip, no new system
        assert probe["hint"] and "Click to list the activities" in probe["hint"], probe
        assert probe["head"], "panel-head strip missing under jarvis"
        browser.close()


def test_panelkit_click_and_census_on_scorecards(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/scorecards", wait_until="domcontentloaded")
        page.wait_for_selector(".panel[data-scorecard] .sl-chip", timeout=10000)

        # promotion census: ZERO elements gained .panel (pre-conversion count 5)
        assert page.evaluate("() => document.querySelectorAll('.panel').length") == 5

        _prove_panelkit_click(page, '.panel[data-scorecard="nasa_stat"]')

        # jarvis: the shelled scorecard panel keeps its stoplight chips + head strip visible
        page.evaluate("() => document.documentElement.setAttribute('data-theme','jarvis')")
        page.wait_for_timeout(100)
        probe = page.evaluate(
            """() => {
              const chip = document.querySelector('.panel[data-scorecard] .sl-chip');
              const head = document.querySelector('.panel[data-scorecard] .panel-head h2');
              return {chip: !!chip, head: head && getComputedStyle(head).display};
            }"""
        )
        assert probe["chip"], "stoplight chips lost under jarvis"
        assert probe["head"] and probe["head"] != "none", f"panel-head hidden: {probe}"
        browser.close()
