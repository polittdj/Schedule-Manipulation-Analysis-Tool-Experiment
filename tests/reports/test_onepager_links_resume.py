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
links, and the layout the page paints is read back.

ADR-0543 (the design handoff's Console rule) re-cast the routing half of this review: a link's
SHAFT is now painted UNDER the items and its head and tag over them, so no shaft can erase a
head, a tag or a move arrow — the halo-above ink oracle this module carried (and its "crowding"
property) described a z-order that no longer exists, and is retired with the rule; the z-order
itself is pinned in a browser (``tests/web/test_onepager_links_browser.py``) and in the
.pptx (``tests/reports/test_onepager_links.py``). What this module's seeded generator pins now
is the ROUTE: every link on 320 dense slides (both pages) is exactly the README's route,
recomputed here by an ORACLE written from the README's text over the layout's own fields —
independent of the router, of ``crossings`` and of the obstacles the slides hand it.

Red first (2026-09-29, on 21e99c76): every test here failed there for the reason its docstring
gives, except the mutation twins and three GUARDS that held on the built tree and exist to kill
the review's surviving mutants — the link surviving its name starting to repeat through the
upload (M4c / M4d), the "none with its dates" sentence (M4e) and the window note on both pages
(M6b). Each of those mutants, applied to this tree, turns them red by name. The route property
(ADR-0543) is red on the pristine tree (fac5773): no route there leaves an item's edge at its
centre line.
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
from typing import Any

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_compare as opc
from schedule_forensics.reports import onepager_links as links_mod
from schedule_forensics.reports.onepager import (
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
    window_compare,
)
from schedule_forensics.reports.onepager_links import LINK_TYPES, Link, PlacedLink
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


# ── the README's route, recomputed from its text (an oracle independent of the router) ───────

#: README §"Logic-link routing and z-order", steps 1-8, as numbers.
_HEAD, _OUT, _IN, _PAD, _TAG = 4.2, 4.0, 6.0, 1.5, 1.5
_BAR, _NAME, _PULL = 10.0, 3.0, 0.002


def _painted(lay: Layout | CompareLayout, p: Any) -> tuple[list[Point], list[Point]]:
    """``(shapes, names)``: the x-extents of what an item paints — read off the layout's own
    fields the way the PAINTERS draw them (``onepager.js`` / ``onepager_compare.js``): each shape
    (a bar's ends; a diamond at its own size; on Compare the ghost and the move arrow) and each
    name (the label's text; on Compare the NEW / REMOVED / DUPLICATE tag)."""
    shapes: list[Point] = []
    sides = [(p.x0, p.x1, p.milestone, p.ms)]
    if isinstance(lay, CompareLayout):
        sides.append((p.ghost_x0, p.ghost_x1, bool(p.ghost_milestone), p.ghost_ms))
        if p.arrow_x0 is not None and p.arrow_x1 is not None:
            shapes.append((min(p.arrow_x0, p.arrow_x1), max(p.arrow_x0, p.arrow_x1)))
    for x0, x1, diamond, size in sides:
        if x0 is not None and x1 is not None:
            shapes.append((x0 - size / 2, x0 + size / 2) if diamond else (x0, x1))
    tag = getattr(p, "badge", "")
    tx = p.label_x - (p.badge_w + 2 if tag and p.label_anchor == "end" else 0.0)
    text = (tx - p.label_w, tx) if p.label_anchor == "end" else (tx, tx + p.label_w)
    names = [text] + ([(p.badge_x, p.badge_x + p.badge_w)] if tag else [])
    return shapes, names


def _current(p: Any) -> Point:
    """The item's own (current) shape: a bar's ends, a diamond's side vertices at its own size."""
    return (p.x0 - p.ms / 2, p.x0 + p.ms / 2) if p.milestone else (p.x0, p.x1)


def _readme_route(lay: Layout | CompareLayout, ln: PlacedLink) -> tuple[list[Point], Point]:
    """``(shaft, tag position)`` the README's steps 1-8 give this link on this slide."""
    by_key = {p.key: p for p in lay.items if p.key}
    p, s = by_key[ln.pred], by_key[ln.succ]
    pe, se = _current(p), _current(s)
    from_finish, to_start = ln.kind[0] == "F", ln.kind[1] == "S"
    out, into = (1 if from_finish else -1), (1 if to_start else -1)
    a = (pe[1] if from_finish else pe[0], p.y)
    b = (se[0] if to_start else se[1], s.y)
    ax, bx = a[0] + out * _OUT, b[0] - into * _IN
    lo = max([x for x, on in ((ax, out == 1), (bx, into == -1)) if on], default=None)
    hi = min([x for x, on in ((ax, out == -1), (bx, into == 1)) if on], default=None)
    lo, hi = (hi, hi) if lo is None else ((lo, lo) if hi is None else (lo, hi))
    end = (b[0] - into * _HEAD, b[1])
    same = abs(a[1] - b[1]) < 0.01
    if same and out == into and into * (b[0] - a[0]) > _IN:
        return [a, end], ((a[0] + b[0]) / 2, a[1] - _TAG)
    if not same and lo <= hi:
        between_rows = [
            q
            for q in lay.items
            if min(a[1], b[1]) < q.y < max(a[1], b[1]) and q is not p and q is not s
        ]
        cands = [lo] if hi - lo < 0.5 else [lo + (hi - lo) * i / 8 for i in range(9)]
        scores = []
        for cx in cands:
            bars = names = 0
            for q in between_rows:
                shapes, words = _painted(lay, q)
                if any(x0 - _PAD <= cx <= x1 + _PAD for x0, x1 in shapes):
                    bars += 1
                elif any(n0 <= cx <= n1 for n0, n1 in words):
                    names += 1
            scores.append(_BAR * bars + _NAME * names + _PULL * abs(cx - bx))
        cx = cands[scores.index(min(scores))]
        shaft = [a, (cx, a[1]), (cx, b[1]), end]
    else:
        gy = s.y + (-1.0 if same or a[1] < b[1] else 1.0) * lay.row_h / 2
        shaft = [a, (ax, a[1]), (ax, gy), (bx, gy), (bx, b[1]), end]
    return shaft, (shaft[1][0] + _TAG, (shaft[1][1] + shaft[2][1]) / 2 + _TAG)


def _off_readme(lay: Layout | CompareLayout) -> list[str]:
    """Every drawn link whose shaft, head or tag is not the README's route."""
    out = []
    for ln in lay.links:
        shaft, (tx, ty) = _readme_route(lay, ln)
        tip, base = ln.head[0], shaft[-1]
        head = [tip, (base[0], base[1] - _HEAD / 2), (base[0], base[1] + _HEAD / 2)]
        same = len(shaft) == len(ln.shaft) and all(
            abs(u - v) < 1e-6
            for want, got in zip([*shaft, *head], [*ln.shaft, *ln.head], strict=True)
            for u, v in zip(want, got, strict=True)
        )
        if not (same and abs(tx - ln.tag_x) < 1e-6 and abs(ty - ln.tag_y) < 1e-6):
            out.append(f"{ln.pred_name} → {ln.succ_name} ({ln.kind}): {ln.shaft} != {shaft}")
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
def dense() -> list[tuple[str, Layout | CompareLayout, int]]:
    """160 seeds, 3-40 items, chains of 2-6 links, as both slides."""
    return list(_slides(range(0, 160), (3, 40), 6))


def test_property_every_route_on_a_dense_slide_is_the_readme_route(
    dense: list[tuple[str, Layout | CompareLayout, int]],
) -> None:
    """Every link the generator makes is drawn — none refused, none flagged, no note — and its
    shaft, head and tag are exactly the README's route over the slide's own items: its edges at
    its centre line, its column the one of the band behind the fewest bars (ghosts and move
    arrows included), then names, nearest the successor; round the successor's row boundary
    when no column stands."""
    assert sum(len(lay.links) for _w, lay, _n in dense) > 1000  # the population is not empty
    shapes = {len(ln.shaft) for _w, lay, _n in dense for ln in lay.links}
    assert shapes == {2, 4, 6}  # straight, one vertical and the way round all occur
    bad = [f"{what}: {e}" for what, lay, _n in dense for e in _off_readme(lay)]
    undrawn = [(what, lay.link_notes[:1]) for what, lay, n in dense if len(lay.links) != n]
    assert bad == [] and undrawn == [], (bad[:3], undrawn[:3])


def test_property_a_small_slide_draws_every_link_and_says_nothing() -> None:
    """A slide of at most 6 items and at most 3 links: every link drawn on the README's route,
    no note at all (the built tree put the "At this density … Split the list" note on 3-item
    slides)."""
    bad = []
    for what, lay, n in _slides(range(1000, 1200), (3, 6), 3):
        if lay.link_notes or len(lay.links) != n or _off_readme(lay):
            bad.append((what, len(lay.links), n, lay.link_notes[:1], _off_readme(lay)[:1]))
    assert bad == [], bad[:5]


@pytest.mark.parametrize("module", [op, opc], ids=["one-pager", "compare"])
def test_mutation_a_slide_that_hands_the_router_no_names_is_caught(
    monkeypatch: pytest.MonkeyPatch, module: Any
) -> None:
    """Teeth: the slide's obstacles stripped of their names (labels, tags) — the router then
    stands columns behind names it no longer sees, and the SAME oracle names those links."""
    monkeypatch.setattr(
        module, "Obstacle", lambda key, y, x0, x1, names=(): links_mod.Obstacle(key, y, x0, x1)
    )
    which = 0 if module is op else 1
    bad = [
        e
        for k, (_w, lay, _n) in enumerate(_slides(range(0, 60), (3, 40), 6))
        if k % 2 == which
        for e in _off_readme(lay)
    ]
    assert bad, "the oracle must see routes off the README when the names are not handed over"


def _pulled_in_across() -> tuple[Any, list[Link]]:
    """Probe was 9/1-10/31 and is now 2/1-3/1: its ghost and its move arrow (10/31 back to 3/1)
    span 2/1-10/31 in the row between A (above) and Z (the next swimlane, starting 11/1). An
    A → Z column nearest Z's stub stands behind the GHOST; with the ghost and the arrow seen, the
    only free column is the one beside A."""

    def doc(source: str, start: D, finish: D) -> OnePagerDoc:
        items = [
            OnePagerItem("Lane", "A", D(2027, 1, 4), D(2027, 1, 20), 2),
            OnePagerItem("Lane", "Probe", start, finish, 3),
            OnePagerItem("Next", "Z", D(2027, 11, 1), D(2027, 12, 20), 4),
        ]
        return OnePagerDoc(source, "S", tuple(keyed(items)), (), ())

    cmp = compare_onepager_docs(
        doc("p.xlsx", D(2027, 9, 1), D(2027, 10, 31)), doc("c.xlsx", D(2027, 2, 1), D(2027, 3, 1))
    )
    k = {r.name: r.key for r in cmp.rows}
    return cmp, [Link(k["A"], k["Z"])]


def test_a_compare_column_never_stands_behind_a_ghost_or_a_move_arrow() -> None:
    doc, links = _pulled_in_across()
    lay = build_compare_layout(doc, TODAY, "T", links=links)
    a, probe, z = (next(p for p in lay.items if p.name == n) for n in ("A", "Probe", "Z"))
    assert a.y < probe.y < z.y and probe.ghost_x1 is not None and probe.arrow_x0 is not None
    (ln,) = lay.links
    assert _off_readme(lay) == []
    assert ln.shaft[1][0] < probe.x0  # the free column beside A, not one behind the ghost


def test_a_windowed_move_arrow_running_to_the_edge_is_part_of_its_rows_obstacle() -> None:
    """With a date window a row that slipped OUT of it keeps its ghost and an arrow to the chart's
    edge — the arrow then reaches past every shape the row still draws (its current one is off
    the slide). Mover sits between A and Z (three swimlanes); its ghost is 4/1-5/1 and its arrow
    runs on to 6/30, so every column from 4/1 on stands behind the ROW and the link takes the
    column before it — the README's route over the painted extent, the arrow included."""
    window = (D(2027, 3, 1), D(2027, 6, 30))

    def doc(source: str, start: D, finish: D) -> OnePagerDoc:
        items = [
            OnePagerItem("L1", "A", D(2027, 3, 2), D(2027, 3, 10), 2),
            OnePagerItem("L2", "Mover", start, finish, 3),
            OnePagerItem("L3", "Z", D(2027, 6, 26), D(2027, 6, 29), 4),
        ]
        return OnePagerDoc(source, "S", tuple(keyed(items)), (), ())

    full = compare_onepager_docs(
        doc("p.xlsx", D(2027, 4, 1), D(2027, 5, 1)), doc("c.xlsx", D(2027, 8, 1), D(2027, 8, 20))
    )
    cmp, _omitted = window_compare(full, window)
    k = {r.name: r.key for r in cmp.rows if r.key}
    lay = build_compare_layout(cmp, TODAY, "T", window=window, links=[Link(k["A"], k["Z"])])
    a, mover, z = (next(p for p in lay.items if p.name == n) for n in ("A", "Mover", "Z"))
    assert a.y < mover.y < z.y and mover.x0 is None and mover.ghost_x1 is not None
    assert mover.arrow_x0 is not None and mover.arrow_x1 is not None
    assert max(mover.arrow_x0, mover.arrow_x1) > mover.ghost_x1 + 50  # the arrow reaches past it
    (ln,) = lay.links
    assert _off_readme(lay) == []
    assert ln.shaft[1][0] < mover.ghost_x0  # the column before the row, not one beside Z


def test_mutation_a_compare_slide_that_hides_its_ghosts_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teeth for ADR-0543's ghost rule on a real slide: the Compare slide hands the router each
    row's CURRENT shape only (the prototype's blind side, and more) — the oracle, which reads the
    ghost and the move arrow off the layout, names the link standing behind them."""
    doc, links = _pulled_in_across()
    rows = {p.key: p for p in build_compare_layout(doc, TODAY, "T").items if p.key}
    real = links_mod.Obstacle

    def current_only(key: str, y: float, x0: float, x1: float, names: Any = ()) -> Any:
        p = rows.get(key)
        if p is not None and p.x0 is not None:
            x0, x1 = (p.x0 - p.ms / 2, p.x0 + p.ms / 2) if p.milestone else (p.x0, p.x1)
        return real(key, y, x0, x1, names)

    monkeypatch.setattr(opc, "Obstacle", current_only)
    assert _off_readme(build_compare_layout(doc, TODAY, "T", links=links)) != []


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
    """Review DOC-LS-01: Design → Build (FF) then Build → Deliver (FS) — two links meeting, not
    a dense slide; the built tree said "At this density … Split the list". Both are drawn, on
    the README's route, and the slide says nothing."""
    lay = _three()
    assert len(lay.links) == 2 and lay.link_notes == [] and _off_readme(lay) == []


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
