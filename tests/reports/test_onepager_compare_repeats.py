"""One-Pager COMPARE, round two (operator, 2026-09-22; ADR-0524): a repeated name, column D, lanes.

The operator's words, and the rulings asked for and given:

* "If the task name and date have not changed on either worksheet they are not DUPLICATE NAME.
  This just means that the task did not slip so only show it once with the single date." Ruling:
  "If the task name and the date matches for a task that is in the same swimlane in both excel
  sheets just put the task once in the swimlane with the single date."
* "use column D in the worksheets to determine if the task has completed or not and then indicate
  that somehow on the chart" — column D holds status words.
* "Make sure the tasks always stay in the correct swimlanes" — a standing requirement.
* "The goal is to show the slips as well as show what has not slipped."

What the matcher must NOT do, measured by the QC-3 skeptics before a line changed: pair the copies
LEFT OVER after the same-date pairing. A monthly review whose window rolled forward one month
(prior 1/1, 2/1, 3/1 -> current 2/1, 3/1, 4/1) paired that way reports a +90-day slip that never
happened — and it becomes the lane's and the headline's worst slip. Leftover copies with nothing
left to pair on one side are NEW / REMOVED; leftovers on BOTH sides are DUPLICATE NAME, named.

Red-first (2026-09-22): written before the change and observed to fail.
"""

from __future__ import annotations

import datetime as dt
import random
from itertools import pairwise

import pytest

from schedule_forensics.reports import onepager_compare as oc
from schedule_forensics.reports.onepager import OnePagerDoc, OnePagerItem, parse_workbook
from schedule_forensics.reports.onepager_compare import (
    ADDED,
    AMBIGUOUS,
    REMOVED,
    SLIPPED,
    UNCHANGED,
    CompareDoc,
    CompareLayout,
    PlacedCompare,
    build_compare_layout,
    compare_onepager_docs,
    compare_tableset,
    item_key,
    lane_key,
)

TODAY = dt.date(2027, 3, 1)
HEAD = ["Swimlane", "Task", "Date", "Status"]


def _doc(rows: list[list[str]], source: str) -> OnePagerDoc:
    return parse_workbook({"List": [HEAD, *rows]}, source)


def _cmp(prior: list[list[str]], current: list[list[str]]) -> CompareDoc:
    return compare_onepager_docs(_doc(prior, "prior.xlsx"), _doc(current, "current.xlsx"))


def _rows(doc: CompareDoc, name: str) -> list[tuple[str, str | None, str | None]]:
    def iso(d: dt.date | None) -> str | None:
        return d.isoformat() if d else None

    return sorted(
        (
            (r.status, iso(r.prior_finish), iso(r.current_finish))
            for r in doc.rows
            if r.name == name
        ),
        key=lambda t: tuple(x or "" for x in t),
    )


# ── a repeated name: identical dates pair, and are drawn ONCE ─────────────────────────────────


def test_a_repeated_name_whose_dates_did_not_change_is_unchanged_not_duplicate() -> None:
    """The operator's case: the same swimlane, name and date in both sheets."""
    prior = [["Alpha", "Design Review", "1/15/2027"], ["Alpha", "Design Review", "5/15/2027"]]
    doc = _cmp(prior, [list(r) for r in prior])
    assert _rows(doc, "Design Review") == [
        (UNCHANGED, "2027-01-15", "2027-01-15"),
        (UNCHANGED, "2027-05-15", "2027-05-15"),
    ]
    assert doc.problems == () and doc.totals.ambiguous == 0 and doc.totals.unchanged == 2
    assert all(r.finish_delta_days == 0 and r.start_delta_days == 0 for r in doc.rows)
    lay = build_compare_layout(doc, TODAY, "t")
    assert [p.badge for p in lay.items] == ["", ""]  # no DUPLICATE NAME tag
    assert all(p.ghost_x0 is None and p.arrow_x0 is None for p in lay.items)  # drawn ONCE
    assert sorted(p.label for p in lay.items) == [
        "Design Review (1/15/27)",
        "Design Review (5/15/27)",
    ]


def test_an_identical_row_twice_in_one_sheet_is_drawn_once_and_named() -> None:
    """The collapse runs BEFORE the copies are counted: without it the second prior copy of an
    unchanged 3/1 milestone would read REMOVED — an item with the same date flagged as gone."""
    prior = [["Gamma", "CDR", "3/1/2027"], ["Gamma", "CDR", "3/1/2027"]]
    doc = _cmp(prior, [["Gamma", "CDR", "3/1/2027"]])
    assert _rows(doc, "CDR") == [(UNCHANGED, "2027-03-01", "2027-03-01")]
    assert any("prior.xlsx" in n and "rows 2, 3" in n and "drawn once" in n for n in doc.notes), (
        doc.notes
    )
    assert doc.problems == ()


def test_a_rolling_window_never_invents_a_slip() -> None:
    """Prior 1/1, 2/1, 3/1 -> current 2/1, 3/1, 4/1: two copies pair on their dates; the 1/1 and
    the 4/1 are left over on BOTH sides and cannot be told apart from a slip — DUPLICATE NAME,
    never "+90 cal d"."""
    prior = [["P", "Review", d] for d in ("1/1/2027", "2/1/2027", "3/1/2027")]
    current = [["P", "Review", d] for d in ("2/1/2027", "3/1/2027", "4/1/2027")]
    doc = _cmp(prior, current)
    assert _rows(doc, "Review") == [
        (AMBIGUOUS, None, "2027-04-01"),
        (AMBIGUOUS, "2027-01-01", None),
        (UNCHANGED, "2027-02-01", "2027-02-01"),
        (UNCHANGED, "2027-03-01", "2027-03-01"),
    ]
    assert doc.totals.slipped == 0 and doc.totals.worst_slip_days is None
    assert all(r.finish_delta_days in (None, 0) for r in doc.rows)
    # the problem names ONLY the copies that could not be paired, never the ones that were
    (problem,) = doc.problems
    assert "prior.xlsx row 2" in problem and "current.xlsx row 4" in problem
    assert "rows 3" not in problem and "compared with nothing" in problem


def test_leftovers_on_one_side_only_are_new_or_removed() -> None:
    added = _cmp(
        [["P", "Audit", "1/1/2027"]], [["P", "Audit", "1/1/2027"], ["P", "Audit", "6/1/2027"]]
    )
    assert _rows(added, "Audit") == [
        (ADDED, None, "2027-06-01"),
        (UNCHANGED, "2027-01-01", "2027-01-01"),
    ]
    gone = _cmp(
        [["P", "Audit", "1/1/2027"], ["P", "Audit", "6/1/2027"]], [["P", "Audit", "1/1/2027"]]
    )
    assert _rows(gone, "Audit") == [
        (REMOVED, "2027-06-01", None),
        (UNCHANGED, "2027-01-01", "2027-01-01"),
    ]
    assert added.problems == () == gone.problems
    # a name repeated in ONE sheet only, with nothing to pair against, is simply new
    fresh = _cmp([], [["P", "Audit", "1/1/2027"], ["P", "Audit", "6/1/2027"]])
    assert {r.status for r in fresh.rows} == {ADDED} and fresh.problems == ()


def test_a_unique_name_still_pairs_whatever_its_dates() -> None:
    doc = _cmp([["P", "Build", "1/1/2027 - 2/1/2027"]], [["P", "Build", "1/1/2027 - 3/1/2027"]])
    (row,) = doc.rows
    assert row.status == SLIPPED and row.finish_delta_days == 28


def test_the_same_name_and_date_in_another_swimlane_is_never_paired_across() -> None:
    doc = _cmp([["Alpha", "Ship", "6/1/2027"]], [["Beta", "Ship", "6/1/2027"]])
    assert sorted((r.lane, r.status) for r in doc.rows) == [("Alpha", REMOVED), ("Beta", ADDED)]
    lay = build_compare_layout(doc, TODAY, "t")
    placed = {p.status: lay.lanes[p.lane].name for p in lay.items}
    assert placed == {REMOVED: "Alpha", ADDED: "Beta"}


def test_typographic_variants_of_a_name_or_a_lane_are_the_same_item_and_are_named() -> None:
    """An en dash, a curly apostrophe or a zero-width space (what a paste from Word or PowerPoint
    brings) must not draw one unchanged task twice as REMOVED + NEW, or split one swimlane in
    two. Only typographic twins fold — a hyphen and a space stay different names."""
    assert item_key("GRC\u2013X", "Crew\u2019s Pre\u2013Ship Review") == item_key(
        "GRC-X", "Crew's Pre-Ship Review"
    )
    assert lane_key("Lane A\u200b") == lane_key("Lane A")
    assert item_key("GRC-MET", "T") != item_key("GRC MET", "T")
    doc = _cmp(
        [["GRC-X", "Crew's Pre-Ship Review", "5/1/2027"]],
        [["GRC\u2013X", "Crew\u2019s Pre\u2013Ship Review", "5/1/2027"]],
    )
    (row,) = doc.rows
    assert row.status == UNCHANGED
    assert any("matched prior row" in n and "punctuation" in n for n in doc.notes), doc.notes
    assert len(build_compare_layout(doc, TODAY, "t").lanes) == 1


def test_the_swimlane_move_note_counts_each_name_once() -> None:
    prior = [["B", "X", "1/1/2027"], ["B", "X", "2/1/2027"]]
    current = [["C", "X", "1/1/2027"], ["C", "X", "2/1/2027"]]
    doc = _cmp(prior, current)
    (note,) = [n for n in doc.notes if "different swimlanes" in n]
    assert note.startswith("1 item name(s)") and note.count("“X”") == 1


# ── column D: carried on every row kind, counted, and its changes flagged ─────────────────────


PRIOR_D = [
    ["Alpha", "Design Review", "1/15/2027", "Complete"],
    ["Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"],
    ["Alpha", "Reopened", "2/10/2027", "Complete"],
    ["Alpha", "Moved after done", "2/12/2027", "Done"],
    ["Beta", "Dropped when done", "1/20/2027", "Complete"],
    ["Beta", "Twin", "3/1/2027", "Complete"],
    ["Beta", "Twin", "4/1/2027", ""],
]
CURRENT_D = [
    ["Alpha", "Design Review", "1/15/2027", "Complete"],
    ["Alpha", "Build", "2/1/2027 - 4/20/2027", "Complete"],
    ["Alpha", "Reopened", "2/10/2027", "In Progress"],
    ["Alpha", "Moved after done", "2/20/2027", "Done"],
    ["Beta", "Brand new", "5/1/2027", "Complete"],
    ["Beta", "Twin", "3/1/2027", "Complete"],
    ["Beta", "Twin", "4/5/2027", "Waiting on vendor"],
]


@pytest.fixture(scope="module")
def dpair() -> CompareDoc:
    return _cmp(PRIOR_D, CURRENT_D)


def _one(doc: CompareDoc, name: str, status: str | None = None) -> oc.CompareRow:
    hits = [r for r in doc.rows if r.name == name and (status is None or r.status == status)]
    assert len(hits) == 1, (name, [(r.status, r.prior_row, r.current_row) for r in hits])
    return hits[0]


def test_every_row_kind_carries_both_sides_of_column_d(dpair: CompareDoc) -> None:
    b = _one(dpair, "Build")
    assert (b.status, b.prior_complete, b.current_complete) == (SLIPPED, False, True)
    assert (_one(dpair, "Brand new").prior_complete, _one(dpair, "Brand new").current_complete) == (
        None,
        True,
    )
    gone = _one(dpair, "Dropped when done")
    assert (gone.status, gone.prior_complete, gone.current_complete) == (REMOVED, True, None)
    same = _one(dpair, "Twin", UNCHANGED)  # the 3/1 copy paired on its date
    assert (same.prior_complete, same.current_complete) == (True, True)
    left = {(r.prior_complete, r.current_complete) for r in dpair.rows if r.status == AMBIGUOUS}
    assert left == {(False, None), (None, False)}
    assert dpair.completion is True


def test_the_complete_count_is_the_current_list_s_checks(dpair: CompareDoc) -> None:
    by = {s.lane: s for s in dpair.lanes}
    # Alpha: Design Review, Build, Moved after done; Beta: Brand new, Twin 3/1
    assert (by["Alpha"].complete, by["Beta"].complete, dpair.totals.complete) == (3, 2, 5)


def test_a_completion_that_went_backwards_or_a_done_item_that_moved_is_flagged(
    dpair: CompareDoc,
) -> None:
    flags = " | ".join(dpair.flags)
    assert (
        "Reopened" in flags and "complete in the prior list, not complete in the current" in flags
    )
    assert "Moved after done" in flags and "+8 cal d" in flags
    assert "Design Review" not in flags and "Build" not in flags  # progress is not a flag
    assert any("Dropped when done" in n and "complete in the prior list" in n for n in dpair.notes)


def test_each_list_s_own_reading_travels_with_the_comparison(dpair: CompareDoc) -> None:
    assert any(
        n.startswith("current.xlsx: ") and "Waiting on vendor" in n for n in dpair.sheet_notes
    ), dpair.sheet_notes


def test_the_excel_export_carries_both_sides_of_column_d(dpair: CompareDoc) -> None:
    ts = compare_tableset(dpair)
    items = ts.tables[0]
    pc, cc = items.headers.index("Prior complete"), items.headers.index("Current complete")
    build = next(r for r in items.rows if r[1] == "Build")
    assert (build[pc], build[cc]) == ("no", "yes")
    new = next(r for r in items.rows if r[1] == "Brand new")
    assert (new[pc], new[cc]) == (None, "yes")
    summary = ts.tables[1]
    assert summary.rows[-1][summary.headers.index("Complete")] == 5
    names = [t.title for t in ts.tables]
    assert "Completion changes" in names and "How each list was read" in names


def test_three_column_lists_carry_no_completion() -> None:
    doc = compare_onepager_docs(
        parse_workbook({"L": [HEAD[:3], ["P", "Build", "1/1/2027"]]}, "p.xlsx"),
        parse_workbook({"L": [HEAD[:3], ["P", "Build", "1/1/2027"]]}, "c.xlsx"),
    )
    (row,) = doc.rows
    assert (row.prior_complete, row.current_complete) == (None, None)
    assert doc.completion is False and doc.flags == () and doc.totals.complete == 0
    lay = build_compare_layout(doc, TODAY, "t")
    assert "done" not in [e.kind for e in lay.legend] and not any(p.done for p in lay.items)


# ── the layout: the check beside the shape, never on it; unchanged drawn once ─────────────────


@pytest.fixture(scope="module")
def dlay(dpair: CompareDoc) -> CompareLayout:
    return build_compare_layout(dpair, TODAY, "Compare")


def _shape_span(lay: CompareLayout, p: PlacedCompare) -> tuple[float, float]:
    half = lay.ms / 2
    assert p.x0 is not None and p.x1 is not None
    return (p.x0 - half, p.x1 + half) if p.milestone else (p.x0, p.x1)


def test_a_complete_item_carries_a_check_beside_its_shape_never_on_it(dlay: CompareLayout) -> None:
    done = {p.name for p in dlay.items if p.done}
    assert done == {"Design Review", "Build", "Moved after done", "Brand new", "Twin"}
    for p in dlay.items:
        if not p.done:
            assert p.done_x is None
            continue
        assert p.done_x is not None and p.done_r > 0 and not p.inside
        s0, s1 = _shape_span(dlay, p)
        assert p.done_x + p.done_r <= s0 - 0.5 or p.done_x - p.done_r >= s1 + 0.5, p.name
        # adjacent to the shape, on the label's side, and the label follows the check
        if p.label_anchor == "start":
            assert s1 < p.done_x < p.label_x
        else:
            assert p.label_x < p.done_x < s0
        ln = dlay.lanes[p.lane]
        assert ln.y0 <= p.y - p.done_r and p.y + p.done_r <= ln.y1
        assert dlay.x0 - 0.01 <= p.done_x - p.done_r and p.done_x + p.done_r <= dlay.x1 + 0.01


def test_the_legend_explains_the_check_only_when_column_d_exists(dlay: CompareLayout) -> None:
    kinds = [e.kind for e in dlay.legend]
    assert kinds.index("removed") + 1 == kinds.index("done") and kinds.count("done") == 1
    assert next(e.label for e in dlay.legend if e.kind == "done") == "Complete (column D)"


def test_an_unchanged_item_is_drawn_once_and_keeps_its_old_geometry() -> None:
    """No ghost under an unchanged bar — and nothing else moves: the ghost it loses had exactly the
    bar's extent, and its label stays OUTSIDE the bar as it always was."""
    # a bar wide enough to hold its own label, and far from the right edge — so a label that
    # moved INSIDE it (what dropping the ghost would allow on its own) would be visible here
    rows = [["P", "Steady long task", "1/5/2027 - 6/30/2027"], ["P", "Slips", "12/1/2027"]]
    doc = _cmp(rows, [rows[0], ["P", "Slips", "12/20/2027"]])
    lay = build_compare_layout(doc, TODAY, "t")
    steady = next(p for p in lay.items if p.name == "Steady long task")
    assert steady.status == UNCHANGED and steady.ghost_x0 is None and steady.ghost_milestone is None
    assert steady.inside is False and steady.label_x > (steady.x1 or 0)


def _extents(lay: CompareLayout) -> dict[tuple[int, int], list[tuple[float, float]]]:
    """Each row's horizontal extent — ghost, shape, CHECK, label and tag — re-derived from the
    geometry, never read from a flag."""
    out: dict[tuple[int, int], list[tuple[float, float]]] = {}
    half = lay.ms / 2
    for p in lay.items:
        xs: list[float] = []
        for a, b, ms in ((p.x0, p.x1, p.milestone), (p.ghost_x0, p.ghost_x1, p.ghost_milestone)):
            if a is None or b is None:
                continue
            xs += [a - (half if ms else 0), b + (half if ms else 0)]
        if p.done and p.done_x is not None:
            xs += [p.done_x - p.done_r, p.done_x + p.done_r]
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


def test_the_packer_reserves_the_check_so_nothing_in_a_row_overlaps(dlay: CompareLayout) -> None:
    for (lane, row), exts in _extents(dlay).items():
        exts.sort()
        for (_, a1), (b0, _) in pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap"


def test_a_check_at_the_right_edge_flips_left_with_its_label() -> None:
    """A complete item near the chart's right edge takes an end-anchored label; the check still sits
    between the label and the shape."""
    rows = [["P", "Early", "1/1/2027"], ["P", "At the edge with a long name", "12/20/2027", "Done"]]
    lay = build_compare_layout(_cmp(rows, rows), TODAY, "t")
    p = next(p for p in lay.items if p.name.startswith("At the edge"))
    assert p.done and p.label_anchor == "end" and p.done_x is not None
    assert p.label_x < p.done_x < (p.x0 or 0)


# ── the per-swimlane strip shows every non-zero count — what did NOT slip included ────────────


def test_the_summary_strip_shows_every_non_zero_count_without_cutting_one(
    dlay: CompareLayout, dpair: CompareDoc
) -> None:
    for box, summary in zip(dlay.summaries, dpair.lanes, strict=True):
        text = " ".join(box.lines)
        assert "…" not in text, text
        for label, n in (
            ("slipped", summary.slipped),
            ("unchanged", summary.unchanged),
            ("new", summary.new),
            ("removed", summary.removed),
            ("ambiguous", summary.ambiguous),
            ("complete", summary.complete),
        ):
            if n:
                assert f"{label} {n}" in text, (label, text)
        assert box.pt >= 3.6


def test_a_one_row_lane_on_a_dense_slide_still_shows_every_count() -> None:
    """The case the old three-line strip cut first: a ONE-row lane on a slide dense enough to step
    the rows down to a floor (here 6 pt). The old rule gave the counts one line at 3.8 pt and cut
    "removed 1 · complete 2" behind an ellipsis — what the operator most needs to see."""
    # six milestones two months apart, so the lane packs into ONE row
    moving_prior = [["L", f"Item {i}", f"{1 + 2 * i}/1/2027"] for i in range(5)]
    moving_current = [
        ["L", "Item 0", "1/1/2027", "Done"],  # unchanged, complete
        ["L", "Item 1", "3/9/2027"],  # slipped +8
        ["L", "Item 2", "4/25/2027"],  # pulled in -6
        ["L", "Item 3", "7/1/2027", "Complete"],  # unchanged, complete
        ["L", "Fresh", "11/15/2027"],  # new ("Item 4" removed)
    ]
    # seven filler swimlanes of eight simultaneous activities: one row each, 56 rows in all
    filler = [
        [f"Filler {lane}", f"Long activity {lane}-{k}", "1/1/2027 - 3/1/2027"]
        for lane in range(7)
        for k in range(8)
    ]
    doc = _cmp(moving_prior + filler, moving_current + filler)
    lay = build_compare_layout(doc, TODAY, "t")
    assert lay.row_h < oc.FLOORS[0][0], lay.row_h  # the floors really were stepped down
    box = next(b for b in lay.summaries if lay.lanes[b.lane].name == "L")
    assert lay.lanes[box.lane].rows == 1
    text = " ".join(box.lines)
    for part in ("slipped 1", "pulled in 1", "unchanged 2", "new 1", "removed 1", "complete 2"):
        assert part in text, (part, box.lines, box.pt)
    assert "…" not in text and box.pt >= 3.6
    assert len(box.lines) * box.pt * 1.25 <= (box.y1 - box.y0) - 1.5 + 0.01


# ── "the tasks always stay in the correct swimlanes": a seeded fuzz of the whole pipeline ─────


LANES = ["Alpha", "Beta", "Gamma Ray", "gamma  ray", "Delta", "E", "GRC\u2013X", "GRC-X"]
NAMES = ["Design Review", "Build", "Test", "Ship", "CDR", "PDR", "TRR", "Launch"]
STATUS = ["", "Complete", "In Progress", "Done", "Waiting"]


def _random_doc(rnd: random.Random, source: str) -> OnePagerDoc:
    items = []
    for i in range(rnd.randint(0, 30)):
        s = dt.date(2026, 6, 1) + dt.timedelta(days=rnd.randint(0, 700))
        f = s if rnd.random() < 0.45 else s + dt.timedelta(days=rnd.randint(1, 150))
        status = rnd.choice(STATUS)
        items.append(
            OnePagerItem(
                rnd.choice(LANES),
                rnd.choice(NAMES),
                s,
                f,
                i + 2,
                (status.startswith(("Complete", "Done"))) if status else False,
            )
        )
    if rnd.random() < 0.5 and items:  # recurring copies and identical duplicates
        items += [items[rnd.randrange(len(items))] for _ in range(rnd.randint(1, 4))]
    return OnePagerDoc(source, "S", tuple(items), (), ())


@pytest.mark.parametrize("seed_block", range(4))
def test_every_item_stays_in_its_own_swimlane_band(seed_block: int) -> None:
    for seed in range(seed_block * 150, seed_block * 150 + 150):
        rnd = random.Random(seed)
        doc = compare_onepager_docs(_random_doc(rnd, "p.xlsx"), _random_doc(rnd, "c.xlsx"))
        if not doc.rows:
            continue
        for r in doc.rows:  # a pair never joins two swimlanes
            assert lane_key(r.lane) == item_key(r.lane, r.name)[0]
        lay = build_compare_layout(doc, TODAY, "t")
        assert len(lay.items) == len(doc.rows), seed
        placed = sorted(
            (
                lane_key(lay.lanes[p.lane].name),
                p.name,
                p.status,
                p.prior_finish or "",
                p.current_finish or "",
            )
            for p in lay.items
        )
        wanted = sorted(
            (
                lane_key(r.lane),
                r.name,
                r.status,
                r.prior_finish.isoformat() if r.prior_finish else "",
                r.current_finish.isoformat() if r.current_finish else "",
            )
            for r in doc.rows
        )
        assert placed == wanted, seed
        keys = [lane_key(ln.name) for ln in lay.lanes]
        assert len(keys) == len(set(keys)), (seed, "one swimlane drawn as two bands")
        for a, b in pairwise(lay.lanes):
            assert a.y1 <= b.y0, seed
        for p in lay.items:
            ln = lay.lanes[p.lane]
            reach = max(lay.bar_h, lay.ms, 1.2 * lay.label_pt) / 2
            if p.done:
                reach = max(reach, p.done_r)
            assert ln.y0 <= p.y - reach and p.y + reach <= ln.y1, (seed, p.name)
            assert p.status != UNCHANGED or p.ghost_x0 is None, (seed, "an unchanged ghost")
            assert not p.done or (p.x0 is not None and p.current_start is not None), seed
