"""Fuse's "Estimated Duration" is MS Project's *Estimated* flag over PLANNED-OR-IN-PROGRESS normal
activities — never completed work, never milestones (R-51, ADR-0533).

The engine's structural health check "Estimated (placeholder) durations" read the flag over EVERY
status: 63 on Hard_File_updated2 / updated3 where Fuse prints 47 / 41 (the register's R-51 row).
The Bible settles the scope before a figure is read: every ``Estimated Duration`` entry in both
committed libraries carries ``IncludePlanned`` / ``IncludeInProgress`` = true, ``IncludeComplete``
= FALSE, ``IncludeNormal`` = true and the single expression ``IsEstimated = True``; the two entries
the DCMA report includes carry ``IncludeMilestone`` = false. The ratio Fuse prints beside the count
is the count over the same population without the expression (the secondary filter): the
planned-or-in-progress normal activities.

Oracles — every one committed, every figure read at test time, none transcribed:

* the AlltheProjects Quick-Add ribbon (``00_REFERENCE_INTAKE/AlltheProjects Analysis Report -
  Quick Add Metrics.xlsx``): the count AND the ratio per label, on every label whose save is a
  committed fixture (the label ↔ save match is ADR-0516's, by the Total Float field): Hard_File
  68 / 0.80, Hard_File_updated 65 / 0.82, the rev-5 Hard_File_updated3 41 / 0.79, the 24-hour
  save 9 / 0.64, and 0 on the flag-free labels (the Large Test File family, Jacked Up 1 / 2,
  Project2, Project5_TAMPERED, EVM1);
* the two Detailed Metric Reports (``Hard_File_update vs update2`` and ``update2 vs update3``,
  the siblings of the Analysis Reports ADR-0516 matched to their saves): the "Estimated
  Duration" column's per-activity ``X`` marks by activity Id on Hard_File_updated (65),
  Hard_File_updated2 (47, in both) and Hard_File_updated3 (41), plus each sheet's own Record
  Count row — the UID-exact leg. The flagged activities Fuse does NOT mark are exactly the
  COMPLETED ones (3 / 16 / 16 / 22), which is what separates the two readings.

Red-first (2026-09-25, pristine tree): the ribbon leg read 68 / 68 / 63 / 63 against 68 / 65 / 41
/ 9 with a population of 110 (a ratio of 0.62 where Fuse prints 0.80), and the X-mark leg found
3 / 16 / 16 / 22 engine offenders Fuse leaves unmarked. Mutants (ADR-0533): the status clause
dropped → the ribbon and X-mark legs red by name; the population left at every non-summary
activity → the ratio leg red by name; the milestone clause dropped → this corpus carries no
estimated milestone, so ONLY ``tests/engine/metrics/test_health_extra.py`` catches it (recorded).

Absence semantics mirror the sibling oracles: skip only when the intake dir is absent; a named
workbook that is missing FAILS (the oracle must not narrow silently).
"""

from __future__ import annotations

import gzip
import zipfile
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics.health_extra import HealthCheck, compute_health_checks
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
FIXTURES = REPO / "tests" / "fixtures"
ALL = INTAKE / "AlltheProjects Analysis Report - Quick Add Metrics.xlsx"
DETAIL_1V2 = ACUMEN / "Hard_File_update vs update2_Fuse - Detailed Metric Report.xlsx"
DETAIL_2V3 = ACUMEN / "Hard_File_update2 vs update3_Fuse - Detailed Metric Report.xlsx"
METRIC = "Estimated Duration"
KEY = "estimated_duration"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

Cell = str | int | float | bool | None

_HF = "golden/fuse_hardfile/Hard_File.mspdi.xml.gz"
_HFU = "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz"
_HFU2 = "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz"
#: rev 2 — the save the update2-vs-update3 workbooks scored (ADR-0516)
_HFU3 = "golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz"
_REV5 = "golden/ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz"
_H24 = "golden/ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz"
_LTF = "golden/fuse_ltf/Large_Test_File.mspdi.xml.gz"
_LTF2 = "golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz"
_P2 = "golden/project2_5/Project2.mspdi.xml"
_P5 = "golden/project2_5/Project5.mspdi.xml"

#: AlltheProjects label → committed fixture (the labels ``test_fuse_duration_fields_oracle`` scores
#: from this workbook, by measurement; a label whose save the repo does not hold is not an oracle)
_RIBBON_LABELS: dict[str, str] = {
    "Hard_File": _HF,
    "Hard_File_updated": _HFU,
    "Hard_File_updated3": _REV5,
    "Hard_File_updated3 2": _REV5,
    "Hard_File_updated4 24 hour calendar": _H24,
    "Hard_File_updated4 24 hour calendar 2": _H24,
    "Jacked Up Schedule 1": "mspdi/jacked_up_schedule_1.xml",
    "Jacked up Schedule 2": "mspdi/jacked_up_schedule_2.xml",
    "Large Test File": _LTF,
    "Large Test File 2": _LTF,
    "Large Test File Leveled": "golden/ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz",
    "Large Test File2": _LTF2,
    "Large Test File2 2": _LTF2,
    "Project2": _P2,
    "Project2 2": _P2,
    "Project2 3": _P2,
    "Project5_TAMPERED": _P5,
    "Project5_TAMPERED 2": _P5,
    "EVM1": "golden/evm/EVM1.mspdi.xml",
}

#: Detailed Metric Report → {sheet (the project label): committed fixture}
_DETAIL_SHEETS: dict[Path, dict[str, str]] = {
    DETAIL_1V2: {"Hard_File_updated": _HFU, "Hard_File_updated2": _HFU2},
    DETAIL_2V3: {"Hard_File_updated2": _HFU2, "Hard_File_updated3": _HFU3},
}


# ── the workbooks (std-lib only) ──────────────────────────────────────────────────────────────


def _col_index(ref: str) -> int:
    """``"P14"`` → 15 (Fuse's writer omits ``r`` on consecutive cells and writes it only where it
    SKIPPED a column — a document-order reader slides those rows; ADR-0516 M10)."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _sheets(path: Path) -> list[tuple[str, list[list[Cell]]]]:
    """Every sheet of an xlsx as rows of typed cells, column-addressed."""
    assert path.exists(), f"Fuse workbook missing from the intake (Law 2 oracle): {path.name}"
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_M}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_M}t")))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") or "" for r in rels}
        out: list[tuple[str, list[list[Cell]]]] = []
        sheets_el = wb.find(f"{_M}sheets")
        assert sheets_el is not None
        for s in sheets_el:
            target = targets[s.get(f"{_R}id") or ""]
            target = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
            rows: list[list[Cell]] = []
            for row in ET.fromstring(zf.read(target)).iter(f"{_M}row"):
                cells: list[Cell] = []
                for c in row.findall(f"{_M}c"):
                    ref = c.get("r")
                    if ref is not None:
                        while len(cells) < _col_index(ref):
                            cells.append(None)
                    v = c.find(f"{_M}v")
                    if v is None or v.text is None:
                        cells.append(None)
                        continue
                    kind = c.get("t")
                    if kind == "s":
                        cells.append(shared[int(v.text)])
                    elif kind == "b":
                        cells.append(bool(int(v.text)))
                    else:
                        try:
                            cells.append(
                                float(v.text) if "." in v.text or "E" in v.text else int(v.text)
                            )
                        except ValueError:
                            cells.append(v.text)
                rows.append(cells)
            out.append((s.get("name") or "", rows))
        return out


@cache
def _ribbon() -> tuple[dict[str, Cell], dict[str, Cell]]:
    """The AlltheProjects 'Ribbon Analysis' sheet's Estimated Duration column, per label — the
    counts block, then the ratios block (the block turns where a label repeats)."""
    rows = dict(_sheets(ALL))["Ribbon Analysis"]
    col: int | None = None
    blocks: list[dict[str, Cell]] = [{}, {}]
    block = 0
    for r in rows:
        if METRIC in r:
            col = r.index(METRIC)
            continue
        if col is not None and r and r[0] == "Ribbons" and isinstance(r[1], str):
            if r[1] in blocks[0] and block == 0:
                block = 1
            blocks[block][r[1]] = r[col] if col < len(r) else None
    assert blocks[0] and blocks[1], "the ribbon's two blocks were not found"
    return blocks[0], blocks[1]


def _detail(path: Path, sheet: str) -> tuple[int, frozenset[int]]:
    """One Detailed Metric Report sheet's Estimated Duration column: (the sheet's own Record
    Count for it, the activity Ids carrying an ``X``)."""
    rows = dict(_sheets(path))[sheet]
    col: int | None = None
    record_count: int | None = None
    marked: set[int] = set()
    for r in rows:
        if col is None:
            if METRIC in r:
                col = r.index(METRIC)
            continue
        if len(r) > 4 and r[4] == "Record Count" and record_count is None:
            v = r[col] if col < len(r) else None
            assert isinstance(v, int), (path.name, sheet, v)
            record_count = v
            continue
        is_activity_row = len(r) > 3 and r[0] == sheet and isinstance(r[3], int)
        if is_activity_row and col < len(r) and r[col] == "X":
            marked.add(r[3])
    assert col is not None and record_count is not None, (path.name, sheet)
    return record_count, frozenset(marked)


# ── the engine ────────────────────────────────────────────────────────────────────────────────


@cache
def _fixture(rel: str) -> Schedule:
    path = FIXTURES / rel
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return parse_mspdi_text(raw.decode("utf-8"), source_file=path.name)


@cache
def _check(rel: str) -> HealthCheck:
    sch = _fixture(rel)
    return next(c for c in compute_health_checks(sch, compute_cpm(sch)).checks if c.key == KEY)


def _flagged(rel: str) -> frozenset[int]:
    """Every non-summary activity carrying the flag, whatever its status — the pristine reading."""
    return frozenset(
        t.unique_id for t in _fixture(rel).tasks if t.is_estimated_duration and not t.is_summary
    )


# ── the ribbon: count and ratio per label ─────────────────────────────────────────────────────


def test_the_ribbon_count_and_ratio_reproduce_on_every_committed_save() -> None:
    counts, ratios = _ribbon()
    missing = sorted(label for label in _RIBBON_LABELS if label not in counts)
    assert not missing, f"labels the ribbon does not carry: {missing}"
    for label, rel in _RIBBON_LABELS.items():
        check = _check(rel)
        assert check.count == counts[label], (label, check.count, counts[label])
        assert check.population > 0, (label, "no planned-or-in-progress normal activity")
        assert round(check.count / check.population, 2) == ratios[label], (
            label,
            check.count,
            check.population,
            ratios[label],
        )
    # the leg is not vacuous: the corpus carries flagged saves, on which the ribbon prints a count
    scored = {label for label in _RIBBON_LABELS if counts[label]}
    assert len(scored) >= 4, scored


def test_the_every_status_reading_is_refuted_by_the_ribbon() -> None:
    """The check must be able to tell the two readings apart: on every progressed Hard_File save
    the flag over every status exceeds the ribbon's planned-or-in-progress count."""
    counts, _ratios = _ribbon()
    separated = 0
    for label, rel in _RIBBON_LABELS.items():
        if len(_flagged(rel)) != counts[label]:
            assert len(_flagged(rel)) > counts[label], (label, len(_flagged(rel)), counts[label])
            separated += 1
    # Hard_File_updated (68 vs 65), the rev-5 updated3 (63 vs 41), the 24-hour save (63 vs 9)
    assert separated >= 3, separated


# ── the detail reports: the X marks by UID ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("book", "sheet"),
    [(book, sheet) for book, sheets in _DETAIL_SHEETS.items() for sheet in sheets],
    ids=lambda x: x.name[:26] if isinstance(x, Path) else x,
)
def test_the_x_marks_are_the_engines_offenders_by_uid(book: Path, sheet: str) -> None:
    rel = _DETAIL_SHEETS[book][sheet]
    record_count, marked = _detail(book, sheet)
    check = _check(rel)
    assert record_count == len(marked), (sheet, record_count, len(marked))
    assert check.count == len(marked), (sheet, check.count, len(marked))
    cited = frozenset(check.offenders)
    if len(marked) <= len(check.offenders) or len(cited) == len(marked):
        assert cited == marked, (sheet, sorted(cited ^ marked))
    else:  # the citation cap (50) truncates the offender list; every cited UID must be a mark
        assert cited <= marked, (sheet, sorted(cited - marked))
    # what separates the readings: the flagged activities Fuse does NOT mark are the completed ones
    unmarked = _flagged(rel) - marked
    assert unmarked, (sheet, "no completed flagged activity — the leg cannot discriminate")
    by_uid = {t.unique_id: t for t in _fixture(rel).tasks}
    not_complete = sorted(u for u in unmarked if not by_uid[u].is_complete)
    assert not not_complete, (sheet, not_complete)
    assert not any(by_uid[u].is_complete for u in marked), (sheet, "Fuse marked completed work")


def test_the_detail_reports_agree_with_the_ribbon_on_the_shared_save() -> None:
    """Hard_File_updated appears in both oracles; the ribbon's count is the detail sheet's marks."""
    counts, _ratios = _ribbon()
    record_count, marked = _detail(DETAIL_1V2, "Hard_File_updated")
    assert counts["Hard_File_updated"] == record_count == len(marked)
