"""ADR-0540's full-page fill, and ADR-0543's single layout: the One-Pager rows FILL the slide,
and the slide is laid out ONCE — its logic links never move an item.

The operator's rulings (2026-09-29): (a) the slide's rows, bars and labels scale to use the
whole slide — fewer items, larger bars and text. ADR-0540's second ruling — fit every link by
escalation (more room between the rows, a gutter lane, a reorder within a swimlane, and as the
last resort a link drawn dashed and named in a footnote) — is SUPERSEDED by ADR-0543 (the design
handoff's Console rule): a link's shaft runs UNDER the items and its head over them, so no route
collides with anything, nothing escalates, and every link whose two ends are on the slide is
drawn. What this module pins of that:

* the fill (unchanged since ADR-0540) and the diamond cap;
* the slide is laid out once — with its links it is item for item the slide without them, on
  every dense slide of an independent generator, the four seeds that DID escalate on the
  pristine tree included — and every link is drawn, with no note;
* the router runs once per slide (it ran up to ten times under the escalation), deterministic;
* the Excel Notes carry no fitting sentence, and the retired fitting fields and names are gone;
* the per-state cache and its snapshot (ADR-0540's review, unchanged).

Red first: on the pristine tree (fac5773) the single-layout, route-once, Excel and retired-names
pins fail — its escalation re-laid the four seeds' slides (glyphs at 80 %, a gutter, a reorder,
a reserved footnote band), called the router once per attempt, wrote "reordered within their
swimlane" into the Excel Notes, and carried ``fit_notes`` / ``footnote`` / ``gutter``. The
generator of dense slides below is INDEPENDENT of the layout's code.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import random
from collections.abc import Sequence
from typing import Any

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_compare as opc
from schedule_forensics.reports.onepager import (
    BAR_F,
    LABEL_MAX,
    LANES_Y1,
    MS_F,
    X1,
    Layout,
    OnePagerDoc,
    OnePagerItem,
    build_layout,
    keyed,
    layout_json,
)
from schedule_forensics.reports.onepager_compare import (
    CompareLayout,
    build_compare_layout,
    compare_onepager_docs,
)
from schedule_forensics.reports.onepager_links import LINK_TYPES, Link
from schedule_forensics.web import onepager_actions as act
from schedule_forensics.web import onepager_common
from schedule_forensics.web.onepager import linkable_items, onepager_layout
from schedule_forensics.web.onepager_compare import linkable_rows
from schedule_forensics.web.state import SessionState
from web.onepager_twin import twin_xlsx

D = dt.date
TODAY = D(2026, 1, 1)
HEAD = ("Swimlane", "Task", "Start", "Finish", "Complete")
MB = 10 * 1024 * 1024


# ── an independent generator of dense slides ──────────────────────────────────────────────────


def _slide(
    seed: int, n_items: tuple[int, int], n_links: tuple[int, int]
) -> tuple[list[OnePagerItem], list[Link]]:
    """A seeded list of 2-5 swimlanes over ~18 months (milestones, 1-3-day bars, long bars) and
    a DAG of links running forward in a random order of the items — the shape a busy programme
    review carries, written without the router's or the layout's code."""
    r = random.Random(seed)
    n = r.randint(*n_items)
    lanes = ["Eng", "Ops", "Test", "Sup", "Mgmt"][: r.randint(2, 5)]
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
    links: list[Link] = []
    for _ in range(r.randint(*n_links)):
        a, b = sorted(r.sample(order, 2), key=rank.__getitem__)
        ln = Link(a, b, r.choice(LINK_TYPES))
        if ln not in links:
            links.append(ln)
    return items, links


#: Seeds of the generator above whose BASE layout (no escalation) leaves a link no route clears,
#: by the step that resolves it (found by a search over seeds 0-420, recorded in ADR-0540).
#: SHRINK was 69 until the review's `GLYPH_MAX` (smaller glyphs at that density left room at
#: base); 36 is the first seed step 1 alone resolves on the capped slide
#: Seeds of the generator above whose layout ESCALATED on the pristine tree (ADR-0540's search
#: over seeds 0-420), by the step that resolved them there: glyphs at 80 %, a gutter lane, a
#: reorder within the swimlane, the dashed last resort. Under ADR-0543 none of them escalates.
SHRINK, GUTTER, REORDER, FORCE = 36, 111, 164, 197
DENSE = ((30, 110), (8, 40))


def _items(n: int, lanes: int = 3) -> list[OnePagerItem]:
    rnd = random.Random(n)
    out = []
    for i in range(n):
        s = D(2026, 1, 5) + dt.timedelta(days=rnd.randint(0, 600))
        f = s + dt.timedelta(days=rnd.choice([0, 0, 14, 30, 60, 90]))
        out.append(OnePagerItem(f"Lane {i % lanes + 1}", f"Item {i + 1}", s, f, i + 2))
    return keyed(out)


def _compare(n: int) -> Any:
    prior = _items(n)
    moved = [
        OnePagerItem(
            i.lane, i.name, i.start, i.finish + dt.timedelta(days=(7 if k % 3 == 0 else 0)), i.row
        )
        for k, i in enumerate(prior)
    ]
    return compare_onepager_docs(
        OnePagerDoc("p.xlsx", "S", tuple(prior), (), ()),
        OnePagerDoc("c.xlsx", "S", tuple(keyed(moved)), (), ()),
    )


# ── the full-page fill ────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("n", [3, 10, 40])
def test_the_rows_fill_the_slide_on_both_pages(n: int) -> None:
    """Operator ruling (a): the lanes reach the bottom of the lane area at every size — on the
    pristine tree a 3-item slide reached 13.7 % of it (rows capped at 13 pt)."""
    lay = build_layout(_items(n), TODAY, "T")
    clay = build_compare_layout(_compare(n), TODAY, "C")
    for slide in (lay, clay):
        assert slide.lanes_y1 == pytest.approx(LANES_Y1, abs=0.01), (n, slide.lanes_y1)
        assert slide.row_h > 13.0  # the old cap
        # the glyphs are sized from the packed row height — the pitch, or a few percent under
        # it where the packing has no fixed point (fit_rows) — never over it
        glyph = min(slide.row_h, op.GLYPH_MAX)  # the review's cap: a bar 27 pt, a diamond 25
        assert 0.9 * glyph * BAR_F <= slide.bar_h <= glyph * BAR_F + 1e-9
        assert 0.9 * glyph * MS_F <= slide.ms <= glyph * MS_F + 1e-9
        for p in slide.items:
            band = slide.lanes[p.lane]
            assert band.y0 < p.y < band.y1


def test_fewer_items_give_larger_bars_and_text_up_to_the_label_cap() -> None:
    three, forty = build_layout(_items(3), TODAY, "T"), build_layout(_items(40), TODAY, "T")
    assert three.row_h > forty.row_h and three.bar_h > forty.bar_h
    assert three.label_pt == LABEL_MAX and forty.label_pt < LABEL_MAX
    assert three.lanes[0].name_pt > forty.lanes[0].name_pt  # the swimlane names grow too


def test_mutation_the_fill_check_goes_red_under_the_old_row_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = op.fit_rows

    def capped(pack: Any, avail: float) -> tuple[float, float, float, bool]:
        row_h, glyph_h, label_pt, fits = real(pack, avail)
        return min(row_h, 13.0), min(glyph_h, 13.0), min(label_pt, 8.0), fits

    monkeypatch.setattr(op, "fit_rows", capped)
    lay = build_layout(_items(3), TODAY, "T")
    assert lay.lanes_y1 < LANES_Y1 - 100  # the same measure the test above takes


def test_a_dense_list_still_steps_the_floors_down_and_fills_the_slide() -> None:
    """The floors are untouched: 144 items land at the 5-pt label floor and the slide is still
    exactly one slide — filled to the bottom of the lane area."""
    lay = build_layout(_items(144), TODAY, "T")
    assert lay.label_pt == pytest.approx(5.0) and lay.lanes_y1 == pytest.approx(LANES_Y1, abs=0.01)


# ── the slide is laid out once: its links never move an item (ADR-0543) ─────────────────────


def _geometry(lay: Layout | CompareLayout) -> dict[str, Any]:
    """Everything a slide places, without its links: the layout's JSON minus the link fields."""
    data = layout_json(lay) if isinstance(lay, Layout) else opc.compare_layout_json(lay)
    legend = [e for e in data["legend"] if e["kind"] != "link"]
    out = {k: v for k, v in data.items() if k not in ("links", "link_notes", "legend", "legend_pt")}
    return out | {"legend": [(e["kind"], e["label"]) for e in legend]}


@pytest.mark.parametrize("seed", [SHRINK, GUTTER, REORDER, FORCE, *range(0, 8)])
def test_a_slide_is_laid_out_once_and_its_links_never_move_an_item(seed: int) -> None:
    """With its links the slide IS the slide without them — rows, bars, labels, lanes, the
    chart's right edge, the lane area — and every link is drawn, with no note: on the pristine
    tree these four seeds were re-laid by the escalation (the 80-% glyphs, the gutter lane, the
    reorder, the footnote band), and its other seeds refused or flagged links."""
    items, links = _slide(seed, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    bare = build_layout(items, TODAY, "T")
    assert _geometry(lay) == _geometry(bare)
    assert lay.x1 == X1 and lay.lanes_y1 == pytest.approx(bare.lanes_y1)
    assert len(lay.links) == len(links) and lay.link_notes == []


def test_the_compare_slide_is_laid_out_once_too() -> None:
    """The Compare slide routes by the same rule: the 12 x 12 sweep (which escalated to a
    reorder and ten dashed links on the pristine tree) is the slide without its links."""
    from reports.test_onepager_links import _compare_sweep_doc, _sweep_links

    doc = _compare_sweep_doc(12, 12)
    links = _sweep_links([r.key for r in doc.rows if r.key])
    lay = build_compare_layout(doc, TODAY, "T", links=links)
    assert _geometry(lay) == _geometry(build_compare_layout(doc, TODAY, "T"))
    assert len(lay.links) == len(links) and lay.link_notes == []


def test_mutation_a_layout_that_moves_items_for_its_links_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teeth: a layout that narrows the chart whenever it has links (the pristine gutter's
    shape) — the geometry check names it."""
    real = op.build_layout

    def gutter(items: Any, today: Any, title: Any, *a: Any, **k: Any) -> Layout:
        lay = real(items, today, title, *a, **k)
        return dataclasses.replace(lay, x1=lay.x1 - 12.0) if k.get("links") else lay

    items, links = _slide(GUTTER, *DENSE)
    monkeypatch.setattr(op, "build_layout", gutter)
    moved = op.build_layout(items, TODAY, "T", links=links)
    assert _geometry(moved) != _geometry(op.build_layout(items, TODAY, "T"))


def test_the_router_runs_once_per_slide_and_the_slide_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The escalation called the router once per ATTEMPT — up to ten times on one slide, paced
    by a work budget; the slide now calls it once, and two runs lay the same slide out the same
    way. A 96-item, 120-link slide — past any real programme review — draws every link."""
    calls: list[int] = []
    real = op._logic

    def spy(*a: Any, **k: Any) -> Any:
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(op, "_logic", spy)
    items, links = _slide(FORCE, *DENSE)
    a = build_layout(items, TODAY, "T", links=links)
    assert len(calls) == 1
    assert layout_json(a) == layout_json(build_layout(items, TODAY, "T", links=links))
    big = _items(96)
    rnd = random.Random(96)
    keys = [it.key for it in big]
    many: list[Link] = []
    while len(many) < 120:
        p, s = rnd.sample(keys, 2)
        ln = Link(p, s, rnd.choice(LINK_TYPES))
        if ln not in many and not any(m.pred == s and m.succ == p for m in many):
            many.append(ln)
    calls.clear()
    lay = build_layout(big, TODAY, "T", links=many)
    assert len(calls) == 1 and len(lay.links) == 120 and lay.link_notes == []


def test_the_retired_fitting_fields_and_names_are_gone() -> None:
    """ADR-0543 retired ADR-0540's escalation entirely: no slide carries fitting notes, a
    footnote or a gutter lane, and the escalation's machinery is not left behind as dead code a
    test could still poke."""
    retired_fields = {
        "fit_notes", "footnote", "footnote_x", "footnote_y", "footnote_pt", "footnote_lh", "gutter",
    }  # fmt: skip
    for cls in (Layout, CompareLayout):
        assert retired_fields.isdisjoint(f.name for f in dataclasses.fields(cls)), cls
    gone = (
        "Fit", "Attempt", "fit_links", "escalation_words", "fit_notes", "disclose_fit",
        "spare_row_footnote", "footnote_text", "footnote_lines", "footnote_entries",
        "apply_swaps", "reordered_names", "CROWDED_NOTE", "GLYPH_STEPS", "GUTTER_W",
        "RESERVE_NOTE", "WORK_BUDGET", "REORDER_TRIALS", "FOOT_H", "FOOT_PT",
    )  # fmt: skip
    assert [n for n in gone if hasattr(op, n) or hasattr(opc, n)] == []
    assert not hasattr(opc, "_keep_outs")


def _rows(items: Sequence[OnePagerItem]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (it.lane, it.name, it.start.isoformat(), it.finish.isoformat(), "") for it in items
    )


def test_the_excel_list_keeps_the_sheets_order_and_its_notes_carry_no_fitting_sentence() -> None:
    """The seed the pristine tree REORDERED to fit its links: through the page's own actions,
    the Excel list keeps the sheet's order and its Notes say nothing about fitting links (the
    pristine Notes led with "… reordered within their swimlane to fit the logic links")."""
    items, links = _slide(REORDER, *DENSE)
    st = SessionState()
    act.load_list(st, "list.xlsx", twin_xlsx((HEAD, *_rows(items))), max_bytes=MB)
    assert st.onepager is not None
    by_name = {label.split(" · ")[1].split(" (")[0]: k for k, label, _r in linkable_items(st)}
    name_of = {it.key: it.name for it in items}
    for ln in links:
        act.edit_links(
            st, "onepager", "add", by_name[name_of[ln.pred]], by_name[name_of[ln.succ]], ln.kind
        )
    lay = onepager_layout(st, TODAY)
    assert lay is not None and len(lay.links) == len(links)
    ts = act.onepager_workbook(st, TODAY)
    assert not isinstance(ts, str)
    listed = next(t for t in ts.tables if t.title.startswith("One-Pager items"))
    assert [r[1] for r in listed.rows] == [it.name for it in st.onepager.items]  # sheet order
    notes = " ".join(str(r[0]) for r in next(t for t in ts.tables if t.title == "Notes").rows)
    for fitting in ("reordered", "gutter", "of their page-filling size", "footnote"):
        assert fitting not in notes, fitting


def test_the_layout_is_laid_out_once_per_state_and_again_when_the_state_changes() -> None:
    st = SessionState()
    act.load_list(st, "list.xlsx", twin_xlsx((HEAD, *_rows(_items(6)))), max_bytes=MB)
    first = onepager_layout(st, TODAY)
    assert first is not None and onepager_layout(st, TODAY) is first
    keys = [k for k, _l, _r in linkable_items(st)]
    act.edit_links(st, "onepager", "add", keys[0], keys[1], "FS")
    second = onepager_layout(st, TODAY)
    assert second is not None and second is not first and len(second.links) == 1
    act.set_title(st, "Renamed")
    third = onepager_layout(st, TODAY)
    assert third is not second and third.title == "Renamed"
    assert onepager_layout(st, D(2027, 1, 1)) is not third  # today is part of the key


def test_mutation_a_cache_that_ignores_its_key_serves_a_stale_slide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from schedule_forensics.web import onepager as page

    def stale(st: Any, page_name: str, _key: object, compute: Any) -> Any:
        return onepager_common.cached_layout(st, page_name, "constant", compute)

    monkeypatch.setattr(page, "cached_layout", stale)
    st = SessionState()
    act.load_list(st, "list.xlsx", twin_xlsx((HEAD, *_rows(_items(6)))), max_bytes=MB)
    first = onepager_layout(st, TODAY)
    keys = [k for k, _l, _r in linkable_items(st)]
    act.edit_links(st, "onepager", "add", keys[0], keys[1], "FS")
    assert onepager_layout(st, TODAY) is first  # the check above would name this


@pytest.mark.parametrize("page_name", ["onepager", "compare"])
def test_a_link_added_while_the_slide_is_laid_out_never_leaves_a_stale_slide_behind(
    monkeypatch: pytest.MonkeyPatch, page_name: str
) -> None:
    """Review of ADR-0540 (F2): Polaris² serves the One-Pager routes with no session lock, so a
    POST can land while a GET is laying the slide out (up to 15 s on the stress case). The key
    was taken before the layout and the layout re-read the session after it — so the cache kept
    a slide of the NEW state under the OLD key, and served it once the state went back (remove
    the link: the link is still drawn). The layout and its key now read ONE snapshot of the
    session, taken at one instant: a slide is always exactly the state its key names, and the
    POST's own state is laid out afresh on the next read."""
    from schedule_forensics.web import onepager as page
    from schedule_forensics.web import onepager_compare as cpage

    st = SessionState()
    rows = twin_xlsx((HEAD, *_rows(_items(6))))
    if page_name == "onepager":
        act.load_list(st, "list.xlsx", rows, max_bytes=MB)
        keys = [k for k, _l, _r in linkable_items(st)]
        served, fresh, mod, hook = page.onepager_layout, page._onepager_layout, page, "windowed_doc"
    else:
        act.load_compare(st, "prior", "a.xlsx", rows, max_bytes=MB)
        act.load_compare(st, "current", "b.xlsx", rows, max_bytes=MB)
        keys = [k for k, _l, _r in linkable_rows(st)]
        served, fresh, mod = (
            cpage.onepager_compare_layout,
            cpage._onepager_compare_layout,
            cpage,
        )
        hook = "window_compare"
    orig, landed = getattr(mod, hook), []

    def post_lands_mid_layout(*a: Any, **k: Any) -> Any:
        if not landed:  # the first read of the list during the layout: a POST adds a link
            landed.append(True)
            act.edit_links(st, page_name, "add", keys[0], keys[1], "FS")
        return orig(*a, **k)

    monkeypatch.setattr(mod, hook, post_lands_mid_layout)
    torn = served(st, TODAY)
    assert torn is not None and landed
    assert not torn.links, "the slide answered a state it was not asked for"
    act.edit_links(st, page_name, "remove", keys[0], keys[1], "FS")  # back to the keyed state
    again, oracle = served(st, TODAY), fresh(st, TODAY)
    assert again is not None and oracle is not None
    assert not again.links and again.links == oracle.links and again == oracle


def test_the_snapshot_carries_every_attribute_of_the_session_protocol() -> None:
    """A protocol attribute the snapshot lacked would fail at the first page read that wants
    it — this names it at the attribute, in the change that adds it."""
    assert {f.name for f in dataclasses.fields(onepager_common.OnePagerSnapshot)} == set(
        onepager_common.OnePagerSession.__annotations__
    )


def test_the_cache_key_reads_every_field_of_a_link_not_only_its_identity() -> None:
    """Review of ADR-0540 (F6, latent): ``Link`` compares on ``(pred, succ, kind)`` alone, but
    the layout's absent-end notes are built from the ends' identities and labels — so two link
    tuples that are ``==`` can lay out differently. The key reads every field."""
    st = SessionState()
    act.load_list(st, "list.xlsx", twin_xlsx((HEAD, *_rows(_items(6)))), max_bytes=MB)
    keys = [k for k, _l, _r in linkable_items(st)]
    act.edit_links(st, "onepager", "add", keys[0], keys[1], "FS")
    first = onepager_layout(st, TODAY)
    (ln,) = st.onepager_links
    st.onepager_links = (dataclasses.replace(ln, pred_ident=("other", "name", "", "")),)
    assert st.onepager_links == (ln,)  # equal as links …
    assert onepager_layout(st, TODAY) is not first  # … but not the same layout


# ── the routing / rendering review of ADR-0540 (its third table): each pin was red as found ──

_REVIEW_NAMES = [
    "Design", "Build", "Test", "Ship", "Review", "CDR", "PDR", "Integrate", "Qualify",
    "Deliver", "Kickoff", "Audit", "Fix", "Retest", "Accept", "Close", "Plan", "Order parts",
    "Long lead procurement of the cryogenic assembly", "SRR", "TRR", "FRR", "ORR",
]  # fmt: skip
_REVIEW_WIDE = ["WWWWWW MMMMM", "Mmmm Wwww", "OMEGA WORKS", "Wide Milestone Mark"]
_REVIEW_TODAY = D(2026, 6, 1)


def _review_slide(
    seed: int, n_items: tuple[int, int] = (40, 140), n_links: tuple[int, int] = (10, 60)
) -> tuple[list[OnePagerItem], list[Link]]:
    """The routing review's OWN generator (ported verbatim, so its seeds reproduce here): 2-6
    swimlanes over ~20 months; 30 % milestones, 15 % 1-3-day bars, the rest 5-150-day bars;
    repeated names (dated keys), wide-glyph names, some complete; a DAG of links in a random
    topological order, all four types, a few fan-outs from one hub. Shares no code with the
    module's own generator above, nor with the router."""
    r = random.Random(seed * 1000003 + 17)
    n = r.randint(*n_items)
    lanes = ["Eng", "Ops", "Test", "Supply", "Mgmt", "Flight"][: r.randint(2, 6)]
    items = []
    for k in range(n):
        start = D(2026, 1, 5) + dt.timedelta(days=r.randrange(0, 600))
        kind = r.random()
        if kind < 0.3:
            finish = start
        elif kind < 0.45:
            finish = start + dt.timedelta(days=r.randint(1, 3))
        else:
            finish = start + dt.timedelta(days=r.randint(5, 150))
        q = r.random()
        if q < 0.08:
            name = r.choice(_REVIEW_WIDE)
        elif q < 0.3:
            name = r.choice(_REVIEW_NAMES)
        else:
            name = f"{r.choice(_REVIEW_NAMES)} {k}"
        complete = r.random() < 0.15
        items.append(OnePagerItem(r.choice(lanes), name, start, finish, k + 2, complete))
    items = keyed(items)
    order = [it.key for it in items]
    r.shuffle(order)
    rank = {k: i for i, k in enumerate(order)}
    links: list[Link] = []
    want = r.randint(*n_links)
    hub = r.choice(order)
    guard = 0
    while len(links) < want and guard < want * 20:
        guard += 1
        if r.random() < 0.15:
            a, b = sorted((hub, r.choice(order)), key=rank.__getitem__)
            if a == b:
                continue
        else:
            a, b = sorted(r.sample(order, 2), key=rank.__getitem__)
        ln = Link(a, b, r.choice(LINK_TYPES))
        if ln not in links:
            links.append(ln)
    return items, links


def _diamond_edges(lay: Layout | CompareLayout) -> list[tuple[str, float, float]]:
    """``(name, left, right)`` of every diamond drawn — the current one and, on Compare, the
    ghost — sized as the painters size it (the item's own size when it carries one)."""
    out = []
    for p in lay.items:
        if p.milestone and p.x0 is not None:
            half = getattr(p, "ms", lay.ms) / 2
            out.append((p.name, p.x0 - half, p.x0 + half))
        gx = getattr(p, "ghost_x0", None)
        if getattr(p, "ghost_milestone", False) and gx is not None:
            half = getattr(p, "ghost_ms", lay.ms) / 2
            out.append((f"{p.name} (prior)", gx - half, gx + half))
    return out


def test_review_a_diamond_never_leaves_the_chart_nor_covers_the_swimlane_names() -> None:
    """Routing review F1: the page-filling glyphs were sized from the uncapped row, so a 2-item
    list drew a 259-pt diamond — 107 pt off the slide on the Timeline, 119 pt into the Compare
    summary column, and over the swimlane-name column on a first-day milestone (still 25 pt
    past the chart at 5 items). A diamond's size is capped (a milestone is a date, not a span)
    and each one is clamped to the chart's edges, overhanging them by at most the 3 pt a dense
    slide always did."""
    kick = OnePagerItem("Eng", "Kickoff", D(2026, 3, 2), D(2026, 3, 20), 2)
    cdr = OnePagerItem("Eng", "CDR", D(2026, 6, 30), D(2026, 6, 30), 3)
    first = OnePagerItem("Eng", "Start MS", D(2026, 3, 1), D(2026, 3, 1), 2)
    work = OnePagerItem("Eng", "Work", D(2026, 3, 5), D(2026, 4, 5), 3)
    cases: list[Layout | CompareLayout] = [
        build_layout(keyed([kick, cdr]), _REVIEW_TODAY, "T"),
        build_layout(keyed([first, work]), _REVIEW_TODAY, "T"),
    ]
    for n in (1, 2, 3, 5, 8, 13, 40):
        items = [*_items(n), first, cdr]
        cases.append(build_layout(keyed(items), _REVIEW_TODAY, "T"))
    prior = OnePagerDoc("p", "S", tuple(keyed([kick, cdr])), (), ())
    cur = OnePagerDoc(
        "c",
        "S",
        tuple(keyed([kick, dataclasses.replace(cdr, finish=D(2026, 3, 1), start=D(2026, 3, 1))])),
        (),
        (),
    )
    cases.append(build_compare_layout(compare_onepager_docs(prior, cur), _REVIEW_TODAY, "C"))
    for lay in cases:
        assert lay.ms <= 30.0, lay.ms  # a milestone is a date, not a span
        for name, left, right in _diamond_edges(lay):
            assert left >= lay.x0 - 3.0 and right <= lay.x1 + 3.0, (
                name,
                left,
                right,
                lay.x0,
                lay.x1,
            )
            assert left >= lay.lane_col_x1, (name, left, lay.lane_col_x1)
            assert right <= 960.0


def test_review_a_list_that_fills_the_slide_keeps_every_link_on_it() -> None:
    """Routing review F2: 116 same-day milestones fill the slide to its last row; with links
    into one of them and into the last rows, the pristine escalation reserved a footnote band,
    sank the list ("runs off the bottom" for rows that were on the slide) and moved the DATA DATE
    caption. Laid out once, the list still fits, every link is drawn and nothing is named."""
    rows = 116
    its = keyed(
        [OnePagerItem("Eng", f"M{k}", D(2026, 3, 15), D(2026, 3, 15), k + 2) for k in range(rows)]
    )
    keys = [i.key for i in its]
    plain = build_layout(its, _REVIEW_TODAY, "T")
    assert not any("does not fit" in n for n in plain.notes) and plain.lanes_y1 == pytest.approx(
        LANES_Y1
    )
    links = [Link(keys[k], keys[9], "FS") for k in range(1, 9)] + [
        Link(keys[0], keys[rows - 1 - j], "FS") for j in range(3)
    ]
    lay = build_layout(its, _REVIEW_TODAY, "T", links=links)
    assert lay.link_notes == [] and not [n for n in lay.notes if "does not fit one slide" in n]
    assert len(lay.links) == len(links) and lay.lanes_y1 == pytest.approx(LANES_Y1)
    assert max(p.y for p in lay.items) < lay.legend_y0
    assert lay.today_label_y == plain.today_label_y


@pytest.mark.parametrize("seed", [1, 103, 105, 110])
def test_review_the_review_generators_slides_are_laid_out_once(seed: int) -> None:
    """The routing review's own generator (repeated names, wide glyphs, complete items, a hub of
    fan-out links): seed 1 put a clean head on an earlier leg, 103 and 110 reached the gutter
    lane and 105 reserved a footnote band with nothing to say on the pristine tree. Laid out
    once, each is its slide without links, every link drawn."""
    items, links = _review_slide(seed)
    lay = build_layout(items, _REVIEW_TODAY, "T", links=links)
    assert _geometry(lay) == _geometry(build_layout(items, _REVIEW_TODAY, "T"))
    assert len(lay.links) == len(links) and lay.link_notes == []
