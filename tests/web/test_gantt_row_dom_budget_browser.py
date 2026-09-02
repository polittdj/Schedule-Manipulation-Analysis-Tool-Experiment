"""Every Gantt row must carry a FIXED, small number of DOM nodes — gridlines and holiday shading
are shared backgrounds, never per-row <div>s.

Operator 2026-09-02: "the program is running like shit … TERRIBLE lag when you switch pages or
even scroll." Measured on the operator-scale reference IMS (2,125 rows, 12.3 years, one file) on
the pre-fix tree, /analysis: **1,801,557 DOM nodes** — 1,578,875 of them `.g-grid` gridline divs
(743 per row: every year/quarter/month/week boundary re-painted as a <div> inside every track)
and 170,927 `.g-nonwork-holiday` divs (80 per row); a 26,386 ms synchronous rebuild on one zoom
step; scrolling at p50 200 ms/frame (5 fps) while every other page held 17 ms. Server TTFB for
the same page was 388 ms — the lag was entirely the DOM.

The fix paints one SVG data-URI background per gridline set (SFGantt.paintGrid) and one per
calendar's holidays (SFTimescale.decorateCell), shared by every row through a generated
stylesheet rule. These tests pin the budget by RENDERED DOM, not by reading the source: a row
may not exceed ROW_BUDGET nodes, no per-row gridline/holiday divs may exist, and the gridlines
must still be there (as a background image), on both HTML-Gantt families (/analysis and /path).
FAIL-side tests were observed RED on the pre-fix tree (TP5: 213 `.g-grid` per row on /analysis).
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
FIXTURE = REPO / "tests" / "fixtures" / "test_projects" / "TP5_LongSpan_Synthetic.xml"
KEY = "TP5_LongSpan_Synthetic"
#: a calendar WITH holiday exceptions (TP5 has none) — exercises the holiday-layer branch
HOLIDAY_FIXTURE = REPO / "tests" / "fixtures" / "test_projects" / "TP2_Bridge_4x10_Calendar.xml"
HOLIDAY_KEY = "TP2_Bridge_4x10_Calendar"
#: nodes per body row (cells + track + bar/milestone + status line + shading layer + a few
#: labels) — the pre-fix /analysis row carried 834 on the operator's file, 220+ on TP5
ROW_BUDGET = 40


def _load(client: TestClient) -> None:
    for i, fx in enumerate((FIXTURE, HOLIDAY_FIXTURE)):
        files = [("files", (fx.name, fx.read_bytes(), "text/xml"))]
        meta = json.dumps([{"rel": fx.name, "mtime": 1_700_000_000_000 + i}])
        assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200


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


_CENSUS = """(sel) => {
  const rows = [...document.querySelectorAll(sel.rows)];
  const per = rows.map(r => r.querySelectorAll('*').length);
  const track = document.querySelector(sel.track);
  const cs = track ? getComputedStyle(track) : null;
  return {
    rows: rows.length,
    maxRow: per.length ? Math.max(...per) : null,
    gridDivs: document.querySelectorAll(sel.scope + ' .g-grid').length,
    holidayDivs: document.querySelectorAll(sel.scope + ' .g-nonwork-holiday').length,
    trackBg: cs ? cs.backgroundImage : null,
    tiers: document.querySelectorAll(sel.scope + ' .g-tier').length,
  };
}"""


def _open(browser: Any, served: str, path: str, ready: str) -> Any:
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(served + path, wait_until="load")
    page.wait_for_selector(ready, timeout=30000)
    page.wait_for_timeout(800)
    return page


def _assert_budget(c: dict[str, Any], where: str) -> None:
    assert c["rows"] > 0, f"{where}: no rows rendered"
    assert c["gridDivs"] == 0, (
        f"{where}: {c['gridDivs']} per-row gridline divs (must be a background)"
    )
    assert c["holidayDivs"] == 0, f"{where}: {c['holidayDivs']} per-row holiday divs"
    assert c["maxRow"] <= ROW_BUDGET, f"{where}: a row carries {c['maxRow']} nodes (> {ROW_BUDGET})"
    # the gridlines did not simply vanish: they are painted as a background image on the track
    assert c["trackBg"] and "svg" in c["trackBg"], (
        f"{where}: track has no gridline background: {c['trackBg']}"
    )
    assert c["tiers"] >= 1, f"{where}: header lost its tiers"


def test_analysis_rows_stay_within_the_dom_budget(browser: Any, served: str) -> None:
    page = _open(browser, served, f"/analysis/{KEY}", "#grid table.gantt-grid")
    c = page.evaluate(
        _CENSUS, {"rows": "#grid tbody tr", "track": "#grid .g-track", "scope": "#grid"}
    )
    _assert_budget(c, "/analysis")
    # zoomed in (finer gridlines) the budget must hold — the pre-fix tree ADDED a div per line
    page.evaluate("() => { document.getElementById('vizZoom').value = '24'; }")
    page.click("#zoomIn")
    page.wait_for_timeout(800)
    c2 = page.evaluate(
        _CENSUS, {"rows": "#grid tbody tr", "track": "#grid .g-track", "scope": "#grid"}
    )
    _assert_budget(c2, "/analysis @30px/day")
    page.context.close()


def test_path_rows_stay_within_the_dom_budget(browser: Any, served: str) -> None:
    page = _open(browser, served, "/path", ".path-track")
    c = page.evaluate(
        _CENSUS, {"rows": ".path-grid tbody tr", "track": ".path-track", "scope": ".path-grid"}
    )
    _assert_budget(c, "/path")
    page.context.close()


def test_holidays_are_one_shared_layer_not_a_div_per_holiday_per_row(
    browser: Any, served: str
) -> None:
    """TP2's calendar carries four exceptions inside the span. Pre-fix each was a
    `.g-nonwork-holiday` div in every row; now the row's shading layer carries them as ONE svg
    background layer (class `g-nonwork-holidays`) shared through a generated rule."""
    page = _open(browser, served, f"/analysis/{HOLIDAY_KEY}", "#grid table.gantt-grid")
    c = page.evaluate(
        """() => {
          const sel = '#grid .g-nonwork-behind, #grid .g-nonwork-front';
          const layers = [...document.querySelectorAll(sel)];
          const withHoli = layers.filter(l => l.classList.contains('g-nonwork-holidays'));
          const bg = withHoli.length ? getComputedStyle(withHoli[0]).backgroundImage : null;
          return {layers: layers.length, withHoli: withHoli.length, bg,
                  holidayDivs: document.querySelectorAll('#grid .g-nonwork-holiday').length,
                  rules: (document.getElementById('sfGanttShared') || {childNodes: []})
                    .childNodes.length};
        }"""
    )
    assert c["layers"] > 0, "no shading layers rendered (is non-working shading off?)"
    assert c["withHoli"] == c["layers"], f"holiday layer missing on some rows: {c}"
    assert c["holidayDivs"] == 0, f"{c['holidayDivs']} per-row holiday divs survived"
    assert c["bg"] and "svg" in c["bg"] and "gradient" in c["bg"], (
        f"layer lacks svg+gradient: {c['bg']}"
    )
    assert c["rules"] <= 24, f"shared stylesheet unbounded: {c['rules']} rules"
    page.context.close()
