"""/standards wears the Claude Design "Control Standards and Execution Indices" layout
(ADR-0475), functionality unchanged — the ninth page on the design.

The artboard (the v2 canvas's ``section[data-screen-label="Control Standards and Execution
Indices"]``, EXECUTED over loopback HTTP in all four themes — ADR-0464's recipe with
``setScreen('sd')``, zero page errors): kicker ``Control · Standards`` · headline ("Every metric,
beside its formula and its source.") · lede · a FAMILY SELECTOR ROW whose three buttons carry the
family name AND its row count (``DCMA 14-point assessment · 16`` · ``agency / Acumen-Fuse execution
indices · 14`` · ``Industry Standards · Schedule Execution Metrics (SEM) · 10``) beside
``⤓ EXCEL · ALL FAMILIES`` · a per-family take line · ONE family panel at a time (head + note + a
``SOURCE:`` chip) · a SEVEN-column table ``REF · METRIC · VALUE · STATUS · THRESHOLD · FORMULA ·
SOURCE`` · a footnote ("A metric this file cannot score prints '—' with an N/A status; the tool
never fabricates a zero") · an "Assessment scorecards →" footer.

**The mock's three counts are this page's own live counts.** Measured on the golden Project2 +
Project5 pair before a line was written: DCMA 16 rows, Fuse 14, SEM 10 — 16 / 14 / 10, the
artboard's numbers exactly. That is what makes the count chips a port and not an invention.

What the layout changes: the masthead already led (unlike /wbs, ADR-0471), so the move is the
family strip — the mock's selector row, ported as IN-PAGE NAVIGATION (``.viz-controls.cd-cursor``,
one ``.cd-chip`` per family carrying its live count, an anchor to that family's panel) — plus the
per-family ``.sf-take`` the mock gives all three where the page had one, the REF column, and the
mock's footnote as the page's own disclosure.

Named omissions (ADR-0475), each with its reason:
  * the mock's **tab-hiding** — a chip that hides the other two families removes rows a reviewer
    Ctrl-Fs, prints and reads side by side; "every standards metric in one place" is the page's
    whole purpose. The chips scroll, they do not conceal, and the ``cd-note`` says so.
  * ``⤓ EXCEL · ALL FAMILIES`` — NO export covers the Fuse or SEM families (the analysis workbook
    stops at DCMA-14; ADR-0327 records the residual). A ⤓ labelled ALL FAMILIES would lie, which
    is the dead/lying-⤓ defect class ``_standards_section``'s own docstring names.
  * the mock's ``INFO`` **status** — the engine's vocabulary is PASS / FAIL / NA (``CheckStatus``);
    a mock is never a metric definition (ADR-0471's precedent for the WBS footnote's wording).
  * the mock's ``01a`` / ``01b`` **split of DCMA-01** — the engine scores ONE ``DCMA01`` "Logic"
    check. The REF column carries the engine's own ``metric_id``, never the mock's decomposition.
  * the **Continue footer** ("Assessment scorecards →") — the chrome's story spine already serves
    the next chapter (ADR-0471's precedent).

Red-first (2026-09-07), on the pristine tree: no strip, no chips, no pill, no panel anchors, no
REF column, and a ``.sf-take`` on the DCMA panel only.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.test_ui_control_effect_census import _FAMILY

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

CHIP = re.compile(r'<a class="cd-chip" data-idx="(\d+)" href="(#[a-z-]+)"[^>]*>([^<]+)</a>')
PILL = re.compile(r'<span class="muted cd-pill" data-no-i18n>([^<]+)</span>')

#: the design's order on the served page: masthead · the family strip · the intro · the families
ORDER = (
    "<div class=chapter-kicker",
    '<h1 class="page-takeaway"',
    '<p class="page-lede">',
    "id=standardsFamilies",
    "DCMA-14 point assessment",
    "NASA / Acumen-Fuse execution indices",
    "Schedule Execution Metrics (SEM)",
)

#: the artboard's own counts, which are this page's live counts on the golden pair
FAMILIES = (("#std-dcma", "DCMA-14", 16), ("#std-fuse", "Acumen-Fuse", 14), ("#std-sem", "SEM", 10))


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
    """Elements carrying the `panel` CLASS — the promotion census the r12 sweep pins."""

    class Count(HTMLParser):
        n = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if "panel" in (dict(attrs).get("class") or "").split():
                self.n += 1

    parser = Count()
    parser.feed(page)
    return parser.n


def _family_chunk(page: str, title: str) -> str:
    start = page.index(title)
    return page[start : page.index("</table>", start)]


def test_the_family_strip_serves_one_anchor_chip_per_family_with_its_live_count(
    pair: TestClient,
) -> None:
    page = pair.get("/standards").text
    assert page.count("id=standardsFamilies") == 1
    chips = CHIP.findall(page)
    assert [(idx, href) for idx, href, _label in chips] == [
        ("0", "#std-dcma"),
        ("1", "#std-fuse"),
        ("2", "#std-sem"),
    ], chips
    for (_href, short, count), (_idx, _h, label) in zip(FAMILIES, chips, strict=True):
        assert label == f"{short} &middot; {count}", label


def test_each_chips_count_is_the_rows_that_family_actually_renders(pair: TestClient) -> None:
    """The count is a MEASUREMENT of the served table, not a constant beside it."""
    page = pair.get("/standards").text
    rendered = [
        _family_chunk(page, title).count("<tr><td")
        for title in (
            "DCMA-14 point assessment",
            "NASA / Acumen-Fuse execution indices",
            "Schedule Execution Metrics (SEM)",
        )
    ]
    assert rendered == [count for _href, _short, count in FAMILIES], rendered
    for (_href, short, _count), rows in zip(FAMILIES, rendered, strict=True):
        assert f"{short} &middot; {rows}" in page


def test_every_chip_anchors_a_panel_that_is_served(pair: TestClient) -> None:
    """A chip whose target does not exist is a dead control — the rank-3 law."""
    page = pair.get("/standards").text
    for href, _short, _count in FAMILIES:
        assert f"id={href[1:]}" in page, href


def test_the_strip_carries_a_pill_and_says_nothing_is_hidden(pair: TestClient) -> None:
    page = pair.get("/standards").text
    pill = PILL.search(page)
    assert pill and pill.group(1).startswith("40 metrics &middot; Project5.mspdi.xml"), pill
    assert "a chip jumps to one" in page and "nothing is hidden" in page


def test_chips_carry_no_id_and_no_family_word(pair: TestClient) -> None:
    """The M1 control census recognises a stepper by id + className; an anchor chip is neither."""
    page = pair.get("/standards").text
    tags = re.findall(r'<a class="cd-chip[^>]*>', page)
    assert len(tags) == 3
    for tag in tags:
        assert " id=" not in tag and not re.search(_FAMILY, tag), tag
    strip = re.search(r'<div class="viz-controls cd-cursor" id=(\w+)>(.*?)</div>', page, re.S)
    assert strip and not re.search(_FAMILY, strip.group(1))
    values = re.findall(r'(?:class|id)="?([^" >]+)"?', strip.group(2))
    assert values and not any(re.search(_FAMILY, v) for v in values), values


def test_the_masthead_leads_then_the_strip_then_the_three_families(pair: TestClient) -> None:
    page = pair.get("/standards").text
    missing = [mark for mark in ORDER if mark not in page]
    assert not missing, missing
    positions = [page.index(mark) for mark in ORDER]
    assert positions == sorted(positions), list(zip(ORDER, positions, strict=True))


def test_the_table_carries_the_artboards_ref_column_first(pair: TestClient) -> None:
    page = pair.get("/standards").text
    assert page.count("<th scope=col>Ref</th>") == 3
    header = (
        "<tr><th scope=col>Ref</th><th scope=col>Metric</th><th scope=col>Value</th>"
        "<th scope=col>Status</th><th scope=col>Threshold</th><th scope=col>Formula</th>"
        "<th scope=col>Source</th></tr>"
    )
    assert page.count(header) == 3


def test_the_ref_cell_is_the_engines_own_metric_id_never_the_mocks_decomposition(
    pair: TestClient,
) -> None:
    page = pair.get("/standards").text
    dcma = _family_chunk(page, "DCMA-14 point assessment")
    for mid in ("DCMA01", "DCMA04_FS", "DCMA13", "DCMA14"):
        assert f"<td class=std-ref>{mid}</td>" in dcma, mid
    assert "01a" not in dcma and "01b" not in dcma  # the mock's split; the engine scores one 01
    sem = _family_chunk(page, "Schedule Execution Metrics (SEM)")
    assert "<td class=std-ref>sem_bei_current</td>" in sem


def test_all_three_families_carry_the_take_the_mock_gives_each(pair: TestClient) -> None:
    """The pristine page put a .sf-take on the DCMA panel only; the artboard gives all three."""
    page = pair.get("/standards").text
    assert page.count("<p class=sf-take") == 3
    for title in (
        "DCMA-14 point assessment",
        "NASA / Acumen-Fuse execution indices",
        "Schedule Execution Metrics (SEM)",
    ):
        chunk = _family_chunk(page, title)
        assert "sf-take" in chunk, title
        # the r12 contract: the counts line precedes the muted read-me line
        assert chunk.index("sf-take") < chunk.index("<p class=muted>"), title
    # the DCMA take keeps its pinned wording verbatim; the two new ones use its exact idiom
    assert "<p class=sf-take data-no-i18n>10 passed · 4 failed · 2 N/A on Project5.mspdi.xml.</p>"
    takes = re.findall(r"<p class=sf-take data-no-i18n>([^<]*)</p>", page)
    assert takes == [
        "10 passed · 4 failed · 2 N/A on Project5.mspdi.xml.",
        "0 passed · 1 failed · 13 N/A on Project5.mspdi.xml.",
        "0 passed · 0 failed · 10 N/A on Project5.mspdi.xml.",
    ], takes


def test_each_familys_take_tallies_to_the_rows_that_family_renders(pair: TestClient) -> None:
    """A take that does not add up to its own table is the drift this helper exists to prevent."""
    page = pair.get("/standards").text
    takes = re.findall(
        r"<p class=sf-take data-no-i18n>(\d+) passed · (\d+) failed · (\d+) N/A", page
    )
    assert len(takes) == 3
    for (passed, failed, na), (_href, _short, rows) in zip(takes, FAMILIES, strict=True):
        assert int(passed) + int(failed) + int(na) == rows, (passed, failed, na, rows)


def test_the_page_states_the_artboards_never_fabricate_a_zero_disclosure(pair: TestClient) -> None:
    page = pair.get("/standards").text
    assert "the tool never fabricates a zero" in page
    assert "N/A status" in page


def test_the_uncovered_families_still_carry_no_export(pair: TestClient) -> None:
    """The mock's ⤓ EXCEL · ALL FAMILIES is NOT ported: no export covers Fuse or SEM."""
    page = pair.get("/standards").text
    assert "ALL FAMILIES" not in page
    assert page.count("data-export") == 1  # the DCMA analysis workbook, unchanged
    for title in ("NASA / Acumen-Fuse execution indices", "Schedule Execution Metrics (SEM)"):
        assert "data-export" not in _family_chunk(page, title), title


def test_the_mocks_info_status_never_reaches_the_page(pair: TestClient) -> None:
    """CheckStatus is PASS / FAIL / NA; a design mock is never a metric definition."""
    page = pair.get("/standards").text
    assert ">INFO<" not in page


def test_every_panel_figure_and_row_survives_the_layout(pair: TestClient) -> None:
    page = pair.get("/standards").text
    assert _panels(page) == 5  # intro · DCMA · Fuse · SEM · the chrome's Ask panel
    assert page.count("<table class=card-table>") == 3
    assert page.count("<tr><td") == 40
    for probe in ("DCMA 14-Point Assessment", "Fuse v8.11.0 Metric History parity."):
        assert probe in page, probe


def test_a_single_loaded_version_still_serves_the_strip_with_its_own_counts() -> None:
    """Unlike a per-file drill (ADR-0470), the families exist with ONE file loaded — and this is
    the corpus that proves a count is COMPUTED rather than a constant beside the table.

    The DCMA family always scores exactly 16 checks and SEM always 10, so no fixture in the repo
    can distinguish a hardcoded 16 / 10 from a measured one (recorded in ADR-0475; the mutation
    battery says so by name). The Fuse family DOES vary: the CEI rows need a prior version, so
    the same page reads 9 with one file loaded and 14 with two. A chip count that did not follow
    its table is caught here and nowhere else."""
    page = _client("Project5").get("/standards").text
    assert "id=standardsFamilies" in page
    chips = CHIP.findall(page)
    assert [href for _idx, href, _label in chips] == ["#std-dcma", "#std-fuse", "#std-sem"]
    assert "CEI needs" in page  # the single-version note the family already served
    fuse_rows = _family_chunk(page, "NASA / Acumen-Fuse execution indices").count("<tr><td")
    assert fuse_rows == 9, fuse_rows  # 14 on the pair: the CEI rows are the difference
    assert [label for _idx, _href, label in chips] == [
        "DCMA-14 &middot; 16",
        "Acumen-Fuse &middot; 9",
        "SEM &middot; 10",
    ], chips
    assert "35 metrics &middot; Project5.mspdi.xml" in page  # the pill follows too (40 on the pair)
