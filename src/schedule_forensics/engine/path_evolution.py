"""Critical-path evolution across versions — the Bow-Wave-style path animation (M18 item 7).

Steps through the loaded versions (oldest → newest by data date) and, for each, the
**critical path** (``total_float <= 0``) and how it changed from the prior version: which
activities **entered** the critical path, which **left** it, which **stayed**, and the
duration changes on the path. Alongside, the schedule-optics signals the operator asked to
surface here — **remaining-duration cuts on the critical path** and **logic removed** — reuse
the canonical manipulation detector (:func:`engine.manipulation.detect_manipulation`) so the
flags match the Compare/Trend pages exactly.

The forensic read: a critical path that keeps shedding activities while the project finish
holds steady — especially with durations cut or logic removed on the path — is a schedule
being massaged to absorb a slip rather than recover it. Everything is computed from the
loaded files; nothing is fabricated.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class PathChange:
    """Why one activity entered or left the critical path between two versions.

    ``reason`` is a short code (see :func:`_classify_entered` / :func:`_classify_left`) the
    UI styles; ``detail`` is the plain-English explanation (surfaced in the reason-chip hover).
    The attribution reports the OBSERVABLE change to that activity (new / removed / duration /
    logic / constraint / completed) — and, when nothing about the activity itself changed,
    NAMES the slip elsewhere that consumed its float (entering) or the movement that gave it
    float (leaving). Honest, not invented: every cited slip / link / delta is read from the
    loaded versions and their CPM results.
    """

    uid: int
    name: str
    reason: str
    detail: str


@dataclass(frozen=True)
class CriticalSnapshot:
    """One version's critical path and how it moved from the prior version."""

    label: str
    status_date: str | None  # the data date (ISO), if recorded
    project_finish: str  # ISO date — the network's computed finish
    finish_delta_days: int | None  # calendar-day finish move vs the prior version (+ = later)
    critical: tuple[int, ...]  # the critical-path UIDs this version (sorted)
    entered: tuple[int, ...]  # critical now, not in the prior version
    left: tuple[int, ...]  # critical in the prior version, not now
    stayed: tuple[int, ...]  # critical in both
    duration_changed: tuple[int, ...]  # currently-critical activities whose duration changed
    shortened_on_path: tuple[int, ...]  # incomplete critical activities shortened vs prior
    removed_logic_count: int  # logic links removed vs the prior version
    #: per-activity attribution for why each entered / left the path (parallel to
    #: ``entered`` / ``left`` by UID; empty for the first version — no prior to compare).
    entered_changes: tuple[PathChange, ...] = ()
    left_changes: tuple[PathChange, ...] = ()


@dataclass(frozen=True)
class PathEvolution:
    """The whole workbook's critical-path evolution: per-version snapshots, oldest first."""

    snapshots: tuple[CriticalSnapshot, ...]


def _finding_uids(findings: Sequence[object], metric_id: str) -> set[int]:
    """Offender UIDs of the (first) finding with ``metric_id`` — empty if none."""
    for f in findings:
        if getattr(f, "metric_id", None) == metric_id:
            return {c.unique_id for c in f.citations}  # type: ignore[attr-defined]
    return set()


def _finding_count(findings: Sequence[object], metric_id: str) -> int:
    return len(_finding_uids(findings, metric_id))


def _links_touching(schedule: Schedule) -> dict[int, set[tuple[int, int, str]]]:
    """UID → the set of logic links (pred, succ, type) it participates in. Comparing this
    set across versions reveals links added to / removed from a specific activity."""
    out: dict[int, set[tuple[int, int, str]]] = {}
    for r in schedule.relationships:
        sig = (r.predecessor_id, r.successor_id, r.type.value)
        out.setdefault(r.predecessor_id, set()).add(sig)
        out.setdefault(r.successor_id, set()).add(sig)
    return out


def _early_finish_dates(schedule: Schedule, cpm: CPMResult) -> dict[int, dt.date]:
    """Each task's CPM early-finish as a calendar date — the basis for the cross-version slip."""
    return {
        uid: offset_to_datetime(schedule.project_start, t.early_finish, schedule.calendar).date()
        for uid, t in cpm.timings.items()
    }


def _predecessors(schedule: Schedule) -> dict[int, tuple[int, ...]]:
    """successor UID → its direct predecessor UIDs (for walking a driving chain backward)."""
    out: dict[int, list[int]] = {}
    for r in schedule.relationships:
        out.setdefault(r.successor_id, []).append(r.predecessor_id)
    return {k: tuple(v) for k, v in out.items()}


@dataclass(frozen=True)
class _PairContext:
    """Cross-version movement context for the reason classifiers, so ``slack_consumed`` /
    ``gained_float`` can name the slip elsewhere instead of stopping at "a slip elsewhere".

    All fields derive from the two versions' CPM results (never fabricated): ``slip_days`` is
    each activity's early-finish movement in calendar days (current minus prior, + = later);
    ``cur_preds`` maps successor → its direct predecessors in the current version (to walk an
    activity's driving chain); ``finish_delta_days`` is the project-finish move.
    """

    slip_days: dict[int, int]
    cur_preds: dict[int, tuple[int, ...]]
    finish_delta_days: int | None


def _name_in(schedule: Schedule, uid: int) -> str:
    task = schedule.tasks_by_id.get(uid)
    return task.name if task is not None else f"UID {uid}"


def _dur_change_detail(prior_min: int, cur_min: int, per_day: int, *, increased: bool) -> str:
    """A quantified duration change: signed working-day delta, ``from → to``, and percent."""
    pd = per_day or 1
    before, after = prior_min / pd, cur_min / pd
    delta = after - before
    pct = f", {delta / before * 100:+.0f}%" if before else ""
    verb = "increased" if increased else "shortened"
    return f"Duration {verb} {delta:+g}wd ({before:g}wd → {after:g}wd{pct})."


def _describe_link(uid: int, link: tuple[int, int, str], schedule: Schedule) -> str:
    """One logic link described relative to ``uid``: a predecessor (``←``) or successor (``→``)
    edge naming the other endpoint (name + UID + link type), resolved from ``schedule``."""
    pred, succ, link_type = link
    other = succ if pred == uid else pred
    arrow = "→" if pred == uid else "←"
    return f"{arrow} {_name_in(schedule, other)} (UID {other}, {link_type})"


def _links_detail(uid: int, links: set[tuple[int, int, str]], schedule: Schedule, verb: str) -> str:
    """Cite the specific links added to / removed from ``uid`` (up to three, then ``+N more``)."""
    ordered = sorted(links)
    shown = [_describe_link(uid, link, schedule) for link in ordered[:3]]
    more = len(ordered) - len(shown)
    tail = f" (+{more} more)" if more > 0 else ""
    plural = "s" if len(ordered) != 1 else ""
    return f"{len(ordered)} logic link{plural} {verb}: " + "; ".join(shown) + tail + "."


def _driving_slip(
    uid: int, preds: dict[int, tuple[int, ...]], slip_days: dict[int, int]
) -> tuple[int, int] | None:
    """The transitive predecessor of ``uid`` with the largest positive early-finish slip, as
    ``(slip_days, predecessor_uid)`` — the upstream activity whose slippage most plausibly
    consumed ``uid``'s float. ``None`` when no predecessor finished later."""
    seen: set[int] = set()
    stack = [uid]
    best: tuple[int, int] | None = None
    while stack:
        for p in preds.get(stack.pop(), ()):
            if p in seen:
                continue
            seen.add(p)
            stack.append(p)
            slip = slip_days.get(p, 0)
            if slip > 0 and (best is None or slip > best[0]):
                best = (slip, p)
    return best


def _largest_slip(slip_days: dict[int, int], exclude: int) -> tuple[int, int] | None:
    """The activity (other than ``exclude``) with the largest positive early-finish slip."""
    best: tuple[int, int] | None = None
    for u, slip in slip_days.items():
        if u == exclude or slip <= 0:
            continue
        if best is None or slip > best[0]:
            best = (slip, u)
    return best


def _classify_entered(
    uid: int,
    cur: Schedule,
    prior: Schedule,
    cur_links: dict[int, set[tuple[int, int, str]]],
    prior_links: dict[int, set[tuple[int, int, str]]],
    ctx: _PairContext | None = None,
) -> PathChange:
    """Why ``uid`` is on the critical path now but was not in the prior version."""
    cur_t = cur.tasks_by_id.get(uid)
    name = cur_t.name if cur_t is not None else f"UID {uid}"
    per_day = cur.calendar.working_minutes_per_day
    prior_t = prior.tasks_by_id.get(uid)
    if prior_t is None or cur_t is None:
        return PathChange(uid, name, "new", "New activity added to the schedule.")
    if cur_t.duration_minutes > prior_t.duration_minutes:
        return PathChange(
            uid,
            name,
            "duration_up",
            _dur_change_detail(
                prior_t.duration_minutes, cur_t.duration_minutes, per_day, increased=True
            ),
        )
    if cur_t.has_hard_constraint and not prior_t.has_hard_constraint:
        return PathChange(
            uid, name, "constraint", f"Hard constraint added ({cur_t.constraint_type.value})."
        )
    added = cur_links.get(uid, set()) - prior_links.get(uid, set())
    if added:
        return PathChange(uid, name, "logic_added", _links_detail(uid, added, cur, "added"))
    # The activity itself is unchanged — it became critical because float was consumed by a slip
    # elsewhere. Name that slip (its driving chain first, then the largest slip anywhere) so the
    # reason points at a specific activity rather than a vague "elsewhere".
    detail = "Became critical as a slip elsewhere consumed its float (this activity is unchanged)."
    if ctx is not None:
        upstream = _driving_slip(uid, ctx.cur_preds, ctx.slip_days)
        if upstream is not None:
            slip, p = upstream
            detail = (
                f"Unchanged here — became critical when upstream '{_name_in(cur, p)}' "
                f"(UID {p}) finished {slip}d later, consuming this activity's float."
            )
        else:
            other = _largest_slip(ctx.slip_days, exclude=uid)
            if other is not None:
                slip, p = other
                detail = (
                    f"Unchanged here — float consumed by slippage elsewhere "
                    f"(largest: '{_name_in(cur, p)}' UID {p}, +{slip}d)."
                )
    return PathChange(uid, name, "slack_consumed", detail)


def _classify_left(
    uid: int,
    cur: Schedule,
    prior: Schedule,
    cur_links: dict[int, set[tuple[int, int, str]]],
    prior_links: dict[int, set[tuple[int, int, str]]],
    ctx: _PairContext | None = None,
) -> PathChange:
    """Why ``uid`` was on the critical path in the prior version but is not now."""
    prior_t = prior.tasks_by_id.get(uid)
    cur_t = cur.tasks_by_id.get(uid)
    ref = cur_t if cur_t is not None else prior_t
    name = ref.name if ref is not None else f"UID {uid}"
    per_day = cur.calendar.working_minutes_per_day
    if cur_t is None:
        return PathChange(uid, name, "removed", "Activity removed from the schedule.")
    if cur_t.is_complete and not (prior_t is not None and prior_t.is_complete):
        pct = round(cur_t.percent_complete)
        finished = (
            f", finished {cur_t.actual_finish.date().isoformat()}"
            if cur_t.actual_finish is not None
            else ""
        )
        return PathChange(
            uid,
            name,
            "completed",
            f"Completed since the prior version ({pct}%{finished}) — no longer drives work.",
        )
    if prior_t is not None and cur_t.duration_minutes < prior_t.duration_minutes:
        return PathChange(
            uid,
            name,
            "duration_down",
            _dur_change_detail(
                prior_t.duration_minutes, cur_t.duration_minutes, per_day, increased=False
            ),
        )
    removed = prior_links.get(uid, set()) - cur_links.get(uid, set())
    if removed:
        return PathChange(uid, name, "logic_removed", _links_detail(uid, removed, prior, "removed"))
    if prior_t is not None and prior_t.has_hard_constraint and not cur_t.has_hard_constraint:
        return PathChange(
            uid, name, "constraint", f"Hard constraint removed ({prior_t.constraint_type.value})."
        )
    # Unchanged but no longer on the longest path — quantify the float-relevant movement (its own
    # forecast-finish move vs the project finish) instead of a bare "gained float".
    detail = "Gained float — no longer on the longest path."
    if ctx is not None:
        own = ctx.slip_days.get(uid)
        fd = ctx.finish_delta_days
        if own is not None and fd is not None:
            detail = (
                f"Unchanged here — off the longest path now (its forecast finish moved "
                f"{own:+d}d while the project finish moved {fd:+d}d)."
            )
        elif own is not None:
            detail = (
                f"Unchanged here — off the longest path now (its forecast finish moved {own:+d}d)."
            )
    return PathChange(uid, name, "gained_float", detail)


def compute_path_evolution(
    schedules: Sequence[Schedule], cpms: Sequence[CPMResult]
) -> PathEvolution:
    """Per-version critical-path snapshots for ``schedules`` (given oldest → newest).

    ``cpms`` is parallel to ``schedules`` (the caller's cached results). Requires at least
    one version; the first has no prior, so its change fields are empty."""
    if not schedules:
        raise ValueError("the path-evolution analysis needs at least one schedule version")
    if len(cpms) != len(schedules):
        raise ValueError("cpms must parallel schedules")

    snapshots: list[CriticalSnapshot] = []
    prior_critical: set[int] = set()
    prior_finish_date = None
    for i, (sch, cpm) in enumerate(zip(schedules, cpms, strict=True)):
        critical = set(cpm.critical_path)
        finish = offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar).date()

        if i == 0:
            entered: set[int] = set()
            left: set[int] = set()
            duration_changed: tuple[int, ...] = ()
            shortened_on_path: tuple[int, ...] = ()
            removed_logic = 0
            finish_delta: int | None = None
            entered_changes: tuple[PathChange, ...] = ()
            left_changes: tuple[PathChange, ...] = ()
        else:
            prior_sch, prior_cpm = schedules[i - 1], cpms[i - 1]
            entered = critical - prior_critical
            left = prior_critical - critical
            cur_links = _links_touching(sch)
            prior_links = _links_touching(prior_sch)
            finish_delta = (finish - prior_finish_date).days if prior_finish_date else None
            cur_ef = _early_finish_dates(sch, cpm)
            prior_ef = _early_finish_dates(prior_sch, prior_cpm)
            ctx = _PairContext(
                slip_days={
                    uid: (cur_ef[uid] - prior_ef[uid]).days
                    for uid in cur_ef.keys() & prior_ef.keys()
                },
                cur_preds=_predecessors(sch),
                finish_delta_days=finish_delta,
            )
            entered_changes = tuple(
                _classify_entered(uid, sch, prior_sch, cur_links, prior_links, ctx)
                for uid in sorted(entered)
            )
            left_changes = tuple(
                _classify_left(uid, sch, prior_sch, cur_links, prior_links, ctx)
                for uid in sorted(left)
            )
            prior_dur = {t.unique_id: t.duration_minutes for t in prior_sch.tasks}
            duration_changed = tuple(
                sorted(
                    t.unique_id
                    for t in sch.tasks
                    if t.unique_id in critical
                    and t.unique_id in prior_dur
                    and t.duration_minutes != prior_dur[t.unique_id]
                )
            )
            signals = detect_manipulation(sch, prior_sch, current_cpm=cpm, prior_cpm=prior_cpm)
            shortened_on_path = tuple(
                sorted(_finding_uids(signals, "MANIP_SHORTENED_DURATION") & critical)
            )
            removed_logic = _finding_count(signals, "MANIP_DELETED_LOGIC")

        snapshots.append(
            CriticalSnapshot(
                label=sch.source_file or sch.name,
                status_date=sch.status_date.date().isoformat() if sch.status_date else None,
                project_finish=finish.isoformat(),
                finish_delta_days=finish_delta,
                critical=tuple(sorted(critical)),
                entered=tuple(sorted(entered)),
                left=tuple(sorted(left)),
                stayed=tuple(sorted(critical & prior_critical)) if i else (),
                duration_changed=duration_changed,
                shortened_on_path=shortened_on_path,
                removed_logic_count=removed_logic,
                entered_changes=entered_changes,
                left_changes=left_changes,
            )
        )
        prior_critical = critical
        prior_finish_date = finish

    return PathEvolution(snapshots=tuple(snapshots))
