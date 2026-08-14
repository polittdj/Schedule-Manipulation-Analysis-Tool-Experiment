# ADR-0401 — The sandbox wipe and the first JCL battery

Status: accepted (2026-08-14)

## Context

Operator kickoff (2026-08-14): STEP ONE, verify the kickoff is not stale and the work not
already done; then take `polittdj/SMAT-SANDBOX` to a greenfield state and clone this
repository into it as a backup; and "find a way to test if the JCL function of the program
functions correctly by creating pass and fail tests that you use in a sandbox."

STEP ONE measured green before anything moved: HANDOFF / highest ADR 0400 / v1.0.201 matched
disk and `origin/main` (`be9b3c1`); the designated branch (`claude/smat-sandbox-greenfield-binedp`)
carried no prior work; SMAT-SANDBOX held a 2026-07-11 snapshot (768 files, "Add files via
upload", three stale branches, six CLOSED July PRs); and NO mutation battery had ever targeted
`engine/jcl.py` (searched SESSION-LOG's 14,191 lines and every ADR). The JCL function is
`engine/jcl.py` — ADR-0269's FICSM joint cost-&-schedule confidence engine.

## Decision A — SMAT-SANDBOX: mirrored, then wiped EMPTY at operator direction

1. **DISC-01 gate first.** Visibility measured `private` (can_push true) before any push —
   moving this repository's history (which carries the DISC-01 strings) into it kept the
   mitigated posture. Law 1: a push of already-published commits stages nothing new; the
   committed intake is non-CUI (ADR-0152).
2. **The mirror was built and verified.** A sorted `ls-remote` heads+tags comparator was
   observed RED before (15 differing lines) and GREEN after: all 9 experiment branches
   byte-identical on the sandbox. Mechanism: the proxy 403'd whole-pack pushes, so history
   went over as 46 first-parent slice pushes plus per-branch pushes.
3. **The 403 diagnosis REVERSED.** First read as a body-size cap; measurement refuted that —
   a ZERO-object single-ref DELETION push also 403s, while every additive push of any size
   succeeded. **The proxy blocks ref deletions, full stop**; every failed push had carried
   `--prune`. (The first "push exit: 0" was also a `| tail` exit-mask — the comparator's RED
   caught it.)
4. **Mid-session the operator countermanded.** The mirror's force-pushes had bumped the
   sandbox's old CLOSED July PRs with "force-pushed" notices; the operator ordered: get out
   of SMAT-SANDBOX and make it a greenfield. Final state, verified by `ls-remote`: **every
   branch (12 names) force-pointed at one parentless empty commit `91b3395`** — no project
   content or history reachable anywhere in that repository; the `sandbox` remote and the
   local clone removed. **The backup objective is explicitly ABANDONED — no backup of this
   repository exists.** The 12 branch NAMES are proxy-undeletable; deleting them (or the
   repo) is a GitHub-UI action for the operator.

## Decision B — the first JCL battery, and the joint-statement closure module

Method (QC-1 throughout): a scratchpad sandbox copy of `src/ + tests/ + pyproject.toml`;
an import-origin canary asserted before every battery; the instrument md5-restored and
verified after every mutant; suite = `test_jcl.py` + `test_jcl_web.py` (+ `test_lhs.py` /
`test_sra_view.py` for survivor confirmation). Baseline 29 passed in ~5 s.

**Round 1 — 33 mutants** (16 lead-designed; 14 independently workflow-designed under
ADR-0240 — three Map agents + one designer, every prediction lead-re-measured; 3 written to
prove the new module's own teeth): 10/16 lead mutants killed by the existing suite; the six
survivors re-run against the WIDER suite downgraded L13 (`sampling` passthrough — killed by
nine `test_lhs` tests by name; a survivor of a narrow suite is a hypothesis, not a finding).
Nine confirmed gaps: scl/ccl redefined to `both/n`, the quadrant-counter swap, frontier
`k` floored (every prior fixture had INTEGER `confidence*n`), the default target rounded
before comparison (every prior EAC exact at 2dp), the `iterations>=1` gate, the ADR-0308
completed-task guard inside compute_jcl's risk loop, the risk-replacement moved after the
cost loop (the joint coupling itself), the cost-CDF step `idx/n`, the confidence floor,
and the seed stamp. Closed in **`tests/engine/test_jcl_joint_statement_closure.py`**;
regression: 32/33 killed by name in the three-module suite + L13's guard in `test_lhs`.
Two fixture lessons paid for en route: the first quadrant fixture FAILED INTACT because
`cost_only` was STRUCTURALLY empty (cost is monotone in the driver that also drives
lateness — the FICSM multipliers decouple it; targets then measured to populate all four
quadrants 99/13/21/67 with an 8.24 boundary margin), and the frontier fixture needed
fractional `confidence*n` (115 × 0.70) to make flooring observable.

**Adversarial round (the HOOK-01 pattern held again):** two attacker agents + one
test-critic vs the mutation-green first revision. **All 12 attack mutants survived** —
independent convergence on the same population holes (both attackers wrote the identical
multi-risk edit): gate precedence, multi-risk impact summing, the `max(0,·)` opportunity
floor, the completed-predicate divergence (`actual_finish` at pc<100), focus-vs-project
finish (every fixture's focus was the network sink), the `ti+td>0` costed predicate at
τ=0, the `spent + (ti + td)` float association, the latest-stored-finish anchor fallback,
`sunk_total` dropping unbudgeted actuals, `cost_p80` off-by-one (all prior percentile pins
degenerate), and the frontier grid truncated at P90 (the constant itself). Closed with
eight new tests + two fold-ins, each intact-probed first; the association mutant survived
even the first closure attempt — **`spent = 0.0` makes any re-association exact**, so the
fixture records a 0.01 spend at values where the ulp genuinely moves (red-first caught the
no-teeth fixture). Critic findings all addressed: explicit seeds wherever a liveness or
margin precondition rides the sampled shape; two discriminating-power self-checks added
(the k-rank step and the multiplier-swap EAC delta past 2dp).

**Final:** 21 tests, intact green; the combined 45-spec battery (44 distinct edits) kills
every mutant by name — 44 in the three-module suite, L13 in `test_lhs` — and the module
ALONE does not re-kill what the older tests already own (scoping run). The touched web
module (`test_jcl_web.py`) runs 9 passed + 1 xfailed.

## Decision C — JCL-BR-01: session branches reach the SSI run but not compute_jcl

Measured end-to-end on the real routes: before any branch, the JCL and SSI finish marginals
are equal; after ONE probabilistic branch is POSTed (`/sra/branch`, 2→4, p=50%, 3/5/8 d),
the SSI percentiles move (2025-01-16/23/28/29) and the JCL percentiles do not
(2025-01-15/20/22/23). `compute_jcl`'s signature carries no branch/conditional inputs and
`/api/sra/jcl` (app.py:5908-5916) passes none, while the SSI route passes both (ADR-0273/0274)
— so the football chart's schedule axis silently leaves the SSI S-curve exactly when
branches are configured, violating ADR-0269's "one story" guarantee in that configuration.
Landed as the strict xfail `test_finish_marginal_still_matches_ssi_with_a_probabilistic_branch`
in `tests/web/test_jcl_web.py` (the ADR-0395 pattern: a fix flips it loudly; remove the
marker in that commit). The fix is design-gated SHIPPED code — carry the branches through
`compute_jcl` and extend the equivalence pins to branch configurations, or honest-gate the
JCL panel while branches exist — version bump + wheel + nine installers in that unit
(ADR-0148). Conditional branches share the gap.

## Also recorded (semantics audit, lead-verified; docs follow-ups, no code change)

- ADR-0269's "additive risks" wording predates ADR-0359's measured replace semantics; code
  and tests are correct, the ADRs stand as history.
- `web/help.py`'s JCL `eac` glossary formula omits the time-independent (1−τ) term;
  regenerate METRIC-DICTIONARY when fixed.
- The "EAC = AC + (BAC − EV)" gloss holds under clean EVM data only.

## Consequences

- Tests + docs only: **v1.0.201 and SCHEMA 2.11.0 unchanged**, no wheel/installer rebuild
  (ADR-0395/0399/0400 precedent).
- xfail census: `tests/audit` still exactly one live xfail (TEST-01); the NEW strict xfail
  lives in `tests/web` (JCL-BR-01).
- SMAT-SANDBOX is an empty greenfield; **no backup of this repository exists there**, and
  the operator owns deleting the 12 residual branch names (or the repo).
- The JCL engine's semantic surface is battery-guarded: an engine edit that changes any
  closed family goes loudly red by name.

## Verification pointers

Every flip list quoted above is a battery's printed output (never a prediction); the
instruments were md5-verified restored after every mutant and the import-origin canary
asserted per run. The branch-divergence probe ran through the real `/sra/branch` +
`/api/sra/ssi` + `/api/sra/jcl` routes; its durable encoding is the strict xfail plus this
ADR. NASA NPR 7120.5F / CEH v4.0 App. J and GAO-16-89G remain the JCL formula anchors
(ADR-0269).
