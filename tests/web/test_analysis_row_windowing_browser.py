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


# ── ADR-0458: a scroll re-aim keeps the rows that stay on screen (incremental window) ────────

_MARK_MID = """() => { const g = document.getElementById('grid');
  const trs = [...g.querySelectorAll('tbody tr[data-uid]')];
  const mid = trs[Math.floor(trs.length / 2)];
  mid.__sfProbe = true;
  return {uid: mid.getAttribute('data-uid'), start: trs[0].getAttribute('data-uid'),
          painted: trs.length}; }"""
_CHECK_MARK = """(uid) => { const g = document.getElementById('grid');
  const trs = [...g.querySelectorAll('tbody tr[data-uid]')];
  const tr = g.querySelector('tbody tr[data-uid="' + uid + '"]');
  return {present: !!tr, same: !!(tr && tr.__sfProbe), connected: !!(tr && tr.isConnected),
          start: trs.length ? trs[0].getAttribute('data-uid') : null, painted: trs.length,
          spacers: g.querySelectorAll('tbody tr.g-vspacer').length,
          scrollTop: g.scrollTop, scrollH: g.scrollHeight}; }"""


def test_a_scroll_re_aim_keeps_the_nodes_of_rows_that_stay_in_the_window(
    browser: Any, served: tuple[str, int]
) -> None:
    """Scroll so the window must re-aim (past the overscan margin) while a middle row stays
    inside it: that row's <tr> must be the SAME node afterwards. Pre-ADR-0458 every re-aim
    emptied the tbody and repainted the whole window — observed RED (same=False) on the
    pristine tree — which is where the operator's residual scroll lag lived (a ~115-row
    repaint, half of it native layout, on every step)."""
    page = _open(browser, served)
    before = page.evaluate(_MARK_MID)
    # one viewport plus half the overscan: the window MUST move, the middle row MUST survive
    page.evaluate(
        "() => { const g = document.getElementById('grid'); g.scrollTop += 900 + 20 * 18; }"
    )
    page.wait_for_timeout(600)
    after = page.evaluate(_CHECK_MARK, before["uid"])
    assert after["start"] != before["start"], f"the window did not re-aim: {before} → {after}"
    assert after["present"] and after["connected"], f"the marked row left the window: {after}"
    assert after["same"], f"the row that stayed on screen was repainted as a new node: {after}"
    assert after["spacers"] >= 1 and after["scrollH"] >= served[1] * 12
    assert after["painted"] < served[1] / 2, "the re-aim un-windowed the grid"
    # the rows that ENTERED were pinned like the rest: every painted row's first cell is sticky
    # at the frozen offset (computed style, never the inline attribute)
    frozen = page.evaluate(
        """() => [...document.querySelectorAll('#grid tbody tr[data-uid]')].map(tr => {
          const cs = getComputedStyle(tr.firstElementChild);
          return cs.position === 'sticky' && cs.left !== 'auto'; })"""
    )
    assert frozen and all(frozen), f"{frozen.count(False)} rows lost the frozen column"
    page.context.close()


def test_re_aims_in_both_directions_keep_the_window_contiguous_and_the_extent_honest(
    browser: Any, served: tuple[str, int]
) -> None:
    """Twelve alternating scroll steps: after each, the painted rows are one contiguous run of
    the population in order (no gaps, no duplicates), the spacers hold exactly the rows outside
    the window, and the scroll extent still spans every row."""
    page = _open(browser, served)
    # the population's order comes from the page's own JSON (file order = the grid's default
    # sort); the oracle is guarded: the opening window must be its prefix
    order = [
        str(a["unique_id"])
        for a in page.request.get(f"{served[0]}/api/analysis/{KEY}").json()["activities"]
    ]
    opening = page.evaluate(
        "() => [...document.querySelectorAll('#grid tbody tr[data-uid]')]"
        ".map(t => t.getAttribute('data-uid'))"
    )
    assert opening and order[: len(opening)] == opening, (opening[:5], order[:5])
    total = served[1]
    deltas = [700, 700, -300, 1500, -900, 400, 2200, -2500, 600, 600, -100, 900]
    for d in deltas:
        page.evaluate("(d) => { document.getElementById('grid').scrollTop += d; }", d)
        page.wait_for_timeout(350)
        s = page.evaluate(
            """() => { const g = document.getElementById('grid');
              const rows = [...g.querySelectorAll('tbody tr')];
              const uids = rows.filter(t => t.hasAttribute('data-uid'))
                .map(t => t.getAttribute('data-uid'));
              const kinds = rows.map(t => t.classList.contains('g-vspacer') ? 'S'
                : (t.hasAttribute('data-uid') ? 'R' : 'W'));
              const sp = rows.filter(t => t.classList.contains('g-vspacer'))
                .map(t => parseFloat(t.firstChild.style.height));
              const painted = rows.filter(t => t.hasAttribute('data-uid'));
              const first = painted[0], last = painted[painted.length - 1];
              const pitch = painted.length > 1
                ? (last.offsetTop + last.offsetHeight - first.offsetTop) / painted.length : 0;
              return {uids, kinds: kinds.join(''), sp, pitch, scrollH: g.scrollHeight,
                      clientH: g.clientHeight}; }"""
        )
        assert len(set(s["uids"])) == len(s["uids"]), f"duplicate rows after {d}: {s['kinds']}"
        # the painted rows are ONE contiguous slice of the population, in order
        first = order.index(s["uids"][0])
        assert s["uids"] == order[first : first + len(s["uids"])], (
            f"the window is not a contiguous ordered slice after {d}: {s['kinds']}"
        )
        # and the spacers account for exactly the rows outside it, at the RENDERED row pitch
        # (spacer heights are whole pixels; the pitch is whatever the browser laid out)
        if s["sp"]:
            outside = total - len(s["uids"])
            assert abs(sum(s["sp"]) / outside - s["pitch"]) <= 1.0, (s["sp"], outside, s["pitch"])
        assert s["kinds"].count("S") <= 2 and "SS" not in s["kinds"], s["kinds"]
        assert s["kinds"].strip("S").find("S") < 0, (
            f"a spacer inside the window after {d}: {s['kinds']}"
        )
        assert s["scrollH"] >= total * 12, f"scroll extent {s['scrollH']} too short after {d}"
    page.context.close()


#: MARK stamps the overlay once; CHECK only READS the stamp — a check that re-stamped would be
#: satisfied by a brand-new node (the first draft of this pin did exactly that and stayed green
#: on the "overlay re-created per draw" mutant).
_MARK_LINKS = """() => { const svg = document.querySelector('#grid svg.g-links');
  if (svg) svg.__sfProbe = 'marked';
  return !!svg; }"""
_LINKS = """() => { const g = document.getElementById('grid');
  const svg = g.querySelector('svg.g-links');
  return {present: !!svg, same: !!(svg && svg.__sfProbe === 'marked'),
          paths: svg ? svg.querySelectorAll('path').length : 0,
          painted: g.querySelectorAll('tbody tr[data-uid]').length}; }"""


def test_the_link_overlay_is_one_reused_node_drawing_only_what_the_window_can_see(
    browser: Any, served: tuple[str, int]
) -> None:
    """The dependency-link overlay is ONE svg per pane, kept across scroll re-aims, and it holds
    only the links the materialized window can see — not every relationship in the file.
    Pre-ADR-0458 every re-aim removed and re-created a table-sized svg holding EVERY link
    (observed RED on the pristine tree: a new node after the re-aim; paths ≈ the whole
    population), which was the largest residual scroll cost at operator scale."""
    page = _open(browser, served)
    total = served[1]
    assert page.evaluate(_MARK_LINKS), "links are on by default and the overlay must exist"
    first = page.evaluate(_LINKS)
    assert first["present"] and first["same"]
    # visible-only: a 605-row file has ~one predecessor per row; the window is ~1/4 of it
    assert first["paths"] < total * 0.6, f"the overlay holds the whole file's links: {first}"
    page.evaluate("() => { document.getElementById('grid').scrollTop += 900 + 20 * 18; }")
    page.wait_for_timeout(600)
    after = page.evaluate(_LINKS)
    assert after["present"] and after["same"], f"the overlay was re-created on a re-aim: {after}"
    assert 0 < after["paths"] < total * 0.6, after
    # and the toggle still removes it outright
    page.evaluate(
        "() => { const c = document.getElementById('showLinks'); c.checked = false;"
        " c.dispatchEvent(new Event('change', {bubbles: true})); }"
    )
    page.wait_for_timeout(600)
    assert not page.evaluate(_LINKS)["present"]
    page.context.close()
