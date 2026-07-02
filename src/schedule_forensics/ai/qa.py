"""Ask-the-AI — grounded question answering over the schedule's computed facts (§6.D).

The analyst types a question; the answer is grounded in a **fact sheet the engine
computed** (frame dates, DCMA verdicts, findings, float bands, completion performance,
forecasts, driving path) — every fact a :class:`CitedStatement`. Three answering modes
(operator-selectable in AI Settings, M18 "AI at full power"; ADR-0129):

* **annotate** (the default): the model may compute differences/ratios from the facts and
  explain implications, but any figure NOT in the cited facts is flagged in an
  ``[AI-derived …]`` footer (``_annotate_unsourced``) — the answer is kept, yet a derived
  number can never be mistaken for an engine figure.
* **strict**: any numeric figure in the model's answer that does not appear in the fact
  sheet **discards the whole answer** (the cited facts are shown instead — the tool
  presents no number the engine did not compute).
* **interpretive**: the model's text is returned verbatim and is **not** figure-gated — the
  operator opts into raw analysis; the standing *"AI can err — verify against citations"*
  disclaimer rides every answer and the cited facts are always shown alongside.

**Role-aware figure gate (audit F-11, ADR-0137; hardened ADR-0138).** The strict/annotate gate
distinguishes a figure that appears in the facts as a real engine **value** from one that appears
**only** as an activity **name** or **UID** (e.g. a finding "… drive the path to 'Milestone 2099'
(UID 6077)"). A digit matching only such an identifier — never a value — is one the model has
re-used in another role (a name-digit ``2099`` as a finish year, a UID ``6077`` as a count):
**strict discards** that answer and **annotate flags** it. The split is collision-safe: a digit
that is *both* a value and an identifier counts as a value, so real figures are never discarded.
The ADR-0138 hardening (QC audit 2026-07-01): identifier extraction is **span-based** (an empty or
digit-bearing task name can no longer shred the value set — D6); ISO dates are **whole tokens**
(their fragments can never become derivation operands — D1); the identifier check runs **before**
the Layer-B derivation check (a re-roled UID can never launder through a coincidental
reconstruction — D4); and an identifier written *as* an identifier — a ``UID n`` reference or a
quoted cited activity name — is correct role usage and passes, so strict no longer discards a
faithful driving-path answer (D15). The **unit-role step (ADR-0145)** adds the first semantic
check: a value written with an EXPLICIT unit that contradicts every unit the facts state it with
(a "5%"-only figure re-used as "5 days") is discarded (strict) / flagged (annotate); bare usages
and multi-unit tokens are never touched (collision-safe). **Interpretive mode stays ungated by
design** (raw model output, opt-in). A fuller semantic role model remains future work.

With the offline Null backend there is no generation at all: the facts matching the
question are returned verbatim. :func:`build_workbook_fact_sheet` extends the same
contract across every loaded version (multi-version pages). Everything runs locally;
the question and the data never leave the machine.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable

from schedule_forensics.ai.backend import AIBackend
from schedule_forensics.ai.citations import _TOKEN_RE, CitedStatement, figure_tokens
from schedule_forensics.ai.derivation import RATIO_KINDS, Derivation, verify_derivation
from schedule_forensics.engine.cpm import CPMResult, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation, ScheduleAudit
from schedule_forensics.engine.forecast import ForecastSet, compute_finish_forecasts
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.engine.metrics.derived import dcma_pass_rate, population_share
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
        # Derived (Layer A): the finish-driving share as a sourced percentage, so the analyst (and a
        # live model) gets "N of M = X%" already computed and cited rather than deriving it ad hoc.
        driving_share = population_share(len(finish_driving), len(tasks))
        if driving_share is not None:
            facts.append(
                CitedStatement(
                    f"Derived — finish-driving concentration: {driving_share}% of the network "
                    f"({len(finish_driving)} of {len(tasks)} activities) sits at zero float to the "
                    "project end.",
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
    # Derived (Layer A): the DCMA 14-point pass rate over the APPLICABLE checks (n/a excluded),
    # a cited headline health figure computed from the audit's own pass/fail tally.
    pass_rate = dcma_pass_rate(audit.passed, audit.failed)
    if pass_rate is not None:
        applicable = audit.passed + audit.failed
        fail_cites = tuple(c for chk in audit.failed_checks for c in chk.citations[:1])[:5]
        facts.append(
            CitedStatement(
                f"Derived — DCMA 14-point assessment: {audit.passed} of {applicable} applicable "
                f"checks pass ({pass_rate}% pass rate); {audit.not_applicable} not applicable.",
                fail_cites or drivers,
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


def _strip_gate_footers(text: str) -> str:
    """The model's own prose, without any tool-appended gate footer (``\\n\\n[…]`` blocks).

    The cross-check must compare what the MODELS said — a footer's arithmetic operands are the
    tool's, and counting them fabricated "the answers DIFFER" verdicts on agreeing answers
    (QC audit D16)."""
    return text.split("\n\n[", 1)[0]


def figure_agreement(primary: str, second: str) -> str:
    """The dual-model cross-check note: do the two answers cite the same figures?

    Deterministic (engine-computed, never a third model): the numeric figures of each
    answer — footers stripped, dates as whole tokens — are compared as multisets.
    Agreement is corroboration, not proof — the cited facts remain the ground truth
    either way.
    """
    a = Counter(figure_tokens(_strip_gate_footers(primary)))
    b = Counter(figure_tokens(_strip_gate_footers(second)))
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
#: Layer B (ADR-0135): figures NOT literally in the facts but RECONSTRUCTED from sourced figures by
#: a standard operation are shown with their reconstruction — a verified derivation, not invented.
_DERIVED_NOTE = (
    "\n\n[Derived figures — recomputed by the tool from the cited facts via a standard operation "
    "(confirm each relationship is meaningful): {exprs}]"
)


#: Unit-role step (ADR-0145): a cited value re-used with an explicitly DIFFERENT unit than the
#: engine stated (a percentage re-written as days, a count re-written as a percentage).
_UNIT_NOTE = (
    "\n\n[Figures re-used with a different unit than the engine stated — confirm the unit, not "
    "just the number: {figs}]"
)


#: Role-aware gate (ADR-0137, audit F-11): figures that match ONLY an activity name / UID in the
#: facts (never a real engine value) are identifiers the model has re-used in another role.
_ROLE_NOTE = (
    "\n\n[Figures matching an activity name or ID, not an engine value — confirm the role, not "
    "just the number: {figs}]"
)


def _sourced_floats(allowed: set[str]) -> list[float]:
    out: list[float] = []
    for tok in sorted(allowed):  # deterministic operand order (sets are unordered)
        try:
            out.append(float(tok))
        except ValueError:  # whole-date tokens are evidence, never arithmetic operands
            continue
    return out


def _boundary_pattern(literal: str) -> str:
    """``literal`` escaped for regex, digit-boundary-guarded when it starts/ends with a digit —
    so a task named "5" matches the standalone 5, never the 5 inside 45 (QC audit D6)."""
    pattern = re.escape(literal)
    if literal[0].isdigit() or literal[0] == "-":
        pattern = r"(?<![\d.-])" + pattern
    if literal[-1].isdigit():
        pattern = pattern + r"(?![\d.])"
    return pattern


def _identifier_spans(
    text: str, names: Iterable[str], uids: Iterable[int]
) -> list[tuple[int, int]]:
    """Character spans of ``text`` occupied by a cited activity name or a ``UID n`` reference.

    Span-based (never ``str.replace``): an empty name contributes no span instead of shredding the
    text character-by-character, and digit-boundary guards keep a numeric name from swallowing
    digits inside adjacent numbers (QC audit D6).
    """
    spans: list[tuple[int, int]] = []
    for name in names:
        if not name:
            continue
        spans += [m.span() for m in re.finditer(_boundary_pattern(name), text)]
    for uid in uids:
        spans += [m.span() for m in re.finditer(rf"\bUID\s+{re.escape(str(uid))}(?![\d.])", text)]
    return spans


def _inside(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(start <= span[0] and span[1] <= end for start, end in spans)


#: Explicit unit context right after a figure (ADR-0145 unit-role step). Only UNAMBIGUOUS
#: markers count: "%"/"percent" vs a plain count/duration unit word. A bare figure ("... is 5.")
#: carries no unit information and is never role-checked — conservative by design.
_PCT_UNIT_RE = re.compile(r"\s?(?:%|percent\b)", re.IGNORECASE)
_PLAIN_UNIT_RE = re.compile(
    r"\s(?:working\s+)?(?:days?|activities|tasks|minutes|hours|links|relationships)\b",
    re.IGNORECASE,
)


def _unit_role(text: str, end: int) -> str | None:
    """The explicit unit attached to the figure ending at ``end``: "pct", "plain", or None."""
    tail = text[end : end + 16]
    if _PCT_UNIT_RE.match(tail):
        return "pct"
    if _PLAIN_UNIT_RE.match(tail):
        return "plain"
    return None


def _figure_roles(
    evidence: Iterable[CitedStatement],
) -> tuple[set[str], set[str], set[str], dict[str, set[str]]]:
    """``(value_figures, identifier_figures, identifier_names)`` across the evidence facts
    (audit F-11 role split, hardened per QC audit D1/D6).

    A **value** figure is a token that appears in a fact's text *outside* every cited activity-name
    / ``UID n`` span — a real engine value (count, %, duration). ISO dates are single whole tokens
    (never year/month/day fragments). An **identifier** figure is one carried by a citation's task
    name or unique id. A digit that is *both* is a value (not role-suspect); only a digit appearing
    **exclusively** as an identifier is treated as one — the collision-safety that keeps a UID ``5``
    from discarding a genuine count ``5``. ``identifier_names`` are the non-empty cited task names,
    used to recognise a name *quoted* in an answer as identifier-role usage. ``unit_roles`` maps a
    value token to the EXPLICIT unit contexts the facts state it in ("pct" / "plain") — the
    ADR-0145 unit-role step; tokens the facts only ever use bare carry no entry (never checked).
    """
    value_figs: set[str] = set()
    id_figs: set[str] = set()
    id_names: set[str] = set()
    unit_roles: dict[str, set[str]] = {}
    for f in evidence:
        names = [c.task_name for c in f.citations if c.task_name]
        uids = [c.unique_id for c in f.citations]
        id_names.update(names)
        for name in names:
            id_figs.update(figure_tokens(name))
        id_figs.update(str(uid) for uid in uids)
        spans = _identifier_spans(f.text, names, uids)
        for m in _TOKEN_RE.finditer(f.text):
            if not _inside(m.span(), spans):
                value_figs.add(m.group())
                role = _unit_role(f.text, m.end())
                if role is not None:  # record only EXPLICIT unit contexts (ADR-0145)
                    unit_roles.setdefault(m.group(), set()).add(role)
    return value_figs, id_figs, id_names, unit_roles


#: Most distinct non-value figures per answer given a Layer-B reconstruction attempt; the rest are
#: flagged unverified (fail-closed). Bounds the gate's cost on a pathological answer (QC audit D23).
_MAX_GATED_FIGURES = 24


def _classify_figures(
    text: str,
    value_figs: set[str],
    id_figs: set[str],
    id_names: set[str],
    unit_roles: dict[str, set[str]] | None = None,
) -> tuple[list[Derivation], list[str], list[str], list[str]]:
    """Split the answer's figures into VERIFIED derivations (reconstructed from the cited *values*
    by a standard operation — Layer B), IDENTIFIER-reused figures (an identifier digit used as a
    value — F-11 role gate), and UNVERIFIED figures (neither). A figure literally present as a
    value is none of these; a figure written *as* an identifier (inside a ``UID n`` reference or a
    quoted cited activity name) is correct identifier-role usage and passes.

    Priority per occurrence: value → identifier-role usage → **identifier-only (checked BEFORE
    derivation, so a re-roled UID can never launder through a coincidental reconstruction — QC
    audit D4)** → verified derivation → unverified. A token is flagged if ANY occurrence misuses
    it; deduped in first-occurrence order.

    The fourth return, ``unit_misused`` (ADR-0145), is the unit-role step of the F-11 semantic
    half: a VALUE token written with an EXPLICIT unit that contradicts every unit the facts state
    it with (a "5%"-only figure re-used as "5 days", or a plain count re-used as a percentage).
    Both sides must be explicit and disjoint — a bare usage, a bare fact, or a token the facts use
    in both unit contexts is never flagged (collision-safe, like the identifier split).
    """
    sourced = _sourced_floats(value_figs)
    identifier_only = id_figs - value_figs
    ref_spans = _identifier_spans(text, id_names, [])
    ref_spans += [m.span() for m in re.finditer(r"\bUID\s+-?\d+(?![\d.])", text)]
    verified: list[Derivation] = []
    id_reused: list[str] = []
    unverified: list[str] = []
    unit_misused: list[str] = []
    handled: set[str] = set()
    gated = 0
    for m in _TOKEN_RE.finditer(text):
        fig = m.group()
        if fig in value_figs:
            fact_units = (unit_roles or {}).get(fig)
            if fact_units:
                usage = _unit_role(text, m.end())
                if usage is not None and usage not in fact_units and fig not in unit_misused:
                    unit_misused.append(fig)  # explicit unit contradicts every cited unit
            continue
        if fig in handled:
            continue
        if _inside(m.span(), ref_spans):
            # written as an identifier (a "UID n" reference / a quoted cited name): correct role
            # when it IS a cited identifier; an invented reference is unverified (fail closed).
            if fig in id_figs:
                continue
            handled.add(fig)
            unverified.append(fig)
            continue
        handled.add(fig)
        if fig in identifier_only:  # BEFORE derivation — never launder a re-roled identifier (D4)
            id_reused.append(fig)
            continue
        gated += 1
        derivation = verify_derivation(fig, sourced) if gated <= _MAX_GATED_FIGURES else None
        if derivation is not None:
            verified.append(derivation)
        else:
            unverified.append(fig)
    return verified, id_reused, unverified, unit_misused


def _annotate_unsourced(
    text: str,
    value_figs: set[str],
    id_figs: set[str],
    id_names: set[str],
    unit_roles: dict[str, set[str]] | None = None,
) -> str:
    """Annotate the non-value figures (C2 fix, ADR-0129; verify-or-flag, ADR-0135; role gate,
    ADR-0137; hardened ADR-0138).

    Annotate, do not discard: the rich analysis is kept. A figure the engine did not state as a
    value is either **verified-derived** (reconstructed from the cited values, with arithmetic),
    an **identifier reused as a figure** (matches only a name/UID — flagged for role, F-11),
    or **unverified** (flagged AI-derived). So a derived number can never be mistaken for an engine
    figure, and a name/UID digit re-used in another role is called out. Returns ``text`` unchanged
    when every figure is already a cited value or a correct identifier reference.
    """
    verified, id_reused, unverified, unit_misused = _classify_figures(
        text, value_figs, id_figs, id_names, unit_roles
    )
    out = text
    if verified:
        out += _DERIVED_NOTE.format(exprs="; ".join(d.expression for d in verified))
    if id_reused:
        out += _ROLE_NOTE.format(figs=", ".join(id_reused))
    if unit_misused:
        out += _UNIT_NOTE.format(figs=", ".join(unit_misused))
    if unverified:
        out += _ANNOTATE_NOTE.format(figs=", ".join(unverified))
    return out


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

    * **strict** — a model answer survives only if every number it contains is a cited engine
      **value**, a correct **identifier reference** (a ``UID n`` / quoted cited activity name —
      ADR-0138), **or a ratio-class reconstruction** of cited values (Layer B, ADR-0135 — a
      standard rate recomputed by the tool, shown with its arithmetic; integer targets must
      reconstruct **exactly**). An invented figure, an additive-only reconstruction, **or a figure
      matching only an activity name/UID used as a value** (a re-roled identifier — F-11 role gate,
      checked BEFORE the derivation gate so it can never launder through one) discards the answer
      wholesale. No invented or re-roled number reaches the analyst.
    * **annotate** (default) — the model may derive figures from the facts; a figure not stated as a
      value is shown as a **verified derivation** (reconstructed, Layer B), flagged as an
      **identifier reused as a figure** (matches only a name/UID — F-11), or flagged **AI-derived**
      (no reconstruction) — so a derived number can never be mistaken for an engine figure.
    * **interpretive** — the model's text is returned verbatim, ungated; the operator opts
      into raw model analysis and the "AI can err — verify against the citations" disclaimer
      rides every answer. (This mode does NOT guarantee sourced figures.)

    The strict/annotate gate is **role-aware** (audit F-11; hardened ADR-0138): it splits a figure
    that appears as an engine value from one that appears only as an activity name/UID, and the
    latter — when used *as a value* — is discarded (strict) or flagged (annotate). See the module
    docstring for the span/date/priority hardening.
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
    value_figs, id_figs, id_names, unit_roles = _figure_roles(evidence)
    if mode == "strict":
        verified, id_reused, unverified, unit_misused = _classify_figures(
            text, value_figs, id_figs, id_names, unit_roles
        )
        # strict trusts a figure only if it is a cited VALUE or a RATIO-class reconstruction of
        # cited values (a standard rate — far less coincidence-prone than an integer difference;
        # Layer B, ADR-0135). An unverified figure, an additive-only reconstruction, OR an
        # identifier reused as a figure (matches only a name/UID — F-11 role gate) discards the
        # whole answer (the caller shows the cited facts instead).
        if (
            unverified
            or id_reused
            or unit_misused  # an explicit-unit contradiction (ADR-0145) is a re-roled figure
            or any(d.kind not in RATIO_KINDS for d in verified)
        ):
            return None, shown
        if verified:  # all ratio-class — accept, but show how each was recomputed
            text += _DERIVED_NOTE.format(exprs="; ".join(d.expression for d in verified))
    elif mode == "annotate":
        # keep the answer; verify/role/flag its figures
        text = _annotate_unsourced(text, value_figs, id_figs, id_names, unit_roles)
    return text, shown
