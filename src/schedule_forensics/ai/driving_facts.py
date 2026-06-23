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

import re

from schedule_forensics.ai.citations import CitedStatement
from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.driving_slack import (
    DEFAULT_SECONDARY_MAX_DAYS,
    PathTier,
    compute_driving_slack,
    driving_path,
)
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
