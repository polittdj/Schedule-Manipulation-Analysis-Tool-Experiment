# ADR-0145 — Unit-role figure gate: the first semantic step of the F-11 role model

## Status

Accepted. Extends ADR-0137/0138 (value-vs-identifier role gate); the first deliverable of the
"fuller semantic role model" those ADRs deferred as future work.

## Context

After ADR-0138, the strict/annotate gate guaranteed a figure is a cited **value**, a correct
**identifier reference**, or an exact **reconstruction** — but said nothing about *how* a value is
used. A model could take a figure the engine stated only as a percentage ("… (5%)") and re-write it
as a duration ("the margin is 5 days"): every digit checks out, the meaning is fabricated. The QC
audit called this the *semantic* half of F-11.

A full semantic model is out of reach deterministically, but one slice is checkable with zero
false-positive risk appetite: **explicit unit contradictions**.

## Decision

`ai/qa.py` (`_unit_role`, wired through `_figure_roles` → `_classify_figures`):

1. **Fact side.** For every value token, record the EXPLICIT unit contexts the facts state it in:
   `pct` (followed by `%`/`percent`) or `plain` (followed by a count/duration unit word — day(s),
   activities, tasks, minutes, hours, links, relationships). A token the facts only use bare gets
   **no entry** and is never checked.
2. **Answer side.** A value token written with an explicit unit that is **absent from its fact
   unit set** is `unit_misused`: **strict discards** the answer, **annotate flags** it with a
   dedicated footer ("re-used with a different unit than the engine stated").
3. **Collision-safe by construction, like the identifier split:** flagged only when *both* sides
   are explicit *and* disjoint. Bare answer usage ("the figure is 5"), bare fact usage, and
   multi-unit tokens (a `5` the facts state both as a count and as `5%`) are never touched.
4. Interpretive stays ungated by design. Disclosures updated (qa docstring, Ask-the-AI panel,
   CLAUDE.md); regression tests pin all six behaviors.

## Consequences

- The classic unit-fabrication move (a percentage re-rolled as days, a count re-rolled as a
  percentage) no longer survives strict mode or passes unflagged in annotate.
- Deliberately conservative: anything ambiguous passes untouched, so no legitimate answer is
  lost — the same fail-open-on-ambiguity posture that kept the identifier gate collision-safe.
- What remains future work: unit synonyms the regexes don't cover, cross-sentence unit inference,
  and true semantic roles (dates-as-deadlines, ratios-as-trends). Each can extend `_unit_role`
  without touching the gate's structure.

## Alternatives considered

- **Flag bare usages against single-unit facts** ("the rate is 5" when facts say only `5%`).
  Rejected: "rate is 5" plausibly *means* 5% — ambiguity must pass (fail-open on ambiguity,
  fail-closed on contradiction).
- **An NLP/model-based role classifier.** Rejected: the gate exists to check the model; it cannot
  itself rest on model judgment (ADR-0135's determinism rationale).
