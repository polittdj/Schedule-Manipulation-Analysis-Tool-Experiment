"""``read_xlsx_numbered``: each row carries the row NUMBER Excel shows, not its position.

ADR-0524.

Excel omits a blank row that carries no formatting from ``<sheetData>`` — measured: 18 of the 51
Excel-authored workbooks committed under ``00_REFERENCE_INTAKE`` skip row numbers, and 8 keep
FORMATTED empty rows. A reader that counts ``<row>`` elements therefore mis-numbers every row
after the first unformatted spacer, and the One-Pager's problems, notes and ▦ DATA "row" columns
send the operator to the wrong line. ECMA-376 also makes ``r=`` OPTIONAL on rows and cells (a
missing one is the previous + 1), and 47 committed non-Excel workbooks write it only after a gap;
``read_xlsx`` puts every r-less cell in column A, which would drop a completion value into the
swimlane column. ``read_xlsx`` itself is left byte-for-byte as it was (the SRA importers read
through it); the numbered reader is the One-Pager's.

Red-first (2026-09-22): written before ``read_xlsx_numbered`` existed and observed to fail at
import.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from schedule_forensics.reports import xlsx_read
from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx, read_xlsx_numbered
from web.onepager_twin import TWIN_ROWS, twin_xlsx

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _book(sheet_data: str, shared: tuple[str, ...] = ()) -> bytes:
    """One sheet whose ``<sheetData>`` body is exactly ``sheet_data``."""
    sst = "".join(f"<si><t>{s}</t></si>" for s in shared)
    parts = {
        "xl/workbook.xml": (
            f'<workbook xmlns="{_MAIN}" xmlns:r="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships"><sheets><sheet name="List" sheetId="1" '
            'r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        "xl/sharedStrings.xml": f'<sst xmlns="{_MAIN}">{sst}</sst>',
        "xl/worksheets/sheet1.xml": (
            f'<worksheet xmlns="{_MAIN}"><sheetData>{sheet_data}</sheetData></worksheet>'
        ),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in parts.items():
            zf.writestr(name, body)
    return buf.getvalue()


def _is(text: str) -> str:
    return f"<is><t>{text}</t></is>"


def test_an_omitted_spacer_row_keeps_every_later_row_on_its_excel_number() -> None:
    """The twin in Excel's own shape: the spacer rows are simply absent."""
    numbered = read_xlsx_numbered(twin_xlsx(TWIN_ROWS, omit_blank=True))["Sheet1"]
    by_task = {cells[1]: n for n, cells in numbered if len(cells) > 1}
    # TWIN_ROWS: row 1 header, row 2 spacer, row 3 Boots 1, ... row 25 "MET ATP for Hot-Fire"
    assert by_task["Boots 1"] == 3 and by_task["CDR"] == 7
    assert by_task["MET ATP for Hot-Fire"] == len(TWIN_ROWS) == 25
    # the default twin (every spacer written as an empty <row>) numbers the same rows the same
    padded = read_xlsx_numbered(twin_xlsx(TWIN_ROWS))["Sheet1"]
    assert {cells[1]: n for n, cells in padded if len(cells) > 1} == by_task


def test_a_formatted_empty_row_is_counted_once_not_twice() -> None:
    data = (
        f'<row r="1"><c r="A1" t="inlineStr">{_is("Lane")}</c></row>'
        '<row r="2" ht="15.75" customHeight="1"/>'  # present, formatted, no cells
        f'<row r="5"><c r="A5" t="inlineStr">{_is("Later")}</c></row>'
    )
    assert read_xlsx_numbered(_book(data))["List"] == [(1, ["Lane"]), (2, []), (5, ["Later"])]


def test_an_r_less_row_is_the_previous_row_plus_one_and_an_r_less_cell_the_next_column() -> None:
    """ECMA-376: both ``r=`` attributes are optional. A producer that writes them only after a gap
    must still land a fourth-column value in column D — never on top of the swimlane in A."""
    data = (
        f'<row r="2"><c r="A2" t="inlineStr">{_is("Dallas")}</c>'
        f'<c t="inlineStr">{_is("CDR")}</c><c><v>46662</v></c>'
        f'<c t="inlineStr">{_is("Complete")}</c></row>'
        f'<row><c t="inlineStr">{_is("Dallas")}</c><c r="C3"><v>46670</v></c>'
        f'<c t="inlineStr">{_is("In Progress")}</c></row>'
    )
    got = read_xlsx_numbered(_book(data))["List"]
    assert got == [
        (2, ["Dallas", "CDR", "46662", "Complete"]),
        (3, ["Dallas", "", "46670", "In Progress"]),
    ]
    # the whole-twin case: no r= anywhere, rows and columns implied by order
    rless = read_xlsx_numbered(twin_xlsx(TWIN_ROWS, rless=True))["Sheet1"]
    assert [n for n, _c in rless] == list(range(1, len(TWIN_ROWS) + 1))
    assert rless[2] == (3, ["Flight Manifests", "Boots 1", "46565"])


def test_rows_out_of_order_or_an_unreadable_reference_are_refused_by_name() -> None:
    backwards = (
        f'<row r="5"><c r="A5" t="inlineStr">{_is("x")}</c></row>'
        f'<row r="3"><c r="A3" t="inlineStr">{_is("y")}</c></row>'
    )
    with pytest.raises(XlsxError, match="row 3"):
        read_xlsx_numbered(_book(backwards))
    bad_ref = f'<row r="1"><c r="$A$1" t="inlineStr">{_is("x")}</c></row>'
    with pytest.raises(XlsxError, match=r"\$A\$1"):
        read_xlsx_numbered(_book(bad_ref))


def test_the_plain_reader_is_unchanged_for_its_other_callers() -> None:
    """``read_xlsx`` keeps counting as it always did — the SRA importers read through it and the
    change is the One-Pager's alone (a whole-corpus digest was compared before and after)."""
    data = (
        f'<row r="1"><c r="A1" t="inlineStr">{_is("Lane")}</c></row>'
        f'<row r="5"><c r="A5" t="inlineStr">{_is("Later")}</c></row>'
    )
    assert read_xlsx(_book(data))["List"] == [["Lane"], ["Later"]]
    plain = read_xlsx(twin_xlsx(TWIN_ROWS, omit_blank=True))["Sheet1"]
    numbered = read_xlsx_numbered(twin_xlsx(TWIN_ROWS, omit_blank=True))["Sheet1"]
    assert plain == [cells for _n, cells in numbered]  # same cells, only the numbers differ


@pytest.mark.parametrize("reader", [read_xlsx, read_xlsx_numbered], ids=["plain", "numbered"])
def test_both_readers_share_one_decompression_budget(
    reader: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The zip-bomb defense (ADR-0247/0250) covers the numbered reader too: it must read through
    the SAME budgeted helper, not a copy that a monkeypatched cap would miss."""
    blob = _book("", shared=("A" * 5_000,))
    monkeypatch.setattr(xlsx_read, "_MAX_XLSX_DECOMPRESSED_BYTES", 2_000)
    with pytest.raises(XlsxError, match=r"size cap|zip bomb"):
        reader(blob)  # type: ignore[operator]


@pytest.mark.parametrize("reader", [read_xlsx, read_xlsx_numbered], ids=["plain", "numbered"])
def test_both_readers_refuse_a_dtd_bearing_part(reader: object) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0"?><!DOCTYPE workbook [<!ENTITY x "y">]>'
            f'<workbook xmlns="{_MAIN}"><sheets/></workbook>',
        )
    with pytest.raises(XlsxError, match="DTD"):
        reader(buf.getvalue())  # type: ignore[operator]
