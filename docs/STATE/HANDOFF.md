# Handoff — 2026-08-08 (e) (phase 3 slice 9: the /sra page family out of the monolith; the payload aimed off the critical path; ADR-0373; v1.0.181)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-vdowl5`
> (branched from `main` 41c5462 after #557 squash-merged). **Shipped code changed** — version
> bumped **v1.0.180 → v1.0.181** BEFORE the suite; wheel + nine installers rebuilt once after
> the last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0373**.
>
> **Phase-3 slice 9 is CLOSED (queue item 1): the /sra page family → `web/sra.py` (1,848
> lines; 30 names / 22 regions), app.py 16,384 → 14,597.** The re-measured census priced
> ADR-0365's prediction exactly: prefix 847 / 13 names, closure 32 names / 1,756 lines —
> `_ssi_panel` (235) and `_ssi_export_tables` (248) are IN (the prefix is a finder, the
> closure is the definition). TWO descents into `components.py` (`_TS_CAPTION_MARK` — three
> other routes serve the marker; `_schedule_risks` — margin + five /api routes derive it);
> `_ssi_three_point`/`_risk_events`/`_schedule_branches`/`_schedule_conditionals` stay
> (route machinery no page owns). `LAYER_ORDER` `… → ssi → mission → sra → app`; E501
> travels; `sra.py` imports NOTHING from `web.ssi` (panel/data split — the run machinery is
> upstream of routes, not of the page family). Constants carried their `#:` doc-comment
> blocks (ast spans do not see comments — five regions extended BY EYE before the cut).
> `test_axis_titles`' `_TS_CAPTION_MARK` counter repointed in the same commit (the ADR-0349
> trap, not tripped).
>
> ## Verification
> Oracle rebuilt per the ADR-0372 recipe and grown 151 → **294 labels** (every parameterless
> GET incl. validation-4xx bodies · both fmts × 27 exports · 8 named exports on TP4 v5 · the
> variants · [target-set]/[target-cleared] now re-rendering the FULL GET+export surface ·
> the slice-7 crafted v4/v2 setup-load sequences RETURNED with 12+4 after-renders, 303s
> asserted). Double-render determinism across two processes, 0 flapping, three normalizers
> inherited. **The first crafted v4 payload measured two FALSE darks**: it aimed factors/
> bcwc/risk/branch at UIDs 12–15 — tasks the v5 snapshot has COMPLETED — so ADR-0308 made
> every risk inert, the S-curve collapsed to one point and OAT was all-zero; scurve+tornado
> probed 0 twice (a stronger-anchor re-probe separated weak-anchor from dark). Re-aimed at
> the LIVE critical chain (factor 22 · bcwc 23 · override 24 · risk→22 · branch across the
> real 22→24 FS tie · conditional plans 24→25 · focus=project finish) both light at
> [v4] DOCX sra. Pre-flight probe: 29/32 render-proven (xlsx→`_ssi_export_tables`,
> docx→`_sra_report_blocks`+charts+NASA constants — structural sets); 3 oracle-dark = the
> SAME ADR-0365 stored-fields trio, route-covered in Python by
> `test_load_from_schedule_seeds_the_register_from_the_files_risk_fields` + the uid152
> parity oracles. Proof: per-region byte-identity **24/24** (asserted in the cut script,
> re-verified after ruff-fix AND after format) · multiset **104 added / 8 removed — zero
> code lines, all 8 import-shape artifacts** · 12 app.py imports dropped, sweep-clean ·
> **294/294 routes byte-identical pristine vs cut** · falsified in the new locations
> **32/32 EXACT** (dark stayed dark), restores md5-verified. Sweeps: monkeypatch+attr over
> all 70 bound names — zero hits (control `app_mod.non_summary` found 2×); source-text over
> all 15 app.py readers, positive-controlled (`sra_grid.js` ∈ axis_titles ∩ `_ssi_panel`),
> every hit adjudicated. Mutation battery **6/6 named**, twins green (enumeration guard's
> 9th/10th consecutive live catch); mutation 2's FIRST shape (upward import in a NEW
> top-level def) drew the re-export guard TOO — a defensive-overlap true positive; and the
> battery-patch that reshaped it first MISSED silently via unanchored heredoc replace (patch
> the patcher with landed-count discipline). Statics green (python -m ruff check WHOLE TREE
> · format · mypy strict 127 · bandit exit 0 · node --check per file). Full suite + parity:
> counts in SESSION-LOG (this session).
>
> ## Next
> The queue resumes at phase-3 slice 10 — by re-measured prefix (each family owes its OWN
> closure): **forecast 391** · what 289 · portfolio 253 · evm 239 · where 235 · how 214 —
> EACH per the ADR-0365 recipe (closure before cut · span-scoped probe · the six-mutation
> battery). Then the standing queue unchanged: stored-SRA-fields MSPDI fixture (would light
> the three dark members from a FILE) · driving-corridor fixture · three page-lede-less
> pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs
> known-good constraints · P80/P90 recurring-exception residual · doc-drift sweep
> (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact
> match"; CLAUDE.md phase-3/E501 lines — sra.py now ALSO joins the E501 list unpatched
> there) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:** re-convert FX-03/04
> (verify UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen run on a crafted
> sub-day-negative-float schedule · license · branch-protection contexts · proprietary
> reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0373 closed — do not re-open. NEW this session: (1) **a crafted oracle payload
> must be aimed at the LIVE critical chain** — completed-task UIDs measure the fixture's
> history, not the member's reach (two false darks until the re-aim); and a 0-move probe is
> believed dark only after a SECOND, stronger anchor also moves 0. (2) **Patch the patcher
> with landed-count discipline** — an unanchored heredoc replace on the battery script
> missed silently and re-ran last hour's mutation; use exact-match edits that fail loudly.
> (3) Constants carry `#:` doc-comment blocks the ast span does NOT see — extend regions by
> eye before any byte moves. (4) A census "external referrer" that is a create_app route is
> NEVER a blocker (routes import downward) — but a nested create_app helper (e.g.
> `_margin_risk_data`) marks a 2-family name for DESCENT. Standing traps unchanged
> (silent-405 setup · anchored splices with landed-count asserts · ADR-0259 dedupe vs memo ·
> round-half-even 240→0 · MSPDI re-derives Duration · env-defect masquerade · binding-wrap
> spies · named-failure rule (pytest exit ≠ failing test — assert the test RAN) · never
> mutate a running suite's tree, docs included · empty sweep needs a positive control ·
> `grep -c` exits 1 on zero · three-tier parity evidence · stored-start floors /
> non-additive rows · B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis
> focus→tip family load-sensitive · five playwright-only failures pre-existing,
> CI-invisible · oracle telemetry labels normalized by VALUE · scratchpad harnesses
> hardcode the repo root). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
