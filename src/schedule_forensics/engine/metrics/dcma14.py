"""DCMA 14-point assessment — the primary Acumen-parity schedule-health framework.

Reproduces Acumen Fuse's "Fuse® Analyst Report" ribbon for Project2/Project5
(`docs/PLAN/PARITY-TARGETS.md §B`). Each check returns a :class:`MetricResult`
(count / population / measured value / threshold / pass-fail / offender UIDs). Float
and critical-path inputs come from the CPM engine (ADR-0010); date checks use the
schedule's stored dates and ``status_date`` (the data date is metric-relevant: BEI,
Missed and the invalid-date checks change as it advances).

Definitions validated against the golden P2/P5 exports (counts/percentages match
exactly) with one documented residual (ADR-0012): **High Float** counts one fewer
incomplete activity than Acumen (43/40 vs 44/41) because Acumen reads MS Project's
progress-aware total float for a single near-status activity per project; the
pass/fail (≫5%) is unaffected. Tracked for M9.
"""

from __future__ import annotations

from collections import Counter

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    Direction,
    MetricResult,
    effective_total_float,
    evaluate,
    forty_four_days_min,
    is_incomplete,
    non_summary,
    percent,
    to_offset,
)
from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType

#: MS Project hard/mandatory constraints (DCMA-05). SNET/FNET are soft (excluded).
_HARD_CONSTRAINTS = frozenset(
    {ConstraintType.MSO, ConstraintType.MFO, ConstraintType.SNLT, ConstraintType.FNLT}
)
#: Injected delay for the critical-path test (DCMA-12), in working DAYS — converted
#: on the schedule's own calendar at test time.
_CRITICAL_PATH_TEST_DELAY_DAYS = 100


def compute_dcma14(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """Compute all 14 DCMA checks, keyed by id (``"DCMA01"`` … ``"DCMA14"`` with
    ``DCMA04`` split into FS / SS-FF / SF rows to mirror the Acumen ribbon)."""
    tasks = non_summary(schedule)
    real_ids = {t.unique_id for t in tasks}
    incomplete = [t for t in tasks if is_incomplete(t)]
    pct_by = {t.unique_id: t.percent_complete for t in tasks}
    n_tasks, n_inc = len(tasks), len(incomplete)

    # logic links restricted to the activity network
    links = [
        r
        for r in schedule.relationships
        if r.predecessor_id in real_ids and r.successor_id in real_ids
    ]
    n_links = len(links)
    has_pred: set[int] = set()
    has_succ: set[int] = set()
    npred: Counter[int] = Counter()
    for r in links:
        has_succ.add(r.predecessor_id)
        has_pred.add(r.successor_id)
        npred[r.successor_id] += 1

    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    tf = {uid: t.total_float for uid, t in result.timings.items()}
    status_off = to_offset(schedule, schedule.status_date)

    out: dict[str, MetricResult] = {}

    # DCMA-01 Logic — incomplete activities missing a predecessor and/or successor.
    logic_off = tuple(
        t.unique_id
        for t in incomplete
        if t.unique_id not in has_pred or t.unique_id not in has_succ
    )
    out["DCMA01"] = _r("DCMA01", "Logic", len(logic_off), n_inc, "%", 5.0, Direction.LE, logic_off)

    # DCMA-02 Leads — incomplete ACTIVITIES with a negative-lag predecessor link (count,
    # must be 0). Fuse counts activities, not links ("0 activities (0%) have 2. Leads" in
    # the golden Fuse briefing): two leads into one task is ONE offender.
    leads = tuple(
        dict.fromkeys(
            r.successor_id
            for r in links
            if r.lag_minutes < 0 and pct_by.get(r.successor_id, 0.0) < 100.0
        )
    )
    out["DCMA02"] = MetricResult(
        "DCMA02",
        "Leads",
        len(leads),
        n_links,
        float(len(leads)),
        "count",
        CheckStatus.NOT_APPLICABLE
        if n_links == 0
        else evaluate(float(len(leads)), 0.0, Direction.EQ),
        0.0,
        Direction.EQ,
        leads,
    )

    # DCMA-03 Lags — incomplete ACTIVITIES with a positive-lag predecessor link
    # (activity-counted like DCMA-02; the golden P5 value 1 is one such activity).
    lags = tuple(
        dict.fromkeys(
            r.successor_id
            for r in links
            if r.lag_minutes > 0 and pct_by.get(r.successor_id, 0.0) < 100.0
        )
    )
    out["DCMA03"] = _r("DCMA03", "Lags", len(lags), n_links, "%", 5.0, Direction.LE, lags)

    # DCMA-04 Relationship types — FS share (≥90%); SS/FF and SF reported separately.
    fs = sum(1 for r in links if r.type is RelationshipType.FS)
    ssff = tuple(
        r.successor_id
        for r in links
        if r.type in (RelationshipType.SS, RelationshipType.FF)
        and pct_by.get(r.successor_id, 0.0) < 100.0
    )
    sf = tuple(
        r.successor_id
        for r in links
        if r.type is RelationshipType.SF and pct_by.get(r.successor_id, 0.0) < 100.0
    )
    out["DCMA04_FS"] = _r("DCMA04_FS", "FS Relationships", fs, n_links, "%", 90.0, Direction.GE, ())
    out["DCMA04_SSFF"] = _r(
        "DCMA04_SSFF", "SS/FF Relationships", len(ssff), n_links, "%", None, None, ssff
    )
    out["DCMA04_SF"] = _r("DCMA04_SF", "SF Relationships", len(sf), n_links, "%", None, None, sf)

    # DCMA-05 Hard constraints.
    hard = tuple(t.unique_id for t in tasks if t.constraint_type in _HARD_CONSTRAINTS)
    out["DCMA05"] = _r(
        "DCMA05", "Hard Constraints", len(hard), n_tasks, "%", 5.0, Direction.LE, hard
    )

    # DCMA-06 High float — incomplete activities with total float > 44 working days
    # (the day threshold converts on this schedule's own calendar).
    forty_four = forty_four_days_min(schedule)
    # High Float — incomplete activities with total float > 44 working days. Scored on the source
    # tool's STORED Total Slack when present (matches Acumen on progressed files — verified 44/44 on
    # the authoritative Project2/Project5 exports, closing the former recomputed-float residual,
    # ADR-0012/ADR-0109), else the recomputed CPM float (ADR-0080).
    high_float = tuple(
        t.unique_id
        for t in incomplete
        if effective_total_float(t, tf.get(t.unique_id, 0)) > forty_four
    )
    out["DCMA06"] = _r(
        "DCMA06", "High Float", len(high_float), n_inc, "%", 5.0, Direction.LE, high_float
    )

    # DCMA-07 Negative float — incomplete activities with total float < 0. Scored on the source
    # tool's STORED Total Slack when present (Acumen fidelity on progressed files), else the
    # recomputed CPM float (ADR-0080).
    neg = tuple(
        t.unique_id for t in incomplete if effective_total_float(t, tf.get(t.unique_id, 0)) < 0
    )
    out["DCMA07"] = _r("DCMA07", "Negative Float", len(neg), n_inc, "%", 0.0, Direction.EQ, neg)

    # DCMA-08 High duration — incomplete activities with baseline duration > 44 days.
    high_dur = tuple(
        t.unique_id
        for t in incomplete
        if t.baseline_duration_minutes is not None
        and t.baseline_duration_minutes > (44 * 1440 if t.duration_is_elapsed else forty_four)
    )
    out["DCMA08"] = _r(
        "DCMA08", "High Duration", len(high_dur), n_inc, "%", 5.0, Direction.LE, high_dur
    )

    # DCMA-09 Invalid dates — actuals after the status date, or an incomplete activity
    # whose forecast start is already in the past (vs the status date).
    invalid: list[int] = []
    status_dt = schedule.status_date
    for t in tasks:
        bad = False
        if status_dt is not None:
            if t.actual_start is not None and t.actual_start > status_dt:
                bad = True
            if t.actual_finish is not None and t.actual_finish > status_dt:
                bad = True
        if (
            is_incomplete(t)
            and t.actual_start is None
            and status_off is not None
            and t.unique_id in result.timings
            and result.timings[t.unique_id].early_start < status_off
        ):
            bad = True
        if bad:
            invalid.append(t.unique_id)
    if status_dt is None:
        # without a data date neither condition can be assessed — NA, not a fabricated PASS
        out["DCMA09"] = MetricResult(
            "DCMA09",
            "Invalid Dates",
            0,
            n_tasks,
            0.0,
            "%",
            CheckStatus.NOT_APPLICABLE,
            0.0,
            Direction.EQ,
        )
    else:
        out["DCMA09"] = _r(
            "DCMA09", "Invalid Dates", len(invalid), n_tasks, "%", 0.0, Direction.EQ, tuple(invalid)
        )

    # DCMA-10 Resources — incomplete, real-duration activities with no resource assigned.
    candidates = [t for t in incomplete if t.duration_minutes > 0]
    no_res = tuple(t.unique_id for t in candidates if not t.resource_names)
    out["DCMA10"] = _r(
        "DCMA10", "Resources", len(no_res), len(candidates), "%", 5.0, Direction.LE, no_res
    )

    # DCMA-11 Missed activities — baselined-due-by-status activities not finished on time.
    due = [
        t
        for t in tasks
        if t.baseline_finish is not None
        and status_dt is not None
        and t.baseline_finish <= status_dt
    ]
    missed = tuple(
        t.unique_id
        for t in due
        if not (
            t.percent_complete >= 100.0
            and t.actual_finish is not None
            and t.baseline_finish is not None
            and t.actual_finish <= t.baseline_finish
        )
    )
    out["DCMA11"] = _r(
        "DCMA11", "Missed Activities", len(missed), len(due), "%", 5.0, Direction.LE, missed
    )

    # DCMA-12 Critical path test — a delay on a critical activity must flow to the finish.
    out["DCMA12"] = _critical_path_test(schedule, result)

    # DCMA-13 CPLI — (critical-path length + project total float) / critical-path length.
    out["DCMA13"] = _cpli(result, status_off)

    # DCMA-14 BEI — see compute_bei (ADR-0089). Factored out so the grouping/breakdown UI can
    # score BEI per group without a CPM re-solve (it is pure counts), one source of truth.
    out["DCMA14"] = compute_bei(schedule)

    return out


def compute_bei(schedule: Schedule) -> MetricResult:
    """DCMA-14 Baseline Execution Index — Acumen "BEI - Value Tasks" (ADR-0089, corrects ADR-0085):

        countif(PercentComplete,"=100%") / SUM(IF(BaselineFinish<=ProjectTimeNow,1))

    over the Normal-activity filter (Normal=true, Milestone=false, Summary=false) — i.e.
    numerator = complete NORMAL tasks (non-summary, non-milestone); denominator = NORMAL tasks
    baselined to finish by the data date. No baseline-duration filter and no missing-baseline term
    (ADR-0085 added both; Acumen's real Large-File ribbon disproved them). Validated vs Acumen:
    goldens 0.74 / 0.59 EXACT; Large-File denominator EXACT (1228), numerator within 2 of 632.
    Early completions count (BEI can exceed 1.0). Pure counts — no CPM — so the grouping UI can
    score it per group cheaply.
    """
    status_dt = schedule.status_date
    bei_normal = [t for t in non_summary(schedule) if not t.is_milestone]
    bei_complete = sum(1 for t in bei_normal if t.percent_complete >= 100.0)
    bei_due = [
        t
        for t in bei_normal
        if t.baseline_finish is not None
        and status_dt is not None
        and t.baseline_finish <= status_dt
    ]
    bei_den = len(bei_due)
    # the activities dragging BEI below 1.0 — baselined-due Normal tasks not finished (citable)
    bei_offenders = tuple(t.unique_id for t in bei_due if t.actual_finish is None)
    if bei_den and status_dt is not None:
        bei = bei_complete / bei_den
        return MetricResult(
            "DCMA14",
            "BEI",
            bei_complete,
            bei_den,
            round(bei, 2),
            "ratio",
            evaluate(bei, 0.95, Direction.GE),
            0.95,
            Direction.GE,
            bei_offenders,
        )
    return MetricResult(
        "DCMA14",
        "BEI",
        bei_complete,
        bei_den,
        0.0,
        "ratio",
        CheckStatus.NOT_APPLICABLE,
        0.95,
        Direction.GE,
    )


def _r(
    metric_id: str,
    name: str,
    count: int,
    population: int,
    unit: str,
    threshold: float | None,
    direction: Direction | None,
    offenders: tuple[int, ...],
) -> MetricResult:
    """Build a percentage-valued :class:`MetricResult` and evaluate it.

    An empty population is NOT_APPLICABLE, never a fabricated ``0%`` — a GE-direction
    check (FS Relationships ≥ 90%) would otherwise FAIL with zero offenders on a
    schedule with no logic links at all (an offender-less finding then violates the §6
    citation contract downstream).
    """
    value = percent(count, population)
    status = (
        CheckStatus.NOT_APPLICABLE if population == 0 else evaluate(value, threshold, direction)
    )
    return MetricResult(
        metric_id,
        name,
        count,
        population,
        value,
        unit,
        status,
        threshold,
        direction,
        offenders,
    )


def _critical_path_test(schedule: Schedule, result: CPMResult) -> MetricResult:
    """Inject a delay on the lowest-UID critical activity; the project finish must move
    by exactly that delay (a continuous, controlling critical path). 0 == pass."""
    by_id = {t.unique_id: t for t in schedule.tasks}
    targets = [
        tid
        for tid in result.critical_path
        if tid in by_id
        and by_id[tid].duration_minutes > 0
        and not by_id[tid].is_summary
        and by_id[tid].is_active  # inactive tasks are off the network (ADR-0128)
    ]
    if not targets:
        return MetricResult(
            "DCMA12",
            "Critical Path Test",
            0,
            0,
            0.0,
            "count",
            CheckStatus.NOT_APPLICABLE,
            0.0,
            Direction.EQ,
        )
    target = by_id[min(targets)]
    delay_min = _CRITICAL_PATH_TEST_DELAY_DAYS * schedule.calendar.working_minutes_per_day
    delayed = target.model_copy(update={"duration_minutes": target.duration_minutes + delay_min})
    perturbed = schedule.model_copy(
        update={
            "tasks": tuple(
                delayed if t.unique_id == target.unique_id else t for t in schedule.tasks
            )
        }
    )
    # `result` already proved the network schedulable; only a duration grew, so this
    # recompute cannot newly cycle/refuse — any CPMError propagates (fail loud).
    new_result = compute_cpm(perturbed)
    moved = new_result.project_finish - result.project_finish == delay_min
    measured = 0.0 if moved else 1.0
    return MetricResult(
        "DCMA12",
        "Critical Path Test",
        int(measured),
        1,
        measured,
        "count",
        evaluate(measured, 0.0, Direction.EQ),
        0.0,
        Direction.EQ,
        # on FAIL, cite the tested activity: its injected delay did not flow to the finish —
        # the verifiable starting point for repairing the broken controlling logic (§6).
        offender_uids=() if moved else (target.unique_id,),
    )


def _cpli(result: CPMResult, status_offset: int | None) -> MetricResult:
    """Critical Path Length Index = (remaining critical-path length + project total float) ÷
    remaining critical-path length. The denominator is the **remaining** length — from the
    data date (status) to the project finish — matching the Bible's ``ProjectRemainingDuration``
    and the DCMA standard (ADR-0086), not the full project span. With no imposed deadline the
    controlling path's float is 0, so CPLI = 1; a negative project float (behind an imposed
    finish) drives it < 1, and the remaining denominator makes that deviation correctly sharp."""
    # remaining critical-path length: data date -> project finish (working minutes); falls back
    # to the full network length when the schedule carries no status date.
    length = result.project_finish - max(status_offset or 0, 0)
    if length <= 0:
        return MetricResult(
            "DCMA13", "CPLI", 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE, 0.95, Direction.GE
        )
    project_float = min((t.total_float for t in result.timings.values()), default=0)
    cpli = (length + project_float) / length
    status = evaluate(cpli, 0.95, Direction.GE)
    # on FAIL, cite the most-negative-float activities — the chain that is consuming the
    # project's float and dragging CPLI under threshold (verifiable, §6).
    offenders: tuple[int, ...] = ()
    if status is CheckStatus.FAIL:
        offenders = tuple(
            sorted(uid for uid, t in result.timings.items() if t.total_float == project_float)
        )
    return MetricResult(
        "DCMA13",
        "CPLI",
        0,
        1,
        round(cpli, 2),
        "ratio",
        status,
        0.95,
        Direction.GE,
        offenders,
    )
