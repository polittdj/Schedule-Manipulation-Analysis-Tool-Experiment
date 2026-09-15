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
from schedule_forensics.engine.cpm import (
    CPMResult,
    _offset_to_wall,
    datetime_to_offset,
)
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
    #: The focus's finish on the axis the drivers are measured on: the file's own stored Finish
    #: (MS Project's — the date SSI's Directional Path shows), else the CPM early finish.
    finish: dt.date | None
    #: True when ``finish`` is the file's stored Finish; False when the file stores none and the
    #: CPM early finish stands in (hand-authored schedules).
    finish_stored: bool = False
    #: The engine's logic-only early finish, carried ONLY when it disagrees with the stored Finish
    #: by a whole working day or more; ``None`` when they agree (or nothing is stored to disagree
    #: with). ``logic_gap_days`` is that disagreement in working days, positive = logic later.
    logic_finish: dt.date | None = None
    logic_gap_days: int = 0
    #: True only when the focus EXISTS here but its driving slack could not be computed — a
    #: different fact from "the activity is not in this file", and never merged with it.
    unreadable: bool = False


@dataclass(frozen=True)
class _FocusFinish:
    """The focus's finish in one version on the two axes the tool keeps (ADR-0310)."""

    finish: dt.date | None
    stored: bool
    logic_finish: dt.date | None
    logic_gap_days: int


# --- whose date the focus finish is (OR-20) ----------------------------------------------------
#
# The drivers above are measured on the file's STORED, progress-aware dates (``date_basis``): the
# axis SSI runs on inside MS Project and the only one that reproduced its export (ADR-0011). The
# finish printed beside them was the engine's logic-only CPM early finish, unlabelled. On the
# operator's own IMS the two disagree by more than a day on 50 of 1,723 scheduled activities (up
# to 106 days); a focus among them was reported at a date neither MS Project nor SSI shows, next
# to a SCHEDULE-LOGIC FINISH SERIES of the same shape — and a 32-version answer tabled one such
# date 656 days past the Finish the file carries. So the reported finish is the stored Finish, the
# logic-only finish rides beside it only where the two part company (Law 2: stated, never
# silently substituted), and the header says which date this line carries.


def _logic_finish_wall(schedule: Schedule, cpm: CPMResult, uid: int) -> dt.datetime | None:
    """The focus's own logic-only early finish as an instant, honouring an own-calendar instant.

    A task on its own calendar carries wall-clock instants the project working-minute axis
    cannot represent (ADR-0476); ``early_finish_wall`` is those, and it wins when present —
    the same precedence ``engine/metrics/dcma14.py`` uses.
    """
    timing = cpm.timings.get(uid)
    if timing is None:
        return None
    if timing.early_finish_wall is not None:
        return timing.early_finish_wall
    return _offset_to_wall(
        schedule.project_start, timing.early_finish, schedule.calendar, role="finish"
    )


def _focus_finish(schedule: Schedule, cpm: CPMResult, uid: int) -> _FocusFinish:
    """The focus's finish as the file stores it, with the logic-only finish where it disagrees.

    The stored Finish is the figure (the drivers' axis; MS Project's and SSI's date). The CPM
    early finish stands in only when the file stores no Finish. A logic-only finish that differs
    from the stored one by a whole working day or more is carried with its signed gap so the line
    can disclose it; a sub-day difference is a representation, not a disagreement, and is not.

    Both finishes are compared on ONE ruler — the project working-minute axis every CPM offset
    lives on (ADR-0310), with the stored instant converted by :func:`datetime_to_offset`. On that
    ruler a Friday 17:00 finish and the Monday 08:00 milestone MS Project stores after it are the
    same offset; a wall-clock window between the two reads a full day (measured: 480 minutes of
    :func:`working_minutes_between` on the default calendar) and would disclose a disagreement
    that is only a representation.
    """
    task = schedule.tasks_by_id.get(uid)
    stored = task.finish if task is not None else None
    logic = _logic_finish_wall(schedule, cpm, uid)
    if stored is None:
        return _FocusFinish(logic.date() if logic is not None else None, False, None, 0)
    timing = cpm.timings.get(uid)
    if logic is None or timing is None:
        return _FocusFinish(stored.date(), True, None, 0)
    stored_offset = datetime_to_offset(schedule.project_start, stored, schedule.calendar)
    gap_minutes = timing.early_finish - stored_offset
    gap_days = abs(gap_minutes) // schedule.calendar.working_minutes_per_day
    if gap_days < 1:
        return _FocusFinish(stored.date(), True, None, 0)
    signed = gap_days if gap_minutes > 0 else -gap_days
    return _FocusFinish(stored.date(), True, logic.date(), signed)


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
        ff = _focus_finish(schedule, cpm, uid)
        points.append(
            _PathPoint(
                label,
                schedule.status_date,
                drivers,
                ff.finish,
                finish_stored=ff.stored,
                logic_finish=ff.logic_finish,
                logic_gap_days=ff.logic_gap_days,
            )
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
    finish = ""
    if point.finish is not None:
        finish = f"; UID {uid} finishes {_date(point.finish)}"
        if not point.finish_stored:
            finish += " (computed by CPM — the file stores no Finish for it)"
        elif point.logic_finish is not None:
            when = "later" if point.logic_gap_days > 0 else "earlier"
            finish += (
                f" (the file's stored Finish; this engine's logic-only finish for it is "
                f"{_date(point.logic_finish)}, {abs(point.logic_gap_days)} working days {when} — "
                f"a date the file's logic alone does not reproduce)"
            )
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
        f"its Finish moved {moved:+d} calendar day(s), from {_date(first.finish)} in "
        f"{first.label} to {_date(last.finish)} in {last.label}"
        if moved is not None
        else "its Finish could not be read in both ends of the series"
    )
    missing = (
        f" UID {uid} is absent from {absent} of the {len(points)} loaded version(s)."
        if absent
        else ""
    )
    disagree = sum(1 for p in measured if p.logic_finish is not None)
    logic_note = (
        f" Note: in {disagree} of the {len(measured)} measured version(s) this engine's "
        f"logic-only finish for UID {uid} disagrees with the stored Finish by a working day or "
        f"more — read those lines with both dates in view."
        if disagree
        else ""
    )
    return CitedStatement(
        f"DRIVING-PATH MOVEMENT for {focus_name} (UID {uid}) across {len(measured)} measured "
        f"version(s): the count of activities driving it went from {len(first.drivers or ())} in "
        f"{first.label} to {len(last.drivers or ())} in {last.label}, and {move_txt}. Of the "
        f"{len(measured) - 1} version-to-version step(s), {rewired} changed WHICH activities "
        f"drive it, and {held} of those changed the membership while leaving its Finish on the "
        f"same date. That is a count of what changed, not a statement of why: a re-wire can be "
        f"re-planning, a correction, or a scope change, and reading intent into it requires the "
        f"change and counterfactual facts, not this line.{missing}{logic_note}",
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
            f"data date first, NOT the newest version's path applied to the others. The finish "
            f"on each line is UID {uid}'s own stored Finish in that file (MS Project's Finish, "
            f"the date SSI's Directional Path shows) — NOT the project's network finish, which "
            f"the SCHEDULE-LOGIC FINISH SERIES carries separately; where this engine's logic-only "
            f"finish for UID {uid} disagrees with the stored Finish by a working day or more, "
            f"both dates are stated on that line: {rendered}{note}.",
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
