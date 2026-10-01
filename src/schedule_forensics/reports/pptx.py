"""Minimal, dependency-free .pptx writer — the One-Pager as ONE slide of native PowerPoint shapes.

A ``.pptx`` is a zip of XML parts; this emits the smallest set PowerPoint and LibreOffice accept
(content types, package relationships, a presentation, one blank master + layout, a theme, one
slide) using DrawingML preset shapes: rounded rectangles for activities, diamonds for milestones,
dotted connectors for the month grid, a red connector for today, text boxes for every label.
Every shape is a real, editable object on the slide — the operator can nudge a label or recolour
a lane in PowerPoint — and every one of them is named for the selection pane.

The geometry is NOT computed here. :func:`render_onepager_pptx` paints the
:class:`schedule_forensics.reports.onepager.Layout` the browser paints, point for point (one
layout unit = one point = 12,700 EMU), so the page is an honest preview of the export.
Std-lib only (``zipfile``), byte-deterministic (fixed zip timestamps, fixed part order) — the
same posture as the Word and Excel writers beside it. Like those, the slide carries the CUI
marking top and bottom (Law 1 — every exported artifact carries its handling caveat); the text
is the page's own marking, so a session asserted UNCLASSIFIED exports that wording instead.

**The deck as a carrier (ADR-0544).** The operator asked to re-import any export and have the
slide come back with its logic intact, so a deck can carry the session's record two ways at
once, both opt-in and both leaving the default export byte-identical to before:

* ``payload`` — the record's bytes (:mod:`~.session_payload`) in a custom XML part
  (``customXml/item1.xml``, root ``<lodestar xmlns="urn:lodestar:session">``), related from
  the presentation the way Word relates its data stores. :func:`~.pptx_read.read_pptx` finds
  it by that NAMESPACE, never by the part's name.
* ``settings`` — the same facts on the shapes' alt text (``descr``): the Title shape says
  ``LODESTAR slide: {json}`` and every item shape ``LODESTAR item: {json}``. This is the
  FALLBACK: a deck re-saved by another program may drop a custom XML part it does not
  understand (LibreOffice — UNVERIFIED here, no Impress in this container; CI's interop test
  measures it), but alt text is a property every editor keeps, so the slide can still be
  rebuilt from its shapes.

A risk (``Placed.kind == "risk"``) is an upward triangle — DrawingML's ``triangle`` preset
points up — filled in its probability's colour (:data:`RISK_COLORS`) with the slide-white
outline every item has, and its impact text after the label in that colour, exactly as the
Compare slide paints a delta; the legend's ``risk-*`` kinds are the same triangle, small.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Mapping

from schedule_forensics.reports.onepager import Layout
from schedule_forensics.reports.onepager_compare import CompareLayout
from schedule_forensics.reports.onepager_links import LINK_W, PlacedLink

_EMU_PER_PT = 12700
_SLIDE_W, _SLIDE_H = 12192000, 6858000  # 13.333 x 7.5 in — 16:9
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
_NS = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
)
_REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
_CT_BASE = "application/vnd.openxmlformats-officedocument."

#: The print palette (white slide): ten distinct, muted hues in the order the layout assigns
#: ``Lane.color``. The browser paints the SAME index through the ``--lane-N`` theme tokens.
LANE_PALETTE = (
    "2E5C9A",
    "C55A11",
    "3A7D44",
    "7B3F9E",
    "B8860B",
    "1F8A8A",
    "A0334F",
    "556B2F",
    "4A6FA5",
    "8C6D46",
)
_INK, _MUTED, _LINE, _GRID = "1C2330", "5B6675", "C9D1DC", "9AA5B5"
_TODAY, _WHITE, _CUI, _SYMBOL = "C00000", "FFFFFF", "4B2E83", "6B7280"
#: The Timeline chart's right edge in points (the Compare slide's is its summary column's).
_SLIDE_RIGHT = 944.0
_YEAR_SHADE = ("F5F7FA", "EAEEF3")


def _esc(value: str) -> str:
    """XML-escape text content (this module only WRITES XML; nothing is parsed)."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _attr(value: str) -> str:
    """XML-escape an ATTRIBUTE value — text's three plus the double quote the attribute is
    delimited by. Measured on the tree before ADR-0544: a shape named ``Say "hi"`` wrote a slide
    no parser accepted, because names went through :func:`_esc` alone; the alt-text records this
    change adds are JSON, so every one of them carries quotes."""
    return _esc(value).replace('"', "&quot;")


#: The print palette of a risk's probability (ADR-0544; the PDF painter imports these): high ·
#: medium · low · ``unknown`` (a probability the register's reader could not read — neutral,
#: never guessed). The medium is the Compare slide's DUPLICATE amber, the high its slip red.
RISK_COLORS: Mapping[str, str] = {
    "high": "B3261E",
    "medium": "B8860B",
    "low": "1E7B34",
    "unknown": "6B7280",
}
#: The risk glyph's DrawingML preset — an isosceles triangle, apex UP, so no flip is needed. A
#: module constant so a test can break it in memory and watch the glyph check go red by name.
_RISK_PRST = "triangle"

#: The alt-text records (``descr`` on ``p:cNvPr``), by prefix: the Title shape's settings and
#: one per item shape. :mod:`~.pptx_read` reads them back by these same prefixes.
SETTINGS_DESCR = "LODESTAR slide: "
ITEM_DESCR = "LODESTAR item: "
#: The custom XML part's namespace — what the reader looks for — and the fixed data-store item
#: ID its properties part names (one deck, one store: a constant keeps the bytes deterministic).
CUSTOM_XML_NS = "urn:lodestar:session"
_DATASTORE_ITEM_ID = "{5B0E7A7C-3F1D-4C7A-9E2B-6D1A2C3E4F50}"
#: XML 1.0 cannot carry a control character other than tab, newline and return, in any
#: escaping; a payload holding one is refused by name rather than silently altered.
_XML_FORBIDDEN_RE = re.compile("[^\x09\x0a\x0d\x20-퟿-�\U00010000-\U0010ffff]")


def tint(hex6: str, keep: float) -> str:
    """Mix a colour toward white, keeping ``keep`` of the hue (``0.07`` is a lane band)."""
    channels = (int(hex6[i : i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{round(255 - (255 - c) * keep):02X}" for c in channels)


def _rels(pairs: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<Relationship Id="rId{i}" Type="{_REL_BASE}{kind}" Target="{target}"/>'
        for i, (kind, target) in enumerate(pairs, start=1)
    )
    return (
        _XML
        + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + body
        + "</Relationships>"
    )


_CONTENT_TYPES = (
    _XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    f'<Override PartName="/ppt/presentation.xml" ContentType="{_CT_BASE}'
    'presentationml.presentation.main+xml"/>'
    f'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="{_CT_BASE}'
    'presentationml.slideMaster+xml"/>'
    f'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="{_CT_BASE}'
    'presentationml.slideLayout+xml"/>'
    f'<Override PartName="/ppt/slides/slide1.xml" ContentType="{_CT_BASE}'
    'presentationml.slide+xml"/>'
    f'<Override PartName="/ppt/theme/theme1.xml" ContentType="{_CT_BASE}theme+xml"/>'
    f'<Override PartName="/ppt/presProps.xml" ContentType="{_CT_BASE}'
    'presentationml.presProps+xml"/>'
    f'<Override PartName="/ppt/viewProps.xml" ContentType="{_CT_BASE}'
    'presentationml.viewProps+xml"/>'
    f'<Override PartName="/ppt/tableStyles.xml" ContentType="{_CT_BASE}'
    'presentationml.tableStyles+xml"/>'
    '<Override PartName="/docProps/core.xml" '
    'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    f'<Override PartName="/docProps/app.xml" ContentType="{_CT_BASE}extended-properties+xml"/>'
    "</Types>"
)
#: The content-type Override and the presentation relationship a deck gains ONLY when it carries
#: a session record (ADR-0544): the item part itself is covered by the ``xml`` Default, its
#: properties part needs the customXmlProperties type, and the presentation relates to the item
#: the way a Word document relates to its data stores.
_CUSTOM_XML_OVERRIDE = (
    '<Override PartName="/customXml/itemProps1.xml" '
    f'ContentType="{_CT_BASE}customXmlProperties+xml"/>'
)
_CUSTOM_XML_REL = ("customXml", "../customXml/item1.xml")
_ROOT_RELS = _rels([("officeDocument", "ppt/presentation.xml")])
_PRESENTATION = (
    _XML + f'<p:presentation {_NS} saveSubsetFonts="1">'
    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
    '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>'
    f'<p:sldSz cx="{_SLIDE_W}" cy="{_SLIDE_H}"/><p:notesSz cx="6858000" cy="9144000"/>'
    "</p:presentation>"
)
_PRESENTATION_REL_PAIRS = [
    # rId1 / rId2 are named by <p:sldMasterId> / <p:sldId> in _PRESENTATION — appending only.
    ("slideMaster", "slideMasters/slideMaster1.xml"),
    ("slide", "slides/slide1.xml"),
    ("theme", "theme/theme1.xml"),
    ("presProps", "presProps.xml"),
    ("viewProps", "viewProps.xml"),
    ("tableStyles", "tableStyles.xml"),
]
_PRESENTATION_RELS = _rels(_PRESENTATION_REL_PAIRS)
_CUSTOM_XML_ITEM_RELS = _rels([("customXmlProps", "itemProps1.xml")])
_CUSTOM_XML_PROPS = (
    _XML + f'<ds:datastoreItem ds:itemID="{_DATASTORE_ITEM_ID}" '
    'xmlns:ds="http://schemas.openxmlformats.org/officeDocument/2006/customXml">'
    f'<ds:schemaRefs><ds:schemaRef ds:uri="{CUSTOM_XML_NS}"/></ds:schemaRefs>'
    "</ds:datastoreItem>"
)


def _custom_xml_item(payload: bytes) -> str:
    """The session record as the custom XML part's one element: its bytes as UTF-8 text,
    XML-escaped, under the namespace the reader looks for. Not UTF-8, or a control character XML
    cannot carry, is refused by name — never altered into something that would read back as a
    different record."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("the session record is not UTF-8 text") from exc
    if _XML_FORBIDDEN_RE.search(text):
        raise ValueError("the session record holds a character XML cannot carry")
    return _XML + f'<lodestar xmlns="{CUSTOM_XML_NS}" format="1">{_esc(text)}</lodestar>'


# The three parts every PowerPoint-authored package carries and this writer did not (R-52,
# ADR-0498). All three are OPTIONAL — LibreOffice Impress loads both decks without them, measured;
# the register's "does not load in LibreOffice 7" was an install with NO presentation import
# filter, which refuses a PowerPoint-authored .pptx and a Microsoft-authored .xlsx with the same
# sentence. They are written anyway because a part-list diff against
# `00_REFERENCE_INTAKE/mpp/Politte Schedule Tool.pptx` showed them to be the whole structural
# delta, and PowerPoint itself is UNVERIFIED here: matching the reference implementation's package
# shape removes that shape as a variable. Each is the MEASURED minimum of what that deck carries —
# PowerPoint's own MRU colours, window geometry and 2010/2012 extensions are editor state, not
# document content, so they are not copied. The tableStyles `def` GUID is the empty-list default
# read out of that same deck.
_PRES_PROPS = _XML + f"<p:presentationPr {_NS}/>"
_VIEW_PROPS = _XML + f'<p:viewPr {_NS}><p:gridSpacing cx="76200" cy="76200"/></p:viewPr>'
_TABLE_STYLES = (
    _XML + '<a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>'
)
_PH_FILL = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
_PH_LINE = (
    '<a:ln w="6350" cap="flat" cmpd="sng" algn="ctr">'
    + _PH_FILL
    + '<a:prstDash val="solid"/></a:ln>'
)
_THEME = (
    _XML + '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'name="OnePager"><a:themeElements><a:clrScheme name="OnePager">'
    '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
    '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
    '<a:dk2><a:srgbClr val="1F2A44"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2>'
    '<a:accent1><a:srgbClr val="2E5C9A"/></a:accent1>'
    '<a:accent2><a:srgbClr val="C55A11"/></a:accent2>'
    '<a:accent3><a:srgbClr val="3A7D44"/></a:accent3>'
    '<a:accent4><a:srgbClr val="7B3F9E"/></a:accent4>'
    '<a:accent5><a:srgbClr val="B8860B"/></a:accent5>'
    '<a:accent6><a:srgbClr val="1F8A8A"/></a:accent6>'
    '<a:hlink><a:srgbClr val="0563C1"/></a:hlink>'
    '<a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>'
    '<a:fontScheme name="OnePager"><a:majorFont><a:latin typeface="Calibri Light"/>'
    '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont>'
    '<a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
    '</a:fontScheme><a:fmtScheme name="OnePager">'
    "<a:fillStyleLst>" + _PH_FILL * 3 + "</a:fillStyleLst>"
    "<a:lnStyleLst>" + _PH_LINE * 3 + "</a:lnStyleLst>"
    "<a:effectStyleLst>"
    + "<a:effectStyle><a:effectLst/></a:effectStyle>" * 3
    + "</a:effectStyleLst><a:bgFillStyleLst>"
    + _PH_FILL * 3
    + "</a:bgFillStyleLst>"
    "</a:fmtScheme></a:themeElements></a:theme>"
)
_EMPTY_TREE = (
    '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
    '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
)
_MASTER = (
    _XML + f'<p:sldMaster {_NS}><p:cSld><p:bg><p:bgRef idx="1001">'
    '<a:schemeClr val="bg1"/></p:bgRef></p:bg>'
    f"<p:spTree>{_EMPTY_TREE}</p:spTree></p:cSld>"
    '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
    'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" '
    'folHlink="folHlink"/>'
    '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
    "<p:txStyles><p:titleStyle><a:lvl1pPr/></p:titleStyle>"
    "<p:bodyStyle><a:lvl1pPr/></p:bodyStyle><p:otherStyle><a:lvl1pPr/></p:otherStyle>"
    "</p:txStyles></p:sldMaster>"
)
_MASTER_RELS = _rels(
    [("slideLayout", "../slideLayouts/slideLayout1.xml"), ("theme", "../theme/theme1.xml")]
)
_LAYOUT_PART = (
    _XML + f'<p:sldLayout {_NS} type="blank" preserve="1"><p:cSld name="Blank">'
    f"<p:spTree>{_EMPTY_TREE}</p:spTree></p:cSld>"
    "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"
)
_LAYOUT_RELS = _rels([("slideMaster", "../slideMasters/slideMaster1.xml")])
_SLIDE_RELS = _rels([("slideLayout", "../slideLayouts/slideLayout1.xml")])


def _core(product: str) -> str:
    """The package's core properties — the program that wrote it named as its creator."""
    return (
        _XML + "<cp:coreProperties "
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>One-Pager</dc:title><dc:creator>{_esc(product)}</dc:creator>"
        "</cp:coreProperties>"
    )


def _app(product: str) -> str:
    return (
        _XML + "<Properties "
        'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f"<Application>{_esc(product)}</Application><Slides>1</Slides></Properties>"
    )


#: The program named in an export's properties unless the caller says otherwise; LODESTAR, the
#: standalone One-Pager program built from these same modules, passes its own name (ADR-0539).
PRODUCT = "POLARIS²"


def _emu(pt: float) -> int:
    return round(pt * _EMU_PER_PT)


def _fill(color: str | None) -> str:
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>' if color else "<a:noFill/>"


def _ln(color: str | None, width_pt: float, dash: str | None = None) -> str:
    if not color:
        return "<a:ln><a:noFill/></a:ln>"
    dash_xml = f'<a:prstDash val="{dash}"/>' if dash else ""
    return f'<a:ln w="{_emu(width_pt)}">{_fill(color)}{dash_xml}</a:ln>'


#: A text glow in the slide's own white, ~1.5 pt (ADR-0543): it renders BEHIND the glyphs, so a
#: label or a link's type tag stays readable where a logic link's shaft runs under it — the
#: .pptx twin of the page's halo (``paint-order: stroke`` in the slide's ground). DrawingML's
#: ``CT_TextCharacterProperties`` is a sequence: the fill, THEN ``effectLst``, then ``latin``.
_GLOW = f'<a:effectLst><a:glow rad="{_emu(1.5)}"><a:srgbClr val="{_WHITE}"/></a:glow></a:effectLst>'


def _run(text: str, size_pt: float, color: str, bold: bool, glow: bool = False) -> str:
    """One run. ``glow`` is opt-in, never inferred from the colour: an item's label OUTSIDE its
    bar and a link's type tag glow; a label inside its bar and a tag's badge text never do."""
    b = ' b="1"' if bold else ""
    return (
        f'<a:r><a:rPr lang="en-US" sz="{round(size_pt * 100)}"{b} dirty="0">'
        f'{_fill(color)}{_GLOW if glow else ""}<a:latin typeface="Calibri"/></a:rPr>'
        f"<a:t>{_esc(text)}</a:t></a:r>"
    )


#: One shape's position and size as :meth:`_Slide.group` reads them back out of its XML.
_XFRM_RE = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>')


class _Slide:
    """Accumulates the ``<p:spTree>`` children of the one slide, in paint order."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self._next_id = 1

    def _id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _cnv(self, name: str, descr: str = "") -> str:
        """One shape's non-visual properties: the next id, its selection-pane name and — only
        when given — its alt text (``descr``, the attribute every editor keeps; ADR-0544's
        fallback record). No ``descr`` attribute at all without one, so a deck that carries no
        record is byte-identical to the deck written before records existed."""
        alt = f' descr="{_attr(descr)}"' if descr else ""
        return f'<p:cNvPr id="{self._id()}" name="{_attr(name)}"{alt}/>'

    def shape(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str | None,
        *,
        prst: str = "rect",
        line: str | None = None,
        line_pt: float = 0.5,
        dash: str | None = None,
        name: str,
        descr: str = "",
    ) -> None:
        self.parts.append(
            f"<p:sp><p:nvSpPr>{self._cnv(name, descr)}"
            "<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>"
            f'<a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/>'
            f'<a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>'
            f"{_fill(fill)}{_ln(line, line_pt, dash)}</p:spPr></p:sp>"
        )

    def arrow(
        self, x0: float, x1: float, y: float, color: str, width_pt: float, *, name: str
    ) -> None:
        """A horizontal connector from ``x0`` to ``x1`` with a triangle head at ``x1`` — the
        compare slide's "the finish moved from here to here". DrawingML puts the ``tailEnd`` at
        the line's END, and a leftward line is a rightward one flipped, so a pull-in is
        ``flipH`` with its head still at ``x1``."""
        flip = ' flipH="1"' if x1 < x0 else ""
        self.parts.append(
            f"<p:cxnSp><p:nvCxnSpPr>{self._cnv(name)}"
            "<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>"
            f'<a:xfrm{flip}><a:off x="{_emu(min(x0, x1))}" y="{_emu(y)}"/>'
            f'<a:ext cx="{_emu(abs(x1 - x0))}" cy="0"/></a:xfrm>'
            '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{_emu(width_pt)}">{_fill(color)}'
            '<a:tailEnd type="triangle" w="med" len="med"/></a:ln></p:spPr></p:cxnSp>'
        )

    def segment(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        color: str,
        width_pt: float,
        *,
        name: str,
    ) -> None:
        """A straight stroke from ``(x0, y0)`` to ``(x1, y1)`` — column D's check is two of them
        (ADR-0524). DrawingML's ``line`` preset runs from the top-left to the bottom-right of its
        box, so the stroke is written left to right and a RISING one is that preset flipped
        vertically (never ``flipH``). Round caps and a round join, so two strokes that meet at a
        point leave no notch at the vertex."""
        if x1 < x0:
            x0, y0, x1, y1 = x1, y1, x0, y0
        flip = ' flipV="1"' if y1 < y0 else ""
        self.parts.append(
            f"<p:cxnSp><p:nvCxnSpPr>{self._cnv(name)}"
            "<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>"
            f'<a:xfrm{flip}><a:off x="{_emu(x0)}" y="{_emu(min(y0, y1))}"/>'
            f'<a:ext cx="{_emu(x1 - x0)}" cy="{_emu(abs(y1 - y0))}"/></a:xfrm>'
            '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{_emu(width_pt)}" cap="rnd">{_fill(color)}<a:round/></a:ln>'
            "</p:spPr></p:cxnSp>"
        )

    def text_runs(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        runs: list[tuple[str, str, bool]],
        size_pt: float,
        *,
        align: str = "l",
        anchor: str = "ctr",
        glow: bool = False,
        name: str,
        descr: str = "",
    ) -> None:
        """One paragraph of several runs — ``(text, colour, bold)`` each — so a label can carry
        its calendar-day delta in the slip or pull-in colour beside the item's own name.
        ``glow`` gives every run the slide-white text glow (:data:`_GLOW`)."""
        body = "".join(_run(t, size_pt, c, b, glow) for t, c, b in runs)
        self.parts.append(
            f"<p:sp><p:nvSpPr>{self._cnv(name, descr)}"
            '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/>'
            f'<a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" '
            f'anchor="{anchor}"/><a:lstStyle/><a:p><a:pPr algn="{align}"/>{body}</a:p>'
            "</p:txBody></p:sp>"
        )

    def vline(
        self,
        x: float,
        y0: float,
        y1: float,
        color: str,
        width_pt: float,
        *,
        dash: str | None = None,
        name: str,
    ) -> None:
        self.parts.append(
            f"<p:cxnSp><p:nvCxnSpPr>{self._cnv(name)}"
            "<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>"
            f'<a:xfrm><a:off x="{_emu(x)}" y="{_emu(y0)}"/><a:ext cx="0" cy="{_emu(y1 - y0)}"/>'
            '</a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f"{_ln(color, width_pt, dash)}</p:spPr></p:cxnSp>"
        )

    def hline(
        self, x0: float, x1: float, y: float, color: str, width_pt: float, *, name: str
    ) -> None:
        self.parts.append(
            f"<p:cxnSp><p:nvCxnSpPr>{self._cnv(name)}"
            "<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>"
            f'<a:xfrm><a:off x="{_emu(x0)}" y="{_emu(y)}"/><a:ext cx="{_emu(x1 - x0)}" cy="0"/>'
            '</a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f"{_ln(color, width_pt)}</p:spPr></p:cxnSp>"
        )

    def text(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        lines: list[str],
        size_pt: float,
        color: str,
        *,
        bold: bool = False,
        align: str = "l",
        anchor: str = "ctr",
        glow: bool = False,
        name: str,
        descr: str = "",
    ) -> None:
        paras = "".join(
            f'<a:p><a:pPr algn="{align}"/>{_run(line, size_pt, color, bold, glow)}</a:p>'
            for line in lines
        )
        self.parts.append(
            f"<p:sp><p:nvSpPr>{self._cnv(name, descr)}"
            '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/>'
            f'<a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" '
            f'anchor="{anchor}"/><a:lstStyle/>{paras}</p:txBody></p:sp>'
        )

    def freeform(
        self,
        points: list[tuple[float, float]],
        *,
        line: str | None,
        line_pt: float,
        fill: str | None = None,
        closed: bool = False,
        name: str,
    ) -> None:
        """One custom-geometry shape through ``points`` (slide points): an OPEN path is a line
        (a logic link's shaft, round-joined), a CLOSED one a filled polygon (its arrowhead). The
        path's own coordinates are the points less the shape's offset, in EMU, so the shape lands
        exactly where the page draws it. A degenerate extent (a straight vertical or horizontal
        leg) is widened to one EMU — a zero-size path box has no scale."""
        xs = [x for x, _y in points]
        ys = [y for _x, y in points]
        x0, y0 = min(xs), min(ys)
        w = max(_emu(max(xs) - x0), 1)
        h = max(_emu(max(ys) - y0), 1)
        path = "".join(
            ("<a:moveTo>" if i == 0 else "<a:lnTo>")
            + f'<a:pt x="{_emu(x - x0)}" y="{_emu(y - y0)}"/>'
            + ("</a:moveTo>" if i == 0 else "</a:lnTo>")
            for i, (x, y) in enumerate(points)
        ) + ("<a:close/>" if closed else "")
        ln = (
            f'<a:ln w="{_emu(line_pt)}" cap="rnd">{_fill(line)}<a:round/></a:ln>'
            if line
            else "<a:ln><a:noFill/></a:ln>"
        )
        fill_mode = "" if closed else ' fill="none"'
        self.parts.append(
            f"<p:sp><p:nvSpPr>{self._cnv(name)}"
            "<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>"
            f'<a:xfrm><a:off x="{_emu(x0)}" y="{_emu(y0)}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
            "<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>"
            '<a:rect l="0" t="0" r="r" b="b"/>'
            f'<a:pathLst><a:path w="{w}" h="{h}"{fill_mode}>{path}'
            f"</a:path></a:pathLst></a:custGeom>{_fill(fill)}{ln}</p:spPr></p:sp>"
        )

    def group(self, start: int, name: str) -> None:
        """Wrap every shape added since ``start`` (an index into :attr:`parts`) in ONE named
        group, so an operator moves, recolours or deletes a whole logic link as one object. The
        group's child space IS the slide's (``chOff``/``chExt`` equal ``off``/``ext``), so no
        child moves by being grouped."""
        inner = self.parts[start:]
        boxes = [
            (int(m[0]), int(m[1]), int(m[2]), int(m[3]))
            for part in inner
            for m in _XFRM_RE.findall(part)
        ]
        if not boxes:
            return
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        cx = max(max(b[0] + b[2] for b in boxes) - x0, 1)
        cy = max(max(b[1] + b[3] for b in boxes) - y0, 1)
        box = f'<a:off x="{x0}" y="{y0}"/><a:ext cx="{cx}" cy="{cy}"/>'
        del self.parts[start:]
        self.parts.append(
            f"<p:grpSp><p:nvGrpSpPr>{self._cnv(name)}"
            "<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr>"
            f'<a:xfrm>{box}<a:chOff x="{x0}" y="{y0}"/><a:chExt cx="{cx}" cy="{cy}"/></a:xfrm>'
            f"</p:grpSpPr>{''.join(inner)}</p:grpSp>"
        )

    def xml(self) -> str:
        return (
            _XML + f"<p:sld {_NS}><p:cSld><p:spTree>{_EMPTY_TREE}{''.join(self.parts)}"
            "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        )


def _package(slide: _Slide, product: str = PRODUCT, payload: bytes | None = None) -> bytes:
    """The zip. With ``payload`` (ADR-0544) three parts join the sixteen — the custom XML item,
    its properties, its rels — plus the item's content-type Override and the presentation's
    relationship to it; without one, exactly the sixteen parts written before, byte for byte."""
    carrying = payload is not None
    content_types = (
        _CONTENT_TYPES.replace("</Types>", _CUSTOM_XML_OVERRIDE + "</Types>")
        if carrying
        else _CONTENT_TYPES
    )
    presentation_rels = (
        _rels([*_PRESENTATION_REL_PAIRS, _CUSTOM_XML_REL]) if carrying else _PRESENTATION_RELS
    )
    parts = [
        ("[Content_Types].xml", content_types),
        ("_rels/.rels", _ROOT_RELS),
        ("docProps/core.xml", _core(product)),
        ("docProps/app.xml", _app(product)),
        ("ppt/presentation.xml", _PRESENTATION),
        ("ppt/_rels/presentation.xml.rels", presentation_rels),
        ("ppt/theme/theme1.xml", _THEME),
        ("ppt/presProps.xml", _PRES_PROPS),
        ("ppt/viewProps.xml", _VIEW_PROPS),
        ("ppt/tableStyles.xml", _TABLE_STYLES),
        ("ppt/slideMasters/slideMaster1.xml", _MASTER),
        ("ppt/slideMasters/_rels/slideMaster1.xml.rels", _MASTER_RELS),
        ("ppt/slideLayouts/slideLayout1.xml", _LAYOUT_PART),
        ("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _LAYOUT_RELS),
        ("ppt/slides/slide1.xml", slide.xml()),
        ("ppt/slides/_rels/slide1.xml.rels", _SLIDE_RELS),
    ]
    if payload is not None:
        parts += [
            ("customXml/item1.xml", _custom_xml_item(payload)),
            ("customXml/itemProps1.xml", _CUSTOM_XML_PROPS),
            ("customXml/_rels/item1.xml.rels", _CUSTOM_XML_ITEM_RELS),
        ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in parts:
            info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, content.encode("utf-8"))
    return buf.getvalue()


#: The logic-link ink in the slide's print palette (ADR-0543): the SHAFT in the secondary ink —
#: it runs UNDER the items — and the arrowhead and type tag in the primary ink, over them.
_SHAFT, _LINK = "384658", _INK


def _link_name(ln: PlacedLink) -> str:
    return f"{ln.pred_name} → {ln.succ_name} ({ln.kind})"


def _link_shafts(s: _Slide, links: list[PlacedLink]) -> None:
    """Every drawn logic link's SHAFT — a native open freeform, round-joined, the layout's own
    polyline — in a group of its own named ``Logic link: …``. Painted AFTER the lanes and BEFORE
    the first item, so every bar, diamond and label sits over it (ADR-0543): no halo, no dash,
    and no DrawingML line-end (the head is the layout's own polygon, :func:`_link_heads`)."""
    for ln in links:
        start = len(s.parts)
        what = _link_name(ln)
        s.freeform(ln.shaft, line=_SHAFT, line_pt=LINK_W, name=f"Logic link line: {what}")
        s.group(start, f"Logic link: {what}")


def _link_heads(s: _Slide, links: list[PlacedLink]) -> None:
    """Every drawn logic link's ARROWHEAD — the layout's own filled triangle, its tip on the
    successor's edge — and, for anything but Finish-to-Start, its type tag (glowing in the
    slide's white), grouped as ``Logic link arrowhead: …``. Painted AFTER the items' labels and
    BEFORE the data-date line, so a head is never under an item (ADR-0543)."""
    for ln in links:
        start = len(s.parts)
        what = _link_name(ln)
        s.freeform(
            ln.head, line=None, line_pt=0, fill=_LINK, closed=True, name=f"Logic link head: {what}"
        )
        if ln.tag:
            w = len(ln.tag) * ln.tag_pt * 0.62 + 1
            x = ln.tag_x if ln.tag_anchor == "start" else ln.tag_x - w
            s.text(
                x,
                ln.tag_y - ln.tag_pt,
                w,
                ln.tag_pt * 1.3,
                [ln.tag],
                ln.tag_pt,
                _LINK,
                bold=True,
                align="l" if ln.tag_anchor == "start" else "r",
                glow=True,
                name=f"Logic link type: {what}",
            )
        s.group(start, f"Logic link arrowhead: {what}")


def _settings_descr(settings: Mapping[str, object] | None) -> str:
    """The Title shape's alt text: the settings as sorted JSON after :data:`SETTINGS_DESCR`;
    ``""`` (no attribute) without settings."""
    return SETTINGS_DESCR + json.dumps(settings, sort_keys=True) if settings is not None else ""


def _item_descr(carrying: bool, **fields: object) -> str:
    """One item shape's alt text: its facts as sorted JSON after :data:`ITEM_DESCR`, written
    only when the deck carries settings (``carrying``) — the fallback is all-or-nothing, so a
    deck is never half a record."""
    return ITEM_DESCR + json.dumps(fields, sort_keys=True) if carrying else ""


def _risk_color(prob: str) -> str:
    return RISK_COLORS.get(prob, RISK_COLORS["unknown"])


def _risk_glyph(
    s: _Slide, x: float, y: float, ms: float, prob: str, *, name: str, descr: str = ""
) -> None:
    """The risk's triangle — apex at ``y - ms/2``, base at ``y + ms/2`` across ``x ± ms/2`` —
    filled in its probability's colour with the slide-white outline a milestone has."""
    s.shape(
        x - ms / 2,
        y - ms / 2,
        ms,
        ms,
        _risk_color(prob),
        prst=_RISK_PRST,
        line=_WHITE,
        name=name,
        descr=descr,
    )


def _risk_legend(s: _Slide, kind: str, x: float, cy: float) -> None:
    """A legend entry of kind ``risk-<prob>``: the small triangle, where a milestone's entry has
    its small diamond."""
    s.shape(x + 1.5, cy - 3.5, 7, 7, _risk_color(kind[5:]), prst=_RISK_PRST, name=f"Legend: {kind}")


#: The read-me's extra clause when a slide draws a risk (ADR-0544) — only then, so a slide
#: without one reads exactly as before.
_RISK_READ_ME = " · triangles = risks (colour = probability)"


def render_onepager_pptx(
    layout: Layout,
    *,
    marking: str,
    source: str,
    product: str = PRODUCT,
    payload: bytes | None = None,
    settings: Mapping[str, object] | None = None,
) -> bytes:
    """The layout as one 16:9 slide of native shapes. ``marking`` is the session's CUI banner
    text (top and bottom strips); ``source`` is the provenance footer. ``payload`` and
    ``settings`` (ADR-0544) make the deck a carrier of the session — see the module doc; both
    ``None`` writes the deck exactly as before."""
    lay = layout
    carrying = settings is not None
    s = _Slide()
    s.text(0, 1, lay.w, 8, [marking], 6, _CUI, bold=True, align="ctr", name="CUI marking (top)")
    s.text(
        0,
        lay.h - 9,
        lay.w,
        8,
        [marking],
        6,
        _CUI,
        bold=True,
        align="ctr",
        name="CUI marking (bottom)",
    )
    s.text(
        lay.lane_col_x0,
        lay.title_y - 15,
        760,
        18,
        [lay.title],
        16,
        _INK,
        bold=True,
        name="Title",
        descr=_settings_descr(settings),
    )
    if lay.subtitle:
        s.text(
            lay.lane_col_x0, lay.sub_y - 8, 760, 10, [lay.subtitle], 7.5, _MUTED, name="Subtitle"
        )
    top, bot = lay.year_y0, lay.lanes_y1
    for band in lay.years:
        s.shape(
            band.x0,
            top,
            band.x1 - band.x0,
            bot - top,
            _YEAR_SHADE[band.shade],
            name=f"Year band {band.label}",
        )
        if band.x1 - band.x0 > 18:
            s.text(
                band.x0,
                top,
                band.x1 - band.x0,
                lay.year_y1 - top,
                [band.label],
                8,
                _INK,
                bold=True,
                align="ctr",
                name=f"Year {band.label}",
            )
    for tick in lay.months:
        s.vline(
            tick.x, lay.year_y1, bot, _GRID, 0.4, dash="sysDot", name=f"Month line {tick.x:.0f}"
        )
        if tick.label:
            half = tick.label_x - tick.x
            s.text(
                tick.x,
                lay.year_y1,
                2 * half,
                lay.mon_y1 - lay.year_y1,
                [tick.label],
                lay.month_pt,
                _MUTED,
                align="ctr",
                name="Month label",
            )
    for band in lay.years:
        s.vline(band.x0, top, bot, _LINE, 0.6, name="Year line")
    s.vline(lay.x1, top, bot, _LINE, 0.6, name="Year line")
    s.hline(lay.lane_col_x0, lay.x1, lay.mon_y1, _LINE, 0.7, name="Header line")
    col_w = lay.lane_col_x1 - lay.lane_col_x0
    for lane in lay.lanes:
        hue = LANE_PALETTE[lane.color % len(LANE_PALETTE)]
        h = lane.y1 - lane.y0
        s.shape(
            lay.lane_col_x0,
            lane.y0,
            lay.x1 - lay.lane_col_x0,
            h,
            tint(hue, 0.07),
            name=f"Lane: {lane.name}",
        )
        s.shape(
            lay.lane_col_x0, lane.y0, col_w, h, tint(hue, 0.16), name=f"Lane label: {lane.name}"
        )
        s.shape(lay.lane_col_x0, lane.y0, 3, h, hue, name="Lane edge")
        s.text(
            lay.lane_col_x0 + 7,
            lane.y0,
            col_w - 8,
            h,
            lane.lines,
            lane.name_pt,
            _INK,
            bold=True,
            name=f"Lane name: {lane.name}",
        )
    _link_shafts(s, lay.links)  # under every item (ADR-0543)
    risks_drawn = False
    for p in lay.items:
        hue = LANE_PALETTE[lay.lanes[p.lane].color % len(LANE_PALETTE)]
        descr = _item_descr(
            carrying,
            lane=lay.lanes[p.lane].name,
            name=p.name,
            start=p.start,
            finish=p.finish,
            # the list's status column, when it has one; ``None`` says the sheet had none —
            # not "not complete" (the parser's own distinction); a risk has no such column
            complete=p.done if lay.status_label and p.kind != "risk" else None,
            key=p.key,
            kind=p.kind,
            prob=p.prob,
            impact=p.impact,
        )
        if p.kind == "risk":
            risks_drawn = True
            ms = p.ms or lay.ms
            _risk_glyph(s, p.x0, p.y, ms, p.prob, name=f"Risk: {p.name}", descr=descr)
        elif p.milestone:
            ms = p.ms or lay.ms  # its own size at the chart's edge (ADR-0540 review F1)
            s.shape(
                p.x0 - ms / 2,
                p.y - ms / 2,
                ms,
                ms,
                hue,
                prst="diamond",
                line=_WHITE,
                name=f"Milestone: {p.name}",
                descr=descr,
            )
        else:
            s.shape(
                p.x0,
                p.y - lay.bar_h / 2,
                p.x1 - p.x0,
                lay.bar_h,
                hue,
                prst="roundRect",
                line=_WHITE,
                name=f"Activity: {p.name}",
                descr=descr,
            )
        if p.done and p.done_x is not None:
            _done_badge(s, p.done_x, p.y, p.done_r, name=p.name)
        box_w, box_y = p.label_w + 4, p.y - lay.row_h / 2
        if p.kind == "risk" and p.impact:
            # the label with its impact after it in the probability's colour — the Compare
            # slide's delta run, in the Timeline's own ink (a risk is never inside a bar)
            runs: list[tuple[str, str, bool]] = [
                (p.label, _INK, False),
                (" " + p.impact, _risk_color(p.prob), True),
            ]
            at_end = p.label_anchor != "start"
            s.text_runs(
                p.label_x - box_w if at_end else p.label_x,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                align="r" if at_end else "l",
                glow=True,
                name=f"Label: {p.name}",
            )
        elif p.inside:
            s.text(
                p.label_x,
                box_y,
                box_w,
                lay.row_h,
                [p.label],
                lay.label_pt,
                _WHITE,
                bold=True,
                name=f"Label: {p.name}",
            )
        elif p.label_anchor == "start":
            s.text(
                p.label_x,
                box_y,
                box_w,
                lay.row_h,
                [p.label],
                lay.label_pt,
                _INK,
                glow=True,
                name=f"Label: {p.name}",
            )
        else:
            s.text(
                p.label_x - box_w,
                box_y,
                box_w,
                lay.row_h,
                [p.label],
                lay.label_pt,
                _INK,
                align="r",
                glow=True,
                name=f"Label: {p.name}",
            )
    _link_heads(s, lay.links)  # over every item, under the data-date line (ADR-0543)
    if lay.today_x is not None:
        s.vline(lay.today_x, top, bot, _TODAY, 1.5, name="Data date")
        if lay.today_label_anchor == "start":
            s.text(
                lay.today_label_x,
                lay.today_label_y - 6,
                90,
                8,
                [lay.today_label],
                6,
                _TODAY,
                bold=True,
                name="Data date label",
            )
        else:
            s.text(
                lay.today_label_x - 90,
                lay.today_label_y - 6,
                90,
                8,
                [lay.today_label],
                6,
                _TODAY,
                bold=True,
                align="r",
                name="Data date label",
            )
    s.hline(lay.lane_col_x0, lay.x1, lay.legend_y0, _LINE, 0.7, name="Legend line")
    lp = lay.legend_pt
    for e in lay.legend:
        cy = e.y - 2.5
        if e.kind == "activity":
            s.shape(e.x, cy - 2.5, 10, 5, _SYMBOL, prst="roundRect", name="Legend: activity")
        elif e.kind == "milestone":
            s.shape(e.x + 1.5, cy - 3.5, 7, 7, _SYMBOL, prst="diamond", name="Legend: milestone")
        elif e.kind == "done":
            s.shape(e.x + 2, cy - 3, 6, 6, _DONE, prst="ellipse", name="Legend: complete")
            vx, vy = e.x + 4.64, cy + 1.26
            s.segment(e.x + 3.5, cy + 0.06, vx, vy, _WHITE, 0.6, name="Done tick: legend")
            s.segment(vx, vy, e.x + 6.65, cy - 1.2, _WHITE, 0.6, name="Done tick: legend")
        elif e.kind == "today":
            s.vline(e.x + 5, cy - 4, cy + 4, _TODAY, 1.5, name="Legend: data date")
        elif e.kind == "link":
            s.freeform(
                [(e.x, cy), (e.x + 7.4, cy)], line=_SHAFT, line_pt=LINK_W, name="Legend: link"
            )
            s.freeform(
                [(e.x + 10, cy), (e.x + 7.4, cy - 1.3), (e.x + 7.4, cy + 1.3)],
                line=None,
                line_pt=0,
                fill=_LINK,
                closed=True,
                name="Legend: link head",
            )
        elif e.kind.startswith("risk-"):
            _risk_legend(s, e.kind, e.x, cy)
        else:
            hue = LANE_PALETTE[e.color % len(LANE_PALETTE)]
            s.shape(e.x, cy - 3, 10, 6, hue, prst="roundRect", name=f"Legend: {e.label}")
        s.text(
            e.x + 13, e.y - lp - 2, e.w, lp + 4, [e.label], lp, _INK, name=f"Legend text: {e.label}"
        )
    s.text(lay.lane_col_x0, lay.h - 18, 500, 8, [source], 5.5, _MUTED, name="Source")
    s.text(
        lay.x1 - 300,
        lay.h - 18,
        300,
        8,
        [
            "Timeline: months and years · bars = activities · diamonds = milestones · "
            "red line = data date" + (_RISK_READ_ME if risks_drawn else "")
        ],
        5.5,
        _MUTED,
        align="r",
        name="Read-me",
    )
    return _package(s, product, payload)


# ── the One-Pager COMPARE slide (ADR-0465) ────────────────────────────────────────────────────

#: Print colours for the delta encoding — a slip, a pull-in, a NEW tag, a REMOVED tag, a
#: DUPLICATE-NAME tag. The browser paints the same roles through --bad / --ok / --accent /
#: --muted / --warn.
_SLIP, _PULL, _NEW, _REMOVED, _DUP = "B3261E", "1E7B34", "1F6FEB", "6B7280", "B8860B"
_BADGE_INK = "FFFFFF"


def _tag_color(badge: str) -> str:
    return {"NEW": _NEW, "REMOVED": _REMOVED}.get(badge, _DUP)


#: Column D's check (ADR-0524): the page's ``--muted`` ("completed work", DESIGN-SYSTEM §1) in the
#: slide's print palette, with a white check — the SAME points ``onepager_compare.js`` draws.
_DONE = _MUTED


def _done_badge(s: _Slide, cx: float, cy: float, r: float, *, name: str) -> None:
    """A disc of radius ``r`` at ``(cx, cy)`` with a white check: a short stroke down to the
    vertex, a long one up to the right — the second is the rising, flipped one."""
    s.shape(cx - r, cy - r, 2 * r, 2 * r, _DONE, prst="ellipse", name=f"Done: {name}")
    w = max(0.35, r * 0.32)
    vx, vy = cx - 0.12 * r, cy + 0.42 * r
    s.segment(cx - 0.5 * r, cy + 0.02 * r, vx, vy, _WHITE, w, name=f"Done tick: {name}")
    s.segment(vx, vy, cx + 0.55 * r, cy - 0.4 * r, _WHITE, w, name=f"Done tick: {name}")


def render_onepager_compare_pptx(
    layout: CompareLayout,
    *,
    marking: str,
    source: str,
    product: str = PRODUCT,
    payload: bytes | None = None,
    settings: Mapping[str, object] | None = None,
) -> bytes:
    """The compare layout as one 16:9 slide of native shapes: the ADR-0446 slide with the PRIOR
    position as a dashed ghost, the CURRENT one solid, an arrow per moved finish carrying its
    calendar-day delta, NEW / REMOVED / DUPLICATE NAME tags, and the per-swimlane summary
    column. Same geometry as the page (one layout unit = one point = 12,700 EMU). ``payload``
    and ``settings`` as on :func:`render_onepager_pptx`; here every item record also carries
    its ``side`` (``prior`` on a ghost, ``current`` on a solid shape) and its ``status``."""
    lay = layout
    carrying = settings is not None
    s = _Slide()
    s.text(0, 1, lay.w, 8, [marking], 6, _CUI, bold=True, align="ctr", name="CUI marking (top)")
    s.text(
        0,
        lay.h - 9,
        lay.w,
        8,
        [marking],
        6,
        _CUI,
        bold=True,
        align="ctr",
        name="CUI marking (bottom)",
    )
    s.text(
        lay.lane_col_x0,
        lay.title_y - 15,
        760,
        18,
        [lay.title],
        16,
        _INK,
        bold=True,
        name="Title",
        descr=_settings_descr(settings),
    )
    if lay.subtitle:
        s.text(
            lay.lane_col_x0, lay.sub_y - 8, 900, 10, [lay.subtitle], 7.5, _MUTED, name="Subtitle"
        )
    top, bot = lay.year_y0, lay.lanes_y1
    for band in lay.years:
        s.shape(
            band.x0,
            top,
            band.x1 - band.x0,
            bot - top,
            _YEAR_SHADE[band.shade],
            name=f"Year band {band.label}",
        )
        if band.x1 - band.x0 > 18:
            s.text(
                band.x0,
                top,
                band.x1 - band.x0,
                lay.year_y1 - top,
                [band.label],
                8,
                _INK,
                bold=True,
                align="ctr",
                name=f"Year {band.label}",
            )
    for tick in lay.months:
        s.vline(
            tick.x, lay.year_y1, bot, _GRID, 0.4, dash="sysDot", name=f"Month line {tick.x:.0f}"
        )
        if tick.label:
            half = tick.label_x - tick.x
            s.text(
                tick.x,
                lay.year_y1,
                2 * half,
                lay.mon_y1 - lay.year_y1,
                [tick.label],
                lay.month_pt,
                _MUTED,
                align="ctr",
                name="Month label",
            )
    for band in lay.years:
        s.vline(band.x0, top, bot, _LINE, 0.6, name="Year line")
    s.vline(lay.x1, top, bot, _LINE, 0.6, name="Year line")
    s.hline(lay.lane_col_x0, lay.summary_x1, lay.mon_y1, _LINE, 0.7, name="Header line")
    s.text(
        lay.summary_x0 + 2,
        lay.year_y1,
        lay.summary_x1 - lay.summary_x0 - 2,
        lay.mon_y1 - lay.year_y1,
        ["CHANGE SUMMARY"],
        5.5,
        _MUTED,
        bold=True,
        name="Summary header",
    )
    col_w = lay.lane_col_x1 - lay.lane_col_x0
    for lane in lay.lanes:
        hue = LANE_PALETTE[lane.color % len(LANE_PALETTE)]
        h = lane.y1 - lane.y0
        s.shape(
            lay.lane_col_x0,
            lane.y0,
            lay.x1 - lay.lane_col_x0,
            h,
            tint(hue, 0.07),
            name=f"Lane: {lane.name}",
        )
        s.shape(
            lay.lane_col_x0, lane.y0, col_w, h, tint(hue, 0.16), name=f"Lane label: {lane.name}"
        )
        s.shape(lay.lane_col_x0, lane.y0, 3, h, hue, name="Lane edge")
        s.text(
            lay.lane_col_x0 + 7,
            lane.y0,
            col_w - 8,
            h,
            lane.lines,
            lane.name_pt,
            _INK,
            bold=True,
            name=f"Lane name: {lane.name}",
        )
    for box in lay.summaries:
        hue = LANE_PALETTE[lay.lanes[box.lane].color % len(LANE_PALETTE)]
        s.shape(
            box.x0,
            box.y0,
            box.x1 - box.x0,
            box.y1 - box.y0,
            tint(hue, 0.10),
            name=f"Summary: {lay.lanes[box.lane].name}",
        )
        s.text(
            box.x0 + 2.5,
            box.y0,
            box.x1 - box.x0 - 4,
            box.y1 - box.y0,
            box.lines,
            box.pt,
            _INK,
            name=f"Summary text: {lay.lanes[box.lane].name}",
        )
    _link_shafts(s, lay.links)  # under every item (ADR-0543)
    risks_drawn = False
    for p in lay.items:
        hue = LANE_PALETTE[lay.lanes[p.lane].color % len(LANE_PALETTE)]
        lane_name = lay.lanes[p.lane].name
        if p.ghost_x0 is not None and p.ghost_x1 is not None:
            # the PRIOR list's row: its dates; its completion is not on this layout (column
            # D's check is the CURRENT list's), so ``None`` — never a guess
            ghost_descr = _item_descr(
                carrying,
                side="prior",
                status=p.status,
                lane=lane_name,
                name=p.name,
                start=p.prior_start,
                finish=p.prior_finish,
                complete=None,
                key=p.key,
                kind=p.kind,
                prob=p.prob,
                impact=p.impact,
            )
            if p.ghost_milestone:
                gms = p.ghost_ms or lay.ms
                s.shape(
                    p.ghost_x0 - gms / 2,
                    p.y - gms / 2,
                    gms,
                    gms,
                    None,
                    prst="diamond",
                    line=hue,
                    line_pt=0.75,
                    dash="dash",
                    name=f"Prior milestone: {p.name}",
                    descr=ghost_descr,
                )
            else:
                s.shape(
                    p.ghost_x0,
                    p.y - lay.bar_h / 2,
                    p.ghost_x1 - p.ghost_x0,
                    lay.bar_h,
                    None,
                    prst="roundRect",
                    line=hue,
                    line_pt=0.75,
                    dash="dash",
                    name=f"Prior activity: {p.name}",
                    descr=ghost_descr,
                )
        if p.arrow_x0 is not None and p.arrow_x1 is not None:
            slip = p.status == "slipped"
            s.arrow(
                p.arrow_x0,
                p.arrow_x1,
                p.arrow_y,
                _SLIP if slip else _PULL,
                0.9,
                name=f"{'Slip' if slip else 'Pull-in'}: {p.name}",
            )
        if p.x0 is not None and p.x1 is not None:
            descr = _item_descr(
                carrying,
                side="current",
                status=p.status,
                lane=lane_name,
                name=p.name,
                start=p.current_start,
                finish=p.current_finish,
                complete=p.done if lay.status_label and p.kind != "risk" else None,
                key=p.key,
                kind=p.kind,
                prob=p.prob,
                impact=p.impact,
            )
            if p.kind == "risk":
                risks_drawn = True
                _risk_glyph(
                    s, p.x0, p.y, p.ms or lay.ms, p.prob, name=f"Risk: {p.name}", descr=descr
                )
            elif p.milestone:
                ms = p.ms or lay.ms
                s.shape(
                    p.x0 - ms / 2,
                    p.y - ms / 2,
                    ms,
                    ms,
                    hue,
                    prst="diamond",
                    line=_WHITE,
                    name=f"Milestone: {p.name}",
                    descr=descr,
                )
            else:
                s.shape(
                    p.x0,
                    p.y - lay.bar_h / 2,
                    p.x1 - p.x0,
                    lay.bar_h,
                    hue,
                    prst="roundRect",
                    line=_WHITE,
                    name=f"Activity: {p.name}",
                    descr=descr,
                )
        if p.done and p.done_x is not None:
            _done_badge(s, p.done_x, p.y, p.done_r, name=p.name)
        delta_color = (
            _risk_color(p.prob)
            if p.kind == "risk"
            else {"slipped": _SLIP, "pulled in": _PULL}.get(p.status, _DUP)
        )
        ink = _WHITE if p.inside else _INK
        runs: list[tuple[str, str, bool]] = [(p.label, ink, bool(p.inside))]
        if p.delta:
            runs.append((" " + p.delta, delta_color, True))
        box_w, box_y = p.label_w + 4, p.y - lay.row_h / 2
        if p.label_anchor == "end":
            right = p.label_x - (p.badge_w + 2 if p.badge else 0.0)
            s.text_runs(
                right - box_w,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                align="r",
                glow=not p.inside,
                name=f"Label: {p.name}",
            )
        else:
            s.text_runs(
                p.label_x,
                box_y,
                box_w,
                lay.row_h,
                runs,
                lay.label_pt,
                glow=not p.inside,
                name=f"Label: {p.name}",
            )
        if p.badge:
            s.shape(
                p.badge_x,
                p.y - lay.label_pt * 0.6,
                p.badge_w,
                lay.label_pt * 1.2,
                _tag_color(p.badge),
                prst="roundRect",
                name=f"Tag: {p.badge} — {p.name}",
            )
            s.text(
                p.badge_x,
                p.y - lay.label_pt * 0.6,
                p.badge_w,
                lay.label_pt * 1.2,
                [p.badge],
                lay.label_pt,
                _BADGE_INK,
                bold=True,
                align="ctr",
                name=f"Tag text: {p.badge} — {p.name}",
            )
    _link_heads(s, lay.links)  # over every item, under the data-date line (ADR-0543)
    if lay.today_x is not None:
        s.vline(lay.today_x, top, bot, _TODAY, 1.5, name="Data date")
        if lay.today_label_anchor == "start":
            s.text(
                lay.today_label_x,
                lay.today_label_y - 6,
                90,
                8,
                [lay.today_label],
                6,
                _TODAY,
                bold=True,
                name="Data date label",
            )
        else:
            s.text(
                lay.today_label_x - 90,
                lay.today_label_y - 6,
                90,
                8,
                [lay.today_label],
                6,
                _TODAY,
                bold=True,
                align="r",
                name="Data date label",
            )
    s.hline(lay.lane_col_x0, lay.summary_x1, lay.legend_y0, _LINE, 0.7, name="Legend line")
    lp = lay.legend_pt
    for e in lay.legend:
        cy = e.y - 2.5
        if e.kind == "activity":
            s.shape(e.x, cy - 2.5, 10, 5, _SYMBOL, prst="roundRect", name="Legend: current")
        elif e.kind in ("ghost", "removed"):
            s.shape(
                e.x,
                cy - 2.5,
                10,
                5,
                None,
                prst="roundRect",
                line=_SYMBOL,
                line_pt=0.75,
                dash="dash",
                name=f"Legend: {e.kind}",
            )
        elif e.kind == "slip":
            s.arrow(e.x, e.x + 10, cy, _SLIP, 0.9, name="Legend: slip")
        elif e.kind == "pull":
            s.arrow(e.x + 10, e.x, cy, _PULL, 0.9, name="Legend: pull-in")
        elif e.kind == "new":
            s.shape(e.x, cy - 3, 10, 6, _NEW, prst="roundRect", name="Legend: new")
        elif e.kind == "done":
            s.shape(e.x + 2, cy - 3, 6, 6, _DONE, prst="ellipse", name="Legend: complete")
            vx, vy = e.x + 4.64, cy + 1.26
            s.segment(e.x + 3.5, cy + 0.06, vx, vy, _WHITE, 0.6, name="Done tick: legend")
            s.segment(vx, vy, e.x + 6.65, cy - 1.2, _WHITE, 0.6, name="Done tick: legend")
        elif e.kind == "today":
            s.vline(e.x + 5, cy - 4, cy + 4, _TODAY, 1.5, name="Legend: data date")
        elif e.kind == "link":
            s.freeform(
                [(e.x, cy), (e.x + 7.4, cy)], line=_SHAFT, line_pt=LINK_W, name="Legend: link"
            )
            s.freeform(
                [(e.x + 10, cy), (e.x + 7.4, cy - 1.3), (e.x + 7.4, cy + 1.3)],
                line=None,
                line_pt=0,
                fill=_LINK,
                closed=True,
                name="Legend: link head",
            )
        elif e.kind.startswith("risk-"):
            _risk_legend(s, e.kind, e.x, cy)
        else:
            hue = LANE_PALETTE[e.color % len(LANE_PALETTE)]
            s.shape(e.x, cy - 3, 10, 6, hue, prst="roundRect", name=f"Legend: {e.label}")
        s.text(
            e.x + 13, e.y - lp - 2, e.w, lp + 4, [e.label], lp, _INK, name=f"Legend text: {e.label}"
        )
    s.text(lay.lane_col_x0, lay.h - 18, 520, 8, [source], 5.5, _MUTED, name="Source")
    s.text(
        lay.summary_x1 - 380,
        lay.h - 18,
        380,
        8,
        [
            "Solid = current (unchanged: once) · ghost = prior · arrow = finish moved "
            "(\u00b1N cal d) · check = complete (col. D) · red line = data date"
            + (_RISK_READ_ME if risks_drawn else "")
        ],
        5.5,
        _MUTED,
        align="r",
        name="Read-me",
    )
    return _package(s, product, payload)
