"""/analysis materializes only the visible row window at scale (operator 2026-09-02, perf).

After the shared-background painters (test_gantt_row_dom_budget_browser.py) the operator-scale
grid (2,125 rows) still scrolled at ~117 ms/frame with a 1.7 s rebuild: the remaining cost is
NATIVE — layout + sticky positioning of 12,750 frozen cells and a 34,000-px-tall table — not
script (CPU profile: 3.6 s of 4.8 s sampled in "(program)"). /path solved the same shape in
ADR-0442 (windowed paintRows, 1,623 ms → 49 ms). This ports that window to /analysis: at or above
WINDOW_MIN_ROWS the tbody carries the viewport slice ± overscan between two spacer rows; a
vertical scroll re-aims it; Find, "links" and print force a full paint (they address arbitrary
rows). The fixture is TP5 replicated five times with UID offsets (605 rows) — above the window
floor, below the full-paint suites' 121. FAIL-side tests were RED on the pre-fix tree (every row
materialized: 605 `tr[data-uid]`).
"""

from __future__ import annotations

import json
import re
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
BASE = REPO / "tests" / "fixtures" / "test_projects" / "TP5_LongSpan_Synthetic.xml"
NAME = "TP5_x5.xml"
KEY = "TP5_x5"
COPIES = 5


def _replicated() -> bytes:
    xml = BASE.read_text(encoding="utf-8")
    m = re.search(r"<Tasks>(.*)</Tasks>", xml, re.S)
    assert m
    block = m.group(1)
    copies = [block]
    for k in range(1, COPIES):
        off = 100000 * k
        c = re.sub(
            r"<UID>(\d+)</UID>", lambda mm, o=off: f"<UID>{int(mm.group(1)) + o}</UID>", block
        )
        c = re.sub(
            r"<PredecessorUID>(\d+)</PredecessorUID>",
            lambda mm, o=off: f"<PredecessorUID>{int(mm.group(1)) + o}</PredecessorUID>",
            c,
        )
        c = re.sub(r"<Name>([^<]*)</Name>", lambda mm, kk=k: f"<Name>{mm.group(1)} #{kk}</Name>", c)
        copies.append(c)
    return xml.replace(m.group(0), "<Tasks>" + "".join(copies) + "</Tasks>").encode("utf-8")


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
        files = [("files", (NAME, _replicated(), "text/xml"))]
        meta = json.dumps([{"rel": NAME, "mtime": 1_700_000_000_000}])
        assert c.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
        total = len(c.get(f"/api/analysis/{KEY}").json()["activities"])
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", total
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


_STATE = """() => { const g = document.getElementById('grid');
  return {painted: g.querySelectorAll('tbody tr[data-uid]').length,
          spacers: g.querySelectorAll('tbody tr.g-vspacer').length,
          scrollH: g.scrollHeight, clientH: g.clientHeight}; }"""


def _open(browser: Any, served: tuple[str, int]) -> Any:
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(f"{served[0]}/analysis/{KEY}", wait_until="load")
    page.wait_for_selector("#grid table.gantt-grid", timeout=60000)
    page.wait_for_timeout(800)
    return page


def test_only_the_viewport_window_is_materialized_at_scale(
    browser: Any, served: tuple[str, int]
) -> None:
    total = served[1]
    assert total >= 500, f"fixture too small to exercise the window: {total}"
    page = _open(browser, served)
    s = page.evaluate(_STATE)
    assert s["painted"] < total / 2, f"{s['painted']} of {total} rows materialized — no window"
    assert s["spacers"] >= 1, "no spacer row keeps the scrollbar honest"
    # the scroll extent still spans every row (spacers), so the scrollbar is truthful
    assert s["scrollH"] >= total * 12, f"scroll extent {s['scrollH']} too short for {total} rows"
    page.context.close()


def test_scrolling_re_aims_the_window_to_the_tail(browser: Any, served: tuple[str, int]) -> None:
    page = _open(browser, served)
    last_uid = page.evaluate(
        """async () => { const api = location.pathname.replace('/analysis/', '/api/analysis/');
             const r = await fetch(api);
             const j = await r.json(); return j.activities[j.activities.length - 1].unique_id; }"""
    )
    page.evaluate(
        "() => { const g = document.getElementById('grid'); g.scrollTop = g.scrollHeight; }"
    )
    page.wait_for_timeout(700)
    found = page.evaluate(
        "(uid) => !!document.querySelector('#grid tr[data-uid=\"' + uid + '\"]')", last_uid
    )
    assert found, (
        f"the tail row (UID {last_uid}) was not materialized after scrolling to the bottom"
    )
    s = page.evaluate(_STATE)
    assert s["painted"] < served[1] / 2, "scrolling to the bottom un-windowed the grid"
    page.context.close()


def test_find_reaches_a_row_outside_the_window(browser: Any, served: tuple[str, int]) -> None:
    page = _open(browser, served)
    last_uid = page.evaluate(
        """async () => { const api = location.pathname.replace('/analysis/', '/api/analysis/');
             const r = await fetch(api);
             const j = await r.json(); return j.activities[j.activities.length - 1].unique_id; }"""
    )
    page.fill("#gridFind", str(last_uid))
    page.dispatch_event("#gridFind", "change")
    page.wait_for_timeout(800)
    hit = page.evaluate(
        "(uid) => { const r = document.querySelector('#grid tr[data-uid=\"' + uid + '\"]');"
        " return r ? r.className : null; }",
        last_uid,
    )
    assert hit is not None and "row-found" in hit, f"Find did not mark the tail row: {hit}"
    page.context.close()
