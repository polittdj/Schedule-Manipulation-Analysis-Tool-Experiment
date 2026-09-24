"""The One-Pager date window (operator request 2026-09-23, ADR-0527) in the layout engine.

Rulings (asked and given 2026-09-23): an item that TOUCHES the window stays and is CUT at the
edge it runs past — only an item wholly outside is omitted, and named; on the compare slide a row
stays when its PRIOR or its CURRENT position touches the window, so an item that slipped out of
the window is still on it. The timescale is exactly the window — never widened to whole months
or to today. Without a window every layout is the ADR-0446 / ADR-0526 layout, unchanged.

Red-first (2026-09-24): on the pristine tree ``window_items`` / ``window_compare`` did not exist
and ``build_layout`` / ``build_compare_layout`` took no window — every test here errored.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_compare as oc

D = dt.date
TODAY = D(2027, 3, 1)
WIN = (D(2027, 1, 1), D(2027, 6, 30))


def _item(name: str, start: D, finish: D, lane: str = "A", row: int = 2) -> op.OnePagerItem:
    return op.OnePagerItem(lane, name, start, finish, row)


ITEMS = [
    _item("Before", D(2026, 6, 1), D(2026, 12, 31), row=2),  # ends the day before: omitted
    _item("Straddle left", D(2026, 11, 1), D(2027, 3, 15), row=3),  # cut at the left edge
    _item("Inside", D(2027, 2, 1), D(2027, 4, 1), row=4),
    _item("Milestone in", D(2027, 5, 5), D(2027, 5, 5), "B", 5),
    _item("Straddle right", D(2027, 6, 1), D(2027, 9, 1), "B", 6),  # cut at the right edge
    _item("Ends on day one", D(2026, 10, 1), D(2027, 1, 1), "B", 7),  # touches: kept
    _item("Starts on last day", D(2027, 6, 30), D(2027, 8, 1), "C", 8),  # touches: kept
    _item("After", D(2027, 7, 1), D(2027, 7, 1), "C", 9),  # a milestone the day after: omitted
]


def test_window_items_keeps_every_item_that_touches_the_window_and_omits_the_rest() -> None:
    kept, omitted = op.window_items(ITEMS, WIN)
    assert [i.name for i in omitted] == ["Before", "After"]
    assert [i.name for i in kept] == [i.name for i in ITEMS if i.name not in ("Before", "After")]


def test_the_timescale_is_exactly_the_window_never_whole_months_or_today() -> None:
    kept, _ = op.window_items(ITEMS, (D(2027, 1, 15), D(2027, 3, 10)))
    lay = op.build_layout(kept, D(2027, 9, 1), "T", window=(D(2027, 1, 15), D(2027, 3, 10)))
    assert (lay.t0, lay.t1) == ("2027-01-15", "2027-03-11")  # the last day is included
    assert lay.today_x is None and "chosen date window" in lay.today_note
    # the first tick is the window's edge; the partial first month is labelled only if it fits
    assert lay.months[0].x == pytest.approx(op.X0)
    assert [m.label for m in lay.months] == ["Jan", "Feb", "Mar"]
    assert all(op.X0 <= m.x <= op.X1 for m in lay.months)


def test_today_inside_the_window_is_drawn_and_outside_it_is_not() -> None:
    kept, _ = op.window_items(ITEMS, WIN)
    assert op.build_layout(kept, TODAY, "T", window=WIN).today_x is not None
    assert op.build_layout(kept, D(2027, 7, 1), "T", window=WIN).today_x is None


def test_a_straddling_bar_is_cut_at_the_edge_and_keeps_its_true_finish_in_its_label() -> None:
    kept, _ = op.window_items(ITEMS, WIN)
    lay = op.build_layout(kept, TODAY, "T", window=WIN)
    by = {p.name: p for p in lay.items}
    assert by["Straddle left"].x0 == pytest.approx(op.X0)
    assert by["Straddle right"].x1 == pytest.approx(op.X1)
    assert by["Straddle right"].label == "Straddle right (9/1/27)"
    for p in lay.items:
        assert op.X0 <= p.x0 <= p.x1 <= op.X1, p.name
    # a bar touching only the first day still draws its 3-pt floor INSIDE the chart
    assert by["Ends on day one"].x0 == pytest.approx(op.X0)
    assert by["Ends on day one"].x1 == pytest.approx(op.X0 + 3)
    assert by["Starts on last day"].x1 == pytest.approx(op.X1)
    cut_note = next(n for n in lay.notes if "cut at it" in n)
    for name in ("Straddle left", "Straddle right", "Ends on day one", "Starts on last day"):
        assert name in cut_note
    assert "Inside" not in cut_note


def test_build_layout_refuses_an_item_wholly_outside_its_window() -> None:
    with pytest.raises(ValueError, match="wholly outside"):
        op.build_layout(ITEMS, TODAY, "T", window=WIN)


def test_windowed_doc_names_every_omitted_item_and_the_excel_says_so() -> None:
    doc = op.OnePagerDoc("list.xlsx", "Sheet1", tuple(ITEMS), (), ())
    view, omitted = op.windowed_doc(doc, WIN)
    assert len(view.items) == 6 and len(omitted) == 2
    assert omitted[0] == "A · Before (6/1/26 to 12/31/26, row 2)"
    assert omitted[1] == "C · After (7/1/27, row 9)"
    same, none = op.windowed_doc(doc, None)
    assert same is doc and none == []
    ts = op.onepager_tableset(view, WIN, omitted)
    items_table, _, notes = ts.tables
    assert len(items_table.rows) == 6
    flat = [r[0] for r in notes.rows]
    assert flat[0].startswith("date window 2027-01-01 to 2027-06-30: 2 item(s)")
    assert "left off (outside the window): A · Before (6/1/26 to 12/31/26, row 2)" in flat
    assert op.subtitle_for(view, 3, TODAY, WIN).startswith(
        "Prepared 2027-03-01 · window 1/1/27 – 6/30/27 · 6 items"
    )


#: The no-window layout of a fixed list, digested on the pristine tree (8c71c639) — the window
#: work must leave every existing slide byte-identical.
_PRISTINE_DIGEST = "b60a37dd0acf66403751b5a78a5d5233e3a66b6e6f6cd61b679859def84cfbac"


def _digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def test_without_a_window_the_slides_are_the_pristine_slides() -> None:
    lay = op.build_layout(ITEMS, TODAY, "T", "S")
    prior = op.OnePagerDoc("p.xlsx", "S", tuple(ITEMS), (), ())
    moved = tuple(
        op.OnePagerItem(i.lane, i.name, i.start, i.finish + dt.timedelta(days=30), i.row)
        for i in ITEMS
    )
    cd = oc.compare_onepager_docs(prior, op.OnePagerDoc("c.xlsx", "S", moved, (), ()))
    cl = oc.build_compare_layout(cd, TODAY, "T", "S")
    got = _digest([op.layout_json(lay), oc.compare_layout_json(cl)])
    assert got == _PRISTINE_DIGEST


# ── the compare slide ─────────────────────────────────────────────────────────────────────────


def _cmp(prior: list[op.OnePagerItem], current: list[op.OnePagerItem]) -> oc.CompareDoc:
    return oc.compare_onepager_docs(
        op.OnePagerDoc("p.xlsx", "S", tuple(prior), (), ()),
        op.OnePagerDoc("c.xlsx", "S", tuple(current), (), ()),
    )


PRIOR = [
    _item("Slipped out", D(2027, 4, 1), D(2027, 5, 1)),  # current 8/1: out of the window
    _item("Slipped in", D(2026, 9, 1), D(2026, 11, 1)),  # prior outside, current inside
    _item("MS out", D(2027, 6, 1), D(2027, 6, 1)),  # a milestone that slipped out
    _item("Far past", D(2026, 1, 1), D(2026, 2, 1)),  # both sides outside: omitted
    _item("Unchanged", D(2027, 2, 1), D(2027, 3, 1)),
    _item("Gone", D(2027, 2, 10), D(2027, 2, 20)),  # removed, inside
    _item("Gone early", D(2026, 2, 10), D(2026, 2, 20)),  # removed, outside: omitted
]
CURRENT = [
    _item("Slipped out", D(2027, 4, 1), D(2027, 8, 1)),
    _item("Slipped in", D(2027, 1, 20), D(2027, 2, 15)),
    _item("MS out", D(2027, 9, 1), D(2027, 9, 1)),
    _item("Far past", D(2026, 1, 1), D(2026, 3, 1)),
    _item("Unchanged", D(2027, 2, 1), D(2027, 3, 1)),
    _item("New late", D(2027, 12, 1), D(2027, 12, 1)),  # new, outside: omitted
]


def test_a_row_stays_when_its_prior_or_its_current_position_touches_the_window() -> None:
    full = _cmp(PRIOR, CURRENT)
    view, omitted = oc.window_compare(full, WIN)
    names = {r.name for r in view.rows}
    assert names == {"Slipped out", "Slipped in", "MS out", "Unchanged", "Gone"}
    assert len(omitted) == 3
    assert any(o.startswith("A · Far past — slipped (prior") for o in omitted)
    assert any(o.startswith("A · New late — new (current 12/1/27)") for o in omitted)
    # the counts are the window's, recounted — not the full comparison's
    assert (full.totals.slipped, view.totals.slipped) == (4, 3)
    assert (full.totals.removed, view.totals.removed) == (2, 1)
    assert view.totals.new == 0 and full.totals.new == 1
    assert [s.slipped for s in view.lanes] == [3]
    assert oc.window_compare(full, None) == (full, [])


def test_the_compare_slide_cuts_at_the_edge_and_runs_an_arrow_out_of_the_window() -> None:
    view, _ = oc.window_compare(_cmp(PRIOR, CURRENT), WIN)
    lay = oc.build_compare_layout(view, TODAY, "T", window=WIN)
    by = {p.name: p for p in lay.items}
    out = by["Slipped out"]
    assert out.x1 == pytest.approx(oc.X1)  # the current bar is cut at the right edge
    assert out.arrow_x1 == pytest.approx(oc.X1)  # its arrow runs to the edge
    assert out.delta == "+92 cal d"  # ...and its move keeps the true figure
    ms = by["MS out"]
    assert ms.x0 is None and ms.ghost_x0 is not None  # the current diamond is off the slide
    assert ms.arrow_x1 == pytest.approx(oc.X1) and ms.arrow_x0 == pytest.approx(ms.ghost_x0)
    slip_in = by["Slipped in"]
    assert slip_in.ghost_x0 is None and slip_in.x0 is not None  # the prior bar is off the slide
    assert slip_in.arrow_x0 == pytest.approx(oc.X0)
    for p in lay.items:
        for x in (p.x0, p.x1, p.ghost_x0, p.ghost_x1, p.arrow_x0, p.arrow_x1):
            assert x is None or oc.X0 <= x <= oc.X1, p.name
    note = next(n for n in lay.notes if "run past the date window" in n)
    assert "Slipped out (slipped)" in note and "Unchanged" not in note
    assert (lay.t0, lay.t1) == ("2027-01-01", "2027-07-01")


def test_build_compare_layout_refuses_a_row_wholly_outside_its_window() -> None:
    with pytest.raises(ValueError, match="wholly outside"):
        oc.build_compare_layout(_cmp(PRIOR, CURRENT), TODAY, "T", window=WIN)


def test_the_compare_excel_states_the_window_and_names_every_row_it_left_off() -> None:
    view, omitted = oc.window_compare(_cmp(PRIOR, CURRENT), WIN)
    ts = oc.compare_tableset(view, WIN, omitted)
    rows = {t.title: t for t in ts.tables}
    assert len(ts.tables[0].rows) == 5
    notes = [r[0] for r in rows["Notes"].rows]
    assert any(n.startswith("date window 2027-01-01 to 2027-06-30: 3 item(s)") for n in notes)
    assert sum(n.startswith("left off (outside the window): ") for n in notes) == 3
    assert oc.compare_subtitle(view, TODAY, WIN).count("window 1/1/27 – 6/30/27") == 1


def test_a_bar_filling_the_window_carries_its_label_on_the_bar_not_over_the_lane_names() -> None:
    """Rendered 2026-09-24: an UNCHANGED bar spanning the whole window had its label end-anchored
    left of the chart, over the swimlane names ("Overall GTA Window" over "BobbySon"). With a
    window, a row whose ghost and arrow are off the slide — or whose shapes leave no room outside
    — carries its label on its solid bar when it fits."""
    prior = [
        _item("Overall GTA Window", D(2026, 6, 10), D(2028, 6, 22)),
        _item("Long slip", D(2026, 5, 1), D(2027, 12, 1)),
    ]
    current = [
        _item("Overall GTA Window", D(2026, 6, 10), D(2028, 6, 22)),
        _item("Long slip", D(2026, 5, 1), D(2028, 2, 1)),
    ]
    view, _ = oc.window_compare(_cmp(prior, current), WIN)
    lay = oc.build_compare_layout(view, TODAY, "T", window=WIN)
    by = {p.name: p for p in lay.items}
    for name in ("Overall GTA Window", "Long slip"):
        p = by[name]
        assert p.inside and not p.clipped, name
        assert p.label_anchor == "start" and p.label_x == pytest.approx(oc.X0 + 2), name
    # without a window the same unchanged row keeps the ADR-0526 rule (a prior side: outside)
    plain = oc.build_compare_layout(_cmp(prior, current), TODAY, "T")
    assert not {p.name: p for p in plain.items}["Overall GTA Window"].inside


def test_an_edge_month_sliver_is_labelled_only_as_its_visible_part_allows() -> None:
    """Mutation battery 2026-09-24 (M8a / M9 survived a 55-day window): on a multi-year window the
    first and last months are ~9-pt slivers. Each is labelled only as its VISIBLE part allows (a
    letter, never 'Jan') and every label sits inside its own visible slice, inside the chart."""
    win = (D(2026, 1, 20), D(2028, 12, 10))
    lay = op.build_layout([_item("x", D(2027, 1, 1), D(2027, 2, 1))], D(2027, 1, 1), "T", window=win)
    ms = lay.months
    assert len(ms) == 36
    assert (ms[0].label, ms[1].label, ms[-2].label, ms[-1].label) == ("J", "Feb", "Nov", "D")
    edges = [m.x for m in ms] + [op.X1]
    for m, right in zip(ms, edges[1:], strict=True):
        assert m.x <= m.label_x <= right, m
        assert m.label_x == pytest.approx((m.x + right) / 2)
