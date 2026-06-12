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
    backend: AIBackend,
    facts: tuple[CitedStatement, ...],
    question: str,
    *,
    mode: str = "strict",
) -> tuple[str | None, tuple[CitedStatement, ...]]:
    """(model answer or ``None``, the cited facts used). Fail-closed; mode-gated.

    The Null backend (or an empty/failed generation) answers with no prose — the caller
    shows the facts themselves. In **strict** mode a model answer survives only if every
    number it contains appears in the fact sheet (subset gate; discarded wholesale
    otherwise). In **interpretive** mode the model may derive figures from the facts
    (differences, ratios, plain-language analysis) — the caller must show the cited
    facts alongside and the standing "AI can err" disclaimer.
    """
    chosen = relevant_facts(facts, question)
    if backend.name == "null":
        return None, chosen
    if mode == "interpretive":
        prompt = (
            "You are a forensic schedule analyst. The cited facts below are your only "
            "evidence. Answer the question in plain language: you may compute "
            "differences, ratios, and interpretations FROM these facts and explain "
            "their implications, but never contradict them or claim data they do not "
            "contain — say so when the facts are silent. Be concise.\n\nFACTS:\n"
            + "\n".join(f"- {f.text}" for f in chosen)
            + f"\n\nQUESTION: {question}\nANSWER:"
        )
    else:
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
    if mode != "interpretive":
        allowed = set()
        for f in chosen:
            allowed.update(_FIGURE_RE.findall(f.text))
        if set(_FIGURE_RE.findall(text)) - allowed:
            return None, chosen  # the model introduced a number the engine never computed
    return text, chosen
