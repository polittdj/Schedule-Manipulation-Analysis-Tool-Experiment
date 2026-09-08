"""Per-UID driving-path facts for Ask-the-AI — let the engine answer, the model only narrate.

The local 8B model keeps getting "what is the driving path to UID X?" / "how many activities
drive UID X with zero days of driving slack?" wrong, because multi-hop path + slack traversal over
hundreds of activities is exactly what a small LLM is unreliable at. The engine already computes
this **exactly** and SSI-parity-validated (`engine/driving_slack.py`, ADR-0011). So when a question
names a UID with driving/path/slack intent, we run the engine and inject its answer as **cited**
facts; the model then narrates them, and the citation figure-gate (`ai.citations`) discards any
number it did not get from the engine — so it can never introduce a wrong count. This module IS the
"skill" the model references: it teaches nothing to the weights, it feeds the deterministic truth.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from itertools import pairwise

from schedule_forensics.ai.citations import CitedStatement
from schedule_forensics.ai.version_facts import elide_series
from schedule_forensics.engine.cpm import CPMResult, _offset_to_wall
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    PathTier,
    compute_driving_slack,
    driving_path,
)
from schedule_forensics.engine.trend import order_versions
from schedule_forensics.model.schedule import Schedule

#: A UID referenced explicitly (e.g. "UID 143", "task 143", "activity #143"). Requiring the keyword
#: avoids matching unrelated numbers in the question ("300 iterations", "0 days", "1 working day").
_UID_RE = re.compile(r"\b(?:uid|id|activity|task)\s*#?\s*0*(\d{1,7})\b", re.IGNORECASE)

#: Driving/path intent — injected only when the question is actually about driving paths.
_INTENT = ("driv", "path to", "controls", "controlling", "predecessor", "feeds into", "slack")


def _activities(n: int) -> str:
    """``"1 activity"`` / ``"7 activities"`` — correct pluralisation for the narrated counts."""
    return f"{n} activity" if n == 1 else f"{n} activities"


#: How many distinct focus UIDs to answer for, and how many drivers to name in-sentence (the full
#: set is still carried in the citations).
_MAX_UIDS = 2
_MAX_NAMED = 3


def _named_uids(question: str) -> list[int]:
    """Distinct UIDs named explicitly in the question, in order of first mention."""
    out: list[int] = []
    for m in _UID_RE.finditer(question):
        uid = int(m.group(1))
        if uid not in out:
            out.append(uid)
    return out


def driving_path_summary(
    schedule: Schedule, cpm: CPMResult, uid: int
) -> tuple[CitedStatement, ...]:
    """Cited driving-path facts for one focus ``uid`` (``()`` if it isn't a scheduled activity).

    Emits up to two facts: the count of activities on its **driving path** (0 days of driving slack
    — SSI's whole-working-day axis) with a few named in line and the full set carried as citations,
    plus the count of **near-driving** activities (the secondary day-tier). Every figure traces to
    the engine, so callers (Ask-the-AI narration, or the one-click button) never compute them.
    """
    if uid not in schedule.tasks_by_id:
        return ()
    try:
        results = compute_driving_slack(schedule, uid, cpm_result=cpm)
    except (KeyError, ValueError):
        return ()
    focus = schedule.tasks_by_id[uid]

    def _cite(u: int) -> Citation:
        t = schedule.tasks_by_id.get(u)
        return Citation(schedule.source_file, u, t.name if t is not None else "")

    drivers = [u for u in driving_path(schedule, results) if u != uid]
    named = ", ".join(f"UID {u}" for u in drivers[:_MAX_NAMED])
    tail = f" (e.g. {named})" if drivers else ""
    facts = [
        CitedStatement(
            f"The driving path to {focus.name} (UID {uid}) comprises {_activities(len(drivers))} "
            f"driving it with 0 days of driving slack{tail}.",
            tuple(_cite(u) for u in [uid, *drivers[:12]]),
        )
    ]
    near = [u for u, r in results.items() if u != uid and r.tier == PathTier.SECONDARY]
    if near:
        facts.append(
            CitedStatement(
                f"Near-driving UID {uid}: {_activities(len(near))} within "
                f"{DEFAULT_SECONDARY_MAX_DAYS} working days of driving slack.",
                tuple(_cite(u) for u in [uid, *near[:12]]),
            )
        )
    return tuple(facts)


def driving_path_facts(
    schedule: Schedule, cpm: CPMResult, question: str
) -> tuple[CitedStatement, ...]:
    """Cited driving-path facts for any UID named in a driving/path/slack question (else ``()``).

    Injected into the Ask-the-AI fact sheet so the model narrates the engine's exact driving-path
    answer instead of attempting the graph traversal itself (and the citation figure-gate discards
    any number it did not get from the engine).
    """
    if not any(k in question.lower() for k in _INTENT):
        return ()
    facts: list[CitedStatement] = []
    for uid in _named_uids(question)[:_MAX_UIDS]:
        facts.extend(driving_path_summary(schedule, cpm, uid))
    return tuple(facts)


# --- the per-version series (OR-11a) --------------------------------------------------------
#
# The workbook ask computed the driving path for ONE version — ``schedules[-1]`` — so a question
# spanning 32 loaded files was answered from the newest one's path. Measured on the pre-fix tree
# with 32 versions loaded and the focus UID named: exactly ONE driving-path fact reached the
# model, citing ONE file. The engine could always compute the rest (``compute_driving_slack``
# reproduces the operator's SSI Directional Path export for UID 152 EXACTLY — 76 of 76 members on
# the real 2,126-task master IMS, at 0.039 s a call); nothing looped it.


@dataclass(frozen=True)
class _PathPoint:
    """One version's driving path to the focus, as measured on THAT version's own network."""

    label: str
    status_date: dt.datetime | None
    #: ``None`` when the focus is absent from this version, or its slack could not be computed.
    drivers: frozenset[int] | None
    finish: dt.date | None
    #: True only when the focus EXISTS here but its driving slack could not be computed — a
    #: different fact from "the activity is not in this file", and never merged with it.
    unreadable: bool = False


def _focus_finish(schedule: Schedule, cpm: CPMResult, uid: int) -> dt.date | None:
    """The focus's own computed early finish as a date, honouring an own-calendar instant.

    A task on its own calendar carries wall-clock instants the project working-minute axis
    cannot represent (ADR-0476); ``early_finish_wall`` is those, and it wins when present —
    the same precedence ``engine/metrics/dcma14.py`` uses.
    """
    timing = cpm.timings.get(uid)
    if timing is None:
        return None
    if timing.early_finish_wall is not None:
        return timing.early_finish_wall.date()
    return _offset_to_wall(
        schedule.project_start, timing.early_finish, schedule.calendar, role="finish"
    ).date()


def _path_points(schedules: list[Schedule], cpms: list[CPMResult], uid: int) -> list[_PathPoint]:
    """One point per version, OLDEST FIRST by data date, each measured on its own network.

    The CPMs are re-paired BY IDENTITY after ordering. Ordering the schedules and then zipping
    positionally would measure one version's network against another version's timings — a
    silently wrong number, which in a testimony context is the worst defect this repo can ship.
    """
    by_obj = {id(s): c for s, c in zip(schedules, cpms, strict=True)}
    points: list[_PathPoint] = []
    for schedule in order_versions(schedules):
        cpm = by_obj[id(schedule)]
        label = schedule.source_file or schedule.name
        if uid not in schedule.tasks_by_id:
            points.append(_PathPoint(label, schedule.status_date, None, None))
            continue
        try:
            results = compute_driving_slack(schedule, uid, cpm_result=cpm)
        except (KeyError, ValueError):
            points.append(_PathPoint(label, schedule.status_date, None, None, unreadable=True))
            continue
        drivers = frozenset(u for u in driving_path(schedule, results) if u != uid)
        points.append(
            _PathPoint(label, schedule.status_date, drivers, _focus_finish(schedule, cpm, uid))
        )
    return points


def _date(value: dt.datetime | dt.date | None) -> str:
    return value.isoformat()[:10] if value is not None else "none"


def _series_entry(point: _PathPoint, uid: int) -> str:
    head = f"{point.label} (data date {_date(point.status_date)})"
    if point.unreadable:
        return f"{head} — the driving path to UID {uid} could not be computed for this version"
    if point.drivers is None:
        return f"{head} — UID {uid} is not in this version"
    finish = f", focus finishes {_date(point.finish)}" if point.finish is not None else ""
    return f"{head} {_activities(len(point.drivers))} driving it{finish}"


def _movement_fact(
    points: list[_PathPoint], uid: int, focus_name: str, cite: tuple[Citation, ...]
) -> CitedStatement | None:
    """First-to-last movement plus the step census — a MEASUREMENT, never an accusation.

    The engine states what changed and what did not; naming a motive is the analyst's job, and
    the citation gate exists precisely because an AI rephrase must not smuggle one in
    (``introduces_loaded_terms``). So this sentence counts re-wires and says so, and stops.
    """
    measured = [p for p in points if p.drivers is not None]
    if len(measured) < 2:
        return None
    first, last = measured[0], measured[-1]
    rewired = held = 0
    for prev, cur in pairwise(measured):
        if prev.drivers != cur.drivers:
            rewired += 1
            if prev.finish is not None and prev.finish == cur.finish:
                held += 1
    absent = sum(1 for p in points if p.drivers is None and not p.unreadable)
    moved = (
        (last.finish - first.finish).days
        if first.finish is not None and last.finish is not None
        else None
    )
    move_txt = (
        f"its computed finish moved {moved:+d} calendar day(s), from {_date(first.finish)} in "
        f"{first.label} to {_date(last.finish)} in {last.label}"
        if moved is not None
        else "its computed finish could not be read in both ends of the series"
    )
    missing = (
        f" UID {uid} is absent from {absent} of the {len(points)} loaded version(s)."
        if absent
        else ""
    )
    return CitedStatement(
        f"DRIVING-PATH MOVEMENT for {focus_name} (UID {uid}) across {len(measured)} measured "
        f"version(s): the count of activities driving it went from {len(first.drivers or ())} in "
        f"{first.label} to {len(last.drivers or ())} in {last.label}, and {move_txt}. Of the "
        f"{len(measured) - 1} version-to-version step(s), {rewired} changed WHICH activities "
        f"drive it, and {held} of those changed the membership while leaving its computed finish "
        f"on the same date. That is a count of what changed, not a statement of why: a re-wire "
        f"can be re-planning, a correction, or a scope change, and reading intent into it "
        f"requires the change and counterfactual facts, not this line.{missing}",
        cite,
        pinned=True,
    )


def driving_path_series(
    schedules: list[Schedule], cpms: list[CPMResult], uid: int
) -> tuple[CitedStatement, ...]:
    """The driving path to one focus ``uid`` computed for EVERY loaded version (OR-11a).

    Two pinned facts: the per-version series (each version's own driver count and the focus's own
    computed finish, oldest data date first) and the movement census. ``()`` for a single version
    — there is no series — and ``()`` when the focus exists in no version at all.

    Pinned because both selectors (``relevant_facts``'s 12 and ``model_evidence``'s 48) rank by
    question overlap: the frame of a cross-version answer must not be rankable out of it
    (ADR-0392's rule). One fact per version would ALSO have overflowed the 48 cap the moment the
    workbook passed ~40 files, so the series is one line, elided by the shared rule when long.
    """
    if len(schedules) < 2:
        return ()
    points = _path_points(schedules, cpms, uid)
    if all(p.drivers is None for p in points):
        return ()  # the focus is in no version we could measure — say nothing rather than "0"
    focus_name = next(
        (s.tasks_by_id[uid].name for s in order_versions(schedules)[::-1] if uid in s.tasks_by_id),
        f"UID {uid}",
    )
    cite = tuple(
        Citation(s.source_file, uid if uid in s.tasks_by_id else 0, s.source_file or s.name)
        for s in order_versions(schedules)
    )
    rendered, note = elide_series([_series_entry(p, uid) for p in points])
    facts = [
        CitedStatement(
            f"DRIVING-PATH SERIES for {focus_name} (UID {uid}) across all {len(points)} loaded "
            f"version(s) — each version's OWN driving path, recomputed on that version's own "
            f"network (activities with 0 days of driving slack to the focus), ordered oldest "
            f"data date first, NOT the newest version's path applied to the others: "
            f"{rendered}{note}.",
            cite,
            pinned=True,
        )
    ]
    movement = _movement_fact(points, uid, focus_name, cite)
    if movement is not None:
        facts.append(movement)
    return tuple(facts)


def driving_path_series_facts(
    schedules: list[Schedule], cpms: list[CPMResult], question: str
) -> tuple[CitedStatement, ...]:
    """Per-version driving-path series for every UID a driving/path/slack question names.

    Same gate as :func:`driving_path_facts` — intent word plus an explicit UID — so an unrelated
    question never pays for the traversal, and the same ``_MAX_UIDS`` bound.
    """
    if not any(k in question.lower() for k in _INTENT):
        return ()
    facts: list[CitedStatement] = []
    for uid in _named_uids(question)[:_MAX_UIDS]:
        facts.extend(driving_path_series(schedules, cpms, uid))
    return tuple(facts)
