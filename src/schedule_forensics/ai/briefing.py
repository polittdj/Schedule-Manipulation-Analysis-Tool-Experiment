"""Executive Briefing — the leadership-facing forensic schedule summary.

Rebuilt to model a forensic Executive Summary written for senior leadership *without* a
scheduling background (operator request, ADR-0121): a metadata header + a one-line verdict
banner, then numbered sections —

    1. The Bottom Line          (verdict, plain-English story, the single most important number)
    2. How the Project Has Performed   (progress + what's done / what's in progress)
    3. The Critical Path — Then and Now
    4. Schedule Health Dashboard
    5. Risks and Opportunities
    6. Recommended Actions      (+ if-nothing-done / if-implemented)
    7. How to Verify Every Number  (+ methodology + limitations)

Every figure is computed by the engine on the spot and every statement and table row is a
:class:`~schedule_forensics.ai.citations.CitedStatement` / cited row — file + UID + task name
(the §6 contract). The configured local backend may *rephrase* prose but can never alter a
number or drop a citation (:func:`~schedule_forensics.ai.citations.reattach` re-verifies). The
briefing fabricates nothing: where the engine cannot derive a figure (e.g. a baseline critical
path from an MPP that stores only the current Critical flag), the limitation is stated, not
invented.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from schedule_forensics.ai.backend import AIBackend
from schedule_forensics.ai.citations import CitedStatement, assert_all_cited, reattach
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.engine.cpm import (
    CPMResult,
    compute_cpm,
    datetime_to_offset,
    offset_to_datetime,
)
from schedule_forensics.engine.dcma_audit import Citation, audit_schedule
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.metrics import CheckStatus
from schedule_forensics.engine.metrics._common import is_effective_critical, non_summary
from schedule_forensics.engine.metrics.schedule_card import compute_activity_makeup
from schedule_forensics.engine.path_evolution import compute_path_evolution
from schedule_forensics.engine.recommendations import Category, Finding, Severity, recommend
from schedule_forensics.engine.s_curve import compute_s_curve
from schedule_forensics.engine.trend import order_versions
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: How many rows a detail table (completed / in-progress / risks) shows before it is capped; the
#: section's prose calls out the overflow so the cap is never silent.
_TABLE_CAP = 12


@dataclass(frozen=True)
class BriefingTable:
    """A structured, cited table view of a section's figures.

    ``headers`` may be empty for a label/value profile strip. ``row_citations`` aligns 1:1 with
    ``rows`` — the §6 cited-everything contract holds for table rows exactly as for prose.
    """

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    row_citations: tuple[tuple[Citation, ...], ...]


@dataclass(frozen=True)
class BriefingSection:
    """One (sub)section of the executive briefing.

    ``level`` mirrors the numbered hierarchy (1 = "2. …", 2 = "2.1 …", 3 = "2.1.1 …") so the page
    and the Word export render the same outline. ``statements`` carry the cited prose (polished by
    the local backend); ``table`` is engine data the model never touches.
    """

    heading: str
    statements: tuple[CitedStatement, ...]
    level: int = 1
    kind: str = "prose"
    table: BriefingTable | None = None


@dataclass(frozen=True)
class ExecutiveBriefing:
    """The full leadership Executive Briefing for the loaded workbook."""

    title: str
    subtitle: str
    generated_on: dt.date
    verdict: str
    meta_rows: tuple[tuple[str, str], ...]
    banner: tuple[tuple[str, str], ...]
    sections: tuple[BriefingSection, ...] = field(default_factory=tuple)

    def to_text(self) -> str:
        parts = [f"# {self.title}", self.subtitle, f"Report generated on {_day(self.generated_on)}"]
        for label, value in self.meta_rows:
            parts.append(f"{label}: {value}")
        parts.append(f"\nVerdict: {self.verdict}")
        for label, value in self.banner:
            parts.append(f"  {label}: {value}")
        for section in self.sections:
            parts.append(f"\n{'#' * (section.level + 1)} {section.heading}")
            parts.extend(f"- {s.rendered()}" for s in section.statements)
            if section.table is not None:
                if section.table.headers:
                    parts.append("  | " + " | ".join(section.table.headers) + " |")
                for row in section.table.rows:
                    parts.append("  | " + " | ".join(row) + " |")
        return "\n".join(parts)


# --- small shared helpers ---------------------------------------------------------------------


def _day(d: dt.date) -> str:
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def _label(schedule: Schedule) -> str:
    return schedule.source_file or schedule.name


def _finish_drivers(schedule: Schedule, cpm: CPMResult) -> tuple[Citation, ...]:
    """Cite the activities that control the project finish (early finish == network finish).

    With no schedulable activities at all (a summary-only template), the first task rows are the
    terminal anchor — the §6 never-uncited invariant must hold for every statement.
    """
    by_id = schedule.tasks_by_id
    drivers = tuple(
        Citation(_label(schedule), uid, by_id[uid].name)
        for uid, t in sorted(cpm.timings.items())
        if t.early_finish == cpm.project_finish and uid in by_id
    )
    if not drivers:
        drivers = tuple(Citation(_label(schedule), t.unique_id, t.name) for t in schedule.tasks[:3])
    if not drivers:
        drivers = (Citation(schedule.source_file, 0, _label(schedule)),)
    return drivers


def _cite(schedule: Schedule, uids: tuple[int, ...]) -> tuple[Citation, ...]:
    by_id = schedule.tasks_by_id
    return tuple(
        Citation(_label(schedule), uid, by_id[uid].name if uid in by_id else "<unknown>")
        for uid in uids
    )


def _finish_dt(schedule: Schedule, cpm: CPMResult) -> dt.datetime:
    return offset_to_datetime(schedule.project_start, cpm.project_finish, schedule.calendar)


def _iso(d: dt.datetime | None) -> str:
    return d.date().isoformat() if d is not None else "—"


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def _baseline_window(tasks: list[Task]) -> tuple[dt.datetime | None, dt.datetime | None]:
    starts = [t.baseline_start for t in tasks if t.baseline_start is not None]
    finishes = [t.baseline_finish for t in tasks if t.baseline_finish is not None]
    return (min(starts) if starts else None, max(finishes) if finishes else None)


def _workday_slip(
    schedule: Schedule, cpm: CPMResult, baseline_finish: dt.datetime | None
) -> int | None:
    """Forecast finish minus baseline finish in **working days** (the forensic unit).

    The forecast finish is ``cpm.project_finish`` (already a working-minute offset from project
    start); the baseline finish is converted to the same offset on the project calendar, so the
    difference divided by the calendar's working-minutes-per-day is the slip in workdays.
    """
    if baseline_finish is None:
        return None
    per_day = schedule.calendar.working_minutes_per_day or 480
    baseline_off = datetime_to_offset(schedule.project_start, baseline_finish, schedule.calendar)
    return round((cpm.project_finish - baseline_off) / per_day)


def _slip_phrase(slip: int | None) -> str:
    if slip is None:
        return "with no baseline finish to compare against"
    if slip > 0:
        return f"{slip} workday(s) behind its baseline finish"
    if slip < 0:
        return f"{-slip} workday(s) ahead of its baseline finish"
    return "on its baseline finish"


def _var_cell(slip: int | None) -> str:
    if slip is None:
        return "no baseline"
    if slip > 0:
        return f"+{slip} wd"
    if slip < 0:
        return f"{slip} wd"
    return "on schedule"


def _wd_var(schedule: Schedule, planned: dt.datetime | None, actual: dt.datetime | None) -> str:
    """Per-activity working-day variance (actual/forecast finish vs baseline finish) for tables."""
    if planned is None or actual is None:
        return "—"
    per_day = schedule.calendar.working_minutes_per_day or 480
    a = datetime_to_offset(schedule.project_start, actual, schedule.calendar)
    p = datetime_to_offset(schedule.project_start, planned, schedule.calendar)
    delta = round((a - p) / per_day)
    return f"{delta:+d}" if delta else "0"


def _spi(schedule: Schedule, cpm: CPMResult) -> float | None:
    """Duration-based Schedule Performance Index proxy (count-based earned schedule, SPI(t))."""
    return compute_finish_forecasts(schedule, cpm).spi_t


def _verdict(slip: int | None, spi: float | None, dcma_fails: int) -> str:
    """Transparent leadership verdict (not an opaque score): ON TRACK / WATCH / AT RISK from the
    finish variance, the duration-based SPI, and the count of failing DCMA-14 checks."""
    big_slip = slip is not None and slip > 20
    low_spi = spi is not None and spi < 0.90
    if big_slip or low_spi or ((slip is not None and slip > 0) and dcma_fails >= 4):
        return "AT RISK"
    on_time = slip is not None and slip <= 0
    healthy_spi = spi is None or spi >= 0.95
    if on_time and dcma_fails == 0 and healthy_spi:
        return "ON TRACK"
    return "WATCH"


# --- section builders -------------------------------------------------------------------------


def _bottom_line(
    schedule: Schedule,
    cpm: CPMResult,
    *,
    verdict: str,
    slip: int | None,
    spi: float | None,
    dcma_fails: int,
    dcma_applicable: int,
) -> list[BriefingSection]:
    label = _label(schedule)
    finish = _finish_dt(schedule, cpm)
    drivers = _finish_drivers(schedule, cpm)
    incomplete = [t for t in non_summary(schedule) if t.percent_complete < 100.0]
    critical = [
        t
        for t in incomplete
        if t.unique_id in cpm.timings
        and is_effective_critical(t, cpm.timings[t.unique_id].total_float)
    ]
    one_liner = CitedStatement(
        f"In one sentence: {label} is forecast to finish on {_day(finish.date())}, "
        f"{_slip_phrase(slip)}, and the schedule is {verdict}. The slip — if any — is carried by "
        f"the {len(critical)} incomplete critical activit(ies) that control the finish date, and "
        f"{dcma_fails} of {dcma_applicable} applicable DCMA-14 quality checks are failing.",
        drivers,
    )
    roadmap = CitedStatement(
        "This briefing explains what the schedule says, what it means, what is at risk, where the "
        "opportunities are, and what to do about it — written for leadership without a scheduling "
        "background. Every figure below is traceable to a specific activity by its Unique ID, "
        "shown in brackets; hand this report to a planner with the source schedule and any number "
        "can be verified in minutes (Section 7).",
        drivers,
    )
    as_of = (
        f"data date {_day(schedule.status_date.date())}"
        if schedule.status_date
        else "the latest update"
    )
    story = CitedStatement(
        "Think of the project as a train on a single track. The track is the critical path — the "
        "chain of activities where any delay pushes the final finish date out one-for-one. "
        "Activities off that track have float (slack) and can slip a little without moving the "
        f"end date. As of {as_of}, {len(critical)} of {len(incomplete)} unfinished activities are "
        "on the critical track, so that is where management attention earns the most back.",
        _cite(schedule, tuple(t.unique_id for t in critical[:10])) or drivers,
    )
    if spi is not None:
        number = CitedStatement(
            f"The single most important number is the Schedule Performance Index (SPI): {spi:.3f}. "
            "An SPI at or above 0.95 is generally read as on track; below about 0.90 is where "
            "formal corrective action usually activates. This SPI is a duration-based proxy "
            "(earned schedule), not an earned-value cost SPI — the two are normally close on a "
            "schedule-only review like this one.",
            drivers,
        )
    else:
        number = CitedStatement(
            "A Schedule Performance Index could not be computed (it needs a data date and baseline "
            "finishes). The finish variance above is the headline measure instead: "
            f"{_slip_phrase(slip)}.",
            drivers,
        )
    return [
        BriefingSection("1. The Bottom Line", (one_liner, roadmap), level=1, kind="bottomline"),
        BriefingSection("1.1 The Story in Plain English", (story,), level=2),
        BriefingSection("1.2 The Single Most Important Number", (number,), level=2),
    ]


def _performance(schedule: Schedule, cpm: CPMResult) -> list[BriefingSection]:
    label = _label(schedule)
    makeup = compute_activity_makeup(schedule)
    tasks = non_summary(schedule)
    drivers = _finish_drivers(schedule, cpm)
    # the S-curve needs at least one finish date; a date-less template has no curve to read
    has_dates = any(t.finish is not None or t.baseline_finish is not None for t in tasks)
    planned_pct: float | None = None
    actual_pct: float | None = None
    if has_dates:
        curve = compute_s_curve([schedule]).versions[0]
        idx = curve.status_index
        if idx is not None and idx < len(curve.planned):
            planned_pct = curve.planned[idx]
            actual_pct = curve.actual[idx]
    if planned_pct is not None and actual_pct is not None:
        gap = actual_pct - planned_pct
        track = (
            "tracking ahead of plan"
            if gap > 1
            else "tracking behind plan"
            if gap < -1
            else "tracking on plan"
        )
        curve_txt = (
            f" Against the S-curve, cumulative completion is {actual_pct:.1f}% versus a planned "
            f"{planned_pct:.1f}% at the data date — {track}."
        )
    else:
        curve_txt = ""
    overview = CitedStatement(
        f"{label} contains {makeup.normal} activities (plus {makeup.milestones} milestone(s) and "
        f"{makeup.summaries} summaries). {makeup.complete} are complete "
        f"({_pct(makeup.complete, makeup.total)}%), {makeup.in_progress} are in progress "
        f"({_pct(makeup.in_progress, makeup.total)}%), and {makeup.planned} are not yet started "
        f"({_pct(makeup.planned, makeup.total)}%).{curve_txt}",
        drivers,
    )
    sections = [BriefingSection("2. How the Project Has Performed", (overview,), level=1)]

    done = [t for t in tasks if t.percent_complete >= 100.0]
    done_sorted = sorted(done, key=lambda t: t.actual_finish or t.finish or dt.datetime.max)
    done_rows = tuple(
        (
            str(t.unique_id),
            t.name,
            _iso(t.baseline_finish),
            _iso(t.actual_finish or t.finish),
            _wd_var(schedule, t.baseline_finish, t.actual_finish or t.finish),
        )
        for t in done_sorted[:_TABLE_CAP]
    )
    overflow_done = (
        f" Showing the first {_TABLE_CAP} of {len(done)}." if len(done) > _TABLE_CAP else ""
    )
    done_stmt = CitedStatement(
        f"{len(done)} activit(ies) are complete, totaling {_pct(makeup.complete, makeup.total)}% "
        f"of the project by count.{overflow_done}",
        _cite(schedule, tuple(t.unique_id for t in done_sorted[:10])) or drivers,
    )
    sections.append(
        BriefingSection(
            "2.1 What Has Been Accomplished",
            (done_stmt,),
            level=2,
            table=BriefingTable(
                headers=("UID", "Activity", "Baseline Finish", "Actual Finish", "Var (wd)"),
                rows=done_rows,
                row_citations=tuple(
                    _cite(schedule, (t.unique_id,)) for t in done_sorted[:_TABLE_CAP]
                ),
            ),
        )
    )

    wip = [t for t in tasks if 0.0 < t.percent_complete < 100.0]
    wip_sorted = sorted(wip, key=lambda t: -t.percent_complete)
    wip_rows = tuple(
        (
            str(t.unique_id),
            t.name,
            f"{t.percent_complete:g}%",
            _iso(t.baseline_finish),
            _wd_var(schedule, t.baseline_finish, t.finish),
            "YES"
            if (
                t.unique_id in cpm.timings
                and is_effective_critical(t, cpm.timings[t.unique_id].total_float)
            )
            else "No",
        )
        for t in wip_sorted[:_TABLE_CAP]
    )
    overflow_wip = (
        f" Showing the first {_TABLE_CAP} of {len(wip)}." if len(wip) > _TABLE_CAP else ""
    )
    wip_stmt = CitedStatement(
        f"{len(wip)} activit(ies) are in progress — work started but not closed by the data date. "
        "The ones on the critical path (On CP? = YES) are the focus area, because their finish "
        f"variance moves the project finish directly.{overflow_wip}",
        _cite(schedule, tuple(t.unique_id for t in wip_sorted[:10])) or drivers,
    )
    sections.append(
        BriefingSection(
            "2.2 What Is In Progress",
            (wip_stmt,),
            level=2,
            table=BriefingTable(
                headers=("UID", "Activity", "% Comp", "Baseline Finish", "Var (wd)", "On CP?"),
                rows=wip_rows,
                row_citations=tuple(
                    _cite(schedule, (t.unique_id,)) for t in wip_sorted[:_TABLE_CAP]
                ),
            ),
        )
    )
    return sections


def _critical_path(schedules: list[Schedule], cpms: list[CPMResult]) -> list[BriefingSection]:
    schedule, cpm = schedules[-1], cpms[-1]
    drivers = _finish_drivers(schedule, cpm)
    critical_uids = tuple(
        t.unique_id
        for t in non_summary(schedule)
        if t.unique_id in cpm.timings and cpm.timings[t.unique_id].is_critical
    )
    intro = CitedStatement(
        "The critical path is the longest chain of dependent activities through the project; a "
        "delay on any of them moves the finish date one-for-one. Everything else has float. "
        f"The current critical path contains {len(critical_uids)} activit(ies).",
        _cite(schedule, critical_uids[:10]) or drivers,
    )
    sections = [BriefingSection("3. The Critical Path — Then and Now", (intro,), level=1)]

    if len(schedules) >= 2:
        snap = compute_path_evolution(schedules, cpms).snapshots[-1]
        entered_rows = tuple(
            (
                str(uid),
                schedule.tasks_by_id[uid].name if uid in schedule.tasks_by_id else "<unknown>",
            )
            for uid in snap.entered
        )
        left_prior = schedules[-2]
        left_rows = tuple(
            (
                str(uid),
                left_prior.tasks_by_id[uid].name if uid in left_prior.tasks_by_id else "<unknown>",
            )
            for uid in snap.left
        )
        change_stmt = CitedStatement(
            f"Comparing the two most recent versions, {len(snap.stayed)} of {len(snap.critical)} "
            f"critical activities are unchanged. {len(snap.entered)} moved onto the critical path "
            f"and {len(snap.left)} moved off — a measure of how stable the plan is.",
            _cite(schedule, snap.critical[:10]) or drivers,
        )
        sub = BriefingSection("3.1 What Changed Between the Versions", (change_stmt,), level=2)
        sections.append(sub)
        if entered_rows:
            sections.append(
                BriefingSection(
                    "Newly Critical",
                    (),
                    level=3,
                    table=BriefingTable(
                        ("UID", "Activity"),
                        entered_rows,
                        tuple(_cite(schedule, (uid,)) for uid in snap.entered),
                    ),
                )
            )
        if left_rows:
            sections.append(
                BriefingSection(
                    "No Longer Critical",
                    (),
                    level=3,
                    table=BriefingTable(
                        ("UID", "Activity"),
                        left_rows,
                        tuple(_cite(left_prior, (uid,)) for uid in snap.left),
                    ),
                )
            )
    else:
        note = CitedStatement(
            "Only one schedule version is loaded, so a baseline-vs-current critical-path "
            "comparison is not available: MPP/XER files store only the current Critical flag, and "
            "the tool does not reconstruct a baseline critical path from baseline durations "
            "(Section 7.2). Load an earlier version to see which activities moved onto or off the "
            "critical path over time.",
            drivers,
        )
        sections.append(BriefingSection("3.1 What Changed", (note,), level=2))
    return sections


def _dashboard(
    schedule: Schedule,
    cpm: CPMResult,
    *,
    slip: int | None,
    spi: float | None,
    dcma_fails: int,
    dcma_applicable: int,
) -> list[BriefingSection]:
    makeup = compute_activity_makeup(schedule)
    drivers = _finish_drivers(schedule, cpm)
    spi_reading = f"{spi:.3f}" if spi is not None else "n/a"
    spi_status = (
        "—"
        if spi is None
        else "green (>= 0.95)"
        if spi >= 0.95
        else "amber (0.90-0.95)"
        if spi >= 0.90
        else "red (< 0.90)"
    )
    rows = (
        (
            "Task status",
            f"{makeup.complete} done / {makeup.in_progress} in progress / {makeup.planned} planned",
            "—",
        ),
        (
            "Schedule slippage",
            "no baseline" if slip is None else f"{slip:+d} workdays vs baseline finish",
            "green"
            if (slip is not None and slip <= 0)
            else "amber"
            if (slip is not None and slip <= 20)
            else "red",
        ),
        ("Schedule Performance Index", spi_reading, spi_status),
        (
            "DCMA-14 quality",
            f"{dcma_fails} of {dcma_applicable} checks failing",
            "green" if dcma_fails == 0 else "amber" if dcma_fails <= 3 else "red",
        ),
    )
    stmt = CitedStatement(
        "Four indicators summarize the schedule's health at a glance — task status, schedule "
        "slippage, the duration-based SPI, and the DCMA-14 quality checks.",
        drivers,
    )
    return [
        BriefingSection(
            "4. Schedule Health Dashboard",
            (stmt,),
            level=1,
            table=BriefingTable(
                ("Indicator", "Reading", "Status"),
                rows,
                tuple(drivers for _ in rows),
            ),
        )
    ]


def _risks_opportunities(
    schedule: Schedule, findings: tuple[Finding, ...]
) -> list[BriefingSection]:
    drivers_anchor = (Citation(schedule.source_file, 0, _label(schedule)),)
    risks = [f for f in findings if f.category in (Category.RISK, Category.CONCERN)]
    opps = [f for f in findings if f.category is Category.OPPORTUNITY]
    intro = CitedStatement(
        f"The engine flags {len(risks)} risk(s) and {len(opps)} opportunit(ies) from the "
        "schedule's logic, float, baseline movement, and DCMA exceptions. Each is tied to specific "
        "activities by Unique ID.",
        risks[0].citations if risks else opps[0].citations if opps else drivers_anchor,
    )
    sections = [BriefingSection("5. Risks and Opportunities", (intro,), level=1)]

    risk_rows = tuple(
        (
            f"R-{i + 1}",
            f.title,
            ", ".join(str(c.unique_id) for c in f.citations[:6]) or "—",
            f.severity.name,
            f.detail,
        )
        for i, f in enumerate(risks[:_TABLE_CAP])
    )
    risk_stmt = CitedStatement(
        f"{len(risks)} risk(s) are tracked, ordered by severity."
        + (f" Showing the first {_TABLE_CAP}." if len(risks) > _TABLE_CAP else "")
        if risks
        else "No risks were flagged for this schedule at the current thresholds.",
        risks[0].citations if risks else drivers_anchor,
    )
    sections.append(
        BriefingSection(
            "5.1 Risk Register",
            (risk_stmt,),
            level=2,
            table=BriefingTable(
                ("ID", "Risk", "UIDs", "Severity", "Notes"),
                risk_rows,
                tuple(f.citations or drivers_anchor for f in risks[:_TABLE_CAP]),
            )
            if risk_rows
            else None,
        )
    )

    opp_rows = tuple(
        (
            f"O-{i + 1}",
            f.title,
            ", ".join(str(c.unique_id) for c in f.citations[:6]) or "—",
            f"{f.impact_days:g} wd" if f.impact_days is not None else "risk reduction",
        )
        for i, f in enumerate(opps[:_TABLE_CAP])
    )
    opp_stmt = CitedStatement(
        f"{len(opps)} opportunit(ies) exist to recover slip or reduce downstream risk."
        if opps
        else "No discrete recovery opportunities were flagged at the current thresholds.",
        opps[0].citations if opps else drivers_anchor,
    )
    sections.append(
        BriefingSection(
            "5.2 Opportunities",
            (opp_stmt,),
            level=2,
            table=BriefingTable(
                ("ID", "Opportunity", "UIDs", "Potential recovery"),
                opp_rows,
                tuple(f.citations or drivers_anchor for f in opps[:_TABLE_CAP]),
            )
            if opp_rows
            else None,
        )
    )
    return sections


_SEV_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}


def _recommended_actions(
    schedule: Schedule, findings: tuple[Finding, ...], slip: int | None
) -> list[BriefingSection]:
    drivers_anchor = (Citation(schedule.source_file, 0, _label(schedule)),)
    actionable = sorted(
        (f for f in findings if f.course_of_action),
        key=lambda f: _SEV_ORDER.get(f.severity, 9),
    )
    rows = tuple(
        (
            str(i + 1),
            f.course_of_action,
            ", ".join(str(c.unique_id) for c in f.citations[:6]) or "—",
            f"{f.impact_days:g} wd" if f.impact_days is not None else "risk mitigation",
        )
        for i, f in enumerate(actionable[:_TABLE_CAP])
    )
    intro = CitedStatement(
        "The actions below are listed in priority (severity) order, each paired with the "
        "activities it targets and its expected schedule effect. They are engine-derived from the "
        "same findings in Section 5; an analyst should confirm owners and dates before issuing."
        if actionable
        else "No corrective actions are indicated at the current thresholds — maintain the plan "
        "and re-check at the next update.",
        actionable[0].citations if actionable else drivers_anchor,
    )
    sections = [
        BriefingSection(
            "6. Recommended Actions",
            (intro,),
            level=1,
            table=BriefingTable(
                ("#", "Action", "Targets UIDs", "Expected effect"),
                rows,
                tuple(f.citations or drivers_anchor for f in actionable[:_TABLE_CAP]),
            )
            if rows
            else None,
        )
    ]
    floor = (
        "the current slip is the floor, not the ceiling"
        if (slip is not None and slip > 0)
        else "the schedule currently forecasts no slip, but that assumes the remaining work "
        "executes to plan"
    )
    nothing = CitedStatement(
        f"If no corrective action is taken, {floor}. The forecast assumes the rest of the project "
        "runs exactly per plan from here; that assumption weakens wherever upcoming critical work "
        "has no adjacent float (a delivery or interface delay there becomes a day-for-day project "
        "slip).",
        drivers_anchor,
    )
    recoverable = sum(
        f.impact_days
        for f in findings
        if f.category is Category.OPPORTUNITY and f.impact_days is not None
    )
    implemented = CitedStatement(
        f"If the opportunities in Section 5.2 are implemented, up to about {recoverable:g} "
        "workday(s) of slip are potentially recoverable; the risk-mitigation actions do not "
        "recover slip directly but reduce the chance of new slip during the higher-risk phases "
        "ahead."
        if recoverable
        else "The flagged actions are risk-mitigation rather than direct slip recovery: they "
        "reduce the chance of new slip rather than pulling the finish date in.",
        drivers_anchor,
    )
    sections.append(BriefingSection("6.1 If Nothing Is Done", (nothing,), level=2))
    sections.append(
        BriefingSection("6.2 If Recommended Actions Are Implemented", (implemented,), level=2)
    )
    return sections


def _verify(schedules: list[Schedule]) -> list[BriefingSection]:
    anchor = tuple(Citation(s.source_file, 0, _label(s)) for s in schedules)
    files = ", ".join(_label(s) for s in schedules)
    steps = CitedStatement(
        f"This report is built directly from the source schedule(s): {files}. Every claim cites a "
        "specific activity by Unique ID. To verify any number: (1) open the source schedule in "
        "Microsoft Project or a compatible viewer; (2) show the Unique ID column; (3) find the UID "
        "cited here; (4) compare its Baseline Start/Finish to its Start/Finish to confirm the "
        "stated variance; (5) filter Critical = Yes to reproduce the critical-path activities in "
        "Section 3.",
        anchor,
    )
    methodology = CitedStatement(
        "Methodology: variances are computed in working days on each schedule's own calendar. The "
        "current critical path is taken from the schedule's stored Critical flag where present, "
        "falling back to the tool's CPM (forward/backward pass, zero-float threshold). The "
        "Schedule Performance Index is a duration-based earned-schedule proxy. All figures are "
        "recomputed by the engine on load — nothing is cached or hand-entered.",
        anchor,
    )
    limitations = CitedStatement(
        "Limitations: MPP/XER files store only the current Critical flag, so a baseline critical "
        "path is not natively available and the then-vs-now comparison needs two loaded versions. "
        "Working-day counts assume each schedule's stated calendar; task-specific calendars may "
        "shift an individual activity's variance by a day or two. The SPI is duration-based, not "
        "an earned-value cost SPI, and unless cost/earned-value data is present this review is "
        "schedule-only.",
        anchor,
    )
    return [
        BriefingSection("7. How to Verify Every Number", (steps,), level=1),
        BriefingSection("7.1 Methodology", (methodology,), level=2),
        BriefingSection("7.2 Limitations", (limitations,), level=2),
    ]


# --- orchestration ----------------------------------------------------------------------------


def _empty_briefing(ordered: list[Schedule], report_day: dt.date) -> ExecutiveBriefing:
    cite = tuple(Citation(s.source_file, 0, _label(s)) for s in ordered)
    text = (
        f"No schedulable activities are in scope across the {len(ordered)} loaded version(s) — a "
        "filter or selection matched nothing, so there is nothing to brief."
    )
    return ExecutiveBriefing(
        title="Schedule Forensics — Executive Briefing",
        subtitle="Forensic Schedule Health Review",
        generated_on=report_day,
        verdict="N/A",
        meta_rows=(("Report date", _day(report_day)),),
        banner=(("Status", "no schedulable activities in scope"),),
        sections=(BriefingSection("1. The Bottom Line", (CitedStatement(text, cite),), level=1),),
    )


def build_briefing(
    schedules: list[Schedule],
    *,
    backend: AIBackend | None = None,
    cpms: list[CPMResult] | None = None,
    today: dt.date | None = None,
) -> ExecutiveBriefing:
    """Build the cited leadership Executive Briefing for the loaded version(s).

    Versions are ordered by data date (oldest first); the newest is the subject of the report.
    With two or more versions, Section 3 shows a real critical-path then-vs-now. ``backend``
    (default offline Null) may rephrase the prose; citations are re-attached and re-verified.
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

    if not any(any(not t.is_summary for t in s.tasks) for s in ordered):
        return _empty_briefing(ordered, report_day)

    subject, subject_cpm = ordered[-1], cpm_list[-1]
    label = _label(subject)
    tasks = non_summary(subject)
    _, baseline_finish = _baseline_window(tasks)
    finish = _finish_dt(subject, subject_cpm)
    slip = _workday_slip(subject, subject_cpm, baseline_finish)
    spi = _spi(subject, subject_cpm)
    audit = audit_schedule(subject, subject_cpm)
    applicable = [c for c in audit.checks if c.status is not CheckStatus.NOT_APPLICABLE]
    dcma_fails = sum(1 for c in applicable if c.status is CheckStatus.FAIL)
    verdict = _verdict(slip, spi, dcma_fails)
    prior = ordered[-2] if len(ordered) >= 2 else None
    prior_cpm = cpm_list[-2] if len(ordered) >= 2 else None
    findings = recommend(subject, prior, current_cpm=subject_cpm, prior_cpm=prior_cpm)

    meta_rows = (
        ("Report date", _day(report_day)),
        (
            "Schedule data date",
            _day(subject.status_date.date()) if subject.status_date else "not statused",
        ),
        ("Source schedule", label),
        ("Versions loaded", str(len(ordered))),
        ("Classification", "Internal — management use; verify against the source schedule"),
    )
    banner = (
        ("Status", verdict),
        ("SPI (duration-based)", f"{spi:.3f}" if spi is not None else "n/a"),
        ("Forecast finish", _day(finish.date())),
        (
            "Baseline finish",
            _day(baseline_finish.date()) if baseline_finish else "no baseline",
        ),
        ("Slip", _var_cell(slip)),
    )

    sections: list[BriefingSection] = []
    sections += _bottom_line(
        subject,
        subject_cpm,
        verdict=verdict,
        slip=slip,
        spi=spi,
        dcma_fails=dcma_fails,
        dcma_applicable=len(applicable),
    )
    sections += _performance(subject, subject_cpm)
    sections += _critical_path(ordered, cpm_list)
    sections += _dashboard(
        subject,
        subject_cpm,
        slip=slip,
        spi=spi,
        dcma_fails=dcma_fails,
        dcma_applicable=len(applicable),
    )
    sections += _risks_opportunities(subject, findings)
    sections += _recommended_actions(subject, findings, slip)
    sections += _verify(ordered)

    be: AIBackend = backend if backend is not None else NullBackend()
    polished_sections: list[BriefingSection] = []
    for section in sections:
        assert_all_cited(section.statements)
        polished = tuple(be.generate(s.text) for s in section.statements)
        polished_sections.append(
            BriefingSection(
                section.heading,
                reattach(polished, section.statements),
                level=section.level,
                kind=section.kind,
                table=section.table,  # tables are engine data — the model never touches them
            )
        )
    return ExecutiveBriefing(
        title="Schedule Forensics — Executive Briefing",
        subtitle="Forensic Schedule Health Review & Corrective-Action Outlook",
        generated_on=report_day,
        verdict=verdict,
        meta_rows=meta_rows,
        banner=banner,
        sections=tuple(polished_sections),
    )


def briefing_blocks(briefing: ExecutiveBriefing) -> list[object]:
    """The briefing as Word blocks (reports.docx) — the same content as the page, verbatim, so a
    leader can hand out a .docx that matches the on-screen Executive Briefing."""
    from schedule_forensics.reports.docx import DocTable, Heading, Paragraph

    blocks: list[object] = [
        Heading(briefing.title, level=0),
        Paragraph(briefing.subtitle, italic=True),
        Paragraph(f"Report generated on {briefing.generated_on.strftime('%A, %B %d, %Y')}."),
    ]
    for label, value in briefing.meta_rows:
        blocks.append(Paragraph(value, lead=f"{label}:"))
    blocks.append(Paragraph(briefing.verdict, lead="Overall status:"))
    blocks.append(DocTable(("Indicator", "Reading"), tuple(briefing.banner)))
    for section in briefing.sections:
        blocks.append(Heading(section.heading, level=min(max(section.level, 1), 4)))
        for stmt in section.statements:
            blocks.append(Paragraph(stmt.rendered()))
        if section.table is not None and section.table.rows:
            blocks.append(DocTable(section.table.headers, section.table.rows))
    return blocks
