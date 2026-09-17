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

ADR-0487 (R-56) closed it: the two heads, UIDs 302 and 385, are finished by MATERIAL / COST
bookings whose recorded windows the engine now reads as execution legs — updated3's project
finish is EXACT (2026-12-12 17:00), finish-within-a-day 60 -> 103 of 110, stored slack exact
9 -> 42 of 68, Critical 103 unmoved; every other golden below is byte-identical. The remaining
seven disagreements are UID 403's leveling split and its chain, the two day-boundary
milestones and UID 188 — none a contour.

ADR-0491 (R-60) read the leveling SPLITS: every golden was regenerated from its OWN save with
the converter's timephased data (tests/fixtures/golden/PROVENANCE.json), the importer reads a
WORK booking's zero-work blocks as the boundaries of its pieces, and the engine honours the gap
between the pieces that no other booking of the task works through — in working minutes of the
leg's calendar, forward and on the backward pass. Re-measured on every golden: the three
unprogressed / lightly progressed Hard_File snapshots' project finishes went from one day early
to EXACT; finish-within-a-day Hard_File 92 -> 103, updated 100 -> 108, updated2 93 -> 109 (its
Critical agreement 80 -> 107), updated3 104 -> 106 (UID 403 and 404 exact, 403's stored slack
12,888 reproduced); Large_Test_File 1569 -> 1666 (stored slack 842 -> 865, Critical 1682 ->
1721), File2 1589 -> 1687 (1686 -> 1717); Project2 / Project5 unmoved and still exact. No
activity anywhere moved AWAY from its stored finish except UID 5306's chain on the leveled SSI
golden, by the 8 minutes MS Project's own arithmetic carries (four 2:36 daily gaps) on a start
already a day late. Hard_File's UID 14 now spans its stored 10-26 20:00 -> 10-29 11:00 exactly;
UID 401 spans 5.6 days like MS Project; its chain sat one working day early, registered as R-64
with a mechanism ("milestone 387 hangs on an external predecessor, UID -65535") the file refutes:
no external link exists in any golden, and -65535 is the ResourceUID of MS Project's unassigned-
work placeholder on the milestone's own assignment.

ADR-0505 (R-64) found and carried the instant the axis lost: a project-calendar MILESTONE between
two crew-calendar activities. UID 178's 16-hour crew finishes Tuesday 08-04 08:00; milestone 181
is stored there; the integer project axis cannot tell that minute from Monday 17:00, and the crew
successor 189 was started from the minute's end-of-day rendering — fifteen hours early, then a
working day early once 187's 9-hour shortfall crossed 08-14 17:00 (184 -> 148 -> 384 landed on
the Friday, MS Project on the Monday) — all the way down 385 -> 386 -> 387 -> 400 -> 404. A
zero-duration project-axis task now carries its driving predecessor's wall instant (its own
integer minute unchanged), and a crew successor starts from it. Re-measured on every golden:
Hard_File EVERY activity finishes on its stored instant (finish-within-a-day 103 -> 110, exact
40 -> 110, stored slack exact 39 -> 101 of 110, Critical 108 -> 110); updated 108 -> 110;
updated2 109 -> 110; updated3 106 -> 110; the 24-hour snapshot's project finish 11-17 01:00 ->
the stored 11-19 01:00 EXACT (finish-within-a-day 100 -> 109, stored slack 4 -> 7 of 19: UID
407's 1,920 and UIDs 411 / 155's -4,320 now exact); Project2 / Project5 / the Large Test Files
unmoved (two milestones there, UIDs 168 and 7107, now sit ON their predecessor's finish instead
of the lunch hour after it — the contiguous projection's documented drift, no longer displayed).

Red first (pre-ADR-0474 engine): Hard_File finish +42.0 d, critical agreement 54 / 110;
Project2 finish 2027-08-30 vs stored 09-14, stored slack exact on 7 / 65. Red first
(pre-ADR-0505 engine): every floor below at its new value, and every dated pin in
test_hard_file_crews_and_leveling_delays_are_what_the_engine_honours, by name.
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
    # rel, stored finish, |finish gap| <= days, finish-within-a-day floor, critical floor,
    # stored-slack-exact floor
    # (ADR-0491: every snapshot's project finish is EXACT once the leveling splits are read;
    # ADR-0505: every activity of the four Standard-calendar snapshots finishes within a day —
    # 110 of 110 — and the 24-hour snapshot's finish is EXACT too, its own row below)
    ("fuse_hardfile/Hard_File.mspdi.xml.gz", dt.datetime(2026, 11, 5, 12, 0), 0, 110, 110, 101),
    (
        "fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
        dt.datetime(2026, 11, 5, 12, 0),
        0,
        110,
        110,
        101,
    ),
    (
        "fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
        dt.datetime(2026, 11, 6, 17, 0),
        0,
        110,
        107,
        36,
    ),
    (
        "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
        dt.datetime(2026, 12, 12, 17, 0),
        0,
        110,
        103,
        46,
    ),
    # the 24-hour snapshot (its crews and the post-launch chain on the 24 Hours calendar):
    # UID 156 "Post Launch Preparation COMPLETE" is stored on a SUNDAY, 11-15 17:00, where its
    # crew predecessor finished; carrying that instant puts the chain 36 -> 9 -> 144 -> 145 ->
    # 146 -> 411 / 155 on its stored dates and the project finish on the stored 11-19 01:00
    (
        "fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz",
        dt.datetime(2026, 11, 19, 1, 0),
        0,
        109,
        70,
        7,
    ),
]


def test_updated3_finishes_where_ms_project_finishes_once_recorded_bookings_are_read() -> None:
    """R-56 (ADR-0487): UIDs 302 and 385 are finished by material / cost bookings whose
    recorded windows the engine now reads. The project finish is EXACT (it read 13 days early),
    both heads land on the recorded instant, and the disclosure names them. UID 403 is the
    remaining head — a leveling SPLIT (seven days of gap between two work pieces in the .mpp)
    the MSPDI does not carry; its own row."""
    sch, res = _load("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz")
    assert _finish_wall(sch, res) == dt.datetime(2026, 12, 12, 17, 0)
    assert res.timing(385).early_finish_wall == dt.datetime(2026, 11, 4, 14, 24)
    assert res.timing(302).early_finish_wall == dt.datetime(2026, 10, 21, 12, 0)
    # UID 210 too: a COMPLETED fixed-duration task whose 24-hour crew leg alone would end four
    # days early; its material window carries the plan to the recorded finish, which the
    # completed-window pin (ADR-0476) then confirms — the disclosure names what the plan did
    assert res.booking_span_driven == (210, 302, 385)
    # UID 403 is the leveling SPLIT (ADR-0491, R-60): three pieces of work with eight working
    # days and 3.2 hours of nothing between them, read from the regenerated golden's
    # timephased data; it lands on the stored instant (the contiguous engine read 10-23 15:00)
    assert res.timing(403).early_finish_wall == dt.datetime(2026, 11, 5, 9, 12)
    assert res.timing(403).late_start_wall == dt.datetime(2026, 11, 25, 13, 48)
    assert res.timing(403).total_float == sch.task_by_id(403).stored_total_float_minutes == 12888
    assert 403 in res.split_driven
    census = _census(sch, res)
    assert census["tf_exact"] >= 46 and census["tf_n"] == 68


@pytest.mark.parametrize(
    ("rel", "stored", "days", "finish_floor", "critical_floor", "tf_floor"), _HARD_FILE
)
def test_hard_file_finish_is_within_the_row_tolerance_of_ms_project(
    rel: str,
    stored: dt.datetime,
    days: int,
    finish_floor: int,
    critical_floor: int,
    tf_floor: int,
) -> None:
    sch, res = _load(rel)
    assert sch.project_finish == stored  # the stored finish IS the file's FinishDate
    gap = (_finish_wall(sch, res) - stored).total_seconds() / 86400
    assert abs(gap) <= days, f"CPM finish {_finish_wall(sch, res)} vs stored {stored}: {gap:+.1f} d"
    census = _census(sch, res)
    assert census["n"] == 110
    assert census["finish_1d"] >= finish_floor, census
    assert census["critical"] >= critical_floor, census
    assert census["tf_exact"] >= tf_floor, census


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
    # finish and 25 d 7 h of ELAPSED delay put it at 15:00 on the Tuesday — MS Project's own
    # arithmetic (its 402 finishes Thursday 08-27, 08-28 08:00 + 25 d 7 h = the stored Tuesday
    # 09-22 15:00). UID 401's span itself (5.6 days for 40 h of work) is the split ADR-0491
    # reads. The chain sat one working day early until ADR-0505 (R-64): milestone 181 is
    # stored at Tuesday 08-04 08:00, where its 16-hour crew (UID 178) finished; the project
    # axis rendered that minute as Monday 17:00 and started the crew successor 189 there.
    admitted = _offset_to_wall(
        sch.project_start, res.timing(402).early_finish, sch.calendar, role="start"
    )
    assert sch.task_by_id(403).leveling_delay_minutes == 36420
    assert admitted + dt.timedelta(minutes=36420) == dt.datetime(2026, 9, 22, 15, 0)
    assert res.timing(403).early_start_wall == dt.datetime(2026, 9, 22, 15, 0)
    assert res.timing(401).early_start_wall == dt.datetime(2026, 8, 21, 17, 0)
    assert res.timing(401).early_finish_wall == dt.datetime(2026, 8, 27, 8, 0)
    # the R-64 chain, from the carried instant down to the milestone that closes it — every
    # one on its stored Start / Finish (the carried milestones expose the instant on their
    # early walls; the crew activities on theirs; UID 384 is a Standard-calendar activity,
    # read through the axis), and the stored slack of the chain's head, 240 minutes
    assert res.timing(178).early_finish_wall == dt.datetime(2026, 8, 4, 8, 0)
    assert res.timing(181).early_start_wall == dt.datetime(2026, 8, 4, 8, 0)
    assert res.timing(181).early_finish_wall == dt.datetime(2026, 8, 4, 8, 0)
    assert res.timing(189).early_start_wall == dt.datetime(2026, 8, 4, 8, 0)
    assert res.timing(189).early_finish_wall == dt.datetime(2026, 8, 4, 17, 0)
    assert res.timing(189).total_float == sch.task_by_id(189).stored_total_float_minutes == 240
    assert res.timing(187).early_finish_wall == dt.datetime(2026, 8, 14, 17, 0)
    assert res.timing(184).early_finish_wall == dt.datetime(2026, 8, 14, 17, 0)
    assert res.timing(148).early_finish_wall == dt.datetime(2026, 8, 14, 17, 0)
    assert _offset_to_wall(
        sch.project_start, res.timing(384).early_start, sch.calendar, role="start"
    ) == dt.datetime(2026, 8, 17, 8, 0)
    assert res.timing(387).early_finish_wall == dt.datetime(2026, 8, 18, 17, 0)
    assert res.timing(400).early_start_wall == dt.datetime(2026, 8, 18, 17, 0)
    assert res.timing(403).early_finish_wall == dt.datetime(2026, 10, 8, 15, 0)
    assert res.timing(404).early_finish_wall == dt.datetime(2026, 10, 8, 15, 0)
    # the other three handoffs the census found on this file: milestones 216 and 381 hand
    # their crew successors 241 and 396 the stored instants; every one of the 110 activities
    # now finishes on its stored Finish (the row's floor above is 110)
    assert res.timing(241).early_start_wall == dt.datetime(2026, 8, 21, 12, 0)
    assert res.timing(396).early_start_wall == dt.datetime(2026, 8, 24, 13, 0)
    assert res.timing(396).early_finish_wall == dt.datetime(2026, 8, 25, 12, 0)
    # UID 14 (a 200 % booking on a 24-hour task calendar, a 16-hour crew, split by leveling):
    # the stored span, exactly
    assert res.timing(14).early_start_wall == dt.datetime(2026, 10, 26, 20, 0)
    assert res.timing(14).early_finish_wall == dt.datetime(2026, 10, 29, 11, 0)
    assert res.split_driven == (14, 321, 398, 401, 403)
    # UID 178 / 179: the 16-hour crew after a Friday 17:00 finish — 72 h / 63 h of delay put
    # them at Monday 17:00 and Monday 08:00, exactly the stored starts and finishes
    assert res.timing(178).early_start_wall == dt.datetime(2026, 8, 3, 17, 0)
    assert res.timing(178).early_finish_wall == dt.datetime(2026, 8, 4, 8, 0)
    assert res.timing(179).early_start_wall == dt.datetime(2026, 8, 3, 8, 0)
    assert res.timing(179).total_float == sch.task_by_id(179).stored_total_float_minutes == 480


# --- Project2 / Project5: the leveled Fuse §E goldens ------------------------------------------

# tf_n RE-PINNED 65 → 106 and 95 → 99 on 2026-09-14 (R-49, ADR-0490): the importer now infers the
# zero the MPXJ writer dropped on every Critical activity whose ``TotalSlack`` element is absent
# (41 on Project2, 4 on Project5), so the stored-slack population grows by exactly those — and
# tf_exact grows by the same, because the engine's pure-logic float is 0 for every one of them.
_PROJECTS = [
    ("project2_5/Project2.mspdi.xml", dt.datetime(2027, 9, 14, 17, 0), 106, 124),
    ("project2_5/Project5.mspdi.xml", dt.datetime(2028, 1, 26, 17, 0), 99, 126),
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

# (tf_exact, tf_n) RE-PINNED (842, 1022) → (844, 1024) and (668, 936) → (730, 998) on 2026-09-14
# (R-49, ADR-0490): the inferred zeros — 2 on Large Test File, 62 on File2, every one a Critical
# activity whose element the MPXJ writer dropped — join the stored-slack population, and each is
# reproduced exactly by the engine's own float. The pre-inference figures are the ones on the left.
_LARGE = [
    ("fuse_ltf/Large_Test_File.mspdi.xml.gz", 1723, 1666, 867, 1024, 1721),
    ("fuse_ltf/Large_Test_File2.mspdi.xml.gz", 1722, 1687, 730, 998, 1717),
]


@pytest.mark.parametrize(("rel", "n", "finish_floor", "tf_exact", "tf_n", "critical_floor"), _LARGE)
def test_large_test_files_are_unmoved_by_the_crew_calendars(
    rel: str, n: int, finish_floor: int, tf_exact: int, tf_n: int, critical_floor: int
) -> None:
    """Their 177 fixed-work bookings below work / units span the task (the type rule); the
    2026-09-07 figures equalled the pre-ADR-0474 engine's exactly, and ADR-0491's splits moved
    every one of their 100 / 104 movers TOWARD the stored finish, none away."""
    sch, res = _load(rel)
    census = _census(sch, res)
    assert census["n"] == n
    assert census["finish_1d"] >= finish_floor, census
    assert (census["tf_exact"], census["tf_n"]) == (tf_exact, tf_n)
    assert census["critical"] >= critical_floor, census
