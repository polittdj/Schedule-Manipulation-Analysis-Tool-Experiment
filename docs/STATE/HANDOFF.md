# Handoff — 2026-07-19i (interactive legends phase 2 — trend.js stacked/grouped; v1.0.84; highest ADR 0276)

> ## STATUS (current) — operator (after merging #419 phase 1): standing "do all you can" → phase 2 of the interactive-legend rollout (ADR-0276, no new ADR). **trend.js is now FULLY covered:** the multi-series line chart (phase 1) PLUS the **stacked-bar** and **grouped-bar** charts now have click-to-show/hide legends + all/none. Discovery: **`curves.js` already had NATIVE toggles** (`buildLegend` has its own show/hide + Show-all/Hide-all), so the Curves page is already done and untouched. Highest ADR **0276**.
>
> - **Phase 2 change (trend.js):** the stacked-bar (`stackedBarChart`) and grouped-bar draws now tag
>   each `rect` with `data-series="<segment/group label>"` (re-tagged every frame), and their
>   `legend(...)` calls opt in (`{toggle: segments.length>1}` / `{toggle: groups.length>1}`). The
>   generic `SFLegend` module (ADR-0276, phase 1) needed **no change** — it just works once the marks
>   are tagged. (Stacked segments hide leaving their gap — an honest "removed" look; grouped bars hide
>   cleanly.) The "ahead/behind favorable" chart at the 636 call site stays static (its 2 legend
>   labels are semantic, not separable series).
> - **Verified:** `tests/web/test_legend_toggle_wiring.py` extended to pin the stacked + grouped
>   opt-ins + `data-series` tags; the `SFLegend` node harness (`legend_toggle_harness.mjs`) already
>   covers the toggle/all-none/redraw-persist logic. Full local gate green (ruff, format, mypy 116,
>   bandit exit 0, node, pytest). v1.0.83 → **1.0.84**, wheel + 9 installers lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state.
> - **State:** v1.0.84; **ADR-0276** highest (no new ADR — phase-2 rollout); wheel + 9 installers
>   lockstep. Branch `claude/conditional-branching-contingency-bi6g00` (harness-designated; restarted
>   from merged main 12f7a51 = v1.0.83 #419). This session's PR carries legend phase 2.
> - **NEXT: interactive legends phase 3+ (remaining hand-rolled-legend charts).** Adopt the SFLegend
>   convention (`data-series` on marks + `data-series-toggle`/`data-series-all` on the legend) chart
>   by chart, one focused PR each per DESIGN-SYSTEM. Remaining (curves.js DONE natively; trend.js DONE):
>   `margin_dashboard.js` · `performance.js` · `path_evolution.js` · `cei.js` · `dashboard.js` ·
>   `sra_grid.js` — check each for a native toggle first (like curves had). Also still OWED by the
>   operator: ADR-0261 PowerShell crash log + large dataset; ADR-0258 Claude-Design portfolio prompt.
>   The file-free #331 Hulett backlog remains DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
