"""The One-Pager COMPARE engine: two three-column lists matched on the only key the sheet carries.

Operator request (2026-09-04): drop TWO One-Pager sheets and make it perfectly clear which tasks
slipped and by how much. The ADR-0446 intake carries NO unique id and NO calendar, so the engine
under test here (a) matches rows on the normalised ``(swimlane, item)`` pair and reports an
unmatched row as NEW or REMOVED by name — a rename is one removed plus one new, a swimlane move
the same — and (b) measures every move in CALENDAR days, the only unit the sheet can support.

Red-first (2026-09-05): this module was written before ``reports/onepager_compare.py`` existed
and observed to fail at import; each assertion below then went green only when the engine did
the thing it names. The mutation battery (see the ADR) breaks each rule by name.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.reports.onepager import OnePagerDoc, parse_rows
from schedule_forensics.reports.onepager_compare import (
    ADDED,
    AMBIGUOUS,
    PULLED_IN,
    REMOVED,
    SLIPPED,
    START_MOVED,
    UNCHANGED,
    CompareDoc,
    compare_onepager_docs,
    item_key,
)

#: The synthetic PRIOR sheet — every case the request names, one row each, plus the ones the
#: intake's own quirks force (a spacing-variant spelling, a swimlane move).
PRIOR_ROWS = [
    ["Swimlane Name", "Task", "Date"],
    ["Lane A", "Slips", "1/10/2027 - 3/1/2027"],
    ["Lane A", "Pulls in", "2/1/2027 - 6/30/2027"],
    ["Lane A", "Steady", "4/1/2027 - 5/1/2027"],
    ["Lane A", "Starts later", "5/1/2027 - 8/1/2027"],
    ["Lane A", "Old name", "7/7/2027"],
    ["Lane B", "Was a milestone", "9/9/2027"],
    ["Lane B", "Gone", "10/1/2027"],
    ["Lane B", "Twin", "11/1/2027"],
    ["Lane B", "Twin", "11/5/2027"],
    ["Lane B", "Moves lane", "12/1/2027"],
    ["Lane  A", "spaced  spelling", "1/1/2028"],
]
CURRENT_ROWS = [
    ["Swimlane Name", "Task", "Date"],
    ["Lane A", "Slips", "1/10/2027 - 3/31/2027"],
    ["Lane A", "Pulls in", "2/1/2027 - 6/15/2027"],
    ["Lane A", "Steady", "4/1/2027 - 5/1/2027"],
    ["Lane A", "Starts later", "5/15/2027 - 8/1/2027"],
    ["Lane A", "New name", "7/7/2027"],
    ["Lane A", "Brand new", "8/8/2027"],
    ["Lane B", "Was a milestone", "9/1/2027 - 9/30/2027"],
    ["Lane B", "Twin", "11/3/2027"],
    ["Lane C", "Moves lane", "12/1/2027"],
    ["Lane A", "Spaced Spelling", "1/1/2028"],
]


def _doc(rows: list[list[str]], source: str) -> OnePagerDoc:
    items, problems, notes = parse_rows(rows)
    return OnePagerDoc(source, "Sheet1", tuple(items), tuple(problems), tuple(notes))


@pytest.fixture(scope="module")
def pair() -> CompareDoc:
    return compare_onepager_docs(_doc(PRIOR_ROWS, "prior.xlsx"), _doc(CURRENT_ROWS, "current.xlsx"))


def _row(doc: CompareDoc, name: str, lane: str | None = None) -> object:
    hits = [r for r in doc.rows if r.name == name and (lane is None or r.lane == lane)]
    assert len(hits) == 1, (name, lane, [(r.lane, r.name, r.status) for r in hits])
    return hits[0]


# ── the key ───────────────────────────────────────────────────────────────────────────────────


def test_the_match_key_is_the_lane_merge_key_and_the_whitespace_collapsed_casefolded_name() -> None:
    assert item_key("Lane  A", "spaced  spelling") == item_key("Lane A", "Spaced Spelling")
    assert item_key("Lane A", "Twin") != item_key("Lane B", "Twin")  # the lane is part of the key
    assert item_key("Lane A", "Boots 1") != item_key("Lane A", "Boots 2")


# ── the statuses, one row each ────────────────────────────────────────────────────────────────


def test_a_later_finish_is_a_slip_measured_in_calendar_days(pair: CompareDoc) -> None:
    r = _row(pair, "Slips")
    assert r.status == SLIPPED
    assert (r.prior_finish, r.current_finish) == (dt.date(2027, 3, 1), dt.date(2027, 3, 31))
    assert r.finish_delta_days == 30 and r.start_delta_days == 0  # 3/1 -> 3/31 is 30 CALENDAR days
    assert (r.prior_row, r.current_row) == (2, 2)


def test_an_earlier_finish_is_a_pull_in_with_a_negative_delta(pair: CompareDoc) -> None:
    r = _row(pair, "Pulls in")
    assert r.status == PULLED_IN and r.finish_delta_days == -15 and r.start_delta_days == 0


def test_identical_dates_read_unchanged(pair: CompareDoc) -> None:
    r = _row(pair, "Steady")
    assert r.status == UNCHANGED and (r.start_delta_days, r.finish_delta_days) == (0, 0)


def test_a_start_that_moves_under_a_fixed_finish_is_its_own_status(pair: CompareDoc) -> None:
    r = _row(pair, "Starts later")
    assert r.status == START_MOVED and r.start_delta_days == 14 and r.finish_delta_days == 0


def test_a_rename_is_one_removed_and_one_new_never_a_guess(pair: CompareDoc) -> None:
    old, new = _row(pair, "Old name"), _row(pair, "New name")
    assert old.status == REMOVED and old.current_row is None and old.current_finish is None
    assert old.prior_finish == dt.date(2027, 7, 7) and old.finish_delta_days is None
    assert new.status == ADDED and new.prior_row is None and new.prior_finish is None
    assert new.current_finish == dt.date(2027, 7, 7) and new.finish_delta_days is None


def test_a_row_only_in_the_current_sheet_is_new_and_only_in_the_prior_is_removed(
    pair: CompareDoc,
) -> None:
    assert _row(pair, "Brand new").status == ADDED
    assert _row(pair, "Gone").status == REMOVED


def test_a_milestone_that_became_an_activity_is_compared_on_its_finish_and_named(
    pair: CompareDoc,
) -> None:
    r = _row(pair, "Was a milestone")
    assert r.status == SLIPPED and r.finish_delta_days == 21 and r.start_delta_days == -8
    assert (r.prior_milestone, r.current_milestone) == (True, False) and r.type_changed
    assert any("Was a milestone" in n and "milestone" in n and "activity" in n for n in pair.notes)


def test_a_duplicate_name_collision_is_reported_and_never_merged(pair: CompareDoc) -> None:
    twins = [r for r in pair.rows if r.name == "Twin"]
    assert len(twins) == 3 and all(r.status == AMBIGUOUS for r in twins)
    # the prior sheet's two rows and the current sheet's one all stay visible, dated from their
    # own sheet, with no delta computed against a guessed partner
    assert sorted(r.prior_row for r in twins if r.prior_row) == [9, 10]
    assert [r.current_row for r in twins if r.current_row] == [9]
    assert all(r.finish_delta_days is None for r in twins)
    assert any("prior.xlsx" in p and "rows 9, 10" in p and "Twin" in p for p in pair.problems)


def test_a_swimlane_move_is_one_removed_and_one_new_and_the_page_is_told(pair: CompareDoc) -> None:
    assert _row(pair, "Moves lane", "Lane B").status == REMOVED
    assert _row(pair, "Moves lane", "Lane C").status == ADDED
    assert any(
        "Moves lane" in n and "different swimlanes" in n and "not inferred" in n for n in pair.notes
    )


def test_spelling_variants_match_and_the_match_is_named(pair: CompareDoc) -> None:
    r = _row(pair, "Spaced Spelling")
    assert r.status == UNCHANGED and r.lane == "Lane A"  # the CURRENT sheet's spelling wins
    assert any("spaced  spelling" in n and "Spaced Spelling" in n for n in pair.notes)


# ── the summaries the slide and the takeaway quote ────────────────────────────────────────────


def test_per_lane_summaries_count_every_status_and_name_the_worst_slip(pair: CompareDoc) -> None:
    by = {ls.lane: ls for ls in pair.lanes}
    assert list(by) == ["Lane A", "Lane B", "Lane C"]  # first-seen order, current sheet first
    a, b, c = by["Lane A"], by["Lane B"], by["Lane C"]
    assert (a.slipped, a.pulled_in, a.start_moved, a.unchanged, a.new, a.removed, a.ambiguous) == (
        1,
        1,
        1,
        2,
        2,
        1,
        0,
    )
    assert (a.worst_slip_name, a.worst_slip_days) == ("Slips", 30)
    assert (b.slipped, b.pulled_in, b.unchanged, b.new, b.removed, b.ambiguous) == (
        1,
        0,
        0,
        0,
        2,
        3,
    )
    assert (b.worst_slip_name, b.worst_slip_days) == ("Was a milestone", 21)
    assert (c.new, c.removed, c.worst_slip_name) == (1, 0, None)


def test_the_totals_are_the_sum_of_the_lanes(pair: CompareDoc) -> None:
    t = pair.totals
    assert (t.slipped, t.pulled_in, t.start_moved, t.unchanged, t.new, t.removed, t.ambiguous) == (
        2,
        1,
        1,
        2,
        3,
        3,
        3,
    )
    assert (t.worst_slip_name, t.worst_slip_days) == ("Slips", 30)
    assert len(pair.rows) == 15  # 10 current rows + 5 prior-only rows (2 removed... see below)
    assert [r.name for r in pair.rows if r.current_row is None] == [
        "Old name",
        "Gone",
        "Twin",
        "Twin",
        "Moves lane",
    ]


def test_the_two_sources_travel_with_the_document(pair: CompareDoc) -> None:
    assert (pair.prior_source, pair.current_source) == ("prior.xlsx", "current.xlsx")


def test_the_same_sheet_twice_is_all_unchanged_with_nothing_to_report() -> None:
    doc = _doc(CURRENT_ROWS, "same.xlsx")
    same = compare_onepager_docs(doc, doc)
    assert {r.status for r in same.rows} == {UNCHANGED}
    assert same.totals.slipped == 0 and same.totals.worst_slip_name is None
    assert same.problems == () and same.notes == ()


def test_an_empty_side_is_all_new_or_all_removed() -> None:
    empty = OnePagerDoc("empty.xlsx", "Sheet1", (), (), ())
    cur = _doc(CURRENT_ROWS, "current.xlsx")
    assert {r.status for r in compare_onepager_docs(empty, cur).rows} == {ADDED}
    assert {r.status for r in compare_onepager_docs(cur, empty).rows} == {REMOVED}


# ── the layout: the ADR-0446 slide with the delta encoded ─────────────────────────────────────

from itertools import pairwise  # noqa: E402

from schedule_forensics.reports import onepager_compare as oc  # noqa: E402
from schedule_forensics.reports.onepager_compare import (  # noqa: E402
    CompareLayout,
    PlacedCompare,
    build_compare_layout,
    compare_layout_json,
    compare_subtitle,
    compare_tableset,
    delta_text,
)
from schedule_forensics.reports.xlsx import render_xlsx  # noqa: E402
from schedule_forensics.reports.xlsx_read import read_xlsx  # noqa: E402

TODAY = dt.date(2027, 6, 1)


@pytest.fixture(scope="module")
def lay(pair: CompareDoc) -> CompareLayout:
    return build_compare_layout(pair, TODAY, "Compare", compare_subtitle(pair, TODAY))


def _placed(lay: CompareLayout, name: str, status: str | None = None) -> PlacedCompare:
    hits = [p for p in lay.items if p.name == name and (status is None or p.status == status)]
    assert len(hits) == 1, (name, status, [(p.status, p.lane) for p in hits])
    return hits[0]


def _extents(lay: CompareLayout) -> dict[tuple[int, int], list[tuple[float, float]]]:
    """Each row's horizontal extent — ghost, solid shape, label and badge — re-derived from the
    geometry, never read from a flag."""
    out: dict[tuple[int, int], list[tuple[float, float]]] = {}
    half = lay.ms / 2
    for p in lay.items:
        xs: list[float] = []
        for a, b, ms in ((p.x0, p.x1, p.milestone), (p.ghost_x0, p.ghost_x1, p.ghost_milestone)):
            if a is None or b is None:
                continue
            xs += [a - (half if ms else 0), b + (half if ms else 0)]
        left, right = min(xs), max(xs)
        text_end = p.badge_x + p.badge_w if p.badge else (p.label_x + p.label_w)
        if p.inside:
            ext = (left, right)
        elif p.label_anchor == "start":
            ext = (left, max(right, text_end))
        else:
            full = p.label_w + (p.badge_w + 2 if p.badge else 0)
            ext = (min(left, p.label_x - full), right)
        out.setdefault((p.lane, p.row), []).append(ext)
    return out


def test_the_compare_slide_is_not_overflowed_and_nothing_overlaps_in_a_row(
    lay: CompareLayout,
) -> None:
    assert lay.lanes_y1 <= oc.LANES_Y1 + 0.01
    for (lane, row), exts in _extents(lay).items():
        exts.sort()
        for (_, a1), (b0, _) in pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap"
    for p in lay.items:
        ln = lay.lanes[p.lane]
        assert ln.y0 < p.y < ln.y1
        for x in (p.x0, p.x1, p.ghost_x0, p.ghost_x1, p.arrow_x0, p.arrow_x1):
            assert x is None or lay.x0 - 0.01 <= x <= lay.x1 + 0.01


def test_a_slip_draws_an_arrow_from_the_prior_finish_to_the_current_finish(
    lay: CompareLayout,
) -> None:
    p = _placed(lay, "Slips")
    assert p.status == SLIPPED and p.ghost_x1 is not None and p.x1 is not None
    assert (p.arrow_x0, p.arrow_x1) == (p.ghost_x1, p.x1) and p.arrow_x1 > p.arrow_x0
    assert p.ghost_x0 == p.x0  # the start did not move: the ghost and the bar share a left edge
    assert p.delta == "+30 cal d" and p.label == "Slips (3/31/27)"
    assert p.arrow_y < p.y - lay.bar_h / 2  # the arrow rides just above the bar


def test_a_pull_in_arrow_points_left_with_a_minus_delta(lay: CompareLayout) -> None:
    p = _placed(lay, "Pulls in")
    assert p.status == PULLED_IN and p.arrow_x1 is not None and p.arrow_x0 is not None
    assert p.arrow_x1 < p.arrow_x0 and p.delta == "\u221215 cal d"
    assert p.ghost_x1 is not None and p.x1 is not None and p.ghost_x1 > p.x1


def test_an_unchanged_row_has_no_arrow_no_delta_and_a_ghost_under_its_bar(
    lay: CompareLayout,
) -> None:
    p = _placed(lay, "Steady")
    assert p.status == UNCHANGED and p.arrow_x0 is None and p.arrow_x1 is None
    assert p.delta == "" and p.badge == ""
    assert (p.ghost_x0, p.ghost_x1) == (p.x0, p.x1)


def test_a_start_only_move_says_so_without_an_arrow(lay: CompareLayout) -> None:
    p = _placed(lay, "Starts later")
    assert p.status == START_MOVED and p.arrow_x0 is None
    assert p.delta == "start +14 cal d" and p.ghost_x1 == p.x1 and p.ghost_x0 != p.x0


def test_a_new_item_has_no_ghost_and_a_new_badge(lay: CompareLayout) -> None:
    p = _placed(lay, "Brand new")
    assert p.status == ADDED and p.ghost_x0 is None and p.ghost_milestone is None
    assert p.badge == "NEW" and p.badge_w > 0 and p.arrow_x0 is None
    assert p.badge_x >= p.label_x + p.label_w  # the tag follows the text


def test_a_removed_item_is_a_ghost_only_with_a_removed_badge(lay: CompareLayout) -> None:
    p = _placed(lay, "Gone")
    assert p.status == REMOVED and p.x0 is None and p.x1 is None
    assert p.ghost_x0 is not None and p.badge == "REMOVED" and p.label == "Gone (10/1/27)"


def test_a_type_change_draws_a_diamond_ghost_under_a_bar(lay: CompareLayout) -> None:
    p = _placed(lay, "Was a milestone")
    assert p.ghost_milestone is True and p.milestone is False
    assert p.ghost_x0 == p.ghost_x1 and p.x1 is not None and p.x0 is not None and p.x1 > p.x0
    assert p.delta == "+21 cal d"


def test_collision_rows_are_tagged_and_never_carry_a_delta(lay: CompareLayout) -> None:
    twins = [p for p in lay.items if p.name == "Twin"]
    assert len(twins) == 3 and all(p.badge == "DUPLICATE NAME" and p.delta == "" for p in twins)
    assert all(p.arrow_x0 is None for p in twins)


def test_every_delta_figure_on_the_slide_is_a_cell_the_table_carries(
    lay: CompareLayout, pair: CompareDoc
) -> None:
    """The r10 rule at the layout: a figure drawn on the slide is a figure the table renders."""
    table = compare_tableset(pair).tables[0]
    finish_col = table.headers.index("Finish delta (calendar days)")
    start_col = table.headers.index("Start delta (calendar days)")
    cells = {(r[1], r[finish_col], r[start_col]) for r in table.rows}
    for p in lay.items:
        if not p.delta:
            continue
        figure = int(p.delta.replace("start ", "").replace("\u2212", "-").split(" ")[0])
        if p.delta.startswith("start "):
            assert (p.name, 0, figure) in cells, (p.name, p.delta)
        else:
            assert any(n == p.name and f == figure for n, f, _s in cells), (p.name, p.delta)
        assert p.delta.endswith(" cal d")  # the unit is on every figure


def test_the_summary_column_has_one_box_per_lane_naming_the_worst_slip(
    lay: CompareLayout,
) -> None:
    assert len(lay.summaries) == len(lay.lanes)
    for box, ln in zip(lay.summaries, lay.lanes, strict=True):
        assert (box.y0, box.y1) == (ln.y0, ln.y1) and box.lane == ln.index
        assert (box.x0, box.x1) == (lay.summary_x0, lay.summary_x1) and box.pt >= 3.6
        assert 1 <= len(box.lines) <= 3 and all(box.lines)
    a = lay.summaries[0].lines
    joined = " ".join(a)
    assert "slipped 1" in joined and "pulled in 1" in joined and "new 2" in joined
    assert any("Slips" in line and "+30 cal d" in line for line in a)
    c = lay.summaries[2].lines
    assert any("new 1" in line for line in c) and any("no slip" in line for line in c)


def test_the_chart_area_ends_where_the_summary_column_begins(lay: CompareLayout) -> None:
    assert lay.x1 == oc.X1 < lay.summary_x0 < lay.summary_x1 == 944.0
    assert lay.months[0].x == lay.x0 and lay.years[-1].x1 == pytest.approx(lay.x1)
    assert all(lay.x0 <= m.x <= lay.x1 + 0.01 for m in lay.months)


def test_the_legend_carries_the_encoding_then_every_swimlane(lay: CompareLayout) -> None:
    kinds = [e.kind for e in lay.legend]
    assert kinds[:7] == ["activity", "ghost", "slip", "pull", "new", "removed", "today"]
    assert kinds.count("lane") == len(lay.lanes)
    assert all(e.x + e.w <= lay.summary_x1 + 0.01 for e in lay.legend)


def test_today_is_drawn_inside_the_window_and_the_window_is_whole_months(
    lay: CompareLayout,
) -> None:
    assert lay.today_x is not None and lay.x0 <= lay.today_x <= lay.x1
    assert lay.today_label == "TODAY 6/1/27" and lay.t0.endswith("-01") and lay.t1.endswith("-01")
    assert lay.t0 == "2027-01-01" and lay.t1 == "2028-02-01"


def test_the_subtitle_names_both_files_and_the_unit(pair: CompareDoc) -> None:
    sub = compare_subtitle(pair, TODAY)
    assert "prior.xlsx" in sub and "current.xlsx" in sub and "calendar days" in sub
    assert "2 slipped" in sub and "1 pulled in" in sub and "3 new" in sub and "3 removed" in sub


def test_delta_text_writes_the_sign_and_the_unit_every_time() -> None:
    assert delta_text(30) == "+30 cal d" and delta_text(-15) == "\u221215 cal d"


def test_compare_layout_json_round_trips(lay: CompareLayout) -> None:
    import json

    back = json.loads(json.dumps(compare_layout_json(lay)))
    assert back["prior_source"] == "prior.xlsx" and len(back["items"]) == 15
    assert back["items"][0]["arrow_y"] is not None and "summaries" in back


def test_the_excel_export_round_trips_with_prior_current_and_delta_columns(
    pair: CompareDoc,
) -> None:
    sheets = read_xlsx(render_xlsx(compare_tableset(pair)))
    items = next(rows for name, rows in sheets.items() if "Compared" in name)
    header = next(r for r in items if r and r[0] == "Swimlane")
    assert "Finish delta (calendar days)" in header and "Prior finish" in header
    slips = next(r for r in items if len(r) > 1 and r[1] == "Slips")
    assert slips[header.index("Finish delta (calendar days)")] == "30"
    assert slips[header.index("Status")] == SLIPPED
    summary = next(rows for name, rows in sheets.items() if "summary" in name.lower())
    assert any(r and r[0] == "Total" for r in summary)
    problems = next(rows for name, rows in sheets.items() if "Collisions" in name)
    assert any("Twin" in c for row in problems for c in row)


def test_nothing_to_lay_out_is_an_error_not_an_empty_slide() -> None:
    from schedule_forensics.reports.onepager_compare import LaneSummary

    empty = CompareDoc(
        "a", "b", (), (), LaneSummary("Total", 0, 0, 0, 0, 0, 0, 0, None, None), (), ()
    )
    with pytest.raises(ValueError):
        build_compare_layout(empty, TODAY, "Empty")


def _dense(lanes: int, per_lane: int) -> CompareDoc:
    """``per_lane`` simultaneous activities per lane, each slipped a little — every one its own
    row, so the packing has to step the floors down."""
    prior = [
        [
            f"Lane {i % lanes}",
            f"Activity number {i} with a long name",
            f"1/{1 + i % 20}/2027 - 3/1/2027",
        ]
        for i in range(lanes * per_lane)
    ]
    current = [[lane, name, span.replace("3/1/2027", "3/15/2027")] for lane, name, span in prior]
    return compare_onepager_docs(_doc(prior, "p.xlsx"), _doc(current, "c.xlsx"))


def test_a_dense_comparison_steps_the_floors_down_and_says_so() -> None:
    lay = build_compare_layout(_dense(8, 8), TODAY, "Dense")
    assert lay.lanes_y1 <= oc.LANES_Y1 + 0.01
    assert oc.FLOORS[-1][0] <= lay.row_h < oc.FLOORS[0][0]
    assert any(n.startswith("Dense comparison") for n in lay.notes)
    for (lane, row), exts in _extents(lay).items():
        exts.sort()
        for (_, a1), (b0, _) in pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap"
    beyond = build_compare_layout(_dense(8, 16), TODAY, "Beyond")
    assert beyond.lanes_y1 > oc.LANES_Y1
    assert any("does not fit one slide" in n for n in beyond.notes)


def test_a_pull_in_ghost_keeps_its_row_to_itself() -> None:
    """The packer must reserve the GHOST's extent too: a prior bar that ran to June still sits on
    the slide after the pull-in to February, and a new mid-April item cannot share its row."""
    prior = [["L", "Pulled back", "1/1/2027 - 6/1/2027"]]
    current = [
        ["L", "Pulled back", "1/1/2027 - 2/1/2027"],
        ["L", "Newcomer", "4/15/2027 - 5/1/2027"],
    ]
    lay = build_compare_layout(
        compare_onepager_docs(_doc(prior, "p.xlsx"), _doc(current, "c.xlsx")), TODAY, "Ghost"
    )
    a, b = _placed(lay, "Pulled back"), _placed(lay, "Newcomer")
    assert a.ghost_x1 is not None and b.x0 is not None and a.ghost_x1 > b.x0  # the ghost overhangs
    assert a.row != b.row, "the newcomer was packed under the ghost"
    for (lane, row), exts in _extents(lay).items():
        exts.sort()
        for (_, a1), (b0, _) in pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap"
