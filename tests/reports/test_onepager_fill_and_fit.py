"""ADR-0540: the One-Pager rows FILL the slide, and every requested logic link is fitted — by
escalation, never by a second slide, and never silently.

The operator's rulings (2026-09-29): (a) the slide's rows, bars and labels scale to use the
whole slide — fewer items, larger bars and text; (b) to fit every link the layout may, in this
order, make more room between the rows, add a gutter lane at the chart's edge, and reorder items
WITHIN a swimlane (never across); (c) as the last resort a link no route clears is DRAWN along the
route that covers the least, flagged (dashed) and named on the page AND on the slide (its
footnote, which the .pptx carries); (d) a reorder is disclosed on the page, and the Excel list
keeps the sheet's own order.

Red first (2026-09-29, on 996b28b2 — the pristine tree): the fill tests fail there because the
rows were capped at 13 pt (a 3-item slide filled 13.7 % of the lane area, measured); every
escalation test fails there because the router refused a collision instead of escalating (the
links are "not drawn — every route it could take here would cover …"); the footnote, the fit
notes, ``PlacedLink.flagged`` and the cache do not exist there. The generator of dense slides
below is INDEPENDENT of the layout's code, and the ink oracle is the resume review's
(``test_onepager_links_resume``), which names every head, tag and move-arrow head a later link
covers. Mutation twins arm the load-bearing checks.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import io
import itertools
import json
import math
import random
import zipfile
from collections.abc import Sequence
from typing import Any

import pytest

from lodestar.lodestar_probe import deck_shapes
from reports.test_onepager_links_resume import _erasures
from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_links as links_mod
from schedule_forensics.reports import pptx
from schedule_forensics.reports.onepager import (
    BAR_F,
    CROWDED_NOTE,
    FOOT_H,
    FOOT_LINES_MAX,
    GUTTER_W,
    LABEL_MAX,
    LANE_COL_X0,
    LANES_Y1,
    LEGEND_Y0,
    MS_F,
    X1,
    Fit,
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
from schedule_forensics.reports.pptx import render_onepager_pptx
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
SHRINK, GUTTER, REORDER, FORCE = 36, 111, 164, 197
DENSE = ((30, 110), (8, 40))


def _base_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pristine posture: no escalation, so a collision is refused and named."""
    monkeypatch.setattr(op, "fit_links", lambda attempt, *_a: attempt(Fit()))


def _refused(lay: Layout | CompareLayout) -> list[str]:
    return [n for n in lay.link_notes if "would cover" in n]


def _flagged(lay: Layout | CompareLayout) -> list[Any]:
    return [ln for ln in lay.links if ln.flagged]


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

    def capped(pack: Any, avail: float, glyph: float) -> tuple[float, float, float, bool]:
        row_h, glyph_h, label_pt, fits = real(pack, avail, glyph)
        return min(row_h, 13.0), min(glyph_h, 13.0), min(label_pt, 8.0), fits

    monkeypatch.setattr(op, "fit_rows", capped)
    lay = build_layout(_items(3), TODAY, "T")
    assert lay.lanes_y1 < LANES_Y1 - 100  # the same measure the test above takes


def test_a_dense_list_still_steps_the_floors_down_and_fills_the_slide() -> None:
    """The floors are untouched: 144 items land at the 5-pt label floor and the slide is still
    exactly one slide — filled to the bottom of the lane area."""
    lay = build_layout(_items(144), TODAY, "T")
    assert lay.label_pt == pytest.approx(5.0) and lay.lanes_y1 == pytest.approx(LANES_Y1, abs=0.01)


# ── a clean base takes no step ────────────────────────────────────────────────────────────────


def test_a_slide_the_base_layout_routes_takes_no_step_and_carries_no_footnote() -> None:
    items, links = _slide(3, (3, 12), (1, 4))
    lay = build_layout(items, TODAY, "T", links=links)
    assert len(lay.links) == len(links) and not _flagged(lay) and not _refused(lay)
    assert lay.fit_notes == [] and lay.footnote == "" and lay.gutter is None
    assert lay.lanes_y1 == pytest.approx(LANES_Y1, abs=0.01)  # no footnote band reserved
    assert lay.x1 == X1


# ── the escalation, step by step ──────────────────────────────────────────────────────────────


def test_step_1_more_room_between_the_rows_fits_the_links(monkeypatch: pytest.MonkeyPatch) -> None:
    items, links = _slide(SHRINK, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    assert len(lay.links) == len(links) and not _flagged(lay) and not _refused(lay)
    assert lay.fit_notes and lay.fit_notes[0].startswith(
        "Bars, diamonds and labels are drawn at 80%"
    )
    assert lay.bar_h == pytest.approx(lay.row_h * BAR_F * 0.8)
    assert lay.gutter is None and "reordered" not in " ".join(lay.fit_notes)
    assert "bars and labels at 80%" in lay.footnote
    assert lay.lanes_y1 == pytest.approx(LANES_Y1 - FOOT_H, abs=0.01)  # the footnote's band
    _base_only(monkeypatch)
    base = build_layout(items, TODAY, "T", links=links)
    assert _refused(base) and len(base.links) < len(links)  # the pristine posture refused it


def test_step_2_the_gutter_lane_fits_the_links() -> None:
    items, links = _slide(GUTTER, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    assert len(lay.links) == len(links) and not _flagged(lay) and not _refused(lay)
    assert lay.gutter is not None and lay.x1 == pytest.approx(X1 - GUTTER_W)
    gx0, gx1 = lay.gutter
    through = [ln for ln in lay.links if len(ln.shaft) >= 5 and gx0 <= ln.shaft[2][0] <= gx1]
    assert through, "no link runs out to the gutter lane and back"
    for ln in through:  # out along its channel, down or up the gutter, back in beside its successor
        assert ln.shaft[1][1] == ln.shaft[2][1] and ln.shaft[2][0] == ln.shaft[3][0]
        assert ln.shaft[3][1] == ln.shaft[4][1]
    assert any("gutter lane" in n for n in lay.fit_notes) and "gutter lane" in lay.footnote
    assert all(p.x1 <= lay.x1 + 0.01 for p in lay.items)  # no bar runs into the gutter


def test_step_3_a_reorder_within_the_swimlane_fits_the_links_and_is_disclosed() -> None:
    items, links = _slide(REORDER, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    plain = build_layout(items, TODAY, "T")
    assert len(lay.links) == len(links) and not _flagged(lay) and not _refused(lay)
    note = next((n for n in lay.fit_notes if "reordered within their swimlane" in n), None)
    assert note is not None and "The Excel list keeps the sheet's own order." in note
    assert "reordered within their swimlane" in lay.footnote
    lane_of = {p.key: p.lane for p in plain.items}
    row_of = {p.key: p.row for p in plain.items}
    moved = [p for p in lay.items if p.row != row_of[p.key]]
    assert moved, "the disclosure names a reorder that did not happen"
    for p in lay.items:
        assert p.lane == lane_of[p.key], "an item crossed a swimlane"
    for p in moved:
        assert p.name in note


def test_the_reordered_slide_keeps_every_row_free_of_overlaps() -> None:
    items, links = _slide(REORDER, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    rows: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for p in lay.items:
        left = p.x0 - lay.ms / 2 if p.milestone else p.x0
        right = p.x1 + lay.ms / 2 if p.milestone else p.x1
        if p.inside:
            ext = (left, right)
        elif p.label_anchor == "start":
            ext = (left, p.label_x + p.label_w)
        else:
            ext = (p.label_x - p.label_w, right)
        rows.setdefault((p.lane, p.row), []).append(ext)
    for (lane, row), exts in rows.items():
        exts.sort()
        for (_a0, a1), (b0, _b1) in itertools.pairwise(exts):
            assert a1 <= b0 + 0.01, f"lane {lane} row {row}: extents overlap after the reorder"


def test_mutation_a_swap_the_packer_cannot_honour_is_refused() -> None:
    ext = {0: [(0, 100.0, 200.0), (1, 150.0, 260.0), (1, 400.0, 500.0)]}
    assert op._swap_ok(ext, (0, 0, 1))  # 100-200 fits beside 400-500; 150-260 alone in row 0
    assert not op._swap_ok(ext, (0, 0, 2))  # 100-200 would sit on 150-260 in row 1
    assert not op._swap_ok(ext, (0, 1, 2))  # already in the same row: nothing to swap
    assert op.apply_swaps([0, 1, 1], 0, [(0, 0, 2)]) == [1, 1, 0]
    assert op.apply_swaps([0, 1, 1], 1, [(0, 0, 2)]) == [0, 1, 1]  # another lane's swap


def test_the_last_resort_draws_the_link_dashed_and_names_the_overlap_on_page_and_slide() -> None:
    items, links = _slide(FORCE, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    flagged = _flagged(lay)
    assert len(lay.links) == len(links), "every requested link is drawn — none refused"
    assert flagged and not _refused(lay)
    for ln in flagged:
        assert ln.overlap
        what = f"logic link “{ln.pred_name}” → “{ln.succ_name}” ({ln.kind})"
        assert any(n.startswith(what) and " is drawn DASHED over " in n for n in lay.link_notes)
        # the footnote names it compactly (the items' names; the review's F4), or counts it
        assert (
            all(name in lay.footnote for name in _entry_names(ln))
            or " more, named on" in lay.footnote
        )
    assert lay.footnote.startswith(
        f"Caution — {len(flagged)} logic link(s) drawn dashed over other ink"
    )
    # it fits the slide at the footnote's measured advance (0.66 em — LibreOffice ran the 0.52-em
    # budget off the slide's edge), so the .pptx never cuts it at the right edge
    for line in lay.footnote.split("\n"):
        assert len(line) * op.FOOT_PT * op.FOOT_CHAR_W <= X1 - lay.footnote_x + 0.01
    assert lay.lanes_y1 == pytest.approx(
        LANES_Y1 - op.foot_height(lay.footnote.count("\n") + 1), abs=0.01
    )
    assert lay.today_label_y < lay.footnote_y - lay.footnote_pt  # the two lines do not collide
    data = json.loads(json.dumps(layout_json(lay)))
    assert sum(ln["flagged"] for ln in data["links"]) == len(flagged)
    assert data["footnote"] == lay.footnote and data["footnote_y"] == LEGEND_Y0 - 2.5


def test_the_pptx_paints_a_flagged_link_dashed_and_carries_the_footnote() -> None:
    items, links = _slide(FORCE, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    with zipfile.ZipFile(
        io.BytesIO(pptx.render_onepager_pptx(lay, marking="CUI", source="s"))
    ) as zf:
        xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
    assert xml.count('<a:prstDash val="dash"/>') == len(_flagged(lay))
    assert xml.count('name="Footnote"') == 1
    for line in lay.footnote.split("\n"):  # one paragraph per line
        assert pptx._esc(line) in xml
    assert xml.count("Logic link line (dashed, over other ink): ") == len(_flagged(lay))
    clean = build_layout(_items(6), TODAY, "T")
    with zipfile.ZipFile(
        io.BytesIO(pptx.render_onepager_pptx(clean, marking="CUI", source="s"))
    ) as zf:
        assert 'name="Footnote"' not in zf.read("ppt/slides/slide1.xml").decode("utf-8")


def test_mutation_without_the_escalation_the_links_of_every_step_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teeth for the four step tests: the pristine posture (no escalation) refuses a link on each
    fixture — the SAME checks go red by name."""
    _base_only(monkeypatch)
    for seed in (SHRINK, GUTTER, REORDER, FORCE):
        items, links = _slide(seed, *DENSE)
        lay = build_layout(items, TODAY, "T", links=links)
        assert _refused(lay) and not _flagged(lay) and len(lay.links) < len(links), seed
        assert lay.fit_notes == [] and lay.footnote == ""


def test_mutation_a_footnote_left_off_the_slide_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(op, "footnote_text", lambda *_a, **_k: "")
    items, links = _slide(FORCE, *DENSE)
    lay = build_layout(items, TODAY, "T", links=links)
    assert _flagged(lay) and lay.footnote == ""  # the checker above would name this


# ── the property: every erasure is by a flagged link, and it names its victim ─────────────────


@pytest.fixture(scope="module")
def dense_slides() -> list[tuple[str, Layout]]:
    return [
        (
            f"seed {seed}",
            build_layout(*_slide(seed, *DENSE)[:1], TODAY, "T", links=_slide(seed, *DENSE)[1]),
        )
        for seed in range(0, 40)
    ]


def test_property_every_erasure_is_by_a_flagged_link_that_names_its_victim(
    dense_slides: list[tuple[str, Layout]],
) -> None:
    """The reviewers' oracle over an independent generator: a head or tag covered by a later
    link is allowed only when THAT link is flagged and its ``overlap`` names the victim; nothing
    is ever covered silently. The population must carry flagged links, or this is vacuous."""
    assert sum(len(lay.links) for _w, lay in dense_slides) > 600
    assert any(_flagged(lay) for _w, lay in dense_slides)
    bad = []
    for what, lay in dense_slides:
        flagged = {
            f"{ln.pred_name} → {ln.succ_name} ({ln.kind})": ln.overlap for ln in _flagged(lay)
        }
        for e in _erasures(lay):
            victim = e.split(": ")[0].removeprefix("the head of ").removeprefix("the tag of ")
            named = any(victim.split(" (")[0].split(" → ")[0] in ov for ov in flagged.values())
            if not named:
                bad.append(f"{what}: {e}")
        if _refused(lay):
            bad.append(f"{what}: a link was refused")
    assert bad == [], bad[:5]


def test_mutation_without_the_ink_check_the_property_goes_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(links_mod, "_conflicts", lambda *_a, **_k: ([], [], False))
    erased = [
        e
        for seed in range(0, 20)
        for e in _erasures(
            build_layout(_slide(seed, *DENSE)[0], TODAY, "T", links=_slide(seed, *DENSE)[1])
        )
    ]
    assert erased  # and none of these links is flagged, so the property above would name them


# ── a tag beside a shared channel (the 3-item slide that called itself crowded) ──────────────


def test_a_tag_beside_a_shared_channel_stands_clear_of_both_lines() -> None:
    """Three milestones in one swimlane, an SS, an SF and a second SS between them: at the
    page-filling sizes the type tag (9.8 pt) is taller than the track spacing (1 pt), so a tag
    centred on its channel line lay on its neighbour's and the 3-item slide said "At this
    density …". The tag now takes a spot ABOVE or BELOW the line, beside the leg into the head."""
    from reports.test_onepager_links_resume import _seg_dist, _tag_ink
    from reports.test_onepager_links_resume import _slide as review_slide

    items, links = review_slide(
        662, (3, 6), 3
    )  # 1034 stopped biting under GLYPH_MAX; 662: two spots crowd, four clear
    lay = build_layout(items, TODAY, "T", links=links)
    assert len(lay.links) == 3 and lay.link_notes == [] and CROWDED_NOTE not in lay.link_notes
    for ln in lay.links:
        if not ln.tag:
            continue
        x0, x1, y0, y1 = _tag_ink(ln)
        pts = [(x0 + (x1 - x0) * i / 6, y0 + (y1 - y0) * j / 6) for i in range(7) for j in range(7)]
        for other in lay.links:
            if other is ln:
                continue
            for a, b in zip(other.shaft, other.shaft[1:], strict=False):
                assert all(_seg_dist(x, y, a, b) > 0.5 for x, y in pts), (ln.kind, other.kind)


def test_mutation_with_two_tag_spots_the_three_item_slide_calls_itself_crowded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from reports.test_onepager_links_resume import _slide as review_slide

    real = links_mod._tag_spots
    monkeypatch.setattr(links_mod, "_tag_spots", lambda *a, **k: real(*a, **k)[:2])
    items, links = review_slide(
        662, (3, 6), 3
    )  # 1034 stopped biting under GLYPH_MAX; 662: two spots crowd, four clear
    lay = build_layout(items, TODAY, "T", links=links)
    assert CROWDED_NOTE in lay.link_notes


# ── the Compare slide, the Excel export, the session cache, determinism ───────────────────────


def test_the_compare_slide_escalates_and_flags_the_same_way() -> None:
    from reports.test_onepager_links import _compare_sweep_doc, _sweep_links

    doc = _compare_sweep_doc(12, 12)
    keys = [r.key for r in doc.rows if r.key]
    links = _sweep_links(keys)
    lay = build_compare_layout(doc, TODAY, "T", links=links)
    assert len(lay.links) == len(links) and not _refused(lay)
    assert _flagged(lay) and lay.footnote.startswith("Caution")
    assert any("reordered within their swimlane" in n for n in lay.fit_notes)
    lines = lay.footnote.count("\n") + 1  # ten flagged links: the footnote takes its four lines
    assert lines == op.FOOT_LINES_MAX
    assert lay.lanes_y1 == pytest.approx(LANES_Y1 - op.foot_height(lines), abs=0.01)
    with zipfile.ZipFile(
        io.BytesIO(pptx.render_onepager_compare_pptx(lay, marking="CUI", source="s"))
    ) as zf:
        xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
    # the prior ghosts are dashed shapes too: count the dashed LINK lines by their names
    assert xml.count("Logic link line (dashed, over other ink): ") == len(_flagged(lay))
    assert 'name="Footnote"' in xml


def _rows(items: Sequence[OnePagerItem]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (it.lane, it.name, it.start.isoformat(), it.finish.isoformat(), "") for it in items
    )


def test_the_excel_list_keeps_the_sheets_order_and_says_the_slide_reordered() -> None:
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
    assert lay is not None and any("reordered" in n for n in lay.fit_notes)
    ts = act.onepager_workbook(st, TODAY)
    assert not isinstance(ts, str)
    listed = next(t for t in ts.tables if t.title.startswith("One-Pager items"))
    assert [r[1] for r in listed.rows] == [it.name for it in st.onepager.items]  # sheet order
    notes = next(t for t in ts.tables if t.title == "Notes")
    assert any("reordered within their swimlane" in str(r[0]) for r in notes.rows)


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


def test_the_escalation_is_deterministic_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Counts, never seconds, pace the escalation, so two runs lay the same slide out the same
    way; on a 96-item, 120-link slide — past any real programme review — the routes judged over
    every attempt stay within the work budget plus the attempts the budget cannot cut short (the
    one that crosses it, the last resort and its taller pass), and the attempts are few. CI's
    first run of this pin (2026-09-30) took 83.6 s on the 3.13 runner where this container took
    16 s, so the earlier 40-s wall-clock bound was replaced by these counts — the bound the ADR
    actually claims; a budget switched off runs every reorder trial and fails the count."""
    reports: list[Any] = []
    real = op.route_all

    def spy(*a: Any, **k: Any) -> Any:
        rep = real(*a, **k)
        reports.append(rep)
        return rep

    monkeypatch.setattr(op, "route_all", spy)
    items, links = _slide(FORCE, *DENSE)
    a, b = (
        build_layout(items, TODAY, "T", links=links),
        build_layout(items, TODAY, "T", links=links),
    )
    assert layout_json(a) == layout_json(b)
    big = _items(96)
    rnd = random.Random(96)
    keys = [it.key for it in big]
    many = []
    while len(many) < 120:
        p, s = rnd.sample(keys, 2)
        ln = Link(p, s, rnd.choice(LINK_TYPES))
        if ln not in many and not any(m.pred == s and m.succ == p for m in many):
            many.append(ln)
    reports.clear()
    lay = build_layout(big, TODAY, "T", links=many)
    judged = [r.judged for r in reports]
    assert 3 <= len(judged) <= 1 + len(op.GLYPH_STEPS) + 1 + 3, judged  # base, steps, force, taller
    assert sum(judged) <= op.WORK_BUDGET + 3 * max(judged), (sum(judged), judged)
    assert len(lay.links) + sum(1 for n in lay.link_notes if " is not drawn — " in n) == 120


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


def test_review_a_footnote_reserve_never_sinks_a_list_that_fits() -> None:
    """Routing review F2: 116 same-day milestones fill the slide to its last row with no links;
    with colliding links the last resort reserved the footnote band, the list no longer "fit",
    links into the last rows were "not drawn — runs off the bottom" (they were on the slide),
    the size note said the list never fit, and the TODAY caption sat on the footnote. A reserve
    that alone sinks a fitting list is not taken: the links are drawn and named on the page and
    in the Excel Notes, and the slide says why it carries no footnote."""
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
    assert not [n for n in lay.link_notes if "runs off the bottom" in n]
    assert not [n for n in lay.notes if "does not fit one slide" in n]
    assert len(lay.links) == len(links) and lay.lanes_y1 == pytest.approx(LANES_Y1)
    assert max(p.y for p in lay.items) < lay.legend_y0
    if lay.footnote:
        assert lay.today_label_y < lay.footnote_y - lay.footnote_pt
    if _flagged(lay):
        assert any("no room" in n and "footnote" in n for n in lay.notes), lay.notes


def test_review_a_shortened_lane_area_is_always_explained() -> None:
    """Routing review F3: on one slide the base layout had collisions, no step helped, and the
    forced attempt — at the shrunken geometry the footnote band leaves — drew every link clean:
    10 pt of lane area gone, footnote empty, nothing disclosed. A lane area shorter than the
    slide's is always explained, in the footnote and in the fitting notes."""
    silent = []
    for seed in range(100, 116):
        items, links = _review_slide(seed)
        lay = build_layout(items, _REVIEW_TODAY, "T", links=links)
        if lay.lanes_y1 < LANES_Y1 - 0.01 and not lay.footnote:
            silent.append(seed)
    assert not silent, silent
    # the review's case was seed 105 (forced, then clean — the reserve must say so); under
    # ADR-0541's router (heads checked against every leg) that seed carries a flagged link, and
    # no review seed in 100-699 shows the shape any more — so the MECHANISM is pinned directly:
    # a reserved band with nothing else to say is explained, in the fitting notes and on the slide
    fitted: list[str] = []
    notes: list[str] = []
    op.disclose_fit(Fit(foot=True, force=True), [], fitted, notes)
    assert fitted == [op.RESERVE_NOTE] and notes == []
    lines = op.footnote_lines([], Fit(foot=True), [], {}, X1 - LANE_COL_X0, FOOT_LINES_MAX)
    assert lines and " ".join(lines) == op.RESERVE_NOTE


def _entry_names(ln: Any) -> list[str]:
    """The item NAMES a flagged link's disclosure must carry: its two ends and every end of
    every link it covers (the router quotes them “…”)."""
    import re

    def bare(label: str) -> str:  # ``Swimlane · Item (dates)`` -> ``Item``
        return re.sub(r" \([\d/]+(?: to [\d/]+)?\)$", "", label.split(" · ", 1)[-1])

    return [bare(ln.pred_name), bare(ln.succ_name)] + [
        bare(q) for q in re.findall(r"“([^”]+)”", ln.overlap)
    ]


@pytest.mark.parametrize("page_name", ["onepager", "compare"])
def test_review_the_footnote_names_every_flagged_link_or_counts_the_rest(page_name: str) -> None:
    """Routing review F4 / rendering review F1: the footnote was ONE line of 256 characters, and a
    single entry ran 150-220 — so 262 of 288 flagged slides on the review's fuzz, and 12 of 13
    on the module's own generator, were cut, most before the first link was named in full. The
    .pptx carries no other disclosure. The footnote now names each flagged link compactly (the
    items' names; the swimlane only when a name repeats), wraps over up to four lines whose
    room the slide reserves, and when even four lines cannot hold every entry it drops whole
    entries and COUNTS them — never a cut mid-name."""
    if page_name == "onepager":
        its = [OnePagerItem("Eng", "Hub", D(2026, 3, 10), D(2026, 3, 11), 2)]
        for k in range(10):
            its.append(
                OnePagerItem(
                    "Eng",
                    f"alpha {k}",
                    D(2026, 1, 5) + dt.timedelta(days=9 * k),
                    D(2026, 1, 6) + dt.timedelta(days=9 * k),
                    3 + k,
                )
            )
        its = keyed(its)
        lay: Layout | CompareLayout = build_layout(
            its,
            _REVIEW_TODAY,
            "T",
            links=[Link(its[k].key, its[0].key, "FS") for k in range(1, 11)],
        )
    else:
        from reports.test_onepager_links import _compare_sweep_doc, _sweep_links

        doc = _compare_sweep_doc(12, 12)
        lay = build_compare_layout(
            doc, TODAY, "T", links=_sweep_links([r.key for r in doc.rows if r.key])
        )
    flagged = _flagged(lay)
    assert len(flagged) >= 6, len(flagged)
    lines = lay.footnote.split("\n")
    assert 1 <= len(lines) <= 4 and lay.footnote.startswith("Caution")
    named = [ln for ln in flagged if all(name in lay.footnote for name in _entry_names(ln))]
    rest = len(flagged) - len(named)
    if rest:
        assert f"and {rest} more" in lay.footnote, (rest, lay.footnote)
    else:
        assert "more" not in lines[-1].rsplit(" ", 3)[-1]
    assert "…" not in lay.footnote  # never cut mid-name
    reserve = LANES_Y1 - lay.lanes_y1
    assert reserve == pytest.approx(FOOT_H + (len(lines) - 1) * op.FOOT_LINE_H, abs=0.01), (
        reserve,
        len(lines),
    )


def test_review_a_gutter_route_records_the_predecessors_side_by_its_own_shaft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routing review F5: a gutter route leaves the predecessor on the side of ITS channel but
    was recorded on the side of the successor's (``route.y``) — 10 of 18 gutter links on the
    review's seeds — so a later link could take the same attachment point on that side. The
    router's report now carries the attachment ledger, and every recorded side is the side the
    shaft leaves on."""
    reports: list[Any] = []
    real = op.route_all

    def spy(*a: Any, **k: Any) -> Any:
        rep = real(*a, **k)
        reports.append(rep)
        return rep

    monkeypatch.setattr(op, "route_all", spy)
    gutter_links = opposite = 0
    # gutter routes are rare on the Timeline: three seeds of the two generators carry one each,
    # each leaving the predecessor on the side OPPOSITE the successor's channel — the case the
    # old ledger recorded wrong (a ledger keyed by ``route.y`` fails this test). Re-pinned under
    # ADR-0541 (heads checked against every leg): review seeds 12 and 13 no longer reach the
    # gutter; 103 and 110 do (a search over review seeds 100-259 and this module's 0-219)
    for gen, seed in ((_slide, 111), (_review_slide, 103), (_review_slide, 110)):
        items, links = _slide(seed, *DENSE) if gen is _slide else _review_slide(seed)
        reports.clear()
        lay = build_layout(items, TODAY if gen is _slide else _REVIEW_TODAY, "T", links=links)
        assert lay.gutter is not None, seed
        points = getattr(reports[-1], "points", None)
        assert points is not None, "route_all's report carries no attachment ledger"
        by_key = {p.key: p for p in lay.items}
        for ln in lay.links:
            if len(ln.shaft) >= 5 and lay.gutter[0] <= ln.shaft[2][0] <= lay.gutter[1]:
                gutter_links += 1
                p = by_key[ln.pred]
                leaves_below = ln.shaft[1][1] > p.y
                opposite += leaves_below != (ln.shaft[3][1] > p.y)
                assert ln.shaft[0][0] in points.get((ln.pred, leaves_below), ()), (
                    seed,
                    ln.pred,
                    leaves_below,
                )
    assert gutter_links >= 3 and opposite >= 2, (gutter_links, opposite)


def test_review_the_pptx_footnote_is_the_caution_colour_not_the_duplicate_name_hue() -> None:
    """Rendering review F6: the .pptx footnote was painted ``_DUP`` — the DUPLICATE-NAME badge's
    goldenrod — while the docs promise the caution colour the page uses (``--warn``)."""
    its = [OnePagerItem("Eng", "Hub", D(2026, 3, 10), D(2026, 3, 11), 2)]
    for k in range(10):
        its.append(
            OnePagerItem(
                "Eng",
                f"alpha {k}",
                D(2026, 1, 5) + dt.timedelta(days=9 * k),
                D(2026, 1, 6) + dt.timedelta(days=9 * k),
                3 + k,
            )
        )
    its = keyed(its)
    lay = build_layout(
        its, _REVIEW_TODAY, "T", links=[Link(its[k].key, its[0].key, "FS") for k in range(1, 11)]
    )
    assert _flagged(lay)
    warn = getattr(pptx, "_WARN", None)
    assert warn is not None and warn != pptx._DUP
    with zipfile.ZipFile(
        io.BytesIO(pptx.render_onepager_pptx(lay, marking="CUI", source="s"))
    ) as zf:
        xml = zf.read("ppt/slides/slide1.xml").decode("utf-8")
    foot = xml.split('name="Footnote"')[1].split("</p:sp>")[0]
    assert f'<a:srgbClr val="{warn}"/>' in foot and pptx._DUP not in foot
    assert foot.count("<a:p>") == lay.footnote.count("\n") + 1  # one paragraph per line


# ── a head on an earlier link's leg (ADR-0541; ADR-0540's review recorded the gutter case) ────


def _pt_seg(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _seg_seg(a: Any, b: Any, c: Any, d: Any) -> float:
    def ccw(p: Any, q: Any, r: Any) -> bool:
        return (r[1] - p[1]) * (q[0] - p[0]) > (q[1] - p[1]) * (r[0] - p[0])

    if ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d):
        return 0.0
    return min(_pt_seg(*a, c, d), _pt_seg(*b, c, d), _pt_seg(*c, a, b), _pt_seg(*d, a, b))


def _inside(p: Any, tri: list[Any]) -> bool:
    signs = 0
    for i in range(3):
        (x1, y1), (x2, y2) = tri[i], tri[(i + 1) % 3]
        cross = (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1)
        signs |= 1 if cross > 0 else 2 if cross < 0 else 0
    return signs in (1, 2)


def _seg_tri(seg: Any, tri: list[Any]) -> float:
    """The distance from a leg to a head's triangle — 0 when the leg enters it. An independent
    oracle: written without the router's boxes or its ``_within``."""
    a, b = seg
    if _inside(a, tri) or _inside(b, tri):
        return 0.0
    return min(_seg_seg(a, b, tri[i], tri[(i + 1) % 3]) for i in range(3))


def _heads_on_legs(lay: Layout | CompareLayout) -> list[str]:
    """Every CLEAN-judged link whose head lies within a touch of an EARLIER link's horizontal
    leg (a flagged link names its overlap; a clean one claims to cover nothing)."""
    touch = links_mod._TOUCH
    out = []
    for i, ln in enumerate(lay.links):
        if ln.flagged:
            continue
        tri = [tuple(p) for p in ln.head]
        for e in lay.links[:i]:
            for seg in zip(e.shaft, e.shaft[1:], strict=False):
                if abs(seg[0][1] - seg[1][1]) > 1e-9:
                    continue  # a vertical leg: the router checked those all along
                if _seg_tri(seg, tri) < touch:
                    out.append(f"{ln.pred_name} → {ln.succ_name} on {e.pred_name} → {e.succ_name}")
    return out


def test_review_a_clean_links_head_never_sits_on_an_earlier_links_leg(
    dense_slides: list[tuple[str, Layout]],
) -> None:
    """ADR-0540 recorded "`_conflicts` checks new heads against vertical legs only (2 slides of
    600 with a later head's base on an earlier gutter leg)". The premise fell when measured: no
    gutter case in 1,800 slides of three generators, but a clean-judged head on an earlier PLAIN
    horizontal leg on 66 of 100 review-generator slides and 22 of 100 of this module's — the
    leg runs through the head's base, which reads as that link ending there. Every leg is
    checked now; this property is red on the pristine tree (seeds 2, 12, 18, … of the fixture)."""
    bad = [(what, hit) for what, lay in dense_slides for hit in _heads_on_legs(lay)]
    assert bad == [], bad[:6]


def test_review_the_review_generators_slide_that_carried_one_is_clean_now() -> None:
    """Seed 1 of the review's generator: one clean-judged head on an earlier channel leg on the
    pristine tree (its leg entered the head's triangle: distance 0)."""
    items, links = _review_slide(1)
    lay = build_layout(items, _REVIEW_TODAY, "T", links=links)
    assert _heads_on_legs(lay) == []
    assert len(lay.links) == len(links)  # nothing lost: re-routed or drawn dashed and named


def test_mutation_checking_the_vertical_legs_only_puts_a_head_back_on_a_leg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The oracle has teeth: ADR-0540's rule (vertical legs only) fails it by name on seed 1."""
    monkeypatch.setattr(links_mod, "_head_legs", lambda e: [vb for _x, _lo, _hi, vb in e.verticals])
    items, links = _review_slide(1)
    lay = build_layout(items, _REVIEW_TODAY, "T", links=links)
    assert _heads_on_legs(lay) != []


# ── the legend's spare row carries the footnote of a list that fills the slide (ADR-0541) ────


def _full_slide_with_collisions() -> tuple[list[OnePagerItem], list[Link]]:
    """Review F2's list: 116 same-day milestones fill the slide to its last row, and links into
    one of them collide — the reserve alone would sink a list that fits."""
    rows = 116
    its = keyed(
        [OnePagerItem("Eng", f"M{k}", D(2026, 3, 15), D(2026, 3, 15), k + 2) for k in range(rows)]
    )
    keys = [i.key for i in its]
    links = [Link(keys[k], keys[9], "FS") for k in range(1, 9)] + [
        Link(keys[0], keys[rows - 1 - j], "FS") for j in range(3)
    ]
    return its, links


def test_review_the_legends_spare_row_carries_the_footnote_of_a_list_that_fills_the_slide() -> None:
    """ADR-0540 recorded the corner and left the .pptx without a footnote; ADR-0541 decides:
    when the legend uses one of its two rows, the spare row carries ONE line — the count of
    the links drawn dashed and the entries that fit — on the page AND in the PowerPoint, and the
    note says so. RED on the pristine tree (footnote empty, the note said "not on the slide")."""
    its, links = _full_slide_with_collisions()
    lay = build_layout(its, _REVIEW_TODAY, "T", links=links)
    assert _flagged(lay) and lay.lanes_y1 == pytest.approx(LANES_Y1)  # the corner: full, forced
    assert len({e.y for e in lay.legend}) == 1  # one legend row: the second is spare
    assert lay.footnote.startswith(f"Caution — {len(_flagged(lay))} logic link(s) drawn dashed")
    assert "\n" not in lay.footnote  # one line
    assert lay.footnote_y == pytest.approx(lay.legend_y0 + 6 + (lay.legend_pt + 4.5))
    assert lay.today_label_y < lay.footnote_y - lay.footnote_pt
    assert any("spare row carries a one-line count" in n for n in lay.notes), lay.notes
    assert not any("not on the slide" in n for n in lay.notes)
    deck = render_onepager_pptx(lay, marking="CUI", source="s", product="t")
    assert deck_shapes(deck)["Footnote"] == lay.footnote


def test_mutation_a_legend_that_needs_both_rows_leaves_the_slide_without_a_footnote_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A legend wrapped to two rows has no spare row: the footnote stays off the slide and the
    note says where the links are named instead — the row condition, not the feature, is what
    this checks (wide legend text forces the wrap)."""
    real = op.text_w
    monkeypatch.setattr(op, "text_w", lambda text, size: real(text, size) * 6)
    its, links = _full_slide_with_collisions()
    lay = build_layout(its, _REVIEW_TODAY, "T", links=links)
    assert _flagged(lay) and len({e.y for e in lay.legend}) == 2
    assert lay.footnote == ""
    assert any("not on the slide or in the PowerPoint" in n for n in lay.notes), lay.notes
