# Handoff — 2026-07-19c (ADR-0272: risk-critical Gantt tint — #331 Hulett #12, Opus Ultracode; v1.0.78; highest ADR 0272)

> ## STATUS (current) — operator said "do all you can without my files, continue with Opus Ultracode"; the #331 phase continues at Hulett #12: the SSI schedule grid's Gantt bars now **tint by Criticality Index** (how often each activity was on the critical path across the last Monte-Carlo run) — the risk-critical view (ADR-0272). Version 1.0.77 → 1.0.78 (wheel + 9 installers in lockstep). **Premise correction caught by verify-everything BEFORE any code:** the task was scoped "pure UI" on the belief SSIResult carried CI — it did NOT (compute_sra_ssi tallied `critical_counts` per iteration then DISCARDED it; CI lived only on the legacy compute_sra/SRAResult path, a different sim). So it needed a minimal ADDITIVE engine change (plumb the already-computed value through), not new math.
>
> - **Engine (`sra.py`, additive — Law 2 clean, no new number):** `SSIResult` gains
>   `criticality: tuple[tuple[int,float],...] = ()` (uid, fraction-of-iterations-critical, asc uid),
>   appended last → inert to the finish-cdf pin + the ssi==jcl equality. `_build_ssi_result` takes
>   `critical_counts` and builds `count/n`; `compute_sra_ssi` passes the counts it already tallies.
>   No engine LOGIC change — the value was computed every run and thrown away; now carried through.
> - **Web:** `SessionState.sra_criticality` (uid→CI) + `sra_criticality_iters` cache the LAST run
>   (set in the `/api/sra/ssi` handler — the grid + run are decoupled fetches). `_ssi_grid_rows`
>   adds `criticality_index` per row; `/api/sra/grid` reports `criticality_available`+`_iters` for
>   provenance; `_ssi_data` echoes `criticality`. `sra_grid.js` `timelineCell` tints the bar
>   `g-bar g-ci-{0..4}` (banded 0/<20/20-50/50-80/≥80%) behind the **"tint by criticality"** toggle,
>   with a legend + "last N-iteration run" provenance; the tint is a ROW property so it survives
>   sort/filter/group/zoom re-renders. `sra_ssi.js` fires a `sf-ssi-run` window event after a run →
>   `sra_grid.js` reloads (no shared-global coupling). Bands reuse the sanctioned risk-heat palette
>   (fixed hexes, theme-independent — the DESIGN-SYSTEM exception); NASA-red stays reserved for the
>   deterministic critical path. i18n +"tint by criticality" ×4 langs.
> - **Verified:** `tests/engine/test_sra_ssi.py` (+3: CI ranks driver>0.95 / off-path<0.05,
>   determinism, all-point-mass 0/1 split); `tests/web/test_sra_grid.py` (+grid-row CI, run→grid
>   provenance) + `test_sra_ssi_web.py` (+toggle/legend/CSS-band/JS-wiring, payload CI). **Browser
>   four-theme check** (`scratchpad/verify_tint.py`, CSP-strict Chromium): the CI→band→color map is
>   correct end-to-end — on Project5's rigid critical path, 122 bars green (CI=0) / 4 red (CI=1.0)
>   in console/daylight/apollo/jarvis. Full local gate green (ruff, format, mypy 116, bandit, node,
>   pytest). v1.0.77 → **1.0.78**, wheel + 9 installers in lockstep.
> - **Standing rule (from #412, now on main):** update `docs/STATE/LESSONS-LEARNED.md` DAILY —
>   append a Part VIII entry when a lesson is learned; it's first-class durable state.
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261
>   on-machine re-validation); Claude-Design prompt (Portfolio US-map/site drill, ADR-0258).
>   #13 XER per-task calendars PARKED.
> - **State:** v1.0.78; **ADR-0272** highest; wheel + 9 installers in lockstep. Branch
>   `claude/handoff-continuation-vistlu` (restarted from main after #411 merged). This session
>   merged #411 (LHS); the Gantt-tint is the open PR at this snapshot.
> - **NEXT (file-free):** the #331 Hulett-deck ranked items after #12 are worked through; re-read
>   issue #331 for the next-ranked item, or pick up the 3 OWED operator inputs when supplied
>   (ADR-0261/0258). Keep the daily LESSONS-LEARNED entry as part of the end-of-session ritual.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
