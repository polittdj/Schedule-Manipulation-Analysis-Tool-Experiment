"""Risks on the One-Pager slides (ADR-0544): the register's rows packed into their swimlanes as
single moments, drawn as triangles in their probability's colour, never a task or a milestone.

The operator (2026-10-01): "reflect the risk like you would a milestone as a single moment in
time with the risk name, date of occurrence and the Potential Impact next to it … the
Probability of Occurrence [colours it] Red (High), Yellow (Medium) or Green (Low) … inserted
into the swimlane based on the date of occurrence … clearly identified by the reader that they
are Risks and not actual tasks or schedule milestones."

Red first: every assertion below was observed to fail on the tree before the layout knew a
``risks`` argument (``TypeError``), and each rule's mutation twin breaks it by name.
"""

from __future__ import annotations

import datetime as dt
from itertools import pairwise

import pytest

from schedule_forensics.reports import onepager as op
from schedule_forensics.reports import onepager_compare as oc
from schedule_forensics.reports.onepager import OnePagerDoc, OnePagerItem, build_layout, layout_json
from schedule_forensics.reports.onepager_compare import build_compare_layout, compare_onepager_docs
from schedule_forensics.reports.onepager_risks import OnePagerRisk, impact_label, keyed_risks

TODAY = dt.date(2027, 3, 1)


def _item(lane: str, name: str, s: dt.date, f: dt.date, row: int) -> OnePagerItem:
    return OnePagerItem(lane, name, s, f, row)


ITEMS = op.keyed(
    [
        _item("Alpha", "Design Review", dt.date(2027, 1, 15), dt.date(2027, 1, 15), 2),
        _item("Alpha", "Build", dt.date(2027, 2, 1), dt.date(2027, 4, 15), 3),
        _item("Beta", "Test", dt.date(2027, 5, 1), dt.date(2027, 6, 30), 4),
        _item("Beta", "Ship", dt.date(2027, 7, 15), dt.date(2027, 7, 15), 5),
    ]
)
RISKS = keyed_risks(
    [
        OnePagerRisk("Alpha", "Vendor part late", dt.date(2027, 3, 10), "30 d", 30, "high", 2),
        OnePagerRisk("Beta", "Range unavailable", dt.date(2027, 6, 1), "2 wk", 14, "medium", 3),
        OnePagerRisk("Beta", "Weather hold", dt.date(2027, 7, 20), "5", 5, "low", 4),
        OnePagerRisk("Gamma", "Funding gap", dt.date(2027, 4, 1), "a quarter", None, "unknown", 5),
    ]
)
IMPACTS = {r.key: impact_label(r) for r in RISKS}


@pytest.fixture(scope="module")
def lay() -> op.Layout:
    return build_layout(ITEMS, TODAY, "T", risks=RISKS, risk_impacts=IMPACTS)


def _risks(lay: op.Layout) -> list[op.Placed]:
    return [p for p in lay.items if p.kind == "risk"]


def test_every_risk_is_placed_as_a_single_moment_in_its_swimlane(lay: op.Layout) -> None:
    placed = _risks(lay)
    assert len(placed) == 4 and all(p.milestone and p.x0 == p.x1 and p.ms > 0 for p in placed)
    lanes = {ln.index: ln.name for ln in lay.lanes}
    assert {lanes[p.lane] for p in placed} == {"Alpha", "Beta", "Gamma"}
    # a risk's x is its date's x on the same timescale as the items
    t0, t1 = dt.date.fromisoformat(lay.t0), dt.date.fromisoformat(lay.t1)
    for p in placed:
        when = dt.date.fromisoformat(p.finish)
        assert p.x0 == pytest.approx(lay.x0 + (when - t0).days / (t1 - t0).days * (lay.x1 - lay.x0))
    # items are untouched in kind
    assert all(
        p.kind == "item" and p.prob == "" and p.impact == "" for p in lay.items if p.kind != "risk"
    )


def test_a_risk_is_labelled_as_a_risk_with_its_date_and_impact(lay: op.Layout) -> None:
    by_name = {p.name: p for p in _risks(lay)}
    assert by_name["Vendor part late"].label == "RISK · Vendor part late (3/10/27)"
    assert by_name["Vendor part late"].impact == "impact +30 cal d"
    assert by_name["Range unavailable"].impact == "impact +14 cal d"
    assert by_name["Funding gap"].impact == "impact: a quarter"
    assert by_name["Funding gap"].prob == "unknown"
    assert {p.prob for p in _risks(lay)} == {"high", "medium", "low", "unknown"}
    # the reserved width covers the label AND the impact (set in the monospace face)
    for p in _risks(lay):
        need = (
            len(p.label) * lay.label_pt * op.CHAR_W
            + len(f" {p.impact}") * lay.label_pt * op.MONO_CHAR_W
        )
        assert p.label_w >= need - 0.01


def test_a_swimlane_named_only_in_the_register_gets_its_own_band_and_is_named(
    lay: op.Layout,
) -> None:
    names = [ln.name for ln in lay.lanes]
    assert names == [
        "Alpha",
        "Beta",
        "Gamma",
    ]  # first-seen order: the list's lanes, then the register's
    assert any("Gamma" in n and "only in the risk register" in n for n in lay.notes), lay.notes


def test_the_legend_names_every_probability_drawn_in_order(lay: op.Layout) -> None:
    kinds = [e.kind for e in lay.legend]
    assert [k for k in kinds if k.startswith("risk-")] == [
        "risk-high",
        "risk-medium",
        "risk-low",
        "risk-unknown",
    ]
    labels = {e.kind: e.label for e in lay.legend}
    assert labels["risk-high"] == "Risk — high probability"
    assert labels["risk-unknown"] == "Risk — probability not read"
    only_high = build_layout(ITEMS, TODAY, "T", risks=RISKS[:1], risk_impacts=IMPACTS)
    assert [e.kind for e in only_high.legend if e.kind.startswith("risk-")] == ["risk-high"]


def test_the_layout_json_carries_the_three_risk_fields(lay: op.Layout) -> None:
    blob = layout_json(lay)
    risk = next(p for p in blob["items"] if p["kind"] == "risk")
    assert {"kind", "prob", "impact"} <= set(risk) and risk["key"]
    assert all(p["kind"] in ("item", "risk") for p in blob["items"])


def test_risks_pack_into_rows_like_milestones_and_never_overlap_an_item(lay: op.Layout) -> None:
    """Two placements on one row never overlap in x (the first-fit rule holds with risks in)."""
    by_row: dict[tuple[int, int], list[op.Placed]] = {}
    for p in lay.items:
        by_row.setdefault((p.lane, p.row), []).append(p)
    for group in by_row.values():
        spans = sorted(
            (
                (p.x0 - (p.ms or lay.ms) / 2, p.x1 + (p.ms or lay.ms) / 2)
                if p.milestone
                else (p.x0, p.x1)
            )
            for p in group
        )
        for (a0, a1), (b0, b1) in pairwise(spans):
            assert a1 <= b0 + 0.01, (a0, a1, b0, b1)


def test_without_risks_the_layout_is_the_layout_it_always_was() -> None:
    plain = build_layout(ITEMS, TODAY, "T")
    assert all(p.kind == "item" for p in plain.items) and not any(
        e.kind.startswith("risk-") for e in plain.legend
    )
    assert len(plain.lanes) == 2 and plain.notes == []


def test_a_risk_is_never_a_link_end_but_is_an_obstacle(lay: op.Layout) -> None:
    from schedule_forensics.reports.onepager_links import Link

    risk = _risks(lay)[0]
    item = next(p for p in lay.items if p.kind == "item")
    linked = build_layout(
        ITEMS, TODAY, "T", links=[Link(risk.key, item.key, "FS")], risks=RISKS, risk_impacts=IMPACTS
    )
    assert linked.links == [] and len(linked.link_notes) == 1
    assert "is no longer in the list" in linked.link_notes[0]


def test_a_risk_outside_the_window_is_refused_by_the_layout() -> None:
    win = (dt.date(2027, 1, 1), dt.date(2027, 3, 31))
    inside = [r for r in RISKS if win[0] <= r.date <= win[1]]
    items = [i for i in ITEMS if op.overlaps(i.start, i.finish, win)]
    lay = build_layout(items, TODAY, "T", window=win, risks=inside, risk_impacts=IMPACTS)
    assert [p.name for p in _risks(lay)] == ["Vendor part late"]
    with pytest.raises(ValueError, match="risk lies outside the window"):
        build_layout(items, TODAY, "T", window=win, risks=RISKS, risk_impacts=IMPACTS)


def test_mutation_a_risk_drawn_as_an_item_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """MUTATION: ``risk_prob`` forgetting the kind — the triangle's colour word gone — is caught
    by the probability check; a layout that marked a risk ``item`` by the kind check."""
    monkeypatch.setattr(op, "risk_prob", lambda prob: "")
    broken = build_layout(ITEMS, TODAY, "T", risks=RISKS, risk_impacts=IMPACTS)
    assert {p.prob for p in broken.items if p.kind == "risk"} == {""}


# ── the Compare slide ─────────────────────────────────────────────────────────────────────────


def _cmp() -> oc.CompareDoc:
    prior = OnePagerDoc("p.xlsx", "S", tuple(ITEMS), (), ())
    moved = tuple(
        OnePagerItem(i.lane, i.name, i.start, i.finish + dt.timedelta(days=30), i.row)
        for i in ITEMS
    )
    return compare_onepager_docs(prior, OnePagerDoc("c.xlsx", "S", moved, (), ()))


@pytest.fixture(scope="module")
def clay() -> oc.CompareLayout:
    return build_compare_layout(_cmp(), TODAY, "C", risks=RISKS, risk_impacts=IMPACTS)


def test_compare_places_every_risk_as_a_current_moment_with_no_ghost(
    clay: oc.CompareLayout,
) -> None:
    risks = [p for p in clay.items if p.kind == "risk"]
    assert len(risks) == 4
    for p in risks:
        assert p.status == oc.RISK and p.milestone and p.x0 == p.x1 and p.ms > 0
        assert p.ghost_x0 is None and p.arrow_x0 is None and p.badge == ""
        assert (
            p.label.startswith("RISK · ") and p.delta == p.impact and p.impact.startswith("impact")
        )
        assert p.key.startswith("risk:")
    assert {p.prob for p in risks} == {"high", "medium", "low", "unknown"}


def test_compare_summaries_never_count_a_risk(clay: oc.CompareLayout) -> None:
    doc = _cmp()
    assert len(clay.summaries) == len(doc.lanes) == 2  # Gamma, the register's lane, has no strip
    assert len(clay.lanes) == 3 and clay.lanes[2].name == "Gamma"
    assert doc.totals.slipped == 4 and all(s.lane != "Gamma" for s in doc.lanes)


def test_compare_legend_and_json_carry_the_risks(clay: oc.CompareLayout) -> None:
    kinds = [e.kind for e in clay.legend]
    assert [k for k in kinds if k.startswith("risk-")] == [
        "risk-high",
        "risk-medium",
        "risk-low",
        "risk-unknown",
    ]
    blob = oc.compare_layout_json(clay)
    assert sum(1 for p in blob["items"] if p["kind"] == "risk") == 4


def test_compare_without_risks_is_unchanged() -> None:
    plain = build_compare_layout(_cmp(), TODAY, "C")
    assert all(p.kind == "item" for p in plain.items) and len(plain.lanes) == 2
    assert not any(e.kind.startswith("risk-") for e in plain.legend)


def test_mutation_compare_risk_status_leaking_into_a_summary_is_caught() -> None:
    """MUTATION: a risk counted by ``_summary`` would raise on its status — the summaries are
    built from the DOCUMENT's rows, never the layout's synthetic ones."""
    doc = _cmp()
    with pytest.raises(KeyError):
        oc._summary(
            "x",
            [
                *doc.rows,
                oc.CompareRow(
                    "Alpha",
                    "r",
                    oc.RISK,
                    None,
                    None,
                    TODAY,
                    TODAY,
                    None,
                    None,
                    None,
                    None,
                    None,
                    True,
                    None,
                    None,
                    "risk:x",
                ),
            ],
        )
