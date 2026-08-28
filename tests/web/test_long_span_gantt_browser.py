"""Long-span Gantt behavior on /path — the operator's second live defect, driven at span scale.

Operator evidence (2026-08-28, AUDIT-2026-08-27 Phase-0 addendum): their real schedule spans
2017-2029 (~4,500 calendar days). On it, /path exhibited three defects the TP4-scale suite could
never see, all reproduced by probe against a synthetic look-alike before any fix (QC-1 red-first):

1. **The reflow path leaves the timeline COLUMN pinned at its attach-time width** (ADR-0441).
   ``SFColResize.attach`` sizes the ``.g-head`` th fresh per attach — but attach runs only from
   ``render()``, while the Zoom slider and Fit go through ``reflow()``, which swaps a new scale
   into the th and leaves the th's inline width/minWidth/maxWidth stale. After Fit the measured
   truth was: every bar painted inside a 969px track — positioned inside a **40,104px** column
   with the pane still scrolled 24,206px right from the data-date seat. Track rect left:
   **-24,205px**. "Renders wrong" and "controls do nothing" in one mechanism: the view stares at
   dead space.
2. **The whole-schedule posture opens at the slider default (8 px/day) regardless of span**
   (path.js ``fitFill = posture !== "whole"``): a 4,500-day schedule opens as a ~36,000px track
   whose viewport slice is almost always empty.
3. **The timescale header degrades instead of adapting**: fitted, the month tier renders 165
   bands averaging **5.9px, zero labeled** — the operator's picket fence — because tierBands only
   shrinks LABELS (full -> narrow -> empty) and never promotes UNITS the way MS Project does when
   zoomed out.

The fixture (``TP5_LongSpan_Synthetic.xml``, 121 tasks, 2017-2029) carries the SPAN, not the row
count — the width/posture/promotion defects reproduce at any row count, and the 2,280-row
performance measurements stay in the audit ledger (scratchpad probe), not in CI.

State seeded/driven per the repo's browser-test idioms; every FAIL-side test here was observed
RED on the pre-fix tree (see docs/adr/0441 for the recorded failures).
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

PATH = "/path"


def _load(client: TestClient) -> None:
    files = [("files", (FIXTURE.name, FIXTURE.read_bytes(), "text/xml"))]
    meta = json.dumps([{"rel": FIXTURE.name, "mtime": 1_700_000_000_000}])
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    # NO target on purpose — the whole-schedule posture is the surface under test.


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


def _open(browser: Any, served: str) -> Any:
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(served + PATH, wait_until="load")
    page.wait_for_selector(".path-track", timeout=30000)
    page.wait_for_timeout(1500)
    return page


_GEOM = """() => {
  const th = document.querySelector('.path-timeline-head');
  const scale = document.querySelector('.path-scale');
  const track = document.querySelector('.path-track');
  return {
    th_w: th ? Math.round(th.getBoundingClientRect().width) : null,
    scale_w: scale ? Math.round(scale.getBoundingClientRect().width) : null,
    track_w: track ? Math.round(track.getBoundingClientRect().width) : null,
    win: window.innerWidth,
  };
}"""

_TIERS = """() => [...document.querySelectorAll('.path-scale .g-tier')].map(t => {
  const bs = [...t.querySelectorAll('.g-band')];
  const ws = bs.map(b => b.getBoundingClientRect().width);
  return {
    bands: bs.length,
    labeled: bs.filter(b => b.textContent.trim()).length,
    avg_w: ws.length ? ws.reduce((a, c) => a + c, 0) / ws.length : null,
  };
})"""

_VISIBLE_MARKS = """() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  let n = 0;
  document.querySelectorAll('.gantt-bar, .g-ms').forEach(b => {
    const r = b.getBoundingClientRect();
    if (r.right > 0 && r.left < vw && r.bottom > 0 && r.top < vh && r.width >= 1) n++;
  });
  return n;
}"""


def _fit(page: Any) -> None:
    page.click("#pathFit")
    page.wait_for_timeout(600)


def _table_into_view(page: Any) -> None:
    page.evaluate("() => document.querySelector('.path-grid').scrollIntoView()")
    page.wait_for_timeout(300)


# ── ADR-0441 fix A: reflow must re-size the pinned timeline column ────────────────────────────


def test_fit_resizes_the_timeline_column_to_the_new_axis(browser: Any, served: str) -> None:
    """THE stale-pin mechanism. Pre-fix: after Fit the scale shrinks to ~page width while the th
    keeps its attach-time inline width (measured 40,104px at operator scale) — every bar painted,
    none on screen. The th must track the axis on every reflow."""
    page = _open(browser, served)
    g0 = page.evaluate(_GEOM)
    assert g0["th_w"] is not None and g0["scale_w"] is not None
    _fit(page)
    g1 = page.evaluate(_GEOM)
    assert abs(g1["th_w"] - g1["scale_w"]) <= 4, (
        f"timeline column ({g1['th_w']}px) did not follow the fitted scale ({g1['scale_w']}px) — "
        "the reflow path left the attach-time pin in place"
    )
    _table_into_view(page)
    assert page.evaluate(_VISIBLE_MARKS) >= 1, "fitted view shows no bar/milestone in the viewport"
    page.context.close()


# ── ADR-0441 fix C: a long-span whole-schedule view opens FITTED, not at 8 px/day ─────────────


def test_whole_schedule_long_span_opens_fitted(browser: Any, served: str) -> None:
    """Pre-fix the no-target posture opened this 4,500-day span at the slider default — a
    ~36,000px track whose visible slice is almost always empty (the operator's first screenshot).
    A span that cannot fit at the default zoom must open fitted."""
    page = _open(browser, served)
    g = page.evaluate(_GEOM)
    assert g["track_w"] <= 3 * g["win"], (
        f"whole-schedule opened as a {g['track_w']}px track in a {g['win']}px window"
    )
    _table_into_view(page)
    assert page.evaluate(_VISIBLE_MARKS) >= 1
    page.context.close()


# ── ADR-0441 fix B: the header promotes units at low density instead of degrading ─────────────


def test_fitted_header_has_no_unlabeled_picket_fence_tier(browser: Any, served: str) -> None:
    """Pre-fix, fitted: months = 165 bands, 0 labeled, 5.9px average — an unreadable picket
    fence (the operator's report: "should be showing Years, Quarters, and Months and it is
    not"). Post-fix every rendered tier holds legible, labeled bands (months promote to
    quarters at this density and return on zoom-in — the MS Project behavior)."""
    page = _open(browser, served)
    _fit(page)
    tiers = page.evaluate(_TIERS)
    assert tiers, "no tier rows rendered"
    for i, t in enumerate(tiers):
        assert not (t["bands"] > 0 and t["labeled"] == 0), f"tier {i} is an unlabeled fence: {t}"
        assert t["avg_w"] is None or t["avg_w"] >= 10, f"tier {i} bands are sub-legible: {t}"
    page.context.close()


def test_zoomed_in_view_still_offers_months(browser: Any, served: str) -> None:
    """The promotion must be density-driven, not permanent: at 12 px/day a month is ~250px wide
    and the configured Years/Quarters/Months stack must come back. (PASS-side pin — green before
    and after the fix; it is what stops an over-eager promotion from deleting months forever.)"""
    page = _open(browser, served)
    page.evaluate(
        """() => {
          const z = document.getElementById('pathZoom');
          z.value = '12';
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(800)  # outlasts the reflow debounce
    tiers = page.evaluate(_TIERS)
    month_like = [t for t in tiers if t["bands"] >= 100 and t["labeled"] > 0]
    assert month_like, f"no month-density tier at 12 px/day: {tiers}"
    page.context.close()


# ── ADR-0441 fix D: a slider drag coalesces into one rebuild ──────────────────────────────────


def test_zoom_slider_input_burst_is_debounced(browser: Any, served: str) -> None:
    """A drag fires dozens of input events; pre-fix each one synchronously rebuilt the whole
    grid (measured 4-6 s per rebuild at the operator's 2,280 rows — the page reads as dead).
    A burst of 6 events must coalesce into a single trailing rebuild."""
    page = _open(browser, served)
    rebuilds = page.evaluate(
        """async () => {
          const th = document.querySelector('.path-timeline-head');
          let n = 0;
          new MutationObserver(muts => {
            muts.forEach(m => { if (m.addedNodes.length) n++; });
          }).observe(th, {childList: true});
          const z = document.getElementById('pathZoom');
          for (const v of [9, 10, 11, 12, 13, 14]) {
            z.value = String(v);
            z.dispatchEvent(new Event('input', {bubbles: true}));
          }
          await new Promise(r => setTimeout(r, 700));
          return n;
        }"""
    )
    assert rebuilds <= 2, f"6 slider events caused {rebuilds} grid rebuilds"
    page.context.close()
