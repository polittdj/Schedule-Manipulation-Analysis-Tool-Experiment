"""Ask-the-AI — grounded question answering over the schedule's computed facts (§6.D).

The analyst types a question; the answer is grounded in a **fact sheet the engine
computed** (frame dates, DCMA verdicts, findings, float bands, completion performance,
forecasts, driving path) — every fact a :class:`CitedStatement`. Two answering modes
(operator-selectable, M18 "AI at full power"):

* **interpretive** (default): the model may compute differences/ratios from the facts
  and explain implications — derived figures are allowed; every answer ships with the
  cited facts alongside and the standing *"AI can err — verify against citations"*
  disclaimer in the UI.
* **strict**: any numeric figure in the model's answer that does not appear in the fact
  sheet **discards the whole answer** (the cited facts are shown instead — the tool
  presents no number the engine did not compute).

With the offline Null backend there is no generation at all: the facts matching the
question are returned verbatim. :func:`build_workbook_fact_sheet` extends the same
contract across every loaded version (multi-version pages). Everything runs locally;
the question and the data never leave the machine.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable

from schedule_forensics.ai.backend import AIBackend
from schedule_forensics.ai.citations import _FIGURE_RE, CitedStatement
from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation, ScheduleAudit
from schedule_forensics.engine.forecast import ForecastSet, compute_finish_forecasts
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.engine.trend import order_versions
from schedule_forensics.model.schedule import Schedule

#: Most facts to SHOW the analyst for a question (the question-relevant selection).
_MAX_FACTS = 12
#: Most facts to feed a live local model as EVIDENCE. The analyst is shown the relevant
#: slice (`relevant_facts`), but a real model is given the whole cited picture so it can
#: both answer the question and reason about the schedule as a whole — local, so a fuller
#: prompt costs nothing externally. Comfortably exceeds a single schedule's fact count.
_MODEL_MAX_FACTS = 48

_WORD_RE = re.compile(r"[a-z0-9]{3,}")
#: Question words that carry no selection signal.
_STOPWORDS = frozenset(
    "the and for are was were will what when where which who why how does did with this "  # noqa: SIM905
    "that have has been being can could should would much many tell show give about than "
    "schedule project activity activities task tasks".split()
)
#: Vague/no-match question: lead with the frame fact + a few headline facts (NOT the whole
#: sheet — padding the result back up to the cap made every answer look identical, the
#: "same results no matter what you ask" defect).
_OVERVIEW_FACTS = 4
#: Forensic intent aliases: ``word-prefix → substrings to look for in the fact text``. The
#: analyst's vocabulary that the engine's facts phrase differently — "late"/"slip"/"delay"
#: live in the facts as "behind"/"variance"/"forecast", "risk" as "float"/"critical", etc.
#: A question word starting with a key adds that key's substrings to the match set, so the
#: question reaches the facts that actually carry the answer (matched case-insensitively).
_INTENT_ALIAS: dict[str, tuple[str, ...]] = {
    "late": ("behind", "variance", "forecast", "finish", "slip"),
    "slip": ("behind", "variance", "forecast", "finish"),
    "delay": ("behind", "variance", "forecast", "finish"),
    "behind": ("behind", "variance"),
    "earl": ("ahead", "forecast"),
    "risk": ("float", "critical", "negative"),
    "logic": ("logic", "lag", "lead", "constraint"),
    "depend": ("logic", "lag", "lead"),
    "link": ("logic", "lag", "lead"),
    "constraint": ("constraint", "hard"),
    "forecast": ("forecast", "finish"),
    "finish": ("forecast", "finish"),
    "complet": ("complete", "progress", "performance"),
    "progress": ("complete", "progress", "performance"),
    "critic": ("critical", "driving", "float"),
    "driv": ("driving", "critical", "float"),
    "float": ("float", "critical", "negative"),
    "manipul": ("manipulation", "signal", "finding"),
    "find": ("finding",),
    "problem": ("finding", "fail"),
    "issue": ("finding", "fail"),
}


def _stems(text: str) -> set[str]:
    """Lower-cased content stems of ``text`` — plural/suffix-insensitive so "findings"
    matches "Finding", "constraints" matches "Constraint", "forecasts" matches "forecast"."""
    out: set[str] = set()
    for word in _WORD_RE.findall(text.lower()):
        if word in _STOPWORDS:
            continue
        for suffix in ("ing", "ied", "ies", "ed", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        out.add(word)
    return out


def build_fact_sheet(
    schedule: Schedule,
    cpm: CPMResult,
    audit: ScheduleAudit,
    findings: tuple[Finding, ...],
    float_bands: dict[str, MetricResult],
    completion: dict[str, MetricResult],
    forecast: ForecastSet,
) -> tuple[CitedStatement, ...]:
    """The cited facts a question may be answered from — engine-computed, never the model's."""
    label = schedule.source_file or schedule.name
    by_id = schedule.tasks_by_id
    finish_driving = [
        uid
        for uid, t in sorted(cpm.timings.items())
        if t.early_finish == cpm.project_finish and uid in by_id
    ]
    drivers = tuple(Citation(label, uid, by_id[uid].name) for uid in finish_driving) or tuple(
        Citation(label, t.unique_id, t.name) for t in schedule.tasks[:3]
    )

    tasks = non_summary(schedule)
    data_date = schedule.status_date.date().isoformat() if schedule.status_date else "none recorded"
    completed = sum(1 for t in tasks if t.percent_complete >= 100.0)
    in_progress = sum(1 for t in tasks if 0.0 < t.percent_complete < 100.0)
    cpm_finish = offset_to_datetime(
        schedule.project_start, cpm.project_finish, schedule.calendar
    ).date()
    facts: list[CitedStatement] = [
        CitedStatement(
            f"Schedule frame: project start {schedule.project_start.date().isoformat()}, "
            f"data date {data_date}, "
            f"computed CPM finish {cpm_finish.isoformat()}. {len(tasks)} activities: "
            f"{completed} complete, {in_progress} in progress, "
            f"{len(tasks) - completed - in_progress} not started.",
            drivers,
        )
    ]
    if finish_driving:
        facts.append(
            CitedStatement(
                f"Finish-driving activities: {len(finish_driving)} of {len(tasks)} activities "
                f"complete on the computed finish {cpm_finish.isoformat()} (zero float to the "
                "project end).",
                drivers,
            )
        )
    for f in forecast.forecasts:
        if f.finish is not None:
            facts.append(
                CitedStatement(
                    f"Finish forecast ({f.name}): {f.finish.isoformat()} — {f.basis}.", drivers
                )
            )
    for check in audit.checks:
        if check.status is CheckStatus.NOT_APPLICABLE:
            continue
        cites = check.citations[:5] or drivers
        facts.append(
            CitedStatement(
                f"DCMA {check.name}: {check.status} — {check.count} of {check.population} "
                f"({round(check.value, 2)}{check.unit}).",
                cites,
            )
        )
    for finding in findings[:8]:
        facts.append(
            CitedStatement(
                f"Finding [{finding.severity}/{finding.category}]: {finding.title}. "
                f"{finding.course_of_action}",
                finding.citations,
            )
        )
    for mid in ("float_total_0", "float_total_lt5", "float_total_lt10"):
        r = float_bands[mid]
        facts.append(
            CitedStatement(
                f"Float band {r.name}: {r.count} of {r.population} incomplete activities "
                f"({r.value}%).",
                _cite(schedule, label, r.offender_uids[:5]) or drivers,
            )
        )
    for mid in ("completed_behind", "avg_days_late", "avg_completion_variance", "mei"):
        r = completion[mid]
        if r.population:
            facts.append(
                CitedStatement(
                    f"Completion performance — {r.name}: {r.value}{r.unit} "
                    f"({r.count} of {r.population}).",
                    _cite(schedule, label, r.offender_uids[:5]) or drivers,
                )
            )
    return tuple(facts)


def _cite(schedule: Schedule, label: str, uids: tuple[int, ...]) -> tuple[Citation, ...]:
    by_id = schedule.tasks_by_id
    return tuple(Citation(label, uid, by_id[uid].name) for uid in uids if uid in by_id)


def build_workbook_fact_sheet(
    schedules: list[Schedule], cpms: list[CPMResult]
) -> tuple[CitedStatement, ...]:
    """Cited facts spanning EVERY loaded version — the multi-version pages' ask panel.

    Reuses the Diagnostic Executive Briefing's deterministic, fully-cited statements
    (workbook frame, cross-version trend, per-project summaries, per-project quality
    verdicts) and adds the latest consecutive pair's manipulation signals plus the
    newest version's finish forecasts. Engine-computed only — nothing is generated.
    """
    from schedule_forensics.ai.briefing import build_briefing  # local: avoid module cycle

    briefing = build_briefing(schedules, cpms=cpms)
    facts: list[CitedStatement] = [s for section in briefing.sections for s in section.statements]
    ordered = order_versions(schedules)
    by_obj = {id(s): c for s, c in zip(schedules, cpms, strict=True)}
    if len(ordered) >= 2:
        prior, current = ordered[-2], ordered[-1]
        for finding in detect_manipulation(
            current, prior, current_cpm=by_obj[id(current)], prior_cpm=by_obj[id(prior)]
        )[:6]:
            facts.append(
                CitedStatement(
                    f"Manipulation signal (latest pair) [{finding.severity}]: {finding.title}. "
                    f"{finding.course_of_action}",
                    finding.citations,
                )
            )
    latest, latest_cpm = ordered[-1], by_obj[id(ordered[-1])]
    label = latest.source_file or latest.name
    by_id = latest.tasks_by_id
    drivers = tuple(
        Citation(label, uid, by_id[uid].name)
        for uid, t in sorted(latest_cpm.timings.items())
        if t.early_finish == latest_cpm.project_finish and uid in by_id
    ) or tuple(Citation(label, t.unique_id, t.name) for t in latest.tasks[:3])
    for f in compute_finish_forecasts(latest, latest_cpm).forecasts:
        if f.finish is not None:
            facts.append(
                CitedStatement(
                    f"Latest-version finish forecast ({f.name}): {f.finish.isoformat()} — "
                    f"{f.basis}.",
                    drivers,
                )
            )
    return tuple(facts)


def _question_overlap(question: str) -> Callable[[CitedStatement], int]:
    """A scorer: how strongly a fact relates to the question (stem overlap + intent aliases).

    Shared by :func:`relevant_facts` (what the analyst is shown) and :func:`model_evidence`
    (relevance ordering of the full sheet for the model prompt) so the two never drift.
    """
    qstems = _stems(question)
    qwords = _WORD_RE.findall(question.lower())
    alias_subs: set[str] = set()
    for key, subs in _INTENT_ALIAS.items():
        if any(word.startswith(key) for word in qwords):
            alias_subs.update(subs)

    def overlap(fact: CitedStatement) -> int:
        text = fact.text.lower()
        return len(qstems & _stems(fact.text)) + sum(sub in text for sub in alias_subs)

    return overlap


def relevant_facts(
    facts: tuple[CitedStatement, ...], question: str, limit: int = _MAX_FACTS
) -> tuple[CitedStatement, ...]:
    """The facts most related to the question — the frame fact always leads, then the facts
    whose stems overlap the (alias-expanded) question, ranked by overlap.

    Only genuinely matching facts follow the frame: a focused question yields a focused
    selection that varies with what was asked. A vague question (no overlap at all) falls
    back to a small headline overview rather than the whole sheet — padding every result
    back up to the cap is what made the answers look identical regardless of the question.
    """
    if not facts:
        return ()
    overlap = _question_overlap(question)
    ranked = sorted(facts[1:], key=lambda f: -overlap(f))
    matched = [f for f in ranked if overlap(f) > 0]
    keep = [facts[0]]
    if matched:
        keep += matched[: limit - 1]
    else:  # nothing matched: a bounded headline overview, never the whole sheet
        keep += ranked[: min(limit - 1, _OVERVIEW_FACTS)]
    return tuple(keep)


def model_evidence(
    facts: tuple[CitedStatement, ...], question: str, limit: int = _MODEL_MAX_FACTS
) -> tuple[CitedStatement, ...]:
    """The evidence a LIVE local model is given: the whole cited picture, frame first, then
    every other fact ordered by relevance to the question.

    Distinct from :func:`relevant_facts` (which trims to what the analyst is *shown*): a real
    model answers best with the complete computed context, so it can connect the question to
    the wider schedule (drivers, float, forecasts, findings) instead of a narrow slice. Runs
    locally, so a fuller prompt has no external cost.
    """
    if not facts:
        return ()
    overlap = _question_overlap(question)
    ranked = sorted(facts[1:], key=lambda f: -overlap(f))
    return tuple([facts[0], *ranked])[:limit]


def figure_agreement(primary: str, second: str) -> str:
    """The dual-model cross-check note: do the two answers cite the same figures?

    Deterministic (engine-computed, never a third model): the numeric figures of each
    answer are compared as multisets. Agreement is corroboration, not proof — the cited
    facts remain the ground truth either way.
    """
    a, b = Counter(_FIGURE_RE.findall(primary)), Counter(_FIGURE_RE.findall(second))
    if a == b:
        return "Cross-check: both models cite identical figures."
    parts = []
    only_a = sorted((a - b).elements())
    only_b = sorted((b - a).elements())
    if only_a:
        parts.append("only the primary cites " + ", ".join(only_a[:8]))
    if only_b:
        parts.append("only the second cites " + ", ".join(only_b[:8]))
    return (
        "Cross-check: the two answers DIFFER on figures ("
        + "; ".join(parts)
        + ") — verify against the cited facts."
    )


_ANNOTATE_NOTE = (
    "\n\n[AI-derived figures — produced by the local model, not computed by the engine; "
    "verify against the cited facts above: {figs}]"
)


def _annotate_unsourced(text: str, allowed: set[str]) -> str:
    """Flag every figure in ``text`` the engine did not compute (the C2 fix; ADR-0129).

    Annotate, do not discard: the rich analysis is kept, but a footer enumerates each figure the
    model derived itself (any token not in ``allowed``, the figures across the cited facts), so an
    analyst can never mistake an AI-derived number for an engine figure. Order-preserving and
    de-duplicated; returns ``text`` unchanged when every figure is already sourced.
    """
    derived = [fig for fig in dict.fromkeys(_FIGURE_RE.findall(text)) if fig not in allowed]
    if not derived:
        return text
    return text + _ANNOTATE_NOTE.format(figs=", ".join(derived))


def answer_question(
    backend: AIBackend,
    facts: tuple[CitedStatement, ...],
    question: str,
    *,
    mode: str = "strict",
) -> tuple[str | None, tuple[CitedStatement, ...]]:
    """(model answer or ``None``, the cited facts used). Fail-closed; mode-gated.

    The Null backend (or an empty/failed generation) answers with no prose — the caller
    shows the facts themselves. The operator chooses the mode (AI Settings); the figure
    guarantee depends on it (ADR-0129):

    * **strict** — a model answer survives only if every number it contains appears in the
      fact sheet (subset gate; discarded wholesale otherwise). No unsourced figure can reach
      the analyst.
    * **annotate** (default) — the model may derive figures from the facts (differences,
      ratios, plain-language analysis), but any figure NOT in the cited facts is flagged in a
      footer as AI-derived, so a derived number can never be mistaken for an engine figure.
    * **interpretive** — the model's text is returned verbatim, ungated; the operator opts
      into raw model analysis and the "AI can err — verify against the citations" disclaimer
      rides every answer. (This mode does NOT guarantee sourced figures.)
    """
    shown = relevant_facts(facts, question)
    if backend.name == "null":
        return None, shown
    if mode in ("interpretive", "annotate"):
        # A live local model gets the WHOLE cited picture (free analysis, still grounded) —
        # not just the slice shown to the analyst — so it can reason across the schedule.
        evidence = model_evidence(facts, question)
        prompt = (
            "You are a senior forensic schedule analyst. The cited facts below are computed "
            "by the scheduling engine from the project and are your ONLY evidence. Give the "
            "analyst the most useful, accurate analysis you can of their question:\n"
            "- Answer the question directly and specifically first.\n"
            "- You MAY compute differences, ratios, rates and trends FROM these facts and "
            "explain what they imply for the schedule — what is driving the slip, where the "
            "risk is, and how healthy the logic, float and progress are.\n"
            "- Where the facts support it, name the risks and suggest concrete recovery "
            "actions.\n"
            "- Never state data the facts do not contain; if they are silent on something, "
            "say so plainly.\n"
            "Write in clear, well-structured plain English.\n\nFACTS:\n"
            + "\n".join(f"- {f.text}" for f in evidence)
            + f"\n\nQUESTION: {question}\nANSWER:"
        )
    else:
        # Strict mode stays narrow and exact: the model sees only the shown facts and any
        # figure it emits that is not in them discards the whole answer.
        evidence = shown
        prompt = (
            "You are a forensic schedule analyst. Answer the question using ONLY the facts "
            "below. Quote figures exactly as written; if the facts do not contain the answer, "
            "say that they do not.\n\nFACTS:\n"
            + "\n".join(f"- {f.text}" for f in evidence)
            + f"\n\nQUESTION: {question}\nANSWER:"
        )
    try:
        text = backend.generate(prompt).strip()
    except Exception:
        return None, shown
    if not text:
        return None, shown
    allowed: set[str] = set()
    for f in evidence:
        allowed.update(_FIGURE_RE.findall(f.text))
    if mode == "strict":
        if set(_FIGURE_RE.findall(text)) - allowed:
            return None, shown  # the model introduced a number the engine never computed
    elif mode == "annotate":
        text = _annotate_unsourced(text, allowed)  # keep the answer; flag derived figures
    return text, shown
