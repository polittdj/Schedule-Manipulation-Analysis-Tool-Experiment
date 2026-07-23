# ADR-0281 — dashboard card tier + single-flight + single-computation analysis

Status: accepted (2026-07-23)

## Context

A read-only audit-validation session (2026-07-23) re-verified a ChatGPT "5.6 Sol" performance audit
against HEAD `f551b01` (v1.0.90), built characterization tests for every claim, and prototyped the
endorsed fixes in a sandbox. Four mechanisms were confirmed (all reproduced against the untouched
tree — the numbers below are measured, not estimated):

1. **The Dashboard builds a full `_Analysis` per loaded version, and thrashes the analysis LRU past
   its cap.** `_dashboard_data` calls `analysis_for(key, sch)` for every version but uses only **3
   of `_Analysis`'s 8 fields** — `cpm.project_finish`, `float_bands["float_total_0"]`, and
   `audit.checks`. Once the loaded-version count crosses `_ANALYSIS_CACHE_MAX` (48) the LRU evicts
   on every pass, so **every dashboard refresh recomputed every version, forever** (measured: N=50
   warm refresh 8.2–8.6 s and 50 full analyses *each* refresh; N=40 warm 0.13 s / 0 recomputes — a
   ~65× cliff from crossing the cap).
2. **No single-flight.** `analysis_for` / `cpm_scoped_for` compute OUTSIDE the session lock
   (ADR-0261 P4) and store last-write-wins, so N concurrent cold requests for one key ran N full
   computes (measured: 8 threads → 8 `_compute_analysis`).
3. **Each cold `_compute_analysis` recomputed its deterministic dependencies several times.** The
   direct `audit_schedule` + `compute_baseline_compliance`, then `recommend()` recomputed both
   internally, then `build_narrative()` called `recommend()` again — **3× audit, 3× baseline
   compliance, 2× recommend** for one analysis.
4. **Upload dedup was O(M²).** The `/upload` byte-identical dedup rescanned the whole
   `content_hashes` map for every file (M(M−1)/2 scanned pairs).

The audit was directionally right on all three P0/P1 mechanisms but had to be re-grounded against
HEAD: it was stale on ADR-0280 API names (it referenced the retired `dcma_exclude_milestones`; the
live knob is `SessionState.dcma_acumen_parity`, scope token `A=1`, engine kwarg `acumen_parity`),
wrong on an "importer `strptime` hotspot" (the importer already uses `datetime.fromisoformat`), and
cited an impossible 63-hex-character "SHA-256". Everything below is written in ADR-0280 terms and
was re-proven in the sandbox before adoption. The **hard acceptance line is byte-identical dashboard
payloads** (Law 2: fidelity over speed).

## Decision

Four fixes, gated by characterization tests committed first (`tests/web/test_dashboard_perf_contract.py`,
`tests/web/test_upload_dedup_scaling.py` — op-count/equality pins per ADR-0249, failing on the
untouched tree):

- **A′ — dashboard card tier.** A frozen `_DashCore` holds ONLY the three projected primitives the
  card renders (the finish offset, the zero-float band's count/value, and `(metric_id, name,
  status)` per DCMA check) — never the heavy engine objects (a `MetricResult`/`AuditCheck` pins
  citation tuples), so an entry is ~1 KiB. `SessionState.dash_cores` is a plain dict epoch-keyed by
  the same `(key, scope-signature)` as `cpms` (a filter/target/parity change re-keys automatically),
  **not** the capped LRU — the whole point is that it never evicts under the cap.
  `dashboard_core_for` has three tiers: a resident dash-core → returned as-is; a resident full
  analysis → projected down with no engine work; otherwise only the DCMA audit + zero-float band are
  computed off the single-flighted CPM solve. `_dashboard_data` reads the core; nothing else in it
  changes. Cleared in `/session/wipe` alongside `analyses`/`summaries`/`cpms`.
- **B — single-flight striped locks.** 64 fixed `threading.Lock` stripes; `_stripe_for(ck)` hashes
  the epoch key to a stripe. On a cache miss, `analysis_for` and `cpm_scoped_for` (which serves
  `dashboard_core_for`) take the stripe OUTSIDE `_lock` (stripe → `_lock` ordering, never nested),
  **re-derive `ck`/`gen`/`parity` under `_lock` inside the stripe** (a scope flip while queued
  recomputes under the CURRENT key, never a stale one), re-check the cache, compute once, and store
  under the existing `wipe_gen` guard. Exceptions propagate to every waiter's caller (the
  `with`-scoped locks release) and a later call recomputes cleanly; unrelated keys stay concurrent
  (a rare stripe collision only serialises two unrelated cold computes, never yields a wrong number).
- **C — compute each deterministic dependency once.** `recommend()` gains
  `precomputed_audit` / `precomputed_compliance`; `build_narrative()` gains `precomputed_findings`;
  every existing call site keeps its behaviour (defaults `None`). `_compute_analysis` computes the
  audit + baseline compliance once and threads them through, and hands the findings to the narrative.
  **Deliberate pin:** in Acumen-parity mode the recommender still derives findings from the DEFAULT
  (non-parity) audit — today's behaviour, kept byte-for-byte — so the precomputed audit is reused
  only in default mode; parity mode passes `None` and the recommender recomputes the default audit
  itself (1×/1×/1× default; 2×/1×/1× parity). Whether findings *should* follow the parity audit is a
  separate product question, filed as **ADR-0282**, not decided here.
- **D — linear upload dedup.** Build a reverse index `(content-hash, folder-context) → first-loaded
  key` once per batch under `_lock`, look it up in O(1) per file, and keep it in lockstep as files
  are accepted. `setdefault` keeps the first-loaded key on a collision — byte-identical to the old
  first-match scan — preserving the rename/folder-context rules exactly.

## Consequences

- **No number changes.** The dashboard payload is byte-identical (golden SHA-256 pinned for two real
  2,126-task fixtures, parity ON, and the unsolvable-`CPMError` card); findings and narrative are
  byte-equal to the plain `recommend`/`build_narrative` path; `pytest -m parity` and the golden
  suites stay green. This is a speed/robustness change only (Law 2).
- **Measured (sandbox, 2,126-task fixture):** dashboard N=50 warm 8.2–8.6 s → 0.14 s with zero engine
  work (and the LRU cliff cannot exist at any N); 8× concurrent cold same key 8 computes → 1; cold
  `_compute_analysis` 0.253 s → 0.098 s (audit/compliance/recommend 3×/3×/2× → 1×/1×/1×); upload
  dedup 16→32 files 120→496 scanned pairs → 0.
- **`dash_cores`/`cpms` are plain dicts** that accumulate one small entry per (version, epoch);
  orphan epochs are bounded by wipe, exactly like the existing `cpms`/`summaries` tiers. A byte-aware
  bound is deferred (measure hit-rate/weight first — never another slightly-too-small LRU).
- **Deferred (separate PRs, deliberately not folded in):** Fix E (active-population scoping of the
  target control + endpoint banner — a real cross-project UID leak, its characterization test is
  committed `xfail`); lazy status-UID payload trim; home.js bounded-concurrency pre-read; the
  manifest-projection memo; instrument-then-budget the `cpms`/`summaries` tiers; an MPP capability
  probe; importer profiling; the `web/app.py` monolith split. See the validation prompt for the
  ordered backlog.
