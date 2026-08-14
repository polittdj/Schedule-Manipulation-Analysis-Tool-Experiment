"""ADR-0391's OWN-CALENDAR actual-start floor (cpm.py forward pass, ``exec_cal`` branch).

The 2026-08-13 audit queue carried this finding (SESSION-LOG 2026-08-13; it predates the
audit table itself): the own-calendar half of the ADR-0391 floor was behaviorally
unguarded — deleting the ``if task.actual_start is not None`` block inside the
``tid in exec_cal`` forward-pass branch left ``tests/engine`` (963 passed) AND the parity
gate (52 passed, 0 failed) green, measured 2026-08-14 in a branch-deleted sandbox. Three
measured root causes: no ``tests/fixtures/test_projects`` battery file has ANY exec_cal
task; ``test_progressed_finish_fidelity.py`` deliberately steps over own-calendar tasks
(wall instants); and ADR-0391's own mutation battery ("deleting the floor, 8 failures")
exercised only the project-axis half (``_actual_start_bounds``), which an exec_cal task
never reaches — its branch ``continue``s first.

The stakes are not theoretical: on the primary golden (Large_Test_File, 2,126 tasks) the
floor binds on 19 own-calendar UIDs, and deleting the branch pulls UID 5230's early start
from 2023-08-08 back to 2017-09-05 — a ~6-year understatement — while ``project_finish``
and every value the SSI/parity pins read stay byte-identical, which is exactly why the
existing suites were blind.

QC-1 (prove-able-to-fail): this module was run against that branch-deleted sandbox before
landing — the synthetic tests fail (UID 2 ES_wall comes back 2026-01-05 16:00, project
finish offset 1920, ``actual_start_driven`` empty) and the golden test fails on all five
named UIDs; the whole module passes on the intact tree; and it stays GREEN when the
project-axis floor (the already-guarded sibling) is deleted instead, so it aims at the
own-calendar branch specifically and cannot be satisfied by the other half. The ADR-0240
adversarial round then found the population blind to three PARTIAL mutations (floor-source
substitution to the stored Start; ``>=``/append-always false-positive disclosure; snap
dropped) — closed by UID 2's disagreeing stored Start, the UID 4 equal-instant control,
and the Tue-Sat void-snap test; each was re-proven red against its named mutant sandbox
(1/1/1/2 narrow failures) with the isolation control still green.

Synthetic scenario (expectations hand-derived in the assertions' comments):
  Mon-Fri/480 project calendar, project start Mon 2026-01-05 08:00.
  UID 1  "Mobilize"                1d, project calendar, no actuals
  UID 2  "Around-the-clock pour"   2880 min on its OWN 24/7 calendar (uid 7),
                                   FS after 1, ActualStart Mon 2026-01-12 00:00, 25%
  UID 3  "Cure and strip"          1d, project calendar, FS after 2

UID 2 executes on a materially different calendar, so it is scheduled by the own-calendar
branch — the PROJECT-AXIS floor never touches it. Its logic ES wall is UID 1's finish
(Mon 2026-01-05 16:00); the recorded actual start a week later must floor it to
2026-01-12 00:00 and push UID 3 and the project finish a week out. No constraints, not
manual: with ``actual_start`` set, ``_stored_date_bounds`` skips the task by design, so
only the ADR-0391 floor can move it.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: Own-calendar (CalendarUID 68) in-progress tasks on the primary golden where the
#: ADR-0391 floor BINDS (recorded actual start later than logic ES) — five of the 19
#: measured. Named positives; their EXPECTED dates are derived from the file at test
#: time, never transcribed here.
_GOLDEN_FLOORED_UIDS = (5230, 5345, 6104, 6105, 6436)


def _schedule() -> Schedule:
    return Schedule(
        name="adr0391-own-cal-floor",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        calendar=Calendar(),
        calendars=(
            Calendar(
                uid=7,
                name="24 Hours",
                working_minutes_per_day=1440,
                work_weekdays=(0, 1, 2, 3, 4, 5, 6),
            ),
        ),
        tasks=(
            Task(unique_id=1, name="Mobilize", duration_minutes=480),
            Task(
                unique_id=2,
                name="Around-the-clock pour",
                duration_minutes=2880,
                calendar_uid=7,
                percent_complete=25.0,
                actual_start=dt.datetime(2026, 1, 12, 0, 0),
                # A stored Start that DISAGREES with the recorded actual start (adversarial
                # round, F1): the floor must read actual_start — an implementation flooring
                # from the stored Start instead lands a week late (2026-01-19) and both
                # test populations were previously blind to the substitution (the synthetic
                # had start=None; every golden row had start == actual_start).
                start=dt.datetime(2026, 1, 19, 0, 0),
            ),
            Task(unique_id=3, name="Cure and strip", duration_minutes=480),
            # Equal-instant control (adversarial round, F2): an own-calendar task whose
            # recorded actual start EQUALS its logic early start. The floor is strictly
            # greater-than, so this UID must NOT be disclosed as actual-start-driven —
            # a >= or append-always regression adds it to the tuple and fails the exact
            # equality below (previously the false-positive direction was unguarded).
            Task(
                unique_id=4,
                name="Site security (already running)",
                duration_minutes=480,
                calendar_uid=7,
                percent_complete=50.0,
                actual_start=dt.datetime(2026, 1, 5, 8, 0),
            ),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS),
        ),
    )


def test_own_calendar_task_floors_at_its_recorded_actual_start() -> None:
    res = compute_cpm(_schedule())
    t2 = res.timing(2)
    assert t2 is not None
    # The floor: work that began 2026-01-12 00:00 cannot be scheduled at the logic
    # start (Mon 2026-01-05 16:00). Wall instants are the own-calendar truth surface.
    assert t2.early_start_wall == dt.datetime(2026, 1, 12, 0, 0)
    assert t2.early_finish_wall == dt.datetime(2026, 1, 14, 0, 0)  # +2880 min on 24/7
    # Project-axis projections: Jan 5-9 are five full Mon-Fri days (2400 min) before
    # Jan 12 00:00; the finish adds Jan 12+13 (960) with Jan 14 00:00 pre-workday.
    assert (t2.early_start, t2.early_finish) == (2400, 3360)
    # The disclosure surface: the floored UID is reported as actual-start-driven,
    # and NOT as date_driven (ADR-0391 keeps the two lists separate).
    assert res.actual_start_driven == (2,)
    assert res.date_driven == ()


def test_own_calendar_floor_propagates_to_successors_and_project_finish() -> None:
    res = compute_cpm(_schedule())
    t1, t3 = res.timing(1), res.timing(3)
    assert t1 is not None and t3 is not None
    # Successor on the project axis starts after the floored finish (Wed 08:00).
    assert (t3.early_start, t3.early_finish) == (3360, 3840)
    assert res.project_finish == 3840  # Wed 2026-01-14 16:00, a week later than logic
    # The floor re-shapes float/criticality: UID 1 gains the week the pour lost
    # (its LF retreats from UID 2's late start, Mon Jan 12 08:00 = offset 2400).
    assert t1.total_float == 1920 and not t1.is_critical
    assert t3.total_float == 0 and t3.is_critical


def test_own_calendar_floor_snaps_a_void_actual_start_to_working_time() -> None:
    """The floor snaps the recorded instant onto the task's OWN calendar (adversarial
    round, F3): an actual start recorded in the calendar's void (Sunday 03:00 on a
    Tue-Sat calendar) must land on the next working instant, Tue 2026-01-20 08:00 —
    an unsnapped implementation schedules work at a non-working instant. The main
    scenario cannot see this (its own calendar is 24/7, where snapping is the
    identity), and every own-calendar actual start on the golden sits at a working
    08:00 already."""
    sch = Schedule(
        name="adr0391-own-cal-floor-snap",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        calendar=Calendar(),
        calendars=(
            Calendar(
                uid=8,
                name="Tue-Sat",
                working_minutes_per_day=480,
                work_weekdays=(1, 2, 3, 4, 5),
            ),
        ),
        tasks=(
            Task(
                unique_id=9,
                name="Weekend-shifted crew",
                duration_minutes=480,
                calendar_uid=8,
                percent_complete=10.0,
                actual_start=dt.datetime(2026, 1, 18, 3, 0),  # Sunday, in the void
            ),
        ),
    )
    res = compute_cpm(sch)
    t9 = res.timing(9)
    assert t9 is not None
    # Sun Jan 18 03:00 -> Mon is non-working on Tue-Sat -> Tue Jan 20 08:00.
    assert t9.early_start_wall == dt.datetime(2026, 1, 20, 8, 0)
    assert t9.early_finish_wall == dt.datetime(2026, 1, 20, 16, 0)
    assert res.actual_start_driven == (9,)


def test_golden_own_calendar_actuals_floor_at_their_recorded_starts() -> None:
    """The floor on REAL own-calendar tasks, expectation derived from the file itself.

    For each named UID the early start WALL instant must equal the task's stored
    ``ActualStart`` (the floor binds there — the logic-only start is years earlier),
    and the UID must be disclosed on ``actual_start_driven``. With the branch deleted
    this fails on every row (UID 5230 comes back 2017-09-05, six years early).
    """
    path = GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz"
    sch = parse_mspdi_text(
        gzip.decompress(path.read_bytes()).decode("utf-8"), source_file=path.name
    )
    res = compute_cpm(sch)
    by_uid = {t.unique_id: t for t in sch.tasks}
    driven = set(res.actual_start_driven)
    for uid in _GOLDEN_FLOORED_UIDS:
        task = by_uid[uid]
        assert task.actual_start is not None  # fixture contract for the named rows
        timing = res.timing(uid)
        assert timing is not None
        assert timing.early_start_wall == task.actual_start, (
            f"UID {uid}: own-calendar early start {timing.early_start_wall} does not "
            f"honor the recorded actual start {task.actual_start} (ADR-0391 floor)"
        )
        assert uid in driven, f"UID {uid} missing from actual_start_driven"
