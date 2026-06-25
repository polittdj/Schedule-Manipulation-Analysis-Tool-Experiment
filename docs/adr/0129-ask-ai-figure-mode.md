# ADR-0129 — Operator-selectable Ask-the-AI figure mode (annotate / strict / interpretive)

## Status

Accepted.

## Context

The charter stated "every AI-emitted figure is re-verified against engine citations, so the model can
never introduce an unsourced number." The QC audit (`docs/STATE/AUDIT-2026-06-25.md`, finding C2) showed
this was **false in the default Ask-the-AI mode**: `qa_mode` defaulted to `interpretive`, and in
`answer_question` the figure-subset gate ran only when `mode != "interpretive"`. So the default path
returned the local model's text — including numbers the engine never computed — verbatim. A repo test
even pinned it (`31415` survived to the client). In a forensic/testimony context an analyst could copy a
fabricated figure believing the "no unsourced number" guarantee held.

The operator's decision: give the user a **choice** between a strict mode and an annotate-derived-figures
mode, and **re-scope the documented guarantee** so it honestly describes each mode.

## Decision

`qa_mode` is operator-selectable in AI Settings with three values; the **default is `annotate`**:

1. **`annotate` (default).** The model gets the full cited fact sheet and may analyze/derive freely
   (same rich prompt as interpretive), but the answer is post-processed: every figure NOT present in the
   cited facts is enumerated in an `[AI-derived …]` footer (`qa._annotate_unsourced`). The answer is
   **kept** (useful analysis) and a derived number can **never be mistaken** for an engine figure.
2. **`strict`.** Unchanged: any answer containing a figure not in the fact sheet is discarded wholesale
   (the caller shows the cited facts instead). No unsourced figure reaches the analyst.
3. **`interpretive`.** The model's text is returned verbatim and is **not** figure-gated — the operator
   explicitly opts into raw analysis. The standing "AI can err — verify against the citations" disclaimer
   rides every answer, and the cited facts are always shown alongside.

**Re-scoped guarantee (CLAUDE.md).** "No unsourced number reaches the analyst" holds for the
narrative / briefing / translation paths and the **strict** and **annotate** Q&A modes — **not** for
interpretive. The narrative-path `reattach` gate is also clarified as a *numeric subset* gate (it guards
digits, not prose — audit finding H2, addressed separately).

## Consequences

- The default Ask-the-AI experience is now safe-by-default: rich model analysis is preserved, but any
  AI-derived figure is flagged, so the charter's framing matches actual behavior.
- The operator can still pick `strict` (maximum rigor, terse) or `interpretive` (raw, ungated) per the
  engagement. Locality (Law 1) is unaffected — the mode governs only prose handling; the backend routing
  and loopback/fail-closed posture are untouched.
- Tests: `tests/ai/test_qa.py` adds an annotate unit test; `tests/web/test_ask_everywhere.py` covers all
  three modes through the route; the prior interpretive-default assertions were updated to the new
  `annotate` default.

## Alternatives considered

- **Make `strict` the default.** Rejected: strict discards an entire useful answer over a single derived
  ratio, which is poor default UX; annotate keeps the analysis while still flagging derived figures.
- **Inline marking of each figure.** Rejected for now in favor of a single enumerated footer — inline
  regex substitution on model prose risks mangling numbers embedded in other tokens (dates, times); the
  footer is unambiguous and non-destructive.
- **Drop interpretive entirely.** Rejected: some operators want raw model output; keeping it as an
  explicit, clearly-labeled, un-guaranteed choice (with the disclaimer) is more honest than removing it.
