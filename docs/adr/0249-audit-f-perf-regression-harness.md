# ADR-0249 — audit-F: a deterministic performance/memory-regression harness

## Status

Accepted. Operator-selected next step after PR-P1's safe increment (ADR-0248). Closes audit finding
**F** ("No dedicated performance regression gate found") from the committed
`00_REFERENCE_INTAKE/references/POLARIS_Independent_Audit_2026-07-15.md`, and is the enabling step
the audit's required-action-order (#3) puts before the HIGH-risk perf optimizations.

## Context

The repo has extensive correctness, parity, security, and UI tests but no gate that fails when a
performance property regresses. So a future change could silently un-hoist the SRA finish-rank
(ADR-0248 audit-C) or revert the analysis-cache to an unbounded dict (ADR-0248 #4) and every existing
test would still pass. The audit listed six perf/memory concerns (import peak memory, CPM latency,
100-version cache memory, SRA latency/memory, filter-toggle time, AI cancellation).

The hard constraint is **CI reliability**: a wall-clock latency gate flakes across CI machines (the
3.11 + 3.13 matrix, shared runners), and a flaky gate is worse than none — it erodes trust and gets
disabled. So the harness must be **deterministic**.

## Decision

Add `tests/perf/test_perf_regression.py`, gating the *already-shipped* perf properties with
**deterministic** assertions only — operation counts and cache residency, never timing:

1. **audit-C — SRA finish-rank reuse.** Spy `_average_ranks` across one `compute_sra`: for `N`
   activities it must be called exactly `N + 1` (one hoisted finish rank + one duration rank each),
   not `2N`. Un-hoisting the finish rank (the pre-ADR-0248 form) makes it `2N` and fails.
2. **#4 — analysis-cache residency bound.** After opening detailed analysis for `3 × cap` versions,
   `len(SessionState.analyses) <= _ANALYSIS_CACHE_MAX` (memory ∝ residency), and the most-recently
   opened version is still resident (the LRU keeps the working set hot). Reverting the LRU to a plain
   dict makes residency equal the version count and fails.
3. **#4 — relative memory demonstration.** A `tracemalloc` **relative** comparison (a bounded cache
   traces a lower peak than an unbounded one over the same workload), robust because it asserts a
   direction, not an absolute ceiling — so it never flakes on machine-specific memory.

**Deliberately excluded** (documented in the harness): wall-clock latency gates for CPM / SRA / filter
toggle (need a benchmark harness with warm-up + a machine baseline — a flaky fit for a unit gate) and
the deferred-feature memory items — import peak memory rides #9 (MSPDI streaming) and AI-cancellation
behavior rides #10, each gated by its own PR when that work lands.

Test-only: no `src/` change, so the version stays 1.0.58 and the wheel / 9 installers are untouched.

## Consequences

- The two shipped optimizations (audit-C hoist, #4 LRU) are now regression-gated: a change that undoes
  either fails CI, deterministically.
- The gate never flakes — it asserts operation counts, residency, and a relative memory direction, so
  it is stable across the CI Python matrix and shared runners.
- The remaining audit-F concerns are explicitly parked against their owning PRs, so a later session
  extends the harness alongside the HIGH-risk work rather than pinning today's un-optimized status quo.
