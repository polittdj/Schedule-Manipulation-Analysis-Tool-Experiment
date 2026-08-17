"""Why did the focus-shown DCMA tip not appear? — shared diagnostic (BROWSER-ORPHAN-01).

``test_float_tip_dismiss.py`` and ``test_float_tip_scroll.py`` both wait for a focus-shown
``.dcma-tip-float`` and both time out **on a GitHub runner only** (chromium 1234), while passing
on the dev container's vendored chromium 1194. They are two of the tests BROWSER-ORPHAN-01
un-orphaned, so this is the first time either has ever executed on CI — the failure is newly
VISIBLE, not newly caused.

Three hypotheses were measured locally and REFUTED, which is why this file exists instead of a fix:

1. **headless shell vs full chrome** — the runner takes playwright's own resolution, which uses
   ``chrome-headless-shell``; the container pins the full ``chrome`` binary. Pointing the resolver
   at the vendored headless shell locally: both tests still PASS.
2. **the row is not focusable** — ``.dcma-ov-row`` is built with an unconditional ``tabindex="0"``.
3. **``focus()`` scrolls, and the document-level scroll-hide kills the tip it just showed** —
   measured with the row both fully and only partially in view, with and without
   ``preventScroll``: ``window.scrollY`` moved 0px in all four combinations and the tip showed
   in all four.

The remaining difference is the chromium BUILD (1194 vs 1234), which cannot be reproduced in this
container: ``playwright install chromium`` fails because the egress proxy blocks
``cdn.playwright.dev``. Guessing from here would be exactly the "a suggested fix is a hypothesis"
trap, so instead the timeout carries the state that distinguishes the remaining causes — did focus
land on the row, does the row have a box (``placeFloatTip`` returns false for 0x0), how many tips
exist, and what does each one's ``display`` actually say. One CI round then yields the diagnosis.
"""

from __future__ import annotations

from typing import Any

#: The property under test: SOME float tip is displayed. Kept identical to the inline literal both
#: modules already used, so this helper changes the diagnosis, never the verdict.
TIP_VISIBLE = (
    "() => [...document.querySelectorAll('.dcma-tip-float')].some(n => n.style.display === 'block')"
)

#: Everything that distinguishes the surviving causes of "no tip appeared".
_TIP_STATE = """() => {
  const tips = [...document.querySelectorAll('.dcma-tip-float')];
  const ae = document.activeElement;
  const isRow = !!(ae && ae.classList && ae.classList.contains('dcma-ov-row'));
  const r = isRow ? ae.getBoundingClientRect() : null;
  const h = document.querySelector('header');
  const hr = h ? h.getBoundingClientRect() : null;
  return {
    active: ae ? (ae.tagName + '.' + (ae.className || '')).slice(0, 80) : null,
    active_is_a_dcma_row: isRow,
    // placeFloatTip() refuses to show a tip for a row measuring 0x0 — if this is 0x0 the
    // handler ran and DECLINED, which is a different defect from the handler never running.
    focused_row_box: r
      ? [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]
      : null,
    tip_count: tips.length,
    tip_displays: tips.map(n => n.style.display || '(unset)').slice(0, 10),
    any_tip_block: tips.some(n => n.style.display === 'block'),
    scrollY: Math.round(window.scrollY),
    viewport: [document.documentElement.clientWidth, window.innerHeight],
    header: hr ? {right: Math.round(hr.right), bottom: Math.round(hr.bottom)} : null,
  };
}"""


def settle_scroll(page: Any, quiet_ms: int = 120, timeout: int = 2000) -> None:
    """Block until no scroll event has fired for ``quiet_ms`` — the fix for the race above.

    ``scroll_into_view_if_needed()`` delivers its scroll event ASYNCHRONOUSLY, measured at 57-70ms
    after the call returns. Focusing immediately therefore races it, and the loser is the tip: the
    product hides tips on scroll *by design* (the scroll test's own docstring calls that a FACT),
    so a focus-show that lands BEFORE the late scroll event is wiped by it. Waiting for scroll
    quiescence makes the focus-show land after, deterministically.

    Quiescence rather than a flat sleep: the observed delay is machine-dependent, and a constant
    tuned on this container is exactly the kind of timing pin that fails on a slower runner.
    """
    page.evaluate(
        """() => {
          window.__lastScroll = performance.now();
          if (!window.__scrollSettleHooked) {
            window.__scrollSettleHooked = true;
            addEventListener('scroll', () => { window.__lastScroll = performance.now(); }, true);
          }
        }"""
    )
    page.wait_for_function(
        "(q) => performance.now() - (window.__lastScroll || 0) > q",
        arg=quiet_ms,
        timeout=timeout,
    )


def wait_for_tip(page: Any, timeout: int = 4000) -> None:
    """Wait for a focus-shown float tip; on timeout FAIL with the state that explains why.

    Same assertion, same timeout — only the failure message gains evidence. A bare
    ``TimeoutError: Timeout 4000ms exceeded`` says nothing about which of the surviving causes
    fired, and this failure can only be observed on a machine we cannot attach a debugger to.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    try:
        page.wait_for_function(TIP_VISIBLE, timeout=timeout)
    except PlaywrightTimeout:
        raise AssertionError(
            "the focus-shown DCMA float tip never became visible within "
            f"{timeout}ms. State at timeout: {page.evaluate(_TIP_STATE)}"
        ) from None
