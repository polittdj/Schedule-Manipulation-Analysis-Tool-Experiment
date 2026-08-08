# Handoff — 2026-08-08 (the 2026-08-07 audit's four P0s landed: sub-day fidelity · parity F5 adjudicated · briefing memo · integrity disclosure; ADR-0366..0369; v1.0.177)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-u67l5w`
> (branched from `main` dbcc8d2 after #553 squash-merged 22:57Z). **Shipped code changed** —
> version bumped **v1.0.176 → v1.0.177** BEFORE the suite; wheel + nine installers rebuilt once
> after the last code change (SCHEMA stays 2.11.0 — the new engine fields are computed, never
> persisted). Highest ADR now **ADR-0369**. All four audit P0s landed, every new guard
> mutation-proven able to fail with a NARROW, NAMED failure set and green twins:
>
> 1. **Sub-day effects (F1/F7, ADR-0366).** `ChangeEffect`/`ChangeEffectsReport` carry exact
> `*_minutes` fields; the int-day fields are untouched and their legacy round-half-even is now
> itself PINNED (60/235/240 → 0 — 240 is exactly half a day and banker's sends it to 0 — and
> 241 → 1). /integrity renders signed `+<1 wd` / `-<1 wd` (rows sort by minutes; the artifact
> "N of M have no effect" counts by minutes; aggregate `+<1 working day`); the duration label
> renders "cut 0.12→0.5 wd (60→240 min)" and a sub-day lag "(lag +0.5d / +240 min)" — every
> whole-day label byte-identical to before; the qa fact says "less than one working day
> LATER/EARLIER", never "no effect", for a real sub-day mover. Golden pins hold unchanged
> ("+21 wd", "33 of 33 have no effect"). Four reverts → 5/3/2/1 named failures.
> 2. **Parity milestone population (F5, ADR-0367) — CODE CONFIRMED CORRECT; the docstrings were
> the defect.** AFT verbatim: DCMA "1. Logic" = `IncludeMilestone=true` PLUS FilterExpression
> `Baseline Duration GreaterThan 0` (second copy adds `EV Method NotEqual LOE Value`); the
> NASA-lib "Missing Logic" family = `IncludeMilestone=true` with an EMPTY FilterExpressions.
> The audit's TP4 row was a CROSS-METRIC comparison: schedule_quality/ribbon mirrors Missing
> Logic (TP4 1=1; FX-05 5→8 UID-exact), DCMA-01-parity mirrors "1. Logic". The audit's
> baseline-PRESENCE hypothesis FAILS 4 named ADR-0280 pins (population / Resources /
> day-grained neg-float / DCMA-09 scope) — **measured-false, do not re-chase**. Full parity
> gate re-pinned green at HEAD first (52 passed / 0 failed, 11:36). Fix is DOCS ONLY:
> dcma14.py ×3 + state.py ×1 now state that milestone-ness is neither inclusion nor exclusion
> and the duration predicate drops ordinary milestones BY DESIGN. ACUMEN-PARITY-MODE.md was
> already correct; help.py/METRIC-DICTIONARY never carried the claim (untouched).
> 3. **/briefing memo (P1, ADR-0368).** `build_briefing` hands its audit to
> `recommend(precomputed_audit=)` — ONE DCMA audit per build (each audit embeds the DCMA-12
> delay-injection CPM re-solve). `SessionState.briefing_for` memoises the deterministic build:
> SINGLE-entry, keyed scope_signature (the parity toggle folds in) + report day + solvable-set
> IDENTITY, ADR-0281 stripe single-flight, auto-wiped (not in the wipe keep-set). /briefing,
> / (Mission Control) and /export/{fmt}/briefing share it; /api/ai/briefing stays live-built
> (non-deterministic by design). Guards: cold==warm BYTE-IDENTICAL with build-count 1 across
> all three surfaces; parity toggle re-keys 1→2→3; ADR-0259 byte-identical re-upload dedupes
> (memo legitimately survives) while CHANGED bytes force a rebuild.
> 4. **Integrity disclosure (F2/F4, ADR-0369).** An unresolvable focus target now returns a
> sentinel report (`target_unavailable=True`, no figures, aggregate_solved False) and the page
> renders a banner naming the failed target and the remedy — "no changes detected" still
> returns None (contract kept). `skipped_unsolvable_labels` / `skipped_capped_labels`
> (len==count by construction) render as `<details class=skipped-changes>` identity lists in
> both branches. The DECM-29I401a detail states each movement — "UID 1 baseline finish
> 2025-02-01 → 2025-03-03 (+30 calendar days)", set/erased phrased as such, first 6 verbatim +
> counted remainder (the FX-06 magnitude gap). qa: the sentinel emits NO change-effect facts;
> the aggregate fact only when ≥1 revert measured AND the joint solve succeeded, phrased
> "EVERY detected change" only when nothing was skipped (else the ADR-0358 partial wording).
>
> ## Verification
> Statics green (ruff whole-tree · format · mypy strict 125 files · bandit) · full parity gate
> 52/52 at HEAD before any P0-2 decision (11:36; 14 playwright-gated skips) · every touched
> module green (engine change_effects 15 · manipulation 8 · dcma14 26 · web subday 4 ·
> disclosure 4 · briefing_memo 3 · ai briefing 16 · integration pins 9) · node --check per
> file · installer lockstep test green · FULL suite first run **1 failed / 3510 passed /
> 44 skipped (22:44)** — the one failure was `test_change_effects_returns_none_for_a_summary_
> target`, the OLD None-contract pin that ADR-0369 deliberately replaced (module missed by the
> targeted sweep; the full suite exists for exactly this) — test updated to pin the sentinel,
> re-run tail reported on the PR.
>
> ## Next
> Phase 3 monolith split resumes at **mission 304** (stale census — RE-MEASURE the closure
> first; expect sra ~700+ over its "264"; the panel 235 + `_ssi_export_tables` 248 +
> `_file_stored_risks` wait there). Then: how 290 · sra (re-measured) · what 257 · where 235 ·
> portfolio 231 · evm 208 · forecast 204 — each per the ADR-0365 recipe. Standing queue:
> stored-SRA-fields MSPDI fixture · driving-corridor fixture · the three page-lede-less pages
> (/briefing /path /compare) · /groups Activities (ADR-0343) · installers vs known-good
> constraints · P80/P90 recurring-exception residual · the audit's doc-drift sweep
> (PARITY-REPORT still says the reference .mpps are git-ignored + calls Project2.mpp "CUI
> intake" — superseded by ADR-0151/0152; FINAL-REPORT blanket "exact match" beyond the three
> evidence tiers; CLAUDE.md's phase-3 + single-E501 lines lag) · ~150 MB RSS retained per
> loaded 9 MB file (no per-file unload) · 3 web tests calling GET /target where only POST
> exists · Phase 6 docs. **Operator:** re-convert FX-03/04 (open the authored .xml, VERIFY
> UID17=5d / UID131=1w before save — the finish MUST move) + re-run Fuse and replace the two
> oracles · one Acumen run on a crafted sub-day-negative-float schedule (closes the
> Negative-Float O1 oracle gap — the AFT has NO formula for it) · license · branch-protection
> contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0369 closed — do not re-open. Two NEW named traps this session paid for:
> (1) **a revert that changes nothing "passes"** — a python `s.index()` splice grabbed the
> FIRST `return tuple(facts)` in qa.py and silently RE-DECLARED the still-guarded function
> below the cut; the "revert" changed no behavior and the test stayed green. Anchor splices
> uniquely (`s.index(needle, after)`), and verify the mutation LANDED (grep the mutated
> property) before trusting any revert run. (2) **ADR-0259 hash-dedupe vs memo tests** — a
> byte-identical re-upload leaves the session untouched, so an identity-keyed memo
> LEGITIMATELY survives it; an invalidation test must upload CHANGED bytes (and assert the
> dedupe twin). Standing traps: MS Project XML import derives Duration from stored dates ·
> an environment defect can masquerade as a product defect (the Java-loader story) ·
> binding-wrap spies undercount — patch the module that CALLS (state, not app) or count at a
> construction chokepoint · a mutation is "caught" only when the failure summary NAMES the
> test · NEVER mutate the tree while a suite runs (the parity gate alone is 11.6 min;
> docs included) · an empty sweep is evidence only with a positive control · `grep -c` exits
> 1 on zero — chain with `;` · parity evidence is three-tiered — never report uniform
> equivalence · SMAT floors predecessor-less unstarted tasks at stored start; per-row
> counterfactuals are non-additive BY DESIGN · bandit B608 → house nosec on HTML f-strings ·
> pydantic floor 2.6 / fastapi 0.110.2 (air-gap) · the /analysis focus→tip family is
> load-sensitive — do NOT chase. A number written mid-session is not a measurement (wc
> decides). Full suite ~20 min — background `python -u`, read the tail.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
