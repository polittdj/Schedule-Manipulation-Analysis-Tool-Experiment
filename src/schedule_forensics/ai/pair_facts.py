"""Consecutive-pair comparative facts for Ask-the-AI — the whole workbook, two at a time.

**The defect this closes (operator report, 2026-08-18).** "In the Schedule Integrity page when
there are more than two schedules loaded the tool only does a comparative analysis of the last
two schedules when you Ask the AI a question." Measured on a synthetic 4-version workbook whose
manipulation sat in the FIRST two updates: the workbook fact sheet held **zero** manipulation
facts, neither shortened activity was named anywhere in the evidence, and the one statement on the
subject was *"No incomplete activity on the critical path had its duration shortened between
v03.mpp and v04.mpp"* — an affirmative negative, scoped to one pair, that reads as a workbook
verdict. Ask "across these 32 schedules, is there a pattern of manipulation?" and the honest answer
from that evidence is "no", because 30 of the 31 available comparisons were never made.

The population itself was already a fact (ADR-0392's :mod:`~schedule_forensics.ai.version_facts`),
and the S-curve and finish *series* spanned every version. What had no engine answer to cite was
the **diff** dimension: manipulation only exists between two snapshots, so a series of them has to
be walked pair by pair. :func:`~schedule_forensics.engine.pair_series.compute_pairwise_series`
walks it; this module states the result as cited facts.

Two facts are :attr:`~schedule_forensics.ai.citations.CitedStatement.pinned`, for the same reason
ADR-0392 pinned the population — a question phrased in none of their words must not be able to
rank the comparative frame out of the evidence:

1. **the comparison series** — every consecutive pair, oldest first, with that update's signal
   tally and what the computed finish did across it;
2. **the recurrence tally** — per signal type, in how many steps it fired, its longest unbroken
   run, and how many findings it accounts for. This is the arithmetic behind "pattern": one cut is
   an event, the same signal in 24 of 31 updates is a pattern. It states counts, never intent.

Behind them ride bounded per-step **detail** facts naming the activities involved. They are
allocated round-robin, oldest step first, so a workbook whose manipulation sits early is
represented before any single step gets a second entry — a "top N by severity" cut would have
re-created the newest-first bias this module exists to remove. When the bound truncates, the
statement says so; a truncation the reader cannot see is the defect class, not the fix.
"""

from __future__ import annotations

from schedule_forensics.ai.citations import CitedStatement
from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.pair_series import (
    PairStep,
    PairwiseSeries,
    compute_pairwise_series,
)
from schedule_forensics.engine.recommendations import Finding
from schedule_forensics.model.schedule import Schedule

#: Compact human label per manipulation ``metric_id``, for the series/recurrence tallies. The
#: findings' own titles carry counts ("3 incomplete activities had their duration shortened"),
#: which cannot be summed across steps without reading as a per-step figure, so the tallies use
#: these fixed phrases and the counts are the series'. ``tests/engine/test_pair_series.py``
#: computes the emitted ``MANIP_*`` id set from the engine source and fails if this table misses
#: one — a hand-maintained list of another module's constants goes stale silently.
_SIGNAL_LABELS: dict[str, str] = {
    "MANIP_DELETED_TASK": "task deleted from the critical path",
    "MANIP_DEACTIVATED_TASK": "task deactivated",
    "MANIP_DELETED_LOGIC": "logic link removed",
    "MANIP_ADDED_LOGIC": "logic link added",
    "MANIP_SHORTENED_DURATION": "duration shortened",
    "MANIP_CONSTRAINT_ADDED": "hard constraint added",
    "MANIP_CALENDAR_LOOSENED": "calendar loosened",
    "MANIP_BASELINE_CHANGE": "baseline date changed",
    "MANIP_ACTUAL_CHANGE": "actual date edited",
    "MANIP_ACTUAL_ERASED": "actual date erased",
    "MANIP_COST_CHANGE": "cost changed",
    "MANIP_ACTUAL_COST_ERASED": "actual cost erased",
    "MANIP_WORK_CHANGE": "work hours changed",
    "MANIP_ACTUAL_WORK_ERASED": "actual work erased",
    "MANIP_RESOURCE_CHANGE": "resource assignment edited",
}

#: Steps rendered in full inside the series fact before the middle is elided (and the elision
#: STATED). 31 monthly updates render comfortably; a multi-hundred-version portfolio would drown
#: the rest of the evidence. Mirrors ADR-0392's series elision, deliberately.
_STEPS_FULL_MAX = 60
_STEPS_EDGE = 20
#: Most per-step DETAIL facts emitted, across the whole series. Allocated round-robin oldest-first
#: (see the module docstring); truncation is stated in the series fact.
_MAX_DETAIL_FACTS = 12


def _signal_label(metric_id: str) -> str:
    """The compact phrase for a signal, falling back to the raw id so an unmapped NEW signal is
    still reported (degraded, visibly) rather than silently dropped from the tally."""
    return _SIGNAL_LABELS.get(metric_id, metric_id)


#: Cited activities named INSIDE a detail fact's text. The Ask prompt is assembled from each
#: fact's ``text`` alone — never ``rendered()`` — so an activity that lives only in the citation
#: tuple is invisible to the model, and "1 incomplete activities had their duration shortened"
#: reaches it with no way to say WHICH. Naming a bounded few in the text closes that for the
#: comparative facts without touching the figure gate's value/identifier split (which reads the
#: text and the citations separately).
_NAMED_ACTIVITIES = 4


def _named_activities(finding: Finding) -> str:
    """`` Activities: 'Excavate elevator pit' (UID 34), …`` — bounded, with the overflow stated."""
    cited = finding.citations[:_NAMED_ACTIVITIES]
    if not cited:
        return ""
    named = ", ".join(f"'{c.task_name}' (UID {c.unique_id})" for c in cited)
    extra = len(finding.citations) - len(cited)
    more = f" and {extra} further cited activity(ies)" if extra > 0 else ""
    return f" Activities: {named}{more}."


def _anchor(series: PairwiseSeries) -> tuple[Citation, ...]:
    """One citation per compared version — these facts are ABOUT the set of comparisons, so the
    files being compared are the anchor (UID 0 = the file, as the briefing's verify section uses).
    """
    seen: list[str] = []
    for step in series.steps:
        for label in (step.prior_label, step.current_label):
            if label not in seen:
                seen.append(label)
    return tuple(Citation(label, 0, label) for label in seen)


def _step_tally(step: PairStep) -> str:
    """``duration shortened x2, logic link removed x1`` — this step's signals, most-fired first."""
    counts: dict[str, int] = {}
    for finding in step.findings:
        label = _signal_label(finding.metric_id)
        counts[label] = counts.get(label, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ", ".join(f"{label} x{n}" for label, n in ordered)


def _render_step(step: PairStep) -> str:
    moved = step.finish_movement_days
    finish = f"computed finish {moved:+d}d" if moved is not None else "computed finish unreadable"
    if not step.findings:
        return f"step {step.index} {step.prior_label} to {step.current_label}: no signals, {finish}"
    return (
        f"step {step.index} {step.prior_label} to {step.current_label}: "
        f"{step.signals} signal(s) ({_step_tally(step)}), {finish}"
    )


def _elide(entries: list[str]) -> tuple[str, str]:
    """``(rendered series, elision note)`` — the whole series, or both edges plus a stated gap."""
    if len(entries) <= _STEPS_FULL_MAX:
        return "; ".join(entries), ""
    hidden = len(entries) - 2 * _STEPS_EDGE
    kept = entries[:_STEPS_EDGE] + entries[-_STEPS_EDGE:]
    return (
        "; ".join(kept),
        f" (the {hidden} step(s) between the oldest {_STEPS_EDGE} and the newest {_STEPS_EDGE} "
        "are omitted from this line for length; they WERE compared and are counted in the "
        "recurrence tally below)",
    )


def _series_fact(
    series: PairwiseSeries, cite: tuple[Citation, ...], truncated: int
) -> CitedStatement:
    entries = [_render_step(s) for s in series.steps]
    rendered, note = _elide(entries)
    n_steps = len(series.steps)
    # NEVER n_steps + 1: an uncomparable pair drops a step without dropping the versions, and
    # deriving the count made a 4-version workbook with one unsolvable file say "all 2 loaded
    # version(s) were compared" — the exact class of misstatement this module exists to close.
    n_versions = series.versions
    skipped = ""
    completeness = (
        "so this is the complete set of comparisons available in this workbook; every update is "
        "here, not just the newest pair"
    )
    if series.uncomparable:
        completeness = (
            "so a comparison exists only where both sides solve; this is every comparison that "
            "COULD be made, which is not every update in the workbook"
        )
        skipped = (
            f" {len(series.uncomparable)} adjacent pair(s) could NOT be compared because a "
            f"version's network does not solve — {', '.join(series.uncomparable)}. Those are "
            "unmeasured, NOT signal-free."
        )
    detail = ""
    if truncated:
        detail = (
            f" Per-activity detail facts are emitted for the first {_MAX_DETAIL_FACTS} signals "
            f"allocated across the signal-bearing steps oldest-first; {truncated} further "
            "signal(s) are counted in this series and in the recurrence tally but are not "
            "individually detailed below."
        )
    return CitedStatement(
        f"PAIRWISE COMPARISON SERIES: all {n_versions} loaded version(s) were compared "
        f"CONSECUTIVELY, oldest to newest, two at a time — {n_steps} comparison(s). "
        f"Manipulation signals exist only between two snapshots, {completeness}. "
        f"{series.total_signals} signal(s) fired in total, in "
        f"{series.steps_with_signals} of {n_steps} step(s): {rendered}{note}.{skipped}{detail}",
        cite,
        pinned=True,
    )


def _recurrence_fact(series: PairwiseSeries, cite: tuple[Citation, ...]) -> CitedStatement:
    n_steps = len(series.steps)
    if not series.recurrence:
        return CitedStatement(
            f"MANIPULATION-SIGNAL RECURRENCE: none of the {n_steps} consecutive-pair "
            f"comparison(s) fired any manipulation signal. This is a measured result across "
            f"every update in the workbook, not an unexamined one.",
            cite,
            pinned=True,
        )
    parts = [
        f"{_signal_label(r.metric_id)} fired in {r.steps_present} of {n_steps} step(s) "
        f"({r.total_findings} finding(s); longest unbroken run {r.longest_run} step(s); "
        f"first step {r.first_step}, last step {r.last_step})"
        for r in series.recurrence
    ]
    net = series.net_finish_movement_days
    finish_note = (
        f" Across the whole series the computed finish moved {net:+d} calendar day(s)."
        if net is not None
        else " The computed finish movement across the series is unreadable."
    )
    return CitedStatement(
        f"MANIPULATION-SIGNAL RECURRENCE across the {n_steps} consecutive-pair comparison(s): "
        f"{'; '.join(parts)}.{finish_note} Read these as counts, not as intent: a signal in one "
        f"step of {n_steps} is a single event, while a signal recurring across many steps — "
        f"especially in an unbroken run — is the repetition a forensic reviewer calls a pattern. "
        f"The tool asserts the counts and the changes behind them; it does not assert why they "
        f"were made.",
        cite,
        pinned=True,
    )


def _detail_facts(series: PairwiseSeries) -> tuple[list[CitedStatement], int]:
    """Per-step findings, allocated ROUND-ROBIN oldest step first (see the module docstring).

    Returns ``(facts, undetailed_count)`` so the series fact can state the truncation.
    """
    queues = [(step, list(step.findings)) for step in series.steps if step.findings]
    total = sum(len(q) for _, q in queues)
    facts: list[CitedStatement] = []
    round_index = 0
    while len(facts) < _MAX_DETAIL_FACTS and any(len(q) > round_index for _, q in queues):
        for step, queue in queues:
            if len(facts) >= _MAX_DETAIL_FACTS:
                break
            if len(queue) <= round_index:
                continue
            finding = queue[round_index]
            moved = step.finish_movement_days
            effect = (
                f"Across this same update the computed finish moved {moved:+d} calendar day(s)."
                if moved is not None
                else "The computed finish movement across this update is unreadable."
            )
            facts.append(
                CitedStatement(
                    f"Manipulation signal at step {step.index} of {len(series.steps)} "
                    f"({step.prior_label} to {step.current_label}) [{finding.severity}]: "
                    f"{finding.title}.{_named_activities(finding)} "
                    f"{finding.course_of_action} {effect}",
                    finding.citations or _anchor(series),
                )
            )
        round_index += 1
    return facts, max(total - len(facts), 0)


def pairwise_comparison_facts(
    schedules: list[Schedule], cpms: list[CPMResult] | None = None
) -> tuple[CitedStatement, ...]:
    """The consecutive-pair comparative facts for a multi-version workbook.

    Returns ``()`` for fewer than two versions — there is no comparison to make, and the
    single-version facts already say which file they describe.
    """
    if len(schedules) < 2:
        return ()
    series = compute_pairwise_series(schedules, cpms)
    if not series.steps:
        # Every adjacent pair was uncomparable. Returning () here would be the exact failure this
        # module exists to close: the reader cannot tell "no comparison was possible" from "the
        # comparisons were made and were clean". Say which, and name the pairs (Law 2).
        if not series.uncomparable:
            return ()
        labels = ", ".join(series.uncomparable)
        cite = tuple(
            Citation(s.source_file or s.name, 0, s.source_file or s.name) for s in schedules
        )
        return (
            CitedStatement(
                f"PAIRWISE COMPARISON SERIES: of the {series.versions} loaded version(s), NONE "
                f"of the {len(series.uncomparable)} adjacent version pair(s) could be compared, "
                f"because a version's network does not solve "
                f"— {labels}. No manipulation signal has been measured across this workbook. This "
                f"is missing analysis, NOT an absence of signals; do not read it as a clean "
                f"workbook.",
                cite,
                pinned=True,
            ),
        )
    cite = _anchor(series)
    details, undetailed = _detail_facts(series)
    return (_series_fact(series, cite, undetailed), _recurrence_fact(series, cite), *details)
