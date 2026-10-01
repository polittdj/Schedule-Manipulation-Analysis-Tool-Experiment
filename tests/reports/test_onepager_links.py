"""Logic links the operator draws on a One-Pager (operator request 2026-09-29, ADR-0539) — the
engine side: item keys, the refusals, the routing on real slides, the named undrawn links, the
legend, the JSON and the PowerPoint painter. The routing RULE itself (ADR-0543, the design
handoff's Console rule, step by step and against the prototype's own routes) is pinned in
``tests/reports/test_onepager_links_console.py``.

A One-Pager list carries no logic, so a link is never inferred: the operator picks two items and
the slide draws exactly that arrow. What this module pins:

* **Keys.** A link names its ends by :func:`~schedule_forensics.reports.onepager.item_keys` — a
  unique swimlane-and-name keeps its key when its dates move; a REPEATED name is keyed by its
  dates, so a rolling monthly list re-attaches a link to the 2/15 review and never to whatever
  review now sits in its position; identical twins are told apart; a date window never re-keys.
* **Refusals** (:func:`check_link`), each by name — itself, an unknown item, a duplicate, a loop
  (naming the chain), the cap, an unknown type — while an SS and an FF on one pair are allowed.
* **Routing on real slides** (``build_layout`` / ``build_compare_layout``): each type leaves the
  EDGE it names at the item's centre line (a milestone's: its own diamond's side vertex) and its
  head tips on the successor's edge, 4.2 pt long; a non-FS type is tagged at 5 pt beside the first
  vertical leg. Every link whose two ends are on the slide is drawn, at every density of the
  sweep, with no note — the shafts run UNDER the items, so nothing is ever "crowded" or
  "flagged" (ADR-0543 retired ADR-0540's escalation, footnote and gutter). A link head is the
  only part of a link painted over the items, and none lands on a Compare move arrow's head.
* **Every undrawn link is NAMED**, with its reason; the legend gains ONE link entry, only when a
  link is drawn; the JSON carries links as plain data.
* **The PowerPoint**, in the page's z-order: each link's SHAFT is a group of its own ("Logic
  link: …") painted after the lanes and BEFORE the first item; its HEAD and type tag a second
  group ("Logic link arrowhead: …") AFTER the items' labels and BEFORE the data-date line; each
  group's box is its children's union; the head is the layout's own closed polygon and the shaft
  its own open polyline, with no DrawingML line-end, no halo, no dash; the labels outside their
  bars and the type tags glow in the slide's white, and nothing else does.

Red first: the keys, refusals, not-drawn and legend pins predate ADR-0543 and are unchanged. The
routing and PowerPoint pins were rewritten for ADR-0543 and are red on the pristine tree
(fac5773): its heads tipped on the successor's top or bottom edge, its tags were 70 % of the
label size, its densest sweep slides carried the crowding note, and its .pptx painted each link
as ONE group (halo, line, head, tag) after the labels. Mutation proofs live beside the checks
they arm (``test_mutation_*``).
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
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
    LABEL_MAX,
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
    REMOVED,
    CompareDoc,
    CompareLayout,
    build_compare_layout,
    compare_layout_json,
    compare_onepager_docs,
    row_label,
    window_compare,
)
from schedule_forensics.reports.onepager_links import (
    HEAD,
    MAX_LINKS,
    Link,
    check_link,
    links_table,
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
    # it tips on THAT diamond: FS enters a milestone at its LEFT vertex (ADR-0543)
    tip = (feb_placed.x0 - feb_placed.ms / 2, feb_placed.y)
    assert lay.links[0].head[0] == pytest.approx(tip)
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
    twin1 = next(p for p in lay.items if p.key == first)
    assert twin1.y != twin2.y  # identical twins stack: the head's row says which one it joins
    assert lay.links[0].head[0] == pytest.approx((twin2.x0 - twin2.ms / 2, twin2.y))


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


# ── routing semantics, on real slides ───────────────────────────────────────────────────────

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


def _edges(p: Any) -> tuple[float, float]:
    """An item's shape edges as the painters draw it: a bar's two ends, a milestone's centre ±
    half its OWN diamond (``Placed.ms``, clamped at the chart's edge)."""
    return (p.x0 - p.ms / 2, p.x0 + p.ms / 2) if p.milestone else (p.x0, p.x1)


@pytest.mark.parametrize(
    ("kind", "pred_at", "succ_at"),
    [("FS", 1, 0), ("SS", 0, 0), ("FF", 1, 1), ("SF", 0, 1)],
)
def test_each_type_leaves_and_enters_the_end_it_names(
    route_doc: OnePagerDoc, kind: str, pred_at: int, succ_at: int
) -> None:
    """A finish end is the item's RIGHT edge, a start end its LEFT edge, both at its centre line
    (README step 1): FS leaves the predecessor's finish and tips at the successor's start; SS, FF
    and SF likewise. The head's tip lies ON the successor's edge, the shaft ends at the head's
    base, and the base is :data:`HEAD` back along the last leg."""
    concept, fab = _key(route_doc, "Concept"), _key(route_doc, "Fabricate")
    lay = build_layout(route_doc.items, TODAY, "T", links=[Link(concept, fab, kind)])
    (ln,) = lay.links
    p, s = _placed(lay, concept), _placed(lay, fab)
    assert ln.shaft[0] == pytest.approx((_edges(p)[pred_at], p.y))
    tip = ln.head[0]
    assert tip == pytest.approx((_edges(s)[succ_at], s.y))
    into = 1 if succ_at == 0 else -1
    assert ln.shaft[-1] == pytest.approx((tip[0] - into * HEAD, tip[1]))
    assert ln.tag == ("" if kind == "FS" else kind)


def test_a_milestone_end_is_its_own_diamonds_side_vertex(route_doc: OnePagerDoc) -> None:
    """Ship (a milestone in the lower lane) → Gate (a milestone in the upper lane): FS leaves
    Ship's RIGHT vertex and tips on Gate's LEFT one; SF the other two — each diamond at its own
    size, at its centre line."""
    ship, gate = _key(route_doc, "Ship"), _key(route_doc, "Gate")
    for kind, out_at, in_at in (("FS", 1, 0), ("SF", 0, 1)):
        lay = build_layout(route_doc.items, D(2027, 1, 1), "T", links=[Link(ship, gate, kind)])
        (ln,) = lay.links
        p, s = _placed(lay, ship), _placed(lay, gate)
        assert p.milestone and s.milestone and p.ms > 0 and s.ms > 0
        assert ln.shaft[0] == pytest.approx((_edges(p)[out_at], p.y))
        assert ln.head[0] == pytest.approx((_edges(s)[in_at], s.y))


def _assert_heads_on_edges(lay: Layout) -> None:
    """Every drawn head's tip lies on the successor's left or right edge, at its centre line."""
    for ln in lay.links:
        s = _placed(lay, ln.succ)
        tip_x, tip_y = ln.head[0]
        on_edge = min(abs(tip_x - e) for e in _edges(s)) < 1e-6 and abs(tip_y - s.y) < 1e-6
        assert on_edge, (
            f"the head of {ln.pred_name} → {ln.succ_name} tips at {ln.head[0]}, off the edge"
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
    route_doc: OnePagerDoc,
) -> None:
    lay = build_layout(route_doc.items, TODAY, "T", links=_chain(route_doc))
    s = _placed(lay, lay.links[0].succ)
    centre = (s.x0 + s.x1) / 2
    moved = replace(lay.links[0], head=[(centre, s.y), *lay.links[0].head[1:]])
    with pytest.raises(AssertionError, match="off the edge"):
        _assert_heads_on_edges(replace(lay, links=[moved, *lay.links[1:]]))


def test_heads_are_4_2_pt_and_tags_are_5_pt_beside_the_first_vertical(
    route_doc: OnePagerDoc,
) -> None:
    """Every head is the README's triangle — :data:`HEAD` long along the last leg and as wide —
    whatever the slide's size; a non-FS type is tagged at 5 pt, 1.5 pt right of the first
    vertical leg at its middle (+1.5), anchored at its start."""
    lay = build_layout(route_doc.items, TODAY, "T", links=_chain(route_doc))
    assert lay.label_pt == LABEL_MAX  # a roomy slide: the head does not scale with it
    for ln in lay.links:
        (tx, ty), (bx0, by0), (bx1, by1) = ln.head
        assert bx0 == bx1 == pytest.approx(ln.shaft[-1][0]) and abs(bx0 - tx) == pytest.approx(HEAD)
        assert by1 - by0 == pytest.approx(HEAD) and (by0 + by1) / 2 == pytest.approx(ty)
        assert ln.tag_pt == 5.0 and ln.tag_anchor == "start"
        if len(ln.shaft) > 2:
            mid = (ln.shaft[1][1] + ln.shaft[2][1]) / 2
            assert (ln.tag_x, ln.tag_y) == pytest.approx((ln.shaft[1][0] + 1.5, mid + 1.5))


# ── the sweep: every density, both slides ───────────────────────────────────────────────────


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


def test_the_sweep_spans_the_page_filling_slide_down_to_the_label_floors(
    onepager_sweep: list[Layout],
) -> None:
    """The clearance claim below is only as wide as this sweep: it must reach the roomy slide
    AND both label floors (5.0 pt at row 7, 4.2 pt at row 5.5), with links drawn at each.
    Since ADR-0540 the rows FILL the slide, so the roomy end is far above the old 13-pt cap
    (six items in three swimlanes: 70 pt rows) and its labels stand at the LABEL_MAX cap."""
    assert onepager_sweep[0].row_h > 13.0 and onepager_sweep[-1].row_h < 6.0
    assert onepager_sweep[0].label_pt == LABEL_MAX
    assert {round(lay.label_pt, 2) for lay in onepager_sweep} >= {LABEL_MAX, 5.0, 4.2}
    assert all(len(lay.links) >= 3 for lay in onepager_sweep)


def test_every_link_on_the_sweep_is_drawn_and_no_slide_says_anything(
    onepager_sweep: list[Layout], compare_sweep: list[CompareLayout]
) -> None:
    """ADR-0543: a shaft runs UNDER whatever item it passes, so no density is "crowded" and no
    link is refused, flagged or drawn dashed — every link whose ends are on the slide is drawn,
    and the slide carries no note about its links at all (the pristine tree's densest sweep
    slides carried the crowding note)."""
    layouts: list[Layout | CompareLayout] = [*onepager_sweep, *compare_sweep]
    for lay in layouts:
        assert lay.link_notes == [], (lay.row_h, lay.link_notes[:1])
        assert len(lay.links) >= 3
    made = [len(_sweep_links([i.key for i in _sweep_items(*d)])) for d in DENSITIES]
    assert [len(lay.links) for lay in onepager_sweep] == made


def test_links_never_move_an_item_on_the_sweep(
    onepager_sweep: list[Layout], compare_sweep: list[CompareLayout]
) -> None:
    """The slide is laid out ONCE (ADR-0543): with its links it is the slide without them, item
    for item — the pristine tree escalated the densest sweep slides (glyphs at 80 %, a gutter, a
    reorder), moving every row."""
    for (n_lanes, per_lane), lay in zip(DENSITIES, onepager_sweep, strict=True):
        bare = build_layout(_sweep_items(n_lanes, per_lane), TODAY, "T")
        assert lay.items == bare.items and lay.lanes == bare.lanes and lay.x1 == bare.x1
    for (n_lanes, per_lane), clay in zip(DENSITIES[:-1], compare_sweep, strict=True):
        cbare = build_compare_layout(_compare_sweep_doc(n_lanes, per_lane), TODAY, "T")
        assert clay.items == cbare.items and clay.lanes == cbare.lanes


def _slipped_compare(filler: int = 0) -> CompareDoc:
    """Frame (unchanged) and Inspect (a milestone) share the top row; Wiring slipped 60 days in
    the row below, its move arrow reaching up toward the gap a Frame → Inspect leg must use.
    ``filler`` unchanged items in a second swimlane, one row each, bring the page-filling rows
    (ADR-0540: 209 pt for three rows) down to the 13-pt density the naive-band mutant needs."""

    def doc(source: str, wiring_finish: D) -> OnePagerDoc:
        items = [
            OnePagerItem("Build", "Frame", D(2027, 1, 4), D(2027, 3, 1), 2),
            OnePagerItem("Build", "Wiring", D(2027, 2, 1), wiring_finish, 3),
            OnePagerItem("Build", "Inspect", D(2027, 9, 1), D(2027, 9, 1), 4),
            *(
                OnePagerItem("Filler", f"Filler {n}", D(2027, 4, 1), D(2027, 8, 1), 10 + n)
                for n in range(filler)
            ),
        ]
        return OnePagerDoc(source, "S", tuple(keyed(items)), (), ())

    return compare_onepager_docs(doc("prior.xlsx", D(2027, 5, 3)), doc("cur.xlsx", D(2027, 7, 2)))


def _slipped_layout(filler: int = 0) -> CompareLayout:
    doc = _slipped_compare(filler)
    k = {r.name: r.key for r in doc.rows}
    return build_compare_layout(doc, TODAY, "T", links=[Link(k["Frame"], k["Inspect"])])


# ── a link and a Compare move arrow (review UIP-2, re-cast for ADR-0543) ─────────────────


def _tri(tri: Sequence[Sequence[float]], n: int = 10) -> list[tuple[float, float]]:
    (ax, ay), (bx, by), (cx, cy) = tri
    return [
        ((ax * u + bx * v + cx * (n - u - v)) / n, (ay * u + by * v + cy * (n - u - v)) / n)
        for u in range(n + 1)
        for v in range(n + 1 - u)
    ]


def _inside(px: float, py: float, tri: Sequence[Sequence[float]]) -> bool:
    (x1, y1), (x2, y2), (x3, y3) = tri
    d = [
        (px - bx) * (ay - by) - (ax - bx) * (py - by)
        for (ax, ay), (bx, by) in (((x1, y1), (x2, y2)), ((x2, y2), (x3, y3)), ((x3, y3), (x1, y1)))
    ]
    return not (any(v < 0 for v in d) and any(v > 0 for v in d))


def _move_heads_under_link_heads(lay: CompareLayout) -> list[str]:
    """Every Compare move arrow's HEAD — as the page paints it: its tip on the new finish,
    ``arrow_head`` back toward the old one and as tall — that a logic link's HEAD covers. Under
    ADR-0543's z-order a link's shaft is painted UNDER the item layer the move arrow belongs to,
    so its head is the only part of a link that can cover one (review UIP-2's concern, re-cast)."""
    out = []
    h = lay.arrow_head
    for p in lay.items:
        if p.arrow_x0 is None or p.arrow_x1 is None:
            continue
        d = 1.0 if p.arrow_x1 >= p.arrow_x0 else -1.0
        tip, back = (p.arrow_x1, p.arrow_y), p.arrow_x1 - d * h
        pts = _tri([tip, (back, p.arrow_y - h / 2), (back, p.arrow_y + h / 2)])
        for ln in lay.links:
            under = sum(_inside(x, y, ln.head) for x, y in pts)
            if under:
                what = f"{ln.pred_name} → {ln.succ_name} ({ln.kind})"
                out.append(f"{what}: its head covers {under}/{len(pts)} of {p.name}'s move head")
    return out


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
@pytest.mark.parametrize("finish", [D(2026, 11, 15), D(2026, 9, 30)], ids=["slipped", "pulled-in"])
def test_a_link_at_a_moved_finish_never_puts_its_head_on_the_move_arrow(
    pred: str, succ: str, kind: str, finish: D
) -> None:
    """Review UIP-2's four links off (and into) Design's moved finish: the shaft runs under the
    item layer the move arrow is painted in (pinned by the z-order tests), and the head — the
    one part painted over it — never lands on the arrow's head; the link is drawn, unnamed."""
    lay = _uip2_layout(finish, pred, succ, kind)
    design = next(p for p in lay.items if p.name == "Design")
    assert design.arrow_x0 is not None and len(lay.links) == 1 and lay.link_notes == []
    assert _move_heads_under_link_heads(lay) == []


def test_no_link_head_lands_on_a_move_arrow_head_on_any_compare_slide(
    compare_sweep: list[CompareLayout],
) -> None:
    assert sum(p.arrow_x0 is not None for lay in compare_sweep for p in lay.items) > 50
    for lay in compare_sweep:
        assert _move_heads_under_link_heads(lay) == [], lay.row_h


def test_mutation_a_head_moved_onto_the_move_arrow_is_caught() -> None:
    lay = _uip2_layout(D(2026, 11, 15), "Design", "PDR", "FS")
    design = next(p for p in lay.items if p.name == "Design")
    assert design.arrow_x1 is not None
    x, y = design.arrow_x1, design.arrow_y
    on = [(x + 1, y), (x - 4, y - 2), (x - 4, y + 2)]
    hit = replace(lay, links=[replace(lay.links[0], head=on)])
    assert _move_heads_under_link_heads(hit) != []


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


# ── the PowerPoint painter, in the page's z-order ───────────────────────────────────────────


def _slide(data: bytes) -> ET.Element:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return ET.fromstring(zf.read("ppt/slides/slide1.xml"))


def _name(el: ET.Element) -> str:
    c = el.find(f"{{{_P}}}nvGrpSpPr/{{{_P}}}cNvPr")
    if c is None:
        c = el.find(f"{{{_P}}}nvSpPr/{{{_P}}}cNvPr")
    if c is None:
        c = el.find(f"{{{_P}}}nvCxnSpPr/{{{_P}}}cNvPr")
    return "" if c is None else c.get("name", "")


def _groups(root: ET.Element, prefix: str) -> list[ET.Element]:
    return [g for g in root.iter(f"{{{_P}}}grpSp") if _name(g).startswith(prefix)]


def _link_groups(root: ET.Element) -> list[ET.Element]:
    """The SHAFT groups (``Logic link: …``)."""
    return _groups(root, "Logic link: ")


def _head_groups(root: ET.Element) -> list[ET.Element]:
    """The HEAD groups (``Logic link arrowhead: …``)."""
    return _groups(root, "Logic link arrowhead: ")


def _box(xfrm: ET.Element, off: str = "off", ext: str = "ext") -> tuple[int, int, int, int]:
    o, e = xfrm.find(f"{{{_A}}}{off}"), xfrm.find(f"{{{_A}}}{ext}")
    assert o is not None and e is not None
    return int(o.get("x", "")), int(o.get("y", "")), int(e.get("cx", "")), int(e.get("cy", ""))


def _group_box_errors(root: ET.Element) -> list[str]:
    """Each link group's ``off``/``ext`` (and ``chOff``/``chExt``) against the union of its
    children's own boxes — the shaft groups and the head groups alike."""
    out = []
    for g in [*_link_groups(root), *_head_groups(root)]:
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
    """Every drawn link has ONE shaft group holding ONE open, unfilled shaft of the layout's own
    polyline, and ONE head group holding a CLOSED head of the layout's own points (and its type
    tag exactly when the link carries one) — relative to each shape's offset, in EMU — with no
    halo, no dash and no DrawingML line-end anywhere."""
    out = []
    shafts = {_name(g): g for g in _link_groups(root)}
    heads = {_name(g): g for g in _head_groups(root)}
    for ln in lay.links:
        what = f"{ln.pred_name} → {ln.succ_name} ({ln.kind})"
        g, h = shafts.get(f"Logic link: {what}"), heads.get(f"Logic link arrowhead: {what}")
        if g is None or h is None:
            out.append(f"no shaft group or no head group for {what}")
            continue
        kids = [_name(sp).split(":")[0] for sp in g.findall(f"{{{_P}}}sp")]
        if kids != ["Logic link line"]:
            out.append(f"{what}: the shaft group holds {kids}")
            continue
        path, pts = _path(g.findall(f"{{{_P}}}sp")[0])
        if pts != _relative(ln.shaft)[1]:
            out.append(f"{what}: Logic link line {pts} != the layout's shaft")
        if path.get("fill") != "none" or path.find(f"{{{_A}}}close") is not None:
            out.append(f"{what}: the shaft is not an open, unfilled path")
        hk = {_name(sp).split(":")[0]: sp for sp in h.findall(f"{{{_P}}}sp")}
        want = {"Logic link head", *(["Logic link type"] if ln.tag else [])}
        if set(hk) != want:
            out.append(f"{what}: the head group holds {sorted(hk)}")
            continue
        head_path, head_pts = _path(hk["Logic link head"])
        want_off, want_pts = _relative(ln.head)
        head_xfrm = hk["Logic link head"].find(f"{{{_P}}}spPr/{{{_A}}}xfrm")
        assert head_xfrm is not None
        if _box(head_xfrm)[:2] != want_off or head_pts != want_pts:
            out.append(f"{what}: head {head_pts} at {_box(head_xfrm)[:2]} != {want_pts}")
        if head_path.find(f"{{{_A}}}close") is None or head_path.get("fill") == "none":
            out.append(f"{what}: the head is not a closed, filled polygon")
        for grp in (g, h):
            xml = ET.tostring(grp, encoding="unicode")
            for bad in ("tailEnd", "headEnd", "prstDash", "halo"):
                if bad in xml:
                    out.append(f"{what}: {_name(grp)} carries {bad}")
    return out


@pytest.fixture(scope="module")
def linked_layout() -> Layout:
    doc = _doc(ROUTE_ROWS)
    return build_layout(doc.items, TODAY, "T", links=[*_chain(doc), Link(doc.items[0].key, "x")])


def _render(lay: Layout, **kw: str) -> bytes:
    return pptx.render_onepager_pptx(lay, marking="CUI", source="Source: list.xlsx", **kw)


def test_the_pptx_paints_one_shaft_group_and_one_head_group_per_drawn_link(
    linked_layout: Layout,
) -> None:
    root = _slide(_render(linked_layout))
    assert len(linked_layout.links) == 3 and len(linked_layout.link_notes) == 1
    what = [f"{ln.pred_name} → {ln.succ_name} ({ln.kind})" for ln in linked_layout.links]
    assert [_name(g) for g in _link_groups(root)] == [f"Logic link: {w}" for w in what]
    assert [_name(g) for g in _head_groups(root)] == [f"Logic link arrowhead: {w}" for w in what]


def test_mutation_the_group_count_goes_red_when_links_are_not_grouped(
    linked_layout: Layout, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pptx._Slide, "group", lambda self, start, name: None)
    root = _slide(_render(linked_layout))
    assert _link_groups(root) == [] and _head_groups(root) == []


def test_each_link_groups_box_is_the_union_of_its_childrens_boxes(linked_layout: Layout) -> None:
    root = _slide(_render(linked_layout))
    assert _group_box_errors(root) == []


def test_mutation_a_group_box_that_is_not_the_union_is_caught(linked_layout: Layout) -> None:
    root = _slide(_render(linked_layout))
    for g in (_link_groups(root)[0], _head_groups(root)[0]):
        off = g.find(f"{{{_P}}}grpSpPr/{{{_A}}}xfrm/{{{_A}}}off")
        assert off is not None
        off.set("x", str(int(off.get("x", "0")) + 1))  # one EMU of drift, in memory
    assert len(_group_box_errors(root)) == 2


def test_the_pptx_head_and_shaft_are_the_layouts_own_points(linked_layout: Layout) -> None:
    """DrawingML's own line-end heads are sized by the renderer; this head is the layout's
    polygon, so the page and the slide draw the SAME head."""
    assert pptx._emu(123.456) == _emu(123.456)  # the painter's conversion is the oracle's
    root = _slide(_render(linked_layout))
    assert _lockstep_errors(root, linked_layout) == []
    compare = _slipped_layout()
    croot = _slide(pptx.render_onepager_compare_pptx(compare, marking="CUI", source="s"))
    assert len(_link_groups(croot)) == len(_head_groups(croot)) == 1
    assert _lockstep_errors(croot, compare) == [] and _group_box_errors(croot) == []


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


# the spTree's paint order: one top-level child per entry, back to front

_ITEM = re.compile(
    r"^(Activity|Milestone|Prior activity|Prior milestone|Slip|Pull-in|Done|Done tick|Label"
    r"|Tag|Tag text): "
)


def _order(root: ET.Element) -> list[str]:
    tree = root.find(f"{{{_P}}}cSld/{{{_P}}}spTree")
    assert tree is not None
    return [_name(el) for el in tree if el.tag != f"{{{_P}}}nvGrpSpPr" and _name(el)]


def _z_order_errors(root: ET.Element) -> list[str]:
    """README §10: every shaft group sits after the lanes (and on Compare the summaries) and
    BEFORE the first item shape; every head group AFTER the last item's label / tag and BEFORE
    the data-date line."""
    order = _order(root)
    items = [i for i, n in enumerate(order) if _ITEM.match(n) and not n.endswith(": legend")]
    under = [i for i, n in enumerate(order) if n.startswith(("Lane", "Summary"))]
    shafts = [i for i, n in enumerate(order) if n.startswith("Logic link: ")]
    heads = [i for i, n in enumerate(order) if n.startswith("Logic link arrowhead: ")]
    dd = [i for i, n in enumerate(order) if n == "Data date"]
    out = []
    if not (items and shafts and heads):
        return [f"nothing to order: {len(items)} items, {len(shafts)} shafts, {len(heads)} heads"]
    if max(shafts) > min(items):
        out.append(f"a shaft is painted over an item ({order[max(shafts)]})")
    if under and min(shafts) < max(under):
        out.append("a shaft is painted under a lane or summary")
    if min(heads) < max(items):
        out.append(f"an item is painted over a head ({order[max(items)]})")
    if dd and max(heads) > min(dd):
        out.append("a head is painted over the data-date line")
    return out


def test_the_pptx_paints_shafts_under_the_items_and_heads_over_them(
    linked_layout: Layout,
) -> None:
    root = _slide(_render(linked_layout))
    assert _z_order_errors(root) == []
    compare = _slipped_layout()
    croot = _slide(pptx.render_onepager_compare_pptx(compare, marking="CUI", source="s"))
    order = _order(croot)
    assert any(n.startswith("Slip: ") for n in order) and any(
        n.startswith("Summary: ") for n in order
    )
    assert _z_order_errors(croot) == []


@pytest.mark.parametrize(
    ("both_at", "named"),
    [
        ("_link_heads", "a shaft is painted over an item"),
        ("_link_shafts", "an item is painted over"),
    ],
)
def test_mutation_a_layer_painted_in_the_other_place_is_caught(
    linked_layout: Layout, monkeypatch: pytest.MonkeyPatch, both_at: str, named: str
) -> None:
    """Two mutants: both layers painted where the HEADS go (the shafts over the items — the
    pristine order), or both where the SHAFTS go (the heads under them) — the order check names
    the layer out of place."""
    shafts, heads = pptx._link_shafts, pptx._link_heads

    def both(s: Any, links: Any) -> None:
        shafts(s, links)
        heads(s, links)

    other = "_link_shafts" if both_at == "_link_heads" else "_link_heads"
    monkeypatch.setattr(pptx, both_at, both)
    monkeypatch.setattr(pptx, other, lambda s, links: None)
    errors = _z_order_errors(_slide(_render(linked_layout)))
    assert any(e.startswith(named) for e in errors), errors


def _runs(root: ET.Element) -> list[tuple[str, str, bool]]:
    """``(shape name, run text, glows)`` for every run on the slide."""
    out = []
    for sp in root.iter(f"{{{_P}}}sp"):
        for r in sp.iter(f"{{{_A}}}r"):
            rpr = r.find(f"{{{_A}}}rPr")
            assert rpr is not None
            glow = rpr.find(f"{{{_A}}}effectLst/{{{_A}}}glow")
            out.append(
                (_name(sp), "".join(t.text or "" for t in r.iter(f"{{{_A}}}t")), glow is not None)
            )
    return out


def _glow_errors(root: ET.Element, lay: Layout | CompareLayout) -> list[str]:
    """The glow is on exactly the intended runs: an item's label OUTSIDE its bar (on Compare its
    delta run too) and every link's type tag — never a label inside its bar, a NEW / REMOVED tag's
    text, or any other text on the slide — and each glow is the slide's white at 1.5 pt, between
    the run's fill and its typeface (DrawingML's schema order)."""
    inside = {f"Label: {p.name}" for p in lay.items if p.inside}
    outside = {f"Label: {p.name}" for p in lay.items if not p.inside}
    out = []
    for name, text, glows in _runs(root):
        want = name in outside or name.startswith("Logic link type: ")
        if glows != want:
            out.append(f"{name} ({text!r}): glow {glows}, wanted {want}")
        if name in inside and glows:
            out.append(f"{name}: a label inside its bar glows")
    for rpr in root.iter(f"{{{_A}}}rPr"):
        kids = [c.tag.rsplit("}", 1)[1] for c in rpr]
        if "effectLst" not in kids:
            continue
        glow = rpr.find(f"{{{_A}}}effectLst/{{{_A}}}glow")
        colour = None if glow is None else glow.find(f"{{{_A}}}srgbClr")
        if kids != ["solidFill", "effectLst", "latin"]:
            out.append(f"a glow out of DrawingML's order: {kids}")
        if glow is None or glow.get("rad") != "19050" or colour is None:
            out.append("an effect list that is not a 1.5-pt glow")
        elif colour.get("val") != "FFFFFF":
            out.append(f"a glow that is not the slide's white: {colour.get('val')}")
    return out


def test_labels_outside_their_bars_and_type_tags_glow_and_nothing_else_does() -> None:
    """Each run's glow is OPT-IN (``_run(..., glow=...)``), never inferred from its colour: the
    Compare slide's inside label and its coloured delta run, and the white tag text, never glow."""
    doc = _doc(ROUTE_ROWS)
    lay = build_layout(doc.items, TODAY, "T", links=_chain(doc))
    root = _slide(_render(lay))
    assert any(p.inside for p in lay.items) and any(not p.inside for p in lay.items)
    assert any(name.startswith("Logic link type: ") for name, _t, _g in _runs(root))
    assert _glow_errors(root, lay) == []
    clay = _slipped_layout()
    croot = _slide(pptx.render_onepager_compare_pptx(clay, marking="CUI", source="s"))
    assert _glow_errors(croot, clay) == []
    tagged = _tagged_compare()
    troot = _slide(pptx.render_onepager_compare_pptx(tagged, marking="CUI", source="s"))
    assert any(n.startswith("Tag text: ") for n, _t, _g in _runs(troot))
    assert any(p.inside for p in tagged.items) and any(
        p.delta and not p.inside for p in tagged.items
    )
    assert _glow_errors(troot, tagged) == []


def _tagged_compare() -> CompareLayout:
    """A Compare slide with a NEW tag, a REMOVED ghost, a slipped label carrying its delta run
    and an inside label — every run kind the glow rule distinguishes — and an SS link."""
    prior = [
        OnePagerItem("Lane", "Long base", D(2027, 1, 4), D(2027, 9, 30), 2),
        OnePagerItem("Lane", "Moves", D(2027, 2, 1), D(2027, 3, 1), 3),
        OnePagerItem("Lane", "Goes", D(2027, 4, 1), D(2027, 4, 1), 4),
    ]
    current = [
        prior[0],
        OnePagerItem("Lane", "Moves", D(2027, 2, 1), D(2027, 4, 1), 3),
        OnePagerItem("Other", "Fresh long new bar", D(2027, 1, 4), D(2027, 12, 1), 5),
    ]
    doc = compare_onepager_docs(
        OnePagerDoc("p.xlsx", "S", tuple(keyed(prior)), (), ()),
        OnePagerDoc("c.xlsx", "S", tuple(keyed(current)), (), ()),
    )
    k = {r.name: r.key for r in doc.rows if r.key}
    return build_compare_layout(doc, TODAY, "T", links=[Link(k["Long base"], k["Moves"], "SS")])


@pytest.mark.parametrize("colour_rule", [False, True])
def test_mutation_a_glow_on_the_wrong_runs_is_caught(
    linked_layout: Layout, monkeypatch: pytest.MonkeyPatch, colour_rule: bool
) -> None:
    """Two mutants: every run glows; or the glow is a COLOUR rule (every non-white run) — the
    latter glows the legend, the title and the inside label's coloured delta."""
    real = pptx._run

    def every(text: str, size: float, color: str, bold: bool, glow: bool = False) -> str:
        return real(text, size, color, bold, color != "FFFFFF" if colour_rule else True)

    monkeypatch.setattr(pptx, "_run", every)
    assert _glow_errors(_slide(_render(linked_layout)), linked_layout) != []


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


def test_the_deck_carries_no_footnote_and_no_retired_link_parts(linked_layout: Layout) -> None:
    """ADR-0543 retired the slide's footnote, the halo under each shaft and the dashed fallback."""
    for data in (
        _render(linked_layout),
        pptx.render_onepager_compare_pptx(_slipped_layout(), marking="CUI", source="s"),
    ):
        names = [_name(el) for el in _slide(data).iter() if _name(el)]
        assert "Footnote" not in names
        assert not [n for n in names if "halo" in n or "dashed" in n]
    assert not hasattr(pptx, "_WARN") and not hasattr(pptx, "_footnote")


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
