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


# ── the timescale header must stay INSIDE its own box, and its bands must not overlap ─────────

_BAND_BOX = """() => {
  const scale = document.querySelector('.path-scale');
  if (!scale) return {err: 'no .path-scale'};
  const axisW = parseFloat(scale.style.width) || scale.clientWidth;
  const rows = [...scale.querySelectorAll('.g-tier')].map(t => {
    const bs = [...t.querySelectorAll('.g-band')].map(b => ({
      label: (b.textContent || '').trim(),
      left: parseFloat(b.style.left) || 0,
      width: parseFloat(b.style.width) || 0,
    }));
    let overflow = 0, overlap = 0;
    bs.forEach((b, i) => {
      overflow = Math.max(overflow, (b.left + b.width) - axisW);
      if (i) overlap = Math.max(overlap, (bs[i-1].left + bs[i-1].width) - b.left);
    });
    return {cls: t.className, n: bs.length, overflow: Math.round(overflow),
            overlap: Math.round(overlap), first: bs[0] || null, last: bs[bs.length-1] || null};
  });
  return {axisW: Math.round(axisW), scrollW: scale.scrollWidth, clientW: scale.clientWidth, rows};
}"""


def test_tier_bands_stay_inside_the_axis_and_never_overlap(browser: Any, served: str) -> None:
    """A partial unit at either END of the span must be TRUNCATED, not drawn a full unit wide.

    ``tierBands`` clamped only the band's ``left`` (``Math.max(0, left)``) while computing its
    width from the UNCLAMPED edges and never clamping ``right`` to ``axis.width``. On the
    operator's 12.3-year IPMR that draws the first year band a full year wide from x=0 — so
    2017 (0..81px) OVERLAPPED 2018 (starting at 47px) by 34px and its label sat over the join —
    and the last band ran 57px PAST the header's own right edge (scrollWidth 1026 vs clientWidth
    969), bleeding over the column beside it. Measured on both the fitted and zoomed views: the
    span almost never starts and ends on a clean year boundary, so at least one end is wrong
    essentially always.
    """
    page = _open(browser, served)
    try:
        for view, act in (("fitted", _fit), ("as-opened", lambda p: None)):
            act(page)
            page.wait_for_timeout(400)
            box = page.evaluate(_BAND_BOX)
            assert not box.get("err"), box
            assert box["rows"], f"{view}: no tier rows rendered"
            for row in box["rows"]:
                assert row["overflow"] <= 1, (
                    f"{view}: {row['cls']} runs {row['overflow']}px past the axis "
                    f"({row['axisW'] if 'axisW' in row else box['axisW']}px) — last band "
                    f"{row['last']}; the header bleeds over the next column"
                )
                assert row["overlap"] <= 1, (
                    f"{view}: {row['cls']} has bands overlapping by {row['overlap']}px — "
                    f"first band {row['first']}; two labels are drawn over each other"
                )
            assert box["scrollW"] <= box["clientW"] + 1, (
                f"{view}: the header overflows its own box "
                f"(scrollWidth {box['scrollW']} > clientWidth {box['clientW']})"
            )
    finally:
        page.close()


# ── positioning MODE, not just geometry: the Gantt's positioned elements must stay absolute ────
#
# Every .g-band / .gantt-bar / .g-ms is created WITH a title= (its hover text). tooltips.js
# promotes a non-empty title to data-sf-hint at load, and hud.css anchors the hint bubble with
# `[data-sf-hint]{position:relative}` — which, at equal specificity and later in the cascade,
# OVERRODE `.g-band{position:absolute}`. The bands fell into block flow, one per line, each shifted
# by its inline `left`: a diagonal staircase of years, everything past the third row clipped.
# Bars and diamonds were flipped too, surviving only because a track holds one child. The inline
# left/width the earlier tests read were all correct — position mode is invisible to them. Only
# the RENDERED rect sees it.

_RENDERED_MODE = """() => {
  const scale = document.querySelector('.path-scale');
  const sr = scale.getBoundingClientRect();
  const tiers = [...scale.querySelectorAll('.g-tier')].map(t => {
    const bs = [...t.querySelectorAll('.g-band')];
    const tops = [...new Set(bs.map(b => Math.round(b.getBoundingClientRect().top - sr.top)))];
    return {cls: t.className.replace('g-tier ', ''), n: bs.length, distinctTops: tops.length,
            tops: tops.slice(0, 5)};
  });
  const mode = sel => {
    const els = [...document.querySelectorAll(sel)];
    const bad = els.filter(e => getComputedStyle(e).position !== 'absolute');
    return {n: els.length, notAbsolute: bad.length,
            hinted: els.filter(e => e.hasAttribute('data-sf-hint')).length};
  };
  return {tiers, scrollH: scale.scrollHeight, clientH: scale.clientHeight,
          band: mode('.path-scale .g-band'), bar: mode('.gantt-bar'), ms: mode('.g-ms')};
}"""


def test_header_bands_bars_and_milestones_stay_absolutely_positioned(
    browser: Any, served: str
) -> None:
    """The one assertion that could have caught the operator's staircase: rendered y, per tier.

    Three faces of the same defect, each asserted on the RENDERED tree:
      * every band in a tier paints on ONE row (a second distinct top is the staircase);
      * the header does not overflow its own height (the clipped rows below the third);
      * the computed position of every band, bar and milestone is `absolute` — including the
        ones that carry a tooltip, which is exactly the population the anchor rule hijacked.
    """
    page = _open(browser, served)
    try:
        page.wait_for_timeout(500)
        m = page.evaluate(_RENDERED_MODE)
        for t in m["tiers"]:
            assert t["distinctTops"] == 1, (
                f"{t['cls']}: its {t['n']} bands paint on {t['distinctTops']} different rows "
                f"(tops {t['tops']}…) — the bands have fallen into block flow and cascade "
                f"diagonally instead of tiling one row"
            )
        # The gold data-date line (.pv-now) deliberately overhangs the header by 2px top and
        # bottom to join the track gridlines, so exact equality is the wrong bound. A stacked
        # row is a whole tier row — 18px — and the staircase measured ~180; anything under one
        # row of overflow is hairline, anything at or over it is a row that fell into flow.
        assert m["scrollH"] - m["clientH"] < 18, (
            f"the header overflows its own box vertically by {m['scrollH'] - m['clientH']}px "
            f"(scrollHeight {m['scrollH']} vs clientHeight {m['clientH']}): at least one row "
            f"is stacking below the visible header"
        )
        for name in ("band", "bar", "ms"):
            r = m[name]
            assert r["n"] > 0, f"no {name} elements rendered"
            assert r["notAbsolute"] == 0, (
                f"{r['notAbsolute']} of {r['n']} {name} elements are not position:absolute "
                f"({r['hinted']} carry data-sf-hint) — the tooltip anchor rule is overriding "
                f"the Gantt's own positioning"
            )
    finally:
        page.close()


def test_the_hint_anchor_still_positions_static_hosts_after_the_downgrade(
    browser: Any, served: str
) -> None:
    """The other half of the :where() change: static hosts must still get their bubble anchor.

    `[data-sf-hint]{position:relative}` existed to give a STATIC element (a heading, a button,
    a hint-dot) a positioned box for its `::after` callout. Dropping the selector to zero
    specificity must not lose that — otherwise the fix trades a broken header for broken
    tooltips sitewide, and `test_tooltips.py` (byte pins on the CSS text) would never notice.
    The contract is asserted on COMPUTED position, which is what anchors the bubble, so it needs
    no hover and no 1.5s transition-delay wait.
    """
    page = _open(browser, served)
    try:
        page.wait_for_timeout(500)
        r = page.evaluate("""() => {
          const hosts = [...document.querySelectorAll('[data-sf-hint]')]
            .filter(e => !e.closest('.path-scale, .path-track, .g-track'));
          const byPos = {};
          hosts.forEach(e => {
            const p = getComputedStyle(e).position; byPos[p] = (byPos[p] || 0) + 1;
          });
          const staticLeft = hosts.filter(e => getComputedStyle(e).position === 'static');
          return {hosts: hosts.length, byPos,
                  staticSample: staticLeft.slice(0,3).map(e => e.tagName + '.' + e.className)};
        }""")
        assert r["hosts"] > 0, "no non-Gantt hint hosts on the page to check the anchor against"
        assert not r["staticSample"], (
            f"{r['byPos'].get('static', 0)} of {r['hosts']} tooltip hosts are "
            f"position:static — the bubble has no anchor and will position against the page "
            f"instead of its host: "
            f"{r['staticSample']}"
        )
        assert r["byPos"].get("relative", 0) > 0, (
            f"no hint host is position:relative ({r['byPos']}) — the zero-specificity "
            f"anchor rule is not applying at all"
        )
    finally:
        page.close()
