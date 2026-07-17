"""Zip-bomb defense for the std-lib ``.xlsx`` reader (audit, ADR-0247).

An ``.xlsx`` is a ZIP; ``zipfile`` decompresses a member fully on ``read()`` with no bound, so a
tiny upload can inflate to gigabytes and exhaust RAM. ``read_xlsx`` now streams every part through
one shared byte budget (:data:`_MAX_XLSX_DECOMPRESSED_BYTES`), so a hostile workbook is rejected
with :class:`XlsxError` instead of being fully decompressed. The SRA re-import routes additionally
cap the COMPRESSED upload (parity with ``/upload``'s 500 MB limit) — covered in
``tests/web/test_sra_excel_templates.py``.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from schedule_forensics.reports import xlsx_read
from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx

_WORKBOOK = (
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheets/></workbook>"
)


def _xlsx(shared_strings: bytes, workbook: str = _WORKBOOK) -> bytes:
    """A minimal valid ``.xlsx`` with chosen ``sharedStrings.xml`` / workbook bodies."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/sharedStrings.xml", shared_strings)
    return buf.getvalue()


def test_read_xlsx_rejects_a_decompression_bomb(monkeypatch: pytest.MonkeyPatch) -> None:
    """A part that inflates past the cap raises XlsxError before it is fully read into RAM.

    Mutation check: with the ``_read`` budget removed (a plain ``zf.read``), the 200 KB
    sharedStrings part parses cleanly and NO error is raised — this test then fails.
    """
    # 200 KB of a single repeated byte: highly compressible, so the .xlsx itself stays tiny — the
    # essence of a zip bomb (small on disk, huge on decompression).
    payload = b"<sst>" + b"A" * 200_000 + b"</sst>"
    blob = _xlsx(payload)
    assert len(blob) < 5_000, (
        "the bomb's COMPRESSED size should be tiny (it is highly compressible)"
    )

    monkeypatch.setattr(xlsx_read, "_MAX_XLSX_DECOMPRESSED_BYTES", 2_000)
    with pytest.raises(XlsxError, match=r"size cap|zip bomb"):
        read_xlsx(blob)


def test_read_xlsx_total_budget_spans_every_part(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared budget spans parts (audit ADR-0250): TWO parts each UNDER the cap, but
    summing OVER it, must still be rejected — proving ``remaining`` accumulates across parts rather
    than resetting per part. Mutation check: reset the budget per ``_read`` call and this passes on
    each part alone, so no error is raised and this test fails; the single-part bomb tests above
    would NOT catch that regression."""
    # sharedStrings is read first (~601 B), then workbook.xml (~600 B). Under a 1000-byte cap each
    # fits alone (601 < 1000, 600 < 1000) but the running total (601 leaves 399, then 600 > 399)
    # trips on the SECOND part — only because the budget is shared. Padding is a highly compressible
    # comment, so both parts decompress large while the .xlsx stays tiny.
    shared = b"<sst>" + b"B" * 590 + b"</sst>"  # ~601 decompressed bytes
    workbook = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<!--" + "A" * 540 + "--><sheets/></workbook>"
    )  # ~600 decompressed bytes
    blob = _xlsx(shared, workbook=workbook)
    monkeypatch.setattr(xlsx_read, "_MAX_XLSX_DECOMPRESSED_BYTES", 1_000)
    with pytest.raises(XlsxError, match=r"size cap|zip bomb"):
        read_xlsx(blob)


def test_read_xlsx_accepts_a_normal_small_workbook() -> None:
    """The cap never rejects a legitimate (sub-megabyte) workbook — no false positive."""
    sheets = read_xlsx(_xlsx(b'<sst xmlns="x"/>'))
    assert sheets == {}  # valid workbook, no sheets declared — read cleanly under the real cap
