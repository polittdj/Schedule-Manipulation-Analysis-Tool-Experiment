"""/cei wears the Claude Design "06 Work piling up" layout (ADR-0456; the ADR-0451 method):
the chart panel's cursor strip — Auto-play as the primary button, Prev / Next, ONE chip per
snapshot, the frame pill — then the two ADR-0268 forms as the options row, then the chart; below
it the prototype's two-column row: the CEI panel beside a "How to read this" block whose three
beats are this page's own explainer. Every id, form byte, panel, toolbar glyph and data figure the
page carried before survives ("don't modify any of the functionality"). Red-first: the pre-restyle
page had a flat stepper row, no chips, no two-column row and no reading block.
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

#: every id cei.js reads, plus the two ids the contract tests pin — all must survive the restyle
IDS = ("ceiChart", "prevSnap", "nextSnap", "autoPlay", "snapLabel", "ceiTotals", "ceiTrack")


def _panels(page: str) -> int:
    """Elements carrying the `panel` CLASS (the promotion census the r10 contract pins)."""

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


def test_the_cursor_strip_carries_the_stepper_and_one_chip_per_snapshot(pair: TestClient) -> None:
    page = pair.get("/cei").text
    cursor = re.search(r'<div class="viz-controls cd-cursor">(.*?)\n</div>', page, re.S)
    assert cursor, "no design cursor strip"
    strip = cursor.group(1)
    for ident in ("autoPlay", "prevSnap", "nextSnap", "snapLabel", "ceiTotals"):
        assert f"id={ident}" in strip, ident
    assert "id=autoPlay type=button class=cd-play" in strip  # the primary button IS the stepper's
    chips = re.findall(r'<button type=button class="cd-chip( on)?" data-idx="(\d+)"', strip)
    assert [idx for _, idx in chips] == ["0", "1"], chips  # the golden pair: two snapshots
    assert [bool(on) for on, _ in chips] == [True, False]  # the chart opens on the first snapshot
    assert 'title="Project2.mspdi.xml">v1</button>' in strip  # a chip names its file
    assert 'title="Project5.mspdi.xml">v2</button>' in strip
    for ident in IDS:
        assert f"id={ident}" in page, f"lost #{ident}"


def test_the_two_column_row_holds_the_cei_panel_and_the_reading_block(pair: TestClient) -> None:
    page = pair.get("/cei").text
    row = re.search(r'<div class="cd-grid cd-grid-2">(.*?)</div>\n<script', page, re.S)
    assert row, "no design two-column row"
    body = row.group(1)
    assert body.index("CEI &mdash; Current Execution Index") < body.index("How to read this")
    what, how, decide = _EXPLAINERS["Bow Wave / CEI"]
    beats = re.findall(r'<div class="cd-beat (cd-beat-\w+)"><b>(.*?)</b> (.*?)</div>', body, re.S)
    assert [(cls, lead) for cls, lead, _ in beats] == [
        ("cd-beat-accent", "The wave."),
        ("cd-beat-warn", "The index."),
        ("cd-beat-bad", "Why it matters."),
    ]
    # the beats are this page's own explainer, verbatim — no new prose
    assert [text for _, _, text in beats] == [what, how, decide]
    assert '<section class="cd-block cd-read">' in body and "cd-block panel" not in page


def test_nothing_the_contract_pins_moved(pair: TestClient) -> None:
    """The restyle is a re-arrangement: the panel census, the toolbars, the forms and the
    figures the r10 contract pins are byte-for-byte what they were."""
    page = pair.get("/cei").text
    assert _panels(page) == 5  # a parser census — a substring count also matches `panel-head`
    assert page.count("class=sf-take") == 2 and page.count("class=prov-chip") == 2
    assert page.count("<form") == 6
    assert "<form method=post action=/target class=viz-controls>" in page
    assert "<form method=get action=/cei class=viz-controls>" in page
    assert "id=ceiChart class=chart-host" in page
    assert page.count("⤓ EXCEL") == 2 and "▦ DATA" not in page
    assert page.count("/static/panelkit.js") == 1 and "/static/cei.js" in page
    # the options row keeps both forms and sits ABOVE the chart, the colour legend prose below it
    assert page.index("<div class=cd-options>") < page.index("id=ceiChart")
    assert page.index("id=ceiChart") < page.index("Gold = baselined to finish")


def test_the_mission_wall_serves_no_chips_and_the_shared_script_still_runs_there(
    pair: TestClient,
) -> None:
    """cei.js is the /mission wall's chart script too; the wall serves no chip list, and the
    script must treat that as a no-op rather than throw (the browser half of this is the
    zero-pageerror assertion the wall's own browser tests already carry)."""
    mission = pair.get("/mission").text
    assert "cd-chip" not in mission
    for ident in ("ceiChart", "prevSnap", "nextSnap", "autoPlay", "snapLabel"):
        assert f'id="{ident}"' in mission or f"id={ident}" in mission, ident
    js = pair.get("/static/cei.js").text
    assert 'document.querySelectorAll(".cd-chip[data-idx]")' in js
    assert "function syncChips()" in js and "function goTo(i)" in js
