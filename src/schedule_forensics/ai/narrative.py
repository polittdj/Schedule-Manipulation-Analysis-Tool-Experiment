"""Cited forensic narrative — the "generate a story" layer (§6.D), built on cited findings.

Assembles the analyst story from the deterministic, already-cited engine signals — the
risk/opportunity/concern recommendations (:func:`recommend`), the manipulation-trend
detector (:func:`detect_manipulation`), and the CPM/progress trend — as
:class:`CitedStatement`s. An :class:`AIBackend` may *rephrase* each statement's prose
(:meth:`generate`); citations come only from the engine and are re-attached and re-verified
(:func:`reattach`), so the model can polish wording but can never drop a citation or invent
a fact. With the default :class:`NullBackend` the cited findings are emitted verbatim.
"""

from __future__ import annotations

from schedule_forensics.ai.backend import AIBackend
from schedule_forensics.ai.citations import CitedStatement, Narrative, reattach
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.recommendations import Finding, recommend
from schedule_forensics.model.schedule import Schedule

#: The rephrase instruction a LIVE local model receives per statement. The bare engine sentence
#: used to be sent as the whole prompt, so completion models CONTINUED it instead of rephrasing —
#: nearly every generation failed preserves_figures and burned gen_timeout for nothing (QC audit
#: D17). The reattach gate still verifies figures + loaded terms on whatever comes back.
_POLISH_PROMPT = (
    "Rewrite the forensic schedule statement below in clearer, more fluent analyst prose. "
    "Keep EVERY number, date, and percentage exactly as written; do not add, drop, or alter any "
    "figure; do not add accusations or conclusions. Reply with the rewritten sentence only.\n\n"
    "STATEMENT: {text}\nREWRITE:"
)


def polish_prompt(text: str) -> str:
    """The instruction-wrapped rephrase prompt for one engine statement (QC audit D17)."""
    return _POLISH_PROMPT.format(text=text)


def clean_polish(candidate: str) -> str:
    """A model reply normalized for :func:`reattach`: leading "REWRITE:" stripped; a reply that
    echoes the prompt scaffolding returns "" so reattach falls back to the verbatim engine
    sentence (empty is never accepted — fail closed)."""
    out = candidate.strip()
    if out.upper().startswith("REWRITE:"):
        out = out[len("REWRITE:") :].strip()
    if "STATEMENT:" in out or "REWRITE:" in out:
        return ""  # prompt echo — force the verbatim fallback
    return out


def _statement(finding: Finding) -> CitedStatement:
    text = f"[{finding.severity}/{finding.category}] {finding.title}. {finding.course_of_action}"
    return CitedStatement(text=text, citations=finding.citations)


def _clean_bill(schedule: Schedule, cpm: CPMResult) -> CitedStatement:
    """A cited 'no issues found' statement for a well-formed schedule (cites the finish driver).

    A summary-only file has no finish drivers at all — the first task rows are the
    terminal citation anchor (§6: a statement can never be uncited).
    """
    tasks = schedule.tasks_by_id
    drivers = tuple(
        Citation(schedule.source_file, uid, tasks[uid].name)
        for uid, t in cpm.timings.items()
        if t.early_finish == cpm.project_finish and uid in tasks
    )
    if drivers:
        return CitedStatement(
            text="No DCMA, compliance, or manipulation findings were raised; the schedule is "
            "well-formed. The cited activities control the project finish.",
            citations=drivers,
        )
    rows = tuple(Citation(schedule.source_file, t.unique_id, t.name) for t in schedule.tasks[:3])
    if rows:
        return CitedStatement(
            text="No DCMA, compliance, or manipulation findings were raised. No schedulable "
            "activities were found (summary rows only) — the cited rows are the file's contents.",
            citations=rows,
        )
    # an empty scope (e.g. a session filter that matched nothing) has no rows to cite — anchor on
    # the file itself so the statement is never uncited (§6: a statement can never be uncited).
    return CitedStatement(
        text="No DCMA, compliance, or manipulation findings were raised. No activities are in "
        "scope (a filter or selection matched nothing) — the citation is the file itself.",
        citations=(Citation(schedule.source_file, 0, schedule.name),),
    )


def build_narrative(
    current: Schedule,
    prior: Schedule | None = None,
    *,
    target_uid: int | None = None,
    backend: AIBackend | None = None,
    current_cpm: CPMResult | None = None,
    prior_cpm: CPMResult | None = None,
) -> Narrative:
    """Build the cited forensic narrative for ``current`` (vs ``prior`` if given).

    ``backend`` rephrases the prose (default :class:`NullBackend` = verbatim). Every emitted
    statement is guaranteed to carry a citation (file + UID + task) — verified before return.
    """
    be: AIBackend = backend if backend is not None else NullBackend()
    cpm_cur = current_cpm if current_cpm is not None else compute_cpm(current)

    findings: list[Finding] = list(
        recommend(
            current,
            prior,
            current_cpm=cpm_cur,
            prior_cpm=prior_cpm,
            target_uid=target_uid,
        )
    )
    if prior is not None:
        findings.extend(
            detect_manipulation(current, prior, current_cpm=cpm_cur, prior_cpm=prior_cpm)
        )

    sources: tuple[CitedStatement, ...] = (
        tuple(_statement(f) for f in findings) if findings else (_clean_bill(current, cpm_cur),)
    )
    # a LIVE model rephrases the prose (instruction-wrapped, QC audit D17); the Null backend
    # skips generation entirely (its echo IS the verbatim text). Citations are re-attached from
    # the engine and re-verified either way.
    if be.name == "null":
        statements = sources
    else:
        polished = tuple(clean_polish(be.generate(polish_prompt(s.text))) for s in sources)
        statements = reattach(polished, sources)

    title = f"Schedule forensic narrative — {current.name}"
    if prior is not None:
        title += f" ({prior.source_file or 'prior'} → {current.source_file or 'current'})"
    return Narrative(title=title, statements=statements)
