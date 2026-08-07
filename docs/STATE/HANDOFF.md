# Handoff — 2026-08-06 (evening: risk-replace semantics ADR-0359; exports answer ADR-0360; unrestricted AI + battery ADR-0361; v1.0.173)

> ## STATUS (current) — **pushed, draft PR open.** ADR-0359/0360/0361, **v1.0.173**, SCHEMA 2.11.0.
> The operator merged #547 (slice 4) and filed a five-part directive with NEW committed
> oracles (main `f1f13f9`: the 2,125-task SRA schedule + SSI's 5000-iter SRA histogram +
> SSI's Sensitivity export — absorbed into the census: 410 files / 22 mpp / mismatches 99).
>
> ## ADR-0359 — the SRA delta's engine term, pinned to two decimals and fixed
> Inputs first (ADR-0356's lesson): the operator's session replayed a 783-task-vintage setup
> (98/435 factors agree, 0/406 BC/WC agree) — session-side, largest term. On FILE-TRUE inputs
> the engine still ran +25 mean / +32-35 cal at P50-P90. SSI's Sensitivity export cracked it:
> all 64 duration rows matched the engine's OAT to <=0.01 wd (CPM/calendars/ML EXACT), and the
> two R/O rows fell short of the impact by EXACTLY the affected tasks' MLs (321-304.48=16.52;
> 45-35.03=9.97): **a fired risk's impact REPLACES the affected activity's remaining duration
> — the engine was ADDING it**, and the affected task samples its own Best/Worst when not
> fired (SSI lists the R/O tasks as duration rows too). Fixed in compute_sra_ssi AND
> compute_jcl; OAT gains ranked R/O rows. Landing: mean +414.6 vs SSI +417.9 cal, sigma 155.2
> vs 152.4, P10-P90 within 1-3 d of the weighted histogram; risk means 305.9/37.9 vs SSI's
> 304.48/35.03. New parity oracle test_sra_ssi_oracle_uid152_v2.py (OAT row-for-row +
> distribution + risk outcomes); July oracle still 5/5; four new pins mutation-proven
> (replace->add: 4 fail). The sharp discriminator: impact < ML pulls the finish BELOW
> deterministic — impossible under add.
>
> ## ADR-0360 — "Export to Excel does nothing" = a measured 140-second silent recompute
> All wires were present (precise-parser sweep: 0 dead of every page; the first regex probe's
> 45 were ITS OWN false positives). /export/xlsx/sra re-ran the MC + full 919-task OAT on
> every click: 139.8 s measured, zero feedback. Fixed: run/OAT caches keyed by the FULL
> resolved-input identity incl. schedule bytes (140 s -> 0.1 s warm; the workbook now equals
> the SCREEN — the operator's iterations, not a hardcoded 2000); panelkit's EXCEL click shows
> busy-guarded "PREPARING…" via fetch->blob with navigation fallback; Load-from-schedule now
> seeds the RISK REGISTER from the file's SSI fields (R7443 86%/321d, R7433 63%/45d — the
> exact percentages the operator's register showed) and the CHECK-INPUTS warning carries a
> one-click "Use the file's own values". Standing guards: test_export_wiring (every button
> wired + every wire answers), test_sra_export_reuse, both mutation-proven.
>
> ## ADR-0360 also — the /sra bars drill; every drill offers every field
> Float-exposure/Risk-flags segments joined sf-drill (hover names count; click lists exactly
> the counted activities). STANDARD_FIELDS widened 6 -> full task-level catalog (verbatim
> values, None never 0) — every drill's add-column list, /groups filters, and drill exports
> now offer any ingested MS Project field + all custom fields. test_sra_bars_drill pins it
> end-to-end (mutation-proven).
>
> ## ADR-0361 — unrestricted AI mode + the known-pass/known-fail battery
> Fourth opt-in Q&A mode: verbatim, ungated, INVITED to calculate; receives a bounded
> 400-row activity data block. Law 1 unmoved (same loopback backends; Null stays closed —
> pinned). Battery: a measured-CLEAN 25-activity program (every populated DCMA check PASSES)
> + 14 seeded twins with DECLARED collateral and a no-undeclared-flips assertion; pairs for
> float bands, completion, manipulation (honest re-status = zero findings); every page
> renders on clean/wrecked/TP4 corpora. Nine wrong seed assumptions died on contact and are
> encoded (DCMA08 flags BASELINE duration; the CP test is only defeated by a mid-chain MFO
> pinning a task's own finish; late-vs-baseline must not cross the DD...). 21 passed,
> harness mutation-proven.
>
> ## Next
> Battery phase 2: cei · hmi · fei/bri · evm · schedule_quality · forecast · SRA-readiness
> pairs (framework in place). Phase 3 monolith split resumes at **margin 379** (re-measure
> the closure; ADR-0350/0351/0352/0358 rules). Then: driving-corridor fixture · the three
> page-lede-less pages · /groups Activities counting summary rows (ADR-0343) · installers vs
> known-good constraints · the P80/P90 recurring-calendar-exception residual (own unit;
> note ADR-0359 showed OAT deltas match SSI exactly, so the recurring-exception effect did
> NOT surface in this comparison) · Phase 6 docs. **Operator:** license · branch-protection ·
> proprietary reruns · OR-04 · whether the July mpp/ oracle should re-export under replace
> semantics for a tighter v1 tolerance band.
>
> ## Carried forward
> ADR-0353..0358 closed — do not re-open. The workbook Mean/StdDev cells are UNWEIGHTED
> (held again); the occurrence-weighted histogram is the only oracle. A parity delta is a
> claim about INPUTS first (two sessions running). Run the mutation BEFORE trusting any pin;
> assert the ORIGINAL anchor absent (the probe harness caught its own suffixed mutation
> AGAIN this session — the in-harness assert works). `pydantic>=2` NOT a safe floor (2.6);
> `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2 floor). `ruff check .` whole tree as
> `python -m ruff`. Never `git checkout` to undo a mutation — cp from scratchpad.
> `grep -c` exits 1 on zero — chain with `;`. The /analysis focus->tip family is
> load-sensitive — do NOT chase. bandit B608 on HTML f-strings with "from" → the house
> `# nosec B608 (HTML, not SQL)`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
