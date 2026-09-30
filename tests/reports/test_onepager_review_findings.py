"""ADR-0539's adversarial review — every finding the review reproduced, pinned so it cannot return.

The build of the C start · D finish · E complete intake and the operator's logic links was
attacked after it was written by an intake reviewer (INTAKE-n), a links reviewer (LINKS-n) and the
lead. Each test here was run RED on the tree the review read (the finding reproduced) before the
fix made it green; the two property tests use generators independent of the detector — sheets
typed the older way and sheets typed the current way — and judge the detector by the FORCED
reading of the same sheet (the upload form's layout choice), never by the detector's own output.
"""

from __future__ import annotations

import datetime as dt
import io
import random
import zipfile
from collections.abc import Sequence

import pytest

import schedule_forensics.reports.onepager as op
from schedule_forensics.reports.onepager import OnePagerItem, build_layout, keyed
from schedule_forensics.reports.onepager_links import (
    HALO_W,
    Link,
    PlacedLink,
    check_link,
)
from schedule_forensics.reports.xlsx_read import read_xlsx_numbered
from web.onepager_twin import twin_xlsx

_Row = tuple[str, ...]
D = dt.date


def _doc(rows: Sequence[_Row], layout: str | None = None) -> op.OnePagerDoc:
    sheets = read_xlsx_numbered(twin_xlsx(rows))
    return op.parse_numbered_workbook(sheets, "list.xlsx", layout=layout)


def _items(doc: op.OnePagerDoc) -> list[tuple[str, str, str, str]]:
    return [(i.lane, i.name, i.start.isoformat(), i.finish.isoformat()) for i in doc.items]


# ── the intake ──────────────────────────────────────────────────────────────────────────────


def test_intake_1_one_date_among_words_in_d_keeps_every_row_of_an_older_sheet() -> None:
    """A notes / RAG column D holding ONE date among words it cannot read is the older layout:
    in the current layout D must be a finish, so every word counts against it (the review's
    repro read it as the current layout and skipped three of four rows)."""
    doc = _doc(
        (
            ("Swimlane", "Task", "Date", "Notes"),
            ("Alpha", "Design Review", "1/15/2027", "On schedule"),
            ("Alpha", "Build", "2/1/2027 - 4/1/2027", "Awaiting parts"),
            ("Alpha", "Test", "5/1/2027", "3/1/2027"),
            ("Beta", "Ship", "6/27/2027", "Slipped two weeks"),
        )
    )
    assert doc.layout == op.DATE_STATUS and doc.problems == ()
    assert [n for _l, n, _s, _f in _items(doc)] == ["Design Review", "Build", "Test", "Ship"]


def test_intake_1_a_date_that_cannot_be_the_finish_is_not_evidence_of_one() -> None:
    """A D date BEFORE C's date, or not the end of a range typed in C, is a note or a status
    date — it counts against the current layout."""
    doc = _doc(
        (
            ("Beta", "Item 0", "3/14/2027", "4/15/2027"),
            ("Alpha", "Item 1", "8/6/2027", "Green"),
            ("Beta", "Item 2", "1/1/2027 - 11/1/2027", "3/1/2027"),
        )
    )
    assert doc.layout == op.DATE_STATUS and doc.problems == () and len(doc.items) == 3
    assert "1 of them before column C's date or not the end of its range" in doc.layout_note


def test_intake_2_an_undecided_layout_is_a_note_never_a_skipped_row() -> None:
    doc = _doc(
        (
            ("Alpha", "Design Review", "1/15/2027", "Complete"),
            ("Alpha", "Build", "2/1/2027", "3/1/27"),
        )
    )
    assert doc.problems == () and len(doc.items) == 2
    assert "the layout could not be decided" in doc.layout_note


def test_intake_3_a_status_word_with_a_date_word_in_d_s_header_lets_the_content_decide() -> None:
    """ "Complete By" / "Complete Date" / "Done By" / "Planned Complete" over a column of dates
    is a FINISH column: the activities stay activities and column E's status is read."""
    for head in ("Complete By", "Complete Date", "Done By", "Planned Complete"):
        doc = _doc(
            (
                ("Swimlane", "Task", "Start", head, "Status"),
                ("Alpha", "Build", "2/1/2027", "4/1/2027", "In Progress"),
                ("Alpha", "Test", "4/5/2027", "6/30/2027", ""),
                ("Beta", "Ship", "7/1/2027", "7/1/2027", "Complete"),
            )
        )
        assert doc.layout == op.START_FINISH, head
        assert _items(doc)[0] == ("Alpha", "Build", "2027-02-01", "2027-04-01"), head
        assert [i.complete for i in doc.items] == [False, False, True], head


def test_intake_3_positive_unanimous_content_overrules_the_header_and_says_so() -> None:
    doc = _doc(
        (
            ("Swimlane", "Task", "Date", "Past Due"),
            ("Alpha", "Design Review", "1/15/2027", "No"),
            ("Alpha", "Build", "2/1/2027 - 4/1/2027", "Yes"),
            ("Beta", "Ship", "6/27/2027", "No"),
        )
    )
    assert doc.layout == op.DATE_STATUS and doc.problems == () and len(doc.items) == 3
    assert doc.layout_note.startswith("column D is headed “Past Due” but holds only status words")


def test_intake_3_words_the_reader_cannot_read_never_overrule_a_finish_header() -> None:
    doc = _doc(
        (
            ("Swimlane", "Task", "Start", "Finish", "Complete"),
            ("Alpha", "Build", "2/1/2027", "Q3 FY27", ""),
            ("Alpha", "Test", "4/5/2027", "Q4 FY27", ""),
        )
    )
    assert doc.layout == op.START_FINISH  # both rows refused BY NAME, never redrawn as milestones
    assert len(doc.problems) == 2 and all("Q" in p for p in doc.problems)


def test_intake_5_a_year_zero_month_token_is_no_date_and_never_a_500() -> None:
    assert op.parse_date("1/0000") is None
    doc = _doc(
        (("Alpha", "Kickoff", "1/15/2027", "1/0000"), ("Alpha", "Review", "2/1/2027", "Done"))
    )
    assert len(doc.items) == 2


def test_intake_6_column_e_is_never_dropped_unsaid_when_d_is_empty() -> None:
    doc = _doc(
        (
            ("Alpha", "Design Review", "1/15/2027", "", "Waiting on vendor"),
            ("Alpha", "Build", "2/1/2027", "", "Awaiting sign-off"),
        )
    )
    assert (doc.layout, doc.status_column) == (op.START_FINISH, "E")
    assert len(doc.completion_notes) == 2  # the words are NAMED, not silently dropped


def test_intake_7_a_note_above_the_header_and_a_status_dated_header_are_not_rows() -> None:
    above = _doc(
        (
            ("", "", "", "As of 9/1/26"),
            ("Swimlane", "Task", "Date", "Status"),
            ("Alpha", "Design Review", "1/15/2027", "Complete"),
            ("Alpha", "Build", "2/1/2027", "Pending"),
        )
    )
    dated = _doc(
        (
            ("Swimlane", "Task", "Date", "9/1/2026"),
            ("Alpha", "Design Review", "1/15/2027", "Green"),
            ("Alpha", "Build", "2/1/2027 - 4/1/2027", "Amber"),
            ("Beta", "Ship", "6/27/2027", "Red"),
        )
    )
    for doc, n in ((above, 2), (dated, 3)):
        assert doc.layout == op.DATE_STATUS and doc.problems == () and len(doc.items) == n


def test_intake_7_a_finish_only_first_data_row_is_still_data() -> None:
    doc = _doc(
        (
            ("Milestones", "Program Start", "", "9/1/2026", ""),
            ("Milestones", "Launch", "3/1/2027", "3/1/2027", "Complete"),
        )
    )
    assert [n for _l, n, _s, _f in _items(doc)] == ["Program Start", "Launch"]


def _older_sheet(r: random.Random) -> list[_Row]:
    known = ["Complete", "In Progress", "Done", "Not Started", "Pending", "Open", "Closed"]
    unknown = ["Green", "Amber", "Red", "On schedule", "Awaiting parts", "see notes", "Bob"]
    rows: list[_Row] = []
    words = known if r.random() < 0.5 else unknown
    for k in range(r.randint(3, 8)):
        c = r.choice(
            [
                f"{r.randint(1, 12)}/{r.randint(1, 28)}/2027",
                f"{r.randint(1, 6)}/1/2027 - {r.randint(7, 12)}/1/2027",
                str(r.randint(46000, 46800)),
            ]
        )
        pick = r.random()
        d = r.choice(words) if pick < 0.8 else r.choice(["", "TBD", "N/A", "12/31/2026"])
        rows.append((r.choice(["Alpha", "Beta"]), f"Item {k}", c, d))
    if r.random() < 0.5:
        rows.insert(0, ("Swimlane", "Task", "Date", r.choice(["Notes", "RAG", "Status", "Owner"])))
    return rows


def _current_sheet(r: random.Random) -> list[_Row]:
    def fmt(d: dt.date) -> str:
        return r.choice(
            [f"{d.month}/{d.day}/{d.year}", d.isoformat(), f"{d.month}/{d.day}/{d.year % 100:02d}"]
        )

    rows: list[_Row] = []
    for k in range(r.randint(2, 10)):
        s = D(2027, 1, 1) + dt.timedelta(days=r.randrange(500))
        kind = r.random()
        if kind < 0.3:
            c, d = fmt(s), fmt(s)
        elif kind < 0.4:
            c, d = "", fmt(s)
        elif kind < 0.5:
            c, d = fmt(s), ""
        else:
            c, d = fmt(s), fmt(s + dt.timedelta(days=r.randint(1, 200)))
        rows.append((f"Lane {k % 3}", f"Item {k}", c, d, r.choice(["Complete", "", "Open", "X"])))
    if r.random() < 0.6:
        head = r.choice(["Finish", "End", "Due", "Complete By", "ECD", "Target Date", "Forecast"])
        rows.insert(0, ("Swimlane", "Task", "Start", head, "Complete"))
    return rows


def test_every_sheet_typed_the_older_way_reads_exactly_as_the_older_reading() -> None:
    """Property (review INTAKE-1): 300 sheets typed the older way — status words, RAG / notes /
    owner words, placeholders and a stray date in D — read on auto EXACTLY as the forced older
    reading reads them: the same items, and no problem the older reading does not raise."""
    for seed in range(300):
        rows = _older_sheet(random.Random(seed))
        auto, older = _doc(rows), _doc(rows, op.DATE_STATUS)
        assert _items(auto) == _items(older), (seed, rows)
        assert set(auto.problems) <= set(older.problems), (seed, rows, auto.problems)


def test_every_sheet_typed_the_current_way_reads_as_the_current_layout() -> None:
    """Property: 300 sheets typed C start · D finish (D never before C) · E complete — with and
    without a header, finish headers of every common spelling — read on auto as the current
    layout, with the same items as the forced current reading."""
    for seed in range(300):
        rows = _current_sheet(random.Random(seed))
        auto, current = _doc(rows), _doc(rows, op.START_FINISH)
        assert auto.layout == op.START_FINISH, (seed, rows, auto.layout_note)
        assert _items(auto) == _items(current), (seed, rows)


# ── the links ───────────────────────────────────────────────────────────────────────────────


def _keyed(rows: Sequence[tuple[str, str, dt.date, dt.date]]) -> list[OnePagerItem]:
    return keyed(
        [OnePagerItem(lane, n, s, f, i + 1, None) for i, (lane, n, s, f) in enumerate(rows)]
    )


def _layout(rows: Sequence[tuple[str, str, dt.date, dt.date]], links: Sequence[_Row]) -> op.Layout:
    items = _keyed(rows)
    key = {it.name: it.key for it in items}
    return build_layout(
        items, D(2026, 1, 1), "T", links=[Link(key[a], key[b], k) for a, b, k in links]
    )


def _seg_distance(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / span))
    return float(((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5)


def _erased(target: list[tuple[float, float]], later: Sequence[PlacedLink]) -> float:
    """The share of ``target``'s sample points under a LATER link's halo (painted after, it
    erases what it covers)."""
    hit = sum(
        any(
            _seg_distance(x, y, a, b) < HALO_W / 2
            for m in later
            for a, b in zip(m.shaft, m.shaft[1:], strict=False)
        )
        for x, y in target
    )
    return hit / len(target)


def _head_points(head: list[tuple[float, float]]) -> list[tuple[float, float]]:
    (ax, ay), (bx, by), (cx, cy) = head
    n = 10
    return [
        (
            ax * u / n + bx * v / n + cx * (n - u - v) / n,
            ay * u / n + by * v / n + cy * (n - u - v) / n,
        )
        for u in range(n + 1)
        for v in range(n + 1 - u)
    ]


@pytest.mark.parametrize(
    ("wide", "gate_finish"),
    [
        (False, D(2026, 3, 1)),
        (True, D(2026, 3, 1)),
        (True, D(2026, 3, 2)),
        (True, D(2026, 3, 3)),
        (True, D(2026, 3, 4)),
    ],
    ids=["milestone", "milestone-18-months", "1-day-bar", "2-day-bar", "3-day-bar"],
)
def test_links_1_a_chain_through_a_milestone_keeps_the_head_into_the_milestone(
    wide: bool, gate_finish: dt.date
) -> None:
    """The review's repro: Alpha → Gate → Bravo, all FS in one lane. The link out of Gate used
    to start exactly where the head INTO Gate sat, and its halo erased the head — the slide read
    as one line from Alpha to Bravo. Each end of an item now takes its own attachment point.

    Review SKL-2: the fix gave a milestone's start and finish ONE point list but a bar's two
    ends two — and on an 18-month slide (a far item in another lane) a 1-3 day bar's two ends
    sit closer than a slot, so the link out of its finish erased 46 % of the head into its start
    on a slide that said nothing. The points on one side of an item are now one list, whichever
    end takes them; a bar too short for two takes the second link on its other side."""
    rows = [
        ("Eng", "Alpha", D(2026, 1, 5), D(2026, 1, 31)),
        ("Eng", "Gate", D(2026, 3, 1), gate_finish),
        ("Eng", "Bravo", D(2026, 4, 1), D(2026, 5, 31)),
    ]
    if wide:
        rows.append(("Ops", "Far end", D(2027, 6, 1), D(2027, 6, 1)))
    lay = _layout(rows, [("Alpha", "Gate", "FS"), ("Gate", "Bravo", "FS")])
    into_gate, out_of_gate = lay.links
    assert _erased(_head_points(into_gate.head), [out_of_gate]) == 0.0
    gate_y = next(p.y for p in lay.items if p.name == "Gate")
    (tip_x, tip_y), (out_x, out_y) = into_gate.head[0], out_of_gate.shaft[0]
    same_side = (tip_y > gate_y) == (out_y > gate_y)
    assert not same_side or abs(tip_x - out_x) >= 2.0  # two points, not one
    assert not lay.link_notes  # nothing undrawn, nothing crowded


def test_links_1_a_three_item_chain_never_loses_the_head_into_its_middle_item() -> None:
    """Review DOC-LS-02: A, B, C in one lane, C → B (SF) then B → A (FS). The FS link left B's
    finish right where the SF head entered it — 100 % of that head under its halo, on a 3-item
    slide whose only disclosure was "At this density … Split the list"."""
    lay = _layout(
        [
            ("Eng", "A", D(2026, 8, 4), D(2026, 9, 19)),
            ("Eng", "B", D(2026, 1, 27), D(2026, 3, 8)),
            ("Eng", "C", D(2026, 8, 25), D(2026, 11, 18)),
        ],
        [("C", "B", "SF"), ("B", "A", "FS")],
    )
    first, second = lay.links
    assert _erased(_head_points(first.head), [second]) == 0.0
    assert lay.link_notes == []


def test_links_1_a_bar_taking_fs_in_and_sending_ss_out_of_its_start_keeps_both() -> None:
    lay = _layout(
        [
            ("Eng", "Design", D(2026, 1, 5), D(2026, 2, 1)),
            ("Eng", "Build", D(2026, 2, 5), D(2026, 4, 1)),
            ("Eng", "TRR", D(2026, 5, 1), D(2026, 5, 1)),
        ],
        [("Design", "Build", "FS"), ("Build", "TRR", "SS")],
    )
    assert _erased(_head_points(lay.links[0].head), lay.links[1:]) == 0.0


def test_links_2_a_type_tag_is_never_erased_by_a_later_link_in_its_channel() -> None:
    """The review's repro: SS then FF on one pair put half the SS tag under the FF link's
    halo. A tag's ink is now reserved in its channel."""
    lay = _layout(
        [
            ("Eng", "Prime", D(2026, 1, 4), D(2026, 6, 30)),
            ("Eng", "Succ", D(2027, 1, 3), D(2027, 3, 1)),
        ],
        [("Prime", "Succ", "SS"), ("Prime", "Succ", "FF")],
    )
    ss, ff = lay.links
    width = len(ss.tag) * ss.tag_pt * 0.62
    x0 = ss.tag_x if ss.tag_anchor == "start" else ss.tag_x - width
    ink = [
        (x0 + width * i / 8, ss.tag_y - ss.tag_pt * 0.7 * j / 8) for i in range(9) for j in range(9)
    ]
    assert ss.tag == "SS" and _erased(ink, [ff]) == 0.0


def test_links_2_a_later_links_vertical_leg_never_erases_a_type_tag() -> None:
    """Review SKL-1: the LINKS-2 fix reserved a tag against later HORIZONTAL legs only. Through
    the page's own actions — Item 28 → Item 37 (SS), then Item 30 (a milestone one day before
    Item 37) → Item 9 (FS): the FS link's first leg rose straight through the SS tag and its
    halo erased 22 % of it, on a roomy slide (row 13 pt then; page-filling since ADR-0540)
    that said nothing."""
    from schedule_forensics.web import onepager_actions as act
    from schedule_forensics.web.onepager import linkable_items, onepager_layout
    from schedule_forensics.web.state import SessionState

    rows = (
        ("Swimlane", "Task", "Start", "Finish", "Complete"),
        ("Lane 4", "Item 9", "6/13/2027", "8/27/2027", ""),
        ("Lane 1", "Item 26", "5/31/2026", "7/28/2026", ""),
        ("Lane 3", "Item 28", "4/1/2027", "8/28/2027", ""),
        ("Lane 0", "Item 30", "2/15/2027", "2/15/2027", ""),
        ("Lane 1", "Item 37", "2/16/2027", "2/16/2027", ""),
    )
    st = SessionState()
    act.load_list(st, "l.xlsx", twin_xlsx(rows), max_bytes=10 * 1024 * 1024)
    key = {label.split(" · ")[1].split(" (")[0]: k for k, label, _r in linkable_items(st)}
    for a, b, kind in (("Item 28", "Item 37", "SS"), ("Item 30", "Item 9", "FS")):
        act.edit_links(st, "onepager", "add", key[a], key[b], kind)
    lay = onepager_layout(st, D(2026, 6, 1))
    assert lay is not None and lay.row_h > 13.0  # a roomy slide (ADR-0540: page-filling rows)
    ss, fs = lay.links
    width = len(ss.tag) * ss.tag_pt * 0.62
    x0 = ss.tag_x if ss.tag_anchor == "start" else ss.tag_x - width
    ink = [
        (x0 + width * i / 8, ss.tag_y - ss.tag_pt * 0.7 * j / 8) for i in range(9) for j in range(9)
    ]
    assert ss.tag == "SS" and _erased(ink, [fs]) == 0.0
    assert _erased(_head_points(ss.head), [fs]) == 0.0
    assert lay.link_notes == []


def _idents(items: Sequence[OnePagerItem]) -> dict[str, tuple[str, ...]]:
    from schedule_forensics.reports.onepager import item_ident  # new with the fix (red first)

    return {it.key: item_ident(it.lane, it.name, it.start, it.finish) for it in items}


def test_links_4_a_link_survives_its_name_starting_or_stopping_to_repeat() -> None:
    """Review LINKS-4: an item's KEY changes form when its name starts or stops repeating; the
    link re-binds to the one item that is still exactly its item."""
    ship = ("Eng", "Ship", D(2026, 6, 1), D(2026, 6, 1))
    once = _keyed([("Eng", "Review", D(2026, 3, 1), D(2026, 3, 1)), ship])
    idents = _idents(once)
    link = Link(once[0].key, once[1].key, "FS", "", "", idents[once[0].key], idents[once[1].key])
    twice = _keyed(
        [
            ("Eng", "Review", D(2026, 3, 1), D(2026, 3, 1)),
            ("Eng", "Review", D(2026, 4, 1), D(2026, 4, 1)),
            ship,
        ]
    )
    from schedule_forensics.reports.onepager_links import rebind

    (moved,) = rebind([link], _idents(twice))
    assert moved.pred == twice[0].key  # the 3/1 review — not the new 4/1 one
    back = _keyed([("Eng", "Review", D(2026, 3, 1), D(2026, 3, 1)), ship])
    (again,) = rebind([moved], _idents(back))
    assert again.pred == back[0].key


def test_links_4_a_rolling_list_never_moves_a_link_to_another_month() -> None:
    """The blocker ADR-0539's plan red team found, re-attacked through the re-bind: the 3/1
    review is linked, next month's list drops it and keeps the 4/1 review — the link must stay
    unresolved and be NAMED truly, never re-attached to the 4/1 review."""
    ship = ("Eng", "Ship", D(2026, 6, 1), D(2026, 6, 1))
    before = _keyed(
        [
            ("Eng", "Monthly review", D(2026, 3, 1), D(2026, 3, 1)),
            ("Eng", "Monthly review", D(2026, 4, 1), D(2026, 4, 1)),
            ship,
        ]
    )
    idents = _idents(before)
    link = Link(
        before[0].key, before[2].key, "FS", "", "", idents[before[0].key], idents[before[2].key]
    )
    after = _keyed([("Eng", "Monthly review", D(2026, 4, 1), D(2026, 4, 1)), ship])
    from schedule_forensics.reports.onepager_links import rebind

    (kept,) = rebind([link], _idents(after))
    assert kept.pred not in {it.key for it in after}


def test_links_5_a_loop_through_an_item_the_window_hides_names_it() -> None:
    links = [
        Link("a", "b", "FS", "A", "Bravo (hidden)"),
        Link("b", "c", "FS", "Bravo (hidden)", "C"),
    ]
    why = check_link(links, Link("c", "a", "FS"), {"a": "A", "c": "C"})
    assert why is not None and "Bravo (hidden)" in why and "?" not in why


def test_links_6_the_excel_export_explains_a_link_when_the_window_leaves_no_slide() -> None:
    """Review LINKS-6: with a date window that leaves no item on the slide, the export's "Logic
    links" table said "no — see the note below" with no note under it."""
    from schedule_forensics.web import onepager_actions as act
    from schedule_forensics.web.onepager import linkable_items
    from schedule_forensics.web.state import SessionState

    st = SessionState()
    rows = (
        ("Swimlane", "Task", "Start", "Finish", "Complete"),
        ("Eng", "A", "1/5/2026", "3/1/2026", ""),
        ("Eng", "B", "4/5/2026", "6/1/2026", ""),
    )
    act.load_list(st, "l.xlsx", twin_xlsx(rows), max_bytes=10 * 1024 * 1024)
    (a, _la, _ra), (b, _lb, _rb) = linkable_items(st)
    act.edit_links(st, "onepager", "add", a, b, "FS")
    act.set_window(st, "2027-01-01", "2027-03-31", "set")
    ts = act.onepager_workbook(st, D(2026, 1, 1))
    assert not isinstance(ts, str)
    table = next(t for t in ts.tables if t.title == "Logic links")
    assert table.rows[0][-1] == "no — see the note below"
    assert str(table.rows[-1][-1]).startswith("No item of the list falls inside the date window")


def test_an_excel_boolean_in_the_status_column_reads_as_excel_shows_it() -> None:
    """TRUE typed in Excel (and a cell checkbox) is a BOOLEAN cell, ``<c t="b"><v>1</v></c>``;
    the One-Pager reads it as the TRUE Excel shows, so it is complete — the shared reader's
    default keeps its stored 1 for every other caller."""
    from schedule_forensics.web.onepager_actions import read_list

    data = twin_xlsx(
        (
            ("Swimlane", "Task", "Start", "Finish", "Complete"),
            ("Alpha", "Kickoff", "1/15/2027", "1/15/2027", "@T"),
            ("Alpha", "Build", "2/1/2027", "4/1/2027", "@F"),
        )
    )
    zin = zipfile.ZipFile(io.BytesIO(data))
    sst = zin.read("xl/sharedStrings.xml").decode()
    index = {s: n for n, s in enumerate(sst.split("<si><t>")[1:]) for s in [s.split("<")[0]]}
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zout:
        for name in zin.namelist():
            body = zin.read(name)
            if name == "xl/worksheets/sheet1.xml":
                text = body.decode()
                for word, bit in (("@T", 1), ("@F", 0)):
                    text = text.replace(f't="s"><v>{index[word]}</v>', f't="b"><v>{bit}</v>')
                body = text.encode()
            zout.writestr(name, body)
    doc = read_list(out.getvalue(), "bool.xlsx", max_bytes=10 * 1024 * 1024)
    assert isinstance(doc, op.OnePagerDoc)
    assert [i.complete for i in doc.items] == [True, False] and doc.completion_notes == ()
