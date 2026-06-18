"""Driving path **between two chosen UniqueIDs** — and how it moves across versions.

The operator picks a *source* UID **A** and a *target* UID **B**; this answers "what is the
controlling logic corridor from A to B, and does A actually drive B?" — then steps the loaded
versions (oldest → newest) to show how that corridor changes.

**Definition (built on the driving-slack engine, ADR-0011).** The *driving path to B* is the
chain of activities with under one working day of driving slack to B — the work that controls
B's date (:func:`engine.driving_slack.compute_driving_slack` /
:func:`engine.driving_slack.driving_path`). The *driving path between A and B* is the segment of
that chain lying on a logic route from A to B: the driving-path activities that are descendants
of A (plus A itself), topologically ordered A → … → B. A is said to **drive** B when A is itself
on B's driving path; if A only reaches B through activities that carry slack, the two are
*connected* but A does **not** drive B (we report the slack instead of a path). When several
equal-length legs drive B in parallel, every activity on them is included — the honest driving
sub-network, not an arbitrary single chain.

Everything is read from the loaded files and their CPM/driving-slack results; nothing is
fabricated.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    DEFAULT_TERTIARY_MAX_DAYS,
    compute_driving_slack,
)
from schedule_forensics.engine.path_trace import descendants_of, topo_order
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class DrivingPathBetween:
    """The driving corridor from ``source_uid`` to ``target_uid`` in one schedule version."""

    source_uid: int
    target_uid: int
    #: the driving-path activities from source to target, topologically ordered (source first,
    #: target last). Empty when source does not drive target (or either endpoint is absent).
    path: tuple[int, ...]
    source_present: bool  # source is a scheduled (non-summary) activity in this version
    target_present: bool  # target is a scheduled (non-summary) activity in this version
    connected: bool  # a directed logic route source → target exists
    drives: bool  # source is ON target's driving path (it controls target's date)
    #: source's driving slack to target in whole working days, when connected (``0`` while it
    #: drives); ``None`` when not connected or an endpoint is absent.
    source_slack_days: int | None

    @property
    def length(self) -> int:
        """Number of activities on the driving corridor (0 when there is none)."""
        return len(self.path)


def driving_path_between(
    schedule: Schedule,
    source_uid: int,
    target_uid: int,
    *,
    secondary_max_days: int = DEFAULT_SECONDARY_MAX_DAYS,
    tertiary_max_days: int = DEFAULT_TERTIARY_MAX_DAYS,
    cpm_result: CPMResult | None = None,
) -> DrivingPathBetween:
    """The driving corridor from ``source_uid`` to ``target_uid`` in ``schedule``.

    Robust to absent or summary endpoints (returns a flagged result rather than raising) so it
    can be mapped across versions where an activity may not exist yet. ``cpm_result`` is the
    caller's cached CPM for ``schedule`` (recomputed when ``None``)."""
    by_id = schedule.tasks_by_id
    src_t = by_id.get(source_uid)
    tgt_t = by_id.get(target_uid)
    source_present = src_t is not None and not src_t.is_summary
    target_present = tgt_t is not None and not tgt_t.is_summary

    if not target_present:
        return DrivingPathBetween(
            source_uid, target_uid, (), source_present, False, False, False, None
        )

    if source_uid == target_uid:
        # degenerate: a task trivially "drives" itself.
        self_path: tuple[int, ...] = (target_uid,) if source_present else ()
        return DrivingPathBetween(
            source_uid,
            target_uid,
            self_path,
            source_present,
            True,
            source_present,
            source_present,
            0 if source_present else None,
        )

    results = compute_driving_slack(
        schedule,
        target_uid=target_uid,
        secondary_max_days=secondary_max_days,
        tertiary_max_days=tertiary_max_days,
        cpm_result=cpm_result,
    )

    # results covers target and exactly its ancestors; source absent there ⇒ no route to target.
    if not source_present or source_uid not in results:
        return DrivingPathBetween(
            source_uid, target_uid, (), source_present, True, False, False, None
        )

    slack_days = int(results[source_uid].driving_slack_days)
    if not results[source_uid].on_driving_path:
        # connected, but source reaches target only through activities carrying slack.
        return DrivingPathBetween(source_uid, target_uid, (), True, True, True, False, slack_days)

    driving_set = {uid for uid, r in results.items() if r.on_driving_path}
    corridor = {source_uid} | (driving_set & descendants_of(schedule, source_uid))
    path = topo_order(schedule, corridor)
    return DrivingPathBetween(source_uid, target_uid, path, True, True, True, True, slack_days)


@dataclass(frozen=True)
class DrivingPathSnapshot:
    """One version's driving corridor between the two UIDs, and how it moved from the prior one."""

    label: str
    status_date: str | None  # the data date (ISO), if recorded
    between: DrivingPathBetween
    names: tuple[str, ...]  # activity names parallel to ``between.path``
    entered: tuple[int, ...]  # on the corridor now, not in the prior version
    left: tuple[int, ...]  # on the corridor in the prior version, not now
    stayed: tuple[int, ...]  # on the corridor in both
    length_delta: int | None  # corridor-length change vs the prior version (None for the first)
    #: plain-English transition vs the prior version (e.g. "driving path appeared",
    #: "A stopped driving B"); ``None`` for the first version (no prior to compare).
    change_note: str | None

    @property
    def status(self) -> str:
        """This version's state as a short phrase the UI can show as a chip."""
        b = self.between
        if not b.target_present:
            return "target activity absent"
        if not b.source_present:
            return "source activity absent"
        if not b.connected:
            return "no logic route A → B"
        if b.drives:
            return f"driving path of {b.length} activities"
        return f"connected — A holds {b.source_slack_days}d of slack to B (not driving)"


@dataclass(frozen=True)
class DrivingPathEvolution:
    """The whole workbook's driving-corridor evolution between two UIDs, oldest version first."""

    source_uid: int
    target_uid: int
    snapshots: tuple[DrivingPathSnapshot, ...]


def _transition(prior: DrivingPathBetween, cur: DrivingPathBetween) -> str | None:
    """A short note describing how the corridor's state changed between two versions."""
    if not prior.target_present and cur.target_present:
        return "target activity appeared"
    if prior.target_present and not cur.target_present:
        return "target activity removed"
    if not prior.source_present and cur.source_present:
        return "source activity appeared"
    if prior.source_present and not cur.source_present:
        return "source activity removed"
    if cur.drives and not prior.drives:
        return "driving path appeared" if not prior.connected else "A now drives B"
    if prior.drives and not cur.drives:
        return "driving path broke" if not cur.connected else "A stopped driving B"
    if not cur.connected and prior.connected:
        return "logic route A → B lost"
    if cur.connected and not prior.connected:
        return "logic route A → B gained"
    return None


def compute_driving_path_evolution(
    schedules: Sequence[Schedule],
    cpms: Sequence[CPMResult],
    source_uid: int,
    target_uid: int,
    *,
    secondary_max_days: int = DEFAULT_SECONDARY_MAX_DAYS,
    tertiary_max_days: int = DEFAULT_TERTIARY_MAX_DAYS,
) -> DrivingPathEvolution:
    """Per-version driving corridors between ``source_uid`` and ``target_uid`` (oldest → newest).

    ``cpms`` is parallel to ``schedules`` (the caller's cached results). Requires at least one
    version; the first has no prior, so its diff fields are empty."""
    if not schedules:
        raise ValueError("the driving-path analysis needs at least one schedule version")
    if len(cpms) != len(schedules):
        raise ValueError("cpms must parallel schedules")

    snapshots: list[DrivingPathSnapshot] = []
    prior_between: DrivingPathBetween | None = None
    prior_path: set[int] = set()
    for sch, cpm in zip(schedules, cpms, strict=True):
        between = driving_path_between(
            sch,
            source_uid,
            target_uid,
            secondary_max_days=secondary_max_days,
            tertiary_max_days=tertiary_max_days,
            cpm_result=cpm,
        )
        by_id = sch.tasks_by_id
        names = tuple((by_id[uid].name if uid in by_id else f"UID {uid}") for uid in between.path)
        cur_path = set(between.path)
        if prior_between is None:
            entered: tuple[int, ...] = ()
            left: tuple[int, ...] = ()
            stayed: tuple[int, ...] = ()
            length_delta: int | None = None
            change_note: str | None = None
        else:
            entered = tuple(sorted(cur_path - prior_path))
            left = tuple(sorted(prior_path - cur_path))
            stayed = tuple(sorted(cur_path & prior_path))
            length_delta = between.length - prior_between.length
            change_note = _transition(prior_between, between)

        snapshots.append(
            DrivingPathSnapshot(
                label=sch.source_file or sch.name,
                status_date=sch.status_date.date().isoformat() if sch.status_date else None,
                between=between,
                names=names,
                entered=entered,
                left=left,
                stayed=stayed,
                length_delta=length_delta,
                change_note=change_note,
            )
        )
        prior_between = between
        prior_path = cur_path

    return DrivingPathEvolution(
        source_uid=source_uid, target_uid=target_uid, snapshots=tuple(snapshots)
    )
