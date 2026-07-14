"""v4 Feature 2 lazy summary tier: a VersionSummary must equal what the full analysis reports."""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics import CheckStatus
from schedule_forensics.engine.metrics.margin import compute_margin
from schedule_forensics.engine.summary import VersionSummary, compute_summary
from schedule_forensics.importers.mspdi import parse_mspdi_text

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def test_summary_equals_the_full_analysis() -> None:
    sch = parse_mspdi_text((GOLDEN / "Project5.mspdi.xml").read_bytes().decode("utf-8-sig"))
    summary = compute_summary(sch)

    cpm = compute_cpm(sch)
    audit = audit_schedule(sch, cpm)
    assert summary.unsolvable is False
    assert (
        summary.finish_iso
        == offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar)
        .date()
        .isoformat()
    )
    assert summary.effective_margin_days == compute_margin(sch, cpm).effective_margin_days
    assert summary.dcma_pass == sum(1 for c in audit.checks if c.status is CheckStatus.PASS)
    assert summary.dcma_fail == sum(1 for c in audit.checks if c.status is CheckStatus.FAIL)
    assert summary.task_count == len(sch.tasks)
    assert summary.status_date_iso == (
        sch.status_date.date().isoformat() if sch.status_date is not None else None
    )


def test_summary_json_round_trips() -> None:
    sch = parse_mspdi_text((GOLDEN / "Project2.mspdi.xml").read_bytes().decode("utf-8-sig"))
    summary = compute_summary(sch)
    assert VersionSummary.from_json(summary.to_json()) == summary  # cache format is lossless


def test_unsolvable_network_summarizes_without_raising() -> None:
    # a two-task logic loop: A → B and B → A cannot be scheduled
    ns = 'xmlns="http://schemas.microsoft.com/project"'
    loop = (
        f"<Project {ns}><StartDate>2025-01-06T08:00:00</StartDate><Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>2</PredecessorUID></PredecessorLink></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID></PredecessorLink></Task>"
        "</Tasks></Project>"
    )
    summary = compute_summary(parse_mspdi_text(loop))
    assert summary.unsolvable is True
    assert summary.finish_iso is None and summary.effective_margin_days is None
    assert summary.dcma_pass == 0 and summary.dcma_fail == 0
