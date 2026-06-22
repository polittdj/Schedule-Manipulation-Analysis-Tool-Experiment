"""The stdlib .xlsx / .docx writers — structure, content, and determinism (M18)."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from schedule_forensics.reports.docx import (
    DocTable,
    Heading,
    Paragraph,
    render_document,
    render_docx,
)
from schedule_forensics.reports.tables import Table, TableSet, driving_table
from schedule_forensics.reports.xlsx import render_xlsx

TS = TableSet(
    "Demo export",
    (
        Table("Summary", ("Item", "Value"), (("Schedule", "P5 & co"), ("Activities", 145))),
        Table("Numbers", ("UID", "Float (d)"), ((101, 1.5), (102, None), (103, -3))),
        Table("Summary", ("Item", "Value"), (("dupe sheet name", "ok"),)),
    ),
)


def _zip_names(blob: bytes) -> list[str]:
    return zipfile.ZipFile(io.BytesIO(blob)).namelist()


def test_driving_table_appends_selected_custom_columns() -> None:
    rows = [
        {"unique_id": 1, "name": "A", "custom": {"CA-WBS": "X1", "CAM": "Bob"}},
        {"unique_id": 2, "name": "B", "custom": {"CA-WBS": "X2"}},  # no CAM
    ]
    # no custom labels -> the fixed column set is unchanged
    assert len(driving_table(rows, 143).headers) == 12
    t = driving_table(rows, 143, ["CA-WBS", "CAM"])
    assert t.headers[-2:] == ("CA-WBS", "CAM")
    assert t.rows[0][-2:] == ("X1", "Bob")
    assert t.rows[1][-2:] == ("X2", None)  # missing custom value -> None cell


def test_xlsx_has_the_minimum_valid_parts_and_one_sheet_per_table() -> None:
    blob = render_xlsx(TS)
    names = _zip_names(blob)
    assert "[Content_Types].xml" in names
    assert "xl/workbook.xml" in names and "xl/styles.xml" in names
    assert sum(1 for n in names if n.startswith("xl/worksheets/")) == len(TS.tables)


def test_xlsx_cells_round_trip_strings_numbers_and_skip_none() -> None:
    blob = render_xlsx(TS)
    sheet = zipfile.ZipFile(io.BytesIO(blob)).read("xl/worksheets/sheet2.xml").decode()
    root = ET.fromstring(sheet)
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows = root.findall(".//s:row", ns)
    assert len(rows) == 4  # header + 3 data rows (the None cell is skipped, not its row)
    cells_row2 = rows[1].findall("s:c", ns)
    assert [c.get("r") for c in cells_row2] == ["A2", "B2"]
    assert cells_row2[0].find("s:v", ns).text == "101"
    # the None cell is skipped entirely (row 3 carries only the UID cell)
    cells_row3 = rows[2].findall("s:c", ns)
    assert [c.get("r") for c in cells_row3] == ["A3"]


def test_xlsx_escapes_markup_and_dedupes_sheet_names() -> None:
    blob = render_xlsx(TS)
    zf = zipfile.ZipFile(io.BytesIO(blob))
    workbook = zf.read("xl/workbook.xml").decode()
    assert "P5 &amp; co" in zf.read("xl/worksheets/sheet1.xml").decode()
    assert 'name="Summary"' in workbook and "Summary~2" in workbook


def test_xlsx_and_docx_are_byte_deterministic() -> None:
    assert render_xlsx(TS) == render_xlsx(TS)
    assert render_docx(TS) == render_docx(TS)


def test_docx_document_carries_headings_tables_and_escapes() -> None:
    blob = render_docx(TS)
    names = _zip_names(blob)
    assert "[Content_Types].xml" in names and "word/document.xml" in names
    doc = zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml").decode()
    assert "Demo export" in doc and "P5 &amp; co" in doc
    assert doc.count("<w:tbl>") == len(TS.tables)


def test_docx_blocks_render_paragraph_leads_and_italics() -> None:
    blob = render_document(
        (
            Heading("Brief", level=0),
            Paragraph("Body text with a cited claim.", lead="FINDING:"),
            Paragraph("AI can make mistakes.", italic=True),
            DocTable(("A", "B"), (("1",),)),  # short row pads to the header width
        )
    )
    doc = zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml").decode()
    assert "FINDING:" in doc and "<w:i/>" in doc
    assert doc.count("<w:tc>") == 4  # 2 header + 2 body cells (padded)


_CUI = "CONTROLLED UNCLASSIFIED INFORMATION (CUI)"


def test_xlsx_marks_every_sheet_cui() -> None:
    """Law 1: every exported spreadsheet page carries the CUI banner/footer marking."""
    zf = zipfile.ZipFile(io.BytesIO(render_xlsx(TS)))
    sheets = [n for n in zf.namelist() if n.startswith("xl/worksheets/")]
    assert sheets  # sanity
    for name in sheets:
        sheet = zf.read(name).decode()
        # marking lives in headerFooter (after sheetData) so the cell grid is untouched
        assert "<headerFooter>" in sheet
        assert sheet.count(_CUI) == 2  # oddHeader + oddFooter
    # the CUI marking must not have displaced any data row
    root = ET.fromstring(zf.read("xl/worksheets/sheet2.xml").decode())
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    assert len(root.findall(".//s:row", ns)) == 4  # header + 3 data rows, unchanged


def test_docx_marks_every_page_cui() -> None:
    """Law 1: every Word export carries a CUI header + footer on every page."""
    zf = zipfile.ZipFile(io.BytesIO(render_docx(TS)))
    names = zf.namelist()
    assert "word/header1.xml" in names and "word/footer1.xml" in names
    assert _CUI in zf.read("word/header1.xml").decode()
    assert _CUI in zf.read("word/footer1.xml").decode()
    # referenced from the section so the banner repeats on every page, and the relationships resolve
    document = zf.read("word/document.xml").decode()
    assert "<w:headerReference " in document and "<w:footerReference " in document
    rels = zf.read("word/_rels/document.xml.rels").decode()
    assert 'Target="header1.xml"' in rels and 'Target="footer1.xml"' in rels
    # content types declare the new parts (Word rejects the file otherwise)
    ctypes = zf.read("[Content_Types].xml").decode()
    assert "/word/header1.xml" in ctypes and "/word/footer1.xml" in ctypes


def test_render_document_marks_cui_on_the_narrative_brief() -> None:
    """The Diagnostic Brief flows through render_document — it must be CUI-marked too."""
    blob = render_document((Heading("Diagnostic Brief", level=0), Paragraph("Body.")))
    zf = zipfile.ZipFile(io.BytesIO(blob))
    assert _CUI in zf.read("word/header1.xml").decode()
    assert _CUI in zf.read("word/footer1.xml").decode()
