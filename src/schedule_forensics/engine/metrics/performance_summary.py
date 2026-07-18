"""Performance Analysis Summary metrics (operator 2026-07-10, ADR-0182).

Recreates, from schedule metadata alone, the seven graph families of the operator's
``PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx`` reference workbook:

- **G1 — Work-to-Go census**: per calendar month, the activities ACTIVE in that month (their
  current span overlaps it) split by type (normal / milestone / summary), by completion state
  (completed vs to-go as of the data date), and by longest-path membership.
- **G2 — Bow-wave activity flow**: per month, activities baselined / scheduled / actually
  starting and finishing, plus the late-start / late-finish delay buckets (≤30 / 31-60 / >60
  calendar days vs baseline).
- **G3 — Execution index curves**: the monthly BEI (cumulative actual ÷ cumulative baselined,
  starts and finishes) and monthly HMI hit rates (+ 3-month rolling average). The reference
  workbook leaves its CEI rows empty (a cross-version measure), so no per-month CEI is
  fabricated here either.
- **G4 — Workoff burden**: per month, baseline execution categorized (executed to plan /
  early / workoff of past-due baseline / delayed future baseline), with the not-yet-done
  backlog mirrored BELOW the axis at the month the baseline placed it.
- **G5 — Duration Ratio (DRM)**: per completed task, actual duration ÷ baseline duration —
  the cumulative-probability S-curve plus a middle-70% histogram.
- **G6/G7 quads** use :func:`to_go_snapshot` (to-go starts/finishes vs remaining baseline,
  critical share of the to-go work); the portfolio assembly lives at the web layer where all
  loaded versions are in hand.

Nothing here is imputed: a month with no qualifying population reads ``None`` (rendered N/A),
and every count is reproducible from the ``Task`` fields it cites.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Safety cap on the month axis (30 years). A corrupt date (year 2999) would otherwise build a
#: multi-thousand-column series; beyond the cap the axis is truncated and the caller discloses.
_MAX_MONTHS = 360


def _month(d: dt.datetime | dt.date) -> dt.date:
    return dt.date(d.year, d.month, 1)


def _next_month(m: dt.date) -> dt.date:
    return dt.date(m.year + 1, 1, 1) if m.month == 12 else dt.date(m.year, m.month + 1, 1)


def _month_key(m: dt.date) -> str:
    return f"{m.year:04d}-{m.month:02d}"


def _span(t: Task) -> tuple[dt.datetime, dt.datetime] | None:
    """The task's CURRENT occupied span: actuals where they exist, else scheduled dates."""
    s = t.actual_start or t.start or t.baseline_start
    f = t.actual_finish or t.finish or t.baseline_finish
    s = s if s is not None else f
    f = f if f is not None else s
    if s is None or f is None:  # both were None: the task carries no dates at all
        return None
    return (s, f) if s <= f else (f, s)


def month_axis(schedule: Schedule) -> tuple[dt.date, ...]:
    """First-of-month buckets spanning every date the schedule carries (all tasks, baseline +
    current + actual), truncated at ``_MAX_MONTHS``. Empty when the file has no dates."""
    dates: list[dt.datetime] = []
    for t in schedule.tasks:
        candidates = (
            t.start,
            t.finish,
            t.actual_start,
            t.actual_finish,
            t.baseline_start,
            t.baseline_finish,
        )
        for d in candidates:
            if d is not None:
                dates.append(d)
    if schedule.status_date is not None:
        dates.append(schedule.status_date)
    if not dates:
        return ()
    m = _month(min(dates))
    last = _month(max(dates))
    out: list[dt.date] = []
    while m <= last and len(out) < _MAX_MONTHS:
        out.append(m)
        m = _next_month(m)
    return tuple(out)


# ---------------------------------------------------------------------------- G1: census


@dataclass(frozen=True)
class CensusMonth:
    """One month of the work-to-go census (counts of activities ACTIVE in the month)."""

    month: str  # "YYYY-MM"
    normal: int  # normal tasks active in the month
    milestones: int
    summaries: int
    tm_total: int  # tasks & milestones (non-summary) active in the month
    tm_completed: int  # of those, complete as of the data date
    tm_to_go: int  # of those, incomplete (the work-to-go profile)
    normal_to_go: int
    lp_tm: int  # tasks & milestones active this month that sit on the longest path
    lp_normal: int


@dataclass(frozen=True)
class WorkToGoCensus:
    months: tuple[CensusMonth, ...]
    status_month: str | None  # the data-date month key (the census's completed/to-go split)
    truncated: bool  # True when the month axis hit the safety cap (disclosed, never silent)


def work_to_go_census(schedule: Schedule, critical_uids: frozenset[int]) -> WorkToGoCensus:
    """G1 — per month: activities whose current span overlaps the month, split by type,
    completion state (vs the data date) and longest-path membership (``critical_uids`` is the
    effective-critical set the rest of the tool uses as the longest path).

    Bucketed (ADR-0261 P3): the axis is contiguous first-of-month buckets, so a task's span maps
    to a month-index range arithmetically; each task adds +1/-1 deltas at its range ends and one
    prefix-sum pass builds every month — O(tasks + months), not O(months x tasks). Pure integer
    re-ordering of the same additions: every count is identical to the per-month scan it
    replaces (pinned by tests/engine/test_performance_summary_census.py's equivalence test)."""
    axis = month_axis(schedule)
    n = len(axis)
    status = schedule.status_date
    if n == 0:
        return WorkToGoCensus(
            months=(),
            status_month=_month_key(_month(status)) if status is not None else None,
            truncated=False,
        )
    y0, m0 = axis[0].year, axis[0].month

    def _idx(d: dt.date) -> int:
        return (d.year - y0) * 12 + (d.month - m0)

    # one delta array per counter; index len(axis) absorbs the -1 of ranges ending on the last month
    counters = [[0] * (n + 1) for _ in range(8)]
    (
        d_normal,
        d_milestones,
        d_summaries,
        d_completed,
        d_to_go,
        d_normal_to_go,
        d_lp_tm,
        d_lp_normal,
    ) = counters
    for t in schedule.tasks:
        sp = _span(t)
        if sp is None:
            continue
        lo = max(0, _idx(_month(sp[0].date())))
        hi = min(n - 1, _idx(_month(sp[1].date())))
        if lo > hi:  # entirely outside the (possibly truncated) axis
            continue
        if t.is_summary:
            d_summaries[lo] += 1
            d_summaries[hi + 1] -= 1
            continue
        if t.is_milestone:
            d_milestones[lo] += 1
            d_milestones[hi + 1] -= 1
        else:
            d_normal[lo] += 1
            d_normal[hi + 1] -= 1
        if t.is_complete:
            d_completed[lo] += 1
            d_completed[hi + 1] -= 1
        else:
            d_to_go[lo] += 1
            d_to_go[hi + 1] -= 1
            if not t.is_milestone:
                d_normal_to_go[lo] += 1
                d_normal_to_go[hi + 1] -= 1
        if t.unique_id in critical_uids:
            d_lp_tm[lo] += 1
            d_lp_tm[hi + 1] -= 1
            if not t.is_milestone:
                d_lp_normal[lo] += 1
                d_lp_normal[hi + 1] -= 1

    months: list[CensusMonth] = []
    running = [0] * 8
    for i, m in enumerate(axis):
        for c in range(8):
            running[c] += counters[c][i]
        normal, milestones, summaries, tm_completed, tm_to_go, normal_to_go, lp_tm, lp_normal = (
            running
        )
        months.append(
            CensusMonth(
                month=_month_key(m),
                normal=normal,
                milestones=milestones,
                summaries=summaries,
                tm_total=normal + milestones,
                tm_completed=tm_completed,
                tm_to_go=tm_to_go,
                normal_to_go=normal_to_go,
                lp_tm=lp_tm,
                lp_normal=lp_normal,
            )
        )
    return WorkToGoCensus(
        months=tuple(months),
        status_month=_month_key(_month(status)) if status is not None else None,
        truncated=n == _MAX_MONTHS,
    )


# ---------------------------------------------------------------- G2/G3: bow-wave flow


@dataclass(frozen=True)
class FlowMonth:
    """One month of activity starts/finishes flow (G2) + execution index curves (G3)."""

    month: str
    baselined_starts: int  # baseline start falls in this month
    scheduled_starts: int  # current (scheduled/actual) start falls in this month
    actual_starts: int  # actual start falls in this month
    baselined_finishes: int
    scheduled_finishes: int
    actual_finishes: int
    # late buckets (calendar days actual vs baseline, bucketed at the ACTUAL month):
    started_late_30: int  # 1..30 days late
    started_late_60: int  # 31..60
    started_late_over: int  # >60
    finished_late_30: int
    finished_late_60: int
    finished_late_over: int
    # G3 curves (None = no qualifying population, or month after the data date):
    bei_starts: float | None  # cumulative actual starts / cumulative baselined starts
    bei_finishes: float | None
    hmi_starts: float | None  # of tasks baselined to start THIS month, share started by month-end
    hmi_finishes: float | None
    hmi_starts_roll3: float | None  # 3-month rolling average of the defined hmi values
    hmi_finishes_roll3: float | None
    cum_baselined_starts: int
    cum_scheduled_starts: int
    cum_actual_starts: int
    cum_baselined_finishes: int
    cum_scheduled_finishes: int
    cum_actual_finishes: int
    # per-month UID lists behind the late-bucket BARS (drill; each list length == its count above)
    started_late_30_uids: tuple[int, ...] = ()
    started_late_60_uids: tuple[int, ...] = ()
    started_late_over_uids: tuple[int, ...] = ()
    finished_late_30_uids: tuple[int, ...] = ()
    finished_late_60_uids: tuple[int, ...] = ()
    finished_late_over_uids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ActivityFlow:
    months: tuple[FlowMonth, ...]
    status_month: str | None
    truncated: bool


def _bucket_late(days: int) -> int | None:
    """0 / 1 / 2 for the ≤30 / 31-60 / >60 late buckets; None when not late."""
    if days <= 0:
        return None
    return 0 if days <= 30 else 1 if days <= 60 else 2


def activity_flow(schedule: Schedule) -> ActivityFlow:
    """G2 + G3 — monthly starts/finishes (baselined / scheduled / actual), late buckets, and
    the BEI / HMI execution curves. Index curves stop at the data-date month (no index is
    fabricated for future months, matching the reference workbook)."""
    axis = month_axis(schedule)
    idx = {_month_key(m): i for i, m in enumerate(axis)}
    n = len(axis)
    z = [0] * n
    bl_s, sc_s, ac_s = list(z), list(z), list(z)
    bl_f, sc_f, ac_f = list(z), list(z), list(z)
    late_s = [list(z), list(z), list(z)]
    late_f = [list(z), list(z), list(z)]
    # parallel UID accumulators — appended in lockstep with the count increments below so the
    # drill lists exactly the activities each late-bucket bar counts (never diverges).
    late_s_uids: list[list[list[int]]] = [[[] for _ in range(n)] for _ in range(3)]
    late_f_uids: list[list[list[int]]] = [[[] for _ in range(n)] for _ in range(3)]
    hmi_s_hit, hmi_s_due = list(z), list(z)
    hmi_f_hit, hmi_f_due = list(z), list(z)

    def _at(d: dt.datetime | None) -> int | None:
        return None if d is None else idx.get(_month_key(_month(d)))

    for t in non_summary(schedule):
        i_bls, i_blf = _at(t.baseline_start), _at(t.baseline_finish)
        i_ss, i_sf = _at(t.actual_start or t.start), _at(t.actual_finish or t.finish)
        i_as, i_af = _at(t.actual_start), _at(t.actual_finish)
        if i_bls is not None:
            bl_s[i_bls] += 1
        if i_blf is not None:
            bl_f[i_blf] += 1
        if i_ss is not None:
            sc_s[i_ss] += 1
        if i_sf is not None:
            sc_f[i_sf] += 1
        if i_as is not None:
            ac_s[i_as] += 1
        if i_af is not None:
            ac_f[i_af] += 1
        if t.actual_start is not None and t.baseline_start is not None and i_as is not None:
            b = _bucket_late((t.actual_start.date() - t.baseline_start.date()).days)
            if b is not None:
                late_s[b][i_as] += 1
                late_s_uids[b][i_as].append(t.unique_id)
        if t.actual_finish is not None and t.baseline_finish is not None and i_af is not None:
            b = _bucket_late((t.actual_finish.date() - t.baseline_finish.date()).days)
            if b is not None:
                late_f[b][i_af] += 1
                late_f_uids[b][i_af].append(t.unique_id)
        # HMI hit = the actual landed no later than the END of its baselined month
        if i_bls is not None:
            hmi_s_due[i_bls] += 1
            if t.actual_start is not None and _month(t.actual_start) <= axis[i_bls]:
                hmi_s_hit[i_bls] += 1
        if i_blf is not None:
            hmi_f_due[i_blf] += 1
            if t.actual_finish is not None and _month(t.actual_finish) <= axis[i_blf]:
                hmi_f_hit[i_blf] += 1

    status = schedule.status_date
    status_i = None if status is None else idx.get(_month_key(_month(status)))

    def _roll3(vals: list[float | None], i: int) -> float | None:
        window = [v for v in vals[max(0, i - 2) : i + 1] if v is not None]
        return round(sum(window) / len(window), 2) if window else None

    months: list[FlowMonth] = []
    cbs = css = cas = cbf = csf = caf = 0
    hmi_s_vals: list[float | None] = []
    hmi_f_vals: list[float | None] = []
    for i, m in enumerate(axis):
        cbs, css, cas = cbs + bl_s[i], css + sc_s[i], cas + ac_s[i]
        cbf, csf, caf = cbf + bl_f[i], csf + sc_f[i], caf + ac_f[i]
        in_past = status_i is not None and i <= status_i
        bei_s = round(cas / cbs, 2) if in_past and cbs else None
        bei_f = round(caf / cbf, 2) if in_past and cbf else None
        hmi_s = round(hmi_s_hit[i] / hmi_s_due[i], 2) if in_past and hmi_s_due[i] else None
        hmi_f = round(hmi_f_hit[i] / hmi_f_due[i], 2) if in_past and hmi_f_due[i] else None
        hmi_s_vals.append(hmi_s)
        hmi_f_vals.append(hmi_f)
        months.append(
            FlowMonth(
                month=_month_key(m),
                baselined_starts=bl_s[i],
                scheduled_starts=sc_s[i],
                actual_starts=ac_s[i],
                baselined_finishes=bl_f[i],
                scheduled_finishes=sc_f[i],
                actual_finishes=ac_f[i],
                started_late_30=late_s[0][i],
                started_late_60=late_s[1][i],
                started_late_over=late_s[2][i],
                finished_late_30=late_f[0][i],
                finished_late_60=late_f[1][i],
                finished_late_over=late_f[2][i],
                bei_starts=bei_s,
                bei_finishes=bei_f,
                hmi_starts=hmi_s,
                hmi_finishes=hmi_f,
                hmi_starts_roll3=_roll3(hmi_s_vals, i) if in_past else None,
                hmi_finishes_roll3=_roll3(hmi_f_vals, i) if in_past else None,
                cum_baselined_starts=cbs,
                cum_scheduled_starts=css,
                cum_actual_starts=cas,
                cum_baselined_finishes=cbf,
                cum_scheduled_finishes=csf,
                cum_actual_finishes=caf,
                started_late_30_uids=tuple(late_s_uids[0][i]),
                started_late_60_uids=tuple(late_s_uids[1][i]),
                started_late_over_uids=tuple(late_s_uids[2][i]),
                finished_late_30_uids=tuple(late_f_uids[0][i]),
                finished_late_60_uids=tuple(late_f_uids[1][i]),
                finished_late_over_uids=tuple(late_f_uids[2][i]),
            )
        )
    return ActivityFlow(
        months=tuple(months),
        status_month=_month_key(_month(status)) if status is not None else None,
        truncated=n == _MAX_MONTHS,
    )


# ------------------------------------------------------------------- G4: workoff burden


@dataclass(frozen=True)
class BurdenMonth:
    """One month of the workoff-burden categorization (starts + finishes).

    Above-axis categories are bucketed at the month the event HAPPENED (actual month) or is
    now FORECAST to happen (scheduled month); ``backlog`` is the negative mirror — the same
    not-yet-done work plotted at the month its BASELINE placed it, so the chart shows both
    where the un-done work was promised and where it now sits."""

    month: str
    # starts
    s_bl_plan: int  # baselined this month AND started this month (executed to plan)
    s_early: int  # started this month, baseline was in a LATER month
    s_workoff: int  # started this month, baseline was in an EARLIER month (backlog burned)
    s_past_due: int  # NOT started, baseline past-due (≤ data date), now forecast this month
    s_delayed: int  # NOT started, future baseline, forecast later than baselined (slipping)
    s_backlog: int  # NEGATIVE — not-started work at the month its baseline start promised
    # finishes
    f_bl_plan: int
    f_early: int
    f_workoff: int
    f_past_due: int
    f_delayed: int
    f_backlog: int  # NEGATIVE
    # per-month UID lists behind each category bar (drill; |count| == len). Backlog is a negative
    # count mirrored below the axis; its UID list carries exactly that not-done work.
    s_bl_plan_uids: tuple[int, ...] = ()
    s_early_uids: tuple[int, ...] = ()
    s_workoff_uids: tuple[int, ...] = ()
    s_past_due_uids: tuple[int, ...] = ()
    s_delayed_uids: tuple[int, ...] = ()
    s_backlog_uids: tuple[int, ...] = ()
    f_bl_plan_uids: tuple[int, ...] = ()
    f_early_uids: tuple[int, ...] = ()
    f_workoff_uids: tuple[int, ...] = ()
    f_past_due_uids: tuple[int, ...] = ()
    f_delayed_uids: tuple[int, ...] = ()
    f_backlog_uids: tuple[int, ...] = ()


@dataclass(frozen=True)
class WorkoffBurden:
    months: tuple[BurdenMonth, ...]
    status_month: str | None
    truncated: bool


def workoff_burden(schedule: Schedule) -> WorkoffBurden:
    """G4 — baseline-execution categories per month, with the un-done backlog mirrored below
    the axis at its baselined month. Only activities carrying a baseline date participate in
    their respective (starts / finishes) categorization; others simply have nothing to
    categorize against (never guessed)."""
    axis = month_axis(schedule)
    idx = {_month_key(m): i for i, m in enumerate(axis)}
    n = len(axis)
    keys = (
        "s_bl_plan",
        "s_early",
        "s_workoff",
        "s_past_due",
        "s_delayed",
        "s_backlog",
        "f_bl_plan",
        "f_early",
        "f_workoff",
        "f_past_due",
        "f_delayed",
        "f_backlog",
    )
    acc: dict[str, list[int]] = {k: [0] * n for k in keys}
    # parallel UID accumulators — appended in lockstep with every count change below, so the
    # drill lists exactly the activities each category bar counts (|count| == len for backlog).
    acc_uids: dict[str, list[list[int]]] = {k: [[] for _ in range(n)] for k in keys}
    status = schedule.status_date
    dd_month = _month(status) if status is not None else None

    def _at(d: dt.datetime | None) -> int | None:
        return None if d is None else idx.get(_month_key(_month(d)))

    def _one(
        prefix: str,
        uid: int,
        baseline: dt.datetime | None,
        actual: dt.datetime | None,
        scheduled: dt.datetime | None,
    ) -> None:
        i_bl = _at(baseline)
        if i_bl is None or baseline is None:
            return
        if actual is not None:
            i_ac = _at(actual)
            if i_ac is None:
                return
            bm, am = _month(baseline), _month(actual)
            kind = "bl_plan" if am == bm else "early" if am < bm else "workoff"
            acc[f"{prefix}_{kind}"][i_ac] += 1
            acc_uids[f"{prefix}_{kind}"][i_ac].append(uid)
            return
        # not done yet: mirror the backlog at the baselined month…
        acc[f"{prefix}_backlog"][i_bl] -= 1
        acc_uids[f"{prefix}_backlog"][i_bl].append(uid)
        # …and place the forecast above the axis where it now sits
        i_sc = _at(scheduled)
        if i_sc is None or scheduled is None:
            return
        bm, sm = _month(baseline), _month(scheduled)
        if dd_month is not None and bm <= dd_month:
            acc[f"{prefix}_past_due"][i_sc] += 1
            acc_uids[f"{prefix}_past_due"][i_sc].append(uid)
        elif sm > bm:
            acc[f"{prefix}_delayed"][i_sc] += 1
            acc_uids[f"{prefix}_delayed"][i_sc].append(uid)
        # future baseline still forecast on plan: no bar (nothing has deviated)

    for t in non_summary(schedule):
        _one("s", t.unique_id, t.baseline_start, t.actual_start, t.start)
        _one("f", t.unique_id, t.baseline_finish, t.actual_finish, t.finish)

    def _burden_month(i: int, m: dt.date) -> BurdenMonth:
        # counts + parallel UID lists, one keyword per field (a `**dict` splat no longer
        # type-checks now that the dataclass mixes int and tuple fields).
        c = {k: acc[k][i] for k in keys}
        return BurdenMonth(
            month=_month_key(m),
            s_bl_plan=c["s_bl_plan"],
            s_early=c["s_early"],
            s_workoff=c["s_workoff"],
            s_past_due=c["s_past_due"],
            s_delayed=c["s_delayed"],
            s_backlog=c["s_backlog"],
            f_bl_plan=c["f_bl_plan"],
            f_early=c["f_early"],
            f_workoff=c["f_workoff"],
            f_past_due=c["f_past_due"],
            f_delayed=c["f_delayed"],
            f_backlog=c["f_backlog"],
            s_bl_plan_uids=tuple(acc_uids["s_bl_plan"][i]),
            s_early_uids=tuple(acc_uids["s_early"][i]),
            s_workoff_uids=tuple(acc_uids["s_workoff"][i]),
            s_past_due_uids=tuple(acc_uids["s_past_due"][i]),
            s_delayed_uids=tuple(acc_uids["s_delayed"][i]),
            s_backlog_uids=tuple(acc_uids["s_backlog"][i]),
            f_bl_plan_uids=tuple(acc_uids["f_bl_plan"][i]),
            f_early_uids=tuple(acc_uids["f_early"][i]),
            f_workoff_uids=tuple(acc_uids["f_workoff"][i]),
            f_past_due_uids=tuple(acc_uids["f_past_due"][i]),
            f_delayed_uids=tuple(acc_uids["f_delayed"][i]),
            f_backlog_uids=tuple(acc_uids["f_backlog"][i]),
        )

    months = tuple(_burden_month(i, m) for i, m in enumerate(axis))
    return WorkoffBurden(
        months=months,
        status_month=_month_key(dd_month) if dd_month is not None else None,
        truncated=n == _MAX_MONTHS,
    )


# ------------------------------------------------------------- G5: duration ratio (DRM)


@dataclass(frozen=True)
class DurationRatioPoint:
    uid: int
    name: str
    baseline_days: float  # baseline duration in working days
    actual_days: float  # actual duration in working days (the completed task's duration)
    drm: float  # actual / baseline
    cum_prob: float  # rank / n over the ascending-sorted DRM population


@dataclass(frozen=True)
class HistogramBin:
    lo: float
    hi: float
    count: int


@dataclass(frozen=True)
class DurationRatioData:
    points: tuple[DurationRatioPoint, ...]  # ascending by DRM
    bins: tuple[HistogramBin, ...]  # histogram of the middle 70% of DRM values
    drm_min: float | None
    drm_avg: float | None
    drm_max: float | None
    n: int  # qualifying completed tasks
    n_excluded: int  # completed tasks without a usable baseline duration (disclosed)


def duration_ratio(schedule: Schedule) -> DurationRatioData:
    """G5 — Duration Ratio Metric per COMPLETED normal task: actual duration ÷ baseline
    duration (working time). For a complete task the schedule's stored duration IS the actual
    duration (MS Project sets Duration = ActualDuration at 100%). Tasks without a positive
    baseline duration cannot form a ratio and are counted in ``n_excluded`` — never imputed."""
    per_day = schedule.calendar.working_minutes_per_day or 480
    pts: list[tuple[int, str, float, float, float]] = []
    excluded = 0
    for t in non_summary(schedule):
        if t.is_milestone or not t.is_complete:
            continue
        bl = t.baseline_duration_minutes
        if bl is None or bl <= 0:
            excluded += 1
            continue
        drm = t.duration_minutes / bl
        pts.append((t.unique_id, t.name, bl / per_day, t.duration_minutes / per_day, drm))
    pts.sort(key=lambda p: (p[4], p[0]))
    n = len(pts)
    points = tuple(
        DurationRatioPoint(
            uid=uid,
            name=name,
            baseline_days=round(b, 2),
            actual_days=round(a, 2),
            drm=round(drm, 3),
            cum_prob=round((i + 1) / n, 4),
        )
        for i, (uid, name, b, a, drm) in enumerate(pts)
    )
    bins: tuple[HistogramBin, ...] = ()
    if n:
        drop = int(n * 0.15)
        mid = [p[4] for p in pts[drop : n - drop]] or [p[4] for p in pts]
        lo, hi = min(mid), max(mid)
        nbins = min(20, max(5, int(len(mid) ** 0.5)))
        width = (hi - lo) / nbins or 1.0
        counts = [0] * nbins
        for v in mid:
            counts[min(nbins - 1, int((v - lo) / width))] += 1
        bins = tuple(
            HistogramBin(lo=round(lo + i * width, 3), hi=round(lo + (i + 1) * width, 3), count=c)
            for i, c in enumerate(counts)
        )
    all_drm = [p[4] for p in pts]
    return DurationRatioData(
        points=points,
        bins=bins,
        drm_min=round(min(all_drm), 3) if all_drm else None,
        drm_avg=round(sum(all_drm) / n, 3) if all_drm else None,
        drm_max=round(max(all_drm), 3) if all_drm else None,
        n=n,
        n_excluded=excluded,
    )


# ------------------------------------------------------- G6/G7: to-go quad ingredients


@dataclass(frozen=True)
class ToGoSnapshot:
    """The to-go execution snapshot behind the G6/G7 portfolio quads for ONE version."""

    baselined_to_start_remaining: int  # baseline start after the data date
    scheduled_to_start_to_go: int  # not yet started
    baselined_to_finish_remaining: int  # baseline finish after the data date
    scheduled_to_finish_to_go: int  # not yet finished
    start_ratio: float | None  # to-go starts ÷ remaining baselined starts (None: nothing left)
    finish_ratio: float | None
    tm_to_go: int  # incomplete tasks & milestones
    critical_to_go: int  # of those, on the effective critical path
    critical_share: float | None  # critical_to_go / tm_to_go


def to_go_snapshot(schedule: Schedule, critical_uids: frozenset[int]) -> ToGoSnapshot:
    """G6/G7 ingredients: how the REMAINING work compares with what the baseline said should
    remain (ratios > 1 = more to-go work than planned — the bow wave), and how much of the
    to-go work is on the critical path. Undefined ratios stay ``None`` (rendered N/A)."""
    status = schedule.status_date
    tasks = non_summary(schedule)
    bl_s_rem = bl_f_rem = 0
    if status is not None:
        bl_s_rem = sum(
            1 for t in tasks if t.baseline_start is not None and t.baseline_start > status
        )
        bl_f_rem = sum(
            1 for t in tasks if t.baseline_finish is not None and t.baseline_finish > status
        )
    togo_start = sum(1 for t in tasks if t.actual_start is None)
    togo_finish = sum(1 for t in tasks if not t.is_complete)
    critical_togo = sum(1 for t in tasks if not t.is_complete and t.unique_id in critical_uids)
    return ToGoSnapshot(
        baselined_to_start_remaining=bl_s_rem,
        scheduled_to_start_to_go=togo_start,
        baselined_to_finish_remaining=bl_f_rem,
        scheduled_to_finish_to_go=togo_finish,
        start_ratio=round(togo_start / bl_s_rem, 2) if bl_s_rem else None,
        finish_ratio=round(togo_finish / bl_f_rem, 2) if bl_f_rem else None,
        tm_to_go=togo_finish,
        critical_to_go=critical_togo,
        critical_share=round(critical_togo / togo_finish, 3) if togo_finish else None,
    )
