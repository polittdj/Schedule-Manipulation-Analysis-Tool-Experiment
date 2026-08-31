"""M5 (WP2) — the page-chrome controls: theme, page scale, language, Task Information, and the
Mission wall's chart toolbars.

These are the controls the WP1 census could not place in a family (they are not
zoom/fit/pan/play/step), and they are the ones the rest of the suite has been *bypassing*:
twenty modules exercise the four views by calling
``document.documentElement.setAttribute('data-theme', …)`` directly, so ``#themeSelect``'s own
change handler, its ``localStorage`` persistence and its pre-paint restore have never once been
driven. A control that every test routes around is a control nothing tests.

Three defects the first run of these drivers caught (all CONFIRMED-FIXED, see the ADR):

* **M5-01** — the Mission wall served **30** ``.chart-host`` tiles but only **9** chartframe
  toolbars. ``chartframe.js`` scanned once at ``DOMContentLoaded``; the wall's other 21 tiles
  fetch their data afterwards, so they were never framed. Measured decisively rather than
  guessed: a manual ``SFChartFrame.scan()`` on the settled wall took the count 9 → 30, which
  makes it an attach-vs-fetch race — the SAME shape as WP1's UI-02 sticky scrollbar — and not a
  design choice. The nine existing toolbars were confirmed FUNCTIONAL first (zoom grew their
  svg 536 → 670 px), so this restores a working affordance to 21 tiles rather than spreading
  dead chrome; ``mission.py`` also marks the tiles it does NOT want framed with ``chart-note``
  instead of ``chart-host``, so the class is the wall's own deliberate switch.
* **M5-02** — the Language selector always returned the operator to ``/``, never to the page
  they were reading. ``/language`` derived its destination from the ``Referer`` header, and the
  app sends ``Referrer-Policy: no-referrer`` on every response, so that header is never there.
  Measured absent from four different pages. The repo had already diagnosed and solved this for
  the banner Project switcher (``select[data-sf-nexturl-submit]`` + a server-validated
  ``next_url``, whose comment in ``chrome.js`` names the no-referrer policy as the reason) — the
  language form was simply never moved onto it.
* **M5-03** — ``driving_path.js`` was the only animated module ignoring prefers-reduced-motion;
  driven in ``test_ui_stepper_autoplay_browser.py`` and pinned statically by the now-computed
  A2 sweep in ``test_accessibility.py``.

``#uiScale`` is driven here too, and is NOT a defect: an early probe called it dead because it
measured ``document.body``'s width, which is full-bleed at any zoom. Measured on a heading's own
box it scales correctly (212 → 265 → 371 → 191 px across 1.0/1.25/1.75/0.9), so the driver
measures a real element, not the body.
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

THEMES = ("console", "daylight", "apollo", "jarvis")


def _load(client: TestClient) -> None:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
    meta = json.dumps(
        [
            {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(VERSIONS)
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    assert (
        client.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False).status_code
        == 303
    )


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


@pytest.fixture(scope="module")
def browser() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


def _page(browser: Any, base: str, url: str) -> Any:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(base + url, wait_until="networkidle")
    return ctx, page


# ── the view switcher ─────────────────────────────────────────────────────────────────────────


def test_theme_select_applies_all_four_views_and_actually_restyles_the_page(
    served: str, browser: Any
) -> None:
    """The REAL select, not ``setAttribute``: each view stamps, persists, and repaints.

    The repaint half is what the twenty ``setAttribute`` callers cannot check — stamping the
    attribute is what they do, so they would still pass if the four themes resolved to one
    palette. Four distinct rendered text colours is the proof the tokens actually differ.
    """
    ctx, page = _page(browser, served, "/")
    try:
        colours = {}
        for theme in THEMES:
            page.select_option("#themeSelect", theme)
            page.wait_for_timeout(150)
            current = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            assert current == theme
            assert page.evaluate("() => localStorage.getItem('sf-theme')") == theme, (
                f"{theme}: the choice was applied but never persisted"
            )
            colours[theme] = page.evaluate(
                "() => getComputedStyle(document.body).color + '|'"
                " + getComputedStyle(document.documentElement).backgroundColor"
            )
        assert len(set(colours.values())) == len(THEMES), (
            f"the four views did not resolve to four distinct palettes: {colours}"
        )
    finally:
        ctx.close()


def test_theme_choice_survives_a_reload(served: str, browser: Any) -> None:
    """theme.js is loaded synchronously in <head> so the saved view applies before first paint."""
    ctx, page = _page(browser, served, "/")
    try:
        page.select_option("#themeSelect", "apollo")
        page.wait_for_timeout(150)
        page.reload(wait_until="networkidle")
        theme_now = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert theme_now == "apollo"
        assert page.evaluate("() => document.getElementById('themeSelect').value") == "apollo", (
            "the view was restored but the select did not reflect it"
        )
    finally:
        ctx.close()


def test_theme_toggle_round_trips_daylight_and_the_last_dark_view(
    served: str, browser: Any
) -> None:
    """#themeToggle flips daylight <-> the last DARK view chosen, not a hardcoded pair."""
    ctx, page = _page(browser, served, "/")
    try:
        page.select_option("#themeSelect", "jarvis")
        page.wait_for_timeout(150)
        page.click("#themeToggle")
        page.wait_for_timeout(150)
        read = "() => document.documentElement.getAttribute('data-theme')"
        assert page.evaluate(read) == "daylight"
        page.click("#themeToggle")
        page.wait_for_timeout(150)
        assert page.evaluate(read) == "jarvis", (
            "the toggle did not return to the last DARK view (jarvis) — it fell back to a default"
        )
    finally:
        ctx.close()


def test_ui_scale_rescales_the_rendered_page_and_persists(served: str, browser: Any) -> None:
    """#uiScale rescales what is actually drawn — measured on a heading's box, not on body.

    body is full-bleed at every zoom, so measuring it reports "no change" and would call a
    working control dead. The heading's own rect is the honest measurement.
    """
    ctx, page = _page(browser, served, "/standards")
    try:

        def head_width() -> float:
            return page.evaluate(
                "() => { const h = document.querySelector('h1, h2, .brand');"
                " return h ? h.getBoundingClientRect().width : 0; }"
            )

        page.select_option("#uiScale", "1")
        page.wait_for_timeout(200)
        base_w = head_width()
        assert base_w > 0
        page.select_option("#uiScale", "1.75")
        page.wait_for_timeout(250)
        big = head_width()
        assert big > base_w * 1.4, f"175% did not enlarge the render: {base_w} -> {big}"
        assert page.evaluate("() => localStorage.getItem('sf-scale')") == "1.75"
        page.select_option("#uiScale", "0.9")
        page.wait_for_timeout(250)
        small = head_width()
        assert small < base_w, f"90% did not shrink the render: {base_w} -> {small}"
    finally:
        ctx.close()


# ── language ──────────────────────────────────────────────────────────────────────────────────


def test_language_select_translates_and_returns_to_the_page_you_were_on(
    served: str, browser: Any
) -> None:
    """Picking a language translates the page AND leaves you where you were (M5-02).

    Driven from several pages because "returns to the page you were on" is a claim about every
    page, and because a single page could pass by coincidence if it happened to be ``/``. The
    session language is process-wide, so it is restored to English at the end — otherwise this
    test silently translates every test that runs after it.
    """
    ctx, page = _page(browser, served, "/")
    try:
        for start in ("/standards", "/evm", "/risks"):
            page.goto(served + start, wait_until="networkidle")
            english = page.evaluate("() => document.body.innerText")
            with page.expect_navigation(wait_until="networkidle"):
                page.select_option("select[name=lang]", "es")
            landed = page.url[len(served) :]
            assert landed == start, (
                f"choosing a language from {start} landed on {landed!r} — the operator is thrown "
                f"back to the dashboard and loses the page they were reading"
            )
            assert page.evaluate("() => document.querySelector('select[name=lang]').value") == "es"
            assert page.evaluate("() => document.body.innerText") != english, (
                f"{start}: the language was accepted but the page did not translate"
            )
            with page.expect_navigation(wait_until="networkidle"):
                page.select_option("select[name=lang]", "en")
    finally:
        page.goto(served + "/", wait_until="networkidle")
        try:
            with page.expect_navigation(wait_until="networkidle"):
                page.select_option("select[name=lang]", "en")
        except Exception:
            pass
        ctx.close()


# ── Task Information ──────────────────────────────────────────────────────────────────────────


def test_task_information_opens_on_double_click_and_closes_on_escape(
    served: str, browser: Any
) -> None:
    """The MS-Project Task Information dialog: DOUBLE click (single click highlights, ADR-0186).

    Populated, not merely present — an overlay that opens empty is the same class of defect as a
    control that flips without moving anything.
    """
    ctx, page = _page(browser, served, "/path")
    try:
        page.wait_for_timeout(1200)
        row = page.query_selector("tr[data-uid]")
        assert row is not None, "/path served no activity rows to open"
        row.scroll_into_view_if_needed()
        row.dblclick()
        page.wait_for_timeout(600)
        overlay = page.evaluate(
            "() => { const o = document.querySelector('.ti-overlay');"
            " return o ? {text: o.innerText, display: getComputedStyle(o).display} : null; }"
        )
        assert overlay is not None, "double-clicking an activity row opened no Task Information"
        assert overlay["display"] != "none"
        assert "Task Information" in overlay["text"], f"unexpected overlay: {overlay['text'][:80]}"
        assert len(overlay["text"]) > 100, (
            f"the dialog opened but is empty ({len(overlay['text'])} chars) — a populated dialog "
            f"carries the activity's fields and its tab strip"
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        assert page.evaluate(
            "() => { const o = document.querySelector('.ti-overlay');"
            " return !o || getComputedStyle(o).display === 'none'; }"
        ), "Escape did not close the Task Information dialog"
    finally:
        ctx.close()


# ── the Mission wall's chart toolbars (the WP1 design question, decided) ───────────────────────


def test_every_mission_chart_host_carries_a_chartframe_toolbar(served: str, browser: Any) -> None:
    """M5-01: the wall's async tiles are framed too, not just the nine that beat the scan.

    The WP1 census floor-pinned 30 hosts against 9 toolbars and logged it as a design question.
    It is not one: the wall marks every tile it wants framed with ``chart-host`` (and the tiles
    it does not with ``chart-note``), and the 21 unframed ones were simply built after the
    one-shot DOMContentLoaded scan had already run.
    """
    ctx, page = _page(browser, served, "/mission")
    try:
        page.wait_for_timeout(2500)
        counts = page.evaluate(
            "() => ({hosts: document.querySelectorAll('.chart-host').length,"
            " framed: document.querySelectorAll('.cf-bar').length})"
        )
        assert counts["hosts"] >= 30, f"the wall lost tiles: {counts}"
        assert counts["framed"] == counts["hosts"], (
            f"{counts['hosts'] - counts['framed']} of {counts['hosts']} wall tiles have no chart "
            f"toolbar — the scan ran before they were fetched"
        )
        # and the scan must already be a fixed point: running it again changes nothing
        page.evaluate("() => window.SFChartFrame.scan()")
        page.wait_for_timeout(300)
        again = page.evaluate("() => document.querySelectorAll('.cf-bar').length")
        assert again == counts["framed"], (
            f"a second scan changed the count {counts['framed']} -> {again}: framing is not "
            f"idempotent and the observer will loop"
        )
    finally:
        ctx.close()


def test_a_late_framed_mission_tile_actually_zooms(served: str, browser: Any) -> None:
    """The toolbars restored to the async tiles must WORK, not just render.

    Adding 21 dead toolbars would be worse than adding none — the WP1 UI-01 lesson. So a tile
    that was NOT framed before this fix is driven, and its svg must grow.
    """
    ctx, page = _page(browser, served, "/mission")
    try:
        page.wait_for_timeout(2500)
        bars = page.query_selector_all(".cf-bar")
        assert len(bars) >= 30
        zoomed = 0
        for bar in bars[-6:]:  # the tail: tiles that arrive last, i.e. the previously unframed
            zin = bar.query_selector("[aria-label='Zoom in']")
            if zin is None:
                continue
            width_js = """(b) => { const w = b.closest('.cf-frame');
                const s = w && w.querySelector('svg');
                return s ? s.getBoundingClientRect().width : null; }"""
            before = page.evaluate(width_js, bar)
            if not before:
                continue
            zin.scroll_into_view_if_needed()
            zin.click()
            page.wait_for_timeout(200)
            after = page.evaluate(width_js, bar)
            assert after is not None and after > before * 1.05, (
                f"a restored tile toolbar does not zoom: {before} -> {after}"
            )
            zoomed += 1
        assert zoomed >= 2, f"only {zoomed} late tiles could be driven — the sample proves nothing"
    finally:
        ctx.close()
