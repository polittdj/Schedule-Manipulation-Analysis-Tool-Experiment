"""Driving-slack day-grid regression (ADR-0045).

SSI computes driving slack on a WHOLE-WORKING-DAY grid where each activity occupies a whole
number of working days. Real stored dates carry ragged times of day (activities finishing at
noon, afternoon-shift starts), so an activity's working span comes out a few minutes off a
whole day. Left raw, that sub-day raggedness ACCUMULATES through the backward pass's span
subtraction and can tip a long driving chain's whole-day slack across a boundary, so a
genuine 0-day SSI path reads as 1-day secondary (the operator's "Large Test File"). The fix
snaps each activity's SPAN to the nearest whole working day, stopping the accumulation while
leaving each activity's own sub-day phase intact (so it still floors onto the right SSI day).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.driving_slack import PathTier, compute_driving_slack
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

PER_DAY = 480


def _task(uid: int, start: dt.datetime, finish: dt.datetime, dur: int = PER_DAY) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", start=start, finish=finish, duration_minutes=dur)


def test_ragged_span_chain_stays_on_the_driving_path() -> None:
    """A day-contiguous chain with ragged times must read DRIVING, not tip to secondary.

    A finishes Tue 12:00 and B starts Tue 14:00 (same working day) into the target milestone:
    SSI's whole-day grid reads the chain as 0-day driving. Raw minute offsets would carry the
    ragged spans; the span-snap keeps each activity's sub-day phase, which still floors onto
    SSI's day 0 — so the whole chain reads DRIVING.
    """
    mon = dt.datetime(2025, 1, 6, 8, 0)  # a Monday
    a = _task(1, dt.datetime(2025, 1, 6, 8, 0), dt.datetime(2025, 1, 7, 12, 0))  # Mon -> Tue 12:00
    b = _task(2, dt.datetime(2025, 1, 7, 14, 0), dt.datetime(2025, 1, 8, 9, 0))  # Tue 14:00 -> Wed
    target = _task(3, dt.datetime(2025, 1, 8, 9, 0), dt.datetime(2025, 1, 8, 9, 0), dur=0)
    sch = Schedule(
        name="ragged",
        project_start=mon,
        tasks=(a, b, target),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )
    res = compute_driving_slack(sch, 3)
    for uid in (1, 2, 3):
        assert res[uid].on_driving_path, (uid, res[uid].driving_slack_minutes)
        assert res[uid].tier is PathTier.DRIVING
        assert res[uid].driving_slack_minutes // PER_DAY == 0  # sub-day phase floors onto day 0


def test_genuine_multiday_slack_survives_the_day_snap() -> None:
    # a side activity stored to finish a clean 3 working days before the target needs it keeps
    # its real 3-day driving slack (the snap removes only sub-day raggedness, not real slack)
    mon = dt.datetime(2025, 1, 6, 8, 0)
    driver = _task(1, mon, dt.datetime(2025, 1, 13, 8, 0), dur=5 * PER_DAY)
    side = _task(2, mon, dt.datetime(2025, 1, 8, 8, 0), dur=2 * PER_DAY)
    target = _task(3, dt.datetime(2025, 1, 13, 8, 0), dt.datetime(2025, 1, 13, 8, 0), dur=0)
    sch = Schedule(
        name="side",
        project_start=mon,
        tasks=(driver, side, target),
        relationships=(
            Relationship(predecessor_id=1, successor_id=3),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )
    res = compute_driving_slack(sch, 3)
    assert res[1].driving_slack_minutes == 0 and res[1].tier is PathTier.DRIVING  # the driver
    assert res[2].driving_slack_minutes == 3 * PER_DAY  # three clean working days
    assert float(res[2].driving_slack_days) == 3.0 and res[2].tier is PathTier.SECONDARY


def test_golden_driving_slack_unchanged(golden_project5: Schedule) -> None:
    # the curated goldens are day-aligned, so the span-snap is a no-op (whole-day spans round
    # to themselves); the driving path to a known late milestone is unchanged (parity-safe).
    res = compute_driving_slack(golden_project5, 143)
    assert res[143].driving_slack_minutes == 0  # the target is always on its own path
    assert res[143].on_driving_path and res[143].tier is PathTier.DRIVING
