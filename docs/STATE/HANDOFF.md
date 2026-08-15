# Handoff — 2026-08-15 (d) (ENG-DEAD-01 closed: `actual_start_driven` reaches the analyst — INFO/OPPORTUNITY finding, path-grid column, dictionary entry; ADR-0407; v1.0.206 shipped)

> ## STATUS (current) — ADR-0407 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0407**. **SHIPPED code changed** (`recommendations.py`, `help.py`,
> `driving.py`, `path.js`) — version **v1.0.205 → v1.0.206**, SCHEMA 2.11.0 unchanged,
> wheel + nine installers rebuilt (lockstep 64/64). The ONE strict xfail repo-wide is
> still **JCL-BR-01** (`tests/web/test_jcl_web.py`) — now also the LAST agent-queue item.
>
> ## What landed — ADR-0407 (ENG-DEAD-01: the unconsumed channel is wired)
> `CPMResult.actual_start_driven` (ADR-0391's floored-UID disclosure) was produced at
> `cpm.py:1357` and consumed by NO product code (audit ENG-DEAD-01, re-verified live).
> Now: **(1)** `_actual_start_floor_findings` in `engine/recommendations.py` emits an
> **INFO/OPPORTUNITY** finding ("N activities are scheduled from their recorded actual
> starts", cited per activity). OPPORTUNITY is LOAD-BEARING: `web/risks.py` builds the
> matrix/ranking/recovery plan from RISK+CONCERN only, so the disclosure never becomes a
> threat row — ADR-0391's "evidence, not an unsupported date", held at the finding level.
> **(2)** `/api/driving` rows carry `actual_start_driven` beside `date_driven`
> (`web/driving.py`), and path.js FIELDS offers "Actual-start-driven" (default off).
> Excel path export untouched by symmetry (`_DRIVING_COLUMNS` excludes both flags).
> **(3)** `help.py` documents the metric id (dimension falls through to Realism —
> correct, no `_DIM_*` edit); `METRIC-DICTIONARY.md` regenerated.
> **QC-1:** red-first (4 of 5 new tests failed by name pre-wiring); mutation battery
> **7/7 caught by the named test** in a PYTHONPATH shadow (import-origin asserted,
> pristine controls green before/after, instruments md5-identical). Blast radius
> enumerated BEFORE implementing, then measured: 210 passed across every findings
> consumer with exactly ONE moved pin — the r11 `PAGE_SCRIPTS` byte-freeze of path.js,
> re-baselined with the freeze's own documented idiom (old→new digest in place).
> `#drivingTiersData`/`#dpData` frozen payloads have their own reducers; they did not move.
>
> ## Next — in order
> **Operator: the V-1/V-2/V-3 verification table in OPERATOR-REQUESTS.md** (arm-once on
> the NASA machine; catalog populating = Bearer accepted; still-401-with-key → capture the
> AI Hub's documented scheme) → **DISC-01** (operator / authorizing official) →
> **PO-04/05** (BLOCKED on the CEI/HMI export) → **JCL-BR-01** (agent; shipped-code;
> carry session branches through compute_jcl or honest-gate the panel; the last strict
> xfail flips loudly — LAST AGENT-QUEUE ITEM) → 8 stale remote branches + SMAT-SANDBOX
> names (operator UI; sessions cannot push ref deletions, ADR-0401).
>
> ## Carried forward
> ADR-0353..0407 closed — do not re-open. NEW lesson this session: **enumerate the
> byte-freeze surfaces BEFORE editing anything a freeze covers** — the r11 PAGE_SCRIPTS
> freeze on path.js was found in pre-implementation recon, so its red was a predicted
> re-baseline, not a surprise; and the freeze constants carry their own re-baseline idiom
> (ADR + what moved + old→new digest) — follow it, never bare-swap a hash. Standing traps
> unchanged (see the archive — data pins vs guarantees · mutation-green vs adversarial ·
> monkeypatch per CALL SITE · never measure a mutating tree · never mutate a measuring
> instrument · two ruffs, use `python -m ruff` · parity >900 s · container starts with NO
> deps · fetch before numbering and before committing · `wc` decides). QC-1/QC-2 are
> ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree · format --check · mypy strict 155
> files · bandit · node per-file). Full suite on the final tree: **4071 passed, 47
> skipped (env-gated playwright), 1 xfailed (JCL-BR-01 — the sole strict xfail
> repo-wide), 0 failed, exit 0, 28:02**. Parity: **72 passed, 15 skipped, exit 0,
> 13:49**. Installer lockstep 64/64 against the v1.0.206 wheel. The first gate run
> honestly FAILED on `test_aft_formula_audit`'s every-documented-id census — the THIRD
> dictionary guard, missed in pre-enumeration (see LESSONS (d)); the NOT_IN_BIBLE row
> closed it and the whole gate re-ran green on the final tree.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
