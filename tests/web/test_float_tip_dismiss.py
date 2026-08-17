"""The DCMA overview float tip must be dismissable, and must never cover the nav (OR-02).

Operator report, 2026-07-28: *"I keep getting this weird call-out that covers the menu bar on
the left side of the screen that I can't get to go away unless I switch to another page but then
it will return. It is the DCMA 11 — Missed Activities call-out."*

Two separate defects were MEASURED behind that one sentence (2026-07-30), and this module pins
both shut. Neither is a class read-back — every assertion is a box or a rendered style, per
ADR-0304.

**1. It could not be dismissed.** ``.dcma-tip-float`` is ``pointer-events:none``, so a tip can
never receive its own ``mouseleave``; every hide has to be driven from elsewhere. The only paths
were the anchor row's ``mouseleave``, its ``blur``, and any scroll — and a tip shown by FOCUS
(what a click or a tap on a ``tabindex=0`` row does) is reachable by neither of the first two:
the pointer was never over the row, and focus stays put. Measured before the fix, of six
dismissals a real operator would try, three STUCK::

    STICKS :: Escape key            HIDES :: click elsewhere
    STICKS :: move the mouse away   HIDES :: scroll
    STICKS :: window blur/alt-tab   HIDES :: anchor row removed

**2. It painted over the daylight nav.** The placement guard asked for
``getComputedStyle(header).position === "fixed"`` — true for console/apollo/jarvis, whose header
is a 236px left rail at >=761px, but daylight's full-width top bar is ``sticky``, so the clamp
was skipped entirely. With hit-checked hovers (a row Playwright refuses to hover is a row no
operator can trigger, so it is excluded honestly) the callout overlapped the daylight header at
1280x520, 1280x800 AND 1440x600, while no fixed-rail view overlapped at any size.

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this module (ADR-0418) (same posture as
``test_float_tip_scroll.py`` — the runtime stays stdlib-only, Law 1)::

    pip install playwright
    python -m pytest tests/web/test_float_tip_dismiss.py -q -s
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs
from web.tip_probe import settle_scroll, wait_for_tip

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

TIP_VISIBLE = (
    "() => [...document.querySelectorAll('.dcma-tip-float')].some(n => n.style.display === 'block')"
)

# The tip's box against the header's box — the whole question OR-02 asks, in one expression.
# The z-index 10000 tip paints over ANY header, fixed, sticky, or in-flow — so the assertion is
# purely geometric: whenever the header has an on-screen box, the tip must not intersect it.
OVERLAPS_HEADER = """() => {
  const tip = [...document.querySelectorAll('.dcma-tip-float')]
    .find(n => n.style.display === 'block');
  const h = document.querySelector('header');
  if (!tip || !h) return false;
  const t = tip.getBoundingClientRect(), r = h.getBoundingClientRect();
  if (r.bottom <= 0 || r.width === 0) return false;  // scrolled away / not rendered
  return !(t.right <= r.left || t.left >= r.right || t.bottom <= r.top || t.top >= r.bottom);
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
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        payload = (GOLDEN / "Project2.mspdi.xml").read_bytes()
        r = c.post("/upload", files={"files": ("Project2.mspdi.xml", payload, "text/xml")})
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


def _show_by_focus(page: Any, row: Any) -> None:
    """Show the tip the way a click or a tap does — focus, no pointer involved."""
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.evaluate(
        "() => [...document.querySelectorAll('.dcma-tip-float')]"
        ".forEach(n => n.style.display='none')"
    )
    row.scroll_into_view_if_needed()
    settle_scroll(page)  # the scroll lands async and would hide the tip focus is about to show
    row.focus()
    wait_for_tip(page)


def test_the_dcma11_callout_can_be_dismissed_every_way_an_operator_would_try(served: str) -> None:
    """The operator's sentence, executable: it must GO AWAY.

    Escape, moving the pointer off the row, and leaving the window each hide a focus-shown tip.
    Before the fix all three stuck — the operator's "I can't get [it] to go away".
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(served + "/analysis/Project2", wait_until="domcontentloaded")
        page.wait_for_selector(".dcma-ov-row", timeout=15000)

        # the operator's own callout, by name — not just "some row"
        row = page.locator(".dcma-ov-row", has_text="Missed Activities").first
        assert row.count() > 0, "no DCMA 11 — Missed Activities row to test"

        _show_by_focus(page, row)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        assert not page.evaluate(TIP_VISIBLE), "Escape did not dismiss the callout"

        # Pointer-away: derive the away-point from the row's MEASURED box (a fixed magic
        # coordinate sat 7px under the row and would silently land back on it if the panel ever
        # reflows). Two moves, because the dismissal deliberately requires >8px of real travel —
        # a 1px desk-bump must NOT kill a keyboard-opened tip (jitter threshold, ADR-0314).
        _show_by_focus(page, row)
        box = row.bounding_box()
        ax = min(box["x"] + box["width"] + 160, 1270)
        ay = min(box["y"] + box["height"] + 160, 790)
        page.mouse.move(ax, ay)
        page.mouse.move(ax + 12, ay + 12)
        page.wait_for_timeout(150)
        assert not page.evaluate(TIP_VISIBLE), "moving the pointer away did not dismiss the callout"

        _show_by_focus(page, row)
        page.evaluate("() => window.dispatchEvent(new Event('blur'))")
        page.wait_for_timeout(150)
        assert not page.evaluate(TIP_VISIBLE), "leaving the window did not dismiss the callout"

        browser.close()


def test_the_tips_are_born_hidden(served: str) -> None:
    """Every float tip must carry display:none from CREATION, before any scroll or hover.

    ``.dcma-tip-float`` CSS computes visible (it opts out of the CSS hover-gating), so a tip
    created without an inline ``display:none`` paints at the viewport's (0,0) — all 16 stacked
    over the nav — until the first scroll hides them. Loads WITH an auto-scroll (the Gantt's
    scroll-to-data-date) masked that; loads without one kept the stack: the operator's "it
    returns after I switch pages". This pins the invariant the fix restores: born hidden, shown
    only by hover-intent or focus.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        # Record each tip's inline display AT INSERTION (microtask — before any scroll event can
        # run): the scroll-hide handler ALSO writes display:none, so inspecting after load could
        # not tell "born hidden" from "hidden by the masking auto-scroll" — the exact ambiguity
        # that hid this bug in the first place.
        page.add_init_script(
            """
            window.__tipBirth = [];
            new MutationObserver((records) => {
              for (const r of records) for (const n of r.addedNodes) {
                if (n.nodeType === 1 && n.classList && n.classList.contains('dcma-tip-float'))
                  window.__tipBirth.push(n.style.display);
              }
            }).observe(document, {childList: true, subtree: true});
            """
        )
        page.goto(served + "/analysis/Project2", wait_until="domcontentloaded")
        page.wait_for_selector(".dcma-tip-float", timeout=15000, state="attached")
        births = page.evaluate("() => window.__tipBirth")
        assert births, "no float tip insertion observed — probe proved nothing"
        unhidden = [b for b in births if b != "none"]
        assert not unhidden, (
            f"{len(unhidden)} of {len(births)} tips inserted VISIBLE "
            f"(inline display {unhidden[:3]!r})"
        )
        browser.close()


@pytest.mark.parametrize("theme", ["console", "daylight", "apollo", "jarvis"])
@pytest.mark.parametrize("size", [(1280, 520), (1280, 800), (1440, 600), (600, 700)])
def test_the_callout_never_paints_over_the_nav_in_any_theme(
    served: str, theme: str, size: tuple[int, int]
) -> None:
    """A help affordance must never trap the primary navigation — in ANY of the four views.

    daylight is the one this bites: its header is ``sticky``, not ``fixed``, so the old guard
    skipped it and the callout landed on the nav at the three wide sizes. The 600x700 cell
    exercises the <=761px in-flow burger header, which the clamp also clears while it is on
    screen (the shape test is the header's measured box, not its position).
    """
    from playwright.sync_api import sync_playwright

    width, height = size
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(served + "/analysis/Project2", wait_until="domcontentloaded")
        page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
        page.wait_for_selector(".dcma-ov-row", timeout=15000)

        rows = page.locator(".dcma-ov-row")
        measured = 0
        for i in range(rows.count()):
            row = rows.nth(i)
            try:
                # a hit-target-checked hover: a row that cannot be hovered is a row no operator
                # can trigger, so it is excluded rather than counted as a pass.
                row.hover(timeout=1500)
            except Exception:
                continue
            page.wait_for_timeout(60)
            row.focus()  # focus shows immediately — no hover-intent wait needed
            page.wait_for_timeout(80)
            if not page.evaluate(TIP_VISIBLE):
                continue
            # count only rows whose tip was actually MEASURED — counting hovered rows let the
            # whole cell pass vacuously if a regression stopped tips from showing at all.
            measured += 1
            assert not page.evaluate(OVERLAPS_HEADER), (
                f"{theme} {width}x{height}: the DCMA callout painted over the nav "
                f"(row {i}: {row.locator('.dcma-ov-name').inner_text()})"
            )
        assert measured, f"{theme} {width}x{height}: no tip measured — probe proved nothing"
        browser.close()
