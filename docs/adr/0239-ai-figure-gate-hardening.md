# ADR-0239 — AI figure-gate hardening: translate gate, number-words, accusation stems (PR-R1)

## Status

Accepted. The three highest-stakes VALID-AND-OPEN items from the validated prior audits
(2026-07-13/14, re-verified by sandbox probes on 2026-07-16), all Law-2 surfaces.

## Context

Three proven bypasses of the "no unsourced number / no unverified accusation reaches the
analyst" guarantees: (H1) `_ai_translate` was the ONE AI `.generate()` emission with no figure
gate — a soft prompt instruction only, reply stored verbatim; (M4) the figure tokenizer was
digits-only, so a model spelling a count out ("Twelve activities") slipped every gate (probe:
`figure_tokens("Twelve activities") == []`); (M5) the accusatory-term guard was an exact-word
list — fabricated / doctored / misleading / gamed / rigged / cheated / misrepresented all passed.

## Decision

1. **H1:** every accepted translation line must satisfy `preserves_figures(source, line)`;
   a line that drops, invents, or alters any figure is discarded and the caller keeps the source
   text verbatim (fail closed, per-line). Every `.generate()` output reaching the operator now
   passes the same figure check.
2. **M4:** `figure_tokens` gains a bounded number-word lexicon (two…ninety + scale words + zero
   + dozen), each tokenizing to its digit string — "twelve" and "12" are the SAME evidence token,
   so a legitimate rephrase passes and an introduced spelled-out count fails. "one" is
   deliberately excluded (pronoun saturation would force fallbacks on harmless prose; an invented
   count of one is the least material figure). One tokenizer feeds every gate, so
   strict/annotate Q&A and the dual-model cross-check inherit the fix.
3. **M5:** the loaded-terms guard adds stem matching (`fabricat-`, `mislead-`, `misrepresent-`,
   `doctored/doctoring`, `rigged/rigging`, `gamed`, `cheat-`, `deceiv-`, `cover-up`). Stems are
   chosen so ordinary words ("doctor", "rig", "game") never match, and `manipulat-` is absent by
   design — manipulation is this tool's own domain vocabulary; only *introduced* terms are ever
   flagged.

## Consequences

- The audit probes that proved the bypasses are now adversarial regression tests
  (`tests/ai/test_citations.py`, `tests/web/test_i18n.py`).
- The bounded lexicon slightly widens what counts as a figure; a rephrase that introduces prose
  number-words where the engine used none now falls back to the verbatim sentence — fail-closed
  by design, never a wrong number.
- Interpretive Q&A remains ungated by design (ADR-0129); the strict/annotate contract is what
  these gates back.
