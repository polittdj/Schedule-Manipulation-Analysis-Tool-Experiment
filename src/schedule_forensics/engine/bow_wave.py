"""Bow-wave / CEI analysis — monthly finish profiles across snapshots (§6.D).

Models the "Activity Finishes — As of <month>" bow-wave chart: for every loaded snapshot,
each calendar month carries three counts over the non-summary activities —

* **baselined** — activities whose *baseline* finish falls in the month;
* **scheduled** — activities whose current (forecast or actual) finish falls in the month;
* **finished** — activities whose *actual* finish falls in the month.

Work that keeps sliding right shows as a swelling "bow wave" of scheduled bars just past
each snapshot's status date. The **Current Execution Index (CEI)** quantifies it per
snapshot pair: of the activities the *prior* snapshot **forecast** (its current finish) to
land in the following month, how many of THOSE actually finished by the end of it —

    CEI(k) = finished_by_end_of_P(planned set, snapshot k) / planned_for_P(snapshot k-1)

where ``P`` is the calendar month after snapshot ``k-1``'s status date and the *planned set*
is the activities the prior snapshot forecast to finish in ``P``. The view also reports what
snapshot ``k`` *re-scheduled* for ``P`` (the push-to-the-right evidence).

This **bow-wave CEI is forecast-anchored and pairwise** — distinct from the single-schedule
EVM ``cei_finish`` (:mod:`.metrics.evm`), which is the *baseline*-anchored ratio of
completed-on-time to baseline-due-by-status activities (= Baseline Finish Compliance). Both
are "execution indices" but answer different questions (did this month's forecast hold? vs
did the baseline hold?) and must not be conflated — see ADR-0052.

Every count is computed from the loaded files on the spot — nothing is fabricated. All
snapshots share one month axis so the per-snapshot charts animate cleanly.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.month_axis import bucket as _bucket
from schedule_forensics.engine.month_axis import month_index as _ym
from schedule_forensics.engine.month_axis import month_label as _label
from schedule_forensics.model.schedule import Schedule

#: Month-axis bounds relative to the snapshots' status dates (the reference deck spans
#: roughly -14/+7 months around each status date; the union across snapshots is used).
_MONTHS_BEFORE_FIRST_STATUS = 18
_MONTHS_AFTER_LAST_STATUS = 12
#: Hard cap on the axis length so a stray far-future date cannot explode the chart. When
#: over the cap, the oldest months are shed first — the newest status month and its CEI
#: period always stay on-axis.
_MAX_MONTHS = 48


@dataclass(frozen=True)
class SnapshotProfile:
    """One snapshot's monthly finish profile over the shared month axis."""

    label: str  # the version label (source file or name)
    status_index: int | None  # index of the data-date month on the shared axis (None = off-axis)
    baselined: tuple[int, ...]  # per month: baseline finishes
    scheduled: tuple[int, ...]  # per month: current forecast/actual finishes
    finished: tuple[int, ...]  # per month: actual finishes
    cei: float | None  # finished/planned for the follow-on month (None for the first snapshot)
    cei_period: str | None  # the month CEI measures (label)
    cei_planned: int | None  # prior snapshot's plan for that month
    cei_scheduled: int | None  # this snapshot's (re-)schedule for that month
    cei_finished: int | None  # actually finished in that month per this snapshot
    # item F: where a focused target activity lands on this snapshot's shared axis (None = no
    # target, target absent this snapshot, or its finish is off-axis) — the chart marks the month.
    target_scheduled_index: int | None = None  # month index of the target's current finish
    target_finished_index: int | None = None  # month index of the target's actual finish


@dataclass(frozen=True)
class BowWave:
    """The whole workbook's bow-wave dataset: one shared month axis + per-snapshot profiles."""

    month_labels: tuple[str, ...]
    snapshots: tuple[SnapshotProfile, ...]


def compute_bow_wave(schedules: Sequence[Schedule], target_uid: int | None = None) -> BowWave:
    """Monthly finish profiles + CEI for ``schedules`` (given oldest → newest).

    Requires at least one schedule. The month axis is shared across snapshots (clamped to
    the data span and to ±18/12 months around the status dates, max 48 buckets — when over
    the cap the oldest months are shed first, never the newest status month).

    ``target_uid`` (item F) focuses one activity: each snapshot reports the month index of
    that activity's current (scheduled) finish and actual finish on the shared axis, so the
    chart can mark where the target lands and how it slides across snapshots. ``None`` (or an
    off-axis / absent target) leaves the indices ``None`` — purely additive, no metric change.
    """
    if not schedules:
        raise ValueError("the bow-wave analysis needs at least one schedule version")

    per_snapshot: list[tuple[list[dt.datetime], list[dt.datetime], list[dt.datetime]]] = []
    sched_ym_by_uid: list[dict[int, int]] = []  # per snapshot: UID -> scheduled-finish month
    fin_ym_by_uid: list[dict[int, int]] = []  # per snapshot: UID -> actual-finish month
    data_months: list[int] = []
    status_yms: list[int | None] = []
    for sch in schedules:
        tasks = non_summary(sch)
        baselined = [t.baseline_finish for t in tasks if t.baseline_finish is not None]
        scheduled = [t.finish for t in tasks if t.finish is not None]
        finished = [t.actual_finish for t in tasks if t.actual_finish is not None]
        per_snapshot.append((baselined, scheduled, finished))
        sched_ym_by_uid.append({t.unique_id: _ym(t.finish) for t in tasks if t.finish is not None})
        fin_ym_by_uid.append(
            {t.unique_id: _ym(t.actual_finish) for t in tasks if t.actual_finish is not None}
        )
        data_months.extend(_ym(d) for d in (*baselined, *scheduled, *finished))
        status_yms.append(_ym(sch.status_date) if sch.status_date is not None else None)

    if not data_months:
        raise ValueError("no finish dates found in any loaded version (nothing to profile)")
    statuses = [s for s in status_yms if s is not None]
    # the axis contains every status month and its CEI period (status+1); data months are
    # clamped to a window around the statuses so an outlier date can't explode the chart
    lo, hi = min(data_months), max(data_months)
    if statuses:
        lo = min(max(lo, min(statuses) - _MONTHS_BEFORE_FIRST_STATUS), min(statuses))
        hi = max(min(hi, max(statuses) + _MONTHS_AFTER_LAST_STATUS), max(statuses) + 1)
    over = hi - lo + 1 - _MAX_MONTHS
    if over > 0:
        # Over the cap: shed the oldest history first, then surplus look-ahead, then the
        # oldest status months — never the newest status month or its CEI period (the
        # animation's "now"). Shed status months degrade gracefully (status_index/CEI None).
        lo = min(lo + over, min(statuses)) if statuses else lo + over
        over = hi - lo + 1 - _MAX_MONTHS
        if over > 0:
            hi = max(hi - over, max(statuses) + 1)
            lo = max(lo, hi - _MAX_MONTHS + 1)
    n = hi - lo + 1

    profiles: list[SnapshotProfile] = []
    for k, sch in enumerate(schedules):
        baselined, scheduled, finished = per_snapshot[k]
        b, s, f = (_bucket(d, lo, n) for d in (baselined, scheduled, finished))
        cei: float | None = None
        cei_period: str | None = None
        planned: int | None = None
        resched: int | None = None
        done: int | None = None
        prior_status = status_yms[k - 1] if k > 0 else None
        if prior_status is not None:
            period = prior_status + 1  # the month after the prior snapshot's data date
            if lo <= period <= hi:
                i = period - lo
                # Bow-wave CEI: of the activities the PRIOR snapshot *forecast* to finish
                # in the period (its current finish lands in P), count those whose actual
                # finish lands by the END of that period — an unplanned finish in the month
                # earns no credit, an early finish of a planned one does. Forecast-anchored
                # and pairwise; distinct from the baseline-anchored EVM cei_finish (ADR-0052).
                planned_uids = {uid for uid, ym in sched_ym_by_uid[k - 1].items() if ym == period}
                planned = len(planned_uids)
                resched = s[i]
                done = sum(
                    1
                    for uid in planned_uids
                    if fin_ym_by_uid[k].get(uid) is not None and fin_ym_by_uid[k][uid] <= period
                )
                cei_period = _label(period)
                cei = round(done / planned, 2) if planned else None
        status = status_yms[k]
        # item F: locate the focused target activity on this snapshot's axis (its scheduled and
        # actual finish months), reusing the per-snapshot UID→month maps already built above.
        tgt_sched = tgt_fin = None
        if target_uid is not None:
            sym = sched_ym_by_uid[k].get(target_uid)
            if sym is not None and lo <= sym <= hi:
                tgt_sched = sym - lo
            fym = fin_ym_by_uid[k].get(target_uid)
            if fym is not None and lo <= fym <= hi:
                tgt_fin = fym - lo
        profiles.append(
            SnapshotProfile(
                label=sch.source_file or sch.name,
                status_index=(status - lo) if status is not None and lo <= status <= hi else None,
                baselined=b,
                scheduled=s,
                finished=f,
                cei=cei,
                cei_period=cei_period,
                cei_planned=planned,
                cei_scheduled=resched,
                cei_finished=done,
                target_scheduled_index=tgt_sched,
                target_finished_index=tgt_fin,
            )
        )
    return BowWave(
        month_labels=tuple(_label(m) for m in range(lo, hi + 1)),
        snapshots=tuple(profiles),
    )
