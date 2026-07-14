"""An INACTIVE task must not inflate the project baseline finish (the CPLI basis).

MS Project excludes inactive tasks from every rollup, and so does the rest of this engine
(CPM / metrics / driving-slack all drop ``not is_active`` — ADR-0128). The imported project
baseline finish must agree: a late baseline finish carried on an inactive row is ignored."""

from __future__ import annotations

from schedule_forensics.importers.mspdi import parse_mspdi_text

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _task(uid: int, bl_finish: str, *, active: bool = True) -> str:
    active_el = "" if active else "<Active>0</Active>"
    return (
        f"<Task><UID>{uid}</UID><Name>T{uid}</Name><Duration>PT8H0M0S</Duration>{active_el}"
        f"<Baseline><Number>0</Number><Finish>{bl_finish}</Finish></Baseline></Task>"
    )


def test_inactive_task_baseline_finish_excluded_from_project_baseline() -> None:
    doc = (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate><Tasks>"
        + _task(1, "2025-03-01T17:00:00", active=True)
        + _task(2, "2030-12-31T17:00:00", active=False)  # far-future baseline on an INACTIVE row
        + "</Tasks></Project>"
    )
    sch = parse_mspdi_text(doc)
    assert sch.baseline_finish is not None
    # the project baseline finish is the ACTIVE task's (2025), NOT the inactive task's 2030
    assert sch.baseline_finish.year == 2025


def test_active_task_baseline_finish_still_counts() -> None:
    doc = (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate><Tasks>"
        + _task(1, "2025-03-01T17:00:00", active=True)
        + _task(2, "2027-09-01T17:00:00", active=True)  # later, but ACTIVE → it defines the finish
        + "</Tasks></Project>"
    )
    sch = parse_mspdi_text(doc)
    assert sch.baseline_finish is not None and sch.baseline_finish.year == 2027
