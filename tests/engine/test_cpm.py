"""CPM engine tests — hand-verified synthetic networks, every link type and
constraint, the refusal/error paths, and the calendar offset helpers.

The time axis is integer working minutes from ``project_start`` (480 == one day).
``project_start`` is a Monday 08:00 so the standard Mon-Fri calendar is exercised.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import (
    CPMError,
    compute_cpm,
    datetime_to_offset,
    offset_to_datetime,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480
CAL = Calendar()


def _task(uid: int, dur_days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _rel(
    p: int, s: int, rtype: RelationshipType = RelationshipType.FS, lag_days: float = 0
) -> Relationship:
    return Relationship(
        predecessor_id=p, successor_id=s, type=rtype, lag_minutes=int(lag_days * DAY)
    )


def _sched(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


# --- core forward/backward passes -------------------------------------------------


def test_linear_chain_all_critical() -> None:
    s = _sched([_task(1, 2), _task(2, 3), _task(3, 1)], [_rel(1, 2), _rel(2, 3)])
    r = compute_cpm(s)
    assert r.project_finish == 6 * DAY
    assert r.critical_path == (1, 2, 3)
    for uid in (1, 2, 3):
        assert r.timing(uid).total_float == 0
        assert r.timing(uid).is_critical
    assert r.timing(1).early_start == 0 and r.timing(1).early_finish == 2 * DAY
    assert r.timing(3).early_finish == 6 * DAY


def test_parallel_diamond_float_on_short_branch() -> None:
    # A(1d) -> {B(2d), C(4d)} -> D(1d). C is the driver; B carries 2 days of float.
    s = _sched(
        [_task(1, 1), _task(2, 2), _task(3, 4), _task(4, 1)],
        [_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)],
    )
    r = compute_cpm(s)
    assert r.project_finish == 6 * DAY
    assert r.critical_path == (1, 3, 4)
    assert r.timing(2).total_float == 2 * DAY
    assert r.timing(2).free_float == 2 * DAY
    assert r.timing(2).is_critical is False
    for uid in (1, 3, 4):
        assert r.timing(uid).total_float == 0
    assert r.timing(1).free_float == 0


def test_fs_lag_pushes_successor() -> None:
    s = _sched([_task(1, 1), _task(2, 1)], [_rel(1, 2, lag_days=2)])
    r = compute_cpm(s)
    assert r.timing(2).early_start == 3 * DAY  # 1d duration + 2d lag
    assert r.timing(2).early_finish == 4 * DAY
    assert r.timing(1).free_float == 0  # lag consumes the gap


def test_ss_link_float() -> None:
    # A(3d) SS-> B(1d): B starts with A, finishes early, gathers float; A drives finish.
    s = _sched([_task(1, 3), _task(2, 1)], [_rel(1, 2, RelationshipType.SS)])
    r = compute_cpm(s)
    assert r.project_finish == 3 * DAY
    assert r.timing(1).total_float == 0
    assert r.timing(2).early_start == 0
    assert r.timing(2).total_float == 2 * DAY


def test_ff_link_float() -> None:
    # A(1d) FF-> B(3d): B's finish governs A's; A gains float.
    s = _sched([_task(1, 1), _task(2, 3)], [_rel(1, 2, RelationshipType.FF)])
    r = compute_cpm(s)
    assert r.project_finish == 3 * DAY
    assert r.timing(2).total_float == 0
    assert r.timing(1).total_float == 2 * DAY
    assert r.timing(1).free_float == 2 * DAY


def test_sf_link_runs() -> None:
    # SF is rare; assert the branch computes and the network finishes coherently.
    s = _sched([_task(1, 1), _task(2, 1)], [_rel(1, 2, RelationshipType.SF)])
    r = compute_cpm(s)
    assert r.project_finish == 1 * DAY
    assert r.timing(1).is_critical


def test_multiple_open_ends_only_longest_is_critical() -> None:
    # A(1d) -> B(2d); A -> C(5d). Two finish points; only the longer chain is critical.
    s = _sched([_task(1, 1), _task(2, 2), _task(3, 5)], [_rel(1, 2), _rel(1, 3)])
    r = compute_cpm(s)
    assert r.project_finish == 6 * DAY
    assert r.critical_path == (1, 3)
    assert r.timing(2).total_float == 3 * DAY  # finishes at 3d vs network 6d
    assert r.timing(2).free_float == 3 * DAY


# --- constraints ------------------------------------------------------------------


def test_snet_floors_early_start_and_creates_float() -> None:
    snet = offset_to_datetime(MON, 5 * DAY, CAL)
    s = _sched(
        [_task(1, 1), _task(2, 1, constraint_type=ConstraintType.SNET, constraint_date=snet)],
        [_rel(1, 2)],
    )
    r = compute_cpm(s)
    assert r.timing(2).early_start == 5 * DAY  # floored, not 1d from predecessor
    assert r.timing(1).total_float == 4 * DAY  # predecessor now has slack


def test_fnet_floors_via_finish() -> None:
    fnet = offset_to_datetime(MON, 4 * DAY, CAL)  # finish no earlier than day 4
    s = _sched([_task(1, 2, constraint_type=ConstraintType.FNET, constraint_date=fnet)])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 2 * DAY  # off(4d) - dur(2d)
    assert r.timing(1).early_finish == 4 * DAY


def test_snlt_cap_can_force_negative_float() -> None:
    # B must start no later than day 1, but its predecessor pushes it to day 3.
    snlt = offset_to_datetime(MON, 1 * DAY, CAL)
    s = _sched(
        [_task(1, 3), _task(2, 1, constraint_type=ConstraintType.SNLT, constraint_date=snlt)],
        [_rel(1, 2)],
    )
    r = compute_cpm(s)
    assert r.timing(2).early_start == 3 * DAY
    assert r.timing(2).total_float < 0  # cap earlier than the driven start


def test_fnlt_cap() -> None:
    # B finishes at 1d but a 5d sibling sets the network finish; FNLT at 2d caps B's late finish.
    fnlt = offset_to_datetime(MON, 2 * DAY, CAL)
    s = _sched(
        [_task(1, 5), _task(2, 1, constraint_type=ConstraintType.FNLT, constraint_date=fnlt)]
    )
    r = compute_cpm(s)
    assert r.project_finish == 5 * DAY
    assert r.timing(2).late_finish == 2 * DAY
    assert r.timing(2).total_float == 1 * DAY  # cap 2d - early finish 1d


def test_mso_pins_start() -> None:
    mso = offset_to_datetime(MON, 3 * DAY, CAL)
    s = _sched([_task(1, 2, constraint_type=ConstraintType.MSO, constraint_date=mso)])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 3 * DAY  # pinned regardless of project start
    assert r.timing(1).total_float <= 0  # pinned -> no positive float
    assert r.timing(1).is_critical


def test_mfo_pins_finish() -> None:
    mfo = offset_to_datetime(MON, 5 * DAY, CAL)
    s = _sched([_task(1, 2, constraint_type=ConstraintType.MFO, constraint_date=mfo)])
    r = compute_cpm(s)
    assert r.timing(1).early_finish == 5 * DAY  # finish pinned
    assert r.timing(1).early_start == 3 * DAY  # 5d - 2d duration
    assert r.timing(1).is_critical


def test_deadline_caps_late_finish() -> None:
    # A task deadline is a backward cap; binds only when earlier than the network finish.
    deadline = offset_to_datetime(MON, 3 * DAY, CAL)
    s = _sched([_task(1, 5), _task(2, 1, deadline=deadline)])
    r = compute_cpm(s)
    assert r.project_finish == 5 * DAY
    assert r.timing(2).late_finish == 3 * DAY
    assert r.timing(2).total_float == 2 * DAY  # deadline 3d - early finish 1d


def test_required_finish_offset_drives_negative_float() -> None:
    s = _sched([_task(1, 2), _task(2, 2)], [_rel(1, 2)])
    r = compute_cpm(s, required_finish_offset=2 * DAY)  # demand finish 2d earlier than the 4d EF
    assert r.timing(1).total_float == -2 * DAY
    assert r.timing(2).total_float == -2 * DAY
    assert all(r.timing(u).is_critical for u in (1, 2))


def test_summary_tasks_excluded_from_network() -> None:
    s = _sched([_task(1, 1), Task(unique_id=99, name="WBS", duration_minutes=0, is_summary=True)])
    r = compute_cpm(s)
    assert set(r.timings) == {1}


# --- refusal / error paths --------------------------------------------------------


def test_alap_is_refused() -> None:
    when = offset_to_datetime(MON, 2 * DAY, CAL)
    s = _sched([_task(1, 1, constraint_type=ConstraintType.ALAP, constraint_date=when)])
    with pytest.raises(CPMError, match="ALAP"):
        compute_cpm(s)


def test_constraint_without_date_is_refused() -> None:
    s = _sched([_task(1, 1, constraint_type=ConstraintType.SNET)])
    with pytest.raises(CPMError, match="no constraint_date"):
        compute_cpm(s)


def test_cycle_is_refused() -> None:
    s = _sched([_task(1, 1), _task(2, 1)], [_rel(1, 2), _rel(2, 1)])
    with pytest.raises(CPMError, match="cycle"):
        compute_cpm(s)


def test_empty_schedule() -> None:
    s = _sched([Task(unique_id=1, name="root", duration_minutes=0, is_summary=True)])
    r = compute_cpm(s)
    assert r.project_finish == 0
    assert r.critical_path == ()
    assert r.timings == {}


# --- calendar offset helpers ------------------------------------------------------


def test_offset_round_trip_skips_weekend() -> None:
    # 5 working days from Monday lands on the following Friday's end-of-day.
    target = offset_to_datetime(MON, 5 * DAY, CAL)
    assert datetime_to_offset(MON, target, CAL) == 5 * DAY
    # 1 working day past Friday rolls over the weekend to the next Monday.
    next_day = offset_to_datetime(MON, 5 * DAY + 1, CAL)
    assert next_day.weekday() == 0  # Monday


def test_offset_to_datetime_rejects_negative() -> None:
    with pytest.raises(ValueError, match="must be >= 0"):
        offset_to_datetime(MON, -1, CAL)


def test_offset_to_datetime_advances_nonworking_start() -> None:
    saturday = dt.datetime(2025, 1, 11, 8, 0)  # Sat — caller passed a non-working start
    landed = offset_to_datetime(saturday, 1 * DAY, CAL)
    assert landed.weekday() == 0  # advanced to Monday before counting work time


def test_datetime_to_offset_negative_for_earlier_target() -> None:
    earlier = MON - dt.timedelta(days=7)
    assert datetime_to_offset(MON, earlier, CAL) == -5 * DAY  # one work-week earlier


def test_datetime_to_offset_nonworking_day_has_no_intraday() -> None:
    saturday = dt.datetime(2025, 1, 11, 12, 0)  # Sat — not a working day
    # whole working days Mon..Fri = 5, no intraday term added for the weekend target
    assert datetime_to_offset(MON, saturday, CAL) == 5 * DAY
