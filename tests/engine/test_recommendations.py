"""Recommendation-engine tests — golden P5-vs-P2 findings + synthetic cases (§6.E).

Asserts the cited risk/opportunity/concern set, that every finding carries a citation
(file + UID + task), and the severity ordering.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from schedule_forensics.engine.recommendations import (
    Category,
    Finding,
    Likelihood,
    Severity,
    impact_rank,
    likelihood_rank,
    recommend,
    severity_rank,
)
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


def test_logic_on_summary_tasks_is_flagged_and_cited() -> None:
    # ADR-0043: a predecessor on a summary is honored (children pushed) AND flagged.
    tasks = (
        Task(unique_id=1, name="P", wbs="2.1", duration_minutes=5 * DAY),
        Task(unique_id=10, name="Phase", wbs="1", is_summary=True, duration_minutes=0),
        Task(unique_id=11, name="Child", wbs="1.1", duration_minutes=DAY),
    )
    rels = (Relationship(predecessor_id=1, successor_id=10),)  # logic on summary 10
    findings = recommend(Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels))
    flagged = [f for f in findings if f.metric_id == "logic_on_summary_tasks"]
    assert len(flagged) == 1
    assert "summary task" in flagged[0].title and flagged[0].severity == Severity.MEDIUM
    assert [c.unique_id for c in flagged[0].citations] == [10]  # the offending summary, cited


def test_no_summary_logic_no_flag(golden: Callable[[str], Schedule]) -> None:
    # the curated goldens carry no logic on summaries -> the finding never fires
    findings = recommend(golden("Project5"))
    assert not any(f.metric_id == "logic_on_summary_tasks" for f in findings)


def test_summary_target_uid_is_ignored_not_a_keyerror(
    golden: Callable[[str], Schedule],
) -> None:
    # UID 0 is MS Project's project-summary row: present in tasks_by_id but absent from
    # the logic network — recommend() must skip the trace, not raise KeyError
    findings = recommend(golden("Project2"), target_uid=0)
    assert not any(f.metric_id == "driving_path" for f in findings)


# --- quantified risk scoring (5x5 Likelihood x Impact matrix) ---


def test_likelihood_rank_orders_certain_high_to_rare_low() -> None:
    assert likelihood_rank(Likelihood.CERTAIN) == 5
    assert likelihood_rank(Likelihood.LIKELY) == 4
    assert likelihood_rank(Likelihood.POSSIBLE) == 3
    assert likelihood_rank(Likelihood.UNLIKELY) == 2
    assert likelihood_rank(Likelihood.RARE) == 1


def test_severity_rank_orders_high_to_info() -> None:
    assert severity_rank(Severity.HIGH) == 4
    assert severity_rank(Severity.MEDIUM) == 3
    assert severity_rank(Severity.LOW) == 2
    assert severity_rank(Severity.INFO) == 1


def test_impact_rank_bands_on_quantified_exposure() -> None:
    assert impact_rank(60.0, Severity.INFO) == 5  # >=60 catastrophic, ignores severity
    assert impact_rank(100.0, Severity.INFO) == 5
    assert impact_rank(20.0, Severity.INFO) == 4  # >=20 major
    assert impact_rank(59.9, Severity.INFO) == 4
    assert impact_rank(5.0, Severity.INFO) == 3  # >=5 moderate
    assert impact_rank(19.9, Severity.INFO) == 3
    assert impact_rank(0.1, Severity.INFO) == 2  # 0 < days < 5 minor
    assert impact_rank(4.9, Severity.INFO) == 2


def test_impact_rank_falls_back_to_severity_when_unquantified() -> None:
    for days in (None, 0.0, -3.0):
        assert impact_rank(days, Severity.HIGH) == 4
        assert impact_rank(days, Severity.MEDIUM) == 3
        assert impact_rank(days, Severity.LOW) == 2
        assert impact_rank(days, Severity.INFO) == 1


def _finding(severity: Severity, **kw: object) -> Finding:
    return Finding(
        category=Category.RISK,
        severity=severity,
        metric_id="x",
        title="t",
        detail="d",
        course_of_action="c",
        citations=(),
        **kw,  # type: ignore[arg-type]
    )


def test_finding_risk_score_is_impact_times_likelihood() -> None:
    # quantified exposure -> impact band 4 (>=20), likelihood CERTAIN -> 5 => 20
    f = _finding(Severity.MEDIUM, impact_days=25.0, likelihood=Likelihood.CERTAIN)
    assert f.impact_score == 4 and f.likelihood_score == 5 and f.risk_score == 20
    # unquantified -> severity fallback impact 3 (MEDIUM), likelihood POSSIBLE -> 3 => 9
    g = _finding(Severity.MEDIUM, likelihood=Likelihood.POSSIBLE)
    assert g.impact_score == 3 and g.likelihood_score == 3 and g.risk_score == 9
    # extremes stay inside the 1..25 box
    lo = _finding(Severity.INFO, likelihood=Likelihood.RARE)
    hi = _finding(Severity.HIGH, impact_days=99.0, likelihood=Likelihood.CERTAIN)
    assert lo.risk_score == 1 and hi.risk_score == 25


def test_recommend_attaches_negative_float_exposure_as_certain_risk() -> None:
    # B (10d) must finish by a deadline 5 working days after start -> negative float on the
    # baselined-due, not-completed activity => quantified exposure, likelihood CERTAIN.
    status = dt.datetime(2025, 1, 20, 17, 0)
    deadline = dt.datetime(2025, 1, 13, 17, 0)  # 5 working days after MON
    tasks = (
        Task(
            unique_id=1,
            name="B",
            duration_minutes=10 * DAY,
            deadline=deadline,
            baseline_finish=deadline,
        ),
    )
    s = Schedule(name="s", project_start=MON, status_date=status, tasks=tasks)
    findings = recommend(s)
    nc = next(f for f in findings if f.metric_id == "not_completed")
    assert nc.float_days is not None and nc.float_days < 0  # negative total float (behind)
    assert nc.impact_days is not None and nc.impact_days > 0  # exposure = days behind
    assert nc.impact_days == round(-nc.float_days, 1)
    assert nc.likelihood is Likelihood.CERTAIN and nc.likelihood_score == 5
    assert nc.driving_float_days is None  # no target_uid set


def test_recommend_positive_float_finding_has_zero_impact_and_severity_likelihood() -> None:
    # logic on a summary -> a MEDIUM concern citing the summary; the summary's children carry
    # positive total float => impact_days 0.0 (not behind) and a severity-based likelihood.
    tasks = (
        Task(unique_id=1, name="P", wbs="2.1", duration_minutes=5 * DAY),
        Task(unique_id=10, name="Phase", wbs="1", is_summary=True, duration_minutes=0),
        Task(unique_id=11, name="Child", wbs="1.1", duration_minutes=DAY),
    )
    rels = (Relationship(predecessor_id=1, successor_id=10),)
    findings = recommend(Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels))
    flagged = next(f for f in findings if f.metric_id == "logic_on_summary_tasks")
    # the cited summary (UID 10) has no leaf timing of its own; only-positive-float findings
    # never read as exposure -> impact_days is 0.0 (if a cited timing exists) or None.
    assert flagged.impact_days in (0.0, None)
    assert flagged.likelihood is not Likelihood.CERTAIN  # severity fallback, not realized
    assert flagged.likelihood is Likelihood.POSSIBLE  # MEDIUM -> POSSIBLE


def test_recommend_positive_float_activity_yields_zero_impact() -> None:
    # a finding whose cited activity has strictly positive float => float_days>0, impact 0.0.
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=2, name="long", duration_minutes=10 * DAY),
        Task(unique_id=3, name="focus", duration_minutes=DAY),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=3),
    )
    s = Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels)
    opp = next(f for f in recommend(s, target_uid=3) if f.metric_id == "driving_path")
    assert opp.float_days is not None  # at least one cited activity has a timing
    assert opp.impact_days == 0.0  # on-driving-path activities are at/above float, not behind


def test_recommend_driving_float_populated_only_with_target() -> None:
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=2, name="B", duration_minutes=3 * DAY),
        Task(unique_id=3, name="focus", duration_minutes=DAY),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=3),
    )
    s = Schedule(name="s", project_start=MON, tasks=tasks, relationships=rels)

    with_target = next(f for f in recommend(s, target_uid=3) if f.metric_id == "driving_path")
    assert with_target.driving_float_days is not None  # the cited chain is traced to the focus

    # with no target_uid, no finding may carry a driving slack
    assert all(f.driving_float_days is None for f in recommend(s))
