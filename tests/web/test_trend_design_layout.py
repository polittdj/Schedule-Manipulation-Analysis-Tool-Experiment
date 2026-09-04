"""/trend wears the Claude Design "05 How it moved" layout (ADR-0460; the ADR-0451/0456 method):
a masthead cursor strip — the page's own ▶ Play all / ⏭ Step all master mounted as the primary
control, ONE chip per version, the frame pill — the Focus form as the options row, then the
prototype's rows: the version-trend table beside the manipulation signals (the design's "finish by
version" beside "net finish impact per update"), the trend charts full width, the quality
drill-down beside the schedule-quality sentences and a "How to read this" block whose three beats
are this page's own explainer, the margin burndown full width. Every id, form byte, panel, toolbar
glyph and figure the page carried before survives ("don't modify any of the functionality"); the
third design page also aliases /volatility's ``vol-*`` cursor vocabulary onto the shared ``cd-*``
family (the repo's own rule: extract when a third caller appears).

Red-first (2026-09-04): the pristine page had no cursor strip, no chips, no design rows and no
reading block, and /volatility still spoke ``vol-chip``.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.chrome import _EXPLAINERS

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"

#: every id the three page scripts read, plus the ids the contract tests pin — all must survive
IDS = (
    "trendCharts",
    "qualDrillPanel",
    "qualMetric",
    "qualPrev",
    "qualLabel",
    "qualNext",
    "qualPlay",
    "qualBars",
    "qualDrill",
    "findingsDrill",
    "findingsData",
    "marginBurndown",
    "sfDrillMount",
)
#: the six panel heads, in the DESIGN's reading order (the table beside the signals, the charts,
#: the drill beside the sentences, the burndown)
HEADS = (
    "Version trend &mdash; 2 versions, oldest first (by data date)",
    "Manipulation-trend signals (consecutive versions)",
    "Trend charts",
    "Quality drill-down &amp; animation",
    "Schedule-quality trends",
    "Schedule margin burndown",
)


def _panels(page: str) -> int:
    """Elements carrying the `panel` CLASS — a parser census (a substring count also matches
    `panel-head`, the trap ADR-0456's first draft fell into)."""

    class Count(HTMLParser):
        n = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if "panel" in (dict(attrs).get("class") or "").split():
                self.n += 1

    parser = Count()
    parser.feed(page)
    return parser.n


@pytest.fixture
def pair() -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert resp.status_code == 200
    return client


def test_the_cursor_strip_serves_the_master_slot_and_one_chip_per_version(
    pair: TestClient,
) -> None:
    page = pair.get("/trend").text
    cursor = re.search(
        r'<div class="viz-controls cd-cursor" id=trendCursor>(.*?)\n</div>', page, re.S
    )
    assert cursor, "no design cursor strip"
    strip = cursor.group(1)
    # trend.js mounts its OWN master (#sfPlayAll / #sfStepAll) into this slot once the data lands
    assert "<span id=trendMaster class=cd-master></span>" in strip
    chips = re.findall(r'<button type=button class="cd-chip( on)?" data-idx="(\d+)"', strip)
    assert [idx for _, idx in chips] == ["0", "1"], chips  # the golden pair: two versions
    # every chart opens fully revealed (= the classic all-versions chart), so the LAST chip is on
    assert [bool(on) for on, _ in chips] == [False, True]
    assert 'title="Project2.mspdi.xml" data-no-i18n>v1</button>' in strip  # a chip names its file
    assert 'title="Project5.mspdi.xml" data-no-i18n>v2</button>' in strip
    assert 'id=trendFrame class="muted cd-pill" data-no-i18n' in strip
    # the strip sits at the top of the body, before the options row and every panel
    assert (
        page.index("id=trendCursor") < page.index("<div class=cd-options>") < page.index(HEADS[0])
    )


def test_the_design_rows_hold_the_verbatim_panels_in_the_design_order(pair: TestClient) -> None:
    page = pair.get("/trend").text
    positions = [page.index(f"<div class=panel-head><h2>{h}</h2>") for h in HEADS]
    assert positions == sorted(positions), "panel heads are not in the design's order"
    # row 1: the table beside the signals (the design's 1.2fr / .8fr row)
    row1 = re.search(
        r'<div class="cd-grid cd-grid-12">(.*?)</div>\n'
        r'<div class=panel data-export="/export/xlsx/trend">',
        page,
        re.S,
    )
    assert row1, "no 1.2fr/.8fr row"
    assert HEADS[0] in row1.group(1) and HEADS[1] in row1.group(1)
    assert HEADS[2] not in row1.group(1)
    # row 2: the drill beside a stack of the sentences + the reading block
    row2 = re.search(
        r'<div class="cd-grid cd-grid-2">(.*?)</div>\n</div>\n'
        r'<div class=panel data-export="/export/xlsx/margin">',
        page,
        re.S,
    )
    assert row2, "no drill / reading row"
    body = row2.group(1)
    assert body.index(HEADS[3]) < body.index("<div class=cd-stack>") < body.index(HEADS[4])
    assert body.index(HEADS[4]) < body.index("How to read this")
    what, how, decide = _EXPLAINERS["Trend"]
    beats = re.findall(r'<div class="cd-beat (cd-beat-\w+)"><b>(.*?)</b> (.*?)</div>', body, re.S)
    assert [(cls, lead) for cls, lead, _ in beats] == [
        ("cd-beat-accent", "What it shows."),
        ("cd-beat-warn", "How to read it."),
        ("cd-beat-bad", "Why it matters."),
    ]
    assert [text for _, _, text in beats] == [what, how, decide]  # the page's own words, verbatim
    assert '<section class="cd-block cd-read">' in body and "cd-block panel" not in page


def test_nothing_the_contract_pins_moved(pair: TestClient) -> None:
    """The restyle is a re-arrangement: the panel census, the takes, the provenance chips, the
    exports, the toolbar glyphs, the forms and every id are byte-for-byte what they were
    (measured on the pristine page: 10 panels · 6 takes · 6 chips · 4 + 1 exports · 3 ⤓ · 4 ⛶ ·
    5 forms · no ▦ in the served HTML — the charts add theirs client-side)."""
    page = pair.get("/trend").text
    assert _panels(page) == 10
    assert page.count("class=sf-take") == 6 and page.count("class=prov-chip") == 6
    assert page.count('data-export="/export/xlsx/trend"') == 4
    assert page.count('data-export="/export/xlsx/margin"') == 1
    assert page.count("⤓ EXCEL") == 3 and page.count("⛶") == 4 and "▦ DATA" not in page
    assert page.count("<form") == 5
    # the Focus form is byte-exact, still panel-wrapped, and now IS the options row
    assert (
        "<div class=cd-options>\n<div class=panel>"
        "<form method=get action=/trend class=viz-controls>"
    ) in page
    assert 'id=trendCharts class="charts chart-host"' in page
    for ident in IDS:
        assert f"id={ident}" in page, f"lost #{ident}"
    for src in (
        "/static/trend.js",
        "/static/trend_drill.js",
        "/static/margin.js",
        "/static/panelkit.js",
        "/static/findings_drill.js",
    ):
        assert page.count(src) == 1, src
    # the focus target still flows into the charts host and the form
    focused = pair.get("/trend?target=1").text
    assert 'data-target="1"' in focused and 'value="1"' in focused


def test_the_scripts_expose_the_frame_and_the_chips_drive_the_existing_steppers(
    pair: TestClient,
) -> None:
    """A chip is the page's own steppers: trend.js / margin.js / trend_drill.js each publish the
    frame they are showing as ``data-frame`` on the control they already own, and the cursor
    clicks the Next buttons that already exist the number of times that lands every chart on the
    chosen version — nothing renders any other way than the buttons render it."""
    trend = pair.get("/static/trend.js").text
    assert 'bar.setAttribute("data-frame", String(idx));' in trend
    assert 'document.getElementById("trendMaster")' in trend  # the master mounts into the strip
    assert "function sfDesignCursor()" in trend and "function goTo(i)" in trend
    assert "function syncChips()" in trend
    assert '"#trendCursor .cd-chip[data-idx]"' in trend
    # the cursor is wired only after the master exists
    assert trend.index("sfMasterBar();") < trend.index("sfDesignCursor();")
    assert 'bar.setAttribute("data-frame", String(idx));' in pair.get("/static/margin.js").text
    drill = pair.get("/static/trend_drill.js").text
    assert 'bars.setAttribute("data-frame", String(current));' in drill


def test_volatility_shares_the_cd_cursor_vocabulary(pair: TestClient) -> None:
    """The third design page aliases /volatility's cursor classes onto the shared family: one
    vocabulary for the cursor strip, the primary play button, the chips and the frame pill;
    the page-specific ``vol-*`` blocks, rows, KPI and bands stay."""
    vol = pair.get("/volatility").text
    assert '<div class="viz-controls cd-cursor" id=volCursor>' in vol
    assert "id=volPlay type=button class=cd-play" in vol
    assert "<span class=cd-chips>" in vol and 'id=volLabel class="muted cd-pill"' in vol
    assert re.findall(r'class="cd-chip[^"]*" data-idx="(\d+)"', vol) == ["0", "1"]
    for old in ("vol-cursor", "vol-play", "vol-chips", "vol-chip", "vol-pill"):
        assert old not in vol, old
    assert 'data-vol-panel="1"' in vol  # the page-specific vocabulary is untouched
    js = pair.get("/static/volatility.js").text
    assert js.count('querySelectorAll(".cd-chip")') == 2 and ".vol-chip" not in js
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    for rule in (".vol-cursor", ".vol-play", ".vol-chips", ".vol-chip", ".vol-pill"):
        assert f"{rule} " not in css and f"{rule}{{" not in css, rule
        assert f"{rule}." not in css, rule
    assert ".cd-grid-12 {" in css and ".cd-stack {" in css
