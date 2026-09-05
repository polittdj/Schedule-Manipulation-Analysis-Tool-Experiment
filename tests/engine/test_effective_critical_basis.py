"""MAN-01 (WP6, ADR-0463): the critical-and-incomplete set follows the source tool's flag.

``change_metrics`` (Acumen §E SN03/SN04) and ``manipulation`` (deleted/deactivated-task severity,
the trend's critical count) each kept a private ``_critical_incomplete`` on pure-logic
``timing.is_critical`` while the rest of the engine scores Critical through
``_common.is_effective_critical`` — MS Project's stored, progress-aware flag when the file carries
it (Acumen's own basis, ADR-0080/0150). Measured on the golden P2 -> P5 pair: on the effective basis
the No-Longer-Critical membership becomes UID-exact with the Fuse export (the documented 96 <-> 99
swap disappears), counts unchanged everywhere. One shared helper now serves both.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.metrics.change_metrics import compute_change_metrics
from schedule_forensics.engine.recommendations import Severity
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)
DAY = 480


def _network(flags: dict[int, bool | None], *, drop: int | None = None) -> Schedule:
    """1 (3d) -> 2 (1d) is the logic-critical chain; 3 (1d) runs parallel with 3 days of float.
    ``flags`` is the file's stored Critical flag per task (None = the file carried none)."""
    tasks = [
        Task(unique_id=1, name="one", duration_minutes=3 * DAY, stored_is_critical=flags.get(1)),
        Task(unique_id=2, name="two", duration_minutes=DAY, stored_is_critical=flags.get(2)),
        Task(unique_id=3, name="three", duration_minutes=DAY, stored_is_critical=flags.get(3)),
    ]
    return Schedule(
        name="S",
        project_start=MON,
        tasks=tuple(t for t in tasks if t.unique_id != drop),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def test_change_metrics_follow_the_stored_flag_over_pure_logic() -> None:
    prior = _network({})  # no flags: pure logic says {1, 2}
    current = _network({1: True, 2: False, 3: True})  # the scheduler's call: {1, 3}
    ch = compute_change_metrics(current, prior)
    assert list(ch["new_critical"].offender_uids) == [3]
    assert list(ch["no_longer_critical"].offender_uids) == [2]


def test_a_deleted_task_the_file_flagged_critical_is_a_high_severity_finding() -> None:
    prior = _network({3: True})  # pure logic gives 3 three days of float; the file says Critical
    current = _network({}, drop=3)
    (deleted,) = [
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_DELETED_TASK"
    ]
    assert deleted.severity is Severity.HIGH


def test_the_trend_critical_count_follows_the_stored_flag() -> None:
    (point,) = trend_across_versions([_network({1: False, 2: False, 3: True})])
    assert point.critical == 1


def test_a_completed_task_is_never_counted_even_when_flagged() -> None:
    flagged_done = _network({3: True}).model_copy(
        update={
            "tasks": tuple(
                t.model_copy(update={"percent_complete": 100.0}) if t.unique_id == 3 else t
                for t in _network({3: True}).tasks
            )
        }
    )
    (point,) = trend_across_versions([flagged_done])
    assert point.critical == 2  # 1 and 2 by pure logic (no flag); 3 is done
