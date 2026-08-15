# Handoff — 2026-08-15 (b) (the final report stops overclaiming: conditional locality, tempered parity, M15 contradiction resolved, JCL EAC gloss transcribes the engine; ADR-0405; v1.0.205)

> ## STATUS (current) — ADR-0405 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`
> (restarted from `main` **8a794a0** = #592's squash after its merge). Highest ADR now
> **0405**. **SHIPPED code changed** (`help.py` ships in the wheel) — version **v1.0.205**,
> SCHEMA 2.11.0 unchanged, wheel + nine installers rebuilt (lockstep 64/64). xfails
> unchanged: TEST-01 + JCL-BR-01.
>
> ## What landed — ADR-0405 (DOC-01 + ADR-0401's two JCL docs follow-ups, one small unit)
> **(1) `docs/FINAL-REPORT.md` stops overclaiming.** §6.G's absolute "No data off-machine"
> became conditionally FALSE the moment ADR-0402 shipped — it now states the guarantee the
> way `_observed_banner` states it: compute/serving/parsing local-offline unconditionally;
> the ONE sanctioned exception is AI prompt egress through the operator-armed approved
> gateway (allowlist-pinned, acknowledgment-gated, bannered, transaction-logged). The stale
> "`.gitignore` blocks all schedule formats" is replaced with the pre-commit-guard truth
> (ADR-0152/0347/0399). §6.B's evidence names the tempering ("exact or with documented,
> gate-locked residuals" — PARITY-REPORT is the row-by-row truth); §6.F describes the
> current backend surface (cloud option removed; gateway sole non-local path, never a
> fallback); §7's 645-tests/32-ADRs counts are labeled as the original closeout's with a
> pointer to the live Gate-at-close. **The M15 contradiction is resolved delivered-ward**
> (header + §6.A row + ADR-0030 all said delivered while the DoD still said "◻ BLOCKED") —
> and the test that PINNED the contradiction (`assert "BLOCKED" in report`,
> test_docs.py — the ADR-0385 stale-guard class, again) is repointed to hold the
> RESOLUTION (`"BLOCKED" not in report` + `"ADR-0030" in report`), plus a NEW guard pinning
> the conditionality itself ("Conditional since ADR-0402" + `_observed_banner` + the
> transaction log + "gate-locked residuals" must stay).
> **(2) `web/help.py`'s JCL `eac` gloss transcribes the engine** (jcl.py:255-258/266/297
> read and cited, not inherited): the (1-tau)/tau split over rem = budget x (1-%complete)
> — the old gloss scaled the WHOLE remaining budget by the duration ratio, coinciding with
> the engine only at the tau=1 default — and AC + (BAC - EV) now carries its clean-EVM
> precondition (recorded actuals; EV = sum(budget x %complete); the engine's
> budgeted-cost fallback breaks the identity otherwise). METRIC-DICTIONARY regenerated
> (sync test green).
> **Verification:** stash/restore red-proof — the repointed + new doc guards ran 2 FAILED
> by name against the pre-edit report, 10/10 green after; the gloss's oracle is the engine
> source itself (QC-2 provenance).
>
> ## Next — in order
> **Operator: verify v1.0.205 (or later) on the NASA machine — arm once, confirm a plain
> double-click launch comes up armed with the catalog populated** (still 401 WITH the key
> → capture the AI Hub's documented auth scheme; a follow-on ADR adds it on evidence) →
> **DISC-01 release determination** (operator / authorizing official) → **PO-04/05**
> (BLOCKED on an operator-delivered CEI/HMI reference export) → **TEST-01** chromium
> build-number pins (22 modules; agent-doable, tests-only, NEXT UP) →
> `actual_start_driven` consumed nowhere (ENG-DEAD-01; shipped-code lockstep) →
> **JCL-BR-01** (shipped-code; carry branches through compute_jcl or honest-gate the
> panel; the strict xfail flips loudly) → 8 stale remote branches (DoD 091; ref-deletion
> pushes 403 from sessions — operator UI) → SMAT-SANDBOX branch-name cleanup (operator UI).
>
> ## Carried forward
> ADR-0353..0405 closed — do not re-open. NEW lessons this session: **a narrative doc's
> hard count is a claim that rots — label it as of-its-date and point at the live ledger**
> (645/32 sat as "current" for six weeks of 4,000/400 reality); **a guard can pin a
> contradiction as easily as a truth** — test_docs.py asserted "BLOCKED" while the same
> file's header said delivered (second paid instance of the ADR-0385 class; when a doc
> contradicts itself, check whether a test is HOLDING the contradiction); **transcribe
> formulas from the engine, cite the lines** (the eac gloss drifted exactly where prose
> was written from memory instead of code). Standing traps unchanged (see the archive —
> data pins vs guarantees · mutation-green vs adversarial · monkeypatch per CALL SITE ·
> never measure a mutating tree · never mutate a measuring instrument · two ruffs, use
> `python -m ruff` · parity >900 s · container starts with NO deps · fetch before
> numbering and before committing · `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green: `python -m ruff check .` (All checks passed) / `python -m ruff format
> --check .` (1,013 files) / `python -m mypy src/` (155 files, no issues) / bandit exit 0 /
> node --check per file, 0 fails. **Full suite on the FINAL tree: 4065 passed, 47 skipped,
> 2 xfailed (TEST-01 + JCL-BR-01), 0 failed, exit 0, 28:46** — 4065 = the (a) close's 4064
> + the new FINAL-REPORT conditionality guard. **Parity gate: 72 passed, 15 skipped
> (env-gated), exit 0, 13:45.** Installer lockstep 64/64 against the final v1.0.205 wheel.
> Drift guards green.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
