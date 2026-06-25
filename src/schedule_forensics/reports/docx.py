"""Minimal, dependency-free .docx writer (M18 — every table exportable to Word).

A ``.docx`` is a zip of XML parts; this emits the smallest valid subset Word accepts
(content types, package relationships, ``word/document.xml``) using direct run
formatting — no styles part needed. The block API (:class:`Heading`,
:class:`Paragraph`, :class:`DocTable`) is deliberately generic: the narrative
Diagnostic Brief renders through the same primitives as the plain table exports.
Byte-deterministic (fixed zip timestamps, fixed part order).
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.reports.tables import TableSet


def _esc(value: str) -> str:
    """XML-escape text content (this module only WRITES XML; nothing is parsed)."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/header1.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
    '<Override PartName="/word/footer1.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
# DrawingML namespaces for the vendor-free inline vector charts (ADR-0124). wp/a are the ECMA
# OOXML URIs; wpg/wps are the Microsoft-2010 shape-group vocabulary Word renders natively. Declared
# once on the document root so chart runs don't repeat them. No new ZIP part -> determinism intact.
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_WPG = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_EMU_PER_INCH = 914400

#: CUI marking applied to every page of every Word export (Law 1 — every exported artifact
#: carries its handling caveat). A header (top of page) + footer (bottom of page) part, each
#: referenced from ``<w:sectPr>``, so the banner repeats on every printed page regardless of
#: how the body flows. Separate parts (not body paragraphs) → the document body and the tests
#: that read it are untouched.
_CUI_BANNER = "CONTROLLED UNCLASSIFIED INFORMATION (CUI)"

#: Relationships for the header/footer parts referenced from the document body's sectPr.
_DOCUMENT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type="{_R}/header" Target="header1.xml"/>'
    f'<Relationship Id="rId2" Type="{_R}/footer" Target="footer1.xml"/>'
    "</Relationships>"
)


def _cui_part(tag: str) -> str:
    """A header (``hdr``) or footer (``ftr``) part holding the centered, bold CUI banner."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:{tag} xmlns:w="{_W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{_esc(_CUI_BANNER)}</w:t>'
        f"</w:r></w:p></w:{tag}>"
    )


@dataclass(frozen=True)
class Heading:
    """A heading block; level 0 is the document title."""

    text: str
    level: int = 1


@dataclass(frozen=True)
class Paragraph:
    """Body prose. ``bold_lead`` renders ``lead`` bold ahead of the text (citations,
    verdict phrases); ``italic`` styles the whole paragraph (disclaimers)."""

    text: str
    lead: str = ""
    italic: bool = False


@dataclass(frozen=True)
class DocTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class Chart:
    """A vendor-free chart embedded natively in the .docx (ADR-0124). ``kind='vector'`` draws an
    inline DrawingML shape group — ``polylines`` (S-curve / axis), ``rects`` (histogram & tornado
    bars), and ``dots`` (percentile markers) — all positioned in a 0..1 plot-fraction space (x
    right, y up; the renderer inverts y). ``kind='matrix'`` emits a shaded ``w:tbl`` (the 5x5 grid),
    the most reliably-rendered primitive. No image part: the drawing lives inline in document.xml so
    byte-determinism is preserved."""

    kind: str = "vector"
    width_in: float = 6.2
    height_in: float = 2.6
    # each polyline: (points in 0..1 plot fraction, stroke hex, stroke width in EMU)
    polylines: tuple[tuple[tuple[tuple[float, float], ...], str, int], ...] = ()
    # each rect (bar): (x0, y0, x1, y1) in 0..1 plot fraction + fill hex
    rects: tuple[tuple[float, float, float, float, str], ...] = ()
    # each dot: (x, y) in 0..1 plot fraction + fill hex
    dots: tuple[tuple[float, float, str], ...] = ()
    # matrix grid: rows top->bottom of (cell text, fill hex, text-colour hex)
    grid: tuple[tuple[tuple[str, str, str], ...], ...] = ()


Block = Heading | Paragraph | DocTable | Chart

#: Half-point font sizes per heading level (0 = title).
_HEADING_SIZES = {0: 40, 1: 30, 2: 25, 3: 23}


def render_document(blocks: Sequence[Block]) -> bytes:
    """Serialize blocks as a deterministic .docx (bytes)."""
    body = "".join(_block_xml(b, i) for i, b in enumerate(blocks))
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document xmlns:w="{_W}" xmlns:r="{_R}" xmlns:wp="{_WP}" xmlns:a="{_A}" '
        f'xmlns:wpg="{_WPG}" xmlns:wps="{_WPS}"><w:body>{body}'
        '<w:sectPr><w:headerReference w:type="default" r:id="rId1"/>'
        '<w:footerReference w:type="default" r:id="rId2"/>'
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"/></w:sectPr>'
        "</w:body></w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in (
            ("[Content_Types].xml", _CONTENT_TYPES),
            ("_rels/.rels", _ROOT_RELS),
            ("word/_rels/document.xml.rels", _DOCUMENT_RELS),
            ("word/document.xml", document),
            ("word/header1.xml", _cui_part("hdr")),
            ("word/footer1.xml", _cui_part("ftr")),
        ):
            info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, content)
    return buf.getvalue()


def render_docx(tableset: TableSet) -> bytes:
    """A plain Word export of a :class:`TableSet`: title + per-table heading + table."""
    blocks: list[Block] = [Heading(tableset.title, level=0)]
    for table in tableset.tables:
        blocks.append(Heading(table.title, level=1))
        blocks.append(DocTable(table.headers, table.rows))
    return render_document(blocks)


def _block_xml(block: Block, idx: int = 0) -> str:
    if isinstance(block, Chart):
        return _chart_xml(block, idx + 1)  # docPr id must be unique per drawing
    if isinstance(block, Heading):
        size = _HEADING_SIZES.get(block.level, 22)
        return (
            '<w:p><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:sz w:val="{size}"/></w:rPr>'
            f'<w:t xml:space="preserve">{_esc(block.text)}</w:t></w:r></w:p>'
        )
    if isinstance(block, Paragraph):
        italic = "<w:i/>" if block.italic else ""
        lead = (
            f"<w:r><w:rPr><w:b/>{italic}</w:rPr>"
            f'<w:t xml:space="preserve">{_esc(block.lead)} </w:t></w:r>'
            if block.lead
            else ""
        )
        return (
            '<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>'
            f"{lead}<w:r><w:rPr>{italic}</w:rPr>"
            f'<w:t xml:space="preserve">{_esc(block.text)}</w:t></w:r></w:p>'
        )
    return _table_xml(block)


def _table_xml(table: DocTable) -> str:
    borders = (
        "<w:tblBorders>"
        + "".join(
            f'<w:{side} w:val="single" w:sz="4" w:color="999999"/>'
            for side in ("top", "left", "bottom", "right", "insideH", "insideV")
        )
        + "</w:tblBorders>"
    )
    head = "<w:tr>" + "".join(_cell_xml(h, bold=True) for h in table.headers) + "</w:tr>"
    rows = "".join(
        "<w:tr>"
        + "".join(_cell_xml(value, bold=False) for value in _padded(row, len(table.headers)))
        + "</w:tr>"
        for row in table.rows
    )
    return (
        f'<w:tbl><w:tblPr>{borders}<w:tblW w:w="0" w:type="auto"/></w:tblPr>{head}{rows}</w:tbl>'
        "<w:p/>"
    )


def _cell_xml(value: object, *, bold: bool) -> str:
    text = "" if value is None else str(value)
    bold_tag = "<w:b/>" if bold else ""
    rpr = f'<w:rPr>{bold_tag}<w:sz w:val="18"/></w:rPr>'
    return (
        '<w:tc><w:tcPr><w:tcMar><w:left w:w="80" w:type="dxa"/>'
        '<w:right w:w="80" w:type="dxa"/></w:tcMar></w:tcPr>'
        f'<w:p><w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p></w:tc>'
    )


def _padded(row: tuple[object, ...], width: int) -> tuple[object, ...]:
    return row + (None,) * (width - len(row)) if len(row) < width else row[:width]


# --- vendor-free inline vector charts (ADR-0124) -------------------------------------------------


def _emu(inches: float) -> int:
    """Inches -> EMU (914400 per inch), the DrawingML unit. round() gives a deterministic int."""
    return round(inches * _EMU_PER_INCH)


def _xfrm(off_x: int, off_y: int, ext_w: int, ext_h: int) -> str:
    return f'<a:xfrm><a:off x="{off_x}" y="{off_y}"/><a:ext cx="{ext_w}" cy="{ext_h}"/></a:xfrm>'


def _ln(color: str, width_emu: int, *, fill_none: bool = False) -> str:
    cap = ' cap="rnd"' if fill_none else ""
    fill = f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
    return f'<a:ln w="{width_emu}"{cap}>{fill}</a:ln>'


def _poly_shape(
    off_x: int,
    off_y: int,
    ext_w: int,
    ext_h: int,
    pts: Sequence[tuple[int, int]],
    color: str,
    w: int,
) -> str:
    """An open polyline (custGeom) — the S-curve and the axis. ``pts`` are LOCAL EMU within
    ``(ext_w, ext_h)``, origin top-left, +y down. ``fill="none"`` renders the stroke only."""
    moves = "".join(
        (
            f'<a:moveTo><a:pt x="{x}" y="{y}"/></a:moveTo>'
            if i == 0
            else f'<a:lnTo><a:pt x="{x}" y="{y}"/></a:lnTo>'
        )
        for i, (x, y) in enumerate(pts)
    )
    return (
        f"<wps:wsp><wps:cNvSpPr/><wps:spPr>{_xfrm(off_x, off_y, ext_w, ext_h)}"
        f'<a:custGeom><a:avLst/><a:gdLst/><a:rect l="0" t="0" r="{ext_w}" b="{ext_h}"/>'
        f'<a:pathLst><a:path w="{ext_w}" h="{ext_h}" fill="none">{moves}</a:path></a:pathLst>'
        f"</a:custGeom><a:noFill/>{_ln(color, w, fill_none=True)}</wps:spPr><wps:bodyPr/></wps:wsp>"
    )


def _rect_shape(off_x: int, off_y: int, ext_w: int, ext_h: int, fill: str) -> str:
    """A filled rectangle (preset geometry) — histogram & tornado bars, and shaded cells."""
    return (
        f"<wps:wsp><wps:cNvSpPr/><wps:spPr>{_xfrm(off_x, off_y, max(1, ext_w), max(1, ext_h))}"
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
        f"{_ln('33414E', 3175)}</wps:spPr><wps:bodyPr/></wps:wsp>"
    )


def _ellipse_shape(cx: int, cy: int, r: int, fill: str) -> str:
    return (
        f"<wps:wsp><wps:cNvSpPr/><wps:spPr>{_xfrm(cx - r, cy - r, 2 * r, 2 * r)}"
        f'<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></wps:spPr><wps:bodyPr/></wps:wsp>'
    )


def _chart_xml(chart: Chart, draw_id: int) -> str:
    if chart.kind == "matrix":
        return _matrix_table_xml(chart.grid)
    w_emu = _emu(chart.width_in)
    h_emu = _emu(chart.height_in)
    ml, mr, mt, mb = _emu(0.45), _emu(0.12), _emu(0.10), _emu(0.28)
    plot_w = max(1, w_emu - ml - mr)
    plot_h = max(1, h_emu - mt - mb)

    def gx(fx: float) -> int:
        return ml + round(fx * plot_w)

    def gy(fy: float) -> int:
        return mt + round((1.0 - fy) * plot_h)  # invert: fraction 1 = top

    shapes: list[str] = []
    for pts, color, width_emu in chart.polylines:
        local = [(round(fx * plot_w), round((1.0 - fy) * plot_h)) for fx, fy in pts]
        if len(local) >= 2:
            shapes.append(_poly_shape(ml, mt, plot_w, plot_h, local, color, width_emu))
    for x0, y0, x1, y1, fill in chart.rects:
        left, right = gx(min(x0, x1)), gx(max(x0, x1))
        top, bot = gy(max(y0, y1)), gy(min(y0, y1))
        shapes.append(_rect_shape(left, top, right - left, bot - top, fill))
    for x, y, fill in chart.dots:
        shapes.append(_ellipse_shape(gx(x), gy(y), _emu(0.028), fill))
    group = (
        "<wpg:wgp><wpg:cNvGrpSpPr/><wpg:grpSpPr>"
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{w_emu}" cy="{h_emu}"/>'
        f'<a:chOff x="0" y="0"/><a:chExt cx="{w_emu}" cy="{h_emu}"/></a:xfrm></wpg:grpSpPr>'
        + "".join(shapes)
        + "</wpg:wgp>"
    )
    return (
        "<w:p><w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{w_emu}" cy="{h_emu}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{draw_id}" name="chart{draw_id}"/><wp:cNvGraphicFramePr/>'
        f'<a:graphic><a:graphicData uri="{_WPG}">{group}</a:graphicData></a:graphic>'
        "</wp:inline></w:drawing></w:r></w:p>"
    )


def _matrix_table_xml(grid: tuple[tuple[tuple[str, str, str], ...], ...]) -> str:
    """The 5x5 matrix as a shaded ``w:tbl`` (per-cell ``w:shd`` fill) — the most reliably-rendered
    vector primitive across Word/LibreOffice (ADR-0124 fallback promoted to the matrix path)."""
    rows = ""
    for row in grid:
        cells = ""
        for text, fill, tcolor in row:
            cells += (
                '<w:tc><w:tcPr><w:tcW w:w="820" w:type="dxa"/>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
                '<w:tcMar><w:left w:w="40" w:type="dxa"/><w:right w:w="40" w:type="dxa"/></w:tcMar>'
                '<w:vAlign w:val="center"/></w:tcPr>'
                '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:color w:val="{tcolor}"/><w:sz w:val="16"/></w:rPr>'
                f'<w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p></w:tc>'
            )
        rows += f"<w:tr>{cells}</w:tr>"
    borders = (
        "<w:tblBorders>"
        + "".join(
            f'<w:{side} w:val="single" w:sz="4" w:color="FFFFFF"/>'
            for side in ("top", "left", "bottom", "right", "insideH", "insideV")
        )
        + "</w:tblBorders>"
    )
    return f'<w:tbl><w:tblPr>{borders}<w:tblW w:w="0" w:type="auto"/></w:tblPr>{rows}</w:tbl><w:p/>'
