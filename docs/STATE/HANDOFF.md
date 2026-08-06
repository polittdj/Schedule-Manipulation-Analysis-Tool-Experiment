# Handoff — 2026-08-06 (SSI delta root-caused ADR-0356; the 1440 boundary blessed by the operator's oracle ADR-0357; v1.0.171)

> ## STATUS (current) — **pushed to the open PR #546 branch.** ADR-0356, **v1.0.171**.
> The operator reported a significant SSI-vs-tool delta on a NEW `Large_Test_File2.mpp`
> (md5 differs from the committed intake) + their saved setup + SSI's workbook. Full
> ADR-0240 rigor, measured end to end: **the engine is exonerated** — on file-true inputs it
> lands σ within 2.5% (157.3 vs 153.4), P50 within 8 d of SSI's occurrence-weighted
> histogram (NEVER the workbook's unweighted Mean/StdDev cells — 95 d off their own weighted
> mean here). **Root cause: the session replayed a setup captured against an earlier vintage**
> (605/783 factors stale, 939 file-factor tasks absent, 400/435 BC/WC stale; the fired-risk
> lobe ran σ≈110 vs SSI's 41.9 purely from stale factor-5 ranges). R2 in the register template
> was in NEITHER run (R1+R2 overshoots the oracle; the register import route handles the
> operator's workbook perfectly — verified by running it).
> **The product defect:** the app could not read the schedule's OWN stored SRA fields at all —
> a stale setup was the only way to fill the grid, silently. Fixed twice over (ADR-0356):
> `POST /sra/load-from-schedule` seeds factors+BC/WC VERBATIM from the file's fields, and
> setup_version 4 stamps a vintage fingerprint with a CHECK-INPUTS warning (with counts) on
> every mismatched load. Sandbox effectiveness test on the REAL artifacts: the fixed path
> reproduces the exoneration figures exactly (det_pct 0.1280, mean +330.1, σ 157.3).
>
> ## THE SELF-AGREEING ORACLE — fourth discriminator catch in ONE day
> The fingerprint pin re-called the SAME helper as its oracle, so the constant-hash mutation
> passed ("" == ""). Re-pinned on independent properties (64-hex + vintage sensitivity).
> Day's tally: identity fixtures (0353) · identity calendar (0354) · identity population
> (0355) · self-referential oracle (0356). **Run the mutation BEFORE trusting any pin.**
>
> ## Carried findings from the dive (recorded, not chased)
> P80/P90 residual ~20 cal d on this file family ← the importer skips its six RECURRING
> calendar-exception patterns (single-block model, logged at import) — its own unit + oracle.
> The uploaded artifacts are NOT committed (operator's call; they'd make a strong second
> parity oracle — the current one is `ssi_uid152`). The workbook Mean/StdDev-cell trap held
> again. bandit B608 false-positives on HTML f-strings when text contains "from" — the house
> `# nosec B608 (HTML, not SQL)` on the closing line is the pattern.
>
> ## THE 1440 BOUNDARY IS CLOSED — ADR-0357 (all three ADR-0240 reserved items now done)
> The operator's `24Hour_Calendar.mpp` settled it: MS Project stores the RAW instant
> (T01:00/T02:00 finishes, instant-contiguous handoffs), ZERO midnight-spelled stored dates,
> and MSPDI cannot represent "24:00" — next-day 00:00 is the ONLY spelling of a day-boundary
> instant. Current rendering is MSP's own convention; the intuitive 23:59 "repair" would have
> CREATED the parity break. Pinned by `tests/engine/test_1440_boundary.py` (mutation-proven
> against exactly that repair). No code changed. Oracle file NOT committed (operator's call).
>
> ## Next
> Twelve page
> families (`integrity` 402 first, ADR-0350/0351/0352 rules) · driving-corridor fixture ·
> three `page-lede`-less pages · `/groups` Activities counting summary rows (ADR-0343) ·
> installers vs known-good constraints · Phase 6 docs. **Operator:** license ·
> branch-protection · intake re-upload (+ optionally THIS file family as a second oracle) ·
> proprietary reruns · OR-04 · the 24h `.mpp` · whether R2 should be in both runs.
>
> ## Carried forward
> ADR-0353/0354/0355/0356 closed — do not re-open. `%`/`e%` pass-through, 364-day elapsed
> year, 480 absent-property default = MPXJ's OWN behaviour. DATE literals still share C4's
> None shape (recorded in ADR-0355). EVALUATOR_VERSION stays 2. The `/analysis` focus→tip
> family is load-sensitive — do NOT chase. `pydantic>=2` NOT a safe floor (2.6); `fastapi>=
> 0.110` an AIR-GAP VIOLATION (0.110.2). `ruff check .` whole tree as `python -m ruff`. Never
> `git checkout` to undo a mutation — `cp` from scratchpad. `grep -c` exits 1 on zero.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
