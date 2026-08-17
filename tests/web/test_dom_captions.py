"""Decision B1's DOM caption mechanisms, proven where they run (ADR-0326).

Two mechanisms, one voice (`.ch-atd`, `.ch-at`'s DOM sibling):

* **native ``<table><caption>``** — workbench's ribbon and drill grid build one with the table;
* **the ONE SFGantt timescale slot** — ``buildTierScale`` renders a caption row above the tiers
  whenever the served page carries a ``data-ts-caption`` marker; the four Gantt-family
  consumers (/path, /evolution, /driving-path, /sra's SSI grid) are labeled by four one-line
  server opt-ins and ZERO consumer-module edits.

The server half is pinned with a TestClient (the marker is served on exactly the opted-in
pages); the rendered half runs in real chromium (the slot row draws with the token size and
case, sits ABOVE the first tier band instead of overlaying it, and a tier-scale page WITHOUT
the marker — /analysis — renders no slot, guarding against global leakage).

Chromium skips when playwright/the bundled browser are absent, exactly like
``test_axis_titles_visual.py`` (deliberate: Law 1 keeps the runtime stdlib-only).
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.

#: the four pages that opt their timescale headers into the caption slot (app.py's
#: _TS_CAPTION_MARK) — and one tier-scale page that deliberately does NOT (/analysis).
MARKED_PAGES = ("/path", "/evolution", "/driving-path", "/sra")

#: the same four pages as CHROMIUM walks them. Two need real data to draw a timescale at all
#: (measured: without it they render a picker note and NO header, so the slot assertion would
#: be vacuous): /path draws once a session target exists (the fixture sets 143, the golden
#: pair's known target), and /driving-path draws once a trace RESOLVES — 142 → 143 is the
#: pair the server embeds a dpData corridor for (26 → 143, though both are critical, is not
#: a driving trace and the server embeds nothing).
CHROMIUM_URLS = ("/path", "/evolution", "/driving-path?source=142&target=143", "/sra")


def _client_with_goldens() -> TestClient:
    from schedule_forensics.web.app import SessionState, create_app

    c = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
        assert r.status_code == 200, (name, r.status_code)
    return c


def test_the_marker_is_served_on_exactly_the_opted_in_pages() -> None:
    """Server half of the slot mechanism: the four Gantt-family pages carry the marker; the
    home page and /analysis (a tier-scale page whose axis the slot does NOT name) do not."""
    c = _client_with_goldens()
    for route in MARKED_PAGES:
        page = c.get(route)
        assert page.status_code == 200, route
        assert 'data-ts-caption="Schedule dates"' in page.text, f"{route}: marker missing"
    for route in ("/", "/analysis/Project2"):
        page = c.get(route)
        assert page.status_code == 200, route
        assert "data-ts-caption" not in page.text, f"{route}: marker leaked"


def test_workbench_page_still_ships_its_script_and_no_marker() -> None:
    """Workbench's captions are table-native (built by workbench.js), not slot-fed — the page
    must ship the module and must NOT carry the timescale marker."""
    c = _client_with_goldens()
    page = c.get("/workbench")
    assert page.status_code == 200
    assert "/static/workbench.js" in page.text
    assert "data-ts-caption" not in page.text


# ── the rendered half (real chromium) ──────────────────────────────────────────────────────

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")


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
    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
            assert r.status_code == 200, (name, r.status_code)
        # /path and /driving-path draw their Gantt tables only once a session target exists
        # (measured: without one they render a "no session target" note and NO timescale, so
        # the slot assertion would be vacuous there). 143 is the golden pair's known target
        # (test_target_and_theme.py).
        r = c.post("/target", data={"uid": "143", "next_url": "/"}, follow_redirects=False)
        assert r.status_code in (200, 303), r.status_code

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


_SLOT_PROBE = """() => {
  const cap = document.querySelector('.g-tscap.ch-atd');
  if (!cap) return null;
  const r = cap.getBoundingClientRect(), cs = getComputedStyle(cap);
  const tier = cap.parentElement.querySelector('.g-tier');
  const tr = tier ? tier.getBoundingClientRect() : null;
  return {text: cap.textContent, w: Math.round(r.width), h: Math.round(r.height),
          fs: cs.fontSize, tt: cs.textTransform,
          capBottom: Math.round(r.bottom), tierTop: tr ? Math.round(tr.top) : null};
}"""

_TABLE_PROBE = """() => {
  const cap = document.querySelector('table.wb-matrix caption.ch-atd');
  if (!cap) return null;
  const r = cap.getBoundingClientRect(), cs = getComputedStyle(cap);
  return {text: cap.textContent, w: Math.round(r.width), h: Math.round(r.height),
          fs: cs.fontSize, tt: cs.textTransform};
}"""


def test_the_slot_and_the_table_caption_render_for_real(served: str) -> None:
    """The whole mechanism, measured: the slot renders on all four opted-in pages with the
    token size and case and ABOVE the tier bands; workbench's ribbon caption renders with the
    same voice; /analysis (tier scale, no marker) renders NO slot."""
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1600, "height": 1100})

        for route in CHROMIUM_URLS:
            page.goto(served + route, wait_until="domcontentloaded")
            try:
                page.wait_for_selector(".g-tscap.ch-atd", timeout=8000, state="attached")
            except Exception:
                problems.append(f"{route}: slot never rendered")
                continue
            page.wait_for_timeout(120)
            cap = page.evaluate(_SLOT_PROBE)
            if not cap:
                problems.append(f"{route}: slot missing at probe time")
                continue
            if cap["text"] != "Schedule dates":
                problems.append(f"{route}: slot text {cap['text']!r}")
            if cap["w"] <= 0 or cap["h"] <= 0:
                problems.append(f"{route}: zero-size slot box")
            if abs(float(cap["fs"].removesuffix("px")) - 11.0) > 0.2:
                problems.append(f"{route}: font-size {cap['fs']}, want 11px")
            if cap["tt"] != "uppercase":
                problems.append(f"{route}: text-transform={cap['tt']}")
            # its own row, never an overlay: the caption box ends before the first tier begins
            if cap["tierTop"] is not None and cap["capBottom"] > cap["tierTop"] + 1:
                problems.append(
                    f"{route}: slot overlaps the tiers (capBottom {cap['capBottom']} > "
                    f"tierTop {cap['tierTop']})"
                )

        # workbench: the native table caption, same voice
        page.goto(served + "/workbench", wait_until="domcontentloaded")
        try:
            page.wait_for_selector("table.wb-matrix caption.ch-atd", timeout=8000)
            page.wait_for_timeout(120)
            cap = page.evaluate(_TABLE_PROBE)
            if not cap:
                problems.append("/workbench: ribbon caption missing at probe time")
            else:
                if cap["w"] <= 0 or cap["h"] <= 0:
                    problems.append("/workbench: zero-size caption box")
                if abs(float(cap["fs"].removesuffix("px")) - 11.0) > 0.2:
                    problems.append(f"/workbench: font-size {cap['fs']}, want 11px")
                if cap["tt"] != "uppercase":
                    problems.append(f"/workbench: text-transform={cap['tt']}")
        except Exception:
            problems.append("/workbench: ribbon caption never rendered")

        # the negative control: a tier-scale page WITHOUT the marker renders no slot
        page.goto(served + "/analysis/Project2", wait_until="domcontentloaded")
        try:
            page.wait_for_selector(".g-scale-tiered", timeout=8000, state="attached")
        except Exception:
            problems.append("/analysis: tier scale itself never rendered (control is vacuous)")
        if page.evaluate("() => !!document.querySelector('.g-tscap')"):
            problems.append("/analysis: slot leaked onto an un-marked page")

        browser.close()

    assert not problems, f"{len(problems)} DOM-caption problem(s):\n  " + "\n  ".join(problems)
