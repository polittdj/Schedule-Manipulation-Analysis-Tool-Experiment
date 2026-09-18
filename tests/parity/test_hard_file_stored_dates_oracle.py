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

R-67 (ADR-0510) carried the LATE instant, the backward mirror: a fast-path milestone whose
binding need is an instant the axis lost — a wall-path successor's late start less its elapsed
leveling delay, a carried milestone's instant, or (on a file with wall-path tasks) a binding
deadline / constraint date or the backward target — sits at the earliest such instant, a
wall-path predecessor retreats from it, and a milestone whose early instant is carried measures
its slack between its two instants. Hard_File UID 147's stored LateStart is SATURDAY 08-01 13:00
(178's late start less 72 elapsed hours); the crew predecessor 157 read Monday 08:00 for it and
took its late finish two crew hours after the stored Friday 23:00, and UID 94 inherited 150
minutes of slack on its own calendar (6,510 vs 6,360). On the 24-hour snapshot the chain head is
milestone 155's DEADLINE, 11-05 17:00 — no successor at all — and the 24-hour crew below it read
11-06 08:00, fifteen crew hours late, down to milestone 156 (-4,320 vs -4,740). Re-measured on
every golden, late-finish instants EXACT: Hard_File 78 -> 94 of 110, updated 83 -> 87, updated2
27 -> 37, updated3 30 -> 45, the 24-hour snapshot 3 -> 15; stored slack exact Hard_File 101 -> 108
(404's 9,480), updated2 36 -> 38, updated3 46 -> 48, the 24-hour snapshot 7 -> 15; Project2 /
Project5 unmoved (108 / 99 late finishes exact); the Large Test Files' late finishes unmoved
(918 -> 919, 824) and 18 / 25 milestone late starts newly exact. Across the 44 files (15 goldens +
29 conversions) 268 late finishes moved toward the stored instant and 17 away — every one of the
17 on a chain whose late dates MS Project derives past a COMPLETED or STARTED successor the
engine's backward pass still runs through (updated3's 188 is stored 12-12 while its completed
successor 291's late start is 09-08), or a completed milestone's own record; registered, not
this rule's.

Red first (pre-ADR-0474 engine): Hard_File finish +42.0 d, critical agreement 54 / 110;
Project2 finish 2027-08-30 vs stored 09-14, stored slack exact on 7 / 65. Red first
(pre-ADR-0505 engine): every floor below at its new value, and every dated pin in
test_hard_file_crews_and_leveling_delays_are_what_the_engine_honours, by name. Red first
(pre-R-67 engine): every late-finish floor, the raised slack floors, and every dated pin in
test_a_milestones_late_instant_is_carried_to_its_crew_predecessor, by name.
"""

from __future__ import annotations

import datetime as dt
import gzip
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import (
    CPMResult,
    _offset_to_wall,
    compute_cpm,
    is_recorded_complete,
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


_NS = "{http://schemas.microsoft.com/project}"


@cache
def _stored_late_finishes(rel: str) -> dict[int, dt.datetime]:
    """MS Project's stored LateFinish per UID, read from the golden's own XML — the model does
    not carry late dates (CPM dates are derived by the engine, never stored on the task).
    Keyed by the golden's PATH: the Hard_File snapshots share one project name."""
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    out: dict[int, dt.datetime] = {}
    for node in ET.fromstring(text).iter(_NS + "Task"):
        uid, lf = node.findtext(_NS + "UID"), node.findtext(_NS + "LateFinish")
        if uid is not None and lf:
            out[int(uid)] = dt.datetime.fromisoformat(lf)
    assert out, rel
    return out


def _finish_wall(sch: Schedule, res: CPMResult) -> dt.datetime:
    return res.project_finish_wall or offset_to_datetime(
        sch.project_start, res.project_finish, sch.calendar
    )


def _census(sch: Schedule, res: CPMResult, rel: str) -> dict[str, int]:
    """Per-activity agreement with the stored values: finishes within a day, stored slack
    reproduced exactly, Critical flag agreed, late-finish instant exact (R-67)."""
    out = {
        "n": 0,
        "finish_1d": 0,
        "tf_n": 0,
        "tf_exact": 0,
        "critical": 0,
        "lf_n": 0,
        "lf_exact": 0,
    }
    stored_lf = _stored_late_finishes(rel)
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
        # R-67 (ADR-0510): the late-finish INSTANT against MS Project's stored LateFinish (read
        # from the file's own XML — the model carries no late dates), exact to the second.
        # R-70 (ADR-0512, 2026-09-18): INCOMPLETE activities only — a completed activity's
        # stored LateFinish is its ActualFinish (8,644 of 8,644 across the 44-file corpus), a
        # record the engine does not model (18 coincidental matches before R-70, 0 after), so
        # it adjudicates nothing here, ADR-0507's decision 3 applied to the late dates.
        if not is_recorded_complete(t):
            lf = tm.late_finish_wall or _offset_to_wall(
                sch.project_start, tm.late_finish, sch.calendar, role="finish"
            )
            out["lf_n"] += 1
            out["lf_exact"] += stored_lf.get(t.unique_id) == lf
        # R-62 (ADR-0507, 2026-09-18): a completed activity's stored slack is MS Project's zero by
        # fiat (its stored start AND finish slack are (0, 0) on every finished activity of every
        # intake file) — a record, not a schedule — so it adjudicates nothing here. A no-op on
        # the pre-R-62 importer (no finished activity carries the element on any golden) and
        # load-bearing after it: without the progress guard Project2's tf_n reads 126, not 106.
        if t.stored_total_float_minutes is not None and t.percent_complete < 100.0:
            out["tf_n"] += 1
            out["tf_exact"] += tm.total_float == t.stored_total_float_minutes
        out["critical"] += tm.is_critical == t.stored_is_critical
    return out


# --- Hard_File: 16-hour and 24-hour crews, twelve leveled activities ----------------------------

_HARD_FILE = [
    # rel, stored finish, |finish gap| <= days, finish-within-a-day floor, critical floor,
    # stored-slack-exact floor, late-finish-instant-exact floor
    # (ADR-0491: every snapshot's project finish is EXACT once the leveling splits are read;
    # ADR-0505: every activity of the four Standard-calendar snapshots finishes within a day —
    # 110 of 110 — and the 24-hour snapshot's finish is EXACT too, its own row below;
    # R-67 / ADR-0510: the slack floors 101 -> 108, 36 -> 38, 46 -> 48, 7 -> 15 and the late-finish
    # floors 94 / 87 / 37 / 45 / 15 — measured 2026-09-18 with the carried late instant;
    # R-70 / ADR-0512 (2026-09-18): a finished successor presents no late need and a started one
    # its remaining portion — the Critical floors 107 -> 109, 103 -> 109 and 70 -> 110, the slack
    # floor 48 -> 49 (updated3's UID 188, the row's witness) and the 24-hour snapshot's
    # late-finish floor 15 -> 17 (UIDs 302 / 385, bound by the project finish once their
    # completed successors bind nothing); the late-finish census counts incomplete work only)
    (
        "fuse_hardfile/Hard_File.mspdi.xml.gz",
        dt.datetime(2026, 11, 5, 12, 0),
        0,
        110,
        110,
        108,
        94,
    ),
    (
        "fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
        dt.datetime(2026, 11, 5, 12, 0),
        0,
        110,
        110,
        101,
        87,
    ),
    (
        "fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
        dt.datetime(2026, 11, 6, 17, 0),
        0,
        110,
        109,
        38,
        37,
    ),
    (
        "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
        dt.datetime(2026, 12, 12, 17, 0),
        0,
        110,
        109,
        49,
        45,
    ),
    # the 24-hour snapshot (its crews and the post-launch chain on the 24 Hours calendar):
    # UID 156 "Post Launch Preparation COMPLETE" is stored on a SUNDAY, 11-15 17:00, where its
    # crew predecessor finished; carrying that instant puts the chain 36 -> 9 -> 144 -> 145 ->
    # 146 -> 411 / 155 on its stored dates and the project finish on the stored 11-19 01:00.
    # R-67: milestone 155's late instant is its DEADLINE, and carrying it puts the same chain's
    # LATE dates and slacks on the stored values too (156: -4,740; 146: -19,200)
    (
        "fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz",
        dt.datetime(2026, 11, 19, 1, 0),
        0,
        109,
        110,
        15,
        17,
    ),
]


def test_updated3_finishes_where_ms_project_finishes_once_recorded_bookings_are_read() -> None:
    """R-56 (ADR-0487): UIDs 302 and 385 are finished by material / cost bookings whose
    recorded windows the engine now reads. The project finish is EXACT (it read 13 days early),
    both heads land on the recorded instant, and the disclosure names them. UID 403 is the
    remaining head — a leveling SPLIT (seven days of gap between two work pieces in the .mpp)
    the MSPDI does not carry; its own row."""
    rel = "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz"
    sch, res = _load(rel)
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
    census = _census(sch, res, rel)
    assert census["tf_exact"] >= 46 and census["tf_n"] == 68


@pytest.mark.parametrize(
    ("rel", "stored", "days", "finish_floor", "critical_floor", "tf_floor", "lf_floor"),
    _HARD_FILE,
)
def test_hard_file_finish_is_within_the_row_tolerance_of_ms_project(
    rel: str,
    stored: dt.datetime,
    days: int,
    finish_floor: int,
    critical_floor: int,
    tf_floor: int,
    lf_floor: int,
) -> None:
    sch, res = _load(rel)
    assert sch.project_finish == stored  # the stored finish IS the file's FinishDate
    gap = (_finish_wall(sch, res) - stored).total_seconds() / 86400
    assert abs(gap) <= days, f"CPM finish {_finish_wall(sch, res)} vs stored {stored}: {gap:+.1f} d"
    census = _census(sch, res, rel)
    assert census["n"] == 110
    assert census["finish_1d"] >= finish_floor, census
    assert census["critical"] >= critical_floor, census
    assert census["tf_exact"] >= tf_floor, census
    assert census["lf_exact"] >= lf_floor, census


def test_a_milestones_late_instant_is_carried_to_its_crew_predecessor() -> None:
    """R-67 (ADR-0510), the backward mirror of ADR-0505. Base snapshot: milestone 147's stored
    LateStart is Saturday 08-01 13:00 — UID 178's late start less its 72 elapsed hours of
    leveling delay — and the crew predecessor 157 retreats from it onto its stored Friday
    23:00 (its late start 15:00, its slack 2,760 — the START slack on the project calendar);
    UID 94, one link higher, lands on its stored late window and its stored 6,360 on its own
    ``Standard+Sat.`` calendar. The same rule one link down: milestone 181's late instant is
    the crew successor 189's late start, 08-04 21:00 — an instant outside the Standard day —
    and 178 / 179 / 180 retreat from it onto their stored 21:00 late finishes and their stored
    slacks 240 / 480 / 720. Milestone 404, the network's end after a crew whose finish sits
    mid-day (10-08 15:00), measures its slack between its two instants: 9,480, the stored
    figure (the axis's contiguous projection read 9,420). The one form left, named: the engine
    writes 178's late start at the END of the crew's morning block, 12:00, where MS Project
    writes the START of its afternoon block, 13:00 — the same working minute on every calendar
    in the file — so 147's carried instant reads Saturday 12:00 for the stored 13:00 (the
    contiguous projection of the 13:00 form would hand every project-calendar predecessor the
    lunch hour as float; registered, not chased)."""
    rel = "fuse_hardfile/Hard_File.mspdi.xml.gz"
    sch, res = _load(rel)
    stored_lf = _stored_late_finishes(rel)
    assert res.timing(189).late_start_wall == dt.datetime(2026, 8, 4, 21, 0)
    assert res.timing(189).late_finish_wall == stored_lf[189] == dt.datetime(2026, 8, 5, 12, 0)
    assert res.timing(181).late_start_wall == res.timing(181).late_finish_wall
    assert res.timing(181).late_finish_wall == stored_lf[181] == dt.datetime(2026, 8, 4, 21, 0)
    for uid, slack in ((178, 240), (179, 480), (180, 720)):
        assert res.timing(uid).late_finish_wall == stored_lf[uid] == dt.datetime(2026, 8, 4, 21, 0)
        assert res.timing(uid).late_start_wall == dt.datetime(2026, 8, 4, 12, 0)
        assert res.timing(uid).total_float == sch.task_by_id(uid).stored_total_float_minutes
        assert res.timing(uid).total_float == slack
    assert res.timing(147).late_start_wall == res.timing(147).late_finish_wall
    assert res.timing(147).late_finish_wall == dt.datetime(2026, 8, 1, 12, 0)
    assert stored_lf[147] == dt.datetime(2026, 8, 1, 13, 0)
    assert res.timing(147).total_float == sch.task_by_id(147).stored_total_float_minutes == 0
    assert res.timing(157).late_finish_wall == stored_lf[157] == dt.datetime(2026, 7, 31, 23, 0)
    assert res.timing(157).late_start_wall == dt.datetime(2026, 7, 31, 15, 0)
    assert res.timing(157).total_float == sch.task_by_id(157).stored_total_float_minutes == 2760
    assert res.timing(94).late_finish_wall == stored_lf[94] == dt.datetime(2026, 7, 31, 15, 0)
    assert res.timing(94).late_start_wall == dt.datetime(2026, 7, 30, 22, 0)
    assert res.timing(94).total_float == sch.task_by_id(94).stored_total_float_minutes == 6360
    assert res.timing(404).late_finish_wall == stored_lf[404] == dt.datetime(2026, 11, 5, 12, 0)
    assert res.timing(404).early_finish_wall == dt.datetime(2026, 10, 8, 15, 0)
    assert res.timing(404).total_float == sch.task_by_id(404).stored_total_float_minutes == 9480
    # the 24-hour snapshot: the chain head is milestone 155's DEADLINE, carried with no successor
    # at all; the 24-hour crew 146 retreats from it (11-05 17:00, not the rendered 11-06 08:00)
    # and the chain 145 -> 144 -> 9 -> 36 -> 156 lands on every stored late date and slack
    rel = "fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz"
    sch, res = _load(rel)
    stored_lf = _stored_late_finishes(rel)
    deadline = dt.datetime(2026, 11, 5, 17, 0)
    assert sch.task_by_id(155).deadline == deadline
    assert res.timing(155).late_finish_wall == res.timing(411).late_finish_wall == deadline
    assert res.timing(146).late_finish_wall == stored_lf[146] == deadline
    assert res.timing(146).late_start_wall == dt.datetime(2026, 11, 3, 17, 0)
    assert res.timing(146).total_float == sch.task_by_id(146).stored_total_float_minutes == -19200
    for uid, lf, slack in (
        (145, dt.datetime(2026, 11, 3, 17, 0), -4740),
        (144, dt.datetime(2026, 11, 3, 9, 0), -4740),
        (9, dt.datetime(2026, 11, 3, 1, 0), -4380),
        (36, dt.datetime(2026, 11, 2, 17, 0), -4740),
        (141, dt.datetime(2026, 11, 2, 9, 0), -4800),
    ):
        assert res.timing(uid).late_finish_wall == stored_lf[uid] == lf
        assert res.timing(uid).total_float == sch.task_by_id(uid).stored_total_float_minutes
        assert res.timing(uid).total_float == slack
    assert res.timing(156).late_finish_wall == stored_lf[156] == dt.datetime(2026, 11, 2, 9, 0)
    assert res.timing(156).total_float == sch.task_by_id(156).stored_total_float_minutes == -4740


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
# lf_exact (the late-finish INSTANT) 108 / 99 of 126 — unmoved by R-67 (ADR-0510): these
# files carry no zero-duration task, so the carried late instant cannot touch them (a control).
# lf_exact RE-PINNED 108 -> 106 of 106 and 99 of 99 on 2026-09-18 (R-70, ADR-0512): the census
# now counts INCOMPLETE activities only — a completed activity's stored LateFinish is its
# ActualFinish, a record (8,644 of 8,644 across the corpus) the engine does not model, and
# Project2's two coincidental matches were completed activities bound to completed successors.
# EVERY incomplete activity of both files now has its late-finish instant exact, and Project2's
# Critical agreement is 126 of 126 (the two completed activities that read critical carry the
# float of the project finish, as MS Project reads them).
_PROJECTS = [
    ("project2_5/Project2.mspdi.xml", dt.datetime(2027, 9, 14, 17, 0), 106, 126, 106),
    ("project2_5/Project5.mspdi.xml", dt.datetime(2028, 1, 26, 17, 0), 99, 126, 99),
]


@pytest.mark.parametrize(("rel", "stored", "tf_n", "critical_floor", "lf_exact"), _PROJECTS)
def test_leveled_goldens_reproduce_the_stored_finish_and_every_stored_slack(
    rel: str, stored: dt.datetime, tf_n: int, critical_floor: int, lf_exact: int
) -> None:
    sch, res = _load(rel)
    assert sch.project_finish == stored
    assert _finish_wall(sch, res) == stored
    census = _census(sch, res, rel)
    assert census["n"] == 126 and census["finish_1d"] == 126
    assert (census["tf_exact"], census["tf_n"]) == (tf_n, tf_n)
    assert census["critical"] >= critical_floor, census
    assert (census["lf_exact"], census["lf_n"]) == (lf_exact, lf_exact), census


# --- the Large Test Files: eighteen crew calendars that differ only by holidays, unmoved -------

# (tf_exact, tf_n) RE-PINNED (842, 1022) → (844, 1024) and (668, 936) → (730, 998) on 2026-09-14
# (R-49, ADR-0490): the inferred zeros — 2 on Large Test File, 62 on File2, every one a Critical
# activity whose element the MPXJ writer dropped — join the stored-slack population, and each is
# reproduced exactly by the engine's own float. The pre-inference figures are the ones on the left.
# tf_exact RE-PINNED 867 → 874 and 730 → 736 on 2026-09-18 (R-65, ADR-0508): the leveling gaps
# are measured in working seconds and rounded cumulatively to the minute, so 13 / 21 split
# bookings occupy exactly the window MS Project recorded (they read 1 to 62 minutes short), and
# 66 / 101 activities moved TOWARD their stored finish in working minutes, none away; File2's
# finish-within-a-day 1687 → 1689.
# lf_floor (the late-finish INSTANT, exact): 918 -> 919 and 824 on 2026-09-18 (R-67, ADR-0510) —
# the carried late instant reaches one activity on Large Test File and no finish on File2, while
# 18 / 25 of their milestones' late starts became exact with it.
# tf_exact RE-PINNED 874 -> 876 and 736 -> 740, lf_floor 919 -> 921 and 824 -> 828, the Critical
# floors 1721 -> 1723 and 1717 -> 1721 on 2026-09-18 (R-70, ADR-0512): the predecessors of
# finished work take their late dates from the project finish, and those of started work from
# the remaining portion — 2 / 4 late finishes and 2 / 4 slacks newly exact, none lost.
_LARGE = [
    ("fuse_ltf/Large_Test_File.mspdi.xml.gz", 1723, 1666, 876, 1024, 1723, 921),
    ("fuse_ltf/Large_Test_File2.mspdi.xml.gz", 1722, 1689, 740, 998, 1721, 828),
]


@pytest.mark.parametrize(
    ("rel", "n", "finish_floor", "tf_exact", "tf_n", "critical_floor", "lf_floor"), _LARGE
)
def test_large_test_files_are_unmoved_by_the_crew_calendars(
    rel: str,
    n: int,
    finish_floor: int,
    tf_exact: int,
    tf_n: int,
    critical_floor: int,
    lf_floor: int,
) -> None:
    """Their 177 fixed-work bookings below work / units span the task (the type rule); the
    2026-09-07 figures equalled the pre-ADR-0474 engine's exactly, and ADR-0491's splits moved
    every one of their 100 / 104 movers TOWARD the stored finish, none away."""
    sch, res = _load(rel)
    census = _census(sch, res, rel)
    assert census["n"] == n
    assert census["finish_1d"] >= finish_floor, census
    assert (census["tf_exact"], census["tf_n"]) == (tf_exact, tf_n)
    assert census["critical"] >= critical_floor, census
    assert census["lf_exact"] >= lf_floor, census


# --- R-70 (ADR-0512): the backward pass stops at finished work --------------------------------


def test_the_backward_pass_does_not_run_through_a_completed_successor() -> None:
    """Hard_File_updated3 UID 188's only successor is the completed UID 291, stored with a late
    start of 09-08 08:00 — its own record. MS Project derives 188's late finish from the project
    finish (stored 12-12 17:00, TotalSlack 203,345 tenths = 20,334.5 min, FreeSlack the same);
    the pre-R-70 engine bound 188 to 291's need and read 09-08, three months early, -12,305
    minutes of float, and 189 / 181 / 178 / 179 / 180 above it followed. Now 188's late finish
    IS the backward target, its free float is measured to the project finish like its total
    float, and the chain's floats sit within the half-minute of a sub-minute recorded instant
    (188 finishes 14:05:30) of the stored figures. The target's instant is the Saturday 12-12
    17:00 of a crew's calendar; a non-zero-duration activity on the project axis reads the
    minute's Friday rendering, 12-11 17:00 — R-67's non-milestone class, named, not this row's."""
    sch, res = _load("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz")
    by = {t.unique_id: t for t in sch.tasks}
    tm = res.timing(188)
    assert tm.late_finish == res.project_finish
    assert tm.free_float == tm.total_float
    assert tm.total_float > 0 and not tm.is_critical
    for uid in (188, 189, 181, 178, 179, 180):
        stored = by[uid].stored_total_float_minutes
        assert stored is not None and abs(res.timing(uid).total_float - stored) <= 1, uid
    # the 24-hour snapshot's three: 99 %-complete activities whose only successor is finished;
    # each late finish is the project finish (stored 11-19 01:00), two on the crew's own instant
    res24 = _load("fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz")[1]
    for uid in (267, 302, 385):
        assert res24.timing(uid).late_finish == res24.project_finish, uid
    for uid in (302, 385):
        assert res24.timing(uid).late_finish_wall == dt.datetime(2026, 11, 19, 1, 0), uid
