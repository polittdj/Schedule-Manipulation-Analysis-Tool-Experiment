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


def _statement(finding: Finding) -> CitedStatement:
    text = f"[{finding.severity}/{finding.category}] {finding.title}. {finding.course_of_action}"
    return CitedStatement(text=text, citations=finding.citations)


def _clean_bill(schedule: Schedule, cpm: CPMResult) -> CitedStatement:
    """A cited 'no issues found' statement for a well-formed schedule (cites the finish driver)."""
    tasks = schedule.tasks_by_id
    drivers = tuple(
        Citation(schedule.source_file, uid, tasks[uid].name)
        for uid, t in cpm.timings.items()
        if t.early_finish == cpm.project_finish and uid in tasks
    )
    return CitedStatement(
        text="No DCMA, compliance, or manipulation findings were raised; the schedule is "
        "well-formed. The cited activities control the project finish.",
        citations=drivers,
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
    # the model rephrases the prose; citations are re-attached from the engine and re-verified
    polished = tuple(be.generate(s.text) for s in sources)
    statements = reattach(polished, sources)

    title = f"Schedule forensic narrative — {current.name}"
    if prior is not None:
        title += f" ({prior.source_file or 'prior'} → {current.source_file or 'current'})"
    return Narrative(title=title, statements=statements)
