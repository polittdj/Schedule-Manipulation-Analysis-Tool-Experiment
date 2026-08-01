"""Per-task-calendar CPM parity — the "Jacked Up Schedule" oracle files (OR-05).

Two MS Project files were built by the operator's SME with KNOWN scheduling traps and
committed (non-CUI) under ``00_REFERENCE_INTAKE/mpp/``; the committed fixtures here are
their verbatim MPXJ→MSPDI conversions. The companion PowerPoint
(``Politte Schedule Tool.pptx``) plus MS Project's own STORED values in the files are
the oracle:

* **Jacked Up Schedule 1** — the project calendar (Standard) has the ENTIRE September
  2026 non-working ("Sep Void"); one task runs on a **"24 Hours" calendar** through the
  void (stored Total Slack 36 900 min = 76.88 d at the project's 480 min/day), one is an
  **eDays elapsed** task (stored slack 3 780 min = 2.63 edays), and the critical path
  must NOT include either (the void makes the Standard-calendar feeder critical
  instead). Project finish 2026-10-07.
* **Jacked up Schedule 2** — a **Must-Finish-On** milestone violated by its predecessor
  chain must carry the violation as NEGATIVE slack (stored -2 400 min = -5 d), exactly
  as MS Project reports it.

Every expected number below is read from the source file's stored fields (slack stored
in tenths of a minute) and cross-checked against the PowerPoint screenshots — never
from this engine's own output (Law 2: the reference tool is the oracle).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model.schedule import Schedule

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "mspdi"


@pytest.fixture(scope="module")
def jacked1() -> tuple[Schedule, CPMResult]:
    sch = parse_mspdi(_FIXTURES / "jacked_up_schedule_1.xml")
    return sch, compute_cpm(sch)


@pytest.fixture(scope="module")
def jacked2() -> tuple[Schedule, CPMResult]:
    sch = parse_mspdi(_FIXTURES / "jacked_up_schedule_2.xml")
    return sch, compute_cpm(sch)


def _finish_date(sch: Schedule, res: CPMResult) -> dt.date:
    return offset_to_datetime(sch.project_start, res.project_finish, sch.calendar).date()


# --- Jacked Up Schedule 1: 24-hour calendar + eDays through a month-long void ---------


def test_jacked1_project_finish_matches_ms_project(jacked1) -> None:
    """MS Project computes 2026-10-07; a single-calendar pass that burns the 24-hour
    task's 120 h as fifteen 8-hour project days lands 2026-10-28 instead."""
    sch, res = jacked1
    assert _finish_date(sch, res) == dt.date(2026, 10, 7)


def test_jacked1_recomputed_float_equals_stored_for_every_task(jacked1) -> None:
    """The engine's pure-logic float must equal MS Project's stored Total Slack on this
    unprogressed file — for EVERY task that carries one, in exact minutes (24-hour
    calendar task: 36 900; eDays task: 3 780; Standard tasks: 3 840 / 480)."""
    sch, res = jacked1
    mismatches = {}
    for t in sch.tasks:
        if t.is_summary or t.stored_total_float_minutes is None:
            continue
        got = res.timing(t.unique_id).total_float
        if got != t.stored_total_float_minutes:
            mismatches[t.unique_id] = (got, t.stored_total_float_minutes)
    assert not mismatches, f"recomputed != stored (uid: (recomputed, stored)): {mismatches}"


def test_jacked1_total_float_exact_minutes(jacked1) -> None:
    """The full per-task float table, in exact working minutes (oracle: the stored
    slack fields; zero-slack tasks store no element and must recompute to 0)."""
    _sch, res = jacked1
    expected = {
        4: 0,  # ID 1  MS: Project Start
        5: 0,  # ID 2  Crit Path Task 1
        1: 0,  # ID 3  Dangling Finish (Crit Path Task 2a)
        3: 0,  # ID 4  Crit Path Task 2b
        6: 0,  # ID 5  Crit Path Task 3
        2: 3840,  # ID 6  Dangling Start — 8 d
        15: 3840,  # ID 7  Dangling Start Successor — 8 d
        14: 0,  # ID 8  Crit Path Task 4
        16: 0,  # ID 9  Standard into 24h (the void makes it critical)
        19: 36900,  # ID 10 24-hour-calendar task — 76.88 d at 480/day
        17: 480,  # ID 11 Standard into edays — 1 d
        20: 3780,  # ID 12 eDays task — 2.63 edays
        18: 480,  # ID 13 Standard past the void — 1 d
        21: 0,  # ID 14 Crit Path Task 6
        22: 0,  # ID 15 MS: Project Finish
    }
    got = {uid: res.timing(uid).total_float for uid in expected}
    assert got == expected


def test_jacked1_critical_set_excludes_the_24h_and_eday_tasks(jacked1) -> None:
    """MS Project's critical path: IDs 1-5, 8, 9, 14, 15. The 24-hour task (UID 19,
    76.88 d) and the eDays task (UID 20, 2.63 ed) float; the Standard-calendar feeder
    into the void (UID 16) is critical because any slip costs it a month."""
    _sch, res = jacked1
    assert set(res.critical_path) == {4, 5, 1, 3, 6, 14, 16, 21, 22}


def test_jacked1_24h_task_runs_through_the_void_on_its_own_calendar(jacked1) -> None:
    """UID 19 (24 Hours): starts when its predecessor finishes (2026-08-31 17:00) and
    consumes 120 wall-hours -> finishes 2026-09-05 17:00, inside the project calendar's
    void — representable only as a wall-clock instant."""
    _sch, res = jacked1
    tm = res.timing(19)
    assert tm.early_start_wall == dt.datetime(2026, 8, 31, 17, 0)
    assert tm.early_finish_wall == dt.datetime(2026, 9, 5, 17, 0)


def test_jacked1_eday_task_fills_the_void(jacked1) -> None:
    """UID 20 (32 eDays, calendar None): 2026-08-27 17:00 + 768 wall-hours ->
    2026-09-28 17:00 (MS Project's stored dates)."""
    _sch, res = jacked1
    tm = res.timing(20)
    assert tm.early_start_wall == dt.datetime(2026, 8, 27, 17, 0)
    assert tm.early_finish_wall == dt.datetime(2026, 9, 28, 17, 0)


def test_jacked1_free_float_matches_stored(jacked1) -> None:
    """Stored FreeSlack: UID 15 = 3 840 (no successor, gap to project finish);
    UID 19 = 36 900 and UID 20 = 3 780 (each measured on the task's own calendar);
    UID 2 = 0 (its successor starts immediately)."""
    _sch, res = jacked1
    assert res.timing(15).free_float == 3840
    assert res.timing(19).free_float == 36900
    assert res.timing(20).free_float == 3780
    assert res.timing(2).free_float == 0


# --- Jacked up Schedule 2: Must-Finish-On violation = negative slack ------------------


def test_jacked2_project_finish(jacked2) -> None:
    sch, res = jacked2
    assert _finish_date(sch, res) == dt.date(2026, 10, 9)


def test_jacked2_mfo_violation_reports_negative_slack(jacked2) -> None:
    """UID 30 is a Must-Finish-On 2026-08-14 milestone whose predecessor (UID 29)
    cannot finish before 08-21: MS Project stores Total Slack -2 400 min (-5 d) on BOTH
    — the violated pin itself must report the violation, not a placid 0."""
    _sch, res = jacked2
    assert res.timing(29).total_float == -2400
    assert res.timing(30).total_float == -2400


def test_jacked2_recomputed_float_equals_stored_for_every_task(jacked2) -> None:
    """Same stored-vs-recomputed sweep as Jacked 1 — covers the SNET task (-2 400), the
    MFO milestone (-2 400), and the deadline-less UID 32 (+6 240 = 13 d)."""
    sch, res = jacked2
    mismatches = {}
    for t in sch.tasks:
        if t.is_summary or t.stored_total_float_minutes is None:
            continue
        got = res.timing(t.unique_id).total_float
        if got != t.stored_total_float_minutes:
            mismatches[t.unique_id] = (got, t.stored_total_float_minutes)
    assert not mismatches, f"recomputed != stored (uid: (recomputed, stored)): {mismatches}"


def test_jacked2_critical_set(jacked2) -> None:
    """MS Project flags exactly the zero/negative-slack tasks: the start milestone, the
    30-day spine (UID 33), the finish milestone, and the two -5 d constraint tasks."""
    _sch, res = jacked2
    assert set(res.critical_path) == {4, 33, 22, 29, 30}


def test_jacked2_null_rows_are_not_tasks(jacked2) -> None:
    """The file carries five IsNull=1 blank rows (IDs 4-7, 10); they must not enter the
    model (16-vs-12 row counts in the source pair are the tell)."""
    sch, _res = jacked2
    assert len(sch.tasks) == 7  # UID-0 summary + 6 real activities
    assert {25, 26, 27, 28, 31}.isdisjoint({t.unique_id for t in sch.tasks})


# --- Deadline pipeline: importer -> engine (Jacked 2's slide intent) ------------------


_DEADLINE_MSPDI = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <StartDate>2026-08-03T08:00:00</StartDate>
  <Tasks>
    <Task><UID>1</UID><ID>1</ID><Name>A</Name><Duration>PT40H0M0S</Duration>
      <DurationFormat>7</DurationFormat></Task>
    <Task><UID>2</UID><ID>2</ID><Name>B with deadline</Name><Duration>PT40H0M0S</Duration>
      <DurationFormat>7</DurationFormat><Deadline>2026-08-07T17:00:00</Deadline>
      <PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>
    </Task>
  </Tasks>
</Project>
"""


def test_offcalendar_chain_propagates_wall_instants(jacked1) -> None:
    """Two off-calendar tasks in a row must hand the TRUE wall instant across the link —
    the project axis collapses the whole void to one grid point, so an int round-trip
    would start the successor five days before its predecessor finishes. Built by giving
    Jacked 1's 24-hour task a 24-hour successor."""
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.task import Task

    sch, _res = jacked1
    extra = Task(unique_id=900, name="24h follow-on", duration_minutes=1440, calendar_uid=4)
    chained = sch.model_copy(
        update={
            "tasks": (*sch.tasks, extra),
            "relationships": (
                *sch.relationships,
                Relationship(predecessor_id=19, successor_id=900),
            ),
        }
    )
    res = compute_cpm(chained)
    tm = res.timing(900)
    assert tm.early_start_wall == dt.datetime(2026, 9, 5, 17, 0)  # pred's wall finish
    assert tm.early_finish_wall == dt.datetime(2026, 9, 6, 17, 0)


def test_offcalendar_task_with_no_predecessors_starts_at_project_start(jacked1) -> None:
    """Offset 0 under the start-role mapping is the project start instant, not the next
    working day — a logic-unbound off-calendar task must not drift by a day."""
    from schedule_forensics.model.task import Task

    sch, _res = jacked1
    lone = Task(unique_id=901, name="lone 24h", duration_minutes=1440, calendar_uid=4)
    res = compute_cpm(sch.model_copy(update={"tasks": (*sch.tasks, lone)}))
    assert res.timing(901).early_start_wall == sch.project_start


def test_same_pattern_task_calendar_stays_on_the_integer_fast_path(jacked1) -> None:
    """A task calendar whose working pattern equals the project calendar's (e.g. a derived
    resource calendar that inherits everything) must NOT route through the wall machinery."""
    _sch, res = jacked1
    for uid in (4, 5, 1, 3, 6, 2, 15, 14, 16, 17, 18, 21, 22):
        tm = res.timing(uid)
        assert tm.early_start_wall is None and tm.late_finish_wall is None, uid


def test_dcma12_passes_a_perfect_elapsed_chain() -> None:
    """Review-confirmed false FAIL: two chained elapsed tasks form a continuous,
    constraint-free critical path, but the downstream task's weekend collapse shifts the
    axis delta by a day and the exact-axis equality missed. Continuity's wall-axis
    signature (project finish instant shifts exactly with the tested activity's finish)
    must rescue the verdict."""
    from schedule_forensics.engine.dcma_audit import audit_schedule
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.task import Task

    sch = Schedule(
        name="echain",
        project_start=dt.datetime(2026, 1, 2, 8, 0),  # a Friday
        tasks=(
            Task(unique_id=1, name="E1", duration_minutes=1440, duration_is_elapsed=True),
            Task(unique_id=2, name="E2", duration_minutes=1440, duration_is_elapsed=True),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    audit = audit_schedule(sch, compute_cpm(sch))
    (check,) = [c for c in audit.checks if c.name == "Critical Path Test"]
    assert str(check.status) == "PASS"


def test_offcalendar_midday_finish_projects_on_the_contiguous_ruler() -> None:
    """Review-confirmed two-ruler defect: on a lunch-segmented project calendar, a 24/7
    predecessor finishing mid-day used to project segment-aware (420) while constraints
    and rendering measure contiguously (480) — its successor rendered BEFORE the
    predecessor's finish and a same-instant SNET out-bound the link. Projection must use
    the canonical contiguous ruler."""
    from schedule_forensics.engine.cpm import datetime_to_offset, offset_to_datetime
    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.task import Task

    lunch = Calendar(
        uid=1,
        name="Standard+lunch",
        working_minutes_per_day=480,
        day_segments=((480, 720), (780, 1020)),  # 08:00-12:00 + 13:00-17:00
    )
    cal24 = Calendar(
        uid=4, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
    )
    sch = Schedule(
        name="rulers",
        project_start=dt.datetime(2026, 1, 5, 8, 0),  # a Monday
        calendar=lunch,
        calendars=(lunch, cal24),
        tasks=(
            Task(unique_id=1, name="P", duration_minutes=480, calendar_uid=4),  # -> Mon 16:00
            Task(unique_id=2, name="S", duration_minutes=480),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    res = compute_cpm(sch)
    pred_finish_wall = res.timing(1).early_finish_wall
    assert pred_finish_wall == dt.datetime(2026, 1, 5, 16, 0)
    # one ruler: the successor's axis start equals the canonical projection of that instant
    assert res.timing(2).early_start == datetime_to_offset(
        sch.project_start, pred_finish_wall, lunch
    )
    # and it never RENDERS before the predecessor's true finish
    rendered = offset_to_datetime(sch.project_start, res.timing(2).early_start, lunch)
    assert rendered >= pred_finish_wall


def test_a_24_hour_project_calendar_does_not_crash_the_wall_mapping() -> None:
    """A 1440-minute working day ends at minute 1440 — the NEXT day's midnight. The wall
    mapping must build that instant via day-arithmetic, not ``datetime(hour=24)`` (which
    raises). Repro: a 24-hour PROJECT calendar with one Standard-calendar (off-calendar)
    task downstream (final-diff review blocker, reproduced before the fix)."""
    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.task import Task

    cal24 = Calendar(
        uid=1, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
    )
    std = Calendar(uid=2, name="Standard", working_minutes_per_day=480)
    sch = Schedule(
        name="c24",
        project_start=dt.datetime(2026, 1, 5, 0, 0),
        calendar=cal24,
        calendars=(cal24, std),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=1440),
            Task(unique_id=2, name="B", duration_minutes=480, calendar_uid=2),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    res = compute_cpm(sch)
    assert res.timing(2).early_start_wall == dt.datetime(2026, 1, 6, 0, 0)
    assert res.timing(2).total_float == 0


def test_all_project_calendar_schedule_has_no_wall_fields() -> None:
    """Fast-path sentinel: with no off-calendar and no elapsed tasks the result must carry
    no wall instants at all (the new machinery provably never ran)."""
    sch = parse_mspdi(_FIXTURES / "commercial_construction.xml")
    res = compute_cpm(sch)
    assert res.project_finish_wall is None
    assert all(
        t.early_start_wall is None and t.late_finish_wall is None for t in res.timings.values()
    )


def test_deadline_survives_import_and_drives_negative_float(tmp_path: Path) -> None:
    """A `<Deadline>` in the MSPDI must reach the engine as a backward cap: B's logic
    finish is 08-14 against a 08-07 deadline -> -5 d on B AND on its predecessor (the
    cap propagates upstream, matching MS Project). Guards the full import->CPM pipeline
    the Jacked-2 slide exercises (its own saved file lost the deadline pre-save)."""
    from schedule_forensics.importers.mspdi import parse_mspdi_text

    sch = parse_mspdi_text(_DEADLINE_MSPDI, source_file="deadline.xml")
    assert [t.deadline for t in sch.tasks if t.unique_id == 2] == [dt.datetime(2026, 8, 7, 17, 0)]
    res = compute_cpm(sch)
    assert res.timing(2).total_float == -2400
    assert res.timing(1).total_float == -2400


# --- The operator's RE-SAVED Jacked 2 (deadline now in the bytes; slide 6 closed) -----


def test_resaved_jacked2_deadline_reads_minus_five_days_end_to_end() -> None:
    """The operator re-saved `Jacked up Schedule 2.mpp` WITH Task 11's deadline
    (2026-08-14) after the original upload proved the deadline never hit disk; this
    fixture is that file's verbatim MPXJ conversion. The slide-6 oracle now closes
    end-to-end with no engine change: UID 32 carries the deadline, its stored Total
    Slack (-2 400 min = -5 d) equals the recomputed float exactly, all three -5 d tasks
    are critical, and DCMA-07 cites them. (On the pre-ADR-0322 engine this fails: the
    violated-MFO UID 30 recomputed 0 against stored -2 400.)"""
    import datetime as _dt

    from schedule_forensics.engine.metrics.dcma14 import compute_dcma14

    sch = parse_mspdi(_FIXTURES / "jacked_up_schedule_2_with_deadline.xml")
    t32 = next(t for t in sch.tasks if t.unique_id == 32)
    assert t32.deadline == _dt.datetime(2026, 8, 14, 17, 0)
    res = compute_cpm(sch)
    assert res.timing(32).total_float == -2400 == t32.stored_total_float_minutes
    mismatches = {
        t.unique_id: (res.timing(t.unique_id).total_float, t.stored_total_float_minutes)
        for t in sch.tasks
        if not t.is_summary
        and t.stored_total_float_minutes is not None
        and res.timing(t.unique_id).total_float != t.stored_total_float_minutes
    }
    assert not mismatches, f"recomputed != stored: {mismatches}"
    assert set(res.critical_path) == {4, 33, 22, 29, 30, 32}
    assert set(compute_dcma14(sch, cpm_result=res)["DCMA07"].offender_uids) == {29, 30, 32}
