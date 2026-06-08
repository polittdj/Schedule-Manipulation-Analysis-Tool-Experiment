"""UniqueID-keyed version diff — the structural delta between two schedule snapshots (M11).

`diff_versions(prior, current)` reports, **by UniqueID only** (§6.B — never row id, never
name): added / deleted activities, per-task field-level deltas (durations, baseline/actual/
forecast dates, % complete, constraint), and added / removed **logic** (relationships). It
is the deterministic substrate the manipulation-trend detector (:mod:`.manipulation`) and
the version-comparison views read; it states *what changed*, not *why* (intent is the
detector's job, with citations).
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.model.relationship import RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: The task fields the diff tracks (attribute name → human label for display/citations).
_TRACKED_FIELDS: tuple[tuple[str, str], ...] = (
    ("duration_minutes", "Duration"),
    ("remaining_duration_minutes", "Remaining Duration"),
    ("baseline_duration_minutes", "Baseline Duration"),
    ("baseline_start", "Baseline Start"),
    ("baseline_finish", "Baseline Finish"),
    ("actual_start", "Actual Start"),
    ("actual_finish", "Actual Finish"),
    ("start", "Forecast Start"),
    ("finish", "Forecast Finish"),
    ("percent_complete", "% Complete"),
    ("constraint_type", "Constraint Type"),
    ("constraint_date", "Constraint Date"),
)

#: A logic link identity for set diffing: (predecessor, successor, type, lag_minutes).
LinkKey = tuple[int, int, RelationshipType, int]


@dataclass(frozen=True)
class FieldDelta:
    """One changed task field: the attribute, its label, and before/after values."""

    field: str
    label: str
    before: object
    after: object


@dataclass(frozen=True)
class TaskDiff:
    """All field-level changes for one activity present in both versions (keyed by UID)."""

    unique_id: int
    name: str
    deltas: tuple[FieldDelta, ...]

    def changed(self, field: str) -> FieldDelta | None:
        """Return the delta for ``field`` if it changed, else ``None``."""
        return next((d for d in self.deltas if d.field == field), None)


@dataclass(frozen=True)
class VersionDiff:
    """The full prior→current delta, matched by UniqueID."""

    prior_file: str | None
    current_file: str | None
    added_tasks: tuple[int, ...]  # in current, not prior
    deleted_tasks: tuple[int, ...]  # in prior, not current
    changed_tasks: tuple[TaskDiff, ...]  # present in both, with >=1 field delta
    added_links: tuple[LinkKey, ...]  # logic in current, not prior
    removed_links: tuple[LinkKey, ...]  # logic in prior, not current (deleted logic)

    def task_diff(self, unique_id: int) -> TaskDiff | None:
        return next((t for t in self.changed_tasks if t.unique_id == unique_id), None)


def _links(schedule: Schedule) -> set[LinkKey]:
    real = {t.unique_id for t in schedule.tasks if not t.is_summary}
    return {
        (r.predecessor_id, r.successor_id, r.type, r.lag_minutes)
        for r in schedule.relationships
        if r.predecessor_id in real and r.successor_id in real
    }


def _task_deltas(prior: Task, current: Task) -> tuple[FieldDelta, ...]:
    out: list[FieldDelta] = []
    for field, label in _TRACKED_FIELDS:
        before = getattr(prior, field)
        after = getattr(current, field)
        if before != after:
            out.append(FieldDelta(field=field, label=label, before=before, after=after))
    return tuple(out)


def diff_versions(prior: Schedule, current: Schedule) -> VersionDiff:
    """Compute the UniqueID-keyed structural diff from ``prior`` to ``current``.

    Summary activities are excluded (they are roll-ups); matching is by UniqueID only.
    """
    prior_by_id = {t.unique_id: t for t in prior.tasks if not t.is_summary}
    cur_by_id = {t.unique_id: t for t in current.tasks if not t.is_summary}
    added = tuple(sorted(set(cur_by_id) - set(prior_by_id)))
    deleted = tuple(sorted(set(prior_by_id) - set(cur_by_id)))

    changed: list[TaskDiff] = []
    for uid in sorted(set(prior_by_id) & set(cur_by_id)):
        deltas = _task_deltas(prior_by_id[uid], cur_by_id[uid])
        if deltas:
            changed.append(TaskDiff(unique_id=uid, name=cur_by_id[uid].name, deltas=deltas))

    prior_links, cur_links = _links(prior), _links(current)
    return VersionDiff(
        prior_file=prior.source_file,
        current_file=current.source_file,
        added_tasks=added,
        deleted_tasks=deleted,
        changed_tasks=tuple(changed),
        added_links=tuple(sorted(cur_links - prior_links)),
        removed_links=tuple(sorted(prior_links - cur_links)),
    )
