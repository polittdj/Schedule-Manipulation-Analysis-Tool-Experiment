"""Critical-path counterfactual — the finish if work cut from the path were restored.

Between two consecutive versions some activities **leave** the critical (driving) path. Some
leave honestly: they **completed**, or a slip elsewhere gave them float ("gained float" — the
activity itself is unchanged, it is simply no longer on the longest chain). Others leave because
the activity itself was **changed** — its remaining duration was cut, a predecessor/successor
link was removed, or a hard constraint was dropped — which can make a slipping finish *look*
recovered.

This module isolates the activities that left the path **without completing** and whose own
**duration / logic / constraints changed**, reverts exactly those changes to their prior-version
values, re-runs CPM, and reports what the project finish (and an optional target activity's
finish) **would have been**. The gap between that counterfactual finish and the real one is the
schedule time the *changes* — not real progress — removed from the path.

Everything is computed from the two loaded versions; nothing is fabricated. Completed activities
are excluded by construction (you cannot "un-complete" delivered work).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from schedule_forensics.engine.cpm import CPMError, CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.path_evolution import effective_critical_set
from schedule_forensics.model.schedule import Schedule

#: A logic link as it touches one activity: (predecessor, successor, type, lag) — comparable
#: across versions to detect a link added to or removed from that activity.
_Link = tuple[int, int, str, int]


def _links_touching(schedule: Schedule, uid: int) -> set[_Link]:
    return {
        (r.predecessor_id, r.successor_id, r.type.value, r.lag_minutes)
        for r in schedule.relationships
        if r.predecessor_id == uid or r.successor_id == uid
    }


@dataclass(frozen=True)
class RevertedActivity:
    """One activity that left the critical path without completing, and the change reverted."""

    uid: int
    name: str
    reason: str  # short code: duration_cut / logic_removed / constraint_removed / changed
    changes: tuple[str, ...]  # plain-English description of exactly what was reverted


@dataclass(frozen=True)
class GainedFloatActivity:
    """An activity that left the path while UNCHANGED — float freed up elsewhere, not a change
    to this activity (so there is nothing to revert; reported for transparency)."""

    uid: int
    name: str


@dataclass(frozen=True)
class PathCounterfactual:
    """What the finish would be if the path-shedding changes were undone (latest version pair)."""

    prior_label: str
    current_label: str
    reverted: tuple[RevertedActivity, ...]
    gained_float: tuple[GainedFloatActivity, ...]
    actual_finish: str  # the current version's real computed finish (ISO date)
    counterfactual_finish: str  # the finish with the reverts applied (ISO date)
    finish_delta_days: int  # counterfactual minus actual; > 0 means the changes pulled finish IN
    target_uid: int | None = None
    target_name: str | None = None
    target_actual_finish: str | None = None
    target_counterfactual_finish: str | None = None
    target_delta_days: int | None = None
    #: candidates existed but re-running CPM with the reverts failed (e.g. a cycle) — the panel
    #: degrades to naming the activities without a counterfactual finish.
    uncomputable: bool = field(default=False)


def _wd(minutes: int, per_day: int) -> str:
    return f"{minutes / (per_day or 1):g}wd"


def compute_path_counterfactual(
    prior: Schedule,
    current: Schedule,
    prior_cpm: CPMResult,
    current_cpm: CPMResult,
    *,
    target_uid: int | None = None,
) -> PathCounterfactual | None:
    """The counterfactual for the ``prior`` → ``current`` pair, or ``None`` when no
    non-completed, self-changed activity left the critical path (nothing to revert)."""
    # progress-aware effective basis (ADR-0150): the stored Critical flag first — the pure
    # CPM set collapses to the tail of a progressed file, hiding the very reverts this
    # counterfactual exists to expose
    left = effective_critical_set(prior, prior_cpm) - effective_critical_set(current, current_cpm)
    cur_by = current.tasks_by_id
    prior_by = prior.tasks_by_id
    per_day = current.calendar.working_minutes_per_day

    reverted: list[RevertedActivity] = []
    gained_float: list[GainedFloatActivity] = []
    revert_uids: set[int] = set()
    task_updates: dict[int, dict[str, object]] = {}

    for uid in sorted(left):
        cur_t = cur_by.get(uid)
        prior_t = prior_by.get(uid)
        if cur_t is None or prior_t is None:
            continue  # removed from the schedule entirely — not a "changed" activity
        if cur_t.is_complete:
            continue  # excluded by construction — completed work is not reverted
        dur_changed = cur_t.duration_minutes != prior_t.duration_minutes
        con_changed = (cur_t.constraint_type, cur_t.constraint_date) != (
            prior_t.constraint_type,
            prior_t.constraint_date,
        )
        cur_links = _links_touching(current, uid)
        prior_links = _links_touching(prior, uid)
        logic_changed = cur_links != prior_links
        if not (dur_changed or con_changed or logic_changed):
            gained_float.append(GainedFloatActivity(uid, cur_t.name))
            continue

        changes: list[str] = []
        update: dict[str, object] = {}
        reason = "changed"
        if dur_changed:
            update["duration_minutes"] = prior_t.duration_minutes
            verb = "cut" if cur_t.duration_minutes < prior_t.duration_minutes else "raised"
            changes.append(
                f"duration {verb} {_wd(cur_t.duration_minutes, per_day)} "
                f"→ restored {_wd(prior_t.duration_minutes, per_day)}"
            )
            if cur_t.duration_minutes < prior_t.duration_minutes:
                reason = "duration_cut"
        if con_changed:
            update["constraint_type"] = prior_t.constraint_type
            update["constraint_date"] = prior_t.constraint_date
            changes.append(
                f"constraint {cur_t.constraint_type.value}→{prior_t.constraint_type.value} restored"
            )
            if reason == "changed":
                reason = "constraint_removed"
        if logic_changed:
            removed = prior_links - cur_links  # links present before, gone now → restore
            added = cur_links - prior_links  # links added now → drop
            parts = []
            if removed:
                parts.append(f"{len(removed)} link(s) restored")
            if added:
                parts.append(f"{len(added)} link(s) removed")
            changes.append("logic " + " & ".join(parts))
            if reason == "changed" and removed:
                reason = "logic_removed"
        if update:
            task_updates[uid] = update
        revert_uids.add(uid)
        reverted.append(RevertedActivity(uid, cur_t.name, reason, tuple(changes)))

    if not reverted and not gained_float:
        return None  # nothing left the path among present, non-completed activities

    actual_finish = offset_to_datetime(
        current.project_start, current_cpm.project_finish, current.calendar
    ).date()
    target_name = (
        cur_by[target_uid].name if target_uid is not None and target_uid in cur_by else None
    )

    if not reverted:
        # only "gained float" (unchanged) leavers — nothing to revert; report + explain them.
        return PathCounterfactual(
            prior_label=prior.source_file or prior.name,
            current_label=current.source_file or current.name,
            reverted=(),
            gained_float=tuple(gained_float),
            actual_finish=actual_finish.isoformat(),
            counterfactual_finish=actual_finish.isoformat(),
            finish_delta_days=0,
            target_uid=target_uid,
            target_name=target_name,
        )

    # Build the counterfactual schedule: revert the candidates' task fields, and revert the logic
    # links that touch any candidate to their prior-version state (endpoints must still exist).
    new_tasks = tuple(
        t.model_copy(update=task_updates[t.unique_id]) if t.unique_id in task_updates else t
        for t in current.tasks
    )
    cur_ids = {t.unique_id for t in current.tasks}

    def touches(pred: int, succ: int) -> bool:
        return pred in revert_uids or succ in revert_uids

    kept = [r for r in current.relationships if not touches(r.predecessor_id, r.successor_id)]
    restored = [
        r
        for r in prior.relationships
        if touches(r.predecessor_id, r.successor_id)
        and r.predecessor_id in cur_ids
        and r.successor_id in cur_ids
    ]
    seen: set[tuple[int, int, str, int]] = set()
    rels = []
    for r in [*kept, *restored]:
        key = (r.predecessor_id, r.successor_id, r.type.value, r.lag_minutes)
        if key in seen:
            continue
        seen.add(key)
        rels.append(r)

    try:
        cf = current.model_copy(update={"tasks": new_tasks, "relationships": tuple(rels)})
        cf_cpm = compute_cpm(cf)
    except (CPMError, ValueError):
        # the reverted logic produced an unsolvable network (e.g. a cycle) — name the activities
        # but do not claim a counterfactual finish.
        return PathCounterfactual(
            prior_label=prior.source_file or prior.name,
            current_label=current.source_file or current.name,
            reverted=tuple(reverted),
            gained_float=tuple(gained_float),
            actual_finish=actual_finish.isoformat(),
            counterfactual_finish=actual_finish.isoformat(),
            finish_delta_days=0,
            target_uid=target_uid,
            target_name=target_name,
            uncomputable=True,
        )

    cf_finish = offset_to_datetime(cf.project_start, cf_cpm.project_finish, cf.calendar).date()

    t_actual = t_cf = t_delta = None
    if (
        target_uid is not None
        and target_uid in current_cpm.timings
        and target_uid in cf_cpm.timings
    ):
        ta = offset_to_datetime(
            current.project_start, current_cpm.timings[target_uid].early_finish, current.calendar
        ).date()
        tc = offset_to_datetime(
            cf.project_start, cf_cpm.timings[target_uid].early_finish, cf.calendar
        ).date()
        t_actual, t_cf, t_delta = ta.isoformat(), tc.isoformat(), (tc - ta).days

    return PathCounterfactual(
        prior_label=prior.source_file or prior.name,
        current_label=current.source_file or current.name,
        reverted=tuple(reverted),
        gained_float=tuple(gained_float),
        actual_finish=actual_finish.isoformat(),
        counterfactual_finish=cf_finish.isoformat(),
        finish_delta_days=(cf_finish - actual_finish).days,
        target_uid=target_uid,
        target_name=target_name,
        target_actual_finish=t_actual,
        target_counterfactual_finish=t_cf,
        target_delta_days=t_delta,
    )
