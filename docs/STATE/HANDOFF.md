# Handoff — 2026-07-19h (interactive legends phase 1 — SFLegend + trend charts; v1.0.83; highest ADR 0276)

> ## STATUS (current) — operator (after merging #418): "do all you can without my files" → picked up the operator's earlier **interactive-legend** ask. **Phase 1 shipped as v1.0.83 (ADR-0276):** a reusable, animation-safe `SFLegend` toggle module + its first adopter, the `trend.js` multi-series charts (the CEI-across-periods chart the operator screenshotted). Remaining charts adopt the same convention in phased follow-ups. Highest ADR **0276**.
>
> - **What it does:** click a legend entry on a (wired) chart to **show/hide that series**, plus a
>   **show-all/none** control. "For instance, on CEI, choose whether you're looking at Tasks vs
>   Milestones" — the operator's exact ask.
> - **Module (`static/legend_toggle.js`, `window.SFLegend`)** — generic + opt-in by convention:
>   series SVG carry `data-series="<key>"`, legend entries carry `data-series-toggle="<key>"`, an
>   optional all/none control carries `data-series-all`. ONE delegated document click listener (+
>   Enter/Space) toggles `display` on the matching series within the entry's **scope** (smallest
>   ancestor holding both — trend's `.chart` wrap), so charts on a page are independent.
>   **Animation-safe:** a **lazy per-scope MutationObserver** re-applies the hidden set after each
>   frame redraw (the steppers rebuild their series SVG every frame) and disconnects when nothing is
>   hidden. Air-gap/CSP-safe; **Law-2 honest-N:** it only styles the on-screen SVG (a view filter),
>   never removes data — the hidden data-table / Excel export are untouched.
> - **First adopter (`trend.js`):** `legend(wrap, items, {toggle: series.length>1})` emits the
>   toggle markup + all/none; the multi-series line draw tags each mark (`polyline`/`circle`/value
>   `text`) with `data-series="<label>"` (re-tagged every frame). Single-series charts don't opt in.
>   CSS (`app.css`): pointer/focus affordance + dim/strike an OFF series.
> - **Verified:** `tests/web/js/legend_toggle_harness.mjs` (+`test_legend_toggle_js.py`) — hide/show,
>   per-scope independence, all/none, and the load-bearing **re-drawn element inherits the hidden
>   state**; `tests/web/test_legend_toggle_wiring.py` — module loaded app-wide + serves, trend.js
>   emits the opt-in markup + tags its series. Full local gate green (ruff, format, mypy 116, bandit
>   exit 0, node, pytest). v1.0.82 → **1.0.83**, wheel + 9 installers lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state.
> - **State:** v1.0.83; **ADR-0276** highest; wheel + 9 installers lockstep. Branch
>   `claude/conditional-branching-contingency-bi6g00` (harness-designated; restarted from merged main
>   e0ec367 = v1.0.82 #418). This session's PR carries the legend phase 1.
> - **NEXT: interactive legends phase 2+ (roll the SFLegend convention out chart-by-chart).** The
>   mechanism is generic — a chart adopts it by adding `data-series` to its series marks +
>   `data-series-toggle` to its legend entries (+ `data-series-all`), no per-chart toggle logic. Order
>   (one focused PR each per DESIGN-SYSTEM "never big-bang"): the OTHER trend.js chart types
>   (stacked/segments/groups at the remaining `legend(...)` call sites) → `curves.js::buildLegend` →
>   `margin_dashboard.js` / `performance.js` → `path_evolution.js` → `cei.js` → `dashboard.js` →
>   `sra_grid.js`. Also still OWED by the operator: ADR-0261 PowerShell crash log + large dataset;
>   ADR-0258 Claude-Design portfolio prompt. The file-free #331 Hulett backlog remains DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
