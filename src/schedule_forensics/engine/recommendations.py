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

from dataclasses import dataclass, replace
from enum import StrEnum

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.dcma_audit import Citation, ScheduleAudit, audit_schedule
from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_change_metrics,
    compute_net_finish_impact,
)
from schedule_forensics.engine.metrics._common import MetricResult
from schedule_forensics.engine.summary_logic import summaries_with_logic
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.units import MINUTES_PER_DAY

#: DCMA checks whose failure is a high-severity schedule-integrity risk.
_HIGH_SEVERITY_DCMA = frozenset({"DCMA07", "DCMA11", "DCMA12", "DCMA13", "DCMA14"})

#: Working minutes in one standard 8-hour working day (480) — the canonical duration axis
#: (matches :data:`schedule_forensics.model.units.MINUTES_PER_DAY`). Used to convert the
#: engine's working-minute floats into the working-day exposure the risk matrix bands on.
_MIN_PER_DAY = MINUTES_PER_DAY


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


#: Most-severe-first sort key, shared by the recommender and the manipulation detector.
SEVERITY_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}


class Likelihood(StrEnum):
    """How likely a finding's threat is to occur — the matrix's Likelihood axis."""

    CERTAIN = "CERTAIN"  # already realized (e.g. cited activity is behind / negative float)
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNLIKELY = "UNLIKELY"
    RARE = "RARE"


def likelihood_rank(value: Likelihood) -> int:
    """The 1..5 ordinal of a likelihood (CERTAIN=5 … RARE=1) — the matrix's row index."""
    return {
        Likelihood.CERTAIN: 5,
        Likelihood.LIKELY: 4,
        Likelihood.POSSIBLE: 3,
        Likelihood.UNLIKELY: 2,
        Likelihood.RARE: 1,
    }[value]


def severity_rank(value: Severity) -> int:
    """The 1..4 ordinal of a severity (HIGH=4 … INFO=1) — the qualitative impact fallback."""
    return {Severity.HIGH: 4, Severity.MEDIUM: 3, Severity.LOW: 2, Severity.INFO: 1}[value]


def impact_rank(impact_days: float | None, severity: Severity) -> int:
    """The 1..5 Impact-axis band for a finding.

    Quantified path: a positive ``impact_days`` (working-day schedule exposure) bands the
    impact — ``>=60`` is catastrophic (5), ``>=20`` major (4), ``>=5`` moderate (3), and any
    smaller positive exposure is minor (2). With no quantified exposure (``None`` or ``<=0``)
    it falls back to the qualitative severity: HIGH->4, MEDIUM->3, LOW->2, INFO->1.
    """
    if impact_days is not None and impact_days > 0:
        if impact_days >= 60:
            return 5
        if impact_days >= 20:
            return 4
        if impact_days >= 5:
            return 3
        return 2
    return severity_rank(severity)


@dataclass(frozen=True)
class Finding:
    """One cited recommendation: category + severity + course of action + provenance.

    The quantified-risk fields (``likelihood`` … ``driving_float_days``) are appended by the
    :func:`recommend` quantification pass from the CPM citations, so the finding can drop onto
    a 5x5 (Likelihood x Impact) risk matrix with a testimony-defensible, deterministic score.
    """

    category: Category
    severity: Severity
    metric_id: str
    title: str
    detail: str
    course_of_action: str
    citations: tuple[Citation, ...]
    likelihood: Likelihood = Likelihood.POSSIBLE
    impact_days: float | None = None  # schedule exposure in working days (None = not quantified)
    float_days: float | None = None  # tightest total float among cited activities (working days)
    driving_float_days: float | None = None  # tightest driving slack to the target among cited

    @property
    def likelihood_score(self) -> int:
        """The Likelihood-axis ordinal (1..5) — the matrix row index."""
        return likelihood_rank(self.likelihood)

    @property
    def impact_score(self) -> int:
        """The Impact-axis ordinal (1..5) — banded on quantified exposure, else severity."""
        return impact_rank(self.impact_days, self.severity)

    @property
    def risk_score(self) -> int:
        """The 5x5 matrix cell value (1..25): impact x likelihood."""
        return self.impact_score * self.likelihood_score


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
    precomputed_audit: ScheduleAudit | None = None,
    precomputed_compliance: dict[str, MetricResult] | None = None,
) -> tuple[Finding, ...]:
    """Produce the cited risk/opportunity/concern findings for ``current``.

    Supply ``prior`` (an earlier version) to add version-to-version change findings, and
    ``target_uid`` to add the driving-path opportunity. CPM results may be passed to avoid
    recomputation. Findings are ordered most-severe first, then by metric id.

    ``precomputed_audit`` / ``precomputed_compliance`` (ADR-0281) let a caller that already holds
    the DEFAULT DCMA audit and baseline-compliance metrics for exactly ``current`` + ``current_cpm``
    hand them in, so the recommender does not recompute them. They MUST be the default (non-Acumen-
    parity) audit and the baseline compliance for this schedule + solve; the findings are
    byte-identical to computing them here. Left ``None`` (every existing call site) nothing changes.
    """
    cpm_cur = current_cpm if current_cpm is not None else compute_cpm(current)
    findings: list[Finding] = []
    findings.extend(_dcma_findings(current, cpm_cur, precomputed_audit=precomputed_audit))
    findings.extend(_logic_support_findings(current, cpm_cur))
    findings.extend(_summary_logic_findings(current))
    findings.extend(
        _compliance_findings(current, cpm_cur, precomputed_compliance=precomputed_compliance)
    )
    if prior is not None:
        findings.extend(_change_findings(current, prior, cpm_cur, prior_cpm))
    if target_uid is not None:
        findings.extend(_driving_path_findings(current, target_uid))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.metric_id))
    return _quantify(tuple(findings), current, cpm_cur, target_uid)


def _quantify(
    findings: tuple[Finding, ...],
    schedule: Schedule,
    cpm: CPMResult,
    target_uid: int | None,
) -> tuple[Finding, ...]:
    """Attach the deterministic risk-matrix fields to each finding from its CPM citations.

    For every finding it takes the cited activities that have a CPM timing and derives:
    the tightest total float (``float_days``), the resulting schedule exposure
    (``impact_days`` = the magnitude of any negative float — days already behind), the
    tightest driving slack to ``target_uid`` (``driving_float_days``, only when a target is
    set), and the matrix ``likelihood`` (CERTAIN when there is real exposure, else a
    severity fallback). Findings whose citations have no CPM timing keep the None defaults
    and the severity-based likelihood.
    """
    from schedule_forensics.engine.driving_slack import (  # local: avoid import cycle
        DrivingSlackResult,
        compute_driving_slack,
    )

    # Convert on the SCHEDULE'S calendar, like every other engine day conversion — a fixed 480
    # overstated float/impact days by 25% on a 10-hour calendar (QC audit D13); 480 remains only
    # the fallback for a degenerate 0-minute calendar.
    per_day = schedule.calendar.working_minutes_per_day or _MIN_PER_DAY
    tf_days: dict[int, float] = {
        uid: round(t.total_float / per_day, 1) for uid, t in cpm.timings.items()
    }
    ds: dict[int, DrivingSlackResult] = {}
    if target_uid is not None:
        try:
            ds = compute_driving_slack(schedule, target_uid=target_uid)
        except (KeyError, ValueError):
            ds = {}

    out: list[Finding] = []
    for finding in findings:
        cited = [c.unique_id for c in finding.citations if c.unique_id in cpm.timings]
        float_days = min(tf_days[u] for u in cited) if cited else None
        impact_days = round(max(0.0, -float_days), 1) if float_days is not None else None
        ds_cited = [float(ds[u].driving_slack_days) for u in cited if u in ds]
        driving_float_days = min(ds_cited) if ds and ds_cited else None
        if impact_days is not None and impact_days > 0:
            likelihood = Likelihood.CERTAIN
        else:
            likelihood = {
                Severity.HIGH: Likelihood.LIKELY,
                Severity.MEDIUM: Likelihood.POSSIBLE,
                Severity.LOW: Likelihood.UNLIKELY,
                Severity.INFO: Likelihood.RARE,
            }[finding.severity]
        out.append(
            replace(
                finding,
                likelihood=likelihood,
                impact_days=impact_days,
                float_days=float_days,
                driving_float_days=driving_float_days,
            )
        )
    return tuple(out)


def _finish_driver_citations(schedule: Schedule, cpm: CPMResult) -> tuple[Citation, ...]:
    """Cite the activities controlling the project finish (early finish == network finish).

    The fallback for schedule-level checks (e.g. Critical Path Test, CPLI) that can fail
    without per-activity offenders — the §6 never-uncited invariant must hold for every
    finding, and the finish-controlling chain is the verifiable anchor of those checks.
    With no schedulable activities at all (e.g. a summary-only template), the first task
    rows are the terminal anchor — a citation can never be empty.
    """
    uids = tuple(
        sorted(uid for uid, t in cpm.timings.items() if t.early_finish == cpm.project_finish)
    )
    if not uids:
        uids = tuple(t.unique_id for t in schedule.tasks[:3])
    return _cite(schedule, uids)


def _dcma_findings(
    schedule: Schedule,
    cpm_cur: CPMResult,
    *,
    precomputed_audit: ScheduleAudit | None = None,
) -> list[Finding]:
    audit = (
        precomputed_audit if precomputed_audit is not None else audit_schedule(schedule, cpm_cur)
    )
    out: list[Finding] = []
    fallback: tuple[Citation, ...] | None = None
    for check in audit.failed_checks:
        severity = Severity.HIGH if check.metric_id in _HIGH_SEVERITY_DCMA else Severity.MEDIUM
        citations = check.citations
        if not citations:
            if fallback is None:
                fallback = _finish_driver_citations(schedule, cpm_cur)
            citations = fallback
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
                citations=citations,
            )
        )
    return out


def _logic_support_findings(schedule: Schedule, cpm_cur: CPMResult) -> list[Finding]:
    """The ADR-0034 stored-date divergence: dates the network logic does not support.

    The CPM honored these activities' stored dates (manual pin / logic-unbound floor)
    because a pure forward pass would have scheduled them elsewhere — on sparse-logic
    files, packed at the project start. Honest forensics: the schedule reproduces the
    source file AND the divergence is reported, cited per activity, never silent.
    """
    if not cpm_cur.date_driven:
        return []
    n = len(cpm_cur.date_driven)
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.MEDIUM,
            metric_id="logic_unsupported_dates",
            title=f"{n} scheduled date{'s are' if n != 1 else ' is'} not supported by logic",
            detail=(
                "These activities sit at manually-placed / stored dates that predecessor "
                "logic does not produce — a pure critical-path pass would schedule them "
                "elsewhere. The tool honors the stored dates so the computed schedule "
                "matches the source file, and flags the divergence here."
            ),
            course_of_action="Tie these activities into the network with real predecessor "
            "logic (or confirm the manual dates are deliberate); dates that logic cannot "
            "reproduce cannot be trusted to move correctly when the plan changes.",
            citations=_cite(schedule, cpm_cur.date_driven),
        )
    ]


def _summary_logic_findings(schedule: Schedule) -> list[Finding]:
    """Logic attached to summary tasks (ADR-0043) — a scheduling best-practice violation.

    The CPM honors this logic the way MS Project does (it is lowered onto the summary's
    children, so the computed dates match the source file), but relationships belong on the
    work, not the roll-up: logic on a summary hides the true driver, double-counts when the
    summary also has child logic, and breaks when the summary's children change. Flagged and
    cited so the analyst can move the logic down to the activities."""
    flagged = summaries_with_logic(schedule)
    if not flagged:
        return []
    n = len(flagged)
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.MEDIUM,
            metric_id="logic_on_summary_tasks",
            title=f"{n} summary task{'s carry' if n != 1 else ' carries'} logic",
            detail=(
                "These summary (roll-up) tasks have predecessor or successor relationships. "
                "MS Project applies that logic to the summary's children, so the tool "
                "schedules the children to match the file — but logic on a summary is a "
                "recognized anti-pattern (DCMA/PMI): it obscures the real driving activity "
                "and misbehaves when the summary's contents change."
            ),
            course_of_action="Move the relationships off the summary onto the specific "
            "activities that drive and are driven by the work; keep summaries as pure "
            "roll-ups.",
            citations=_cite(schedule, flagged),
        )
    ]


def _compliance_findings(
    schedule: Schedule,
    cpm_cur: CPMResult,
    *,
    precomputed_compliance: dict[str, MetricResult] | None = None,
) -> list[Finding]:
    if schedule.status_date is None:
        return []
    c = (
        precomputed_compliance
        if precomputed_compliance is not None
        else compute_baseline_compliance(schedule, cpm_cur)
    )
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
    task = schedule.tasks_by_id.get(target_uid)
    if task is None or task.is_summary:
        return []  # summary rollups are not in the logic network — nothing to trace
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
