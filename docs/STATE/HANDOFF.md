# Handoff — 2026-07-18 (deep performance ADR-0261: epoch-keyed scope caches, CPM tier, census buckets, offload bounds; v1.0.68; highest ADR 0261)

> ## STATUS (current) — ADR-0261 executes ADR-0257 §"Recorded" (deep-perf P1–P5 + the latency gate), Law-2-proven: a 160-hash battery (5 scope states × 32 pages/APIs, TP4 goldens, instrument proven deterministic by double-run) stayed BYTE-IDENTICAL after every step; parity green throughout. Measured on the synthetic 5×1200-task set: cold /performance 0.674s → 0.066s (~10×), filter-toggle render sequence 0.417s → 0.079s (~5×). Version 1.0.67 → 1.0.68 (wheel + 9 installers in lockstep).
>
> - **P1 surgical invalidation:** `_invalidate_scope` resets only the identity memos; analyses/
>   summaries/polished are keyed by `(key, scope-signature)` (full canonical text, never a hash)
>   with the RAW schedule as identity anchor — filter/target toggles flip between RESIDENT epochs
>   (identity-asserted in `tests/web/test_scope_epoch_cache.py`); highlight shares the unfiltered
>   epoch; a re-upload still recomputes; default-epoch keys are byte-identical to before.
> - **P2 CPM tier:** `cpm_for` + `cpms` cache — `_solvable_versions` (every multi-version page)
>   obtains ONLY the solve per version; `_compute_analysis(sch, cpm=…)` reuses it later. One solve
>   per version per epoch (count-gated).
> - **P3:** `_perf_version_block` memoises each version's G1–G5 block per scope epoch (a
>   /performance re-render runs ZERO census passes — count-gated); `work_to_go_census` bucketed to
>   O(tasks+months) via diff arrays + prefix sums, pinned EQUAL to the verbatim per-month-scan
>   oracle kept in the test (mixed types, dateless, baseline-only, 360-month truncation clamp).
> - **P4:** engine compute + summary SQLite I/O now run OUTSIDE the session `_lock` (store under
>   it; D18 atomicity kept; duplicate computes deterministic, last-write-wins).
> - **P5:** `OFFLOAD_TIMEOUT_S` (30 min) — a wedged worker can never hang a request forever (pool
>   torn down, actionable error, recovery test-pinned); OAT sweep capped at the WEB boundary
>   (`_OAT_MAX_ACTIVITIES` 1500, largest-ML-remaining, DISCLOSED in payload + panel; engine
>   untouched; below the cap byte-identical).
> - **Latency gate (the ADR-0249 exclusion closed):** deterministic P1/P2/P3 recompute-count gates
>   + one RELATIVE timing gate (epoch hit < the compute it replaces) in
>   `tests/perf/test_perf_regression.py` — no absolute wall-clock, nothing to flake.
> - **Deliberately NOT done:** lazy `_Analysis` fields (blast radius vs. gain once the population
>   pass stopped building full analyses — revisit only on profiling evidence); a timeout on the
>   rare in-process offload FALLBACK (uninterruptible same-interpreter; size caps bound it).
> - **Still OWED by the operator:** the PowerShell crash log + their large dataset — re-validate
>   the lag fix on their machine (five projects, one large) when provided.
> - **State:** v1.0.68; **ADR-0261** highest; wheel + 9 installers in lockstep; branch
>   `claude/portfolio-data-integrity-gantt-pf30ef` (restarted from the #397 squash; draft PR).
> - **NEXT:** /mission 1-version tile degrade (ADR-0258 known pre-existing); Portfolio US-map/site
>   drill when the Claude-Design prompt arrives; exhaustive per-widget + five-large-file stress
>   with the operator's dataset; THEN the standing queue: #13 XER per-task calendars (PARKED) →
>   SEC-2/SEC-3 hardening → ADR-0251 family-B unify → zero-margin SRA toggle → roles i18n catalog.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
