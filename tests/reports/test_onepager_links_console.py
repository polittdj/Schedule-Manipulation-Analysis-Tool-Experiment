"""The Console routing rule for One-Pager logic links (ADR-0543; the design handoff's "Logic-link
routing and z-order", steps 1-8) — :func:`route` and :func:`route_links` in
:mod:`schedule_forensics.reports.onepager_links`, and the anchors and obstacles the two slides
hand them.

What this module pins:

* **Each README step**, on hand-built anchors and obstacles: the four types' anchors (step 1),
  the stubs and the band (2-3, the SS / FF band one column at its closed side), the straight
  same-row link (4), the single vertical and its column — bars cost 10, names 3, distance
  from the successor's stub 0.002 a point, the first of equals (5), the go-round along the
  successor's row boundary on the side facing the predecessor (6), the head (7) and the tag (8).
* **Two cost mutants random layouts never kill** (measured: a NAME_COST 3 -> 1 mutant survives
  a 5,315-link differential against the prototype; BAR_COST 10 -> 3 is caught by 10 of those
  links) — each killed here by a fixture built for it.
* **ADR-0543's deliberate deviation from the prototype**: a Compare row's obstacle is its FULL
  painted extent — current shape, prior ghost (both sides of it) and move arrow; the prototype
  extended a row only leftward, so a ghost pulled in to the right of its bar was missed.
* **A frozen PROTOTYPE oracle** (``tests/fixtures/onepager_links_prototype_routes.json``): 190
  links the design handoff's own ``routeLinks`` (node) routed — an implementation independent
  of ours — reproduced to 1e-6, shaft, head and tag.
* **What the slides hand the router**: one anchor per keyed item at its shape's edges (a
  milestone's centre ± half its OWN diamond), one obstacle per item — its shape extent and its
  names (the label as painted; on Compare the NEW / REMOVED / DUPLICATE tag too).

Red first: on the pristine tree (fac5773) this module fails at import — ``route``, ``Obstacle``,
``crossings`` and the router's new ``Anchor`` do not exist there. Mutation proofs for the
load-bearing pins are the ``test_mutation_*`` twins and the cost-constant pins below (each names
the constant whose mutant it kills).
"""

from __future__ import annotations

import datetime as dt
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_compare as opc
from schedule_forensics.reports import onepager_links as links_mod
from schedule_forensics.reports.onepager import OnePagerDoc, OnePagerItem, build_layout, keyed
from schedule_forensics.reports.onepager_compare import build_compare_layout, compare_onepager_docs
from schedule_forensics.reports.onepager_links import (
    HEAD,
    Anchor,
    Grid,
    Link,
    Obstacle,
    crossings,
    route,
    route_links,
)

D = dt.date
DAY = D(2027, 1, 1)
TODAY = D(2027, 6, 1)
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "onepager_links_prototype_routes.json"


def _a(left: float, right: float, y: float) -> Anchor:
    return Anchor(left, right, y, DAY, DAY)


def _grid(*items: Obstacle, row_h: float = 20.0, limit: float = 1e9) -> Grid:
    return Grid(row_h, tuple(items), limit)


def _approx(points: Sequence[tuple[float, float]]) -> list[Any]:
    return [pytest.approx(p) for p in points]


# ── step 1: anchors ───────────────────────────────────────────────────────────────────────────

P, S = _a(100, 200, 50), _a(300, 400, 90)  # the predecessor a row above the successor


@pytest.mark.parametrize(
    ("kind", "a", "b"),
    [
        ("FS", (200, 50), (300, 90)),  # finish -> start
        ("SS", (100, 50), (300, 90)),  # start  -> start
        ("FF", (200, 50), (400, 90)),  # finish -> finish
        ("SF", (100, 50), (400, 90)),  # start  -> finish
    ],
)
def test_step_1_each_type_leaves_and_enters_the_edge_it_names(
    kind: str, a: tuple[float, float], b: tuple[float, float]
) -> None:
    """A finish end is the item's RIGHT edge, a start end its LEFT edge, both at its centre line;
    the head's tip touches the successor's edge there."""
    shaft, head, _tx, _ty = route(P, S, kind, _grid())
    assert shaft[0] == pytest.approx(a)
    assert head[0] == pytest.approx(b)


# ── steps 2-5: the band and the single vertical ───────────────────────────────────────────────


def test_step_5_a_forward_link_between_rows_is_one_vertical_beside_the_successor() -> None:
    """FS with nothing in the way: out along the predecessor's row, ONE vertical, in along the
    successor's row; the band is [ax, bx] = [p.right + 4, s.left - 6] and with every column
    free the one nearest the successor's stub wins (step 5's 0.002-per-point pull)."""
    shaft, _head, _tx, _ty = route(P, S, "FS", _grid())
    assert shaft == _approx([(200, 50), (294, 50), (294, 90), (300 - HEAD, 90)])


def test_step_5_a_band_narrower_than_half_a_point_has_one_column() -> None:
    p, s = _a(100, 200, 50), _a(210.3, 300, 90)  # ax = 204, bx = 204.3: one candidate, 204
    shaft, _h, _tx, _ty = route(p, s, "FS", _grid(Obstacle("x", 70, 203, 206)))
    assert shaft[1][0] == pytest.approx(204.0)  # even through a bar: there is no other column


@pytest.mark.parametrize(("kind", "column"), [("SS", 96.0), ("FF", 406.0)])
def test_step_3_an_ss_or_ff_band_is_one_column_at_its_closed_side(kind: str, column: float) -> None:
    """SS leaves leftward and enters from the left: only ``hi = min(ax, bx)`` bounds it, so its
    one column stands left of BOTH starts (the prototype's -1e9 sentinel resolves to exactly
    this); FF likewise right of both finishes — even with a bar in that column."""
    blocking = Obstacle("x", 70, column - 1, column + 1)
    shaft, _h, _tx, _ty = route(P, S, kind, _grid(blocking))
    assert len(shaft) == 4 and shaft[1][0] == pytest.approx(column) == shaft[2][0]


def _band(*items: Obstacle) -> float:
    """The column FS takes from P (100-200, y 50) to a successor at x 900 (y 110): its band runs
    from ax = 204 to bx = 894, so the candidates stand 86.25 pt apart: 204, 290.25, … 894."""
    p, s = _a(100, 200, 50), _a(900, 950, 110)
    shaft, _h, _tx, _ty = route(p, s, "FS", _grid(*items))
    return float(shaft[1][0])


def test_step_5_the_column_passes_behind_no_bar_when_one_is_free() -> None:
    assert _band() == pytest.approx(894.0)  # all free: nearest the successor
    bar = Obstacle("b", 70, 800, 899)  # covers the last two candidates (807.75 and 894)
    assert _band(bar) == pytest.approx(721.5)


def test_step_5_a_bar_is_counted_within_cross_pad_of_its_extent() -> None:
    """Step 5: "shape extent (±1.5pt)". A bar ending 1.4 pt short of the candidate covers it;
    one ending 1.6 pt short does not."""
    assert _band(Obstacle("b", 70, 600, 892.6)) == pytest.approx(894.0 - 86.25 * 4)
    assert _band(Obstacle("b", 70, 600, 892.4)) == pytest.approx(894.0)


def test_step_5_only_items_strictly_between_the_two_rows_and_not_its_own_ends_count() -> None:
    """The legs' own rows (y 50 and 110) are not crossed by the vertical, and the link's own two
    items are never obstacles to it."""
    on_rows = (Obstacle("r0", 50, 0, 960), Obstacle("r1", 110, 0, 960))
    assert _band(*on_rows) == pytest.approx(894.0)
    p, s = _a(100, 200, 50), _a(900, 950, 110)
    own = Obstacle("p", 70, 0, 960)  # keyed as the predecessor: skipped
    shaft, _h, _tx, _ty = route(p, s, "FS", _grid(own), ("p", "s"))
    assert shaft[1][0] == pytest.approx(894.0)


def test_step_5_bars_cost_more_than_names_and_ties_go_to_the_successor() -> None:
    """A name in the way is cheaper than a bar; among equally crossed columns the one nearest
    the successor's stub wins — and of exact equals, the first (the band is walked from lo)."""
    names_everywhere = Obstacle("n", 70, -10, -5, ((150, 950),))
    assert _band(names_everywhere) == pytest.approx(894.0)  # every column a name: nearest wins
    bar_near = Obstacle("b", 70, 850, 950)
    assert _band(names_everywhere, bar_near) == pytest.approx(807.75)
    assert crossings(500, 50, 110, _grid(names_everywhere, bar_near), ()) == (0, 1)
    assert crossings(894, 50, 110, _grid(names_everywhere, bar_near), ()) == (1, 1)


def test_a_name_costs_three_so_a_free_column_690_pt_away_beats_a_name() -> None:
    """Kills the NAME_COST 3 -> 1 mutant (it survives every random differential): every column
    but the farthest passes behind a name; the free column is 690 pt from the successor's stub,
    so it costs 1.38 — less than a name at 3, MORE than a name at 1."""
    name = Obstacle("n", 70, -10, -5, ((250, 950),))
    assert links_mod.NAME_COST == 3.0
    assert _band(name) == pytest.approx(204.0)


def test_a_bar_costs_ten_so_two_names_beat_one_bar() -> None:
    """Kills the BAR_COST 10 -> 3 mutant (10 of 5,315 random links catch it): the column beside
    the successor passes behind ONE bar; the next one behind TWO names (6 at a name's 3) and
    every other behind a bar and more. At 10 a bar costs more than two names; at 3 it would not."""
    near_bar = Obstacle("b", 70, 893, 895)
    two_names = (
        Obstacle("n1", 80, -10, -5, ((800, 810),)),
        Obstacle("n2", 90, -10, -5, ((800, 810),)),
    )
    elsewhere = Obstacle("c", 100, 150, 799, ((150, 799),))
    assert links_mod.BAR_COST == 10.0
    assert _band(near_bar, *two_names, elsewhere) == pytest.approx(807.75)


# ── steps 4 and 6: straight, and the way round ────────────────────────────────────────────────


def test_step_4_a_same_row_link_pointing_the_right_way_is_one_straight_segment() -> None:
    p, s = _a(100, 200, 50), _a(300, 400, 50)
    shaft, head, tag_x, tag_y = route(p, s, "FS", _grid())
    assert shaft == _approx([(200, 50), (300 - HEAD, 50)])
    assert head == _approx([(300, 50), (300 - HEAD, 50 - HEAD / 2), (300 - HEAD, 50 + HEAD / 2)])
    assert (tag_x, tag_y) == pytest.approx((250, 48.5))  # 1.5 pt above the middle
    back_p, back_s = _a(300, 400, 50), _a(100, 200, 50)  # SF leftward: start -> finish
    shaft, head, _tx, _ty = route(back_p, back_s, "SF", _grid())
    assert shaft == _approx([(300, 50), (200 + HEAD, 50)])


def test_step_4_needs_more_than_the_successors_stand_off() -> None:
    """Straight only when the successor is MORE than 6 pt the right way; at exactly 6 the link
    steps out and goes round above the successor's row."""
    p = _a(100, 200, 50)
    assert len(route(p, _a(206.01, 300, 50), "FS", _grid())[0]) == 2
    shaft, _h, _tx, _ty = route(p, _a(206, 300, 50), "FS", _grid())
    assert shaft == _approx(
        [(200, 50), (204, 50), (204, 40), (200, 40), (200, 50), (206 - HEAD, 50)]
    )


@pytest.mark.parametrize(
    ("p_y", "s_y", "gy"),
    [(90, 50, 60), (50, 90, 80), (50, 50, 40)],
    ids=["predecessor-below", "predecessor-above", "same-row"],
)
def test_step_6_a_backward_link_goes_round_on_the_side_facing_the_predecessor(
    p_y: float, s_y: float, gy: float
) -> None:
    """FS whose successor starts before the predecessor ends: out 4 pt, along the successor's
    row boundary — half a row (here 20) toward the predecessor, ABOVE it on its own row — and
    in 6 pt short of the successor."""
    p, s = _a(300, 400, p_y), _a(100, 200, s_y)
    shaft, head, tag_x, tag_y = route(p, s, "FS", _grid())
    assert shaft == _approx(
        [(400, p_y), (404, p_y), (404, gy), (94, gy), (94, s_y), (100 - HEAD, s_y)]
    )
    assert head[0] == pytest.approx((100, s_y))
    assert (tag_x, tag_y) == pytest.approx((405.5, (p_y + gy) / 2 + 1.5))


def test_step_6_different_rows_with_an_empty_band_go_round() -> None:
    """FS into a successor that starts 2 pt after the predecessor ends, a row below: ax = 204 >
    bx = 196, so no single vertical stands in the band."""
    p, s = _a(100, 200, 50), _a(202, 300, 70)
    shaft, _h, _tx, _ty = route(p, s, "FS", _grid())
    assert shaft == _approx(
        [(200, 50), (204, 50), (204, 60), (196, 60), (196, 70), (202 - HEAD, 70)]
    )


# ── steps 7 and 8: the head and the tag ───────────────────────────────────────────────────────


@pytest.mark.parametrize(("kind", "tip_x", "base_x"), [("FS", 300, 300 - HEAD), ("FF", 400, 404.2)])
def test_step_7_the_head_tips_on_the_edge_and_its_base_is_the_shafts_end(
    kind: str, tip_x: float, base_x: float
) -> None:
    shaft, head, _tx, _ty = route(P, S, kind, _grid())
    assert head == _approx([(tip_x, 90), (base_x, 90 - HEAD / 2), (base_x, 90 + HEAD / 2)])
    assert shaft[-1] == pytest.approx((base_x, 90))


def test_step_8_the_tag_stands_beside_the_first_vertical_and_fs_carries_none() -> None:
    names = {"p": "P", "s": "S"}
    anchors = {"p": P, "s": S}
    drawn, notes = route_links(
        [Link("p", "s", k) for k in ("FS", "SS", "FF", "SF")], anchors, names, _grid()
    )
    assert notes == [] and [d.tag for d in drawn] == ["", "SS", "FF", "SF"]
    for d in drawn:
        assert d.tag_pt == 5.0 and d.tag_anchor == "start"
        assert (d.tag_x, d.tag_y) == pytest.approx(
            (d.shaft[1][0] + 1.5, (d.shaft[1][1] + d.shaft[2][1]) / 2 + 1.5)
        )


# ── ADR-0543's deviation: a Compare row's obstacle is its FULL painted extent ─────────────────


def _pulled_in_compare() -> Any:
    """Probe — a MILESTONE — was 10/1; it is now 3/1: pulled in seven months, so its prior ghost
    diamond lies far to the RIGHT of its current one, and the move arrow runs from the ghost's
    CENTRE (10/1) back to 3/1 — the ghost's right half lies beyond every other part of the row.
    A (the row above Probe) and Z (the next swimlane, below it) carry the link."""

    def doc(source: str, when: D) -> OnePagerDoc:
        items = [
            OnePagerItem("Lane", "A", D(2027, 1, 4), D(2027, 1, 20), 2),
            OnePagerItem("Lane", "Probe", when, when, 3),
            OnePagerItem("Next", "Z", D(2027, 12, 1), D(2027, 12, 20), 4),
        ]
        return OnePagerDoc(source, "S", tuple(keyed(items)), (), ())

    return compare_onepager_docs(doc("p.xlsx", D(2027, 10, 1)), doc("c.xlsx", D(2027, 3, 1)))


def _spy_grid(monkeypatch: pytest.MonkeyPatch, module: Any) -> list[Grid]:
    """Every Grid a slide hands the router (the slide's own call, unchanged)."""
    grids: list[Grid] = []
    real = module.route_links

    def spy(links: Any, anchors: Any, names: Any, grid: Grid, absent: Any = None) -> Any:
        grids.append(grid)
        return real(links, anchors, names, grid, absent)

    monkeypatch.setattr(module, "route_links", spy)
    return grids


def test_a_pulled_in_ghost_right_of_its_bar_is_part_of_the_rows_obstacle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The prototype took ``min(left, ghost_x0) .. right``: a ghost pulled in to the RIGHT of the
    current shape was not an obstacle at all. Here the row's extent runs to the GHOST diamond's
    right vertex — past the current diamond and past the move arrow, which ends at the ghost's
    centre — and a column through that half of the ghost alone counts it as a BAR."""
    doc = _pulled_in_compare()
    k = {r.name: r.key for r in doc.rows}
    grids = _spy_grid(monkeypatch, opc)
    lay = build_compare_layout(doc, TODAY, "T", links=[Link(k["A"], k["Z"])])
    (grid,) = grids
    probe = next(p for p in lay.items if p.name == "Probe")
    assert probe.milestone and probe.ghost_milestone and probe.x0 is not None
    assert probe.ghost_x0 is not None and probe.arrow_x0 == pytest.approx(probe.ghost_x0)
    ghost_right = probe.ghost_x0 + probe.ghost_ms / 2
    assert ghost_right > max(probe.x0 + probe.ms / 2, probe.arrow_x0, probe.arrow_x1 or 0.0)
    ob = next(o for o in grid.items if o.key == k["Probe"])
    assert (ob.x0, ob.x1) == pytest.approx((probe.x0 - probe.ms / 2, ghost_right))
    a, z = (next(p for p in lay.items if p.name == n) for n in ("A", "Z"))
    beyond_the_arrow = probe.ghost_x0 + probe.ghost_ms / 4
    assert crossings(beyond_the_arrow, a.y, z.y, grid, (k["A"], k["Z"])) == (1, 0)


def test_the_router_sees_every_part_of_a_moved_rows_shape_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On the Compare sweep: each row's obstacle spans its current shape, its ghost and its
    move arrow (each diamond at its OWN size), and its names are the label as painted — an
    end-anchored label with a tag ending where the tag's gap begins — and the tag box."""
    from reports.test_onepager_links import _compare_sweep_doc, _sweep_links

    doc = _compare_sweep_doc(6, 6)
    keys = [r.key for r in doc.rows if r.key]
    grids = _spy_grid(monkeypatch, opc)
    lay = build_compare_layout(doc, TODAY, "T", links=_sweep_links(keys))
    (grid,) = grids
    assert len(grid.items) == len(lay.items) and grid.row_h == lay.row_h
    tagged = moved = 0
    for p, ob in zip(lay.items, grid.items, strict=True):
        spans = []
        if p.x0 is not None and p.x1 is not None:
            h = p.ms / 2
            spans.append((p.x0 - h, p.x0 + h) if p.milestone else (p.x0, p.x1))
        if p.ghost_x0 is not None and p.ghost_x1 is not None:
            h = p.ghost_ms / 2
            spans.append(
                (p.ghost_x0 - h, p.ghost_x0 + h) if p.ghost_milestone else (p.ghost_x0, p.ghost_x1)
            )
        if p.arrow_x0 is not None and p.arrow_x1 is not None:
            moved += 1
            spans.append(tuple(sorted((p.arrow_x0, p.arrow_x1))))
        assert (ob.key, ob.y) == (p.key, p.y)
        assert (ob.x0, ob.x1) == pytest.approx((min(s[0] for s in spans), max(s[1] for s in spans)))
        right = p.label_x - (p.badge_w + 2 if p.badge else 0.0)
        words = (
            (right - p.label_w, right)
            if p.label_anchor == "end"
            else (
                p.label_x,
                p.label_x + p.label_w,
            )
        )
        want = [words] + ([(p.badge_x, p.badge_x + p.badge_w)] if p.badge else [])
        tagged += bool(p.badge)
        assert [tuple(n) for n in ob.names] == [pytest.approx(w) for w in want], p.name
    assert tagged and moved  # the sweep carries NEW / REMOVED tags and move arrows


def test_an_end_anchored_label_with_a_tag_is_handed_over_as_painted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A NEW item at the chart's right edge has its label ANCHORED AT ITS END, left of the shape,
    with the NEW tag between the text and the shape (``badge_x .. badge_x + badge_w``, ending at
    ``label_x``): the painters draw the text ending ``badge_w + 2`` short of ``label_x``, so the
    router's name for it must too — not the text shifted onto the tag."""
    prior = [
        OnePagerItem("Lane", "A", D(2027, 1, 4), D(2027, 1, 20), 2),
        OnePagerItem("Next", "Z", D(2027, 6, 1), D(2027, 6, 20), 3),
    ]
    late = OnePagerItem("Mid", "A newly added late item", D(2027, 12, 1), D(2027, 12, 31), 4)
    doc = compare_onepager_docs(
        OnePagerDoc("p.xlsx", "S", tuple(keyed(prior)), (), ()),
        OnePagerDoc("c.xlsx", "S", tuple(keyed([*prior, late])), (), ()),
    )
    k = {r.name: r.key for r in doc.rows if r.key}
    grids = _spy_grid(monkeypatch, opc)
    lay = build_compare_layout(doc, TODAY, "T", links=[Link(k["A"], k["Z"])])
    (grid,) = grids
    p = next(q for q in lay.items if q.name == late.name)
    assert p.badge == "NEW" and p.label_anchor == "end"
    ob = next(o for o in grid.items if o.key == p.key)
    text_right = p.label_x - p.badge_w - 2
    assert [tuple(n) for n in ob.names] == [
        pytest.approx((text_right - p.label_w, text_right)),
        pytest.approx((p.badge_x, p.badge_x + p.badge_w)),
    ]
    assert p.badge_x + p.badge_w == pytest.approx(p.label_x)  # the tag ends where the anchor is


def test_the_timeline_hands_the_router_each_items_edges_and_its_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One anchor per item at its shape's edges — a milestone's centre ± half its OWN diamond
    (clamped at the chart's edge, ADR-0540 review F1) — and one obstacle: that extent and the
    label as painted."""
    from reports.test_onepager_links import _sweep_items, _sweep_links

    # the sweep plus a milestone on the timescale's first day: its diamond is clamped to 6 pt
    its = keyed(
        [*_sweep_items(6, 6), OnePagerItem("Lane 0", "Edge", D(2027, 1, 1), D(2027, 1, 1), 99)]
    )
    grids = _spy_grid(monkeypatch, op)
    lay = build_layout(its, TODAY, "T", links=_sweep_links([i.key for i in its]))
    (grid,) = grids
    assert any(p.milestone and p.ms != lay.ms for p in lay.items)  # an own size is exercised
    for p, ob in zip(lay.items, grid.items, strict=True):
        left, right = (p.x0 - p.ms / 2, p.x0 + p.ms / 2) if p.milestone else (p.x0, p.x1)
        assert ob.key == p.key and (ob.y, ob.x0, ob.x1) == pytest.approx((p.y, left, right))
        lab = (
            (p.label_x - p.label_w, p.label_x)
            if p.label_anchor == "end"
            else (
                p.label_x,
                p.label_x + p.label_w,
            )
        )
        assert [tuple(n) for n in ob.names] == [pytest.approx(lab)]
    by_key = {p.key: p for p in lay.items}
    for ln in lay.links:  # and the routes start and end on those edges
        p, s = by_key[ln.pred], by_key[ln.succ]
        pe = (p.x0 - p.ms / 2, p.x0 + p.ms / 2) if p.milestone else (p.x0, p.x1)
        se = (s.x0 - s.ms / 2, s.x0 + s.ms / 2) if s.milestone else (s.x0, s.x1)
        from_start, to_start = ln.kind[0] == "S", ln.kind[1] == "S"
        assert ln.shaft[0] == pytest.approx((pe[0] if from_start else pe[1], p.y))
        assert ln.head[0] == pytest.approx((se[0] if to_start else se[1], s.y))


# ── the frozen PROTOTYPE oracle ───────────────────────────────────────────────────────────────


def _prototype_cases() -> list[dict[str, Any]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "routeLinks" in data["_provenance"]
    return list(data["cases"])


def _route_case(case: dict[str, Any]) -> list[Any]:
    """The fixture's case through OUR router, built as the prototype sees it: a row's obstacle is
    its shape's extent and its label (``label_x`` and ``lw``, anchored start or end)."""
    obstacles, anchors = [], {}
    for it in case["items"]:
        lx, lw = it["label_x"], it["lw"]
        name = (lx - lw, lx) if it["label_anchor"] == "end" else (lx, lx + lw)
        obstacles.append(Obstacle(it["key"], it["y"], it["left"], it["right"], (name,)))
        anchors[it["key"]] = Anchor(it["left"], it["right"], it["y"], DAY, DAY)
    links = [Link(ln["pred"], ln["succ"], ln["kind"]) for ln in case["links"]]
    drawn, notes = route_links(links, anchors, {}, Grid(case["row_h"], tuple(obstacles), 1e9))
    assert notes == []
    return drawn


def _mismatches(cases: list[dict[str, Any]]) -> list[str]:
    out = []
    for ci, case in enumerate(cases):
        for want, got in zip(case["links"], _route_case(case), strict=True):
            if len(want["shaft"]) != len(got.shaft):
                out.append(f"case {ci} {want['pred']}→{want['succ']} ({want['kind']}): shape")
                continue
            pts = [
                *zip(want["shaft"], got.shaft, strict=True),
                *zip(want["head"], got.head, strict=True),
            ]
            same = all(
                math.isclose(w, g, abs_tol=1e-6) for a, b in pts for w, g in zip(a, b, strict=True)
            )
            same = same and math.isclose(want["tag_x"], got.tag_x, abs_tol=1e-6)
            same = same and math.isclose(want["tag_y"], got.tag_y, abs_tol=1e-6)
            if not same:
                out.append(f"case {ci} {want['pred']}→{want['succ']} ({want['kind']})")
    return out


def test_our_router_reproduces_every_route_the_prototype_drew() -> None:
    cases = _prototype_cases()
    assert sum(len(c["links"]) for c in cases) >= 150
    kinds = {ln["kind"] for c in cases for ln in c["links"]}
    shapes = {len(ln["shaft"]) for c in cases for ln in c["links"]}
    assert kinds == {"FS", "SS", "FF", "SF"} and shapes == {2, 4, 6}  # every type, every shape
    assert _mismatches(cases) == []


@pytest.mark.parametrize(
    ("name", "value"),
    [("BAR_COST", 3.0), ("CROSS_PAD", 0.0), ("PULL", -0.002), ("STUB_OUT", 5.0)],
)
def test_mutation_the_prototype_oracle_names_a_mutated_constant(
    monkeypatch: pytest.MonkeyPatch, name: str, value: float
) -> None:
    """Teeth: each constant mutated in memory, the SAME oracle reports routes off the
    prototype's (the fixture keeps every link the BAR_COST and CROSS_PAD mutants route
    differently)."""
    monkeypatch.setattr(links_mod, name, value)
    assert _mismatches(_prototype_cases()) != []


def test_mutation_the_name_and_bar_pins_kill_the_cost_mutants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two targeted fixtures above, under the mutants they were built for."""
    name = Obstacle("n", 70, -10, -5, ((250, 950),))
    monkeypatch.setattr(links_mod, "NAME_COST", 1.0)
    assert _band(name) != pytest.approx(204.0)
    monkeypatch.setattr(links_mod, "NAME_COST", 3.0)
    monkeypatch.setattr(links_mod, "BAR_COST", 3.0)
    near_bar = Obstacle("b", 70, 893, 895)
    two_names = (
        Obstacle("n1", 80, -10, -5, ((800, 810),)),
        Obstacle("n2", 90, -10, -5, ((800, 810),)),
    )
    elsewhere = Obstacle("c", 100, 150, 799, ((150, 799),))
    assert _band(near_bar, *two_names, elsewhere) != pytest.approx(807.75)
