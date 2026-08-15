"""B1's table captions, RENDERED — every DOM_PENDING module driven in a real browser (ADR-0340).

`test_axis_titles.py` proves each module CALLS `SFGantt.tableCaption`, and
`dom_caption_harness.mjs` proves the helper builds the right node in the right place. Neither
proves the call is ever REACHED: these captions are built inside `.then()` callbacks, click
handlers and a modal, so a module can hold a perfectly good caption call on a code path the app
never takes. That is the standing "'I proved my tests can fail' is not 'I tested the feature'"
lesson, and the specific trap here is a load-order one — every captioned table is built by a
script INSIDE `<main>`, and `whatif.js` captions SYNCHRONOUSLY at parse time, so a helper hung
off `window.SFChartFrame` (emitted after `</main>`) would leave that page's two grids silently
uncaptioned with the whole source-level suite still green.

So each module is driven through its REAL trigger and the caption read back off the live DOM:

* `whatif.js` — /evolution, both grids, rendered at parse time (the load-order proof);
* `driving_tiers.js` — /driving-path?target=…, rendered after /api/analysis resolves;
* `workbench.js` — /workbench, rendered after /api/workbench resolves;
* `findings_drill.js` — /integrity, after clicking a finding's "view all N" link;
* `ribbon_drill.js` — /ribbon, after clicking a metric cell;
* `scorecards.js` — /scorecards, after a real Monte-Carlo run (the one table whose row unit is
  a percentile rather than an activity);
* `drilldown.js` — the shared drill MODAL, after clicking an `.sf-drill` trigger.

Every assertion reads the STRUCTURE (the table's first element child, parsed into tag/class/text)
rather than regex-scanning the page — a `.*?` across repeated tables would let any table's caption
satisfy any table's assertion. Visibility is measured in all four themes, because a caption that
inherits a transparent colour is present in the DOM and absent on the operator's screen.

Skips unless playwright + the bundled chromium are present (same posture as the other chromium
modules — the runtime stays stdlib-only, Law 1).
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
# build-agnostic (TEST-01, ADR-0406): the FIRST vendored chromium, whatever build the
# container ships — a chromium bump must never silently skip this module again
_PW_CHROMES = sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome"))
CHROME = _PW_CHROMES[0] if _PW_CHROMES else Path("/opt/pw-browsers/absent/chrome")

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason=f"bundled chromium not at {CHROME}")

THEMES = ("console", "daylight", "apollo", "jarvis")

#: The golden pair's driving-path target. Asserted to populate the panel before anything is read
#: off it, so a fixture change fails loudly here instead of silently skipping the caption check.
TIERS_TARGET = 4


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            assert (
                c.post(
                    "/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")}
                ).status_code
                == 200
            )

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


#: Reads ONE table's caption as structure — the element the browser actually made the table's
#: first child, with its tag, class and text kept together. Returning a record per table (rather
#: than scanning the page for "a caption somewhere") is what stops one table's caption from
#: satisfying another table's assertion.
_PROBE = """
(sel) => {
  const t = document.querySelector(sel);
  if (!t) return { found: false, reason: "no table matched " + sel };
  const first = t.firstElementChild;
  if (!first) return { found: false, reason: "table is empty" };
  const cs = getComputedStyle(first);
  return {
    found: true,
    tag: first.tagName,
    cls: first.className,
    text: (first.textContent || "").trim(),
    display: cs.display,
    color: cs.color,
    fontSize: cs.fontSize,
    width: first.getBoundingClientRect().width,
    height: first.getBoundingClientRect().height,
    rows: t.querySelectorAll("tr").length,
  };
}
"""


def _read_caption(page: Any, table_selector: str) -> dict[str, Any]:
    probe: dict[str, Any] = page.evaluate(_PROBE, table_selector)
    assert probe["found"], f"{table_selector}: {probe.get('reason')}"
    return probe


def _assert_captioned(probe: dict[str, Any], expected: str, where: str) -> None:
    """The caption contract, checked exactly — not 'a caption exists somewhere on the page'."""
    assert probe["tag"] == "CAPTION", (
        f"{where}: the table's FIRST child is <{probe['tag'].lower()}>, not <caption> — "
        "invalid markup, and the table's accessible name stops being reliable"
    )
    assert probe["cls"] == "ch-atd", f"{where}: caption class is {probe['cls']!r}, want 'ch-atd'"
    assert probe["text"] == expected, f"{where}: caption text is {probe['text']!r}"
    # present in the DOM is not the same as on screen (the standing rank-2 lesson)
    assert probe["display"] != "none", f"{where}: caption is display:none"
    assert probe["width"] > 0 and probe["height"] > 0, f"{where}: caption has no box — {probe}"
    assert "rgba(0, 0, 0, 0)" not in probe["color"], f"{where}: caption colour is transparent"


def _page(pw: Any, served: str, route: str) -> tuple[Any, Any]:
    browser = pw.chromium.launch(executable_path=str(CHROME))
    page = browser.new_page(viewport={"width": 1360, "height": 900})
    page.goto(served + route, wait_until="domcontentloaded")
    return browser, page


WHATIF_OFF = "Activities whose own changes took them OFF the critical path — one row per activity"
WHATIF_ON = "Activities ADDED to the critical path between the two versions — one row per activity"


def test_whatif_captions_both_grids_at_parse_time(served: str) -> None:
    """The load-order proof, and the only place it can be made.

    whatif.js runs its render SYNCHRONOUSLY inside its IIFE — no fetch, no click, no
    DOMContentLoaded — from a script tag inside `<main>`. If the DOM caption helper lived in
    chartframe.js (emitted after `</main>`) `SFGantt`'s stand-in would be undefined at that
    instant and BOTH captions would be missing, with every source-level assertion still passing.

    It also proves the per-table text is really per-table: these two grids carry identical column
    headers, so a shared caption string would read as correct in a source diff and be wrong on
    screen for one of them.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/evolution")
        page.wait_for_selector("#whatifTable table caption.ch-atd", timeout=15000)

        off = _read_caption(page, "#whatifTable table")
        _assert_captioned(off, WHATIF_OFF, "/evolution #whatifTable")

        on = _read_caption(page, "#whatifAddedTable table")
        _assert_captioned(on, WHATIF_ON, "/evolution #whatifAddedTable")

        assert off["text"] != on["text"], "the two grids share a caption — one of them is wrong"
        browser.close()


def test_driving_tiers_captions_the_tier_table(served: str) -> None:
    """Rendered after /api/analysis resolves — a path a synchronous probe would miss entirely."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, f"/driving-path?target={TIERS_TARGET}")
        assert page.locator("#drivingTiers").count() == 1, (
            f"target={TIERS_TARGET} no longer populates the tiers panel — the golden fixture "
            "moved, and this test would otherwise pass by never finding a table"
        )
        page.wait_for_selector("#drivingTiers table caption.ch-atd", timeout=15000)
        probe = _read_caption(page, "#drivingTiers table")
        _assert_captioned(
            probe,
            "Driving-path activities by tier — one row per activity",
            "/driving-path #drivingTiers",
        )
        assert probe["rows"] > 1, "the tier table rendered no data rows — caption proves nothing"
        browser.close()


def test_workbench_captions_its_matrix(served: str) -> None:
    """The pre-existing DOM_TABLE_CAPTIONED member, re-verified after ADR-0340 moved it onto the
    shared helper — the conversion must not have cost it its caption."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/workbench")
        page.wait_for_selector("table.wb-matrix caption.ch-atd", timeout=15000)
        _assert_captioned(
            _read_caption(page, "table.wb-matrix"),
            "Selected metrics × schedule version",  # noqa: RUF001 — matches workbench.js exactly
            "/workbench matrix",
        )
        browser.close()


def test_findings_drill_captions_the_cited_activity_list(served: str) -> None:
    """Click-driven: the caption text names the FINDING, so it is built per selection."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/integrity")
        link = page.locator("a.cite-more[data-finding]").first
        assert link.count() == 1, "/integrity offers no citation drill — nothing to caption"
        link.click()
        page.wait_for_selector("#findingsDrill table caption.ch-atd", timeout=15000)
        probe = _read_caption(page, "#findingsDrill table")
        assert probe["tag"] == "CAPTION" and probe["cls"] == "ch-atd", probe
        assert probe["text"].startswith("Activities cited by "), probe["text"]
        assert probe["text"].endswith(" — one row per activity"), probe["text"]
        # the finding's own title has to be IN it — otherwise the caption is a constant
        # masquerading as a per-selection name
        assert len(probe["text"]) > len("Activities cited by  — one row per activity"), probe
        _assert_captioned(probe, probe["text"], "/integrity #findingsDrill")
        browser.close()


def test_ribbon_drill_captions_the_metric_drill(served: str) -> None:
    """Click-driven, and the caption names the METRIC that was clicked."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/ribbon")
        cell = page.locator(".rib-cell[data-metric]").first
        assert cell.count() == 1, "/ribbon offers no metric cells — nothing to drill"
        cell.click()
        page.wait_for_selector("#ribbonDrill table caption.ch-atd", timeout=15000)
        probe = _read_caption(page, "#ribbonDrill table")
        assert probe["text"].startswith("Activities behind "), probe["text"]
        assert probe["text"].endswith(" — one row per activity"), probe["text"]
        _assert_captioned(probe, probe["text"], "/ribbon #ribbonDrill")
        browser.close()


def test_scorecards_captions_the_reserve_table(served: str) -> None:
    """The one table in the family whose ROW UNIT is a percentile, not an activity — which is the
    whole reason a caption earns its place here. Needs a real Monte-Carlo run to exist at all."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/scorecards")
        page.wait_for_selector("#reserveRun", timeout=15000)
        page.fill("#reserveDate", "2027-06-30")
        page.fill("#reserveIters", "200")  # keep the on-demand SRA cheap; the table is the point
        page.click("#reserveRun")
        page.wait_for_selector("#reserveOut table caption.ch-atd", timeout=60000)
        probe = _read_caption(page, "#reserveOut table")
        _assert_captioned(
            probe,
            "Schedule reserve by confidence level — one row per percentile",
            "/scorecards #reserveOut",
        )
        assert probe["rows"] > 1, "the reserve table rendered no percentile rows"
        browser.close()


def test_the_drill_modal_captions_its_grid(served: str) -> None:
    """drilldown.js is the shared modal every chart's click-through opens — the one captioned
    table that is not part of any page's static markup."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/scorecards")
        trigger = page.locator(".sf-drill[data-uids], .sf-drill[data-segment]").first
        assert trigger.count() == 1, "/scorecards offers no .sf-drill trigger"
        trigger.click()
        page.wait_for_selector("#sfDrillOverlay table.sf-drill-grid caption.ch-atd", timeout=20000)
        probe = _read_caption(page, "#sfDrillOverlay table.sf-drill-grid")
        assert probe["text"].startswith("Activities behind "), probe["text"]
        assert probe["text"].endswith(" — one row per activity"), probe["text"]
        _assert_captioned(probe, probe["text"], "drill modal")
        browser.close()


@pytest.mark.parametrize("theme", THEMES)
def test_the_caption_stays_visible_in_every_theme(served: str, theme: str) -> None:
    """`.ch-atd` reads `--muted`, and `--muted` is re-declared by every theme.

    DESIGN-SYSTEM.md asks for four-theme verification, and jarvis is the known clobber family. A
    caption rendered in a colour with no alpha — or collapsed to a zero box — is present in the
    HTML and absent on the operator's screen, which is exactly the failure a source pin cannot
    see. Driven on /evolution because both of its grids are captioned at parse time, so the probe
    reads TWO independently-built captions per theme rather than one.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/evolution")
        page.wait_for_selector("#whatifTable table caption.ch-atd", timeout=15000)
        page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
        page.wait_for_timeout(120)

        for sel, want in (
            ("#whatifTable table", WHATIF_OFF),
            ("#whatifAddedTable table", WHATIF_ON),
        ):
            probe = _read_caption(page, sel)
            _assert_captioned(probe, want, f"{theme} {sel}")
            # the type ramp must resolve to a real size — an unresolved var() computes to 0px
            size = float(probe["fontSize"].rstrip("px"))
            assert size > 0, f"{theme} {sel}: --sf-fs-axis-title did not resolve ({probe})"
        browser.close()


@pytest.mark.parametrize("theme", THEMES)
def test_the_modal_caption_stays_visible_in_every_theme(served: str, theme: str) -> None:
    """The SECOND rendering context, because one is not coverage (the standing gate-shape #3).

    The test above reads captions sitting in the normal page flow. The drill modal is a different
    stack — an `.sf-drill-overlay` with its own backdrop, over a `.sf-drill-dialog.panel` — and a
    theme that restyles `.panel` inside an overlay can leave the caption legible on `/evolution`
    and invisible here without touching one byte of shared CSS. `--muted` over a scrim is exactly
    the pairing that goes wrong, so it is measured where it actually renders.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page = _page(p, served, "/scorecards")
        page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
        trigger = page.locator(".sf-drill[data-uids], .sf-drill[data-segment]").first
        assert trigger.count() == 1, "/scorecards offers no .sf-drill trigger"
        trigger.click()
        page.wait_for_selector("#sfDrillOverlay table.sf-drill-grid caption.ch-atd", timeout=20000)
        page.wait_for_timeout(120)

        probe = _read_caption(page, "#sfDrillOverlay table.sf-drill-grid")
        _assert_captioned(probe, probe["text"], f"{theme} drill modal")
        assert probe["text"].startswith("Activities behind "), probe["text"]
        size = float(probe["fontSize"].rstrip("px"))
        assert size > 0, f"{theme} modal: --sf-fs-axis-title did not resolve ({probe})"

        # the caption must not be painted the same colour as the surface behind it — a
        # theme-supplied `--muted` that collapses onto the dialog background is invisible while
        # every presence assertion above still passes
        surface = page.evaluate(
            "() => getComputedStyle("
            "document.querySelector('#sfDrillOverlay .sf-drill-dialog')).backgroundColor"
        )
        assert probe["color"] != surface, (
            f"{theme}: modal caption colour {probe['color']} equals the dialog background — "
            "present in the DOM, invisible on screen"
        )
        browser.close()
