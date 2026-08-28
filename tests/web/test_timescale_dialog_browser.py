"""M2 — the Timescale dialog and its persisted-config load path, driven in a real browser.

Until this module, ZERO behavioral coverage existed for the MS-Project Timescale dialog
(``static/timescale.js``): every existing pin froze control BYTES, none drove an effect. This
suite drives the dialog end to end (open → tab → edit → OK/Cancel/Reset, measured on the page
BEHIND the dialog) and pins the ADR-0440 load-path hardening.

The load-path half is the WP0 live-defect chase (AUDIT-2026-08-27, rows A1-A4/B2). v1.0.221
merged ``localStorage["sf.timescale.v1"]`` into the config with NO validation
(timescale.js:60-77), while the 25-1000 Size clamp lived only on dialog EDITS — so a persisted
out-of-range/garbage value reproduced the operator's exact report ("controls do nothing" +
"renders wrong" on /path, /driving-path, /evolution) with zero console errors, invisibly to a
fresh-profile probe, and survived Reset-view/launch wipes by design (persist.js exempts the
Timescale key). A hostile tier ``units`` crashed the Gantt render outright
("Cannot read properties of undefined (reading 'fn')") because ``labelDef`` lacked the fallback
``UNITS`` has — and /evolution swallowed that crash into a MISLEADING "Failed to load the
path-evolution data." box.

Red-first (QC-1): every ``*_clamped_on_load`` / ``*_fall_back*`` / ``*cannot_crash*`` /
``*matrix_cell*`` test below was observed to FAIL against the pre-fix tree before the
timescale.js sanitizer existed — the observations are recorded in docs/adr/0440 and the audit
ledger. State is seeded via ``context.add_init_script`` because timescale.js reads localStorage
at script PARSE time; seeding after load is vacuous (the seeded tests' mutation proof is
"seed removed → the PASS side returns", asserted by the A0-baseline test doubling as that side).
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

#: the five TP4 DataCenter snapshots as ONE five-version project (the r11 corpus — /path,
#: /driving-path and /evolution all render their full Gantt take against it).
VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
TARGET_UID = 26

PATH = "/path"
EVO = "/evolution"

STORE_KEY = "sf.timescale.v1"
DIALOG = ".ts-dialog"
#: the dialog's Size % field — the ONLY number input carrying the 25 floor (Count floors at 1).
SIZE_INPUT = '.ts-dialog input[type=number][min="25"]'
OK_BTN = ".ts-dialog .ts-ok"


# ── server + browser (the r11 served() idiom, one of each for the module) ─────────────────────


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
    """ONE chromium for the whole module — isolation comes from a fresh context per test."""
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


def _seed_ts(obj: Any) -> str:
    """An add_init_script line seeding the persisted Timescale config BEFORE any script parses."""
    payload = json.dumps(json.dumps(obj))
    return f"try{{localStorage.setItem({STORE_KEY!r},{payload})}}catch(e){{}}"


def _open(browser: Any, served: str, route: str, seed: str | None = None) -> tuple[Any, list[str]]:
    """A fresh context + page on ``route`` with pageerrors collected from before first paint."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    if seed:
        ctx.add_init_script(seed)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + route, wait_until="load")
    page.wait_for_timeout(1200)  # charts + the seat pass settle before any baseline measure
    return page, errors


_CFG = "() => window.SFTimescale.config()"
_FACTOR = "() => window.SFTimescale.sizeFactor()"
_MAX_BAR = """() => {
  const ws = [...document.querySelectorAll('.gantt-bar')].map(b => b.getBoundingClientRect().width);
  return ws.length ? Math.max(...ws) : null;
}"""
_TRACK_W = """(sel) => {
  const t = document.querySelector(sel);
  return t ? Math.round(t.getBoundingClientRect().width) : null;
}"""


def _drag_path_zoom(page: Any) -> None:
    """Double /path's own Zoom slider and fire the input event its listener is bound to."""
    page.evaluate(
        """() => {
          const z = document.getElementById('pathZoom');
          z.value = String(Math.min(Number(z.max || 40), (Number(z.value) || 8) * 2));
          z.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
    )
    page.wait_for_timeout(400)


def _open_dialog(page: Any) -> None:
    page.click("#timescaleBtn")
    page.wait_for_selector(DIALOG, timeout=5000)


# ── the dialog itself (open / tabs / preview) ─────────────────────────────────────────────────


def test_timescale_button_opens_the_dialog_with_four_tabs_and_a_live_preview(
    browser: Any, served: str
) -> None:
    """#timescaleBtn is bound once for every page; the dialog is the MS Project four-tab shape
    and its preview strip renders REAL tier bands (not an empty box)."""
    page, errors = _open(browser, served, PATH)
    _open_dialog(page)
    tabs = page.locator(".ts-tab").all_text_contents()
    assert tabs == ["Top Tier", "Middle Tier", "Bottom Tier", "Non-working time"]
    assert page.locator(".ts-preview-box .ts-preview-scale").count() == 1
    assert page.locator(".ts-preview-box .g-band").count() >= 1  # bands actually laid out
    assert errors == []
    page.context.close()


def test_clicking_a_tab_switches_the_pane(browser: Any, served: str) -> None:
    """The Non-working tab must swap the pane content (radio group appears) and take the
    ts-tab-on highlight with it — the middle tier opens active."""
    page, _ = _open(browser, served, PATH)
    _open_dialog(page)
    assert page.locator(".ts-tab-on").text_content() == "Middle Tier"
    assert page.locator('.ts-pane input[name="tsDraw"]').count() == 0
    page.click('.ts-tab:has-text("Non-working time")')
    page.wait_for_timeout(150)
    assert page.locator(".ts-tab-on").text_content() == "Non-working time"
    assert page.locator('.ts-pane input[name="tsDraw"]').count() == 3
    page.context.close()


# ── OK / Cancel / Reset semantics, measured on the page BEHIND the dialog ─────────────────────


def test_ok_commits_a_size_change_to_the_page_behind_and_persists_it(
    browser: Any, served: str
) -> None:
    """Size 200% + OK must MEASURABLY widen the bars (the sf-timescale reflow), and the commit
    must land in localStorage — the dialog's whole contract in one drive."""
    page, errors = _open(browser, served, PATH)
    before = page.evaluate(_MAX_BAR)
    assert before is not None and before > 10  # a healthy baseline, not the 2px floor
    _open_dialog(page)
    page.fill(SIZE_INPUT, "200")
    page.click(OK_BTN)
    page.wait_for_timeout(500)
    after = page.evaluate(_MAX_BAR)
    assert after is not None and 1.6 <= after / before <= 2.4, (before, after)
    stored = page.evaluate(f"() => JSON.parse(localStorage.getItem({STORE_KEY!r}))")
    assert stored["size"] == 200
    assert errors == []
    page.context.close()


def test_cancel_discards_the_draft_entirely(browser: Any, served: str) -> None:
    """Cancel after a Size edit: nothing moves, nothing persists, the factor stays 1 — the
    dialog edits a DRAFT (work), never the live config."""
    page, _ = _open(browser, served, PATH)
    before = page.evaluate(_MAX_BAR)
    _open_dialog(page)
    page.fill(SIZE_INPUT, "200")
    page.click('.ts-foot button:has-text("Cancel")')
    page.wait_for_timeout(400)
    assert page.locator(DIALOG).count() == 0
    assert page.evaluate(_FACTOR) == 1
    assert page.evaluate(_MAX_BAR) == before
    assert page.evaluate(f"() => localStorage.getItem({STORE_KEY!r})") is None
    page.context.close()


def test_reset_to_default_then_ok_restores_the_stock_timescale(browser: Any, served: str) -> None:
    """From a persisted legal 200% (page opens at 2x), the dialog's "Reset to default" + OK must
    bring the measured page back to the stock 100% look and persist size 100."""
    page, _ = _open(browser, served, PATH, seed=_seed_ts({"size": 200}))
    assert page.evaluate(_FACTOR) == 2  # the seed really applied (in-range values load verbatim)
    doubled = page.evaluate(_MAX_BAR)
    _open_dialog(page)
    page.click('.ts-foot button:has-text("Reset to default")')
    page.click(OK_BTN)
    page.wait_for_timeout(500)
    assert page.evaluate(_FACTOR) == 1
    restored = page.evaluate(_MAX_BAR)
    assert restored is not None and doubled is not None and restored < doubled / 1.5
    assert page.evaluate(f"() => JSON.parse(localStorage.getItem({STORE_KEY!r}))")["size"] == 100
    page.context.close()


def test_escape_closes_the_dialog_without_committing(browser: Any, served: str) -> None:
    page, _ = _open(browser, served, PATH)
    _open_dialog(page)
    page.fill(SIZE_INPUT, "300")
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    assert page.locator(DIALOG).count() == 0
    assert page.evaluate(_FACTOR) == 1
    assert page.evaluate(f"() => localStorage.getItem({STORE_KEY!r})") is None
    page.context.close()


def test_a_committed_config_survives_reload_and_applies_on_other_pages(
    browser: Any, served: str
) -> None:
    """The config is per-browser, not per-page: commit 200% on /path, reload (still 2x), then
    open /evolution in the SAME context — its Gantt must load at 2x too."""
    page, _ = _open(browser, served, PATH)
    _open_dialog(page)
    page.fill(SIZE_INPUT, "200")
    page.click(OK_BTN)
    page.wait_for_timeout(300)
    page.reload(wait_until="load")
    page.wait_for_timeout(800)
    assert page.evaluate(_FACTOR) == 2
    other = page.context.new_page()
    other.goto(served + EVO, wait_until="load")
    other.wait_for_timeout(800)
    assert other.evaluate(_FACTOR) == 2
    page.context.close()


# ── the ADR-0440 load-path hardening (all red-first against the pre-fix tree) ─────────────────


def test_corrupt_persisted_json_falls_back_to_defaults(browser: Any, served: str) -> None:
    """Unparseable storage → the stock config, no crash. (A pre-existing behavior PIN — the
    JSON.parse try/catch predates ADR-0440; the sanitizer must not break it.)"""
    corrupt = f"try{{localStorage.setItem({STORE_KEY!r},'{{not json')}}catch(e){{}}"
    page, errors = _open(browser, served, PATH, seed=corrupt)
    assert errors == []
    assert page.evaluate(_FACTOR) == 1
    assert page.evaluate(_CFG)["size"] == 100
    assert (page.evaluate(_MAX_BAR) or 0) > 10
    page.context.close()


def test_out_of_range_low_persisted_size_is_clamped_on_load(browser: Any, served: str) -> None:
    """AUDIT row A1 (the operator-symptom cell): a persisted ``size: 1`` used to load verbatim
    → sizeFactor 0.01 → every bar at the 2px floor and the zoom slider visually inert. The load
    path must clamp to the dialog's own floor (25) — and the dialog must OPEN showing the healed
    value, so the operator can SEE what their state became."""
    page, errors = _open(browser, served, PATH, seed=_seed_ts({"size": 1}))
    assert errors == []
    cfg = page.evaluate(_CFG)
    assert cfg["size"] == 25
    assert page.evaluate(_FACTOR) == 0.25
    _open_dialog(page)
    assert page.locator(SIZE_INPUT).input_value() == "25"
    page.context.close()


def test_out_of_range_high_persisted_size_is_clamped_and_geometry_is_sane(
    browser: Any, served: str
) -> None:
    """AUDIT row A2: a persisted ``size: 100000`` used to load verbatim → sizeFactor 1000 → a
    ~476,000px track ("renders wrong": the viewport shows one giant band). Clamped to 1000 the
    track must come back inside sane bounds on /path."""
    page, errors = _open(browser, served, PATH, seed=_seed_ts({"size": 100000}))
    assert errors == []
    assert page.evaluate(_CFG)["size"] == 1000
    assert page.evaluate(_FACTOR) == 10
    track = page.evaluate(_TRACK_W, ".path-track")
    assert track is not None and 200 <= track <= 60000, track
    page.context.close()


def test_a_numeric_string_persisted_size_is_clamped_not_multiplied(
    browser: Any, served: str
) -> None:
    """AUDIT row A4: ``size: "600000"`` (a STRING) passed Number() downstream and produced a
    6000x zoom. The sanitizer must coerce-then-clamp strings exactly like numbers."""
    page, errors = _open(browser, served, PATH, seed=_seed_ts({"size": "600000"}))
    assert errors == []
    assert page.evaluate(_CFG)["size"] == 1000
    assert page.evaluate(_FACTOR) == 10
    page.context.close()


def test_a_non_numeric_persisted_size_falls_back_to_the_default(browser: Any, served: str) -> None:
    """``size: "abc"`` pre-fix stayed in the config verbatim (sizeFactor happened to survive on
    its ``||100`` belt, but config() served garbage to the dialog). Non-coercible → default 100."""
    page, errors = _open(browser, served, PATH, seed=_seed_ts({"size": "abc"}))
    assert errors == []
    assert page.evaluate(_CFG)["size"] == 100
    assert page.evaluate(_FACTOR) == 1
    page.context.close()


def test_hostile_tier_units_cannot_crash_the_gantt(browser: Any, served: str) -> None:
    """AUDIT row B2 — the second live defect: ``top.units: "bogus"`` crashed every tier build
    ("Cannot read properties of undefined (reading 'fn')") because labelDef indexed
    LABELS[units] without the fallback UNITS has; /path lost its whole Gantt and /evolution
    swallowed the crash into a misleading "Failed to load" box. Post-fix: unknown enums fall
    back to that tier's defaults, a wild count clamps to 999, and the Gantt renders."""
    seed = _seed_ts(
        {
            "top": {"units": "bogus", "label": "nope", "count": -5, "align": "<x>"},
            "middle": {"units": "hours", "count": 1_000_000_000},
        }
    )
    page, errors = _open(browser, served, PATH, seed=seed)
    # force a full tier REBUILD through the hostile config — the crash lives in tierBands, so a
    # load-time-only check can miss it when the first paint outruns the error collector
    _drag_path_zoom(page)
    assert errors == [], errors
    cfg = page.evaluate(_CFG)
    assert cfg["top"]["units"] == "years" and cfg["top"]["label"] == "y_full"
    assert cfg["top"]["count"] == 1 and cfg["top"]["align"] == "center"
    assert cfg["middle"]["units"] == "hours" and cfg["middle"]["count"] == 999
    assert page.evaluate(_TRACK_W, ".path-track") is not None
    assert page.locator("[class*='g-scale-rows-']").count() >= 1

    evo = page.context.new_page()
    evo_errors: list[str] = []
    evo.on("pageerror", lambda e: evo_errors.append(str(e)))
    evo.goto(served + EVO, wait_until="load")
    evo.wait_for_timeout(1200)
    assert evo_errors == []
    assert evo.evaluate(_TRACK_W, ".g-track") is not None  # not the "Failed to load" box
    page.context.close()


def test_garbage_show_and_fiscal_month_fall_back_to_their_defaults(
    browser: Any, served: str
) -> None:
    """``show: 0`` isn't a tier count and ``fyStartMonth: 99`` isn't a month; both loaded
    verbatim pre-fix (show=0 happened to paint 3 tiers only because the ladder's else-branch
    caught it — the CONFIG stayed poisoned and the dialog displayed it)."""
    page, errors = _open(browser, served, PATH, seed=_seed_ts({"show": 0, "fyStartMonth": 99}))
    assert errors == []
    cfg = page.evaluate(_CFG)
    assert cfg["show"] == 3
    assert cfg["fyStartMonth"] == 9
    page.context.close()


def test_a1_matrix_cell_zoom_regains_a_measured_effect(browser: Any, served: str) -> None:
    """THE "controls do nothing" symptom, repaired and measured: with the healed 25% config the
    /path bars must sit ABOVE the 2px floor and doubling the Zoom slider must visibly move them
    (pre-fix at 0.01x: bars pinned at 2px, a full slider doubling moved the widest bar ~6px)."""
    page, errors = _open(browser, served, PATH, seed=_seed_ts({"size": 1}))
    assert errors == []
    before = page.evaluate(_MAX_BAR)
    assert before is not None and before >= 4, f"bars still at the floor: {before}"
    _drag_path_zoom(page)
    after = page.evaluate(_MAX_BAR)
    assert after is not None and after >= before * 1.5, (before, after)
    page.context.close()


def test_a2_matrix_cell_evolution_geometry_and_zoom_are_sane_again(
    browser: Any, served: str
) -> None:
    """AUDIT row A2 on /evolution: pre-fix the track measured ~670,000px and a zoom click moved
    the world by an imperceptible fraction. Post-clamp (10x) the track is bounded and the zoom
    buttons produce a real measured change."""
    page, errors = _open(browser, served, EVO, seed=_seed_ts({"size": 100000}))
    assert errors == []
    track = page.evaluate(_TRACK_W, ".g-track")
    assert track is not None and 200 <= track <= 60000, track
    before = page.evaluate(
        """() => {
          const ws = [...document.querySelectorAll("[class*='ev-b-'],[class*='ev-t-']")]
            .map(b => b.getBoundingClientRect().width);
          return ws.length ? Math.max(...ws) : null;
        }"""
    )
    page.click("#evoZoomIn")
    page.click("#evoZoomIn")
    page.wait_for_timeout(500)
    after = page.evaluate(
        """() => {
          const ws = [...document.querySelectorAll("[class*='ev-b-'],[class*='ev-t-']")]
            .map(b => b.getBoundingClientRect().width);
          return ws.length ? Math.max(...ws) : null;
        }"""
    )
    assert before is not None and after is not None and abs(after - before) >= 1.0, (before, after)
    page.context.close()
