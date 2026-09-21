"""A RENDER failure and a LOAD failure are different findings and must not print one sentence.

R-09 (CI-03's residual). Every fetch-driven page module has the same shape::

    fetch("/api/…")
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) { …builds the panel, draws the chart… })
      .catch(function () { box.textContent = "Failed to load the … data."; });

The terminal ``.catch`` is attached to the WHOLE chain, so it also covers the ``.then`` that
draws. When the draw throws, the analyst is told the data failed to load — a TRUE symptom with a
FALSE explanation, in a tool whose output is testimony. ``test_chartframe_load_order_browser``
already names this in prose ("the module's own ``.catch`` swallows the error and prints 'Failed
to load the … data.' (a FALSE sentence — the data loaded; the render threw)"); ADR-0461 fixed the
CAUSE it had found and left the conflation.

**The registered population was wrong, and the ledger's own literal is why.** R-09 and
``fetch_catch_failed_to_load_modules`` both count files carrying ``"Failed to load the"`` — 13.
The class is ``"Failed to load"``, and three modules omit the article: ``app.js``
("Failed to load analysis."), ``trend.js`` ("Failed to load trend data.") and ``trend_drill.js``
("Failed to load quality drill-down data."). **Sixteen**, measured 2026-09-21 — and the three
invisible ones were found by RENDERING ``/trend`` under a poisoned draw, not by reading the
ledger. The census below therefore keys on the class, not the article, and
``test_the_ledger_literal_does_not_undercount_the_class`` pins the gap closed.

Measured on the pristine tree (2026-09-21), in real Chromium, with the draw dependency poisoned
so the fetch succeeds and only the draw throws — the control being the SAME page with the asset
served untouched:

===================  ==========  ==============  ====================  ==================
variant              module      dep reached     every /api/ response  what the page says
===================  ==========  ==============  ====================  ==================
control              cei.js      0               200                   (nothing)
POISONED             cei.js      1               200                   "Failed to load …"
control              path_evo    0               200                   (nothing)
POISONED             path_evo    3               200                   "Failed to load …"
control              dashboard   0               200                   (nothing)
POISONED             dashboard   1               200                   "Failed to load …"
===================  ==========  ==============  ====================  ==================

**The row's own prescribed witness does not reach its own named instance.** R-09 asks for a stub
of ``SFChartFrame.axisTitles`` "green on each of the 13 modules"; only TEN of the sixteen
reference ``SFChartFrame`` at all. The rest draw through ``SFGantt`` (``driving_tiers``,
``findings_drill``, ``path_evolution`` — the row's named instance — ``ribbon_drill`` and
``app``) or ``SFDrill`` (``dashboard``). The population is therefore poisoned per DEPENDENCY
FAMILY, three assets covering 16 of 16, and the family map is asserted to cover the COMPUTED
population so a seventeenth module cannot slip in uncovered.

Teeth, because this repo's most-repeated defect is a green test that could never fail:

* the page under test is asserted to actually CARRY the module under test (a route that stopped
  emitting the script would otherwise pass vacuously — ``driving_tiers.js`` is emitted only for a
  ``/driving-path`` target that has driving tiers);
* the poisoned dependency is asserted to have been REACHED (the thrower counts itself), so a
  poisoning that stopped working cannot read as a fix;
* every ``/api/`` response the browser saw is asserted to be 200, so "the data loaded" is measured
  rather than assumed — without it this test could not tell a draw throw from a real outage;
* two modules are CLICK-DRIVEN (``findings_drill`` fetches on a citation's ``a.cite-more``,
  ``ribbon_drill`` on a ``.rib-cell[data-metric]``). A first cut loaded their pages and asserted
  on a page that had never fetched at all: both read "no sentence at all" and the test was red for
  the wrong reason. Their trigger is clicked, and the click is asserted to have found a target.

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES this (ADR-0418).
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"
CHROME = ROOT / "src" / "schedule_forensics" / "web" / "chrome.py"

#: The class of load-failure sentence. NOT ``"Failed to load the"`` — that article is what hid
#: three of the sixteen modules from the register and from the wp8 ledger.
LOAD_LITERAL = "Failed to load"

#: The article-bearing literal the ledger used to count. Kept only to pin the undercount closed.
LEDGER_LITERAL = "Failed to load the"

#: The seam that separates the two findings (``static/loader.js``).
SEAM = "SFLoad.drawn"

#: What a draw failure must say instead — never the load sentence.
DRAW_LITERAL = "could not be drawn"

LOADER_TAG = '<script src="/static/loader.js"></script>'
MAIN_OPEN = "<main>{{ banner }}{{ body }}</main>"

#: module -> (route, the asset defining its draw dependency, that dependency's global).
#: Routes are asserted below to serve the module; the map is asserted to cover the census.
CASES: dict[str, tuple[str, str, str]] = {
    "cei.js": ("/cei", "chartframe.js", "SFChartFrame"),
    "curves.js": ("/curves", "chartframe.js", "SFChartFrame"),
    "drift.js": ("/forecast", "chartframe.js", "SFChartFrame"),
    "histogram.js": ("/analysis/Project2", "chartframe.js", "SFChartFrame"),
    "margin.js": ("/trend", "chartframe.js", "SFChartFrame"),
    "scatter.js": ("/analysis/Project2", "chartframe.js", "SFChartFrame"),
    "scurve.js": ("/scurve", "chartframe.js", "SFChartFrame"),
    "wbs.js": ("/wbs/Project2", "chartframe.js", "SFChartFrame"),
    "trend.js": ("/trend", "chartframe.js", "SFChartFrame"),
    "trend_drill.js": ("/trend", "chartframe.js", "SFChartFrame"),
    "driving_tiers.js": ("/driving-path?target=145", "gantt.js", "SFGantt"),
    "findings_drill.js": ("/integrity", "gantt.js", "SFGantt"),
    "path_evolution.js": ("/evolution", "gantt.js", "SFGantt"),
    "ribbon_drill.js": ("/ribbon", "gantt.js", "SFGantt"),
    "app.js": ("/analysis/Project2", "gantt.js", "SFGantt"),
    "dashboard.js": ("/", "drilldown.js", "SFDrill"),
}

#: Modules whose fetch fires only on a click — the selector that starts it.
TRIGGER: dict[str, str] = {
    "findings_drill.js": "a.cite-more[data-finding]",
    "ribbon_drill.js": ".rib-cell[data-metric]",
}

#: Appended to the served dependency asset: every function the global exposes throws, and counts
#: itself first so "was the draw dependency reached?" is measured rather than inferred.
POISON = """
;(function () {
  var o = window.%(g)s;
  if (!o) return;
  var n = {};
  for (var k in o) {
    if (typeof o[k] === "function") {
      n[k] = function () {
        window.__SF_PROBE_HITS = (window.__SF_PROBE_HITS || 0) + 1;
        throw new Error("SF-PROBE-RENDER-THROW");
      };
    } else {
      n[k] = o[k];
    }
  }
  window.%(g)s = n;
})();
"""


def _census(literal: str = LOAD_LITERAL) -> set[str]:
    """The modules that print a load sentence — COMPUTED, never hand-listed."""
    return {p.name for p in STATIC.glob("*.js") if literal in p.read_text(encoding="utf-8")}


def test_the_case_map_covers_exactly_the_modules_that_print_a_load_sentence() -> None:
    """A seventeenth module must not be able to join the population uncovered."""
    census = _census()
    assert census, "the census found no module printing a load sentence — the glob is wrong"
    assert set(CASES) == census, (
        "the poisoned-case map and the computed population disagree: "
        f"uncovered={sorted(census - set(CASES))} stale={sorted(set(CASES) - census)}"
    )


def test_the_ledger_literal_does_not_undercount_the_class() -> None:
    """The three article-less sentences are the reason this row's population was 13, not 16.
    Whatever the ledger counts, the CLASS is what gets fixed — if a future module writes
    "Failed to load analysis." again, the class census sees it and the article census does not."""
    article = _census(LEDGER_LITERAL)
    whole = _census()
    assert article <= whole
    assert whole - article == {"app.js", "trend.js", "trend_drill.js"}, (
        "the set of modules whose load sentence omits the article has changed: "
        f"{sorted(whole - article)}"
    )


def test_the_seam_never_quotes_the_literals_it_censuses() -> None:
    """``loader.js`` is inside the glob the census reads, so a seam that quotes the load sentence
    in its own doc comment counts ITSELF and the population silently becomes seventeen. Measured:
    the first cut did exactly that and three assertions went red naming ``loader.js``. Same class
    as the pre-commit hook's rule against writing a signature literal in its own comments, and as
    ``pgrep -f`` matching its own shell."""
    seam = (STATIC / "loader.js").read_text(encoding="utf-8")
    quoted = [lit for lit in (LOAD_LITERAL, DRAW_LITERAL) if lit in seam]
    assert not quoted, (
        f"loader.js quotes the literal(s) it censuses {quoted} and therefore counts itself; "
        "describe the sentence instead of writing it"
    )


def test_every_module_routes_its_draw_through_the_loader_seam() -> None:
    """The fix, at its source: the draw runs inside the seam, so a throw there is reported as a
    DRAW failure and never reaches the chain's terminal ``.catch``. Red on the pristine tree,
    where no module mentions the seam."""
    missing = sorted(
        name for name in _census() if SEAM not in STATIC.joinpath(name).read_text(encoding="utf-8")
    )
    assert not missing, f"these modules still funnel a draw throw into the load .catch: {missing}"


def test_every_module_still_reports_a_genuine_load_failure() -> None:
    """The load sentence must SURVIVE the fix — a fetch failure is still a load failure."""
    assert len(_census()) == len(CASES)


def test_every_module_words_its_draw_failure_distinctly() -> None:
    """Each module must carry the draw sentence too, or its draw failure has nowhere to be said."""
    missing = sorted(
        name
        for name in _census()
        if DRAW_LITERAL not in STATIC.joinpath(name).read_text(encoding="utf-8")
    )
    assert not missing, f"these modules have no draw-failure sentence: {missing}"


def test_the_layout_emits_the_loader_seam_before_main() -> None:
    """``loader.js`` sits in the layout HEAD, like ``gantt.js`` / ``chartframe.js`` (ADR-0461):
    the seam must be defined before any body script — or any callback one schedules — can run."""
    layout = CHROME.read_text(encoding="utf-8")
    start = layout.index("_LAYOUT = Template(")
    head = layout[start : layout.index(MAIN_OPEN, start)]
    assert LOADER_TAG in head, "loader.js must be emitted in the layout HEAD, before <main>"


pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _poisoned_app(dep_file: str, dep_global: str) -> Any:
    """The golden pair loaded, with ONE asset served with a thrower appended."""
    app = create_app(SessionState())
    body = STATIC.joinpath(dep_file).read_text(encoding="utf-8") + POISON % {"g": dep_global}

    @app.middleware("http")
    async def poison(request: Any, call_next: Any) -> Any:
        if request.url.path == f"/static/{dep_file}":
            return Response(content=body, media_type="text/javascript")
        return await call_next(request)

    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
            assert r.status_code == 200, (name, r.status_code)
    return app


def _serve(app: Any) -> tuple[Any, str]:
    import uvicorn

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(120):
        if server.started:
            break
        time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


_STATE = """() => ({
  hits: window.__SF_PROBE_HITS || 0,
  load_worded: [...document.querySelectorAll('main *')]
    .filter(n => n.children.length === 0 && /Failed to load/i.test(n.textContent || ''))
    .map(n => n.textContent.trim()),
  draw_worded: [...document.querySelectorAll('main *')]
    .filter(n => n.children.length === 0 && /could not be drawn/i.test(n.textContent || ''))
    .map(n => n.textContent.trim()),
})"""

#: dep asset -> the modules drawn through it (derived from CASES, so it cannot drift).
FAMILIES = sorted({dep for _route, dep, _g in CASES.values()})


@pytest.mark.parametrize("dep_file", FAMILIES)
def test_a_draw_throw_never_reads_as_a_load_failure(dep_file: str) -> None:
    """Per dependency family: poison the draw, then require every page that draws through it to
    say the DRAW failed and never that the LOAD failed — with the data proven to have arrived."""
    from playwright.sync_api import sync_playwright

    from web.browser_chrome import chrome_kwargs

    members = {m: r for m, (r, dep, _g) in CASES.items() if dep == dep_file}
    dep_global = next(g for _r, dep, g in CASES.values() if dep == dep_file)
    server, base = _serve(_poisoned_app(dep_file, dep_global))
    problems: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**chrome_kwargs())
            for module, route in sorted(members.items()):
                ctx = browser.new_context(viewport={"width": 1500, "height": 1000})
                page = ctx.new_page()
                api: list[int] = []
                # `sink=api` binds this page's list explicitly: a late-bound closure would let a
                # listener from the previous route append into the next one's evidence (ruff B023)
                page.on(
                    "response",
                    lambda r, sink=api: sink.append(r.status) if "/api/" in r.url else None,
                )
                page.goto(base + route, wait_until="domcontentloaded")
                # never networkidle on this app: heartbeat.js / sysmon.js never settle
                page.wait_for_timeout(1800)
                html = page.content()
                # TEETH 1 — the page really carries the module under test
                assert f"/static/{module}" in html, (
                    f"{route} no longer serves {module}: this case would pass vacuously"
                )
                # click-driven modules never fetch on load; a page that never fetched proves
                # nothing about the .catch under test
                sel = TRIGGER.get(module)
                if sel:
                    node = page.query_selector(sel)
                    assert node is not None, (
                        f"{module} @ {route}: no {sel} to click, so its fetch never fires and "
                        "this case would pass vacuously"
                    )
                    node.click()
                    page.wait_for_timeout(1800)
                state = page.evaluate(_STATE)
                # TEETH 2 — the draw dependency really was reached and really threw
                assert state["hits"] >= 1, (
                    f"{module} @ {route}: the poisoned {dep_global} was never called "
                    "(nothing was proven about a draw failure)"
                )
                # TEETH 3 — the data provably arrived, so a load sentence is provably false
                assert api and all(s == 200 for s in api), (
                    f"{module} @ {route}: an /api/ response was not 200 ({sorted(set(api))}); "
                    "a load failure would be a TRUE sentence and this case proves nothing"
                )
                if state["load_worded"] or not state["draw_worded"]:
                    problems.append(
                        f"{module} @ {route}: load-worded={state['load_worded']} "
                        f"draw-worded={state['draw_worded']}"
                    )
                ctx.close()
            browser.close()
    finally:
        server.should_exit = True
    assert not problems, (
        f"a draw throw behind {dep_file} still reads as a load failure:\n  " + "\n  ".join(problems)
    )
