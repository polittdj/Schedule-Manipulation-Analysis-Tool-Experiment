"""The Working-calendar panel discloses its single-calendar base-CPM basis (#26).

When a file assigns some activities their own calendar, the base CPM still models only the single
project calendar (ADR-0028). The panel must SAY so — otherwise the analyst reads the one
project-calendar row as the whole time basis. Single-calendar files stay silent (no cry-wolf).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import _calendar_panel

_DAY = 480


def _mixed() -> Schedule:
    cal24 = Calendar(
        uid=10, name="24 Hours", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
    )
    tasks = (
        Task(unique_id=1, name="Mon-Fri task", duration_minutes=_DAY),
        Task(unique_id=2, name="Round-the-clock task", duration_minutes=_DAY, calendar_uid=10),
    )
    return Schedule(
        name="mixed",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard"),
        calendars=(cal24,),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _single() -> Schedule:
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=_DAY),
        Task(unique_id=2, name="B", duration_minutes=_DAY),
    )
    return Schedule(
        name="plain",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard"),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def test_multi_calendar_panel_discloses_the_single_calendar_basis() -> None:
    html = _calendar_panel(_mixed())
    assert "Working calendar" in html  # still the same panel
    assert 'class="notice info"' in html  # the disclosure banner is present
    assert "24 Hours" in html  # names the off-project calendar
    assert "single-calendar approximation" in html  # states the base-CPM limitation
    assert "ADR-0028" in html and "ADR-0118" in html  # cites both bases (base CPM vs SSI path)


def test_single_calendar_panel_is_silent() -> None:
    html = _calendar_panel(_single())
    assert "Working calendar" in html  # the panel still renders
    assert 'class="notice info"' not in html  # ...but NO disclosure (nothing to disclose)
    assert "single-calendar approximation" not in html
