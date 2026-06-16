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

from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class PathChange:
    """Why one activity entered or left the critical path between two versions.

    ``reason`` is a short code (see :func:`_classify_entered` / :func:`_classify_left`) the
    UI styles; ``detail`` is the plain-English explanation. The attribution reports the
    OBSERVABLE change to that activity (new / removed / duration / logic / constraint /
    completed); when nothing about the activity itself changed, entering is attributed to a
    slip elsewhere consuming its float and leaving to it gaining float — honest, not invented.
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


def _dur_wd(minutes: int, per_day: int) -> str:
    return f"{minutes / (per_day or 1):g}wd"


def _classify_entered(
    uid: int,
    cur: Schedule,
    prior: Schedule,
    cur_links: dict[int, set[tuple[int, int, str]]],
    prior_links: dict[int, set[tuple[int, int, str]]],
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
            f"Duration increased ({_dur_wd(prior_t.duration_minutes, per_day)} "
            f"→ {_dur_wd(cur_t.duration_minutes, per_day)}).",
        )
    if cur_t.has_hard_constraint and not prior_t.has_hard_constraint:
        return PathChange(
            uid, name, "constraint", f"Hard constraint added ({cur_t.constraint_type.value})."
        )
    added = cur_links.get(uid, set()) - prior_links.get(uid, set())
    if added:
        n = len(added)
        return PathChange(
            uid,
            name,
            "logic_added",
            f"{n} logic link{'s' if n != 1 else ''} added on this activity.",
        )
    return PathChange(
        uid,
        name,
        "slack_consumed",
        "Became critical as a slip elsewhere consumed its float (this activity is unchanged).",
    )


def _classify_left(
    uid: int,
    cur: Schedule,
    prior: Schedule,
    cur_links: dict[int, set[tuple[int, int, str]]],
    prior_links: dict[int, set[tuple[int, int, str]]],
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
        return PathChange(
            uid, name, "completed", "Completed since the prior version (no longer drives work)."
        )
    if prior_t is not None and cur_t.duration_minutes < prior_t.duration_minutes:
        return PathChange(
            uid,
            name,
            "duration_down",
            f"Duration shortened ({_dur_wd(prior_t.duration_minutes, per_day)} "
            f"→ {_dur_wd(cur_t.duration_minutes, per_day)}).",
        )
    removed = prior_links.get(uid, set()) - cur_links.get(uid, set())
    if removed:
        n = len(removed)
        return PathChange(
            uid,
            name,
            "logic_removed",
            f"{n} logic link{'s' if n != 1 else ''} removed from this activity.",
        )
    if prior_t is not None and prior_t.has_hard_constraint and not cur_t.has_hard_constraint:
        return PathChange(
            uid, name, "constraint", f"Hard constraint removed ({prior_t.constraint_type.value})."
        )
    return PathChange(uid, name, "gained_float", "Gained float — no longer on the longest path.")


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
            entered_changes = tuple(
                _classify_entered(uid, sch, prior_sch, cur_links, prior_links)
                for uid in sorted(entered)
            )
            left_changes = tuple(
                _classify_left(uid, sch, prior_sch, cur_links, prior_links) for uid in sorted(left)
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
            finish_delta = (finish - prior_finish_date).days if prior_finish_date else None

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
