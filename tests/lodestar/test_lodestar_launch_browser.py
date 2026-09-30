"""LODESTAR's launch page in a real browser (ADR-0541): the lightshow paints without an error,
the copy is LODESTAR's, the marking bars stay on the page at a laptop and a phone width in all
four views, the transit ends in the studio, the skip and the opt-out land on the Timeline."""

from __future__ import annotations

import datetime as dt
import socketserver
import threading
from collections.abc import Iterator
from typing import Any

import pytest

from schedule_forensics.lodestar.server import LodestarServer, LodestarState
from web.browser_chrome import chrome_kwargs

TODAY = dt.date(2026, 9, 1)
THEMES = ("console", "daylight", "apollo", "jarvis")
WIDTHS = (1440, 390)


@pytest.fixture(scope="module")
def base() -> Iterator[str]:
    srv = LodestarServer(0, LodestarState(), TODAY)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    socketserver.BaseServer.shutdown(srv)
    srv.server_close()
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


_STATE = """() => {
  const vh = window.innerHeight, vw = window.innerWidth;
  const inside = (el) => { const r = el.getBoundingClientRect();
    return r.top >= -0.5 && r.bottom <= vh + 0.5 && r.left >= -0.5 && r.right <= vw + 0.5
      && r.height > 0; };
  const bars = [...document.querySelectorAll('.cui-banner')];
  const c = document.getElementById('sfBootCanvas');
  return {
    bars: bars.length, barsInside: bars.every(inside),
    canvas: !!(c && c.width > 0 && c.height > 0),
    kicker: document.getElementById('sfBootKicker').textContent,
    h1: document.getElementById('sfBootH1').textContent,
    brand: document.querySelector('.ls-boot-brand').textContent.replace(/\\s+/g, ' ').trim(),
    brandInside: inside(document.querySelector('.ls-boot-brand')),
    seq: document.getElementById('sfBootSeq').textContent,
    scenes: window.SFBoot.scenes.length, home: window.SFBoot.home,
    stages: window.SFBoot.stages,
    accent: getComputedStyle(document.documentElement).getPropertyValue('--boot-accent').trim(),
  };
}"""


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("width", WIDTHS)
def test_the_page_paints_as_lodestar_with_its_chrome_on_screen(
    browser: Any, base: str, theme: str, width: int
) -> None:
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 780})
    ctx.add_init_script(f"try {{ localStorage.setItem('sf-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/launch")
    page.wait_for_selector("#sfBootKicker:not(:empty)")
    got = page.evaluate(_STATE)
    assert errors == [], errors
    assert got["bars"] == 2 and got["barsInside"], got
    assert got["canvas"] and got["brandInside"], got
    assert got["brand"] == "✦ LODESTAR One-Pager Studio"
    assert got["kicker"].startswith("01 — LODESTAR") and "star to steer by" in got["h1"]
    assert got["scenes"] == 3 and got["home"] == "/onepager"
    assert got["stages"][-1] == "STUDIO OPEN" and got["seq"] == "PRE-FLIGHT"
    assert got["accent"].lower() == "#f0c24b", (theme, got["accent"])  # the lodestar's gold
    ctx.close()


def test_the_transit_ends_in_the_studio_and_the_skip_lands_on_the_timeline(
    browser: Any, base: str
) -> None:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(base + "/launch")
    page.wait_for_selector("#sfBootKicker:not(:empty)")
    page.click("#sfBootBegin")  # reduced motion: the destination at once, no 7-s wait
    page.wait_for_selector("#sfBoot.is-ready")
    assert page.evaluate("document.getElementById('sfBootStage').textContent") == "STUDIO OPEN"
    assert page.locator(".boot-quick button").count() == 2
    with page.expect_navigation():
        page.click("#sfBootEnter")
    assert page.url.endswith("/onepager")
    page.goto(base + "/launch")
    page.wait_for_selector("#sfBootSkip")
    with page.expect_navigation():
        page.click("#sfBootSkip")
    assert page.url.endswith("/onepager")
    ctx.close()


def test_the_opt_out_goes_straight_to_the_studio_next_time(browser: Any, base: str) -> None:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(base + "/launch")
    page.wait_for_selector("#sfBootNever")
    page.check("#sfBootNever")
    page.goto(base + "/launch")
    page.wait_for_url("**/onepager")
    assert page.url.endswith("/onepager")
    page.goto(base + "/launch?replay=1")  # the way back in
    page.wait_for_selector("#sfBootKicker:not(:empty)")
    assert page.url.endswith("/launch?replay=1")
    ctx.close()
