"""Diagnostic Executive Briefing — the workbook-level executive summary (§6.D/E).

Builds the report an analyst hands to leadership, modeled on an Acumen Fuse Diagnostic
Executive Briefing: a workbook summary, a cross-version Trend Analysis, a per-project
summary (dates, progress percentages, baseline variance), and a per-project schedule-quality
section with a verdict per DCMA check. Every statement is a
:class:`~schedule_forensics.ai.citations.CitedStatement` (file + UID + task — §6 contract),
and the configured local backend may *rephrase* the prose but can never alter a number or
drop a citation (:func:`~schedule_forensics.ai.citations.reattach` re-verifies).

All figures are computed by the engine on the spot — the briefing fabricates nothing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from schedule_forensics.ai.backend import AIBackend
from schedule_forensics.ai.citations import CitedStatement, assert_all_cited, reattach
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation, audit_schedule
from schedule_forensics.engine.metrics import CheckStatus
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.trend import compute_quality_trend, order_versions
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


@dataclass(frozen=True)
class BriefingSection:
    """One titled section of the executive briefing."""

    heading: str
    statements: tuple[CitedStatement, ...]


@dataclass(frozen=True)
class ExecutiveBriefing:
    """The full diagnostic executive briefing for the loaded workbook."""

    title: str
    generated_on: dt.date
    sections: tuple[BriefingSection, ...]

    def to_text(self) -> str:
        parts = [f"# {self.title}", f"Report generated on {_day(self.generated_on)}"]
        for section in self.sections:
            parts.append(f"\n## {section.heading}")
            parts.extend(f"- {s.rendered()}" for s in section.statements)
        return "\n".join(parts)


def _day(d: dt.date) -> str:
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def _label(schedule: Schedule) -> str:
    return schedule.source_file or schedule.name


def _finish_drivers(schedule: Schedule, cpm: CPMResult) -> tuple[Citation, ...]:
    """Cite the activities that control the project finish (early finish == network finish)."""
    by_id = schedule.tasks_by_id
    return tuple(
        Citation(_label(schedule), uid, by_id[uid].name)
        for uid, t in sorted(cpm.timings.items())
        if t.early_finish == cpm.project_finish
    )


def _cite(schedule: Schedule, uids: tuple[int, ...]) -> tuple[Citation, ...]:
    by_id = schedule.tasks_by_id
    return tuple(
        Citation(_label(schedule), uid, by_id[uid].name if uid in by_id else "<unknown>")
        for uid in uids
    )


def _finish_date(schedule: Schedule, cpm: CPMResult) -> dt.datetime:
    return offset_to_datetime(schedule.project_start, cpm.project_finish, schedule.calendar)


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def _baseline_window(tasks: list[Task]) -> tuple[dt.datetime | None, dt.datetime | None]:
    starts = [t.baseline_start for t in tasks if t.baseline_start is not None]
    finishes = [t.baseline_finish for t in tasks if t.baseline_finish is not None]
    return (min(starts) if starts else None, max(finishes) if finishes else None)


def _workbook_section(
    schedules: list[Schedule], cpms: list[CPMResult], today: dt.date
) -> BriefingSection:
    labels = ", ".join(_label(s) for s in schedules)
    starts = [s.project_start for s in schedules]
    finishes = [_finish_date(s, c) for s, c in zip(schedules, cpms, strict=True)]
    latest_i = max(range(len(finishes)), key=lambda i: finishes[i])
    text = (
        f"A Schedule Forensics analysis was conducted on {_day(today)} on "
        f"{len(schedules)} schedule version(s): {labels}. The earliest start date is "
        f"{_day(min(starts).date())} with the latest completion date being "
        f"{_day(finishes[latest_i].date())}."
    )
    citations = _finish_drivers(schedules[latest_i], cpms[latest_i])
    return BriefingSection("Workbook Summary", (CitedStatement(text, citations),))


def _trend_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefingSection:
    trends = compute_quality_trend(schedules, cpms)
    statements: list[CitedStatement] = []
    for trend in trends:
        if trend.worst_index is not None and trend.worst_offender_uids:
            citations = _cite(schedules[trend.worst_index], trend.worst_offender_uids[:10])
        elif trend.worst_index is not None:
            citations = _finish_drivers(schedules[trend.worst_index], cpms[trend.worst_index])
        else:
            citations = _finish_drivers(schedules[-1], cpms[-1])
        statements.append(CitedStatement(trend.sentence(), citations))
    return BriefingSection("Trend Analysis", tuple(statements))


def _project_section(schedule: Schedule, cpm: CPMResult) -> BriefingSection:
    label = _label(schedule)
    tasks = non_summary(schedule)
    n = len(tasks)
    complete = sum(1 for t in tasks if t.percent_complete >= 100.0)
    in_progress = sum(1 for t in tasks if 0.0 < t.percent_complete < 100.0)
    planned = n - complete - in_progress
    milestones = sum(1 for t in tasks if t.is_milestone)
    # UID 0 is MS Project's project-level summary row — not a real WBS summary (Acumen
    # excludes it from the summary count too).
    summaries = sum(1 for t in schedule.tasks if t.is_summary and t.unique_id != 0)
    finish = _finish_date(schedule, cpm)
    drivers = _finish_drivers(schedule, cpm)

    status = (
        f"currently in progress with a status date of {_day(schedule.status_date.date())}"
        if schedule.status_date is not None
        else "not statused (no data date recorded)"
    )
    statements = [
        CitedStatement(
            f"The {label} project has a start date of {_day(schedule.project_start.date())} "
            f"and has {_day(finish.date())} as the completion date. The project is {status}. "
            f"It has {n} normal activities of which {complete} ({_pct(complete, n)}%) are "
            f"complete, {in_progress} ({_pct(in_progress, n)}%) are in progress and "
            f"{planned} ({_pct(planned, n)}%) are still planned. It contains "
            f"{milestones} milestone(s) and {summaries} summaries.",
            drivers,
        )
    ]
    baseline_start, baseline_finish = _baseline_window(tasks)
    if baseline_start is not None and baseline_finish is not None:
        delta_days = (finish.date() - baseline_finish.date()).days
        if delta_days > 0:
            variance = f"The project is currently behind schedule by {delta_days} days."
        elif delta_days < 0:
            variance = f"The project is currently ahead of schedule by {-delta_days} days."
        else:
            variance = "The project is currently on schedule against its baseline."
        statements.append(
            CitedStatement(
                f"The project baseline start date was {_day(baseline_start.date())} with the "
                f"baseline finish date being {_day(baseline_finish.date())}. {variance}",
                drivers,
            )
        )
    return BriefingSection(f"{label} Project", tuple(statements))


def _verdict(status: CheckStatus) -> str:
    if status is CheckStatus.PASS:
        return "No exceptions beyond the threshold. This is the target state."
    if status is CheckStatus.FAIL:
        return "Improvements are required."
    return "Not applicable for this schedule."


def _quality_section(schedule: Schedule, cpm: CPMResult) -> BriefingSection:
    label = _label(schedule)
    audit = audit_schedule(schedule, cpm)
    fallback = _finish_drivers(schedule, cpm)
    statements: list[CitedStatement] = []
    for check in audit.checks:
        if check.status is CheckStatus.NOT_APPLICABLE:
            continue
        value = f"{check.value:g}{check.unit}"
        text = (
            f"{check.name}: {check.count} of {check.population} activities ({value}). "
            f"{_verdict(check.status)}"
        )
        if check.status is CheckStatus.FAIL and check.suggested_improvement:
            text += f" {check.suggested_improvement}"
        statements.append(CitedStatement(text, check.citations or fallback))
    return BriefingSection(f"{label} Schedule Quality Analysis", tuple(statements))


def build_briefing(
    schedules: list[Schedule],
    *,
    backend: AIBackend | None = None,
    cpms: list[CPMResult] | None = None,
    today: dt.date | None = None,
) -> ExecutiveBriefing:
    """Build the cited Diagnostic Executive Briefing for the loaded versions.

    Versions are ordered by data date (oldest first). With two or more versions the
    briefing includes the cross-version Trend Analysis; a single version gets the project
    summary and quality sections only. ``backend`` (default offline Null) may rephrase the
    prose; citations are re-attached and re-verified.
    """
    if not schedules:
        raise ValueError("the briefing needs at least one schedule version")
    ordered = order_versions(schedules)
    if cpms is None:
        cpm_list = [compute_cpm(s) for s in ordered]
    else:
        by_id = {id(s): c for s, c in zip(schedules, cpms, strict=True)}
        cpm_list = [by_id[id(s)] for s in ordered]
    report_day = today if today is not None else dt.date.today()

    sections = [_workbook_section(ordered, cpm_list, report_day)]
    if len(ordered) >= 2:
        sections.append(_trend_section(ordered, cpm_list))
    for schedule, cpm in zip(ordered, cpm_list, strict=True):
        sections.append(_project_section(schedule, cpm))
    for schedule, cpm in zip(ordered, cpm_list, strict=True):
        sections.append(_quality_section(schedule, cpm))

    be: AIBackend = backend if backend is not None else NullBackend()
    polished_sections: list[BriefingSection] = []
    for section in sections:
        assert_all_cited(section.statements)
        polished = tuple(be.generate(s.text) for s in section.statements)
        polished_sections.append(
            BriefingSection(section.heading, reattach(polished, section.statements))
        )
    return ExecutiveBriefing(
        title="Schedule Forensics — Diagnostic Executive Briefing",
        generated_on=report_day,
        sections=tuple(polished_sections),
    )
