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


Block = Heading | Paragraph | DocTable

#: Half-point font sizes per heading level (0 = title).
_HEADING_SIZES = {0: 40, 1: 30, 2: 25, 3: 23}


def render_document(blocks: Sequence[Block]) -> bytes:
    """Serialize blocks as a deterministic .docx (bytes)."""
    body = "".join(_block_xml(b) for b in blocks)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document xmlns:w="{_W}" xmlns:r="{_R}"><w:body>{body}'
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


def _block_xml(block: Block) -> str:
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
