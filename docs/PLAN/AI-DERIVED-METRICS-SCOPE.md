# SCOPE — Derive-and-Verify AI metrics

**Status:** proposal / scope only. Nothing here is implemented. Awaiting operator sign-off on the
metric list (§4) and the verification contract (§3) before Phase 1.

**Operator direction (the requirement this serves):** *"Use the metrics calculated by the code to
answer questions to the best of its ability, even if that means deriving new metrics from those
metrics that were derived from the tool itself — but only if they are derived according to industry
standard, best practices, and verified for accuracy."*

---

## 1. Problem & today's behavior

The AI layer already grounds every answer in an engine-computed **fact sheet** of cited statements
(`ai/qa.py:build_fact_sheet` / `build_workbook_fact_sheet`; each fact a `CitedStatement` carrying
`file + UID + task` citations). The three Q&A modes (ADR-0129) handle *derived* figures like this:

- **strict** — any number in the model's answer not present in the fact sheet **discards the whole
  answer** (`qa.py:426-428`).
- **annotate** (default) — the answer is kept, but every figure not in the fact sheet is **flagged**
  as `[AI-derived … verify against the cited facts]` (`qa.py:_annotate_unsourced`, `:346`). It is
  *labeled*, never *verified*.
- **interpretive** — returned verbatim, ungated.

So today a legitimate derived metric (e.g. "12 of 126 hard constraints = **9.5%**") is treated
identically to a hallucinated one: strict throws it away, annotate slaps an "unverified" footer on
it. The operator wants the tool to instead **compute the standard derivation itself and present it as
trustworthy**, with the derivation reproducible and labeled — not merely flagged as suspect.

The two non-negotiable laws bound the solution: **Law 1** (offline/loopback — unchanged here, all
local) and **Law 2** (fidelity — *no unsourced or unverified number may reach the analyst as fact*).
The design must make derivation *more* capable without weakening Law 2.

## 2. Design — two layers

### Layer A — Engine-computed derived metrics (the trustworthy core)

A small, curated library of **standard secondary metrics** the *engine* computes deterministically
from the primary `MetricResult`s (`metrics/_common.py:MetricResult` exposes `count`, `population`,
`value`, `offender_uids` — rich enough inputs). Each derived metric:

- is a **pure function of already-computed primary metric figures** (no new schedule traversal, so it
  cannot disagree with the primaries);
- maps to a **named, sourced formula** — DCMA-14, the NASA Acumen `.aft` Bible, or a recognized EVM /
  schedule-quality standard — recorded in `web/help.py` exactly like every primary metric, and
  regenerated into `docs/METRIC-DICTIONARY.md`;
- becomes a first-class **cited fact** in the fact sheet, so it is *as trustworthy as any engine
  number* and the AI simply narrates it. **No model verification is needed** because the engine, not
  the model, computed it.

This is the heart of "derive per industry standard, verified": the derivation lives in tested code
with a cited source, not in the model.

### Layer B — Verified ad-hoc derivation gate (for Q&A the library doesn't precompute)

For derivations Layer A does not precompute, upgrade the annotate path from *flag* to
*verify-or-flag*. When the model emits a figure not in the fact sheet, a **deterministic verifier**
attempts to reconstruct it from sourced inputs over a **bounded whitelist of standard operations**
(difference, ratio/percentage-of-population, period-over-period delta & rate, sum across an offender
set). If a reconstruction reproduces the emitted figure within a defined tolerance, the figure is
**relabeled `[derived: A op B = C — from <citations>]` (verified)** instead of
`[AI-derived, unverified]`. If nothing reconstructs it, it stays **flagged** (annotate) or **discards
the answer** (strict) — exactly as today. Fail-closed: an unverifiable number never gains trust.

Layer B is strictly additive to the existing gate and never lets an unverified number pass as fact —
it only *upgrades the label* of figures it can independently reproduce.

## 3. The verification contract (must be signed off before Phase 1)

1. **Inputs must be sourced.** Every operand of a verified derivation must itself be a figure present
   in the engine fact sheet (or a Layer-A derived fact). No operand may originate from the model.
2. **Operations are a closed whitelist.** Only the named standard operations in §4/Layer B — no
   arbitrary symbolic math. Adding an operation is a code + ADR change, not a model freedom.
3. **Deterministic recomputation, exact-or-tolerance match.** The verifier recomputes in Python;
   acceptance requires equality after a **defined rounding rule** (proposal: ratios/percredits to 1
   decimal place, matching the engine's display precision; counts exact). The tolerance is explicit
   and tested, not a fuzzy "close enough".
4. **Labeled at the point of use.** A verified derived figure is always shown with its inputs +
   operation + citations, so a testimony reader can reproduce it from committed artifacts. A
   non-verified figure keeps the existing "AI-derived — verify" footer.
5. **Law 2 preserved.** "No unsourced number reaches the analyst as fact" still holds: Layer A
   numbers are engine-computed; Layer B numbers are either engine-reproduced (verified) or explicitly
   marked unverified. The H2 accusation guard and the sign-aware figure gate (ADR-0131/0132) are
   unchanged and still apply.
6. **No parity movement.** Layer A adds *new* facts only; it must not alter any existing metric value
   or golden. A test asserts each derived metric equals the hand-computed function of its primaries
   on the goldens.

## 4. Proposed initial metric list (Layer A) — for sign-off

Each is a standard, sourced derivation of figures the engine already computes. **Pick the subset you
want; I will not add any metric whose formula I cannot cite to a recognized source.**

| Derived metric | Formula (from primaries) | Source / standard |
|----------------|--------------------------|-------------------|
| **% of population** for each count metric (hard constraints, high float, negative float, missing logic, …) | `count / population × 100` | NASA Acumen `.aft` ratio metrics / DCMA population ratios |
| **DCMA checks passed (n/14)** & overall pass rate | tally of `status == PASS` across DCMA-01..14 | DCMA 14-Point Assessment |
| **Schedule-quality offender concentration** | `Σ offender_uids` distinct count vs population | Acumen schedule-quality rollup |
| **Critical-Ratio (SCI)** where cost-loaded | `SPI × CPI` | EVM standard (Schedule-Cost Index) |
| **Period-over-period deltas & rates** for any trended metric | `vₙ − vₙ₋₁`, `(vₙ − vₙ₋₁)/Δstatus-periods` | built on existing `engine/trend.py` series |
| **Net change composition** (added / slipped / completed shares of a version delta) | shares of the §E change set | already engine-tracked (diff/change-metrics) |

Explicitly **out of scope** unless you ask: any composite "score" with an *unpublished* weighting
(the Acumen SQ/DCMA composite scores stay `_scores_deferred` — we don't invent a weighting), and any
metric requiring an artifact we don't have (Fuse §E re-validation, the `.aft` Bible literal match).

## 5. Phasing

- **Phase 0 (this doc):** operator signs off on the §4 list + the §3 contract.
- **Phase 1 — Layer A:** implement the chosen derived metrics as a `engine/metrics/derived.py` module
  of pure functions over primary `MetricResult`s; add them to `help.py` (+ regenerate the dictionary)
  and to the fact sheet; pin each with a golden-based test (`derived == hand-computed`). Parity-neutral
  by construction. One ADR.
- **Phase 2 — Layer B:** the verified-derivation gate in `qa.py` (reconstruct-and-relabel); extend the
  annotate footer to distinguish *verified-derived* from *unverified*; unit-test each whitelisted
  operation with a positive (reproduces → verified) and negative (cannot reproduce → stays flagged)
  case. One ADR.
- **Phase 3 (optional):** surface verified derivations in the narrative / executive briefing too,
  through the same `citations.reattach` gate (which already guards figures + accusations).

## 6. Risks & mitigations

- **Layer B as a backdoor for hallucinated numbers** → mitigated by §3.2/3.3: closed operation
  whitelist + exact deterministic recomputation, fail-closed. If it can't be reproduced, it is not
  trusted.
- **Floating-point / rounding drift** → an explicit rounding rule (§3.3) tested on both sides, mirroring
  the M5 client/server-precision fix.
- **Scope creep into novel "metrics"** → §3.2: only sourced, named standard formulas; novelty requires
  an ADR, never a model decision.
- **Parity regression** → §3.6: Layer A is additive; a test asserts no primary/golden value moves.
- **Testimony defensibility (Daubert-style, engineering only)** → every derived value is reproducible
  from committed inputs + a cited formula and labeled at the point of use; error/rounding bounds are
  disclosed. (Not legal advice — consult counsel for any admissibility question.)
- **Law 1** → unchanged; no new network path, all derivations local.

## 7. What I need from you

1. Which rows of the **§4 metric list** to build (all, or a subset).
2. Sign-off on the **§3 verification contract**, especially the rounding rule in §3.3.
3. Whether to include **Phase 2 (Layer B)** now or ship **Layer A first** and evaluate.
