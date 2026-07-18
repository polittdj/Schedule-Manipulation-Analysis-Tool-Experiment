# ADR-0263 — session-consistency audit remediation (epoch pairing, wipe finality, upload locking, summary-margin overlay)

## Status

Accepted. Remediates the confirmed findings of this session's full handoff-verification audit
(ADR-0240 protocol: a ten-agent Ultracode sweep over every ADR-0261/handoff claim, every
major finding re-verified by the lead against code and executable tests before any change).
The audit CONFIRMED the ADR-0261 record at large — P1 signatures/keys/residency, P2 tier, P3
memo + census-oracle equality, P5 bounds, the latency gate's determinism, version/installer
lockstep, parity green (44 parity tests; AFT pinning live against the committed Bible) — and
surfaced the defects below, each reproduced deterministically before it was fixed.

## The confirmed defects, and the decisions

1. **Mixed-epoch pairing (MAJOR).** Callers paired an epoch-keyed compute with a SEPARATELY
   fetched scope — `cpm_for(key, sch)` then `st.scope(sch)`, or `analysis_for` then
   `st.scope(raw)` — two lock windows with a gap a concurrent filter/target change could land
   in, pairing an old-epoch solve with a new-epoch population. Worst case: `_perf_version_block`
   memoised that poisoned pairing under the NEW epoch's identity and re-served it for the rest
   of the epoch (persistent wrong numbers — the one REFUTED sub-claim of ADR-0261's
   "staleness is structurally impossible"). **Decision: make the inconsistent pair
   unrepresentable.** `_Analysis` now carries `scoped` — the exact schedule every field was
   computed from — and every pairing call site uses it; the population pass uses the new
   `SessionState.cpm_scoped_for` which resolves the scoped object and the epoch key in ONE
   lock window and solves exactly that object (`cpm_for` delegates to it). Ten call sites
   swapped; each also saves a lock round-trip.
2. **Wipe finality (MAJOR).** The wipe's contract is "nothing of the operator's data survives
   the reset" — but a compute in flight during the wipe could store AFTER it: worst,
   `summary_for` re-inserted the derived-metrics blob into the on-disk CUI cache after the
   wipe's `clear()` (which also ran outside the lock), and the wipe's own tail reset the SRA
   register/AI config after releasing the lock. **Decision: wipe generations.**
   `SessionState.wipe_gen` bumps inside the wipe's locked block, the on-disk `clear()` and the
   SRA/AI resets moved inside that same block, and every store path (analyses, cpms,
   summaries, the P3 memo, the disk `put_summary`/`put_schedule`) captures the generation
   before computing and stores only if it is unchanged — the disk put now happens under the
   lock, so a wipe can never be followed by a late re-insert. A `_scope_gen` sibling
   (bumped by `_invalidate_scope`) guards the identity-keyed P3 memo the same way, so an
   epoch flip mid-compute leaves NO entry rather than a dead-id orphan. The in-memory
   epoch caches (`analyses`/`cpms`/`summaries`) are deliberately NOT scope-gen-guarded —
   old-epoch entries under old-epoch keys are exactly P1's resident-epoch feature.
3. **Upload/`/example` locking (MAJOR, pre-existing D18 gap).** The upload loop read and
   mutated `st.schedules`/`st.file_meta`/`st.content_hashes` with NO lock while locked
   readers iterate those dicts (the D18 KeyError class), and its disk-cache
   `put_schedule` could race a wipe. **Decision:** short lock windows — the dup-scan and the
   three-dict store run under the lock (the slow parse stays outside), both guarded by the
   upload's wipe generation; a mid-upload wipe now aborts the remaining files LOUDLY (a
   manifest error line) instead of half-resurrecting the session. `/example` stores under the
   lock; the post-upload RAM estimate iterates a locked snapshot.
4. **Summary-tier margin vs the confirmed overlay (number consistency).** The Portfolio row's
   `effective_margin_days` came from name-based detection only, while the margin
   dashboard/trend/SRA honor the operator's CONFIRMED margin set (ADR-0230) — the same
   quantity could silently differ across pages after a confirmation. **Decision:**
   `compute_summary` gains `margin_uids` (default `None` = byte-identical); `summary_for`
   resolves the overlay with the SRA's exact precedence (this version's overlay, else the
   union) and, when one exists, computes fresh and neither consults nor overwrites the
   content-hash disk blob (which holds the name-based default — the same skip-disk pattern
   scoped versions use). `POST /margin/confirm` clears the in-memory summaries tier (the
   union fallback means one confirm can move every version's row).
5. **Cache-key hygiene (minor).** `_clean_key` strips control characters — a filename
   smuggling `\x1f` could collide a session key with another key's epoch key (the identity
   anchor blocked wrong service; the key space is now collision-free by construction).
6. **Gate gaps closed.** The P2 count gate only exercised the default epoch — a new gate pins
   one solve per version PER EPOCH with a zero-solve toggle-back. The ADR-0261 P5 OAT cap
   disclosure had zero coverage — new tests pin the capped payload note (and the JS
   renderer's wiring) and the no-note below-cap payload. New deterministic race regressions
   (monkeypatched hooks force each interleaving — no timing, nothing to flake) cover the
   epoch pairing, the P3-memo flip guard, wipe-vs-summary/analysis/upload, and the margin
   overlay consistency.
7. **Drift-guard breadth + doc truth.** The AFT Bible drift guard audited only
   `sorted(...)[0]` — the OLDER of the two committed snapshots; it now audits EVERY committed
   `.aft` (verified near-identical first: 759 names in both, one formula-set difference that
   is a dropped duplicate differing only by outer parentheses, not pinned).
   `__init__.__version__` sat at a hand-written "0.0.0" for 68 releases — it now derives from
   the installed distribution metadata (std-lib `importlib.metadata`). Stale docstrings
   fixed: the census oracle-test pointer (named a nonexistent file), the perf harness header
   (claimed no timing assertions), the AFT audit header ("git-ignored Bible"). Stale
   version stamps refreshed in `NEXT-SESSION-PROMPT.md` / `REPO-INVENTORY.md`.

## Deliberately NOT done (recorded, with reasons)

- **Bounding `cpms`/`summaries` across epochs** (three agents flagged unbounded epoch
  accumulation): an LRU on the P2 tier would make the every-page population pass thrash on
  large portfolios (each render re-solving evicted versions) — a worse disease than bounded
  memory growth in a single-operator session that `wipe` fully clears. Revisit only on
  profiling evidence (the ADR-0261 discipline).
- **Epoch-key reuse when a scope leaves a version unchanged** (a Target absent from a version
  recomputes a byte-identical analysis under the new key): a missed-reuse inefficiency,
  never a wrong number; recorded.
- The polished-narrative cache anchors the SCOPED object (wording drift vs ADR-0261's "raw
  anchor" claim): behaviorally safe (default-epoch scoped IS raw; a mismatch only forces a
  re-polish, never stale service); recorded, not changed.

## Consequences

- No engine number moved: `compute_summary(margin_uids=None)` and every remediation path are
  byte-identical for the states the 160-hash battery covered; parity untouched and green.
- Tests: `tests/web/test_session_consistency.py` (six deterministic race/consistency
  regressions), the P2 epoch gate in `tests/perf/test_perf_regression.py`, the OAT cap pair
  in `tests/web/test_sra_ssi_web.py`, the all-Bibles AFT guard.
- Version 1.0.68 → 1.0.69; wheel + 9 installers in lockstep (ruff format BEFORE the wheel
  build, per the banked lesson).
