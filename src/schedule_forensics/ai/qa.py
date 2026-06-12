"""Ask-the-AI — grounded question answering over the schedule's computed facts (§6.D).

The analyst types a question; the answer comes from a **fact sheet the engine computed**
(frame dates, DCMA verdicts, findings, float bands, completion performance, forecasts,
driving path) — every fact a :class:`CitedStatement`. The selected local backend may
*phrase* an answer, but it is gated hard: any numeric figure in the model's answer that
does not appear in the fact sheet **discards the whole answer** (the cited facts are shown
instead — Law 2: the tool never presents an invented number). With the offline Null
backend there is no generation at all: the facts matching the question are returned
verbatim. Everything runs locally; the question and the data never leave the machine.
"""

from __future__ import annotations

import re

from schedule_forensics.ai.backend import AIBackend
from schedule_forensics.ai.citations import _FIGURE_RE, CitedStatement
from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation, ScheduleAudit
from schedule_forensics.engine.forecast import ForecastSet
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.model.schedule import Schedule

#: Most facts to feed the model / return for a question (keeps prompts small and local).
_MAX_FACTS = 12

_WORD_RE = re.compile(r"[a-z0-9]{3,}")
#: Question words that carry no selection signal.
_STOPWORDS = frozenset(
    "the and for are was were will what when where which who why how does did with this "  # noqa: SIM905
    "that have has been being can could should would much many tell show give about than "
    "schedule project activity activities task tasks".split()
)


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
    drivers = tuple(
        Citation(label, uid, by_id[uid].name)
        for uid, t in sorted(cpm.timings.items())
        if t.early_finish == cpm.project_finish and uid in by_id
    ) or tuple(Citation(label, t.unique_id, t.name) for t in schedule.tasks[:3])

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


def relevant_facts(
    facts: tuple[CitedStatement, ...], question: str, limit: int = _MAX_FACTS
) -> tuple[CitedStatement, ...]:
    """The facts most related to the question (term overlap; the frame fact always leads)."""
    terms = {w for w in _WORD_RE.findall(question.lower()) if w not in _STOPWORDS}
    scored = sorted(
        (fact for fact in facts[1:]),
        key=lambda fact: -len(terms & set(_WORD_RE.findall(fact.text.lower()))),
    )
    keep = [facts[0]] if facts else []
    keep += [f for f in scored if terms & set(_WORD_RE.findall(f.text.lower()))][: limit - 1]
    if len(keep) < min(limit, len(facts)):  # vague question: pad with the leading facts
        keep += [f for f in facts if f not in keep][: limit - len(keep)]
    return tuple(keep)


def answer_question(
    backend: AIBackend, facts: tuple[CitedStatement, ...], question: str
) -> tuple[str | None, tuple[CitedStatement, ...]]:
    """(model answer or ``None``, the cited facts used). Fail-closed and figure-gated.

    The Null backend (or an empty/failed generation) answers with no prose — the caller
    shows the facts themselves. A model answer survives only if **every number it contains
    appears in the fact sheet** (subset gate); otherwise it is discarded wholesale.
    """
    chosen = relevant_facts(facts, question)
    if backend.name == "null":
        return None, chosen
    prompt = (
        "You are a forensic schedule analyst. Answer the question using ONLY the facts "
        "below. Quote figures exactly as written; if the facts do not contain the answer, "
        "say that they do not.\n\nFACTS:\n"
        + "\n".join(f"- {f.text}" for f in chosen)
        + f"\n\nQUESTION: {question}\nANSWER:"
    )
    try:
        text = backend.generate(prompt).strip()
    except Exception:
        return None, chosen
    if not text:
        return None, chosen
    allowed = set()
    for f in chosen:
        allowed.update(_FIGURE_RE.findall(f.text))
    if set(_FIGURE_RE.findall(text)) - allowed:
        return None, chosen  # the model introduced a number the engine never computed
    return text, chosen
