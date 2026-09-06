"""MAN-02 / MAN-03 (WP6b, ADR-0467): the resource-booking finding cites the file the activity is
IN, and an absent remaining-work figure is not described as work burned down.

MAN-02: ``_resource_assignment_edits`` cited every booking to the CURRENT file, including a
booking whose activity exists only in the PRIOR version (deleted since) — a citation naming a
file the activity is not in. MAN-03: ``assignment_change_rows`` compares remaining work with
``(before or 0) != (after or 0)``, so a booking whose prior export carried NO remaining-work
figure and whose current one does was counted among the bookings that "only burned down
remaining work with progress" — a sentence about work that was never measured.

Red-first (2026-09-06): UID 7's citation read ``current.xml``; the None→240 booking was counted
as burn-down.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.manipulation import (
    _resource_assignment_edits,
    assignment_change_rows,
)
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)
CREW = (Resource(unique_id=9, name="Crew"),)


def _task(uid: int, name: str, remaining: int | None, *resources: int) -> Task:
    return Task(
        unique_id=uid,
        name=name,
        duration_minutes=480,
        resource_assignments=tuple(
            Assignment(resource_id=r, work_minutes=480, remaining_work_minutes=remaining)
            for r in resources
        ),
    )


def _schedule(file: str, *tasks: Task) -> Schedule:
    return Schedule(name=file, source_file=file, project_start=MON, resources=CREW, tasks=tasks)


def test_a_booking_on_an_activity_deleted_since_is_cited_to_the_prior_file() -> None:
    prior = _schedule("prior.xml", _task(1, "Keep", 480, 9), _task(7, "Deleted later", 480, 9))
    current = _schedule("current.xml", _task(1, "Keep", 480, 9))
    rows = assignment_change_rows(prior, current)
    assert [(r.task_uid, r.kind) for r in rows] == [(7, "removed")]
    (finding,) = _resource_assignment_edits(prior, current, current.source_file)
    (cite,) = finding.citations
    assert (cite.unique_id, cite.source_file) == (7, "prior.xml"), cite
    assert "absent from the current version" in finding.detail


def test_a_booking_still_present_is_cited_to_the_current_file() -> None:
    prior = _schedule("prior.xml", _task(1, "Keep", 480, 9))
    current = _schedule("current.xml", _task(1, "Keep", 480, 9), _task(2, "New booking", 480, 9))
    (finding,) = _resource_assignment_edits(prior, current, current.source_file)
    assert [(c.unique_id, c.source_file) for c in finding.citations] == [(2, "current.xml")]
    assert "absent from the current version" not in finding.detail


def test_a_remaining_work_figure_that_appears_is_not_called_burn_down() -> None:
    # task 1: the prior export carried no remaining-work figure, the current one does (240);
    # task 2: a real plan edit (a booking added) so the finding fires at all
    prior = _schedule("prior.xml", _task(1, "Keep", None, 9), _task(2, "Edited", 480))
    current = _schedule("current.xml", _task(1, "Keep", 240, 9), _task(2, "Edited", 480, 9))
    rows = {(r.task_uid, r.kind): r for r in assignment_change_rows(prior, current)}
    assert rows[(1, "remaining_work")].before_minutes is None  # the None side is kept as None
    (finding,) = _resource_assignment_edits(prior, current, current.source_file)
    assert "only burned down remaining work" not in finding.detail, finding.detail
    assert "remaining-work figure" in finding.detail, finding.detail


def test_a_real_burn_down_is_still_disclosed_as_statusing() -> None:
    prior = _schedule("prior.xml", _task(1, "Keep", 480, 9), _task(2, "Edited", 480))
    current = _schedule("current.xml", _task(1, "Keep", 240, 9), _task(2, "Edited", 480, 9))
    (finding,) = _resource_assignment_edits(prior, current, current.source_file)
    assert "1 booking(s) only burned down remaining work" in finding.detail, finding.detail
