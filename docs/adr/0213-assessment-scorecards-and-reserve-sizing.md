# ADR-0213 — Assessment scorecards (NASA STAT / GAO-10 / SRA-readiness) + reserve sizing

## Status

Accepted. Operator directive 2026-07-13: "add all the remaining functionality … mentioned in the
Gaps worth adding (ranked) [issue #331] if they don't already exist … in one PR." This PR delivers
the lowest-fidelity-risk, highest-value slice of that backlog — the consolidation scorecards
(#3 NASA STAT, #4 GAO 10-practices, #5 SRA-readiness gate) and buffer/target-date reserve sizing
(#7). The heavier parity-gated statistical items (#1 JCL/FICSM cost co-sampling, #2 the correlation
matrix / risk-driver UI, #6 scenario persistence, and the Hulett-deck sampling variants) are tracked
as the dedicated validated follow-on the issue's own sequencing calls for, and are **not** in this PR.

## Context

Issue #331 distilled two committed reference decks (INT-02 ICEAA; a SEER SRA primer) into seven
ranked gaps. Three of them — NASA STAT, the GAO Schedule Assessment Guide's ten best practices, and
an SRA-readiness gate — are, in the issue's own words, "mostly **consolidation** + a few new checks"
of metrics the engine already computes and gate-locks against the Fuse/DCMA goldens. A fourth,
buffer/target-date recommendation, is percentile arithmetic over the SRA finish distribution the
`/sra` page already simulates. None of the four needs new metric *math*, so none carries the fidelity
risk (Law 2) that the cost co-sampling / branching / correlation-matrix items do — which is why they
are separable into their own validated phase.

The tool already surfaces every underlying figure piecemeal (the DCMA-14 audit, logic-integrity
checks, the SRA CDF), but not organized under the three named frameworks an assessor reaches for, and
not as an explicit reserve-sizing answer to "how much buffer protects the committed date at P70/P80?"

## Decision

Add `engine/scorecards.py` — a **pure consolidation layer**, disciplined so that **every scored
figure equals a number the engine already computes**:

- `compute_nasa_stat` / `compute_gao_scorecard` / `compute_sra_readiness` return frozen `Scorecard`
  / `ScorecardCheck` records. A scored line's status is taken **verbatim** from the gate-locked DCMA
  audit (`_audit_status` maps the `AuditCheck` straight through — no re-scoring) or from an
  unambiguous structural rule (a summary carrying logic, an actual after the data date → PASS iff
  the count is 0). Genuinely-new lines are trivial deterministic model scans (missing-predecessor vs
  missing-successor split, milestone / manual-task / estimated-duration counts, the actuals-after vs
  forecast-in-past split of DCMA-09) with **cited offenders**. Where a framework defines no numeric
  pass bar, the line is `INFO` (a count, never a fabricated pass/fail) and is excluded from the pass
  rate — so `Scorecard.score` is honest.
- `reserve_recommendation` sizes the schedule reserve to hit a committed **project finish** date at
  P50/P70/P80/P90 by reading the finish offset off the existing SRA CDF (nearest-rank quantile) and
  differencing against the committed date on the schedule calendar. Pure arithmetic — no new
  simulation, no new statistics.

Web: a new `/scorecards` page (a chapter-02 "Can we trust the plan?" secondary) renders the three
ribbons for a chosen version and a reserve card fed by an on-demand `/api/scorecards/buffer` endpoint
(the Monte-Carlo runs off the page-load path, like the OAT sensitivity). Excel/Word export of the
three scorecards; a vendored `scorecards.js` drives only the reserve fetch (air-gap safe, Law 1). The
GAO/STAT chips reuse the existing stoplight vocabulary plus a theme-token `.sl-info` variant.

## Consequences

- The assessor sees DCMA-14, NASA STAT, GAO-10 and SRA-readiness side by side, each figure traceable
  to its already-validated source (the provenance string on every line), and can defend a committed
  date's contingency at a stated confidence — all without any new metric that could diverge from the
  reference tools.
- No engine parity surface changed: the scorecards read the DCMA audit and SRA CDF; the byte-frozen
  `compute_sra` / DCMA paths are untouched. `reserve_recommendation` is unit-tested with exact CDF
  arithmetic; the scorecards are pinned to equal the DCMA audit statuses they consolidate.
- The heavier #1/#2/#6 + Hulett-deck statistical items remain open in issue #331 for a dedicated,
  reference-validated phase — explicitly out of scope here to keep this PR within the fidelity bar.
