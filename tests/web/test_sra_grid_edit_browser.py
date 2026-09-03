"""M4 (WP3) — the SRA grid's edit / paste-from-Excel / save round trip, DRIVEN in Chromium.

The WP1 UI map's last queued row (27). ``test_sra_grid.py`` pins the plumbing through
``TestClient`` (the JSON feed, the batched POST, the setup Save/Load) and pins the paste handler by
grepping the served JS for ``"paste"`` and ``split("\\t")`` — bytes, not behaviour. Nothing before
this module ever typed into a cell, pasted a clipboard, pressed Save grid, or read the status line
the operator reads. This module drives each control and measures the effect, the WP2 way.

Two oracles per control, and BOTH are required:

* **LABEL** — ``#ssiGridStatus``, the one line the operator watches ("1 task(s) with unsaved
  edits.", "Pasted 3 value(s) …", "Saved 1 change(s)").
* **GRID** — a digest of the rendered grid. DOM-shape-agnostic (tag + class + inline style + leaf
  text) like WP2's chart digest, PLUS every input's live ``value`` and every radio's ``checked``,
  because an edit lives in a property the attribute digest cannot see.
  ``test_grid_digest_is_stable_and_sensitive`` proves the digest holds still across a reload and
  moves on a saved edit; without that pin every "the grid changed" assertion below is noise.

The paste path is fed a REAL clipboard: ``navigator.clipboard.writeText`` + ``Control+V`` (measured
2026-09-03: Chromium delivers the ``paste`` event with the clipboard text under the
``clipboard-read`` / ``clipboard-write`` context permissions). The payloads are Excel-shaped —
CRLF line ends, a trailing newline, tab-separated columns for a block.

What the first run of these drivers caught (all observed RED before the fix, see ADR-0454):

* **M4-01** — "Refresh grid" and the post-run reload (``sf-ssi-run``) reset the pending map, so
  unsaved edits were destroyed silently ("1 task(s) with unsaved edits." → "145 tasks.").
* **M4-02** — a blanked cell was sent as ``""`` and the route skipped it: the operator saw the
  cell empty, pressed Save, read "Saved 0 change(s)." and watched the old value come back. There
  was no way to clear a factor or a range from the grid at all.
* **M4-03** — an unparseable pasted token (an Excel header word, ``12,5``) vanished on save with
  no report, and an out-of-range ``7`` was clamped to 5 without a word. ADR-0313's rule for this
  page: a value the operator supplied is never silently altered or dropped.
* **M4-04** — the "Saved N change(s)." confirmation was overwritten by the reload's "145 tasks."
  before it could be read (it survived one fetch round trip).
* **M4-05** — a non-number typed into a cell (Chromium's ``badInput``) queued as an EMPTY edit.
  Harmless while ``""`` was ignored; with M4-02 fixed it would have become a silent clear.
* **M4-06** — leaving the page (the SSI panel's own forms all POST + redirect) discarded pending
  edits with no ``beforeunload`` guard.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "project2_5" / "Project5.mspdi.xml"

#: The first three INCOMPLETE leaf rows in grid (DOM) order — a fill-down lands on consecutive
#: inputs, and a completed row refuses a range (ADR-0308), so the paste targets must be open work.
#: Derived at module import from the same feed the grid reads, never transcribed.
STATUS_SEL = "#ssiGridStatus"


def _inp(uid: int, key: str) -> str:
    return f'#ssiGrid input.sra-inp[data-uid="{uid}"][data-key="{key}"]'


def _radio(uid: int) -> str:
    return f'#ssiGrid input.sra-focus[data-uid="{uid}"]'


# ── oracles ───────────────────────────────────────────────────────────────────────────────────

_DIGEST_JS = """() => {
  const out = [];
  document.querySelectorAll("#ssiGrid *").forEach(el => {
    const a = n => el.getAttribute(n) || "";
    let live = "";
    if (el.tagName === "INPUT") live = el.type === "radio" ? (el.checked ? "on" : "off") : el.value;
    out.push(el.tagName + "|" + a("class") + "|" + (el.style ? el.style.cssText : "") +
             "|" + live + "|" + (el.children.length ? "" : (el.textContent || "").slice(0, 60)));
  });
  return out.join(";");
}"""

_LOADED_RE = r"/^\d+ tasks\b/"


def digest(page: Any) -> str:
    raw: str = page.evaluate(_DIGEST_JS)
    assert raw, "grid container empty"
    return hashlib.sha1(raw.encode()).hexdigest()


def status(page: Any) -> str:
    value: str = page.evaluate(f"() => document.querySelector('{STATUS_SEL}').textContent")
    return value


def wait_loaded(page: Any) -> None:
    """The grid has (re)loaded: rows painted and the status line opens with the task count."""
    page.wait_for_function(
        "() => document.querySelectorAll('#ssiGrid input.sra-inp').length > 0 && "
        f"{_LOADED_RE}.test(document.querySelector('{STATUS_SEL}').textContent)"
    )


def save(page: Any) -> dict[str, Any]:
    """Press Save grid, return the POST /sra/grid response body, and wait for the reload."""
    with page.expect_response(
        lambda r: r.url.endswith("/sra/grid") and r.request.method == "POST"
    ) as info:
        page.click("#ssiGridSave")
    body: dict[str, Any] = info.value.json()
    wait_loaded(page)
    return body


def paste(page: Any, selector: str, text: str) -> None:
    """A REAL paste: put ``text`` on the system clipboard and press Ctrl+V in the focused cell."""
    page.evaluate("t => navigator.clipboard.writeText(t)", text)
    page.focus(selector)
    page.keyboard.press("Control+V")


def api_row(base: str, page: Any, uid: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = page.request.get(base + "/api/sra/grid").json()["rows"]
    return next(r for r in rows if r["unique_id"] == uid)


def setup_json(base: str, page: Any) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(page.request.get(base + "/sra/ssi/save").body())
    return body


# ── server + browser (the r11 idiom, as in WP2) ───────────────────────────────────────────────


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _serve(state: SessionState) -> tuple[str, Any]:
    import uvicorn

    app = create_app(state)
    with TestClient(app) as c:
        r = c.post(
            "/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")}
        )
        assert r.status_code == 200
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    return f"http://127.0.0.1:{port}", server


@pytest.fixture(scope="module")
def served() -> Iterator[tuple[str, SessionState]]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    state = SessionState()
    base, server = _serve(state)
    yield base, state
    server.should_exit = True


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


@pytest.fixture
def grid(browser: Any, served: tuple[str, SessionState]) -> Iterator[tuple[str, SessionState, Any]]:
    """A fresh page on /sra with the SSI inputs wiped — every test starts from the pristine grid.

    The server session outlives a browser context (a WP2 trap), so the SRA inputs are reset on
    the STATE, not by a new server: factors, ranges and the focus are the only things the grid
    writes."""
    base, state = served
    state.sra_factors.clear()
    state.sra_bcwc.clear()
    state.sra_focus_uid = None
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"]
    )
    page = ctx.new_page()
    page.goto(base + "/sra")
    wait_loaded(page)
    yield base, state, page
    ctx.close()


@pytest.fixture(scope="module")
def open_uids(served: tuple[str, SessionState]) -> list[int]:
    """The first three consecutive INCOMPLETE leaf rows in grid order, derived from the feed."""
    base, _state = served
    import urllib.request

    with urllib.request.urlopen(base + "/api/sra/grid") as resp:  # loopback only
        rows = json.load(resp)["rows"]
    run: list[int] = []
    for r in rows:
        if r["editable"] and not r["completed"]:
            run.append(r["unique_id"])
            if len(run) == 3:
                return run
        else:
            run = []
    raise AssertionError("Project5 has no three consecutive incomplete leaf rows")


# ── the oracle itself ─────────────────────────────────────────────────────────────────────────


def test_grid_digest_is_stable_and_sensitive(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """Holds still across a full page reload; moves on a saved edit. Without this pin every digest
    assertion below is unfalsifiable."""
    _base, _state, page = grid
    d0 = digest(page)
    page.reload()
    wait_loaded(page)
    assert digest(page) == d0, "the pristine grid must render byte-identically on a reload"
    uid = open_uids[0]
    page.fill(_inp(uid, "factor"), "4")
    page.keyboard.press("Tab")
    assert digest(page) != d0, "a typed (unsaved) value must already move the digest"
    save(page)
    assert digest(page) != d0, "a saved edit must move the digest after the reload"


# ── edit → queue → save ───────────────────────────────────────────────────────────────────────


def test_typing_a_factor_queues_it_and_the_edit_survives_a_repaint(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    _base, state, page = grid
    uid = open_uids[0]
    page.fill(_inp(uid, "factor"), "4")
    page.keyboard.press("Tab")
    assert status(page) == "1 task(s) with unsaved edits."
    assert state.sra_factors.get(uid) is None, "queued, not saved"
    # a zoom nudge is a FULL re-render (new table); the pending value must be re-applied
    page.evaluate(
        "() => { const z = document.getElementById('ssiGridZoom'); z.value = '2.2';"
        " z.dispatchEvent(new Event('input')); }"
    )
    page.wait_for_function(f"() => document.querySelector('{_inp(uid, 'factor')}') !== null")
    assert page.input_value(_inp(uid, "factor")) == "4"
    assert status(page) == "1 task(s) with unsaved edits."


def test_save_grid_posts_the_deltas_and_the_row_shows_the_derived_range(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    base, state, page = grid
    uid = open_uids[0]
    d0 = digest(page)
    page.fill(_inp(uid, "factor"), "4")
    page.keyboard.press("Tab")
    body = save(page)
    assert body["ok"] is True and body["saved"] == 1
    row = api_row(base, page, uid)
    assert row["factor"] == 4
    assert row["bc_days"] < row["remaining_days"] < row["wc_days"]  # factor 4 spreads the range
    # the reloaded grid shows what the feed says — value for value
    assert page.input_value(_inp(uid, "factor")) == "4"
    assert float(page.input_value(_inp(uid, "bc_days"))) == row["bc_days"]
    assert float(page.input_value(_inp(uid, "wc_days"))) == row["wc_days"]
    assert digest(page) != d0
    # and the setup file the operator downloads carries the same edit
    setup = setup_json(base, page)
    assert setup["factors"][str(uid)] == 4
    assert setup["bcwc_minutes"][str(uid)] == list(state.sra_bcwc[uid])


def test_manual_best_worst_overrides_and_paints_the_envelope(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    base, _state, page = grid
    uid = open_uids[1]
    assert page.locator(f'#ssiGrid tr[data-uid="{uid}"] .g-envelope').count() == 0
    page.fill(_inp(uid, "bc_days"), "2")
    page.keyboard.press("Tab")
    page.fill(_inp(uid, "wc_days"), "11")
    page.keyboard.press("Tab")
    assert status(page) == "1 task(s) with unsaved edits."  # one task, two fields
    assert save(page)["saved"] == 1
    row = api_row(base, page, uid)
    assert (row["bc_days"], row["wc_days"]) == (2.0, 11.0)
    env = page.locator(f'#ssiGrid tr[data-uid="{uid}"] .g-envelope')
    assert env.count() == 1
    # tooltips.js promotes title= to data-sf-hint at load (the WP1 trap) — read either
    hint = env.get_attribute("data-sf-hint") or env.get_attribute("title") or ""
    assert "2/11" in hint, hint


def test_focus_radio_round_trips_to_the_ssi_target(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    base, state, page = grid
    uid = open_uids[2]
    page.check(_radio(uid))
    assert status(page) == "1 task(s) with unsaved edits."
    assert save(page)["saved"] == 1
    assert state.sra_focus_uid == uid
    assert api_row(base, page, uid)["is_focus"] is True
    assert page.is_checked(_radio(uid))
    assert page.request.get(base + "/api/sra/ssi?iterations=100").json()["target_uid"] == uid


# ── paste from Excel ──────────────────────────────────────────────────────────────────────────


def test_excel_column_paste_fills_down_from_the_pasted_cell(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    base, state, page = grid
    a, b, c = open_uids
    paste(page, _inp(a, "factor"), "3\r\n4\r\n5\r\n")  # Excel: CRLF + trailing newline
    assert status(page).startswith("Pasted 3 value(s) down the column")
    assert [page.input_value(_inp(u, "factor")) for u in (a, b, c)] == ["3", "4", "5"]
    assert save(page)["saved"] == 3
    assert [state.sra_factors[u] for u in (a, b, c)] == [3, 4, 5]
    assert [api_row(base, page, u)["factor"] for u in (a, b, c)] == [3, 4, 5]


def test_excel_block_paste_fills_factor_best_worst_left_to_right(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    base, state, page = grid
    a, b, _c = open_uids
    paste(page, _inp(a, "factor"), "2\t1.5\t9.5\r\n1\t2\t3\r\n")
    assert status(page).startswith("Pasted 6 value(s)")
    assert [page.input_value(_inp(a, k)) for k in ("factor", "bc_days", "wc_days")] == [
        "2",
        "1.5",
        "9.5",
    ]
    assert save(page)["saved"] == 2
    mpd = 480
    assert state.sra_factors[a] == 2
    assert state.sra_bcwc[a] == (round(1.5 * mpd), round(9.5 * mpd))  # manual beats the factor
    row_b = api_row(base, page, b)
    assert (row_b["factor"], row_b["bc_days"], row_b["wc_days"]) == (1, 2.0, 3.0)


def test_a_block_pasted_onto_best_case_starts_there(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """The pasted cell's column is the block's first column; columns past Worst are dropped."""
    base, state, page = grid
    a = open_uids[0]
    paste(page, _inp(a, "bc_days"), "1\t2\t3\r\n")
    assert page.input_value(_inp(a, "factor")) == ""
    got = (page.input_value(_inp(a, "bc_days")), page.input_value(_inp(a, "wc_days")))
    assert got == ("1", "2")
    assert save(page)["saved"] == 1
    assert state.sra_factors.get(a) is None
    assert api_row(base, page, a)["bc_days"] == 1.0


def test_a_single_pasted_value_falls_through_to_native_entry(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """One value with no tab is a manual entry: the handler steps aside, the browser pastes."""
    _base, _state, page = grid
    a = open_uids[0]
    paste(page, _inp(a, "factor"), "5")
    assert not status(page).startswith("Pasted")
    assert page.input_value(_inp(a, "factor")) == "5"  # the browser's own paste landed
    page.keyboard.press("Tab")
    assert status(page) == "1 task(s) with unsaved edits."


# ── the setup round trip ──────────────────────────────────────────────────────────────────────


def test_setup_save_load_reproduces_the_grid_in_a_fresh_session(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """Save grid → download the setup → load it into a NEW server on the same file: the grid
    renders identically (the digest, input values and radio included)."""
    base, _state, page = grid
    pristine = digest(page)
    a, b, _c = open_uids
    paste(page, _inp(a, "factor"), "3\r\n4\r\n")
    page.check(_radio(b))
    save(page)
    edited = digest(page)
    assert edited != pristine
    blob = page.request.get(base + "/sra/ssi/save").body()

    other = SessionState()
    base2, server2 = _serve(other)
    try:
        page2 = page.context.new_page()
        page2.goto(base2 + "/sra")
        wait_loaded(page2)
        assert digest(page2) == pristine, "same file, no setup → the pristine grid"
        r = page2.request.post(
            base2 + "/sra/ssi/load",
            multipart={"setup": {"name": "s.json", "mimeType": "application/json", "buffer": blob}},
        )
        assert r.ok
        page2.reload()
        wait_loaded(page2)
        assert digest(page2) == edited
        assert other.sra_factors[a] == 3 and other.sra_focus_uid == b
    finally:
        server2.should_exit = True


# ── FAIL-side drivers (each observed RED on the pre-ADR-0454 tree) ────────────────────────────


def test_refresh_grid_keeps_unsaved_edits(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-01: Refresh reloads the rows; it is not "discard my edits"."""
    _base, state, page = grid
    uid = open_uids[0]
    page.fill(_inp(uid, "factor"), "4")
    page.keyboard.press("Tab")
    page.click("#ssiGridReload")
    wait_loaded(page)
    assert page.input_value(_inp(uid, "factor")) == "4"
    assert "1 unsaved" in status(page), status(page)
    assert state.sra_factors.get(uid) is None, "refresh must not save behind the operator's back"


def test_a_completed_ssi_run_reload_keeps_unsaved_edits(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-01 (second door): the post-run reload that refreshes the criticality tint."""
    _base, _state, page = grid
    uid = open_uids[0]
    page.fill(_inp(uid, "factor"), "2")
    page.keyboard.press("Tab")
    page.evaluate("() => window.dispatchEvent(new Event('sf-ssi-run'))")
    wait_loaded(page)
    assert page.input_value(_inp(uid, "factor")) == "2"
    assert "1 unsaved" in status(page), status(page)


def test_blanking_a_cell_clears_it_on_save(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-02: what the operator sees before Save is what is saved — a blank clears."""
    base, state, page = grid
    uid = open_uids[0]
    state.sra_factors[uid] = 4
    state.sra_bcwc[uid] = (96, 672)
    page.reload()
    wait_loaded(page)
    assert page.input_value(_inp(uid, "factor")) == "4"
    page.fill(_inp(uid, "factor"), "")
    page.keyboard.press("Tab")
    body = save(page)
    assert body["saved"] == 1, body
    assert state.sra_factors.get(uid) is None
    assert page.input_value(_inp(uid, "factor")) == ""
    # the range was not blanked, so it stays (literal: only the blanked cell clears)
    assert state.sra_bcwc[uid] == (96, 672)
    # now blank both range cells → the stored pair is gone
    page.fill(_inp(uid, "bc_days"), "")
    page.keyboard.press("Tab")
    page.fill(_inp(uid, "wc_days"), "")
    page.keyboard.press("Tab")
    assert save(page)["saved"] == 1
    assert uid not in state.sra_bcwc
    assert api_row(base, page, uid)["bc_days"] is None


def test_a_rejected_paste_value_is_reported_not_swallowed(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-03: an Excel header word, a comma decimal and an out-of-range 7 — each named."""
    _base, state, page = grid
    a, b, c = open_uids
    paste(page, _inp(a, "factor"), "Factor\r\n12,5\r\n7\r\n")
    body = save(page)
    assert body["saved"] == 1  # only the 7 applied (clamped)
    rejected = {(r["uid"], r["field"]): r for r in body["rejected"]}
    assert set(rejected) == {(a, "factor"), (b, "factor")}
    assert rejected[(a, "factor")]["value"] == "Factor"
    assert rejected[(b, "factor")]["value"] == "12,5"
    assert body["clamped"] == [{"uid": c, "field": "factor", "value": "7", "applied": 5}]
    assert state.sra_factors.get(a) is None and state.sra_factors.get(b) is None
    assert state.sra_factors[c] == 5
    line = status(page)
    assert f"UID {a}" in line and "Factor" in line and "not a number" in line, line
    assert f"UID {b}" in line and "12,5" in line, line
    assert f"UID {c}" in line and "7" in line and "5" in line and "clamped" in line, line


def test_the_save_confirmation_survives_the_reload(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-04: "Saved 1 change(s)" must still be readable once the grid has reloaded."""
    _base, _state, page = grid
    page.fill(_inp(open_uids[0], "factor"), "3")
    page.keyboard.press("Tab")
    save(page)
    line = status(page)
    assert re.match(r"^\d+ tasks", line), line
    assert "Saved 1 change(s)" in line, line


def test_a_non_number_typed_into_a_cell_is_refused_at_the_cell(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-05: Chromium reports ``e`` in a number input as badInput with an EMPTY value; queuing it
    would clear the cell on save. Refuse at the cell and say so."""
    _base, state, page = grid
    uid = open_uids[0]
    state.sra_factors[uid] = 3
    page.reload()
    wait_loaded(page)
    page.click(_inp(uid, "factor"))
    page.keyboard.press("Control+A")
    page.keyboard.type("e")
    page.keyboard.press("Tab")
    line = status(page)
    assert f"UID {uid}" in line and "not a number" in line and "not queued" in line, line
    assert "unsaved" not in line
    # nothing was queued, so Save has nothing to post — and the stored ranking is untouched
    page.click("#ssiGridSave")
    assert status(page) == "Nothing to save."
    assert state.sra_factors[uid] == 3, "the refused keystroke must not clear the stored factor"


def test_leaving_the_page_with_unsaved_edits_asks_first(
    grid: tuple[str, SessionState, Any], open_uids: list[int]
) -> None:
    """M4-06: the SSI panel's own forms POST + redirect; a pending edit must raise beforeunload."""
    base, _state, page = grid
    seen: list[str] = []
    page.on("dialog", lambda d: (seen.append(d.type), d.dismiss()))
    page.fill(_inp(open_uids[0], "factor"), "4")
    page.keyboard.press("Tab")
    # the dismissed dialog aborts the navigation, which goto reports as an error (ERR_ABORTED)
    with contextlib.suppress(Exception):
        page.goto(base + "/sra", timeout=3000)
    assert seen == ["beforeunload"], seen
    assert page.input_value(_inp(open_uids[0], "factor")) == "4"  # still here, still pending
    # and once saved there is nothing to guard
    seen.clear()
    save(page)
    page.goto(base + "/sra")
    wait_loaded(page)
    assert seen == []
