"""M1 (WP1, FULL SCOPE) — the sitewide UI control-effect census, computed from the served DOM.

The 2026-08-27 audit found 27 interactive behaviors with no browser test driving them; existing
pins freeze control BYTES, not effects. The reduced census (zoom/fit/pan on the three Gantt
pages, 12 drivers) landed with WP0; THIS is the full M1: every HTML page the app serves is
censused, and every in-family control is either DRIVEN here with a measured oracle or carries
an explicit, dated deferral to its campaign work package. Nothing is allowed to be unknown.

Three layers, none hand-derivable (the ADR-0439 lesson — a hand-written route list turned 404s
into "clean"):

1. **Page population is computed from the app's own route table** (every GET route whose
   response_class is HTMLResponse), plus explicitly-listed extra STATES of a route that serve a
   different control population (``/driving-path`` with a trace serves dp* controls; plain, it
   falls back to the /path workspace). A new page with no census row is RED; a census row for a
   page the app no longer serves is RED.
2. **Control population is harvested from the served DOM** per page: every control whose
   id/class matches the family shape (zoom / fit / pan / entire / play / prev / next / step /
   cf-btn) must equal the census row — ids exactly, id-less controls (chartframe ``cf-btn``,
   the shared ``sf-frame`` steppers) by class identity and exact count. An unknown in-family
   control is RED (the census half); a censused control missing from the DOM is RED (the floor
   half). Deleting any row is the module's mutation proof: the census fails BY NAME.
3. **Structural floors** per page pin the non-family interaction surfaces the drivers cover as
   FAMILIES (chart hosts, chartframe bars, legend toggles, column-resize grips, sticky
   scrollbars, drill triggers, enlarge buttons): a page may gain instances without a census
   edit (the family driver covers them), but losing any is RED.

Every censused control id maps to the driver test that measures its EFFECT (bar/track/scroll
geometry — a control that flips state without moving the measured world is exactly the WP0
defect class), or to an explicit deferral marker naming the campaign package that drives it
(``WP2:M3`` steppers/autoplay clock-stepped, ``WP2:M5`` the mission wall's own tile system).
``test_every_declared_driver_exists`` makes a typo'd driver name RED.

Harness: the r11 ``served()`` idiom + one chromium for the module (fresh context per test).
The census walk reuses ONE context; pages with async tiles are polled until two consecutive
harvests agree. Zero pageerrors is asserted on every page — measured true sitewide today.
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
ANALYSIS = "/analysis/{name}"

#: Extra per-route STATES whose control population differs from the bare route's (layer 1).
EXTRA_STATES = [DP]

#: Structural-floor legend — the tuple order in every census row's "floors" entry.
FLOOR_KEYS = (
    ".chart-host",
    ".cf-bar",
    "[data-series-toggle]",
    "[data-series-all]",
    ".col-rsz",
    ".sf-sticky-xscroll",
    ".sf-drill",
    "[data-sf-big], .tile-expand",
)

#: Deferral markers (allowed as driver values): the campaign package that owns the driver.
WP2_M3 = "WP2:M3 stepper/autoplay clock-stepped driver (queued)"
WP2_M5 = "WP2:M5 mission-wall pass (tile system owns these)"
#: Cross-reference markers: the control is the /path workspace served under another route, or
#: a stepper this module already exercises as driver infrastructure.
SAME_AS_PATH = "= /path workspace (same path.js machinery; driven by the /path drivers)"
DP_STEP_BACK = "= exercised as step-back infrastructure by all three dp drivers"

#: The census: one row per served page state. "ids": in-family controls WITH an id -> driver
#: test in this module, or a deferral/cross-reference marker. "anon": id-less in-family
#: controls by class identity -> (exact count, driver/marker). "floors": FLOOR_KEYS minimums.
#: Baseline measured from the served DOM on the TP4 five-version corpus, target 26, 1440x900.
CF_DRIVER = "test_chartframe_zoom_in_grows_the_svg_and_reset_restores"
CF_FS_DRIVER = "test_chartframe_fullscreen_toggles_and_returns"
CENSUS: dict[str, dict[str, Any]] = {
    "/launch": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 0)},
    "/": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 15, 1)},
    ANALYSIS: {
        "ids": {
            "fitBtn": "test_viz_fit_project_shrinks_the_scale_to_the_page",
            "zoomIn": "test_viz_zoom_steps_scale_the_grid_bars",
            "zoomOut": "test_viz_zoom_steps_scale_the_grid_bars",
        },
        "anon": {
            "cf-btn:Full screen": (3, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (3, CF_DRIVER),
            "cf-btn:Zoom in": (3, CF_DRIVER),
            "cf-btn:Zoom out": (3, CF_DRIVER),
        },
        "floors": (3, 3, 0, 0, 12, 2, 0, 17),
    },
    "/card/{name}": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 3)},
    "/wbs/{name}": {
        "ids": {},
        "anon": {
            "cf-btn:Full screen": (1, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (1, CF_DRIVER),
            "cf-btn:Zoom in": (1, CF_DRIVER),
            "cf-btn:Zoom out": (1, CF_DRIVER),
        },
        "floors": (1, 1, 0, 0, 0, 0, 8, 3),
    },
    "/standards": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 3)},
    "/portfolio": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 2)},
    "/mission": {
        "ids": {
            "autoPlay": WP2_M3,
            "driftPlay": WP2_M3,
            "evoPlay": WP2_M3,
            "missionPlay": WP2_M3,
            "missionStep": WP2_M3,
            "nextDrift": WP2_M3,
            "nextEvo": WP2_M3,
            "nextScurve": WP2_M3,
            "nextSnap": WP2_M3,
            "prevDrift": WP2_M3,
            "prevEvo": WP2_M3,
            "prevScurve": WP2_M3,
            "prevSnap": WP2_M3,
            "qualNext": WP2_M3,
            "qualPlay": WP2_M3,
            "qualPrev": WP2_M3,
            "scurvePlay": WP2_M3,
        },
        "anon": {
            ".sf-frame-next": (23, WP2_M3),
            ".sf-frame-play": (23, WP2_M3),
            ".sf-frame-prev": (23, WP2_M3),
            "cf-btn:Full screen": (9, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (9, CF_DRIVER),
            "cf-btn:Zoom in": (9, CF_DRIVER),
            "cf-btn:Zoom out": (9, CF_DRIVER),
        },
        # 30 chart hosts but only 9 chartframe bars: the 21 async-fetched tiles are never
        # framed (no zoom/fullscreen toolbar) — an OBSERVED gap logged in the WP1 UI map,
        # deliberately not "fixed" blind (the wall has its own tile-expand system).
        "floors": (30, 9, 30, 11, 7, 1, 76, 30),
    },
    "/compare": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 3)},
    PATH: {
        "ids": {
            "pathFit": "test_path_view_entire_project_returns_to_a_fitted_track",
            "pathZoom": "test_path_zoom_slider_measurably_scales_the_bars",
        },
        "anon": {},
        "floors": (0, 0, 0, 0, 8, 1, 0, 1),
    },
    "/trend": {
        "ids": {
            "qualNext": WP2_M3,
            "qualPlay": WP2_M3,
            "qualPrev": WP2_M3,
            "sfPlayAll": WP2_M3,
            "sfStepAll": WP2_M3,
        },
        "anon": {
            ".sf-frame-next": (21, WP2_M3),
            ".sf-frame-play": (21, WP2_M3),
            ".sf-frame-prev": (21, WP2_M3),
            "cf-btn:Full screen": (2, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (2, CF_DRIVER),
            "cf-btn:Zoom in": (2, CF_DRIVER),
            "cf-btn:Zoom out": (2, CF_DRIVER),
        },
        "floors": (2, 2, 27, 10, 0, 0, 69, 26),
    },
    "/margin": {
        "ids": {},
        "anon": {
            "cf-btn:Full screen": (2, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (2, CF_DRIVER),
            "cf-btn:Zoom in": (2, CF_DRIVER),
            "cf-btn:Zoom out": (2, CF_DRIVER),
        },
        "floors": (2, 2, 8, 2, 0, 0, 0, 4),
    },
    "/evm": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 5)},
    "/resources": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 0)},
    "/cei": {
        "ids": {"autoPlay": WP2_M3, "nextSnap": WP2_M3, "prevSnap": WP2_M3},
        "anon": {
            "cf-btn:Full screen": (1, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (1, CF_DRIVER),
            "cf-btn:Zoom in": (1, CF_DRIVER),
            "cf-btn:Zoom out": (1, CF_DRIVER),
        },
        "floors": (1, 1, 3, 1, 0, 0, 13, 2),
    },
    "/scurve": {
        "ids": {"nextScurve": WP2_M3, "prevScurve": WP2_M3, "scurvePlay": WP2_M3},
        "anon": {
            "cf-btn:Full screen": (1, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (1, CF_DRIVER),
            "cf-btn:Zoom in": (1, CF_DRIVER),
            "cf-btn:Zoom out": (1, CF_DRIVER),
        },
        "floors": (1, 1, 0, 0, 0, 0, 0, 2),
    },
    "/ribbon": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 1)},
    "/volatility": {
        "ids": {"volNext": WP2_M3, "volPlay": WP2_M3, "volPrev": WP2_M3},
        "anon": {
            "cf-btn:Full screen": (10, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (10, CF_DRIVER),
            "cf-btn:Zoom in": (10, CF_DRIVER),
            "cf-btn:Zoom out": (10, CF_DRIVER),
        },
        "floors": (10, 10, 0, 0, 0, 0, 18, 10),
    },
    "/performance": {
        "ids": {"perfNext": WP2_M3, "perfPlay": WP2_M3, "perfPrev": WP2_M3},
        "anon": {
            "cf-btn:Full screen": (14, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (14, CF_DRIVER),
            "cf-btn:Zoom in": (14, CF_DRIVER),
            "cf-btn:Zoom out": (14, CF_DRIVER),
        },
        "floors": (14, 14, 41, 9, 0, 0, 31, 14),
    },
    EVO: {
        "ids": {
            "evoPanL": "test_evo_pan_moves_the_viewport_and_returns",
            "evoPanR": "test_evo_pan_moves_the_viewport_and_returns",
            "evoPlay": WP2_M3,
            "evoZoomIn": "test_evo_zoom_in_grows_bars_and_clamps_at_max",
            "evoZoomOut": "test_evo_zoom_out_reaches_the_floor_and_recovers",
            "evoZoomReset": "test_evo_reset_restores_the_fitted_axis",
            "nextEvo": WP2_M3,
            "prevEvo": WP2_M3,
            "volNext": WP2_M3,
            "volPlay": WP2_M3,
            "volPrev": WP2_M3,
        },
        "anon": {
            "cf-btn:Full screen": (4, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (4, CF_DRIVER),
            "cf-btn:Zoom in": (4, CF_DRIVER),
            "cf-btn:Zoom out": (4, CF_DRIVER),
        },
        "floors": (4, 4, 0, 0, 7, 1, 12, 6),
    },
    "/integrity": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 2)},
    "/driving-path": {
        "ids": {"pathFit": SAME_AS_PATH, "pathZoom": SAME_AS_PATH},
        "anon": {},
        "floors": (0, 0, 0, 0, 8, 1, 0, 1),
    },
    "/groups": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 1)},
    "/forecast": {
        "ids": {"driftPlay": WP2_M3, "nextDrift": WP2_M3, "prevDrift": WP2_M3},
        "anon": {
            "cf-btn:Full screen": (1, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (1, CF_DRIVER),
            "cf-btn:Zoom in": (1, CF_DRIVER),
            "cf-btn:Zoom out": (1, CF_DRIVER),
        },
        "floors": (1, 1, 0, 0, 0, 0, 0, 5),
    },
    "/curves": {
        "ids": {"sfPlayAll": WP2_M3, "sfStepAll": WP2_M3},
        "anon": {
            ".sf-frame-next": (2, WP2_M3),
            ".sf-frame-play": (2, WP2_M3),
            ".sf-frame-prev": (2, WP2_M3),
            "cf-btn:Full screen": (3, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (3, CF_DRIVER),
            "cf-btn:Zoom in": (3, CF_DRIVER),
            "cf-btn:Zoom out": (3, CF_DRIVER),
        },
        "floors": (3, 3, 0, 0, 0, 0, 0, 3),
    },
    "/workbench": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 1)},
    "/scorecards": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 6, 4)},
    "/brief": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 7)},
    "/risks": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 7)},
    "/sra": {
        "ids": {
            "ssiGridFit": "test_sra_grid_fit_shrinks_the_scale_to_the_pane",
            "ssiGridZoom": "test_sra_grid_zoom_slider_scales_the_bars",
        },
        "anon": {
            "cf-btn:Full screen": (4, CF_FS_DRIVER),
            "cf-btn:Reset zoom": (4, CF_DRIVER),
            "cf-btn:Zoom in": (4, CF_DRIVER),
            "cf-btn:Zoom out": (4, CF_DRIVER),
        },
        "floors": (4, 4, 0, 0, 7, 0, 19, 12),
    },
    "/briefing": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 1)},
    "/settings": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 0)},
    "/help": {"ids": {}, "anon": {}, "floors": (0, 0, 0, 0, 0, 0, 0, 0)},
    DP: {
        "ids": {
            "dpFit": "test_dp_view_entire_project_fits_the_corridor",
            "dpNext": WP2_M3,
            "dpPlay": WP2_M3,
            "dpPrev": DP_STEP_BACK,
            "dpZoomIn": "test_dp_zoom_in_grows_bars_and_clamps_at_max",
            "dpZoomOut": "test_dp_zoom_out_shrinks_bars_and_clamps_at_min",
        },
        "anon": {},
        "floors": (0, 0, 0, 0, 0, 1, 0, 3),
    },
}

#: The in-family shape (layer 2). Matched against id + className ONLY — free text and tooltips
#: carry schedule data and prose that false-positive ("Fit-Out" in a project name, "dis-play-",
#: "s-pan-" inside help text; measured 2026-08-31), and tooltips.js MOVES title= into
#: data-sf-title at load, so attribute text is not a stable signature either. ``pan(?!d)``
#: keeps evoPanL/R while excluding every "expand". cf-btn identifies the chartframe toolbar,
#: whose four buttons carry aria-labels, not ids.
_FAMILY = r"zoom|fit|pan(?!d)|entire|play|prev|next|step|cf-btn"

_HARVEST = (
    """() => {
  const fam = /"""
    + _FAMILY
    + """/i;
  const ids = [], anon = {};
  document.querySelectorAll("button, input:not([type=hidden]), [role=button]").forEach(el => {
    if (!fam.test(el.id + " " + el.className)) return;
    if (el.id) { ids.push(el.id); return; }
    const cls = String(el.className);
    const key = cls.indexOf("cf-btn") >= 0
      ? "cf-btn:" + (el.getAttribute("aria-label") || el.title || el.textContent.trim())
      : "." + cls.trim().split(/\\s+/).sort().join(".");
    anon[key] = (anon[key] || 0) + 1;
  });
  const q = sel => document.querySelectorAll(sel).length;
  return {ids: ids.sort(), anon,
          floors: [q(".chart-host"), q(".cf-bar"), q("[data-series-toggle]"),
                   q("[data-series-all]"), q(".col-rsz"), q(".sf-sticky-xscroll"),
                   q(".sf-drill"), q("[data-sf-big], .tile-expand")]};
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


NEWEST = f"TP4_DataCenter_v{len(VERSIONS)}"


def _fill(route: str) -> str:
    return route.replace("{name}", NEWEST)


def _open(browser: Any, served: str, route: str) -> tuple[Any, list[str]]:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + _fill(route), wait_until="load")
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


def test_census_pages_match_the_served_route_table() -> None:
    """Layer 1, both halves: the census's page keys must equal the app's computed HTML route
    table (plus the declared EXTRA_STATES). A new HTML page with no census row fails here BY
    NAME; a census row for a route the app no longer serves fails here too."""
    from fastapi.routing import APIRoute
    from starlette.responses import HTMLResponse

    app = create_app(SessionState())
    computed = set()
    for r in app.routes:
        if not isinstance(r, APIRoute) or "GET" not in r.methods:
            continue
        rc = r.response_class
        if not (isinstance(rc, type) and issubclass(rc, HTMLResponse)):
            continue
        assert "{" not in r.path.replace("{name}", ""), f"unfillable param route: {r.path}"
        computed.add(r.path)
    expected = computed | set(EXTRA_STATES)
    uncensused = expected - set(CENSUS)
    stale = set(CENSUS) - expected
    assert not uncensused, f"served HTML page(s) with NO census row: {sorted(uncensused)}"
    assert not stale, f"census row(s) for pages the app no longer serves: {sorted(stale)}"


def test_every_declared_driver_exists() -> None:
    """A census row naming a driver test that does not exist is a lie the census would never
    catch on its own — resolve every ``test_*`` driver value against this module."""
    missing = []
    for route, spec in CENSUS.items():
        drivers = list(spec["ids"].values()) + [d for _, d in spec["anon"].values()]
        for d in drivers:
            if d.startswith("test_") and d not in globals():
                missing.append((route, d))
    assert not missing, f"census rows name non-existent driver test(s): {missing}"


@pytest.mark.parametrize(
    "route", sorted(CENSUS), ids=lambda r: r.replace("/", "_").replace("?", "_q_")
)
def test_census_every_in_family_control_is_specced_and_every_specced_control_exists(
    browser: Any, served: str, route: str
) -> None:
    """Layers 2+3: the served DOM's in-family controls must equal ``CENSUS[route]`` — ids
    exactly, id-less identities by exact count — and the structural floors must hold. A new
    in-family control with no driver fails here (the census half); a censused control the page
    no longer serves fails here too (the floor half). Mutation proof: delete any row or dock
    any floor and THIS test fails naming the control. Zero pageerrors sitewide is part of the
    pin (measured true on every page today)."""
    page, errors = _open(browser, served, route)
    h = page.evaluate(_HARVEST)
    for _ in range(8):  # async pages (/mission tiles) settle late — poll to agreement
        page.wait_for_timeout(600)
        h2 = page.evaluate(_HARVEST)
        if h2 == h:
            break
        h = h2
    spec = CENSUS[route]
    assert errors == [], f"pageerror(s) on {route}: {errors}"
    harvested_ids = set(h["ids"])
    specced_ids = set(spec["ids"])
    unknown = harvested_ids - specced_ids
    missing = specced_ids - harvested_ids
    assert not unknown, f"{route}: in-family control(s) with NO driver spec: {sorted(unknown)}"
    assert not missing, (
        f"{route}: censused control(s) missing from the served DOM: {sorted(missing)}"
    )
    spec_anon = {k: n for k, (n, _) in spec["anon"].items()}
    assert h["anon"] == spec_anon, (
        f"{route}: id-less in-family population moved: served {h['anon']} != census {spec_anon}"
    )
    for key, floor, got in zip(FLOOR_KEYS, spec["floors"], h["floors"], strict=True):
        assert got >= floor, f"{route}: {key} fell below its floor: {got} < {floor}"
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


# ── 5. /analysis drivers (the #vizZoom surface: hidden input, ± buttons, Fit) ─────────────────


def test_viz_zoom_steps_scale_the_grid_bars(browser: Any, served: str) -> None:
    """#zoomIn/#zoomOut step the hidden #vizZoom px/day by 1.25x — the measured activity-grid
    bar must grow on + and come back down on -."""
    page, errors = _open(browser, served, ANALYSIS)
    page.wait_for_selector("#grid .g-bar", timeout=30000)
    before = page.evaluate(_MAX_BAR, "#grid .g-bar")
    assert before is not None and before > 5
    page.click("#zoomIn")
    page.wait_for_timeout(500)
    grown = page.evaluate(_MAX_BAR, "#grid .g-bar")
    assert grown is not None and grown >= before * 1.15, (before, grown)
    page.click("#zoomOut")
    page.wait_for_timeout(500)
    back = page.evaluate(_MAX_BAR, "#grid .g-bar")
    assert back is not None and back < grown, (grown, back)
    assert errors == []
    page.context.close()


def test_viz_fit_project_shrinks_the_scale_to_the_page(browser: Any, served: str) -> None:
    """Zoom in far (the scale overflows the pane), then "Fit project" must bring the timeline
    back DOWN — a measured shrink of the #grid scale, with bars still painted."""
    page, errors = _open(browser, served, ANALYSIS)
    page.wait_for_selector("#grid .g-bar", timeout=30000)
    for _ in range(6):
        page.click("#zoomIn")
    page.wait_for_timeout(600)
    zoomed = page.evaluate(_TRACK_W, "#grid .g-scale")
    page.click("#fitBtn")
    page.wait_for_timeout(700)
    fitted = page.evaluate(_TRACK_W, "#grid .g-scale")
    assert zoomed is not None and fitted is not None
    assert fitted < zoomed, (zoomed, fitted)
    assert (page.evaluate(_MAX_BAR, "#grid .g-bar") or 0) > 0
    assert errors == []
    page.context.close()


# ── 6. /sra grid drivers (the fifth zoom surface) ─────────────────────────────────────────────


def test_sra_grid_zoom_slider_scales_the_bars(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, "/sra")
    page.wait_for_selector("#ssiGrid .g-bar", timeout=30000)
    before = page.evaluate(_MAX_BAR, "#ssiGrid .g-bar")
    assert before is not None and before > 5
    page.evaluate(
        """() => {
          const z = document.getElementById('ssiGridZoom');
          z.value = String(Math.min(Number(z.max || 6), Number(z.value) * 2));
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(600)
    after = page.evaluate(_MAX_BAR, "#ssiGrid .g-bar")
    assert after is not None and after >= before * 1.5, (before, after)
    assert errors == []
    page.context.close()


def test_sra_grid_fit_shrinks_the_scale_to_the_pane(browser: Any, served: str) -> None:
    page, errors = _open(browser, served, "/sra")
    page.wait_for_selector("#ssiGrid .g-bar", timeout=30000)
    page.evaluate(
        """() => {
          const z = document.getElementById('ssiGridZoom');
          z.value = z.max || '6';
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(600)
    zoomed = page.evaluate(_TRACK_W, "#ssiGrid .g-scale")
    page.click("#ssiGridFit")
    page.wait_for_timeout(600)
    fitted = page.evaluate(_TRACK_W, "#ssiGrid .g-scale")
    host_w = page.evaluate("() => document.getElementById('ssiGrid').clientWidth")
    assert zoomed is not None and fitted is not None
    assert fitted < zoomed, (zoomed, fitted)
    assert fitted <= host_w + 2, (fitted, host_w)
    assert errors == []
    page.context.close()


# ── 7. the Timescale Size % multiplier, driven on all five consumer pages ─────────────────────


def test_timescale_size_multiplier_scales_all_five_consumer_pages(
    browser: Any, served: str
) -> None:
    """sizeFactor() multiplies the axis px on every Gantt (app.js /analysis, path.js,
    driving_path.js, path_evolution.js, sra_grid.js). Seed size=200 via add_init_script
    (localStorage is read at script PARSE time — the WP0 trap) and the measured scale width
    must come out ~2x the default on each page. Ratios measured 1.94-2.0 on 2026-08-31."""
    cases = [
        (ANALYSIS, "#grid .g-scale", False),
        (PATH, ".path-track", False),
        (DP, "#dpChart .path-track", True),  # newest version's corridor is empty — step back
        (EVO, ".g-track", False),
        ("/sra", "#ssiGrid .g-scale", False),
    ]
    for route, sel, step_back in cases:
        widths = {}
        for label, seed in (("default", None), ("size200", '{"size": 200}')):
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            if seed is not None:
                ctx.add_init_script(
                    f"try {{ localStorage.setItem('sf.timescale.v1', '{seed}'); }} catch (e) {{}}"
                )
            page = ctx.new_page()
            page.goto(served + _fill(route), wait_until="load")
            page.wait_for_timeout(1500)
            if step_back:
                _dp_step_back(page)
            widths[label] = page.evaluate(_TRACK_W, sel)
            ctx.close()
        assert widths["default"] and widths["size200"], (route, widths)
        ratio = widths["size200"] / widths["default"]
        assert 1.7 <= ratio <= 2.3, f"{route}: Size 200% scaled the axis by {ratio:.2f}x ({widths})"


# ── 8. chartframe family drivers (the -/+/Reset/full-screen bar on every .chart-host) ────────


def _cf_btn(page: Any, label: str) -> Any:
    return page.locator(f'.cf-bar .cf-btn[aria-label="{label}"]').first


def test_chartframe_zoom_in_grows_the_svg_and_reset_restores(browser: Any, served: str) -> None:
    """The shared chartframe toolbar: the plus button multiplies the chart SVG's width (1.25x
    steps, the % label follows), Reset returns to 100%. Driven on /margin's first chart; every
    .chart-host sitewide gets the same toolbar (the census floors pin how many)."""
    page, errors = _open(browser, served, "/margin")
    page.wait_for_selector(".chart-host svg", timeout=30000)
    before = page.evaluate(_TRACK_W, ".chart-host svg")
    assert before is not None and before > 100
    _cf_btn(page, "Zoom in").click()
    page.wait_for_timeout(400)
    grown = page.evaluate(_TRACK_W, ".chart-host svg")
    assert grown is not None and grown >= before * 1.15, (before, grown)
    label = page.locator(".cf-bar .cf-zoom").first.text_content()
    assert label == "125%", label
    _cf_btn(page, "Reset zoom").click()
    page.wait_for_timeout(400)
    restored = page.evaluate(_TRACK_W, ".chart-host svg")
    assert restored is not None and abs(restored - before) <= before * 0.05, (before, restored)
    assert page.locator(".cf-bar .cf-zoom").first.text_content() == "100%"
    assert errors == []
    page.context.close()


def test_chartframe_fullscreen_toggles_and_returns(browser: Any, served: str) -> None:
    """⤢ enters full screen (the Fullscreen API, or the cf-max fixed-position fallback when the
    API is denied — headless takes either branch) and the same button leaves it. The measured
    fact: the frame's rect grows to ~the viewport and comes back."""
    page, errors = _open(browser, served, "/margin")
    page.wait_for_selector(".chart-host svg", timeout=30000)
    state = """() => {
      const w = document.querySelector('.cf-frame');
      const r = w.getBoundingClientRect();
      return {fs: document.fullscreenElement === w, max: w.classList.contains('cf-max'),
              w: Math.round(r.width), h: Math.round(r.height)};
    }"""
    before = page.evaluate(state)
    assert not before["fs"] and not before["max"]
    _cf_btn(page, "Full screen").click()
    page.wait_for_timeout(600)
    entered = page.evaluate(state)
    assert entered["fs"] or entered["max"], entered
    assert entered["w"] >= before["w"], (before, entered)
    page.locator('.cf-bar .cf-btn[aria-label="Full screen"]').first.click()
    page.wait_for_timeout(600)
    left = page.evaluate(state)
    assert not left["fs"] and not left["max"], left
    assert errors == []
    page.context.close()


# ── 9. legend toggles ─────────────────────────────────────────────────────────────────────────


def test_legend_toggle_hides_the_series_and_show_all_restores(browser: Any, served: str) -> None:
    """SFLegend: clicking a legend entry display:none's its [data-series] elements (a VIEW
    filter — the data table and export are untouched); clicking again restores; the
    [data-series-all] control round-trips hide-all/show-all. Driven on /trend."""
    page, errors = _open(browser, served, "/trend")
    page.wait_for_selector("[data-series-toggle]", timeout=30000)
    picked = page.evaluate(
        """() => {
      const items = [...document.querySelectorAll('[data-series-toggle]')];
      for (const it of items) {
        const key = it.getAttribute('data-series-toggle');
        let scope = it.closest('[data-series-scope]');
        if (!scope) {
          let n = it;
          while (n && n.querySelector) {
            if (n.querySelector('[data-series]')) { scope = n; break; }
            n = n.parentNode;
          }
        }
        if (!scope) continue;
        const els = scope.querySelectorAll('[data-series="' + CSS.escape(key) + '"]');
        if (els.length) {
          it.setAttribute('data-census-pick', '1');
          scope.setAttribute('data-census-scope', '1');
          return {key, series: els.length};
        }
      }
      return null;
    }"""
    )
    assert picked and picked["series"] > 0, "no legend entry with resolvable series on /trend"
    visible = """() => {
      const scope = document.querySelector('[data-census-scope]');
      const key = document.querySelector('[data-census-pick]').getAttribute('data-series-toggle');
      const els = [...scope.querySelectorAll('[data-series="' + CSS.escape(key) + '"]')];
      return els.filter(e => e.style.display !== 'none').length;
    }"""
    assert page.evaluate(visible) == picked["series"]
    page.locator("[data-census-pick]").click()
    page.wait_for_timeout(300)
    assert page.evaluate(visible) == 0, "toggled series still displayed"
    page.locator("[data-census-pick]").click()
    page.wait_for_timeout(300)
    assert page.evaluate(visible) == picked["series"], "series did not come back"
    # show-all/none round trip on the same scope's [data-series-all], when it has one
    has_all = page.evaluate(
        "() => !!document.querySelector('[data-census-scope] [data-series-all]')"
    )
    if has_all:
        page.locator("[data-census-scope] [data-series-all]").first.click()
        page.wait_for_timeout(300)
        assert page.evaluate(visible) == 0, "hide-all left the series displayed"
        page.locator("[data-census-scope] [data-series-all]").first.click()
        page.wait_for_timeout(300)
        assert page.evaluate(visible) == picked["series"], "show-all did not restore"
    assert errors == []
    page.context.close()


# ── 10. column drag-resize ────────────────────────────────────────────────────────────────────


def test_column_drag_resize_widens_the_column_and_clamps(browser: Any, served: str) -> None:
    """SFColResize: dragging a header grip resizes exactly that column (fixed layout — the
    others hold), and a hard leftward drag clamps at the 28px minimum."""
    page, errors = _open(browser, served, PATH)
    page.wait_for_selector(".path-grid .col-rsz", timeout=30000)
    # raw mouse drags need in-viewport coordinates — scroll the grid up first (the WP0 trap:
    # the KPI block fills the first viewport and the grid header sits below the fold)
    page.evaluate("() => document.querySelector('.path-grid').scrollIntoView()")
    page.evaluate("() => window.scrollBy(0, -40)")
    page.wait_for_timeout(400)
    # column 1 (UID): the Name column carries its own CSS min-width:200px which out-floors the
    # JS 28px clamp — the clamp is only measurable on a column with no CSS floor of its own
    handle = page.locator(".path-grid thead th:nth-child(1) .col-rsz")
    th_w = (
        "() => document.querySelector('.path-grid thead th:nth-child(1)')"
        ".getBoundingClientRect().width"
    )
    before = page.evaluate(th_w)
    box = handle.bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 60, cy, steps=4)
    page.mouse.up()
    page.wait_for_timeout(300)
    widened = page.evaluate(th_w)
    assert widened is not None and abs(widened - (before + 60)) <= 6, (before, widened)
    box = handle.bounding_box()
    assert box is not None
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx - 500, cy, steps=4)
    page.mouse.up()
    page.wait_for_timeout(300)
    # two clamp signatures: the JS floor pins the styled width at 28px, and the measured
    # geometry lands on a small stable floor (Chromium adds its own min-content floor on
    # cells, ~53px here) instead of following the -500px drag
    style_w = page.evaluate(
        "() => document.querySelector('.path-grid thead th:nth-child(1)').style.width"
    )
    assert style_w == "28px", f"JS min clamp did not engage: styled {style_w}"
    clamped = page.evaluate(th_w)
    assert clamped is not None and 20 <= clamped <= 60, f"measured floor unreasonable: {clamped}"
    assert clamped < widened, (widened, clamped)
    assert errors == []
    page.context.close()


# ── 11. sticky-scrollbar sync ─────────────────────────────────────────────────────────────────


def test_sticky_scrollbar_mirrors_and_drives_the_pane(browser: Any, served: str) -> None:
    """SFGantt.stickyScrollbar: the viewport-bottom proxy mirrors the pane's scrollLeft AND
    drives it — both directions measured. The proxy only shows when the pane overflows and is
    on screen, so zoom in first and scroll the grid into view (the WP0 KPI-block trap)."""
    page, errors = _open(browser, served, PATH)
    page.evaluate(
        """() => {
          const z = document.getElementById('pathZoom');
          z.value = z.max || '40';
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(600)
    page.evaluate("() => document.querySelector('.path-grid').scrollIntoView()")
    page.evaluate("() => window.scrollBy(0, -60)")
    page.wait_for_timeout(600)
    shown = page.evaluate(
        """() => { const b = document.querySelector('.sf-sticky-xscroll');
                   return b && b.style.display !== 'none' && b.offsetHeight > 0; }"""
    )
    assert shown, "sticky proxy scrollbar not visible over an overflowing on-screen pane"
    page.evaluate("() => { document.querySelector('.path-view').scrollLeft = 300; }")
    page.wait_for_timeout(400)
    proxy = page.evaluate("() => document.querySelector('.sf-sticky-xscroll').scrollLeft")
    assert abs(proxy - 300) <= 3, f"proxy did not mirror the pane: {proxy}"
    page.evaluate("() => { document.querySelector('.sf-sticky-xscroll').scrollLeft = 80; }")
    page.wait_for_timeout(400)
    pane = page.evaluate("() => document.querySelector('.path-view').scrollLeft")
    assert abs(pane - 80) <= 3, f"pane did not follow the proxy: {pane}"
    assert errors == []
    page.context.close()


# ── 12. bar-click drills ──────────────────────────────────────────────────────────────────────


def test_bar_click_drill_opens_the_activity_overlay(browser: Any, served: str) -> None:
    """The shared sf-drill contract (drilldown.js): clicking a marked chart element opens the
    activity drill overlay with a populated grid; Escape closes it. Driven on /trend, whose
    bars the census floors count sitewide (69 there, 76 on /mission, ...)."""
    page, errors = _open(browser, served, "/trend")
    page.wait_for_selector(".sf-drill", timeout=30000)
    page.locator(".sf-drill").first.click(force=True)
    page.wait_for_selector("#sfDrillOverlay", timeout=10000)
    # the dialog shell opens first; the activity grid lands from an async fetch — and its rows
    # are appended straight to the <table> (createElement DOM: no tbody exists to select)
    page.wait_for_selector("#sfDrillOverlay .sf-drill-grid td", timeout=15000)
    rows = page.evaluate(
        """() => [...document.querySelectorAll('#sfDrillOverlay .sf-drill-grid tr')]
                 .filter(tr => tr.querySelector('td')).length"""
    )
    assert rows >= 1, "drill overlay opened without activity rows"
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    gone = page.evaluate("() => !document.getElementById('sfDrillOverlay')")
    assert gone, "Escape did not close the drill overlay"
    assert errors == []
    page.context.close()


# ── 13. enlarge, then print ───────────────────────────────────────────────────────────────────


def test_enlarge_then_print_returns_the_panel_to_the_flow(browser: Any, served: str) -> None:
    """The A5 print contract meets ⛶: an enlarged block-layout panel is a fixed-position focus
    overlay on screen, and under print media it must return to the flow (base.css measured it
    printing as a floating card otherwise) while the toolbars ([data-noprint], .cf-bar) hide.
    Back on screen media, the overlay returns."""
    page, errors = _open(browser, served, "/scurve")
    page.wait_for_selector("[data-sf-big]", timeout=30000)
    page.locator("[data-sf-big]").first.click()
    page.wait_for_timeout(400)
    panel_pos = """() => {
      const p = document.querySelector('.panel.is-big');
      return p ? window.getComputedStyle(p).position : null;
    }"""
    assert page.evaluate(panel_pos) == "fixed", "⛶ did not lift the panel into the overlay"
    page.emulate_media(media="print")
    page.wait_for_timeout(300)
    assert page.evaluate(panel_pos) == "static", "enlarged panel still out of flow under print"
    hidden = page.evaluate(
        """() => {
      const gone = sel => [...document.querySelectorAll(sel)].every(
        el => window.getComputedStyle(el).display === 'none');
      return {noprint: gone('[data-noprint]'), cfbar: gone('.cf-bar')};
    }"""
    )
    assert hidden["noprint"] and hidden["cfbar"], f"print still shows chrome: {hidden}"
    page.emulate_media(media="screen")
    page.wait_for_timeout(300)
    assert page.evaluate(panel_pos) == "fixed", "overlay did not return on screen media"
    assert errors == []
    page.context.close()
