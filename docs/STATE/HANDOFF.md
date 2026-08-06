# Handoff — 2026-08-06 (SRA-LEGACY closed: one basis, one axis; ADR-0353; v1.0.168)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0353, **v1.0.168**.
> First Fable 5 Max reserved item (ADR-0240) done: the legacy `/sra` cross-basis defect carried
> since `audit/SRA-ROOTCAUSE-20260730.md` §6 is **closed**. `compute_sra` now computes its own
> **all-ML anchor** (the `cpm` parameter is REMOVED — a foreign-basis anchor is structurally
> unrepresentable), and the whole legacy date surface (`*_date` fields, `_sra_data`'s
> S-curve/histogram/mean/marker, `reserve_recommendation` rows, the buffer route's committed
> conversion) carries `stored_finish_correction` — ADR-0256's pattern, finally adopted by the
> path it was written for. Wheel + nine installers rebuilt at **v1.0.168**.
>
> ## MEASURED, BOTH SIDES (all four goldens, before any code was written)
> **Leg A (basis):** EVM1 (2 in-progress, 0 resume>stop — the class ADR-0309's floor cannot
> rescue) det_pct **0.9910 → 0.4930**; the realism card stops calling a progressed plan
> "conservative". EVM2/P2/P5 (all resume-floored): det_pct **unchanged to 4 dp** — blast radius
> exactly the resume-less class. **Leg B (dates):** correction measured **15 d 1 h on Project2**;
> its buffer panel at committed = stored plan finish went **confidence 1.0000 / P80 reserve
> 0.0 wd → 0.4900 / 2.4 wd** — the optimistic-direction failure, inverted. Sim offsets
> p10/p50/p80/p90 **byte-identical pre/post everywhere** (the simulation itself untouched).
>
> ## VERIFICATION SHAPE (prove-able-to-fail, all five fired)
> Five mutations, each verified original-anchor-ABSENT by re-reading the file, each failing
> exactly its guard, each restored from a scratchpad copy (never `git checkout`): anchor
> reverted → basis test + both web pins; engine correction zeroed → date-axis test; reserve row
> correction dropped → scorecards pin; `_sra_data` correction zeroed → `/api/sra` pin; committed
> converted naively → buffer pin. New pins: `tests/engine/test_sra.py` (progressed chain),
> `tests/engine/test_scorecards.py` (correction moves dates, never offsets/confidence),
> `tests/web/test_sra_stored_axis.py` (end-to-end, inline resume-less progressed MSPDI).
> Parity **49 passed**. The synthetic SRA suite was byte-identical by construction (unprogressed,
> no stored finishes) — which is WHY the defect lived: no fixture exercised the forensic target.
>
> ## TRAPS PAID FOR THIS SESSION
> `grep -c` **exits 1 on zero count** — it silently short-circuited an `&&`-chained mutation run;
> chain verification greps with `;` not `&&`. A repo-wide sed for `key, sch, a = picked` hit
> THREE routes (two still use `a`) — line-target sed repairs, then whole-tree ruff. PATH ruff is
> stale 0.15.8 (`/root/.local/bin`); the gate ran `python -m ruff` = 0.16.1 (the CI resolver).
>
> ## Next
> Fable 5 Max queue (ADR-0240): **V3** (`engine/msp_filters.py` elapsed literals — product
> decision first: elapsed axis vs reject-with-warning; present measured options) · **ADR-0348's
> `tod + per_day == 1440` residual** (no oracle in corpus — decision-shaped). Then the standing
> queue: twelve page families (`integrity` 402 · `margin` 379 · `trend` 348 · `ssi` 335 ·
> `mission` 304 · `how` 290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 · `evm` 208
> · `forecast` 204) each adding to `LAYER_ORDER` + `VIEW_MODULES` + the monkeypatch sweep over
> ALL bound names + the renderability pre-flight · a driving-corridor fixture · the three
> `page-lede`-less pages (`/briefing`, `/path`, `/compare`) · `/groups` "Activities" counting
> summary rows (ADR-0343) · nine installers vs `-c constraints/known-good.txt` (62 lockstep
> tests) · Phase 6 docs. **Operator only:** license · branch-protection contexts · intake
> re-upload · proprietary-tool reruns · OR-04.
>
> ## Carried forward
> XER importer has NO `resume` read (P6 suspend/resume differs — unmeasured, rootcause §6).
> EVM2's det date now displays stored 2012-10-04: ADR-0108's 2-wd residual is absorbed into the
> DISPLAY by the anchoring (SSI-consistent, deliberate, ADR-0353 Consequences); offset space
> still shows it — do NOT re-report it as a new date bug. Correction fidelity is day-scale
> (sub-day constants slide within the day — EVM1's 7 h). The `/analysis` focus→tip family is
> load-sensitive — do NOT chase. `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110`
> is an AIR-GAP VIOLATION (0.110.2 floor). Run `ruff check .` — the WHOLE tree — as
> `python -m ruff`. Never `git checkout <file>` to undo a mutation — `cp` from a scratchpad copy.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
