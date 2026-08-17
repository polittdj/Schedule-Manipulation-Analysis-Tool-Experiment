# Handoff — 2026-08-16 (b) (deep-dive audit unit 2: MF-01 — TCPI was scored with its PASS direction INVERTED, so unaffordable programmes reported PASS; ADR-0410; v1.0.208 shipped)

> ## STATUS (current) — audit IN PROGRESS on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0410**. **SHIPPED code changed** (`engine/metrics/evm.py`) — version
> **v1.0.207 → v1.0.208**, SCHEMA 2.11.0 unchanged, wheel + nine installers rebuilt
> (lockstep 64/64). Unit 1 (HOOK-02 / ADR-0409) is MERGED-PENDING in **PR #595**.
> **The audit is NOT finished** — see `docs/STATE/AUDIT-2026-08-16.md`, the live ledger
> where every row is marked FIXED / LEAD-VERIFIED / REPORTED.
>
> ## What landed — ADR-0410 (MF-01, Law-2 high)
> `_index()` in `engine/metrics/evm.py` hardcoded `Direction.GE` for all three EVM indices.
> Right for SPI/CPI; **TCPI is inverted by definition** — (BAC-EV)/(BAC-AC) is the
> efficiency the REMAINING work must achieve, so >1.0 is bad news. `help.py:571` already
> published "pass <= 1.0"; the engine scored the opposite. Measured: a programme needing
> **1.6x** planned efficiency reported **PASS**, a comfortable one at 0.25x reported FAIL —
> and TCPI feeds `_DIM_AFFORDABILITY`, so the affordability dimension showed green exactly
> on programmes that could not afford to finish. **The NUMBER was always right** (the NASA
> `.aft` row pins the formula as MATCH), so no parity value moves and `help.py` needed no
> edit: the fix makes the code obey docs it already shipped.
> **THREE oracles pinned the defect in place** (ADR-0385 stale-guard class, 3rd instance):
> `_EVM_SEEDS` is documented "measured, then pinned" and was measured against the inverted
> direction; a fixture literally named `blown` (CPI 0.54, ~2x per unit of work) asserted its
> affordability index PASSES; and `test_evm.py` asserted FAIL on a TCPI of 0.5. All three
> repointed here with the reason recorded inline.
> **QC-1:** fix built and measured in a PYTHONPATH SHADOW **before the real tree was
> touched** (operator directive) — blast radius measured there across all 26 EVM-touching
> test files: exactly **4 failures / 430, every one a bug-pinning oracle**, zero genuine
> regressions. Red-first by name; blast-radius set **432 passed** after. Mutation battery
> **4/4 caught by the named tests** (shadow, import-origin canary, instruments
> md5-identical, controls green both sides) — M4 deliberately flips SPI so the
> neighbours-unchanged control is PROVED to have teeth, not assumed to. Four independent
> instruments agree: published help text, live probe, mutation battery, NASA `.aft`.
>
> ## Next — the audit continues
> Round-2 finders still to return: findings/trend/manipulation · importers · web core · page
> modules A/B · static JS · **the test suite itself** · docs/config/CI · AI figure-gates,
> plus the completeness critic. **22 REPORTED findings await lead verification**, including
> CPM-01 and MC-01 (both rated critical by their finders — unverified). Then the route x
> test gap-fill: the inventory is **137 routes** (65 page · 34 api · 38 export), enumerated
> twice independently, of which **5 lack a success test and 16 lack a failure-mode test**.
>
> ## Carried forward
> ADR-0353..0410 closed — do not re-open. NEW lesson: **"measured, then pinned" fixtures
> inherit whatever the code did on the day they were written** — when a verdict is wrong,
> the fixture becomes the defect's bodyguard, and the giveaway is a fixture whose NAME
> contradicts its assertion (`blown` asserting PASS). Read fixture names as claims.
> Standing traps unchanged (see the archive — defence-in-depth twins hide layer deaths ·
> a suggested fix is a hypothesis · data pins vs guarantees · monkeypatch per CALL SITE ·
> never measure a mutating tree · never mutate a measuring instrument · two ruffs, use
> `python -m ruff` · parity >900 s · container starts with NO deps · fetch before numbering
> and before committing · `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree · format --check · mypy strict 155
> files · bandit). Full suite on the FINAL tree: **4096 passed, 47 skipped, 0 failed, exit
> 0, 18:27**. Parity: **72 passed, 15 skipped, exit 0, 8:47** — unchanged, confirming the
> fix moves no computed value. Installer lockstep **64/64** against the v1.0.208 wheel.
> Drift guards 10/10. (The first gate run reported 3 failures — all three were the drift
> guards correctly reporting that the state docs did not yet name ADR-0410 / v1.0.208; the
> docs in this same commit resolve them, and the whole suite was then re-run on the final
> tree.)

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
