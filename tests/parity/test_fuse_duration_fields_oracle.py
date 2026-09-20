"""Acumen Fuse's *Original* / *Remaining* / *Baseline Duration* FIELDS divide by the ACTIVITY's
own calendar day, and the DCMA-14 population and the "8. High Duration" tile read the Baseline
Duration field (R-76, ADR-0518).

Measured on every duration cell the operator's Fuse v8.11.0 workbooks display beside an activity
— the four Hard_File analysis workbooks (the rows ADR-0516 matched to their SAVE by the Total
Float field: 771 Original, 771 Remaining, 297 Baseline cells over five snapshots) and the
AlltheProjects Analysis Report (every label whose save is a committed fixture, matched the same
way) — the fields reproduce under ONE rule each:

* **Original Duration** and **Baseline Duration** are the minutes over the task's own calendar's
  day when it names one the schedule carries, else the project's, rounded half-to-even to whole
  days — and the ELAPSED flag is IGNORED: UID 146's 2,880 elapsed minutes display **6** (the
  project's 480), not 2. UID 14 (1,440 minutes on "24 Hours") displays 1, not 3; the 24-hour
  file's 302 / 385 / 389 display 2 / 3 / 1, not 5 / 9 / 3.
* **Remaining Duration** divides by 1440 for an elapsed activity (146: 2,880 → **2**; Jacked Up
  Schedule 1's UID 20: 46,080 → **32**, not 96) and by the task's own calendar day otherwise.
* the half-even tie: a 240-minute baseline on a 480 day displays **0** (UIDs 99 / 642); half
  away from zero would print 1, and the floor of any duration is refuted on 1,409 rows.

Two residual classes, both named and pinned exactly: UID 5267 on Large Test File2 stores
``PT107H59M36S`` — 6,479.6 minutes, 13.4992 days, displayed 13 — where the model's minute grid
holds 6,480 (13.5 → 14; R-65's class); and the two 99 %-complete SUMMARIES 315 / 129 on the
24-hour snapshot, whose RemainingDuration MPXJ dropped as a zero (ActualDuration == Duration):
Fuse shows 0, the model's percent fallback derives 247 / 242 minutes → 1.

The population rule the audit row asked to decide FIRST: Fuse's DCMA filter "Baseline Duration
> 0" reads that FIELD on the own day — the 24-hour file's UIDs 302 / 385 (a 480-minute baseline on
a 1,440-minute calendar → 0) leave the population, and the ribbon's ratios prove it three ways:
"7. Negative Float" 0.92 = 11 / **12** (11 / 14 would print 0.79), "9. Invalid Forecast Dates"
0.08 = 1 / 12 (1 / 14 → 0.07), and the tile's own detail grid lists UID 267 alone where the
unfiltered Quick-Add metric lists 267 / 302 / 385. The "8. High Duration" tile is the Baseline
Duration field > 44 over that baselined-incomplete population: Large Test File 87 / 927 → 0.09
and File2 86 / 904 → 0.10 (the engine's all-incomplete 1,024 / 998 would print 0.08 / 0.09).

Registered here, NOT consumed by the engine yet: **R-78** — Fuse's Float Ratio™ is the mean of
its whole-day fields (TotalFloat field / RemainingDuration field) and N/A whenever a divisor is
0; **R-79** — the "9. Invalid Forecast Dates" tile's denominator is the baselined INCOMPLETE
population (322 / 904 → 0.36 on File2) where the engine's parity mode divides by every baselined
activity.

Absence semantics mirror ``test_fuse_hardfile_float_divisor_oracle``: skip only when the intake
dir is absent; a named workbook that is missing FAILS (the oracle must not narrow silently).
"""

from __future__ import annotations

import gzip
import math
import re
import zipfile
from collections.abc import Callable, Iterator
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics import compute_dcma14, compute_float_ratio
from schedule_forensics.engine.metrics._common import (
    activity_day_minutes,
    acumen_total_float_field,
    effective_total_float,
    non_summary,
    round_half_up,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
FIXTURES = REPO / "tests" / "fixtures"
GOLDEN = FIXTURES / "golden"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_ANALYST = (
    ACUMEN / "HA296F~1.XLS"
)  # the 7/15 Fuse Analyst report (rev-5 updated3 + the 24-hour save)
_ALL = INTAKE / "AlltheProjects Analysis Report - Quick Add Metrics.xlsx"
_H24 = "Hard_File_updated4 24 hour calendar"
_REV5 = "golden/ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz"
_G24 = "golden/ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz"
_LTF = "golden/fuse_ltf/Large_Test_File.mspdi.xml.gz"
_LTF2 = "golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz"
_P2 = "golden/project2_5/Project2.mspdi.xml"

Cell = str | int | float | bool | None

#: workbook → {Fuse project label: committed fixture} — every save matched by MEASUREMENT (the
#: Total Float field reproduces 100 % of the displayed floats; asserted below), never by name
_WORKBOOKS: dict[Path, dict[str, str]] = {
    ACUMEN / "Hard_File_Fuse - Fuse Analysis Report.xlsx": {
        "Hard_File": "golden/fuse_hardfile/Hard_File.mspdi.xml.gz",
        "Hard_File_updated": "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
    },
    ACUMEN / "Hard_File_update vs update2_Fuse - Analysis Report.xlsx": {
        "Hard_File_updated": "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
        "Hard_File_updated2": "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
    },
    ACUMEN / "Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx": {
        "Hard_File_updated2": "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
        "Hard_File_updated3": "golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",  # rev 2
    },
    _ANALYST: {"Hard_File_updated3": _REV5, _H24: _G24},
    _ALL: {
        "EVM1": "golden/evm/EVM1.mspdi.xml",
        "Hard_File": "golden/fuse_hardfile/Hard_File.mspdi.xml.gz",
        "Hard_File_updated": "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
        "Hard_File_updated3": _REV5,  # the rev-5 save: rev 2 misses 6 floats per label
        "Hard_File_updated3 2": _REV5,
        _H24: _G24,
        f"{_H24} 2": _G24,
        "Jacked Up Schedule 1": "mspdi/jacked_up_schedule_1.xml",
        "Jacked up Schedule 2": "mspdi/jacked_up_schedule_2.xml",
        "Large Test File": _LTF,
        "Large Test File 2": _LTF,  # Fuse's second import of the same file
        "Large Test File Leveled": "golden/ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz",
        "Large Test File2": _LTF2,
        "Large Test File2 2": _LTF2,
        "Project2": _P2,
        "Project2 2": _P2,
        "Project2 3": _P2,
        "Project5_TAMPERED": "golden/project2_5/Project5.mspdi.xml",
        "Project5_TAMPERED 2": "golden/project2_5/Project5.mspdi.xml",
    },
}
#: AlltheProjects labels deliberately NOT scored, each with its reason — a label that scores a
#: save the repo does not hold is not an oracle (EVM2 8 / 11 floats match, Hard_File_updated2
#: 42 / 110, the five TP4 versions 7-13 / 15 — later saves than the fixtures); the rest exist
#: only as intake ``.mpp`` files with no committed MSPDI
_ALL_EXCLUDED = frozenset(
    {
        "EVM2",
        "Hard_File_updated2",
        "Hard_File_updated_with_logic_reestablished",
        "Project3",
        "Project3 2",
        "Project4",
        "Project4 2",
        "Project5",
        "SRA Large Test File2",
        "SRA Large Test File2 2",
        *(f"TP4_DataCenter_v{n}{s}" for n in range(1, 6) for s in ("", " 2")),
    }
)
_COLUMNS = (
    "Total Float",
    "Original Duration",
    "Remaining Duration",
    "Baseline Duration",
    "Type",
    "Status",
)
_DURATIONS = ("Original Duration", "Remaining Duration", "Baseline Duration")


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
    """Every sheet of an xlsx as rows of typed cells, column-addressed (std-lib only)."""
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


def _as_number(x: Cell) -> int | float | None:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str) and x.strip().lstrip("-").isdigit():
        return int(x)
    return None


def _grids(path: Path) -> Iterator[tuple[str, int, dict[str, Cell]]]:
    """Every row of every detail grid that carries Id / Project and a duration column:
    (project label, Id, {column: cell})."""
    for _sheet, rows in _sheets(path):
        for i, r in enumerate(rows):
            if "Id" in r and "Project" in r and any(c in r for c in _DURATIONS):
                id_i, pj_i = r.index("Id"), r.index("Project")
                cols = {c: r.index(c) for c in _COLUMNS if c in r}
                j = i + 1
                while j < len(rows) and len(rows[j]) > id_i:
                    uid = _as_number(rows[j][id_i])
                    if not isinstance(uid, int):
                        break
                    row = rows[j]
                    yield (
                        str(row[pj_i]),
                        uid,
                        {c: row[k] for c, k in cols.items() if k < len(row)},
                    )
                    j += 1


@cache
def _displayed(path: Path) -> dict[tuple[str, int], dict[str, Cell]]:
    """(project, Id) → the displayed cells across every grid of one workbook; an activity
    displayed twice with two values for one column is an ERROR, not a choice."""
    shown: dict[tuple[str, int], dict[str, Cell]] = {}
    for project, uid, cells in _grids(path):
        prior = shown.setdefault((project, uid), {})
        for col, v in cells.items():
            if v in (None, ""):
                continue
            assert prior.setdefault(col, v) == v, (path.name, project, uid, col, prior[col], v)
    return shown


def _workbooks_present() -> None:
    missing = [p.name for p in _WORKBOOKS if not p.exists()]
    assert not missing, f"Fuse workbook(s) missing from the intake (Law 2 oracle): {missing}"


@cache
def _fixture(rel: str) -> Schedule:
    path = FIXTURES / rel
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return parse_mspdi_text(raw.decode("utf-8"), source_file=path.name)


@cache
def _effective(rel: str) -> dict[int, float]:
    sch = _fixture(rel)
    tf = {u: t.total_float for u, t in compute_cpm(sch).timings.items()}
    return {t.unique_id: effective_total_float(t, tf.get(t.unique_id, 0)) for t in sch.tasks}


def _calendar_day(sch: Schedule, t: Task) -> int:
    """The alternative rules are spelled out here, independent of the helper under test."""
    by_uid = {c.uid: c for c in sch.calendars}
    if t.calendar_uid is not None and t.calendar_uid in by_uid:
        return by_uid[t.calendar_uid].working_minutes_per_day
    return sch.calendar.working_minutes_per_day


def _remaining_minutes(t: Task) -> int:
    """The model's remaining: the stored value, else the percent fallback (float_ratio's rule)."""
    if t.remaining_duration_minutes is not None:
        return t.remaining_duration_minutes
    return round(t.duration_minutes * (100.0 - t.percent_complete) / 100.0)


def _ribbon(
    path: Path, anchor: str
) -> tuple[dict[str, dict[str, Cell]], dict[str, dict[str, Cell]]]:
    """The 'Ribbon Analysis' sheet's two blocks (counts, then ratios): snapshot → {tile: value};
    ``anchor`` is a label of the header row (the Analyst workbooks carry "Status Date ", the
    AlltheProjects report does not)."""
    rows = dict(_sheets(path))["Ribbon Analysis"]
    header: list[Cell] | None = None
    blocks: list[dict[str, dict[str, Cell]]] = [{}, {}]
    block = 0
    for r in rows:
        if anchor in r:
            header = r
            continue
        if header is not None and r and r[0] == "Ribbons" and isinstance(r[1], str):
            if r[1] in blocks[0] and block == 0:
                block = 1
            blocks[block][r[1]] = {
                str(h): v for h, v in zip(header, r, strict=False) if isinstance(h, str)
            }
    return blocks[0], blocks[1]


# ── the fields ────────────────────────────────────────────────────────────────────────────────


def test_every_displayed_duration_divides_by_the_activitys_own_calendar_day() -> None:
    from schedule_forensics.engine.metrics._common import (
        activity_calendar_day_minutes,
        acumen_duration_field,
    )

    _workbooks_present()
    rules: dict[str, Callable[[int, Task, Schedule], float]] = {
        # the shipped rules (the helpers under test)
        "Original Duration": lambda m, t, sch: acumen_duration_field(
            m, activity_calendar_day_minutes(sch, t)
        ),
        "Baseline Duration": lambda m, t, sch: acumen_duration_field(
            m, activity_calendar_day_minutes(sch, t)
        ),
        "Remaining Duration": lambda m, t, sch: acumen_duration_field(
            m, activity_day_minutes(sch, t)
        ),
    }
    alternatives: dict[str, Callable[[int, Task, Schedule], float]] = {
        "project day": lambda m, t, sch: round(m / sch.calendar.working_minutes_per_day),
        "1440 for an elapsed ORIGINAL / BASELINE": lambda m, t, sch: round(
            m / (1440 if t.duration_is_elapsed else _calendar_day(sch, t))
        ),
        "floor": lambda m, t, sch: math.floor(m / _calendar_day(sch, t)),
        "half away from zero": lambda m, t, sch: round_half_up(m / _calendar_day(sch, t)),
    }
    population: dict[tuple[str, str], int] = {}
    misses: dict[str, list[tuple[str, str, int, int, Cell, float]]] = {c: [] for c in _DURATIONS}
    alt_misses: dict[tuple[str, str], set[tuple[str, int]]] = {}
    tf_checked = tf_wrong = 0
    for book, projects in _WORKBOOKS.items():
        group = "AlltheProjects" if book == _ALL else "Hard_File"
        for (project, uid), cells in _displayed(book).items():
            if book == _ALL and project in _ALL_EXCLUDED:
                continue
            rel = projects[project]  # an unmapped label raises here: the population must be named
            sch = _fixture(rel)
            t = sch.tasks_by_id[uid]  # a Fuse Id that is not a UID of the fixture raises here
            shown_tf = _as_number(cells.get("Total Float"))
            if shown_tf is not None:  # the save check: the R-75 field must reproduce every float
                tf_checked += 1
                field = acumen_total_float_field(
                    t, _effective(rel)[uid], activity_day_minutes(sch, t)
                )
                if abs(field - shown_tf) >= 1e-9:
                    tf_wrong += 1
            minutes = {
                "Original Duration": t.duration_minutes,
                "Baseline Duration": t.baseline_duration_minutes,
                "Remaining Duration": _remaining_minutes(t),
            }
            for col in _DURATIONS:
                shown = _as_number(cells.get(col))
                m = minutes[col]
                if shown is None or m is None:
                    continue
                population[(group, col)] = population.get((group, col), 0) + 1
                got = rules[col](m, t, sch)
                if abs(got - shown) >= 1e-9:
                    misses[col].append((project, book.name[:24], uid, m, shown, got))
                for name, alt in alternatives.items():
                    if col == "Remaining Duration" and name.startswith("1440"):
                        continue  # the Remaining field DOES take 1440 for an elapsed activity
                    if abs(alt(m, t, sch) - shown) >= 1e-9:
                        alt_misses.setdefault((col, name), set()).add((project, uid))
    assert (tf_checked, tf_wrong) == (10_706, 0), (tf_checked, tf_wrong)
    assert population == {
        ("Hard_File", "Original Duration"): 771,
        ("Hard_File", "Remaining Duration"): 771,
        ("Hard_File", "Baseline Duration"): 297,
        ("AlltheProjects", "Original Duration"): 9_935,
        ("AlltheProjects", "Remaining Duration"): 9_935,
        ("AlltheProjects", "Baseline Duration"): 1_085,
    }, population
    # the residuals, exactly — every miss is one of the two named classes
    assert not misses["Baseline Duration"], misses["Baseline Duration"][:8]
    grid = {(p, u) for p, _b, u, _m, _s, _g in misses["Original Duration"]}
    assert grid == {("Large Test File2", 5267), ("Large Test File2 2", 5267)}, misses[
        "Original Duration"
    ][:8]
    rem = {(p, u) for p, _b, u, _m, _s, _g in misses["Remaining Duration"]}
    assert rem == {
        ("Large Test File2", 5267),
        ("Large Test File2 2", 5267),
        (_H24, 315),
        (_H24, 129),
    }, misses["Remaining Duration"][:8]
    # the minute grid: the file stores 107 h 59 min 36 s — 13.4992 days, displayed 13 — where
    # the model holds the minute 6,480 (13.5 → 14 under the reference's own half-even rule)
    ltf2 = _fixture(_LTF2)
    assert ltf2.tasks_by_id[5267].duration_minutes == 6480
    xml = gzip.decompress((FIXTURES / _LTF2).read_bytes()).decode("utf-8")
    m5267 = re.search(r"<Task>\s*<UID>5267</UID>.*?<Duration>([^<]+)</Duration>", xml, re.S)
    assert m5267 is not None and m5267.group(1) == "PT107H59M36S"
    assert _displayed(_ALL)[("Large Test File2", 5267)]["Original Duration"] == 13
    assert round((107 * 60 + 59 + 36 / 60) / 480) == 13 and round(6480 / 480) == 14
    # the dropped zero: two 99 % summaries whose RemainingDuration MPXJ omitted (ActualDuration ==
    # Duration in the MSPDI); Fuse shows the file's 0, the percent fallback derives 247 / 242
    h24 = _fixture(_G24)
    for uid, derived in ((315, 247), (129, 242)):
        t = h24.tasks_by_id[uid]
        assert t.is_summary and t.remaining_duration_minutes is None and t.percent_complete == 99.0
        assert _remaining_minutes(t) == derived and round(derived / 480) == 1
        assert _displayed(_ANALYST)[(_H24, uid)]["Remaining Duration"] == 0
    # the alternatives, refuted BY NAME (a superset may miss more; never fewer)
    named: dict[tuple[str, str], set[tuple[str, int]]] = {
        ("Original Duration", "project day"): {
            ("Hard_File_updated3", 14),
            (_H24, 14),
            (_H24, 302),
            (_H24, 385),
            (_H24, 389),
            ("Jacked Up Schedule 1", 19),
        },
        ("Original Duration", "1440 for an elapsed ORIGINAL / BASELINE"): {
            ("Hard_File_updated3", 146),
            (_H24, 146),
            ("Jacked Up Schedule 1", 20),
        },
        ("Baseline Duration", "1440 for an elapsed ORIGINAL / BASELINE"): {
            ("Hard_File_updated3", 146),
            (_H24, 146),
        },
        ("Baseline Duration", "project day"): {(_H24, 14), (_H24, 302), (_H24, 385), (_H24, 389)},
        ("Baseline Duration", "half away from zero"): {
            ("Hard_File", 99),
            ("Large Test File", 642),
            ("Large Test File2", 642),
        },
        ("Original Duration", "floor"): {("Hard_File", 94), ("Hard_File", 267)},
        ("Remaining Duration", "project day"): {
            (_H24, 14),
            (_H24, 389),
            ("Jacked Up Schedule 1", 19),
        },
    }
    for key, rows in named.items():
        assert rows <= alt_misses.get(key, set()), (key, rows - alt_misses.get(key, set()))
    assert len(alt_misses[("Original Duration", "floor")]) == 1_409  # distinct (project, Id)
    # the discriminating cells, with the values each candidate day prints
    rev5 = _fixture(_REV5)
    t14, t146 = rev5.tasks_by_id[14], rev5.tasks_by_id[146]
    assert (t14.duration_minutes, activity_calendar_day_minutes(rev5, t14)) == (1440, 1440)
    assert (t146.duration_minutes, t146.duration_is_elapsed) == (2880, True)
    assert activity_calendar_day_minutes(rev5, t146) == 480  # the elapsed flag is ignored here
    assert activity_day_minutes(rev5, t146) == 1440  # …and honoured by the Remaining field
    shown3 = _displayed(_ANALYST)
    assert (
        acumen_duration_field(2880, 480),
        shown3[("Hard_File_updated3", 146)]["Original Duration"],
    ) == (6, 6)
    assert (
        acumen_duration_field(2880, 1440),
        shown3[("Hard_File_updated3", 146)]["Remaining Duration"],
    ) == (2, 2)
    assert (acumen_duration_field(1440, 1440), shown3[(_H24, 14)]["Original Duration"]) == (1, 1)
    ju1 = _fixture("mspdi/jacked_up_schedule_1.xml")
    t20 = ju1.tasks_by_id[20]
    assert t20.duration_is_elapsed and t20.duration_minutes == 46_080
    shown_all = _displayed(_ALL)
    assert (
        shown_all[("Jacked Up Schedule 1", 20)]["Original Duration"]
        == acumen_duration_field(46_080, 480)
        == 96
    )
    assert (
        shown_all[("Jacked Up Schedule 1", 20)]["Remaining Duration"]
        == acumen_duration_field(46_080, 1440)
        == 32
    )
    assert acumen_duration_field(240, 480) == 0 and round_half_up(240 / 480) == 1  # the tie


# ── the population and the tile ───────────────────────────────────────────────────────────────


def test_the_dcma_population_reads_the_baseline_field_on_the_own_day_on_the_24_hour_hard_file() -> (
    None
):
    _workbooks_present()
    counts, ratios = _ribbon(_ANALYST, "Status Date ")
    assert counts[_H24]["7. Negative Float"] == 11 and ratios[_H24]["7. Negative Float"] == 0.92
    assert counts[_H24]["9. Invalid Forecast Dates"] == 1
    assert ratios[_H24]["9. Invalid Forecast Dates"] == 0.08
    h24 = _fixture(_G24)
    d = compute_dcma14(h24, acumen_parity=True)
    assert (d["DCMA07"].count, d["DCMA07"].population) == (11, 12)
    assert round(11 / 12, 2) == 0.92 and round(11 / 14, 2) == 0.79  # the pristine population, 14
    assert round(1 / 12, 2) == 0.08 and round(1 / 14, 2) == 0.07
    # the two excluded: a 480-minute baseline on the 1,440-minute "24 Hours" calendar → field 0
    for uid in (302, 385):
        t = h24.tasks_by_id[uid]
        assert t.baseline_duration_minutes == 480 and _calendar_day(h24, t) == 1440
        assert t.percent_complete < 100.0
        assert uid not in d["DCMA07"].offender_uids
    incomplete_baselined = {
        t.unique_id
        for t in non_summary(h24)
        if t.percent_complete < 100.0 and (t.baseline_duration_minutes or 0) >= 480
    }
    assert len(incomplete_baselined) == 14 and {302, 385} <= incomplete_baselined
    assert d["DCMA05"].population == d["DCMA06"].population == d["DCMA01"].population == 12
    # DCMA-09: the tile's own grid lists UID 267 alone; the unfiltered Quick-Add "Invalid Forecast
    # Dates" grid lists 267 / 302 / 385 (the dropped-zero 99 % class) — the population filter is
    # the whole difference, and the engine now reads the tile's 1
    invalid = [
        sorted(u for u, (p, _v) in got.items() if p == _H24)
        for label, got in _detail_grids(_ANALYST)
        if label.startswith("All activities with planned work in the past")
    ]
    assert sorted(invalid, key=len) == [[267], [267, 302, 385]], invalid
    assert d["DCMA09"].offender_uids == (267,)
    # R-79 (registered): the tile's denominator is the baselined INCOMPLETE population — File2's
    # 322 / 0.36 reproduce only with 904 — where the engine's parity mode divides by every
    # baselined activity (1,568 on File2; 84 here)
    lcounts, lratios = _ribbon(
        ACUMEN / "Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx",
        "Status Date ",
    )
    assert (
        lcounts["Large Test File2"]["9. Invalid Forecast Dates"],
        lratios["Large Test File2"]["9. Invalid Forecast Dates"],
    ) == (322, 0.36)
    assert (
        round(322 / 904, 2) == 0.36 and round(322 / 998, 2) == 0.32 and round(322 / 1568, 2) == 0.21
    )
    assert compute_dcma14(_fixture(_LTF2), acumen_parity=True)["DCMA09"].population == 1568


def _detail_grids(path: Path) -> Iterator[tuple[str, dict[int, tuple[str, Cell]]]]:
    """Every detail grid with Id / Project columns: (label, {Id: (project, Total Float)}); the label
    is the last text-only row above the header (the divisor oracle's reader)."""
    for _sheet, rows in _sheets(path):
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
            if "Id" in r and "Project" in r:
                id_i, pj_i = r.index("Id"), r.index("Project")
                got: dict[int, tuple[str, Cell]] = {}
                j = i + 1
                while j < len(rows) and len(rows[j]) > max(id_i, pj_i):
                    uid = _as_number(rows[j][id_i])
                    if not isinstance(uid, int):
                        break
                    got[uid] = (str(rows[j][pj_i]), None)
                    j += 1
                if got:
                    yield label, got
                i = j
                continue
            i += 1


def test_the_high_duration_tile_is_the_baseline_field_over_the_baselined_incomplete() -> None:
    _workbooks_present()
    book = ACUMEN / "Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx"
    counts, ratios = _ribbon(book, "Status Date ")
    assert (
        counts["Large Test File"]["8. High Duration"],
        ratios["Large Test File"]["8. High Duration"],
    ) == (87, 0.09)
    assert (
        counts["Large Test File2"]["8. High Duration"],
        ratios["Large Test File2"]["8. High Duration"],
    ) == (86, 0.1)
    for rel, count, population, ratio in ((_LTF, 87, 927, 0.09), (_LTF2, 86, 904, 0.10)):
        d = compute_dcma14(_fixture(rel), acumen_parity=True)["DCMA08"]
        assert (d.count, d.population) == (count, population), (rel, d.count, d.population)
        assert round(d.count / d.population, 2) == ratio
    # the pristine denominator — every incomplete activity — prints the other digit on BOTH files
    assert round(87 / 1024, 2) == 0.08 and round(86 / 998, 2) == 0.09
    # the small files: Project2 1 / 106 → 0.01 (both denominators agree there), Project5 0, and
    # every Hard_File snapshot 0 (the 7/15 Analyst report, both saves)
    d2 = compute_dcma14(_fixture(_P2), acumen_parity=True)["DCMA08"]
    assert (d2.count, d2.population, round(d2.value)) == (1, 106, 1)
    assert (
        compute_dcma14(_fixture("golden/project2_5/Project5.mspdi.xml"), acumen_parity=True)[
            "DCMA08"
        ].count
        == 0
    )
    hcounts, _hr = _ribbon(_ANALYST, "Status Date ")
    for project, rel in _WORKBOOKS[_ANALYST].items():
        assert hcounts[project]["8. High Duration"] == 0
        assert compute_dcma14(_fixture(rel), acumen_parity=True)["DCMA08"].count == 0, project
    # the default (pure-logic) mode keeps every incomplete activity in its denominator
    assert compute_dcma14(_fixture(_LTF))["DCMA08"].population == 1024


# ── registered, not consumed yet ──────────────────────────────────────────────────────────────


def test_fuses_float_ratio_is_the_mean_of_its_whole_day_fields_r78_registered() -> None:
    """Fuse's Float Ratio™ (``AVERAGE(TotalFloat/RemainingDuration)``, Normal, planned or in
    progress) averages its WHOLE-DAY fields and reads N/A whenever a Remaining Duration field is
    0 — recomputed here from the fields Fuse itself displays, it reproduces every numeric tile of
    the AlltheProjects ribbon and every N/A. The engine averages MINUTES and skips a zero
    remaining, so it reads -11.85 where Fuse reads -10.94 (Hard_File_updated3, rev 5), and a
    number where Fuse reads N/A (Large Test File, Hard_File, EVM1). R-78 registers it; this pin
    keeps the row's premise executable (the engine-side assertion flips when the row closes)."""
    _workbooks_present()
    _counts, _ratios = _ribbon(_ALL, "Float Ratio™")
    fuse = {label: cells["Float Ratio™"] for label, cells in _counts.items()}

    def from_fields(book: Path, project: str) -> float | str:
        terms: list[float] = []
        for (p, _uid), cells in _displayed(book).items():
            if p != project or cells.get("Type") != "Normal" or cells.get("Status") == "Complete":
                continue
            tf, rd = (
                _as_number(cells.get("Total Float")),
                _as_number(cells.get("Remaining Duration")),
            )
            assert tf is not None and rd is not None, (project, _uid)
            if rd == 0:
                return "N/A"
            terms.append(tf / rd)
        return round(sum(terms) / len(terms), 4)

    assert (
        from_fields(_ANALYST, "Hard_File_updated3") == -10.9446
        and fuse["Hard_File_updated3"] == -10.94
    )
    assert from_fields(_ANALYST, _H24) == "N/A" and fuse[_H24] == "N/A"  # UID 389's field is 0
    assert from_fields(_ALL, "Project2") == 14.0076 and fuse["Project2"] == 14.01
    assert (
        from_fields(_ALL, "Jacked Up Schedule 1") == 0.7678 and fuse["Jacked Up Schedule 1"] == 0.77
    )
    assert (
        from_fields(_ALL, "Jacked up Schedule 2") == 0.2667 and fuse["Jacked up Schedule 2"] == 0.27
    )
    assert (
        from_fields(_ALL, "Hard_File") == "N/A" and fuse["Hard_File"] == "N/A"
    )  # UID 99: 240 min → 0
    # the engine today (registered gap, R-78)
    assert compute_float_ratio(_fixture(_REV5))["float_ratio"].value == -11.85
    assert compute_float_ratio(_fixture(_LTF))["float_ratio"].value == 119.61
    assert compute_float_ratio(_fixture(_P2))["float_ratio"].value == 14.01
