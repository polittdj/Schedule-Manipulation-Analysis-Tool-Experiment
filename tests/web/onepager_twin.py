"""The synthetic twin of the operator's One-Pager workbook, shared by the ADR-0446 tests.

Written the way Excel writes one — a shared-strings table, bare numbers for dates — so the
path ``read_xlsx`` takes on a real file is the path under test. The real workbook is not
committed; every quirk it carried is reproduced here by row.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable

# ── a synthetic twin of the operator's workbook, written the way Excel writes one ─────────────

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def twin_xlsx(rows: Iterable[tuple[object, ...]]) -> bytes:
    """A minimal .xlsx with a SHARED-STRINGS table (Excel's own encoding, not the tool's
    inline-string writer), numbers written bare — the exact shape ``read_xlsx`` sees in the
    field."""
    shared: list[str] = []

    def sidx(s: str) -> int:
        if s not in shared:
            shared.append(s)
        return shared.index(s)

    sheet_rows = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, v in enumerate(row):
            ref = f"{chr(65 + c)}{r}"
            if v is None or v == "":
                continue
            if isinstance(v, (int, float)):
                cells.append(f'<c r="{ref}" s="1"><v>{v}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="s"><v>{sidx(str(v))}</v></c>')
        sheet_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    sst = "".join(f"<si><t>{s.replace('&', '&amp;').replace('<', '&lt;')}</t></si>" for s in shared)
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/'
            'package/2006/content-types"><Default Extension="rels" ContentType="application/'
            'vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" '
            'ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName='
            '"/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sharedStrings+xml"/></Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="{_MAIN}" xmlns:r="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet '
            'name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/></Relationships>'
        ),
        "xl/sharedStrings.xml": (
            f'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="{_MAIN}">{sst}</sst>'
        ),
        "xl/worksheets/sheet1.xml": (
            f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{_MAIN}"><sheetData>'
            f"{''.join(sheet_rows)}</sheetData></worksheet>"
        ),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in parts.items():
            zf.writestr(name, content)
    return buf.getvalue()


#: The operator's workbook, in miniature: every date form it carried, its typo row, its
#: spacing-variant swimlane, and its spacer rows. Serial 46565 is a real Excel date cell
#: (2027-06-27); 46310 is a date typed into a General-formatted cell (2026-10-15).
TWIN_ROWS: tuple[tuple[object, ...], ...] = (
    ("Swimlane Name", "Task", "Date"),
    (),
    ("Flight Manifests", "Boots 1", 46565),
    ("Flight Manifests", "Boots 2", 46840),
    (),
    ("Dallas", "Uncrewed Lander Campaign", "04/20/2027 - 06/20/2027"),
    ("Dallas", "CDR", 46662),
    ("Dallas", "Crewed Lander Campaign", "03/15/2028 - 07/10/2028"),
    (),
    ("Crew Life", "MET Testing", "12/1/2026 - 4/15/27"),
    ("Crew Life", "MET On-Dock", 46310),
    (),
    ("BobbySon", "Overall GTA Window", "06/10/26 - 06/22/28"),
    ("BobbySon", "Stack No. 2 Testing", "11/10/26 - 2/13/27"),
    (),
    ("GRC-Blue RR-6", "Screen Assembly, Design & Fabrication", "05/2026 - 11/2026"),
    ("GRC-Blue RR-6", "Build up, test, tear down", "12/2026 - 3/2027"),
    (),
    ("GRC- (MCaRR-2)", "TRR", 46280),
    ("GRC-(MCaRR-2)", "Life Testing", "9/16/26 - 02/28/27"),
    (),
    ("GRC-MET Testing", "Prepare Test Rig", "9/18/25 - 3/20/27"),
    ("GRC-MET Testing", "Blue Origin On-Dock", "10/122/2026"),
    ("GRC-MET Testing", "ECT Test", "11/4/2026 - 12/12/26"),
    ("", "MET ATP for Hot-Fire", 46412),
)
