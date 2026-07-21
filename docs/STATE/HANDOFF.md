# Handoff — 2026-07-21 (interactive legends phase 3a — performance.js + cei.js; v1.0.85; highest ADR 0276)

> ## STATUS (current) — operator (after merging #420 phase 2): standing "do all you can" → phase 3a of the interactive-legend rollout (ADR-0276, no new ADR — extended with a phase-3 note). **performance.js** (the G1–G4 census / flow / index / burden families — 5 legend-bearing charts) and **cei.js** (the bow-wave chart the operator NAMED: "when I'm looking at CEI, I want to select ... milestones or tasks") now have click-to-show/hide legends + all/none. Highest ADR **0276**.
>
> - **The load-bearing new mechanism — a stable-scope marker.** Phase 1's `scopeFor` returns the
>   *smallest* ancestor holding the series, which is correct when the legend sits OUTSIDE the svg
>   (trend.js's `.chart` wrap survives redraws). But performance.js / cei.js draw the legend INSIDE an
>   svg that `frame()` / `render()` **rebuild every animation frame**, so that ancestor is the
>   transient svg and the hidden set dies on the next step. **Prototype-verified the bug then the fix**
>   against the real module (`scratchpad/legend_scope_verify.mjs`): `scopeFor` now honors an explicit
>   `data-series-scope` marker on the persistent host (performance: the `monthFrame` host; cei:
>   `#ceiChart`), so the hidden set + its MutationObserver live on the surviving host. trend.js and all
>   phase-1/2 charts are UNAFFECTED (no marker → identical fallback; existing harness still green).
> - **Series-key discipline:** each legend entry carries an explicit `key` where its short label ≠ the
>   series name it toggles (perf g2 "Scheduled" vs series "Scheduled/forecast"; g2cum "BL starts" vs
>   "Baselined starts (cum)"; g3 monthly-HMI dots share the rolling line's key). cei maps its 3
>   families to BOTH the grouped bars and the running-totals curves so the toggle holds across the
>   bars↔curves mode switch.
> - **Verified:** new node harness `tests/web/js/legend_scope_harness.mjs` (run by
>   `test_legend_toggle_js.py`) boots the real module with a **firing** MutationObserver and proves
>   scopeFor→marked-host, redraw persistence, marked-host independence, all/none-survives-redraw;
>   `test_legend_toggle_wiring.py` gains performance + cei opt-in assertions. Full local gate green
>   (ruff, format, mypy 116, bandit exit 0, node, pytest 2600+). v1.0.84 → **1.0.85**, wheel + 9
>   installers lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state (done: 2026-07-21 entry).
> - **State:** v1.0.85; **ADR-0276** highest (no new ADR — phase-3 note appended); wheel + 9 installers
>   lockstep. Branch `claude/conditional-branching-contingency-bi6g00` (harness-designated; restarted
>   from merged main 2cc8f1e = v1.0.84 #420). This session's PR carries legend phase 3a.
> - **NEXT: interactive legends phase 3b (bespoke).** `margin_dashboard.js` + `dashboard.js` are NOT
>   mechanical adoptions: margin's burn-down legend mixes true series (contingency, requirement line)
>   with per-month conditional **color-states** (the same margin bar is green or red) + marker glyphs
>   (corrective carets, Fig 5-30 band); dashboard's legends live inside an `<a>` card (a toggle needs
>   `preventDefault` or it follows the link), one card scope spans two mini-charts, and toggling a
>   100%-proportion strip leaves gaps. `sra_grid.js` (tint-scale heatmap key) + `path_evolution.js`
>   (descriptive legend) have **no series to toggle** → intentionally SKIPPED. Also still OWED by the
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
