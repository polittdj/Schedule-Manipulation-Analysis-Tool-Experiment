# Handoff — 2026-07-21b (interactive legends phase 3b — margin_dashboard.js; v1.0.86; highest ADR 0276)

> ## STATUS (current) — operator merged #421 (phase 3a); standing "do all you can" → phase 3b of the interactive-legend rollout (ADR-0276, no new ADR — extended with a phase-3b note). **margin_dashboard.js** (the executive margin/contingency **burn-down** + margin **erosion** charts) now has click-to-show/hide legends + all/none. With this, **the rollout is substantially complete** — every analysis chart with separable series (trend, curves-native, performance, cei, margin) is covered. Highest ADR **0276**.
>
> - **The new wrinkle — a mixed toggle / static legend.** margin renders **once** (no version stepper),
>   so its legend's svg scope is already stable and it needs **no** `data-series-scope` marker (unlike
>   performance/cei). But its burn-down legend has a swatch that is **not a series**: the margin bars
>   are green above / red below the NASA requirement, and "Below requirement" explains that *recoloring*
>   — toggling it is meaningless. So margin's own `legend()` gained a per-item `static: true` flag: a
>   static entry is a plain, non-clickable color key, while every real series (margin bars — one key for
>   both colors — contingency, requirement line, planned depletion, corrective carets, Fig 5-30 band +
>   diamonds, erosion trend, zero-margin marker) is tagged + togglable. The generic `SFLegend` module
>   needed **no change** (a static entry has no toggle attr → ignored by the module and by all/none).
> - **Verified:** `tests/web/js/legend_static_harness.mjs` (run by `test_legend_toggle_js.py`) boots the
>   real module against margin's shape — one toggle hides both colors of the conditional-color margin
>   series, the static key is inert, all/none skips it. `test_legend_toggle_wiring.py` pins the emitted
>   markup (`static:true` opt-out + tagged marks + explicit `Erosion trend` key). Prototype-verified the
>   shape first (`scratchpad/margin_legend_verify.mjs`). Full local gate green (ruff, format, mypy 116,
>   bandit exit 0, node, pytest). v1.0.85 → **1.0.86**, wheel + 9 installers lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state (done: 2026-07-21 cont. entry).
> - **State:** v1.0.86; **ADR-0276** highest (no new ADR — phase-3b note appended); wheel + 9 installers
>   lockstep. Branch `claude/conditional-branching-contingency-bi6g00` (restarted from merged main
>   35182e4 = v1.0.85 #421). This session's PR carries legend phase 3b.
> - **NEXT: the interactive-legend rollout is substantially DONE.** Intentionally SKIPPED (no separable
>   series to toggle): `dashboard.js` (landing-page summary cards inside an `<a>` link — low value +
>   anchor-wrapping/proportion-strip issues; the per-file charts it links to already have toggles),
>   `sra_grid.js` (tint-scale heatmap key), `path_evolution.js` (descriptive legend). If the operator
>   wants dashboard cards toggled anyway, that needs a `preventDefault` module tweak + per-mini-chart
>   scope split. Also still OWED by the operator (blocks deferred work): ADR-0261 PowerShell crash log +
>   large dataset; ADR-0258 Claude-Design portfolio prompt. The file-free #331 Hulett backlog is DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
