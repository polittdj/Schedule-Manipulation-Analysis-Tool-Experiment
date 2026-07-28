"""Ultracode round 10 — /performance wears the panel contract (ADR-0298 vocabulary).

The conversion decorates the FOURTEEN ``.tile.panel`` G1-G7 mounts plus the intro shell. This
module is shaped to /performance's OWN hazards, each of which a prior round shipped somewhere:

* **inert glyph** (the round-4 ``/evm`` defect) — panelkit.js is a PER-PAGE include, so the
  markup is only half the evidence. The include is asserted here and a REAL chromium click is
  asserted in :func:`test_panelkit_click_drives_a_performance_tile` below;
* **▦ DATA with nothing behind it** — these tiles ship no ``.sf-drawer`` and no ``.sr-only``
  table, and ``mission.js`` (the only driver of ``.tile-data``) is not on this route, so the
  glyph must be ABSENT, not decorative;
* **the master stepper falsifies static per-file strings** — ``performance.js::setVersion``
  re-binds G1-G5 to a different loaded file on every ◀/▶/Play tick. So every tile take must
  quote NO digit its own title/hint does not already render, and every tile's provenance chip
  must be the first→last RANGE chip (:func:`_series_prov_chip`), never a single file's;
* **one convention** — the intro panel already owns this page's Excel control, so it must keep
  exactly ONE Excel affordance and gain no second ⤓;
* **the embedded JSON blob** — ``tests/web/test_performance_view.py`` splits the page on the
  literal ``id=perfData>``; new markup must never introduce a second one;
* **the promotion census** — nothing may GAIN ``.panel`` (hud.css's broad jarvis ``.panel``
  rules would then apply to it): 18 before the conversion, 18 after;
* **the axis captions are frozen** (standing requirement 5, ADR-0298/0301/0303) — this round
  touched no ``static/*.js`` at all, and the three quad captions are pinned byte-for-byte here.
"""

from __future__ import annotations

import gzip
import json
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "fuse_hardfile"
PERF_JS = ROOT / "src" / "schedule_forensics" / "web" / "static" / "performance.js"

#: the fourteen chart mounts, in render order (test_performance_view.py pins the same list)
MOUNTS = (
    "g1Census",
    "g1Normal",
    "g2Starts",
    "g2Finishes",
    "g2Cum",
    "g3Starts",
    "g3Finishes",
    "g4Starts",
    "g4Finishes",
    "g5Scurve",
    "g5Hist",
    "quadHmiCei",
    "quadRatio",
    "quadBeiCp",
)

#: panelkit.js's EXACT strings — a page may render only these (and the toggled forms panelkit
#: itself writes at click time). Anything else is a parallel vocabulary (ADR-0298).
PANELKIT_LABELS = ("▦ DATA", "▦ HIDE DATA", "⤓ EXCEL", "⛶ ENLARGE", "⛶ SHRINK")

#: `.panel` elements on /performance BEFORE the round-10 conversion, on this fixture pair:
#: 2 status stacks + the intro shell + 14 tiles + the Ask panel. The conversion DECORATES
#: existing panels — it must never promote a new one into hud.css's jarvis `.panel` rules.
PANELS_BEFORE = 18


def _client(*names: str) -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in names:
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        r = c.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
        assert r.status_code == 200
    return c


@pytest.fixture(scope="module")
def page() -> str:
    return _client("Hard_File", "Hard_File_updated3").get("/performance").text


def _tiles(page: str) -> list[str]:
    """Each ``<section class="tile panel" …>…</section>`` of the G1-G7 wall, in order."""
    grid = page.split("<div class=mosaic id=perfGrid>", 1)[1].split("</div>\n<script", 1)[0]
    return re.findall(r'<section class="tile panel".*?</section>', grid, re.S)


def _intro_panel(page: str) -> str:
    """The Performance-Analysis-Summary shell panel (head → the mosaic)."""
    return page.split("<div class=panel><div class=panel-head>", 1)[1].split(
        "<div class=mosaic id=perfGrid>", 1
    )[0]


# ── the contract itself ────────────────────────────────────────────────────────────────────


def test_panelkit_is_included_exactly_once(page: str) -> None:
    """Standing requirement 2. The src is cache-busted (``?v=1.0.x``) so match a SUBSTRING;
    TWO includes would register the delegated listener twice and net-cancel every toggle."""
    assert "/static/panelkit.js" in page
    assert page.count("/static/panelkit.js") == 1
    assert "/static/performance.js" in page  # the page's own renderer still ships


def test_every_tile_wears_the_head_tools_prov_and_take(page: str) -> None:
    tiles = _tiles(page)
    assert len(tiles) == len(MOUNTS)
    for mount, tile in zip(MOUNTS, tiles, strict=True):
        assert f"id={mount}" in tile, mount
        # the mission-wall tile-head form: title, then the tools strip, inside .tile-head
        assert '<span class="tile-actions sf-tools" data-noprint=1>' in tile, mount
        assert tile.index("sf-tools") < tile.index("</div><div class=tile-prov>"), mount
        # provenance + a one-sentence takeaway
        assert "<div class=tile-prov><span class=prov-chip data-no-i18n>" in tile, mount
        assert "<p class=sf-take data-no-i18n>" in tile, mount
        assert tile.count("<p class=sf-take") == 1, mount
        # the strip lives in the HEAD, never inside .chart-host (chartframe.js wraps that host
        # in .cf-frame at runtime and the G2/G4/G5 bars are SFDrill click targets)
        host = tile.split("<div class=chart-host", 1)[1]
        assert "sf-tools" not in host, mount


def test_only_the_real_glyphs_ship_and_data_is_deliberately_absent(page: str) -> None:
    """Vocabulary-not-a-stamp: ⤓ and ⛶ are wired; ▦ would be inert here, so it is omitted."""
    assert page.count("⤓ EXCEL") == len(MOUNTS)
    assert page.count("⛶ ENLARGE") == len(MOUNTS)
    assert page.count("data-sf-excel") == len(MOUNTS)
    assert page.count("data-sf-big") == len(MOUNTS)
    # no ▦ DATA and no drawer to drive it — an inert glyph is the defect this round prevents
    assert "▦" not in page
    assert "data-sf-data" not in page
    assert "class=sf-drawer" not in page
    # and no vocabulary this page cannot drive: mission.js is NOT on this route, so its
    # .tile-data / .tile-expand classes would be dead buttons
    assert "tile-data" not in page and "tile-expand" not in page
    assert "/static/mission.js" not in page
    # every rendered glyph label is one panelkit owns
    for label in re.findall(r"[▦⤓⛶][^<]*", page):
        assert label.strip() in PANELKIT_LABELS, label


def test_enlarge_is_panel_scoped_because_each_tile_holds_exactly_one_chart(page: str) -> None:
    """N charts in one panel would desync N ``.is-big`` labels; each tile holds exactly one,
    so the single button may carry ``data-sf-big`` for the whole panel."""
    for mount, tile in zip(MOUNTS, _tiles(page), strict=True):
        assert tile.count("class=chart-host") == 1, mount
        assert tile.count("data-sf-big") == 1, mount


def test_excel_points_at_a_live_endpoint_serving_exactly_these_series() -> None:
    """⤓ EXCEL follows the panel's ``data-export``. Never a dead link: the URL is fetched."""
    c = _client("Hard_File", "Hard_File_updated3")
    page = c.get("/performance").text
    urls = set(re.findall(r'<section class="tile panel" data-export="([^"]+)"', page))
    assert len(urls) == 1, urls  # one workbook, whose five sheets are these fourteen tiles
    url = urls.pop().replace("&amp;", "&")
    assert url.startswith("/export/xlsx/performance?file=")
    r = c.get(url)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml"
    )


def test_intro_panel_head_take_and_the_page_lede(page: str) -> None:
    intro = _intro_panel(page)
    assert "<h2>Performance Analysis Summary</h2>" in page  # the heading TEXT is unchanged
    assert "<div class=panel-head>" in page
    assert page.count("<div class=panel-head>") == 1
    assert "<span class=prov-chip data-no-i18n>" in intro
    assert "<p class=sf-take data-no-i18n>G1&ndash;G5 open on " in intro
    assert '<p class="page-lede">' in page  # the header block's missing lede (measured 0 before)


# ── hazard-shaped proofs (standing requirement 4) ──────────────────────────────────────────


def test_h2_no_take_quotes_a_figure_its_own_tile_does_not_already_render(page: str) -> None:
    """The master stepper re-binds G1-G5 to another file on every tick, so a server-rendered
    per-file number would become false on the first ▶. Every digit-run in a tile take must
    already appear in that tile's own title/hint — i.e. no take invents a figure."""
    for mount, tile in zip(MOUNTS, _tiles(page), strict=True):
        # ONLY the <h3> (its title text + its data-sf-hint callout) counts as "already
        # rendered" — never the tools strip, whose &#39;/=1 attributes carry stray digits
        h3 = re.search(r"<h3 class=viz-hint data-sf-hint=\"(.*?)\">(.*?)</h3>", tile, re.S)
        assert h3 is not None, mount
        rendered = h3.group(1) + h3.group(2)
        take = tile.split("<p class=sf-take data-no-i18n>", 1)[1].split("</p>", 1)[0]
        for run in re.findall(r"\d+", take):
            assert run in rendered, f"{mount}: take quotes {run!r}, which its own title does not"


def test_h2_every_tile_carries_the_SERIES_provenance_chip_not_one_file(page: str) -> None:
    """A ``_prov_chip(one_file)`` would be falsified the moment the stepper ticks; the
    first→last RANGE chip holds at every frame."""
    chips = set(re.findall(r"<div class=tile-prov><span class=prov-chip[^>]*>(.*?)</span>", page))
    assert len(chips) == 1, chips
    chip = chips.pop()
    assert chip.startswith("v1→v2 · SOURCE: ")  # the range form, both loaded files named
    assert "Hard_File.mpp.xml" in chip and "Hard_File_updated3.mpp.xml" in chip
    assert " · DD " in chip


def test_h3_the_page_body_form_is_untouched(page: str) -> None:
    """ADR-0268 moved Focus to POST and ``test_performance_version_picker_scopes_g1_to_g5``
    rides this <form>. The toolbar round must not have altered one byte of it."""
    sel = json.loads(page.split("id=perfData>", 1)[1].split("</script>", 1)[0])["version"]
    assert (
        "<form method=get action=/performance class=viz-controls>\n"
        "<label>Project graphs (G1&ndash;G5) use:&nbsp;<select name=file data-sf-autosubmit>\n"
    ) in page
    assert "<noscript><button type=submit>Apply</button></noscript>\n" in page
    assert f'<a class=btn-link href="/export/xlsx/performance?file={sel}">' in page


def test_h4_the_intro_panel_keeps_exactly_one_excel_affordance(page: str) -> None:
    """ADR-0298's one-convention law: it already owns the page's Excel control, so it gains
    neither a second ⤓ nor a ⛶ (``.is-big``'s grid-column is inert on a non-grid panel)."""
    intro = _intro_panel(page)
    assert intro.count("&#11015;") + intro.count("⤓") == 1
    assert "data-sf-excel" not in intro
    assert "data-sf-big" not in intro


def test_h5_the_embedded_dataset_marker_is_still_unique_and_parses(page: str) -> None:
    assert page.count("id=perfData>") == 1
    data = json.loads(page.split("id=perfData>", 1)[1].split("</script>", 1)[0])
    assert len(data["quads"]) == 2 and data["drm"]["n"] > 0
    # the JSON block stays the page's ONLY src-less script (test_csp_strict_scripts.py)
    assert '<script type="application/json" id=perfData>' in page


def test_promotion_census_nothing_gained_dot_panel(page: str) -> None:
    """An element that GAINS ``.panel`` joins hud.css's broad jarvis ``.panel`` fight."""
    panels = re.findall(r'class="(?:tile )?panel(?: status-stack)?"|class=panel[ >]', page)
    assert len(panels) == PANELS_BEFORE


def test_no_inline_handlers_were_introduced(page: str) -> None:
    """Strict ``script-src 'self'`` CSP: delegation only, zero ``on*=`` attributes."""
    assert not re.search(r"\son[a-z]+=", page)


def test_requirement_5_the_quad_axis_captions_are_byte_identical(page: str) -> None:
    """This round touched no ``static/*.js`` at all. The three quad captions — the ONLY
    ``SFChartFrame.axisTitles`` call site on this page — are pinned here so a later toolbar
    edit cannot move one silently (ADR-0298/0301/0303)."""
    js = PERF_JS.read_text(encoding="utf-8")
    assert js.count("SFChartFrame.axisTitles(") == 1
    assert "    SFChartFrame.axisTitles(svg, { L: L, R: R, T: T, B: B }, opts);\n" in js
    for caption in (
        'xLabel: "HMI (tasks)"',
        'yLabel: "CEI (finish)"',
        'xLabel: "To-go starts ÷ baseline remaining"',
        'yLabel: "To-go finishes ÷ baseline remaining"',
        'xLabel: "BEI"',
        'yLabel: "critical ÷ to-go T&M"',
    ):
        assert caption in js, caption


def test_chartframes_own_zoom_bar_is_neither_removed_nor_duplicated(page: str) -> None:
    """``chartframe.js``'s zoom/fullscreen bar is a DIFFERENT control from ⛶ ENLARGE: it is
    global and auto-scans every ``.chart-host``. The round must leave all 14 hosts alone."""
    assert page.count("class=chart-host") == len(MOUNTS)
    assert "/static/chartframe.js" in page


# ── the same claims, in a real browser (standing requirement 2) ─────────────────────────────

CHROME = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (see module docs)")
    if not CHROME.exists():
        pytest.skip(f"bundled chromium not at {CHROME}")
    import uvicorn

    app = create_app(SessionState())
    with TestClient(app) as c:
        for name in ("Hard_File", "Hard_File_updated3"):
            xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
            assert (
                c.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")}).status_code
                == 200
            )
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.mark.parametrize("theme", ["console", "jarvis"])
def test_panelkit_click_drives_a_performance_tile(served: str, theme: str) -> None:
    """Markup alone is not evidence. ONE real click on a tile's ⛶ must flip the tile to
    ``.is-big`` (546px → the full mosaic row) and the label to ⛶ SHRINK, and a second must
    restore both — proving the per-page include AND the delegated listener, under the theme
    whose broad ``html[data-theme=jarvis] button`` rule out-ranks the contract's."""
    from playwright.sync_api import sync_playwright

    sel = ".tile.panel[data-export]"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(CHROME))
        # never networkidle on this app: heartbeat.js (3s) / sysmon.js (2s) never settle
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/performance", wait_until="load")
        page.wait_for_selector("#g1Census", timeout=25000)
        page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
        page.wait_for_timeout(250)

        assert page.evaluate(
            "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
        ), "panelkit.js script element missing on /performance"
        assert page.locator(f"{sel} [data-sf-big]").count() == len(MOUNTS)

        btn = page.locator(f"{sel} [data-sf-big]").first
        assert btn.inner_text() == "⛶ ENLARGE"
        narrow = page.evaluate(
            f"() => document.querySelector('{sel}').getBoundingClientRect().width"
        )
        btn.click()  # a REAL user click (isTrusted), not element.click() from a script
        page.wait_for_timeout(100)
        state = page.evaluate(
            f"() => {{ const t = document.querySelector('{sel}');"
            " return {big: t.classList.contains('is-big'),"
            " w: t.getBoundingClientRect().width}; }"
        )
        assert state["big"], "click did not toggle .is-big — panelkit.js not driving /performance"
        assert state["w"] > narrow + 100, (narrow, state["w"])  # a genuine enlarge, not a no-op
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"

        btn.click()  # and back — never leave the page mutated
        page.wait_for_timeout(100)
        assert not page.evaluate(
            f"() => document.querySelector('{sel}').classList.contains('is-big')"
        )
        assert btn.inner_text() == "⛶ ENLARGE"

        # the contract classes actually PAINT under this theme (a defined token is not a
        # painting token) and nothing this round added escapes its tile
        probe = page.evaluate(
            """() => {
              const t = document.querySelector('.tile.panel[data-export]');
              const vis = e => {
                const c = getComputedStyle(e), r = e.getBoundingClientRect();
                return c.visibility === 'visible' && c.display !== 'none'
                       && r.width > 0 && r.height > 0;
              };
              const heights = new Set();
              let escapes = 0;
              document.querySelectorAll('.tile.panel[data-export]').forEach(tile => {
                const tr = tile.getBoundingClientRect();
                tile.querySelectorAll('.sf-tools button').forEach(b => {
                  heights.add(Math.round(b.getBoundingClientRect().height));
                  const r = b.getBoundingClientRect();
                  if (r.right > tr.right + 1 || r.left < tr.left - 1) escapes++;
                });
              });
              return {chip: vis(t.querySelector('.prov-chip')),
                      take: vis(t.querySelector('.sf-take')),
                      tools: vis(t.querySelector('.sf-tools button')),
                      heights: [...heights], escapes};
            }"""
        )
        assert probe["chip"] and probe["take"] and probe["tools"], probe
        assert probe["escapes"] == 0, probe
        # ONE distinct button height across all 28 buttons: no label split its glyph onto a
        # second line (the long /performance titles squeeze the strip — base.css nowrap rule)
        assert len(probe["heights"]) == 1, probe["heights"]
        browser.close()


def test_h2_a_real_stepper_tick_falsifies_nothing_this_round_rendered(served: str) -> None:
    """The signature /performance hazard, closed live. ONE real click on ``#perfNext`` re-binds
    G1-G5 to a DIFFERENT loaded file (``#perfStep`` names it). Every string this round added is
    server-rendered, so it cannot follow — which is exactly why none of them may be file-scoped.
    Proof: after the tick the takes and provenance chips are byte-unchanged AND still true (the
    chip is the whole-series range that spans the file now on screen)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/performance", wait_until="load")
        page.wait_for_selector("#g1Census", timeout=25000)
        page.wait_for_timeout(300)

        read = (
            "() => ({takes: [...document.querySelectorAll('.sf-take')].map(e => e.textContent),"
            " chips: [...document.querySelectorAll('.prov-chip')].map(e => e.textContent),"
            " step: (document.getElementById('perfStep') || {}).textContent || ''})"
        )
        first = page.evaluate(read)
        page.locator("#perfNext").click()  # a REAL tick of the master stepper
        page.wait_for_timeout(400)
        after = page.evaluate(read)

        # the stepper genuinely moved to another file
        assert after["step"] and after["step"] != first["step"], (first["step"], after["step"])
        stepped_file = re.search(r"—\s*(\S+\.xml)", after["step"])
        assert stepped_file is not None, after["step"]
        # ...and nothing this round rendered changed or became false
        assert after["takes"] == first["takes"]
        assert after["chips"] == first["chips"]
        for chip in after["chips"]:
            assert chip.startswith("v1→v2 · SOURCE: ")
            assert stepped_file.group(1) in chip, (chip, stepped_file.group(1))
        for take in after["takes"][1:]:  # [0] is the intro take, framed as the OPENING state
            assert not re.search(r"\.xml", take), take
        browser.close()


# ── ROUND-10 LEAD FIXES: two defects the round's own conversion INTRODUCED on this page ─────


def test_enlarging_a_tile_does_not_clip_its_chart_below_a_scroll_fold(served: str) -> None:
    """⛶ ENLARGE must show MORE of the chart, not a taller chart cut in half.

    ``.is-big`` (``base.css``: ``grid-column:1/-1``) widens a mosaic tile 546px → 1108px, and
    these charts are drawn WIDTH-proportional, so the SVG doubles in BOTH axes. Measured before
    the fix: svg 516x266 → 1078x556 inside a host still clamped to ``.mosaic .tile .chart-host
    {height:340px}`` — ``scrollHeight`` 340 → 560, i.e. ~40% of the enlarged chart (the whole X
    axis and every month tick) below a scroll fold. ``app.css`` now gives ``.is-big`` the same
    74vh host its ``.tile-expanded`` sibling has always had.

    Asserted as the INVARIANT (no fold), not as a pixel constant, so a future host-height
    change cannot silently re-open it.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/performance", wait_until="load")
        page.wait_for_selector("#g1Census", timeout=25000)
        page.wait_for_timeout(300)

        measure = (
            "() => { const t = document.querySelector('.tile.panel[data-export]');"
            " const h = t.querySelector('.chart-host');"
            " const s = h.querySelector('svg');"
            " return {tileW: Math.round(t.getBoundingClientRect().width),"
            "         clientH: h.clientHeight, scrollH: h.scrollHeight,"
            "         svgH: s ? Math.round(s.getBoundingClientRect().height) : 0}; }"
        )
        before = page.evaluate(measure)
        page.locator(".tile.panel[data-export] [data-sf-big]").first.click()
        page.wait_for_timeout(400)
        after = page.evaluate(measure)

        assert after["tileW"] > before["tileW"] + 100, (before, after)  # it really enlarged
        assert after["svgH"] > before["svgH"], (before, after)  # and the chart really regrew
        # THE FIX: the taller chart still fits its host — no hidden overflow.
        assert after["scrollH"] <= after["clientH"] + 2, (
            f"⛶ ENLARGE clips the chart: {after['scrollH'] - after['clientH']}px of the "
            f"enlarged svg sits below the fold ({after})"
        )
        browser.close()


def test_stepping_repoints_every_tile_export_at_the_file_its_chart_now_draws(
    served: str,
) -> None:
    """A forensic export control must never disagree with the visual it sits on.

    The server pins each tile's ``data-export`` to ``?file=<the file selected at RENDER time>``,
    but the master stepper re-binds G1-G5 to a DIFFERENT file with no reload — so before the fix
    the ⤓ beside a chart drawing ``Hard_File`` handed back ``Hard_File_updated3``'s datasets.
    ``performance.js``'s ``setVersion()`` now re-points every tile alongside the file caption it
    already writes. The stepped URL is fetched here too: honest AND alive, never a dead link.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/performance", wait_until="load")
        page.wait_for_selector("#g1Census", timeout=25000)
        page.wait_for_timeout(300)

        read = (
            "() => ({exports: [...document.querySelectorAll('#perfGrid [data-export]')]"
            "          .map(t => t.getAttribute('data-export')),"
            "         step: (document.getElementById('perfStep') || {}).textContent || '',"
            "         svg: [...document.querySelectorAll('#g1Census svg text')]"
            "          .map(n => n.textContent).join('|')})"
        )
        first = page.evaluate(read)
        page.locator("#perfNext").click()
        page.wait_for_timeout(500)
        after = page.evaluate(read)

        stepped = re.search(r"—\s*(\S+\.xml)", after["step"])
        assert stepped is not None, after["step"]
        assert after["svg"] != first["svg"], "the stepper did not actually re-bind the chart"
        assert len(after["exports"]) == len(MOUNTS)
        want = f"/export/xlsx/performance?file={quote(stepped.group(1), safe='')}"
        assert set(after["exports"]) == {want}, (after["exports"], want)
        # and it is a LIVE endpoint, not a plausible-looking dead one
        body = page.evaluate(
            "async (u) => { const r = await fetch(u); "
            "return {ok: r.status, n: (await r.arrayBuffer()).byteLength}; }",
            want,
        )
        assert body["ok"] == 200 and body["n"] > 1000, body
        browser.close()
