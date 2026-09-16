"""R-50 — the library's same-named **Metric History variants**, pinned UID-exact from Fuse's own
per-activity marks.

The register (§3, R-50) said three Bible metrics are not exposed, so a reader of the Metric
History report cannot find them in the tool:

* ``Insufficient Detail™`` — the *Quality - Duration* entry (GUID ``c71b82fe…``), whose
  ``PrimaryFilter`` is ``IncludeMilestone=false`` + ``IncludeComplete=false``: **22** on the Large
  Test File where the tool's ribbon tile (GUID ``a80debf6…``, all statuses) reads 43;
* ``Merge Hotspot (Predecessors >2)`` (GUID ``c5196e05…``) — ``IncludeInProgress=false`` +
  ``IncludeComplete=false``, i.e. **planned only**: 125 where the tile reads 156;
* ``Total # Predecessor Lags`` (GUID ``37c0df8f…``) — planned only, and a count of **links**
  (``sum(numberoflags)``, the Bible's own Description: "predecessor relationships with lags"),
  not of activities: 2 where the tool's activity-counting ``Number of Lags`` tile reads 8.

Why this oracle can refute the tool and not merely agree with it: nothing in the engine produced
any figure here. Both sides come from the vendor's own workbooks —

* ``… - Acumen Fuse - Detailed Metric Report.xlsx`` carries **one column per metric** (the metric
  name in row 11, the metric group in row 10) and an ``X`` on every activity the metric counted,
  with the activity's UniqueID in column D; row 12 is Fuse's total and row 14 its **Record
  Count** (the filtered population the metric scored).
* ``… - Acumen Fuse -Metric History Report.xlsx`` carries the same three figures as labelled rows.

So the two vendor reports are cross-checked against each other first (a transcription slip in
either is caught before the engine is judged), and only then is the engine asked to reproduce the
mark set **by UniqueID**, the count, and the population. A rule that gets the right total from the
wrong activities fails here.

Addressing is **by metric name**, never by column number: a column that moves in a re-export is a
missing-label failure, not a silent read of the neighbouring metric.

Absence semantics mirror ``test_fuse_metric_history_oracle``: skip only when the whole intake
directory is absent; a missing individual workbook FAILS.
"""

from __future__ import annotations

import gzip
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.metrics import compute_schedule_quality
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
LTF_GOLDEN = REPO / "tests" / "fixtures" / "golden" / "fuse_ltf"

_DETAIL = ACUMEN / "Large Test File vs Large Test File2 - Acumen Fuse - Detailed Metric Report.xlsx"
_HISTORY = ACUMEN / "Large Test File vs Large Test File2 - Acumen Fuse -Metric History Report.xlsx"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
Rows = dict[int, dict[int, str]]

#: Detailed Metric Report layout (Fuse v8.11.0 export): metric group / metric name / total /
#: Record Count header rows, then one row per activity from row 16 with its UniqueID in column D.
_ROW_GROUP, _ROW_NAME, _ROW_TOTAL, _ROW_RECORD_COUNT, _ROW_FIRST_ACTIVITY = 10, 11, 12, 14, 16
_COL_ACTIVITY = 4

#: metric id -> (Bible / report label, the metric group that disambiguates a repeated label)
_VARIANTS: dict[str, tuple[str, str]] = {
    "insufficient_detail_history": ("Insufficient Detail™", "Quality - Duration"),
    "merge_hotspot_predecessors_gt2": (
        "Merge Hotspot (Predecessors >2)",
        "Quality - Logic Hotspots - Predecessors",
    ),
    "total_predecessor_lags": (
        "Total # Predecessor Lags",
        "Quality - Logic Hotspots - Predecessors",
    ),
}

#: sheet in both vendor workbooks -> the golden MSPDI conversion of the file Fuse scored
_FILES: dict[str, str] = {
    "Large-Test-File": "Large_Test_File.mspdi.xml.gz",
    "Large-Test-File2": "Large_Test_File2.mspdi.xml.gz",
}


def _col(ref: str) -> int:
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + ord(ch.upper()) - 64
    return n


def _load_workbook(path: Path) -> dict[str, Rows]:
    """{sheet: {row: {col: raw}}}, std-lib; SpreadsheetGear omits ``r=`` so both counters run."""
    assert path.exists(), f"vendor workbook missing while the intake exists: {path.name}"
    out: dict[str, Rows] = {}
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            shared = [
                "".join(t.text or "" for t in si.iter(f"{_M}t"))
                for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_M}si")
            ]
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") or "" for r in rels.findall(f"{_RELS}Relationship")}
        for sh in wb.iter(f"{_M}sheet"):
            t = target.get(sh.get(f"{_R}id") or "", "")
            part = t if t.startswith("xl/") else "xl/" + t.lstrip("/")
            if part not in names:
                continue
            rows: Rows = {}
            ri = 0
            for row in ET.fromstring(zf.read(part)).iter(f"{_M}row"):
                ra = row.get("r")
                ri = int(ra) if ra else ri + 1
                ci = 0
                for c in row.findall(f"{_M}c"):
                    ref = c.get("r")
                    ci = _col(ref) if ref else ci + 1
                    v = c.find(f"{_M}v")
                    if v is None or v.text is None:
                        continue
                    rows.setdefault(ri, {})[ci] = (
                        shared[int(v.text)] if c.get("t") == "s" else v.text
                    )
            out[sh.get("name") or ""] = rows
    return out


def _metric_column(rows: Rows, label: str, group: str) -> int:
    """The Detailed Metric Report column whose row-11 name is ``label`` inside ``group``."""
    names, groups = rows.get(_ROW_NAME, {}), rows.get(_ROW_GROUP, {})
    hits = [
        c
        for c, text in names.items()
        if text.strip() == label and groups.get(c, "").strip() == group
    ]
    assert len(hits) == 1, (
        f"Detailed Metric Report: {label!r} in group {group!r} matched {len(hits)} columns "
        "— the report's layout moved; re-read it before trusting any figure here"
    )
    return hits[0]


def _marked_uids(rows: Rows, column: int) -> tuple[int, ...]:
    """The UniqueIDs Fuse marked ``X`` in this metric's column, ascending."""
    out = []
    for r in sorted(rows):
        if r < _ROW_FIRST_ACTIVITY:
            continue
        cells = rows[r]
        uid = cells.get(_COL_ACTIVITY, "").strip()
        if not uid.isdigit():
            continue
        if cells.get(column, "").strip().upper() == "X":
            out.append(int(uid))
    return tuple(sorted(out))


def _history_row(rows: Rows, label: str) -> tuple[str, str]:
    """The Metric History row for ``label`` → (Large Test File value, Large Test File2 value)."""
    hits = [r for r in sorted(rows) if rows[r].get(2, "").strip() == label]
    assert hits, f"Metric History label {label!r} not found — the oracle's population moved"
    values = {(rows[r].get(4, ""), rows[r].get(7, "")) for r in hits}
    assert len(values) == 1, f"Metric History {label!r} disagrees with itself across rows: {values}"
    return values.pop()


def _schedule(filename: str) -> Schedule:
    path = LTF_GOLDEN / filename
    assert path.exists(), f"golden fixture missing: {path}"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return parse_mspdi_text(fh.read())


@pytest.fixture(scope="module")
def detail() -> dict[str, Rows]:
    return _load_workbook(_DETAIL)


@pytest.fixture(scope="module")
def history() -> dict[str, Rows]:
    return _load_workbook(_HISTORY)


@pytest.mark.parametrize("metric_id", sorted(_VARIANTS))
def test_the_two_vendor_reports_agree_before_the_engine_is_judged(
    metric_id: str, detail: dict[str, Rows], history: dict[str, Rows]
) -> None:
    """Fuse's Metric History total == the count of Fuse's own marks in the Detailed report."""
    label, group = _VARIANTS[metric_id]
    hist_rows = next(iter(history.values()))
    hist = _history_row(hist_rows, label)
    for (sheet, _fixture), expected in zip(_FILES.items(), hist, strict=True):
        rows = detail[sheet]
        column = _metric_column(rows, label, group)
        total = rows[_ROW_TOTAL].get(column, "")
        assert total == expected, (
            f"{label} on {sheet}: Detailed report total {total!r} != Metric History {expected!r}"
        )
        if metric_id != "total_predecessor_lags":  # a link SUM, not one mark per counted unit
            marks = _marked_uids(rows, column)
            assert len(marks) == int(total), (
                f"{label} on {sheet}: {len(marks)} marked activities != the total {total}"
            )


@pytest.mark.parametrize("sheet,fixture", sorted(_FILES.items()))
@pytest.mark.parametrize("metric_id", sorted(_VARIANTS))
def test_the_engine_reproduces_fuses_marks_uid_exact(
    metric_id: str, sheet: str, fixture: str, detail: dict[str, Rows]
) -> None:
    """The tool's variant metric == Fuse's own per-activity marks, by UniqueID."""
    label, group = _VARIANTS[metric_id]
    rows = detail[sheet]
    column = _metric_column(rows, label, group)
    expected_uids = _marked_uids(rows, column)
    expected_total = int(rows[_ROW_TOTAL][column])
    expected_population = int(rows[_ROW_RECORD_COUNT][column])

    quality = compute_schedule_quality(_schedule(fixture))
    assert metric_id in quality, (
        f"{label!r} is not exposed as its own metric — a reader of the Metric History report "
        f"cannot find its figure ({expected_total}) in the tool (R-50)"
    )
    got = quality[metric_id]
    assert got.offender_uids == expected_uids, (
        f"{label} on {sheet}: the tool marks "
        f"{sorted(set(got.offender_uids) - set(expected_uids))[:10]} Fuse does not, and misses "
        f"{sorted(set(expected_uids) - set(got.offender_uids))[:10]}"
    )
    assert got.count == expected_total, f"{label} on {sheet}: {got.count} != Fuse {expected_total}"
    assert got.population == expected_population, (
        f"{label} on {sheet}: population {got.population} != Fuse's Record Count "
        f"{expected_population} — the filter admits a different activity set"
    )


@pytest.mark.parametrize("sheet,fixture", sorted(_FILES.items()))
def test_each_variant_is_a_different_metric_from_its_same_named_tile(
    sheet: str, fixture: str, detail: dict[str, Rows]
) -> None:
    """The point of R-50: the variant and the tile are NOT the same number, so both must exist."""
    quality = compute_schedule_quality(_schedule(fixture))
    pairs = (
        ("insufficient_detail_history", "insufficient_detail"),
        ("merge_hotspot_predecessors_gt2", "merge_hotspot"),
        ("total_predecessor_lags", "number_of_lags"),
    )
    for variant, tile in pairs:
        assert variant in quality and tile in quality, f"{variant} / {tile} missing"
        assert quality[variant].count < quality[tile].count, (
            f"{sheet}: {variant} ({quality[variant].count}) should be a strict subset figure of "
            f"{tile} ({quality[tile].count}) — if they are equal the variant is not exposed, it "
            "is the tile under a second name"
        )
