"""Act III's panel-contract census — ADR-0337 (chapter 12), ADR-0338 (`/risks`), ADR-0339 (`/sra`).

One module for the whole act, because the census discipline is the same for every route joining
the contract and the fixtures are worth sharing. It grew a row per conversion PR; with `/sra` in,
**every Act III route is inside it** and the census is complete.

The numbers were measured on BOTH trees for every route: the converted one, and the pristine tree
immediately before it (restored from a scratchpad copy, re-rendered, then put back — never
`git checkout`). That matters more than it sounds — a first pass at the chapter-12 "before"
figures used a `<div class=panel[ >]` regex that silently misses the QUOTED form
(`<div class="panel brief-doc">`), and so reported `/briefing` as a 1-panel page when it renders 4.
Every panel count here is the honest both-spellings total.

What this file pins, in order of how quietly it could rot:

* the AI-polished briefing keeps its provenance chip. `ai_polish.js` replaces the WHOLE of
  `#briefingBody`, so the chip lives or dies by `/api/ai/briefing` passing the same `prov` the page
  render passed. Nothing about the page looks wrong when it does not — the chip simply disappears
  the moment a local model is active, which is exactly the configuration no test runs by default;
* the panel count is unchanged (the conversion DECORATES existing `.panel`s — a new one would
  inherit jarvis's broad `.panel` rules, i.e. a promotion nobody designed);
* the contract vocabulary lands where it was planned, counted rather than eyeballed;
* the headings still read the same, so every existing substring assertion in
  `test_briefing_view.py` and `test_risks.py` survives the `_panel_head` wrap;
* every `data-export` is a REAL workbook, fetched and checked — never a dead link;
* (ADR-0339) on `/sra`, that last rule has TEETH rather than being automatic: two of its twelve
  converted panels deliberately carry NO ⤓ EXCEL, because their content does not ride
  `/export/xlsx/sra`. Rank 3 is "never a dead OR LYING link", and a lying one renders fine;
* (ADR-0339) `/sra`'s chip is the SINGLE-file chip of the SRA-selected version. Two versions are
  loaded in these fixtures, so a series/pair chip would render `v1→v2` here and the page would be
  claiming figures it never computed — that is what the chip test discriminates against.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as appmod
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

BRIEFING = "/briefing"
BRIEF = "/brief"
RISKS = "/risks"  # chapter 11's sub-page (ADR-0338), same contract, same census discipline
SRA = "/sra"  # chapter 11 proper (ADR-0339) — the last Act III route to join

ROUTES = (BRIEFING, BRIEF, RISKS, SRA)

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
    return {route: c.get(route).text for route in ROUTES}


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
#: `/sra` = 2 `.panel.status-stack` header bars + 12 converted panels + the Ask panel. The
#: long-carried estimate said 13 panels; rendering the pristine page said **15**.
PANEL_CENSUS = {BRIEFING: 4, BRIEF: 8, RISKS: 8, SRA: 15}

#: the contract vocabulary each route NEWLY carries: heads, tool strips, ⛶, takes, chips.
#: All five were **0** on every route before its own round (measured on the pristine tree).
CONTRACT_CENSUS = {
    #          heads, tools, ⛶, takes, chips
    BRIEFING: (1, 1, 1, 1, 1),
    BRIEF: (7, 7, 7, 1, 7),
    RISKS: (7, 7, 7, 7, 7),
    SRA: (12, 12, 12, 12, 12),
}

#: ⤓ EXCEL per route. Everywhere else it equals the tool-strip count; on `/sra` it is deliberately
#: SHORT BY TWO — the "which risk model" explainer is guidance prose with no data in any workbook,
#: and the JCL panel's sheets ride `/export/xlsx/sra` only once the file is cost-loaded (these
#: fixtures are not). Both would otherwise ship a ⤓ that opens a workbook without their data.
EXCEL_CENSUS = {BRIEFING: 1, BRIEF: 7, RISKS: 7, SRA: 10}


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


def test_panelkit_is_included_exactly_once_on_every_converted_route(pages: dict[str, str]) -> None:
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
    # test_risks.py asserts these two as `<h2>Risks <span` / `<h2>Opportunities <span` — the
    # count badge is INSIDE the heading, so the wrap has to preserve the whole opening string.
    for heading in ("<h2>Risks <span", "<h2>Opportunities <span", "<h2>Risk matrix"):
        assert heading in pages[RISKS], heading
    # `/sra` has the most existing substring assertions of the four (test_sra*.py, test_jcl*.py,
    # test_correlation*.py all read these) — all 12 converted headings, verbatim.
    for heading in (
        "<h2>Schedule file for the SRA</h2>",
        "<h2>Which risk model should I use? (pros, cons &amp; examples)</h2>",
        "<h2>Schedule Risk &amp; Opportunity Analysis</h2>",
        "<h2>Correlation matrix (advanced)</h2>",
        "<h2>Joint Cost-&amp;-Schedule Confidence (JCL / FICSM)</h2>",
        "<h2>Legacy SRA &mdash; Monte-Carlo (multiplicative risk drivers)</h2>",
        "<h2>What the results mean</h2>",
        "<h2>Risk inputs</h2>",
        "<h2>Risk drivers (tornado)</h2>",
        "<h2>Finish-date confidence (S-curve)</h2>",
        "<h2>Finish-date distribution</h2>",
        "<h2>Duration sensitivity (tornado)</h2>",
    ):
        assert heading in pages[SRA], heading


def test_every_data_export_on_every_converted_route_is_a_real_workbook(
    client: TestClient, pages: dict[str, str]
) -> None:
    """The rank-3 law: ⤓ EXCEL renders ONLY where the panel carries a `data-export` to an endpoint
    that exists. Fetched, not assumed — a route that 404s is the failure mode this catches."""
    urls = {u for page in pages.values() for u in re.findall(r'data-export="([^"]+)"', page)}
    assert urls == {
        "/export/xlsx/briefing",
        "/export/xlsx/brief",
        "/export/xlsx/risks",
        "/export/xlsx/sra",
    }, urls
    for url in sorted(urls):
        r = client.get(url)
        assert r.status_code == 200, url
        assert r.content[:2] == b"PK", url  # a real xlsx (zip container)


def test_the_excel_glyph_renders_only_where_the_data_really_rides_that_workbook(
    pages: dict[str, str],
) -> None:
    """Rank 3 is "never a dead OR LYING link", and this is the round that makes it bite.

    On `/briefing`, `/brief` and `/risks` every converted panel's data is in the page's workbook,
    so ⤓-count == tool-strip-count and the rule costs nothing. `/sra` is the first route where it
    does not: the "which risk model should I use?" panel is pure guidance (no figure any workbook
    carries) and the JCL panel's sheets only exist once the file is cost-loaded. Both still get
    the head, the ⛶ and the chip — they lose only the glyph that would lie.

    So this asserts the SHORTFALL, not just the presence: a later round that hands every strip a ⤓
    "for consistency" is exactly the regression this catches.
    """
    for route, page in pages.items():
        assert page.count("data-sf-excel") == EXCEL_CENSUS[route], route
        # …and it never renders on a panel with nowhere to send the operator. The count alone is
        # only the NEGATIVE half of rank 3 — a ⤓ sitting on a panel that carries no `data-export`
        # is an inert button, and panelkit.js reads the URL off the PANEL. So pair them: every
        # panel bearing a ⤓ must also bear the export the glyph will follow.
        assert page.count("data-sf-excel") <= page.count("sf-tools"), route
        # split on the PANEL opener (`_PANEL` deliberately does not match `panel-head`, which a
        # plain `"<div class=panel"` split does — that cut each chunk after the attributes)
        for body in _PANEL.split(page)[1:]:
            if "data-sf-excel" in body:
                assert "data-export=" in body, (route, body[:200])
    # (the shortfall is 12 strips - 2 = 10; asserted against the PAGE above, not against
    # the constants — comparing two module constants here would be a tautology)
    sra = pages[SRA]
    # Anchor on the H2, not the words: "Joint Cost-&-Schedule Confidence" also appears in the
    # explainer panel's own JCL <details> prose, and splitting on that matched the wrong panel.
    for bare, marker in (
        ("<h2>Which risk model should I use? (pros, cons &amp; examples)</h2>", "explainer panel"),
        (
            "<h2>Joint Cost-&amp;-Schedule Confidence (JCL / FICSM)</h2>",
            "JCL panel on a duration-only file",
        ),
    ):
        # from the heading to the head strip's closing </div>: the ⤓ must not be in it
        head = sra.split(bare, 1)[1].split("</div>", 1)[0]
        assert "data-sf-excel" not in head, marker
        assert "data-sf-big" in head, marker  # but it DID keep the rest of the contract


def test_the_sra_chip_names_the_selected_file_and_is_not_a_pair_chip(pages: dict[str, str]) -> None:
    """`/sra`'s provenance decision, and the mirror image of ADR-0338's.

    Every model on this page — SSI, OAT, JCL and the legacy Monte-Carlo — resolves its schedule
    through `_sra_selected`; the top panel exists purely to say which file that is. So the chip is
    the SINGLE-file `_prov_chip` of that version. `/risks` went the other way for a real reason
    (its change findings genuinely come from a version PAIR).

    TWO versions are loaded in these fixtures, so this discriminates: `_series_prov_chip` would
    render `v1→v2 · SOURCE: Project2… → Project5…` here, naming a version no figure on the page was
    computed from.
    """
    page = pages[SRA]
    chips = re.findall(r"<span class=prov-chip[^>]*>(.*?)</span>", page, re.S)
    assert len(chips) == CONTRACT_CENSUS[SRA][4]
    assert len(set(chips)) == 1, f"the page runs one file; the chips disagree: {set(chips)}"
    chip = chips[0]
    assert chip.startswith("SOURCE: "), chip
    assert "→" not in chip, f"a pair/series chip on a single-file page: {chip}"
    # and it names the file the page says every model runs against
    active = re.search(r"every SRA model on this page runs against ([^<.]+)\.", page)
    assert active is not None
    assert active.group(1).strip().split(".")[0] in chip, (active.group(1), chip)


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
    # `/sra` carries the SAME two `_status_stack` bars (it is one of the headers that share it), so
    # the scope note is asserted on BOTH routes rather than only the one that first raised it.
    for route in (BRIEFING, SRA):
        bars = pages[route].count('<div class="panel status-stack">')
        assert bars == 2, (route, bars)
        for chunk in pages[route].split('<div class="panel status-stack">')[1:]:
            head = chunk.split("</div>", 1)[0]
            assert "panel-head" not in head and "prov-chip" not in head, route
    # the three bare panels + the twelve converted ones account for every `.panel` on /sra
    # (15 = 12 + 3) — a relation between constants, so it is a comment, not an assert


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

#: routes whose takeaway carries the DoD's *context line* as well as the headline. `/briefing` is
#: the one Act III route still rendering a bare h1 — measured, not assumed, and left alone here
#: because it is ADR-0337's page and this round is `/sra`'s. Named so the gap is recorded rather
#: than hidden by a loop that quietly skips it.
LEDE_ROUTES = (BRIEF, RISKS, SRA)


def test_every_act3_route_carries_the_dod_takeaway(pages: dict[str, str]) -> None:
    """The W4 lesson from ADR-0338, generalized — the reason that round shipped a vacuous gate was
    a per-route rule with a HARD-CODED route key, so dropping `/risks`'s takeaway h1 failed nothing.

    A loop over `pages` is the fix: every route added to this module from here on is covered the
    moment it joins the census, with no second edit to remember.
    """
    for route, page in pages.items():
        assert 'class="page-takeaway"' in page, route
        assert page.count('<h1 class="page-takeaway"') == 1, route
    for route in LEDE_ROUTES:
        assert 'class="page-lede"' in pages[route], route
        assert pages[route].index("page-takeaway") < pages[route].index("page-lede"), route


def test_the_sra_takeaway_quotes_figures_the_page_renders_below_it(pages: dict[str, str]) -> None:
    """`_utility_takeaway`'s hard half, on `/sra`: every figure in the headline must be rendered
    AGAIN further down the same page, so the number the reader meets first is verifiable by
    reading on.

    `/sra`'s headline states the critical and near-critical counts; both are re-rendered by the KPI
    strip immediately below it. The literal `5` in "within 5 days of float" is a THRESHOLD, not a
    measured figure — it is matched as part of the phrase rather than pulled out as a number, which
    is precisely the distinction a naive "every digit in the h1" check would get wrong.

    Each figure is bound to ITS OWN stat card. The first version of this test searched the KPI
    strip for "the label, then the number" with a dot-star under `re.DOTALL`, which spans the whole
    six-card strip — so ANY card's digit satisfied ANY label and the assertion could not fail. It
    was caught by running the revert (W7): swapping the headline to quote `incomplete` and `neg`
    left the test green. Parse the cards, then compare exactly.
    """
    page = pages[SRA]
    h1 = re.search(r'<h1 class="page-takeaway"[^>]*>(.*?)</h1>', page, re.S)
    assert h1 is not None
    text = h1.group(1)
    m = re.match(r"(\d+) activities drive the finish and (\d+) more are near-critical", text)
    assert m is not None, text
    crit, near = m.group(1), m.group(2)
    # EVERY figure in the h1, not just the leading pair: the headline appends ", with N risks
    # registered" whenever the register is non-empty, and a test that binds only the first two
    # would let a fabricated third through. Anything after the threshold phrase is checked here.
    tail = (
        text.split("(within 5 days of float)", 1)[1] if "(within 5 days of float)" in text else ""
    )
    extra = re.findall(r"\d+", tail)
    assert len(extra) <= 1, f"unbound figures in the takeaway: {extra} ({text})"
    # the KPI strip below re-states both — parsed as (label -> value), never as a loose span
    kpi = page.split('<div class="ws-kpi">', 1)[1].split('<div class="ws-bars">', 1)[0]
    cards = {
        label: value
        for value, label in re.findall(
            r"<div class=stat-card><div class=stat-value>(.*?)</div>"
            r"<div class=stat-label>(.*?)</div></div>",
            kpi,
        )
    }
    assert cards, kpi[:400]
    assert cards.get("Critical activities") == crit, (crit, cards)
    assert cards.get("Near-critical (\u22645d)") == near, (near, cards)
    if extra:
        assert cards.get("Registered risks") == extra[0], (extra, cards)
    assert page.index("page-takeaway") < page.index("ws-kpi")


def test_no_sra_take_quotes_a_simulation_figure_before_any_run(pages: dict[str, str]) -> None:
    """Law 2 on a page whose charts are EMPTY at render time.

    Four `/sra` panels are bare chart hosts until the operator runs the Monte-Carlo (`sra.js`
    fetches `/api/sra`; running 1000x CPM during the page render would hang the page). A take on
    one of those panels therefore cannot quote a P50, a mean finish, or a sensitivity — the server
    has not computed one. It has to say what the panel will draw and from what.

    This pins that the four deferred panels' takes stay figure-free, which is the honest shape, and
    that the panels really are empty at render (so the rule is not vacuous on this fixture).
    """
    page = pages[SRA]
    for host in ("sraCdf", "sraHist", "sraSens", "sraRisk"):
        assert f"<div id={host} class=chart-host></div>" in page, f"{host} is not empty at render"
    for heading in (
        "Finish-date confidence (S-curve)",
        "Finish-date distribution",
        "Duration sensitivity (tornado)",
        "What the results mean",
    ):
        chunk = page.split(heading, 1)[1]
        take = re.search(r"<p class=sf-take[^>]*>(.*?)</p>", chunk, re.S)
        assert take is not None, heading
        # percentile labels, day/percent quantities, ISO dates and bare 4-digit years: the shapes
        # a fabricated simulation result would actually take. (The docstring names "a mean finish"
        # — a DATE — so the pattern has to cover dates, not only P-labels and units.)
        forbidden = r"\bP\d{1,2}\b|\d+(\.\d+)?\s*(days|%)|\d{4}-\d{2}-\d{2}|\b(19|20)\d{2}\b"
        assert not re.search(forbidden, take.group(1)), (heading, take.group(1))


def test_the_risks_takeaway_quotes_figures_the_page_renders_below_it(
    pages: dict[str, str],
) -> None:
    """Same DoD rule as `/brief`, and it needs its OWN gate.

    Dropping `/risks`'s takeaway h1 failed nothing until this existed — the `/brief` test only
    reads `/brief`, so a per-route rule needs a per-route assertion. Found by running the revert
    (W4), not by reading the tests.

    It also pins the harder half of `_utility_takeaway`'s contract: every figure in the headline
    must be rendered AGAIN further down the same page, so the reader can verify it by reading on.
    The total (`len(findings)`) is a SUM of three separately-rendered counts, so the lead panel's
    take was changed to state the total explicitly rather than leave the headline quoting a number
    that appears nowhere else.
    """
    page = pages[RISKS]
    assert 'class="page-takeaway"' in page and 'class="page-lede"' in page
    h1 = re.search(r'<h1 class="page-takeaway"[^>]*>(.*?)</h1>', page, re.S)
    assert h1 is not None
    total, high = (int(n) for n in re.findall(r"\d+", h1.group(1)))
    take = re.search(r"<p class=sf-take[^>]*>(.*?)</p>", page, re.S)
    assert take is not None
    assert f"{total} finding" in take.group(1), (h1.group(1), take.group(1))
    assert f"{high} at HIGH severity" in take.group(1), (h1.group(1), take.group(1))
    assert page.index("page-takeaway") < page.index("sf-take")


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


# ── the JCL panel's OTHER branch ──────────────────────────────────────────────────────────────


def _cost_loaded_client() -> TestClient:
    """A session holding a COST-LOADED schedule, so `/sra`'s JCL panel takes its `loaded` branch.

    The golden fixtures this module otherwise uses are duration-only, so every other assertion
    about the JCL panel here exercises the gate in its OFF state only. Built in memory the same
    way `test_jcl_web.py` does — the panel gates on `cost_loaded_total(...) > 0`, nothing more.
    """
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    day = 480
    tasks = tuple(
        Task(
            unique_id=u,
            name=f"T{u}",
            duration_minutes=int(d * day),
            budgeted_cost={2: 1000.0, 3: 50.0}.get(u, 0.0),
        )
        for u, d in ((1, 1), (2, 10), (3, 2), (4, 1))
    )
    rels = tuple(
        Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)
        for p, s in ((1, 2), (1, 3), (2, 4), (3, 4))
    )
    st = SessionState()
    st.schedules["costed"] = Schedule(
        name="J", project_start=dt.datetime(2025, 1, 6, 8, 0), tasks=tasks, relationships=rels
    )
    return TestClient(create_app(st))


def test_the_jcl_panel_gains_its_excel_glyph_only_when_the_file_is_cost_loaded() -> None:
    """The ⤓ gate on `_jcl_panel` has TWO branches and the module's goldens only render one.

    On a duration-only file the JCL sheets are not in `/export/xlsx/sra` at all, so the panel ships
    head + ⛶ + chip and NO ⤓ (asserted above, on the goldens). This is the other half: once the
    file is cost-loaded the sheets really do ride that workbook, so the ⤓ appears and the panel
    carries the export. Without this, a regression that stopped appending the JCL sheets to the
    export while the panel kept its ⤓ would be invisible — a lying link, which is the exact failure
    rank 3 exists to prevent.
    """
    c = _cost_loaded_client()
    page = c.get("/sra").text
    assert "Needs a cost-loaded schedule" not in page, "the fixture did not open the JCL gate"
    head = page.split("<h2>Joint Cost-&amp;-Schedule Confidence (JCL / FICSM)</h2>", 1)[1]
    strip = head.split("</div>", 1)[0]
    assert "data-sf-excel" in strip, "the cost-loaded JCL panel lost its ⤓"
    assert "data-sf-big" in strip
    # …and the workbook it points at is real, and really carries the JCL sheets
    assert 'data-export="/export/xlsx/sra"' in page
    r = c.get("/export/xlsx/sra")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        sheets = z.read("xl/workbook.xml").decode("utf-8", "replace")
    assert "JCL" in sheets, f"the ⤓ points at a workbook with no JCL sheet: {sheets[:400]}"


def test_the_sra_contract_degrades_honestly_when_no_version_solves() -> None:
    """The state where `/export/xlsx/sra` answers **400**, and therefore where a ⤓ would lie.

    `_sra_selected` returns None when no loaded version's CPM solves. The export endpoint refuses
    with 400 in exactly that case, so a panel still offering ⤓ EXCEL would be handing the operator
    a button that errors — a dead link, which is what rank 3 forbids. The provenance chip has
    nothing to attribute either. Both degrade together with the export attribute; the head and the
    ⛶ stay, because enlarging a panel needs no data.

    Built from a CYCLIC network — the cheapest genuinely unsolvable schedule.
    """
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    tasks = tuple(Task(unique_id=u, name=f"T{u}", duration_minutes=480) for u in (1, 2, 3))
    rels = tuple(
        Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)
        for p, s in ((1, 2), (2, 3), (3, 1))  # the cycle
    )
    st = SessionState()
    st.schedules["cyc"] = Schedule(
        name="C", project_start=dt.datetime(2025, 1, 6, 8, 0), tasks=tasks, relationships=rels
    )
    c = TestClient(create_app(st))

    assert c.get("/export/xlsx/sra").status_code == 400, "the fixture is solvable after all"
    page = c.get("/sra").text
    assert page.count("data-sf-excel") == 0, "a ⤓ pointing at an endpoint that answers 400"
    assert 'data-export="/export/xlsx/sra"' not in page
    assert page.count("<span class=prov-chip") == 0, "a chip attributing figures to no version"
    # the rest of the contract survives — a panel with no data can still be enlarged
    assert page.count("<div class=panel-head>") == 12
    assert page.count("data-sf-big") == 12
    # and the JCL take states the REAL reason, not "no budgeted cost" (which would be a claim about
    # cost loading this page cannot make when it never resolved a file at all)
    assert "No analyzable version selected" in page
    assert "No budgeted cost on this file" not in page


def test_the_sra_file_take_counts_the_selector_population_not_every_loaded_file() -> None:
    """The take beside the file picker must count the SAME versions the picker offers.

    `len(st.schedules)` is every loaded file — it spans other Projects and operator-EXCLUDED
    versions (ADR-0258/0259), neither of which `/sra` can run against. `st.ordered_versions()` is
    the analysis population, which is what the dropdown is built from. On the goldens the two
    numbers are identical (2 and 2), so nothing distinguishes them until a version is excluded —
    which is exactly why this test excludes one.
    """
    st = SessionState()
    c = TestClient(create_app(st))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert len(st.schedules) == 2
    st.excluded_keys.add(next(iter(st.schedules)))  # the operator drops one version
    assert len(st.ordered_versions()) == 1, "the exclusion did not narrow the population"

    page = c.get("/sra").text
    take = re.search(r"<p class=sf-take[^>]*>(.*?)</p>", page, re.S)
    assert take is not None
    assert "1 version in this project" in take.group(1), take.group(1)
    assert "2 versions" not in take.group(1), take.group(1)
