"""MS Project's own dates as the oracle for a task calendar meeting a crew calendar (ADR-0503,
R-58).

The roadmap row (report §3, R-58) read: *a task calendar that is not 24-hour, intersected with
a crew calendar, is approximated by the task calendar (Hard_File UID 14 on ``Standard+Sat.``
with the 16-hour crew)*. Two things about that row were measured before anything changed.

**The row's witness is mis-stated.** Hard_File UID 14 carries calendar 10, ``24 Hours`` — the
ONE intersection ADR-0474 already modelled exactly (a 24-hour task calendar yields the crew's
calendar), which is why ADR-0491 found its stored span reproduced to the minute. The task on
``Standard+Sat.`` (calendar 12: 07:00-12:00, 12:30-19:00, 19:30-23:30, Monday to Saturday) is
**UID 94**, an 8-hour activity booked on the same 16-hour crew (06:00-12:00 + 13:00-23:00,
Monday to Friday). The row conflated the two.

**The population is one task.** Across the 15 MSPDI goldens, 301 tasks carry a task calendar
that is neither the project pattern nor 24-hour together with a WORK booking; on 300 of them the
crew's calendar restricts nothing the task calendar works, so intersecting changes nothing and
the engine keeps the task calendar object itself. UID 94 is the one task whose crew calendar
cuts into its own — in five snapshots, three of them recorded-complete (ADR-0476's pin, which
cannot adjudicate a scheduling rule). Over the repository's 29 ``.mpp`` files the population is
the same task in one more save (``Hard_File_updated_with_logic_reestablished``).

**The oracle is met.** On the intersection UID 94 resumes at the crew's 13:00 rather than the
task calendar's 12:30 and finishes at MS Project's 17:00 on both unstarted snapshots; on
``updated`` its Start, Finish, LateStart, LateFinish and TotalSlack are all five stored values —
the late finish on the Friday 23:00 the crew works to, where the task calendar alone wrote the
Saturday 23:30 the crew never works. The slack is measured on the TASK calendar (ADR-0474's
axis, unchanged). Its successor UID 157 lands exact on both snapshots with it. Every other
golden is BYTE-IDENTICAL.

Red first (pristine ADR-0502 tree): UID 94 reads 16:30 on both unstarted snapshots; on
``updated`` its late finish reads Saturday 2026-08-15 23:30 and its slack 3,180 against the
stored 2,190; ``_calendar_intersection`` does not exist.
"""

from __future__ import annotations

import datetime as dt
import gzip
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine import cpm as C
from schedule_forensics.engine.cpm import (
    CPMResult,
    _offset_to_wall,
    _snap_back_to_working,
    _wall_minutes_between,
    compute_cpm,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.resource import ResourceType
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
NS = "{http://schemas.microsoft.com/project}"

HARD_FILE = "fuse_hardfile/Hard_File.mspdi.xml.gz"
UPDATED = "fuse_hardfile/Hard_File_updated.mspdi.xml.gz"

#: every Hard_File snapshot in the corpus, and the calendar its 16-hour crew (resource 1) sits on
SNAPSHOTS = (
    HARD_FILE,
    UPDATED,
    "fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
    "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
    "fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz",
    "ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz",
    "ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz",
)
#: the snapshots where the crew is on the 16-hour calendar and UID 94's leg is a DERIVED
#: intersection; on the two ``24h`` snapshots the crew is round-the-clock and restricts nothing
DERIVED = (*SNAPSHOTS[:4], SNAPSHOTS[5])


def _text(rel: str) -> str:
    path = GOLDEN / rel
    raw = path.read_bytes()
    return gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")


@cache
def _load(rel: str) -> tuple[Schedule, CPMResult]:
    sch = parse_mspdi_text(_text(rel))
    return sch, compute_cpm(sch)


@cache
def _stored_late(rel: str) -> dict[int, tuple[dt.datetime | None, dt.datetime | None]]:
    """MS Project's own LateStart / LateFinish per UID (the model does not carry them)."""
    out: dict[int, tuple[dt.datetime | None, dt.datetime | None]] = {}
    for el in ET.fromstring(_text(rel)).iter(f"{NS}Task"):
        uid = el.findtext(f"{NS}UID")
        if not uid:
            continue
        ls, lf = el.findtext(f"{NS}LateStart"), el.findtext(f"{NS}LateFinish")
        out[int(uid)] = (
            dt.datetime.fromisoformat(ls) if ls else None,
            dt.datetime.fromisoformat(lf) if lf else None,
        )
    return out


def _walls(rel: str, uid: int) -> tuple[dt.datetime, dt.datetime, dt.datetime, dt.datetime]:
    sch, res = _load(rel)
    tm = res.timing(uid)
    ps, cal = sch.project_start, sch.calendar
    return (
        tm.early_start_wall or _offset_to_wall(ps, tm.early_start, cal, role="start"),
        tm.early_finish_wall or _offset_to_wall(ps, tm.early_finish, cal, role="finish"),
        tm.late_start_wall or _offset_to_wall(ps, tm.late_start, cal, role="start"),
        tm.late_finish_wall or _offset_to_wall(ps, tm.late_finish, cal, role="finish"),
    )


def _leg_calendar(rel: str, uid: int) -> C.Calendar:
    sch, _ = _load(rel)
    cal = C.execution_calendar_of(sch, sch.task_by_id(uid))
    assert cal is not None, (rel, uid)
    return cal


# --- the row's witness, corrected ---------------------------------------------------------------


@pytest.mark.parametrize("rel", SNAPSHOTS)
def test_uid_14_is_on_the_24_hour_calendar_and_its_leg_is_the_crews_own(rel: str) -> None:
    """The row named UID 14 "on ``Standard+Sat.``". It is on ``24 Hours`` in every snapshot,
    and its leg is the crew's registered calendar OBJECT — the intersection ADR-0474 already
    modelled exactly, and the reason ADR-0491 found its stored span reproduced."""
    sch, res = _load(rel)
    t = sch.task_by_id(14)
    by_uid = {c.uid: c for c in sch.calendars}
    assert t.calendar_uid == 10 and by_uid[10].name == "24 Hours"
    assert by_uid[10].working_minutes_per_day == 1440
    crew = sch.resources_by_id[t.resource_assignments[0].resource_id]
    assert crew.calendar_uid == 3
    assert _leg_calendar(rel, 14) is by_uid[3]
    if rel == HARD_FILE:
        assert res.timing(14).early_start_wall == dt.datetime(2026, 10, 26, 20, 0)
        assert res.timing(14).early_finish_wall == dt.datetime(2026, 10, 29, 11, 0)


def test_uid_94_carries_standard_plus_sat_and_the_16_hour_crew_and_runs_on_their_intersection() -> (
    None
):
    """The real witness: an 8-hour FIXED_UNITS activity on calendar 12 with one booking on the
    crew whose calendar 3 is the 16-hour day. Its leg is a DERIVED calendar — the common
    weekdays (the crew's Monday to Friday), the common blocks (07:00-12:00, 13:00-19:00,
    19:30-23:00 — 870 minutes), the crew's holidays — that never enters the registry."""
    sch, _ = _load(HARD_FILE)
    t = sch.task_by_id(94)
    by_uid = {c.uid: c for c in sch.calendars}
    assert t.calendar_uid == 12 and by_uid[12].name == "Standard+Sat."
    assert by_uid[12].work_weekdays == (0, 1, 2, 3, 4, 5)
    assert by_uid[12].day_segments == ((420, 720), (750, 1140), (1170, 1410))
    assert by_uid[12].working_minutes_per_day == 930
    assert t.duration_minutes == 480 and len(t.resource_assignments) == 1
    crew = sch.resources_by_id[t.resource_assignments[0].resource_id]
    assert crew.type is ResourceType.WORK and crew.calendar_uid == 3
    assert by_uid[3].day_segments == ((360, 720), (780, 1380))
    assert by_uid[3].work_weekdays == (0, 1, 2, 3, 4)
    leg = _leg_calendar(HARD_FILE, 94)
    assert leg.uid == -2 and leg.name == "Standard+Sat. ∩ Customer Service Team"
    assert leg.work_weekdays == (0, 1, 2, 3, 4)
    assert leg.day_segments == ((420, 720), (780, 1140), (1170, 1380))
    assert leg.working_minutes_per_day == 870
    assert leg.holidays == by_uid[3].holidays  # the crew's — the task calendar has none
    assert all(c is not leg for c in sch.calendars)
    assert [c.uid for c in sch.calendars] == [1, 3, 6, 8, 10, 12]


# --- the oracle -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "day"), [(HARD_FILE, dt.date(2026, 7, 23)), (UPDATED, dt.date(2026, 8, 12))]
)
def test_uid_94_finishes_at_ms_projects_17_00_on_both_unstarted_snapshots(
    rel: str, day: dt.date
) -> None:
    """The task calendar alone resumes at 12:30 and reads 16:30; the common afternoon begins at
    the crew's 13:00 and the stored finish is 17:00 — on the base snapshot and on ``updated``."""
    sch, _ = _load(rel)
    t = sch.task_by_id(94)
    assert not C.is_recorded_complete(t) and t.percent_complete == 0
    es, ef, _ls, _lf = _walls(rel, 94)
    assert (t.start, t.finish) == (
        dt.datetime.combine(day, dt.time(8, 0)),
        dt.datetime.combine(day, dt.time(17, 0)),
    )
    assert es == t.start
    assert ef == t.finish


def test_on_updated_uid_94_reproduces_all_five_stored_values() -> None:
    """Start, Finish, LateStart, LateFinish and TotalSlack, MS Project's own. The late finish
    is the Friday 23:00 the crew works to: the successor's late start less its elapsed leveling
    delay lands on Sunday 00:00, and snapped back on the task calendar ALONE that is Saturday
    23:30 (the pristine reading, a day the crew never works) — on the intersection it is the
    stored Friday 23:00. The slack is the FINISH slack measured on the TASK calendar (2,190;
    the start slack there is 2,220), ADR-0474's axis unchanged."""
    sch, res = _load(UPDATED)
    t = sch.task_by_id(94)
    es, ef, ls, lf = _walls(UPDATED, 94)
    stored_ls, stored_lf = _stored_late(UPDATED)[94]
    assert (
        (es, ef)
        == (t.start, t.finish)
        == (dt.datetime(2026, 8, 12, 8, 0), dt.datetime(2026, 8, 12, 17, 0))
    )
    assert (
        (ls, lf)
        == (stored_ls, stored_lf)
        == (dt.datetime(2026, 8, 14, 14, 30), dt.datetime(2026, 8, 14, 23, 0))
    )
    assert res.timing(94).total_float == t.stored_total_float_minutes == 2190
    # the mechanism, computed: the successor's need, on each calendar
    ps = sch.project_start
    tod0 = ps.hour * 60 + ps.minute
    succ = sch.task_by_id(157)
    need = _stored_late(UPDATED)[157][0]
    assert need is not None and succ.leveling_delay_minutes == 6660
    need -= dt.timedelta(minutes=succ.leveling_delay_minutes)
    assert need == dt.datetime(2026, 8, 16, 0, 0)
    by_uid = {c.uid: c for c in sch.calendars}
    assert _snap_back_to_working(need, by_uid[12], tod0) == dt.datetime(2026, 8, 15, 23, 30)
    assert _snap_back_to_working(need, _leg_calendar(UPDATED, 94), tod0) == stored_lf
    # and the axis: the stored slack is the smaller of the two slacks on the TASK calendar
    assert _wall_minutes_between(es, ls, by_uid[12], tod0) == 2220
    assert _wall_minutes_between(ef, lf, by_uid[12], tod0) == 2190


@pytest.mark.parametrize("rel", [HARD_FILE, UPDATED])
def test_uid_157_downstream_lands_on_ms_projects_instants_with_it(rel: str) -> None:
    """The successor started 16:30 and finished 07:30 the next morning where MS Project stores
    17:00 and 08:00; it follows 94 onto the stored instants on both snapshots, and on
    ``updated`` its stored slack (1,440) is reproduced too."""
    sch, res = _load(rel)
    t = sch.task_by_id(157)
    es, ef, _ls, _lf = _walls(rel, 157)
    assert (es, ef) == (t.start, t.finish)
    if rel == UPDATED:
        assert res.timing(157).total_float == t.stored_total_float_minutes == 1440


def test_on_the_base_snapshot_uid_94s_float_is_exact_once_147s_saturday_is_carried() -> None:
    """UID 94's slack on the base snapshot read 6,510 against the stored 6,360 and the 150
    minutes were NOT this rule's (ADR-0503 named them R-67's). 157's late finish is read from
    milestone 147's late start: MS Project keeps that milestone's late start at Saturday
    2026-08-01 13:00 — UID 178's late start less its 72 elapsed hours of leveling delay, an
    instant inside the weekend — and snapped back on the crew's 16-hour calendar it IS 157's
    stored Friday 23:00. The engine's integer axis has no Saturday instant; until R-67
    (ADR-0510) 147 read Monday 08:00 for the crew predecessor, 157's late finish followed it,
    and 94's two-hour-later late window was 150 minutes of ``Standard+Sat.``. The milestone now
    CARRIES the instant and the chain lands on every stored value. This test's witness used to
    be the engine's disagreement with MS Project (ADR-0505's doctrine: such a test goes red
    when the engine is fixed); it now pins the agreement, computed, not copied. The one form
    left: the engine's 147 sits at Saturday 12:00 where MS Project writes 13:00 — 178's late
    start written at the END of the crew's morning block where MS Project writes the start of
    its afternoon block, the same working minute on every calendar in the file (registered,
    not chased: the contiguous projection of the 13:00 form would hand every project-calendar
    predecessor the lunch hour as float)."""
    sch, res = _load(HARD_FILE)
    ps = sch.project_start
    tod0 = ps.hour * 60 + ps.minute
    by_uid = {c.uid: c for c in sch.calendars}
    stored = _stored_late(HARD_FILE)
    m = sch.task_by_id(147)
    assert m.is_milestone and not m.resource_assignments
    assert [r.predecessor_id for r in sch.relationships if r.successor_id == 147] == [157]
    assert stored[147][0] == dt.datetime(2026, 8, 1, 13, 0)  # a Saturday
    assert stored[147][0].weekday() == 5
    assert _snap_back_to_working(stored[147][0], by_uid[3], tod0) == stored[157][1]
    assert stored[157][1] == dt.datetime(2026, 7, 31, 23, 0)
    # the carried instant: 178's late start (the block-end form of the stored 13:00) less 72 h
    ls_147 = res.timing(147).late_start_wall
    assert ls_147 == res.timing(147).late_finish_wall == dt.datetime(2026, 8, 1, 12, 0)
    assert res.timing(178).late_start_wall == dt.datetime(2026, 8, 4, 12, 0)
    assert ls_147 == res.timing(178).late_start_wall - dt.timedelta(
        minutes=sch.task_by_id(178).leveling_delay_minutes
    )
    assert _snap_back_to_working(ls_147, by_uid[3], tod0) == stored[157][1]
    # 157 retreats from it onto its stored late window and its stored slack, 2,760
    assert _walls(HARD_FILE, 157)[2:] == (
        dt.datetime(2026, 7, 31, 15, 0),
        dt.datetime(2026, 7, 31, 23, 0),
    )
    assert res.timing(157).total_float == sch.task_by_id(157).stored_total_float_minutes == 2760
    # and 94, one link higher, lands on its stored late window and its stored slack, 6,360
    es, ef, ls, lf = _walls(HARD_FILE, 94)
    assert (es, ef) == (dt.datetime(2026, 7, 23, 8, 0), dt.datetime(2026, 7, 23, 17, 0))
    assert (
        (ls, lf)
        == stored[94]
        == (
            dt.datetime(2026, 7, 30, 22, 0),
            dt.datetime(2026, 7, 31, 15, 0),
        )
    )
    assert res.timing(94).total_float == sch.task_by_id(94).stored_total_float_minutes == 6360
    assert _wall_minutes_between(es, ls, by_uid[12], tod0) == 6360
    assert _wall_minutes_between(ef, lf, by_uid[12], tod0) == 6390


def _derived_legs(rel: str) -> list[tuple[int, str]]:
    """``(uid, crew calendar name)`` for every WORK leg whose calendar is a DERIVED intersection,
    from the ENGINE's own shapes (ADR-0500's lesson: a re-implementation is an oracle for
    itself), plus the count of tasks the intersection was asked about."""
    sch, _ = _load(rel)
    out: list[tuple[int, str]] = []
    for t in sch.tasks:
        shape = C._plan_shapes(sch).get(t.unique_id)
        if shape is None or shape.elapsed or shape.task_calendar is None:
            continue
        for leg in shape.legs:
            if not leg.recorded and leg.calendar.uid == -2:
                out.append((t.unique_id, leg.calendar.name))
    return out


def _asked(rel: str) -> tuple[int, int]:
    """``(non-24-hour, 24-hour)`` counts of the tasks carrying an off-pattern task calendar and
    at least one WORK leg — the tasks the intersection was computed for."""
    sch, _ = _load(rel)
    shapes = C._plan_shapes(sch)
    other = round_the_clock = 0
    for t in sch.tasks:
        shape = shapes.get(t.unique_id)
        if shape is None or shape.elapsed or shape.task_calendar is None:
            continue
        if not any(not leg.recorded for leg in shape.legs):
            continue
        if C._is_24x7(shape.task_calendar):
            round_the_clock += 1
        else:
            other += 1
    return other, round_the_clock


def test_the_population_is_uid_94_in_five_snapshots_and_nothing_else_derives() -> None:
    """Across all 15 goldens, 301 tasks carry an off-pattern task calendar with a WORK booking:
    294 on a calendar that is not 24-hour (293 of them on the Large Test Files' project
    calendar under same-pattern crews, where the crew restricts nothing) and the seven
    snapshots of UID 14 on ``24 Hours``. Exactly five legs are derived intersections, all UID
    94's, all on the 16-hour crew. On the two 24-hour-crew snapshots the crew restricts
    nothing and UID 94 keeps ``Standard+Sat.`` itself. A sixth derived leg is the signal to
    re-read ADR-0503's population."""
    goldens = sorted(str(p.relative_to(GOLDEN)) for p in GOLDEN.rglob("*.mspdi.xml*"))
    assert len(goldens) == 15, "the corpus moved; re-derive the census before trusting it"
    derived = [(rel, uid, name) for rel in goldens for uid, name in _derived_legs(rel)]
    assert derived == [(rel, 94, "Standard+Sat. ∩ Customer Service Team") for rel in DERIVED]
    asked = [_asked(rel) for rel in goldens]
    assert (sum(a for a, _ in asked), sum(b for _, b in asked)) == (294, 7)
    for rel in (SNAPSHOTS[4], SNAPSHOTS[6]):
        sch, _ = _load(rel)
        by_uid = {c.uid: c for c in sch.calendars}
        assert _leg_calendar(rel, 94) is by_uid[12]


@pytest.mark.parametrize("rel", DERIVED[2:])
def test_the_three_completed_snapshots_are_pinned_by_their_record_and_adjudicate_nothing(
    rel: str,
) -> None:
    """UID 94 is 100 % complete with both actuals on updated2, updated3 and the SSI copy: its
    stored Finish is its ``actual_finish`` (ADR-0476), exact by the pin whatever calendar the
    leg runs on. Named so the population is not over-counted as five witnesses (ADR-0501)."""
    sch, _ = _load(rel)
    t = sch.task_by_id(94)
    assert C.is_recorded_complete(t)
    assert _walls(rel, 94)[1] == t.finish == t.actual_finish == dt.datetime(2026, 8, 12, 17, 0)


def _exact(rel: str) -> tuple[int, int]:
    """``(finishes exact, stored slacks exact)`` over the active non-summary activities."""
    sch, res = _load(rel)
    fin = tf = 0
    for t in sch.tasks:
        if t.is_summary or not t.is_active:
            continue
        _es, ef, _ls, _lf = _walls(rel, t.unique_id)
        fin += t.finish is not None and ef == t.finish
        tf += (
            t.stored_total_float_minutes is not None
            and res.timing(t.unique_id).total_float == t.stored_total_float_minutes
        )
    return fin, tf


@pytest.mark.parametrize(
    ("rel", "finish_exact", "tf_exact"), [(HARD_FILE, 40, 39), (UPDATED, 108, 101)]
)
def test_the_two_moved_goldens_gain_exactly_the_witness_chain(
    rel: str, finish_exact: int, tf_exact: int
) -> None:
    """Measured pristine → this tree with the same instrument: Hard_File exact finishes 38 → 40
    (94, 157) and exact stored slacks 37 → 39 (95, 412 — the predecessors' late windows follow
    94's); ``updated`` 106 → 108 and 99 → 101 (94, 157). Twelve activities moved across the two
    snapshots, none away from its stored date; the other thirteen goldens are byte-identical.
    Floors: a regression on either count fails by name."""
    fin, tf = _exact(rel)
    assert fin >= finish_exact, (fin, finish_exact)
    assert tf >= tf_exact, (tf, tf_exact)
