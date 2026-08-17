"""The observer storm, MEASURED in a real browser (ADR-0333).

``tests/perf/test_perf_regression.py`` pins the *shape* of the three document-wide
``MutationObserver`` callbacks (records-based, frame-coalesced) so CI — which has no browser —
still fails if a refactor drops it. This module measures the property those contracts stand for:
**how much DOM does one inserted node actually cost?**

The pre-fix form answered "all of it". Every async insertion re-ran
``document.querySelectorAll(".panel h2, … main h3")`` over the whole page and then re-tested every
returned heading against a 114-entry catalog, plus two full-document ``table.gantt-grid`` walks and
one pane walk — and because those callbacks append their own nodes (``stickyScrollbar`` appends a
proxy bar to ``<body>``; ``attachColumnMovers`` appends a grip ``<span>`` to every header cell),
each insertion re-armed the observers and paid the sweep twice.

**The metric is nodes SCANNED, not calls made** — and that distinction is the whole point. Scoping
the query to the inserted node does not reduce the number of ``querySelectorAll`` calls (it can
raise it slightly, since each batched root gets its own now-trivial query); it collapses what each
call has to walk. Measured on ``/analysis/Project5`` with 30 insertions, one per frame:

===========================================  =========  ========
selector                                     before      after
===========================================  =========  ========
``.panel h2, … main h3`` (nodes returned)      1,275         84
``table.gantt-grid`` (nodes returned)             62          0
``#grid, .gantt-scroll, …`` (nodes returned)      31          0
===========================================  =========  ========

There is deliberately **no wall-clock assertion**. The synthetic storm is rAF-bound (30 frames of
paced insertion dominate it), so elapsed time is flat before and after; the saving is work volume,
which is what bites on the operator's real 2,000-row grids and slower hardware. An absolute timing
gate here would assert nothing and flake on CI.

**Skips only when the playwright PACKAGE is absent** — it is not a project dependency (Law 1 keeps
the runtime stdlib-only and air-gapped). The BROWSER is resolved by ``tests/web/browser_chrome.py``,
which prefers a vendored binary and otherwise defers to playwright's own, so a CI runner executes
this module instead of skipping it (BROWSER-ORPHAN-01; the old pinned ``/opt/pw-browsers`` check
skipped everywhere but this container). To run this deliberately::

    pip install playwright
    python -m pytest tests/perf/test_observer_storm.py -q -s
"""

from __future__ import annotations

import importlib.util
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
#: Chromium resolution is ``tests/web/browser_chrome.py``'s single decision (BROWSER-ORPHAN-01):
#: prefer a vendored binary — this image ships 1194 and has no download — else let playwright
#: resolve its own, which is the branch a CI runner takes. Loaded BY PATH, not imported: unlike
#: ``tests/web/``, ``tests/perf/`` carries no ``__init__.py``, so pytest never puts ``tests/`` on
#: ``sys.path`` for this module and ``from web.browser_chrome import …`` would die in collection.
#: Same idiom as ``tests/guards/test_render_oracle_corpus.py``.
_BC_SPEC = importlib.util.spec_from_file_location(
    "sf_browser_chrome", Path(__file__).resolve().parents[1] / "web" / "browser_chrome.py"
)
assert _BC_SPEC is not None and _BC_SPEC.loader is not None
_BC = importlib.util.module_from_spec(_BC_SPEC)
sys.modules["sf_browser_chrome"] = _BC
_BC_SPEC.loader.exec_module(_BC)
chrome_kwargs = _BC.chrome_kwargs

#: One insertion per animation frame — the shape an async chart/grid render actually has, and the
#: pathological case for a non-records observer (a same-frame burst is coalesced by the browser's
#: own record batching anyway, so it would understate the defect).
INSERTIONS = 30

HEAD_SEL = ".panel h2, .panel h3, .chart h3, .tile-head h3, main h2, main h3"
GRID_SEL = "table.gantt-grid"
PANE_SEL = "#grid, .gantt-scroll, .path-view, .sra-grid-scroll"

#: Two INDEPENDENT preconditions, and both must be checked. The chromium path check alone was not
#: enough: in a lean venv that HAS the bundled browser but NOT the pip package (a plain
#: `pip install -e '.[dev]'` — `browser` is its own extra), the skipif passed, the module-scoped
#: `storm` fixture reached its bare `from playwright.sync_api import …`, and both tests ERRORED
#: instead of skipping. Measured on pytest 8.0.2: `1 failed, 3 passed, 2 errors`. `importorskip` is
#: module-level here because EVERY test in this module needs the browser — checking it before the
#: `served` fixture also means no uvicorn server is started only to be thrown away (ADR-0346).
pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    """A real HTTP server with the two golden versions loaded (the browser needs same-origin
    /static, so a TestClient is not enough)."""
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
            assert r.status_code == 200, (name, r.status_code)

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


#: Count the nodes every ``querySelectorAll`` returns, bucketed by selector. Installed AFTER the
#: page has settled, so the boot pass is not what we measure — only what the storm provokes.
_INSTRUMENT = """() => {
  window.__nodes = {};
  for (const proto of [Document.prototype, Element.prototype]) {
    const real = proto.querySelectorAll;
    proto.querySelectorAll = function (sel) {
      const out = real.call(this, sel);
      const k = String(sel);
      window.__nodes[k] = (window.__nodes[k] || 0) + out.length;
      return out;
    };
  }
}"""

_STORM = """async (n) => {
  const host = document.querySelector('main') || document.body;
  for (let i = 0; i < n; i++) {
    const d = document.createElement('div');
    d.className = 'probe-node';
    d.innerHTML = '<h3>Probe heading ' + i + '</h3><p>body</p>';
    host.appendChild(d);
    await new Promise(r => requestAnimationFrame(r));   // one insertion per frame
  }
  await new Promise(r => setTimeout(r, 400));           // let any deferred flush land
  return window.__nodes;
}"""


@pytest.fixture(scope="module")
def storm(served: str) -> Any:
    """Run the insertion storm once and return (nodes-scanned-by-selector, headings-on-page)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(served + "/analysis/Project5", wait_until="networkidle")
        page.wait_for_timeout(1200)
        headings = page.evaluate(f"() => document.querySelectorAll({HEAD_SEL!r}).length")
        page.evaluate(_INSTRUMENT)
        nodes = page.evaluate(_STORM, INSERTIONS)
        browser.close()
    assert headings > 20, f"the probe needs a heading-rich page to be meaningful; got {headings}"
    return nodes, headings


def test_heading_sweep_scales_with_insertions_not_with_the_page(storm: Any) -> None:
    """REGRESSION GATE: the vizhints observer must walk only what was inserted.

    The defect is O(insertions x headings-on-page); the fix is O(insertions). The bound below is
    ``3 x (insertions + headings)`` — comfortably above the measured 84 and far below the measured
    1,275, so it distinguishes the two implementations without pinning an exact count.

    Proved able to fail by reverting ONLY vizhints.js's observer callback to
    ``new MutationObserver(function () { decorate(document); })``: 1,275 scanned, bound 252.
    """
    nodes, headings = storm
    scanned = nodes.get(HEAD_SEL, 0)
    bound = 3 * (INSERTIONS + headings)
    assert scanned <= bound, (
        f"vizhints re-swept the document: {scanned} heading nodes walked for {INSERTIONS} "
        f"insertions on a {headings}-heading page (bound {bound})"
    )


def test_gantt_attachers_do_not_walk_the_document_per_insertion(storm: Any) -> None:
    """REGRESSION GATE: nothing the storm inserts is a Gantt grid or scroll pane, so a
    records-based attacher walks ZERO of them. The pre-fix form walked every grid and every pane
    on the page for each inserted node, twice over (its own grip/bar appends re-armed it).

    Proved able to fail by reverting ONLY gantt.js's observer callback to the three
    ``attach*(document)`` calls: 62 grids and 31 panes walked, bounds 5 and 5.
    """
    nodes, _ = storm
    grids, panes = nodes.get(GRID_SEL, 0), nodes.get(PANE_SEL, 0)
    # a small constant, not 0: an unrelated deferred render on the page may legitimately add one
    assert grids <= 5, f"{grids} gantt-grid nodes walked for {INSERTIONS} unrelated insertions"
    assert panes <= 5, f"{panes} gantt pane nodes walked for {INSERTIONS} unrelated insertions"
