"""DCMA-audit tests — golden P5 audit + synthetic structure / citation checks (§6.E)."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.dcma_audit import Citation, audit_schedule
from schedule_forensics.engine.metrics import CheckStatus
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def test_citation_str_format() -> None:
    c = Citation(source_file="Project5.mspdi.xml", unique_id=143, task_name="Obtain CofO")
    assert str(c) == "Obtain CofO (UID 143, Project5.mspdi.xml)"
    assert "uploaded schedule" in str(Citation(None, 1, "A"))


def test_golden_audit_project5(golden_project5: Schedule) -> None:
    audit = audit_schedule(golden_project5)
    assert audit.source_file == "Project5.mspdi.xml"
    assert len(audit.checks) == 16  # 14 checks, DCMA-04 split into FS / SS-FF / SF rows
    assert audit.passed + audit.failed + audit.not_applicable == 16
    failed_ids = {c.metric_id for c in audit.failed_checks}
    assert {"DCMA06", "DCMA11", "DCMA14"} <= failed_ids  # known P5 failures

    # every failed check carries a suggested improvement and (where it has offenders) citations
    missed = next(c for c in audit.checks if c.metric_id == "DCMA11")
    assert missed.status is CheckStatus.FAIL
    assert missed.suggested_improvement and "missed" in missed.suggested_improvement.lower()
    assert len(missed.citations) == missed.count
    assert all(c.source_file == "Project5.mspdi.xml" and c.task_name for c in missed.citations)

    # a passing check reads the pass note and cites nothing
    passing = next(c for c in audit.checks if c.status is CheckStatus.PASS)
    assert "no action" in passing.suggested_improvement.lower()


def test_audit_clean_schedule_mostly_passes() -> None:
    # a tidy FS chain with a resource and no constraints: the structural checks pass
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=DAY, resource_names=("Crew",)),
        Task(unique_id=2, name="B", duration_minutes=DAY, resource_names=("Crew",)),
        Task(unique_id=3, name="C", duration_minutes=DAY, resource_names=("Crew",)),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
    ]
    audit = audit_schedule(
        Schedule(name="clean", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    )
    failed = {c.metric_id for c in audit.failed_checks}
    # no leads, lags, hard constraints, negative float, high duration in this tidy net
    assert "DCMA02" not in failed and "DCMA05" not in failed and "DCMA07" not in failed
