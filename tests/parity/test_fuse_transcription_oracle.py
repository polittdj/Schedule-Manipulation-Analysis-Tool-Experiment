"""PO-03 — the Fuse transcription is machine-guarded against the vendor Fuse .xlsx workbooks.

``tests/fixtures/golden/project2_5/fuse_exports_2026-06.json`` (ADR-0151) is a HAND
transcription of the operator-delivered Acumen Fuse v8.11.0 export suite, and every number
``test_fuse_export_parity.py`` calls "Fuse's value" flowed through that transcription. The
2026-08-13 audit (PO-03) found the transcription step itself was guarded by NO test — no
parity test read the source vendor workbooks, so a transcription error or a silent edit of
the JSON would still leave ENGINE==FUSE "green" while the oracle no longer said what the
vendor tool said. This module closes that: it re-reads the four load-bearing committed
workbooks with a std-lib reader (zipfile + xml.etree — the repo's runtime-I/O law; openpyxl
is not a dependency) and re-derives every derivable transcribed value:

* Tier 1 — label-addressed Metric History rows (every occurrence of a label must agree);
* Tier 2 — DCMA Report offender lists (Newly Critical / No Longer Critical / CEI-Incomplete);
* Tier 3 — per-activity re-derivations from BOTH Forensic Analysis Reports (no-longer-
  critical, float erosion, duration-increase sets, exact finish serials), plus the
  v1==v2 identity of the derivation sheets **on the read columns** (UID / type / P2 value /
  numeric delta / P5 value — the value-bearing columns of today's transcription; unread
  prose columns can drift without tripping it, by scope — adversarial round, F2).

Workbook facts this module leans on (measured 2026-08-14, see the ADR for this change):
the workbooks are SpreadsheetGear exports that OMIT ``r=`` row/col attributes on most
cells (a reader requiring them sees empty sheets — the reader below tracks implicit
previous+1 counters); ``Logic Density™`` appears at TWO different scopes and only the
occurrence adjacent to ``CP Logic Density™`` is the transcribed one — and the WRONG row's
Project2 value equals the RIGHT row's Project5 value, so value-appears-somewhere checks
cannot distinguish them; Metric History's ``Project Finish`` stores the DAY-FLOOR serial
(46644, not round's 46645) while the exact serials live in the Forensic ``Projects``
sheets; the CEI offender ids are not in UID order (compare sorted).

Absence semantics (tightened by the adversarial round, F1): the module SKIPS only when the
whole ``00_REFERENCE_INTAKE/`` directory is absent (an artifact-less layout). A missing
INDIVIDUAL workbook while the directory exists FAILS loudly instead — the intake manifest
guard reads the git INDEX (committed blobs, deliberately), so an unstaged working-tree
deletion is invisible to it and a skip here would have silently disarmed all 20 guards on
exactly the machine whose run matters (measured: ``rm`` one workbook → 20 skipped, manifest
10 passed). CI is never skipped either way: all four workbooks are git-tracked and pinned
by name in ``docs/INTAKE-MANIFEST.md``.

Proven able to fail (QC-1) against this committed module: a mutated JSON value, a mutated
JSON UID list, and a mutated WORKBOOK cell (byte-patched copy) each flip the named tests
red; the ADR-0240 adversarial round then ran ~25 further sandbox mutations (offender ids,
banner counts, serials, coordinated two-report tampering, label removals) and its four
findings — the skip-hole, the row-identity overclaim, truncating integer reads, and the
untied ``activities_added`` leaf — are closed in this revision, each re-proven red. The
batteries and measured flip lists live in the ADR for this change.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

#: The vendor Fuse export workbooks (.xlsx) this oracle reads.
_METRIC_HISTORY = "P2-P5 - Metric History Report.xlsx"
_DCMA_REPORT = "P2-P5 - DCMA Report.xlsx"
_FORENSIC_V1 = "Project2v5 Forensic Analysis Report.xlsx"
_FORENSIC_V2 = "Project2 vs Project5_TAMPERED Forensic Analysis Report.xlsx"
_WORKBOOKS = (_METRIC_HISTORY, _DCMA_REPORT, _FORENSIC_V1, _FORENSIC_V2)

pytestmark = [
    pytest.mark.parity,
    # Skip ONLY for an artifact-less layout (no intake directory at all). A missing
    # individual workbook is a FAILURE, not a skip — see _workbooks_present below.
    pytest.mark.skipif(
        not INTAKE.exists(),
        reason="00_REFERENCE_INTAKE/ not present in this layout",
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

Rows = dict[int, dict[int, str]]


def _load_workbook(path: Path) -> dict[str, Rows]:
    """{sheet_name: {row: {col: raw_value}}} (1-based), std-lib only.

    SpreadsheetGear omits ``r=`` on most rows and cells: a row without ``r=`` is
    previous-row+1 and a cell without ``r=`` is previous-col+1 within its row, so both
    counters are tracked. Numeric cells keep their raw stored string (full precision).
    """
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
        rel_target = {
            r.get("Id"): r.get("Target") or "" for r in rels.findall(f"{_RELS}Relationship")
        }
        for sh in wb.iter(f"{_M}sheet"):
            target = rel_target.get(sh.get(f"{_R}id") or "", "")
            part = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
            if part not in names:
                part = target.lstrip("/")
                if part not in names:
                    continue
            rows: Rows = {}
            row_idx = 0
            for row in ET.fromstring(zf.read(part)).iter(f"{_M}row"):
                r_attr = row.get("r")
                row_idx = int(r_attr) if r_attr is not None else row_idx + 1
                col_idx = 0
                for c in row.findall(f"{_M}c"):
                    ref = c.get("r")
                    if ref is not None:
                        col_idx = 0
                        for ch in ref:
                            if ch.isdigit():
                                break
                            col_idx = col_idx * 26 + (ord(ch) - 64)
                    else:
                        col_idx += 1
                    if c.get("t") == "inlineStr":
                        is_el = c.find(f"{_M}is")
                        if is_el is not None:
                            rows.setdefault(row_idx, {})[col_idx] = "".join(
                                t.text or "" for t in is_el.iter(f"{_M}t")
                            )
                        continue
                    v = c.find(f"{_M}v")
                    if v is None or v.text is None:
                        continue
                    rows.setdefault(row_idx, {})[col_idx] = (
                        shared[int(v.text)] if c.get("t") == "s" else v.text
                    )
            out[sh.get("name") or "?"] = rows
    return out


def _num(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


@pytest.fixture(scope="module", autouse=True)
def _workbooks_present() -> None:
    """FAIL (never skip) when a workbook is missing while the intake directory exists.

    The intake manifest guard reads the git INDEX, so an unstaged working-tree deletion
    is invisible to it; a skip here would silently disarm every test in this module on
    the local machine whose run matters (adversarial round, F1 — measured)."""
    missing = [name for name in _WORKBOOKS if not (INTAKE / name).exists()]
    assert not missing, (
        f"vendor Fuse workbook(s) missing from the working tree: {missing} — these are "
        "git-tracked oracle inputs; restore them (git checkout -- <path>), do not skip"
    )


@pytest.fixture(scope="module")
def fuse() -> dict:
    return json.loads((GOLDEN / "fuse_exports_2026-06.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mh() -> Rows:
    return _load_workbook(INTAKE / _METRIC_HISTORY)["Project2"]


@pytest.fixture(scope="module")
def dcma() -> dict[str, Rows]:
    return _load_workbook(INTAKE / _DCMA_REPORT)


@pytest.fixture(scope="module")
def forensic() -> dict[str, dict[str, Rows]]:
    return {
        "v1": _load_workbook(INTAKE / _FORENSIC_V1),
        "v2": _load_workbook(INTAKE / _FORENSIC_V2),
    }


def _mh_occurrences(mh: Rows, label: str) -> list[tuple[int, str | None, str | None]]:
    """Every Metric History row whose column-B label matches -> (row, P2 col D, P5 col G)."""
    return [(r, mh[r].get(4), mh[r].get(7)) for r in sorted(mh) if mh[r].get(2) == label]


def _assert_mh(
    mh: Rows, label: str, expected: float, col: str, *, cp_adjacent: bool = False
) -> None:
    """Every occurrence of the label must carry the transcribed value (self-cross-checking:
    drift in ANY of the row's repeats fails). ``cp_adjacent`` selects the occurrence
    immediately followed by the ``CP Logic Density™`` row (the two-scope trap)."""
    occ = _mh_occurrences(mh, label)
    if cp_adjacent:
        occ = [o for o in occ if mh.get(o[0] + 1, {}).get(2) == "CP Logic Density™"]
    assert occ, f"Metric History label {label!r} not found — the oracle's population moved"
    idx = 1 if col == "D" else 2
    got = [(o[0], _num(o[idx])) for o in occ]
    assert all(v == expected for _, v in got), (
        f"Metric History {label!r} col {col}: rows carry {got}, transcription says {expected}"
    )


# --------------------------------------------------------------------------------------
# Tier 1 — Metric History label-addressed rows (§A / §B / §C and the §E headlines).
# --------------------------------------------------------------------------------------

_SQ_LABELS = (
    ("critical_zero_days_float", "Zero Days Float"),
    ("critical_zero_days_float", "Critical Path (Tasks & Milestones)"),
    ("hard_constraints", "Hard Constraints"),
    ("negative_float", "Negative Float"),
    ("insufficient_detail", "Insufficient Detail™"),
    ("merge_hotspot", "Merge Hotspot (Predecessors >2)"),
    ("missing_logic_incomplete_scoped", "Missing Logic"),
)

_DCMA_LABELS = (
    ("DCMA01", "Missing Logic"),
    ("DCMA02", "Activities w/Leads on Predecessor"),
    ("DCMA03", "Total # Predecessor Lags"),
    ("DCMA05", "Hard Constraints"),
    ("DCMA06", "High Float 44d"),
    ("DCMA07", "Negative Float"),
    ("DCMA08", "High Planned Duration (44d)"),
    ("DCMA09", "Wrong Status"),
    ("DCMA14", "BEI - Value Tasks"),
    ("DCMA14_complete", "BEI - Complete Tasks"),
    ("DCMA14_total", "BEI - Total Tasks"),
)

_BC_LABELS = (
    ("forecast_to_be_finished", "Forecast to be Finished"),
    ("completed_on_time", "Completed On Time"),
    ("completed_late", "Completed Late"),
    ("not_completed", "Not Completed"),
    ("baseline_finish_compliance", "Baseline Finish Compliance"),
    ("forecast_to_be_started", "Forecast to be Started"),
    ("started_on_time", "Started On Time"),
    ("started_late", "Started Late"),
    ("not_started", "Not Started"),
    ("baseline_start_compliance", "Baseline Start Compliance"),
)

_PROJECT_COL = (("Project2", "D"), ("Project5", "G"))


@pytest.mark.parametrize(("project", "col"), _PROJECT_COL)
def test_schedule_quality_rows_match_the_metric_history_workbook(
    fuse: dict, mh: Rows, project: str, col: str
) -> None:
    sq = fuse[project]["schedule_quality"]
    # The two-scope trap: only the CP-adjacent Logic Density™ row is the transcribed one.
    _assert_mh(mh, "Logic Density™", sq["logic_density"], col, cp_adjacent=True)
    for key, label in _SQ_LABELS:
        _assert_mh(mh, label, sq[key], col)


@pytest.mark.parametrize(("project", "col"), _PROJECT_COL)
def test_dcma_rows_match_the_metric_history_workbook(
    fuse: dict, mh: Rows, project: str, col: str
) -> None:
    d = fuse[project]["dcma14"]
    for key, label in _DCMA_LABELS:
        _assert_mh(mh, label, d[key], col)
    # DCMA11 is transcribed as the SUM of two Metric History rows.
    idx = 1 if col == "D" else 2
    late = {_num(o[idx]) for o in _mh_occurrences(mh, "Finished Late")}
    unfinished = {
        _num(o[idx]) for o in _mh_occurrences(mh, "Forecast to be Finished but not Finished yet")
    }
    assert len(late) == 1 and len(unfinished) == 1, (
        f"DCMA11 source rows disagree among themselves: late={late} unfinished={unfinished}"
    )
    assert late.pop() + unfinished.pop() == d["DCMA11"]


@pytest.mark.parametrize(("project", "col"), _PROJECT_COL)
def test_baseline_compliance_matches_the_metric_history_workbook(
    fuse: dict, mh: Rows, project: str, col: str
) -> None:
    bc = fuse[project]["baseline_compliance"]
    for key, label in _BC_LABELS:
        _assert_mh(mh, label, bc[key], col)


def test_baseline_compliance_second_source_advanced_sheet(
    fuse: dict, dcma: dict[str, Rows]
) -> None:
    """The DCMA 'Advanced-Baseline-Compliance' sheet is layout-ASYMMETRIC (measured):
    Project5 is the row-10 Current Period grid (cols B-K); Project2 lives on the
    per-metric banner rows in col E (the col-E/F block is headed Project2)."""
    abc = dcma["Advanced-Baseline-Compliance"]
    p5 = [_num(abc.get(10, {}).get(c)) for c in range(2, 12)]
    assert p5 == [fuse["Project5"]["baseline_compliance"][k] for k, _ in _BC_LABELS]
    p2_bc = fuse["Project2"]["baseline_compliance"]
    for key, label in _BC_LABELS:
        hits = [
            (r, _num(abc[r].get(5)))
            for r in sorted(abc)
            if abc[r].get(1) == label and _num(abc[r].get(3)) is not None
        ]
        assert hits and all(v == p2_bc[key] for _, v in hits), (
            f"Advanced sheet banner rows for {label!r}: {hits} vs transcription {p2_bc[key]}"
        )


# --------------------------------------------------------------------------------------
# Tier 2 — DCMA Report offender lists (UID-exact).
# --------------------------------------------------------------------------------------


def _int_cell(raw: str) -> int:
    """A count/UID cell must hold an exact integer. ``int(float(...))`` would TRUNCATE a
    drifted vendor cell (34.6 -> 34) into a green comparison (adversarial round, F3)."""
    value = float(raw)
    assert value.is_integer(), f"expected an integral count/id cell, found {raw!r}"
    return int(value)


def _offender_block(rows: Rows, title: str, id_col: int) -> tuple[int | None, list[int]]:
    """Banner row (col A == title, numeric count in col C), then offender ids from the
    data rows two below the banner until the id column stops being numeric."""
    for r in sorted(rows):
        if rows[r].get(1) == title and _num(rows[r].get(3)) is not None:
            count = _int_cell(rows[r][3])
            ids = []
            rr = r + 3
            while rr in rows and _num(rows[rr].get(id_col)) is not None:
                ids.append(_int_cell(rows[rr][id_col]))
                rr += 1
            return count, ids
    return None, []


def test_critical_transition_offender_lists_match_the_dcma_report(
    fuse: dict, mh: Rows, dcma: dict[str, Rows]
) -> None:
    ch = fuse["change_P2_to_P5"]
    _assert_mh(mh, "Newly Critical Activities", ch["newly_critical"], "G")
    _assert_mh(mh, "Activities No Longer Critical", ch["no_longer_critical"], "G")
    cp = dcma["NASA-Metrics-Critical-Path"]
    nc_count, nc_ids = _offender_block(cp, "Newly Critical Activities", id_col=1)
    assert (nc_count, nc_ids) == (ch["newly_critical"], ch["newly_critical_uids"])
    nlc_count, nlc_ids = _offender_block(cp, "Activities No Longer Critical", id_col=1)
    assert nlc_count == ch["no_longer_critical"]
    assert sorted(nlc_ids) == ch["no_longer_critical_uids"]


def test_finish_slip_offenders_match_and_the_cei_counts_rederive_the_count(
    fuse: dict, mh: Rows, dcma: dict[str, Rows]
) -> None:
    ch = fuse["change_P2_to_P5"]
    # The offender ids sit in col C on this sheet and are NOT in UID order (measured).
    count, ids = _offender_block(
        dcma["NASA-Metrics-Performance-Curre2"], "CEI - Incomplete Tasks", id_col=3
    )
    assert count == ch["finish_slips_cei_incomplete"]
    assert sorted(ids) == ch["finish_slips_cei_incomplete_uids"]
    # Independent second source: CEI Total minus CEI Complete re-derives the count.
    total = {_num(o[2]) for o in _mh_occurrences(mh, "CEI - Total Tasks")}
    complete = {_num(o[2]) for o in _mh_occurrences(mh, "CEI - Complete Tasks")}
    assert len(total) == 1 and len(complete) == 1
    assert total.pop() - complete.pop() == ch["finish_slips_cei_incomplete"]


def test_bei_incomplete_analysis_third_source_row(dcma: dict[str, Rows], fuse: dict) -> None:
    """The provenance's third source for the Project5 DCMA14 quad: the BEI-Incomplete
    sheet's value row (Value | Total | Complete | Incomplete)."""
    d5 = fuse["Project5"]["dcma14"]
    bei = dcma["NASA_Quick-Library-BEI---Incom"]
    row10 = [_num(bei.get(10, {}).get(c)) for c in (1, 2, 3, 4)]
    assert row10 == [
        d5["DCMA14"],
        d5["DCMA14_total"],
        d5["DCMA14_complete"],
        d5["DCMA14_total"] - d5["DCMA14_complete"],
    ]


# --------------------------------------------------------------------------------------
# Tier 3 — the change block's headline rows, exact serials, and the per-activity
# re-derivations from BOTH Forensic Analysis Reports.
# --------------------------------------------------------------------------------------


def test_change_headlines_match_the_metric_history_rows(fuse: dict, mh: Rows) -> None:
    ch = fuse["change_P2_to_P5"]
    _assert_mh(
        mh, "CEI - Value Task Starts - by Status Dates", ch["start_cei_by_status_dates"], "G"
    )
    _assert_mh(mh, "Actually Finished", ch["completed"], "G")
    _assert_mh(mh, "Actually Started - Tasks", ch["in_progress"], "G")
    # Match by NAME, never by the HSD10 code: the adjacent Cumulative row carries the
    # same code with a different number (measured: -9646).
    _assert_mh(mh, "Net Finish Impact (Days)", ch["net_finish_impact_days_stored"], "G")
    # Metric History stores the DAY-FLOOR of the finish serial (floor, not round).
    _assert_mh(mh, "Project Finish", int(ch["project_finish_serial_P2"]), "D")
    _assert_mh(mh, "Project Finish", int(ch["project_finish_serial_P5"]), "G")
    # Consumed by test_fuse_export_parity's start-CEI reconciliation (23 -> 29 starts).
    _assert_mh(mh, "Actual Starts", 23, "D")
    _assert_mh(mh, "Actual Starts", 29, "G")


@pytest.mark.parametrize("report", ["v1", "v2"])
def test_exact_project_finish_serials_match_the_forensic_projects_sheets(
    fuse: dict, forensic: dict[str, dict[str, Rows]], report: str
) -> None:
    ch = fuse["change_P2_to_P5"]
    projects = forensic[report]["Projects"]
    assert _num(projects.get(10, {}).get(5)) == ch["project_finish_serial_P2"]
    assert _num(projects.get(11, {}).get(5)) == ch["project_finish_serial_P5"]
    # activities_added: both snapshots carry the identical 144 activities and the
    # Activities sheet's own header pins the added count at 0 — tie the JSON leaf to
    # that basis (adversarial round, F4: previously the one leaf no assertion read).
    assert _num(projects.get(10, {}).get(13)) == 144
    assert _num(projects.get(11, {}).get(13)) == 144
    assert forensic[report]["Activities"].get(8, {}).get(1) == "Activities - 0 (0%)"
    assert ch["activities_added"] == 0


_DERIVATION_SHEETS = (
    "Critical",
    "Total-Float",
    "Original-Duration",
    "Remaining-Duration",
    "Activity-Status",
)


def _forensic_grid(fv: dict[str, Rows], sheet: str) -> dict[int, dict[str, str | int]]:
    """Data rows (10+) keyed by row: B=UID, D=type, I=P2 value, K=numeric delta, M=P5
    value. Flag sheets spell booleans as Wingdings glyphs (P/O) — derive from those and
    the numeric delta column, never from direction glyphs."""
    rows = fv[sheet]
    out: dict[int, dict[str, str | int]] = {}
    for r in sorted(rows):
        if r < 10:
            continue
        b = _num(rows[r].get(2))
        if b is None:
            continue
        out[r] = {
            "id": int(b),
            "type": rows[r].get(4, ""),
            "p2": rows[r].get(9, ""),
            "k": rows[r].get(11, ""),
            "p5": rows[r].get(13, ""),
        }
    return out


def test_forensic_derivation_sheets_are_row_identical_across_both_reports(
    forensic: dict[str, dict[str, Rows]],
) -> None:
    """The JSON's ``_source`` claims the two independently-created reports agree on the
    derivation sheets; that claim is part of the oracle's authority. Scope: identity is
    asserted over the READ columns (UID/type/P2/delta/P5 — the value-bearing ones);
    unread prose columns are outside it (adversarial round, F2)."""
    for sheet in _DERIVATION_SHEETS:
        g1 = _forensic_grid(forensic["v1"], sheet)
        g2 = _forensic_grid(forensic["v2"], sheet)
        assert g1 == g2, f"Forensic sheet {sheet!r} differs between the two reports"
        assert g1, f"Forensic sheet {sheet!r} has no data rows — population moved"


@pytest.mark.parametrize("report", ["v1", "v2"])
def test_critical_sheet_rederives_newly_and_no_longer_critical(
    fuse: dict, forensic: dict[str, dict[str, Rows]], report: str
) -> None:
    ch = fuse["change_P2_to_P5"]
    fv = forensic[report]
    status = _forensic_grid(fv, "Activity-Status")
    p5_complete = {v["id"] for v in status.values() if v["p5"] == "Complete"}
    crit = _forensic_grid(fv, "Critical")
    p_to_o = {v["id"] for v in crit.values() if v["p2"] == "P" and v["p5"] == "O"}
    o_to_p = [v["id"] for v in crit.values() if v["p2"] == "O" and v["p5"] == "P"]
    summaries = {v["id"] for v in crit.values() if v["type"] == "Summary"}
    assert o_to_p == ch["newly_critical_uids"]
    derived = sorted(p_to_o - summaries - p5_complete)
    assert derived == ch["no_longer_critical_uids"], (
        f"no-longer-critical derivation ({report}) produced {derived}"
    )


@pytest.mark.parametrize("report", ["v1", "v2"])
def test_total_float_sheet_rederives_float_erosion(
    fuse: dict, forensic: dict[str, dict[str, Rows]], report: str
) -> None:
    ch = fuse["change_P2_to_P5"]
    fv = forensic[report]
    status = _forensic_grid(fv, "Activity-Status")
    p5_complete = {v["id"] for v in status.values() if v["p5"] == "Complete"}
    tf = _forensic_grid(fv, "Total-Float")
    decreased = sorted(
        v["id"] for v in tf.values() if v["type"] != "Summary" and (_num(str(v["k"])) or 0) < 0
    )
    erosion = [u for u in decreased if u not in p5_complete]
    assert erosion == ch["float_erosion_stored_basis_uids"]
    assert len(erosion) == ch["float_erosion_stored_basis"]


@pytest.mark.parametrize("report", ["v1", "v2"])
def test_duration_sheets_rederive_the_increase_sets(
    fuse: dict, forensic: dict[str, dict[str, Rows]], report: str
) -> None:
    ch = fuse["change_P2_to_P5"]
    fv = forensic[report]
    for sheet, count_key, uids_key in (
        ("Original-Duration", "original_duration_increases", "original_duration_increases_uids"),
        (
            "Remaining-Duration",
            "remaining_duration_increases_nonsummary",
            "remaining_duration_increases_nonsummary_uids",
        ),
    ):
        grid = _forensic_grid(fv, sheet)
        increased = sorted(
            v["id"]
            for v in grid.values()
            if v["type"] != "Summary" and (_num(str(v["k"])) or 0) > 0
        )
        assert increased == ch[uids_key], f"{sheet} ({report}) derived {increased}"
        assert len(increased) == ch[count_key]
