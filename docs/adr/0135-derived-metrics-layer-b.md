# ADR-0135 — Derived metrics, Layer B (the verified ad-hoc derivation gate)

## Status

Accepted.

## Context

`docs/PLAN/AI-DERIVED-METRICS-SCOPE.md` proposed two layers; **Layer A** (ADR-0133) added engine-computed
derived metrics as cited facts. **Layer B** is the second half: when a local model writes a number that
is NOT literally in the cited facts, the prior behaviour was binary — `strict` discarded the whole
answer, `annotate` flagged the figure as `[AI-derived]`. A *legitimate* derived rate (e.g. "12 of 126 =
9.5%") was treated identically to a hallucination.

The operator's direction: the AI may derive further metrics from the engine's metrics, **but only by a
standard operation, verified for accuracy**. Layer B implements that verification.

## Decision

1. **`ai/derivation.py` — a deterministic verifier.** `verify_derivation(target_token, sourced)` tries
   to reconstruct a model-emitted figure from the engine's **sourced figures only** over a *closed
   whitelist* of standard binary operations — `percent_of` (`a/b*100`), `percent_change`, `ratio`
   (the ratio class), then `difference`, `sum` (additive) — returning the simplest match (ratio-class
   first) or `None`. Ratios/percentages match to **one decimal place** (the Layer A contract rounding);
   counts are exact. No operand ever comes from the model.

2. **`ai/qa.answer_question` — verify-or-flag.**
   - **annotate (default):** a non-sourced figure that reconstructs is shown as a **verified
     derivation** with its arithmetic (`[Derived figures — recomputed by the tool … : 44 / 99 * 100 =
     44.4]`); one that does not is still flagged `[AI-derived …]`. The rich answer is kept either way.
   - **strict:** the answer is accepted if every non-sourced figure is a **ratio-class** reconstruction
     of sourced figures (shown with its arithmetic); any unverified figure, or one whose only
     reconstruction is additive, still discards the whole answer. So strict gains the ability to carry a
     *standard rate derived from engine figures* without admitting an invented number.
   - **interpretive:** unchanged (ungated by design).

3. **Verifies the arithmetic, not the meaning.** A reconstruction proves the number is a standard
   combination of sourced figures; it cannot prove the relationship is *meaningful*. So the
   reconstruction is **always shown** to the analyst (who confirms meaning), and only ratio-class ops —
   far less prone to a coincidental match than an integer difference — are trusted by strict. Additive
   reconstructions are offered in annotate (transparent, kept-with-label) but never trusted by strict.

## Consequences

- The operator's goal is met **safely**: the AI's derived rates are recomputed and shown, not invented;
  a derived figure that is a standard combination of engine figures is verified rather than flagged, and
  strict can now carry one. The Law-2 guarantee strengthens — *no number reaches the analyst that is not
  either sourced or a shown, recomputed combination of sourced figures*.
- **No parity number moves; no engine/metric/fact change** — Layer B operates purely on the model's
  answer text against the already-computed fact figures. Backward-compatible: a non-reconstructible
  figure (the existing `31415` tests) still flags in annotate and discards in strict.
- Law 1 unaffected (all local); the F-11 presence-not-role disclosure (ADR-0134), the H2 accusation guard
  and the sign-aware figure gate (ADR-0131/0132) are unchanged and still apply.

## Alternatives considered

- **Trust additive reconstructions in strict too.** Rejected: an integer `difference`/`sum` of two
  sourced figures coincides with an arbitrary target far more often than a ratio, so trusting it in the
  rigour mode would admit coincidences. Additive reconstructions are surfaced only in annotate, labelled
  and kept, where the analyst sees the arithmetic.
- **Search triples / a full expression grammar.** Rejected for now: pairs over a closed op set bound the
  search and the coincidence surface; a richer grammar raises false-verification risk without a clear
  need. The whitelist can grow by ADR if a real case demands it.
- **A semantic/role-aware gate (close F-11 fully).** Larger future work: compare a figure's *role*
  against the engine fact it came from, not just reconstruct its value. Layer B is the value-level half.
