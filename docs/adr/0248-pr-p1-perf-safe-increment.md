# ADR-0248 — PR-P1 (safe increment): analysis-cache LRU, summary-edge guard, SRA finish-rank reuse

## Status

Accepted. First increment of PR-P1 (the validated performance items from the committed
`00_REFERENCE_INTAKE/references/POLARIS_Independent_Audit_2026-07-15.md`). Delivers the subset that
is provably output-preserving and self-contained; the parity-critical and large items are deferred to
their own PRs, matching the audit's own **required-action-order**.

## Context

An ADR-0240 orchestrated verification (6 read-only agents, one per validated finding, lead-validated
against HEAD at v1.0.57) re-checked each perf item and rated its **output/parity risk** — decisive in
a testimony tool where a fast WRONG number is worthless (Law 2). Verdicts:

- **#4 analysis cache** — still unbounded (`SessionState.analyses` / `polished` are plain dicts, only
  `.clear()`d); ~1.2 GiB at 100 large versions. Fix parity-risk **none** (evicted → recompute
  byte-identical). Small.
- **audit-E summary-edge explosion** — `lower_summary_relationships` lowers summary↔summary logic to
  a leaf cross-product with no bound (O(N²) E' from a sparse source). Fix parity-risk **none** IF it
  only detects-and-discloses above a defensively-high ceiling and NEVER truncates (truncation would
  drop real logic edges → change CPM dates → Law-2 break). Small.
- **audit-C SRA finish-rank reuse** (part of #8) — `_build_result` re-ranks the identical finish
  vector once per activity (N−1 redundant sorts). Fix parity-risk **none** — a pure hoist feeding
  `_pearson` the same two rank lists. Small.
- **#8.1 compiled CPM topology** — parity-risk **HIGH** (reaches into the gate-locked CPM solver).
- **#9 MSPDI iterparse** — parity-risk **HIGH**, large; correctness hinges on whole-tree invariants
  (whole-file percent-lag resolution, cross-section UID refs). The audit itself says keep the DOM
  parser as a fallback until parity is proven, in its own PR.
- **#10 AI cancellation** — parity-risk **none** but a large new async job API + frontend feature.
- **#3 path adjacency cache** — the audit's own gate says "only if benchmarks show measurable
  benefit" (~8 ms for ten traces); a naive `id()`-keyed cache risks staleness on frozen copied
  models. Premature.

## Decision

Ship the three provably-safe items now; defer the rest with rationale.

1. **#4 — count-bounded LRU** (`web/app.py`). `analyses` and `polished` are backed by a std-lib
   `_LRUCache(OrderedDict)` (no `cachetools`): `get_lru` marks most-recently-used, `put` evicts the
   least-recently-used past `_ANALYSIS_CACHE_MAX` (48), all under the existing `_lock`. Only these two
   heavy caches are capped; `schedules` and the cheap `summaries` tier (portfolio scale) stay
   uncapped. An evicted entry recomputes deterministically, so no computed number can move — pinned by
   a recompute-equivalence test (evict → re-request → identical CPM finish / critical path / floats).
2. **audit-E — detect-and-disclose guard** (`engine/summary_logic.py` + `engine/cpm.py`).
   `lower_summary_relationships` projects the fan-out from lengths only and raises
   `SummaryLogicExplosion` past `SUMMARY_EDGE_CEILING` (250 000) rather than building — or silently
   truncating — a dense network. `compute_cpm` re-raises it as `CPMError` so the web layer degrades to
   a disclosed 422, not a 500/hang/OOM. Below the ceiling the lowering is byte-identical (the parity
   goldens carry no summary logic, so the guard is never even reached on them); a test pins that the
   ceiling sits far above a large-but-realistic summary schedule, so a genuine plan is never clipped.
3. **audit-C — finish-rank hoist** (`engine/sra.py`). `_build_result` computes
   `finish_ranks = _average_ranks(finishes_f)` once and calls
   `_pearson(_average_ranks(durs_f), finish_ranks)` per activity instead of
   `_spearman(durs_f, finishes_f)` — removing N−1 redundant sorts of the identical finish vector. A
   test asserts the two forms are `==` (not `approx`) across tied/zero-variance series; the SRA
   determinism + parity gates confirm byte-identical `SRAResult`.

**Deferred (each to its own PR, per the audit's required-action-order):** #8.1 compiled topology and
#9 MSPDI iterparse (both HIGH parity risk — need a full byte-identical proof against the CPM/float/
DCMA + MSPDI goldens, #9 with fresh XXE/billion-laughs security tests and the DOM parser kept as a
fallback); #10 cancellable AI generation-job API (large UX feature); #3 path-adjacency memo
(premature — behind the audit's "only if benchmarks show measurable benefit" gate and a real
`id()`-reuse staleness hazard). A dedicated performance/memory-regression harness (audit-F) is the
recommended enabling first step before any of the HIGH-risk items.

## Consequences

- Detailed-analysis and polished-narrative memory is bounded (no more unbounded growth at portfolio
  scale) with zero effect on any computed number.
- A pathological/hostile summary-to-summary schedule fails loud (disclosed 422) instead of hanging or
  OOM-ing; genuine schedules are untouched.
- Every SRA run drops N−1 redundant finish-vector sorts, byte-identically.
- `src/` changed (`app.py`, `sra.py`, `summary_logic.py`, `cpm.py`) → v1.0.57 → 1.0.58; wheel + 9
  installers rebuilt in lockstep. Full gate green incl. the `parity` gate.
- The remaining PR-P1 items stay queued with an explicit risk rationale, so a later session picks them
  up deliberately (harness first) rather than sweeping them in.
