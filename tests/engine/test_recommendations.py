"""Recommendation-engine tests — golden P5-vs-P2 findings + synthetic cases (§6.E).

Asserts the cited risk/opportunity/concern set, that every finding carries a citation
(file + UID + task), and the severity ordering.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from schedule_forensics.engine.recommendations import Category, Severity, recommend
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def test_golden_recommendations_p5_vs_p2(golden: Callable[[str], Schedule]) -> None:
    findings = recommend(golden("Project5"), golden("Project2"), target_uid=143)
    by_id = {f.metric_id: f for f in findings}

    # version-pair forensic signals are present and cited
    assert "HSD10" in by_id  # net finish impact slip
    assert by_id["HSD10"].category is Category.CONCERN and by_id["HSD10"].severity is Severity.HIGH
    assert "99" in by_id["HSD10"].title  # -99 day slip surfaced
    assert by_id["HSD10"].citations  # cites the finish-controlling activity
    assert by_id["SN05"].category is Category.RISK  # finish slips
    assert by_id["not_completed"].severity is Severity.HIGH

    # driving-path opportunity to the focus UID
    assert by_id["driving_path"].category is Category.OPPORTUNITY
    assert len(by_id["driving_path"].citations) == 36

    # EVERY finding is cited (file + UID + task) — §6.E
    assert findings and all(f.citations for f in findings)
    for f in findings:
        for c in f.citations:
            assert c.source_file == "Project5.mspdi.xml" and c.unique_id > 0 and c.task_name

    # ordered most-severe first
    order = [Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    ranks = [order.index(f.severity) for f in findings]
    assert ranks == sorted(ranks)


def test_recommend_single_schedule_has_no_change_or_path_findings(
    golden: Callable[[str], Schedule],
) -> None:
    findings = recommend(golden("Project5"))  # no prior, no target_uid
    ids = {f.metric_id for f in findings}
    assert "HSD10" not in ids and "SN05" not in ids and "driving_path" not in ids
    # still surfaces DCMA + compliance concerns, all cited
    assert ids and all(f.citations for f in findings)


def test_no_slip_yields_no_net_impact_finding() -> None:
    # current finishes earlier than prior -> positive net impact -> no slip concern
    prior = Schedule(
        name="p",
        project_start=MON,
        status_date=dt.datetime(2025, 1, 20, 17, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=10 * DAY),),
    )
    current = Schedule(
        name="c",
        project_start=MON,
        status_date=dt.datetime(2025, 1, 20, 17, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=5 * DAY),),
    )
    assert not any(f.metric_id == "HSD10" for f in recommend(current, prior))


def test_driving_path_opportunity_and_missing_target() -> None:
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=2, name="B", duration_minutes=3 * DAY),
        Task(unique_id=3, name="focus", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=3),
    ]
    s = Schedule(name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))
    opp = [f for f in recommend(s, target_uid=3) if f.metric_id == "driving_path"]
    assert opp and opp[0].category is Category.OPPORTUNITY and opp[0].citations
    # an unknown target UID yields no driving-path finding (no crash)
    assert not any(f.metric_id == "driving_path" for f in recommend(s, target_uid=999))


def test_summary_only_schedule_yields_cited_findings_never_empty() -> None:
    # a summary-only template solves to an empty CPM timing set; any finding it produces
    # must still cite something (the terminal fallback: the first task rows) — an
    # offender-less finding once 500'd every page via the §6 citation gate
    s = Schedule(
        name="template",
        project_start=MON,
        tasks=(Task(unique_id=0, name="Root", duration_minutes=0, is_summary=True),),
    )
    for finding in recommend(s):
        assert finding.citations, finding.metric_id


def test_summary_target_uid_is_ignored_not_a_keyerror(
    golden: Callable[[str], Schedule],
) -> None:
    # UID 0 is MS Project's project-summary row: present in tasks_by_id but absent from
    # the logic network — recommend() must skip the trace, not raise KeyError
    findings = recommend(golden("Project2"), target_uid=0)
    assert not any(f.metric_id == "driving_path" for f in findings)
