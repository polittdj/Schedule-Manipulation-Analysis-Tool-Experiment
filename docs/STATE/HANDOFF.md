# Handoff — 2026-08-07 (phase 3 slice 7: the ssi run machinery out of the monolith; ADR-0365; v1.0.176)

> ## STATUS (current) — **pushed, draft PR open.** ADR-0365, **v1.0.176** (shipped code changed:
> `app.py`, `components.py`, new `web/ssi.py` — wheel + nine installers REBUILT after the
> bump), SCHEMA 2.11.0. Slice 6 (#551, ADR-0364) squash-merged by the operator at 17:24Z;
> the operator also web-uploaded SIX new reference files (`AlltheProjects` .zip/.afw/4×.xlsx,
> ~49 MB) — the intake manifest is REGENERATED in this commit (410 → 416 tracked files,
> mismatches stay 99; CLAUDE.md count updated).
>
> ## ADR-0365 — phase 3 slice 7: the SSI run machinery; the census flagship left the family
> The stale "ssi 335" census RE-MEASURED: it was `_ssi_panel` (235) + `_ssi_data` (102) by
> prefix — and the closure puts THE PANEL OUT OF THE FAMILY (sole referrer `_sra_body` → it
> is /sra page family, as is `_ssi_export_tables` 248). The behaviour-seeded closure over
> the nine SSI routes gives 15 names / 611 lines partitioned three ways: an 11-name /
> 576-line move set into **`web/ssi.py`** (644 lines: `_ssi_data` · `_ssi_grid_rows` · the
> setup Save/Load cluster · the three stored-field constants); THREE descents into
> `components.py` (`_REMAIN_DAYS_DP` · `_affected_avg_remaining_days` ·
> `_ssi_matrix_counts` — each needed by a mover AND a staying sra member); stays =
> `_ssi_three_point` (7 route families) · `_correlation_spec` (6) · `_schedule_*` ·
> `_MAX_SETUP_BYTES` (upload-cap trio) · `_file_stored_risks`. `app.py` 17,197 → 16,581.
> NOTE: `web.ssi` sorts BEFORE `web.state` (unlike trend) — the re-export block is mid-list.
> Oracle grew 80 → 96 labels: + sra exports/templates, + `[ssi-api]` (the MC is SEEDED:
> `SRAConfig.seed=12345`, per-iteration `Random(seed+i)` — byte-stable at 300 iters),
> + a crafted v4 setup load (exact_overall/LHS/correlation/days-only risk/branch/
> conditional/droppable UIDs) with four after-renders, + a v2 load lighting the ADR-0307
> stale-factor recompute. Launch token is `{hex16}.{wipe_gen}` — a hex-only normalizer
> misses it and 48 labels flap. Proof: 14/14 per-definition byte-identity; multiset 69
> added / 1 removed (the removal = app's parenthesized `SSIRiskStat,`, re-added as
> components' own import; `import hashlib` migrated app→ssi invisibly); **96/96 routes
> byte-identical**; falsified in BOTH new locations, all NINE render-visible members EXACT
> vs their probe sets; five guard mutations red→restored md5-verified (enumeration guard's
> sixth live catch). Probe zeros stated: the stored-fields cluster is oracle-dark but
> unit-covered (`test_ssi_grid_from_schedule`); `_REMAIN_DAYS_DP` 6→2dp is value-invisible
> on whole-day fixtures. Sweeps: one hit = the standing `app_mod.non_summary` memo patch
> (doubles as the live positive control; cleared by the ADR-0364 verification, unchanged).
>
> ## Next
> Phase 3 resumes at **mission 304** (stale census — RE-MEASURE; expect sra to measure
> ~700+ over its "264": the panel 235 + export tables 248 + `_file_stored_risks` wait
> there). Then: the stored-SRA-fields MSPDI fixture (named oracle gap — unlocks the
> stored-fields cluster end-to-end AND the /sra slice) · driving-corridor fixture · the
> three page-lede-less pages (/briefing, /path, /compare) · /groups Activities counting
> summary rows (ADR-0343) · installers vs known-good constraints · the P80/P90
> recurring-calendar-exception residual (own unit) · Phase 6 docs. **Operator:** license ·
> branch-protection · proprietary reruns · OR-04 · whether the July mpp/ oracle should
> re-export under replace semantics.
>
> ## Carried forward
> ADR-0353..0364 closed — do not re-open. Slice recipe held for its seventh outing; new
> permanent additions: (1) a NON-ZERO pytest exit is not a failing test — collection
> errors exit non-zero too; a mutation is "caught" only when the failure summary NAMES the
> test (slice 7's mutations 4–5 first ran against guessed ids and the exit-code check lied
> RED); (2) the census prefix can put a member IN the family the closure puts OUT — the
> panel precedent. A number written mid-session is not a measurement (wc decides). The
> workbook Mean/StdDev cells are UNWEIGHTED. A parity delta is a claim about INPUTS first.
> `pydantic>=2` NOT a safe floor (2.6); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2
> floor). `ruff check .` whole tree as `python -m ruff` (stale 0.15.8 shadows PATH).
> `grep -c` exits 1 on zero — chain with `;`. The /analysis focus→tip family is
> load-sensitive — do NOT chase. bandit B608 on HTML f-strings with "from" → house
> `# nosec B608 (HTML, not SQL)`. Full suite > 10-min foreground timeout — background with
> `python -u` and READ the tail; never mutate the tree (docs included) while it runs;
> mutate→restore harnesses live in ONE background python orchestrator, never a
> timeout-backgroundable foreground call.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
