# Handoff — 2026-08-15 (c) (TEST-01 closed: 22 chromium build-number pins unpinned, the audit xfail flips, a canary-proved census stands guard; the operator verification ledger lands in OPERATOR-REQUESTS; ADR-0406; v1.0.205 unchanged)

> ## STATUS (current) — ADR-0406 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0406**. **NO shipped code changed** — tests + docs only: version stays
> **v1.0.205**, SCHEMA 2.11.0, no wheel/installer rebuild (ADR-0395/0399/0400/0401
> precedent). `tests/audit` now has **ZERO live xfails** (TEST-01 flipped); the ONE
> remaining strict xfail repo-wide is **JCL-BR-01** in `tests/web/test_jcl_web.py`.
>
> ## What landed — ADR-0406 (TEST-01 + OR-10's documentation ledger)
> **(1) TEST-01 closed.** All 22 playwright modules carried the byte-identical pinned line
> `CHROME = Path(".../chromium-1194/chrome-linux/chrome")` — a container chromium bump
> would flip every one to a silent skip. Each now resolves the FIRST vendored chromium by
> sorted glob (r11's discipline, propagated; `_PW_CHROMES`/fallback keeps the
> module-level skipif semantics — no chromium still means skip, never error). The audit
> module's own comment was reworded (its `chromium-1194/...` text SELF-MATCHED the scan it
> documents — the scan reads every test file including itself), and the strict xfail
> marker is removed: `test_test01_no_test_hardcodes_a_chromium_build_number` now stands as
> the permanent whole-tree census. **Canary red-proof:** a planted
> `tests/zz_canary_test01.py` with a pinned path turned the census RED by name; removed,
> 21/21 green. The 22 modules still collect + playwright-skip exactly as before (measured:
> 1 passed 5 skipped on the spot-check trio).
> **(2) OR-10's ledger.** `docs/STATE/OPERATOR-REQUESTS.md` gained the gateway-arc section:
> OR-07/08/09 recorded verbatim with their shipped ADR/PR/version; OR-10 IN FLIGHT; a
> **PENDING OPERATOR VERIFICATION** table (V-1 arm-once flow · V-2 Bearer acceptance ·
> V-3 transaction-log spot-check, each with its concrete how); the **BLOCKED ON OPERATOR**
> list (DISC-01 · CEI/HMI export · branch/SANDBOX UI cleanup); and the **AGENT QUEUE**
> with live status. HANDOFF + NEXT-SESSION-PROMPT carry the same queue per-unit.
>
> ## Next — in order
> **Operator: the V-1/V-2/V-3 verification table in OPERATOR-REQUESTS.md** (arm-once on
> the NASA machine; catalog populating = Bearer accepted; still-401-with-key → capture the
> AI Hub's documented scheme) → **DISC-01** (operator / authorizing official) →
> **PO-04/05** (BLOCKED on the CEI/HMI export) → **ENG-DEAD-01** `actual_start_driven`
> consumed nowhere (agent; SHIPPED-code lockstep when taken — NEXT UP) → **JCL-BR-01**
> (agent; shipped-code; carry branches through compute_jcl or honest-gate the panel; the
> last strict xfail flips loudly) → 8 stale remote branches + SMAT-SANDBOX names
> (operator UI; sessions cannot push ref deletions, ADR-0401).
>
> ## Carried forward
> ADR-0353..0406 closed — do not re-open. NEW lessons this session: **a census that scans
> every test file scans ITSELF** — the audit module's own explanatory comment was an
> offender-in-waiting; write census docs without the matchable literal (r11's no-trailing-
> slash convention) and canary-prove after flipping; **22 identical pinned lines are one
> sed and one census** — the fix cost minutes once the population was enumerated exactly
> (the audit regex, not a loose grep, defines the population). Standing traps unchanged
> (see the archive — data pins vs guarantees · mutation-green vs adversarial · monkeypatch
> per CALL SITE · never measure a mutating tree · never mutate a measuring instrument ·
> two ruffs, use `python -m ruff` · parity >900 s · container starts with NO deps · fetch
> before numbering and before committing · `wc` decides). QC-1/QC-2 are ADR-0393, pinned
> by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree · format --check · mypy strict 155
> files · bandit · node per-file). Full suite on the final tree: **4066 passed, 47
> skipped (env-gated playwright — baseline preserved by the unpinned modules), 1
> xfailed (JCL-BR-01, the sole strict xfail repo-wide; TEST-01's is GONE), 0 failed,
> exit 0, 27:49**. Parity: **72 passed, 15 skipped, exit 0, 13:45**. tests/audit
> standalone: 21 passed, 0 xfailed. No wheel/installer rebuild (no shipped code) —
> the v1.0.205 artifacts stand.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
