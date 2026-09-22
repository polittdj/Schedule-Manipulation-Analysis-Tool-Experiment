"""Minimal, std-lib-only ``.xlsx`` reader — the import side of the round-trip templates (ADR-0211).

The tool exports fill-in Excel templates (:mod:`schedule_forensics.reports.xlsx`) for the SRA risk
register and the per-task Best/Worst-Case durations + Risk Ranking Factors; the operator fills them
in Excel and re-imports. Excel rewrites the file using a **shared-strings** table (unlike our
inline-string writer), so this reader handles every common cell encoding: shared strings
(``t="s"``),
inline strings (``t="inlineStr"``), formula strings (``t="str"``), booleans (``t="b"``), and bare
numbers. Std-lib only (``zipfile`` + ``xml.etree``) — Law 1 (no third-party parser in the runtime).

``read_xlsx(data)`` returns ``{sheet_name: [[cell, …], …]}`` with every cell a **string** (numbers
kept verbatim as written, gaps filled with ``""`` by column so a row's columns line up). The caller
maps header names to columns and coerces — the reader never guesses types or fabricates a value.

``read_xlsx_numbered(data)`` returns the same cells with each row's **Excel row number** beside it
(ADR-0524): ``{sheet_name: [(row_number, [cell, …]), …]}``. Excel leaves an unformatted blank row
OUT of ``<sheetData>`` (18 of the 51 Excel-authored workbooks under ``00_REFERENCE_INTAKE`` skip
row numbers), so a row's position in the list is not the row the operator sees; the number comes
from ``<row r=>``. ECMA-376 makes ``r=`` optional on rows and cells alike — a missing one is the
previous row or column plus one — and a present one that cannot be read, or rows that run
backwards, are refused by name rather than guessed. ``read_xlsx`` is unchanged (the SRA importers
read through it); both readers share one decompression budget and one hardened XML parser.
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET  # nosec B405  # hardened in _parse_xml (DTD/entity rejected)
import zipfile
from collections.abc import Callable
from typing import TypeVar

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

#: A1-style cell reference → (column-letters, row). The letters give the 0-based column index so a
#: sparse row (Excel omits empty cells) still lands each value under the right header.
_CELL_RE = re.compile(r"^([A-Z]+)(\d+)$")


class XlsxError(ValueError):
    """The uploaded file is not a readable .xlsx workbook."""


#: Cap on the TOTAL decompressed bytes read from one workbook (every part summed). An ``.xlsx`` is a
#: ZIP, and std-lib ``zipfile`` decompresses a member fully on ``read()`` with no bound — so a small
#: upload can inflate to gigabytes (a "zip bomb") and exhaust RAM. This caps the DECOMPRESSED total
#: (parity with the web layer's 500 MB compressed per-file upload cap); a real SRA round-trip
#: template decompresses to well under a megabyte, so this never rejects a legitimate file.
_MAX_XLSX_DECOMPRESSED_BYTES = 500 * 1024 * 1024


def _parse_xml(data: bytes) -> ET.Element:
    """Parse one XML part of the workbook, hardened against XXE the same way the MSPDI importer is:
    reject any document carrying a DTD or entity declaration before handing it to ElementTree, and
    surface a malformed part as :class:`XlsxError` rather than a raw ``ParseError``."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise XlsxError("xlsx part with a DTD or entity declaration is rejected (XXE defense)")
    try:
        return ET.fromstring(data)  # nosec B314  # DTD/entity decls rejected above
    except ET.ParseError as exc:
        raise XlsxError(f"malformed xlsx XML part: {exc}") from exc


def _col_index(ref: str) -> int:
    """0-based column index from an A1-style cell ref (``A`` -> 0, ``AA`` -> 26)."""
    m = _CELL_RE.match(ref)
    if not m:
        return 0
    letters = m.group(1)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _si_text(si: ET.Element) -> str:
    """Full text of one shared-string ``<si>`` — concatenating every ``<t>`` (rich-text runs)."""
    return "".join(t.text or "" for t in si.iter(f"{_MAIN}t"))


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    """One ``<c>`` cell as a string, honoring its ``t`` type."""
    ctype = cell.get("t")
    if ctype == "inlineStr":
        is_el = cell.find(f"{_MAIN}is")
        return _si_text(is_el) if is_el is not None else ""
    if ctype == "s":  # shared string: <v> is the index
        v = cell.find(f"{_MAIN}v")
        idx_text = (v.text or "").strip() if v is not None else ""
        if not idx_text:
            return ""
        try:
            return shared[int(idx_text)]
        except (ValueError, IndexError):
            return ""
    # str (formula result), b (bool), n / None (number) — the literal <v> text
    v = cell.find(f"{_MAIN}v")
    return (v.text or "") if v is not None else ""


_Row = TypeVar("_Row")


def read_xlsx(data: bytes) -> dict[str, list[list[str]]]:
    """Parse an ``.xlsx`` file's bytes into ``{sheet_name: rows}`` (every cell a string).

    Raises :class:`XlsxError` if the bytes are not a valid xlsx (bad zip / missing workbook).
    """
    return _read_workbook(data, _read_sheet)


def read_xlsx_numbered(data: bytes) -> dict[str, list[tuple[int, list[str]]]]:
    """Parse an ``.xlsx`` into ``{sheet_name: [(excel_row_number, cells), …]}`` — the cells
    :func:`read_xlsx` returns, each row with the number Excel shows for it (see the module doc).

    Raises :class:`XlsxError` as :func:`read_xlsx` does, and also for a row or cell reference that
    cannot be read or rows that are not in ascending order.
    """
    return _read_workbook(data, _read_sheet_numbered)


def _read_workbook(
    data: bytes, read_sheet: Callable[[ET.Element, list[str]], list[_Row]]
) -> dict[str, list[_Row]]:
    """Open the package once — the shared decompression budget, the hardened XML parser, the
    shared strings, the sheet relationships — and hand every sheet to ``read_sheet``."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise XlsxError("not a valid .xlsx file (bad zip)") from exc

    # Zip-bomb defense: decompress every member through one shared byte budget. ``zf.open(name)``
    # streams, so reading ``remaining + 1`` bounds memory REGARDLESS of the member's declared size
    # (a lying header can't inflate RAM), and the running total caps the whole workbook.
    remaining = _MAX_XLSX_DECOMPRESSED_BYTES

    def _read(name: str) -> bytes:
        nonlocal remaining
        with zf.open(name) as fh:
            chunk = fh.read(remaining + 1)
        if len(chunk) > remaining:
            raise XlsxError("xlsx decompresses past the size cap (possible zip bomb)")
        remaining -= len(chunk)
        return chunk

    names = set(zf.namelist())
    if "xl/workbook.xml" not in names:
        raise XlsxError("not a valid .xlsx workbook (no xl/workbook.xml)")

    # shared strings (optional)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in names:
        sst = _parse_xml(_read("xl/sharedStrings.xml"))
        shared = [_si_text(si) for si in sst.findall(f"{_MAIN}si")]

    # rId -> worksheet part path
    rel_target: dict[str, str] = {}
    if "xl/_rels/workbook.xml.rels" in names:
        rels = _parse_xml(_read("xl/_rels/workbook.xml.rels"))
        for rel in rels.findall(f"{_PKG_REL}Relationship"):
            rid, target = rel.get("Id"), rel.get("Target")
            if rid and target:
                rel_target[rid] = target.lstrip("/")

    def _resolve(target: str) -> str:
        # workbook rels are relative to xl/ ; normalize a leading "worksheets/…" or "/xl/…"
        if target.startswith("xl/"):
            return target
        return f"xl/{target}"

    wb = _parse_xml(_read("xl/workbook.xml"))
    out: dict[str, list[_Row]] = {}
    sheets = wb.find(f"{_MAIN}sheets")
    for sheet in [] if sheets is None else list(sheets):
        name = sheet.get("name") or f"Sheet{len(out) + 1}"
        rid = sheet.get(f"{_REL}id")
        target = rel_target.get(rid or "", "")
        path = _resolve(target) if target else ""
        if path not in names:
            out[name] = []
            continue
        out[name] = read_sheet(_parse_xml(_read(path)), shared)
    return out


def _read_sheet(root: ET.Element, shared: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    data = root.find(f"{_MAIN}sheetData")
    if data is None:
        return rows
    for row in data.findall(f"{_MAIN}row"):
        cells: dict[int, str] = {}
        for c in row.findall(f"{_MAIN}c"):
            ref = c.get("r") or ""
            cells[_col_index(ref)] = _cell_text(c, shared)
        width = (max(cells) + 1) if cells else 0
        rows.append([cells.get(i, "") for i in range(width)])
    return rows


def _read_sheet_numbered(root: ET.Element, shared: list[str]) -> list[tuple[int, list[str]]]:
    """Every ``<row>`` with its Excel row number; each cell in the column its ``r=`` names, or the
    column after the previous cell's when ``r=`` is absent (ECMA-376 — never column A)."""
    rows: list[tuple[int, list[str]]] = []
    data = root.find(f"{_MAIN}sheetData")
    if data is None:
        return rows
    previous = 0
    for row in data.findall(f"{_MAIN}row"):
        number = _row_number(row.get("r"), previous)
        previous = number
        cells: dict[int, str] = {}
        column = -1
        for c in row.findall(f"{_MAIN}c"):
            ref = c.get("r")
            column = column + 1 if not ref else _ref_column(ref, number)
            cells[column] = _cell_text(c, shared)
        width = (max(cells) + 1) if cells else 0
        rows.append((number, [cells.get(i, "") for i in range(width)]))
    return rows


def _row_number(ref: str | None, previous: int) -> int:
    if not ref:
        return previous + 1
    if not ref.isdigit() or int(ref) < 1:
        raise XlsxError(f"unreadable row number r={ref!r} after row {previous}")
    number = int(ref)
    if number <= previous:
        raise XlsxError(f"rows out of order: row {number} follows row {previous}")
    return number


def _ref_column(ref: str, row: int) -> int:
    if not _CELL_RE.match(ref):
        raise XlsxError(f"unreadable cell reference {ref!r} on row {row}")
    return _col_index(ref)
