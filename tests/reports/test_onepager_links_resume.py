"""ADR-0539 (resume): the logic-link router and its bookkeeping, attacked again after review.

The review of the built tree re-opened four fixes and found the crowding note on a 3-item slide:

* **UIP-2** — a link leaving or entering a SLIPPED item's finish ran its vertical leg (and its
  halo, painted above the items) through that item's move-arrow HEAD.
* **SKL-1 / SKL-2 / DOC-LS-02** — a later link's VERTICAL leg, or the link out of a short bar,
  still erased an earlier link's head or type tag, some on slides that said nothing.
* **DOC-LS-01** — a 3-item Timeline with two forward links carried the "At this density … Split
  the list" note: the cause was one link's tag in the other's path, not density.
* **SKL-3 / SKL-4** — a link's stored identity went stale when its item slipped, so a later
  upload lost it or moved it to ANOTHER copy; and identical twin rows were named "none with its
  dates" when both carry them.
* **SKL-5** — the Excel "Logic links" note blamed a date window that was never set.
* **SKL-6** — the upload call sites, the Compare export branch, the tag's second spot and the
  gone-reason text had no pin a revert of them turns red.
* **UILD-6** — the page-only FROM / TO pick tag rendered at 7.1 px at 1440 px, under the design
  system's 8 px floor.

Everything is driven the way a page drives it — ``onepager_actions`` uploads a workbook and adds
links, and the layout the page paints is read back — and judged by an INK ORACLE written here,
independent of the router: a link is painted halo (the canvas colour, ``HALO_W`` wide, round
caps and joins) → line → head → tag, in the order the links were made, ABOVE every item; so a
later link's halo, head or tag covers whatever of an earlier head or tag — or of a move arrow's
head — it overlaps. The property tests use a seeded generator of their own (chains of random
types through random items), never the router's code.

Red first (2026-09-29, on 21e99c76): every test here failed there for the reason its docstring
gives, except the mutation twins and three GUARDS that held on the built tree and exist to kill
the review's surviving mutants — the link surviving its name starting to repeat through the
upload (M4c / M4d), the "none with its dates" sentence (M4e) and the window note on both pages
(M6b). Each of those mutants, applied to this tree, turns them red by name.
"""

from __future__ import annotations

import datetime as dt
import html
import random
import re
import socket
import threading
import time
from collections.abc import Iterator, Sequence
from dataclasses import replace
from itertools import pairwise
from typing import Any

import pytest

from schedule_forensics.reports import onepager_links as links_mod
from schedule_forensics.reports.onepager import (
    CROWDED_NOTE,
    Layout,
    OnePagerDoc,
    OnePagerItem,
    build_layout,
    keyed,
)
from schedule_forensics.reports.onepager_compare import (
    CompareLayout,
    build_compare_layout,
    compare_onepager_docs,
)
from schedule_forensics.reports.onepager_links import HALO_W, LINK_TYPES, Link, PlacedLink
from schedule_forensics.web import onepager_actions as act
from schedule_forensics.web.onepager import linkable_items, onepager_layout
from schedule_forensics.web.onepager_compare import linkable_rows, onepager_compare_layout
from schedule_forensics.web.state import SessionState
from web.onepager_twin import twin_xlsx

D = dt.date
MB = 10 * 1024 * 1024
HEAD = ("Swimlane", "Task", "Start", "Finish", "Complete")
TODAY = D(2026, 1, 1)
Point = tuple[float, float]


# ── the ink oracle (independent of the router) ────────────────────────────────────────────────


def _seg_dist(px: float, py: float, a: Point, b: Point) -> float:
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    span = dx * dx + dy * dy
    t = 0.0 if span == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / span))
    return float(((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5)


def _in_tri(px: float, py: float, tri: Sequence[Point]) -> bool:
    (x1, y1), (x2, y2), (x3, y3) = tri

    def side(ax: float, ay: float, bx: float, by: float) -> float:
        return (px - bx) * (ay - by) - (ax - bx) * (py - by)

    d = (side(x1, y1, x2, y2), side(x2, y2, x3, y3), side(x3, y3, x1, y1))
    return not (any(v < 0 for v in d) and any(v > 0 for v in d))


def _tri_samples(tri: Sequence[Point], n: int = 8) -> list[Point]:
    (ax, ay), (bx, by), (cx, cy) = tri
    return [
        (
            (ax * u + bx * v + cx * (n - u - v)) / n,
            (ay * u + by * v + cy * (n - u - v)) / n,
        )
        for u in range(n + 1)
        for v in range(n + 1 - u)
    ]


def _tag_ink(ln: PlacedLink) -> tuple[float, float, float, float]:
    """The type tag's text as the painters write it: capitals 0.62 em wide, 0.7 em tall above
    the baseline at ``tag_y``, anchored at ``tag_x`` (``start``: its left edge; ``end``: its
    right)."""
    w = len(ln.tag) * ln.tag_pt * 0.62
    x0 = ln.tag_x if ln.tag_anchor == "start" else ln.tag_x - w
    return x0, x0 + w, ln.tag_y - ln.tag_pt * 0.7, ln.tag_y


def _tag_samples(ln: PlacedLink) -> list[Point]:
    x0, x1, y0, y1 = _tag_ink(ln)
    return [(x0 + (x1 - x0) * i / 8, y0 + (y1 - y0) * j / 8) for i in range(9) for j in range(9)]


def _reach(ln: PlacedLink) -> tuple[float, float, float, float]:
    """A box around everything ``ln`` paints — halo, head and tag — for a quick far-away test."""
    xs = [x for x, _ in (*ln.shaft, *ln.head)]
    ys = [y for _, y in (*ln.shaft, *ln.head)]
    if ln.tag:
        x0, x1, y0, y1 = _tag_ink(ln)
        xs += [x0, x1]
        ys += [y0, y1]
    h = HALO_W / 2
    return min(xs) - h, max(xs) + h, min(ys) - h, max(ys) + h


def _covers(ln: PlacedLink, x: float, y: float) -> bool:
    """Whether link ``ln``'s paint covers the point: its halo, its head or its tag's text."""
    x0, x1, y0, y1 = _reach(ln)
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    if any(_seg_dist(x, y, a, b) < HALO_W / 2 for a, b in pairwise(ln.shaft)):
        return True
    if _in_tri(x, y, ln.head):
        return True
    if ln.tag:
        x0, x1, y0, y1 = _tag_ink(ln)
        return x0 <= x <= x1 and y0 <= y <= y1
    return False


def _move_heads(lay: Layout | CompareLayout) -> list[tuple[str, list[Point]]]:
    """Every Compare move arrow's head as the PAGE paints it (``onepager_compare.js`` arrow()):
    its tip on the new finish, its base ``arrow_head`` back toward the old one, as tall."""
    if not isinstance(lay, CompareLayout):
        return []
    out = []
    h = lay.arrow_head
    for p in lay.items:
        if p.arrow_x0 is None or p.arrow_x1 is None:
            continue
        x0, x1, y = p.arrow_x0, p.arrow_x1, p.arrow_y
        d = 1.0 if x1 >= x0 else -1.0
        out.append((p.name, [(x1, y), (x1 - d * h, y - h / 2), (x1 - d * h, y + h / 2)]))
    return out


def _erasures(lay: Layout | CompareLayout) -> list[str]:
    """Every head, type tag and move-arrow head a LATER-painted link covers, named with the
    share of its samples covered."""
    links = list(lay.links)
    out: list[str] = []
    for name, tri in _move_heads(lay):
        pts = _tri_samples(tri)
        hit = sum(any(_covers(ln, x, y) for ln in links) for x, y in pts)
        if hit:
            out.append(f"the move arrow of {name}: {hit}/{len(pts)} of its head covered")
    for i, ln in enumerate(links):
        later = links[i + 1 :]
        what = f"{ln.pred_name} → {ln.succ_name} ({ln.kind})"
        for part, pts in (("head", _tri_samples(ln.head)), ("tag", _tag_samples(ln))):
            if part == "tag" and not ln.tag:
                continue
            hit = sum(any(_covers(m, x, y) for m in later) for x, y in pts)
            if hit:
                out.append(f"the {part} of {what}: {hit}/{len(pts)} covered by a later link")
    return out


# ── the property: an independent generator of chains ──────────────────────────────────────────


def _slide(seed: int, n_items: tuple[int, int], n_links: int) -> tuple[list[OnePagerItem], Any]:
    """A seeded list — 1-3 swimlanes over ~18 months, milestones, short bars (1-3 days) and
    long ones — and a CHAIN X → Y → Z of random types, plus up to ``n_links - 2`` more links
    that keep the logic a DAG (each runs forward in a random order of the items) and never make
    a bar of 1-3 days the end of a THIRD link: such a bar is a few points wide, room for one
    link end on each side, so a third is a real collision — pinned on its own below."""
    r = random.Random(seed)
    n = r.randint(*n_items)
    lanes = ["Eng", "Ops", "Test"][: r.randint(1, 3)]
    items = []
    for k in range(n):
        start = D(2026, 1, 5) + dt.timedelta(days=r.randrange(0, 520))
        kind = r.random()
        if kind < 0.3:
            finish = start
        elif kind < 0.45:
            finish = start + dt.timedelta(days=r.randint(1, 3))
        else:
            finish = start + dt.timedelta(days=r.randint(5, 120))
        items.append(OnePagerItem(r.choice(lanes), f"Item {k}", start, finish, k + 2))
    items = keyed(items)
    order = [it.key for it in items]
    r.shuffle(order)
    rank = {k: i for i, k in enumerate(order)}
    x, y, z = sorted(r.sample(order, 3), key=rank.__getitem__)
    links = [Link(x, y, r.choice(LINK_TYPES)), Link(y, z, r.choice(LINK_TYPES))]
    short = {it.key for it in items if 0 < (it.finish - it.start).days <= 3}
    for _ in range(r.randint(0, n_links - 2)):
        a, b = sorted(r.sample(order, 2), key=rank.__getitem__)
        ln = Link(a, b, r.choice(LINK_TYPES))
        ends = [k for m in links for k in (m.pred, m.succ)]
        if ln not in links and not any(k in short and ends.count(k) >= 2 for k in (a, b)):
            links.append(ln)
    return items, links


def _compared(seed: int, items: list[OnePagerItem]) -> Any:
    """The same list as PRIOR, and a CURRENT in which most finishes moved (slips and pull-ins,
    so move arrows sit above their bars)."""
    r = random.Random(seed * 7 + 1)
    current = []
    for it in items:
        move = dt.timedelta(days=r.choice([0, 9, 21, 45, -12, -30]))
        finish = max(it.finish + move, it.start)
        current.append(replace(it, finish=finish, key=""))
    return compare_onepager_docs(
        OnePagerDoc("prior.xlsx", "S", tuple(items), (), ()),
        OnePagerDoc("current.xlsx", "S", tuple(keyed(current)), (), ()),
    )


def _slides(
    seeds: range, n_items: tuple[int, int], n_links: int
) -> Iterator[tuple[str, Layout | CompareLayout, int]]:
    """Each seed as a One-Pager and as a Compare slide, with the count of links made."""
    for seed in seeds:
        items, links = _slide(seed, n_items, n_links)
        yield f"one-pager seed {seed}", build_layout(items, TODAY, "T", links=links), len(links)
        doc = _compared(seed, items)
        keys = {r.key for r in doc.rows if r.key}
        kept = [ln for ln in links if ln.pred in keys and ln.succ in keys]
        yield f"compare seed {seed}", build_compare_layout(doc, TODAY, "T", links=kept), len(kept)


@pytest.fixture(scope="module")
def dense() -> list[tuple[str, Layout | CompareLayout, list[str]]]:
    """160 seeds, 3-40 items, chains of 2-6 links, as both slides — each with its erasures."""
    return [(what, lay, _erasures(lay)) for what, lay, _n in _slides(range(0, 160), (3, 40), 6)]


def test_property_no_head_or_tag_is_erased_unless_the_slide_says_so(
    dense: list[tuple[str, Layout | CompareLayout, list[str]]],
) -> None:
    """Review DOC-LS-02: a head, a type tag or a move-arrow head covered by a later link is
    allowed only on a slide that carries the crowding note (the reviewers' generator lost 35
    heads and 32 tags on the built tree)."""
    assert sum(len(lay.links) for _w, lay, _e in dense) > 1000  # the population is not empty
    silent = [
        f"{what}: {e}"
        for what, lay, erased in dense
        if CROWDED_NOTE not in lay.link_notes
        for e in erased
    ]
    assert silent == [], silent[:5]


def test_property_a_small_slide_erases_nothing_and_says_nothing() -> None:
    """A slide of at most 6 items and at most 3 links is not dense: every link is drawn,
    nothing is erased and there is no note at all (the built tree put the "At this density …
    Split the list" note on 3-item slides)."""
    bad = []
    for what, lay, n in _slides(range(1000, 1200), (3, 6), 3):
        erased = _erasures(lay)
        if erased or lay.link_notes or len(lay.links) != n:
            bad.append((what, len(lay.links), n, lay.link_notes[:1], erased[:2]))
    assert bad == [], bad[:5]


def test_a_drawn_link_never_erases_ink_even_on_a_dense_slide(
    dense: list[tuple[str, Layout | CompareLayout, list[str]]],
) -> None:
    """The stronger design statement (ADR-0539 resume): the router never DRAWS a link that
    would erase another link's head or tag, or a move arrow's head — when no route between its
    two items keeps them apart, the link is not drawn and is named, with the collision."""
    erased = [f"{what}: {e}" for what, lay, found in dense for e in found]
    assert erased == [], erased[:5]


def test_mutation_without_the_ink_check_the_property_goes_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teeth: the router's ink check switched off (every candidate route judged clean) — the
    same oracle and generator see heads and tags erased."""
    monkeypatch.setattr(links_mod, "_conflicts", lambda *_a, **_k: ([], [], False))
    erased = [e for _w, lay, _n in _slides(range(0, 40), (3, 40), 6) for e in _erasures(lay)]
    assert erased, "the oracle must see erasures when the ink check is off"


# ── through the page's actions ────────────────────────────────────────────────────────────────


def _onepager(rows: Sequence[tuple[str, ...]]) -> SessionState:
    st = SessionState()
    act.load_list(st, "list.xlsx", twin_xlsx((HEAD, *rows)), max_bytes=MB)
    assert st.onepager is not None and st.onepager.items, st.onepager_msg
    return st


def _key(st: SessionState, name: str, compare: bool = False) -> str:
    """The key of the one item on the slide called ``name`` — or, for a repeated name, labelled
    ``name`` with its dates (``Review (3/1/26)``)."""
    items = linkable_rows(st) if compare else linkable_items(st)
    hits = [
        k
        for k, label, _r in items
        if name in (label.split(" · ", 1)[1], label.split(" · ", 1)[1].split(" (")[0])
    ]
    assert len(hits) == 1, (name, hits)
    return hits[0]


def _add(st: SessionState, pred: str, succ: str, kind: str, compare: bool = False) -> None:
    page = "compare" if compare else "onepager"
    act.edit_links(st, page, "add", _key(st, pred, compare), _key(st, succ, compare), kind)
    msg = st.onepager_compare_links_msg if compare else st.onepager_links_msg
    assert msg.startswith("Logic link added"), msg


#: Review DOC-LS-01's list, in its sheet order: Design and Build overlap (two rows), Deliver
#: shares Design's row.
THREE = (
    ("Eng", "Design", "1/25/2026", "2/28/2026", ""),
    ("Eng", "Deliver", "10/30/2026", "11/8/2026", ""),
    ("Eng", "Build", "2/9/2026", "5/5/2026", ""),
)


def _three() -> Layout:
    st = _onepager(THREE)
    _add(st, "Design", "Build", "FF")
    _add(st, "Build", "Deliver", "FS")
    lay = onepager_layout(st, TODAY)
    assert lay is not None
    return lay


def test_a_three_item_forward_chain_carries_no_crowding_note() -> None:
    """Review DOC-LS-01: Design → Build (FF) then Build → Deliver (FS). The FS leg leaves
    Build's finish along the gap where the FF tag stood — two links meeting, not a dense slide;
    the built tree said "At this density … Split the list"."""
    lay = _three()
    assert len(lay.links) == 2 and lay.link_notes == [] and _erasures(lay) == []


def test_a_tag_in_a_later_links_path_takes_its_second_spot() -> None:
    """Review SKL-6 (M2c): with the FS leg running through the FF tag's first spot (beside its
    head), the tag stands at its second — beside its predecessor's end, on the side away from
    its own leg — and nothing is erased."""
    ff, _fs = _three().links
    sx = ff.shaft[0][0]
    assert ff.tag == "FF" and ff.tag_anchor == "end"
    assert sx - 2.0 < ff.tag_x < sx  # right-aligned just left of Design's finish leg


def test_mutation_a_tag_with_one_spot_is_caught_off_its_second(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = links_mod._tag_spots
    monkeypatch.setattr(links_mod, "_tag_spots", lambda *a, **k: real(*a, **k)[:1])
    ff, *_rest = _three().links
    assert not (ff.tag_anchor == "end" and ff.shaft[0][0] - 2.0 < ff.tag_x < ff.shaft[0][0])


SHIP = ("Eng", "Ship", "9/1/2026", "9/1/2026", "")
R31 = ("Eng", "Review", "3/1/2026", "3/1/2026", "")
R41 = ("Eng", "Review", "4/1/2026", "4/1/2026", "")
R320 = ("Eng", "Review", "3/20/2026", "3/20/2026", "")
R501 = ("Eng", "Review", "5/1/2026", "5/1/2026", "")


def _upload(st: SessionState, rows: Sequence[tuple[str, ...]], compare: bool) -> None:
    data = twin_xlsx((HEAD, *rows, SHIP))
    if compare:
        act.load_compare(st, "current", "current.xlsx", data, max_bytes=MB)
    else:
        act.load_list(st, "list.xlsx", data, max_bytes=MB)


def _linked(rows: Sequence[tuple[str, ...]], compare: bool) -> SessionState:
    """``Review → Ship`` (FS) made on a list holding ``rows`` (the Compare page: as CURRENT,
    over a PRIOR of the same rows)."""
    st = SessionState()
    if compare:
        act.load_compare(st, "prior", "prior.xlsx", twin_xlsx((HEAD, *rows, SHIP)), max_bytes=MB)
    _upload(st, rows, compare)
    _add(st, "Review" if len(rows) == 1 else "Review (3/1/26)", "Ship", "FS", compare)
    return st


def _drawn(st: SessionState, compare: bool) -> tuple[list[str], list[str]]:
    lay = onepager_compare_layout(st, TODAY) if compare else onepager_layout(st, TODAY)
    assert lay is not None
    return [ln.pred_name for ln in lay.links], list(lay.link_notes)


PAGES = pytest.mark.parametrize("compare", [False, True], ids=["onepager", "compare"])


@PAGES
def test_a_link_survives_its_name_starting_to_repeat_through_the_upload(compare: bool) -> None:
    """Review SKL-6 (M4c / M4d): LINKS-4 through the UPLOAD, not rebind() alone — the unique
    3/1 Review is linked, then the list gains a 4/1 Review: the link stays on the 3/1 one."""
    st = _linked([R31], compare)
    _upload(st, [R31, R41], compare)
    assert _drawn(st, compare) == (["Eng · Review (3/1/26)"], [])


@PAGES
def test_a_slipped_item_keeps_its_link_when_its_name_then_repeats(compare: bool) -> None:
    """Review SKL-3, scenario C: the unique Review (3/1) is linked; the next upload slips it to
    3/20 (still unique — the link follows it); the one after adds a 5/1 Review. The link stays
    on the 3/20 Review, the item it was drawn on — the built tree lost it ("none with its
    dates"), matching the identity stored when the link was made."""
    st = _linked([R31], compare)
    _upload(st, [R320], compare)
    assert _drawn(st, compare) == (["Eng · Review (3/20/26)"], [])
    _upload(st, [R320, R501], compare)
    assert _drawn(st, compare) == (["Eng · Review (3/20/26)"], [])


@PAGES
def test_a_slipped_item_keeps_its_link_when_a_copy_with_its_old_dates_appears(
    compare: bool,
) -> None:
    """Review SKL-3, scenario D: linked at 3/1, slipped to 4/1, then a 3/1 Review appears
    beside it. The link stays on the 4/1 Review it was drawn on — the built tree moved it,
    silently, to the new 3/1 copy."""
    st = _linked([R31], compare)
    _upload(st, [R41], compare)
    assert _drawn(st, compare) == (["Eng · Review (4/1/26)"], [])
    _upload(st, [R31, R41], compare)
    assert _drawn(st, compare) == (["Eng · Review (4/1/26)"], [])


def test_a_link_to_a_row_now_listed_twice_says_so() -> None:
    """Review SKL-4 (M4e): the linked row appears twice, identically — the link cannot choose,
    and the sentence says why TRULY (the built tree: "none with its dates", while both did)."""
    st = _linked([R31], False)
    _upload(st, [R31, R31], False)
    drawn, notes = _drawn(st, False)
    assert drawn == []
    assert notes == [
        "logic link “Eng · Review (3/1/26)” → “Eng · Ship (9/1/26)” (FS) is not drawn — "
        "“Eng · Review (3/1/26)” no longer matches one item — the list now holds it 2 times "
        "(identical rows: same swimlane, name and dates); pick the one you mean again."
    ]


def test_a_link_whose_name_now_matches_only_other_dates_says_so() -> None:
    """The other half of gone_reason (M4e): a rolling list drops the linked 3/1 Review and keeps
    the 4/1 one — the link is not moved to it, and the reason names the copies it now matches."""
    st = _linked([R31, R41], False)
    _upload(st, [R41], False)
    drawn, notes = _drawn(st, False)
    assert drawn == []
    assert notes == [
        "logic link “Eng · Review (3/1/26)” → “Eng · Ship (9/1/26)” (FS) is not drawn — "
        "“Eng · Review (3/1/26)” no longer matches one item — its swimlane and name now match "
        "1 item(s), none with its dates; pick it again."
    ]


# ── the Excel export's note, by its real cause (review SKL-5 / SKL-6 M6b) ───────────────────


def _links_sheet(ts: Any) -> list[tuple[Any, ...]]:
    assert not isinstance(ts, str), ts
    return [tuple(r) for t in ts.tables if t.title == "Logic links" for r in t.rows]


LIST = (("Eng", "A", "1/5/2026", "3/1/2026", ""), ("Eng", "B", "4/5/2026", "6/1/2026", ""))
#: Every row refused (a word where a date must be): the list loads with no usable item.
NO_ROWS = (("Eng", "A", "soon", "later", ""), ("Eng", "B", "tbd", "tbd", ""))
WINDOW_NOTE = "No item of the list falls inside the date window, so no logic link is drawn."


def _linked_pair(compare: bool) -> SessionState:
    st = SessionState()
    if compare:
        for slot in ("prior", "current"):
            act.load_compare(st, slot, f"{slot}.xlsx", twin_xlsx((HEAD, *LIST)), max_bytes=MB)
    else:
        act.load_list(st, "list.xlsx", twin_xlsx((HEAD, *LIST)), max_bytes=MB)
    _add(st, "A", "B", "FS", compare)
    return st


@PAGES
def test_the_excel_note_blames_the_window_only_when_one_hides_the_slide(compare: bool) -> None:
    """A window that leaves no item: the one note names the window, on BOTH pages (the Compare
    branch had no pin — review SKL-6 M6b)."""
    st = _linked_pair(compare)
    if compare:
        act.set_compare_window(st, "2027-01-01", "2027-03-31", "set")
        rows = _links_sheet(act.compare_workbook(st, TODAY))
    else:
        act.set_window(st, "2027-01-01", "2027-03-31", "set")
        rows = _links_sheet(act.onepager_workbook(st, TODAY))
    assert rows[0][-1] == "no — see the note below" and rows[-1] == ("", "", "note", WINDOW_NOTE)


@PAGES
def test_the_excel_note_says_the_list_has_no_usable_item(compare: bool) -> None:
    """Review SKL-5: the list re-uploaded with no usable row and NO window — the built tree's
    note blamed the date window."""
    st = _linked_pair(compare)
    empty = twin_xlsx((HEAD, *NO_ROWS))
    if compare:
        for slot in ("prior", "current"):
            act.load_compare(st, slot, f"{slot}.xlsx", empty, max_bytes=MB)
        assert st.onepager_compare_window is None and st.onepager_compare_links
        rows = _links_sheet(act.compare_workbook(st, TODAY))
        said = "Neither list has a usable item, so no logic link is drawn."
    else:
        act.load_list(st, "list.xlsx", empty, max_bytes=MB)
        assert st.onepager_window is None and st.onepager_links
        rows = _links_sheet(act.onepager_workbook(st, TODAY))
        said = "The list has no usable item, so no logic link is drawn."
    assert rows[0][-1] == "no — see the note below" and rows[-1] == ("", "", "note", said)


# ── the pick tag's size in a browser (review UILD-6) ──────────────────────────────────────────


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def served() -> Iterator[str]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import create_app

    st = SessionState()
    st.onepager_today = D(2026, 9, 1)
    app = create_app(st)
    api = TestClient(app)
    rows = twin_xlsx((HEAD, *LIST))
    for url, slot in (
        ("/onepager/upload", ""),
        ("/onepager-compare/upload", "prior"),
        ("/onepager-compare/upload", "current"),
    ):
        r = api.post(
            url,
            files={"file": ("list.xlsx", rows, "application/octet-stream")},
            data={"slot": slot} if slot else {},
            follow_redirects=False,
        )
        assert r.status_code == 303, (url, r.status_code)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    from web.browser_chrome import chrome_kwargs

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


#: Pick the first item as FROM through the select (the page's own mark() draws the tag), then
#: measure the tag's RENDERED size: its computed font size in SVG units times the SVG's scale.
_PICK_TAG_PX = """(p) => {
  const from = document.getElementById(p + 'LinkFrom');
  from.value = Array.from(from.options).find(o => o.value).value;
  from.dispatchEvent(new Event('change'));
  const tag = document.querySelector('#' + p + 'Host g.op-pick text.op-pick-tag');
  if (!tag) return null;
  const size = parseFloat(getComputedStyle(tag).fontSize);
  return size * tag.ownerSVGElement.getScreenCTM().a;
}"""
THEMES = ("console", "daylight", "apollo", "jarvis")


def _pick_tag_px(browser: Any, base: str, path: str, prefix: str, style: str = "") -> float:
    """The SMALLEST rendered pick tag over the four views at 1440 px: the dark views' left rail
    narrows the slide (it renders at 1.16x there, 1.41x in daylight)."""
    sizes = []
    for theme in THEMES:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.add_init_script(
                f"try {{ localStorage.setItem('sf-theme', '{theme}'); }} catch (e) {{}}"
            )
            page.goto(base + path)
            page.wait_for_selector("svg.op-svg")
            assert page.evaluate("document.documentElement.getAttribute('data-theme')") == theme
            if style:
                page.add_style_tag(content=style)
            px = page.evaluate(_PICK_TAG_PX, prefix)
        finally:
            page.close()
        assert px is not None, f"no pick tag drawn on {path} ({theme})"
        sizes.append(float(px))
    return min(sizes)


PICK_PAGES = pytest.mark.parametrize(
    ("path", "prefix"), [("/onepager", "op"), ("/onepager-compare", "opc")], ids=["op", "opc"]
)


@PICK_PAGES
def test_the_pick_tag_is_at_least_8px_at_1440_in_every_view(
    browser: Any, served: str, path: str, prefix: str
) -> None:
    """Review UILD-6: the FROM / TO pick tag is page-only chrome (never on the slide or in the
    .pptx), so DESIGN-SYSTEM §1's floor — "8px mono labels, never smaller" — binds it. At 5 SVG
    units it rendered 7.1 px in LODESTAR and 5.8 px in Polaris²'s dark views."""
    assert _pick_tag_px(browser, served, path, prefix) >= 8.0


@PICK_PAGES
@pytest.mark.parametrize("units", [5, 6])
def test_mutation_a_smaller_pick_tag_is_caught_under_the_floor(
    browser: Any, served: str, path: str, prefix: str, units: int
) -> None:
    """Teeth: the pristine 5 units, and the 6 units the review suggested (8.5 px in LODESTAR,
    7.0 px under Polaris²'s rail), both measure under the floor."""
    style = f".op-pick-tag{{font-size:{units}px !important}}"
    assert _pick_tag_px(browser, served, path, prefix, style) < 8.0


# ── guards on the actions' page text ──────────────────────────────────────────────────────────


def test_the_three_item_page_body_never_shows_the_crowding_note() -> None:
    """The same slide through the page body both servers render (the review's own measure)."""
    from schedule_forensics.web.onepager import _onepager_body

    st = _onepager(THREE)
    _add(st, "Design", "Build", "FF")
    _add(st, "Build", "Deliver", "FS")
    body = _onepager_body(st, TODAY)
    text = html.unescape(
        re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", body, flags=re.S))
    )
    assert "At this density" not in text and "not drawn" not in text
