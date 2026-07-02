"""Residual manipulation-detector regressions (audit F-13 / NEW-2, ADR-0143)."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_START = dt.datetime(2026, 1, 5, 8, 0)


def _sched(name: str, tasks: tuple[Task, ...], cal: Calendar | None = None) -> Schedule:
    kwargs = {"name": name, "project_start": _START, "tasks": tasks}
    if cal is not None:
        kwargs["calendar"] = cal
    return Schedule(**kwargs)


def test_deactivation_gets_its_own_signal_high_when_critical_f13() -> None:
    """F-13: flipping a critical task inactive removes it from the CPM network — functionally a
    deletion that never appeared in the deleted-task count. It now fires MANIP_DEACTIVATED_TASK,
    HIGH when the task was on the prior critical path."""
    prior = _sched(
        "v1",
        (
            Task(unique_id=1, name="Long pole", duration_minutes=4800),
            Task(unique_id=2, name="Short", duration_minutes=480),
        ),
    )
    current = _sched(
        "v2",
        (
            Task(unique_id=1, name="Long pole", duration_minutes=4800, is_active=False),
            Task(unique_id=2, name="Short", duration_minutes=480),
        ),
    )
    findings = detect_manipulation(current, prior)
    hits = [f for f in findings if f.metric_id == "MANIP_DEACTIVATED_TASK"]
    assert len(hits) == 1
    assert str(hits[0].severity) == "HIGH"  # UID 1 was the prior critical path
    assert hits[0].citations and hits[0].citations[0].unique_id == 1

    # re-activating (False -> True) is NOT flagged (only the masking direction)
    findings_back = detect_manipulation(prior, current)
    assert not [f for f in findings_back if f.metric_id == "MANIP_DEACTIVATED_TASK"]


def test_net_zero_weekday_swap_is_not_calendar_loosening_new2() -> None:
    """NEW-2: Mon-Fri -> Tue-Sat adds a weekday and removes one — zero net working time. The
    loosening detector must stay silent; a genuine 5->6-day week must still fire."""
    five = Calendar(uid=0, name="FiveDay", work_weekdays=(0, 1, 2, 3, 4))
    swapped = Calendar(uid=0, name="FiveDay", work_weekdays=(1, 2, 3, 4, 5))
    six = Calendar(uid=0, name="SixDay", work_weekdays=(0, 1, 2, 3, 4, 5))
    tasks = (Task(unique_id=1, name="T", duration_minutes=480),)

    silent = detect_manipulation(_sched("v2", tasks, swapped), _sched("v1", tasks, five))
    assert not [f for f in silent if f.metric_id == "MANIP_CALENDAR_LOOSENED"]

    fired = detect_manipulation(_sched("v2", tasks, six), _sched("v1", tasks, five))
    hits = [f for f in fired if f.metric_id == "MANIP_CALENDAR_LOOSENED"]
    assert len(hits) == 1 and "working week grew 5→6" in hits[0].detail
