"""S5 (WP1, ADR-0442) — windowed row painting on /path at row scale.

The operator's 2,301-activity IPMR exposed the cost axis ADR-0441 deferred: one-shot
``paintRows`` measured **1,417 ms** post-0441 (re-measured 1,623 ms median pre-fix on this
container), because every row pays its own gridline divs, non-working shading and freeze
styles. The fix windows the flat grid: at ``WINDOW_MIN_ROWS`` (400) and above only the
viewport slice ± overscan is materialized, spacer rows keep the scrollbar honest, and a
vertical scroll re-aims the window (measured post-fix: 49 ms median, DOM 104,728 → 19,066
nodes at 2,280 rows — the timing numbers live in the audit ledger, per the ADR-0441
precedent; CI asserts STRUCTURE, not milliseconds).

Fixtures are GENERATED at test time by ``tests/web/scale_schedule.py`` (deterministic seed):
the row count is the payload and a committed multi-thousand-row XML would prove nothing more.
900 rows drives the windowed side (2.25x over the threshold); 300 rows pins the full-paint
side (the threshold's boundary-setter — the ADR-0441 rule that the neighbour suite's green
vetoes an over-eager threshold; TP5's 121-row suite is the second veto).

Escapes that must stay FULL paints, each pinned here or in the ADR's mutation battery:
grouped output, "Show links", Find (searches/marks the DOM), and print (the A5 contract
prints scroll panes in full).
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
from web.scale_schedule import generate_mspdi

REPO = Path(__file__).resolve().parents[2]

PATH = "/path"
BIG_N = 900  # windowed side: 2.25x over WINDOW_MIN_ROWS=400
SMALL_N = 300  # full-paint side: under the threshold with margin over the visible slice


def _load(client: TestClient) -> None:
    # the SMALL schedule gets the newer mtime so /path opens on it; tests that need the big
    # one switch via the #pathSchedule picker (the operator's own gesture)
    files = [
        ("files", ("row_scale_big.xml", generate_mspdi(BIG_N).encode(), "text/xml")),
        ("files", ("row_scale_small.xml", generate_mspdi(SMALL_N).encode(), "text/xml")),
    ]
    meta = json.dumps(
        [
            {"rel": "row_scale_big.xml", "mtime": 1_700_000_000_000},
            {"rel": "row_scale_small.xml", "mtime": 1_700_000_086_400},
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    # NO target on purpose — the whole-schedule flat posture is the windowed shape.


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


def _open(browser: Any, served: str, schedule: str) -> tuple[Any, list[str]]:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + PATH, wait_until="load")
    page.wait_for_selector(".path-track", timeout=60000)
    if schedule != "small":
        page.evaluate(
            """() => {
              const sel = document.getElementById('pathSchedule');
              sel.value = 'row_scale_big';
              sel.dispatchEvent(new Event('change', {bubbles: true}));
            }"""
        )
        page.wait_for_selector("#pathBody tr.pv-vspacer, #pathBody tr[data-uid]", timeout=60000)
    page.wait_for_timeout(1200)
    return page, errors


_STATE = """() => {
  const v = document.querySelector('.path-view');
  const trs = [...document.querySelectorAll('#pathBody tr[data-uid]')];
  const uids = trs.map(t => Number(t.getAttribute('data-uid')));
  return {
    painted: trs.length,
    minUid: uids.length ? Math.min(...uids) : null,
    maxUid: uids.length ? Math.max(...uids) : null,
    spacers: document.querySelectorAll('#pathBody tr.pv-vspacer').length,
    scrollTop: v.scrollTop, scrollHeight: v.scrollHeight, clientH: v.clientHeight,
  };
}"""


def test_large_flat_grid_materializes_only_a_window(browser: Any, served: str) -> None:
    """THE S5 mechanism: at 900 rows the tbody must hold a viewport window plus spacer(s),
    not 900 painted rows — and the spacers must keep the scrollbar honest (the pane's
    scrollHeight still spans the whole schedule). Pre-fix this fails with painted == 900."""
    page, errors = _open(browser, served, "big")
    st = page.evaluate(_STATE)
    assert st["painted"] < 400, f"windowing did not engage: {st['painted']} rows materialized"
    assert st["painted"] >= 40, f"window too small to cover the viewport: {st}"
    assert st["spacers"] >= 1, "no spacer row — the scrollbar would lie about the grid's extent"
    assert st["scrollHeight"] > st["clientH"] * 5, f"scroll range collapsed: {st}"
    assert errors == []
    page.context.close()


def test_scrolling_to_the_bottom_paints_the_tail_rows(browser: Any, served: str) -> None:
    """A scroll to the pane's bottom must re-aim the window onto the LAST rows (the highest
    UIDs) while staying windowed — and the scroll position must survive the repaint (the
    repaint clears the tbody, which clamps scrollTop to 0 unless it is captured/restored)."""
    page, errors = _open(browser, served, "big")
    page.evaluate(
        "() => { const v = document.querySelector('.path-view'); v.scrollTop = v.scrollHeight; }"
    )
    page.wait_for_timeout(900)
    st = page.evaluate(_STATE)
    assert st["painted"] < 400, f"grid fell back to a full paint: {st['painted']} rows"
    assert st["maxUid"] == BIG_N, f"tail row not materialized after scroll-to-bottom: {st}"
    assert st["scrollTop"] > st["scrollHeight"] / 2, f"scroll position lost on repaint: {st}"
    assert errors == []
    page.context.close()


def test_small_grid_stays_fully_painted(browser: Any, served: str) -> None:
    """The boundary-setter (PASS side): 300 rows sits under WINDOW_MIN_ROWS and must paint in
    FULL, exactly as every schedule this size always has — TP5's 121-row long-span suite and
    the ADR-0438 seat contract both measure on full paints. An over-eager threshold goes red
    here first (proven by the ADR's mutation battery: threshold 400 -> 100 fails this test)."""
    page, errors = _open(browser, served, "small")
    st = page.evaluate(_STATE)
    assert st["painted"] == SMALL_N, f"small grid was windowed: {st}"
    assert st["spacers"] == 0, f"spacer rows on a full paint: {st}"
    assert errors == []
    page.context.close()


def test_find_reaches_an_off_window_row(browser: Any, served: str) -> None:
    """Find searches and marks the DOM (SFGantt.findTask), so a windowed grid must force one
    full paint before delegating — an off-window UID must come back found, marked and scrolled
    into the pane. Without the escape the status honestly reports no match, which is exactly
    the defect: the row exists in the data and Find cannot see it."""
    page, errors = _open(browser, served, "big")
    target = BIG_N - 5  # comfortably below the initial top window
    page.fill("#pathFind", str(target))
    page.dispatch_event("#pathFind", "change")
    found = None
    for _ in range(10):  # scrollIntoView is smooth (async) — poll to its landing
        page.wait_for_timeout(500)
        found = page.evaluate(
            """() => {
          const r = document.querySelector('tr.row-found');
          if (!r) return {found: false};
          const v = document.querySelector('.path-view');
          const rect = r.getBoundingClientRect(), vrect = v.getBoundingClientRect();
          return {found: true, uid: r.getAttribute('data-uid'),
                  painted: document.querySelectorAll('#pathBody tr[data-uid]').length,
                  inPane: rect.bottom > vrect.top && rect.top < vrect.bottom};
        }"""
        )
        if found["found"] and found["inPane"]:
            break
    assert found and found["found"], "Find never marked the off-window row"
    assert found["uid"] == str(target), found
    assert found["painted"] == BIG_N, f"Find did not force the full paint: {found}"
    assert found["inPane"], f"found row never scrolled into the pane: {found}"
    assert errors == []
    page.context.close()


def test_show_links_disables_windowing(browser: Any, served: str) -> None:
    """The connector overlay joins arbitrary row pairs, so "Show links" must force a full
    paint — a windowed tbody would silently drop every link that crosses the window edge."""
    page, errors = _open(browser, served, "big")
    assert page.evaluate(_STATE)["painted"] < 400  # windowed before the toggle
    page.check("#pathShowLinks")
    page.wait_for_timeout(1500)
    st = page.evaluate(_STATE)
    assert st["painted"] == BIG_N, f"links view still windowed: {st}"
    assert st["spacers"] == 0, st
    assert errors == []
    page.context.close()
