"""Logic links the operator draws on a One-Pager (operator request 2026-09-29, ADR-0539) — the
engine side: item keys, the refusals, the routing, the clearance, the named undrawn links, the
legend, the JSON and the PowerPoint painter.

A One-Pager list carries no logic, so a link is never inferred: the operator picks two items and
the slide draws exactly that arrow. What this module pins:

* **Keys.** A link names its ends by :func:`~schedule_forensics.reports.onepager.item_keys` — a
  unique swimlane-and-name keeps its key when its dates move; a REPEATED name is keyed by its
  dates, so a rolling monthly list re-attaches a link to the 2/15 review and never to whatever
  review now sits in its position; identical twins are told apart; a date window never re-keys.
* **Refusals** (:func:`check_link`), each by name — itself, an unknown item, a duplicate, a loop
  (naming the chain), the cap, an unknown type — while an SS and an FF on one pair are allowed.
* **Routing** (:func:`route_links`): each type leaves the end it names and tips on the end it
  names; a milestone's end is its diamond's centre; the head's tip touches the successor's EDGE
  and the shaft stops at the head's base.
* **Clearance.** No horizontal leg's stroke crosses any glyph — its own ends' included — over
  real ``build_layout`` / ``build_compare_layout`` output from row height 13 down to the label
  floors, each glyph boxed twice: by the router's own ``shape_box`` / ``label_box`` and by an
  independent ink model (so a margin that shrinks cannot shrink the oracle). The one-pager clears
  at every density measured; a DENSE compare slide does not (measured 2026-09-29: 1 hit at 64
  items / row 9.46, 17 at 100 items — legs touching move arrows), and there the layout SAYS so
  (``CROWDED_NOTE``) — a hit is never silent. Legs sharing a channel are stacked on tracks.
  Each glyph kind the router measures (label, NEW tag, check disc, ghost, move arrow) has a
  fixture where it is the ONLY glyph under a leg, so dropping it from the router goes red.
* **Every undrawn link is NAMED**, with its reason; the legend gains ONE link entry, only when a
  link is drawn; the JSON carries links as plain data; the .pptx paints the layout's own head as a
  closed polygon inside one named group whose box is its children's union, with no DrawingML
  line-end, and names the program that wrote it.

Red-first (2026-09-29): on the pristine tree (HEAD 0b45eb2) ``reports/onepager_links`` does not
exist and ``reports.onepager`` has no ``item_keys`` / ``CROWDED_NOTE`` — every test here errors
at import there. Mutation proofs live beside the checks they arm (``test_mutation_*``): each one
breaks the engine or the painter in memory and asserts the SAME checker the real test uses goes
red. One src defect is pinned as a strict xfail — two legs in one channel whose measured bands
differ are offset from DIFFERENT centres, so they can land 0.4 pt apart and merge (see
``test_legs_sharing_a_channel_with_different_bands_never_touch``).
"""

from __future__ import annotations

import datetime as dt
import io
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.reports import onepager_links as links_mod
from schedule_forensics.reports import pptx
from schedule_forensics.reports.onepager import (
    CROWDED_NOTE,
    Layout,
    OnePagerDoc,
    OnePagerItem,
    build_layout,
    item_keys,
    item_label,
    keyed,
    layout_json,
    parse_numbered_workbook,
    windowed_doc,
)
from schedule_forensics.reports.onepager_compare import (
    AMBIGUOUS,
    ARROW_HEAD,
    REMOVED,
    SLIPPED,
    CompareDoc,
    CompareLayout,
    build_compare_layout,
    compare_layout_json,
    compare_onepager_docs,
    row_label,
    window_compare,
)
from schedule_forensics.reports.onepager_links import (
    HALO_W,
    LINK_W,
    MAX_LINKS,
    Anchor,
    Box,
    Grid,
    Link,
    check_link,
    label_box,
    links_table,
    route_links,
    shape_box,
)
from schedule_forensics.reports.xlsx_read import read_xlsx_numbered
from web.onepager_twin import twin_xlsx

D = dt.date
#: A fixed "today" — never the real clock.
TODAY = D(2027, 6, 1)
#: The current sheet layout (ADR-0539): A swimlane · B item · C start · D finish · E complete.
HEADER = ("Swimlane", "Task", "Start", "Finish", "Complete")
_EMU_PER_PT = 12700
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

Glyphs = list[tuple[str, str, Box]]


def _doc(rows: Sequence[tuple[object, ...]], source: str = "list.xlsx") -> OnePagerDoc:
    """A workbook written the way Excel writes one (shared strings, blank rows omitted) and read
    by the path an upload takes — so every key under test is the key a real upload gets."""
    sheets = read_xlsx_numbered(twin_xlsx([HEADER, *rows], omit_blank=True))
    return parse_numbered_workbook(sheets, source)


def _key(doc: OnePagerDoc, name: str, finish: D | None = None) -> str:
    hits = [it for it in doc.items if it.name == name and finish in (None, it.finish)]
    assert len(hits) == 1, (name, finish, [(it.name, it.finish) for it in hits])
    return hits[0].key


def _names(doc: OnePagerDoc) -> dict[str, str]:
    return {it.key: item_label(it) for it in doc.items}


def _emu(pt: float) -> int:
    """Points to EMU, written here and NOT imported, so the painter is judged by an oracle it
    does not share (``pptx._emu`` is compared against it separately)."""
    return round(pt * _EMU_PER_PT)


# ── item keys ─────────────────────────────────────────────────────────────────────────────────


def test_a_unique_item_keeps_its_key_when_its_dates_change() -> None:
    """ADR-0539: a swimlane-and-name that occurs once is keyed date-free — next month's list,
    where the item slipped (and was re-typed with other spacing and case), keeps every link."""
    march = _doc([("Design Team", "PDR", "1/5/2027", "3/20/2027", "")], "march.xlsx")
    april = _doc([("design  team", "PDR", "1/5/2027", "4/30/2027", "")], "april.xlsx")
    assert march.items[0].finish != april.items[0].finish  # the fixture really moved it
    assert march.items[0].key and march.items[0].key == april.items[0].key
    renamed = _doc([("Design Team", "PDR review", "1/5/2027", "3/20/2027", "")])
    assert renamed.items[0].key != march.items[0].key  # the key is the name, not the position


ROLLING_MARCH = [
    ("Program", "Monthly review", "1/15/2027", "1/15/2027", "Complete"),
    ("Program", "Monthly review", "2/15/2027", "2/15/2027", ""),
    ("Program", "Monthly review", "3/15/2027", "3/15/2027", ""),
    ("Program", "Integration", "1/4/2027", "3/1/2027", ""),
]
#: April's update of the same list: the January review rolled off, an April one rolled on.
ROLLING_APRIL = [
    ("Program", "Monthly review", "2/15/2027", "2/15/2027", "Complete"),
    ("Program", "Monthly review", "3/15/2027", "3/15/2027", ""),
    ("Program", "Monthly review", "4/15/2027", "4/15/2027", ""),
    ("Program", "Integration", "1/4/2027", "3/1/2027", ""),
]


def test_a_repeated_name_is_keyed_by_its_dates_never_by_its_position() -> None:
    """The 2/15 review is the SAME review in both months — its link resolves to it, although it
    moved from the second copy to the first. The rolled-off 1/15 review's link is NOT re-attached
    to whatever now sits first: it is left unresolved and named."""
    march, april = _doc(ROLLING_MARCH, "march.xlsx"), _doc(ROLLING_APRIL, "april.xlsx")
    feb_march = _key(march, "Monthly review", D(2027, 2, 15))
    assert feb_march == _key(april, "Monthly review", D(2027, 2, 15))
    jan = _key(march, "Monthly review", D(2027, 1, 15))
    assert jan not in {it.key for it in april.items}
    integ = _key(march, "Integration")
    names = _names(march)
    made = [
        Link(integ, feb_march, "FS", names[integ], names[feb_march]),
        Link(integ, jan, "FS", names[integ], names[jan]),
    ]
    lay = build_layout(april.items, TODAY, "April", links=made)
    assert [(d.pred, d.succ) for d in lay.links] == [(integ, feb_march)]
    feb_placed = next(p for p in lay.items if p.key == feb_march)
    assert feb_placed.finish == "2027-02-15"
    assert lay.links[0].head[0][0] == pytest.approx(feb_placed.x0)  # it tips on THAT diamond
    assert lay.link_notes == [
        f"logic link “{names[integ]}” → “{names[jan]}” (FS) is not drawn — "
        f"“{names[jan]}” is no longer in the list."
    ]


def test_identical_twins_get_distinct_keys_and_each_can_be_linked() -> None:
    """Same swimlane, name AND dates twice: told apart by their order — the one thing left."""
    doc = _doc(
        [
            ("Ops", "Weekly sync", "3/1/2027", "3/1/2027", ""),
            ("Ops", "Weekly sync", "3/1/2027", "3/1/2027", ""),
            ("Ops", "Kickoff", "1/4/2027", "1/4/2027", ""),
        ]
    )
    first, second = (it.key for it in doc.items if it.name == "Weekly sync")
    assert first and second and first != second
    assert item_keys(doc.items) == [it.key for it in doc.items]  # deterministic: re-keying agrees
    kick = _key(doc, "Kickoff")
    lay = build_layout(doc.items, TODAY, "T", links=[Link(kick, second)])
    assert sorted(p.key for p in lay.items) == sorted(it.key for it in doc.items)
    twin2 = next(p for p in lay.items if p.key == second)
    assert [(d.pred, d.succ) for d in lay.links] == [(kick, second)]
    assert lay.links[0].head[0][1] in (
        pytest.approx(twin2.y - lay.ms / 2),
        pytest.approx(twin2.y + lay.ms / 2),
    )


def test_a_date_window_never_renumbers_an_item() -> None:
    """Keys are computed over the WHOLE sheet, once. Re-keying the windowed subset would give the
    in-window copy of a repeated name a date-free key (it no longer repeats there) — the
    discriminating fixture below — and every link to it would silently drop."""
    doc = _doc(
        [
            ("Program", "Review", "1/15/2027", "1/15/2027", ""),
            ("Program", "Review", "5/14/2027", "5/14/2027", ""),
            ("Program", "Build", "4/1/2027", "5/3/2027", ""),
        ]
    )
    window = (D(2027, 4, 1), D(2027, 6, 30))
    shown, omitted = windowed_doc(doc, window)
    assert len(omitted) == 1 and [it.name for it in shown.items] == ["Review", "Build"]
    full = {(it.name, it.finish): it.key for it in doc.items}
    assert [it.key for it in shown.items] == [full[(it.name, it.finish)] for it in shown.items]
    may = full[("Review", D(2027, 5, 14))]
    assert item_keys(shown.items)[0] != may, "the fixture must discriminate a re-keying"
    lay = build_layout(
        shown.items, TODAY, "T", window=window, links=[Link(full[("Build", D(2027, 5, 3))], may)]
    )
    assert {p.key for p in lay.items} == {it.key for it in shown.items}
    assert len(lay.links) == 1 and lay.link_notes == []


def test_placed_items_and_compare_rows_carry_their_keys() -> None:
    """``Placed.key`` / ``PlacedCompare.key`` are what the page's click-to-select names. A compare
    row carries its CURRENT item's key; a row with no current side — REMOVED, or the prior side
    of a DUPLICATE NAME — carries none (a link cannot attach to it)."""
    march, april = _doc(ROLLING_MARCH, "march.xlsx"), _doc(ROLLING_APRIL, "april.xlsx")
    lay = build_layout(april.items, TODAY, "T")
    assert sorted(p.key for p in lay.items) == sorted(it.key for it in april.items)
    cmp = compare_onepager_docs(march, april)
    by_dates = {(r.name, r.prior_finish, r.current_finish): r for r in cmp.rows}
    feb = D(2027, 2, 15)
    assert by_dates[("Monthly review", feb, feb)].key == _key(april, "Monthly review", feb)
    assert by_dates[("Monthly review", D(2027, 1, 15), None)].status == AMBIGUOUS
    assert by_dates[("Monthly review", D(2027, 1, 15), None)].key == ""
    april_review = by_dates[("Monthly review", None, D(2027, 4, 15))]
    assert april_review.key == _key(april, "Monthly review", D(2027, 4, 15))
    clay = build_compare_layout(cmp, TODAY, "T")
    assert sorted(p.key for p in clay.items) == sorted(r.key for r in cmp.rows)
    may = _doc([r for r in ROLLING_APRIL if r[2] != "4/15/2027"], "may.xlsx")
    removed = [r for r in compare_onepager_docs(april, may).rows if r.status == REMOVED]
    assert [(r.prior_finish, r.key) for r in removed] == [(D(2027, 4, 15), "")]


# ── check_link: the refusals ──────────────────────────────────────────────────────────────────

KEYS = ("ka", "kb", "kc", "kd")
NAMES = {"ka": "L · A (1/4/27)", "kb": "L · B (2/1/27)", "kc": "L · C (3/1/27)", "kd": "L · D"}


def test_a_link_is_its_keys_and_type_never_its_labels() -> None:
    """The labels are kept to NAME a link whose item is gone; they are not its identity."""
    a = Link("ka", "kb", "FS", "old label", "old label")
    b = Link("ka", "kb", "FS", "new label", "other")
    assert a == b and hash(a) == hash(b)
    assert Link("ka", "kb", "SS") != a
    assert check_link([a], b, NAMES) == "L · A (1/4/27) → L · B (2/1/27) (FS) is already drawn."


@pytest.mark.parametrize(
    ("new", "expected"),
    [
        (Link("ka", "ka"), "“L · A (1/4/27)” cannot be linked to itself — pick two items."),
        (Link("ka", "gone"), "That item is no longer on the slide — pick it again from the list."),
        (Link("", "kb"), "Pick two items — a From and a To — before adding a logic link."),
        (Link("ka", "kb", "XS"), "Unknown link type “XS” — choose FS, SS, FF or SF."),
        (Link("ka", "kb", "Z" * 50), f"Unknown link type “{'Z' * 20}” — choose FS, SS, FF or SF."),
    ],
)
def test_check_link_refuses_by_name(new: Link, expected: str) -> None:
    assert check_link([], new, NAMES) == expected


def _assert_loop_refused(
    check: Callable[[Sequence[Link], Link, Mapping[str, str]], str | None],
) -> None:
    """A → B → C, then C → A closes a loop: refused, the whole chain named in order."""
    chain = [Link("ka", "kb", "FS"), Link("kb", "kc", "SS")]
    why = check(chain, Link("kc", "ka", "FF"), NAMES)
    assert why is not None, "a link that closes a loop was accepted"
    assert "would close a logic loop" in why
    assert "(L · C (3/1/27) → L · A (1/4/27) → L · B (2/1/27) → L · C (3/1/27))" in why


def test_check_link_refuses_a_loop_naming_the_chain() -> None:
    _assert_loop_refused(check_link)
    # a two-item loop of mixed types is still a loop
    assert "logic loop" in (
        check_link([Link("ka", "kb", "SS")], Link("kb", "ka", "FF"), NAMES) or ""
    )


def test_mutation_the_loop_check_goes_red_when_loop_detection_is_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(links_mod, "_reaches", lambda *_a: None)
    with pytest.raises(AssertionError, match="loop was accepted"):
        _assert_loop_refused(check_link)


def test_an_ss_and_an_ff_on_one_pair_are_both_allowed() -> None:
    """Two relationships between the same two items are two statements, not a duplicate — and
    not a loop (both run A → B)."""
    assert check_link([Link("ka", "kb", "SS")], Link("ka", "kb", "FF"), NAMES) is None
    assert check_link([Link("ka", "kb", "SS")], Link("ka", "kb", "SS", "x", "y"), NAMES)


def test_check_link_caps_the_count_at_exactly_max_links() -> None:
    names = {f"k{i}": f"L · item {i}" for i in range(MAX_LINKS + 2)}
    fan = [Link("k0", f"k{i}") for i in range(1, MAX_LINKS + 1)]  # a fan: no loop anywhere
    assert len(fan) == MAX_LINKS
    new = Link("k1", f"k{MAX_LINKS + 1}")
    assert check_link(fan[:-1], new, names) is None  # one below the cap: accepted
    assert check_link(fan, new, names) == (
        f"A one-pager holds at most {MAX_LINKS} logic links — remove one to add another."
    )


# ── routing semantics ─────────────────────────────────────────────────────────────────────────

#: Two swimlanes, a bar-to-bar in each direction and milestones at both ends of a link.
ROUTE_ROWS = [
    ("Design", "Concept", "1/4/2027", "3/1/2027", ""),
    ("Design", "Gate", "3/15/2027", "3/15/2027", ""),
    ("Build", "Fabricate", "4/5/2027", "7/30/2027", ""),
    ("Build", "Ship", "9/1/2027", "9/1/2027", ""),
]


@pytest.fixture(scope="module")
def route_doc() -> OnePagerDoc:
    return _doc(ROUTE_ROWS)


def _placed(lay: Layout, key: str) -> Any:
    return next(p for p in lay.items if p.key == key)


@pytest.mark.parametrize(
    ("kind", "pred_at", "succ_at"),
    [("FS", "x1", "x0"), ("SS", "x0", "x0"), ("FF", "x1", "x1"), ("SF", "x0", "x1")],
)
def test_each_type_leaves_and_enters_the_end_it_names(
    route_doc: OnePagerDoc, kind: str, pred_at: str, succ_at: str
) -> None:
    """A bar's link point sits 2 pt inside the end the type names (so the arrow visibly meets
    THAT end): FS leaves the predecessor's finish and tips at the successor's start; SS, FF and
    SF likewise. The head's tip lies ON the successor's edge; the shaft ends at the head's base."""
    concept, fab = _key(route_doc, "Concept"), _key(route_doc, "Fabricate")
    lay = build_layout(route_doc.items, TODAY, "T", links=[Link(concept, fab, kind)])
    (ln,) = lay.links
    p, s = _placed(lay, concept), _placed(lay, fab)
    inset = {"x0": 2.0, "x1": -2.0}
    assert ln.shaft[0][0] == pytest.approx(getattr(p, pred_at) + inset[pred_at])
    assert ln.shaft[0][1] == pytest.approx(p.y + lay.bar_h / 2)  # leaves the bottom edge (down)
    tip = ln.head[0]
    assert tip == (
        pytest.approx(getattr(s, succ_at) + inset[succ_at]),
        pytest.approx(s.y - lay.bar_h / 2),
    )  # the successor's TOP edge
    base_y = ln.head[1][1]
    assert ln.head[2][1] == pytest.approx(base_y)
    assert ln.shaft[-1] == (pytest.approx(tip[0]), pytest.approx(base_y))
    assert ln.tag == ("" if kind == "FS" else kind)


def test_a_milestone_end_is_the_diamonds_centre_and_an_upward_link_enters_from_below(
    route_doc: OnePagerDoc,
) -> None:
    """Ship (a milestone in the lower lane) → Gate (a milestone in the upper lane): the shaft
    leaves Ship's TOP vertex, the head tips on Gate's BOTTOM vertex, both at the diamond's centre
    line, whatever the type (a milestone's start is its finish)."""
    ship, gate = _key(route_doc, "Ship"), _key(route_doc, "Gate")
    for kind in ("FS", "SF"):
        lay = build_layout(route_doc.items, D(2027, 1, 1), "T", links=[Link(ship, gate, kind)])
        (ln,) = lay.links
        p, s = _placed(lay, ship), _placed(lay, gate)
        assert ln.shaft[0] == (pytest.approx(p.x0), pytest.approx(p.y - lay.ms / 2))
        assert ln.head[0] == (pytest.approx(s.x0), pytest.approx(s.y + lay.ms / 2))
        assert ln.head[1][1] > ln.head[0][1]  # the base is BELOW the tip: it points up


def _assert_heads_on_edges(lay: Layout) -> None:
    """Every drawn head's tip lies on the successor's top or bottom edge (bar or diamond)."""
    for ln in lay.links:
        s = _placed(lay, ln.succ)
        half = lay.ms / 2 if s.milestone else lay.bar_h / 2
        tip_y = ln.head[0][1]
        assert min(abs(tip_y - (s.y - half)), abs(tip_y - (s.y + half))) < 1e-6, (
            f"the head of {ln.pred_name} → {ln.succ_name} tips at y={tip_y}, off the edge"
        )


def _chain(doc: OnePagerDoc) -> list[Link]:
    keys = [it.key for it in doc.items]
    kinds = ("FS", "SS", "FF", "SF")
    return [Link(a, b, kinds[i % 4]) for i, (a, b) in enumerate(pairwise(keys))]


def test_every_head_tips_on_the_successors_edge(route_doc: OnePagerDoc) -> None:
    lay = build_layout(route_doc.items, TODAY, "T", links=_chain(route_doc))
    assert len(lay.links) == 3
    _assert_heads_on_edges(lay)


def test_mutation_the_edge_check_goes_red_when_the_tip_lands_on_the_centre(
    route_doc: OnePagerDoc, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(links_mod, "_half", lambda _a, _g, _x=None: 0.0)
    lay = build_layout(route_doc.items, TODAY, "T", links=_chain(route_doc))
    with pytest.raises(AssertionError, match="off the edge"):
        _assert_heads_on_edges(lay)


def test_heads_are_sized_by_the_last_leg_and_tags_sit_beside_them(route_doc: OnePagerDoc) -> None:
    """The head's length is the last leg's length held to [0.6, 1.8] pt, its base as wide as it
    is long; a non-FS type is tagged at 70% of the label size (never below 3 pt), on the side
    away from the incoming leg."""
    lay = build_layout(route_doc.items, TODAY, "T", links=_chain(route_doc))
    for ln in lay.links:
        (tx, ty), (bx0, by), (bx1, _by) = ln.head
        length = abs(by - ty)
        assert 0.6 - 1e-9 <= length <= 1.8 + 1e-9
        assert bx1 - bx0 == pytest.approx(length)
        assert (bx0 + bx1) / 2 == pytest.approx(tx)
        if ln.tag:
            assert ln.tag_pt == pytest.approx(max(3.0, lay.label_pt * 0.7))
            leg_from_left = ln.shaft[0][0] <= tx
            assert ln.tag_anchor == ("start" if leg_from_left else "end")
            assert (ln.tag_x > tx) is leg_from_left
    assert max(abs(ln.head[1][1] - ln.head[0][1]) for ln in lay.links) == pytest.approx(1.8)
    # a leg arriving from the RIGHT puts its tag on the left, anchored at its end
    ship, concept = _key(route_doc, "Ship"), _key(route_doc, "Concept")
    back = build_layout(route_doc.items, TODAY, "T", links=[Link(ship, concept, "SS")]).links[0]
    assert back.shaft[0][0] > back.head[0][0]
    assert back.tag == "SS" and back.tag_anchor == "end" and back.tag_x < back.head[0][0]


def _grid(rows: list[float], bands: list[list[Box]]) -> Grid:
    return Grid(rows, bands, rows[0] - 8, rows[-1] + 8, 500.0, 13.0, 8.84, 8.06, 7.8)


def test_the_channel_next_to_the_successor_is_used_unless_it_is_too_narrow() -> None:
    """P (row 0) → S (row 2): the preferred channel is the gap next to S (between rows 1 and 2);
    when a glyph fills that gap over the leg's range, the widest other gap is MEASURED and used."""
    anchors = {
        "p": Anchor(100, 150, 10, False, 0, D(2027, 1, 1), D(2027, 2, 1)),
        "s": Anchor(300, 350, 36, False, 2, D(2027, 3, 1), D(2027, 4, 1)),
    }
    names = {"p": "P", "s": "S"}
    p_box = shape_box(100, 150, 10, False, 8.84, 8.06)  # each end's own bar is a glyph too
    s_box = shape_box(300, 350, 36, False, 8.84, 8.06)
    free: list[list[Box]] = [[p_box], [], [s_box]]
    (ln,), notes, crowded = route_links([Link("p", "s")], anchors, names, _grid([10, 23, 36], free))
    assert 23 < ln.shaft[1][1] < s_box.y0 and not notes and not crowded  # next to the successor
    # row 1 carries a glyph reaching down past the successor's top edge over the leg's range
    blocked: list[list[Box]] = [[p_box], [Box(140, 320, 20, 35.5)], [s_box]]
    (ln,), _notes, crowded = route_links(
        [Link("p", "s")], anchors, names, _grid([10, 23, 36], blocked)
    )
    assert p_box.y1 < ln.shaft[1][1] < 20 and not crowded  # the gap between rows 0 and 1


def test_a_short_bars_link_point_stays_inside_it() -> None:
    """The 2-pt inset shrinks to a third of the bar on a short bar, so the arrow still meets the
    end the type names and never leaves the bar."""
    anchors = {
        "p": Anchor(100, 103, 10, False, 0, D(2027, 1, 1), D(2027, 1, 2)),
        "s": Anchor(300, 350, 23, False, 1, D(2027, 3, 1), D(2027, 4, 1)),
    }
    grid = _grid([10, 23], [[], []])
    fs, ss = route_links(
        [Link("p", "s", "FS"), Link("p", "s", "SS")], anchors, {"p": "P", "s": "S"}, grid
    )[0]
    assert fs.shaft[0][0] == pytest.approx(102.0) and ss.shaft[0][0] == pytest.approx(101.0)


# ── clearance: no horizontal leg through a glyph that is not its own ──────────────────────────


def _ink(x0: float, x1: float, y: float, milestone: bool, lay: Layout | CompareLayout) -> Box:
    """A shape's painted extent with no margin — derived here, not by :func:`shape_box`."""
    if milestone:
        return Box(x0 - lay.ms / 2, x0 + lay.ms / 2, y - lay.ms / 2, y + lay.ms / 2)
    return Box(x0, x1, y - lay.bar_h / 2, y + lay.bar_h / 2)


def _label_ink(p: Any, lay: Layout | CompareLayout, right_pad: float) -> Box:
    """A label's ink by the PAINTERS' rule, not :func:`label_box`'s: the baseline sits
    ``0.35 * label_pt`` below the row centre (``onepager.js`` / ``onepager_compare.js``) and
    Calibri's ascent and descent are 0.75 and 0.25 em."""
    right = p.label_x - right_pad if p.label_anchor == "end" else p.label_x + p.label_w
    base = p.y + 0.35 * lay.label_pt
    return Box(right - p.label_w, right, base - 0.75 * lay.label_pt, base + 0.25 * lay.label_pt)


def _glyphs(lay: Layout | CompareLayout) -> Glyphs:
    """Every glyph the slide paints, by owning key: the shape (and a compare row's ghost), the
    label (with its tag on an end-anchored compare label), the check disc, and on the compare
    slide the move arrow's shaft and head and the NEW / REMOVED tag. Shapes and labels are
    boxed TWICE — by the router's own :func:`shape_box` / :func:`label_box` (what the task
    states the clearance against) and by an independent ink model, so a margin function that
    shrinks cannot shrink the oracle with it."""
    out: Glyphs = []
    compare = isinstance(lay, CompareLayout)
    for p in lay.items:
        if p.x0 is not None and p.x1 is not None:
            out.append((p.key, "shape", shape_box(p.x0, p.x1, p.y, p.milestone, lay.bar_h, lay.ms)))
            out.append((p.key, "shape ink", _ink(p.x0, p.x1, p.y, p.milestone, lay)))
        pad = 0.0
        if compare:
            if p.ghost_x0 is not None and p.ghost_x1 is not None:
                gm = bool(p.ghost_milestone)
                ghost = shape_box(p.ghost_x0, p.ghost_x1, p.y, gm, lay.bar_h, lay.ms)
                out.append((p.key, "ghost", ghost))
                out.append((p.key, "ghost ink", _ink(p.ghost_x0, p.ghost_x1, p.y, gm, lay)))
            if p.arrow_x0 is not None and p.arrow_x1 is not None:
                h = ARROW_HEAD / 2  # the painted head's half-height, not the router's margin
                lo, hi = sorted((p.arrow_x0, p.arrow_x1))
                out.append((p.key, "move arrow", Box(lo, hi, p.arrow_y - h, p.arrow_y + h)))
            if p.badge:  # the painters' tag rect: label_pt * 1.2 tall, centred on the row
                t = lay.label_pt * 0.6
                out.append((p.key, "tag", Box(p.badge_x, p.badge_x + p.badge_w, p.y - t, p.y + t)))
                pad = p.badge_w + 2 if p.label_anchor == "end" else 0.0
        box = label_box(p.label_x, p.label_anchor, p.label_w, p.y, lay.label_pt, pad)
        out.append((p.key, "label", box))
        out.append((p.key, "label ink", _label_ink(p, lay, pad)))
        if p.done_x is not None:
            r = p.done_r
            out.append((p.key, "check", Box(p.done_x - r, p.done_x + r, p.y - r, p.y + r)))
    return out


def _leg_hits(lay: Layout | CompareLayout, own_ends: bool = True) -> list[str]:
    """Each horizontal leg's STROKE (``LINK_W`` thick) against every glyph box on the slide —
    the link's own two items included unless ``own_ends`` is False (a leg must not strike its own
    predecessor's label either; the router measures those glyphs too)."""
    glyphs = _glyphs(lay)
    out: list[str] = []
    for ln in lay.links:
        for (xa, ya), (xb, yb) in zip(ln.shaft, ln.shaft[1:], strict=False):
            if abs(ya - yb) > 1e-9:
                continue
            lo, hi = min(xa, xb), max(xa, xb)
            for key, what, b in glyphs:
                if not own_ends and key in (ln.pred, ln.succ):
                    continue
                if hi >= b.x0 and lo <= b.x1 and ya + LINK_W / 2 > b.y0 and ya - LINK_W / 2 < b.y1:
                    out.append(f"{ln.pred_name} → {ln.succ_name} crosses a {what} at y={ya:.2f}")
    return out


def _sweep_items(n_lanes: int, per_lane: int) -> list[OnePagerItem]:
    """A deterministic list: bars and milestones spread over ~20 months, every fifth complete."""
    out = []
    row = 2
    for li in range(n_lanes):
        for k in range(per_lane):
            start = D(2027, 1, 4) + dt.timedelta(days=(k * 37 + li * 11) % 600)
            ms = (k + li) % 4 == 0
            finish = start if ms else start + dt.timedelta(days=20 + (k * 13) % 90)
            out.append(
                OnePagerItem(f"Lane {li}", f"Item {li}-{k} work", start, finish, row, k % 5 == 0)
            )
            row += 1
    return keyed(out)


def _sweep_links(keys: Sequence[str]) -> list[Link]:
    """Every other item to the next one (the four types in turn), plus longer spans across
    lanes — a mix of short same-row links and legs over many rows."""
    kinds = ("FS", "SS", "FF", "SF")
    out = [Link(keys[i], keys[i + 1], kinds[i % 4]) for i in range(0, len(keys) - 1, 2)]
    return out + [Link(keys[i], keys[i + 7]) for i in range(0, len(keys) - 7, 5)]


#: (swimlanes, items per swimlane): 6 items at row 13 down to 196 at the 4.2-pt label floor.
DENSITIES = ((3, 2), (4, 4), (6, 6), (8, 8), (10, 10), (12, 12), (14, 14))


@pytest.fixture(scope="module")
def onepager_sweep() -> list[Layout]:
    out = []
    for n_lanes, per_lane in DENSITIES:
        its = _sweep_items(n_lanes, per_lane)
        out.append(build_layout(its, TODAY, "T", links=_sweep_links([i.key for i in its])))
    return out


def _compare_sweep_doc(n_lanes: int, per_lane: int) -> CompareDoc:
    """The sweep list as PRIOR; the CURRENT moves most items (slips and pull-ins, so move
    arrows sit above their bars), drops every ninth (REMOVED) and adds one (NEW)."""
    prior = _sweep_items(n_lanes, per_lane)
    current = []
    for i, it in enumerate(prior):
        if i % 9 == 4:
            continue
        shift = dt.timedelta(days=(i % 4) * 15 - 10)
        current.append(replace(it, start=it.start + shift, finish=it.finish + shift, key=""))
    current.append(replace(prior[0], name="Brand new thing", key=""))
    return compare_onepager_docs(
        OnePagerDoc("prior.xlsx", "S", tuple(prior), (), ()),
        OnePagerDoc("current.xlsx", "S", tuple(keyed(current)), (), ()),
    )


@pytest.fixture(scope="module")
def compare_sweep() -> list[CompareLayout]:
    out = []
    for n_lanes, per_lane in DENSITIES[:-1]:
        doc = _compare_sweep_doc(n_lanes, per_lane)
        keys = [r.key for r in doc.rows if r.key]
        out.append(build_compare_layout(doc, TODAY, "T", links=_sweep_links(keys)))
    return out


def test_the_sweep_spans_row_13_down_to_the_label_floors(onepager_sweep: list[Layout]) -> None:
    """The clearance claim below is only as wide as this sweep: it must reach the roomy slide
    AND both label floors (5.0 pt at row 7, 4.2 pt at row 5.5), with links drawn at each."""
    assert onepager_sweep[0].row_h == 13.0 and onepager_sweep[-1].row_h < 6.0
    assert {round(lay.label_pt, 2) for lay in onepager_sweep} >= {7.8, 5.0, 4.2}
    assert all(len(lay.links) >= 3 for lay in onepager_sweep)


def test_no_leg_crosses_a_glyph_on_the_one_pager_at_any_density(
    onepager_sweep: list[Layout],
) -> None:
    for lay in onepager_sweep:
        assert _leg_hits(lay) == [], f"row {lay.row_h:.2f}"
        assert lay.link_notes.count(CROWDED_NOTE) <= 1  # said once per slide, never per link
    assert CROWDED_NOTE not in onepager_sweep[0].link_notes
    assert CROWDED_NOTE in onepager_sweep[-1].link_notes  # the count check above is not vacuous


def test_no_leg_crosses_a_glyph_on_an_uncrowded_compare_and_a_crowded_one_says_so(
    compare_sweep: list[CompareLayout],
) -> None:
    """The compare slide paints a move arrow ABOVE every moved bar, so at density the gap
    between rows can be narrower than a stroke; the layout then carries ``CROWDED_NOTE`` (once).
    A hit is never silent: an uncrowded slide has none."""
    crowded = [CROWDED_NOTE in lay.link_notes for lay in compare_sweep]
    assert any(crowded) and not all(crowded), "the sweep must cover both regimes"
    assert any(p.arrow_x0 is not None for p in compare_sweep[0].items)
    assert all(len(lay.links) >= 2 for lay in compare_sweep)
    for lay, is_crowded in zip(compare_sweep, crowded, strict=True):
        assert lay.link_notes.count(CROWDED_NOTE) <= 1
        hits = _leg_hits(lay)
        assert is_crowded or hits == [], f"row {lay.row_h:.2f}: {hits[:3]}"


def _slipped_compare() -> CompareDoc:
    """Frame (unchanged) and Inspect (a milestone) share the top row; Wiring slipped 60 days in
    the row below, its move arrow reaching up toward the gap a Frame → Inspect leg must use."""

    def doc(source: str, wiring_finish: D) -> OnePagerDoc:
        return OnePagerDoc(
            source,
            "S",
            tuple(
                keyed(
                    [
                        OnePagerItem("Build", "Frame", D(2027, 1, 4), D(2027, 3, 1), 2),
                        OnePagerItem("Build", "Wiring", D(2027, 2, 1), wiring_finish, 3),
                        OnePagerItem("Build", "Inspect", D(2027, 9, 1), D(2027, 9, 1), 4),
                    ]
                )
            ),
            (),
            (),
        )

    return compare_onepager_docs(doc("prior.xlsx", D(2027, 5, 3)), doc("cur.xlsx", D(2027, 7, 2)))


def _slipped_layout() -> CompareLayout:
    doc = _slipped_compare()
    k = {r.name: r.key for r in doc.rows}
    return build_compare_layout(doc, TODAY, "T", links=[Link(k["Frame"], k["Inspect"])])


def test_a_leg_clears_the_move_arrow_of_a_slipped_item() -> None:
    lay = _slipped_layout()
    wiring = next(p for p in lay.items if p.name == "Wiring")
    assert wiring.status == SLIPPED and wiring.arrow_x0 is not None
    (ln,) = lay.links
    assert ln.shaft[1][0] < wiring.arrow_x0 < wiring.arrow_x1 < ln.shaft[-1][0]  # it passes over
    assert _leg_hits(lay) == [] and lay.link_notes == []


@pytest.mark.parametrize(("name", "glyph"), [("Walkdown with a long name", "label"), ("W", "tag")])
def test_a_compare_leg_clears_the_label_and_the_new_tag_of_a_row_it_passes(
    name: str, glyph: str
) -> None:
    """Prime (row 0) → Successor (row 2) runs through the gap next to Successor, over row 1 — a
    NEW item whose short bar ends before the leg begins, so only its LABEL (a long name) or only
    its NEW TAG (a one-letter name) lies under the leg. Either must be measured and cleared."""
    base = [
        OnePagerItem("Build", "Prime", D(2027, 1, 4), D(2027, 3, 1), 2),
        OnePagerItem("Build", "Successor", D(2027, 3, 8), D(2027, 6, 1), 4),
        OnePagerItem("Build", "Late add", D(2028, 1, 3), D(2028, 1, 3), 5),
    ]
    new = OnePagerItem("Build", name, D(2027, 1, 18), D(2027, 1, 29), 3)
    doc = compare_onepager_docs(
        OnePagerDoc("prior.xlsx", "S", tuple(keyed(base)), (), ()),
        OnePagerDoc("cur.xlsx", "S", tuple(keyed([base[0], new, *base[1:]])), (), ()),
    )
    k = {r.name: r.key for r in doc.rows}
    lay = build_compare_layout(doc, TODAY, "T", links=[Link(k["Prime"], k["Successor"])])
    (ln,) = lay.links
    rows = {p.name: p.row for p in lay.items}
    assert (rows["Prime"], rows[name], rows["Successor"]) == (0, 1, 2)
    lo, hi = sorted((ln.shaft[1][0], ln.shaft[2][0]))
    under = {w for key, w, b in _glyphs(lay) if key == k[name] and b.x1 >= lo and b.x0 <= hi}
    assert glyph in under and "shape" not in under, under  # the fixture isolates that glyph
    assert _leg_hits(lay) == [] and lay.link_notes == []


def _under(lay: Layout | CompareLayout, key: str) -> set[str]:
    """Which of ``key``'s glyphs lie under the (only) link's horizontal leg."""
    lo, hi = sorted((lay.links[0].shaft[1][0], lay.links[0].shaft[2][0]))
    return {w for k, w, b in _glyphs(lay) if k == key and b.x1 >= lo and b.x0 <= hi}


@pytest.mark.parametrize(("slide", "next_day"), [("one-pager", 2), ("compare", 3)])
def test_a_leg_clears_a_check_disc_that_is_the_only_glyph_under_it(
    slide: str, next_day: int
) -> None:
    """``Long run`` → ``Next`` (a short FS hop, labels inside their bars) passes over ``Done``,
    a COMPLETE item in the row below whose bar ends just before the hop and whose label starts
    just after it — so its check disc is the one glyph under the leg. (On the compare slide the
    rows are NEW, the only kind whose label may sit inside its bar.)"""
    its = keyed(
        [
            OnePagerItem("Build", "Long run", D(2027, 1, 4), D(2027, 6, 30), 2),
            OnePagerItem("Build", "Done", D(2027, 5, 3), D(2027, 6, 28), 3, True),
            OnePagerItem("Build", "Next", D(2027, 7, next_day), D(2027, 9, 30), 4),
            OnePagerItem("Build", "Far", D(2028, 1, 3), D(2028, 1, 3), 5),
        ]
    )
    lay: Layout | CompareLayout
    if slide == "one-pager":
        k = {i.name: i.key for i in its}
        lay = build_layout(its, TODAY, "T", links=[Link(k["Long run"], k["Next"])])
    else:
        old = OnePagerItem("Other", "Old", D(2027, 1, 4), D(2027, 1, 4), 2)
        doc = compare_onepager_docs(
            OnePagerDoc("prior.xlsx", "S", tuple(keyed([old])), (), ()),
            OnePagerDoc("cur.xlsx", "S", tuple(its), (), ()),
        )
        k = {r.name: r.key for r in doc.rows}
        lay = build_compare_layout(doc, TODAY, "T", links=[Link(k["Long run"], k["Next"])])
    assert _under(lay, k["Done"]) == {"check"}  # the fixture isolates the disc
    assert _leg_hits(lay) == [] and lay.link_notes == []


def test_a_compare_leg_clears_a_prior_ghost_that_is_the_only_glyph_under_it() -> None:
    """``Gone right`` slipped past its own duration: its prior ghost sits under the P → S leg
    while its current bar, its move arrow and its label all lie elsewhere."""

    def doc(source: str, start: D, finish: D) -> OnePagerDoc:
        return OnePagerDoc(
            source,
            "S",
            tuple(
                keyed(
                    [
                        OnePagerItem("Build", "P", D(2027, 1, 4), D(2027, 3, 31), 2),
                        OnePagerItem("Build", "S", D(2027, 4, 30), D(2027, 6, 1), 3),
                        OnePagerItem("Build", "Gone right", start, finish, 4),
                    ]
                )
            ),
            (),
            (),
        )

    cmp = compare_onepager_docs(
        doc("prior.xlsx", D(2027, 3, 15), D(2027, 5, 15)),
        doc("cur.xlsx", D(2027, 7, 1), D(2027, 8, 1)),
    )
    k = {r.name: r.key for r in cmp.rows}
    lay = build_compare_layout(cmp, TODAY, "T", links=[Link(k["P"], k["S"])])
    assert _under(lay, k["Gone right"]) == {"ghost", "ghost ink"}
    assert _leg_hits(lay) == [] and lay.link_notes == []


def _move_head_hits(lay: CompareLayout) -> list[str]:
    """Every link segment — VERTICAL as well as horizontal — whose halo (``HALO_W`` wide, round
    caps, painted ABOVE the items) reaches a move arrow's HEAD as the page paints it (its tip on
    the new finish, ``ARROW_HEAD`` long back toward the old one and as tall), and every link
    head over one. :func:`_leg_hits` skips vertical segments, so it could not see a leg rising
    off a slipped finish through that head (review UIP-2)."""
    out = []
    for p in lay.items:
        if p.arrow_x0 is None or p.arrow_x1 is None:
            continue
        d = 1.0 if p.arrow_x1 >= p.arrow_x0 else -1.0
        tip, back = (p.arrow_x1, p.arrow_y), p.arrow_x1 - d * ARROW_HEAD
        corners = [tip, (back, p.arrow_y - ARROW_HEAD / 2), (back, p.arrow_y + ARROW_HEAD / 2)]
        (ax, ay), (bx, by), (cx, cy) = corners
        n = 10
        pts = [
            ((ax * u + bx * v + cx * (n - u - v)) / n, (ay * u + by * v + cy * (n - u - v)) / n)
            for u in range(n + 1)
            for v in range(n + 1 - u)
        ]
        for ln in lay.links:
            what = f"{ln.pred_name} → {ln.succ_name} ({ln.kind})"
            for a, b in pairwise(ln.shaft):
                hit = sum(_dist(x, y, a, b) < HALO_W / 2 for x, y in pts)
                if hit:
                    leg = "vertical" if abs(a[0] - b[0]) < 1e-9 else "horizontal"
                    out.append(f"{what}: a {leg} leg covers {hit}/{len(pts)} of {p.name}'s head")
            under = sum(_inside(x, y, ln.head) for x, y in pts)
            if under:
                out.append(f"{what}: its head covers {under}/{len(pts)} of {p.name}'s head")
    return out


def _dist(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / span))
    return float(((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5)


def _inside(px: float, py: float, tri: Sequence[tuple[float, float]]) -> bool:
    (x1, y1), (x2, y2), (x3, y3) = tri
    d = [
        (px - bx) * (ay - by) - (ax - bx) * (py - by)
        for (ax, ay), (bx, by) in (((x1, y1), (x2, y2)), ((x2, y2), (x3, y3)), ((x3, y3), (x1, y1)))
    ]
    return not (any(v < 0 for v in d) and any(v > 0 for v in d))


def _moved_compare(design_finish: D) -> CompareDoc:
    """Review UIP-2's list: Design (9/1 → 10/20/26) moves its finish, and PDR — a milestone —
    sits in the row ABOVE Design's bar, so a link between them runs vertically off (or into)
    Design's finish, right where its move arrow's head is drawn."""

    def doc(source: str, finish: D) -> OnePagerDoc:
        return OnePagerDoc(
            source,
            "S",
            tuple(
                keyed(
                    [
                        OnePagerItem("Alpha", "Kickoff", D(2026, 8, 15), D(2026, 8, 15), 2),
                        OnePagerItem("Alpha", "PDR", D(2026, 11, 30), D(2026, 11, 30), 3),
                        OnePagerItem("Alpha", "Design", D(2026, 9, 1), finish, 4),
                        OnePagerItem("Alpha", "Fabrication", D(2026, 12, 10), D(2027, 4, 30), 5),
                    ]
                )
            ),
            (),
            (),
        )

    return compare_onepager_docs(doc("prior.xlsx", D(2026, 10, 20)), doc("cur.xlsx", design_finish))


#: (predecessor, successor, type): off Design's finish (FS / FF) and INTO it (FF / SF).
UIP2 = [
    ("Design", "PDR", "FS"),
    ("Design", "PDR", "FF"),
    ("PDR", "Design", "FF"),
    ("PDR", "Design", "SF"),
]


def _uip2_layout(finish: D, pred: str, succ: str, kind: str) -> CompareLayout:
    doc = _moved_compare(finish)
    k = {r.name: r.key for r in doc.rows}
    return build_compare_layout(doc, TODAY, "T", links=[Link(k[pred], k[succ], kind)])


@pytest.mark.parametrize(("pred", "succ", "kind"), UIP2)
def test_a_link_at_a_slipped_finish_never_covers_its_move_arrow_head(
    pred: str, succ: str, kind: str
) -> None:
    """Review UIP-2: FS / FF leave a bar 2 pt inside its finish and the slip arrow's head spans
    the last 1.8 pt of it — the link's vertical leg and its halo, painted above the items,
    wiped 60 % of the red head off in all four themes. The router now takes the head as ink no
    link may cover (and the .pptx paints the same points)."""
    lay = _uip2_layout(D(2026, 11, 15), pred, succ, kind)
    design = next(p for p in lay.items if p.name == "Design")
    pdr = next(p for p in lay.items if p.name == "PDR")
    assert design.status == SLIPPED and design.arrow_x0 is not None and pdr.row < design.row
    assert len(lay.links) == 1 and lay.link_notes == []
    assert _move_head_hits(lay) == []


@pytest.mark.parametrize(("pred", "succ", "kind"), UIP2)
def test_a_link_at_a_pulled_in_finish_never_covered_its_move_arrow_head(
    pred: str, succ: str, kind: str
) -> None:
    """The review's control (a guard, green on the built tree too): a pull-in's head sits PAST
    the new finish, pointing back, clear of the link's point inside it."""
    lay = _uip2_layout(D(2026, 9, 30), pred, succ, kind)
    assert next(p for p in lay.items if p.name == "Design").arrow_x0 is not None
    assert len(lay.links) == 1 and _move_head_hits(lay) == []


def test_mutation_without_the_move_arrow_keep_outs_a_vertical_leg_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teeth for the oracle AND the fix: the Compare slide stops handing the router its move
    arrows' heads — the same checker names the VERTICAL leg over Design's head."""
    from schedule_forensics.reports import onepager_compare as compare_mod

    monkeypatch.setattr(compare_mod, "_keep_outs", lambda *_a, **_k: ())
    hits = _move_head_hits(_uip2_layout(D(2026, 11, 15), "Design", "PDR", "FS"))
    assert hits and all("a vertical leg covers" in h for h in hits), hits


def test_no_link_covers_a_move_arrow_head_on_any_compare_slide(
    compare_sweep: list[CompareLayout],
) -> None:
    """Every density of the sweep, crowded or not: a move arrow's head says which way a finish
    moved, and no link's halo or head is ever drawn over one."""
    assert sum(p.arrow_x0 is not None for lay in compare_sweep for p in lay.items) > 50
    for lay in compare_sweep:
        assert _move_head_hits(lay) == [], f"row {lay.row_h:.2f}"


def test_mutation_a_naive_row_boundary_channel_is_caught_striking_the_move_arrow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace the MEASURED band with the naive one — the row boundary, half a row below the
    centre — and the same checker reports the leg through the slipped item's move arrow.

    Since review UIP-2 the arrow's HEAD is also ink no link may cover (the Compare slide hands
    the router its move-arrow heads, ``_keep_outs``), a second, independent defense: under the
    naive band alone the router refuses the leg over the head and routes it round the top of
    the slide. So the mutant switches both off to show THIS checker still sees the leg."""
    from schedule_forensics.reports import onepager_compare as compare_mod

    def naive(grid: Grid, j: int, xa: float, xb: float) -> tuple[float, float]:
        c = grid.rows[j] + grid.row_h / 2 if j >= 0 else grid.rows[0] - grid.row_h / 2
        return c - 0.01, c + 0.01

    monkeypatch.setattr(links_mod, "_free", naive)
    monkeypatch.setattr(compare_mod, "_keep_outs", lambda *_a, **_k: ())
    hits = _leg_hits(_slipped_layout(), own_ends=False)
    assert hits and all("crosses a move arrow" in h for h in hits), hits


# ── parallel legs never share a line ──────────────────────────────────────────────────────────


def _merged_legs(lay: Layout | CompareLayout, tol: float) -> list[str]:
    """Pairs of horizontal legs of DIFFERENT links closer than ``tol`` in y over a shared x-range
    (``tol = LINK_W``: their strokes touch; ``1e-6``: exactly collinear)."""
    legs = [
        (i, min(xa, xb), max(xa, xb), ya)
        for i, ln in enumerate(lay.links)
        for (xa, ya), (xb, yb) in zip(ln.shaft, ln.shaft[1:], strict=False)
        if abs(ya - yb) < 1e-9 and abs(xa - xb) > 1e-9
    ]
    out = []
    for n, (i, a0, a1, ay) in enumerate(legs):
        for j, b0, b1, by in legs[n + 1 :]:
            if i != j and abs(ay - by) < tol and min(a1, b1) - max(a0, b0) > 1e-6:
                out.append(f"links {i} and {j}: legs at y={ay:.3f} / {by:.3f} overlap in x")
    return out


def _pair_layout(extra: Sequence[OnePagerItem] = ()) -> Layout:
    """``Prime`` → ``Successor`` twice on one pair — SS and FF, which :func:`check_link` allows —
    both routed through the gap under their shared row, over overlapping x-ranges."""
    its = keyed(
        [
            OnePagerItem("Lane", "Prime contract", D(2027, 1, 4), D(2027, 6, 30), 2),
            *extra,
            OnePagerItem("Lane", "Successor", D(2028, 1, 3), D(2028, 3, 1), 9),
        ]
    )
    p, s = its[0].key, its[-1].key
    pair = [Link(p, s, "FF"), Link(p, s, "SS")]
    assert check_link(pair[:1], pair[1], {p: "P", s: "S"}) is None
    return build_layout(its, TODAY, "T", links=pair)


def test_parallel_legs_in_one_channel_are_stacked_on_separate_tracks() -> None:
    lay = _pair_layout()
    ff, ss = lay.links
    assert ff.shaft[1][1] != ss.shaft[1][1]
    assert abs(ff.shaft[1][1] - ss.shaft[1][1]) == pytest.approx(1.0)  # one track apart
    assert _merged_legs(lay, LINK_W) == [] and lay.link_notes == []


def test_mutation_disabling_the_track_offset_is_caught_as_a_collinear_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(links_mod, "_TRACK", 0.0)
    merged = _merged_legs(_pair_layout(), 1e-6)
    assert merged, "the checker must see the two legs drawn on one line"


def test_no_two_legs_are_collinear_unless_the_slide_says_it_is_crowded(
    onepager_sweep: list[Layout], compare_sweep: list[CompareLayout]
) -> None:
    layouts: list[Layout | CompareLayout] = [*onepager_sweep, *compare_sweep]
    assert any(CROWDED_NOTE not in lay.link_notes and lay.links for lay in layouts)
    for lay in layouts:
        merged = _merged_legs(lay, 1e-6)
        assert CROWDED_NOTE in lay.link_notes or merged == [], (lay.row_h, merged[:3])


def test_legs_sharing_a_channel_with_different_bands_never_touch() -> None:
    """A complete item in the row below puts its LABEL (not its bar) under the FF leg's range and
    its bar under the SS leg's — the two measured bands differ by 0.6 pt."""
    crossing = OnePagerItem(
        "Lane", "Crossing label item runs long", D(2027, 2, 1), D(2027, 5, 1), 3, True
    )
    lay = _pair_layout([crossing])
    # either remedy — separate the strokes, or say the slide is crowded — makes this pass
    assert CROWDED_NOTE in lay.link_notes or _merged_legs(lay, LINK_W) == []


# ── undrawn links are named ───────────────────────────────────────────────────────────────────

WINDOW_ROWS = [
    ("A", "Straddle", "1/4/2027", "4/1/2027", ""),
    ("A", "Inside", "5/3/2027", "5/28/2027", ""),
    ("A", "Later", "9/1/2027", "9/1/2027", ""),
]
WINDOW = (D(2027, 3, 1), D(2027, 6, 30))


def _window_layout(links: Sequence[Link]) -> tuple[Layout, dict[str, str]]:
    """The page's own recipe: the list scoped to the window; every item of the FULL list named;
    each one the window hides given its reason."""
    full = _doc(WINDOW_ROWS)
    shown, _omitted = windowed_doc(full, WINDOW)
    names = _names(full)
    absent = {
        k: "is outside the date window" for k in names if k not in {it.key for it in shown.items}
    }
    lay = build_layout(
        shown.items, TODAY, "T", window=WINDOW, links=links, names=names, absent=absent
    )
    return lay, {it.name: it.key for it in full.items}


def _assert_straddler_start_named(lay: Layout, straddle: str, inside: str) -> None:
    drawn = {(d.pred, d.succ, d.kind) for d in lay.links}
    assert (straddle, inside, "FS") in drawn  # its FINISH is inside the window: drawn
    assert (straddle, inside, "SS") not in drawn, "an end dated outside the window was drawn"
    assert (
        "logic link “A · Straddle (1/4/27 to 4/1/27)” → “A · Inside (5/3/27 to 5/28/27)” (SS) "
        "is not drawn — “A · Straddle (1/4/27 to 4/1/27)”: its start (2027-01-04) is outside "
        "the date window."
    ) in lay.link_notes


def test_an_end_dated_outside_the_window_is_named_though_its_item_straddles_it() -> None:
    """The straddler is ON the slide (cut at the edge), so FS from its finish (4/1, inside) is
    drawn — but SS leaves its START (1/4, outside): cut in x, never in date, so it is named."""
    _lay, k = _window_layout([])
    links = [Link(k["Straddle"], k["Inside"], "FS"), Link(k["Straddle"], k["Inside"], "SS")]
    lay, _k = _window_layout(links)
    _assert_straddler_start_named(lay, k["Straddle"], k["Inside"])


def test_mutation_the_straddler_check_goes_red_when_end_dates_are_not_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _lay, k = _window_layout([])
    monkeypatch.setattr(links_mod, "_off_slide", lambda *_a: None)
    links = [Link(k["Straddle"], k["Inside"], "FS"), Link(k["Straddle"], k["Inside"], "SS")]
    lay, _k = _window_layout(links)
    with pytest.raises(AssertionError, match="dated outside the window was drawn"):
        _assert_straddler_start_named(lay, k["Straddle"], k["Inside"])


def test_an_item_the_window_hides_is_named_by_the_reason_given() -> None:
    _lay, k = _window_layout([])
    lay, _k = _window_layout([Link(k["Inside"], k["Later"])])
    assert lay.links == []
    assert lay.link_notes == [
        "logic link “A · Inside (5/3/27 to 5/28/27)” → “A · Later (9/1/27)” (FS) is not drawn "
        "— “A · Later (9/1/27)” is outside the date window."
    ]


def test_an_item_no_longer_in_the_list_is_named_by_its_saved_label() -> None:
    doc = _doc(ROUTE_ROWS)
    gate = _key(doc, "Gate")
    gone = Link("0123456789abcdef", gate, "FS", "Design · Old task (2/1/27)", "")
    nameless = Link(gate, "fedcba9876543210")
    lay = build_layout(doc.items, TODAY, "T", links=[gone, nameless])
    assert lay.links == []
    assert lay.link_notes == [
        "logic link “Design · Old task (2/1/27)” → “Design · Gate (3/15/27)” (FS) is not drawn "
        "— “Design · Old task (2/1/27)” is no longer in the list.",
        "logic link “Design · Gate (3/15/27)” → “an item” (FS) is not drawn — “an item” is no "
        "longer in the list.",
    ]


def test_an_item_placed_below_the_slide_is_named() -> None:
    """A list too long for one slide at the smallest size places its last rows below it; a link
    to one of those is named, never drawn off the page."""
    its = keyed(
        [
            OnePagerItem("Only lane", f"Overlap {n}", D(2027, 1, 4), D(2027, 3, 1), n + 2)
            for n in range(130)
        ]
    )
    lay = build_layout(its, TODAY, "T", links=[Link(its[0].key, its[-1].key)])
    assert any("does not fit one slide" in n for n in lay.notes)
    assert lay.links == []
    assert lay.link_notes == [
        "logic link “Only lane · Overlap 0 (1/4/27 to 3/1/27)” → “Only lane · Overlap 129 "
        "(1/4/27 to 3/1/27)” (FS) is not drawn — “Only lane · Overlap 129 (1/4/27 to 3/1/27)”: "
        "it runs off the bottom of the slide (the list does not fit one slide)."
    ]


def test_a_compare_link_to_a_row_that_became_removed_is_named() -> None:
    """A link made on March → April; in April → May the successor is gone — REMOVED, with no
    current side — so the link is named by the label it was made with."""
    march, april = _doc(ROLLING_MARCH, "march.xlsx"), _doc(ROLLING_APRIL, "april.xlsx")
    first = compare_onepager_docs(march, april)
    by_name = {(r.name, r.current_finish): r for r in first.rows if r.key}
    integ = by_name[("Integration", D(2027, 3, 1))]
    review = by_name[("Monthly review", D(2027, 4, 15))]
    link = Link(integ.key, review.key, "FS", row_label(integ), row_label(review))
    assert build_compare_layout(first, TODAY, "T", links=[link]).links  # drawn while it exists
    may = _doc([r for r in ROLLING_APRIL if r[2] != "4/15/2027"], "may.xlsx")
    second = compare_onepager_docs(april, may)
    gone = [r for r in second.rows if r.status == REMOVED]
    assert [(r.name, r.prior_finish, r.key) for r in gone] == [
        ("Monthly review", D(2027, 4, 15), "")
    ]
    lay = build_compare_layout(second, TODAY, "T", links=[link])
    assert lay.links == []
    assert lay.link_notes == [
        "logic link “Program · Integration (1/4/27 to 3/1/27)” → “Program · Monthly review "
        "(4/15/27)” (FS) is not drawn — “Program · Monthly review (4/15/27)” is no longer in "
        "the list."
    ]


def test_a_compare_row_with_no_current_position_on_the_slide_is_named() -> None:
    """Windowed compare: a row that slipped OUT of the window stays (its prior touches it) but
    has no current shape there — a link to it is named, not drawn to a ghost."""
    prior = _doc(
        [
            ("A", "Anchor", "3/1/2027", "3/1/2027", ""),
            ("A", "Slides out", "5/3/2027", "6/1/2027", ""),
        ],
        "p.xlsx",
    )
    current = _doc(
        [
            ("A", "Anchor", "3/1/2027", "3/1/2027", ""),
            ("A", "Slides out", "8/2/2027", "9/1/2027", ""),
        ],
        "c.xlsx",
    )
    cmp, _omitted = window_compare(compare_onepager_docs(prior, current), WINDOW)
    k = {r.name: r for r in cmp.rows}
    link = Link(k["Anchor"].key, k["Slides out"].key)
    lay = build_compare_layout(cmp, TODAY, "T", window=WINDOW, links=[link])
    assert lay.links == []
    assert lay.link_notes == [
        "logic link “A · Anchor (3/1/27)” → “A · Slides out (8/2/27 to 9/1/27)” (FS) is not "
        "drawn — “A · Slides out (8/2/27 to 9/1/27)” has no current position on this slide."
    ]


# ── the legend, the JSON, the Excel table ─────────────────────────────────────────────────────


def _link_entries(lay: Layout | CompareLayout) -> list[str]:
    return [e.label for e in lay.legend if e.kind == "link"]


def test_the_legend_gains_exactly_one_link_entry_only_when_a_link_is_drawn(
    route_doc: OnePagerDoc,
) -> None:
    concept, gate = _key(route_doc, "Concept"), _key(route_doc, "Gate")
    none = build_layout(route_doc.items, TODAY, "T")
    undrawn = build_layout(route_doc.items, TODAY, "T", links=[Link(concept, "gone")])
    fs_only = build_layout(route_doc.items, TODAY, "T", links=[Link(concept, gate)])
    tagged = build_layout(route_doc.items, TODAY, "T", links=_chain(route_doc))
    assert _link_entries(none) == [] and _link_entries(undrawn) == [] and undrawn.link_notes
    assert _link_entries(fs_only) == ["Logic link (finish-to-start)"]
    assert _link_entries(tagged) == ["Logic link (finish-to-start; FF/SS tagged)"]
    cmp = _slipped_compare()
    k = {r.name: r.key for r in cmp.rows}
    assert _link_entries(build_compare_layout(cmp, TODAY, "T")) == []
    one = build_compare_layout(cmp, TODAY, "T", links=[Link(k["Frame"], k["Inspect"], "SF")])
    assert _link_entries(one) == ["Logic link (finish-to-start; SF tagged)"]


def test_the_legend_names_the_status_column_the_list_used() -> None:
    """``status_column`` (ADR-0539): the check's legend entry and ``Layout.status_label`` name
    column E for a list in the current layout — and no column when none is given."""
    doc = _doc([("Ops", "Done thing", "1/4/2027", "2/1/2027", "Complete")])
    assert doc.status_column == "E"
    named = build_layout(doc.items, TODAY, "T", status_column=doc.status_column)
    assert named.status_label == "column E"
    assert [e.label for e in named.legend if e.kind == "done"] == ["Complete (column E)"]
    unsaid = build_layout(doc.items, TODAY, "T")
    assert unsaid.status_label == ""
    assert [e.label for e in unsaid.legend if e.kind == "done"] == ["Complete"]


def test_layout_json_carries_links_and_their_notes_as_plain_data(route_doc: OnePagerDoc) -> None:
    concept = _key(route_doc, "Concept")
    links = [*_chain(route_doc), Link(concept, "gone")]
    lay = build_layout(route_doc.items, TODAY, "T", links=links)
    data = json.loads(json.dumps(layout_json(lay)))
    assert data["link_notes"] == lay.link_notes and len(data["link_notes"]) == 1
    assert len(data["links"]) == len(lay.links) == 3
    for got, ln in zip(data["links"], lay.links, strict=True):
        assert got["pred"] == ln.pred and got["succ"] == ln.succ and got["kind"] == ln.kind
        assert got["shaft"] == [list(pt) for pt in ln.shaft]
        assert got["head"] == [list(pt) for pt in ln.head]
        assert got["tag"] == ln.tag and got["pred_name"] == ln.pred_name
    assert [p["key"] for p in data["items"]] == [p.key for p in lay.items]
    clay = _slipped_layout()
    cdata = json.loads(json.dumps(compare_layout_json(clay)))
    assert cdata["links"][0]["shaft"] == [list(pt) for pt in clay.links[0].shaft]


def test_links_table_lists_every_link_made_and_whether_the_slide_draws_it(
    route_doc: OnePagerDoc,
) -> None:
    concept, gate = _key(route_doc, "Concept"), _key(route_doc, "Gate")
    made = [
        Link(concept, gate, "FS", "Design · Concept", "Design · Gate"),
        Link(concept, "gone", "SF", "Design · Concept", "Design · Removed"),
    ]
    lay = build_layout(route_doc.items, TODAY, "T", links=made)
    table = links_table(made, lay.links, lay.link_notes)
    assert table.title == "Logic links"
    assert table.headers == ("From", "To", "Type", "On the slide")
    assert table.rows == (
        ("Design · Concept", "Design · Gate", "Finish-to-Start (FS)", "yes"),
        ("Design · Concept", "Design · Removed", "Start-to-Finish (SF)", "no — see the note below"),
        ("", "", "note", lay.link_notes[0]),
    )


# ── the PowerPoint painter ────────────────────────────────────────────────────────────────────


def _slide(data: bytes) -> ET.Element:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return ET.fromstring(zf.read("ppt/slides/slide1.xml"))


def _name(el: ET.Element) -> str:
    c = el.find(f"{{{_P}}}nvGrpSpPr/{{{_P}}}cNvPr")
    if c is None:
        c = el.find(f"{{{_P}}}nvSpPr/{{{_P}}}cNvPr")
    return "" if c is None else c.get("name", "")


def _link_groups(root: ET.Element) -> list[ET.Element]:
    return [g for g in root.iter(f"{{{_P}}}grpSp") if _name(g).startswith("Logic link: ")]


def _box(xfrm: ET.Element, off: str = "off", ext: str = "ext") -> tuple[int, int, int, int]:
    o, e = xfrm.find(f"{{{_A}}}{off}"), xfrm.find(f"{{{_A}}}{ext}")
    assert o is not None and e is not None
    return int(o.get("x", "")), int(o.get("y", "")), int(e.get("cx", "")), int(e.get("cy", ""))


def _group_box_errors(root: ET.Element) -> list[str]:
    """Each link group's ``off``/``ext`` (and ``chOff``/``chExt``) against the union of its
    children's own boxes."""
    out = []
    for g in _link_groups(root):
        xfrm = g.find(f"{{{_P}}}grpSpPr/{{{_A}}}xfrm")
        assert xfrm is not None
        kids = [
            _box(x)
            for sp in g.findall(f"{{{_P}}}sp")
            if (x := sp.find(f"{{{_P}}}spPr/{{{_A}}}xfrm")) is not None
        ]
        x0, y0 = min(b[0] for b in kids), min(b[1] for b in kids)
        union = (x0, y0, max(b[0] + b[2] for b in kids) - x0, max(b[1] + b[3] for b in kids) - y0)
        for which in (_box(xfrm), _box(xfrm, "chOff", "chExt")):
            if which != union:
                out.append(f"{_name(g)}: {which} != union {union}")
    return out


def _path(sp: ET.Element) -> tuple[ET.Element, list[tuple[int, int]]]:
    path = sp.find(f"{{{_P}}}spPr/{{{_A}}}custGeom/{{{_A}}}pathLst/{{{_A}}}path")
    assert path is not None, f"{_name(sp)} is not a custom-geometry shape"
    pts = [(int(pt.get("x", "")), int(pt.get("y", ""))) for pt in path.iter(f"{{{_A}}}pt")]
    return path, pts


def _relative(
    points: Sequence[tuple[float, float]],
) -> tuple[tuple[int, int], list[tuple[int, int]]]:
    x0, y0 = min(x for x, _ in points), min(y for _, y in points)
    return (_emu(x0), _emu(y0)), [(_emu(x - x0), _emu(y - y0)) for x, y in points]


def _lockstep_errors(root: ET.Element, lay: Layout | CompareLayout) -> list[str]:
    """Every drawn link's group holds a CLOSED head of the layout's own points and an OPEN
    shaft (and halo) of the layout's own polyline — relative to each shape's offset, in EMU —
    and no DrawingML line-end."""
    out = []
    groups = {_name(g): g for g in _link_groups(root)}
    for ln in lay.links:
        what = f"{ln.pred_name} → {ln.succ_name} ({ln.kind})"
        g = groups.get(f"Logic link: {what}")
        if g is None:
            out.append(f"no group for {what}")
            continue
        kids = {_name(sp).split(":")[0]: sp for sp in g.findall(f"{{{_P}}}sp")}
        head_path, head_pts = _path(kids["Logic link head"])
        want_off, want_pts = _relative(ln.head)
        head_xfrm = kids["Logic link head"].find(f"{{{_P}}}spPr/{{{_A}}}xfrm")
        assert head_xfrm is not None
        if _box(head_xfrm)[:2] != want_off or head_pts != want_pts:
            out.append(f"{what}: head {head_pts} at {_box(head_xfrm)[:2]} != {want_pts}")
        if head_path.find(f"{{{_A}}}close") is None or head_path.get("fill") == "none":
            out.append(f"{what}: the head is not a closed, filled polygon")
        for part in ("Logic link line", "Logic link halo"):
            path, pts = _path(kids[part])
            if pts != _relative(ln.shaft)[1]:
                out.append(f"{what}: {part} {pts} != the layout's shaft")
            if path.get("fill") != "none" or path.find(f"{{{_A}}}close") is not None:
                out.append(f"{what}: {part} is not an open, unfilled path")
        if "tailEnd" in ET.tostring(g, encoding="unicode"):
            out.append(f"{what}: carries a DrawingML line-end")
    return out


@pytest.fixture(scope="module")
def linked_layout() -> Layout:
    doc = _doc(ROUTE_ROWS)
    return build_layout(doc.items, TODAY, "T", links=[*_chain(doc), Link(doc.items[0].key, "x")])


def _render(lay: Layout, **kw: str) -> bytes:
    return pptx.render_onepager_pptx(lay, marking="CUI", source="Source: list.xlsx", **kw)


def test_the_pptx_paints_one_named_group_per_drawn_link(linked_layout: Layout) -> None:
    root = _slide(_render(linked_layout))
    names = [_name(g) for g in _link_groups(root)]
    assert len(linked_layout.links) == 3 and len(linked_layout.link_notes) == 1
    assert names == [
        f"Logic link: {ln.pred_name} → {ln.succ_name} ({ln.kind})" for ln in linked_layout.links
    ]


def test_mutation_the_group_count_goes_red_when_links_are_not_grouped(
    linked_layout: Layout, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pptx._Slide, "group", lambda self, start, name: None)
    assert _link_groups(_slide(_render(linked_layout))) == []


def test_each_link_groups_box_is_the_union_of_its_childrens_boxes(linked_layout: Layout) -> None:
    root = _slide(_render(linked_layout))
    assert _group_box_errors(root) == []


def test_mutation_a_group_box_that_is_not_the_union_is_caught(linked_layout: Layout) -> None:
    root = _slide(_render(linked_layout))
    g = _link_groups(root)[0]
    off = g.find(f"{{{_P}}}grpSpPr/{{{_A}}}xfrm/{{{_A}}}off")
    assert off is not None
    off.set("x", str(int(off.get("x", "0")) + 1))  # one EMU of drift, in memory
    assert len(_group_box_errors(root)) == 1


def test_the_pptx_head_and_shaft_are_the_layouts_own_points(linked_layout: Layout) -> None:
    """DrawingML's own line-end heads are sized by the renderer; this head is the layout's
    polygon, so the page and the slide draw the SAME head."""
    assert pptx._emu(123.456) == _emu(123.456)  # the painter's conversion is the oracle's
    root = _slide(_render(linked_layout))
    assert _lockstep_errors(root, linked_layout) == []
    compare = _slipped_layout()
    croot = _slide(pptx.render_onepager_compare_pptx(compare, marking="CUI", source="s"))
    assert len(_link_groups(croot)) == 1 and _lockstep_errors(croot, compare) == []
    assert _group_box_errors(croot) == []


def test_mutation_a_head_drawn_off_the_layouts_points_is_caught(
    linked_layout: Layout, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = pptx._Slide.freeform

    def nudged(self: Any, points: list[tuple[float, float]], **kw: Any) -> None:
        if kw.get("closed"):
            points = [(x, y + 0.5) if i == 0 else (x, y) for i, (x, y) in enumerate(points)]
        real(self, points, **kw)

    monkeypatch.setattr(pptx._Slide, "freeform", nudged)
    errors = _lockstep_errors(_slide(_render(linked_layout)), linked_layout)
    assert len(errors) == len(linked_layout.links) and all(": head " in e for e in errors)


def test_the_legend_link_is_a_line_and_a_head_never_a_rounded_bar(linked_layout: Layout) -> None:
    root = _slide(_render(linked_layout))
    shapes = {_name(sp): sp for sp in root.iter(f"{{{_P}}}sp")}
    for name, closed in (("Legend: link", False), ("Legend: link head", True)):
        sp = shapes[name]
        assert sp.find(f"{{{_P}}}spPr/{{{_A}}}prstGeom") is None, f"{name} is a preset shape"
        path, _pts = _path(sp)
        assert (path.find(f"{{{_A}}}close") is not None) is closed
    bare = build_layout(_doc(ROUTE_ROWS).items, TODAY, "T")
    assert not any(
        n.startswith("Legend: link")
        for n in (_name(sp) for sp in _slide(_render(bare)).iter(f"{{{_P}}}sp"))
    )


def _props(data: bytes) -> tuple[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        core, app = (
            ET.fromstring(zf.read("docProps/core.xml")),
            ET.fromstring(zf.read("docProps/app.xml")),
        )
    creator = next(el.text for el in core.iter() if el.tag.endswith("}creator"))
    application = next(el.text for el in app.iter() if el.tag.endswith("}Application"))
    return creator or "", application or ""


def test_the_deck_names_the_program_that_wrote_it(linked_layout: Layout) -> None:
    """LODESTAR, the standalone One-Pager program, names itself; POLARIS² stays the default."""
    assert _props(_render(linked_layout)) == ("POLARIS²", "POLARIS²")
    assert _props(_render(linked_layout, product="LODESTAR")) == ("LODESTAR", "LODESTAR")
    compare = _slipped_layout()
    for product in ("POLARIS²", "LODESTAR"):
        kw = {} if product == "POLARIS²" else {"product": product}
        data = pptx.render_onepager_compare_pptx(compare, marking="CUI", source="s", **kw)
        assert _props(data) == (product, product)


# ── an independent reader: LibreOffice Impress ────────────────────────────────────────────────

#: A deck PowerPoint wrote (non-CUI, ADR-0152) — the control that proves the instrument works.
_CONTROL = (
    Path(__file__).resolve().parents[2]
    / "00_REFERENCE_INTAKE"
    / "mpp"
    / "Politte Schedule Tool.pptx"
)


def _to_fodp(soffice: str, src: Path, outdir: Path) -> Path | None:
    """``src`` -> flat ODF; the ARTIFACT is the verdict (``soffice`` exits 0 when it refuses a
    file), and a leftover from an earlier run is unlinked first."""
    outdir.mkdir(parents=True, exist_ok=True)
    produced = outdir / (src.stem + ".fodp")
    produced.unlink(missing_ok=True)
    subprocess.run(
        [
            soffice,
            f"-env:UserInstallation=file://{outdir / '_lo_profile'}",
            "--headless",
            "--norestore",
            "--convert-to",
            "fodp",
            "--outdir",
            str(outdir),
            str(src),
        ],
        capture_output=True,
        timeout=300,
        check=False,
    )
    return produced if produced.exists() else None


def test_libreoffice_reads_the_link_groups_back_by_name(
    linked_layout: Layout, tmp_path: Path
) -> None:
    """The group names are the operator's handle on a link in the selection pane — they must
    survive another program's import, not only our own XML."""
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if exe is None or not _CONTROL.exists():
        pytest.skip("LibreOffice or the PowerPoint-authored control deck is absent")
    if _to_fodp(exe, _CONTROL, tmp_path / "control") is None:
        pytest.skip("this LibreOffice cannot import a PowerPoint-authored deck (no Impress)")
    src = tmp_path / "links.pptx"
    src.write_bytes(_render(linked_layout))
    produced = _to_fodp(exe, src, tmp_path / "out")
    assert produced is not None, "LibreOffice refused the deck while loading the control"
    names = {
        v
        for el in ET.parse(produced).getroot().iter()
        for k, v in el.attrib.items()
        if k.endswith("}name")
    }
    want = {
        f"Logic link: {ln.pred_name} → {ln.succ_name} ({ln.kind})" for ln in linked_layout.links
    }
    assert want <= names, sorted(want - names)
