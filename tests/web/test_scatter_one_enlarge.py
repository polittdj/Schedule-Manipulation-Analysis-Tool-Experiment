"""ADR-0317 — the /analysis scatter panel carries ONE ⛶, and it provably moves the box.

Round 11's measured defect: the server head's ``data-sf-big`` flipped its label while the panel
stayed ``position:static`` (the ``:has(.sf-tilebox)`` exclusion), beside scatter.js's second,
working sentence-case ⛶ — two glyphs, one inert. Now the chart row's single button carries
``data-sf-big`` (panelkit.js owns the ⛶ ENLARGE / ⛶ SHRINK label + aria-pressed) AND the
original ``tile-expanded`` wiring (the real viewport-overlay geometry) — the exact /curves
mechanism, and the server head emits no ⛶ for this panel at all.

Standing requirement 2: a control must change a MEASURED BOX under a real click — asserted
here per theme AND with scrollbars visible (the ADR-0314 lesson: headless hides them, the
operator's browser does not). Skip posture mirrors the other vendored-chromium suites.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def test_scatter_panel_head_has_no_second_enlarge() -> None:
    """The static half (the r11 guard's former blind spot, closed): the scatter panel's
    SERVER markup carries ⤓ EXCEL but NO data-sf-big — scatter.js supplies the panel's one ⛶
    at runtime. Able to fail: restore ``big=True`` at the call site and this reads the
    duplicate."""
    state = SessionState()
    client = TestClient(create_app(state))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    assert (
        client.post(
            "/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}
        ).status_code
        == 200
    )
    key = next(iter(state.schedules))
    page = client.get(f"/analysis/{quote(key, safe='')}").text
    chunks = [c for c in page.split("<div class=panel") if "id=scatterChart" in c]
    assert len(chunks) == 1, "exactly one panel hosts the scatter chart"
    chunk = chunks[0]
    assert "data-sf-big" not in chunk, "the server head must not carry a second ⛶ (ADR-0317)"
    assert "⤓ EXCEL" in chunk  # the head keeps its real export control
    assert "id=scatterChart" in chunk and "/static/scatter.js" in chunk


@pytest.fixture(scope="module")
def served() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    import uvicorn

    state = SessionState()
    app = create_app(state)
    with TestClient(app) as c:
        data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    key = next(iter(state.schedules))
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", key
    server.should_exit = True


@pytest.mark.parametrize(
    "theme,show_scrollbars",
    [("console", False), ("daylight", False), ("console", True)],
)
def test_the_one_enlarge_moves_the_measured_box(
    served: Any, theme: str, show_scrollbars: bool
) -> None:
    """ONE ⛶ on the scatter panel, and a REAL click changes the tilebox's measured rect
    (tile-expanded = fixed viewport overlay), with panelkit flipping the label to ⛶ SHRINK —
    proving the single button drives BOTH mechanisms. A second click restores the box. The
    scrollbar-visible cell re-measures under the operator's classic-scrollbar geometry."""
    from playwright.sync_api import sync_playwright

    base, key = served
    panel_sel = ".panel:has(#scatterChart)"
    btn_sel = panel_sel + " button[data-sf-big]"
    with sync_playwright() as pw:
        args: dict[str, Any] = dict(chrome_kwargs())
        if show_scrollbars:
            args["ignore_default_args"] = ["--hide-scrollbars"]
        browser = pw.chromium.launch(**args)
        tab = browser.new_page(viewport={"width": 1280, "height": 900})
        # never networkidle on this app: heartbeat.js (3s) / sysmon.js (2s) never settle
        tab.goto(base + "/analysis/" + quote(key, safe=""), wait_until="load")
        tab.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
        tab.wait_for_selector(btn_sel, timeout=25000)  # sfControls runs after the data fetch

        # exactly ONE enlarge glyph anywhere on this panel, wearing the contract label
        glyphs = tab.locator(panel_sel + " button", has_text="⛶")
        assert glyphs.count() == 1, "the panel must carry exactly one ⛶ (ADR-0317)"
        btn = tab.locator(btn_sel)
        assert btn.inner_text() == "⛶ ENLARGE"

        box_sel = panel_sel + " .sf-tilebox"
        before = tab.locator(box_sel).bounding_box()
        assert before is not None and before["width"] > 200

        # a REAL click (daylight's sticky header steals top-of-page clicks — verify the hit)
        btn.scroll_into_view_if_needed()
        hit = tab.evaluate(
            "sel => { const b = document.querySelector(sel);"
            " const r = b.getBoundingClientRect();"
            " const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);"
            " return el === b || b.contains(el); }",
            btn_sel,
        )
        if not hit:  # nudge below the sticky bar and re-verify via the click's own effect
            tab.evaluate("() => window.scrollBy(0, -120)")
        btn.click()
        assert btn.inner_text() == "⛶ SHRINK"  # panelkit's delegated listener ran
        after = tab.locator(box_sel).bounding_box()
        assert after is not None
        # tile-expanded = a fixed viewport overlay (inset 4vh 3vw). Which SIZE axis grows is
        # theme geometry — console's 236px rail makes the overlay much WIDER; daylight's
        # rail-less column is already ~full-width so the box instead grows TALL. Only the
        # scroll-invariant size axes are asserted (bounding_box y is viewport-relative and the
        # click's own scrollIntoView legitimately moves the page). A label-only flip — the
        # round-11 defect — changes neither.
        dw = after["width"] - before["width"]
        dh = after["height"] - before["height"]
        assert dw > 100 or dh > 100, (theme, show_scrollbars, before, after)

        btn.click()  # and the second click restores the measured box (size + column exactly)
        assert btn.inner_text() == "⛶ ENLARGE"
        restored = tab.locator(box_sel).bounding_box()
        assert restored is not None
        for axis in ("width", "height", "x"):
            assert abs(restored[axis] - before[axis]) < 2, (axis, before, restored)
        browser.close()
