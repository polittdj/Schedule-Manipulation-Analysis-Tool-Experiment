# ADR-0138 — Figure-gate hardening: whole-date tokens, exact counts, identifier-first, span-based names

## Status

Accepted. Amends ADR-0135 (Layer B matching) and ADR-0137 (role gate); part of the 2026-07-01 QC
audit remediation (batch R1).

## Context

A full read-only QC audit (2026-07-01) falsified the strict-mode guarantee "no invented or re-roled
number reaches the analyst" with four confirmed defects, each independently reproduced three ways:

- **D1 (CRITICAL).** `_FIGURE_RE` split ISO dates into fragments (`2026-03-02` → `2026`/`-03`/`-02`),
  seeding the Layer-B operand pool with small negative pseudo-figures; combined with `_matches`'
  round-to-1-dp tolerance (±0.05 on *every* target, including integers), ~33% of invented integers
  1–100 on the committed golden were "verified" — and stamped with a `[Derived figures — recomputed
  by the tool …]` footer counter-signing arithmetic like `0.8 / 27 * 100 = 3` (true value 2.963).
- **D4 (HIGH).** `_classify_figures` tried `verify_derivation` *before* the identifier-only check, so
  a re-roled UID passed strict whenever it coincided (±0.05) with any ratio of two sourced figures
  (`UID 50` == `12 / 24 * 100`) — the exact defect ADR-0137 declared closed.
- **D6 (HIGH).** `_figure_roles` blanked citation names with `str.replace`; an empty task name
  (reachable via the tool's own JSON: `"name": ""`) space-split the whole fact text, and a task
  literally named `"5"` swallowed the 5 inside `45`/`95` — destroying genuine engine values, which
  strict then discarded and annotate falsely footnoted "produced by the local model".
- **D15 (MEDIUM).** Strict discarded any answer that *named* a cited UID ("UID 143") — the exact
  shape the driving-path facts invite — so strict mode and driving-path Q&A were mutually exclusive,
  while (per D4) the only UID mentions that survived were the laundered ones.
- **D16 (MEDIUM).** The dual-model cross-check compared *post-footer* text, so the tool's own
  derivation arithmetic (e.g. the `100` in `12 / 24 * 100`) made two agreeing answers report
  "the two answers DIFFER on figures".
- **D23 (LOW).** No complexity cap: ~10.7 s CPU per answer measured at 350 operands × 30 figures.

## Decision

1. **Whole-date tokens (`ai/citations.py::figure_tokens`).** A new shared tokenizer matches ISO
   dates/timestamps as single tokens before the sign-aware number pattern (M6 unchanged for real
   numbers). Every figure gate — `preserves_figures`, the Q&A role gate, the cross-check — uses it,
   so a date can never shed month/day fragments into any gate. Date tokens are non-numeric to
   `float()`, so they can never be derivation operands or targets.
2. **Exact counts (`ai/derivation.py`).** An integer target token must be reconstructed exactly
   (float-noise epsilon only); the 1-dp tolerance now applies only to decimal targets — the
   engine's own ratio display precision, per the Layer-B contract's "counts exact". Operands are
   capped (`_MAX_OPERANDS = 64`, fact-order first) and the answer-side gate caps reconstruction
   attempts (`_MAX_GATED_FIGURES = 24`; the excess is flagged unverified — fail closed).
3. **Identifier-first classification (`ai/qa.py::_classify_figures`).** Priority per occurrence:
   value → identifier-role usage → **identifier-only (before any derivation attempt)** → verified
   derivation → unverified. A re-roled identifier can never launder through a coincidental
   reconstruction.
4. **Identifier-role usage allowed.** A figure written *as* an identifier — inside a `UID n`
   reference or a quoted cited activity name — is correct role usage and passes when it matches a
   cited identifier; an invented reference (`UID 999`) is unverified (fail closed). Strict mode and
   the driving-path facts are no longer mutually exclusive.
5. **Span-based identifier extraction (`_identifier_spans`).** Citation names locate by
   regex-escaped, digit-boundary-guarded search (a name `"5"` matches only a standalone `5`); an
   empty name contributes no span; `UID n` references match with a trailing digit guard. No
   `str.replace` on arbitrary names anywhere in the gate.
6. **Pre-footer cross-check (`_strip_gate_footers`).** `figure_agreement` compares the models'
   own prose with all tool-appended `\n\n[…]` footers stripped.
7. **Disclosures updated** (qa docstrings, Ask-the-AI panel, CLAUDE.md) to state the hardened
   contract precisely. One acknowledged residual: a bare `100%` (x/x) is still unverifiable and is
   discarded in strict — conservative by choice, since accepting `a / a * 100` would verify any
   invented `100`.

## Consequences

- All six defects have pinned regression tests (`tests/ai/test_qa.py`, `test_derivation.py`,
  `test_citations.py`); the ADR-0137 behaviors (re-roled name-digit discarded, collision-safety,
  annotate role flag) are re-verified unchanged; the full AI suite passes without modifying any
  pre-existing expectation.
- The strict guarantee is now: every figure is a cited value, a correct identifier reference, or an
  exactly/1-dp-reconstructed ratio-class derivation shown with its arithmetic.
- Narrative/briefing figure preservation is unaffected in behavior (dates compare as whole tokens —
  the same rephrasings pass/fail as before); no engine number moves.

## Alternatives considered

- **Ban identifier digits from answers entirely.** Rejected: correct driving-path answers must name
  UIDs; role-aware allowance is strictly more accurate.
- **Accept `a / a * 100` to verify "100%".** Rejected: it would verify any invented `100` whenever a
  single operand exists; fail-closed is the testimony-safe direction.
- **Tolerance-match integers at 1 dp (status quo).** Rejected: measured 33% laundering coverage on
  the committed golden — the headline falsification of the strict guarantee.
