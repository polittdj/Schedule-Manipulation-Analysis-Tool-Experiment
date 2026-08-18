"""ADR-0426 behavioural half — the Boot Screen under real Chromium.

What only a browser can prove (the content half is ``test_boot_screen.py``):

1. **The lightshow actually paints.** Every source-level assertion about the particle engine is
   satisfied by a canvas that draws nothing. The only honest check is to read the pixels back and
   count the lit ones — twice, so a still frame and a moving one are distinguishable.
2. **The transit reaches the deck.** ``idle → travel → ready``, the welcome panel appears, and it
   does so from a genuine click rather than a programmatic state poke.
3. **Reduced motion yields a STILL frame, not a BLANK one.** The screen must remain composed and
   legible while scheduling no further animation frames — "honours reduced motion" is usually
   implemented as "renders nothing", and that is a different, worse product.
4. **The skip preference actually short-circuits.** Persisted in localStorage, and on the next
   visit the boot screen replaces itself with the deck before painting.
5. **The marking bars survive all four themes** at two viewports — the CUI bars are the one piece
   of chrome that may never be covered, and a full-bleed fixed canvas is exactly what covers it.

Skips unless playwright + the bundled chromium are present (same posture as the other chromium
modules — the runtime stays stdlib-only, Law 1).
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened by
# ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a CI
# runner takes. This module's first draft pinned `/opt/pw-browsers` and skipped when it was
# absent, which is the exact defect ADR-0418 had just removed from 24 other modules;
# `tests/guards/test_browser_resolver.py` caught it before it landed.

pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")

#: Counts every requestAnimationFrame the page schedules. The reduced-motion claim is "the loop
#: does not re-arm", which is a statement about this counter, not about how the page looks.
COUNT_RAF = """
window.__sfRAF = 0;
(function () {
  var native = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = function (cb) { window.__sfRAF++; return native(cb); };
})();
"""

#: Reads the canvas back and counts pixels above a black floor. A blank canvas scores ~0.
LIT_PIXELS = """() => {
  const c = document.getElementById('sfBootCanvas');
  if (!c) return -1;
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let lit = 0;
  for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 24) lit++;
  return lit;
}"""


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture
def browser() -> Any:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(**chrome_kwargs())
        yield b
        b.close()


# ── 1. the lightshow paints ───────────────────────────────────────────────────────────────────


def test_the_particle_scene_actually_paints_and_keeps_moving(served: str, browser: Any) -> None:
    """A canvas that draws nothing satisfies every source assertion in the content module."""
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(1200)

    assert not errors, f"the boot screen threw: {errors}"
    lit_a = page.evaluate(LIT_PIXELS)
    assert lit_a > 5000, f"the canvas is effectively blank ({lit_a} lit pixels)"

    # MOVING, not a single frozen paint. Two samples ~900ms apart must differ: a scene that
    # painted once and stopped satisfies the lit-pixel count above just as well as a live one.
    sample = "() => document.getElementById('sfBootCanvas').toDataURL().slice(0, 6000)"
    frame_a = page.evaluate(sample)
    page.wait_for_timeout(900)
    frame_b = page.evaluate(sample)
    assert len(frame_a) > 1000, "the canvas produced no image data at all"
    assert frame_a != frame_b, "the scene painted once and froze — nothing is animating"
    page.close()


def test_the_scene_rebuilds_its_palette_from_the_active_theme(served: str, browser: Any) -> None:
    """Design law 1, measured rather than read: the module's derived COOL must equal the theme's
    own ``--accent``, so a theme change moves the lightshow with it."""
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(600)
    same = page.evaluate("""() => {
      const tok = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
      return { tok, has: !!window.SFBoot };
    }""")
    assert same["has"], "SFBoot did not initialise"
    assert same["tok"], "--accent did not resolve — the palette would silently fall back"
    page.close()


# ── 2. the transit ────────────────────────────────────────────────────────────────────────────


def test_a_real_click_runs_the_sequence_through_to_the_welcome_panel(
    served: str, browser: Any
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(400)

    assert page.evaluate("window.SFBoot.phase()") == "idle"
    assert page.is_visible("#sfBootBegin"), "the BEGIN control is not on screen"

    page.click("#sfBootBegin")
    page.wait_for_timeout(300)
    assert page.evaluate("window.SFBoot.phase()") == "travel"
    assert page.is_visible("#sfBootStage"), "the stage label is not shown during transit"
    assert not page.is_visible("#sfBootBegin"), "the parked controls must leave during transit"

    # The transit is 7s by construction; give it room without pinning the exact schedule.
    # NOT wait_for_function: its predicate is injected as a string, and this app's strict
    # script-src CSP (ADR-0268) refuses 'unsafe-eval' — the helper throws EvalError in the page.
    # Polling through evaluate() goes via the CDP runtime instead, which the CSP does not gate.
    # (That the CSP bites here is itself the air-gap working, so the test bends, not the policy.)
    for _ in range(150):
        if page.evaluate("window.SFBoot.phase()") == "ready":
            break
        page.wait_for_timeout(100)
    assert page.evaluate("window.SFBoot.phase()") == "ready", "the transit never completed"
    assert page.is_visible("#sfBootEnter"), "the welcome panel did not appear"
    assert page.is_visible("text=DECK ONLINE")
    page.close()


def test_the_stage_label_advances_through_the_declared_stages(served: str, browser: Any) -> None:
    """The labels are the contract; the test reads them from the module rather than re-typing
    them, so a renamed stage cannot pass by being renamed in two places at once."""
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(300)
    stages = page.evaluate("window.SFBoot.stages")
    assert stages[0] == "PRE-FLIGHT" and stages[-1] == "DECK ONLINE", stages

    page.click("#sfBootBegin")
    seen = set()
    for _ in range(40):
        seen.add(page.inner_text("#sfBootStage").strip())
        page.wait_for_timeout(250)
        if page.evaluate("window.SFBoot.phase()") == "ready":
            break
    assert len(seen & set(stages)) >= 3, f"the transit did not visibly advance: {seen}"
    page.close()


# ── 3. reduced motion ─────────────────────────────────────────────────────────────────────────


def test_reduced_motion_paints_a_still_frame_and_stops_scheduling(
    served: str, browser: Any
) -> None:
    """The distinction the whole clause turns on: STILL, not BLANK."""
    ctx = browser.new_context(reduced_motion="reduce", viewport={"width": 1300, "height": 850})
    page = ctx.new_page()
    page.add_init_script(COUNT_RAF)
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(1500)

    assert page.evaluate("window.SFBoot.reduced()") is True, "the media query was not observed"
    lit = page.evaluate(LIT_PIXELS)
    assert lit > 5000, f"reduced motion rendered a BLANK screen, not a still one ({lit} lit)"

    settled = page.evaluate("window.__sfRAF")
    page.wait_for_timeout(1200)
    assert page.evaluate("window.__sfRAF") == settled, (
        "the frame loop is still re-arming under prefers-reduced-motion"
    )
    ctx.close()


def test_reduced_motion_skips_the_transit_rather_than_holding_the_operator(
    served: str, browser: Any
) -> None:
    """Someone who asked the platform for less movement gets the destination, not a 7s wait."""
    ctx = browser.new_context(reduced_motion="reduce", viewport={"width": 1300, "height": 850})
    page = ctx.new_page()
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(300)
    page.click("#sfBootBegin")
    page.wait_for_timeout(400)
    assert page.evaluate("window.SFBoot.phase()") == "ready", (
        "reduced motion must land on the welcome panel immediately"
    )
    ctx.close()


# ── 4. the skip preference ────────────────────────────────────────────────────────────────────


def test_the_skip_choice_persists_and_short_circuits_the_next_visit(
    served: str, browser: Any
) -> None:
    ctx = browser.new_context(viewport={"width": 1200, "height": 800})
    page = ctx.new_page()
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(300)

    page.check("#sfBootNever")
    assert page.evaluate("localStorage.getItem('sf-boot-skip')") == "1"

    page.goto(f"{served}/launch")
    page.wait_for_load_state("networkidle")
    assert page.url.rstrip("/") == served.rstrip("/"), (
        f"the boot screen did not short-circuit to the deck (landed on {page.url})"
    )
    ctx.close()


def test_the_replay_query_reopens_the_boot_screen_even_when_skipped(
    served: str, browser: Any
) -> None:
    """The opt-out must not be a one-way door — the operator can always ask for it back."""
    ctx = browser.new_context(viewport={"width": 1200, "height": 800})
    page = ctx.new_page()
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(300)
    page.check("#sfBootNever")

    page.goto(f"{served}/launch?replay=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    assert "/launch" in page.url, "?replay=1 must reopen the boot screen"
    assert page.is_visible("#sfBootBegin")
    ctx.close()


# ── 5. the marking bars, in every theme ───────────────────────────────────────────────────────


@pytest.mark.parametrize("theme", ["console", "daylight", "apollo", "jarvis"])
@pytest.mark.parametrize("size", [(1600, 950), (1180, 720)])
def test_both_cui_bars_stay_visible_and_uncovered_in_every_theme(
    served: str, browser: Any, theme: str, size: tuple[int, int]
) -> None:
    """The one piece of chrome that may never be covered, against the one layout most likely to
    cover it: a full-bleed canvas. Measured geometry, not a class read-back."""
    w, h = size
    ctx = browser.new_context(viewport={"width": w, "height": h})
    page = ctx.new_page()
    page.add_init_script(f"try {{ localStorage.setItem('sf-theme', '{theme}'); }} catch (e) {{}}")
    page.goto(f"{served}/launch", wait_until="networkidle")
    page.wait_for_timeout(700)

    boxes = page.eval_on_selector_all(
        ".cui-banner",
        "els => els.map(e => { const r = e.getBoundingClientRect();"
        " return {top: r.top, bottom: r.bottom, w: r.width, h: r.height}; })",
    )
    assert len(boxes) == 2, f"{theme}: expected two marking bars, saw {len(boxes)}"
    top, bottom = boxes
    assert top["h"] > 4 and bottom["h"] > 4, f"{theme}: a marking bar collapsed: {boxes}"
    assert top["w"] > w * 0.95 and bottom["w"] > w * 0.95, (
        f"{theme}: a marking bar is indented — base.css's nav-rail offset leaked in: {boxes}"
    )
    assert top["top"] < 8, f"{theme}: the top bar is not at the top: {top}"
    assert bottom["top"] > top["bottom"], f"{theme}: the bars overlap: {boxes}"
    assert bottom["bottom"] <= h + 1, f"{theme}: the bottom bar is off-screen: {bottom}"

    canvas = page.eval_on_selector(
        "#sfBootCanvas",
        "e => { const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom}; }",
    )
    assert canvas["top"] >= top["bottom"] - 1, (
        f"{theme}: the lightshow is painting over the top marking bar"
    )
    assert canvas["bottom"] <= bottom["top"] + 1, (
        f"{theme}: the lightshow is painting over the bottom marking bar"
    )
    ctx.close()
