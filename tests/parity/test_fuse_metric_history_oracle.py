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

import datetime as dt
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
_HF23_RIBBON = ACUMEN / "Hard_File_update2 vs update3_Fuse - Excel .xlsx"
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
    currency units, BCWS exact on BOTH — 16,000 on updated since ADR-0492 (R-46: the file's own
    time-phased baseline cost; the project-calendar proration read 16,150 for a straddling
    activity on a 16-hour resource calendar), CPI exact at 2 dp on both, SPI / TCPI within 0.01
    (updated2's ribbon ACWP is 64,105 against the file's 63,763.08 — the Logistics Apprentice's
    hours priced at the status-date rate, ADR-0511; pinned below from the bookings' records)."""
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
        ("Hard_File_updated", updated, 0.0),
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


def test_hard_file_updated3_bcws_equals_the_fuse_ribbon_and_names_its_two_mechanisms() -> None:
    """The updated2-vs-updated3 ribbon (status 46275 / 46307; a workbook no test had read):
    PV (BCWS) 64,240 / 110,440. On updated3 the file's own series (ADR-0492, R-46) settles the
    two cases the linear rule could only agree with by construction: UID 270's three project
    days are ONE merged block of 4,800 the status date falls inside — 3,200 planned, two of
    three days in working minutes of the booking's calendar — and UID 257's 800 of baseline cost
    has no assignment series at all (a booking baselined and since removed) and accrues by the
    linear rule, whole. On updated, UID 187's 16-hour crew plans 3,600 of its 6,000 by the
    status date, and the ribbon's 16,000 is exact. BAC / BCWP / ACWP on updated3 (the ribbon's
    121,800 / 53,715 / 66,245) are R-45's, pinned below from the bookings' records (ADR-0511)."""
    ribbon = {rec["Status Date "]: rec for rec in _ribbon_rows(_HF23_RIBBON)}
    assert (ribbon["46275"]["PV (BCWS)"], ribbon["46307"]["PV (BCWS)"]) == ("64240", "110440")

    from schedule_forensics.engine.metrics.evm import _planned_value

    sch3 = _gz("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz")
    assert _planned_value(sch3, non_summary(sch3)) == pytest.approx(110440.0)
    t270, t257 = sch3.task_by_id(270), sch3.task_by_id(257)
    (b270,) = t270.resource_assignments
    (block,) = b270.baseline_cost_pieces
    assert block.cost == 4800.0 and block.start < sch3.status_date < block.finish
    assert _planned_value(sch3, [t270]) == pytest.approx(3200.0)
    assert t257.budgeted_cost == 800.0
    assert not any(a.baseline_cost_pieces for a in t257.resource_assignments)
    assert _planned_value(sch3, [t257]) == pytest.approx(800.0)
    sch2 = _gz("fuse_hardfile/Hard_File_updated2.mspdi.xml.gz")
    assert _planned_value(sch2, non_summary(sch2)) == pytest.approx(64240.0)
    sch1 = _gz("fuse_hardfile/Hard_File_updated.mspdi.xml.gz")
    assert _planned_value(sch1, [sch1.task_by_id(187)]) == pytest.approx(3600.0)
    assert _planned_value(sch1, non_summary(sch1)) == pytest.approx(16000.0)


# --- SPI(t) — Acumen (R-47, ADR-0495): the per-activity average against EVERY Metric History sheet
# that scores a committed fixture, and its population against the Detailed Metric Report's own
# Record Count. Red-first (2026-09-15): Large Test File read 8.24 / 716 where Fuse reads 8.22 / 717,
# File2 8.17 / 723 where Fuse reads 8.14 / 726 — the engine required a baseline to admit a started
# activity; Fuse admits every started activity with a non-zero actual span and scores an unbaselined
# member as the formula's blank-as-0 term. Every other sheet was exact before and after.
# ------------------------------------------------------------------------------------------------
_LTF_DETAIL = (
    ACUMEN / "Large Test File vs Large Test File2 - Acumen Fuse - Detailed Metric Report.xlsx"
)
_SPI_T_ORACLES: list[tuple[str, str, Path, str, int]] = [
    ("EVM1", "golden/evm/EVM1.mspdi.xml", _ALL_PROJECTS, "EVM1", 4),
    ("EVM2", "golden/evm/EVM2.mspdi.xml", _ALL_PROJECTS, "EVM2", 4),
    ("TP4v1", "test_projects/TP4_DataCenter_v1.xml", _ALL_PROJECTS, "TP4_DataCenter_v1", 4),
    ("TP4v2", "test_projects/TP4_DataCenter_v2.xml", _ALL_PROJECTS, "TP4_DataCenter_v2", 4),
    ("TP4v3", "test_projects/TP4_DataCenter_v3.xml", _ALL_PROJECTS, "TP4_DataCenter_v3", 4),
    ("TP4v4", "test_projects/TP4_DataCenter_v4.xml", _ALL_PROJECTS, "TP4_DataCenter_v4", 4),
    ("TP4v5", "test_projects/TP4_DataCenter_v5.xml", _ALL_PROJECTS, "TP4_DataCenter_v5", 4),
    ("Project2", "golden/project2_5/Project2.mspdi.xml", _ALL_PROJECTS, "Project2", 4),
    ("Project5", "golden/project2_5/Project5.mspdi.xml", _ALL_PROJECTS, "Project5_TAMPERED", 4),
    ("JackedUp1", "mspdi/jacked_up_schedule_1.xml", _ALL_PROJECTS, "Jacked-Up-Schedule-1", 4),
    ("JackedUp2", "mspdi/jacked_up_schedule_2.xml", _ALL_PROJECTS, "Jacked-up-Schedule-2", 4),
    ("HardFile", "gz:fuse_hardfile/Hard_File.mspdi.xml.gz", _ALL_PROJECTS, "Hard_File", 4),
    (
        "HardFile_updated",
        "gz:fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
        _ALL_PROJECTS,
        "Hard_File_updated",
        4,
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
    (
        "HardFile_updated4_24h",
        "gz:ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz",
        _ALL_PROJECTS,
        "Hard_File_updated4-24-hour-cal",
        4,
    ),
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
]


def _spi_t_cell(rows: Rows, col: int) -> str:
    """The Metric History's 'SPI(t)' row (the Bible's per-activity average), raw cell text."""
    hits = [r for r in sorted(rows) if rows[r].get(2, "").strip() == "SPI(t)"]
    assert hits, "no 'SPI(t)' row — not a Metric History sheet"
    return rows[hits[0]][col].strip()


@pytest.mark.parametrize(
    "label,spec,book,sheet,col", _SPI_T_ORACLES, ids=[o[0] for o in _SPI_T_ORACLES]
)
def test_acumen_spi_t_engine_equals_fuse(
    label: str, spec: str, book: Path, sheet: str, col: int
) -> None:
    """ENGINE == FUSE on the 'SPI(t)' row of every Metric History sheet with a committed fixture;
    a Fuse 'N/A' (nothing started) is the engine's NOT_APPLICABLE, never a fabricated figure."""
    from schedule_forensics.engine.metrics import CheckStatus

    cell = _spi_t_cell(_sheet(_load_workbook(book), sheet), col)
    res = compute_evm_indices(_schedule(spec))["spi_t_acumen"]
    if cell == "N/A":
        assert res.status is CheckStatus.NOT_APPLICABLE, (label, res.value)
        return
    assert res.status is not CheckStatus.NOT_APPLICABLE, label
    assert res.value == round_half_up(float(cell), 2), (label, res.value, cell)


def _record_count(path: Path, sheet: str, metric: str) -> int:
    """The Detailed Metric Report's 'Record Count' (row 14) under ``metric``'s column (row 11):
    the number of activities Fuse admitted to that metric. Streams the 9 MB sheet and stops at
    row 14 — the report's activity rows are never materialised."""
    assert path.exists(), f"vendor workbook missing while the intake exists: {path.name}"
    with zipfile.ZipFile(path) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") or "" for r in rels.findall(f"{_RELS}Relationship")}
        part = ""
        for sh in wb.iter(f"{_M}sheet"):
            if sh.get("name") == sheet:
                t = target[sh.get(f"{_R}id") or ""]
                part = t if t.startswith("xl/") else "xl/" + t.lstrip("/")
        assert part, f"sheet {sheet!r} not in {path.name}"
        shared = [
            "".join(t.text or "" for t in si.iter(f"{_M}t"))
            for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_M}si")
        ]
        header: dict[int, str] = {}
        with zf.open(part) as fh:
            for _ev, el in ET.iterparse(fh):
                if el.tag != f"{_M}row":
                    continue
                r = int(el.get("r") or 0)
                cells: dict[int, str] = {}
                for c in el.findall(f"{_M}c"):
                    v = c.find(f"{_M}v")
                    if v is None or v.text is None:
                        continue
                    cells[_col(c.get("r") or "")] = (
                        shared[int(v.text)] if c.get("t") == "s" else v.text
                    )
                if r == 11:
                    header = cells
                elif r == 14:
                    assert cells.get(5, "").strip() == "Record Count", cells.get(5)
                    cols = [k for k, v in header.items() if v.strip() == metric]
                    assert len(cols) == 1, (metric, cols)
                    return int(float(cells[cols[0]]))
                el.clear()
    raise AssertionError(f"no 'Record Count' row in {sheet!r}")


@pytest.mark.parametrize(
    "spec,sheet",
    [
        ("gz:fuse_ltf/Large_Test_File.mspdi.xml.gz", "Large-Test-File"),
        ("gz:fuse_ltf/Large_Test_File2.mspdi.xml.gz", "Large-Test-File2"),
    ],
    ids=["LargeTestFile", "LargeTestFile2"],
)
def test_acumen_spi_t_population_equals_the_fuse_record_count(spec: str, sheet: str) -> None:
    """The engine averages exactly the activities Fuse averaged — the Detailed Metric Report's
    'Record Count' under 'SPI(t)' (717 on Large Test File, 726 on File2) — not merely the same
    2-dp figure. Red-first: 716 / 723 (the started-unbaselined members were skipped)."""
    res = compute_evm_indices(_schedule(spec))["spi_t_acumen"]
    assert res.population == _record_count(_LTF_DETAIL, sheet, "SPI(t)"), (sheet, res.population)


# --- R-45 (ADR-0511): EV / AC follow the booking's time-phased record; the ribbon's BAC is the
# workbook's time line. Red-first (2026-09-18): the pristine engine read updated3's EV 59,340 and
# ACWP 67,703.08 where the ribbon reads 53,715 / 66,245, and updated2's ACWP 63,763.08 for 64,105.

_HF23_FORENSIC = ACUMEN / "Hard_File_updated2 vs update3 Forensic Analysis Report.xlsx"


def _ribbon_rows_with_header(book: Path) -> tuple[dict[int, str], list[dict[str, str]]]:
    rows = _sheet(_load_workbook(book), "Ribbon View")
    hdr_row = next(r for r in sorted(rows) if any(v == "CPI" for v in rows[r].values()))
    return rows[hdr_row], _ribbon_rows(book)


def test_hard_file_ev_and_acwp_equal_the_fuse_ribbon_from_the_bookings_records() -> None:
    """The three progressed Hard_File snapshots against the updated-vs-updated2 and
    updated2-vs-updated3 ribbons: EV (BCWP) exact — 16,800 / 49,700 / 53,715, the last being the
    file's 59,340 less UID 290's 5,625 (22 of 40 booked hours performed against a 100 % percent)
    — and AC (ACWP) to the unit the ribbon prints — 20,800 / 64,105 / 66,245 (the engine's
    20,800.00 / 64,104.61 / 66,244.61: the Logistics Apprentice's 17.077 h at the status-date row
    30, UID 290's record 16 h x 200 + 6 h x 300). CPI exact at 2 dp on all three; SPI exact; TCPI
    exact on updated / updated2. The disagreement is disclosed on SPI: UID 290 alone, on
    updated3."""
    ribbon12 = {rec["Status Date "]: rec for rec in _ribbon_rows(_HF12_RIBBON)}
    ribbon23 = {rec["Status Date "]: rec for rec in _ribbon_rows(_HF23_RIBBON)}
    from schedule_forensics.engine.metrics.evm import (
        _actual_cost_of_work_performed,
        _earned_value,
    )

    for name, rec, ev_expected, disclosed in (
        ("Hard_File_updated", ribbon12["46245"], 16800.0, ()),
        ("Hard_File_updated2", ribbon23["46275"], 49700.0, ()),
        ("Hard_File_updated3", ribbon23["46307"], 53715.0, (290,)),
    ):
        sch = _gz(f"fuse_hardfile/{name}.mspdi.xml.gz")
        ts = non_summary(sch)
        ev, disagreeing = _earned_value(ts)
        assert ev == pytest.approx(ev_expected) and float(rec["EV (BCWP)"]) == ev_expected, name
        assert disagreeing == disclosed, (name, disagreeing)
        acwp = _actual_cost_of_work_performed(sch, ts)
        assert round(acwp) == float(rec["AC (ACWP)"]), (name, "ACWP", acwp)
        idx = compute_evm_indices(sch)
        assert idx["cpi"].value == round(float(rec["CPI"]), 2), (name, "CPI", idx["cpi"].value)
        assert idx["spi"].value == round(float(rec["SPI"]), 2), (name, "SPI", idx["spi"].value)
        assert idx["spi"].offender_uids == disclosed, name
        if name != "Hard_File_updated3":  # updated3's ribbon TCPI runs on the time line's BAC
            assert idx["tcpi"].value == round(float(rec["TCPI(BAC)"]), 2), (name, "TCPI")
    sch3 = _gz("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz")
    assert _actual_cost_of_work_performed(sch3, non_summary(sch3)) == pytest.approx(
        66244.61, abs=0.01
    )
    assert _earned_value([sch3.task_by_id(290)])[0] == pytest.approx(6875.0)  # 22 / 40 x 12,500


def test_the_updated3_ribbons_bac_is_the_workbooks_time_line_not_a_fuse_definition() -> None:
    """Fuse's own whole-file Budget Cost for updated3 (the Forensic report's ``Projects`` sheet) is
    133,400 — the engine's BAC to the unit, and updated2's. The ribbon's 121,800 is the BAC of the
    activities that START before the workbook's time line ends: the ``Time Line`` header is five
    monthly ribbons (2026-07 to 2026-11, built around updated2's 11-06 finish) and updated3,
    finishing
    12-12, carries 15 activities starting in December — 11,600 of baseline cost — which Fuse's own
    per-activity view of updated3 lists nowhere. SPI's denominator (BCWS) is untouched by the
    window; TCPI(BAC) on the ribbon recomputes to 1.23 only with the window's BAC."""
    import gzip
    import xml.etree.ElementTree as ET

    projects = _sheet(_load_workbook(_HF23_FORENSIC), "Projects")
    hdr = next(r for r in sorted(projects) if projects[r].get(1) == "Name")
    # the sheet pairs each label over a change-marker column and a value column: the value is last
    budget_col = max(c for c, v in projects[hdr].items() if v == "Budget Cost")
    fuse_whole_file = {
        projects[r][1]: float(projects[r][budget_col]) for r in sorted(projects) if r > hdr
    }
    assert fuse_whole_file == {"Hard_File_updated2": 133400.0, "Hard_File_updated3": 133400.0}
    hdr_cells, rows = _ribbon_rows_with_header(_HF23_RIBBON)
    serials = sorted({int(v) for v in hdr_cells.values() if v.isdigit()})
    assert serials == [46204, 46235, 46266, 46296, 46327]  # 2026-07-01 … 2026-11-01, monthly
    last_ribbon = dt.date(1899, 12, 30) + dt.timedelta(days=serials[-1])
    window_end = dt.datetime(
        last_ribbon.year + last_ribbon.month // 12, last_ribbon.month % 12 + 1, 1
    )
    assert window_end == dt.datetime(2026, 12, 1)
    ribbon = {rec["Status Date "]: rec for rec in rows}
    ns = "{http://schemas.microsoft.com/project}"
    for name, status, expected_outside in (
        ("Hard_File_updated2", "46275", set()),
        (
            "Hard_File_updated3",
            "46307",
            {7, 9, 13, 14, 36, 141, 144, 145, 146, 409, 407, 410, 156, 411, 155},
        ),
    ):
        path = FIXTURES / "golden" / "fuse_hardfile" / f"{name}.mspdi.xml.gz"
        xml = gzip.decompress(path.read_bytes()).decode("utf-8")
        root = ET.fromstring(xml)
        stored_start = {
            int(t.findtext(f"{ns}UID") or 0): dt.datetime.fromisoformat(
                t.findtext(f"{ns}Start") or ""
            )
            for t in root.iter(f"{ns}Task")
            if t.findtext(f"{ns}Start")
        }
        sch = parse_mspdi_text(xml, source_file=path.name)
        ts = non_summary(sch)
        bac = sum(t.budgeted_cost for t in ts)
        assert bac == fuse_whole_file[name] == 133400.0, name
        outside = {
            t.unique_id
            for t in ts
            if t.unique_id in stored_start and stored_start[t.unique_id] >= window_end
        }
        assert outside == expected_outside, (name, sorted(outside))
        inside_bac = sum(t.budgeted_cost for t in ts if t.unique_id not in outside)
        assert inside_bac == float(ribbon[status]["BAC"]), (name, inside_bac)
        assert bac - inside_bac == (11600.0 if expected_outside else 0.0)
    sch3 = _gz("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz")
    idx = compute_evm_indices(sch3)
    from schedule_forensics.engine.metrics.evm import _actual_cost_of_work_performed, _earned_value

    ev, _ = _earned_value(non_summary(sch3))
    ac = _actual_cost_of_work_performed(sch3, non_summary(sch3))
    assert (
        round((121800.0 - ev) / (121800.0 - ac), 2) == float(ribbon["46307"]["TCPI(BAC)"]) == 1.23
    )
    assert idx["tcpi"].value == 1.19  # the engine's, on the file's whole BAC
