"""/cei's panel contract in a REAL browser — Ultracode round 10.

Markup is not evidence (the round-4 /evm latent gap: a page can wear the whole toolbar and be
inert because panelkit.js is a PER-PAGE include). In real chromium, on /cei, this proves:

* panelkit.js actually LOADS (the ``<script src>`` is cache-busted, so it is matched as a
  SUBSTRING) and its delegated listener drives ONE real user click: ⛶ ENLARGE flips the panel
  to ``.is-big`` and the label to ⛶ SHRINK, and a second click restores both;
* ⤓ EXCEL is not decoration — a real click is followed to the panel's ``data-export`` and the
  browser actually receives the workbook;
* the **promotion census** holds in the live DOM (5 ``.panel`` — the pre-conversion count on
  this fixture pair), so nothing new joins jarvis's broad ``html[data-theme=jarvis] .panel``;
* the **four-theme probe reads COMPUTED styles, never markup** (a defined token is not a
  painting token; apollo also swaps the font-family, so geometry differs, not just colour);
* the **animation and the shared cei.js are intact** — the chart paints, a real click on
  ``#nextSnap`` advances ``#snapLabel``, and the page raises ZERO console/page errors (cei.js
  reads five ids unguarded and is shared with the /mission wall).

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this module (ADR-0418) (same posture as
``test_ch05_panelkit.py`` — the runtime stays stdlib-only, Law 1)."""

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

#: .panel elements on /cei BEFORE the round-10 conversion, on this fixture pair (measured on
#: origin/main). The conversion decorates existing panels only — it never promotes a new one.
PANELS_BEFORE = 5

PANEL_SEL = '.panel[data-export="/export/xlsx/cei"]'


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
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def _open(browser: Any, base: str, errors: list[str] | None = None) -> Any:
    page = browser.new_page(viewport={"width": 1440, "height": 950})
    if errors is not None:
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on(
            "console",
            lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None,
        )
    # never networkidle: the heartbeat (3s) and sysmon (2s) pollers never let the page go idle
    page.goto(base + "/cei", wait_until="domcontentloaded")
    page.wait_for_selector("#ceiChart svg", timeout=25000)
    page.wait_for_timeout(400)
    return page


def test_panelkit_click_excel_and_census(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        errors: list[str] = []
        page = _open(browser, served, errors)

        # the include is really there (cache-busted src ⇒ substring match)
        assert page.evaluate(
            "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
        ), "panelkit.js script element missing on /cei"
        assert (
            page.evaluate(
                "() => [...document.scripts]"
                ".filter(s => s.src.includes('/static/panelkit.js')).length"
            )
            == 1
        ), "panelkit.js included twice ⇒ two delegated listeners ⇒ a double toggle"

        # promotion census in the LIVE dom
        assert page.evaluate("() => document.querySelectorAll('.panel').length") == PANELS_BEFORE
        assert page.evaluate(f"() => document.querySelectorAll('{PANEL_SEL}').length") == 2
        assert page.evaluate("() => document.querySelectorAll('.sf-drawer').length") == 0
        assert page.evaluate("() => document.body.innerText.includes('▦')") is False

        # ONE real user click (isTrusted) on the chart panel's ⛶
        panel = page.locator(PANEL_SEL).first
        btn = panel.locator("[data-sf-big]").first
        assert btn.inner_text() == "⛶ ENLARGE"
        btn.click()
        page.wait_for_timeout(80)
        assert page.evaluate(
            f"() => document.querySelector('{PANEL_SEL}').classList.contains('is-big')"
        ), "click did not toggle .is-big — panelkit.js is not driving /cei"
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"
        btn.click()
        page.wait_for_timeout(80)
        assert not page.evaluate(
            f"() => document.querySelector('{PANEL_SEL}').classList.contains('is-big')"
        )
        assert btn.inner_text() == "⛶ ENLARGE"

        # ⤓ EXCEL is wired AND its endpoint is live
        # Asserted on the NETWORK, not the download URL. ADR-0360 made ⤓ EXCEL fetch the bytes and
        # hand over a same-origin `blob:` (so the button can hold PREPARING through a long
        # server-side re-run), so `download.url` is `blob:…/<uuid>` and can never contain the
        # export path. The old string check was pinning the pre-ADR-0360 navigation and failed on a
        # working button (BROWSER-ORPHAN-01). Watching the response proves the endpoint was really
        # CALLED — mutation-measured: a fetch aimed elsewhere still yields a .xlsx-named blob, and
        # only `seen` notices. The 200 check is secondary: a dead endpoint surfaces as the download
        # wait timing out, because a non-ok response throws before any blob is made.
        xl = panel.locator("[data-sf-excel]").first
        assert xl.inner_text() == "⤓ EXCEL"
        seen: list[tuple[str, int]] = []
        page.on(
            "response",
            lambda r: seen.append((r.url, r.status)) if "/export/xlsx/cei" in r.url else None,
        )
        with page.expect_download(timeout=25000) as info:
            xl.click()
        download = info.value
        assert seen, "a download arrived but nothing ever requested /export/xlsx/cei"
        assert all(status == 200 for _, status in seen), f"/export/xlsx/cei not 200: {seen}"
        assert download.suggested_filename.endswith(".xlsx"), download.suggested_filename

        assert errors == [], errors  # cei.js reads five ids unguarded — a rename would throw
        browser.close()


def test_the_animation_and_chartframe_survive(served: str) -> None:
    """The snapshot stepper still drives the shared cei.js chart, and chartframe's own
    zoom bar (a DIFFERENT vocabulary from the contract's ⛶ ENLARGE) is still attached to the
    chart host, not removed and not duplicated."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        errors: list[str] = []
        page = _open(browser, served, errors)

        label = page.locator("#snapLabel")
        before = label.inner_text()
        page.locator("#nextSnap").click()
        page.wait_for_timeout(200)
        assert label.inner_text() != before, (before, label.inner_text())

        # chartframe's zoom bar is untouched, and there is exactly ONE ⛶ per panel
        assert (
            page.evaluate("() => document.querySelectorAll('#ceiChart ~ .cf-bar, .cf-bar').length")
            >= 1
        )
        assert (
            page.evaluate(
                f"() => document.querySelector('{PANEL_SEL}')"
                ".querySelectorAll('[data-sf-big]').length"
            )
            == 1
        )
        assert errors == [], errors
        browser.close()


def test_four_theme_probe_reads_computed_styles(served: str) -> None:
    """Standing requirement 1: probe COMPUTED styles in every theme. Under jarvis the broad
    ``html[data-theme=jarvis] button`` rule out-ranks ``.sf-tools button`` (later sheet, higher
    specificity) — that is the ALREADY-SHIPPED condition on /trend, /curves, /scurve,
    /portfolio and /integrity, so it is asserted as-is, never "fixed" here."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = _open(browser, served)
        for theme in ("console", "daylight", "apollo", "jarvis"):
            page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
            page.wait_for_timeout(150)
            probe = page.evaluate(
                """() => {
                  const cs = e => e && getComputedStyle(e);
                  const q = s => document.querySelector(s);
                  const head = q('.panel-head'), h2 = q('.panel-head h2');
                  const chip = q('.panel-head .prov-chip'), take = q('.sf-take');
                  const tool = q('.sf-tools button');
                  return {
                    head: cs(head).display,
                    h2_color: cs(h2).color, h2_size: cs(h2).fontSize,
                    chip_border: cs(chip).borderTopWidth, chip_shown: cs(chip).display,
                    chip_w: chip.getBoundingClientRect().width,
                    take_shown: cs(take).display !== 'none',
                    take_color: cs(take).color, take_family: cs(take).fontFamily,
                    tool_shown: cs(tool).display !== 'none',
                    tool_size: cs(tool).fontSize, tool_color: cs(tool).color,
                    wide: [...document.querySelectorAll(
                             '.panel,.panel-head,.sf-tools,.sf-take,.page-takeaway,.page-lede')]
                           .filter(e => e.getBoundingClientRect().right
                                        > document.documentElement.clientWidth + 1)
                           .map(e => e.className.toString().slice(0, 50)),
                  };
                }"""
            )
            # every one PAINTS a real value in every theme (a defined token is not a painting one)
            assert probe["head"] == "flex", (theme, probe)
            assert probe["h2_color"].startswith("rgb"), (theme, probe)
            assert probe["chip_border"] == "1px", (theme, probe)
            assert probe["chip_shown"] != "none" and probe["chip_w"] > 40, (theme, probe)
            assert probe["take_shown"] and probe["take_color"].startswith("rgb"), (theme, probe)
            assert probe["tool_shown"] and probe["tool_size"] != "0px", (theme, probe)
            assert probe["wide"] == [], (theme, probe)
            if theme == "jarvis":
                # the HUD treatment of the tool buttons is what we already ship elsewhere
                assert probe["h2_color"] == "rgb(25, 211, 255)", probe
                assert probe["tool_color"] == "rgb(25, 211, 255)", probe
            if theme == "apollo":
                assert "Plex Mono" in probe["take_family"], probe  # geometry differs, by design
        browser.close()
