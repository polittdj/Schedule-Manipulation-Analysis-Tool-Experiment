# ADR-0133 — Derived metrics, Layer A (engine-computed, cited)

## Status

Accepted.

## Context

The operator asked the AI layer to "use the metrics calculated by the code to answer questions to the
best of its ability, even if that means deriving new metrics from those metrics — but only if they are
derived according to industry standard, best practices, and verified for accuracy."
`docs/PLAN/AI-DERIVED-METRICS-SCOPE.md` (merged, #274) proposed a two-layer design and the operator
signed off on **Layer A first**, building two derived metrics: **% of population** (A) and **DCMA
checks passed, n/14** (B), with the verification contract's rounding rule (ratios/percentages to one
decimal place; counts exact).

The key design choice: a derived figure is only defensible if the *engine* computes it deterministically
from already-computed primaries — not the model. So Layer A lives in tested code with a cited source,
and the AI merely narrates it.

## Decision

1. **`engine/metrics/derived.py`** — two pure functions of figures the engine already produces:
   - `population_share(count, population)` → `count / population × 100` to 1 dp, or `None` on an empty
     population (never a fabricated 0).
   - `dcma_pass_rate(passed, failed)` → `passed / (passed + failed) × 100` to 1 dp over the
     **applicable** checks only (not-applicable excluded, per DCMA convention), or `None` when none is
     applicable.
   Both are exported from the `engine.metrics` package.

2. **Fact sheet (`ai/qa.build_fact_sheet`)** gains two **cited derived facts**, appended after the
   primaries they summarise (the frame fact stays first; no existing fact text changes):
   - *"Derived — DCMA 14-point assessment: {passed} of {applicable} applicable checks pass ({rate}%
     pass rate); {n/a} not applicable."* (cited to the failing checks).
   - *"Derived — finish-driving concentration: {share}% of the network ({n} of {m} activities) sits at
     zero float to the project end."* (the canonical "N of M = X%" derivation, sourced — a figure not
     otherwise shown as a percentage).
   Because they are engine-computed and cited, they are usable in **every** Q&A mode (including strict)
   and the narrative — no `[AI-derived]` flag, because the model did not compute them.

3. **`web/help.py`** documents both as first-class dictionary entries (`dcma_pass_rate`,
   `population_share`) with definition + formula + source (DCMA 14-Point Assessment; the Acumen
   population-ratio metrics). `dcma_pass_rate` is tagged the **Construction** reliability dimension;
   `population_share` takes the default **Realism**. `docs/METRIC-DICTIONARY.md` is regenerated (the
   sync test enforces it).

4. **Tests** (`tests/engine/metrics/test_derived.py`): the formulas exactly (9.5 from 12/126; the
   pass-rate denominator excludes n/a; `None` on empty), **plus a golden test that each derived value
   equals the hand-computed function of the audit's own primaries on Project2/Project5**. A fact-sheet
   test asserts both derived facts appear and are cited.

## Consequences

- **No parity number moves** — `derived.py` reads already-computed figures; it adds no traversal and
  alters no metric. The parity gate stays green; the derived values are pinned to the primaries by the
  golden test, so they cannot silently drift from them.
- A derived figure (a normalised share, the DCMA pass rate) is now **engine-sourced and cited**, so the
  analyst gets it already computed and a strict-mode Q&A no longer rejects it as "unsourced". This is
  the "derive per industry standard, verified" path the operator asked for — the derivation is in code
  with a cited formula, not in model prose.
- Law 1 (offline) and Law 2 (no unsourced number reaches the analyst as fact) are preserved; the H2
  accusation guard and sign-aware figure gate (ADR-0131/0132) are unchanged.

## Alternatives considered

- **Spray `population_share` onto every metric.** Rejected as redundant: most DCMA/quality metrics
  already report their value as a percentage of the population, so a blanket share would duplicate the
  primary. Layer A adds the share only where it is genuinely new (the finish-driving "N of M") and the
  DCMA roll-up, and exposes `population_share` for any future count-unit metric.
- **Layer B (the Q&A verified-derivation gate) in this PR.** Deferred per the operator's "Layer A first,
  then evaluate" decision; scoped in `AI-DERIVED-METRICS-SCOPE.md` §5.
- **Composite Acumen-style scores.** Out of scope — they need an unpublished weighting (kept
  `_scores_deferred`); we do not invent one.
