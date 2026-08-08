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

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMError, CPMResult, compute_cpm
from schedule_forensics.engine.diff import diff_versions
from schedule_forensics.engine.path_evolution import effective_critical_set
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType


@dataclass(frozen=True)
class ChangeEffect:
    """The finish effect of reverting ONE detected change, measured on the chosen target."""

    kind: str  # logic_restored | logic_dropped | duration_restored | constraint_restored
    label: str  # plain-English description of what was reverted
    citation_uids: tuple[int, ...]  # the activities the change touches (for citation)
    target_finish_delta_days: int  # working days on the target (>0 = the change hid a slip)
    project_finish_delta_days: int  # working days on the whole project finish
    #: EXACT working-minute deltas behind the rounded day figures. round() maps a true sub-day
    #: effect (even exactly half a day, via round-half-even) to 0 "no effect" — a Law 2 lie the
    #: 2026-08-07 audit (F1) caught. The day fields keep their rounded meaning; presentation reads
    #: these to render a signed "<1 wd" instead of "no effect" when the truth is sub-day.
    target_finish_delta_minutes: int = 0
    project_finish_delta_minutes: int = 0
    #: True for the MS Project "reschedule uncompleted work" statusing artifact: the CURRENT
    #: version carries an SNET constraint stamped exactly at its own data date. Project writes
    #: these automatically when uncompleted work is rescheduled past the status date — they are
    #: real file differences (never dropped), but the UI clusters them under an explanatory
    #: label so dozens of tool-generated rows don't read as deliberate manual constraint edits.
    is_reschedule_artifact: bool = False


#: Cap on the number of changes reverted individually (each revert = one full CPM pass). A huge
#: version diff (hundreds of changed links across two very different program versions) would
#: otherwise run hundreds of CPM passes per pair and wedge the page; beyond the cap the extra
#: changes are counted in ``skipped_capped`` and disclosed, never silently dropped (Law 2).
#: Reschedule-ARTIFACT constraint reverts (statusing noise, almost always zero-effect) are
#: measured LAST, so on a capped pair the cap starves the artifacts, not the real changes.
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
    #: exact working-minute aggregates behind the rounded day figures (see ChangeEffect)
    aggregate_target_finish_delta_minutes: int = 0
    aggregate_project_finish_delta_minutes: int = 0
    #: reverts whose isolated re-solve produced a logic cycle (can't be measured) — disclosed,
    #: not silently dropped. A cyclic revert is skipped from BOTH the per-change list and the
    #: aggregate so one impossible counterfactual never 500s or corrupts the page.
    skipped_unsolvable: int = 0
    #: changes beyond ``_MAX_CHANGE_EFFECTS`` not individually measured (disclosed).
    skipped_capped: int = 0
    #: of ``skipped_capped``, how many match the reschedule-artifact PATTERN (SNET stamped at
    #: the data date on an incomplete task — detectable without a CPM pass), so the UI's
    #: artifact cluster can disclose "N more detected but not measured" honestly.
    skipped_capped_artifacts: int = 0
    #: False when even the acyclic-subset aggregate re-solve cycled; then the aggregate deltas
    #: are 0 and the UI omits the "all changes together" line rather than showing a wrong figure.
    aggregate_solved: bool = True
    #: the LABELS of the skipped reverts (audit F2, ADR-0369) — count-only disclosure hid WHICH
    #: changes went unmeasured; each label is the same plain-English text a measured row carries.
    #: ``len(skipped_unsolvable_labels) == skipped_unsolvable`` and likewise for capped.
    skipped_unsolvable_labels: tuple[str, ...] = ()
    skipped_capped_labels: tuple[str, ...] = ()
    #: True when the chosen target could not be resolved to a scheduled activity (absent UID,
    #: summary/unscheduled row, or no critical path to auto-anchor on). The report then carries
    #: the FAILED target's identity with per_change empty and aggregate_solved False, so the
    #: page renders a target-unavailable banner instead of silently omitting the panel — the
    #: old contract returned None for BOTH "no target" and "no changes", indistinguishably
    #: (audit F2, ADR-0369).
    target_unavailable: bool = False


def _last_critical_uid(schedule: Schedule, cpm: CPMResult) -> int | None:
    """The activity ON the critical path with the LATEST early finish — the task whose slip moves
    the project finish (the operator's 'last task on the critical path')."""
    crit = effective_critical_set(schedule, cpm)
    if not crit:
        # fall back to the max-early-finish scheduled task (drives the project finish)
        timings = cpm.timings
        return max(timings, key=lambda u: (timings[u].early_finish, u)) if timings else None
    # several activities can TIE at the latest early finish (e.g. a finish milestone plus the
    # tasks feeding it) — break the tie by UID so the choice is deterministic, not set-order
    return max(crit, key=lambda u: (cpm.timings[u].early_finish if u in cpm.timings else -1, u))


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


def _finish_delta_minutes(base: CPMResult, cf: CPMResult, uid: int) -> int:
    """EXACT working-minute movement of ``uid``'s early finish, cf minus base (0 if missing)."""
    b = base.timings.get(uid)
    c = cf.timings.get(uid)
    if b is None or c is None:
        return 0
    return c.early_finish - b.early_finish


def _finish_delta_wd(base: CPMResult, cf: CPMResult, uid: int, per_day: int) -> int:
    """Working-day movement of ``uid``'s early finish, cf minus base (0 if either is missing)."""
    return round(_finish_delta_minutes(base, cf, uid) / per_day)


def _wd_text(minutes: int, per_day: int) -> str:
    """A duration in working days with sub-day fidelity: whole days render as bare integers
    (byte-identical to the old floor-divided label on every whole-day value), a fractional
    value renders to 2 dp — so a sub-day duration can never disappear into "0"."""
    if minutes % per_day == 0:
        return str(minutes // per_day)
    return f"{minutes / per_day:.2f}".rstrip("0").rstrip(".")


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
    # tasks_by_id but NOT in timings — indexing it would KeyError and 500 the whole page. This
    # used to bail to None, indistinguishable from "no changes detected", so the page omitted
    # the panel SILENTLY (audit F2). Now it returns a sentinel report naming the failed target
    # (ADR-0369): per_change empty, every figure 0, aggregate_solved False — nothing a consumer
    # could mistake for a measurement, and enough identity for the disclosure banner.
    if (
        resolved_target is None
        or resolved_target not in current.tasks_by_id
        or resolved_target not in base_cpm.timings
    ):
        bad = resolved_target if resolved_target is not None else target_uid
        bad_name = (
            current.tasks_by_id[bad].name if bad is not None and bad in current.tasks_by_id else ""
        )
        return ChangeEffectsReport(
            target_uid=bad if bad is not None else 0,
            target_name=bad_name,
            target_is_last_critical=target_uid is None,
            actual_target_finish="",
            per_change=(),
            aggregate_target_finish_delta_days=0,
            aggregate_project_finish_delta_days=0,
            aggregate_solved=False,
            target_unavailable=True,
        )
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
    skipped_capped_artifacts = 0
    # the identities behind the skip counts (ADR-0369) — disclosed, never count-only
    skipped_unsolvable_labels: list[str] = []
    skipped_capped_labels: list[str] = []

    def _try_revert(
        kind: str,
        label: str,
        uids: tuple[int, ...],
        cf_schedule: Schedule,
        agg_next: Schedule,
        *,
        is_artifact: bool = False,
    ) -> Schedule:
        """Measure ONE reverted change; return the aggregate to carry forward.

        Reverting a single change (restoring a removed predecessor, dropping an added one, …) can
        reintroduce a logic CYCLE that the later version had broken — the isolated counterfactual
        is then unsolvable. We skip it (counted in ``skipped_unsolvable``) and leave the aggregate
        unchanged so one impossible counterfactual can neither crash the page nor corrupt the
        "all changes together" figure. Beyond the cap we stop measuring and just count the rest.
        """
        nonlocal aggregate, skipped_unsolvable, skipped_capped, skipped_capped_artifacts
        if len(effects) >= _MAX_CHANGE_EFFECTS:
            skipped_capped += 1
            skipped_capped_labels.append(label)
            if is_artifact:
                skipped_capped_artifacts += 1
            return aggregate
        try:
            cf_cpm = compute_cpm(cf_schedule)
        except CPMError:
            skipped_unsolvable += 1
            skipped_unsolvable_labels.append(label)
            return aggregate
        tgt_minutes = _finish_delta_minutes(base_cpm, cf_cpm, resolved_target)
        proj_minutes = cf_cpm.project_finish - base_cpm.project_finish
        effects.append(
            ChangeEffect(
                kind=kind,
                label=label,
                citation_uids=uids,
                target_finish_delta_days=round(tgt_minutes / per_day),
                project_finish_delta_days=round(proj_minutes / per_day),
                target_finish_delta_minutes=tgt_minutes,
                project_finish_delta_minutes=proj_minutes,
                is_reschedule_artifact=is_artifact,
            )
        )
        return agg_next

    # 1. removed logic links (present in prior, gone now) → restore each
    for key in diff.removed_links:
        link = prior_by_key.get(key)
        if link is None:
            continue
        pred, succ = key[0], key[1]
        # whole-day lags keep the old floor-divided text byte-identical; a sub-day lag renders
        # its fractional days + exact minutes instead of collapsing to "+0d" (audit F7 class)
        lag_txt = (
            f" (lag {key[3] // per_day:+d}d)"
            if key[3] % per_day == 0
            else f" (lag {'+' if key[3] > 0 else '-'}{_wd_text(abs(key[3]), per_day)}d / "
            f"{key[3]:+d} min)"
        )
        label = f"restore removed {key[2].value} link {pred}→{succ}" + (lag_txt if key[3] else "")
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

    # 3. duration / constraint changes on activities present in both versions → restore prior
    # value. Reschedule-ARTIFACT constraint reverts are deferred to run AFTER every real change
    # (see below): on a pair large enough to hit the measurement cap, the cap must starve the
    # statusing noise, never a deliberate edit.
    deferred_artifacts: list[tuple[int, str, dict[str, object]]] = []
    for td in diff.changed_tasks:
        uid = td.unique_id
        prior_t = prior_by_id.get(uid)
        cur_t = cur_by_id.get(uid)
        if prior_t is None or cur_t is None:
            continue
        dur = td.changed("duration_minutes")
        if dur is not None and prior_t.duration_minutes != cur_t.duration_minutes:
            verb = "cut" if cur_t.duration_minutes < prior_t.duration_minutes else "raised"
            # sub-day fidelity (audit F7): the old floor-divided label rendered a 240→60 min cut
            # as "cut 0→0 wd". Whole-day pairs stay byte-identical; a fractional side renders to
            # 2 dp with the exact minutes riding along so no duration change can vanish.
            cur_wd = _wd_text(cur_t.duration_minutes, per_day)
            prior_wd = _wd_text(prior_t.duration_minutes, per_day)
            exact = (
                f" ({cur_t.duration_minutes}→{prior_t.duration_minutes} min)"
                if "." in cur_wd or "." in prior_wd
                else ""
            )
            label = f"restore UID {uid} duration ({verb} {cur_wd}→{prior_wd} wd{exact})"
            upd = {"duration_minutes": prior_t.duration_minutes}
            aggregate = _try_revert(
                "duration_restored",
                label,
                (uid,),
                _with_task_field(current, uid, upd),
                _with_task_field(aggregate, uid, upd),
            )
        # a DATE-only constraint move (same type, new date) is just as real as a type flip —
        # e.g. MS Project re-stamping an existing SNET at a new data date — so trigger on either
        con = td.changed("constraint_type") or td.changed("constraint_date")
        if con is not None and (prior_t.constraint_type, prior_t.constraint_date) != (
            cur_t.constraint_type,
            cur_t.constraint_date,
        ):

            def _con_desc(ctype: ConstraintType, cdate: object) -> str:
                date_txt = f" {cdate.date().isoformat()}" if isinstance(cdate, dt.datetime) else ""
                return f"{ctype.value}{date_txt}"

            label = (
                f"restore UID {uid} constraint (now "
                f"{_con_desc(cur_t.constraint_type, cur_t.constraint_date)} → was "
                f"{_con_desc(prior_t.constraint_type, prior_t.constraint_date)})"
            )
            # MS Project "reschedule uncompleted work" artifact: the current version's constraint
            # is an SNET stamped at its OWN data date on an INCOMPLETE task — Project writes
            # these automatically when uncompleted work is pushed past the status date, so it is
            # a statusing side effect, not a manual constraint edit. (A complete task can't be
            # rescheduled, so SNET-at-data-date on one is NOT the artifact.) Flagged and measured
            # LAST (never dropped) so the UI can cluster them and the cap can't starve real edits.
            is_artifact = (
                cur_t.constraint_type is ConstraintType.SNET
                and cur_t.constraint_date is not None
                and current.status_date is not None
                and cur_t.constraint_date.date() == current.status_date.date()
                and cur_t.percent_complete < 100.0
            )
            update: dict[str, object] = {
                "constraint_type": prior_t.constraint_type,
                "constraint_date": prior_t.constraint_date,
            }
            if is_artifact:
                deferred_artifacts.append((uid, label, update))
            else:
                aggregate = _try_revert(
                    "constraint_restored",
                    label,
                    (uid,),
                    _with_task_field(current, uid, update),
                    _with_task_field(aggregate, uid, update),
                )

    # 4. the deferred reschedule-artifact constraint reverts — measured last, so on a capped pair
    # the unmeasured remainder is the zero-effect statusing noise, not the deliberate changes.
    for uid, label, update in deferred_artifacts:
        aggregate = _try_revert(
            "constraint_restored",
            label,
            (uid,),
            _with_task_field(current, uid, update),
            _with_task_field(aggregate, uid, update),
            is_artifact=True,
        )

    # Nothing to say ONLY when no change was detected at all. If changes WERE detected but every
    # isolated revert cycled (all in skipped_unsolvable), still return a report with empty
    # per_change so the page can DISCLOSE "N change(s) detected but none could be measured" rather
    # than silently omitting the panel (Law 2 — every skip is disclosed).
    if not effects and skipped_unsolvable == 0 and skipped_capped == 0:
        return None

    from schedule_forensics.engine.cpm import offset_to_datetime

    # The aggregate re-solve can itself cycle even when every INCLUDED revert solved alone (two
    # restored links that are individually fine but together close a loop). Guard it: on failure
    # report per-change only, with aggregate_solved=False, rather than 500. The aggregate folds in
    # ONLY the individually-measured reverts (skipped/capped ones are excluded), so it is PARTIAL
    # whenever any change was skipped/capped — the UI must not label a partial total "every change".
    agg_target_delta = 0
    agg_project_delta = 0
    agg_target_minutes = 0
    agg_project_minutes = 0
    aggregate_solved = bool(effects)  # no measured reverts -> no meaningful aggregate
    if effects:
        try:
            agg_cpm = compute_cpm(aggregate)
            agg_target_minutes = _finish_delta_minutes(base_cpm, agg_cpm, resolved_target)
            agg_project_minutes = agg_cpm.project_finish - base_cpm.project_finish
            agg_target_delta = round(agg_target_minutes / per_day)
            agg_project_delta = round(agg_project_minutes / per_day)
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
        aggregate_target_finish_delta_minutes=agg_target_minutes,
        aggregate_project_finish_delta_minutes=agg_project_minutes,
        skipped_unsolvable=skipped_unsolvable,
        skipped_capped=skipped_capped,
        skipped_capped_artifacts=skipped_capped_artifacts,
        aggregate_solved=aggregate_solved,
        skipped_unsolvable_labels=tuple(skipped_unsolvable_labels),
        skipped_capped_labels=tuple(skipped_capped_labels),
    )
