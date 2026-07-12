"""The stdlib .xlsx / .docx writers — structure, content, and determinism (M18)."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

import pytest

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


def test_chart_block_renders_native_vector_drawing_and_shaded_matrix() -> None:
    """A Chart block embeds a vendor-free vector drawing (DrawingML shape group: custGeom polylines
    + prstGeom rects) for kind='vector' and a shaded w:tbl for kind='matrix' — no image part, no new
    relationship, and byte-deterministic (ADR-0124)."""
    from schedule_forensics.reports.docx import Chart

    vector = Chart(
        kind="vector",
        polylines=(
            (((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525),
            (((0.05, 0.05), (0.5, 0.55), (0.95, 0.98)), "0B6BCB", 19050),
        ),
        rects=((0.2, 0.0, 0.3, 0.6, "4C78A8"), (0.5, 0.0, 0.6, 0.9, "F58518")),
        dots=((0.5, 0.55, "E8352E"),),
    )
    matrix = Chart(
        kind="matrix",
        grid=tuple(
            tuple((str(c * p), "43A047" if c * p < 8 else "E53935", "FFFFFF") for p in range(1, 6))
            for c in range(5, 0, -1)
        ),
    )
    blob = render_document((Heading("Charts", level=0), vector, matrix))
    zf = zipfile.ZipFile(io.BytesIO(blob))
    assert zf.testzip() is None  # valid zip
    # NO new parts/relationships were added (the drawing lives inline in document.xml)
    assert set(zf.namelist()) == {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/_rels/document.xml.rels",
        "word/document.xml",
        "word/header1.xml",
        "word/footer1.xml",
    }
    document = zf.read("word/document.xml").decode()
    ET.fromstring(document)  # well-formed
    for token in (
        "<w:drawing>",
        "<wpg:wgp>",
        "<a:custGeom>",
        '<a:prstGeom prst="rect"',
        '<a:prstGeom prst="ellipse"',
        "<w:shd ",
    ):
        assert token in document, token
    # the inline vector chart needs a unique, non-zero extent + docPr id; the matrix is a w:tbl
    assert 'wp:docPr id="2"' in document  # the vector chart is the 2nd block -> id 2
    # byte-deterministic
    assert render_document((Heading("Charts", level=0), vector, matrix)) == blob


def test_chart_labels_render_as_inline_text_boxes() -> None:
    """ChartText labels (titles / axis values / legend / data call-outs) become transparent
    DrawingML text boxes in the chart group; multi-line text splits into separate paragraphs."""
    from schedule_forensics.reports.docx import Chart, ChartText

    chart = Chart(
        kind="vector",
        polylines=((((0.0, 1.0), (0.0, 0.0), (1.0, 0.0)), "555555", 9525),),
        labels=(
            ChartText(0.0, 1.1, "Finish-date confidence", "l", 18, "222B35", True),
            ChartText(-0.02, 1.0, "100%", "r", 12),
            ChartText(0.02, 0.8, "P50  2027-12-01\nP80  2027-12-10", "l", 12),
        ),
    )
    document = (
        zipfile.ZipFile(io.BytesIO(render_document((Heading("C", level=0), chart))))
        .read("word/document.xml")
        .decode()
    )
    ET.fromstring(document)  # well-formed even with the text boxes
    assert '<wps:cNvSpPr txBox="1"/>' in document  # the label is a text box
    assert "<w:txbxContent>" in document
    assert "Finish-date confidence" in document and "100%" in document
    # the two-line call-out becomes two paragraphs, one per line
    assert document.count("P50  2027-12-01") == 1 and document.count("P80  2027-12-10") == 1
    # byte-deterministic with the labels embedded
    assert render_document((Heading("C", level=0), chart)) == render_document(
        (Heading("C", level=0), chart)
    )


def test_chart_docpr_ids_are_unique_across_multiple_drawings() -> None:
    """Word flags 'repair' on duplicate drawing ids — every chart gets a distinct docPr id."""
    import re

    from schedule_forensics.reports.docx import Chart

    charts = [Chart(rects=((0.1, 0.0, 0.2, 0.5, "4C78A8"),)) for _ in range(4)]
    document = (
        zipfile.ZipFile(io.BytesIO(render_document(tuple(charts))))
        .read("word/document.xml")
        .decode()
    )
    ids = re.findall(r'wp:docPr id="(\d+)"', document)
    assert len(ids) == 4 and len(set(ids)) == 4


# ── xlsx_read: the import side of the round-trip templates (ADR-0211) ─────────────────────────


def test_read_xlsx_round_trips_render_xlsx() -> None:
    """render_xlsx (inline strings) → read_xlsx reproduces headers, string cells, numbers-as-text,
    and empty cells as ``""`` — the contract the SRA template importer relies on."""
    from schedule_forensics.reports.xlsx_read import read_xlsx

    ts = TableSet(
        "RT demo",
        (
            Table("Alpha", ("A", "B", "C"), (("x", 1, None), ("", -2.5, "z"))),
            Table("Beta", ("UID", "Name"), ((7, "task seven"),)),
        ),
    )
    sheets = read_xlsx(render_xlsx(ts))
    assert list(sheets) == ["Alpha", "Beta"]
    assert sheets["Alpha"][0] == ["A", "B", "C"]  # header row
    # number kept verbatim; a TRAILING empty (None) is dropped from the row width (no <c> emitted)
    assert sheets["Alpha"][1] == ["x", "1"]
    # an INTERIOR/leading empty cell is preserved by column (a later cell fixes the width)
    assert sheets["Alpha"][2] == ["", "-2.5", "z"]
    assert sheets["Beta"][1] == ["7", "task seven"]


def test_read_xlsx_reads_shared_strings() -> None:
    """Excel rewrites files with a sharedStrings table (t="s"); the reader resolves the index."""
    from schedule_forensics.reports.xlsx_read import read_xlsx

    # Build a minimal workbook that uses a shared-strings table, the way Excel saves.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
            'package/2006/content-types"/>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"'
            ' Type="x"/></Relationships>',
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships"><sheets><sheet name="S" sheetId="1" '
            'r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/sharedStrings.xml",
            '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main"><si><t>Hello</t></si><si><t>World</t></si></sst>',
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main"><sheetData><row r="1">'
            '<c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
            '<c r="C1"><v>42</v></c></row></sheetData></worksheet>',
        )
    sheets = read_xlsx(buf.getvalue())
    assert sheets["S"][0] == ["Hello", "World", "42"]


def test_read_xlsx_rejects_non_xlsx() -> None:
    from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx

    with pytest.raises(XlsxError):
        read_xlsx(b"this is not a zip file")


def test_read_xlsx_rejects_dtd_bearing_part() -> None:
    """XXE defense (same as the MSPDI importer): a workbook part carrying a DTD/entity declaration
    is rejected before ElementTree ever parses it."""
    from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><!DOCTYPE workbook [<!ENTITY x "y">]>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheets/></workbook>",
        )
    with pytest.raises(XlsxError, match="DTD or entity"):
        read_xlsx(buf.getvalue())
