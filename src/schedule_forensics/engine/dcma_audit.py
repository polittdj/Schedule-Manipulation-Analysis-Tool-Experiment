"""Independent per-schedule DCMA-14 audit with cited, plain-language improvements (§6.E, M10).

Packages the M7 DCMA-14 engine (:func:`compute_dcma14`) into an auditor's report: each of
the 14 checks becomes an :class:`AuditCheck` carrying its pass/fail vs threshold, the
**cited offending activities** (file + UniqueID + task name — §6, never uncited), and a
plain-language *suggested improvement* an analyst can act on. A :class:`ScheduleAudit`
rolls the checks up with pass/fail/NA tallies. This is the structural audit; the
risk/opportunity/concern narrative is in :mod:`.recommendations`, and the AI story in
``ai/`` (M12). Deterministic and offline (Law 1/2).
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics import CheckStatus, MetricResult, compute_dcma14
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class Citation:
    """A fact's provenance: file + UniqueID + task name, so any figure is verifiable."""

    source_file: str | None
    unique_id: int
    task_name: str

    def __str__(self) -> str:
        return f"{self.task_name} (UID {self.unique_id}, {self.source_file or 'uploaded schedule'})"


@dataclass(frozen=True)
class AuditCheck:
    """One DCMA-14 check as an audit line: result + offenders + suggested improvement."""

    metric_id: str
    name: str
    status: CheckStatus
    count: int
    population: int
    value: float
    unit: str
    threshold: float | None
    suggested_improvement: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class ScheduleAudit:
    """A full independent DCMA-14 audit of one schedule."""

    source_file: str | None
    schedule_name: str
    checks: tuple[AuditCheck, ...]
    passed: int
    failed: int
    not_applicable: int

    @property
    def failed_checks(self) -> tuple[AuditCheck, ...]:
        return tuple(c for c in self.checks if c.status is CheckStatus.FAIL)


#: Plain-language remediation guidance per DCMA-14 check (keyed by the base metric id).
_IMPROVEMENTS: dict[str, str] = {
    "DCMA01": "Add the missing predecessor/successor logic so every incomplete activity is "
    "driven by and drives the network (no danglers).",
    "DCMA02": "Remove negative lags (leads); model the overlap with an explicit SS/FF "
    "relationship and a positive lag instead.",
    "DCMA03": "Reduce reliance on lags; replace a lag with a real activity (e.g. 'cure', "
    "'cure time') so the duration is visible and statusable.",
    "DCMA04_FS": "Prefer Finish-to-Start logic; justify each non-FS relationship and convert "
    "where the work truly is sequential.",
    "DCMA04_SSFF": "Review SS/FF relationships into incomplete work; confirm each reflects "
    "real overlap rather than a workaround for missing detail.",
    "DCMA04_SF": "Eliminate Start-to-Finish relationships unless contractually required; they "
    "are rarely correct and obscure the logic.",
    "DCMA05": "Replace hard constraints (MSO/MFO/SNLT/FNLT) with logic-driven dates or a "
    "deadline; hard constraints mask true float and slip.",
    "DCMA06": "Investigate activities with > 44 working days of total float — usually missing "
    "successor logic; tie them back into the network.",
    "DCMA07": "Resolve negative float by recovering logic, durations, or the imposed finish; "
    "negative float means the plan is already behind its constraint.",
    "DCMA08": "Break down activities longer than 44 working days into statusable detail so "
    "progress and risk are visible.",
    "DCMA09": "Correct invalid dates: no actuals in the future, no incomplete forecast in the "
    "past relative to the data date.",
    "DCMA10": "Resource-load the open, real-duration activities (or confirm they are LOE) so "
    "the schedule supports cost/EVM analysis.",
    "DCMA11": "Address missed activities: re-plan or recover the work baselined to finish by "
    "the data date that has not completed.",
    "DCMA12": "Repair the controlling logic so a delay on a critical activity flows through to "
    "the project finish (a continuous critical path).",
    "DCMA13": "Improve the Critical Path Length Index toward >= 0.95 by recovering the "
    "controlling path's negative float.",
    "DCMA14": "Raise the Baseline Execution Index toward >= 0.95 by completing the work "
    "baselined to finish by the data date.",
}
_OK_NOTE = "Within the DCMA tolerance — no action required."
_NA_NOTE = "Not applicable for this schedule (inputs absent)."


def audit_schedule(schedule: Schedule, cpm_result: CPMResult | None = None) -> ScheduleAudit:
    """Run the 14 DCMA checks and return an independent, cited audit of one schedule."""
    results = compute_dcma14(schedule, cpm_result)
    checks: list[AuditCheck] = []
    for metric_id, result in results.items():
        improvement = (
            _OK_NOTE
            if result.status is CheckStatus.PASS
            else _NA_NOTE
            if result.status is CheckStatus.NOT_APPLICABLE
            else _IMPROVEMENTS.get(metric_id, "Review and remediate the flagged activities.")
        )
        checks.append(
            AuditCheck(
                metric_id=result.metric_id,
                name=result.name,
                status=result.status,
                count=result.count,
                population=result.population,
                value=result.value,
                unit=result.unit,
                threshold=result.threshold,
                suggested_improvement=improvement,
                citations=_cite_offenders(schedule, result),
            )
        )
    passed = sum(1 for c in checks if c.status is CheckStatus.PASS)
    failed = sum(1 for c in checks if c.status is CheckStatus.FAIL)
    na = sum(1 for c in checks if c.status is CheckStatus.NOT_APPLICABLE)
    return ScheduleAudit(
        source_file=schedule.source_file,
        schedule_name=schedule.name,
        checks=tuple(checks),
        passed=passed,
        failed=failed,
        not_applicable=na,
    )


def _cite_offenders(schedule: Schedule, result: MetricResult) -> tuple[Citation, ...]:
    """Build a Citation (file + UID + task name) for each offending activity, sorted by UID."""
    tasks = schedule.tasks_by_id
    return tuple(
        Citation(
            source_file=schedule.source_file,
            unique_id=uid,
            task_name=tasks[uid].name if uid in tasks else "<unknown>",
        )
        for uid in result.offender_uids
    )
