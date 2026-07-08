"""Per-change counterfactual EFFECT on a target activity (operator 2026-07-08).

The Schedule-Integrity page and the Ask-the-AI counterfactual must answer, with an *engine-
computed* number, "if this change had not been made, what would the finish of <target UID> (or
the last task on the critical path) have been?" — not a hand-waved "probably zero". Given a
version pair, this module reverts each detected change ONE AT A TIME (and all together), reruns
CPM, and reports the working-day movement of the chosen target's finish and of the project
finish.

Worked example that motivated it: on Hard_File → Hard_File_updated the FS link 188→187 was
removed. Restoring it and rerunning CPM moves UID 155's finish 2026-11-27 → 2026-12-31 — a
+23 working-day (33 calendar-day) slip the removal hid. The AI previously answered "zero effect";
this module produces the real figure, cited, so the AI (and the page) cannot get it wrong.

Sign convention (matches :mod:`path_counterfactual`): ``finish_delta_days > 0`` means the
counterfactual (change reverted) finishes LATER than the actual schedule — i.e. the change
pulled the finish IN (masked a slip). ``< 0`` means the change pushed the finish out.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.diff import diff_versions
from schedule_forensics.engine.path_evolution import effective_critical_set
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class ChangeEffect:
    """The finish effect of reverting ONE detected change, measured on the chosen target."""

    kind: str  # logic_restored | logic_dropped | duration_restored | constraint_restored
    label: str  # plain-English description of what was reverted
    citation_uids: tuple[int, ...]  # the activities the change touches (for citation)
    target_finish_delta_days: int  # working days on the target (>0 = the change hid a slip)
    project_finish_delta_days: int  # working days on the whole project finish


@dataclass(frozen=True)
class ChangeEffectsReport:
    """Per-change + aggregate counterfactual effects on a target activity."""

    target_uid: int
    target_name: str
    target_is_last_critical: bool  # True when the target was auto-chosen (no explicit target UID)
    actual_target_finish: str  # ISO date — the current schedule's computed target finish
    per_change: tuple[ChangeEffect, ...]
    aggregate_target_finish_delta_days: int  # all reverts applied together, on the target
    aggregate_project_finish_delta_days: int


def _last_critical_uid(schedule: Schedule, cpm: CPMResult) -> int | None:
    """The activity ON the critical path with the LATEST early finish — the task whose slip moves
    the project finish (the operator's 'last task on the critical path')."""
    crit = effective_critical_set(schedule, cpm)
    if not crit:
        # fall back to the max-early-finish scheduled task (drives the project finish)
        timings = cpm.timings
        return max(timings, key=lambda u: timings[u].early_finish) if timings else None
    return max(crit, key=lambda u: cpm.timings[u].early_finish if u in cpm.timings else -1)


def _relationship_key(r: Relationship) -> tuple[int, int, RelationshipType, int]:
    return (r.predecessor_id, r.successor_id, r.type, r.lag_minutes)


def _with_link_restored(current: Schedule, link: Relationship) -> Schedule:
    return current.model_copy(update={"relationships": (*current.relationships, link)})


def _with_link_dropped(current: Schedule, key: tuple[int, int, RelationshipType, int]) -> Schedule:
    kept = tuple(r for r in current.relationships if _relationship_key(r) != key)
    return current.model_copy(update={"relationships": kept})


def _with_task_field(current: Schedule, uid: int, updates: Mapping[str, object]) -> Schedule:
    tasks = tuple(t.model_copy(update=updates) if t.unique_id == uid else t for t in current.tasks)
    return current.model_copy(update={"tasks": tasks})


def _finish_delta_wd(base: CPMResult, cf: CPMResult, uid: int, per_day: int) -> int:
    """Working-day movement of ``uid``'s early finish, cf minus base (0 if either is missing)."""
    b = base.timings.get(uid)
    c = cf.timings.get(uid)
    if b is None or c is None:
        return 0
    return round((c.early_finish - b.early_finish) / per_day)


def compute_change_effects(
    prior: Schedule,
    current: Schedule,
    current_cpm: CPMResult | None = None,
    *,
    target_uid: int | None = None,
) -> ChangeEffectsReport | None:
    """Per-change counterfactual effects on ``target_uid`` (or, when None, the last task on the
    current critical path). Returns ``None`` when the target cannot be resolved.

    Each detected structural change (a removed logic link, an added logic link, a duration change,
    or a constraint change) is reverted ALONE on a copy of ``current``, CPM is rerun, and the
    working-day movement of the target's finish (and the project finish) is recorded — plus one
    aggregate figure with every change reverted together.
    """
    base_cpm = current_cpm if current_cpm is not None else compute_cpm(current)
    per_day = current.calendar.working_minutes_per_day or 480

    resolved_target = (
        target_uid if target_uid is not None else _last_critical_uid(current, base_cpm)
    )
    if resolved_target is None or resolved_target not in current.tasks_by_id:
        return None
    target_name = current.tasks_by_id[resolved_target].name

    diff = diff_versions(prior, current)
    prior_by_key = {_relationship_key(r): r for r in prior.relationships}
    cur_by_key = {_relationship_key(r): r for r in current.relationships}
    prior_by_id = prior.tasks_by_id
    cur_by_id = current.tasks_by_id

    # accumulate the reverts to apply together for the aggregate figure
    aggregate = current
    effects: list[ChangeEffect] = []

    def _record(kind: str, label: str, uids: tuple[int, ...], cf_schedule: Schedule) -> None:
        cf_cpm = compute_cpm(cf_schedule)
        effects.append(
            ChangeEffect(
                kind=kind,
                label=label,
                citation_uids=uids,
                target_finish_delta_days=_finish_delta_wd(
                    base_cpm, cf_cpm, resolved_target, per_day
                ),
                project_finish_delta_days=round(
                    (cf_cpm.project_finish - base_cpm.project_finish) / per_day
                ),
            )
        )

    # 1. removed logic links (present in prior, gone now) → restore each
    for key in diff.removed_links:
        link = prior_by_key.get(key)
        if link is None:
            continue
        pred, succ = key[0], key[1]
        label = f"restore removed {key[2].value} link {pred}→{succ}" + (
            f" (lag {key[3] // per_day:+d}d)" if key[3] else ""
        )
        _record("logic_restored", label, (pred, succ), _with_link_restored(current, link))
        aggregate = _with_link_restored(aggregate, link)

    # 2. added logic links (in current, not prior) → drop each
    for key in diff.added_links:
        if key not in cur_by_key:
            continue
        pred, succ = key[0], key[1]
        _record(
            "logic_dropped",
            f"remove added {key[2].value} link {pred}→{succ}",
            (pred, succ),
            _with_link_dropped(current, key),
        )
        aggregate = _with_link_dropped(aggregate, key)

    # 3. duration / constraint changes on activities present in both versions → restore prior value
    for td in diff.changed_tasks:
        uid = td.unique_id
        prior_t = prior_by_id.get(uid)
        cur_t = cur_by_id.get(uid)
        if prior_t is None or cur_t is None:
            continue
        dur = td.changed("duration_minutes")
        if dur is not None and prior_t.duration_minutes != cur_t.duration_minutes:
            verb = "cut" if cur_t.duration_minutes < prior_t.duration_minutes else "raised"
            label = (
                f"restore UID {uid} duration ({verb} "
                f"{cur_t.duration_minutes // per_day}→{prior_t.duration_minutes // per_day} wd)"
            )
            _record(
                "duration_restored",
                label,
                (uid,),
                _with_task_field(current, uid, {"duration_minutes": prior_t.duration_minutes}),
            )
            aggregate = _with_task_field(
                aggregate, uid, {"duration_minutes": prior_t.duration_minutes}
            )
        con = td.changed("constraint_type")
        if con is not None and (prior_t.constraint_type, prior_t.constraint_date) != (
            cur_t.constraint_type,
            cur_t.constraint_date,
        ):
            label = (
                f"restore UID {uid} constraint "
                f"({cur_t.constraint_type.value}→{prior_t.constraint_type.value})"
            )
            update = {
                "constraint_type": prior_t.constraint_type,
                "constraint_date": prior_t.constraint_date,
            }
            _record("constraint_restored", label, (uid,), _with_task_field(current, uid, update))
            aggregate = _with_task_field(aggregate, uid, update)

    if not effects:
        return None

    agg_cpm = compute_cpm(aggregate)
    from schedule_forensics.engine.cpm import offset_to_datetime

    actual_target = offset_to_datetime(
        current.project_start, base_cpm.timings[resolved_target].early_finish, current.calendar
    )
    return ChangeEffectsReport(
        target_uid=resolved_target,
        target_name=target_name,
        target_is_last_critical=target_uid is None,
        actual_target_finish=actual_target.date().isoformat(),
        per_change=tuple(effects),
        aggregate_target_finish_delta_days=_finish_delta_wd(
            base_cpm, agg_cpm, resolved_target, per_day
        ),
        aggregate_project_finish_delta_days=round(
            (agg_cpm.project_finish - base_cpm.project_finish) / per_day
        ),
    )
