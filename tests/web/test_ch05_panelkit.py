"""Chapter-05 panel-contract behavior in a REAL browser (/trend, /curves, /scurve — rank 9).

Markup alone is not evidence (the round-4 latent-gap lesson): panelkit.js is a PER-PAGE
include, so a page can render the ⛶ / ⤓ glyphs with no script to drive them. This module
proves, in real chromium, on EACH of the three pages:

* panelkit.js actually LOADS — the ``<script src>`` is cache-busted, so the include is matched
  as a SUBSTRING — and its delegated listener works: ONE real click on ⛶ ENLARGE flips the
  panel to ``.is-big`` and the label to ⛶ SHRINK, and a second click restores both;
* the **PROMOTION CENSUS** holds — no element gained ``.panel`` in the conversion (pinned to
  the pre-conversion render of this same fixture pair: 11 on /trend, 4 on /curves, 3 on
  /scurve), so nothing new competes with jarvis's broad ``.panel`` rule;
* the ⤓ EXCEL glyph is not decoration: a real click is followed by panelkit to the panel's
  ``data-export`` and the browser actually receives the workbook (a live endpoint, never a
  dead link);
* the **animation is intact** — a real click on a per-chart Next button advances that chart's
  frame caption, and the page master Step-all still drives it;
* on /curves the SINGLE ⛶ button carries both scopes (the panel's ``.is-big`` via panelkit and
  the chart's ``.tile-expanded`` overlay via its original listener) — one button, one label
  owner, no duplicate glyph;
* the jarvis probe reads COMPUTED styles (never markup): the head strip lays out, the h2 takes
  the jarvis accent, the prov chip keeps its 1px border, the takeaway is visible, and no
  element this round touched extends past the viewport.

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this module (ADR-0418) (same posture as
``test_ribbon_scorecards_panelkit.py`` — the runtime stays stdlib-only, Law 1)."""

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

#: .panel elements on each page BEFORE the rank-9 conversion, on this fixture pair. The
#: conversion decorates existing panels only — it must never promote a new one.
PANELS_BEFORE = {"/trend": 11, "/curves": 4, "/scurve": 3}

#: a selector that is on the page only once its client-side chart has actually drawn
READY = {
    "/trend": "#trendCharts .chart",
    "/curves": "#dataDateChart svg",
    "/scurve": "#scurveChart svg",
}

#: the panel whose ⛶ / ⤓ are exercised, and the endpoint its ⤓ must reach
PANEL = {
    "/trend": ('.panel[data-export="/export/xlsx/trend"]', "/export/xlsx/trend"),
    "/curves": ('.panel[data-export="/export/xlsx/curves"]', "/export/xlsx/curves"),
    "/scurve": ('.panel[data-export="/export/xlsx/scurve"]', "/export/xlsx/scurve"),
}


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


def _open(browser: Any, base: str, route: str) -> Any:
    page = browser.new_page(viewport={"width": 1440, "height": 950})
    # never networkidle: the heartbeat (3s) and sysmon (2s) pollers never let the page go idle
    page.goto(base + route, wait_until="domcontentloaded")
    page.wait_for_selector(READY[route], timeout=25000)
    page.wait_for_timeout(400)
    return page


def _prove_panelkit_click(page: Any, panel_sel: str) -> None:
    """ONE real interaction: panelkit.js is on THIS page and its delegated listener drives it."""
    loaded = page.evaluate(
        "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
    )
    assert loaded, f"panelkit.js script element missing ({page.url})"
    btn = page.locator(f"{panel_sel} [data-sf-big]").first
    assert btn.inner_text() == "⛶ ENLARGE"
    btn.click()  # a REAL user click (isTrusted) — not element.click() from a script
    page.wait_for_timeout(80)
    assert page.evaluate(
        f"() => document.querySelector('{panel_sel}').classList.contains('is-big')"
    ), f"click did not toggle .is-big — panelkit.js not driving {page.url}"
    assert btn.inner_text() == "⛶ SHRINK"
    assert btn.get_attribute("aria-pressed") == "true"
    btn.click()  # and back (never leave the page mutated for later assertions)
    page.wait_for_timeout(80)
    assert not page.evaluate(
        f"() => document.querySelector('{panel_sel}').classList.contains('is-big')"
    )
    assert btn.inner_text() == "⛶ ENLARGE"


def _prove_excel_click(page: Any, panel_sel: str, expected_path: str) -> None:
    """The ⤓ glyph is wired AND its endpoint is live: a real click yields a real download.

    Asserted on the NETWORK, not on the download's URL. ADR-0360 deliberately stopped navigating to
    the export: the button now ``fetch``es (so it can hold a PREPARING state through a 140 s
    server-side model re-run instead of reading as dead) and hands the browser a same-origin
    ``blob:`` via ``URL.createObjectURL``. ``download.url`` is therefore
    ``blob:http://127.0.0.1:PORT/<uuid>`` and can never contain the export path — the old
    ``expected_path in download.url`` had been asserting the pre-ADR-0360 mechanism, and failed
    on a working button (BROWSER-ORPHAN-01).

    Watching the response is stronger than the string it replaces: the old form proved only that a
    URL had a shape, while this proves the export endpoint was really CALLED. Mutation-measured —
    pointing the fetch at an unrelated URL still yields a ``.xlsx``-named blob download, and only
    the ``seen`` assertion notices.

    The ``200`` check is a secondary invariant, not the load-bearing one: measured against a
    deliberately dead (500) endpoint, the failure surfaces as the download wait timing out, because
    a non-ok response throws before any blob is made. Kept because it is free and would catch a
    future shape where a non-200 still produced a download.
    """
    btn = page.locator(f"{panel_sel} [data-sf-excel]").first
    assert btn.inner_text() == "⤓ EXCEL"
    seen: list[tuple[str, int]] = []
    page.on(
        "response",
        lambda r: seen.append((r.url, r.status)) if expected_path in r.url else None,
    )
    with page.expect_download(timeout=25000) as info:
        btn.click()
    download = info.value
    assert seen, (
        f"a download arrived but nothing ever requested {expected_path} — the ⤓ button is not "
        f"wired to its export endpoint ({page.url})"
    )
    assert all(status == 200 for _, status in seen), f"{expected_path} did not answer 200: {seen}"
    assert download.suggested_filename.endswith(".xlsx"), download.suggested_filename


def _jarvis_probe(page: Any) -> dict[str, Any]:
    page.evaluate("() => document.documentElement.setAttribute('data-theme','jarvis')")
    page.wait_for_timeout(150)
    probe: dict[str, Any] = page.evaluate(
        """() => {
          const cs = e => e && getComputedStyle(e);
          const head = document.querySelector('.panel-head');
          const h2 = document.querySelector('.panel-head h2');
          const chip = document.querySelector('.panel-head .prov-chip');
          const take = document.querySelector('.sf-take');
          const tool = document.querySelector('.sf-tools button');
          return {
            head: cs(head) && cs(head).display,
            h2_color: cs(h2) && cs(h2).color,
            h2_upper: cs(h2) && cs(h2).textTransform,
            chip_border: cs(chip) && cs(chip).borderTopWidth,
            take_shown: cs(take) && cs(take).display !== 'none',
            tool_shown: cs(tool) && cs(tool).display !== 'none',
            // nothing the conversion added may push the layout past the viewport. (The
            // documentElement's own scrollWidth is NOT the measure: it reads wide on every
            // page of this app, /ribbon and /evm included, from a pre-existing off-canvas
            // layer — so the check is scoped to the elements this round touches.)
            wide: [...document.querySelectorAll(
                     '.panel,.panel-head,.sf-tools,.sf-take,.page-takeaway,.page-lede')]
                   .filter(e => e.getBoundingClientRect().right
                                > document.documentElement.clientWidth + 1)
                   .map(e => e.className.toString().slice(0, 50)),
          };
        }"""
    )
    assert probe["head"] == "flex", probe
    assert probe["h2_color"] == "rgb(25, 211, 255)", probe  # jarvis --accent, not flattened
    assert probe["h2_upper"] == "uppercase", probe
    assert probe["chip_border"] == "1px", probe
    assert probe["take_shown"] and probe["tool_shown"], probe
    assert probe["wide"] == [], probe
    return probe


@pytest.mark.parametrize("route", ["/trend", "/curves", "/scurve"])
def test_panelkit_click_census_and_jarvis(served: str, route: str) -> None:
    from playwright.sync_api import sync_playwright

    sel, endpoint = PANEL[route]
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = _open(browser, served, route)

        # promotion census: the conversion added ZERO .panel elements
        assert (
            page.evaluate("() => document.querySelectorAll('.panel').length")
            == (PANELS_BEFORE[route])
        ), route

        _prove_panelkit_click(page, sel)
        _prove_excel_click(page, sel, endpoint)
        _jarvis_probe(page)
        browser.close()


def test_curves_single_enlarge_button_carries_both_scopes(served: str) -> None:
    """/curves hosts exactly one chart per panel, so its ⛶ IS the panelkit button: one click
    lifts the chart into its viewport overlay (the ORIGINAL wiring) *and* marks the panel
    .is-big (the contract), with panelkit as the single owner of the label."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = _open(browser, served, "/curves")
        panel = page.locator(".panel:has(#dataDateChart)")
        panel.locator("[data-sf-big]").first.click()
        page.wait_for_timeout(100)
        state = page.evaluate(
            """() => {
              const host = document.querySelector('#dataDateChart');
              const shell = host.closest('.sf-tilebox');
              const p = host.closest('.panel');
              const b = p.querySelector('[data-sf-big]');
              return {big: p.classList.contains('is-big'),
                      overlay: shell.classList.contains('tile-expanded'),
                      overlay_pos: getComputedStyle(shell).position,
                      label: b.textContent,
                      buttons: p.querySelectorAll('[data-sf-big]').length};
            }"""
        )
        assert state["big"] and state["overlay"], state
        assert state["overlay_pos"] == "fixed", state  # the pre-existing overlay still applies
        assert state["label"] == "⛶ SHRINK", state
        assert state["buttons"] == 1, state  # never a second ⛶ on the same panel
        panel.locator("[data-sf-big]").first.click()
        page.wait_for_timeout(100)
        assert not page.evaluate(
            "() => document.querySelector('#dataDateChart').closest('.panel')"
            ".classList.contains('is-big')"
        )
        browser.close()


def test_steppers_and_play_all_still_animate(served: str) -> None:
    """ADR-0275's coordinator and the per-chart steppers are untouched by the normalization."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())

        page = _open(browser, served, "/curves")
        panel = page.locator(".panel:has(#dataDateChart)")
        label = panel.locator(".sf-frame-label").first
        first = label.inner_text()
        panel.locator(".sf-frame-next").first.click()
        page.wait_for_timeout(150)
        stepped = label.inner_text()
        assert stepped != first and "file " in stepped, (first, stepped)
        page.locator("#sfStepAll").click()  # the page master still drives the same stepper
        page.wait_for_timeout(200)
        assert label.inner_text() != stepped
        # ▦ DATA still reveals that chart's own table, with the contract's toggled label
        dat = panel.locator(".tile-data").first
        assert dat.inner_text() == "▦ DATA"
        dat.click()
        page.wait_for_timeout(100)
        assert dat.inner_text() == "▦ HIDE DATA"
        assert page.evaluate(
            "() => document.querySelector('#dataDateChart').closest('.sf-tilebox')"
            ".classList.contains('show-data')"
        )
        page.close()

        page = _open(browser, served, "/trend")
        lbl = page.locator("#trendCharts .sf-frame-label").first
        was = lbl.inner_text()
        page.locator("#trendCharts .sf-frame-next").first.click()
        page.wait_for_timeout(150)
        assert lbl.inner_text() != was
        assert page.locator("#sfPlayAll").count() == 1
        assert page.locator("#qualNext").count() == 1  # the quality stepper joins the beat
        page.close()

        page = _open(browser, served, "/scurve")
        for ident in ("#prevScurve", "#nextScurve", "#scurvePlay"):
            assert page.locator(ident).count() == 1, ident
        sl = page.locator("#scurveLabel")
        before = sl.inner_text()
        page.locator("#prevScurve").click()
        page.wait_for_timeout(150)
        assert sl.inner_text() != before
        browser.close()
