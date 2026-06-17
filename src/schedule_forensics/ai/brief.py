"""The Diagnostic Brief — a cited story of outliers, conflicts, and questions (M18).

Not a report card: the report page already grades every metric. This module reads the
loaded versions the way a forensic scheduler would — *what moved, what contradicts
itself, what deserves a question* — and writes it as plain-English narrative where
every sentence carries its citations (schedule + UniqueID + task name, §6). The Word
export renders the same content through :mod:`schedule_forensics.reports.docx`; the
layout follows the operator's Fuse-generated "Diagnostic Executive Briefing" example
(prose summary → the finish story → questions), per the M18 work order.

Everything is engine-computed and deterministic. AI may later *rephrase* the prose
(M18 item h), never the numbers.
"""

from __future__ import annotations

import datetime as dt
import itertools
from dataclasses import dataclass

from schedule_forensics.ai.citations import CitedStatement
from schedule_forensics.engine.bow_wave import compute_bow_wave
from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.reports.tables import Table

#: A completed activity whose actual duration is at least this multiple of its
#: baseline duration is a stretch outlier worth a question.
DURATION_STRETCH_RATIO = 2.0
#: Forecast methods disagreeing by more than this many calendar days is a question.
FORECAST_SPREAD_DAYS = 45
#: Total float above this many working days usually means missing logic (DCMA-06).
HIGH_FLOAT_DAYS = 44


@dataclass(frozen=True)
class BriefSection:
    """One brief section: a heading, cited prose, and an optional data table."""

    heading: str
    paragraphs: tuple[CitedStatement, ...]
    table: Table | None = None


@dataclass(frozen=True)
class DiagnosticBrief:
    """The whole brief, ready for the page and the Word export."""

    title: str
    generated_on: dt.date
    sections: tuple[BriefSection, ...]


def build_brief(
    schedules: list[Schedule],
    cpms: list[CPMResult],
    *,
    today: dt.date | None = None,
) -> DiagnosticBrief:
    """Build the cited Diagnostic Brief over the loaded, analyzable versions.

    Versions must arrive in forensic (data-date) order with their CPM results —
    exactly what the web layer's ``_solvable_versions`` produces.
    """
    if not schedules:
        raise ValueError("the diagnostic brief needs at least one analyzable schedule")
    generated = today or dt.date.today()
    sections = [
        _summary_section(schedules, cpms),
        _finish_story_section(schedules, cpms),
        _trends_section(schedules, cpms),
        _questions_section(schedules, cpms),
        _risk_recovery_section(schedules, cpms),
        _how_to_verify_section(schedules),
    ]
    return DiagnosticBrief(
        title="Schedule Forensics — Diagnostic Brief",
        generated_on=generated,
        sections=tuple(sections),
    )


# --- sections ---------------------------------------------------------------------------


def _summary_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefSection:
    paragraphs: list[CitedStatement] = []
    latest, latest_cpm = schedules[-1], cpms[-1]
    label = _label(latest)
    tasks = non_summary(latest)
    complete = sum(1 for t in tasks if t.percent_complete >= 100.0)
    in_progress = sum(1 for t in tasks if 0.0 < t.percent_complete < 100.0)
    finish = _finish_date(latest, latest_cpm)
    names = ", ".join(_label(s) for s in schedules)
    paragraphs.append(
        CitedStatement(
            f"This brief covers {len(schedules)} version(s) of the schedule ({names}), "
            f"ordered by data date. The newest version, {label}, holds "
            f"{len(tasks)} activities — {complete} complete, {in_progress} in progress, "
            f"{len(tasks) - complete - in_progress} still to start — and its network "
            f"computes a finish of {finish.isoformat()}.",
            _drivers(latest, latest_cpm),
        )
    )
    if latest.status_date is not None:
        paragraphs.append(
            CitedStatement(
                f"The newest data date is {latest.status_date.date().isoformat()}. "
                "Everything in this brief is computed from the loaded files themselves; "
                "each claim carries the schedule and UniqueIDs that prove it.",
                _drivers(latest, latest_cpm),
            )
        )
    return BriefSection("What this brief covers", tuple(paragraphs))


def _finish_story_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefSection:
    paragraphs: list[CitedStatement] = []
    rows: list[tuple[str | int | float | None, ...]] = []
    prev_finish: dt.date | None = None
    prev_pct: float | None = None
    for sch, cpm in zip(schedules, cpms, strict=True):
        finish = _finish_date(sch, cpm)
        pct = _overall_percent(sch)
        moved = (finish - prev_finish).days if prev_finish is not None else None
        rows.append(
            (
                _label(sch),
                sch.status_date.date().isoformat() if sch.status_date else "n/a",
                finish.isoformat(),
                moved,
                round(pct, 1),
            )
        )
        if moved is not None and moved > 0 and prev_pct is not None and pct > prev_pct:
            paragraphs.append(
                CitedStatement(
                    f"In {_label(sch)} the reported progress went UP (from {prev_pct:.0f}% "
                    f"to {pct:.0f}% complete) while the computed finish moved LATER by "
                    f"{moved} calendar days (to {finish.isoformat()}). Progress and the "
                    "finish moving in opposite directions is the classic sign that the "
                    "remaining work, not the completed work, controls this schedule — "
                    "ask what grew on the driving path.",
                    _drivers(sch, cpm),
                )
            )
        prev_finish, prev_pct = finish, pct
    first, last = _finish_date(schedules[0], cpms[0]), prev_finish
    if last is not None and len(schedules) > 1:
        total = (last - first).days
        direction = "later" if total > 0 else ("earlier" if total < 0 else "unchanged")
        text = (
            f"Across the loaded versions the computed finish moved {abs(total)} calendar "
            f"days {direction} (from {first.isoformat()} to {last.isoformat()})."
            if total
            else f"Across the loaded versions the computed finish held at {first.isoformat()}."
        )
        paragraphs.insert(0, CitedStatement(text, _drivers(schedules[-1], cpms[-1])))
    table = Table(
        "The finish, version by version",
        ("Version", "Data date", "Computed finish", "Moved (days)", "% complete"),
        tuple(rows),
    )
    return BriefSection("The finish story", tuple(paragraphs), table)


def _questions_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefSection:
    """The heart of the brief: outliers and contradictions, each phrased as a question."""
    paragraphs: list[CitedStatement] = []
    paragraphs.extend(_manipulation_questions(schedules, cpms))
    paragraphs.extend(_remaining_cut_questions(schedules))
    paragraphs.extend(_stale_forecast_questions(schedules[-1]))
    paragraphs.extend(_duration_stretch_questions(schedules[-1]))
    paragraphs.extend(_high_float_questions(schedules[-1], cpms[-1]))
    paragraphs.extend(_forecast_spread_questions(schedules[-1], cpms[-1]))
    paragraphs.extend(_cei_questions(schedules, cpms))
    if not paragraphs:
        paragraphs.append(
            CitedStatement(
                "Nothing in the loaded versions tripped the outlier detectors: no "
                "rolled-back history, no stale forecasts, no extreme duration "
                "stretches, no falling execution index. That itself is worth one "
                "question — pristine updates are rare on real programs.",
                _drivers(schedules[-1], cpms[-1]),
            )
        )
    return BriefSection("Questions the data raises", tuple(paragraphs))


def _incomplete_critical(schedule: Schedule, cpm: CPMResult) -> int:
    """Count of incomplete activities on the critical path — the size of the at-risk path."""
    by_id = schedule.tasks_by_id
    return sum(1 for uid in cpm.critical_path if uid in by_id and not by_id[uid].is_complete)


def _negative_float(schedule: Schedule, cpm: CPMResult) -> list[Task]:
    """Incomplete activities behind their own logic (negative total float)."""
    by_id = schedule.tasks_by_id
    return [
        by_id[uid]
        for uid, timing in cpm.timings.items()
        if timing.total_float < 0 and uid in by_id and not by_id[uid].is_complete
    ]


def _trends_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefSection:
    """A high-level read of what is moving from version to version (operator request)."""
    latest, latest_cpm = schedules[-1], cpms[-1]
    if len(schedules) < 2:
        return BriefSection(
            "Trends over time",
            (
                CitedStatement(
                    "Only one schedule version is loaded, so there is no version-to-version "
                    "trend yet. Load the earlier updates to see how the finish, the critical "
                    "path, completion, and float have moved over time.",
                    _drivers(latest, latest_cpm),
                ),
            ),
        )
    first, first_cpm = schedules[0], cpms[0]
    f0, f1 = _finish_date(first, first_cpm), _finish_date(latest, latest_cpm)
    moved = (f1 - f0).days
    p0, p1 = _overall_percent(first), _overall_percent(latest)
    c0, c1 = _incomplete_critical(first, first_cpm), _incomplete_critical(latest, latest_cpm)
    n0, n1 = len(_negative_float(first, first_cpm)), len(_negative_float(latest, latest_cpm))

    direction = "later" if moved > 0 else ("earlier" if moved < 0 else "unchanged")
    paragraphs: list[CitedStatement] = [
        CitedStatement(
            f"Across the {len(schedules)} loaded versions, the computed finish moved "
            f"{abs(moved)} calendar days {direction} (from {f0.isoformat()} to "
            f"{f1.isoformat()}) while overall completion went from {p0:.0f}% to {p1:.0f}%. "
            + (
                "The finish slipping as work is reported done points to the remaining work, "
                "not the completed work, controlling this schedule."
                if moved > 0
                else "The finish holding or pulling in as completion rises is the healthy pattern."
            ),
            _drivers(latest, latest_cpm),
        )
    ]
    if c1 != c0:
        grew = c1 > c0
        paragraphs.append(
            CitedStatement(
                f"The critical path {'grew' if grew else 'shrank'} from {c0} to {c1} incomplete "
                "driving activities. "
                + (
                    "A growing critical path means more of the remaining work now controls the "
                    "finish — the plan is getting more fragile."
                    if grew
                    else "A shrinking critical path is either real recovery or work being taken "
                    "off the path — the 'What-if' analysis on the Evolution page separates the two."
                ),
                _drivers(latest, latest_cpm),
            )
        )
    if n0 or n1:
        trend = (
            "rising schedule pressure — work that cannot finish in time without a change"
            if n1 > n0
            else ("easing" if n1 < n0 else "holding steady")
        )
        paragraphs.append(
            CitedStatement(
                f"Activities behind their logic (negative total float) went from {n0} to {n1} "
                f"— {trend}.",
                _drivers(latest, latest_cpm),
            )
        )
    return BriefSection("Trends over time", tuple(paragraphs))


def _risk_recovery_section(schedules: list[Schedule], cpms: list[CPMResult]) -> BriefSection:
    """Risks, opportunities, and concrete recovery suggestions (operator request). Every item
    is engine-computed and cited; the recovery suggestions are standard schedule-recovery levers
    tied to the specific activities the data flags."""
    latest, cpm = schedules[-1], cpms[-1]
    per_day = latest.calendar.working_minutes_per_day
    tasks = non_summary(latest)
    label = _label(latest)
    paragraphs: list[CitedStatement] = []

    neg = _negative_float(latest, cpm)
    if neg:
        worst = sorted(neg, key=lambda t: cpm.timings[t.unique_id].total_float)[:5]
        behind = round(-cpm.timings[worst[0].unique_id].total_float / per_day)
        paragraphs.append(
            CitedStatement(
                f"Risk — {len(neg)} incomplete activities are behind their own logic (negative "
                f"total float); the worst, '{worst[0].name}', is about {behind} working days "
                "behind. These cannot finish on time unless something changes. Recovery: "
                "re-sequence or fast-track this chain, add resources, or renegotiate the imposed "
                "date — then re-run to confirm the negative float clears.",
                tuple(Citation(label, t.unique_id, t.name) for t in worst),
            )
        )

    high = [
        t
        for t in tasks
        if t.percent_complete < 100.0
        and t.unique_id in cpm.timings
        and cpm.timings[t.unique_id].total_float > HIGH_FLOAT_DAYS * per_day
    ]
    if high:
        worst_high = sorted(high, key=lambda t: -cpm.timings[t.unique_id].total_float)[:5]
        paragraphs.append(
            CitedStatement(
                f"Opportunity / risk — {len(high)} incomplete activities carry more than "
                f"{HIGH_FLOAT_DAYS} working days of total float. As an opportunity that slack "
                "can absorb re-sequencing to pull the critical path in; as a risk, float that "
                "large usually means missing successor logic. Recovery: confirm each is properly "
                "tied into the network, then use the genuine slack to support the driving path.",
                tuple(Citation(label, t.unique_id, t.name) for t in worst_high),
            )
        )

    ahead = [
        t
        for t in tasks
        if t.percent_complete >= 100.0
        and t.actual_finish is not None
        and t.baseline_finish is not None
        and t.actual_finish < t.baseline_finish
    ]
    if ahead:
        paragraphs.append(
            CitedStatement(
                f"Opportunity — {len(ahead)} activities finished ahead of their baseline, which "
                "earned schedule margin. Recovery: make sure that time saved is protected on the "
                "driving path rather than quietly absorbed by downstream delay.",
                tuple(Citation(label, t.unique_id, t.name) for t in ahead[:5]),
            )
        )

    dated = [
        (f.name, f.finish) for f in compute_finish_forecasts(latest, cpm).forecasts if f.finish
    ]
    if len(dated) >= 2:
        lo = min(dated, key=lambda x: x[1])
        hi = max(dated, key=lambda x: x[1])
        spread = (hi[1] - lo[1]).days
        if spread > FORECAST_SPREAD_DAYS:
            paragraphs.append(
                CitedStatement(
                    f"Risk — the finish-forecast methods disagree by {spread} calendar days "
                    f"({lo[0]} says {lo[1].isoformat()}, {hi[0]} says {hi[1].isoformat()}); that "
                    "spread is unmanaged uncertainty. Recovery: reconcile the logic-based and "
                    "pace-based forecasts — re-estimate the to-go durations or repair the network "
                    "so they converge.",
                    _drivers(latest, cpm),
                )
            )

    if not paragraphs:
        paragraphs.append(
            CitedStatement(
                "No negative float, no high-float open-ends, no behind-baseline completions, and "
                "no wide forecast spread stand out in the newest version — the plan looks healthy "
                "on these measures. Recovery focus: keep protecting the driving path and statusing "
                "activities on time so the picture stays trustworthy.",
                _drivers(latest, cpm),
            )
        )
    return BriefSection("Risks, opportunities, and recovery plan", tuple(paragraphs))


def _manipulation_questions(
    schedules: list[Schedule], cpms: list[CPMResult]
) -> list[CitedStatement]:
    out: list[CitedStatement] = []
    for k in range(1, len(schedules)):
        findings = detect_manipulation(
            schedules[k], schedules[k - 1], current_cpm=cpms[k], prior_cpm=cpms[k - 1]
        )
        pair = f"{_label(schedules[k - 1])} → {_label(schedules[k])}"
        for f in findings:
            if str(f.severity) != "HIGH":
                continue
            out.append(
                CitedStatement(
                    f"Between {pair}: {f.title}. In plain terms — {f.detail} "
                    f"What to do: {f.course_of_action}",
                    f.citations,
                )
            )
    return out


def _remaining_cut_questions(schedules: list[Schedule]) -> list[CitedStatement]:
    """Remaining duration cut faster than the calendar moved — the optics tell.

    If a task's remaining duration shrank by clearly more working days than elapsed
    between the two data dates (and its percent complete barely moved), someone made
    the future smaller without doing the work — the simplest way to stop a finish
    date from slipping."""
    if len(schedules) < 2:
        return []
    prior, current = schedules[-2], schedules[-1]
    if prior.status_date is None or current.status_date is None:
        return []
    elapsed_wd = _working_days_between(
        current, prior.status_date.date(), current.status_date.date()
    )
    per_day = current.calendar.working_minutes_per_day
    prior_by = {t.unique_id: t for t in non_summary(prior)}
    offenders: list[tuple[Task, float, float]] = []
    for t in non_summary(current):
        p = prior_by.get(t.unique_id)
        if p is None or t.percent_complete >= 100.0:
            continue
        rem_now = (
            t.remaining_duration_minutes
            if t.remaining_duration_minutes is not None
            else round(t.duration_minutes * (100.0 - t.percent_complete) / 100.0)
        )
        rem_before = (
            p.remaining_duration_minutes
            if p.remaining_duration_minutes is not None
            else round(p.duration_minutes * (100.0 - p.percent_complete) / 100.0)
        )
        cut_days = (rem_before - rem_now) / per_day
        if cut_days > elapsed_wd + 2 and (t.percent_complete - p.percent_complete) < 10.0:
            offenders.append((t, cut_days, t.percent_complete - p.percent_complete))
    out = []
    for t, cut, dpct in sorted(offenders, key=lambda x: -x[1])[:3]:
        out.append(
            CitedStatement(
                f"'{t.name}' (UID {t.unique_id}) had its remaining duration cut by "
                f"{cut:.0f} working days between the last two versions, while only "
                f"{elapsed_wd:.0f} working days passed and its reported progress moved "
                f"{dpct:.0f} points. Shrinking future work faster than time passes is "
                "the cheapest way to hold a finish date — ask what justified the cut.",
                (Citation(_label(schedules[-1]), t.unique_id, t.name),),
            )
        )
    return out


def _stale_forecast_questions(latest: Schedule) -> list[CitedStatement]:
    if latest.status_date is None:
        return []
    dd = latest.status_date
    stale = [
        t
        for t in non_summary(latest)
        if t.percent_complete < 100.0 and t.finish is not None and t.finish < dd
    ]
    if not stale:
        return []
    worst = sorted(stale, key=lambda t: t.finish or dd)[:5]
    days = (dd.date() - (worst[0].finish or dd).date()).days
    return [
        CitedStatement(
            f"{len(stale)} unfinished activities are still scheduled to finish BEFORE "
            f"the data date ({dd.date().isoformat()}) — the oldest by {days} calendar "
            "days. Work scheduled in the past cannot happen; these are unstatused "
            "updates, and every downstream date that depends on them is quietly wrong. "
            "Ask why they were not statused or rescheduled.",
            tuple(Citation(_label(latest), t.unique_id, t.name) for t in worst),
        )
    ]


def _duration_stretch_questions(latest: Schedule) -> list[CitedStatement]:
    per_day = latest.calendar.working_minutes_per_day
    stretched: list[tuple[Task, float]] = []
    for t in non_summary(latest):
        if (
            t.percent_complete >= 100.0
            and t.baseline_duration_minutes
            and t.duration_minutes >= t.baseline_duration_minutes * DURATION_STRETCH_RATIO
        ):
            stretched.append((t, t.duration_minutes / t.baseline_duration_minutes))
    if not stretched:
        return []
    top = sorted(stretched, key=lambda x: -x[1])[:3]
    t, ratio = top[0]
    return [
        CitedStatement(
            f"{len(stretched)} completed activities took at least twice their planned "
            f"duration. The worst, '{t.name}' (UID {t.unique_id}), planned "
            f"{round((t.baseline_duration_minutes or 0) / per_day)} working days and "
            f"took {round(t.duration_minutes / per_day)} ({ratio:.1f}x). If the same "
            "estimating basis produced the REMAINING work's durations, the forecast "
            "inherits that optimism — ask whether to-go durations were re-estimated.",
            tuple(Citation(_label(latest), x.unique_id, x.name) for x, _ in top),
        )
    ]


def _high_float_questions(latest: Schedule, cpm: CPMResult) -> list[CitedStatement]:
    per_day = latest.calendar.working_minutes_per_day
    high = [
        t
        for t in non_summary(latest)
        if t.percent_complete < 100.0
        and t.unique_id in cpm.timings
        and cpm.timings[t.unique_id].total_float > HIGH_FLOAT_DAYS * per_day
    ]
    if not high:
        return []
    worst = sorted(high, key=lambda t: -cpm.timings[t.unique_id].total_float)[:5]
    biggest = round(cpm.timings[worst[0].unique_id].total_float / per_day)
    return [
        CitedStatement(
            f"{len(high)} incomplete activities carry more than {HIGH_FLOAT_DAYS} working "
            f"days of total float (the loosest, '{worst[0].name}', has about {biggest}). "
            "Float that large usually means the activity is not really tied into the "
            "network — its successors are missing, so it can 'slip' forever without "
            "appearing to hurt anything. Ask what these feed, and tie them in.",
            tuple(Citation(_label(latest), t.unique_id, t.name) for t in worst),
        )
    ]


def _forecast_spread_questions(latest: Schedule, cpm: CPMResult) -> list[CitedStatement]:
    forecasts = compute_finish_forecasts(latest, cpm).forecasts
    dated = [(f.name, f.finish) for f in forecasts if f.finish is not None]
    if len(dated) < 2:
        return []
    lo = min(dated, key=lambda x: x[1])
    hi = max(dated, key=lambda x: x[1])
    spread = (hi[1] - lo[1]).days
    if spread <= FORECAST_SPREAD_DAYS:
        return []
    return [
        CitedStatement(
            f"The finish-forecast methods disagree by {spread} calendar days: "
            f"{lo[0]} says {lo[1].isoformat()} while {hi[0]} says {hi[1].isoformat()}. "
            "The logic-based forecast believes the network; the throughput-based ones "
            "believe the team's actual pace. A gap this wide means the network and the "
            "pace tell different stories — one of them is wrong, and the difference is "
            "the schedule risk. Ask which assumption the program is managing to.",
            _drivers(latest, cpm),
        )
    ]


def _cei_questions(schedules: list[Schedule], cpms: list[CPMResult]) -> list[CitedStatement]:
    if len(schedules) < 3:
        return []
    try:
        wave = compute_bow_wave(schedules)
    except ValueError:
        return []
    ceis = [(s.label, s.cei) for s in wave.snapshots if s.cei is not None]
    if len(ceis) < 2 or ceis[-1][1] is None:
        return []
    _, last = ceis[-1]
    declining = all(later <= earlier for (_, earlier), (_, later) in itertools.pairwise(ceis))
    if last >= 0.7 and not declining:
        return []
    series = ", ".join(f"{label}: {value:.2f}" for label, value in ceis)
    trend = "has fallen every period" if declining else "is low"
    return [
        CitedStatement(
            f"The execution index (CEI — of the work each version planned to finish in "
            f"the following month, the share that actually finished) {trend}: {series}. "
            f"At {last:.2f}, roughly {round((1 - last) * 100)}% of the near-term plan is "
            "not happening on schedule month over month — the 'bow wave' of deferred "
            "work is growing. Ask what the recovery plan is for the pushed work.",
            _drivers(schedules[-1], cpms[-1]),
        )
    ]


def _how_to_verify_section(schedules: list[Schedule]) -> BriefSection:
    latest = schedules[-1]
    citation = _drivers_static(latest)
    return BriefSection(
        "How to verify any claim in this brief",
        (
            CitedStatement(
                "Every statement above ends with a citation in square brackets: the "
                "schedule file it came from, the UniqueID, and the activity name. Open "
                "that file, find that UniqueID, and the numbers are there — nothing in "
                "this brief is computed anywhere except from the loaded files, on this "
                "machine.",
                citation,
            ),
        ),
    )


def brief_blocks(brief: DiagnosticBrief) -> list[object]:
    """The brief as Word blocks (reports.docx) — same content as the page, verbatim."""
    from schedule_forensics.reports.docx import DocTable, Heading, Paragraph

    blocks: list[object] = [
        Heading(brief.title, level=0),
        Paragraph(f"Report generated on {brief.generated_on.strftime('%A, %B %d, %Y')}."),
        Paragraph(
            "Generated locally by Schedule Forensics from the loaded schedule files; "
            "every claim cites the schedule, UniqueID, and activity that substantiate it.",
            italic=True,
        ),
    ]
    for section in brief.sections:
        blocks.append(Heading(section.heading, level=1))
        for stmt in section.paragraphs:
            blocks.append(Paragraph(stmt.rendered()))
        if section.table is not None:
            blocks.append(DocTable(section.table.headers, section.table.rows))
    return blocks


# --- shared helpers ---------------------------------------------------------------------


def _label(schedule: Schedule) -> str:
    return schedule.source_file or schedule.name


def _finish_date(schedule: Schedule, cpm: CPMResult) -> dt.date:
    return offset_to_datetime(schedule.project_start, cpm.project_finish, schedule.calendar).date()


def _overall_percent(schedule: Schedule) -> float:
    tasks = non_summary(schedule)
    if not tasks:
        return 0.0
    return sum(t.percent_complete for t in tasks) / len(tasks)


def _drivers(schedule: Schedule, cpm: CPMResult) -> tuple[Citation, ...]:
    """The finish-controlling activities — the §6 fallback citation anchor."""
    label = _label(schedule)
    by_id = schedule.tasks_by_id
    drivers = tuple(
        Citation(label, uid, by_id[uid].name)
        for uid, timing in sorted(cpm.timings.items())
        if timing.early_finish == cpm.project_finish and uid in by_id
    )
    return drivers or _drivers_static(schedule)


def _drivers_static(schedule: Schedule) -> tuple[Citation, ...]:
    label = _label(schedule)
    return tuple(Citation(label, t.unique_id, t.name) for t in schedule.tasks[:3])


def _working_days_between(schedule: Schedule, start: dt.date, end: dt.date) -> float:
    cal = schedule.calendar
    days = 0
    cursor = start
    while cursor < end:
        cursor += dt.timedelta(days=1)
        if cal.is_working_day(cursor):
            days += 1
    return float(days)
