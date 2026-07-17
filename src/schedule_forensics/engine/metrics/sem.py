"""Schedule Execution Metrics (SEM) — the Bible's "Industry Standards" execution family.

The nine remaining members of the NASA Acumen metric library group *Industry Standards /
Schedule Execution Metrics (SEM)* (``BRI Cumulative``, the tenth, lives in
:mod:`schedule_forensics.engine.metrics.fei_bri` and is reused verbatim). Every formula below is
implemented exactly as the committed ``.aft`` library states it (the formula-audit test pins the
strings), on the same conventions the already-Fuse-validated BRI uses: the **Value Task**
population (non-summary, non-milestone), ``ProjectTimeNow`` = the schedule's status date, raw
datetime comparisons, and 2-dp display rounding.

The 30-day window is ``[now - 30 calendar days, now]`` (``ProjectTimeNowMinus30Days``). Two
subtleties the Bible encodes that a summary would lose:

* **BEI Current / Cumulative count ALL actual finishes** in the window/period — the numerator is
  *not* restricted to the baselined set (so the index can exceed 1 when unbaselined work
  completes), unlike BRI whose numerator is the baselined subset. This is also why the SEM
  ``BEI Cumulative`` (actual-finish based) is a *different metric* from the DCMA-14 BEI
  (percent-complete based) — both ship, separately labeled, per the ADR-0176 dual-metric
  precedent.
* **TC-BEI**'s denominator is the baselined-to-go work *not already finished*
  (``BaselineFinish >= now`` and (``ActualFinish >= now`` or no actual)), while **Delta**'s
  to-complete term deliberately uses the *simpler* ``count(BaselineFinish >= now)`` denominator —
  Delta is therefore computed from its own formula, never as the difference of the other two
  rounded outputs.

``FRI Current`` needs each task's **PreviousFinish** — the same activity's forecast finish in the
prior loaded version (joined by UniqueID). With no prior version it reads NA, exactly as Acumen
prints N/A when the snapshot has no predecessor.

A zero denominator follows the Bible's explicit ``IF(den > 0, …, 0)`` else-arm for the *value*
(so exports match Acumen cell-for-cell) but carries ``NOT_APPLICABLE`` status so no UI presents
it as a scored result.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.engine.metrics.fei_bri import compute_bri
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: The Bible's current-period window: ProjectTimeNow minus 30 calendar days.
_WINDOW_DAYS = 30


def _value_tasks(schedule: Schedule) -> list[Task]:
    """The Acumen 'Value Tasks' population: Normal activities (non-summary, non-milestone)."""
    return [t for t in non_summary(schedule) if not t.is_milestone]


def _count(metric_id: str, name: str, count: int, population: int) -> MetricResult:
    return MetricResult(
        metric_id,
        name,
        count,
        population,
        float(count),
        "count",
        CheckStatus.NOT_APPLICABLE,
    )


def _ratio(metric_id: str, name: str, num: int, den: int) -> MetricResult:
    """The Bible's ``ROUND(IF(den > 0, num/den, 0), 2)`` shape: value 0 on an empty denominator
    (cell-for-cell Acumen parity) but never presented as a scored result (status stays NA)."""
    value = round(num / den, 2) if den > 0 else 0.0
    return MetricResult(metric_id, name, num, den, value, "ratio", CheckStatus.NOT_APPLICABLE)


def _in_window(when: dt.datetime | None, w0: dt.datetime, now: dt.datetime) -> bool:
    return when is not None and w0 <= when <= now


def compute_sem(schedule: Schedule, prior: Schedule | None = None) -> dict[str, MetricResult]:
    """All ten SEM metrics for ``schedule`` (``prior`` = the preceding loaded version, feeding
    ``FRI Current``'s PreviousFinish join; ``None`` → FRI reads NA).

    Returns Bible-ordered keys: ``sem_completed``, ``sem_workoff_burden``, ``sem_bri_current``,
    ``bri_cumulative`` (the existing Fuse-validated metric, reused), ``sem_bpi_current``,
    ``sem_bei_current``, ``sem_bei_cumulative``, ``sem_tc_bei``, ``sem_fri_current``,
    ``sem_delta``. Every metric reads NA when the schedule carries no status date.
    """
    tasks = _value_tasks(schedule)
    now = schedule.status_date
    out: dict[str, MetricResult] = {}
    if now is None:
        na = [
            ("sem_completed", "Completed Activities", "count"),
            ("sem_workoff_burden", "Workoff Burden (SEM01)", "count"),
            ("sem_bri_current", "BRI Current (SEM02)", "ratio"),
            ("sem_bpi_current", "BPI Current (SEM04)", "ratio"),
            ("sem_bei_current", "BEI Current (SEM05)", "ratio"),
            ("sem_bei_cumulative", "BEI Cumulative (SEM06)", "ratio"),
            ("sem_tc_bei", "TC-BEI (SEM07)", "ratio"),
            ("sem_fri_current", "FRI Current (SEM08)", "ratio"),
            ("sem_delta", "Delta (BEI vs TC-BEI) (SEM09)", "ratio"),
        ]
        for mid, name, unit in na:
            out[mid] = MetricResult(mid, name, 0, 0, 0.0, unit, CheckStatus.NOT_APPLICABLE)
        out["bri_cumulative"] = compute_bri(schedule)
        return _bible_order(out)
    w0 = now - dt.timedelta(days=_WINDOW_DAYS)

    af_le_now = [t for t in tasks if t.actual_finish is not None and t.actual_finish <= now]
    af_in_win = [t for t in tasks if _in_window(t.actual_finish, w0, now)]
    bf_in_win = [t for t in tasks if _in_window(t.baseline_finish, w0, now)]
    bf_le_now = [t for t in tasks if t.baseline_finish is not None and t.baseline_finish <= now]
    bf_ge_now = [t for t in tasks if t.baseline_finish is not None and t.baseline_finish >= now]

    # Completed Activities — SUM(IF((ActualFinish <= now) * ISNUMBER(ActualFinish), 1, 0))
    out["sem_completed"] = _count(
        "sem_completed", "Completed Activities", len(af_le_now), len(tasks)
    )
    # Workoff Burden — finished THIS window but baselined to finish BEFORE it (burn-down of debt)
    workoff = [t for t in af_in_win if t.baseline_finish is not None and t.baseline_finish < w0]
    out["sem_workoff_burden"] = _count(
        "sem_workoff_burden", "Workoff Burden (SEM01)", len(workoff), len(tasks)
    )
    # BRI Current — of the window's baselined finishes, how many actually finished in the window
    bri_cur_num = sum(1 for t in bf_in_win if _in_window(t.actual_finish, w0, now))
    out["sem_bri_current"] = _ratio(
        "sem_bri_current", "BRI Current (SEM02)", bri_cur_num, len(bf_in_win)
    )
    # BRI Cumulative — the existing Fuse-validated metric, verbatim
    out["bri_cumulative"] = compute_bri(schedule)
    # BPI Current — of the window's baselined finishes, how many are finished AT ALL by now
    bpi_num = sum(1 for t in bf_in_win if t.actual_finish is not None and t.actual_finish <= now)
    out["sem_bpi_current"] = _ratio(
        "sem_bpi_current", "BPI Current (SEM04)", bpi_num, len(bf_in_win)
    )
    # BEI Current — ALL actual finishes in the window over the window's baselined finishes
    out["sem_bei_current"] = _ratio(
        "sem_bei_current", "BEI Current (SEM05)", len(af_in_win), len(bf_in_win)
    )
    # BEI Cumulative — ALL actual finishes to date over the baselined-due population (the SEM
    # actual-finish twin of the DCMA %-complete BEI; both ship, separately labeled)
    out["sem_bei_cumulative"] = _ratio(
        "sem_bei_cumulative", "BEI Cumulative (SEM06)", len(af_le_now), len(bf_le_now)
    )
    # TC-BEI — forecast finishes still to go over the baselined-to-go work not already finished
    tc_den = sum(1 for t in bf_ge_now if t.actual_finish is None or t.actual_finish >= now)
    tc_num = sum(1 for t in tasks if t.finish is not None and t.finish >= now)
    if len(bf_ge_now) > 0 and tc_den > 0:
        out["sem_tc_bei"] = _ratio("sem_tc_bei", "TC-BEI (SEM07)", tc_num, tc_den)
    else:
        out["sem_tc_bei"] = MetricResult(
            "sem_tc_bei", "TC-BEI (SEM07)", tc_num, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE
        )
    # FRI Current — of the tasks the PRIOR version forecast to finish in the window, how many did
    if prior is None:
        out["sem_fri_current"] = MetricResult(
            "sem_fri_current",
            "FRI Current (SEM08)",
            0,
            0,
            0.0,
            "ratio",
            CheckStatus.NOT_APPLICABLE,
        )
    else:
        prev_finish = {t.unique_id: t.finish for t in _value_tasks(prior)}
        fri_pop = [t for t in tasks if _in_window(prev_finish.get(t.unique_id), w0, now)]
        fri_num = sum(1 for t in fri_pop if _in_window(t.actual_finish, w0, now))
        out["sem_fri_current"] = _ratio(
            "sem_fri_current", "FRI Current (SEM08)", fri_num, len(fri_pop)
        )
    # Delta — BEI Cumulative (unrounded) minus the SIMPLE to-complete term (its own formula:
    # count(Finish >= now) / count(BaselineFinish >= now) — NOT TC-BEI's not-finished denominator)
    a = len(af_le_now) / len(bf_le_now) if bf_le_now else 0.0
    b = tc_num / len(bf_ge_now) if bf_ge_now else 0.0
    out["sem_delta"] = MetricResult(
        "sem_delta",
        "Delta (BEI vs TC-BEI) (SEM09)",
        0,
        len(tasks),
        round(a - b, 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
    )
    return _bible_order(out)


_ORDER = (
    "sem_completed",
    "sem_workoff_burden",
    "sem_bri_current",
    "bri_cumulative",
    "sem_bpi_current",
    "sem_bei_current",
    "sem_bei_cumulative",
    "sem_tc_bei",
    "sem_fri_current",
    "sem_delta",
)


def _bible_order(out: dict[str, MetricResult]) -> dict[str, MetricResult]:
    return {k: out[k] for k in _ORDER if k in out}
