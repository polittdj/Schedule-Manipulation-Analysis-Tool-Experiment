"""Risks, opportunities & concerns — cited findings with a course of action (§6.E, M10).

Synthesizes an analyst-grade finding set from the engine's deterministic signals: the
DCMA-14 audit (:mod:`.dcma_audit`), single-schedule float / baseline-compliance metrics,
the optional driving-slack trace to a target UID, and — when a prior version is supplied —
the Schedule-Network change metrics + Net Finish Impact (:mod:`.metrics.change_metrics`).
Each :class:`Finding` is a RISK, OPPORTUNITY, or CONCERN carrying a severity, a plain
course of action, and **citations (file + UniqueID + task name)** — never uncited (§6).

This is the structural, rule-based recommender; the M11 manipulation-trend detector and
the M12 local-AI narrative layer on top of these same signals (the AI only rephrases
already-cited findings — it never invents facts).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.dcma_audit import Citation, audit_schedule
from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_change_metrics,
    compute_net_finish_impact,
)
from schedule_forensics.model.schedule import Schedule

#: DCMA checks whose failure is a high-severity schedule-integrity risk.
_HIGH_SEVERITY_DCMA = frozenset({"DCMA07", "DCMA11", "DCMA12", "DCMA13", "DCMA14"})


class Category(StrEnum):
    """The forensic disposition of a finding."""

    RISK = "RISK"  # a future-facing threat to the plan
    OPPORTUNITY = "OPPORTUNITY"  # a lever to recover or improve
    CONCERN = "CONCERN"  # a current quality/integrity issue (incl. manipulation signals)


class Severity(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True)
class Finding:
    """One cited recommendation: category + severity + course of action + provenance."""

    category: Category
    severity: Severity
    metric_id: str
    title: str
    detail: str
    course_of_action: str
    citations: tuple[Citation, ...]


def _cite(schedule: Schedule, uids: tuple[int, ...]) -> tuple[Citation, ...]:
    tasks = schedule.tasks_by_id
    return tuple(
        Citation(
            source_file=schedule.source_file,
            unique_id=uid,
            task_name=tasks[uid].name if uid in tasks else "<unknown>",
        )
        for uid in uids
    )


def recommend(
    current: Schedule,
    prior: Schedule | None = None,
    *,
    current_cpm: CPMResult | None = None,
    prior_cpm: CPMResult | None = None,
    target_uid: int | None = None,
) -> tuple[Finding, ...]:
    """Produce the cited risk/opportunity/concern findings for ``current``.

    Supply ``prior`` (an earlier version) to add version-to-version change findings, and
    ``target_uid`` to add the driving-path opportunity. CPM results may be passed to avoid
    recomputation. Findings are ordered most-severe first, then by metric id.
    """
    cpm_cur = current_cpm if current_cpm is not None else compute_cpm(current)
    findings: list[Finding] = []
    findings.extend(_dcma_findings(current, cpm_cur))
    findings.extend(_compliance_findings(current, cpm_cur))
    if prior is not None:
        findings.extend(_change_findings(current, prior, cpm_cur, prior_cpm))
    if target_uid is not None:
        findings.extend(_driving_path_findings(current, target_uid))

    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
    findings.sort(key=lambda f: (order[f.severity], f.metric_id))
    return tuple(findings)


def _dcma_findings(schedule: Schedule, cpm_cur: CPMResult) -> list[Finding]:
    audit = audit_schedule(schedule, cpm_cur)
    out: list[Finding] = []
    for check in audit.failed_checks:
        severity = Severity.HIGH if check.metric_id in _HIGH_SEVERITY_DCMA else Severity.MEDIUM
        out.append(
            Finding(
                category=Category.CONCERN,
                severity=severity,
                metric_id=check.metric_id,
                title=f"DCMA {check.name} check fails ({check.count} of {check.population})",
                detail=(
                    f"{check.name}: measured {check.value}{check.unit} against a "
                    f"{check.threshold} threshold."
                ),
                course_of_action=check.suggested_improvement,
                citations=check.citations,
            )
        )
    return out


def _compliance_findings(schedule: Schedule, cpm_cur: CPMResult) -> list[Finding]:
    if schedule.status_date is None:
        return []
    c = compute_baseline_compliance(schedule, cpm_cur)
    out: list[Finding] = []
    late = c["completed_late"]
    if late.count > 0:
        out.append(
            Finding(
                category=Category.CONCERN,
                severity=Severity.MEDIUM,
                metric_id="completed_late",
                title=f"{late.count} activities completed later than baseline",
                detail="Baseline finish compliance is eroded by late completions.",
                course_of_action="Review the drivers of the late finishes and protect the "
                "remaining baseline dates with recovery actions.",
                citations=_cite(schedule, late.offender_uids),
            )
        )
    not_completed = c["not_completed"]
    if not_completed.count > 0:
        out.append(
            Finding(
                category=Category.RISK,
                severity=Severity.HIGH,
                metric_id="not_completed",
                title=f"{not_completed.count} activities baselined-due are not complete",
                detail="Work the baseline placed on/before the data date has not finished — "
                "an immediate slip risk.",
                course_of_action="Re-plan or recover these activities; assess the knock-on "
                "effect on the driving path and the project finish.",
                citations=_cite(schedule, not_completed.offender_uids),
            )
        )
    return out


def _change_findings(
    current: Schedule,
    prior: Schedule,
    cpm_cur: CPMResult,
    prior_cpm: CPMResult | None,
) -> list[Finding]:
    ch = compute_change_metrics(current, prior, current_cpm=cpm_cur, prior_cpm=prior_cpm)
    impact = compute_net_finish_impact(current, prior, current_cpm=cpm_cur, prior_cpm=prior_cpm)
    out: list[Finding] = []

    if impact.value < 0:  # the project finish moved later since the prior version
        # cite the activities that control the (slipped) project finish — those whose early
        # finish equals the network finish (the longest path's end).
        finish_drivers = tuple(
            sorted(
                uid
                for uid, t in cpm_cur.timings.items()
                if t.early_finish == cpm_cur.project_finish
            )
        )
        out.append(
            Finding(
                category=Category.CONCERN,
                severity=Severity.HIGH,
                metric_id="HSD10",
                title=(
                    f"Project finish slipped {abs(int(impact.value))} calendar days "
                    "vs the prior version"
                ),
                detail="The computed project finish moved later between the two snapshots; the "
                "cited activities control the current finish.",
                course_of_action="Identify the driving activities behind the slip and build a "
                "recovery plan; confirm the slip is not masked by logic or date changes.",
                citations=_cite(current, finish_drivers),
            )
        )
    # forensic manipulation watch-list (deep detection in M11); each cites its activities
    for key, category, severity, title, coa in (
        (
            "finish_date_slips",
            Category.RISK,
            Severity.MEDIUM,
            "activities slipped their prior-planned finish",
            "Confirm the slips reflect real progress, not deleted logic or shortened durations.",
        ),
        (
            "float_erosion",
            Category.CONCERN,
            Severity.MEDIUM,
            "activities lost total float since the prior version",
            "Watch for float being consumed to hide a slip; verify the logic that drives them.",
        ),
        (
            "no_longer_critical",
            Category.CONCERN,
            Severity.MEDIUM,
            "activities left the critical path while still incomplete",
            "Confirm criticality changes are from real re-sequencing, not logic deletion (M11).",
        ),
    ):
        metric = ch[key]
        if metric.count > 0:
            out.append(
                Finding(
                    category=category,
                    severity=severity,
                    metric_id=metric.metric_id,
                    title=f"{metric.count} {title}",
                    detail=f"{metric.name} = {metric.count} between the prior and current version.",
                    course_of_action=coa,
                    citations=_cite(current, metric.offender_uids),
                )
            )
    return out


def _driving_path_findings(schedule: Schedule, target_uid: int) -> list[Finding]:
    if target_uid not in schedule.tasks_by_id:
        return []
    results = compute_driving_slack(schedule, target_uid=target_uid)
    on_path = tuple(sorted(uid for uid, r in results.items() if r.on_driving_path))
    if not on_path:
        return []
    target_name = schedule.tasks_by_id[target_uid].name
    return [
        Finding(
            category=Category.OPPORTUNITY,
            severity=Severity.INFO,
            metric_id="driving_path",
            title=f"{len(on_path)} activities drive the path to '{target_name}' (UID {target_uid})",
            detail="These activities have zero driving slack to the focus task — recovering "
            "any of them pulls the focus date in.",
            course_of_action="Target schedule-recovery effort on this driving chain for the "
            "greatest effect on the focus activity's date.",
            citations=_cite(schedule, on_path),
        )
    ]
