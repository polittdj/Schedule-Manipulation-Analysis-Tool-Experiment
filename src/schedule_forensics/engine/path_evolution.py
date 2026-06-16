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
        else:
            prior_sch, prior_cpm = schedules[i - 1], cpms[i - 1]
            entered = critical - prior_critical
            left = prior_critical - critical
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
            )
        )
        prior_critical = critical
        prior_finish_date = finish

    return PathEvolution(snapshots=tuple(snapshots))
