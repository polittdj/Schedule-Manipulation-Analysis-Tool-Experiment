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
from schedule_forensics.engine.metrics._common import is_effective_critical, non_summary
from schedule_forensics.engine.trend import compute_quality_trend, order_versions
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


@dataclass(frozen=True)
class BriefingTable:
    """A structured, cited table view of a section's figures (readability reformat).

    ``headers`` may be empty for a label/value profile strip. ``row_citations`` aligns
    1:1 with ``rows`` — the §6 cited-everything contract holds for table rows exactly
    as it does for prose statements.
    """

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    row_citations: tuple[tuple[Citation, ...], ...]


@dataclass(frozen=True)
class BriefingSection:
    """One titled section of the executive briefing.

    ``statements`` carry the cited prose (polished by the local backend, exported by
    ``to_text``); ``kind`` + ``table`` drive the readable page rendering — the lede
    paragraph, the cross-version trend table, the per-project profile cards, and the
    per-check quality verdict tables. Figures in tables are engine-computed verbatim
    (the model polishes prose only, never data).
    """

    heading: str
    statements: tuple[CitedStatement, ...]
    kind: str = "prose"  # "lede" | "trend" | "project" | "quality" | "prose"
    table: BriefingTable | None = None


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
    """Cite the activities that control the project finish (early finish == network finish).

    With no schedulable activities at all (a summary-only template), the first task rows
    are the terminal anchor — the §6 never-uncited invariant must hold for every statement.
    """
    by_id = schedule.tasks_by_id
    drivers = tuple(
        Citation(_label(schedule), uid, by_id[uid].name)
        for uid, t in sorted(cpm.timings.items())
        if t.early_finish == cpm.project_finish
    )
    if not drivers:
        drivers = tuple(Citation(_label(schedule), t.unique_id, t.name) for t in schedule.tasks[:3])
    return drivers


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
    if not citations:
        # an empty scope (e.g. a session filter that matched nothing) has no finish drivers —
        # anchor on the files themselves so the lede is never uncited (§6 contract).
        citations = tuple(Citation(s.source_file, 0, _label(s)) for s in schedules)
    return BriefingSection("Workbook Summary", (CitedStatement(text, citations),), kind="lede")


def _trend_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefingSection:
    trends = compute_quality_trend(schedules, cpms)
    statements: list[CitedStatement] = []
    rows: list[tuple[str, ...]] = []
    row_citations: list[tuple[Citation, ...]] = []
    for trend in trends:
        if trend.worst_index is not None and trend.worst_offender_uids:
            citations = _cite(schedules[trend.worst_index], trend.worst_offender_uids[:10])
        elif trend.worst_index is not None:
            citations = _finish_drivers(schedules[trend.worst_index], cpms[trend.worst_index])
        else:
            citations = _finish_drivers(schedules[-1], cpms[-1])
        statements.append(CitedStatement(trend.sentence(), citations))
        rows.append((trend.name, " → ".join(f"{v:g}" for v in trend.values), trend.direction))
        row_citations.append(citations)
    return BriefingSection(
        "Trend Analysis",
        tuple(statements),
        kind="trend",
        table=BriefingTable(
            headers=("Metric", "Oldest → newest", "Trend"),
            rows=tuple(rows),
            row_citations=tuple(row_citations),
        ),
    )


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
    profile: list[tuple[str, ...]] = [
        ("Start", _day(schedule.project_start.date())),
        ("Completion", _day(finish.date())),
        (
            "Status date",
            _day(schedule.status_date.date()) if schedule.status_date else "not statused",
        ),
        ("Activities", str(n)),
        ("Complete", f"{complete} ({_pct(complete, n):g}%)"),
        ("In progress", f"{in_progress} ({_pct(in_progress, n):g}%)"),
        ("Planned", f"{planned} ({_pct(planned, n):g}%)"),
        ("Milestones", str(milestones)),
        ("Summaries", str(summaries)),
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
        profile.append(("Baseline window", f"{baseline_start.date()} → {baseline_finish.date()}"))
        profile.append(
            (
                "Vs baseline",
                f"{delta_days:+d} days" if delta_days else "on schedule",
            )
        )
    return BriefingSection(
        f"{label} Project",
        tuple(statements),
        kind="project",
        table=BriefingTable(
            headers=(),
            rows=tuple(profile),
            row_citations=tuple(drivers for _ in profile),
        ),
    )


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
    rows: list[tuple[str, ...]] = []
    row_citations: list[tuple[Citation, ...]] = []
    for check in audit.checks:
        if check.status is CheckStatus.NOT_APPLICABLE:
            continue
        value = f"{check.value:g}{check.unit}"
        text = (
            f"{check.name}: {check.count} of {check.population} activities ({value}). "
            f"{_verdict(check.status)}"
        )
        verdict = _verdict(check.status)
        if check.status is CheckStatus.FAIL and check.suggested_improvement:
            text += f" {check.suggested_improvement}"
            verdict += f" {check.suggested_improvement}"
        citations = check.citations or fallback
        statements.append(CitedStatement(text, citations))
        rows.append((check.name, f"{check.count} of {check.population}", value, verdict))
        row_citations.append(citations)
    return BriefingSection(
        f"{label} Schedule Quality Analysis",
        tuple(statements),
        kind="quality",
        table=BriefingTable(
            headers=("DCMA check", "Count", "Value", "Verdict"),
            rows=tuple(rows),
            row_citations=tuple(row_citations),
        ),
    )


def _assessment_section(schedule: Schedule, cpm: CPMResult, today: dt.date) -> BriefingSection:
    """The executive lede: an overall verdict (ON TRACK / NEEDS ATTENTION / AT RISK) plus the
    headline numbers a sponsor reads first — forecast completion vs baseline, critical exposure,
    and the DCMA-14 fail count — for the latest version. Every figure is engine-computed and cited;
    the verdict is a transparent heuristic (finish slip + DCMA failures), not an opaque score."""
    label = _label(schedule)
    tasks = non_summary(schedule)
    n = len(tasks)
    audit = audit_schedule(schedule, cpm)
    applicable = [c for c in audit.checks if c.status is not CheckStatus.NOT_APPLICABLE]
    fails = sum(1 for c in applicable if c.status is CheckStatus.FAIL)
    finish = _finish_date(schedule, cpm)
    _, baseline_finish = _baseline_window(tasks)
    delta_days = (finish.date() - baseline_finish.date()).days if baseline_finish else None
    incomplete = [t for t in tasks if t.percent_complete < 100.0]
    critical = sum(
        1
        for t in incomplete
        if t.unique_id in cpm.timings
        and is_effective_critical(t, cpm.timings[t.unique_id].total_float)
    )
    behind = delta_days is not None and delta_days > 0
    if delta_days is not None and delta_days <= 0 and fails == 0:
        verdict = "ON TRACK"
    elif (behind and fails >= 4) or (delta_days is not None and delta_days > 20):
        verdict = "AT RISK"
    else:
        verdict = "NEEDS ATTENTION"
    if delta_days is None:
        var_txt = "no baseline finish to compare against"
        var_cell = "no baseline"
    elif delta_days > 0:
        var_txt = f"{delta_days} days behind baseline"
        var_cell = f"+{delta_days} days"
    elif delta_days < 0:
        var_txt = f"{-delta_days} days ahead of baseline"
        var_cell = f"{delta_days} days"
    else:
        var_txt = "on its baseline finish"
        var_cell = "on schedule"
    drivers = _finish_drivers(schedule, cpm)
    text = (
        f"Executive assessment of {label} as of {_day(today)}: {verdict}. The schedule forecasts "
        f"completion on {_day(finish.date())} ({var_txt}); {critical} of {len(incomplete)} "
        f"incomplete activities are critical, and {fails} of {len(applicable)} applicable DCMA-14 "
        f"checks are failing."
    )
    profile: list[tuple[str, ...]] = [
        ("Overall verdict", verdict),
        ("Forecast completion", _day(finish.date())),
        ("Vs baseline finish", var_cell),
        ("Critical activities", f"{critical} of {len(incomplete)} incomplete"),
        ("DCMA-14 checks failing", f"{fails} of {len(applicable)}"),
        ("Activities in scope", str(n)),
    ]
    return BriefingSection(
        "Key Assessment",
        (CitedStatement(text, drivers),),
        kind="assessment",
        table=BriefingTable(
            headers=(),
            rows=tuple(profile),
            row_citations=tuple(drivers for _ in profile),
        ),
    )


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

    # An empty scope (a session filter that matched nothing, or summary-only files) has no
    # schedulable activities, so the per-metric trend/quality sentences would be uncitable. Emit a
    # single cited lede anchored on the files instead of degenerate, uncited sections (§6 contract).
    if not any(any(not t.is_summary for t in s.tasks) for s in ordered):
        cite = tuple(Citation(s.source_file, 0, _label(s)) for s in ordered)
        text = (
            f"No schedulable activities are in scope across the {len(ordered)} loaded version(s) "
            "— a filter or selection matched nothing, so there is nothing to brief."
        )
        sections = [BriefingSection("Workbook Summary", (CitedStatement(text, cite),), kind="lede")]
    else:
        # the executive lede first: overall verdict + headline numbers for the latest version
        sections = [
            _assessment_section(ordered[-1], cpm_list[-1], report_day),
            _workbook_section(ordered, cpm_list, report_day),
        ]
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
            BriefingSection(
                section.heading,
                reattach(polished, section.statements),
                kind=section.kind,
                table=section.table,  # tables are engine data — the model never touches them
            )
        )
    return ExecutiveBriefing(
        title="Schedule Forensics — Diagnostic Executive Briefing",
        generated_on=report_day,
        sections=tuple(polished_sections),
    )
