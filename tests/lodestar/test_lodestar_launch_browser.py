"""LODESTAR's launch page in a real browser (ADR-0541; rebuilt to the "Console" design handoff by
ADR-0543): it paints without an error, the copy is LODESTAR's, the marking bars and the credit
stay on the page at a laptop and a phone width in all four views, the hero cycles (and holds
still under reduced motion), the star fix ends on the welcome panel that opens the studio, and
the skip, Escape and the opt-out land on the Timeline — with ``?replay=1`` the way back in.

Re-aimed by ADR-0543 from v1's Polaris² boot screen (``#sfBoot*``, ``window.SFBoot``, the
``sf-theme`` themes console / daylight / apollo / jarvis). v1's particle canvas and its
``--boot-accent`` gold were retired by the design — the page has no canvas and no sound (pinned
absent below), and its gold is the view's ``--accent-gold`` token, which the ✦ mark must wear in
every view.
"""

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
VIEWS = ("dark", "bright", "contrast", "console")
WIDTHS = (1440, 390)
#: The stories the hero tells, by their kickers' openings (typed from the handoff).
KICKERS = ("01 — LODESTAR", "02 — PRIOR AND CURRENT", "03 — YOUR LOGIC")


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
  const shown = (el) => { const cs = getComputedStyle(el);
    return cs.visibility === 'visible' && cs.display !== 'none'
      && el.getClientRects().length > 0; };
  const bars = [...document.querySelectorAll('.cui-banner')];
  const credits = [...document.querySelectorAll('a[href^="mailto:"]')];
  const mark = document.querySelector('.ls-launch-mark');
  const probe = document.createElement('span');
  probe.style.color = 'var(--accent-gold)';
  document.body.appendChild(probe);
  const gold = getComputedStyle(probe).color;
  probe.remove();
  return {
    theme: document.documentElement.dataset.theme,
    bars: bars.length, barsInside: bars.every(inside),
    credits: credits.length, creditsShown: credits.every(shown),
    noisy: document.querySelectorAll('canvas, audio, video').length,
    kicker: document.getElementById('lsHeroK').textContent,
    h1: document.getElementById('lsHeroH').textContent,
    brand: document.querySelector('.ls-launch-brand').textContent.replace(/\\s+/g, ' ').trim(),
    brandInside: inside(document.querySelector('.ls-launch-brand')),
    seq: document.getElementById('lsSeq').textContent,
    stages: document.querySelectorAll('[data-ls-stage]').length,
    star: shown(document.getElementById('lsStarFix')),
    skip: shown(document.getElementById('lsSkip')),
    mark: getComputedStyle(mark).color, gold: gold,
    hscroll: document.documentElement.scrollWidth > vw + 1,
  };
}"""


def _context(browser: Any, view: str, width: int, **kw: Any) -> Any:
    ctx = browser.new_context(
        viewport={"width": width, "height": 900 if width > 500 else 780}, **kw
    )
    ctx.add_init_script(
        f"try {{ localStorage.setItem('lodestar-view', '{view}'); }} catch (e) {{}}"
    )
    return ctx


@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize("width", WIDTHS)
def test_the_page_paints_as_lodestar_with_its_chrome_on_screen(
    browser: Any, base: str, view: str, width: int
) -> None:
    ctx = _context(browser, view, width)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/launch")
    page.wait_for_selector("#lsHeroK:not(:empty)")
    got = page.evaluate(_STATE)
    ctx.close()
    assert errors == [], errors
    assert got["theme"] == view
    assert got["bars"] == 2 and got["barsInside"], got
    assert got["credits"] == 2 and got["creditsShown"], got  # the credit top and bottom (§7c)
    assert got["noisy"] == 0, got  # no canvas, no sound (ADR-0543 retired v1's)
    assert got["brandInside"] and got["brand"] == "✦ LODESTAR One-Pager Studio", got
    assert got["kicker"].startswith(KICKERS[0]) and "star to steer by" in got["h1"]
    assert got["stages"] == 6 and got["seq"] == "PRE-FLIGHT"
    assert got["star"] and got["skip"], got  # scripting on: the star fix shows beside the skip
    assert not got["hscroll"], f"{view}@{width}: the page scrolls sideways"
    # the ✦ wears this view's gold (a logotype: WCAG 1.4.3 sets it no contrast minimum)
    assert got["mark"] == got["gold"], (view, got["mark"], got["gold"])


def test_mutation_a_mark_off_its_gold_is_named(browser: Any, base: str) -> None:
    """MUTATION: the ✦ painted in the faint text token — the same probe sees it is not the
    view's gold."""
    ctx = _context(browser, "dark", 1440)
    page = ctx.new_page()
    page.goto(base + "/launch")
    page.add_style_tag(content=".ls-launch-mark{color:var(--text-faint)!important}")
    got = page.evaluate(_STATE)
    ctx.close()
    assert got["mark"] != got["gold"]


def _hero_story(browser: Any, base: str, steps: tuple[int, ...], *, reduced: bool) -> list[str]:
    """The hero's kicker at load and after each of ``steps`` ms more of the page's own clock (a
    fake clock — no real wait), with or without ``prefers-reduced-motion``; then the dots'
    ``aria-pressed`` states. (Three stories: a 3-step sample can come back to the first, so
    every step is recorded, never only the last.)"""
    kw: dict[str, Any] = {"reduced_motion": "reduce"} if reduced else {}
    ctx = _context(browser, "dark", 1440, **kw)
    page = ctx.new_page()
    # a PAUSED fake clock: time moves only by run_for (an installed clock that is not paused
    # keeps flowing in real time, and the page's load would eat into the first dwell)
    start = dt.datetime(2026, 9, 1, 8, 0, 0)
    page.clock.install(time=start)
    page.clock.pause_at(start + dt.timedelta(seconds=1))
    page.goto(base + "/launch")
    page.wait_for_selector("#lsHeroK:not(:empty)")
    seen = [page.text_content("#lsHeroK") or ""]
    for ms in steps:
        page.clock.run_for(ms)
        seen.append(page.text_content("#lsHeroK") or "")
    pressed = page.evaluate(
        "() => [...document.querySelectorAll('[data-ls-hero]')]"
        ".map(d => d.getAttribute('aria-pressed'))"
    )
    ctx.close()
    return [*(k[:2] for k in seen), ",".join(pressed)]


def test_the_hero_cycles_every_six_and_a_half_seconds(browser: Any, base: str) -> None:
    """The hero holds its first story until 6.5 s have passed, then shows the second, then the
    third, then the first again — and the dots follow it (the handoff's dwell)."""
    story = _hero_story(browser, base, (6400, 200, 6500, 6500), reduced=False)
    assert story == ["01", "01", "02", "03", "01", "true,false,false"], story


def test_reduced_motion_holds_the_hero_still(browser: Any, base: str) -> None:
    """``prefers-reduced-motion``: nothing moves on its own — the first story stays through two
    dwells and more (a dot still picks one)."""
    story = _hero_story(browser, base, (6600, 6500, 9000), reduced=True)
    assert story == ["01", "01", "01", "01", "true,false,false"], story


def test_mutation_a_cycle_deaf_to_reduced_motion_moves(browser: Any) -> None:
    """MUTATION: the launch script served with its reduced-motion test removed (the page's own
    bytes, rewritten in the server's asset table in memory) — the same probe sees the hero move
    under reduced motion."""
    srv = LodestarServer(0, LodestarState(), TODAY)
    data, ct = srv.assets["lodestar_launch.js"]
    anchor = b'window.matchMedia("(prefers-reduced-motion: reduce)").matches'
    assert anchor in data, "the mutation's anchor moved"
    srv.assets["lodestar_launch.js"] = (data.replace(anchor, b"false"), ct)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}"
        story = _hero_story(browser, url, (6600, 6500, 9000), reduced=True)
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)
    assert story[:3] == ["01", "02", "03"], story


def test_the_transit_ends_in_the_studio_and_the_skip_lands_on_the_timeline(
    browser: Any, base: str
) -> None:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(base + "/launch")
    page.wait_for_selector("#lsHeroK:not(:empty)")
    page.click("#lsStarFix")  # reduced motion: the stages step at once, no 4-s wait
    page.wait_for_selector("#lsWelcome:not([hidden])")
    assert page.text_content("#lsSeq") == "STUDIO OPEN"
    assert page.is_hidden("#lsHero") and page.is_hidden("#lsActions")
    done = page.evaluate(
        "() => [...document.querySelectorAll('[data-ls-stage]')].map(n => n.className)"
    )
    assert done[-1].split() == ["ls-stage", "is-active"] and all("is-done" in d for d in done[:-1])
    assert page.locator(".ls-quick").count() == 2
    assert page.evaluate("document.activeElement.id") == "lsEnter"  # focus goes where to go next
    with page.expect_navigation():
        page.click("#lsEnter")
    assert page.url.endswith("/onepager")
    page.goto(base + "/launch")
    page.wait_for_selector("#lsSkip")
    with page.expect_navigation():
        page.click("#lsSkip")
    assert page.url.endswith("/onepager")
    page.goto(base + "/launch")
    page.wait_for_selector("#lsHeroK:not(:empty)")
    with page.expect_navigation():
        page.keyboard.press("Escape")  # Esc skips to the studio too
    assert page.url.endswith("/onepager")
    ctx.close()


def test_the_opt_out_goes_straight_to_the_studio_next_time(browser: Any, base: str) -> None:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(base + "/launch")
    page.wait_for_selector("#lsNeverWrap")
    page.click("#lsNeverWrap")  # the A1 check's label (its box is the visible control)
    assert page.is_checked("#lsNever")
    assert page.evaluate("localStorage.getItem('sf-boot-skip')") == "1"  # v1's key, kept
    page.goto(base + "/launch")
    page.wait_for_url("**/onepager")
    assert page.url.endswith("/onepager")
    page.goto(base + "/launch?replay=1")  # the way back in (the header's ✦ links here)
    page.wait_for_selector("#lsHeroK:not(:empty)")
    assert page.url.endswith("/launch?replay=1")
    assert page.is_checked("#lsNever")  # the box says what is saved
    page.click("#lsNeverWrap")
    assert page.evaluate("localStorage.getItem('sf-boot-skip')") == "0"
    page.goto(base + "/launch")
    page.wait_for_selector("#lsHeroK:not(:empty)")
    assert page.url.endswith("/launch")
    ctx.close()
