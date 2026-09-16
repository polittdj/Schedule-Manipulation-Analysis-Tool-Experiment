"""R-61 — a FIXED_DURATION leg on an off-pattern crew: the census, the corrected premise, and
the refutation of "the window is the rule" (ADR-0500).

The roadmap row (report §3, R-61) said a FIXED_DURATION booking on an off-pattern crew spans
the DURATION in crew minutes (ADR-0474's type rule) "where MS Project keeps the task's window",
named ``Hard_File_updated3`` UID 210 as the witness, and set the first executable step: census
every such task across the goldens, recorded booking window vs the computed leg. This module is
that census, executed and pinned, plus the three things the census measured:

* **The population is ONE task.** Across all 15 MSPDI goldens there are exactly five
  (golden, task) pairs where an active FIXED_DURATION task carries an off-pattern WORK leg, and
  all five are UID 210 in five snapshots of the same file. There is no unstarted witness, and
  none without a project-calendar co-booking — so no golden can discriminate the rule.
* **The row's premise is mis-stated.** UID 210 is not "masked by the completed-window pin
  (ADR-0476) and by the material leg (ADR-0487)". Its finish-placing PRIMARY leg is the
  ``Standard``-calendar WORK leg of the Logistics Apprentice booking, spanning the same 1,920
  minutes on the PROJECT calendar and landing on the stored finish exactly. The 24-hour Content
  Developer leg finishes four days earlier and has never placed the task.
* **The proposed rule is refuted where it can be tested.** MS Project has no separate scheduler
  for FIXED_DURATION, so "a leg spans the recorded window" is a claim about ratio-1.0 WORK legs
  generally. Generalized over the corpus it moves 315 activities AWAY from their files' own
  stored finishes and NOT ONE toward (ADR-0500's census). The mechanism is already understood:
  a split booking's recorded window spans the leveling gaps ADR-0491 honours separately, so
  reading the window overrides them — the witness pinned below is Large_Test_File UID 5231,
  whose recorded window is 26,880 crew minutes SHORTER than the occupancy the engine correctly
  places.

The oracle for the placement pins is MS Project's own stored ``Finish`` — independent of the
engine that is judged. The shape pin on the type rule is a TRIPWIRE, not evidence: it exists so
that implementing the refuted rule cannot happen silently, and it says nothing about MS Project.
Every pin here is proved able to fail by the ADR's mutation battery.
"""

from __future__ import annotations

import datetime as dt
import gzip
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine import cpm as C
from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.resource import ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import TaskType

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

UPDATED3 = "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz"
LTF = "fuse_ltf/Large_Test_File.mspdi.xml.gz"

#: Every (golden, UniqueID) pair in the corpus where an ACTIVE FIXED_DURATION task carries a
#: WORK booking whose leg calendar differs materially from the project calendar — the whole
#: population R-61's census asked for. Five rows, one task, one file (ADR-0500).
POPULATION = (
    ("fuse_hardfile/Hard_File_updated2.mspdi.xml.gz", 210),
    ("fuse_hardfile/Hard_File_updated3.mspdi.xml.gz", 210),
    ("fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz", 210),
    ("ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz", 210),
    ("ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz", 210),
)

#: UID 210's stored finish — MS Project's own, the oracle the placement pins are judged against.
UID210_STORED_FINISH = dt.datetime(2026, 8, 25, 17, 0)


@cache
def _load(rel: str) -> Schedule:
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
    return parse_mspdi_text(text)


def _ctx(sch: Schedule) -> C._ShapeContext:
    return C._ShapeContext(
        sch, sch.calendar.working_pattern_key(), {c.uid: c for c in sch.calendars}, {}
    )


def _census(rel: str) -> list[tuple[int, str, int, int]]:
    """``(uid, crew calendar, engine leg span, recorded window on that calendar)`` for every
    off-pattern crew leg of an active FIXED_DURATION task in one golden.

    Membership and the span come from the ENGINE'S OWN :func:`_task_shape` — never from a
    re-reading of the rule in this module. A parallel implementation here would pass while the
    engine's own leg resolution was broken (proved: mutating ``_task_shape`` left an
    earlier, re-implemented version of this census green — QC-2's "verify what actually
    resolved at runtime"). The booking is matched to its leg by the calendar OBJECT the
    schedule registered for its resource.
    """
    sch = _load(rel)
    ctx = _ctx(sch)
    out: list[tuple[int, str, int, int]] = []
    for t in sch.tasks:
        if t.is_summary or not t.is_active or t.duration_is_elapsed:
            continue
        if t.task_type is not TaskType.FIXED_DURATION or t.duration_minutes <= 0:
            continue
        shape = C._task_shape(t, ctx)
        if shape is None or shape.elapsed:
            continue
        for leg in shape.legs:
            if not leg.off_pattern or leg.recorded:
                continue  # a recorded span is ADR-0487's material leg, not a crew leg
            window = -1
            for a in t.resource_assignments:
                res = sch.resources_by_id.get(a.resource_id)
                if res is None or res.type is not ResourceType.WORK or a.work_minutes <= 0:
                    continue
                rcal = ctx.by_uid.get(res.calendar_uid) if res.calendar_uid is not None else None
                if rcal is not leg.calendar or a.start is None or a.finish is None:
                    continue
                window = C._recorded_span(leg.calendar, a.start, a.finish)
            out.append(
                (t.unique_id, leg.calendar.name, round(leg.ratio * t.duration_minutes), window)
            )
    return out


def _all_goldens() -> list[str]:
    return sorted(str(p.relative_to(GOLDEN)) for p in GOLDEN.rglob("*.mspdi.xml*"))


# --- the census the row asked for -----------------------------------------------------------


def test_the_census_population_is_one_task_in_five_snapshots_of_one_file() -> None:
    """R-61's first executable step, run over every golden. If this ever returns a sixth row the
    row becomes discriminable again and ADR-0500's close must be re-read."""
    assert len(_all_goldens()) == 15, "the corpus moved; re-derive the census before trusting it"
    found = tuple((rel, uid) for rel in _all_goldens() for uid, _cal, _dur, _win in _census(rel))
    assert found == POPULATION


def test_on_the_only_witness_the_window_and_the_leg_disagree_as_the_row_says() -> None:
    """The row's arithmetic is right: the leg spans the 4-day duration in the 24-hour crew's
    minutes (1,920 = 1.33 days there) where the file records the booking over 7,740 of them."""
    rows = _census(UPDATED3)
    assert rows == [(210, "Content Developer", 1920, 7740)]
    sch = _load(UPDATED3)
    t = next(x for x in sch.tasks if x.unique_id == 210)
    crew = next(
        a
        for a in t.resource_assignments
        if sch.resources_by_id[a.resource_id].name == "Content Developer"
    )
    # the booking's window IS the task's own window — MS Project writes it onto every assignment
    assert (crew.start, crew.finish) == (t.start, t.finish)
    assert (t.start, t.finish) == (dt.datetime(2026, 8, 20, 8, 0), UID210_STORED_FINISH)


# --- the corrected premise ------------------------------------------------------------------


def test_the_off_pattern_crew_leg_has_never_placed_uid_210s_finish() -> None:
    """The row says UID 210 is masked by ADR-0476's completed-window pin and ADR-0487's material
    leg. Measured on the live plan builder, it is masked by NEITHER: the finish-placing PRIMARY
    leg is the ``Standard``-calendar WORK leg, and the crew leg finishes four days earlier."""
    sch = _load(UPDATED3)
    t = next(x for x in sch.tasks if x.unique_id == 210)
    plan = C._execution_plans(sch, [t], {210: t.duration_minutes})[210]
    ps = sch.project_start
    tod0 = ps.hour * 60 + ps.minute
    start = t.start
    assert start is not None
    finish_of = {
        leg.calendar.name: C._leg_finish(C._snap_to_working(start, leg.calendar, tod0), leg, tod0)
        for leg in plan.legs
    }
    # the PRIMARY leg is first, and it is not the crew's
    assert plan.legs[0].calendar.name == "Standard"
    assert plan.legs[0].span == 1920
    assert finish_of["Standard"] == UID210_STORED_FINISH
    assert finish_of["Content Developer"] == dt.datetime(2026, 8, 21, 16, 0)


@pytest.mark.parametrize("rel", [rel for rel, _uid in POPULATION])
def test_uid_210_lands_on_ms_projects_stored_finish_in_every_snapshot(rel: str) -> None:
    """The oracle is the file's own stored ``Finish``. The row's symptom has no observable
    consequence anywhere in the corpus: the task is exact on all five."""
    sch = _load(rel)
    res = compute_cpm(sch)
    t = next(x for x in sch.tasks if x.unique_id == 210)
    tm = res.timing(210)
    ef = tm.early_finish_wall or offset_to_datetime(
        sch.project_start, tm.early_finish, sch.calendar
    )
    assert t.finish == UID210_STORED_FINISH
    assert ef == UID210_STORED_FINISH


# --- the refutation -------------------------------------------------------------------------


def test_reading_a_work_bookings_window_would_undo_the_leveling_split() -> None:
    """Large_Test_File UID 5231 is why "the leg spans the recorded window" cannot be the rule:
    its recorded window is 26,880 crew minutes SHORTER than the span plus the gap ADR-0491
    measured, so reading the window would collapse a leveling split the engine gets right.
    Generalized over the corpus the rule moves 315 activities away from their stored finishes
    and none toward (ADR-0500)."""
    sch = _load(LTF)
    ctx = _ctx(sch)
    t = next(x for x in sch.tasks if x.unique_id == 5231)
    a = next(
        x
        for x in t.resource_assignments
        if (r := sch.resources_by_id.get(x.resource_id)) is not None
        and r.type is ResourceType.WORK
        and x.work_minutes > 0
        and len(x.work_pieces) >= 2
    )
    shape = C._task_shape(t, ctx)
    assert shape is not None
    off = [lg for lg in shape.legs if lg.off_pattern and not lg.recorded]
    assert off and all(lg.calendar is off[0].calendar for lg in off)
    leg_cal = off[0].calendar
    others = [
        w
        for x in t.resource_assignments
        if x is not a
        and (r := sch.resources_by_id.get(x.resource_id)) is not None
        and r.type is ResourceType.WORK
        and x.work_minutes > 0
        for w in C._worked_windows(x)
    ]
    span = t.duration_minutes  # the type rule: FIXED_WORK spans ratio 1.0
    gaps = sum(
        gap for share, gap in C._split_gaps(a, leg_cal, others) if 0 < round(share * span) < span
    )
    window = C._recorded_span(leg_cal, a.start, a.finish)
    assert (span, gaps, span + gaps) == (89760, 26880, 116640)
    assert window == 89760
    assert window - (span + gaps) == -26880


# --- the tripwire (a shape pin, not an oracle) ----------------------------------------------


def test_the_type_rule_still_governs_a_fixed_duration_leg() -> None:
    """ADR-0474's type rule, pinned at the one place R-61 proposed to change it. This is a
    TRIPWIRE and not evidence: it asserts the code's shape so that adopting the refuted rule
    cannot happen silently, and it says nothing about MS Project. The oracles above do that."""
    sch = _load(UPDATED3)
    ctx = _ctx(sch)
    t = next(x for x in sch.tasks if x.unique_id == 210)
    shape = C._task_shape(t, ctx)
    assert shape is not None
    crew = [lg for lg in shape.legs if lg.calendar.name == "Content Developer"]
    assert len(crew) == 1
    assert crew[0].ratio == 1.0, "a FIXED_DURATION leg spans the DURATION, never the window"
    assert crew[0].off_pattern is True
    assert crew[0].recorded is False
