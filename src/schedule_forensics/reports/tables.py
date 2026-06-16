"""Neutral tabular model + builders — the data behind every chart/table, exportable.

Every analytical view reduces to a :class:`TableSet` (an ordered list of titled
tables), which the Word (:mod:`.docx`) and Excel (:mod:`.xlsx`) renderers serialize.
Builders take engine/model objects (or the web layer's already-built row dicts) so the
web layer stays the only place that knows about sessions. Cell values are plain
``str | int | float | None`` — renderers handle the rest. All local (Law 1: exports
are downloads to the operator's own machine).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from schedule_forensics.engine.bow_wave import BowWave
from schedule_forensics.engine.dcma_audit import ScheduleAudit
from schedule_forensics.engine.forecast import CarnacSummary, ForecastSet
from schedule_forensics.engine.metrics._common import MetricResult
from schedule_forensics.engine.metrics.wbs_breakdown import WBSGroup
from schedule_forensics.engine.month_curves import MonthCurves
from schedule_forensics.engine.path_evolution import PathEvolution
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.engine.trend import MetricTrend
from schedule_forensics.model.schedule import Schedule

Cell = str | int | float | None


@dataclass(frozen=True)
class Table:
    """One titled table: headers + uniform rows."""

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[Cell, ...], ...]


@dataclass(frozen=True)
class TableSet:
    """An ordered, titled collection of tables (one export artifact)."""

    title: str
    tables: tuple[Table, ...]


# --- single-schedule report ------------------------------------------------------------


def schedule_summary_table(schedule: Schedule) -> Table:
    cal = schedule.calendar
    weekdays = "".join("MTWTFSS"[d] for d in cal.work_weekdays)
    rows: tuple[tuple[Cell, ...], ...] = (
        ("Schedule", schedule.name),
        ("Source file", schedule.source_file),
        ("Project start", schedule.project_start.date().isoformat()),
        (
            "Status (data) date",
            schedule.status_date.date().isoformat() if schedule.status_date else "none",
        ),
        ("Activities (incl. summaries)", len(schedule.tasks)),
        ("Calendar", cal.name),
        ("Working minutes/day", cal.working_minutes_per_day),
        ("Work week", weekdays),
        ("Holidays", len(cal.holidays)),
    )
    return Table("Schedule summary", ("Item", "Value"), rows)


def dcma_table(audit: ScheduleAudit) -> Table:
    rows = tuple(
        (
            c.name,
            str(c.status),
            c.count,
            c.population,
            round(c.value, 2),
            c.unit,
            ", ".join(str(x.unique_id) for x in c.citations[:12]),
        )
        for c in audit.checks
    )
    return Table(
        "DCMA 14-point assessment",
        ("Check", "Status", "Count", "Population", "Value", "Unit", "Offender UIDs"),
        rows,
    )


def metric_results_table(title: str, results: Mapping[str, MetricResult]) -> Table:
    rows = tuple(
        (
            r.name,
            str(r.status),
            r.count,
            r.population,
            round(r.value, 2),
            r.unit,
            ", ".join(str(u) for u in r.offender_uids[:12]),
        )
        for r in results.values()
    )
    return Table(
        title,
        ("Metric", "Status", "Count", "Population", "Value", "Unit", "Offender UIDs"),
        rows,
    )


def findings_table(findings: Sequence[Finding]) -> Table:
    rows = tuple(
        (
            str(f.severity),
            str(f.category),
            f.title,
            f.course_of_action,
            "; ".join(f"{c.task_name} (UID {c.unique_id})" for c in f.citations[:6]),
            f.citations[0].source_file if f.citations else None,
        )
        for f in findings
    )
    return Table(
        "Findings",
        ("Severity", "Category", "Finding", "Course of action", "Citations", "Schedule"),
        rows,
    )


_ACTIVITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("unique_id", "UID"),
    ("name", "Name"),
    ("wbs", "WBS"),
    ("start", "Start"),
    ("finish", "Finish"),
    ("baseline_start", "Baseline start"),
    ("baseline_finish", "Baseline finish"),
    ("duration_days", "Duration (d)"),
    ("total_float_days", "Total float (d)"),
    ("free_float_days", "Free float (d)"),
    ("percent_complete", "% complete"),
    ("is_critical", "Critical"),
    ("is_milestone", "Milestone"),
    ("resource_names", "Resources"),
)


def activities_table(rows: Iterable[Mapping[str, object]]) -> Table:
    out = []
    for r in rows:
        out.append(tuple(_cell(r.get(key)) for key, _ in _ACTIVITY_COLUMNS))
    return Table("Activities", tuple(label for _, label in _ACTIVITY_COLUMNS), tuple(out))


_DRIVING_COLUMNS: tuple[tuple[str, str], ...] = (
    ("unique_id", "UID"),
    ("name", "Name"),
    ("wbs", "WBS"),
    ("tier", "Tier"),
    ("driving_slack_days", "Driving slack (d)"),
    ("start", "Start"),
    ("finish", "Finish"),
    ("baseline_finish", "Baseline finish"),
    ("duration_days", "Duration (d)"),
    ("total_float_days", "Total float (d)"),
    ("percent_complete", "% complete"),
    ("resource_names", "Resources"),
)


def driving_table(rows: Iterable[Mapping[str, object]], target_uid: int) -> Table:
    out = tuple(tuple(_cell(r.get(key)) for key, _ in _DRIVING_COLUMNS) for r in rows)
    return Table(
        f"Path analysis to UID {target_uid}",
        tuple(label for _, label in _DRIVING_COLUMNS),
        out,
    )


# --- multi-version views ---------------------------------------------------------------


def trend_tables(trends: Sequence[MetricTrend]) -> tuple[Table, ...]:
    """Overview (metric x version) + worst-version + the full per-version offender series.

    The third table is the M18 item-8 drill-down: one row per (metric, version) carrying
    the count and the complete offender-activity UID list for that version (no cap — the
    operator's machine, Law 1), so the offenders behind every trended number are auditable
    in Excel/Word, not just on screen.
    """
    if not trends:
        return ()
    labels = trends[0].labels
    overview = Table(
        "Schedule-quality trend",
        ("Metric", *labels),
        tuple((t.name, *t.values) for t in trends),
    )
    worst = Table(
        "Worst version per metric",
        ("Metric", "Worst version", "Offender UIDs (worst version)"),
        tuple(
            (
                t.name,
                t.labels[t.worst_index] if t.worst_index is not None else "n/a (flat)",
                ", ".join(str(u) for u in t.worst_offender_uids),
            )
            for t in trends
        ),
    )
    series_rows: list[tuple[Cell, ...]] = []
    for t in trends:
        for label, offenders in zip(t.labels, t.offenders_by_version, strict=False):
            series_rows.append(
                (t.name, label, len(offenders), ", ".join(str(u) for u in offenders))
            )
    offenders_series = Table(
        "Quality offenders by version",
        ("Metric", "Version", "Offending activities", "Offender UIDs"),
        tuple(series_rows),
    )
    return (overview, worst, offenders_series)


def bow_wave_tables(wave: BowWave) -> tuple[Table, ...]:
    """The CEI table + every snapshot's monthly finish profile (the chart's data)."""
    cei = Table(
        "CEI - Current Execution Index",
        ("Snapshot", "Period", "Previously planned", "Re-scheduled", "Completed on time", "CEI"),
        tuple(
            (s.label, s.cei_period, s.cei_planned, s.cei_scheduled, s.cei_finished, s.cei)
            for s in wave.snapshots
        ),
    )
    profiles = []
    for s in wave.snapshots:
        profiles.append(
            Table(
                f"Monthly finishes - {s.label}",
                ("Month", "Baselined to finish", "Scheduled to finish", "Actually finished"),
                tuple(
                    (month, b, sch, f)
                    for month, b, sch, f in zip(
                        wave.month_labels, s.baselined, s.scheduled, s.finished, strict=True
                    )
                ),
            )
        )
    return (cei, *profiles)


def month_curves_tables(curves: MonthCurves) -> tuple[Table, ...]:
    """Per-version monthly start/finish curves (the Finishes / Slippage chart data)."""
    tables: list[Table] = []
    for v in curves.versions:
        tables.append(
            Table(
                f"Monthly start/finish curves - {v.label}",
                (
                    "Month",
                    "Baseline finishes",
                    "Actual finishes",
                    "Baseline starts",
                    "Actual starts",
                ),
                tuple(
                    (month, bf, af, bs, as_)
                    for month, bf, af, bs, as_ in zip(
                        curves.month_labels,
                        v.baseline_finishes,
                        v.actual_finishes,
                        v.baseline_starts,
                        v.actual_starts,
                        strict=True,
                    )
                ),
            )
        )
    return tuple(tables)


def wbs_breakdown_tables(groups: Sequence[WBSGroup]) -> tuple[Table, ...]:
    """Two WBS pivots: completion-by-WBS and SPI(t)/Earned-Schedule-by-WBS."""
    completion = Table(
        "Completion metrics by WBS",
        (
            "WBS",
            "Total",
            "Completed",
            "To go",
            "% complete",
            "Ahead",
            "On schedule",
            "Behind",
            "Avg days ahead",
            "Avg days late",
            "Avg variance",
            "Longer",
            "Shorter",
            "Dur ratio min",
            "Dur ratio avg",
            "Dur ratio max",
        ),
        tuple(
            (
                g.wbs,
                g.total,
                g.completed,
                g.not_completed,
                g.percent_complete,
                g.completed_ahead,
                g.completed_on_schedule,
                g.completed_behind,
                g.avg_days_ahead,
                g.avg_days_late,
                g.avg_completion_variance,
                g.longer_than_planned,
                g.shorter_than_planned,
                g.duration_ratio_min,
                g.duration_ratio_avg,
                g.duration_ratio_max,
            )
            for g in groups
        ),
    )
    earned = Table(
        "SPI(t) and Earned Schedule by WBS",
        (
            "WBS",
            "SPI(t)",
            "Earned schedule (working days)",
            "Actual time (working days)",
            "Completed",
        ),
        tuple(
            (g.wbs, g.spi_t, g.earned_schedule_days, g.actual_time_days, g.completed)
            for g in groups
        ),
    )
    return (completion, earned)


def carnac_table(summary: CarnacSummary) -> Table:
    """The deck's Carnac forecast KPI cards as a two-column table (label/value)."""

    def d(value: dt.date | None) -> Cell:
        return value.isoformat() if value is not None else None

    rows: tuple[tuple[Cell, ...], ...] = (
        ("Earliest start", d(summary.earliest_start)),
        ("Latest finish (CPM)", d(summary.latest_finish)),
        ("Project duration (working days)", summary.project_duration_days),
        ("Forecasted end date (rate)", d(summary.forecasted_end)),
        ("Estimated end date (ES, to-go)", d(summary.estimated_end_es)),
        ("Avg tasks per month", summary.avg_tasks_per_month),
        ("Remaining duration (working days)", summary.remaining_duration_days),
        ("SPI(t)", summary.spi_t),
        ("Earned schedule (working days)", summary.earned_schedule_days),
        ("Tasks to complete (to-go)", summary.to_go_count),
    )
    return Table("Forecast summary (Carnac)", ("Card", "Value"), rows)


def path_evolution_tables(evolution: PathEvolution) -> tuple[Table, ...]:
    """Per-version critical-path evolution: size, finish move, entered/left, optics."""
    rows: tuple[tuple[Cell, ...], ...] = tuple(
        (
            s.label,
            s.status_date,
            s.project_finish,
            s.finish_delta_days,
            len(s.critical),
            len(s.entered),
            len(s.left),
            len(s.duration_changed),
            len(s.shortened_on_path),
            s.removed_logic_count,
        )
        for s in evolution.snapshots
    )
    return (
        Table(
            "Critical-path evolution",
            (
                "Version",
                "Data date",
                "Project finish",
                "Finish move (days)",
                "Critical count",
                "Entered path",
                "Left path",
                "Duration changed on path",
                "Shortened on path",
                "Logic links removed",
            ),
            rows,
        ),
    )


def forecast_tables(labels: Sequence[str], sets: Sequence[ForecastSet]) -> tuple[Table, ...]:
    rows = []
    for label, fs in zip(labels, sets, strict=True):
        for f in fs.forecasts:
            rows.append((label, f.name, f.finish.isoformat() if f.finish else "n/a", f.basis))
    methods = Table(
        "Finish forecasts (three methods)",
        ("Version", "Method", "Forecast finish", "Basis"),
        tuple(rows),
    )
    return (methods,)


def _cell(value: object) -> Cell:
    if value is None or isinstance(value, (str, int, float)):
        return value
    if isinstance(value, bool):  # pragma: no cover - bool is int subclass, kept explicit
        return "yes" if value else "no"
    return str(value)
