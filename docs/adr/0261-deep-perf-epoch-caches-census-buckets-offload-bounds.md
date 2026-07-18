# ADR-0261 — Deep performance: epoch-keyed scope caches, CPM tier, census buckets, offload bounds

## Status

Accepted. Executes ADR-0257 §"Recorded" (the deferred deep-performance plan, P1–P5 + a latency
gate) under the Performance & Scalability / Large-Dataset Reliability role's discipline: **no
computed number may move** (Law 2). The operator's owed large dataset never arrived, so
measurement used the recorded fallback — reason from the map, verify number-identity on goldens:
a **160-hash battery** (5 scope states × 32 pages/APIs over the TP4 five-version series, run
twice to prove the instrument deterministic) stayed **byte-identical after every step**, and
`pytest -m parity` stayed green throughout.

## Decision

- **P1 — surgical scope invalidation.** `_invalidate_scope` no longer clears the
  analyses/summaries/polished caches; it resets only the identity memos (`_scoped`/`_matched`,
  plus the new P3 memo). The expensive caches are keyed by ``(key, scope-signature)`` —
  `_scope_signature()` mirrors `scope()`'s population branches exactly (a filter contributes only
  in reduce mode; the saved filter's full canonical dump + prompts, or the flat criteria repr;
  the Target UID) as FULL canonical text, never a hash (a collision could serve a wrong number,
  so there is nothing to collide). The identity anchor moves from the scoped object to the RAW
  schedule: toggling a filter/target ON and back OFF returns to **resident** results
  (identity-asserted in `tests/web/test_scope_epoch_cache.py`), while a re-upload under the same
  key still recomputes. The default epoch's key is the bare session key — byte-identical key
  shape to before for sessions that never touch a filter. Highlight mode shares the unfiltered
  epoch (it marks, never narrows) — asserted, so a reduced population can never leak into it.
- **P2 — the CPM tier.** New `SessionState.cpm_for` + `cpms` cache: `_solvable_versions` (the
  every-multi-version-page population pass) now obtains ONLY the solve per version instead of
  the monolithic `_compute_analysis` (CPM + audit + baseline + float-bands + completion +
  findings + narrative + activity grid). `_compute_analysis(sch, cpm=…)` accepts the cached
  solve, so a later full analysis reuses it — one network solve per version per epoch, gated by
  count in `tests/perf/test_perf_regression.py`.
- **P3 — Performance page memo + census buckets.** `_perf_version_block` memoises each version's
  serialized G1–G5 block (census/flow/burden/DRM — pure functions of the scoped version) per
  scoped-object identity; identity-keyed memos die with the epoch (cleared with the scope memos
  and wipe), so staleness is structurally impossible. A `/performance` re-render computes zero
  census passes (count-gated). The quads recompute each render — cheap linear passes whose HMI
  leg depends on the PRIOR version's status date. `work_to_go_census` itself is bucketed to
  **O(tasks + months)** via per-counter diff arrays over the contiguous month axis + one
  prefix-sum pass — a pure re-ordering of the same integer additions, pinned equal to the
  verbatim per-month-scan oracle (kept in the test) across mixed types, dateless/baseline-only
  tasks, and the 360-month truncation clamp.
- **P4 — compute outside the session lock.** `analysis_for` / `summary_for` / `cpm_for` /
  `_perf_version_block` now run the engine (and the summary tier's SQLite I/O) OUTSIDE
  `_lock`, storing under it — one long analysis no longer serialises every concurrent request.
  Dict operations stay atomic under the lock (the D18 discipline); a concurrent duplicate
  compute of one epoch is deterministic and last-write-wins; a wipe racing a store leaves at
  most one orphaned, never-consulted, LRU-evictable entry.
- **P5 — bounded offload + OAT sweep.** `run_offloaded` gains `OFFLOAD_TIMEOUT_S` (30 min —
  "never hang forever", not run-policing): on expiry the pool is torn down and a clear,
  actionable error surfaces (the SRA routes already render it); recovery on the next call is
  test-pinned. The OAT sensitivity sweep (two CPM solves per candidate) is capped at the WEB
  boundary — above `_OAT_MAX_ACTIVITIES` (1500) only the largest-ML-remaining candidates are
  swept, DISCLOSED in the payload and on the panel (never a silent subset); the engine is
  untouched and sweeps below the cap are byte-identical.
- **The latency gate ADR-0249 excluded.** Deterministic count gates for P1/P2/P3 (recompute
  counts, not wall-clock — the ADR-0249 anti-flake philosophy) plus one RELATIVE timing gate
  (epoch hit strictly cheaper than the compute it replaces — relative on one machine, like the
  existing tracemalloc gate, so it cannot flake on an absolute baseline).

## Measured (synthetic 5×1200-task set; before → after)

Cold `/performance` 0.674s → 0.066s (~10×); warm `/performance` 0.033s → 0.015s; the
filter-set→render→clear→render sequence 0.417s → 0.079s (~5×). Numbers unchanged everywhere
(the 160-hash battery, zero diffs at every step).

## Consequences

- The "select something and wait forever" lag class is addressed at its recorded roots; the
  operator's five-project real run should re-validate on their machine (their large dataset and
  the PowerShell log remain owed).
- Deliberately NOT done: making `_Analysis` fields lazy (P2's broader form) — the blast radius
  (error-timing semantics at dozens of consumers) wasn't worth it once the population pass
  stopped building full analyses; reconsider only if profiling shows a page paying for unused
  analysis fields. The in-process offload FALLBACK path still has no timeout (same interpreter —
  cannot be interrupted safely); the call-site size caps bound it instead.
- Version 1.0.67 → 1.0.68; wheel + 9 installers in lockstep. No engine math changed; parity
  green; the census rewrite is pinned to its oracle inside the test suite.
