"""Manipulation-detection tests — golden (no false positives) + synthetic signal cases (§6.D)."""

from __future__ import annotations

import datetime as dt
import itertools

from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.recommendations import Severity
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _s(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


def _chain(durations: dict[int, int], **task_kw: object) -> Schedule:
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=d) for u, d in durations.items()]
    uids = list(durations)
    rels = [Relationship(predecessor_id=a, successor_id=b) for a, b in itertools.pairwise(uids)]
    return _s(tasks, rels, **task_kw)


def test_golden_p2_to_p5_has_no_false_positive_manipulation(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    # The authoritative Project5 (ADR-0112) has 2 removed logic links vs Project2
    # (106→135 and 113→138), so the detector correctly raises one MANIP_DELETED_LOGIC finding.
    # Baselines unchanged, no deleted tasks, no edited actuals, no shortened durations.
    findings = detect_manipulation(golden_project5, golden_project2)
    assert len(findings) == 1
    assert findings[0].metric_id == "MANIP_DELETED_LOGIC"


def test_detect_deleted_task_on_critical_path() -> None:
    prior = _chain({1: DAY, 2: 2 * DAY, 3: DAY})  # 1->2->3, all critical
    current = _s(
        [
            Task(unique_id=1, name="T1", duration_minutes=DAY),
            Task(unique_id=3, name="T3", duration_minutes=DAY),
        ]
    )  # task 2 (critical) removed, along with its links
    findings = detect_manipulation(current, prior)
    ids = {f.metric_id for f in findings}
    assert "MANIP_DELETED_TASK" in ids and "MANIP_DELETED_LOGIC" in ids
    deleted = next(f for f in findings if f.metric_id == "MANIP_DELETED_TASK")
    assert deleted.severity is Severity.HIGH  # the deleted task was on the prior critical path
    assert any(c.unique_id == 2 for c in deleted.citations)


def test_deleted_logic_citations_carry_the_prior_file() -> None:
    # §6 contract: every citation names its source file — deleted-logic findings cite the prior.
    prior = _chain({1: DAY, 2: 2 * DAY, 3: DAY}, source_file="prior.mpp")
    current = _s(
        [
            Task(unique_id=1, name="T1", duration_minutes=DAY),
            Task(unique_id=3, name="T3", duration_minutes=DAY),
        ]
    )
    logic = next(
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_DELETED_LOGIC"
    )
    assert logic.citations and all(c.source_file == "prior.mpp" for c in logic.citations)


def test_detect_shortened_duration_on_incomplete() -> None:
    prior = _s([Task(unique_id=1, name="A", duration_minutes=10 * DAY)])
    current = _s([Task(unique_id=1, name="A", duration_minutes=4 * DAY, percent_complete=20.0)])
    findings = detect_manipulation(current, prior)
    f = next(f for f in findings if f.metric_id == "MANIP_SHORTENED_DURATION")
    assert f.citations[0].unique_id == 1 and f.severity is Severity.MEDIUM


def test_detect_baseline_date_change() -> None:
    prior = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                baseline_finish=dt.datetime(2025, 2, 1, 17, 0),
            )
        ]
    )
    current = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                baseline_finish=dt.datetime(2025, 4, 1, 17, 0),
            )
        ]
    )
    f = next(
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_BASELINE_CHANGE"
    )
    assert f.severity is Severity.HIGH and f.citations[0].unique_id == 1


def test_detect_edited_actual_but_not_newly_set() -> None:
    # newly-set actual (None -> date) is normal progress and must NOT flag
    prior_new = _s([Task(unique_id=1, name="A", duration_minutes=DAY, percent_complete=0.0)])
    current_new = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 7, 17, 0),
            )
        ]
    )
    assert not any(
        f.metric_id == "MANIP_ACTUAL_CHANGE" for f in detect_manipulation(current_new, prior_new)
    )
    # an EDITED actual (date -> different date) IS the 06A504* signal
    prior_edit = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 7, 17, 0),
            )
        ]
    )
    current_edit = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 14, 17, 0),
            )
        ]
    )
    f = next(
        f
        for f in detect_manipulation(current_edit, prior_edit)
        if f.metric_id == "MANIP_ACTUAL_CHANGE"
    )
    assert f.severity is Severity.HIGH and f.citations[0].unique_id == 1


def test_all_manipulation_findings_are_cited() -> None:
    prior = _chain({1: 5 * DAY, 2: 5 * DAY}, status_date=dt.datetime(2025, 1, 20, 17, 0))
    current = _s(
        [
            Task(
                unique_id=1,
                name="T1",
                duration_minutes=2 * DAY,
                percent_complete=10.0,
                baseline_finish=dt.datetime(2025, 4, 1, 17, 0),
            )
        ],
        status_date=dt.datetime(2025, 1, 20, 17, 0),
    )  # task 2 deleted, task 1 shortened + baseline moved
    findings = detect_manipulation(current, prior)
    assert findings and all(f.citations for f in findings)


def test_trend_across_versions_orders_and_counts(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    trend = trend_across_versions([golden_project2, golden_project5])
    assert len(trend) == 2
    assert trend[0].version_index == 0 and trend[1].version_index == 1
    assert trend[0].completed == 20 and trend[1].completed == 27  # progress between snapshots
    assert trend[0].critical == 41 and trend[1].critical == 4
    assert trend[1].project_finish > trend[0].project_finish  # the finish slipped later


def test_detect_erased_actual_date() -> None:
    # date -> None (progress un-statused) is the classic history rewrite and must flag —
    # it used to read as normal statusing because only date -> date edits were checked
    prior = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_start=dt.datetime(2025, 1, 6, 8, 0),
                actual_finish=dt.datetime(2025, 1, 7, 17, 0),
            )
        ]
    )
    current = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=50.0,
                actual_start=dt.datetime(2025, 1, 6, 8, 0),
            )
        ]
    )
    findings = [
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_ACTUAL_ERASED"
    ]
    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert findings[0].citations[0].unique_id == 1
