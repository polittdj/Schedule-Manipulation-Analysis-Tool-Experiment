"""/margin's Claude Design grid, measured in a REAL browser (ADR-0489).

Markup is not evidence for a claim about GEOMETRY (ADR-0304's lesson). The artboard puts the
burn-down and the erosion trend side by side in two EQUAL columns at 1440 px, and each of the
page's two chart panels is drawn VERBATIM inside its column: a 720-unit viewBox SVG at
``width: 100%``, a panel head with an h2, a ⤓ EXCEL / ⛶ ENLARGE tool strip and the whole-series
provenance chip (``v1→v4 · SOURCE: first → last · DD first → last``, long enough to overrun a
half-width head if the head could not wrap). This module pins, in all four themes: the two chart
panels share one row at equal widths · each panel's SVG and every child of its head end inside
the panel's right edge (element RECTS, never the panel's ``scrollWidth`` — jarvis's corner
brackets sit at ``right:-1px`` on every panel by design) · the per-version table's cells spill
nowhere (``scrollWidth - clientWidth`` per cell, which no rect can see) · the callout sits above
the strip, the strip above the grid · the document does not scroll sideways (ADR-0477's rule) ·
zero page errors — and, once, the chips' EFFECT: a click opens that version's analysis page,
where the margin set is confirmed (ADR-0470's rule that a cursor is navigation is proven by a
driver, never by markup).

Red first (2026-09-14): on the pristine tree the grid does not exist, so the geometry probe
finds no ``.cd-grid-11`` and every theme fails by name; the chip driver fails on the absent chip.

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py`` so a CI runner EXECUTES this module (ADR-0418).
"""

from __future__ import annotations

import datetime as dt
import socket
import threading
import time
from typing import Any

import pytest

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from web.browser_chrome import chrome_kwargs

THEMES = ("console", "daylight", "apollo", "jarvis")
VIEWPORT = {"width": 1440, "height": 900}
DAY = 480
_MARGINS = [("2026-02-27", 40), ("2026-03-31", 30), ("2026-04-30", 20), ("2026-05-29", 10)]

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")


def _t(uid: int, name: str, days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=int(days * DAY), **kw)  # type: ignore[arg-type]


def _r(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _version(status: str, margin_days: float) -> Schedule:
    """The margin-dashboard view test's own fixture: a MARGIN buffer on the delivery chain,
    shrinking version to version (no golden carries a margin-named activity)."""
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime.fromisoformat(status),
        tasks=(
            _t(1, "Work", 500),
            _t(2, "Schedule MARGIN: pre-delivery", margin_days),
            _t(3, "Deliver SV1", 0, is_milestone=True),
        ),
        relationships=(_r(1, 2), _r(2, 3)),
    )


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

    st = SessionState()
    for status, m in _MARGINS:
        v = _version(status, m)
        st.schedules[v.source_file] = v
    st.target_uid = 3
    app = create_app(st)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


#: the two grid panels' boxes and, per panel, the right edge of its SVG and of every child of
#: its head strip; the per-version table's worst cell spill; the vertical order of the design's
#: three new surfaces; the document's scroll width
_GEOMETRY = """() => {
  const grid = document.querySelector('.cd-grid-11');
  if (!grid) return {grid: null};
  const R = e => e.getBoundingClientRect();
  const panels = [...grid.querySelectorAll(':scope > .panel')].map(p => {
    const r = R(p), svg = p.querySelector('.chart-host svg');
    const head = [...p.querySelectorAll('.panel-head > *')];
    return {chart: (p.querySelector('.chart-host') || {}).id || null,
            top: Math.round(r.top + window.scrollY), left: Math.round(r.left),
            width: Math.round(r.width), right: Math.round(r.right),
            svgRight: svg ? Math.round(R(svg).right) : null,
            svgWidth: svg ? Math.round(R(svg).width) : null,
            headRight: Math.round(Math.max(...head.map(e => R(e).right))),
            headKinds: head.map(e => e.tagName + '.' + e.className)};
  });
  const cells = [...document.querySelectorAll(
    '.panel[data-export] table th, .panel[data-export] table td')];
  const top = s => {
    const e = document.querySelector(s);
    return e ? Math.round(R(e).top + window.scrollY) : null;
  };
  return {grid: true, panels, cells: cells.length,
          maxCellSpill: Math.max(...cells.map(c => c.scrollWidth - c.clientWidth)),
          calloutTop: top('.cd-callout'), stripTop: top('#marginCursor'),
          gridTop: top('.cd-grid-11'),
          sw: document.scrollingElement.scrollWidth, iw: window.innerWidth,
          theme: document.documentElement.getAttribute('data-theme')};
}"""


def _open(p: Any, served: str, theme: str) -> tuple[Any, Any, list[str]]:
    browser = p.chromium.launch(**chrome_kwargs())
    ctx = browser.new_context(viewport=VIEWPORT)
    ctx.add_init_script(f"try{{localStorage.setItem('sf-theme','{theme}')}}catch(e){{}}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + "/margin", wait_until="load")
    page.wait_for_selector("#marginErosionChart svg", timeout=15000)
    page.mouse.move(0, 0)  # park the virtual mouse: it survives goto() and would hover a chip
    page.wait_for_timeout(300)
    return browser, page, errors


@pytest.mark.parametrize("theme", THEMES)
def test_the_two_chart_panels_share_one_row_and_nothing_in_them_outgrows_the_panel(
    served: str, theme: str
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served, theme)
        g = page.evaluate(_GEOMETRY)
        browser.close()
    assert not errors, errors
    assert g["grid"], "no .cd-grid-11 on the page"
    assert g["theme"] == theme, g["theme"]
    panels = g["panels"]
    assert [x["chart"] for x in panels] == ["marginBurndownChart", "marginErosionChart"], panels
    # one row, two equal columns, burn-down left of the erosion trend — the artboard's grid
    assert len({x["top"] for x in panels}) == 1, panels
    assert panels[0]["left"] < panels[1]["left"], panels
    assert len({x["width"] for x in panels}) == 1, panels
    assert all(x["width"] < VIEWPORT["width"] // 2 for x in panels), panels
    for x in panels:
        assert x["svgWidth"] and x["svgWidth"] > 300, x  # the chart is drawn, not collapsed
        assert x["svgRight"] <= x["right"], x
        assert x["headRight"] <= x["right"], x  # the h2, the tools and the long chip all fit
        assert "SPAN.prov-chip" in x["headKinds"], x
    assert g["cells"] >= 12 and g["maxCellSpill"] <= 0, g  # the per-version table's cells
    # the design's vertical order: callout, then the strip, then the grid
    assert g["calloutTop"] < g["stripTop"] < g["gridTop"], g
    # and the document does not scroll sideways at rest (ADR-0477's rule, this page included)
    assert g["sw"] == g["iw"] == VIEWPORT["width"], g


def test_a_chip_click_opens_that_versions_analysis_page_where_its_margin_set_is_confirmed(
    served: str,
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served, "console")
        assert page.locator(".cd-chip.on").count() == 0  # a link list has no selected state
        assert page.locator(".cd-pill").inner_text().startswith("v4 · 2026-05-29.mpp · DD ")
        page.locator('.cd-chip[data-idx="0"]').click()
        page.wait_for_load_state("load")
        page.wait_for_selector('form[action="/margin/confirm"]', timeout=15000)
        url = page.url
        key = page.locator('form[action="/margin/confirm"] input[name=key]').get_attribute("value")
        checked = page.locator('input[name=uid][value="2"]').is_checked()
        browser.close()
    assert not errors, errors
    assert url.endswith("/analysis/2026-02-27.mpp"), url
    assert key == "2026-02-27.mpp"
    assert checked  # the named margin task is that version's confirmed set, ticked
