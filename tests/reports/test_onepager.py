"""The One-Pager intake, layout and PowerPoint export (ADR-0446).

Three subjects, one oracle discipline. The **parser** is tested against every hand-typed date
form the operator's own workbook carried (two-digit years, month-only ranges, an Excel serial in
a General cell, a genuine typo) — the workbook itself is not committed; a synthetic twin is built
in-test with ``zipfile`` so the shared-strings path ``read_xlsx`` takes on a real Excel file is
the path under test. The **layout** is checked for the two things a slide must never do — overflow
its page or draw two things on top of each other — by re-deriving both from the geometry rather
than trusting flags. The **.pptx** is read back with the standard library's own XML parser (a
different code path from the writer) and every shape's EMU geometry is compared to the layout
that produced it; a teeth test proves that comparison fails when the writer's unit is wrong.
"""

from __future__ import annotations

import datetime as dt
import io
import xml.etree.ElementTree as ET
import zipfile
from itertools import pairwise

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import pptx as pp
from schedule_forensics.reports.onepager import (
    OnePagerDoc,
    OnePagerItem,
    build_layout,
    layout_json,
    onepager_tableset,
    parse_date,
    parse_rows,
    parse_span,
    parse_workbook,
)
from schedule_forensics.reports.pptx import render_onepager_pptx
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.reports.xlsx_read import read_xlsx
from web.onepager_twin import TWIN_ROWS, twin_xlsx

TODAY = dt.date(2026, 9, 1)


@pytest.fixture(scope="module")
def twin() -> OnePagerDoc:
    return parse_workbook(read_xlsx(twin_xlsx(TWIN_ROWS)), "twin.xlsx")


# ── the parser ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("04/20/2027 - 06/20/2027", (dt.date(2027, 4, 20), dt.date(2027, 6, 20))),
        ("12/1/2026 - 4/15/27", (dt.date(2026, 12, 1), dt.date(2027, 4, 15))),
        ("06/10/26 - 06/22/28", (dt.date(2026, 6, 10), dt.date(2028, 6, 22))),
        ("05/2026 - 11/2026", (dt.date(2026, 5, 1), dt.date(2026, 11, 30))),
        ("9/18/25 - 3/20/27", (dt.date(2025, 9, 18), dt.date(2027, 3, 20))),
        ("11/4/2026 - 12/12/26", (dt.date(2026, 11, 4), dt.date(2026, 12, 12))),
        ("46310", (dt.date(2026, 10, 15), dt.date(2026, 10, 15))),
        ("46564.0", (dt.date(2027, 6, 26), dt.date(2027, 6, 26))),
        ("2027-06-27", (dt.date(2027, 6, 27), dt.date(2027, 6, 27))),
        ("1-Jan-27 \u2013 5-Feb-27", (dt.date(2027, 1, 1), dt.date(2027, 2, 5))),
        ("1/1/27-2/2/27", (dt.date(2027, 1, 1), dt.date(2027, 2, 2))),
        ("Jan 2027", (dt.date(2027, 1, 1), dt.date(2027, 1, 31))),
        ("12/2026", (dt.date(2026, 12, 1), dt.date(2026, 12, 31))),
        ("3/1/2027 to 4/1/2027", (dt.date(2027, 3, 1), dt.date(2027, 4, 1))),
    ],
)
def test_every_hand_typed_date_form_in_the_field_workbook_parses(
    text: str, expected: tuple[dt.date, dt.date]
) -> None:
    assert parse_span(text) == expected


@pytest.mark.parametrize(
    "text", ["10/122/2026", "TBD", "", "12", "1/1/27 - TBD", "2/30/2027", "13/2026"]
)
def test_a_non_date_is_none_never_a_default(text: str) -> None:
    assert parse_span(text) is None
    assert parse_date(text) is None


def test_a_bare_number_outside_the_serial_range_is_not_a_date() -> None:
    assert parse_date("12345") is None  # 1933 — a count, not a date
    assert parse_date("99999") is None


def test_the_twin_workbook_parses_like_the_field_one(twin: OnePagerDoc) -> None:
    assert twin.sheet == "Sheet1" and twin.source == "twin.xlsx"
    assert len(twin.items) == 16
    assert sum(i.milestone for i in twin.items) == 6
    # the typo row is skipped AND named — never a default date
    assert len(twin.problems) == 1
    assert "row 23" in twin.problems[0] and "10/122/2026" in twin.problems[0]
    assert "Blue Origin On-Dock" in twin.problems[0]
    # the row with no swimlane inherits the one above it, and says so
    assert any("row 25" in n and "GRC-MET Testing" in n for n in twin.notes)
    inherited = next(i for i in twin.items if i.name == "MET ATP for Hot-Fire")
    assert inherited.lane == "GRC-MET Testing" and inherited.start == dt.date(2027, 1, 25)
    # a real Excel date cell and a serial typed into a General cell both arrive as serials
    assert next(i for i in twin.items if i.name == "Boots 1").start == dt.date(2027, 6, 27)
    assert next(i for i in twin.items if i.name == "MET On-Dock").start == dt.date(2026, 10, 15)
    # the header row is not an item
    assert not any(i.name == "Task" for i in twin.items)


def test_swapped_dates_are_kept_and_named() -> None:
    items, problems, notes = parse_rows([["Lane", "Backwards", "6/1/27 - 1/1/27"]])
    assert not problems and items[0].start == dt.date(2027, 1, 1)
    assert items[0].finish == dt.date(2027, 6, 1)
    assert "swapped" in notes[0]


def test_a_workbook_with_no_content_is_a_named_problem_not_a_crash() -> None:
    doc = parse_workbook({"Sheet1": [["", ""], []]}, "empty.xlsx")
    assert doc.items == () and doc.problems == ("the workbook has no rows",)


# ── the layout ────────────────────────────────────────────────────────────────────────────────


def _extents(lay: op.Layout) -> dict[tuple[int, int], list[tuple[float, float]]]:
    """Each placed item's horizontal extent (shape + label) re-derived from the geometry."""
    out: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for p in lay.items:
        half = lay.ms / 2 if p.milestone else 0.0
        left, right = p.x0 - half, max(p.x1, p.x0 + half)
        if p.inside:
            ext = (left, right)
        elif p.label_anchor == "start":
            ext = (left, max(right, p.label_x + p.label_w))
        else:
            ext = (min(left, p.label_x - p.label_w), right)
        out.setdefault((p.lane, p.row), []).append(ext)
    return out


def test_the_layout_merges_spacing_variants_and_keeps_first_seen_order(twin: OnePagerDoc) -> None:
    lay = build_layout(twin.items, TODAY, "Twin")
    assert [ln.name for ln in lay.lanes] == [
        "Flight Manifests",
        "Dallas",
        "Crew Life",
        "BobbySon",
        "GRC-Blue RR-6",
        "GRC- (MCaRR-2)",
        "GRC-MET Testing",
    ]
    merged = next(ln for ln in lay.lanes if ln.name == "GRC- (MCaRR-2)")
    assert merged.merged_from == ["GRC-(MCaRR-2)"]
    assert any("GRC-(MCaRR-2)" in n and "merged" in n for n in lay.notes)


def test_nothing_overlaps_in_a_row_and_the_slide_is_not_overflowed(twin: OnePagerDoc) -> None:
    lay = build_layout(twin.items, TODAY, "Twin")
    assert lay.lanes_y1 <= op.LANES_Y1 + 0.01
    for (lane, row), exts in _extents(lay).items():
        exts.sort()
        for (_, a1), (b0, _) in pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap"
    # every item lands inside its own lane band
    for p in lay.items:
        ln = lay.lanes[p.lane]
        assert ln.y0 < p.y < ln.y1


def _simultaneous(lanes: int, per_lane: int) -> list[OnePagerItem]:
    """``per_lane`` activities per lane that all overlap in time, so each needs its own row."""
    return [
        OnePagerItem(
            f"Lane {i % lanes}",
            f"Activity number {i} with a long descriptive name",
            TODAY + dt.timedelta(days=i % per_lane),
            TODAY + dt.timedelta(days=60 + i % per_lane),
            i,
        )
        for i in range(lanes * per_lane)
    ]


def _assert_no_row_overlaps(lay: op.Layout) -> None:
    for (lane, row), exts in _extents(lay).items():
        exts.sort()
        for (_, a1), (b0, _) in pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap"


def test_a_dense_list_steps_the_floors_down_and_says_so() -> None:
    lay = build_layout(_simultaneous(8, 8), TODAY, "Dense")  # 64 rows: past the first floor
    assert lay.lanes_y1 <= op.LANES_Y1 + 0.01
    assert op.FLOORS[-1][0] <= lay.row_h < op.FLOORS[0][0]
    assert sum(ln.rows for ln in lay.lanes) == 64
    assert any(n.startswith("Dense one-pager") for n in lay.notes)
    _assert_no_row_overlaps(lay)


def test_past_the_last_floor_it_is_still_one_slide_and_says_to_split_the_list() -> None:
    lay = build_layout(_simultaneous(8, 12), TODAY, "Extreme")  # 96 rows: past every floor
    assert lay.lanes_y1 <= op.LANES_Y1 + 0.01
    assert op.EMERGENCY[0] <= lay.row_h < op.FLOORS[-1][0]
    assert any("Extremely dense" in n and "splitting" in n for n in lay.notes)
    _assert_no_row_overlaps(lay)
    beyond = build_layout(_simultaneous(8, 16), TODAY, "Beyond")  # 128 rows: nothing fits
    assert beyond.lanes_y1 > op.LANES_Y1
    assert any("does not fit one slide" in n and "Split the list" in n for n in beyond.notes)


def test_today_is_drawn_when_near_the_data_and_named_when_not(twin: OnePagerDoc) -> None:
    near = build_layout(twin.items, TODAY, "Twin")
    assert near.today_x is not None and near.x0 <= near.today_x <= near.x1
    assert near.today_label == "TODAY 9/1/26" and near.today_note == ""
    far = build_layout(twin.items, dt.date(2040, 1, 1), "Twin")
    assert far.today_x is None and "outside the plotted window" in far.today_note
    # a today at the far right flips its caption to the left of the line
    late = build_layout(twin.items, dt.date(2028, 8, 1), "Twin")
    assert late.today_label_anchor == "end" and late.today_label_x < late.today_x


def test_the_header_is_whole_months_with_a_dotted_line_each(twin: OnePagerDoc) -> None:
    lay = build_layout(twin.items, TODAY, "Twin")
    assert lay.t0 == "2025-09-01" and lay.t1 == "2028-08-01"  # window padded to whole months
    assert len(lay.months) == 35 and [b.label for b in lay.years] == [
        "2025",
        "2026",
        "2027",
        "2028",
    ]
    assert lay.months[0].x == lay.x0 and lay.years[-1].x1 == pytest.approx(lay.x1)
    assert all(m.label for m in lay.months)  # 23 pt per month: single letters


def test_labels_carry_the_name_and_the_finish_date(twin: OnePagerDoc) -> None:
    lay = build_layout(twin.items, TODAY, "Twin")
    campaign = next(p for p in lay.items if p.name == "Uncrewed Lander Campaign")
    assert campaign.label == "Uncrewed Lander Campaign (6/20/27)" and not campaign.milestone
    cdr = next(p for p in lay.items if p.name == "CDR")
    assert cdr.label == "CDR (10/2/27)" and cdr.milestone and cdr.x0 == cdr.x1


def test_the_legend_lists_the_three_symbols_then_every_swimlane(twin: OnePagerDoc) -> None:
    lay = build_layout(twin.items, TODAY, "Twin")
    kinds = [e.kind for e in lay.legend]
    assert kinds[:3] == ["activity", "milestone", "today"] and kinds.count("lane") == len(lay.lanes)
    assert len({e.y for e in lay.legend}) <= 2 and all(
        e.x + e.w <= lay.x1 + 0.01 for e in lay.legend
    )


def test_layout_json_is_plain_data_the_page_can_embed(twin: OnePagerDoc) -> None:
    import json

    lay = build_layout(twin.items, TODAY, "Twin <b>")
    blob = json.dumps(layout_json(lay))
    back = json.loads(blob)
    assert (
        back["title"] == "Twin <b>"
        and len(back["items"]) == 16
        and back["today_iso"] == "2026-09-01"
    )


def test_nothing_to_lay_out_is_an_error_not_an_empty_slide() -> None:
    with pytest.raises(ValueError):
        build_layout([], TODAY, "Empty")


# ── the Excel side ────────────────────────────────────────────────────────────────────────────


def test_the_excel_export_round_trips_through_the_tool_s_own_reader(twin: OnePagerDoc) -> None:
    sheets = read_xlsx(render_xlsx(onepager_tableset(twin)))
    items_sheet = next(rows for name, rows in sheets.items() if "items" in name.lower())
    body = [r for r in items_sheet if r and r[0] not in ("Swimlane", "")]
    assert len([r for r in body if len(r) >= 6 and r[3] and r[3][:2] == "20"]) == 16
    skipped = next(rows for name, rows in sheets.items() if "Skipped" in name)
    assert any("10/122/2026" in cell for row in skipped for cell in row)


# ── the PowerPoint export ─────────────────────────────────────────────────────────────────────

_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
EMU = 12700


def _shapes(data: bytes) -> list[ET.Element]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        root = ET.fromstring(zf.read("ppt/slides/slide1.xml"))
    tree = root.find(f"{_P}cSld/{_P}spTree")
    assert tree is not None
    return [el for el in tree if el.tag in (f"{_P}sp", f"{_P}cxnSp")]


def _name(el: ET.Element) -> str:
    c = el.find(f".//{_P}cNvPr")
    return c.get("name", "") if c is not None else ""


def _xfrm(el: ET.Element) -> tuple[int, int, int, int]:
    off = el.find(f".//{_A}xfrm/{_A}off")
    ext = el.find(f".//{_A}xfrm/{_A}ext")
    assert off is not None and ext is not None
    return int(off.get("x", 0)), int(off.get("y", 0)), int(ext.get("cx", 0)), int(ext.get("cy", 0))


def _text(el: ET.Element) -> str:
    return "".join(t.text or "" for t in el.iter(f"{_A}t"))


@pytest.fixture(scope="module")
def deck(twin: OnePagerDoc) -> tuple[op.Layout, bytes]:
    lay = build_layout(twin.items, TODAY, "Twin One-Pager", "Prepared today")
    return lay, render_onepager_pptx(
        lay, marking="Controlled Unclassified Information • CUI", source="Source: twin.xlsx"
    )


def test_the_package_has_every_part_and_every_part_is_well_formed(
    deck: tuple[op.Layout, bytes],
) -> None:
    _, data = deck
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert names[0] == "[Content_Types].xml"
        for part in (
            "ppt/presentation.xml",
            "ppt/slides/slide1.xml",
            "ppt/slideMasters/slideMaster1.xml",
            "ppt/slideLayouts/slideLayout1.xml",
            "ppt/theme/theme1.xml",
            "ppt/_rels/presentation.xml.rels",
            "ppt/slides/_rels/slide1.xml.rels",
        ):
            assert part in names
            ET.fromstring(zf.read(part))  # well-formed, or this raises
        ct = zf.read("[Content_Types].xml").decode()
        assert "presentationml.presentation.main+xml" in ct and "/ppt/slides/slide1.xml" in ct
        pres = ET.fromstring(zf.read("ppt/presentation.xml"))
        size = pres.find(f"{_P}sldSz")
        assert size is not None and (size.get("cx"), size.get("cy")) == ("12192000", "6858000")


def test_every_layout_element_is_a_named_native_shape(deck: tuple[op.Layout, bytes]) -> None:
    lay, data = deck
    names = [_name(s) for s in _shapes(data)]
    assert sum(n.startswith("Activity: ") for n in names) == sum(not p.milestone for p in lay.items)
    assert sum(n.startswith("Milestone: ") for n in names) == sum(p.milestone for p in lay.items)
    assert sum(n.startswith("Label: ") for n in names) == len(lay.items)
    assert sum(n.startswith("Month line") for n in names) == len(lay.months)
    assert sum(n.startswith("Lane name: ") for n in names) == len(lay.lanes)
    assert sum(n.startswith("Year band") for n in names) == len(lay.years)
    assert names.count("Today") == 1 and names.count("Today label") == 1
    assert sum(n.startswith("Legend") for n in names) >= 2 * len(lay.legend)
    assert names.count("CUI marking (top)") == 1 and names.count("CUI marking (bottom)") == 1


def test_shape_geometry_is_the_layout_in_emu(deck: tuple[op.Layout, bytes]) -> None:
    lay, data = deck
    by_name = {_name(s): s for s in _shapes(data)}
    for p in lay.items:
        if p.milestone:
            x, y, cx, cy = _xfrm(by_name[f"Milestone: {p.name}"])
            assert (x, y) == (round((p.x0 - lay.ms / 2) * EMU), round((p.y - lay.ms / 2) * EMU))
            assert (cx, cy) == (round(lay.ms * EMU), round(lay.ms * EMU))
        else:
            x, y, cx, cy = _xfrm(by_name[f"Activity: {p.name}"])
            assert (x, cx) == (round(p.x0 * EMU), round((p.x1 - p.x0) * EMU))
            assert (y, cy) == (round((p.y - lay.bar_h / 2) * EMU), round(lay.bar_h * EMU))
        assert _text(by_name[f"Label: {p.name}"]) == p.label
    assert lay.today_x is not None
    tx, ty, _tcx, tcy = _xfrm(by_name["Today"])
    assert (tx, ty, tcy) == (
        round(lay.today_x * EMU),
        round(lay.year_y0 * EMU),
        round((lay.lanes_y1 - lay.year_y0) * EMU),
    )


def test_presets_dashes_and_colours_match_the_one_pager_language(
    deck: tuple[op.Layout, bytes],
) -> None:
    lay, data = deck
    by_name = {_name(s): s for s in _shapes(data)}
    act = next(s for n, s in by_name.items() if n.startswith("Activity: "))
    ms = next(s for n, s in by_name.items() if n.startswith("Milestone: "))
    assert act.find(f".//{_A}prstGeom").get("prst") == "roundRect"
    assert ms.find(f".//{_A}prstGeom").get("prst") == "diamond"
    month = next(s for n, s in by_name.items() if n.startswith("Month line"))
    assert month.find(f".//{_A}ln/{_A}prstDash").get("val") == "sysDot"
    today = by_name["Today"]
    assert today.find(f".//{_A}ln/{_A}solidFill/{_A}srgbClr").get("val") == "C00000"
    assert today.find(f".//{_A}ln").get("w") == str(round(1.5 * EMU))
    assert (
        _text(by_name["Title"]) == "Twin One-Pager"
        and _text(by_name["Subtitle"]) == "Prepared today"
    )
    assert _text(by_name["CUI marking (top)"]) == "Controlled Unclassified Information • CUI"
    lane_fill = (
        by_name[f"Lane: {lay.lanes[0].name}"].find(f".//{_A}solidFill/{_A}srgbClr").get("val")
    )
    assert lane_fill == pp.tint(pp.LANE_PALETTE[0], 0.07)


def test_operator_text_is_escaped_in_the_slide_xml() -> None:
    items = [
        OnePagerItem(
            "A & B <lane>",
            "Task <script>alert(1)</script> & co",
            TODAY,
            TODAY + dt.timedelta(days=30),
            3,
        )
    ]
    lay = build_layout(items, TODAY, "Title <b>&</b>")
    data = render_onepager_pptx(lay, marking="M", source="S")
    shapes = _shapes(data)  # parses — an unescaped '<' would have broken the XML
    assert any(_text(s) == "Task <script>alert(1)</script> & co (10/1/26)" for s in shapes)
    assert any(_name(s) == "Lane: A & B <lane>" for s in shapes)


def test_the_export_is_byte_deterministic(deck: tuple[op.Layout, bytes]) -> None:
    lay, data = deck
    assert (
        render_onepager_pptx(
            lay, marking="Controlled Unclassified Information • CUI", source="Source: twin.xlsx"
        )
        == data
    )


def test_the_geometry_oracle_has_teeth(
    deck: tuple[op.Layout, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation: a writer whose unit is one EMU off must fail the geometry read-back by name."""
    lay, _ = deck
    monkeypatch.setattr(pp, "_EMU_PER_PT", EMU + 1)
    wrong = render_onepager_pptx(lay, marking="M", source="S")
    by_name = {_name(s): s for s in _shapes(wrong)}
    p = next(p for p in lay.items if not p.milestone)
    x, _y, _cx, _cy = _xfrm(by_name[f"Activity: {p.name}"])
    assert x != round(p.x0 * EMU), "the read-back cannot tell a mis-scaled slide from a right one"
