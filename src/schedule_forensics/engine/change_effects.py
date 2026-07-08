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

from schedule_forensics.engine.cpm import CPMError, CPMResult, compute_cpm
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


#: Cap on the number of changes reverted individually (each revert = one full CPM pass). A huge
#: version diff (hundreds of changed links across two very different program versions) would
#: otherwise run hundreds of CPM passes per pair and wedge the page; beyond the cap the extra
#: changes are counted in ``skipped_capped`` and disclosed, never silently dropped (Law 2).
_MAX_CHANGE_EFFECTS = 60


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
    #: reverts whose isolated re-solve produced a logic cycle (can't be measured) — disclosed,
    #: not silently dropped. A cyclic revert is skipped from BOTH the per-change list and the
    #: aggregate so one impossible counterfactual never 500s or corrupts the page.
    skipped_unsolvable: int = 0
    #: changes beyond ``_MAX_CHANGE_EFFECTS`` not individually measured (disclosed).
    skipped_capped: int = 0
    #: False when even the acyclic-subset aggregate re-solve cycled; then the aggregate deltas
    #: are 0 and the UI omits the "all changes together" line rather than showing a wrong figure.
    aggregate_solved: bool = True


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
    try:
        base_cpm = current_cpm if current_cpm is not None else compute_cpm(current)
    except CPMError:
        return None
    per_day = current.calendar.working_minutes_per_day or 480

    resolved_target = (
        target_uid if target_uid is not None else _last_critical_uid(current, base_cpm)
    )
    # The target must be a SCHEDULED activity: it has to carry CPM timings for a finish delta to
    # exist. A summary / level-of-effort / unscheduled UID (e.g. the project-summary UID 0) is in
    # tasks_by_id but NOT in timings — indexing it would KeyError and 500 the whole page, so bail
    # cleanly to None (the page then simply omits the change-effects panel for this pair).
    if (
        resolved_target is None
        or resolved_target not in current.tasks_by_id
        or resolved_target not in base_cpm.timings
    ):
        return None
    target_name = current.tasks_by_id[resolved_target].name

    diff = diff_versions(prior, current)
    prior_by_key = {_relationship_key(r): r for r in prior.relationships}
    cur_by_key = {_relationship_key(r): r for r in current.relationships}
    prior_by_id = prior.tasks_by_id
    cur_by_id = current.tasks_by_id

    # accumulate the reverts that INDIVIDUALLY re-solve, to apply together for the aggregate
    aggregate = current
    effects: list[ChangeEffect] = []
    skipped_unsolvable = 0
    skipped_capped = 0

    def _try_revert(
        kind: str, label: str, uids: tuple[int, ...], cf_schedule: Schedule, agg_next: Schedule
    ) -> Schedule:
        """Measure ONE reverted change; return the aggregate to carry forward.

        Reverting a single change (restoring a removed predecessor, dropping an added one, …) can
        reintroduce a logic CYCLE that the later version had broken — the isolated counterfactual
        is then unsolvable. We skip it (counted in ``skipped_unsolvable``) and leave the aggregate
        unchanged so one impossible counterfactual can neither crash the page nor corrupt the
        "all changes together" figure. Beyond the cap we stop measuring and just count the rest.
        """
        nonlocal aggregate, skipped_unsolvable, skipped_capped
        if len(effects) >= _MAX_CHANGE_EFFECTS:
            skipped_capped += 1
            return aggregate
        try:
            cf_cpm = compute_cpm(cf_schedule)
        except CPMError:
            skipped_unsolvable += 1
            return aggregate
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
        return agg_next

    # 1. removed logic links (present in prior, gone now) → restore each
    for key in diff.removed_links:
        link = prior_by_key.get(key)
        if link is None:
            continue
        pred, succ = key[0], key[1]
        label = f"restore removed {key[2].value} link {pred}→{succ}" + (
            f" (lag {key[3] // per_day:+d}d)" if key[3] else ""
        )
        aggregate = _try_revert(
            "logic_restored",
            label,
            (pred, succ),
            _with_link_restored(current, link),
            _with_link_restored(aggregate, link),
        )

    # 2. added logic links (in current, not prior) → drop each
    for key in diff.added_links:
        if key not in cur_by_key:
            continue
        pred, succ = key[0], key[1]
        aggregate = _try_revert(
            "logic_dropped",
            f"remove added {key[2].value} link {pred}→{succ}",
            (pred, succ),
            _with_link_dropped(current, key),
            _with_link_dropped(aggregate, key),
        )

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
            upd = {"duration_minutes": prior_t.duration_minutes}
            aggregate = _try_revert(
                "duration_restored",
                label,
                (uid,),
                _with_task_field(current, uid, upd),
                _with_task_field(aggregate, uid, upd),
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
            aggregate = _try_revert(
                "constraint_restored",
                label,
                (uid,),
                _with_task_field(current, uid, update),
                _with_task_field(aggregate, uid, update),
            )

    if not effects:
        return None

    # The aggregate re-solve can itself cycle even when every INCLUDED revert solved alone (two
    # restored links that are individually fine but together close a loop). Guard it: on failure
    # report per-change only, with aggregate_solved=False, rather than 500.
    from schedule_forensics.engine.cpm import offset_to_datetime

    agg_target_delta = 0
    agg_project_delta = 0
    aggregate_solved = True
    try:
        agg_cpm = compute_cpm(aggregate)
        agg_target_delta = _finish_delta_wd(base_cpm, agg_cpm, resolved_target, per_day)
        agg_project_delta = round((agg_cpm.project_finish - base_cpm.project_finish) / per_day)
    except CPMError:
        aggregate_solved = False

    actual_target = offset_to_datetime(
        current.project_start, base_cpm.timings[resolved_target].early_finish, current.calendar
    )
    return ChangeEffectsReport(
        target_uid=resolved_target,
        target_name=target_name,
        target_is_last_critical=target_uid is None,
        actual_target_finish=actual_target.date().isoformat(),
        per_change=tuple(effects),
        aggregate_target_finish_delta_days=agg_target_delta,
        aggregate_project_finish_delta_days=agg_project_delta,
        skipped_unsolvable=skipped_unsolvable,
        skipped_capped=skipped_capped,
        aggregate_solved=aggregate_solved,
    )
