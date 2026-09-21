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

**Float Ratio™ reads those same fields, and the name carries TWO metrics** (R-78, ADR-0519). The
``.aft`` defines ``Float Ratio™`` under both Bible forms, and Fuse prints both under that one tile
name: the AlltheProjects ribbon is ``AVERAGE(TotalFloat/RemainingDuration)`` — N/A whenever a
Remaining Duration field is 0, because ``AVERAGE`` propagates the per-activity divide-by-zero —
while the 7/15 Analyst and update2-vs-update3 ribbons are
``AVERAGE(TotalFloat)/AVERAGE(RemainingDuration)``, which has no per-activity division to fail and
so keeps the zero-remaining activities in BOTH sums. The rev-5 ``Hard_File_updated3`` save reads
-10.94 in one ribbon and -8.01 in the other; the 24-hour file reads N/A and -3.58. One tile is
excluded BY NAME as an unexplained residual: update2-vs-update3's own ``Hard_File_updated3``
(-5.59, and its "CP - Float Ratio™" twin -11.9) reproduces from no committed save under either
form, although that grid's 110 rows reproduce 110/110 and its sibling snapshot's tiles are exact.

Registered here, NOT consumed by the engine yet: **R-79** — the "9. Invalid Forecast Dates" tile's
denominator is the baselined INCOMPLETE population (322 / 904 → 0.36 on File2) where the engine's
parity mode divides by every baselined activity.

Absence semantics mirror ``test_fuse_hardfile_float_divisor_oracle``: skip only when the intake
dir is absent; a named workbook that is missing FAILS (the oracle must not narrow silently).
"""

from __future__ import annotations

import gzip
import math
import re
import zipfile
from collections.abc import Callable, Iterator
from fractions import Fraction
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


# ── Float Ratio™: ONE name, TWO metrics (R-78, ADR-0519) ──────────────────────────────────────
#
# The ``.aft`` carries "Float Ratio™" under BOTH of the Bible's algebraic forms — GUID
# ``a536d1a4`` is ``AVERAGE(TotalFloat/RemainingDuration)``, five further entries are
# ``AVERAGE(TotalFloat)/AVERAGE(RemainingDuration)`` — and the operator's workbooks display
# both under that one tile name: the AlltheProjects ribbon prints the MEAN-OF-RATIOS, the
# 7/15 Analyst and update2-vs-update3 ribbons print the RATIO-OF-MEANS. The rev-5
# ``Hard_File_updated3`` save reads -10.94 in one ribbon and -8.01 in the other, so the two
# forms are separated by MEASUREMENT, not by preference. Both terms are the whole-day FIELDS
# of R-75 / R-76 (``acumen_total_float_field`` / ``acumen_duration_field`` on
# ``activity_day_minutes``), which is why this oracle lives beside them.

_UPD2VS3 = ACUMEN / "Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx"
_REV2 = "golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz"  # the update2vs3 workbook's save
_UPD2 = "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz"


def _tiles(book: Path) -> dict[str, Cell]:
    """Each snapshot's ``Float Ratio™`` ribbon tile. The metric carries no percentage, so the
    ratios block is empty for it and the counts block is the only one that reads."""
    counts, _ratios = _ribbon(book, "Float Ratio™")
    return {label: cells["Float Ratio™"] for label, cells in counts.items()}


def _fuse_pairs(book: Path, project: str) -> list[tuple[int, float, float]]:
    """``(uid, Total Float, Remaining Duration)`` from the cells FUSE ITSELF displays for the
    Float Ratio population (Normal, planned or in progress) — no engine helper is consulted, so
    the expectations below cannot be produced by the code they judge."""
    out: list[tuple[int, float, float]] = []
    for (p, uid), cells in _displayed(book).items():
        if p != project or cells.get("Type") != "Normal" or cells.get("Status") == "Complete":
            continue
        tf, rd = _as_number(cells.get("Total Float")), _as_number(cells.get("Remaining Duration"))
        assert tf is not None and rd is not None, (book.name, project, uid)
        out.append((uid, float(tf), float(rd)))
    return out


def test_fuses_float_ratio_tile_is_the_mean_of_its_whole_day_fields() -> None:
    """The AlltheProjects ribbon's ``Float Ratio™`` is ``AVERAGE(TotalFloat/RemainingDuration)``
    over the whole-day FIELDS, and reads **N/A whenever any Remaining Duration field is 0** —
    Excel's own error propagation through ``AVERAGE``, not a finding about the schedule.

    Measured two independent ways on every label the workbook maps to a committed save: from the
    cells Fuse itself displays, and from the ENGINE (which derives the same fields out of the
    MSPDI). Nine numeric tiles reproduce to 4 dp and ten N/A tiles reproduce exactly; the N/A
    witnesses are a zero Remaining Duration field (the 24-hour file's UID 389 — 480 minutes on a
    1,440-minute calendar; Hard_File's UID 99 — 240 on 480). Refuted by name below: the
    ratio-of-means (that is the OTHER ribbon's tile) and the engine's former minute axis."""
    _workbooks_present()
    tiles = _tiles(_ALL)
    numeric = na = 0
    for label, rel in _WORKBOOKS[_ALL].items():
        tile = tiles[label]
        pairs = _fuse_pairs(_ALL, label)
        assert pairs, label
        zeros = [uid for uid, _tf, rd in pairs if rd == 0]
        primary = compute_float_ratio(_fixture(rel))["float_ratio"]
        if zeros:
            na += 1
            assert tile == "N/A", (label, zeros)
            # the engine says "nothing was averaged" with a 0 population — the ONLY signal its
            # consumers have (the status pill is spent on "informational, no threshold")
            assert (primary.population, primary.value, primary.offender_uids) == (0, 0.0, ()), label
        else:
            numeric += 1
            assert isinstance(tile, (int, float)) and not isinstance(tile, bool), label
            from_cells = round(sum(tf / rd for _uid, tf, rd in pairs) / len(pairs), 4)
            assert round(from_cells, 2) == round(float(tile), 2), (label, from_cells, tile)
            assert primary.population == len(pairs), label
            assert primary.value == round(float(tile), 2), (label, primary.value, tile)
    assert (numeric, na) == (9, 10)
    # the individual figures the row was registered on, spelled out
    assert tiles["Hard_File_updated3"] == -10.94 and tiles["Project2"] == 14.01
    assert tiles["Jacked Up Schedule 1"] == 0.77 and tiles["Jacked up Schedule 2"] == 0.27
    assert tiles["Project5_TAMPERED"] == 22.02
    assert sorted(uid for uid, _tf, rd in _fuse_pairs(_ALL, _H24) if rd == 0) == [
        267,
        302,
        385,
        389,
    ]
    assert sorted(uid for uid, _tf, rd in _fuse_pairs(_ALL, "Hard_File") if rd == 0) == [99]
    # THE RULE, over EVERY label the ribbon displays — including the ones whose SAVE the repo
    # does not hold (TP4 v1-v5, Project3/4, EVM2, this workbook's Hard_File_updated2, SRA). Those
    # are evidence for the RULE, never for the engine, so they are scored from Fuse's own cells
    # only. Under the shipped presentation every one of the 39 reproduces.
    from_cells = 0
    for other, tile_value in tiles.items():
        cells = _fuse_pairs(_ALL, other)
        assert cells, other
        if any(rd == 0 for _uid, _tf, rd in cells):
            assert tile_value == "N/A", other
        else:
            mean = round_half_up(sum(tf / rd for _uid, tf, rd in cells) / len(cells), 2)
            assert isinstance(tile_value, (int, float)) and not isinstance(tile_value, bool), other
            assert mean == round_half_up(float(tile_value), 2), (other, mean, tile_value)
        from_cells += 1
    assert from_cells == 39

    # The tile's two decimals round half AWAY FROM ZERO. ADR-0515 left every ``value_dp``
    # rounding on half-to-even because no reference display was known at that precision; here
    # there is one, and the ribbon holds exactly ONE tie: TP4_DataCenter_v1's mean is exactly 5/8
    # and Fuse WRITES 0.63 into the cell (not 0.625 under a 2-dp format — the workbook's value is
    # 0.63), where half-to-even writes 0.62. Every other label is a non-tie and reads identically
    # under either rule, so this one cell carries the whole claim — and it is asserted to be the
    # only one, so a future corpus that adds a second tie cannot slip past unread.
    ties = []
    for other in tiles:
        cells = _fuse_pairs(_ALL, other)
        if not cells or any(rd == 0 for _uid, _tf, rd in cells):
            continue
        exact = sum(
            Fraction(tf).limit_denominator(10**9) / Fraction(rd).limit_denominator(10**9)
            for _uid, tf, rd in cells
        ) / len(cells)
        scaled = exact * 100
        if scaled - int(scaled) in (Fraction(1, 2), Fraction(-1, 2)):
            ties.append((other, exact, tiles[other]))
    assert ties == [
        ("TP4_DataCenter_v1", Fraction(5, 8), 0.63),
        ("TP4_DataCenter_v1 2", Fraction(5, 8), 0.63),
    ], ties
    assert round(0.625, 2) == 0.62 != 0.63  # what half-to-even would have printed

    # REFUTED by name: the ratio-of-means reads -8.01 on the same save (it is the Analyst
    # ribbon's tile, asserted below), and the engine's former MINUTE axis read -11.85 / 119.61
    assert compute_float_ratio(_fixture(_REV5))["float_ratio_aggregate"].value == -8.01
    per_day = _fixture(_REV5).calendar.working_minutes_per_day
    minutes = [
        (
            _effective(_REV5)[t.unique_id] / per_day,
            _remaining_minutes(t) / (1440 if t.duration_is_elapsed else per_day),
        )
        for t in non_summary(_fixture(_REV5))
        if not t.is_milestone and not t.is_level_of_effort and not t.is_complete
    ]
    old = round(sum(tf / rd for tf, rd in minutes if rd) / sum(1 for _tf, rd in minutes if rd), 2)
    assert old == -11.85 != -10.94  # the engine's reading before R-78, reconstructed here


def test_fuses_float_ratio_tile_is_the_ratio_of_field_means_in_the_other_ribbons() -> None:
    """The 7/15 Analyst and update2-vs-update3 ribbons print the Bible's OTHER form under the
    same name — ``AVERAGE(TotalFloat)/AVERAGE(RemainingDuration)`` over the same population and
    the same whole-day fields — and it is **not** N/A on a zero divisor: there is no per-activity
    division to fail, so the zero-remaining activities stay in BOTH sums.

    The 24-hour file is the discriminator: four of its fourteen scored activities carry a
    Remaining Duration field of 0. Keeping them prints the tile's -3.58; dropping them prints
    -9.58. The mean-of-ratios form reads N/A on that same save (asserted above), which is how we
    know the two tiles are two metrics rather than one tile we have mis-read."""
    _workbooks_present()
    analyst, quick = _tiles(_ANALYST), _tiles(_ALL)
    # the SAME save, two ribbons, two numbers — one name
    assert analyst["Hard_File_updated3"] == -8.01 and quick["Hard_File_updated3"] == -10.94
    assert compute_float_ratio(_fixture(_REV5))["float_ratio_aggregate"].value == -8.01
    assert analyst[_H24] == -3.58 and quick[_H24] == "N/A"
    both = compute_float_ratio(_fixture(_G24))
    assert (both["float_ratio_aggregate"].value, both["float_ratio_aggregate"].population) == (
        -3.58,
        14,
    )
    assert both["float_ratio"].population == 0  # the mean-of-ratios form is N/A on the same save
    # …and the discriminator, from FUSE's OWN cells: dropping the zeros would print -9.58
    pairs = _fuse_pairs(_ANALYST, _H24)
    assert len([1 for _uid, _tf, rd in pairs if rd == 0]) == 4
    kept = sum(tf for _uid, tf, _rd in pairs) / sum(rd for _uid, _rd2, rd in pairs)
    dropped = sum(tf for _uid, tf, rd in pairs if rd) / sum(rd for _uid, _tf, rd in pairs if rd)
    assert (round(kept, 2), round(dropped, 2)) == (-3.58, -9.58)
    # the update2vs3 workbook prints the same form: its update2 snapshot reproduces exactly
    pair = _tiles(_UPD2VS3)
    assert pair["Hard_File_updated2"] == 5.74
    assert compute_float_ratio(_fixture(_UPD2))["float_ratio_aggregate"].value == 5.74
    # NAMED RESIDUAL — that workbook's OTHER snapshot reproduces from no committed save under
    # either form, although its grid's 110 rows reproduce 110/110 (asserted by the field oracle
    # above) from the rev-2 save and its sibling snapshot's tile is exact. Its "CP - Float
    # Ratio™" twin misses the same way (-11.9 against the critical-only -14.17). Disclosed, not
    # explained: the tile is excluded from the oracle BY NAME, so it cannot silently start
    # "passing" under a future rule that happens to hit -5.59.
    assert pair["Hard_File_updated3"] == -5.59
    residual = compute_float_ratio(_fixture(_REV2))
    assert residual["float_ratio_aggregate"].value == -8.24
    assert residual["float_ratio"].value == -11.26
