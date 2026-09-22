"""The /onepager-compare page through the app: the two slots, the comparison it shows, the exports,
the design rows (ADR-0465).

The synthetic pair is the twin workbook (ADR-0446's) as PRIOR and a re-dated copy as CURRENT — a
slip, a pull-in, a new row, a removed row, a type change — so every figure the page prints is one
the engine tests already pin. Red-first (2026-09-05): before the route existed every request here
was a 404.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.xlsx_read import read_xlsx
from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.chrome import _EXPLAINERS
from schedule_forensics.web.i18n import catalog_for
from web.onepager_twin import TWIN_ROWS, twin_xlsx

TODAY = dt.date(2026, 9, 1)

#: The CURRENT sheet: the twin with "Boots 1" slipped 30 calendar days, "CDR" pulled in 7, "MET
#: Testing" removed, "Boots 3" added, "TRR" (a milestone) turned into a two-week activity.
CURRENT_ROWS: tuple[tuple[object, ...], ...] = (
    *(
        row
        for row in (
            ("Flight Manifests", "Boots 1", 46595)
            if r[:2] == ("Flight Manifests", "Boots 1")
            else ("Dallas", "CDR", 46655)
            if r[:2] == ("Dallas", "CDR")
            else None
            if r[:2] == ("Crew Life", "MET Testing")
            else ("GRC- (MCaRR-2)", "TRR", "9/20/2026 - 10/4/2026")
            if r[:2] == ("GRC- (MCaRR-2)", "TRR")
            else r
            for r in TWIN_ROWS
        )
        if row is not None
    ),
    ("Flight Manifests", "Boots 3", "12/1/2028"),
)


@pytest.fixture
def state() -> SessionState:
    st = SessionState()
    st.onepager_today = TODAY
    return st


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _upload(client: TestClient, data: bytes, slot: str, name: str) -> str:
    r = client.post(
        "/onepager-compare/upload",
        files={"file": (name, data, "application/octet-stream")},
        data={"slot": slot},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/onepager-compare"
    return client.get("/onepager-compare").text


def _both(client: TestClient) -> str:
    _upload(client, twin_xlsx(TWIN_ROWS), "prior", "March_baseline.xlsx")
    return _upload(client, twin_xlsx(CURRENT_ROWS), "current", "April_update.xlsx")


def _layout_block(page: str) -> dict:
    m = re.search(r'<script id=opcData type="application/json">(.*?)</script>', page, re.S)
    assert m, "the layout JSON block is missing"
    return json.loads(m.group(1))


def test_the_empty_page_offers_two_slots_the_rules_and_no_slide(client: TestClient) -> None:
    page = client.get("/onepager-compare").text
    assert "Drop two One-Pager lists" in page and "opcData" not in page
    for key in ("Prior", "Current"):
        assert (
            f"id=opcDrop{key}" in page and f"id=opcFile{key}" in page and f"id=opcForm{key}" in page
        )
    assert page.count("name=slot value=prior") == 1 and page.count("name=slot value=current") == 1
    assert 'class="cd-grid cd-grid-2 opc-slots"' in page and "id=opcHint" in page
    assert "How the two lists are matched" in page and "never inferred from a file name" in page
    assert "there is no threshold" in page and "one <b>REMOVED</b> and one <b>NEW</b>" in page
    assert 'href="/export/xlsx/onepager-template"' in page and "/static/onepager_compare.js" in page
    assert page.count("/static/panelkit.js") == 1


def test_one_list_is_not_a_comparison(client: TestClient) -> None:
    page = _upload(client, twin_xlsx(TWIN_ROWS), "prior", "March_baseline.xlsx")
    assert "Loaded 16 item(s) from March_baseline.xlsx as the PRIOR list; 1 row(s) skipped." in page
    assert "One list loaded" in page and "opcData" not in page
    # DELIBERATE re-baseline (ADR-0524): each slot also says what it read in column D
    assert (
        "Loaded <b>March_baseline.xlsx</b> · 16 item(s) · no column D · 1 row(s) skipped." in page
    )
    assert "Rows skipped in the PRIOR list" in page and "10/122/2026" in page
    assert client.get("/export/pptx/onepager-compare").status_code == 422
    assert client.get("/export/xlsx/onepager-compare").status_code == 422


def test_both_lists_draw_the_compare_slide_and_state_every_move(client: TestClient) -> None:
    page = _both(client)
    # DELIBERATE re-baseline (ADR-0524): the headline counts what did NOT slip too — the
    # operator's goal is "to show the slips as well as show what has not slipped"
    assert (
        "2 slipped, 1 pulled in, 12 unchanged, 1 new, 1 removed — March_baseline.xlsx → "
        "April_update.xlsx." in page
    )
    # two slips (Boots 1 +30, TRR +19): the takeaway names the larger one, with its unit
    assert "Worst slip: Boots 1 +30 cal d." in page
    assert "calendar days" in page  # the unit is on the lede
    lay = _layout_block(page)
    assert (
        lay["prior_source"] == "March_baseline.xlsx"
        and lay["current_source"] == "April_update.xlsx"
    )
    assert lay["title"] == "March baseline → April update" and lay["today_x"] is not None
    by_name = {(p["name"], p["status"]): p for p in lay["items"]}
    slip = by_name[("Boots 1", "slipped")]
    assert slip["delta"] == "+30 cal d" and slip["arrow_x1"] > slip["arrow_x0"]
    pull = by_name[("CDR", "pulled in")]
    assert pull["delta"] == "\u22127 cal d" and pull["arrow_x1"] < pull["arrow_x0"]
    assert by_name[("Boots 3", "new")]["badge"] == "NEW"
    assert by_name[("MET Testing", "removed")]["badge"] == "REMOVED"
    trr = by_name[("TRR", "slipped")]
    assert (
        trr["ghost_milestone"] is True and trr["milestone"] is False
    )  # a diamond ghost under a bar
    assert len(lay["summaries"]) == len(lay["lanes"]) == 7
    # the panel contract: export wired, ▦ DATA drawer with every compared row, provenance chip
    assert page.count('data-export="/export/xlsx/onepager-compare"') == 2
    assert "data-sf-data" in page and "<div class=sf-drawer hidden>" in page
    drawer = re.search(r"<div class=sf-drawer hidden>(.*?)</div>", page, re.S)
    assert drawer and drawer.group(1).count("<tr><td>") == len(lay["items"]) == 17
    assert "PRIOR: March_baseline.xlsx · CURRENT: April_update.xlsx · TODAY 2026-09-01" in page
    assert 'href="/export/pptx/onepager-compare"' in page
    # the type change and the intake's own decisions are on the page
    assert "a milestone in the prior sheet, an activity in the current" in page
    assert "Rows skipped in the PRIOR list" in page and "Rows skipped in the CURRENT list" in page


def test_every_figure_the_takeaway_quotes_is_a_cell_the_page_renders(client: TestClient) -> None:
    """The r10 rule: the counts are the Total row's cells, the worst slip a row's delta cell."""
    page = _both(client)
    take = re.search(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', page, re.S)
    assert take
    cells = set(re.findall(r"<t[dh][^>]*>([^<]*)</t[dh]>", page))
    quoted = re.sub(r"[A-Za-z_]+\.xlsx", "", take.group(1))
    for figure in re.findall(r"[+\u2212-]?\d+", quoted):
        assert figure in cells or figure.lstrip("+") in cells, (figure, take.group(1))
    # the summary table: one row per swimlane and the Total row with the same counts
    summary = re.search(
        r'<table class="op-table opc-summary-table sf-datatable">(.*?)</table>', page, re.S
    )
    assert summary and summary.group(1).count("<tr>") == 1 + 7 + 1  # header + 7 lanes + Total
    assert "<th>Total</th>" in summary.group(1)


def test_the_design_rows_hold_the_slide_the_summary_and_the_reading_block(
    client: TestClient,
) -> None:
    page = _both(client)
    markers = [
        '<h1 class="page-takeaway"',
        '<div class=panel data-export="/export/xlsx/onepager-compare">',
        "One-Pager compare",
        "id=opcHost",
        'id=opcData type="application/json"',
        '<div class="cd-grid cd-grid-12">',
        "Per-swimlane summary",
        '<section class="cd-block cd-read"><h2>How to read this</h2>',
        '<div class="cd-grid cd-grid-2 opc-slots">',
        "How the two lists are matched",
        "/static/onepager_compare.js",
    ]
    positions = [page.index(m) for m in markers]
    assert positions == sorted(positions), list(zip(markers, positions, strict=True))
    what, _how, why = _EXPLAINERS["One-Pager Compare"]
    assert f"<b>What it shows.</b> {what}" in page and f"<b>Why it matters.</b> {why}" in page
    # the slide and the summary are the page's ONLY panels — the slots and the rules are blocks
    assert len(re.findall(r"<div class=panel[ >]", page)) == 2


def test_the_powerpoint_export_is_the_same_slide_with_native_delta_shapes(
    client: TestClient,
) -> None:
    page = _both(client)
    lay = _layout_block(page)
    r = client.get("/export/pptx/onepager-compare")
    assert r.status_code == 200
    assert (
        r.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert r.headers[
        "content-disposition"
    ] == 'attachment; filename="March_baseline_→_April_update.pptx"'.replace("→", "_")
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        slide = zf.read("ppt/slides/slide1.xml").decode()
    ET.fromstring(slide)
    ghosts = sum(1 for p in lay["items"] if p["ghost_x0"] is not None)
    arrows = sum(1 for p in lay["items"] if p["arrow_x0"] is not None)
    assert slide.count('name="Prior activity: ') + slide.count('name="Prior milestone: ') == ghosts
    assert slide.count('name="Slip: ') + slide.count('name="Pull-in: ') == arrows == 3
    assert slide.count('name="Tag: NEW — ') == 1 and slide.count('name="Tag: REMOVED — ') == 1
    assert slide.count('name="Summary: ') == 7 and "+30 cal d" in slide and "\u22127 cal d" in slide
    # native encoding: every ghost is a DASHED outline with no fill, every arrow has a triangle
    # head, and the one pull-in (plus the legend's) is the flipped connector
    assert slide.count('<a:prstDash val="dash"/>') == ghosts + 2  # + the two legend ghosts
    assert slide.count('<a:tailEnd type="triangle" w="med" len="med"/>') == arrows + 2
    assert slide.count('flipH="1"') == 1 + 1  # CDR's pull-in + the legend's pull-in
    prior = re.search(
        r'<p:sp><p:nvSpPr><p:cNvPr id="\d+" name="Prior activity: [^"]*"/>.*?</p:sp>', slide
    )
    assert prior and "<a:noFill/>" in prior.group(0) and 'prstDash val="dash"' in prior.group(0)
    assert "Controlled Unclassified Information • CUI" in slide
    assert "Prior: March_baseline.xlsx · Current: April_update.xlsx" in slide


def test_the_excel_export_carries_prior_current_and_delta_columns(client: TestClient) -> None:
    _both(client)
    r = client.get("/export/xlsx/onepager-compare")
    assert (
        r.status_code == 200
        and 'filename="one-pager-compare.xlsx"' in r.headers["content-disposition"]
    )
    sheets = read_xlsx(r.content)
    items = next(rows for name, rows in sheets.items() if "Compared" in name)
    header = next(row for row in items if row and row[0] == "Swimlane")
    assert "Finish delta (calendar days)" in header and "Current finish" in header
    boots = next(row for row in items if len(row) > 1 and row[1] == "Boots 1")
    assert boots[header.index("Finish delta (calendar days)")] == "30"
    assert any("summary" in name.lower() for name in sheets)
    assert client.get("/export/docx/onepager-compare").status_code == 200
    assert client.get("/export/pdf/onepager-compare").status_code == 404


def test_swap_title_and_clear(client: TestClient) -> None:
    _both(client)
    r = client.post("/onepager-compare/swap", follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/onepager-compare").text
    assert "Prior and current swapped." in page
    # what was a slip is now a pull-in, by the same figure
    assert (
        "1 slipped, 2 pulled in, 12 unchanged, 1 new, 1 removed — April_update.xlsx → "
        "March_baseline.xlsx." in page
    )
    lay = _layout_block(page)
    assert {(p["name"], p["status"]) for p in lay["items"]} >= {
        ("Boots 1", "pulled in"),
        ("CDR", "slipped"),
        ("Boots 3", "removed"),
        ("MET Testing", "new"),
    }
    r = client.post(
        "/onepager-compare/title",
        data={"title": "  Where the month went  "},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get("/onepager-compare").text
    assert _layout_block(page)["title"] == "Where the month went"
    pptx = client.get("/export/pptx/onepager-compare")
    assert 'filename="Where_the_month_went.pptx"' in pptx.headers["content-disposition"]
    assert client.post("/onepager-compare/clear", follow_redirects=False).status_code == 303
    page = client.get("/onepager-compare").text
    assert "Both lists cleared." in page and "Drop two One-Pager lists" in page
    assert "opcData" not in page and page.count("Nothing loaded yet.") == 2


def test_a_bad_file_an_unknown_slot_and_the_cap_are_refused_by_name(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = _upload(client, b"not a workbook", "current", "notes.xlsx")
    assert "Could not read that file" in page and "role=alert" in page
    r = client.post(
        "/onepager-compare/upload",
        files={"file": ("x.xlsx", twin_xlsx(TWIN_ROWS), "application/octet-stream")},
        data={"slot": "middle"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get("/onepager-compare").text
    assert "Unknown slot “middle”" in page and "role=alert" in page and "opcData" not in page
    import schedule_forensics.web.app as app_mod

    monkeypatch.setattr(app_mod, "_MAX_UPLOAD_BYTES", 64)
    page = _upload(client, twin_xlsx(TWIN_ROWS), "prior", "big.xlsx")
    assert "exceeds the 0 MB cap" in page and "Nothing loaded yet." in page


def test_operator_text_never_becomes_markup(client: TestClient) -> None:
    hostile = (
        ("Swimlane Name", "Task", "Date"),
        ("<b>Lane</b> & co", "<script>alert(1)</script>", "1/1/2027 - 2/1/2027"),
    )
    later = (
        ("Swimlane Name", "Task", "Date"),
        ("<b>Lane</b> & co", "<script>alert(1)</script>", "1/1/2027 - 3/1/2027"),
        ("<b>Lane</b> & co", "<img src=x onerror=alert(2)>", "3/1/2027"),
    )
    _upload(client, twin_xlsx(hostile), "prior", "p<y>&z.xlsx")
    page = _upload(client, twin_xlsx(later), "current", "c<y>&z.xlsx")
    assert "<script>alert(1)" not in page and "<img src=x" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    lay = _layout_block(page)
    assert {p["name"] for p in lay["items"]} == {
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(2)>",
    }
    assert "\\u003c" in re.search(
        r'id=opcData type="application/json">(.*?)</script>', page, re.S
    ).group(1)
    pptx = client.get("/export/pptx/onepager-compare")
    assert pptx.status_code == 200
    with zipfile.ZipFile(io.BytesIO(pptx.content)) as zf:
        ET.fromstring(zf.read("ppt/slides/slide1.xml"))


def test_the_nav_carries_the_page_on_the_library_rail(client: TestClient) -> None:
    home = client.get("/").text
    assert 'href="/onepager-compare"' in home and "One-Pager Compare" in home
    for lang in ("es", "fr", "de", "pt"):
        cat = catalog_for(lang)
        for term in ("One-Pager Compare", "Per-swimlane summary", "Swap prior and current"):
            assert term in cat, (lang, term)


# ── round two (ADR-0524): column D, a repeated name, the true sheet row, the words on the page ─

#: A four-column pair, written the way Excel writes it (the spacer row between the swimlanes is
#: ABSENT from the file, so every Beta row sits on a later Excel row than its position).
PRIOR_D: tuple[tuple[object, ...], ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Design Review", "5/15/2027", "Not Started"),
    ("Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"),
    (),
    ("Beta", "Reopened", "2/10/2027", "Complete"),
    ("Beta", "Dropped", "1/20/2027", "Complete"),
)
CURRENT_D: tuple[tuple[object, ...], ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Design Review", "5/15/2027", "In Progress"),
    ("Alpha", "Build", "2/1/2027 - 4/20/2027", "Complete"),
    (),
    ("Beta", "Reopened", "2/10/2027", "In Progress"),
    ("Beta", "Brand new", "5/1/2027", "Waiting on vendor"),
)


def _both_d(client: TestClient) -> str:
    _upload(client, twin_xlsx(PRIOR_D, omit_blank=True), "prior", "prior_d.xlsx")
    return _upload(client, twin_xlsx(CURRENT_D, omit_blank=True), "current", "current_d.xlsx")


def test_a_repeated_name_that_did_not_move_is_drawn_once_with_no_duplicate_tag(
    client: TestClient,
) -> None:
    page = _both_d(client)
    lay = _layout_block(page)
    reviews = [p for p in lay["items"] if p["name"] == "Design Review"]
    assert len(reviews) == 2 and {p["status"] for p in reviews} == {"unchanged"}
    assert all(p["badge"] == "" and p["ghost_x0"] is None for p in reviews)
    assert "DUPLICATE NAME" not in json.dumps(lay) and "Duplicate names" not in page


def test_column_d_is_counted_checked_flagged_and_its_unread_words_named(
    client: TestClient,
) -> None:
    page = _both_d(client)
    assert (
        "1 slipped, 0 pulled in, 3 unchanged, 1 new, 1 removed — prior_d.xlsx → "
        "current_d.xlsx. Worst slip: Build +19 cal d. 2 marked complete in column D." in page
    )
    lay = _layout_block(page)
    assert sorted(p["name"] for p in lay["items"] if p["done"]) == ["Build", "Design Review"]
    assert [e["kind"] for e in lay["legend"]].count("done") == 1
    # the summary table and the drawer carry column D; the takeaway's count is the Total cell
    summary = re.search(
        r'<table class="op-table opc-summary-table sf-datatable">(.*?)</table>', page, re.S
    )
    assert summary and "<th>Complete</th>" in summary.group(1)
    total = re.search(r"<tr><th>Total</th>(.*?)</tr>", summary.group(1), re.S)
    assert total and re.findall(r"<td[^>]*>([^<]*)</td>", total.group(1))[7] == "2"
    assert "<th>Prior complete</th>" in page and "<th>Current complete</th>" in page
    # a completion that went backwards is flagged; a word column D could not read is named;
    # a complete item that dropped off the list is named
    assert "Completion changes between the lists" in page
    assert "Reopened): marked complete in the prior list, not complete in the current" in page
    assert "current_d.xlsx: column D “Waiting on vendor” (row 7)" in page
    assert "marked complete in the prior list are not in the current list: “Dropped”" in page
    # each slot says what it read in column D
    assert "Loaded <b>prior_d.xlsx</b> · 5 item(s) · column D: 3 complete." in page
    assert "Loaded <b>current_d.xlsx</b> · 5 item(s) · column D: 2 complete." in page


def test_every_row_the_page_cites_is_the_row_excel_shows(client: TestClient) -> None:
    """Excel leaves the blank spacer out of the file; the drawer must still say row 6."""
    page = _both_d(client)
    drawer = re.search(r"<div class=sf-drawer hidden>(.*?)</div>", page, re.S)
    assert drawer
    reopened = next(tr for tr in drawer.group(1).split("<tr>") if ">Reopened<" in tr)
    cells = re.findall(r"<td[^>]*>([^<]*)</td>", reopened)
    assert cells[9:11] == ["6", "6"], cells  # prior row, current row


def test_a_three_column_list_says_it_has_no_column_d(client: TestClient) -> None:
    page = _both(client)
    assert (
        "Loaded <b>March_baseline.xlsx</b> · 16 item(s) · no column D · 1 row(s) skipped." in page
    )
    assert "marked complete in column D" not in page
    assert "done" not in [e["kind"] for e in _layout_block(page)["legend"]]


def test_column_d_never_reaches_the_single_list_page(client: TestClient) -> None:
    """/onepager draws no completion, so a sentence about column D would describe nothing it
    shows — the notes travel apart (``completion_notes``)."""
    r = client.post(
        "/onepager/upload",
        files={"file": ("d.xlsx", twin_xlsx(CURRENT_D, omit_blank=True), "application/x")},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get("/onepager").text
    assert "Waiting on vendor" not in page and "column D" not in page
    assert 'id=opData type="application/json"' in page


def test_the_words_on_the_page_describe_the_new_rules(client: TestClient) -> None:
    empty = client.get("/onepager-compare").text
    assert "an identical date in both lists" in empty and "drawn once" in empty
    assert "never paired by elimination" in empty
    assert "<b>Column D.</b>" in empty and "Complete, Completed, Done, Finished" in empty
    assert "optional <b>D</b>" in empty  # the intake text names the fourth column
    _what, how, _why = _EXPLAINERS["One-Pager Compare"]
    assert "a solid shape with no ghost is NEW" not in how  # ADR-0465's sentence, now false
    assert "an unchanged item is drawn once" in how and "check" in how
    page = _both(client)
    assert f"<b>How to read it.</b> {how}" in page


def test_the_powerpoint_check_is_a_disc_and_two_round_capped_strokes(
    client: TestClient,
) -> None:
    page = _both_d(client)
    lay = _layout_block(page)
    done = sorted(p["name"] for p in lay["items"] if p["done"])
    r = client.get("/export/pptx/onepager-compare")
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        slide = zf.read("ppt/slides/slide1.xml").decode()
    ET.fromstring(slide)
    assert sorted(re.findall(r'name="Done: ([^"]*)"', slide)) == done
    assert slide.count('name="Done tick: ') == 2 * len(done) + 2  # + the legend's check
    # one rising stroke per check (the legend's included) — flipped VERTICALLY, never flipH,
    # drawn with round caps and a round join so the check has no notch at its vertex
    assert slide.count('flipV="1"') == len(done) + 1
    assert slide.count('flipH="1"') == 1  # the legend's pull-in only (this pair has no pull-in)
    tick = re.search(
        r'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="\d+" name="Done tick: .*?</p:cxnSp>', slide
    )
    assert tick and 'cap="rnd"' in tick.group(0) and "<a:round/>" in tick.group(0)
    assert "<a:tailEnd" not in tick.group(0)
    legend = re.search(
        r'<p:sp><p:nvSpPr><p:cNvPr id="\d+" name="Legend: complete"/>.*?</p:sp>', slide
    )
    assert legend and 'prst="ellipse"' in legend.group(0)
