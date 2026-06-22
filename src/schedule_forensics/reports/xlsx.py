"""Minimal, dependency-free .xlsx writer (M18 — every table exportable to Excel).

An ``.xlsx`` file is a zip of XML parts; this emits the smallest valid subset Excel
accepts: content types, the package/workbook relationships, one worksheet per
:class:`~schedule_forensics.reports.tables.Table`, and a two-font style sheet (normal +
bold header row). Strings are inline (no shared-string table), numbers are native
numeric cells. Output is byte-deterministic: fixed zip timestamps, fixed part order.
"""

from __future__ import annotations

import io
import re
import zipfile

from schedule_forensics.reports.tables import Table, TableSet


def _esc(value: str) -> str:
    """XML-escape text content (this module only WRITES XML; nothing is parsed)."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_attr(value: str) -> str:
    """XML-escape an attribute value (quotes included — sheet names live in attributes)."""
    return _esc(value).replace('"', "&quot;")


#: Excel's hard sheet-name rules: <= 31 chars, none of []:*?/\ .
_SHEET_BAD = re.compile(r"[\[\]:*?/\\]")
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "{sheets}</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="1"><fill><patternFill patternType="none"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf/></cellStyleXfs>
<cellXfs count="2"><xf fontId="0"/><xf fontId="1" applyFont="1"/></cellXfs>
</styleSheet>"""

#: CUI banner/footer marking stamped on every printed page of every sheet (Law 1 — every
#: exported artifact carries its handling caveat). ``&amp;C`` (XML-escaped ``&C``) centers the
#: text; Excel un-escapes and interprets the header/footer codes. Placed after ``<sheetData>``,
#: which is where the OOXML worksheet schema expects ``headerFooter`` — so the cell grid (and the
#: tests that read it) is untouched.
_CUI_BANNER = "CONTROLLED UNCLASSIFIED INFORMATION (CUI)"
_CUI_HEADER_FOOTER = (
    f"<headerFooter><oddHeader>&amp;C{_CUI_BANNER}</oddHeader>"
    f"<oddFooter>&amp;C{_CUI_BANNER}</oddFooter></headerFooter>"
)


def render_xlsx(tableset: TableSet) -> bytes:
    """Serialize a :class:`TableSet` as a deterministic .xlsx workbook (bytes)."""
    sheets = list(_sheet_names(tableset.tables))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.worksheet+xml"/>\n'
            for i in range(len(sheets))
        )
        _add(zf, "[Content_Types].xml", _CONTENT_TYPES.format(sheets=overrides))
        _add(zf, "_rels/.rels", _ROOT_RELS)
        sheet_tags = "".join(
            f'<sheet name="{_esc_attr(name)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
            for i, name in enumerate(sheets)
        )
        _add(
            zf,
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{sheet_tags}</sheets></workbook>",
        )
        rels = "".join(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
            for i in range(len(sheets))
        )
        rels += (
            f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        )
        _add(
            zf,
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{rels}</Relationships>",
        )
        _add(zf, "xl/styles.xml", _STYLES)
        for i, table in enumerate(tableset.tables):
            _add(zf, f"xl/worksheets/sheet{i + 1}.xml", _sheet_xml(table))
    return buf.getvalue()


def _sheet_names(tables: tuple[Table, ...]) -> list[str]:
    seen: dict[str, int] = {}
    names = []
    for table in tables:
        base = _SHEET_BAD.sub(" ", table.title).strip() or "Sheet"
        base = base[:28]
        n = seen.get(base.lower(), 0)
        seen[base.lower()] = n + 1
        names.append(base if n == 0 else f"{base[:26]}~{n + 1}")
    return names


def _sheet_xml(table: Table) -> str:
    cols = "".join(
        f'<col min="{i + 1}" max="{i + 1}" width="{_width(table, i)}" customWidth="1"/>'
        for i in range(len(table.headers))
    )
    rows = [_row_xml(1, table.headers, style=1)]
    for r, row in enumerate(table.rows, start=2):
        rows.append(_row_xml(r, row, style=0))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<cols>{cols}</cols><sheetData>{''.join(rows)}</sheetData>"
        f"{_CUI_HEADER_FOOTER}</worksheet>"
    )


def _row_xml(r: int, cells: tuple[object, ...], *, style: int) -> str:
    out = []
    for i, value in enumerate(cells):
        if value is None:
            continue
        ref = f"{_col_letter(i)}{r}"
        if isinstance(value, bool):
            out.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{value}</t></is></c>')
        elif isinstance(value, (int, float)):
            out.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
        else:
            text = _esc(str(value))
            out.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{text}</t></is></c>')
    return f'<row r="{r}">{"".join(out)}</row>'


def _col_letter(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _width(table: Table, col: int) -> int:
    longest = len(str(table.headers[col]))
    for row in table.rows[:200]:
        if col < len(row) and row[col] is not None:
            longest = max(longest, len(str(row[col])))
    return min(max(longest + 2, 8), 60)


def _add(zf: zipfile.ZipFile, name: str, content: str) -> None:
    info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, content)
