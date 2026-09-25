"""Fuse's "8. High Duration" tile scores PLANNED-OR-IN-PROGRESS work only: the register's R-48
premise — ``IncludeComplete=true`` in the library — is refuted by the library itself and by the
ribbon (R-48, ADR-0532).

* **The library.** Both ``8. High Duration`` entries (GUID ``c6edc255`` — Baseline Duration > 44 —
  and ``eebc7193``, the EV variant against ``Duration Upper Limit``) carry, in BOTH committed
  snapshots and in BOTH of their filters, ``IncludePlanned`` / ``IncludeInProgress`` = true and
  ``IncludeComplete`` = FALSE (``IncludeMilestone`` = true, ``IncludeNormal`` = true), and their
  Remarks say "planned or in-progress". Neither file has changed since its upload.
* **The ribbon discriminates.** The Large Test File pair carries COMPLETED activities whose
  Baseline Duration field exceeds 44 days (77 / 78 of them — UIDs 6337, 6116, 6543, …). A tile
  that admitted completed work would print 164 / 1,569 and 164 / 1,568 (0.10 / 0.10); the Analyst
  ribbon prints 87 / 927 and 86 / 904 (0.09 / 0.10) — the COUNT separates the readings on both
  files, the two-decimal ratio on the first. ADR-0473's row said "no Fuse figure in the repo
  discriminates (every Hard_File ribbon reads 0)": true of Hard_File, false of the Large Test
  File pair pinned since ADR-0518.
* **The engine** already scores incomplete work only, in both modes; no completed activity is a
  DCMA08 offender on any golden that carries completed work (Project5's UID 17 — completed, 60
  baseline days — is the same class with no Fuse ribbon to read).

Red-first (2026-09-25): the library pin goes red by name on a scratch copy with one
``IncludeComplete`` flipped to true (the probe in ADR-0532); the discrimination pin goes red
with ``is_incomplete`` patched to admit completed work — the engine then prints 164 against the
ribbon's 87. Absence semantics mirror the sibling oracles: skip only when the intake dir is
absent; a named workbook or library that is missing FAILS.
"""

from __future__ import annotations

import gzip
import zipfile
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.metrics import compute_dcma14
from schedule_forensics.engine.metrics._common import (
    activity_calendar_day_minutes,
    acumen_duration_field,
    non_summary,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
FIXTURES = REPO / "tests" / "fixtures"
ANALYST = ACUMEN / "Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx"
TILE = "8. High Duration"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

Cell = str | int | float | bool | None

_LTF = "golden/fuse_ltf/Large_Test_File.mspdi.xml.gz"
_LTF2 = "golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz"
#: ribbon label → committed fixture (ADR-0518's pairing)
_RIBBON = {"Large Test File": _LTF, "Large Test File2": _LTF2}
#: every golden that carries completed work, for the no-completed-offender census
_PROGRESSED = (
    _LTF,
    _LTF2,
    "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
    "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
    "golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
    "golden/fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz",
    "golden/ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz",
    "golden/ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz",
    "golden/project2_5/Project2.mspdi.xml",
    "golden/project2_5/Project5.mspdi.xml",
)

_LIBRARIES = sorted(INTAKE.glob("**/NASA Metrics_Complete_*.aft")) if INTAKE.exists() else []
_FLAGS = ("IncludePlanned", "IncludeInProgress", "IncludeComplete")


# ── the library ───────────────────────────────────────────────────────────────────────────────


def _high_duration_entries(path: Path) -> list[tuple[str, str, dict[str, dict[str, str]]]]:
    """Every ``8. High Duration`` entry of one ``.aft``: (guid, remarks, {filter: flags})."""
    root = ET.parse(path).getroot()
    out: list[tuple[str, str, dict[str, dict[str, str]]]] = []
    for metric in root.iter("Metric"):
        if metric.findtext("Name") != TILE:
            continue
        filters: dict[str, dict[str, str]] = {}
        for name in ("PrimaryFilter", "SecondaryFilter"):
            el = metric.find(name)
            assert el is not None, (path.name, TILE, name)
            filters[name] = {flag: el.findtext(flag) or "" for flag in _FLAGS}
            filters[name]["IncludeMilestone"] = el.findtext("IncludeMilestone") or ""
            filters[name]["IncludeNormal"] = el.findtext("IncludeNormal") or ""
        out.append((metric.findtext("Guid") or "", metric.findtext("Remarks") or "", filters))
    return out


def _assert_scores_planned_or_in_progress_only(
    entries: list[tuple[str, str, dict[str, dict[str, str]]]], where: str
) -> None:
    """The predicate the library pin asserts — callable on a mutated scratch copy (the probe)."""
    assert len(entries) >= 2, (where, "the tile has two library entries")
    for guid, remarks, filters in entries:
        for name, flags in filters.items():
            assert flags["IncludeComplete"] == "false", (where, guid, name, flags)
            assert flags["IncludePlanned"] == "true", (where, guid, name, flags)
            assert flags["IncludeInProgress"] == "true", (where, guid, name, flags)
            assert flags["IncludeMilestone"] == "true", (where, guid, name, flags)
            assert flags["IncludeNormal"] == "true", (where, guid, name, flags)
        assert "planned or in-progress" in remarks, (where, guid, remarks)


def test_the_committed_libraries_are_present() -> None:
    assert len(_LIBRARIES) >= 2, [p.name for p in _LIBRARIES]


@pytest.mark.parametrize("library", _LIBRARIES, ids=lambda p: p.name)
def test_every_8_high_duration_entry_excludes_completed_work(library: Path) -> None:
    _assert_scores_planned_or_in_progress_only(_high_duration_entries(library), library.name)


# ── the ribbon ────────────────────────────────────────────────────────────────────────────────


def _col_index(ref: str) -> int:
    """``"P14"`` → 15 (Fuse's writer omits ``r`` on consecutive cells; ADR-0516 M10)."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _sheets(path: Path) -> list[tuple[str, list[list[Cell]]]]:
    """Every sheet of an xlsx as rows of typed cells, column-addressed (std-lib only)."""
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
    """The Analyst 'Ribbon Analysis' sheet, the tile's column per label: counts, then ratios."""
    rows = dict(_sheets(ANALYST))["Ribbon Analysis"]
    col: int | None = None
    blocks: list[dict[str, Cell]] = [{}, {}]
    block = 0
    for r in rows:
        if "Status Date " in r and TILE in r:
            col = r.index(TILE)
            continue
        if col is not None and r and r[0] == "Ribbons" and isinstance(r[1], str):
            if r[1] in blocks[0] and block == 0:
                block = 1
            blocks[block][r[1]] = r[col] if col < len(r) else None
    assert blocks[0] and blocks[1], "the ribbon's two blocks were not found"
    return blocks[0], blocks[1]


# ── the engine ────────────────────────────────────────────────────────────────────────────────


@cache
def _fixture(rel: str) -> Schedule:
    path = FIXTURES / rel
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return parse_mspdi_text(raw.decode("utf-8"), source_file=path.name)


def _completed_by_field(rel: str) -> tuple[int, int]:
    """(completed activities with a Baseline Duration field over 44 days, completed activities
    with a field over 0) — the population a tile with ``IncludeComplete=true`` would add."""
    sch = _fixture(rel)
    by_uid = {c.uid: c for c in sch.calendars}
    high = baselined = 0
    for t in non_summary(sch):
        if not t.is_complete:
            continue
        field = acumen_duration_field(
            t.baseline_duration_minutes or 0, activity_calendar_day_minutes(sch, t, by_uid)
        )
        baselined += field > 0
        high += field > 44
    return high, baselined


def test_the_ribbon_reads_the_incomplete_count_and_can_tell_it_from_the_inclusive_one() -> None:
    counts, ratios = _ribbon()
    ratio_separated = 0
    for label, rel in _RIBBON.items():
        d = compute_dcma14(_fixture(rel), acumen_parity=True)["DCMA08"]
        assert d.count == counts[label], (label, d.count, counts[label])
        assert round(d.count / d.population, 2) == ratios[label], (label, d.count, d.population)
        high, baselined = _completed_by_field(rel)
        assert high >= 1, (label, "no completed high-duration activity: cannot discriminate")
        inclusive = d.count + high
        assert inclusive != counts[label], (label, inclusive, counts[label])
        ratio_separated += round(inclusive / (d.population + baselined), 2) != ratios[label]
    assert ratio_separated >= 1  # the count separates both files; the 2-dp ratio at least one


@pytest.mark.parametrize("rel", _PROGRESSED, ids=lambda r: Path(r).name.split(".")[0])
def test_no_completed_activity_is_a_high_duration_offender(rel: str) -> None:
    sch = _fixture(rel)
    completed = {t.unique_id for t in non_summary(sch) if t.is_complete}
    assert completed, (rel, "not a progressed golden")
    for parity in (False, True):
        d = compute_dcma14(sch, acumen_parity=parity)["DCMA08"]
        leaked = sorted(completed & set(d.offender_uids))
        assert not leaked, (rel, parity, leaked)


def test_the_discriminating_population_exists_beyond_the_ribboned_pair() -> None:
    """Project5's completed UID 17 (60 baseline days) is the same class, with no Fuse ribbon to
    read: the engine's tile stays 0 there — a register note, not an oracle."""
    high, _ = _completed_by_field("golden/project2_5/Project5.mspdi.xml")
    assert high == 1
    assert compute_dcma14(_fixture("golden/project2_5/Project5.mspdi.xml"))["DCMA08"].count == 0
