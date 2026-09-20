"""Acumen Fuse's *Total Float* field divides the stored slack by the ACTIVITY's own day, not the
project's (R-75, ADR-0516): 1440 for an elapsed duration — and then RAW, never rounded — else the
task's own calendar's working minutes per day when it names one, else the project's; rounded
half-to-even (ADR-0514) for every calendar-based activity. NOT the crew's calendar and NOT the
execution calendar the engine schedules the work on (ADR-0474 / ADR-0503).

The audit row asked which day Fuse divides by: UID 146 has no task calendar and was still shown
over 1440. Every Hard_File workbook the operator delivered prints a Total Float beside every
activity of its detail grids — 771 rows across five snapshots once each workbook is matched to
the SAVE it was made from (the 7/15 analyst workbook is the rev-5 save of ``updated3``, the 7/9
Analysis Report the rev-2 save; matched by measurement, 141 / 141 against 129 / 141) — and the
rule reproduces every one. The alternatives fail BY NAME:

* the project day: UID 14 (a "24 Hours" task calendar) -9 for the displayed -3, UID 94
  ("Standard+Sat.", 930 min) 5 for 2, UID 146 (elapsed) -3 for -1; on the 24-hour file 302 / 385
  read 104 / 93 where Fuse shows 34 / 31 — the engine's DCMA-06 read 2 against the ribbon's 0;
* the crew's calendar: UID 14's crew works 16-hour days (-4.5 → -4, not -3); a task with no
  calendar of its own stays on the project day even when its crew works 24 hours (24-hour file
  UID 13: -10 for -4,800, the crew's 1440 would read -3); UID 389's crew is on the project
  pattern while its task calendar is 24 Hours (-14, not -41);
* the engine's execution calendar (the crew under a 24-hour task calendar, ADR-0503; the task ∩
  crew intersection): UID 14 -4, UID 94 3 (2,190 over the 870-minute intersection);
* rounding the elapsed activity: the 24-hour file displays UID 146 at -13.333333333333334 for a
  stored -19,200 minutes where UID 14, on a 24 Hours calendar with the SAME -19,200, reads -13.
  (The first reader of these grids dropped that non-integer cell and read 140 of 140 — a reader
  must never filter the value it judges.) Its behaviour at a tie (-0.5 < x < 0, 44 < x < 44.5) is
  UNVERIFIED: no elapsed activity in the corpus sits there; the field is implemented as displayed.
* UID 302 sits on an OWN-day tie — 49,680 / 1440 = 34.5, shown 34: half-to-even holds on the
  task's axis too (half away from zero would print 35).

Absence semantics mirror ``test_fuse_total_float_field_oracle``: skip only when the intake dir is
absent; a named workbook that is missing FAILS (the oracle must not narrow silently).
"""

from __future__ import annotations

import gzip
import zipfile
from collections.abc import Iterator, Mapping
from fractions import Fraction
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.cpm import compute_cpm, execution_calendar_of
from schedule_forensics.engine.metrics import compute_dcma14, compute_schedule_quality
from schedule_forensics.engine.metrics._common import (
    activity_day_minutes,
    acumen_total_float_field,
    acumen_whole_day_float,
    effective_total_float,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
GOLDEN = REPO / "tests" / "fixtures" / "golden"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_ANALYST = "HA296F~1.XLS"  # the 7/15 Fuse Analyst report: updated3 vs updated4 24 hour calendar
_H24 = "Hard_File_updated4 24 hour calendar"

Cell = str | int | float | bool | None

#: workbook → {Fuse project label: golden} — every save matched by MEASUREMENT, never by name
_WORKBOOKS: dict[str, dict[str, str]] = {
    "Hard_File_Fuse - Fuse Analysis Report.xlsx": {
        "Hard_File": "fuse_hardfile/Hard_File",
        "Hard_File_updated": "fuse_hardfile/Hard_File_updated",
    },
    "Hard_File_update vs update2_Fuse - Analysis Report.xlsx": {
        "Hard_File_updated": "fuse_hardfile/Hard_File_updated",
        "Hard_File_updated2": "fuse_hardfile/Hard_File_updated2",
    },
    "Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx": {
        "Hard_File_updated2": "fuse_hardfile/Hard_File_updated2",
        "Hard_File_updated3": "fuse_hardfile/Hard_File_updated3",  # the rev-2 save (7/9)
    },
    _ANALYST: {
        "Hard_File_updated3": "ssi_hardfile_24h_uid155/Hard_File_updated3",  # rev 5 (7/15)
        _H24: "ssi_hardfile_24h_uid155/Hard_File_updated4_24h",
    },
}
#: activities with a displayed Total Float per (workbook, snapshot) — pinned so a reader or
#: golden regression cannot shrink the population silently
_POPULATION: dict[tuple[str, str], int] = {
    ("Hard_File_Fuse - Fuse Analysis Report.xlsx", "Hard_File"): 45,
    ("Hard_File_Fuse - Fuse Analysis Report.xlsx", "Hard_File_updated"): 61,
    ("Hard_File_update vs update2_Fuse - Analysis Report.xlsx", "Hard_File_updated"): 61,
    ("Hard_File_update vs update2_Fuse - Analysis Report.xlsx", "Hard_File_updated2"): 102,
    ("Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx", "Hard_File_updated2"): 110,
    ("Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx", "Hard_File_updated3"): 110,
    (_ANALYST, "Hard_File_updated3"): 141,
    (_ANALYST, _H24): 141,
}


def _col_index(ref: str) -> int:
    """``"P14"`` → 15: the zero-based column of a cell reference. Fuse's writer omits ``r`` on
    consecutive cells and writes it only where it SKIPPED a column (an empty ratio at a zero
    'before'), so a reader that appends cells in document order slides every later value one
    column left on exactly those rows."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _sheets(path: Path) -> list[tuple[str, list[list[Cell]]]]:
    """Every sheet of an xlsx as rows of typed cells (std-lib only: zip + XML); a cell is placed
    at the column its ``r`` reference names, never merely appended."""
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
                            cells.append(None)  # the column(s) the writer skipped
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
    """A displayed number as Fuse wrote it — an int, or a float kept AS IS (never filtered: the
    raw elapsed float is the finding)."""
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str) and x.strip().lstrip("-").isdigit():
        return int(x)
    return None


_COLUMNS = ("Total Float", "Original Duration", "Remaining Duration")


def _grids(path: Path) -> Iterator[tuple[str, dict[int, tuple[str, dict[str, int | float]]]]]:
    """Every detail grid with Id / Project / Total Float columns: (label, {Id: (project,
    {column: displayed number})}); the label is the last text-only row above the header."""
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
            if "Total Float" in r and "Id" in r and "Project" in r:
                id_i, pj_i = r.index("Id"), r.index("Project")
                cols = {c: r.index(c) for c in _COLUMNS if c in r}
                got: dict[int, tuple[str, dict[str, int | float]]] = {}
                j = i + 1
                while j < len(rows) and len(rows[j]) > max(cols.values()):
                    uid = _as_number(rows[j][id_i])
                    if not isinstance(uid, int):
                        break
                    shown = {
                        c: v for c, k in cols.items() if (v := _as_number(rows[j][k])) is not None
                    }
                    if "Total Float" in shown:
                        got[uid] = (str(rows[j][pj_i]), shown)
                    j += 1
                if got:
                    yield label, got
                i = j
                continue
            i += 1


def _workbooks_present() -> None:
    missing = [name for name in _WORKBOOKS if not (ACUMEN / name).exists()]
    assert not missing, f"Fuse workbook(s) missing from the intake (Law 2 oracle): {missing}"


@cache
def _displayed(workbook: str) -> dict[tuple[str, int], dict[str, int | float]]:
    """(project, Id) → the displayed columns, across every grid of one workbook; an activity
    displayed twice with different values is an ERROR, not a choice."""
    shown: dict[tuple[str, int], dict[str, int | float]] = {}
    for _label, got in _grids(ACUMEN / workbook):
        for uid, (project, values) in got.items():
            prior = shown.setdefault((project, uid), dict(values))
            for col, v in values.items():
                assert prior.setdefault(col, v) == v, (workbook, project, uid, col, prior, v)
    return shown


@cache
def _golden(rel: str) -> Schedule:
    xml = gzip.decompress((GOLDEN / f"{rel}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml, source_file=f"{rel.split('/')[-1]}.mspdi.xml")


@cache
def _effective(rel: str) -> dict[int, float]:
    """The engine's effective total float per activity (the stored slack when the file carries
    it) — the quantity the field is derived from."""
    sch = _golden(rel)
    tf = {u: t.total_float for u, t in compute_cpm(sch).timings.items()}
    return {t.unique_id: effective_total_float(t, tf.get(t.unique_id, 0)) for t in sch.tasks}


def _crew_day(sch: Schedule, task: Task, by_uid: Mapping[int, Calendar]) -> int:
    """The alternative the row weighed: the first assigned resource's own calendar."""
    for a in task.resource_assignments:
        res = sch.resources_by_id.get(a.resource_id)
        if res is not None and res.calendar_uid in by_uid:
            return by_uid[res.calendar_uid].working_minutes_per_day
    return sch.calendar.working_minutes_per_day


def _matches(field: float, shown: int | float) -> bool:
    return abs(field - shown) < 1e-9


def test_every_displayed_total_float_is_the_stored_slack_over_the_activitys_own_day() -> None:
    _workbooks_present()
    misses_by_rule: dict[str, set[tuple[str, int]]] = {
        "project day": set(),
        "crew calendar": set(),
        "execution calendar": set(),
        "task calendar, elapsed on the project day": set(),
        "elapsed axis, task calendar ignored": set(),
        "the elapsed activity rounded": set(),
    }
    wrong: list[tuple[str, str, int, float, int | float]] = []
    population: dict[tuple[str, str], int] = {}
    raw_cells: list[tuple[str, int, int | float]] = []
    for workbook, projects in _WORKBOOKS.items():
        for (project, uid), values in _displayed(workbook).items():
            rel = projects[project]
            sch, eff = _golden(rel), _effective(rel)
            by_uid = {c.uid: c for c in sch.calendars}
            t = sch.tasks_by_id[uid]  # a Fuse Id that is not a UID of the golden raises here
            shown = values["Total Float"]
            population[(workbook, project)] = population.get((workbook, project), 0) + 1
            minutes = eff[uid]
            field = acumen_total_float_field(t, minutes, activity_day_minutes(sch, t, by_uid))
            if not _matches(field, shown):
                wrong.append((workbook, project, uid, field, shown))
            if isinstance(shown, float) and not shown.is_integer():
                raw_cells.append((project, uid, shown))
            mpd = sch.calendar.working_minutes_per_day
            tcal = by_uid.get(t.calendar_uid) if t.calendar_uid is not None else None
            ex = execution_calendar_of(sch, t)
            alternatives = {
                "project day": acumen_whole_day_float(minutes, mpd),
                "crew calendar": acumen_whole_day_float(minutes, _crew_day(sch, t, by_uid)),
                "execution calendar": acumen_whole_day_float(
                    minutes, ex.working_minutes_per_day if ex is not None else mpd
                ),
                "task calendar, elapsed on the project day": acumen_whole_day_float(
                    minutes, tcal.working_minutes_per_day if tcal is not None else mpd
                ),
                "elapsed axis, task calendar ignored": acumen_whole_day_float(
                    minutes, 1440 if t.duration_is_elapsed else mpd
                ),
                "the elapsed activity rounded": acumen_whole_day_float(
                    minutes, activity_day_minutes(sch, t, by_uid)
                ),
            }
            for rule, got in alternatives.items():
                if not _matches(got, shown):
                    misses_by_rule[rule].add((project, uid))
    assert population == _POPULATION, population
    assert not wrong, f"{len(wrong)} displayed floats are not the field: {wrong[:8]}"
    # the ONE non-integer cell in 770 rows: the elapsed activity's slack, raw, on the 24-hour file
    assert raw_cells == [(_H24, 146, -19200 / 1440)] and raw_cells[0][2] == -13.333333333333334
    # the alternatives the row weighed, refuted BY NAME (a superset may miss more; never fewer)
    h24 = _H24
    named = {
        "project day": {
            ("Hard_File_updated", 94),
            ("Hard_File_updated2", 14),
            ("Hard_File_updated2", 146),
            ("Hard_File_updated3", 14),
            ("Hard_File_updated3", 146),
            (h24, 14),
            (h24, 146),
            (h24, 302),
            (h24, 385),
            (h24, 389),
        },
        "crew calendar": {("Hard_File_updated2", 14), (h24, 13), (h24, 389), (h24, 146)},
        "execution calendar": {("Hard_File_updated", 94), ("Hard_File_updated2", 14), (h24, 13)},
        "task calendar, elapsed on the project day": {
            ("Hard_File_updated2", 146),
            ("Hard_File_updated3", 146),
            (h24, 146),
        },
        "elapsed axis, task calendar ignored": {
            ("Hard_File_updated", 94),
            ("Hard_File_updated2", 14),
            (h24, 302),
            (h24, 385),
            (h24, 389),
        },
        "the elapsed activity rounded": {(h24, 146)},
    }
    for rule, rows in named.items():
        assert rows <= misses_by_rule[rule], (rule, rows - misses_by_rule[rule])
    # the project day is exactly the ten named rows — nothing else in 770 moves under the rule
    assert misses_by_rule["project day"] == named["project day"]
    # the discriminating rows, with the values each candidate day prints
    sch2 = _golden("fuse_hardfile/Hard_File_updated2")
    assert _effective("fuse_hardfile/Hard_File_updated2")[14] == -4320
    assert activity_day_minutes(sch2, sch2.tasks_by_id[14]) == 1440  # "24 Hours"
    assert (acumen_whole_day_float(-4320, 1440), acumen_whole_day_float(-4320, 960)) == (-3, -4)
    sch1 = _golden("fuse_hardfile/Hard_File_updated")
    assert _effective("fuse_hardfile/Hard_File_updated")[94] == 2190
    assert activity_day_minutes(sch1, sch1.tasks_by_id[94]) == 930  # "Standard+Sat."
    ex94 = execution_calendar_of(sch1, sch1.tasks_by_id[94])
    assert ex94 is not None and ex94.working_minutes_per_day == 870  # task ∩ crew
    assert (acumen_whole_day_float(2190, 930), acumen_whole_day_float(2190, 870)) == (2, 3)
    sch24 = _golden("ssi_hardfile_24h_uid155/Hard_File_updated4_24h")
    t302 = sch24.tasks_by_id[302]
    eff302 = int(_effective("ssi_hardfile_24h_uid155/Hard_File_updated4_24h")[302])
    assert Fraction(eff302, 1440) == Fraction(69, 2)  # an exact own-day tie
    assert acumen_total_float_field(t302, 49680, activity_day_minutes(sch24, t302)) == 34
    assert _displayed(_ANALYST)[(_H24, 302)]["Total Float"] == 34  # half-even on the own day
    t146 = sch24.tasks_by_id[146]
    assert t146.duration_is_elapsed and t146.calendar_uid is None
    assert acumen_total_float_field(t146, -19200, 1440) == -19200 / 1440  # raw, not -13


def _ribbon_counts() -> dict[str, dict[str, int]]:
    """The 'Ribbon Analysis' sheet's first (count) block: snapshot → {metric: count}."""
    sheets = dict(_sheets(ACUMEN / _ANALYST))
    rows = sheets["Ribbon Analysis"]
    header: list[Cell] | None = None
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        if "Status Date " in r:
            header = r
            continue
        if header is not None and r and r[0] == "Ribbons" and isinstance(r[1], str):
            if r[1] in out:
                break  # the second block repeats the snapshots with the ratios
            out[r[1]] = {
                str(h): int(v)
                for h, v in zip(header, r, strict=False)
                if isinstance(h, str) and h.startswith(("6. ", "7. ")) and isinstance(v, int)
            }
    return out


def test_the_dcma_float_sets_read_that_field_on_the_24_hour_hard_file() -> None:
    _workbooks_present()
    ribbon = _ribbon_counts()
    assert ribbon["Hard_File_updated3"] == {"6. High Float": 0, "7. Negative Float": 40}
    assert ribbon[_H24] == {"6. High Float": 0, "7. Negative Float": 11}
    negative: dict[str, set[int]] = {}
    for label, got in _grids(ACUMEN / _ANALYST):
        if "incomplete and have total float less than 0" in label.lower():
            for uid, (project, _values) in got.items():
                negative.setdefault(project, set()).add(uid)
    assert negative[_H24] == {7, 9, 13, 14, 36, 141, 144, 145, 146, 389, 409}
    assert len(negative["Hard_File_updated3"]) == 40
    # no High Float grid exists in the workbook: an empty set prints no detail rows
    for project, rel in _WORKBOOKS[_ANALYST].items():
        d = compute_dcma14(_golden(rel), acumen_parity=True)
        assert set(d["DCMA06"].offender_uids) == set(), (project, d["DCMA06"].offender_uids)
        assert set(d["DCMA07"].offender_uids) == negative[project], project
        assert d["DCMA07"].count == ribbon[project]["7. Negative Float"]
    # the ribbon's own Negative Float (schedule_quality: every incomplete activity with a stored
    # slack, no baseline filter — a wider population than the DCMA tile's 40 / 11) is UNMOVED
    # by the divisor: 49 / 15 before and after (census: no file in the 44-file corpus moves)
    unmoved = {"Hard_File_updated3": 49, _H24: 15}
    for project, rel in _WORKBOOKS[_ANALYST].items():
        q = compute_schedule_quality(_golden(rel))
        assert q["negative_float"].count == unmoved[project], (project, q["negative_float"])
    # the two activities the project day put in High Float: 104 / 93 project-days of stored
    # slack are 34 / 31 days of their own 24 Hours calendar
    eff24 = _effective("ssi_hardfile_24h_uid155/Hard_File_updated4_24h")
    assert (eff24[302], eff24[385]) == (49680, 44796)
    assert (acumen_whole_day_float(49680, 480), acumen_whole_day_float(44796, 480)) == (104, 93)
    assert (acumen_whole_day_float(49680, 1440), acumen_whole_day_float(44796, 1440)) == (34, 31)


def test_the_duration_fields_divide_by_the_task_calendar_too_r76_registered() -> None:
    """Measured beside the float, NOT consumed by the engine yet (R-76): Fuse's Original and
    Remaining Duration fields also divide by the task's own calendar (UID 14: 1,440 minutes on
    "24 Hours" shown 1, not 3; 24-hour file 302 / 385 / 389: 2 / 3 / 1, not 5 / 9 / 3) — but an
    ELAPSED activity's Original Duration is on the PROJECT day (146: 2,880 minutes shown 6) while
    its Remaining Duration is on 1440 (shown 2). ADR-0515's M1 saw only CHANGED rows, where no
    such activity appears; this pin keeps the register row's premise executable."""
    _workbooks_present()
    shown3 = _displayed(_ANALYST)
    for project in ("Hard_File_updated3", _H24):
        assert shown3[(project, 14)]["Original Duration"] == 1
        assert shown3[(project, 14)]["Remaining Duration"] == 1
        assert shown3[(project, 146)]["Original Duration"] == 6
        assert shown3[(project, 146)]["Remaining Duration"] == 2
    assert shown3[(_H24, 302)]["Original Duration"] == 2  # 2,280 min: 1.58 on 1440, 4.75 on 480
    assert shown3[(_H24, 385)]["Original Duration"] == 3  # 4,224 min: 2.93 on 1440, 8.8 on 480
    assert shown3[(_H24, 389)]["Original Duration"] == 1  # 1,440 min
    sch = _golden("ssi_hardfile_24h_uid155/Hard_File_updated4_24h")
    for uid, minutes in ((14, 1440), (302, 2280), (385, 4224), (389, 1440), (146, 2880)):
        assert sch.tasks_by_id[uid].duration_minutes == minutes, uid
    assert sch.tasks_by_id[146].duration_is_elapsed
    assert all(sch.tasks_by_id[u].calendar_uid == 10 for u in (14, 302, 385, 389))
