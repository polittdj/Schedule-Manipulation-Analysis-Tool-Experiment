"""OR-03 (ADR-0328) behavioral half — the Boot Audio Hum + launch motion under real Chromium.

What only a real browser can prove (the content half is ``test_launch_sequence.py``):

1. **No AudioContext exists before a genuine gesture** — loading the page creates nothing, and a
   PROGRAMMATIC file change (no click, no drop) runs a fully silent load: the change handler must
   never prime, because browsers may not treat ``change`` as user activation.
2. **A genuine gesture primes exactly one context**, the hum's state machine runs for the whole
   (held) load, the launch motion is measurably moving while it runs, and the load then completes.
3. **fadeOut() resolves fast and is CAPPED** — even ``fadeOut(99999)`` returns in well under a
   second, so the pre-navigation fade can never hold a redirect hostage.
4. **Mute persists** across the navigation and a reload (localStorage, house pattern), volume
   persists too, and moving the volume unmutes.
5. **Geometry**: the card's controls and orbit sit inside the card, non-overlapping, in all four
   themes at two viewports — with scrollbars VISIBLE (the ADR-0314 lesson: headless hides them,
   the operator's browser does not).

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this module (ADR-0418) (same posture as
``test_float_tip_dismiss.py`` — the runtime stays stdlib-only, Law 1).
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
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.

pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")

#: Counts real AudioContext constructions — the wrapper delegates to the native constructor, so
#: the app still gets a working context while the test sees every creation.
COUNT_AC = """
window.__sfAC = 0;
['AudioContext', 'webkitAudioContext'].forEach(function (k) {
  var Native = window[k];
  if (!Native) return;
  function Counted() { window.__sfAC++; return new Native(); }
  Counted.prototype = Native.prototype;
  window[k] = Counted;
});
"""

GOLDEN_FILE = {
    "name": "Project2.mspdi.xml",
    "mimeType": "text/xml",
    "buffer": (GOLDEN / "Project2.mspdi.xml").read_bytes(),
}

#: The served app is MODULE-scoped, so a test that lets its upload COMPLETE must use bytes no
#: earlier test loaded — a byte-identical re-upload is deduped (ADR-0259) and redirects home,
#: not to /analysis/... (the first run of this suite failed exactly that way).
GOLDEN_FILE_2 = {
    "name": "Project5.mspdi.xml",
    "mimeType": "text/xml",
    "buffer": (GOLDEN / "Project5.mspdi.xml").read_bytes(),
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


def _hold_uploads(page: Any) -> list[Any]:
    """Park every /upload POST unresolved so the load phase stays open until the test decides.

    The handler only STORES the route (deferred resolution) — never sleeps, because sync-API
    route handlers run on the event loop and a sleep there would freeze the page's own waits.
    """
    held: list[Any] = []
    page.route("**/upload", lambda route: held.append(route))
    return held


def test_no_context_before_a_gesture_and_a_programmatic_change_stays_silent(served: str) -> None:
    """Page load creates no AudioContext, and a load driven by a PROGRAMMATIC input change (no
    click, no drop — exactly the case the plan excludes from priming) runs silent end to end,
    with the overlay and motion still doing their job."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(COUNT_AC)
        page.goto(served + "/", wait_until="load")
        assert page.evaluate("() => window.__sfAC") == 0  # nothing primed by page load

        held = _hold_uploads(page)
        page.set_input_files("#fileInput", files=[GOLDEN_FILE])  # change WITHOUT any gesture
        page.wait_for_selector("#loadOverlay", state="visible", timeout=10000)
        # the load phase is open (the POST is parked) — still no context, hum still idle
        assert page.evaluate("() => window.__sfAC") == 0
        assert page.evaluate("() => window.SFLaunchAudio.state()") == "idle"
        held[0].continue_()  # release the POST: the silent load must still complete
        page.wait_for_url("**/analysis/**", timeout=30000)
        browser.close()


def test_a_gesture_primes_once_hum_spans_the_held_load_and_motion_moves(served: str) -> None:
    """The real operator flow: click "choose files" (a genuine gesture — the context is born
    there, exactly once), pick a file, and while the POST is held open the hum state machine is
    RUNNING and an orbit dot's computed transform measurably changes between two samples —
    "something flying around", not a frozen frame. Releasing the POST lands the report."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(COUNT_AC)
        page.goto(served + "/", wait_until="load")
        held = _hold_uploads(page)

        with page.expect_file_chooser() as fc_info:
            page.click("#pickBtn")
        assert page.evaluate("() => window.__sfAC") == 1  # the click primed exactly one context
        fc_info.value.set_files([GOLDEN_FILE_2])  # bytes the module has NOT loaded yet

        page.wait_for_selector("#loadOverlay", state="visible", timeout=10000)
        page.wait_for_function(
            "() => window.SFLaunchAudio && window.SFLaunchAudio.state() === 'running'",
            timeout=5000,
        )
        assert page.evaluate("() => window.__sfAC") == 1  # start() reuses the primed context

        # the launch motion is really moving: two samples of an orbit dot's transform differ
        orbit = page.locator(".load-orbit").bounding_box()
        assert orbit is not None and orbit["width"] > 60
        sample = "() => getComputedStyle(document.querySelector('.orbit-a')).transform"
        t1 = page.evaluate(sample)
        page.wait_for_timeout(300)
        t2 = page.evaluate(sample)
        assert t1 and t2 and t1 != t2, "the orbit dot did not move between samples"

        held[0].continue_()  # the hum fades (<=200ms) and the client navigates itself
        page.wait_for_url("**/analysis/**", timeout=30000)
        browser.close()


def test_fadeout_resolves_fast_even_when_asked_to_fade_forever(served: str) -> None:
    """The 200ms cap, behavioral: after a real gesture primes the context, ``fadeOut(99999)``
    still resolves in well under a second (uncapped it would take 100 seconds) and closes the
    machine; a NEW load then needs a NEW gesture-primed context."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(COUNT_AC)
        page.goto(served + "/", wait_until="load")

        with page.expect_file_chooser():
            page.click("#pickBtn")  # prime (the chooser is simply never fed)
        assert page.evaluate("() => window.__sfAC") == 1
        page.evaluate("() => window.SFLaunchAudio.start()")
        assert page.evaluate("() => window.SFLaunchAudio.state()") == "running"

        t0 = time.monotonic()
        page.evaluate("() => window.SFLaunchAudio.fadeOut(99999)")  # evaluate awaits the promise
        elapsed = time.monotonic() - t0
        assert elapsed < 1.5, f"fadeOut must be capped at 200ms — took {elapsed:.2f}s"
        assert page.evaluate("() => window.SFLaunchAudio.state()") == "closed"

        # closed means closed: a fresh gesture builds a fresh context (no zombie reuse)
        with page.expect_file_chooser():
            page.click("#pickBtn")
        assert page.evaluate("() => window.__sfAC") == 2
        browser.close()


def test_mute_and_volume_persist_across_navigation_and_reload(served: str) -> None:
    """The plan row's named requirement: mute set DURING a load survives the navigation and a
    reload (sf-hum-mute), the slider persists too (sf-hum-vol), and moving the volume unmutes."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(served + "/", wait_until="load")
        page.evaluate("() => localStorage.clear()")  # a clean slate for the persistence claims
        held = _hold_uploads(page)

        with page.expect_file_chooser() as fc_info:
            page.click("#pickBtn")
        fc_info.value.set_files([GOLDEN_FILE])
        page.wait_for_selector("#loadOverlay", state="visible", timeout=10000)

        mute = page.locator("#humMute")
        assert mute.get_attribute("aria-pressed") == "false"
        mute.click()
        assert mute.get_attribute("aria-pressed") == "true"
        assert mute.inner_text() == "♪ MUTED"
        assert page.evaluate("() => localStorage.getItem('sf-hum-mute')") == "1"

        # end the load benignly (redirect home) — the choice must survive the navigation
        held[0].fulfill(status=200, content_type="application/json", body='{"redirect": "/"}')
        page.wait_for_url(served + "/", timeout=15000)
        assert page.locator("#humMute").get_attribute("aria-pressed") == "true"
        assert page.evaluate("() => window.SFLaunchAudio.muted()") is True

        # volume: input persists and unmutes (OS convention)
        page.locator("#humVol").evaluate(
            "el => { el.value = '70'; el.dispatchEvent(new Event('input')); }"
        )
        assert page.evaluate("() => localStorage.getItem('sf-hum-vol')") == "70"
        assert page.evaluate("() => localStorage.getItem('sf-hum-mute')") == "0"
        page.reload(wait_until="load")
        assert page.locator("#humVol").input_value() == "70"
        assert page.locator("#humMute").get_attribute("aria-pressed") == "false"
        browser.close()


@pytest.mark.parametrize("width,height", [(1280, 800), (860, 560)])
def test_card_geometry_in_all_four_themes_scrollbars_visible(
    served: str, width: int, height: int
) -> None:
    """The overlay card holds together everywhere the operator can put it: in console, daylight,
    apollo and jarvis, at a wide and a small viewport, with classic scrollbars visible, the
    orbit and both hum controls sit INSIDE the card and the controls do not overlap."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs(), ignore_default_args=["--hide-scrollbars"])
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(served + "/", wait_until="load")
        _hold_uploads(page)  # never released: the overlay stays up for every theme
        page.set_input_files("#fileInput", files=[GOLDEN_FILE])
        page.wait_for_selector("#loadOverlay", state="visible", timeout=10000)

        for theme in ("console", "daylight", "apollo", "jarvis"):
            page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
            card = page.locator(".load-card").bounding_box()
            assert card is not None and card["width"] > 200, (theme, width)
            boxes = {}
            for name, sel in (("orbit", ".load-orbit"), ("mute", "#humMute"), ("vol", "#humVol")):
                box = page.locator(sel).bounding_box()
                assert box is not None and box["width"] > 0, (theme, width, name)
                assert box["x"] >= card["x"] - 1 and box["y"] >= card["y"] - 1, (
                    theme,
                    width,
                    name,
                    box,
                    card,
                )
                assert box["x"] + box["width"] <= card["x"] + card["width"] + 1, (
                    theme,
                    width,
                    name,
                    box,
                    card,
                )
                assert box["y"] + box["height"] <= card["y"] + card["height"] + 1, (
                    theme,
                    width,
                    name,
                    box,
                    card,
                )
                boxes[name] = box
            m, v = boxes["mute"], boxes["vol"]
            overlap = not (
                m["x"] + m["width"] <= v["x"]
                or v["x"] + v["width"] <= m["x"]
                or m["y"] + m["height"] <= v["y"]
                or v["y"] + v["height"] <= m["y"]
            )
            assert not overlap, f"mute and volume overlap in {theme} at {width}x{height}"
        browser.close()
