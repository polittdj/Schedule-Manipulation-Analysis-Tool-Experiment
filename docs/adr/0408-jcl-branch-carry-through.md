# ADR-0408 — JCL-BR-01 closes: the branch registers carry through compute_jcl, the last strict xfail flips, and the repo is xfail-free

**Status:** Accepted · **Date:** 2026-08-15 · **Closes:** JCL-BR-01 (ADR-0401's recorded
equivalence break; the final agent-queue item of the 2026-08-13 audit arc) ·
**Version:** v1.0.206 → **v1.0.207** (shipped code: `engine/jcl.py`, `web/app.py`,
`web/sra.py`) — wheel + nine installers rebuilt, lockstep 64/64.

## Context

ADR-0269's "one story" guarantee — the JCL football chart's schedule axis IS the SSI
S-curve — held for factors, risks, correlation, PERT, LHS and the focus event, but
**not for the branch registers**: `compute_jcl` accepted no branch inputs, so
`/api/sra/ssi` fed the session's probabilistic/conditional branches to the SSI run only.
Measured 2026-08-14 (ADR-0401): with a branch configured, SSI percentiles moved and JCL's
did not — recorded as a strict xfail. Worse, the SRA Excel export ran **both** engines
into ONE workbook: the SSI sheets carried the branches, the JCL sheets didn't — a
two-story document in a testimony context.

## Decision — carry-through, by the module's own architecture

`jcl.py` already imports the SSI engine's private helpers as its stated design ("the
duration dimension replicates compute_sra_ssi's draw discipline exactly"). The fix
extends that list — `_augment_with_branches`, `_augment_with_conditionals`,
`_branch_draws`, `_conditional_draws`, `_conditional_trips` — and mirrors the SSI blocks
statement-for-statement (minus SSI's reporting stats, which the JCL result does not
carry):

- **Same augmentation, same ORDER** (branches first, then conditionals — the fragnet
  uids must match between engines; a combined-register test pins the order).
- **Same disjoint draw streams**: branch firing / fragnet durations / conditional
  chosen-plan uniforms come from the pre-built seeded streams, never from the
  per-iteration `rng` — so they perturb neither the duration draws nor the cost
  multiplier draws.
- **The finish-metric conditional probe solve** is replicated (one extra `compute_cpm`
  per iteration, exactly as SSI).
- **Both web call sites** (`/api/sra/jcl` and the SRA export's JCL sheets) now pass
  `branches=_schedule_branches(st), conditionals=_schedule_conditionals(st)` — the
  mirror of the SSI call four lines above each.

**Fragnets are cost-inert BY THE DATA.** A branch's rework fragnet is a zero-budget leaf
(`Task(uid, name, duration_minutes=0)`): branch cost is never elicited anywhere in the
model, and fabricating a burn rate would violate the module's own "never fabricate"
(Law 2). Consequences, all test-pinned: the fragnet enters the cost entries with
`spent = ti = td = 0`, consumes **no** cost-multiplier draw (the `ti + td > 0` guard),
consumes **no** duration draw (a point mass — the sampler's documented rule), and leaves
`deterministic_eac`, the cost CDF and every provenance figure byte-identical to the
no-branch run. A branch moves the **finish axis only**. The JCL panel explainer now
states the full shared-inputs enumeration including the branch registers and this
zero-budget disclosure.

## Deliberately NOT done

- **No costed branches.** Giving fragnets an elicited cost range (a real Hulett
  integrated-cost rework model) is a *model extension* requiring new operator inputs on
  the branch editor — a separate decision, not a parity fix.
- **No JCLResult schema change.** SSI owns branch-outcome reporting (`SSIBranchStat` /
  `SSIConditionalStat`); JCL pins equality to that same curve. SCHEMA stays 2.11.0.
- **No honest-gate fallback.** The queue's alternative (422 while branches exist) died
  the moment measurement showed byte-identity holds through the shared helpers.

## Verification (QC-1)

- **Red first**: 7 new tests failed by name against the pre-change tree (5 engine
  `TypeError: unexpected keyword argument 'branches'`, the web conditional twin, the
  export call-site spy).
- **The loud flip**: with the engine fixed, the strict xfail
  (`test_finish_marginal_still_matches_ssi_with_a_probabilistic_branch`) failed as
  XPASS(strict) — the marker was removed in this commit, exactly as its reason field
  instructed. `grep` proves **zero live xfail markers remain in the whole tree** (the
  four remaining matches are prose describing already-flipped findings).
- **Equivalence pinned at the engine level**: branch-only, conditional-only (both
  metrics, probe solve included), and branch+conditional combined — each asserting
  `jcl.finish_cdf == ssi.cdf` (the FULL distribution) plus a non-vacuity guard
  (the branched SSI curve differs from the unbranched one, so the pin cannot pass on an
  inert branch).
- **Cost-inertness pinned**: multipliers ON, branch on/off → `cost_cdf` byte-identical,
  all five provenance figures equal, `finish_cdf` different.
- **Mutation battery 6/6 caught by the named test** (PYTHONPATH shadow of `src/`,
  import-origin canary per run, pristine controls green before/after, instruments
  md5-identical): augmentation dropped · fragnet cost fabricated · conditionals
  discarded · augmentation order swapped · route kwargs dropped · export kwargs dropped.
  (The originally planned "fragnet consumes a multiplier draw" mutant was replaced
  during design: fragnet uids always sort LAST, so a wasted trailing draw cannot shift a
  real task's draw — a mutant that cannot fail is not a mutant.)
- **Blast radius enumerated then measured**: all 8 JCL-consuming test files ran green
  (37 + 31 + 138 across the sweep); the mdash sentinel and the audit module were checked
  by name and are unaffected; no byte-freeze covers the edited panel paragraph.
- Full gate figures on the final tree in the handoff's Gate-at-close.
