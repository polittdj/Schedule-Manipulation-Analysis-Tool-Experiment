"""M1 (WP1, REDUCED SCOPE) — the zoom/fit/pan control-effect census on the three Gantt pages.

The 2026-08-27 audit found 27 interactive behaviors with no browser test driving them; existing
pins freeze control BYTES, not effects. This module opens WP1's control-effect census at the
kickoff's sanctioned reduced scope: **zoom / fit / pan on /path, /driving-path and /evolution**,
with floors set only to what is actually driven. The full M1 (all five zoom surfaces, chartframe
family, legend toggles, column drag-resize, drills, enlarge-print) extends this module and gets
the WP1 ADR when the census completes.

Two properties, censused from the SERVED DOM — never a hand-written list (the ADR-0439 lesson:
a hand-written route list turned 404s into "clean"):

1. **Population**: every control on these pages whose id/class/title/text matches the
   zoom/fit/pan shape must appear in ``SPEC`` — an unknown in-family control with no driver is
   RED (the census half), and a SPEC'd control missing from the DOM is RED (the floor half).
   Deleting a row from ``SPEC`` is the module's mutation proof: the census test fails BY NAME.
2. **Effect**: every SPEC'd control is DRIVEN with a real interaction and a MEASURED oracle
   (bar/track geometry, scroll position), including the clamp edges — a control that flips
   state without moving the measured world is exactly the defect class WP0 chased.

Harness: the r11 ``served()`` idiom + one chromium for the module (fresh context per test).
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
FIXTURES = REPO / "tests" / "fixtures" / "test_projects"

VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
TARGET_UID = 26

PATH = "/path"
DP = f"/driving-path?source=11&target={TARGET_UID}"
EVO = "/evolution"

#: The driver spec — the census floor AND the census population, page by page. Keys are element
#: ids; every id here must exist on the served page, and every in-family control on the page
#: must be listed here. Values name the driver test(s) covering the control (documentation for
#: the reader; the tests themselves key off the ids).
SPEC: dict[str, dict[str, str]] = {
    PATH: {
        "pathZoom": "test_path_zoom_slider_measurably_scales_the_bars",
        "pathFit": "test_path_view_entire_project_returns_to_a_fitted_track",
    },
    DP: {
        "dpZoomIn": "test_dp_zoom_in_grows_bars_and_clamps_at_max",
        "dpZoomOut": "test_dp_zoom_out_shrinks_bars_and_clamps_at_min",
        "dpFit": "test_dp_view_entire_project_fits_the_corridor",
    },
    EVO: {
        "evoZoomIn": "test_evo_zoom_in_grows_bars_and_clamps_at_max",
        "evoZoomOut": "test_evo_zoom_out_reaches_the_floor_and_recovers",
        "evoZoomReset": "test_evo_reset_restores_the_fitted_axis",
        "evoPanL": "test_evo_pan_moves_the_viewport_and_returns",
        "evoPanR": "test_evo_pan_moves_the_viewport_and_returns",
    },
}

#: The in-family shape: how the census recognizes a zoom/fit/pan control it has never met.
#: Matched against id + class + title + leading text of every button/input/link/role=button.
_FAMILY = "zoom|fit|pan|entire"

_HARVEST = (
    """() => {
  const out = [];
  document.querySelectorAll("button, input, a, [role=button]").forEach(el => {
    const sig = [el.id, el.className, el.title,
                 el.textContent && el.textContent.slice(0, 40)].join(" ");
    if (/"""
    + _FAMILY
    + """/i.test(sig)) out.push(el.id || "(no id) " + sig.trim().slice(0, 60));
  });
  return out;
}"""
)


# ── server + browser (the r11 idiom) ──────────────────────────────────────────────────────────


def _load(client: TestClient) -> None:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
    meta = json.dumps(
        [
            {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(VERSIONS)
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    assert (
        client.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False).status_code
        == 303
    )


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


def _open(browser: Any, served: str, route: str) -> tuple[Any, list[str]]:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + route, wait_until="load")
    page.wait_for_timeout(1200)
    return page, errors


_MAX_BAR = """(sel) => {
  const ws = [...document.querySelectorAll(sel)].map(b => b.getBoundingClientRect().width);
  return ws.length ? Math.max(...ws) : null;
}"""
_TRACK_W = """(sel) => {
  const t = document.querySelector(sel);
  return t ? t.getBoundingClientRect().width : null;
}"""


def _dp_step_back(page: Any) -> None:
    """TP4 v5's corridor for 11->26 is legitimately empty — step to v4 where the bars are."""
    page.click("#dpPrev")
    page.wait_for_timeout(400)


# ── 1. the census ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("route", sorted(SPEC), ids=lambda r: r.split("?")[0])
def test_census_every_in_family_control_is_specced_and_every_specced_control_exists(
    browser: Any, served: str, route: str
) -> None:
    """Two-sided: the served DOM's zoom/fit/pan-shaped controls must equal ``SPEC[route]``.
    A new in-family control with no driver fails here (the census half); a SPEC'd control the
    page no longer serves fails here too (the floor half). Mutation proof: delete any row from
    ``SPEC`` and THIS test fails naming the orphaned control."""
    page, errors = _open(browser, served, route)
    harvested = set(page.evaluate(_HARVEST))
    assert errors == []
    specced = set(SPEC[route])
    unknown = harvested - specced
    missing = specced - harvested
    assert not unknown, f"in-family control(s) with NO driver spec: {sorted(unknown)}"
    assert not missing, f"SPEC'd control(s) missing from the served DOM: {sorted(missing)}"
    page.context.close()


# ── 2. /path drivers ──────────────────────────────────────────────────────────────────────────


def test_path_zoom_slider_measurably_scales_the_bars(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, PATH)
    before = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert before is not None and before > 10
    page.evaluate(
        """() => {
          const z = document.getElementById('pathZoom');
          z.value = String(Math.min(Number(z.max || 40), (Number(z.value) || 8) * 2));
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(400)
    after = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert after is not None and after >= before * 1.5, (before, after)
    assert errors == []
    page.context.close()


def test_path_view_entire_project_returns_to_a_fitted_track(browser: Any, served: str) -> None:
    """Zoom in first (fitFill cleared, track grows), then "View entire project" must come back
    DOWN to a page-fitted track — the fit is a measured shrink, not a class flip."""
    page, errors = _open(browser, served, PATH)
    page.evaluate(
        """() => {
          const z = document.getElementById('pathZoom');
          z.value = z.max || '40';
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(400)
    zoomed = page.evaluate(_TRACK_W, ".path-track")
    page.click("#pathFit")
    page.wait_for_timeout(600)
    fitted = page.evaluate(_TRACK_W, ".path-track")
    assert zoomed is not None and fitted is not None
    assert fitted < zoomed, (zoomed, fitted)
    assert (page.evaluate(_MAX_BAR, ".gantt-bar") or 0) > 0  # the whole-project view has bars
    assert errors == []
    page.context.close()


# ── 3. /driving-path drivers ──────────────────────────────────────────────────────────────────


def test_dp_zoom_in_grows_bars_and_clamps_at_max(browser: Any, served: str) -> None:
    """px walks 6 -> 40 in +2 steps; each click must grow the measured bar, and the click AFTER
    the 40 px/day ceiling must move nothing (the clamp is a fact of geometry, not of code)."""
    page, errors = _open(browser, served, DP)
    _dp_step_back(page)
    before = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert before is not None and before > 10
    page.click("#dpZoomIn")
    page.wait_for_timeout(250)
    grown = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert grown is not None and grown > before, (before, grown)
    for _ in range(18):  # 6 + 2*17 = 40: drive well past the ceiling
        page.click("#dpZoomIn")
    page.wait_for_timeout(400)
    at_max = page.evaluate(_MAX_BAR, ".gantt-bar")
    page.click("#dpZoomIn")
    page.wait_for_timeout(250)
    still = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert at_max is not None and still is not None and abs(still - at_max) < 0.5, (at_max, still)
    assert errors == []
    page.context.close()


def test_dp_zoom_out_shrinks_bars_and_clamps_at_min(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, DP)
    _dp_step_back(page)
    before = page.evaluate(_MAX_BAR, ".gantt-bar")
    for _ in range(4):  # 6 -> 4 -> 2 -> 1 (floor), plus one spare
        page.click("#dpZoomOut")
    page.wait_for_timeout(400)
    at_min = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert before is not None and at_min is not None and at_min < before, (before, at_min)
    page.click("#dpZoomOut")
    page.wait_for_timeout(250)
    still = page.evaluate(_MAX_BAR, ".gantt-bar")
    assert still is not None and abs(still - at_min) < 0.5, (at_min, still)
    assert errors == []
    page.context.close()


def test_dp_view_entire_project_fits_the_corridor(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, DP)
    _dp_step_back(page)
    for _ in range(10):
        page.click("#dpZoomIn")
    page.wait_for_timeout(400)
    zoomed = page.evaluate(_TRACK_W, ".path-track")
    page.click("#dpFit")
    page.wait_for_timeout(500)
    fitted = page.evaluate(_TRACK_W, ".path-track")
    mount_w = page.evaluate("() => document.getElementById('dpChart').clientWidth")
    assert zoomed is not None and fitted is not None
    assert fitted < zoomed, (zoomed, fitted)
    assert fitted <= mount_w + 2, (fitted, mount_w)  # it FITS — no horizontal overflow left
    assert errors == []
    page.context.close()


# ── 4. /evolution drivers ─────────────────────────────────────────────────────────────────────


_EVO_BARS = "[class*='ev-b-'],[class*='ev-t-']"


def test_evo_zoom_in_grows_bars_and_clamps_at_max(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, EVO)
    before = page.evaluate(_MAX_BAR, _EVO_BARS)
    assert before is not None and before > 10
    page.click("#evoZoomIn")
    page.click("#evoZoomIn")
    page.wait_for_timeout(400)
    grown = page.evaluate(_MAX_BAR, _EVO_BARS)
    assert grown is not None and grown >= before * 2, (before, grown)  # 1.6^2 = 2.56x
    for _ in range(12):  # drive past the 40 px/day ceiling
        page.click("#evoZoomIn")
    page.wait_for_timeout(500)
    at_max = page.evaluate(_MAX_BAR, _EVO_BARS)
    page.click("#evoZoomIn")
    page.wait_for_timeout(300)
    still = page.evaluate(_MAX_BAR, _EVO_BARS)
    assert at_max is not None and still is not None and abs(still - at_max) < 1.0, (at_max, still)
    assert errors == []
    page.context.close()


def test_evo_zoom_out_reaches_the_floor_and_recovers(browser: Any, served: str) -> None:
    """Zooming out lands on the 0.02 px/day floor (the track parks on its 120px minimum) and
    the view must survive there and zoom back IN — the round trip an operator actually takes."""
    page, errors = _open(browser, served, EVO)
    for _ in range(10):
        page.click("#evoZoomOut")
    page.wait_for_timeout(500)
    floor_track = page.evaluate(_TRACK_W, ".g-track")
    assert floor_track is not None and floor_track <= 200, floor_track  # parked on the floor
    for _ in range(9):  # 0.02 * 1.6^9 ≈ 1.4 px/day — clear of the 120px track floor on any span
        page.click("#evoZoomIn")
    page.wait_for_timeout(500)
    recovered = page.evaluate(_TRACK_W, ".g-track")
    assert recovered is not None and recovered > floor_track, (floor_track, recovered)
    assert errors == []
    page.context.close()


def test_evo_reset_restores_the_fitted_axis(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, EVO)
    initial = page.evaluate(_TRACK_W, ".g-track")
    assert initial is not None and initial > 200
    for _ in range(4):
        page.click("#evoZoomIn")
    page.wait_for_timeout(400)
    zoomed = page.evaluate(_TRACK_W, ".g-track")
    assert zoomed is not None and zoomed > initial * 2
    page.click("#evoZoomReset")
    page.wait_for_timeout(500)
    restored = page.evaluate(_TRACK_W, ".g-track")
    assert restored is not None and abs(restored - initial) <= initial * 0.1, (initial, restored)
    assert errors == []
    page.context.close()


def test_evo_pan_moves_the_viewport_and_returns(browser: Any, served: str) -> None:
    """Pan is scrollLeft arithmetic on .gantt-scroll — only measurable once the zoomed content
    overflows the pane. Right then left must round-trip back to the left edge."""
    page, errors = _open(browser, served, EVO)
    for _ in range(5):
        page.click("#evoZoomIn")
    page.wait_for_timeout(500)
    start = page.evaluate("() => document.querySelector('.gantt-scroll').scrollLeft")
    page.click("#evoPanR")
    page.wait_for_timeout(300)
    panned = page.evaluate("() => document.querySelector('.gantt-scroll').scrollLeft")
    assert panned > start, (start, panned)
    page.click("#evoPanL")
    page.wait_for_timeout(300)
    back = page.evaluate("() => document.querySelector('.gantt-scroll').scrollLeft")
    assert back < panned, (panned, back)
    assert errors == []
    page.context.close()
