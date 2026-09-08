"""MS Project's own stored dates as the CPM oracle — resource calendars and leveling delay
(ADR-0474, R-44).

Every MSPDI carries the reference tool's computed Start / Finish, LateStart / LateFinish,
TotalSlack and Critical per activity. Hard_File's crews work 16-hour and 24-hour calendars and
twelve of its activities carry a resource-leveling delay; the single-calendar engine read its
project finish 42 days after MS Project's (2026-12-17 vs 2026-11-05) and agreed with the
stored Critical flag on 54 of 110 activities. Project2 / Project5 (the Fuse §E goldens) carry
twenty-one leveled activities each; the engine read their finishes 15 / 1 days early.

The pins below are floors measured on 2026-09-07 with the plan-aware engine; a regression on
any of them fails by name. The residuals are named, not hidden: Hard_File's UID 14 (a 200 %
booking on a 24-hour task calendar with a 16-hour crew) spans 40 h where the rule gives 24 h,
so the three unprogressed / lightly progressed snapshots read one day early; updated3's
remaining gap is UID 385 / 403's CONTOURED assignments (R-56), measured in ADR-0476: MS Project
spreads UID 385's 5,664 minutes over ~17 working days (333 min/d) where the engine's booking
rule gives ~6 (944 min/d), and the 45 activities downstream of the seven chain heads inherit it.

ADR-0476 (R-55) closed the progress half and RE-MEASURED every row below. updated3's project-finish
gap WIDENED, 6 d to 13 d, and that is the point: the pre-ADR-0476 engine pushed completed activities
past their recorded finishes (31 of them engine-LATE on this file, worst +38 d), which masked the
contour understatement underneath. Every per-activity measure improved or held — updated3
finish-within-a-day 42 -> 60, stored slack 6 -> 9, Critical 96 -> 103; updated2 87 -> 93; LTF
1558 -> 1569; LTF2 1563 -> 1589 and slack 655 -> 668 — and Project2 / Project5 did not move at all.
Closing R-56 is what tightens the 13 back down; nothing else in this file may loosen.

Red first (pre-ADR-0474 engine): Hard_File finish +42.0 d, critical agreement 54 / 110;
Project2 finish 2027-08-30 vs stored 09-14, stored slack exact on 7 / 65.
"""

from __future__ import annotations

import datetime as dt
import gzip
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import (
    CPMResult,
    _offset_to_wall,
    compute_cpm,
    offset_to_datetime,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@cache
def _load(rel: str) -> tuple[Schedule, CPMResult]:
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    sch = parse_mspdi_text(text)
    return sch, compute_cpm(sch)


def _finish_wall(sch: Schedule, res: CPMResult) -> dt.datetime:
    return res.project_finish_wall or offset_to_datetime(
        sch.project_start, res.project_finish, sch.calendar
    )


def _census(sch: Schedule, res: CPMResult) -> dict[str, int]:
    """Per-activity agreement with the stored values: finishes within a day, stored slack
    reproduced exactly, Critical flag agreed."""
    out = {"n": 0, "finish_1d": 0, "tf_n": 0, "tf_exact": 0, "critical": 0}
    for t in sch.tasks:
        if t.is_summary or not t.is_active:
            continue
        tm = res.timing(t.unique_id)
        out["n"] += 1
        if t.finish is not None:
            ef = tm.early_finish_wall or offset_to_datetime(
                sch.project_start, tm.early_finish, sch.calendar
            )
            out["finish_1d"] += abs((ef - t.finish).total_seconds()) <= 86400
        if t.stored_total_float_minutes is not None:
            out["tf_n"] += 1
            out["tf_exact"] += tm.total_float == t.stored_total_float_minutes
        out["critical"] += tm.is_critical == t.stored_is_critical
    return out


# --- Hard_File: 16-hour and 24-hour crews, twelve leveled activities ----------------------------

_HARD_FILE = [
    # rel, stored finish, |finish gap| <= days, finish-within-a-day floor, critical floor
    ("fuse_hardfile/Hard_File.mspdi.xml.gz", dt.datetime(2026, 11, 5, 12, 0), 1, 92, 108),
    ("fuse_hardfile/Hard_File_updated.mspdi.xml.gz", dt.datetime(2026, 11, 5, 12, 0), 1, 100, 110),
    ("fuse_hardfile/Hard_File_updated2.mspdi.xml.gz", dt.datetime(2026, 11, 6, 17, 0), 1, 93, 80),
    (
        "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
        dt.datetime(2026, 12, 12, 17, 0),
        13,
        60,
        103,
    ),
]


@pytest.mark.parametrize(("rel", "stored", "days", "finish_floor", "critical_floor"), _HARD_FILE)
def test_hard_file_finish_is_within_the_row_tolerance_of_ms_project(
    rel: str, stored: dt.datetime, days: int, finish_floor: int, critical_floor: int
) -> None:
    sch, res = _load(rel)
    assert sch.project_finish == stored  # the stored finish IS the file's FinishDate
    gap = (_finish_wall(sch, res) - stored).total_seconds() / 86400
    assert abs(gap) <= days, f"CPM finish {_finish_wall(sch, res)} vs stored {stored}: {gap:+.1f} d"
    census = _census(sch, res)
    assert census["n"] == 110
    assert census["finish_1d"] >= finish_floor, census
    assert census["critical"] >= critical_floor, census


def test_hard_file_crews_and_leveling_delays_are_what_the_engine_honours() -> None:
    """The registry carries exactly the crews' off-pattern calendars (16 Hour Work Days,
    24 Hours, and the two task calendars), every 16-hour / 24-hour crew is assigned, and the
    twelve leveled activities are reported as leveling-driven."""
    sch, res = _load("fuse_hardfile/Hard_File.mspdi.xml.gz")
    assert [c.uid for c in sch.calendars] == [1, 3, 6, 8, 10, 12]
    by_uid = {c.uid: c for c in sch.calendars}
    assert by_uid[3].working_minutes_per_day == 960 and by_uid[6].working_minutes_per_day == 1440
    crews = {r.unique_id: r.calendar_uid for r in sch.resources}
    assert crews[1] == 3 and crews[4] == 6 and crews[6] == 8
    assert len(res.leveling_driven) == 12 and 403 in res.leveling_driven
    # UID 403: the calendar admits it at 08:00 the working day after its predecessor's
    # finish, 25 d 7 h of ELAPSED delay land on a Sunday, and the calendar admits it again on
    # Monday 08:00 (the stored start sits one working day later because this fixture's UID 401
    # spans 56 h of its crew's calendar for 40 h of duration — a named residual)
    admitted = _offset_to_wall(
        sch.project_start, res.timing(402).early_finish, sch.calendar, role="start"
    )
    raw = admitted + dt.timedelta(minutes=36420)
    assert sch.task_by_id(403).leveling_delay_minutes == 36420 and raw.weekday() == 6
    assert res.timing(403).early_start_wall == dt.datetime(2026, 9, 21, 8, 0)
    # UID 178 / 179: the 16-hour crew after a Friday 17:00 finish — 72 h / 63 h of delay put
    # them at Monday 17:00 and Monday 08:00, exactly the stored starts and finishes
    assert res.timing(178).early_start_wall == dt.datetime(2026, 8, 3, 17, 0)
    assert res.timing(178).early_finish_wall == dt.datetime(2026, 8, 4, 8, 0)
    assert res.timing(179).early_start_wall == dt.datetime(2026, 8, 3, 8, 0)
    assert res.timing(179).total_float == sch.task_by_id(179).stored_total_float_minutes == 480


# --- Project2 / Project5: the leveled Fuse §E goldens ------------------------------------------

_PROJECTS = [
    ("project2_5/Project2.mspdi.xml", dt.datetime(2027, 9, 14, 17, 0), 65, 124),
    ("project2_5/Project5.mspdi.xml", dt.datetime(2028, 1, 26, 17, 0), 95, 126),
]


@pytest.mark.parametrize(("rel", "stored", "tf_n", "critical_floor"), _PROJECTS)
def test_leveled_goldens_reproduce_the_stored_finish_and_every_stored_slack(
    rel: str, stored: dt.datetime, tf_n: int, critical_floor: int
) -> None:
    sch, res = _load(rel)
    assert sch.project_finish == stored
    assert _finish_wall(sch, res) == stored
    census = _census(sch, res)
    assert census["n"] == 126 and census["finish_1d"] == 126
    assert (census["tf_exact"], census["tf_n"]) == (tf_n, tf_n)
    assert census["critical"] >= critical_floor, census


# --- the Large Test Files: eighteen crew calendars that differ only by holidays, unmoved -------

_LARGE = [
    ("fuse_ltf/Large_Test_File.mspdi.xml.gz", 1723, 1569, 842, 1022, 1682),
    ("fuse_ltf/Large_Test_File2.mspdi.xml.gz", 1722, 1589, 668, 936, 1686),
]


@pytest.mark.parametrize(("rel", "n", "finish_floor", "tf_exact", "tf_n", "critical_floor"), _LARGE)
def test_large_test_files_are_unmoved_by_the_crew_calendars(
    rel: str, n: int, finish_floor: int, tf_exact: int, tf_n: int, critical_floor: int
) -> None:
    """Their 177 fixed-work bookings below work / units span the task (the type rule); the
    2026-09-07 figures equal the pre-ADR-0474 engine's exactly."""
    sch, res = _load(rel)
    census = _census(sch, res)
    assert census["n"] == n
    assert census["finish_1d"] >= finish_floor, census
    assert (census["tf_exact"], census["tf_n"]) == (tf_exact, tf_n)
    assert census["critical"] >= critical_floor, census
