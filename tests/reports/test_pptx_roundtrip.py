"""The PowerPoint export as a CARRIER of the session, and its reader (ADR-0544).

Three promises, each with a twin that breaks the product in memory and watches the SAME check go
red by name (QC-1):

* **the default export is byte-identical to the deck written before carriers existed** — the
  sixteen parts, no ``descr`` anywhere, no custom XML — so every deck test in this tree and the
  operator's PowerPoint keep seeing the file they saw;
* **the session record round-trips** through the custom XML part, found by its namespace, and
  the alt-text fallback alone rebuilds the slide when that part is dropped;
* **a risk is an upward triangle in its probability's colour**, with its impact after the label
  in that colour, and the legend's risk entries are the same triangle.

Every oracle is a typed literal — the member list, the records, the hex colours — never a value
read off the module it judges. The reader's hardening (DTD, decompression budget, exact member
names, a non-LODESTAR deck) is measured here too, each with its twin.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from schedule_forensics.reports import pptx, pptx_read
from schedule_forensics.reports.onepager import Layout, OnePagerDoc, OnePagerItem, build_layout
from schedule_forensics.reports.onepager_compare import (
    CompareLayout,
    build_compare_layout,
    compare_onepager_docs,
)
from schedule_forensics.reports.onepager_risks import OnePagerRisk, impact_label, keyed_risks
from schedule_forensics.reports.pptx import render_onepager_compare_pptx, render_onepager_pptx
from schedule_forensics.reports.pptx_read import read_pptx

_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_TODAY = dt.date(2026, 6, 15)
_REPO_ROOT = Path(__file__).resolve().parents[2]
#: A deck PowerPoint itself wrote (committed, non-CUI per ADR-0152) — a deck that is not ours.
_CONTROL = _REPO_ROOT / "00_REFERENCE_INTAKE" / "mpp" / "Politte Schedule Tool.pptx"

#: The deck's parts before carriers existed — the member list a default export must still have.
_MEMBERS = [
    "[Content_Types].xml",
    "_rels/.rels",
    "docProps/core.xml",
    "docProps/app.xml",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
    "ppt/theme/theme1.xml",
    "ppt/presProps.xml",
    "ppt/viewProps.xml",
    "ppt/tableStyles.xml",
    "ppt/slideMasters/slideMaster1.xml",
    "ppt/slideMasters/_rels/slideMaster1.xml.rels",
    "ppt/slideLayouts/slideLayout1.xml",
    "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
    "ppt/slides/slide1.xml",
    "ppt/slides/_rels/slide1.xml.rels",
]
#: ...and the three a carrier adds.
_CARRIER_MEMBERS = [
    "customXml/item1.xml",
    "customXml/itemProps1.xml",
    "customXml/_rels/item1.xml.rels",
]
_NS = "urn:lodestar:session"
#: A record with every character class the XML carrier must escape, and a non-ASCII one.
_PAYLOAD = '{"lodestar":{"format":1,"page":"timeline","title":"T <&> \\"q\\" — é"}}'.encode()
_SETTINGS = {"page": "timeline", "title": "", "links": [], "sources": {"list": "probe.xlsx"}}
_NO_DATA = "the deck carries no LODESTAR data (no session part and no LODESTAR alt text)"
_HIGH, _LOW, _WHITE = "B3261E", "1E7B34", "FFFFFF"


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────


def _items() -> list[OnePagerItem]:
    return [
        OnePagerItem(
            "Design",
            "Preliminary design review",
            dt.date(2026, 1, 5),
            dt.date(2026, 3, 20),
            2,
            True,
        ),
        OnePagerItem(
            "Build", "Structure fabrication", dt.date(2026, 4, 6), dt.date(2026, 8, 14), 3, False
        ),
        OnePagerItem("Test", "Ready to Ship", dt.date(2026, 12, 4), dt.date(2026, 12, 4), 4, None),
    ]


def _risks() -> list[OnePagerRisk]:
    return keyed_risks(
        [
            OnePagerRisk("Build", "Vendor slip", dt.date(2026, 7, 1), "30", 30, "high", 2),
            OnePagerRisk(
                "Test", "Chamber availability", dt.date(2026, 10, 15), "10 wd", None, "low", 3
            ),
        ]
    )


def _timeline(with_risks: bool = True) -> Layout:
    risks = _risks() if with_risks else []
    return build_layout(
        _items(),
        _TODAY,
        "Program One-Pager",
        "Prepared 2026-06-15",
        status_column="E",
        risks=risks,
        risk_impacts={r.key: impact_label(r) for r in risks},
    )


def _compare(with_risks: bool = True) -> CompareLayout:
    shift = dt.timedelta(days=12)
    prior = OnePagerDoc("prior.xlsx", "Sheet1", tuple(_items()), (), ())
    current = OnePagerDoc(
        "current.xlsx",
        "Sheet1",
        tuple(
            OnePagerItem(i.lane, i.name, i.start + shift, i.finish + shift, i.row, i.complete)
            for i in _items()[:2]
        ),
        (),
        (),
    )
    risks = _risks() if with_risks else []
    return build_compare_layout(
        compare_onepager_docs(prior, current),
        _TODAY,
        "Program Compare",
        risks=risks,
        risk_impacts={r.key: impact_label(r) for r in risks},
    )


def _carrier(lay: Layout | CompareLayout) -> bytes:
    if isinstance(lay, CompareLayout):
        return render_onepager_compare_pptx(
            lay, marking="CUI", source="s", payload=_PAYLOAD, settings=_SETTINGS
        )
    return render_onepager_pptx(
        lay, marking="CUI", source="s", payload=_PAYLOAD, settings=_SETTINGS
    )


def _members(data: bytes) -> list[str]:
    return zipfile.ZipFile(io.BytesIO(data)).namelist()


def _part(data: bytes, name: str) -> bytes:
    return zipfile.ZipFile(io.BytesIO(data)).read(name)


def _slide(data: bytes) -> ET.Element:
    return ET.fromstring(_part(data, "ppt/slides/slide1.xml"))


def _shapes(
    data: bytes,
) -> dict[str, tuple[str | None, list[str], str, list[tuple[str, str, bool]]]]:
    """``name -> (preset, srgb colours in order, descr, runs)`` for every ``p:sp``."""
    out: dict[str, tuple[str | None, list[str], str, list[tuple[str, str, bool]]]] = {}
    for sp in _slide(data).iter(f"{_P}sp"):
        c = sp.find(f"{_P}nvSpPr/{_P}cNvPr")
        assert c is not None
        geom = sp.find(f".//{_A}prstGeom")
        colours = [str(x.get("val")) for x in sp.find(f"{_P}spPr").iter(f"{_A}srgbClr")]  # type: ignore[union-attr]
        runs = []
        for r in sp.iter(f"{_A}r"):
            rpr = r.find(f"{_A}rPr")
            fill = rpr.find(f"{_A}solidFill/{_A}srgbClr") if rpr is not None else None
            runs.append(
                (
                    r.findtext(f"{_A}t") or "",
                    str(fill.get("val")) if fill is not None else "",
                    (rpr.get("b") if rpr is not None else None) == "1",
                )
            )
        out[str(c.get("name"))] = (
            geom.get("prst") if geom is not None else None,
            colours,
            c.get("descr") or "",
            runs,
        )
    return out


def _rezip(data: bytes, edit: Callable[[str, bytes], bytes | None]) -> bytes:
    """The deck with every member passed through ``edit`` (``None`` drops it) — the twins'
    way of breaking a deck the way another program's re-save might."""
    out = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(data)) as src,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst,
    ):
        for info in src.infolist():
            got = edit(info.filename, src.read(info.filename))
            if got is not None:
                dst.writestr(info.filename, got)
    return out.getvalue()


def _drop_custom_xml(name: str, blob: bytes) -> bytes | None:
    """What a re-save that does not understand the part does: the part, its props, its rels,
    its Override and its relationship all gone."""
    if name.startswith("customXml/"):
        return None
    if name == "[Content_Types].xml":
        return re.sub(rb"<Override PartName=\"/customXml/[^>]*/>", b"", blob)
    if name == "ppt/_rels/presentation.xml.rels":
        return re.sub(rb"<Relationship [^>]*customXml[^>]*/>", b"", blob)
    return blob


# ── the default export is the deck written before ─────────────────────────────────────────────


@pytest.mark.parametrize("lay", [_timeline(False), _compare(False)], ids=["timeline", "compare"])
def test_default_arguments_write_the_deck_exactly_as_before(lay: Layout | CompareLayout) -> None:
    """``payload=None, settings=None`` IS the default: the same bytes, the sixteen members, no
    alt text, no custom XML. The lead's wiring passes both explicitly."""
    if isinstance(lay, CompareLayout):
        plain = render_onepager_compare_pptx(lay, marking="CUI", source="s")
        explicit = render_onepager_compare_pptx(
            lay, marking="CUI", source="s", payload=None, settings=None
        )
    else:
        plain = render_onepager_pptx(lay, marking="CUI", source="s")
        explicit = render_onepager_pptx(lay, marking="CUI", source="s", payload=None, settings=None)
    assert plain == explicit
    assert _members(plain) == _MEMBERS
    assert b"descr=" not in _part(plain, "ppt/slides/slide1.xml")
    assert b"customXml" not in _part(plain, "[Content_Types].xml")
    assert b"customXml" not in _part(plain, "ppt/_rels/presentation.xml.rels")


def test_mutation_a_carried_deck_is_not_the_default_deck() -> None:
    """The checks above have teeth: a deck that carries a record fails every one of them, by
    name — so a default export that quietly started carrying would be caught."""
    lay = _timeline(False)
    plain = render_onepager_pptx(lay, marking="CUI", source="s")
    carried = _carrier(lay)
    assert plain != carried
    assert _members(carried) == _MEMBERS + _CARRIER_MEMBERS
    assert b"descr=" in _part(carried, "ppt/slides/slide1.xml")
    assert b'<Override PartName="/customXml/itemProps1.xml"' in _part(
        carried, "[Content_Types].xml"
    )
    assert b'Target="../customXml/item1.xml"' in _part(carried, "ppt/_rels/presentation.xml.rels")


def test_a_carried_deck_is_deterministic_and_every_part_is_well_formed() -> None:
    a, b = _carrier(_timeline()), _carrier(_timeline())
    assert a == b
    for name in _members(a):
        ET.fromstring(_part(a, name))  # every part, including the three new ones, parses


# ── the record round-trips ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("lay", [_timeline(), _compare()], ids=["timeline", "compare"])
def test_the_record_round_trips_through_the_custom_xml_part(lay: Layout | CompareLayout) -> None:
    """The bytes in are the bytes out — escaped on the way in, unescaped on the way out — and
    the part is the data store a PowerPoint package relates from its presentation."""
    data = _carrier(lay)
    got = read_pptx(data)
    assert got.problem == ""
    assert got.payload == _PAYLOAD
    assert got.notes == ()
    root = ET.fromstring(_part(data, "customXml/item1.xml"))
    assert root.tag == f"{{{_NS}}}lodestar" and root.get("format") == "1"
    props = ET.fromstring(_part(data, "customXml/itemProps1.xml"))
    ds = "{http://schemas.openxmlformats.org/officeDocument/2006/customXml}"
    assert props.tag == f"{ds}datastoreItem" and props.get(f"{ds}itemID", "").startswith("{")
    assert props.find(f"{ds}schemaRefs/{ds}schemaRef").get(f"{ds}uri") == _NS  # type: ignore[union-attr]
    rels = _part(data, "ppt/_rels/presentation.xml.rels")
    assert b'relationships/customXml" Target="../customXml/item1.xml"' in rels
    item_rels = _part(data, "customXml/_rels/item1.xml.rels")
    assert b'relationships/customXmlProps" Target="itemProps1.xml"' in item_rels


def test_the_part_is_found_by_its_namespace_never_by_its_name() -> None:
    """A re-save may renumber the part: ``item1`` -> ``item7`` still reads."""
    data = _carrier(_timeline())
    renamed = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(renamed, "w") as dst:
        for info in src.infolist():
            dst.writestr(info.filename.replace("item1", "item7"), src.read(info.filename))
    assert read_pptx(renamed.getvalue()).payload == _PAYLOAD


def test_mutation_a_part_without_the_namespace_is_not_the_record() -> None:
    """The same part with another namespace is NOT read as the record — the namespace is the
    identity, so the test above cannot pass on a reader that takes any ``customXml/item*``."""
    data = _carrier(_timeline())
    other = _rezip(
        data,
        lambda n, b: (
            b.replace(_NS.encode(), b"urn:other:thing") if n == "customXml/item1.xml" else b
        ),
    )
    got = read_pptx(other)
    assert got.payload is None
    assert got.problem == ""  # the alt text still carries the slide
    assert any("session part is absent" in n for n in got.notes)


def test_a_record_xml_cannot_carry_is_refused_by_name() -> None:
    lay = _timeline()
    with pytest.raises(ValueError, match="not UTF-8"):
        render_onepager_pptx(
            lay, marking="CUI", source="s", payload=b"\xff\xfe\x00", settings=_SETTINGS
        )
    with pytest.raises(ValueError, match="cannot carry"):
        render_onepager_pptx(
            lay, marking="CUI", source="s", payload=b'{"a":"\x01"}', settings=_SETTINGS
        )


def test_mutation_without_the_refusal_the_part_would_not_read_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WHY the writer refuses: with the check gone, the part is written and the reader cannot
    parse it — the record is silently lost. The refusal turns that into a named error."""
    monkeypatch.setattr(pptx, "_XML_FORBIDDEN_RE", re.compile("(?!x)x"))  # never matches
    data = render_onepager_pptx(
        _timeline(), marking="CUI", source="s", payload=b'{"a":"\x01"}', settings=_SETTINGS
    )
    got = read_pptx(data)
    assert got.payload is None
    assert any("customXml/item1.xml: malformed XML part" in n for n in got.notes)


# ── the alt-text fallback ─────────────────────────────────────────────────────────────────────

#: Every item shape's record on the Timeline fixture — the swimlane's NAME, ISO dates, the
#: status column's reading (``None`` for a risk: it has no such column), the layout's key.
_TIMELINE_ITEMS = [
    {
        "complete": True,
        "finish": "2026-03-20",
        "impact": "",
        "key": "e669869dcd5b7554",
        "kind": "item",
        "lane": "Design",
        "name": "Preliminary design review",
        "prob": "",
        "start": "2026-01-05",
    },
    {
        "complete": False,
        "finish": "2026-08-14",
        "impact": "",
        "key": "4a20fa75f453e53f",
        "kind": "item",
        "lane": "Build",
        "name": "Structure fabrication",
        "prob": "",
        "start": "2026-04-06",
    },
    {
        "complete": None,
        "finish": "2026-07-01",
        "impact": "impact +30 cal d",
        "key": "40945830077c58c7",
        "kind": "risk",
        "lane": "Build",
        "name": "Vendor slip",
        "prob": "high",
        "start": "2026-07-01",
    },
    {
        "complete": None,
        "finish": "2026-10-15",
        "impact": "impact: 10 wd",
        "key": "e9a8f0ad9efcf78b",
        "kind": "risk",
        "lane": "Test",
        "name": "Chamber availability",
        "prob": "low",
        "start": "2026-10-15",
    },
    {
        "complete": False,
        "finish": "2026-12-04",
        "impact": "",
        "key": "875010cb64ee06e4",
        "kind": "item",
        "lane": "Test",
        "name": "Ready to Ship",
        "prob": "",
        "start": "2026-12-04",
    },
]
#: ...and on the Compare fixture: a ghost is the PRIOR side (its completion unknown to the
#: layout: ``None``), a solid shape the CURRENT side, a risk a current-side ``risk`` status.
#: The compare docs carry no status column, so every ``complete`` is ``None`` here.
_COMPARE_ITEMS = [
    {
        "complete": None,
        "finish": "2026-03-20",
        "impact": "",
        "key": "e669869dcd5b7554",
        "kind": "item",
        "lane": "Design",
        "name": "Preliminary design review",
        "prob": "",
        "side": "prior",
        "start": "2026-01-05",
        "status": "slipped",
    },
    {
        "complete": None,
        "finish": "2026-04-01",
        "impact": "",
        "key": "e669869dcd5b7554",
        "kind": "item",
        "lane": "Design",
        "name": "Preliminary design review",
        "prob": "",
        "side": "current",
        "start": "2026-01-17",
        "status": "slipped",
    },
    {
        "complete": None,
        "finish": "2026-08-14",
        "impact": "",
        "key": "4a20fa75f453e53f",
        "kind": "item",
        "lane": "Build",
        "name": "Structure fabrication",
        "prob": "",
        "side": "prior",
        "start": "2026-04-06",
        "status": "slipped",
    },
    {
        "complete": None,
        "finish": "2026-08-26",
        "impact": "",
        "key": "4a20fa75f453e53f",
        "kind": "item",
        "lane": "Build",
        "name": "Structure fabrication",
        "prob": "",
        "side": "current",
        "start": "2026-04-18",
        "status": "slipped",
    },
    {
        "complete": None,
        "finish": "2026-07-01",
        "impact": "impact +30 cal d",
        "key": "risk:40945830077c58c7",
        "kind": "risk",
        "lane": "Build",
        "name": "Vendor slip",
        "prob": "high",
        "side": "current",
        "start": "2026-07-01",
        "status": "risk",
    },
    {
        "complete": None,
        "finish": "2026-10-15",
        "impact": "impact: 10 wd",
        "key": "risk:e9a8f0ad9efcf78b",
        "kind": "risk",
        "lane": "Test",
        "name": "Chamber availability",
        "prob": "low",
        "side": "current",
        "start": "2026-10-15",
        "status": "risk",
    },
    {
        "complete": None,
        "finish": "2026-12-04",
        "impact": "",
        "key": "",
        "kind": "item",
        "lane": "Test",
        "name": "Ready to Ship",
        "prob": "",
        "side": "prior",
        "start": "2026-12-04",
        "status": "removed",
    },
]


@pytest.mark.parametrize(
    ("lay", "want"),
    [(_timeline(), _TIMELINE_ITEMS), (_compare(), _COMPARE_ITEMS)],
    ids=["timeline", "compare"],
)
def test_every_item_shape_and_the_title_carry_their_record(
    lay: Layout | CompareLayout, want: list[dict[str, object]]
) -> None:
    data = _carrier(lay)
    shapes = _shapes(data)
    assert shapes["Title"][2] == "LODESTAR slide: " + json.dumps(_SETTINGS, sort_keys=True)
    carried = {n: d for n, (_p, _c, d, _r) in shapes.items() if d}
    assert set(carried) == {"Title"} | {
        n
        for n in shapes
        if n.startswith(
            ("Activity: ", "Milestone: ", "Risk: ", "Prior activity: ", "Prior milestone: ")
        )
    }, "alt text sits on the Title and EVERY item shape, nowhere else"
    got = read_pptx(data)
    assert got.settings == _SETTINGS
    assert got.items == want


def test_mutation_a_writer_with_another_prefix_carries_nothing_the_reader_sees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Break the writer's item prefix in memory: the reader (which took the prefix at import)
    finds no item, and the record check above goes red by name."""
    monkeypatch.setattr(pptx, "ITEM_DESCR", "LODESTAR thing: ")
    got = read_pptx(_carrier(_timeline()))
    assert got.items == []
    assert got.items != _TIMELINE_ITEMS


@pytest.mark.parametrize("lay", [_timeline(), _compare()], ids=["timeline", "compare"])
def test_alt_text_alone_rebuilds_the_slide_when_the_part_is_dropped(
    lay: Layout | CompareLayout,
) -> None:
    """A re-save that dropped the custom XML part (its Override and relationship too) still
    yields the settings and every item, and SAYS it did so from the alt text."""
    stripped = _rezip(_carrier(lay), _drop_custom_xml)
    assert not any(n.startswith("customXml/") for n in _members(stripped))
    got = read_pptx(stripped)
    assert got.problem == ""
    assert got.payload is None
    assert got.settings == _SETTINGS
    assert got.items == (_COMPARE_ITEMS if isinstance(lay, CompareLayout) else _TIMELINE_ITEMS)
    assert got.notes == ("the deck's session part is absent — the slide is read from its alt text",)


def test_mutation_stripping_the_alt_text_too_leaves_nothing_and_says_so() -> None:
    def strip(name: str, blob: bytes) -> bytes | None:
        got = _drop_custom_xml(name, blob)
        if got is not None and name == "ppt/slides/slide1.xml":
            got = re.sub(rb' descr="[^"]*"', b"", got)
        return got

    got = read_pptx(_rezip(_carrier(_timeline()), strip))
    assert (got.payload, got.settings, got.items) == (None, None, [])
    assert got.problem == _NO_DATA


def test_an_unreadable_alt_text_record_is_counted_not_guessed() -> None:
    def spoil(name: str, blob: bytes) -> bytes | None:
        if name == "ppt/slides/slide1.xml":
            return blob.replace(b'descr="LODESTAR item: {', b'descr="LODESTAR item: [', 1)
        return blob

    got = read_pptx(_rezip(_carrier(_timeline()), spoil))
    assert len(got.items) == len(_TIMELINE_ITEMS) - 1
    assert "1 LODESTAR alt-text record(s) could not be read and were skipped" in got.notes


# ── a deck that is not ours ───────────────────────────────────────────────────────────────────


def test_a_non_lodestar_deck_is_refused_by_name() -> None:
    assert read_pptx(b"not a zip at all").problem == "not a PowerPoint deck (not a zip package)"
    no_pres = io.BytesIO()
    with zipfile.ZipFile(no_pres, "w") as zf:
        zf.writestr("PPT/presentation.xml", "<x/>")  # the wrong case: names are matched exactly
        zf.writestr("xl/workbook.xml", "<x/>")
    assert (
        read_pptx(no_pres.getvalue()).problem == "not a PowerPoint deck (no ppt/presentation.xml)"
    )
    plain = render_onepager_pptx(_timeline(False), marking="CUI", source="s")
    assert read_pptx(plain).problem == _NO_DATA
    if _CONTROL.exists():
        got = read_pptx(_CONTROL.read_bytes())
        assert got.problem == _NO_DATA and got.items == [] and got.settings is None


# ── hardening ─────────────────────────────────────────────────────────────────────────────────


def _with_dtd(name: str, blob: bytes) -> bytes | None:
    if name == "customXml/item1.xml":
        head, _sep, rest = blob.partition(b"?>")
        return head + b'?><!DOCTYPE lodestar [<!ENTITY e "x">]>' + rest
    return blob


def test_a_part_with_a_dtd_is_refused_and_named() -> None:
    got = read_pptx(_rezip(_carrier(_timeline()), _with_dtd))
    assert got.payload is None
    assert any(
        n.startswith("customXml/item1.xml: a part with a DTD or entity declaration is rejected")
        for n in got.notes
    )
    assert got.items == _TIMELINE_ITEMS  # the fallback still reads


def test_mutation_an_unhardened_parser_would_read_the_dtd_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ElementTree alone accepts an internal DTD — so the check above goes red without the
    guard: the payload comes back, and nothing is named."""
    monkeypatch.setattr(pptx_read, "_parse_xml", ET.fromstring)
    got = read_pptx(_rezip(_carrier(_timeline()), _with_dtd))
    assert got.payload == _PAYLOAD
    assert got.notes == ()


def test_the_decompression_budget_ends_the_read_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _carrier(_timeline())
    assert read_pptx(data).problem == ""
    monkeypatch.setattr(pptx_read, "_MAX_DECOMPRESSED_BYTES", 1000)
    got = read_pptx(data)
    assert got.problem == "the deck decompresses past the size cap (possible zip bomb)"
    assert (got.payload, got.settings, got.items) == (None, None, [])


# ── the risk glyph ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("lay", [_timeline(), _compare()], ids=["timeline", "compare"])
def test_a_risk_is_an_upward_triangle_in_its_probability_colour(
    lay: Layout | CompareLayout,
) -> None:
    """DrawingML's ``triangle`` preset points up; the fill is the probability's print colour,
    the outline the slide's white; the glyph is a milestone's size, centred on its moment; the
    impact follows the label in that colour, bold; the legend's entry is the same triangle."""
    data = (
        render_onepager_pptx(lay, marking="CUI", source="s")
        if isinstance(lay, Layout)
        else render_onepager_compare_pptx(lay, marking="CUI", source="s")
    )
    shapes = _shapes(data)
    assert shapes["Risk: Vendor slip"][:2] == ("triangle", [_HIGH, _WHITE])
    assert shapes["Risk: Chamber availability"][:2] == ("triangle", [_LOW, _WHITE])
    risk = next(p for p in lay.items if p.name == "Vendor slip")
    assert risk.x0 is not None
    ms = risk.ms or lay.ms
    sp = next(
        s
        for s in _slide(data).iter(f"{_P}sp")
        if s.find(f"{_P}nvSpPr/{_P}cNvPr").get("name") == "Risk: Vendor slip"
    )  # type: ignore[union-attr]
    off, ext = sp.find(f".//{_A}off"), sp.find(f".//{_A}ext")
    assert off is not None and ext is not None
    assert (int(off.get("x", "")), int(off.get("y", ""))) == (
        round((risk.x0 - ms / 2) * 12700),
        round((risk.y - ms / 2) * 12700),
    )
    assert (int(ext.get("cx", "")), int(ext.get("cy", ""))) == (
        round(ms * 12700),
        round(ms * 12700),
    )
    runs = shapes["Label: Vendor slip"][3]
    assert runs == [
        ("RISK · Vendor slip (7/1/26)", "1C2330", False),
        (" impact +30 cal d", _HIGH, True),
    ]
    assert shapes["Label: Chamber availability"][3][1] == (" impact: 10 wd", _LOW, True)
    assert shapes["Legend: risk-high"][:2] == ("triangle", [_HIGH])
    assert shapes["Legend: risk-low"][:2] == ("triangle", [_LOW])
    assert "Legend: risk-medium" not in shapes and "Legend: risk-unknown" not in shapes
    assert shapes["Read-me"][3][0][0].endswith(" · triangles = risks (colour = probability)")
    assert "Milestone: Vendor slip" not in shapes and "Activity: Vendor slip" not in shapes


def test_mutation_a_diamond_or_another_colour_is_caught_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pptx, "_RISK_PRST", "diamond")
    shapes = _shapes(render_onepager_pptx(_timeline(), marking="CUI", source="s"))
    assert shapes["Risk: Vendor slip"][0] == "diamond" != "triangle"
    monkeypatch.setattr(pptx, "_RISK_PRST", "triangle")
    monkeypatch.setattr(pptx, "RISK_COLORS", {**pptx.RISK_COLORS, "high": "000000"})
    shapes = _shapes(render_onepager_pptx(_timeline(), marking="CUI", source="s"))
    assert shapes["Risk: Vendor slip"][1] == ["000000", _WHITE] != [_HIGH, _WHITE]
    assert shapes["Legend: risk-high"][1] == ["000000"]


def test_a_slide_without_a_risk_reads_as_before() -> None:
    shapes = _shapes(render_onepager_pptx(_timeline(False), marking="CUI", source="s"))
    assert not any(n.startswith(("Risk: ", "Legend: risk-")) for n in shapes)
    assert shapes["Read-me"][3][0][0] == (
        "Timeline: months and years · bars = activities · diamonds = milestones · "
        "red line = data date"
    )


# ── the attribute escaper (found while attacking this change's plan) ──────────────────────────


def test_a_quoted_name_writes_a_well_formed_slide() -> None:
    """Before ADR-0544 a name holding ``"`` wrote a slide no parser accepted (measured on the
    tree before this change); the alt-text records are JSON, so every one carries quotes."""
    lay = build_layout(
        [OnePagerItem("Lane", 'Say "hi"', dt.date(2027, 1, 5), dt.date(2027, 3, 1), 2)], _TODAY, "T"
    )
    data = render_onepager_pptx(lay, marking="CUI", source="s", settings={"title": 'say "hi"'})
    shapes = _shapes(data)
    assert 'Activity: Say "hi"' in shapes
    assert read_pptx(data).settings == {"title": 'say "hi"'}


def test_mutation_the_text_escaper_alone_writes_a_malformed_slide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pptx, "_attr", pptx._esc)
    lay = build_layout(
        [OnePagerItem("Lane", 'Say "hi"', dt.date(2027, 1, 5), dt.date(2027, 3, 1), 2)], _TODAY, "T"
    )
    data = render_onepager_pptx(lay, marking="CUI", source="s")
    with pytest.raises(ET.ParseError):
        _slide(data)
