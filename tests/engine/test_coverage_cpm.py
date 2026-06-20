"""CPM elapsed-duration bound/cap coverage — SS/FF/SF links and elapsed constraints.

Targets the elapsed-task branches in :func:`compute_cpm` and :func:`_constraint_bounds`:
an ELAPSED task converts each of its predecessor link bounds (FS/SS/FF/SF) and successor
caps onto the wall clock, and an ELAPSED task carrying a date constraint maps the
constraint offset through the elapsed-start / elapsed-finish helpers. Values are
hand-verified against the elapsed-axis semantics (1 eday = 1440 wall-clock minutes; a
weekend finish reads back as the prior Friday end-of-day on the working axis).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import (
    _constraint_bounds,
    _scheduled_tasks,
    compute_cpm,
    offset_to_datetime,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2026, 1, 5, 8, 0)  # a Monday at start of day
DAY = 480  # working minutes per 8h day
EDAY = 1440  # one elapsed day == 24 wall-clock hours in minutes


def _elapsed(uid: int, name: str, *, minutes: int = EDAY, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=minutes, duration_is_elapsed=True, **kw)


def test_elapsed_successor_of_ss_link_anchors_to_predecessor_start() -> None:
    """An SS predecessor bounds an elapsed successor's START at the predecessor's early
    start; the elapsed finish is start + 24 wall-clock hours (1 working day on the grid).
    Exercises the FS/SS forward branch for an elapsed task (cpm.py 448-449)."""
    p = Task(unique_id=1, name="P", duration_minutes=3 * DAY)
    e = _elapsed(2, "E")
    s = Task(unique_id=3, name="S", duration_minutes=DAY)
    sch = Schedule(
        name="ss",
        project_start=MON,
        tasks=(p, e, s),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.SS),
            Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS),
        ),
    )
    cpm = compute_cpm(sch)
    e_t = cpm.timings[2]
    # SS, lag 0: E starts when P starts (offset 0); 1 eday over Mon 08:00 -> Mon 16:00 (480 min).
    assert e_t.early_start == 0
    assert e_t.early_finish == DAY
    # the FS successor starts where E finishes, proving the elapsed finish propagated as an FS cap.
    assert cpm.timings[3].early_start == DAY


def test_elapsed_successor_of_ff_and_sf_predecessor_links() -> None:
    """An FF predecessor anchors the elapsed successor on the predecessor's early FINISH;
    an SF predecessor anchors on the predecessor's early START — both converted to an
    elapsed-start on the wall clock (cpm.py 450-452, the FF/SF else branch)."""
    p = Task(unique_id=1, name="P", duration_minutes=2 * DAY)
    e_ff = _elapsed(2, "E_FF")
    e_sf = _elapsed(3, "E_SF")
    sch = Schedule(
        name="ffsf",
        project_start=MON,
        tasks=(p, e_ff, e_sf),
        relationships=(
            # FF: P (early finish 960) anchors E_FF's finish; elapsed start backs off 1 eday.
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FF),
            # SF: P (early start 0) anchors E_SF's finish via its START anchor.
            Relationship(predecessor_id=1, successor_id=3, type=RelationshipType.SF),
        ),
    )
    cpm = compute_cpm(sch)
    # P spans 2 working days: early_start 0, early_finish 960.
    assert cpm.timings[1].early_finish == 2 * DAY
    # FF anchor = P's early finish (960); one eday back lands E_FF's start a day earlier (480).
    assert cpm.timings[2].early_start == DAY
    assert cpm.timings[2].early_finish == 2 * DAY
    # SF anchor = P's early start (0); E_SF's start backs off to the project start floor (0).
    assert cpm.timings[3].early_start == 0
    assert cpm.timings[3].early_finish == DAY


def test_elapsed_task_backward_caps_from_ss_ff_sf_successors() -> None:
    """An elapsed task's backward pass: an FS successor caps its FINISH, an FF successor caps
    its finish, and SS/SF successors cap its START directly (cpm.py 496-501, 503). The cap
    that binds drives a non-positive total float on the elapsed task."""
    e = _elapsed(1, "E")
    fs = Task(unique_id=2, name="FS", duration_minutes=DAY)
    ff = Task(unique_id=3, name="FF", duration_minutes=DAY)
    ss = Task(unique_id=4, name="SS", duration_minutes=DAY)
    sf = Task(unique_id=5, name="SF", duration_minutes=DAY)
    sch = Schedule(
        name="back",
        project_start=MON,
        tasks=(e, fs, ff, ss, sf),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=1, successor_id=3, type=RelationshipType.FF),
            Relationship(predecessor_id=1, successor_id=4, type=RelationshipType.SS),
            Relationship(predecessor_id=1, successor_id=5, type=RelationshipType.SF),
        ),
    )
    cpm = compute_cpm(sch)
    e_t = cpm.timings[1]
    # E is the sole driver of every successor with no slack of its own: critical (tf <= 0).
    assert e_t.total_float <= 0
    assert e_t.is_critical
    # late finish equals early finish — the binding successor caps left no room to slip.
    assert e_t.late_finish == e_t.early_finish == DAY
    assert 1 in cpm.critical_path


def test_elapsed_task_with_fnet_constraint_uses_elapsed_start_helper() -> None:
    """An ELAPSED task carrying an FNET (finish-no-earlier-than) constraint converts the
    finish offset back to a start floor through the elapsed-start helper (cpm.py 338)."""
    e = _elapsed(
        1,
        "E",
        constraint_type=ConstraintType.FNET,
        constraint_date=dt.datetime(2026, 1, 8, 8, 0),  # Thursday 08:00
    )
    sch = Schedule(name="fnet", project_start=MON, tasks=(e,), relationships=())
    cpm = compute_cpm(sch)
    t = cpm.timings[1]
    # FNET pushes the finish to Thu 08:00; the elapsed start is exactly one eday before it.
    start_dt = offset_to_datetime(MON, t.early_start, sch.calendar)
    finish_dt = offset_to_datetime(MON, t.early_finish, sch.calendar)
    assert finish_dt == dt.datetime(2026, 1, 7, 16, 0)  # Wed end-of-day on the working grid
    assert start_dt == dt.datetime(2026, 1, 6, 16, 0)  # one eday (24h) earlier
    assert t.early_finish - t.early_start == DAY


def test_elapsed_task_with_snlt_constraint_uses_elapsed_finish_helper() -> None:
    """An ELAPSED task carrying an SNLT (start-no-later-than) constraint maps the start cap
    forward to a finish cap through the elapsed-finish helper (cpm.py 345). The cap is built
    by ``_constraint_bounds`` from the constraint's elapsed finish."""
    e = _elapsed(
        1,
        "E",
        constraint_type=ConstraintType.SNLT,
        constraint_date=dt.datetime(2026, 1, 9, 8, 0),  # Friday 08:00
    )
    sch = Schedule(name="snlt", project_start=MON, tasks=(e,), relationships=())
    tasks = _scheduled_tasks(sch)
    duration = {t.unique_id: t.duration_minutes for t in tasks}
    _es_floor, _es_pin, lf_cap = _constraint_bounds(sch, tasks, duration)
    # SNLT caps the START at Fri 08:00; the elapsed-finish helper carries it one eday (24h) forward
    # to the late-FINISH cap. Fri 08:00 + 1 eday wall-clock = Sat 08:00 -> maps to the working-grid
    # offset one eday (480 working min) past Friday's start (Friday's start offset is 4*480=1920).
    finish_cap = lf_cap[1]
    assert finish_cap == 1920 + DAY  # Friday-start offset plus one elapsed day on the working grid
    cap_finish_dt = offset_to_datetime(MON, finish_cap, sch.calendar)
    assert cap_finish_dt == dt.datetime(2026, 1, 9, 16, 0)  # Friday end-of-day on the grid
    # the elapsed task itself schedules at the project start; its float is measured against the cap.
    cpm = compute_cpm(sch)
    assert cpm.timings[1].early_start == 0
