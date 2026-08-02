"""Chapter 12 (`/briefing` + `/brief`) joins the Mission Ops panel contract — ADR-0337.

The census numbers below were measured on BOTH trees: the converted one, and the pristine tree at
`1bcf01a` (restored from a scratchpad copy, re-rendered, then put back). That matters more than it
sounds — a first pass at the "before" figures used a `<div class=panel[ >]` regex that silently
misses the QUOTED form (`<div class="panel brief-doc">`), and so reported `/briefing` as a 1-panel
page when it renders 4. The panel counts here are the honest both-forms totals.

What this file pins, in order of how quietly it could rot:

* the AI-polished briefing keeps its provenance chip. `ai_polish.js` replaces the WHOLE of
  `#briefingBody`, so the chip lives or dies by `/api/ai/briefing` passing the same `prov` the page
  render passed. Nothing about the page looks wrong when it does not — the chip simply disappears
  the moment a local model is active, which is exactly the configuration no test runs by default;
* the panel count is unchanged (the conversion DECORATES existing `.panel`s — a new one would
  inherit jarvis's broad `.panel` rules, i.e. a promotion nobody designed);
* the contract vocabulary lands where it was planned, counted rather than eyeballed;
* the headings still read the same, so every existing substring assertion in
  `test_briefing_view.py` survives the `_panel_head` wrap;
* every `data-export` is a REAL workbook, fetched and checked — never a dead link.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as appmod
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

BRIEFING = "/briefing"
BRIEF = "/brief"

#: both spellings of a panel opener — bare (`<div class=panel>`) and quoted
#: (`<div class="panel brief-doc">`). Missing the second is how the first "before" census
#: under-counted `/briefing` by three.
_PANEL = re.compile(r'<div class=panel[ >]|<div class="panel[ "]')


class _StubBackend:
    """A stand-in local backend, so `/api/ai/briefing` takes its POLISHED path.

    It returns the prompt's own text: the endpoint is being exercised for the HTML it re-renders
    around the model's words, not for the words.
    """

    name = "ollama"
    is_local = True
    model = "stub"

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("stub",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        return prompt.rsplit("\n", 1)[-1]


@pytest.fixture(scope="module")
def pages() -> dict[str, str]:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    return {route: c.get(route).text for route in (BRIEFING, BRIEF)}


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    return c


# ── the census ────────────────────────────────────────────────────────────────────────────────

#: `.panel` per route, BOTH spellings, measured on the pristine tree AND the converted one.
#: `/briefing` = 2 `.panel.status-stack` header bars + the `.panel.brief-doc` + the Ask panel.
#: `/brief` = the lead panel + 6 sections + the Ask panel.
PANEL_CENSUS = {BRIEFING: 4, BRIEF: 8}

#: the contract vocabulary each route NEWLY carries: heads, tool strips, ⛶, takes, chips.
#: All five were **0** on both routes before this round (measured on the pristine tree).
CONTRACT_CENSUS = {
    #          heads, tools, ⛶, takes, chips
    BRIEFING: (1, 1, 1, 1, 1),
    BRIEF: (7, 7, 7, 1, 7),
}


def test_the_panel_count_is_unchanged_by_the_conversion(pages: dict[str, str]) -> None:
    """The conversion DECORATES panels that were already `.panel`. If a count moves, the round
    minted a new box — and every new `.panel` inherits jarvis's broad `html[data-theme=jarvis]
    .panel` rules, i.e. a promotion nobody designed."""
    for route, page in pages.items():
        assert len(_PANEL.findall(page)) == PANEL_CENSUS[route], route


def test_the_contract_vocabulary_lands_where_it_was_planned(pages: dict[str, str]) -> None:
    """Counted, not eyeballed: a head that silently stopped rendering is exactly the failure this
    file exists to catch, and a ⛶ count that drifts from the tool-strip count means a strip lost
    its button (or grew a second glyph nobody wired)."""
    for route, page in pages.items():
        got = (
            page.count("<div class=panel-head>"),
            page.count("sf-tools"),
            page.count("data-sf-big"),
            page.count("<p class=sf-take"),
            page.count("<span class=prov-chip"),
        )
        assert got == CONTRACT_CENSUS[route], (route, got)
        # every tool strip carries exactly one ⛶, and none ships ▦ DATA: these panels ARE prose
        # and tables, so there is no hidden `.sf-drawer` for the glyph to reveal.
        assert page.count("sf-tools") == page.count("data-sf-big"), route
        assert "data-sf-data" not in page, route
        assert page.count("⛶ SHRINK") == 0, route  # the label flips in JS, never server-side


def test_panelkit_is_included_exactly_once_on_both_routes(pages: dict[str, str]) -> None:
    """A page can render the ⛶ / ⤓ buttons with no script to drive them (the round-4 latent-gap
    lesson), and a page can load it twice and double-fire every click."""
    for route, page in pages.items():
        assert page.count("/static/panelkit.js") == 1, route


def test_the_headings_still_read_the_same(pages: dict[str, str]) -> None:
    """`_panel_head` preserves the heading TEXT (the uppercase treatment is CSS). Every existing
    content assertion in test_briefing_view.py is a plain substring on these strings — this pins
    that they survived the wrap."""
    for heading in (
        "1. The Bottom Line",
        "5. Risks and Opportunities",
        "7. How to Verify Every Number",
    ):
        assert heading in pages[BRIEFING], heading
    for heading in ("The finish story", "How to verify any claim in this brief"):
        assert f"<h2>{heading}</h2>" in pages[BRIEF], heading


def test_every_data_export_on_both_routes_is_a_real_workbook(
    client: TestClient, pages: dict[str, str]
) -> None:
    """The rank-3 law: ⤓ EXCEL renders ONLY where the panel carries a `data-export` to an endpoint
    that exists. Fetched, not assumed — a route that 404s is the failure mode this catches."""
    urls = {u for page in pages.values() for u in re.findall(r'data-export="([^"]+)"', page)}
    assert urls == {"/export/xlsx/briefing", "/export/xlsx/brief"}, urls
    for url in sorted(urls):
        r = client.get(url)
        assert r.status_code == 200, url
        assert r.content[:2] == b"PK", url  # a real xlsx (zip container)


# ── the two panels the round deliberately did NOT convert ─────────────────────────────────────


def test_the_ask_panel_and_the_header_bars_stay_bare(pages: dict[str, str]) -> None:
    """Scope, pinned so a later round does not quietly widen it.

    The Ask panel is global chrome `_page` adds to every route, and the two `.panel.status-stack`
    bars on `/briefing` come from `_status_stack`, which several chapter headers share (`/sra`
    among them). Giving either the contract here would be a cross-cutting change wearing a
    chapter-12 label — and would hand a ⤓ EXCEL to panels whose data no workbook carries.
    """
    for page in pages.values():
        ask = page.split("<div class=panel id=askPanel>", 1)[1].split("</div>", 1)[0]
        assert "panel-head" not in ask and "sf-tools" not in ask
    bars = pages[BRIEFING].count('<div class="panel status-stack">')
    assert bars == 2, bars
    for chunk in pages[BRIEFING].split('<div class="panel status-stack">')[1:]:
        head = chunk.split("</div>", 1)[0]
        assert "panel-head" not in head and "prov-chip" not in head


# ── the one that rots silently ────────────────────────────────────────────────────────────────


def test_the_ai_polished_briefing_still_carries_the_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ai_polish.js` does `node.innerHTML = d.html` on the WHOLE of `#briefingBody`, so whatever
    `/api/ai/briefing` returns is what the operator ends up looking at.

    If that endpoint re-renders the body without the provenance chip, nothing looks broken — the
    chip just vanishes the moment a local model is active, which is the one configuration the rest
    of the suite never exercises. The head and the ⛶ would survive either way (panelkit.js binds a
    single delegated listener on `document`, so buttons arriving via innerHTML still work); the
    CHIP is the part that only the caller can supply.
    """
    st = SessionState()
    c = TestClient(create_app(st))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    monkeypatch.setattr(appmod, "_active_backend", lambda state: _StubBackend())

    r = c.get("/api/ai/briefing")
    assert r.status_code == 200
    payload = r.json()
    assert payload["polished"] is True, "the stub backend did not take the polished path"
    html = payload["html"]
    assert "<div class=panel-head>" in html, "the polished swap dropped the panel head"
    assert "<span class=prov-chip" in html, "the polished swap dropped the provenance chip"
    assert "<p class=sf-take" in html, "the polished swap dropped the takeaway"
    assert 'data-export="/export/xlsx/briefing"' in html
    assert "data-sf-big" in html


# ── the DoD's takeaway rule ───────────────────────────────────────────────────────────────────


def test_the_brief_takeaway_quotes_figures_the_page_renders_below_it(pages: dict[str, str]) -> None:
    """DESIGN-SYSTEM §5 + `_utility_takeaway`'s own contract: a headline states a FINDING, and
    every figure in it must already be rendered further down the SAME page, so the number the
    reader meets first is one they can verify by reading on.

    `/brief` had no takeaway h1 at all before this round (measured: `page-takeaway` count 0).
    """
    page = pages[BRIEF]
    assert 'class="page-takeaway"' in page and 'class="page-lede"' in page
    h1 = re.search(r'<h1 class="page-takeaway"[^>]*>(.*?)</h1>', page, re.S)
    assert h1 is not None
    sections, cited = (int(n) for n in re.findall(r"\d+", h1.group(1))[::-1][:2])
    # the same two figures are re-stated by the lead panel's take, which sits below the h1
    take = re.search(r"<p class=sf-take[^>]*>(.*?)</p>", page, re.S)
    assert take is not None
    assert f"{sections} sections" in take.group(1)
    assert f"{cited} cited statement" in take.group(1)
    assert page.index("page-takeaway") < page.index("sf-take")
