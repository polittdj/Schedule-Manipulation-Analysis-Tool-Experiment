"""Acumen Fuse's *Total Float* field is the stored slack rounded HALF-TO-EVEN to whole days, and
the DCMA float classifications read that field (R-03, ADR-0514).

The audit row asked what Fuse does at an exact half-day tie (-0.5 d / 44.5 d), where Python's
``round`` is banker's rounding. No activity in the 44-file corpus sits at the tie, but the
operator's Fuse v8.11.0 exports for the Large Test File pair DISPLAY a Total Float beside every
activity in every detail grid — 3,637 distinct activities across the two snapshots — and the
first snapshot carries 196 activities whose stored slack is an exact half day. Their displayed
values are the oracle: a half-day float with an odd integer part rounds UP (513.5 → 514) and one
with an even integer part rounds DOWN (514.5 → 514, 24.5 → 24). Only half-to-even reproduces all
196; half-away-from-zero misses the 78 even ones, truncation the 118 odd ones (and 154.75 → 155).

The second pin closes the inference: the "6. High Float" and "7. Negative Float" detail sets in
the Analyst Quick Add Metrics workbook are UID-exact against ``compute_dcma14(acumen_parity=True)``
on both snapshots — the filters read the rounded field (UID 5283's -0.29 d, displayed 0, is not in
the Negative Float set; a raw ``< 0`` would have put it there).

Absence semantics mirror ``test_fuse_transcription_oracle``: skip only when the whole intake dir is
absent; a named workbook that is missing FAILS (the oracle must not narrow silently).
"""

from __future__ import annotations

import gzip
import zipfile
from collections.abc import Iterator
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics import compute_dcma14
from schedule_forensics.engine.metrics._common import (
    acumen_whole_day_float,
    effective_total_float,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "fuse_ltf"

#: every Large Test File workbook the operator delivered — each carries detail grids with a
#: Total Float column; the count is pinned so a deleted workbook fails instead of narrowing
_WORKBOOKS = tuple(
    ACUMEN / name
    for name in (
        "Large Test File Acumen DCMA 14 Point vs Program Results.xlsx",
        "Large Test File vs Large Test File2 - Acumen Forensic Analysis Report.xlsx",
        "Large Test File vs Large Test File2 - Acumen Fuse - DCMA Report.xlsx",
        "Large Test File vs Large Test File2 - Acumen Fuse - Detailed Metric Report.xlsx",
        "Large Test File vs Large Test File2 - Acumen Fuse -Metric History Report.xlsx",
        "Large Test File vs Large Test File2 - Acumen Fuse Analysis Quick Add Metrics.xlsx",
        "Large Test File vs Large Test File2 - Acumen Fuse Quick Add Metrics .xlsx",
        "Large Test File vs Large Test File2 - Acumen Fuse Summary Metric DCMA Report.xlsx",
        "Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx",
        "Large Test File vs Large Test File2 - Detailed Metric Report.xlsx",
        "Large Test File vs Large Test File2 - MS Excel Quick Add Metrics .xlsx",
        "Large Test File vs Large Test File2 Forensic Analysis Report.xlsx",
        "Large Test File2 Acumen DCMA 14 Point vs Program Results.xlsx",
    )
)
_ANALYST = ACUMEN / "Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx"
_PROJECTS = {"Large Test File": "Large_Test_File", "Large Test File2": "Large_Test_File2"}

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

Cell = str | int | float | bool | None


def _sheets(path: Path) -> list[tuple[str, list[list[Cell]]]]:
    """Every sheet of an xlsx as rows of typed cells (std-lib only: zip + XML)."""
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


def _as_int(x: Cell) -> int | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, str) and x.strip().lstrip("-").isdigit():
        return int(x)
    return None


def _tables(path: Path) -> Iterator[tuple[str, str, dict[int, tuple[str, int]]]]:
    """Every detail grid with Id / Project / Total Float columns: (sheet, label, {Id: (project,
    displayed float)}); the label is the last text-only row above the header (the metric)."""
    for sheet, rows in _sheets(path):
        label = ""
        i = 0
        while i < len(rows):
            r = rows[i]
            cells = [c for c in r if c not in (None, "")]
            if (
                cells
                and all(isinstance(c, str) for c in cells)
                and len(set(cells)) <= 2
                and "Total Float" not in cells
                and "Id" not in cells
            ):
                label = str(cells[0])
            if "Total Float" in r and "Id" in r and "Project" in r:
                tf_i, id_i, pj_i = r.index("Total Float"), r.index("Id"), r.index("Project")
                got: dict[int, tuple[str, int]] = {}
                j = i + 1
                while j < len(rows) and len(rows[j]) > max(tf_i, id_i, pj_i):
                    uid = _as_int(rows[j][id_i])
                    if uid is None:
                        break
                    shown = _as_int(rows[j][tf_i])
                    if shown is not None:
                        got[uid] = (str(rows[j][pj_i]), shown)
                    j += 1
                if got:
                    yield sheet, label, got
                i = j
                continue
            i += 1


def _workbooks_present() -> None:
    missing = [p.name for p in _WORKBOOKS if not p.exists()]
    assert not missing, f"Fuse workbook(s) missing from the intake (Law 2 oracle): {missing}"


@cache
def _displayed() -> dict[tuple[str, int], set[int]]:
    """(project, Id) → the set of Total Float values Fuse displayed for it, across every grid."""
    shown: dict[tuple[str, int], set[int]] = {}
    for wb in _WORKBOOKS:
        for _sheet, _label, got in _tables(wb):
            for uid, (project, value) in got.items():
                shown.setdefault((project, uid), set()).add(value)
    return shown


@cache
def _golden(name: str) -> Schedule:
    xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml, source_file=f"{name}.mspdi.xml")


@cache
def _engine_days(name: str) -> dict[int, Fraction]:
    """The engine's effective total float (the stored slack when the file carries it) in exact
    working days per activity — the quantity dcma14 classifies."""
    sch = _golden(name)
    cpm = compute_cpm(sch)
    mpd = sch.calendar.working_minutes_per_day
    tf = {u: t.total_float for u, t in cpm.timings.items()}
    return {
        t.unique_id: Fraction(str(effective_total_float(t, tf.get(t.unique_id, 0)))) / mpd
        for t in sch.tasks
    }


def _half_away(days: Fraction) -> int:
    return int(Decimal(str(float(days))).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def test_every_displayed_total_float_is_the_stored_slack_rounded_half_to_even() -> None:
    _workbooks_present()
    shown = _displayed()
    ambiguous = {k: v for k, v in shown.items() if len(v) > 1}
    assert not ambiguous, f"one activity, two displayed floats: {list(ambiguous.items())[:5]}"
    per_project = {p: 0 for p in _PROJECTS}
    halves: list[tuple[int, Fraction, int]] = []
    wrong: list[tuple[str, int, float, int]] = []
    for (project, uid), values in shown.items():
        days = _engine_days(_PROJECTS[project])
        assert uid in days, f"Fuse Id {uid} ({project}) is not a UID of the golden"
        per_project[project] += 1
        d = days[uid]
        value = next(iter(values))
        if acumen_whole_day_float(float(d), 1) != value:
            wrong.append((project, uid, float(d), value))
        if project == "Large Test File" and d.denominator == 2:
            halves.append((uid, d, value))
    # the whole population, pinned so a parser or importer regression cannot shrink it silently
    assert per_project == {"Large Test File": 1513, "Large Test File2": 2124}
    assert not wrong, f"{len(wrong)} displayed floats are not the half-even day: {wrong[:8]}"
    # the discriminating population: half-day floats of BOTH parities, so the rule is decided
    assert len(halves) == 196
    even = [(u, d, v) for u, d, v in halves if int(d) % 2 == 0]
    odd = [(u, d, v) for u, d, v in halves if int(d) % 2 == 1]
    assert (len(odd), len(even)) == (118, 78)
    assert all(v == int(d) for _u, d, v in even), "an even-part half must round DOWN (514.5 → 514)"
    assert all(v == int(d) + 1 for _u, d, v in odd), "an odd-part half must round UP (513.5 → 514)"
    # and the alternatives the audit row weighed are refuted BY NAME on this population
    assert sum(_half_away(d) != v for _u, d, v in halves) == 78  # half away from zero
    assert sum(int(d) != v for _u, d, v in halves) == 118  # truncation


def test_the_dcma_float_sets_read_that_field_uid_exact_on_both_snapshots() -> None:
    _workbooks_present()
    want = {
        "Large Test File": {"DCMA06": 814, "DCMA07": 35},
        "Large Test File2": {"DCMA06": 660, "DCMA07": 112},
    }
    found: dict[tuple[str, str], set[int]] = {}
    for _sheet, label, got in _tables(_ANALYST):
        low = label.lower()
        if "greater than 2 months. should not exceed 5%" in low:
            key = "DCMA06"
        elif "incomplete and have total float less than 0" in low:
            key = "DCMA07"
        else:
            continue
        for uid, (project, _value) in got.items():
            found.setdefault((project, key), set()).add(uid)
    for project, golden in _PROJECTS.items():
        d = compute_dcma14(_golden(golden), acumen_parity=True)
        for key in ("DCMA06", "DCMA07"):
            fuse = found[(project, key)]
            assert len(fuse) == want[project][key], (project, key, len(fuse))
            assert set(d[key].offender_uids) == fuse, (project, key)
    # the raw slack would have flagged UID 5283 (-139 min = -0.29 d); the field reads 0
    days = _engine_days("Large_Test_File2")
    assert Fraction(-139, 480) == days[5283]
    assert 5283 not in found[("Large Test File2", "DCMA07")]
    assert _displayed()[("Large Test File2", 5283)] == {0}
