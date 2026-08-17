# Handoff — 2026-08-17 (a) (deep-dive audit unit 3: MF-02 — the EVM workbook exported a fabricated 0.0 where the page said NOT APPLICABLE; ADR-0411; v1.0.209 shipped)

> ## STATUS (current) — audit IN PROGRESS on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0411**. **SHIPPED code changed** (`web/app.py`) — version **v1.0.208 →
> v1.0.209**, SCHEMA 2.11.0 unchanged, wheel + nine installers rebuilt (lockstep 64/64).
> Units 1-2 (ADR-0409/0410) are pushed on **PR #595**. **The audit is NOT finished** — the
> live ledger is `docs/STATE/AUDIT-2026-08-16.md`, where every row is marked
> FIXED / LEAD-VERIFIED / REPORTED. Do not treat a REPORTED row as a defect.
>
> ## What landed — ADR-0411 (MF-02, Law-2 high)
> `/export/{fmt}/evm` wrote each cell as `value if value is not None else ""`. That guard
> NEVER fires for a NOT_APPLICABLE index: `_na_index` builds the NA result with
> **value=0.0** (its own docstring says "never a fabricated 0") — the meaning lives in
> `status`, and the guard read `value`. Measured on golden Project5 (no cost loading): the
> PAGE renders NA and explains "that is a fact about the file, not a performance figure",
> while the WORKBOOK wrote three `0.0` cells. An analyst reading the hand-out sees CPI 0.00
> — catastrophic cost performance — where the truth is "no cost data". The workbook is the
> artefact that LEAVES the tool and gets quoted. Fixed with a named, shared
> `_export_cell()` helper gating on status (`web/performance.py` already had the correct
> idiom; the helper is what stops the two drifting apart again).
> **QC-1:** red-first by name (module 14 passed after); the test pins BOTH halves — no
> fabricated `0.0` AND the real figures (0.47, 0.91) still travel, so a fix that blanked
> everything would fail it; mutation battery **3/3 caught by the named test** (shadow,
> import-origin canary, instrument md5-identical, controls green both sides).
>
> ## Next — the audit continues
> **The Ultracode fan-out died of credit exhaustion in BOTH rounds** (round 1: 1 of 16
> agents; round 2: 4 of 13, then stalled). Dimensions NEVER audited: findings/trend/
> manipulation · importers · web core · page modules A/B · static JS · **the test suite
> itself** · docs/config/CI · AI figure-gates. These need a fresh session (or a working
> agent pool) — this handoff must not be read as "the repo was fully audited".
> **22 REPORTED findings await lead verification**, incl. CPM-01 and MC-01 (finder-rated
> critical, UNVERIFIED). **MF-05 is explicitly do-not-fix-blind**: an empty-population PASS
> may be CORRECT Acumen parity behaviour and needs the reference export as its oracle.
> Then the route x test gap-fill: **137 routes** (enumerated twice independently), of which
> **5 lack a success test and 16 lack a failure-mode test**.
>
> ## Carried forward
> ADR-0353..0411 closed — do not re-open. NEW lesson: **when two surfaces describe the same
> figure, compare them to each other** — the page/export disagreement localised MF-02
> instantly, and MF-01 was the same shape (published help text right, engine wrong). A
> surface read alone only tells you what it says, never whether it is true. Standing traps
> unchanged (see the archive — defence-in-depth twins hide layer deaths · a suggested fix
> is a hypothesis · "measured, then pinned" fixtures inherit the bug · never measure a
> mutating tree · never mutate a measuring instrument · two ruffs, use `python -m ruff` ·
> parity >900 s · fetch before numbering and before committing · `wc` decides). QC-1/QC-2
> are ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree · format --check 1021 files · mypy
> strict 155 files · bandit). Full suite: **4097 passed, 47 skipped, 0 failed, exit 0,
> 18:30**. Parity: **72 passed, 15 skipped, exit 0, 8:43** — unchanged. Installer lockstep
> **64/64** against the v1.0.209 wheel. Drift guards 5/5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
