"""Path-evolution attribution coverage — driving-chain dedup, largest-slip ranking, the
constraint-removed leave reason, and the finish-delta-absent gained-float phrasing.

Targets the still-uncovered branches in :mod:`engine.path_evolution`: ``_driving_slip``
skipping an already-seen ancestor and a non-slipping predecessor; ``_largest_slip``
keeping the first of two positive slips; ``_classify_entered`` falling through to the
generic note when nothing slipped; and ``_classify_left`` reporting a removed hard
constraint and the gained-float detail when only the activity's own move is known.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.path_evolution import (
    _classify_entered,
    _classify_left,
    _driving_slip,
    _largest_slip,
    _links_touching,
    _PairContext,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=())


# --- _driving_slip: dedup an already-seen ancestor; skip a non-slipping predecessor ----------


def test_driving_slip_dedups_shared_ancestor_and_skips_non_slipping() -> None:
    """A diamond chain (UID 4 ← {2,3} ← 1) reaches the shared ancestor 1 twice — the second
    visit hits the ``seen`` guard. UID 3 has a non-positive slip and is skipped; UID 2's
    positive slip is the answer. (path_evolution.py 176 + branch 180->174.)"""
    preds = {4: (2, 3), 2: (1,), 3: (1,)}
    slip = {1: 0, 2: 5, 3: -2, 4: 0}
    result = _driving_slip(4, preds, slip)
    # only UID 2 slipped positively; 1 (visited twice) and 3 (negative slip) contribute nothing.
    assert result == (5, 2)


def test_driving_slip_returns_none_when_no_predecessor_slipped() -> None:
    """No upstream activity finished later → no driving slip to attribute."""
    assert _driving_slip(2, {2: (1,)}, {1: 0, 2: 0}) is None


# --- _largest_slip: keep the first of two positive slips when the later one is smaller --------


def test_largest_slip_keeps_the_larger_earlier_value() -> None:
    """Iterating a second, smaller positive slip leaves ``best`` unchanged (branch 191->188)."""
    # insertion order puts the larger (7) first; the later 3 is positive but not larger.
    assert _largest_slip({9: 7, 8: 3}, exclude=99) == (7, 9)


# --- _classify_entered: fall through to the generic note when nothing slipped (241->247) -----


def test_entered_slack_consumed_is_generic_when_no_slip_anywhere() -> None:
    """With a context but zero positive slips, neither the driving-chain nor the largest-slip
    naming applies — the note stays the honest generic phrasing (branch 241->247)."""
    b = Task(unique_id=2, name="B", duration_minutes=DAY)
    sch = _sched([b])
    ctx = _PairContext(slip_days={2: 0}, cur_preds={}, finish_delta_days=0)
    pc = _classify_entered(2, sch, sch, _links_touching(sch), _links_touching(sch), ctx)
    assert pc.reason == "slack_consumed"
    assert pc.detail == (
        "Became critical as a slip elsewhere consumed its float (this activity is unchanged)."
    )


# --- _classify_left: removed hard constraint (292) -------------------------------------------


def test_left_reason_hard_constraint_removed() -> None:
    """An activity leaves the path because its hard constraint was dropped (duration / logic
    unchanged) — reason ``constraint``, detail naming the removed type (path_evolution.py 292)."""
    prior = _sched(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                constraint_type=ConstraintType.FNLT,
                constraint_date=MON,
            )
        ]
    )
    cur = _sched([Task(unique_id=1, name="A", duration_minutes=DAY)])
    pc = _classify_left(1, cur, prior, _links_touching(cur), _links_touching(prior))
    assert pc.reason == "constraint"
    assert pc.detail == "Hard constraint removed (FNLT)."


# --- _classify_left: gained-float detail with own move but no finish delta (306-307) ---------


def test_left_gained_float_detail_with_only_own_movement() -> None:
    """When the project finish delta is unknown but the activity's own slip is, the gained-float
    note quantifies just its own forecast-finish move (path_evolution.py 306-307)."""
    a = Task(unique_id=1, name="A", duration_minutes=DAY)
    ctx = _PairContext(slip_days={1: 4}, cur_preds={}, finish_delta_days=None)
    sch = _sched([a])
    pc = _classify_left(1, sch, sch, _links_touching(sch), _links_touching(sch), ctx)
    assert pc.reason == "gained_float"
    assert pc.detail == "Unchanged here — off the longest path now (its forecast finish moved +4d)."
    assert "project finish" not in pc.detail  # the finish-delta clause is intentionally absent
