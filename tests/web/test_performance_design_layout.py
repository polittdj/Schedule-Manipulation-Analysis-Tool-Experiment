"""/performance wears the Claude Design "07 How we execute" layout (ADR-0468), functionality
unchanged.

The artboard (recovered by EXECUTING the v2 canvas over loopback HTTP, ``setScreen('px')``, four
themes, zero page errors): kicker · takeaway · lede · a cursor strip (▶ Play the files · ◂ Back ·
Step ▸ · a FILE pill) · a six-tile KPI row · five numbered panels — ① work-to-go census + workoff
burden · ② duration ratio · ③ bow wave + cumulative S · ④ execution indices, with its reading
paragraph beneath · ⑤ portfolio quads — then an EVM ledger and an SPI(t)-by-WBS chart that are
other pages' data (not ported). The page keeps its fourteen tiles VERBATIM inside the ONE grid the
enlarge contract depends on (``#perfGrid``), regrouped under five ``.cd-band`` headings in the
design's order; its server-rendered ◀ Prev / caption / Next ▶ / ▶ Play are re-homed by
``performance.js`` into a masthead strip with one chip per loaded file (the SELECTED file on — the
page opens on the newest); the reading block reuses the page's own three explainer beats.

Red-first (2026-09-06): the pristine page served no strip, no chips, no bands, no reading block,
and the tiles in the workbook's G1..G7 order.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.chrome import _e
from schedule_forensics.web.performance import _READ_DECIDE, _READ_HOW, _READ_WHAT
from web.test_ui_control_effect_census import _FAMILY

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"

DESIGN_ORDER = [
    ("① Work-to-go census + workoff burden", ["g1Census", "g1Normal", "g4Starts", "g4Finishes"]),
    ("② Duration ratio", ["g5Scurve", "g5Hist"]),
    ("③ Bow wave + cumulative S", ["g2Starts", "g2Finishes", "g2Cum"]),
    ("④ Execution indices", ["g3Starts", "g3Finishes"]),
    ("⑤ Portfolio quads", ["quadHmiCei", "quadRatio", "quadBeiCp"]),
]


def _client(*names: str) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name in names:
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        resp = client.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
        assert resp.status_code == 200
    return client


@pytest.fixture(scope="module")
def pair() -> str:
    return _client("Hard_File", "Hard_File_updated3").get("/performance").text


@pytest.fixture(scope="module")
def one() -> str:
    return _client("Hard_File_updated3").get("/performance").text


def _grid(page: str) -> str:
    return page.split("<div class=mosaic id=perfGrid>", 1)[1].split("</div>\n<script", 1)[0]


def test_the_cursor_strip_serves_the_master_slot_and_one_chip_per_file(pair: str) -> None:
    assert pair.count("id=performanceCursor") == 1
    assert pair.count("<span id=performanceMaster class=cd-master></span>") == 1
    assert pair.count("id=performanceFrame") == 1
    chips = re.findall(r'class="cd-chip( on)?" data-idx="(\d+)" title="([^"]+)"', pair)
    assert [(bool(on), idx) for on, idx, _t in chips] == [(False, "0"), (True, "1")]  # newest on
    assert [t for _on, _idx, t in chips] == ["Hard_File.mpp.xml", "Hard_File_updated3.mpp.xml"]
    assert pair.index("id=performanceCursor") < pair.index("<div class=panel-head>")  # masthead


def test_the_bands_hold_the_verbatim_tiles_in_the_design_order(pair: str) -> None:
    grid = _grid(pair)
    bands = re.findall(r'<h2 class="cd-band"[^>]*>(.*?)</h2>', grid)
    assert bands == [title for title, _mounts in DESIGN_ORDER]
    # a tile spans lines (its hint attribute carries real newlines), hence re.S
    tiles = re.findall(r'<section class="tile panel".*?class=chart-host id=(\w+)>', grid, re.S)
    assert tiles == [m for _t, ms in DESIGN_ORDER for m in ms], tiles
    # each band precedes its own tiles and follows the previous band's last tile
    pos = 0
    for title, mounts in DESIGN_ORDER:
        band_at = grid.index(f'<h2 class="cd-band">{title}</h2>', pos)
        for mount in mounts:
            tile_at = grid.index(f"id={mount}>", band_at)
            assert tile_at > band_at, (title, mount)
            pos = tile_at


def test_the_reading_block_is_the_pages_own_explainer_and_sits_under_the_indices(pair: str) -> None:
    grid = _grid(pair)
    block = '<section class="cd-block cd-read cd-band"><h2>How to read this</h2>'
    assert grid.count(block) == 1
    for lead, text in (
        ("What it shows.", _READ_WHAT),
        ("How to read it.", _READ_HOW),
        ("Why it matters.", _READ_DECIDE),
    ):
        assert f"<b>{lead}</b> {_e(text)}" in grid
    assert grid.index("id=g3Finishes>") < grid.index(block) < grid.index("⑤ Portfolio quads")


def test_a_single_file_keeps_the_bands_and_serves_no_cursor(one: str) -> None:
    for absent in (
        "id=performanceCursor",
        "cd-chip",
        "id=performanceMaster",
        "id=performanceFrame",
    ):
        assert absent not in one
    assert one.count('<h2 class="cd-band">') == 5
    assert one.count('<section class="cd-block cd-read cd-band">') == 1
    assert one.count("id=perfPrev") == 1  # the stepper still renders where it always did


def test_the_chips_and_the_strip_carry_no_census_family_word(pair: str) -> None:
    family = re.compile(_FAMILY, re.IGNORECASE)
    start = pair.index("id=performanceCursor")
    strip = pair[start : pair.index("</div>", start)]
    for attr in re.findall(r'(?:id|class)="?([^"\s>]+)', strip):
        assert not family.search(attr), attr


def test_nothing_the_contract_pins_moved(pair: str, one: str) -> None:
    """Measured on the pristine tree before the layout existed — identical after it."""
    for page in (pair, one):
        assert page.count("<div class=panel") == 3 and page.count("<div class=panel-head>") == 1
        assert page.count("⤓ EXCEL") == 14 and page.count("⛶ ENLARGE") == 14
        assert page.count("data-sf-excel") == 14 and page.count("data-sf-big") == 14
        assert page.count("class=chart-host") == 14 and page.count("<form") == 5
        assert page.count("class=sf-take") == 15 and page.count("class=prov-chip") == 15
        assert page.count("id=perfData>") == 1 and page.count("/static/performance.js") == 1
        assert page.count("/static/panelkit.js") == 1 and "▦" not in page
        assert 'class="tile panel"' in page and page.count('<section class="tile panel"') == 14
        for control in ("id=perfPrev", "id=perfStep", "id=perfNext", "id=perfPlay"):
            assert page.count(control) == 1, control
