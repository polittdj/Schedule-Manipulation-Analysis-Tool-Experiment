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
"""

from __future__ import annotations

import io
import zipfile

from schedule_forensics.reports.onepager import Layout
from schedule_forensics.reports.onepager_compare import CompareLayout

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
_YEAR_SHADE = ("F5F7FA", "EAEEF3")


def _esc(value: str) -> str:
    """XML-escape text content (this module only WRITES XML; nothing is parsed)."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    '<Override PartName="/docProps/core.xml" '
    'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    f'<Override PartName="/docProps/app.xml" ContentType="{_CT_BASE}extended-properties+xml"/>'
    "</Types>"
)
_ROOT_RELS = _rels([("officeDocument", "ppt/presentation.xml")])
_PRESENTATION = (
    _XML + f'<p:presentation {_NS} saveSubsetFonts="1">'
    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
    '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>'
    f'<p:sldSz cx="{_SLIDE_W}" cy="{_SLIDE_H}"/><p:notesSz cx="6858000" cy="9144000"/>'
    "</p:presentation>"
)
_PRESENTATION_RELS = _rels(
    [
        ("slideMaster", "slideMasters/slideMaster1.xml"),
        ("slide", "slides/slide1.xml"),
        ("theme", "theme/theme1.xml"),
    ]
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
_CORE = (
    _XML + "<cp:coreProperties "
    'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:title>One-Pager</dc:title><dc:creator>POLARIS²</dc:creator></cp:coreProperties>"
)
_APP = (
    _XML + "<Properties "
    'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
    "<Application>POLARIS²</Application><Slides>1</Slides></Properties>"
)


def _emu(pt: float) -> int:
    return round(pt * _EMU_PER_PT)


def _fill(color: str | None) -> str:
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>' if color else "<a:noFill/>"


def _ln(color: str | None, width_pt: float, dash: str | None = None) -> str:
    if not color:
        return "<a:ln><a:noFill/></a:ln>"
    dash_xml = f'<a:prstDash val="{dash}"/>' if dash else ""
    return f'<a:ln w="{_emu(width_pt)}">{_fill(color)}{dash_xml}</a:ln>'


def _run(text: str, size_pt: float, color: str, bold: bool) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:r><a:rPr lang="en-US" sz="{round(size_pt * 100)}"{b} dirty="0">'
        f'{_fill(color)}<a:latin typeface="Calibri"/></a:rPr><a:t>{_esc(text)}</a:t></a:r>'
    )


class _Slide:
    """Accumulates the ``<p:spTree>`` children of the one slide, in paint order."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self._next_id = 1

    def _id(self) -> int:
        self._next_id += 1
        return self._next_id

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
    ) -> None:
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{_esc(name)}"/>'
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
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{self._id()}" name="{_esc(name)}"/>'
            "<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>"
            f'<a:xfrm{flip}><a:off x="{_emu(min(x0, x1))}" y="{_emu(y)}"/>'
            f'<a:ext cx="{_emu(abs(x1 - x0))}" cy="0"/></a:xfrm>'
            '<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{_emu(width_pt)}">{_fill(color)}'
            '<a:tailEnd type="triangle" w="med" len="med"/></a:ln></p:spPr></p:cxnSp>'
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
        name: str,
    ) -> None:
        """One paragraph of several runs — ``(text, colour, bold)`` each — so a label can carry
        its calendar-day delta in the slip or pull-in colour beside the item's own name."""
        body = "".join(_run(t, size_pt, c, b) for t, c, b in runs)
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{_esc(name)}"/>'
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
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{self._id()}" name="{_esc(name)}"/>'
            "<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr><p:spPr>"
            f'<a:xfrm><a:off x="{_emu(x)}" y="{_emu(y0)}"/><a:ext cx="0" cy="{_emu(y1 - y0)}"/>'
            '</a:xfrm><a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f"{_ln(color, width_pt, dash)}</p:spPr></p:cxnSp>"
        )

    def hline(
        self, x0: float, x1: float, y: float, color: str, width_pt: float, *, name: str
    ) -> None:
        self.parts.append(
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{self._id()}" name="{_esc(name)}"/>'
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
        name: str,
    ) -> None:
        paras = "".join(
            f'<a:p><a:pPr algn="{align}"/>{_run(line, size_pt, color, bold)}</a:p>'
            for line in lines
        )
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{_esc(name)}"/>'
            '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/>'
            f'<a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" '
            f'anchor="{anchor}"/><a:lstStyle/>{paras}</p:txBody></p:sp>'
        )

    def xml(self) -> str:
        return (
            _XML + f"<p:sld {_NS}><p:cSld><p:spTree>{_EMPTY_TREE}{''.join(self.parts)}"
            "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        )


def _package(slide: _Slide) -> bytes:
    parts = [
        ("[Content_Types].xml", _CONTENT_TYPES),
        ("_rels/.rels", _ROOT_RELS),
        ("docProps/core.xml", _CORE),
        ("docProps/app.xml", _APP),
        ("ppt/presentation.xml", _PRESENTATION),
        ("ppt/_rels/presentation.xml.rels", _PRESENTATION_RELS),
        ("ppt/theme/theme1.xml", _THEME),
        ("ppt/slideMasters/slideMaster1.xml", _MASTER),
        ("ppt/slideMasters/_rels/slideMaster1.xml.rels", _MASTER_RELS),
        ("ppt/slideLayouts/slideLayout1.xml", _LAYOUT_PART),
        ("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _LAYOUT_RELS),
        ("ppt/slides/slide1.xml", slide.xml()),
        ("ppt/slides/_rels/slide1.xml.rels", _SLIDE_RELS),
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in parts:
            info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, content.encode("utf-8"))
    return buf.getvalue()


def render_onepager_pptx(layout: Layout, *, marking: str, source: str) -> bytes:
    """The layout as one 16:9 slide of native shapes. ``marking`` is the session's CUI banner
    text (top and bottom strips); ``source`` is the provenance footer."""
    lay = layout
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
        lay.lane_col_x0, lay.title_y - 15, 760, 18, [lay.title], 16, _INK, bold=True, name="Title"
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
    for p in lay.items:
        hue = LANE_PALETTE[lay.lanes[p.lane].color % len(LANE_PALETTE)]
        if p.milestone:
            s.shape(
                p.x0 - lay.ms / 2,
                p.y - lay.ms / 2,
                lay.ms,
                lay.ms,
                hue,
                prst="diamond",
                line=_WHITE,
                name=f"Milestone: {p.name}",
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
            )
        box_w, box_y = p.label_w + 4, p.y - lay.row_h / 2
        if p.inside:
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
                name=f"Label: {p.name}",
            )
    if lay.today_x is not None:
        s.vline(lay.today_x, top, bot, _TODAY, 1.5, name="Today")
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
                name="Today label",
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
                name="Today label",
            )
    s.hline(lay.lane_col_x0, lay.x1, lay.legend_y0, _LINE, 0.7, name="Legend line")
    lp = lay.legend_pt
    for e in lay.legend:
        cy = e.y - 2.5
        if e.kind == "activity":
            s.shape(e.x, cy - 2.5, 10, 5, _SYMBOL, prst="roundRect", name="Legend: activity")
        elif e.kind == "milestone":
            s.shape(e.x + 1.5, cy - 3.5, 7, 7, _SYMBOL, prst="diamond", name="Legend: milestone")
        elif e.kind == "today":
            s.vline(e.x + 5, cy - 4, cy + 4, _TODAY, 1.5, name="Legend: today")
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
            "red line = today"
        ],
        5.5,
        _MUTED,
        align="r",
        name="Read-me",
    )
    return _package(s)


# ── the One-Pager COMPARE slide (ADR-0465) ────────────────────────────────────────────────────

#: Print colours for the delta encoding — a slip, a pull-in, a NEW tag, a REMOVED tag, a
#: DUPLICATE-NAME tag. The browser paints the same roles through --bad / --ok / --accent /
#: --muted / --warn.
_SLIP, _PULL, _NEW, _REMOVED, _DUP = "B3261E", "1E7B34", "1F6FEB", "6B7280", "B8860B"
_BADGE_INK = "FFFFFF"


def _tag_color(badge: str) -> str:
    return {"NEW": _NEW, "REMOVED": _REMOVED}.get(badge, _DUP)


def render_onepager_compare_pptx(layout: CompareLayout, *, marking: str, source: str) -> bytes:
    """The compare layout as one 16:9 slide of native shapes: the ADR-0446 slide with the PRIOR
    position as a dashed ghost, the CURRENT one solid, an arrow per moved finish carrying its
    calendar-day delta, NEW / REMOVED / DUPLICATE NAME tags, and the per-swimlane summary
    column. Same geometry as the page (one layout unit = one point = 12,700 EMU)."""
    lay = layout
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
        lay.lane_col_x0, lay.title_y - 15, 760, 18, [lay.title], 16, _INK, bold=True, name="Title"
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
    for p in lay.items:
        hue = LANE_PALETTE[lay.lanes[p.lane].color % len(LANE_PALETTE)]
        if p.ghost_x0 is not None and p.ghost_x1 is not None:
            if p.ghost_milestone:
                s.shape(
                    p.ghost_x0 - lay.ms / 2,
                    p.y - lay.ms / 2,
                    lay.ms,
                    lay.ms,
                    None,
                    prst="diamond",
                    line=hue,
                    line_pt=0.75,
                    dash="dash",
                    name=f"Prior milestone: {p.name}",
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
            if p.milestone:
                s.shape(
                    p.x0 - lay.ms / 2,
                    p.y - lay.ms / 2,
                    lay.ms,
                    lay.ms,
                    hue,
                    prst="diamond",
                    line=_WHITE,
                    name=f"Milestone: {p.name}",
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
                )
        delta_color = {"slipped": _SLIP, "pulled in": _PULL}.get(p.status, _DUP)
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
                name=f"Label: {p.name}",
            )
        else:
            s.text_runs(
                p.label_x, box_y, box_w, lay.row_h, runs, lay.label_pt, name=f"Label: {p.name}"
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
    if lay.today_x is not None:
        s.vline(lay.today_x, top, bot, _TODAY, 1.5, name="Today")
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
                name="Today label",
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
                name="Today label",
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
        elif e.kind == "today":
            s.vline(e.x + 5, cy - 4, cy + 4, _TODAY, 1.5, name="Legend: today")
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
            "Solid = current · dashed ghost = prior · arrow = the finish moved (+N cal d slipped, "
            "\u2212N pulled in) · NEW / REMOVED tags · red line = today"
        ],
        5.5,
        _MUTED,
        align="r",
        name="Read-me",
    )
    return _package(s)
