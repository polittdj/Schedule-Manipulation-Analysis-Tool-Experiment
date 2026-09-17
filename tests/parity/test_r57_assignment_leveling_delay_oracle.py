"""MS Project's own dates as the oracle for a BOOKING's leveling delay (ADR-0502, R-57).

The audit row said the delay was "not read — only the task's is honoured (ADR-0474)", named
Hard_File UID 398 and updated2 UID 188, and set the oracle as UID 398's stored finish
2026-08-27 11:59. Two things about that row were measured before anything was changed.

**The population is wider than the row.** Six of the fifteen goldens carry an assignment-level
``LevelingDelay`` — 24 delayed bookings on 17 tasks, including every ``Large_Test_File``
snapshot, not the two Hard_File activities the row lists.

**The rule is ADR-0474 / ADR-0501's type rule, not a new one.** A leg with its OWN span
(``FIXED_UNITS``, ratio < 1) is PUSHED by its delay; a leg that SPANS THE TASK (ratio 1.0)
ABSORBS it — the delay lies inside the span it shares with the task, and on 16 of the 18 such
bookings the file's own ``Assignment/Finish`` IS its ``Task/Finish`` (the other two are
co-bookings that finish earlier either way). The split is exactly 6 push / 18 absorb and it
falls on the type: every pushed booking is Hard_File's, every absorbed one Large_Test_File's.
Pushing an absorbing leg — the obvious reading of the row — was tried first and cost
Large_Test_File 93 of its 1,666 finishes-within-a-day and UIDs 5266 / 5267 / 5270 their EXACT
finishes. That regression is the reason the type guard exists.

**The row's oracle was reached on ``Hard_File_updated`` first, not on ``Hard_File``, and the
difference was not this rule's.** On updated, UID 398 lands on 2026-08-27 11:59 exactly. On the
base snapshot its predecessor's predecessor, UID 381, finished a full day early (2026-08-20
11:59 against the stored 08-21 11:59); 381 -> 396 -> 398 carried that forward, and 398 then
landed early by exactly the 240 working minutes 396 was early by. ADR-0474's task-delay
arithmetic was EXACT on both snapshots when fed the stored predecessor finish, so the residual
was upstream of leveling entirely — registered as R-66, not hidden in this one. ADR-0505 (R-64)
closed R-66 with it: 381 is a project-calendar MILESTONE after a crew-calendar activity (UID
321, finishing Friday 08-21 11:59 on its crew's calendar); the integer project axis rendered
that minute a day earlier, and the milestone now carries its predecessor's instant. Both
snapshots reach the row's oracle, to the minute, with 381 / 396 / 398's stored slacks exact.

Red first (pre-ADR-0502): ``Assignment`` refuses ``leveling_delay_minutes``, ``CPMResult``
carries no ``assignment_leveling_driven``, Hard_File_updated UID 398 reads 2026-08-26 17:00
(0.79 d early) and updated2 UID 188 reads 2026-08-21 14:05 (15 h 45 m early).
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
    _wall_minutes_between,
    compute_cpm,
    offset_to_datetime,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import TaskType

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
NS = "{http://schemas.microsoft.com/project}"

HARD_FILE = "fuse_hardfile/Hard_File.mspdi.xml.gz"
UPDATED = "fuse_hardfile/Hard_File_updated.mspdi.xml.gz"
UPDATED2 = "fuse_hardfile/Hard_File_updated2.mspdi.xml.gz"
LTF = "fuse_ltf/Large_Test_File.mspdi.xml.gz"

#: every golden the delay census sweeps — the POPULATION the claims below are about
CENSUS = [
    HARD_FILE,
    UPDATED,
    UPDATED2,
    "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
    LTF,
    "fuse_ltf/Large_Test_File2.mspdi.xml.gz",
    "project2_5/Project2.mspdi.xml",
    "project2_5/Project5.mspdi.xml",
    "ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz",
    "ssi_uid152/Large_Test_File.mspdi.xml.gz",
]


def _text(rel: str) -> str:
    path = GOLDEN / rel
    raw = path.read_bytes()
    return gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")


@cache
def _load(rel: str) -> tuple[Schedule, CPMResult]:
    sch = parse_mspdi_text(_text(rel))
    return sch, compute_cpm(sch)


def _finish(rel: str, uid: int) -> dt.datetime:
    sch, res = _load(rel)
    tm = res.timing(uid)
    return tm.early_finish_wall or offset_to_datetime(
        sch.project_start, tm.early_finish, sch.calendar
    )


def _stored_finish(rel: str, uid: int) -> dt.datetime:
    sch, _ = _load(rel)
    stored = next(t for t in sch.tasks if t.unique_id == uid).finish
    assert stored is not None, f"{rel} UID {uid} carries no stored finish"
    return stored


# --- the row's own oracle -----------------------------------------------------------------------


def test_uid_398_lands_on_ms_projects_own_finish_once_the_bookings_delay_is_read() -> None:
    """R-57's oracle. UID 398's Technology Lead is booked 8 h on the project pattern, SPLIT
    (ADR-0491, already honoured) and leveled off 239 minutes (not). Reading the delay moves the
    task from 2026-08-26 17:00 to MS Project's own 2026-08-27 11:59, and the disclosure names
    the booking's delay rather than a date or an actual."""
    assert _finish(UPDATED, 398) == dt.datetime(2026, 8, 27, 11, 59)
    assert _finish(UPDATED, 398) == _stored_finish(UPDATED, 398)
    _, res = _load(UPDATED)
    assert 398 in res.assignment_leveling_driven
    # and its two feeders are exact, so nothing upstream is paying for this
    assert _finish(UPDATED, 396) == _stored_finish(UPDATED, 396)
    assert _finish(UPDATED, 381) == _stored_finish(UPDATED, 381)


def test_on_the_base_snapshot_uid_381_and_its_chain_are_exact_since_the_carried_instant() -> None:
    """R-66, closed by ADR-0505 (R-64). Until then the same activity on the base snapshot was NOT
    exact, and the gap was not this rule's: milestone 381 read a day early (2026-08-20 11:59
    against the stored 08-21 11:59), 396 inherited it and 398's finish was early by exactly the
    240 working minutes 396's start was. The milestone now carries the Friday 11:59 its crew
    predecessor 321 finished at, and the chain's three displacements are zero — computed, not
    hand-copied, so a regression of the carried instant fails here by name too."""
    sch, res = _load(HARD_FILE)
    tod0 = sch.project_start.hour * 60 + sch.project_start.minute
    assert _finish(HARD_FILE, 321) == dt.datetime(2026, 8, 21, 11, 59)
    assert res.timing(381).early_finish_wall == dt.datetime(2026, 8, 21, 11, 59)
    assert _finish(HARD_FILE, 381) == _stored_finish(HARD_FILE, 381)
    for uid in (381, 396, 398):
        gap = _wall_minutes_between(
            _finish(HARD_FILE, uid), _stored_finish(HARD_FILE, uid), sch.calendar, tod0
        )
        assert gap == 0, (uid, gap)
        assert res.timing(uid).total_float == sch.task_by_id(uid).stored_total_float_minutes


def test_uid_188s_delayed_crew_moves_from_fifteen_hours_early_to_inside_two_minutes() -> None:
    """The row's second activity. Its Content Developer is booked on a 24-hour calendar and
    leveled off 960 minutes; the engine finished the task with an undelayed crew at 14:05.
    Reading the delay puts it on the delayed crew, 66 seconds under MS Project's instant — the
    engine floors to whole minutes and this booking's work is 348.x of them (R-65's class)."""
    got, stored = _finish(UPDATED2, 188), _stored_finish(UPDATED2, 188)
    assert stored == dt.datetime(2026, 8, 22, 5, 49, 6)
    assert got == dt.datetime(2026, 8, 22, 5, 48)
    assert 0 < (stored - got).total_seconds() <= 120
    _, res = _load(UPDATED2)
    assert 188 in res.assignment_leveling_driven


def test_a_delay_that_does_not_place_the_finish_is_neither_paid_for_nor_disclosed() -> None:
    """updated2's UID 398 carries a 420-minute delay on a crew that still finishes before its
    co-crew. The task was exact before this rule and must stay exact, and the disclosure must
    not claim a delay decided it."""
    assert (
        _finish(UPDATED2, 398) == _stored_finish(UPDATED2, 398) == dt.datetime(2026, 8, 24, 17, 0)
    )
    _, res = _load(UPDATED2)
    assert 398 not in res.assignment_leveling_driven


def test_the_backward_pass_retreats_through_the_delay_and_three_stored_slacks_depend_on_it() -> (
    None
):
    """The mirror half, and it is NOT cosmetic. A delayed leg's latest start must retreat through
    its own delay, or the task's late start lands late and its predecessors inherit it. Dropping
    the retreat survived every other check in this module — it costs Hard_File_updated three of
    its 99 exactly-reproduced stored slacks, on the very chain that feeds UID 398: 321, 381 and
    396 each read 17,640 / 17,640 / 18,660 without it against MS Project's 17,521 / 17,521 /
    18,480. UID 379 moves too (17,700 -> 17,521 against a stored 17,581): closer, not exact,
    and named rather than counted."""
    sch, res = _load(UPDATED)
    stored = {t.unique_id: t.stored_total_float_minutes for t in sch.tasks}
    for uid, tf in ((321, 17521), (381, 17521), (396, 18480)):
        assert res.timing(uid).total_float == stored[uid] == tf, uid
    assert res.timing(379).total_float == 17521 and stored[379] == 17581


# --- the absorb half: the rule that keeps Large_Test_File where it was ---------------------------


def test_task_spanning_bookings_absorb_their_delay_and_large_test_file_does_not_move() -> None:
    """Every Large_Test_File delayed booking is FIXED_WORK at ratio 1.0. Pushing them cost 93
    finishes-within-a-day; absorbing them leaves all three witnesses on MS Project's instant and
    claims nothing on the disclosure."""
    for uid, stored in (
        (5266, dt.datetime(2025, 4, 29, 14, 0)),
        (5267, dt.datetime(2025, 5, 13, 14, 0)),
        (5270, dt.datetime(2025, 8, 8, 8, 30)),
    ):
        assert _finish(LTF, uid) == stored == _stored_finish(LTF, uid), uid
    _, res = _load(LTF)
    assert res.assignment_leveling_driven == ()


# --- the population, so a claim about it can never quietly become a claim about the world --------


def test_the_delay_census_is_pinned_by_file_and_by_type() -> None:
    """ADR-0500's lesson: a residual must name the population it was measured against. This is
    that population — every delayed booking in every golden, split on the ratio that decides
    whether its delay is pushed or absorbed. Every booking must PAIR with a model assignment;
    an instrument that silently drops one would report a confident, wrong census."""
    push = absorb = total = 0
    per_file: dict[str, int] = {}
    for rel in CENSUS:
        sch, _ = _load(rel)
        by = {t.unique_id: t for t in sch.tasks}
        for a_el in ET.fromstring(_text(rel)).iter(f"{NS}Assignment"):
            raw = a_el.findtext(f"{NS}LevelingDelay")
            if not raw or int(raw) == 0:
                continue
            uid = int(a_el.findtext(f"{NS}TaskUID") or "0")
            rid = int(a_el.findtext(f"{NS}ResourceUID") or "-1")
            task = by.get(uid)
            assert task is not None, f"{rel}: delayed booking on unknown task {uid}"
            booking = next((x for x in task.resource_assignments if x.resource_id == rid), None)
            assert booking is not None, (
                f"{rel}: delayed booking {uid}/{rid} never reached the model"
            )
            assert booking.leveling_delay_minutes == max(0, round(int(raw) / 10)), (rel, uid, rid)
            total += 1
            per_file[rel] = per_file.get(rel, 0) + 1
            wu = (booking.work_minutes / booking.units) if booking.units else 0.0
            ratio = (
                min(1.0, wu / task.duration_minutes)
                if task.task_type is TaskType.FIXED_UNITS
                else 1.0
            )
            if ratio < 1.0:
                push += 1
            else:
                absorb += 1
    assert total == 24 and push == 6 and absorb == 18, (total, push, absorb)
    assert per_file == {
        HARD_FILE: 2,
        UPDATED: 2,
        UPDATED2: 2,
        LTF: 5,
        "fuse_ltf/Large_Test_File2.mspdi.xml.gz": 8,
        "ssi_uid152_leveled/Large_Test_File_Leveled.mspdi.xml.gz": 5,
    }, per_file
    # every pushed booking is Hard_File's, every absorbed one Large_Test_File's
    assert sum(per_file[r] for r in (HARD_FILE, UPDATED, UPDATED2)) == push


def test_the_delay_is_read_to_the_nearest_minute_not_truncated() -> None:
    """MS Project stores the delay in TENTHS of a minute. Against its own Assignment/Start on
    the 24 delayed bookings, rounding reproduces 17 and truncating 14, and rounding is never
    the worse of the two on any one of them — so the reader rounds, unlike ADR-0474's
    task-level reader, which truncates (registered, not changed here)."""
    sch, _ = _load("fuse_ltf/Large_Test_File2.mspdi.xml.gz")
    task = next(t for t in sch.tasks if t.unique_id == 5270)
    booking = next(a for a in task.resource_assignments if a.resource_id == 77)
    assert booking.leveling_delay_minutes == 5  # stored 52 tenths = 5.2 minutes
