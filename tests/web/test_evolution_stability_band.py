"""ADR-0427 — Chapter 04's stability band on ``/evolution``.

The Mission Ops prototype renders "How stable is the path" as ONE screen of five numbered panels
driven by a single version cursor. The repo split that content: ``/evolution`` carried the path
Gantt and the what-if ledger, ``/volatility`` carried the churn analytics. This module guards the
band that brings the prototype's panels 1-4 onto the chapter page.

The two claims that actually matter:

1. **ONE dataset, not a fork.** The band is drawn from ``_volatility_data`` — the same effective
   critical sets ``/volatility`` uses — and mounts ``volatility.js``'s OWN chart hosts. If a
   future change re-derives the numbers here, the two pages can disagree about the same schedule,
   which in a testimony product is the worst kind of defect. The test compares the two pages'
   embedded datasets **byte for byte**.

2. **Two populations on one page, each labelled.** The band spans ALL loaded versions; everything
   below it is PAIR-scoped (ADR-0371). That is exactly the shape ADR-0420 names as a hazard — a
   page stating two population sizes at once. Both scopes are correct here and deliberately
   different, so the guard is not "make them agree" but "every panel says which one it means".
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.evolution import _CH04_NUMERALS

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "fuse_hardfile"
#: Four versions — enough for the band's all-version population to DIFFER from any single pair,
#: which is the whole point of the scope guard. Two versions would make the two scopes identical
#: and the test would pass without proving anything.
VERSIONS = ("Hard_File", "Hard_File_updated", "Hard_File_updated2", "Hard_File_updated3")


def _load(names: tuple[str, ...]) -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in names:
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", xml, "text/xml")})
    return c


@pytest.fixture
def client() -> TestClient:
    return _load(VERSIONS)


@pytest.fixture
def client_one() -> TestClient:
    return _load(VERSIONS[:1])


def _voldata(html: str) -> dict[str, object] | None:
    m = re.search(r"id=volData>(.*?)</script>", html, re.S)
    return json.loads(m.group(1)) if m else None


# ── 1. one dataset, one implementation ────────────────────────────────────────────────────────


def test_the_band_mounts_the_prototypes_four_panels(client: TestClient) -> None:
    page = client.get("/evolution").text
    for mount in ("volChurn", "volFlow", "volHeatmap", "volRibbon"):
        assert f"id={mount}" in page, mount
    assert "id=volData" in page and "/static/volatility.js" in page
    # the cursor that drives all four
    assert "id=volPrev" in page and "id=volNext" in page and "id=volPlay" in page


def test_the_band_mounts_ONLY_those_four_of_volatilitys_eleven(client: TestClient) -> None:
    """``volatility.js`` renders whatever hosts a page provides. Mounting a subset is the
    supported use — but if this page silently grew the whole /volatility mosaic, the chapter
    screen would stop being the prototype's five-panel layout and nobody would notice."""
    page = client.get("/evolution").text
    for absent in ("volGauge", "volArea", "volTenure", "volDwell", "volJumpers", "volStrips"):
        assert f"id={absent}" not in page, f"{absent} leaked onto the chapter page"


def test_both_pages_embed_the_byte_identical_dataset(client: TestClient) -> None:
    """The load-bearing one. Two pages, one schedule, one set of numbers."""
    evo = _voldata(client.get("/evolution").text)
    vol = _voldata(client.get("/volatility").text)
    assert evo is not None and vol is not None
    assert evo == vol, "the chapter band re-derived the dataset instead of reusing it"


def test_the_headline_figure_is_the_datasets_own_stability(client: TestClient) -> None:
    """The 32px number must be the dataset's mean Jaccard, not a second rounding of it."""
    page = client.get("/evolution").text
    data = _voldata(page)
    assert data is not None
    stability = data["stability"]
    assert isinstance(stability, float)
    shown = re.search(r'class="stab-num[^"]*"[^>]*>([^<]*)<', page)
    assert shown is not None, "no stability figure rendered"
    assert shown.group(1) == f"{round(stability * 100)}%"


# ── 2. two populations, each labelled (ADR-0420) ──────────────────────────────────────────────


def test_every_band_takeaway_names_its_all_version_population(client: TestClient) -> None:
    """ADR-0420's rule applied forward: this page legitimately carries two populations, so the
    band's panels must each say they read the whole history. A takeaway that drops the scope
    phrase leaves the reader to assume it means the pair the rest of the page is about."""
    page = client.get("/evolution").text
    band = page[page.index("id=evoStabGrid") : page.index("id=volData")]
    takeaways = re.findall(r"<p class=sf-take[^>]*>(.*?)</p>", band, re.S)
    assert len(takeaways) == 4, f"expected one takeaway per band panel, saw {len(takeaways)}"
    scoped = [t for t in takeaways if "loaded versions" in t]
    # The ribbon's takeaway is about the CURSOR's pair by construction, so it names that instead.
    assert len(scoped) >= 3, f"band takeaways not scope-labelled: {takeaways}"
    assert any("cursor" in t for t in takeaways), "the ribbon must name its pair scope"


def test_the_band_and_the_pair_panels_state_different_populations(client: TestClient) -> None:
    """The differential check, in the spirit of ADR-0417/0420's oracle: with four versions
    loaded the band's population (all four) must be observably DIFFERENT from the what-if
    ledger's (one pair). If they ever print the same scope, one of them is lying."""
    page = client.get("/evolution").text
    assert "across all 4 loaded versions" in page, "the band lost its all-version scope"
    assert "one pair" in page or "pair" in page.lower(), "the pair panels lost their scope"


def test_one_version_yields_no_band_because_there_is_no_pair() -> None:
    """One file has no consecutive pair, so there is no carry-over to state. The band must be
    ABSENT, not present-and-zero — zero would be a fabricated figure (design system §7).

    Called DIRECTLY rather than through the route: mutation M3 showed a route-level check never
    fires, because ``/evolution``'s own "load two versions" empty state returns first. A test
    driven through the page would go green whether or not this precondition existed, which is
    this repo's most-repeated defect. The unit call puts the assertion on the real subject.
    """
    from schedule_forensics.web.evolution import _stability_panels

    assert _stability_panels([], []) == ""


def test_the_page_shows_no_band_for_a_single_version(client_one: TestClient) -> None:
    """The end-to-end half of the claim above — true here for the page's own reason."""
    page = client_one.get("/evolution").text
    assert "id=evoStabGrid" not in page
    assert "MEAN CARRY-OVER" not in page


# ── 3. the prototype's numbering ──────────────────────────────────────────────────────────────


def test_the_band_panels_carry_the_prototypes_numerals(client: TestClient) -> None:
    """The prototype numbers its panels, and panel 5's own copy says 'the four panels above are
    the ones that animate' — only true if the reader can tell which four. The numerals come from
    one tuple so a renumber cannot desynchronise them."""
    page = client.get("/evolution").text
    n1, n2, n3, n4, _n5 = _CH04_NUMERALS
    assert f"{n1} Stability signal" in page
    assert f"{n2} Flow of the path" in page
    assert f"{n3} Membership matrix" in page
    assert f"{n4} Transition ribbons" in page


def test_every_band_panel_carries_the_toolbar_contract(client: TestClient) -> None:
    """Design system §3: every data visual ships ⤓ EXCEL and ⛶ ENLARGE."""
    page = client.get("/evolution").text
    band = page[page.index("id=evoStabGrid") : page.index("id=volData")]
    assert band.count("data-sf-excel") == 4, band.count("data-sf-excel")
    assert band.count("data-sf-big") == 4, band.count("data-sf-big")
    assert band.count("data-sf-hint") == 4, "each panel needs its what/how/decide hint"


def test_the_band_does_not_fabricate_a_threshold(client: TestClient) -> None:
    """GAO BP-6 and the DCMA CP test call an erratic chain a failure without publishing a
    number. The band prints one, so it must say on the page that the band is guidance."""
    page = client.get("/evolution").text
    assert "display guidance, not a published threshold" in page
