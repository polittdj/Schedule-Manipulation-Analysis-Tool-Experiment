"""ENGINE==FUSE against the operator's multi-project Fuse v8.11.0 Metric History workbooks and the
Hard_File EVM ribbon — read from the vendor ``.xlsx`` with the std-lib (no transcription step).

Three workbooks under ``00_REFERENCE_INTAKE/`` that no test read before 2026-09-07 (ADR-0473):

* ``AlltheProjects - Metric History Report.xlsx`` — twelve projects on one report, among them the
  cost-loaded EVM1/EVM2, TP4 v1-v5, Project2 and Project5_TAMPERED;
* ``Large Test File vs Large Test File2 - Acumen Fuse -Metric History Report.xlsx`` — the 1,723-
  activity operator schedule, two snapshots side by side;
* ``Hard_File_update2 vs update3_Fuse - Metric History Report.xlsx`` and the ``... - Excel .xlsx``
  ribbons — the cost-loaded Hard_File series with BCWS / BCWP / ACWP / BAC / SPI / CPI / TCPI.

What they settled (each row here failed on the pre-ADR-0473 tree — red first):

* the §C **baseline-compliance block** scores the Bible's CURRENT Finish/Start (actual once
  finished, else the forecast), not the actual dates only — 0 on time where Fuse read 5/5 (EVM1),
  117 where Fuse read 159 (Large Test File2); exact on ten oracles now, every one asserted below;
* the ribbon **Negative Float** classifies the stored slack in whole days (a -0.29 d slack is
  Fuse's zero float: 122 on Large Test File2, the tool read 123);
* **BCWS** is time-phased (linear over the baseline span): 64,240 exact on Hard_File_updated2;
* MSPDI **currency is in hundredths**: BAC 133,400 on the Hard_File ribbon, the tool read
  13,340,000.

The two Large Test File fixtures under ``golden/fuse_ltf/`` are fresh MPXJ conversions of the
intake ``mpp/Large Test File.mpp`` / ``Large Test File2.mpp`` — the files Fuse scored. The older
``golden/ssi_uid152/Large_Test_File.mspdi.xml.gz`` (the SSI driving-slack oracle's fixture) is
NOT that file: its stored slack reads 31 negative-float activities where Fuse and the fresh
conversion read 41, so it stays the SSI fixture and is not a Fuse oracle (ADR-0473).

Absence semantics mirror ``test_fuse_transcription_oracle``: skip only when the whole intake
directory is absent; a missing individual workbook FAILS.
"""

from __future__ import annotations

import gzip
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.metrics import compute_schedule_quality
from schedule_forensics.engine.metrics._common import non_summary, round_half_up
from schedule_forensics.engine.metrics.evm import compute_baseline_compliance, compute_evm_indices
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
FIXTURES = REPO / "tests" / "fixtures"
ACUMEN = INTAKE / "acumen_v8.11.0"

_ALL_PROJECTS = INTAKE / "AlltheProjects - Metric History Report.xlsx"
_LTF_HISTORY = (
    ACUMEN / "Large Test File vs Large Test File2 - Acumen Fuse -Metric History Report.xlsx"
)
_HF23_HISTORY = ACUMEN / "Hard_File_update2 vs update3_Fuse - Metric History Report.xlsx"
_HF12_RIBBON = ACUMEN / "Hard_File_update vs update2_Fuse - Excel .xlsx"
_WORKBOOKS = (_ALL_PROJECTS, _LTF_HISTORY, _HF23_HISTORY, _HF12_RIBBON)

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


def _compliance_block(rows: Rows, col: int) -> dict[str, float]:
    """The 'Baseline Compliance' block: the rows from 'Time Now' to 'Baseline Start Compliance'."""
    labels = (
        "Forecast to be Finished",
        "Completed On Time",
        "Completed Late",
        "Not Completed",
        "Baseline Finish Compliance",
        "Forecast to be Started",
        "Started On Time",
        "Started Late",
        "Not Started",
        "Baseline Start Compliance",
    )
    starts = [r for r in sorted(rows) if rows[r].get(2, "").strip() == "Time Now"]
    assert starts, "no 'Time Now' row — not a Metric History sheet"
    block: dict[str, float] = {}
    for r in range(starts[0], starts[0] + 12):
        label = rows.get(r, {}).get(2, "").strip()
        if label in labels and label not in block:
            block[label] = float(rows[r][col])
    assert set(block) == set(labels), sorted(set(labels) - set(block))
    return block


def _sheet(book: dict[str, Rows], name: str) -> Rows:
    for k, v in book.items():
        if k == name:
            return v
    raise AssertionError(f"sheet {name!r} not in {sorted(book)}")


def _gz(rel: str) -> Schedule:
    path = FIXTURES / "golden" / rel
    return parse_mspdi_text(
        gzip.decompress(path.read_bytes()).decode("utf-8"), source_file=path.name
    )


# --- the oracles: (label, schedule loader, workbook, sheet, value column) ------------------
_LTF_SHEET = "Large-Test-File"
_HF23_SHEET = "Hard_File_updated2"
_HF2_GZ = "Hard_File_updated2.mspdi.xml.gz"
_HF3_GZ = "Hard_File_updated3.mspdi.xml.gz"
_ORACLES: list[tuple[str, str, Path, str, int]] = [
    ("EVM1", "golden/evm/EVM1.mspdi.xml", _ALL_PROJECTS, "EVM1", 4),
    ("EVM2", "golden/evm/EVM2.mspdi.xml", _ALL_PROJECTS, "EVM2", 4),
    ("TP4v1", "test_projects/TP4_DataCenter_v1.xml", _ALL_PROJECTS, "TP4_DataCenter_v1", 4),
    ("TP4v3", "test_projects/TP4_DataCenter_v3.xml", _ALL_PROJECTS, "TP4_DataCenter_v3", 4),
    ("TP4v4", "test_projects/TP4_DataCenter_v4.xml", _ALL_PROJECTS, "TP4_DataCenter_v4", 4),
    ("TP4v5", "test_projects/TP4_DataCenter_v5.xml", _ALL_PROJECTS, "TP4_DataCenter_v5", 4),
    ("Project2", "golden/project2_5/Project2.mspdi.xml", _ALL_PROJECTS, "Project2", 4),
    ("Project5", "golden/project2_5/Project5.mspdi.xml", _ALL_PROJECTS, "Project5_TAMPERED", 4),
    (
        "LargeTestFile",
        "gz:fuse_ltf/Large_Test_File.mspdi.xml.gz",
        _LTF_HISTORY,
        "Large-Test-File",
        4,
    ),
    (
        "LargeTestFile2",
        "gz:fuse_ltf/Large_Test_File2.mspdi.xml.gz",
        _LTF_HISTORY,
        "Large-Test-File",
        7,
    ),
    (
        "HardFile_updated2",
        "gz:fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
        _HF23_HISTORY,
        "Hard_File_updated2",
        4,
    ),
    (
        "HardFile_updated3",
        "gz:fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
        _HF23_HISTORY,
        "Hard_File_updated2",
        7,
    ),
]


def _schedule(spec: str) -> Schedule:
    if spec.startswith("gz:"):
        return _gz(spec[3:])
    return parse_mspdi(FIXTURES / spec)


_ENGINE_KEYS = {
    "Forecast to be Finished": "forecast_to_be_finished",
    "Completed On Time": "completed_on_time",
    "Completed Late": "completed_late",
    "Not Completed": "not_completed",
    "Forecast to be Started": "forecast_to_be_started",
    "Started On Time": "started_on_time",
    "Started Late": "started_late",
    "Not Started": "not_started",
}


@pytest.mark.parametrize("label,spec,book,sheet,col", _ORACLES, ids=[o[0] for o in _ORACLES])
def test_baseline_compliance_block_engine_equals_fuse(
    label: str, spec: str, book: Path, sheet: str, col: int
) -> None:
    """Every count in Fuse's 'Baseline Compliance' block, and both ratios at Fuse's 2 dp."""
    fuse = _compliance_block(_sheet(_load_workbook(book), sheet), col)
    c = compute_baseline_compliance(_schedule(spec))
    for fl, key in _ENGINE_KEYS.items():
        assert c[key].count == int(fuse[fl]), (
            f"{label} {fl}: engine {c[key].count} != Fuse {fuse[fl]:g}"
        )
    # Fuse publishes the two ratios at 2 dp from the counts; derive them from the counts too (the
    # 1-dp percentage the result carries would double-round 8/13 = 0.6154 to 0.61)
    bfc = c["baseline_finish_compliance"]
    bsc = c["baseline_start_compliance"]
    assert round_half_up(bfc.count / bfc.population, 2) == round(
        fuse["Baseline Finish Compliance"], 2
    ), label
    assert round_half_up(bsc.count / bsc.population, 2) == round(
        fuse["Baseline Start Compliance"], 2
    ), label


def _history_value(rows: Rows, label: str, col: int, occurrence: int = 0) -> float:
    hits = [r for r in sorted(rows) if rows[r].get(2, "").strip() == label]
    assert len(hits) > occurrence, (label, len(hits))
    return float(rows[hits[occurrence]][col])


def test_negative_float_is_classified_in_whole_days_on_large_test_file2() -> None:
    """The Metric History's first 'Negative Float' row (the Schedule Errors section) on Large
    Test File2 is 122; the tool read 123 until the -139-minute (-0.29 d) slack of one activity
    was classified as Fuse classifies it — zero float — instead of as negative."""
    rows = _sheet(_load_workbook(_LTF_HISTORY), "Large-Test-File")
    assert _history_value(rows, "Negative Float", 7) == 122
    assert _history_value(rows, "Negative Float", 4) == 41
    sq2 = compute_schedule_quality(_schedule("gz:fuse_ltf/Large_Test_File2.mspdi.xml.gz"))
    assert sq2["negative_float"].count == 122
    sq1 = compute_schedule_quality(_schedule("gz:fuse_ltf/Large_Test_File.mspdi.xml.gz"))
    assert sq1["negative_float"].count == 41


def _ribbon_rows(book: Path) -> list[dict[str, str]]:
    """The 'Ribbon View' data rows keyed by header label (the header row is the one holding CPI)."""
    rows = _sheet(_load_workbook(book), "Ribbon View")
    hdr_row = next(r for r in sorted(rows) if any(v == "CPI" for v in rows[r].values()))
    hdr = rows[hdr_row]
    out: list[dict[str, str]] = []
    for r in sorted(rows):
        if r <= hdr_row:
            continue
        rec: dict[str, str] = {}
        for c in sorted(rows[r]):
            if c in hdr and hdr[c] not in rec:  # the COST columns come first; the work-based
                rec[hdr[c]] = rows[r][c]  # BAC / EAC / AC (ACWP) repeat the labels further right
        if "Status Date " in rec:
            out.append(rec)
    return out


def test_hard_file_evm_aggregates_and_indices_equal_the_fuse_ribbon() -> None:
    """The Hard_File_updated / updated2 ribbon (status 46245 / 46275): BAC, BCWP and ACWP exact in
    currency units, BCWS exact on updated2 (a straddling activity on a 16-hour resource calendar
    leaves 16,150 vs 16,000 on updated — documented in ADR-0473), CPI exact at 2 dp on both,
    SPI / TCPI within 0.01 (Fuse's ACWP-to-time-now trims 342 on updated2)."""
    ribbon = {rec["Status Date "]: rec for rec in _ribbon_rows(_HF12_RIBBON)}
    updated = ribbon["46245"]
    updated2 = ribbon["46275"]
    assert (updated["BAC"], updated["EV (BCWP)"], updated["AC (ACWP)"], updated["PV (BCWS)"]) == (
        "133400",
        "16800",
        "20800",
        "16000",
    )
    assert (updated2["BAC"], updated2["EV (BCWP)"], updated2["PV (BCWS)"]) == (
        "133400",
        "49700",
        "64240",
    )

    from schedule_forensics.engine.metrics.evm import _planned_value

    for name, rec, bcws_tol in (
        ("Hard_File_updated", updated, 150.0),
        ("Hard_File_updated2", updated2, 0.0),
    ):
        sch = _gz(f"fuse_hardfile/{name}.mspdi.xml.gz")
        ts = non_summary(sch)
        bac = sum(t.budgeted_cost for t in ts)
        bcwp = sum(t.budgeted_cost * t.percent_complete / 100.0 for t in ts)
        acwp = sum(t.actual_cost or 0.0 for t in ts)
        assert bac == float(rec["BAC"]), (name, "BAC", bac)
        assert round(bcwp) == float(rec["EV (BCWP)"]), (name, "BCWP", bcwp)
        assert abs(_planned_value(sch, ts) - float(rec["PV (BCWS)"])) <= bcws_tol, (name, "BCWS")
        if name == "Hard_File_updated":
            assert acwp == float(rec["AC (ACWP)"]), (name, "ACWP", acwp)
        idx = compute_evm_indices(sch)
        assert idx["cpi"].value == round(float(rec["CPI"]), 2), (name, "CPI", idx["cpi"].value)
        assert abs(idx["spi"].value - float(rec["SPI"])) <= 0.0101, (name, "SPI", idx["spi"].value)
        assert abs(idx["tcpi"].value - float(rec["TCPI(BAC)"])) <= 0.0101, (
            name,
            "TCPI",
            idx["tcpi"].value,
        )
        # the R-01 disclosure: every started, budgeted activity here carries an actual cost
        assert idx["cpi"].count == 0 and idx["cpi"].offender_uids == ()


def test_currency_scale_reaches_the_task_level() -> None:
    """The root task of Hard_File_updated is written <Cost>13740000</Cost> in the MSPDI and reads
    $137,400 — the Fuse ribbon's '$ Total Cost' — after the hundredths conversion."""
    sch = _gz("fuse_hardfile/Hard_File_updated.mspdi.xml.gz")
    root = next(t for t in sch.tasks if t.unique_id == 0)
    assert (root.cost, root.actual_cost, root.budgeted_cost) == (137400.0, 20800.0, 133400.0)
