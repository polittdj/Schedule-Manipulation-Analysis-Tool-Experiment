"""/scorecards' Claude Design grid, measured in a REAL browser (ADR-0484).

Markup is not evidence for a claim about GEOMETRY (ADR-0304's lesson). The artboard's auto-fit
grid puts the three framework cards side by side at 1440 px, and each card holds the page's
VERBATIM four-column table, which is wider than a third of the page at its natural width —
measured on the first grid: the NASA STAT table read 449 px inside a 374 px card (console),
585 px in apollo (mono + uppercase) and 466 px in jarvis, and in apollo the DOCUMENT scrolled
sideways (1527 > 1440), the UI-03 defect class ADR-0477 retired. So inside the grid a scorecard
table lays out FIXED and its cells wrap ANYWHERE as a last resort (``app.css``,
``.cd-grid-3 .scorecard-table``) — two mechanisms, and the battery showed EACH ALONE keeps the
table inside its card (a wrap-anywhere cell has a one-character min-content, so even an auto
table shrinks to fit), so the geometry pin goes red only when both are removed, while the
cell-spill pin below goes red the moment the wrap rule alone is removed (a fixed cell then
overflows its own box with an unbreakable token, which no element rect can see). This module
pins, in all four themes: the three cards share one row · no table is wider than its card · no
cell's content is wider than the cell · the document does not scroll sideways · zero page errors
— and, once, the chips' EFFECT: a click opens the other version's page with ITS chip on and ITS
figures (the ADR-0470 rule that a per-file drill's cursor is navigation, proven by a browser
driver, never by markup).

Red first (2026-09-11): with the grid but before either rule, the card-width assertion failed in
all four themes on the measured scroll widths (449 > 374 console, 463 > 453 daylight — the card's
own scrollWidth, 585 > 374 apollo, 466 > 374 jarvis) and apollo failed the sideways-scroll
assertion (1527 > 1440); the rect + spill form below was then observed red on the no-rules
stylesheet by the mutation battery.

Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py`` so a CI runner EXECUTES this module (ADR-0418).
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
THEMES = ("console", "daylight", "apollo", "jarvis")
VIEWPORT = {"width": 1440, "height": 900}

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")


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
        for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
            r = c.post("/upload", files={"files": (name, (GOLD / name).read_bytes(), "text/xml")})
            assert r.status_code == 200

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


#: per card: its box, and its table's and every cell's RIGHT EDGE against the card's — element
#: rects, not scrollWidth: jarvis's corner brackets are `.panel::after { right:-1px }` on every
#: panel by design, which puts the panel's own scrollWidth 1 px past its clientWidth in that
#: theme, and a pin that read scrollWidth would fail on the theme's decoration, not on a table
_GEOMETRY = """() => {
  const cards = [...document.querySelectorAll('.cd-grid-3 > .panel[data-scorecard]')].map(p => {
    const r = p.getBoundingClientRect(), t = p.querySelector('table.scorecard-table');
    const all = [...t.querySelectorAll('th, td')];
    const cells = all.map(c => c.getBoundingClientRect().right);
    const spill = Math.max(...all.map(c => c.scrollWidth - c.clientWidth));
    return {key: p.dataset.scorecard, top: Math.round(r.top + window.scrollY),
            left: Math.round(r.left), width: Math.round(r.width), right: Math.round(r.right),
            tableRight: Math.round(t.getBoundingClientRect().right),
            maxCellRight: Math.round(Math.max(...cells)), maxCellSpill: spill,
            tableScroll: t.scrollWidth, tableClient: t.clientWidth};
  });
  return {cards, sw: document.scrollingElement.scrollWidth, iw: window.innerWidth,
          theme: document.documentElement.getAttribute('data-theme')};
}"""


def _open(
    p: Any, served: str, theme: str, route: str = "/scorecards"
) -> tuple[Any, Any, list[str]]:
    browser = p.chromium.launch(**chrome_kwargs())
    ctx = browser.new_context(viewport=VIEWPORT)
    ctx.add_init_script(f"try{{localStorage.setItem('sf-theme','{theme}')}}catch(e){{}}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + route, wait_until="load")
    page.wait_for_selector(".cd-grid-3 .panel[data-scorecard] .sl-chip", timeout=15000)
    page.mouse.move(0, 0)  # park the virtual mouse: it survives goto() and would hover a chip
    page.wait_for_timeout(300)
    return browser, page, errors


@pytest.mark.parametrize("theme", THEMES)
def test_the_three_cards_share_one_row_and_no_table_outgrows_its_card(
    served: str, theme: str
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served, theme)
        g = page.evaluate(_GEOMETRY)
        browser.close()
    assert g["theme"] == theme, g["theme"]
    assert not errors, errors
    cards = g["cards"]
    assert [c["key"] for c in cards] == ["nasa_stat", "gao_10", "sra_readiness"], cards
    # one row, three columns, left to right, equal widths — the artboard's grid, not a stack
    assert len({c["top"] for c in cards}) == 1, cards
    assert [c["left"] for c in cards] == sorted(c["left"] for c in cards), cards
    assert cards[0]["left"] < cards[1]["left"] < cards[2]["left"], cards
    assert len({c["width"] for c in cards}) == 1, cards
    # the verbatim table fits its card: its box and EVERY cell end inside the card's right edge
    # (measured before the rules: a 449-px table in a 374-px card in console, 585 apollo, 466
    # jarvis — and in daylight the card's OWN scrollWidth read 463 > 453 while its table fit, which
    # is why cells are measured here, not the table's scrollWidth alone)
    for c in cards:
        assert c["tableRight"] <= c["right"], c
        assert c["maxCellRight"] <= c["right"], c
        assert c["tableScroll"] <= c["tableClient"], c  # and it does not scroll inside itself
        assert c["maxCellSpill"] <= 0, c  # and no cell's content is wider than the cell's box
    # and the document does not scroll sideways at rest (ADR-0477's rule, this page included)
    assert g["sw"] == g["iw"] == VIEWPORT["width"], g


def test_a_chip_click_opens_the_other_versions_scorecards_with_its_own_chip_on(
    served: str,
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served, "console")
        assert page.locator(".cd-chip.on").inner_text() == "v2"
        assert "NASA STAT 3/4" in page.locator("h1.page-takeaway").inner_text()
        page.locator('.cd-chip[data-idx="0"]').click()
        page.wait_for_load_state("load")
        page.wait_for_selector(".cd-grid-3 .panel[data-scorecard] .sl-chip", timeout=15000)
        url = page.url
        on = page.locator(".cd-chip.on").inner_text()
        h1 = page.locator("h1.page-takeaway").inner_text()
        pill = page.locator(".cd-pill").inner_text()
        scores = page.locator(".cd-score-n").all_inner_texts()
        browser.close()
    assert not errors, errors
    assert url.endswith("/scorecards?file=Project2"), url
    assert on == "v1"
    assert "NASA STAT 4/4" in h1, h1  # Project2's own figure; Project5 reads 3/4
    assert pill.startswith("v1 · Project2.mspdi.xml · DD "), pill
    assert scores == ["4 / 4", "7 / 8", "7 / 7"], scores
