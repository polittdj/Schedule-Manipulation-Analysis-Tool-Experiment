"""/scorecards wears the Claude Design "Control Assessment Scorecards" layout (ADR-0484),
functionality unchanged — the tenth page on the design, the second Control screen.

The artboard (the v2 canvas's ``section[data-screen-label="Control Assessment Scorecards"]``,
EXECUTED over loopback HTTP in all four themes — ADR-0464's recipe with ``setScreen('sk')``, zero
page errors): kicker ``Control · Assessment`` · headline ("Scored the way your reviewer will score
it.") · lede · an accent-bordered take repeating three ratios · a ``SOURCE:`` chip beside one
``⤓ EXCEL`` · THREE framework cards in ONE auto-fit grid (``minmax(320px, 1fr)``), each headed by
its name, a sub-line, a big ``passed / scored``, ``N% OF SCORED``, a bar and an info note, then one
status-pill row per line with a ``⊞ N`` drill · a reserve card with a committed-finish input, a
note and four percentile tiles · a "The briefing →" footer.

What the layout changes: the masthead already led (as on /standards, ADR-0475), so the moves are
the family's cursor strip as NAVIGATION for a per-file drill (ADR-0470's rule, the helper
``components._version_chips`` gaining a ``query=`` form because this page picks its version by
``?file=``), the three scorecard panels VERBATIM inside the artboard's grid, and the artboard's
card-head score fed by the ENGINE's own ``Scorecard.score`` — never a mock figure.

Named omissions (ADR-0484), each with its reason:
  * the mock's **score colour thresholds** (100 % pass → ok, ≥ 70 % → caution, else fail) — a
    threshold the engine does not assert; the bar wears the accent role, and no verdict class.
  * INFO drawn in the **caution** colour — an informational line is not a caution (§1: ``--warn``
    means caution); the page's own ``sl-info`` chip keeps its neutral accent outline.
  * the **reserve tiles**, the mock's "no new simulation runs" note and its calendar-day figure —
    this page's reserve card RUNS the Monte-Carlo on demand (the note would be false), the API
    returns working days only (a calendar-day figure would be fabricated), and the reserve table
    is the captioned DOM table ``scorecards.js`` builds (ADR-0340's ledger).
  * the mock's **take block** — the page's ``h1`` already carries the same three ratios (§2: a
    takeaway is a sentence with a number in it); a second copy is redundancy, not layout.
  * the kicker, the ``SOURCE:`` row's ⤓ and the **Continue footer** — the chrome's spine, the page's
    own Export (Excel) / (Word) buttons and per-panel ⤓ (the SAME three-scorecard workbook), and
    the chrome's Continue segue already serve each (ADR-0471 / ADR-0475's precedent).

Red-first (2026-09-11), on the pristine tree: no strip, no chips, no pill, no grid, no score head.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.scorecards import Scorecard, ScorecardCheck
from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.scorecards import _scorecard_panel
from web.test_ui_control_effect_census import _FAMILY

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
CHIP = re.compile(r'<a class="cd-chip( on)?" data-idx="(\d+)" href="([^"]+)"[^>]*>v(\d+)</a>')
PILL = re.compile(r'<span class="muted cd-pill" data-no-i18n>([^<]+)</span>')
SCORE = re.compile(
    r"<div class=cd-score data-no-i18n><span class=cd-score-n>([^<]+)</span>"
    r"<span class=cd-score-pct>([^<]+)</span>"
)
TAKE = re.compile(r"<p class=sf-take data-no-i18n><b>(\d+)/(\d+) scored checks pass</b>")

#: the design's order on the served page: masthead · strip · the picker · the grid of three
#: cards in the artboard's order · the reserve card · the page's script
ORDER = (
    "<div class=chapter-kicker",
    '<h1 class="page-takeaway"',
    '<p class="page-lede">',
    "id=scorecardsCursor",
    "<form method=get action=/scorecards class=viz-controls>",
    '<div class="cd-grid cd-grid-3">',
    'data-scorecard="nasa_stat"',
    'data-scorecard="gao_10"',
    'data-scorecard="sra_readiness"',
    "id=reserveForm",
    "/static/scorecards.js",
)

#: the page's own picker, byte for byte — the artboard has no version picker, so the page's is
#: kept exactly as it was, in the family's options position between the strip and the cards
PICKER = (
    "<form method=get action=/scorecards class=viz-controls><label>Assess version "
    "<select name=file data-no-i18n data-sf-autosubmit>"
    '<option value="Project2">Project2.mspdi.xml · 2026-05-24</option>'
    '<option value="Project5" selected>Project5.mspdi.xml · 2026-08-27</option>'
    '</select></label><a class=btn href="/export/xlsx/scorecards?file=Project5">Export (Excel)</a>'
    '<a class=btn href="/export/docx/scorecards?file=Project5">Export (Word)</a></form>'
)


def _client(*names: str) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name in names:
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert resp.status_code == 200
    return client


@pytest.fixture(scope="module")
def pair() -> TestClient:
    return _client("Project2", "Project5")


def _panels(page: str) -> int:
    """Elements carrying the `panel` CLASS — the promotion census the r12 sweep pins (5 here)."""

    class Count(HTMLParser):
        n = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if "panel" in (dict(attrs).get("class") or "").split():
                self.n += 1

    parser = Count()
    parser.feed(page)
    return parser.n


def _card(page: str, key: str) -> str:
    start = page.index(f'data-scorecard="{key}"')
    return page[start : page.index("</table>", start)]


def _grid(page: str) -> tuple[str, int]:
    """The grid wrapper's exact extent, found by tracking ``div`` depth from its start tag.

    The first version sliced up to the reserve card's own ``<div class=panel>`` shell — so a
    reserve card pulled INSIDE the grid ended the slice before it could be seen, and the mutation
    came back green. The battery found that instrument weak by name; this one reads nesting."""
    start = page.index('<div class="cd-grid cd-grid-3">')
    depth = 0
    for m in re.finditer(r"<div\b|</div>", page[start:]):
        depth += 1 if m.group().startswith("<div") else -1
        if depth == 0:
            return page[start : start + m.end()], start + m.end()
    raise AssertionError("the grid wrapper never closes")


def test_the_cursor_strip_serves_one_link_chip_per_version_with_the_open_one_on(
    pair: TestClient,
) -> None:
    page = pair.get("/scorecards").text
    assert page.count("id=scorecardsCursor") == 1
    chips = CHIP.findall(page)
    assert [(idx, href, lab) for _on, idx, href, lab in chips] == [
        ("0", "/scorecards?file=Project2", "1"),
        ("1", "/scorecards?file=Project5", "2"),
    ], chips
    assert [on for on, *_rest in chips] == ["", " on"]  # oldest first; the open version on
    pill = PILL.search(page)
    assert pill and pill.group(1).startswith("v2 &middot; Project5.mspdi.xml &middot; DD "), pill
    assert "One assessment per loaded version" in page


def test_a_chip_opens_that_versions_scorecards_with_its_own_chip_on_and_its_own_figures(
    pair: TestClient,
) -> None:
    """The chip is NAVIGATION: the other version's page scores that file, not the open one's."""
    page = pair.get("/scorecards?file=Project2").text
    chips = CHIP.findall(page)
    assert [on for on, *_rest in chips] == [" on", ""]
    pill = PILL.search(page)
    assert pill and pill.group(1).startswith("v1 &middot; Project2.mspdi.xml")
    assert "NASA STAT 4/4 structural checks pass" in page  # Project2's own; Project5 reads 3/4
    assert [m.groups() for m in SCORE.finditer(page)] == [
        ("4 / 4", "100.0% of scored"),
        ("7 / 8", "87.5% of scored"),
        ("7 / 7", "100.0% of scored"),
    ]


def test_one_loaded_version_serves_no_strip_but_still_the_grid_and_the_scores() -> None:
    page = _client("Project5").get("/scorecards").text
    assert "id=scorecardsCursor" not in page and "cd-chip" not in page
    assert page.count('<div class="cd-grid cd-grid-3">') == 1
    assert len(SCORE.findall(page)) == 3


def test_chips_carry_no_id_and_no_family_word(pair: TestClient) -> None:
    """The M1 control census recognises a stepper by id + className; a link chip is neither."""
    page = pair.get("/scorecards").text
    tags = re.findall(r"<a class=\"cd-chip[^>]*>", page)
    assert len(tags) == 2
    for tag in tags:
        assert " id=" not in tag and not re.search(_FAMILY, tag), tag
    strip = re.search(r'<div class="viz-controls cd-cursor" id=(\w+)>(.*?)</div>', page, re.S)
    assert strip and not re.search(_FAMILY, strip.group(1))
    values = re.findall(r'(?:class|id)="?([^" >]+)"?', strip.group(2))
    assert values and not any(re.search(_FAMILY, v) for v in values), values


def test_the_masthead_leads_then_the_strip_the_picker_the_grid_and_the_reserve(
    pair: TestClient,
) -> None:
    page = pair.get("/scorecards").text
    missing = [mark for mark in ORDER if mark not in page]
    assert not missing, missing
    positions = [page.index(mark) for mark in ORDER]
    assert positions == sorted(positions), list(zip(ORDER, positions, strict=True))


def test_the_grid_holds_exactly_the_three_scorecards_and_the_reserve_card_stays_outside(
    pair: TestClient,
) -> None:
    page = pair.get("/scorecards").text
    assert page.count('<div class="cd-grid cd-grid-3">') == 1
    grid, end = _grid(page)
    assert re.findall(r'data-scorecard="([^"]+)"', grid) == ["nasa_stat", "gao_10", "sra_readiness"]
    assert grid.count("<div class=panel ") == 3  # the cards' shells; panel-head is another tag
    assert "<div class=panel>" not in grid  # the reserve card's shell is exactly this
    assert "id=reserveForm" not in grid and "Reserve / buffer sizing" not in grid
    assert page.index("id=reserveForm") > end  # the reserve card follows the grid, outside it


def test_each_card_head_carries_the_engines_score_as_a_figure_and_a_bar(pair: TestClient) -> None:
    """``passed / scored`` and ``score`` are the engine's own fields; the bar's width IS the
    score (one decimal, the page's own percentage idiom — never the mock's integer)."""
    page = pair.get("/scorecards").text
    assert [m.groups() for m in SCORE.finditer(page)] == [
        ("3 / 4", "75.0% of scored"),
        ("5 / 8", "62.5% of scored"),
        ("6 / 7", "85.7% of scored"),
    ]
    bars = re.findall(
        r'<span class=cd-score-bar role=img aria-label="([^"]+)"><i style="width:([0-9.]+)%">',
        page,
    )
    assert bars == [
        ("75.0% of scored checks pass", "75.0"),
        ("62.5% of scored checks pass", "62.5"),
        ("85.7% of scored checks pass", "85.7"),
    ], bars


def test_each_score_head_agrees_with_the_take_line_beneath_it(pair: TestClient) -> None:
    """Two renderings of one engine figure on one card must never disagree."""
    page = pair.get("/scorecards").text
    for key in ("nasa_stat", "gao_10", "sra_readiness"):
        card = _card(page, key)
        score = SCORE.search(card)
        take = TAKE.search(card)
        assert score and take, key
        passed, scored = take.groups()
        assert score.group(1) == f"{passed} / {scored}", key
        assert score.group(2) == f"{100 * int(passed) / int(scored):.1f}% of scored", key
        # the head precedes the framework line, as the artboard puts the score in the card head
        assert card.index("cd-score") < card.index("<p class=muted>") < card.index("sf-take"), key


def test_a_card_with_nothing_scored_prints_a_dash_never_a_fabricated_zero() -> None:
    info = ScorecardCheck("k", "Only informational", "INFO", "0 of 0", "model scan")
    sc = Scorecard("x", "Synthetic", "a framework", (info,), passed=0, failed=0, info=1, na=0)
    assert sc.score is None  # the engine's own answer for an unscored card
    html = _scorecard_panel(sc, "f")
    assert "<span class=cd-score-n>—</span><span class=cd-score-pct>no scored checks</span>" in html
    assert 'aria-label="no scored checks"><i></i>' in html  # an EMPTY bar, no width at all
    assert "0%" not in html and "0.0%" not in html


def test_the_score_head_wears_no_verdict_colour(pair: TestClient) -> None:
    """The mock colours the score by threshold (100 % ok, ≥ 70 % caution, else fail). The engine
    asserts no such bar, so the head carries no ok / warn / bad class — the bar is the accent."""
    page = pair.get("/scorecards").text
    heads = re.findall(r"<div class=cd-score data-no-i18n>.*?</div>", page)
    assert len(heads) == 3
    for head in heads:
        # the guard reads CLASS tokens and colour TOKENS, never prose: the bar's own aria-label
        # says "checks pass", which a word search would flag (my first probe did)
        # a QUOTED value may hold several tokens ("cd-score-bar ok"): read the whole value, then
        # split — the first extractor stopped at the space and the battery walked through it
        classes = [
            c
            for m in re.finditer(r'class=(?:"([^"]*)"|([^\s>]+))', head)
            for c in (m.group(1) or m.group(2)).split()
        ]
        assert classes == ["cd-score", "cd-score-n", "cd-score-pct", "cd-score-bar"], classes
        assert not re.search(r"var\(--(ok|warn|bad)\)", head), head
        assert not re.search(r"\b(ok|warn|bad)\b", " ".join(classes))


def test_every_panel_figure_form_byte_and_export_survives_the_layout(pair: TestClient) -> None:
    page = pair.get("/scorecards").text
    assert _panels(page) == 5  # STAT · GAO · SRA · reserve · the chrome's Ask panel
    assert PICKER in page  # the picker, byte for byte, in the options position
    assert page.count('data-export="/export/xlsx/scorecards?file=Project5"') == 3
    assert page.count("data-sf-big") == 4 and page.count("data-sf-excel") == 3
    assert page.count('class="sl-chip') == 58 and page.count("<table class=scorecard-table>") == 3
    assert page.count("sf-drill") == 7
    assert re.findall(r"<p class=sf-take data-no-i18n>(.*?)</p>", page) == [
        "<b>3/4 scored checks pass</b> &middot; 7 informational &middot; 0 n/a",
        "<b>5/8 scored checks pass</b> &middot; 2 informational &middot; 0 n/a",
        "<b>6/7 scored checks pass</b> &middot; 1 informational &middot; 0 n/a",
    ]
    for probe in ("id=reserveForm", "id=reserveDate", "id=reserveRun", "id=sfDrillMount"):
        assert probe in page, probe
    assert page.count("/static/panelkit.js") == 1


def test_the_mocks_reserve_tiles_note_and_footer_are_not_ported(pair: TestClient) -> None:
    """The reserve card runs the Monte-Carlo ON DEMAND (the mock's "no new simulation runs" would
    be false), the API returns WORKING days only (a calendar-day figure would be fabricated), and
    the Continue segue is the chrome's."""
    page = pair.get("/scorecards").text
    # grep the artifact FIRST: "cal d" is inside the CUI notice's "technical data", so it could
    # never prove a tile absent — the probes are strings the pristine page does NOT carry
    for absent in (
        "P50 FINISH",
        "reserve needed",
        "No new simulation runs",
        "The briefing →",
        "OF SCORED",
    ):
        assert absent not in page, absent
    assert "the simulation is off the page-load path" in page  # the page's own, true, sentence
