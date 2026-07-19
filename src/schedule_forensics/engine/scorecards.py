"""Assessment scorecards — NASA STAT, the GAO 10-practices view, and an SRA-readiness gate.

A **consolidation layer** (issue #331 gaps #3/#4/#5): three named assessment frameworks the
reference decks (INT-02 ICEAA slides 7/8/12/24-37; GAO-16-89G) put *beside* DCMA-14. The Law-2
discipline is strict: **every scored figure is a number the engine already computes** — the
gate-locked DCMA-14 audit (:mod:`.dcma_audit`), the logic-integrity checks
(:mod:`.metrics.logic_integrity`), and deterministic, unambiguous model scans. This module adds
**no new metric math for a scored value**; it groups, labels, and maps validated numbers into a
uniform scorecard shape. The handful of genuinely-new lines are trivial model scans (milestone /
manual-task / estimated-duration counts, the missing-predecessor vs missing-successor split, the
actuals-after-status split of DCMA-09) computed directly with **cited offenders**. Where a
framework defines no numeric pass bar the line is reported ``INFO`` (a count, never a fabricated
pass/fail), so the scorecard's pass rate is honest.

The fourth export, :func:`reserve_recommendation`, sizes the schedule **buffer / reserve** needed
to hit a committed date at a chosen confidence (issue #331 gap #7). It is pure percentile
arithmetic over an *already-simulated* finish distribution (the SRA CDF), introducing no new
statistics — it reads the same Monte-Carlo the ``/sra`` page already runs (ADR-0106).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.dcma_audit import ScheduleAudit
from schedule_forensics.engine.metrics._common import CheckStatus, is_incomplete, non_summary
from schedule_forensics.engine.metrics.logic_integrity import compute_logic_integrity
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.schedule import Schedule

#: Scorecard line status vocabulary (the UI maps these to the theme's pass/fail/neutral chips).
#: ``INFO`` is an informational count with no numeric pass bar — it never affects the pass rate.
#: (These are chip labels, not secrets; bandit B105 reads the word "PASS" as a password.)
PASS = "PASS"  # nosec B105
FAIL = "FAIL"
INFO = "INFO"
NA = "NA"

#: Offenders carried to the drill panel per line (the activity grid is the full record).
_OFFENDER_CAP = 200


@dataclass(frozen=True)
class ScorecardCheck:
    """One scorecard line: a validated figure re-presented under a framework heading.

    ``status`` is one of :data:`PASS` / :data:`FAIL` / :data:`INFO` / :data:`NA`. ``detail`` is the
    human-readable value (e.g. ``"3 of 120 (2.5%)"``); ``provenance`` names the already-validated
    engine source the figure is drawn from, so any number is verifiable. ``offender_uids`` are the
    cited activities behind the figure (empty for a tool-level or informational line).
    """

    key: str
    label: str
    status: str
    detail: str
    provenance: str
    offender_uids: tuple[int, ...] = ()


@dataclass(frozen=True)
class Scorecard:
    """A full assessment scorecard: its checks plus pass/fail/info/na tallies.

    ``passed`` / ``failed`` count only the *scored* lines (those with a numeric or unambiguous pass
    bar); ``info`` lines are informational and excluded from :attr:`score`.
    """

    key: str
    name: str
    framework: str
    checks: tuple[ScorecardCheck, ...]
    passed: int
    failed: int
    info: int
    na: int

    @property
    def scored(self) -> int:
        """Number of lines that carry a pass/fail verdict (denominator of :attr:`score`)."""
        return self.passed + self.failed

    @property
    def score(self) -> float | None:
        """Fraction of scored lines that pass (``None`` when nothing is scored)."""
        return (self.passed / self.scored) if self.scored else None


def _tally(checks: Sequence[ScorecardCheck]) -> tuple[int, int, int, int]:
    passed = sum(1 for c in checks if c.status == PASS)
    failed = sum(1 for c in checks if c.status == FAIL)
    info = sum(1 for c in checks if c.status == INFO)
    na = sum(1 for c in checks if c.status == NA)
    return passed, failed, info, na


def _make(key: str, name: str, framework: str, checks: Sequence[ScorecardCheck]) -> Scorecard:
    passed, failed, info, na = _tally(checks)
    return Scorecard(key, name, framework, tuple(checks), passed, failed, info, na)


def _pct(count: int, population: int) -> str:
    """``"n of N (p%)"`` — the standard count/population/percent detail string."""
    if population <= 0:
        return f"{count} (no applicable activities)"
    return f"{count} of {population} ({100.0 * count / population:.1f}%)"


def _zero_bar(count: int) -> str:
    """PASS iff the count is 0 (for the unambiguous 'should never occur' structural lines)."""
    return PASS if count == 0 else FAIL


def _audit_status(audit: ScheduleAudit, metric_id: str) -> tuple[str, str, tuple[int, ...]]:
    """The validated (status, detail, offenders) for a DCMA-14 check id, or an NA placeholder.

    Reuses the gate-locked audit verbatim — the scorecard never re-scores a DCMA metric.
    """
    check = next((c for c in audit.checks if c.metric_id == metric_id), None)
    if check is None:
        return NA, "not evaluated for this schedule", ()
    status = {
        CheckStatus.PASS: PASS,
        CheckStatus.FAIL: FAIL,
        CheckStatus.NOT_APPLICABLE: NA,
    }[check.status]
    if check.unit == "%":
        detail = _pct(check.count, check.population)
    elif check.unit == "ratio":
        bar = f" (threshold {check.threshold:g})" if check.threshold is not None else ""
        detail = f"{check.value:g}{bar}"
    else:
        detail = f"{check.count}"
    offenders = tuple(c.unique_id for c in check.citations[:_OFFENDER_CAP])
    return status, detail, offenders


# --------------------------------------------------------------------------------------
# Shared deterministic model scans (each unambiguous — no new metric semantics)
# --------------------------------------------------------------------------------------


def _logic_endpoints(schedule: Schedule, real_ids: set[int]) -> tuple[set[int], set[int]]:
    """``(has_predecessor, has_successor)`` UID sets over the activity network (no summaries)."""
    has_pred: set[int] = set()
    has_succ: set[int] = set()
    for r in schedule.relationships:
        if r.predecessor_id in real_ids and r.successor_id in real_ids:
            has_succ.add(r.predecessor_id)
            has_pred.add(r.successor_id)
    return has_pred, has_succ


def _summaries_with_logic(schedule: Schedule) -> tuple[int, ...]:
    """Summary/WBS rollup rows that carry predecessor/successor logic (a construction defect)."""
    summary_ids = {t.unique_id for t in schedule.tasks if t.is_summary}
    tied: set[int] = set()
    for r in schedule.relationships:
        if r.predecessor_id in summary_ids:
            tied.add(r.predecessor_id)
        if r.successor_id in summary_ids:
            tied.add(r.successor_id)
    return tuple(sorted(tied))


def _actuals_after_status(schedule: Schedule) -> tuple[int, ...]:
    """Activities whose actual start or finish is later than the data date (invalid actuals).

    The actuals half of DCMA-09, split out so NASA STAT can report it as its own line
    (dcma14.py lines 198-201). NA-safe: an empty tuple when the file carries no data date.
    """
    status = schedule.status_date
    if status is None:
        return ()
    out = [
        t.unique_id
        for t in non_summary(schedule)
        if (t.actual_start is not None and t.actual_start > status)
        or (t.actual_finish is not None and t.actual_finish > status)
    ]
    return tuple(sorted(out))


def _forecast_in_past(schedule: Schedule) -> tuple[int, ...]:
    """Incomplete activities whose forecast start/finish is already in the past with no actual.

    The forecast half of DCMA-09 (a status-update backlog signal): dcma14.py lines 202-205.
    """
    status = schedule.status_date
    if status is None:
        return ()
    out = [
        t.unique_id
        for t in non_summary(schedule)
        if is_incomplete(t)
        and (
            (t.actual_start is None and t.start is not None and t.start < status)
            or (t.actual_finish is None and t.finish is not None and t.finish < status)
        )
    ]
    return tuple(sorted(out))


def _no_forecast_date(schedule: Schedule) -> tuple[int, ...]:
    """Incomplete activities missing a forecast start AND finish entirely (data completeness)."""
    out = [
        t.unique_id
        for t in non_summary(schedule)
        if is_incomplete(t) and t.start is None and t.finish is None and t.actual_start is None
    ]
    return tuple(sorted(out))


# --------------------------------------------------------------------------------------
# 1. NASA STAT — Schedule Test and Assessment Tool (INT-02 slides 8/12)
# --------------------------------------------------------------------------------------

_STAT_FRAMEWORK = (
    "NASA STAT (Schedule Test & Assessment Tool), INT-02 ICEAA deck slides 8/12. Every figure is "
    "consolidated from the tool's gate-locked DCMA-14 audit, the logic-integrity checks, and "
    "deterministic model scans — no new metric math (Law 2)."
)


def compute_nasa_stat(schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit) -> Scorecard:
    """The NASA STAT health scorecard — validated schedule-construction checks in one ribbon."""
    tasks = non_summary(schedule)
    real_ids = {t.unique_id for t in tasks}
    incomplete = [t for t in tasks if is_incomplete(t)]
    n_inc = len(incomplete)
    has_pred, has_succ = _logic_endpoints(schedule, real_ids)

    missing_pred = tuple(sorted(t.unique_id for t in incomplete if t.unique_id not in has_pred))
    missing_succ = tuple(sorted(t.unique_id for t in incomplete if t.unique_id not in has_succ))
    summaries_tied = _summaries_with_logic(schedule)
    oos = next(
        (c for c in compute_logic_integrity(schedule).checks if c.key == "out_of_sequence"),
        None,
    )
    actuals_after = _actuals_after_status(schedule)
    forecast_past = _forecast_in_past(schedule)
    no_date = _no_forecast_date(schedule)
    milestones = tuple(sorted(t.unique_id for t in tasks if t.is_milestone))
    estimated = tuple(sorted(t.unique_id for t in tasks if t.is_estimated_duration))
    manual = tuple(sorted(t.unique_id for t in tasks if t.is_manual))

    logic_status, logic_detail, logic_off = _audit_status(audit, "DCMA01")
    has_status = schedule.status_date is not None

    checks: list[ScorecardCheck] = [
        ScorecardCheck(
            "missing_logic",
            "Missing logic (predecessor and/or successor)",
            logic_status,
            logic_detail,
            "DCMA-14 check 1 (gate-locked, 5% bar)",
            logic_off,
        ),
        ScorecardCheck(
            "missing_predecessor",
            "To-go activities with no predecessor",
            INFO,
            _pct(len(missing_pred), n_inc),
            "Relationship scan (decomposes DCMA-01); a true project start is expected",
            missing_pred[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "missing_successor",
            "To-go activities with no successor",
            INFO,
            _pct(len(missing_succ), n_inc),
            "Relationship scan (decomposes DCMA-01); a true project finish is expected",
            missing_succ[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "summary_logic",
            "Summary tasks carrying logic ties",
            _zero_bar(len(summaries_tied)),
            f"{len(summaries_tied)}",
            "Relationship scan — logic belongs on activities, not summaries",
            summaries_tied[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "out_of_sequence",
            "Out-of-sequence logic (progressed against the logic)",
            NA if oos is None or not oos.evaluated else _zero_bar(oos.count),
            "not evaluated" if oos is None else _pct(oos.count, oos.population),
            "Logic-integrity check (engine/metrics/logic_integrity)",
            # drill-down: the activities behind the offending edges (the only scored, FAIL-capable
            # STAT line that previously shipped no offenders — the UIDs are computed upstream).
            oos.offender_uids if oos is not None else (),
        ),
        ScorecardCheck(
            "actuals_after_status",
            "Actuals recorded after the data date",
            NA if not has_status else _zero_bar(len(actuals_after)),
            "no data date" if not has_status else f"{len(actuals_after)}",
            "Actuals half of DCMA-09 (invalid dates), split out",
            actuals_after[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "forecast_in_past",
            "Forecast dates in the past (need a status update)",
            NA if not has_status else INFO,
            "no data date" if not has_status else _pct(len(forecast_past), n_inc),
            "Forecast half of DCMA-09 (status-update backlog)",
            forecast_past[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "no_forecast_date",
            "To-go activities with no start or finish date",
            INFO,
            _pct(len(no_date), n_inc),
            "Model scan (data-completeness)",
            no_date[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "milestones",
            "Milestones",
            INFO,
            f"{len(milestones)} of {len(tasks)}",
            "Model scan (is_milestone) — event coverage",
            milestones[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "estimated_duration",
            "Estimated (not-yet-firm) durations",
            INFO,
            _pct(len(estimated), len(tasks)),
            "Model scan (MSPDI <Estimated> flag)",
            estimated[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "manual_tasks",
            "Manually-scheduled tasks (logic overridden)",
            INFO,
            _pct(len(manual), len(tasks)),
            "Model scan (MSPDI <Manual> mode)",
            manual[:_OFFENDER_CAP],
        ),
    ]
    return _make("nasa_stat", "NASA STAT", _STAT_FRAMEWORK, checks)


# --------------------------------------------------------------------------------------
# 2. GAO Schedule Assessment Guide — the 10 best practices (INT-02 slide 7; GAO-16-89G)
# --------------------------------------------------------------------------------------

_GAO_FRAMEWORK = (
    "GAO Schedule Assessment Guide (GAO-16-89G), the ten best practices under four "
    "characteristics. Each practice maps to the tool's already-validated metric(s); this is a "
    "presentation/mapping view — no new metric math (Law 2)."
)


def compute_gao_scorecard(schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit) -> Scorecard:
    """The GAO 10-best-practices compliance view — existing validated metrics mapped to GAO."""
    tasks = non_summary(schedule)
    has_wbs = sum(1 for t in tasks if t.wbs)
    has_baseline = sum(
        1 for t in tasks if t.baseline_finish is not None or t.baseline_duration_minutes is not None
    )

    seq_status, seq_detail, seq_off = _audit_status(audit, "DCMA01")
    res_status, res_detail, res_off = _audit_status(audit, "DCMA10")
    dur_status, dur_detail, dur_off = _audit_status(audit, "DCMA08")
    cp_status, cp_detail, cp_off = _audit_status(audit, "DCMA12")
    hf_status, hf_detail, hf_off = _audit_status(audit, "DCMA06")
    nf_status, nf_detail, nf_off = _audit_status(audit, "DCMA07")
    inv_status, inv_detail, inv_off = _audit_status(audit, "DCMA09")

    summaries_tied = _summaries_with_logic(schedule)
    # BP7 float reasonableness passes only when BOTH high-float and negative-float pass.
    float_status = (
        PASS
        if hf_status == PASS and nf_status == PASS
        else NA
        if hf_status == NA and nf_status == NA
        else FAIL
    )
    float_detail = f"high float {hf_detail}; negative float {nf_detail}"
    # BP5 traceability: danglers (DCMA-01) plus summaries carrying logic — both break the vertical/
    # horizontal trace. PASS only when logic is clean AND no summary carries logic.
    trace_status = (
        PASS if seq_status == PASS and not summaries_tied else NA if seq_status == NA else FAIL
    )
    trace_detail = f"missing logic {seq_detail}; summaries with logic {len(summaries_tied)}"

    checks: list[ScorecardCheck] = [
        ScorecardCheck(
            "bp1_capture",
            "1. Capturing all activities",
            INFO,
            f"{len(tasks)} activities, {has_wbs} WBS-coded",
            "Model scan — completeness is a scope judgement; the counts inform it",
            (),
        ),
        ScorecardCheck(
            "bp2_sequence",
            "2. Sequencing all activities",
            seq_status,
            seq_detail,
            "DCMA-14 check 1 — missing logic",
            seq_off,
        ),
        ScorecardCheck(
            "bp3_resources",
            "3. Assigning resources to all activities",
            res_status,
            res_detail,
            "DCMA-14 check 10 — resources",
            res_off,
        ),
        ScorecardCheck(
            "bp4_durations",
            "4. Establishing the duration of all activities",
            dur_status,
            dur_detail,
            "DCMA-14 check 8 — high duration (statusable detail)",
            dur_off,
        ),
        ScorecardCheck(
            "bp5_traceable",
            "5. Verifying the schedule is traceable horizontally and vertically",
            trace_status,
            trace_detail,
            "DCMA-01 danglers + summaries-with-logic scan",
            tuple(sorted({*seq_off, *summaries_tied}))[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "bp6_critical_path",
            "6. Confirming the critical path is valid",
            cp_status,
            cp_detail,
            "DCMA-14 check 12 — critical-path test",
            cp_off,
        ),
        ScorecardCheck(
            "bp7_float",
            "7. Ensuring reasonable total float",
            float_status,
            float_detail,
            "DCMA-14 checks 6 & 7 — high/negative float",
            tuple(sorted({*hf_off, *nf_off}))[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "bp8_risk",
            "8. Conducting a schedule risk analysis",
            INFO,
            "run the Risk Analysis (SRA) page for a Monte-Carlo confidence range",
            "Tool-supported (engine/sra.py, /sra) — not a property of the file",
            (),
        ),
        ScorecardCheck(
            "bp9_updating",
            "9. Updating the schedule using logic and progress",
            inv_status,
            inv_detail,
            "DCMA-14 check 9 — invalid dates (out-of-date status)",
            inv_off,
        ),
        ScorecardCheck(
            "bp10_baseline",
            "10. Maintaining a baseline schedule",
            PASS if has_baseline else FAIL,
            f"{has_baseline} of {len(tasks)} activities carry a baseline",
            "Model scan — baseline dates/durations present",
            (),
        ),
    ]
    return _make("gao_10", "GAO 10 Best Practices", _GAO_FRAMEWORK, checks)


# --------------------------------------------------------------------------------------
# 3. SRA-readiness gate — is this schedule fit for SRA / FICSM? (INT-02 slides 24-37)
# --------------------------------------------------------------------------------------

_READINESS_FRAMEWORK = (
    "Analysis-Schedule / SRA-readiness synthesis, INT-02 ICEAA deck slides 24-37. Each gate reuses "
    "an already-validated metric or a deterministic model scan; the verdict is whether the file is "
    "fit for a defensible Monte-Carlo / FICSM analysis — no new metric math (Law 2)."
)

#: A "standard" working day spans roughly a normal shift; a near-24h working day compresses the
#: distribution (GAO "no crashing / standard calendar"). Flag well outside 6-12h.
_STD_DAY_MIN_LO = 6 * 60
_STD_DAY_MIN_HI = 12 * 60


def compute_sra_readiness(schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit) -> Scorecard:
    """The SRA-readiness checklist — whether the file is fit for a defensible risk analysis."""
    tasks = non_summary(schedule)
    n = len(tasks)
    wbs_mapped = sum(1 for t in tasks if t.wbs)
    loe = tuple(sorted(t.unique_id for t in tasks if t.is_level_of_effort))
    wmpd = schedule.calendar.working_minutes_per_day or 0

    logic_status, logic_detail, logic_off = _audit_status(audit, "DCMA01")
    res_status, res_detail, res_off = _audit_status(audit, "DCMA10")
    cp_status, cp_detail, cp_off = _audit_status(audit, "DCMA12")
    hc_status, hc_detail, hc_off = _audit_status(audit, "DCMA05")

    checks: list[ScorecardCheck] = [
        ScorecardCheck(
            "wbs_mapped",
            "WBS-mapped activities",
            PASS if n and wbs_mapped == n else FAIL if n else NA,
            _pct(wbs_mapped, n),
            "Model scan — every activity should roll up to the WBS",
            tuple(sorted(t.unique_id for t in tasks if not t.wbs))[:_OFFENDER_CAP],
        ),
        ScorecardCheck(
            "logic_linked",
            "Fully logic-linked network",
            logic_status,
            logic_detail,
            "DCMA-14 check 1 — missing logic",
            logic_off,
        ),
        ScorecardCheck(
            "three_point",
            "Three-point (risk) durations",
            INFO,
            "elicited on the Risk Analysis page — the source file carries single-point durations",
            "Tool-supported (SRA 3-point overrides) — not stored in the schedule file",
            (),
        ),
        ScorecardCheck(
            "resource_loaded",
            "Resource-loaded activities",
            res_status,
            res_detail,
            "DCMA-14 check 10 — resources",
            res_off,
        ),
        ScorecardCheck(
            "critical_path",
            "Critical path defined and valid",
            cp_status,
            cp_detail,
            "DCMA-14 check 12 — critical-path test",
            cp_off,
        ),
        ScorecardCheck(
            "hard_constraints",
            "Minimal hard date constraints",
            hc_status,
            hc_detail,
            "DCMA-14 check 5 — hard constraints",
            hc_off,
        ),
        ScorecardCheck(
            "standard_calendar",
            "Standard working calendar (no crashing)",
            NA if wmpd <= 0 else PASS if _STD_DAY_MIN_LO <= wmpd <= _STD_DAY_MIN_HI else FAIL,
            "unknown calendar" if wmpd <= 0 else f"{wmpd / 60:.1f} h working day",
            "Calendar scan — a near-24h day compresses the risk distribution",
            (),
        ),
        ScorecardCheck(
            "minimal_loe",
            "Minimal level-of-effort / hammock activities",
            _zero_bar(len(loe)) if loe else PASS,
            _pct(len(loe), n),
            "Model scan (is_level_of_effort) — LOE/hammocks are excluded from the risk network",
            loe[:_OFFENDER_CAP],
        ),
    ]
    return _make("sra_readiness", "SRA-Readiness Gate", _READINESS_FRAMEWORK, checks)


def compute_scorecards(
    schedule: Schedule, cpm: CPMResult, audit: ScheduleAudit
) -> tuple[Scorecard, Scorecard, Scorecard]:
    """All three scorecards for one schedule (NASA STAT, GAO 10, SRA-readiness)."""
    return (
        compute_nasa_stat(schedule, cpm, audit),
        compute_gao_scorecard(schedule, cpm, audit),
        compute_sra_readiness(schedule, cpm, audit),
    )


# --------------------------------------------------------------------------------------
# 4. Buffer / reserve sizing — hit a committed date at a chosen confidence (gap #7)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ReserveRow:
    """One confidence level's finish and the reserve needed to protect the committed date."""

    percentile: int
    finish_offset: int  # working-minute offset (pure-CPM axis, same as the SRA CDF)
    finish_date: str  # ISO date via the schedule calendar
    reserve_days: float  # working days of buffer to move the committed date out to this percentile


@dataclass(frozen=True)
class ReserveRecommendation:
    """Reserve sizing over an already-simulated finish distribution (the SRA CDF).

    ``committed_confidence`` is the probability the committed date is met today (the CDF value at
    the committed offset). Each :class:`ReserveRow` gives the finish at a percentile and the working
    days of reserve that would move the committed date out to that confidence (0 when the committed
    date already beats it). The headline recommendations are the P70 and P80 reserves — the SEER
    "realistic target dates & buffers" levels.
    """

    committed_offset: int
    committed_date: str
    committed_confidence: float
    rows: tuple[ReserveRow, ...]
    recommended_p70_days: float
    recommended_p80_days: float


def _finish_at_percentile(cdf: Sequence[tuple[int, float]], pct: float) -> int:
    """Nearest-rank finish offset at ``pct`` (0..100) from an ascending empirical CDF.

    ``cdf`` is ``((finish_offset, cumulative_probability), ...)`` (the SRA S-curve). The nearest-
    rank quantile — the smallest finish whose cumulative probability reaches ``pct`` — is a
    defensible, documented convention for reserve sizing (no interpolation into an unsampled value).
    """
    if not cdf:
        raise ValueError("empty CDF")
    target = pct / 100.0
    for offset, cum in cdf:
        if cum >= target:
            return offset
    return cdf[-1][0]


def _confidence_at(cdf: Sequence[tuple[int, float]], offset: int) -> float:
    """The cumulative probability of finishing on or before ``offset`` (the committed date)."""
    conf = 0.0
    for point_offset, cum in cdf:
        if point_offset <= offset:
            conf = cum
        else:
            break
    return conf


def reserve_recommendation(
    cdf: Sequence[tuple[int, float]],
    committed_offset: int,
    project_start: _dt.datetime,
    calendar: Calendar,
    *,
    percentiles: Sequence[int] = (50, 70, 80, 90),
    committed_date_display: str | None = None,
) -> ReserveRecommendation:
    """Size the schedule reserve to hit ``committed_offset`` at each confidence level.

    Pure arithmetic over the SRA finish CDF — no new simulation, no new statistics. For each
    percentile the finish offset is read from the CDF (nearest-rank); the reserve is the working
    days between the committed date and that finish (0 if the committed date already beats it). The
    working-minutes/day conversion is the schedule calendar's, matching the rest of the tool.
    ``committed_date_display`` overrides the echoed committed date (the caller passes the operator's
    literal input so a calendar-boundary offset round-trip cannot shift the shown date by a day).
    """
    wmpd = calendar.working_minutes_per_day or 480
    rows: list[ReserveRow] = []
    reserve_by_pct: dict[int, float] = {}
    for pct in percentiles:
        finish = _finish_at_percentile(cdf, float(pct))
        reserve_days = round(max(0, finish - committed_offset) / wmpd, 1)
        reserve_by_pct[pct] = reserve_days
        rows.append(
            ReserveRow(
                percentile=pct,
                finish_offset=finish,
                finish_date=offset_to_datetime(project_start, max(finish, 0), calendar)
                .date()
                .isoformat(),
                reserve_days=reserve_days,
            )
        )
    return ReserveRecommendation(
        committed_offset=committed_offset,
        committed_date=committed_date_display
        or offset_to_datetime(project_start, max(committed_offset, 0), calendar).date().isoformat(),
        committed_confidence=round(_confidence_at(cdf, committed_offset), 4),
        rows=tuple(rows),
        recommended_p70_days=reserve_by_pct.get(70, 0.0),
        recommended_p80_days=reserve_by_pct.get(80, 0.0),
    )
