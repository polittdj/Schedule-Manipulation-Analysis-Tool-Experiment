# ADR-0132 — Audit-cluster remediation, batch 2 (H2 accusation guard + M5/M7/L3)

## Status

Accepted.

## Context

ADR-0131 (batch 1) closed the CRITICAL and the importer/serialization cluster the re-audit
(`audit/VERIFICATION-REPORT.md`) found orphaned. Batch 2 finishes the in-environment remainder: the AI
prose-tamper gap (H2), the days↔% rounding mismatch (M5), the path-filter perf jank (M7), and the offload
teardown gap (L3). The operator also set the AI direction: *use the engine's computed metrics fully, derive
further metrics from them when helpful, but only by industry-standard methods and verified for accuracy.*
H2 is implemented to serve that accuracy bar — it blocks an **unverified accusation**, not legitimate
derivation.

No parity number moves (no engine/metric math changes).

## Decision

1. **H2 — the narrative gate rejects an introduced accusation.** `ai/citations.reattach` already kept the
   engine's verbatim sentence unless a rephrase preserved every figure; it now *also* rejects a rephrase
   that **introduces an accusatory/intent term the source lacked** (`introduces_loaded_terms`: fraud,
   deliberate, intentional, conceal, falsify, sabotage, malicious, willful, deceptive, … — a high-precision
   list of *conclusions the engine never draws*). A loaded term already present in the engine's own
   sentence (e.g. a `manipulation` finding) is fine; only *introduced* ones force the verbatim fallback.
   This guards accuracy/testimony-defensibility without constraining legitimate numeric/analytic
   derivation (which carries none of these words) — consistent with the operator's "derive, but verified"
   direction. CLAUDE.md's "guards digits, not prose" note is updated to record the new accusation guard.

2. **M5 — days↔% client/server rounding aligned.** Both sides now round each per-task remaining-days value
   at the **same precision** (`_REMAIN_DAYS_DP = 6`) before averaging: the server `SF_REMAIN_DAYS` payload
   and `_affected_avg_remaining_days` both use it, so the auto-derived days↔% magnitudes match exactly for
   sub-day tasks (previously the server averaged unrounded values while the client averaged the 3-dp
   payload, diverging). 6 dp keeps sub-day tasks from collapsing to zero while matching exactly.

3. **M7 — path-filter no longer janks.** The `pathFilter` `input` handler is **debounced** (~140 ms) so a
   full `tbody` rebuild + freeze-style pass runs once per typing pause instead of every keystroke on the
   ~1700-row grid; `freezeColumns` additionally **skips redundant per-cell style writes** (only touches the
   DOM when an offset actually changes), cutting churn on rows that persist across repaints.

4. **L3 — offload worker torn down on any exit.** `web/offload` registers its pool teardown (`_reset`) with
   `atexit`, so the worker process is reaped on the browser-gone watchdog / any non-`/api/shutdown` exit,
   not only the Quit route. The explicit `shutdown_offload()` call on the Quit route is unchanged.

## Consequences

- **No parity number moves** (parity gate green); each fix is pinned by a new/updated test.
- The forensic narrative can no longer have an unverified *intent/fraud* conclusion slipped in by the local
  model — closing the H2 prose gap while leaving non-accusatory polishing and legitimate metric derivation
  intact.
- The days↔% derive is deterministic across client and server; the path filter is responsive on large
  schedules; the offload child is reliably reaped.
- **The audit cluster is now fully remediated in-environment.** What remains is artifact-gated only
  (`audit/PARK-LIST.md`: Fuse/SSI/.aft/.mpp), plus F-11 (interpretive-mode role re-labeling), which stays
  an accepted, documented design choice.

## Alternatives considered

- **A broad accusation denylist (incl. `manipulation`).** Rejected: the engine legitimately emits
  manipulation findings, so a broad list would suppress faithful narrative. The list is scoped to
  intent/conclusion terms the engine never asserts, and only flags *introduced* ones.
- **Emit higher-precision SF_REMAIN_DAYS but keep the server unrounded (M5).** Rejected: only rounding both
  sides at the same point makes them provably equal; unrounded-vs-rounded still drifts at the boundary.
- **A FastAPI shutdown event for L3.** atexit is the broader net (covers non-graceful exits the ASGI
  shutdown event misses); the two are complementary, and atexit alone closes the documented gap.
