# Handoff — 2026-07-19g (post-#417 audit hardening + Mission Control play/stop fix; v1.0.82; highest ADR 0275)

> ## STATUS (current) — operator (after merging #417): "continue [the read-only Ultracode audit] AND address the Mission Control play/stop bug + interactive legends." This session ships the audit hardening + the play/stop fix as **v1.0.82**; the interactive-legend feature is scoped as the phased **NEXT** (see below). Highest ADR **0275**.
>
> - **Read-only Ultracode audit of merged #417 (ADR-0274)** ran (4 dims, adversarial verify). Lead
>   reconciled + fixed the real findings:
>   - **M1 (medium, 2-reviewer + lead repro):** a **summary / inactive** monitor passed the
>     augmentation gate (built from ALL tasks) but is absent from `compute_cpm().timings` / the
>     override map (non-summary AND active) → finish-metric **KeyError aborted the whole SSI run**
>     (422); duration-metric **silently read 0** → wrong plan mix reported `applied=True` (Law-2 silent
>     wrong number). FIX: gate the monitor + plan endpoints on `non_summary(schedule)` in
>     `_augment_with_conditionals`; add `is_active` to the web `_valid`. Inert + disclosed instead.
>     +3 engine regression tests.
>   - **L5:** `/sra/conditional` `_uid` used `isdigit()` (admits `--5`, `²` → 500). FIX: `int()` +
>     ValueError guard. **M2/H1/M3 (tests):** strengthened the tautological which-plan-wins web
>     assert (known-side, threshold 0 → Plan B 100%); added the missing **DOCX** disclosure test;
>     added a **Save/Load fidelity** round-trip test (metric/trip_when/threshold/plan durations).
> - **Play/stop bug (Mission Control) — FIXED (ADR-0275).** Root cause: the master "Play all" steps
>   every chart by programmatically clicking their Next buttons; a per-chart Stop only cleared that
>   chart's own timer, so the master kept stepping it ("hit stop, kept playing", worst when enlarged).
>   FIX: a shared **`window.SFPlayAll`** coordinator in `chartframe.js` — masters (`mission.js`,
>   `trend.js #sfPlayAll`) register their `stop()`, and a **capture-phase** document listener stops
>   every master on a **TRUSTED** user click on any per-chart animation control. The master's own
>   `element.click()` is `isTrusted=false`, so it never stops itself (the load-bearing distinction).
>   Verified by a Node harness (`tests/web/js/playall_harness.mjs` + `test_playall_js.py`).
> - **Verified:** full local gate green (ruff, format, mypy 116, bandit exit 0, node, pytest — engine
>   conditional 14 + ssi-web + playall). v1.0.81 → **1.0.82**, wheel + 9 installers in lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state.
> - **State:** v1.0.82; **ADR-0275** highest; wheel + 9 installers lockstep. Branch
>   `claude/conditional-branching-contingency-bi6g00` (harness-designated; restarted from merged main).
>   This session's PR carries the audit hardening + play/stop fix.
> - **NEXT: interactive legends (operator ask, phased UI work — NOT yet built).** "Click a legend
>   entry on ANY chart to show/hide that series, plus all/none, on ALL charts/pages." Architecture
>   finding: there is **NO shared legend helper** — ~18 chart modules each hand-roll their legend
>   (`trend.js::legend`, `curves.js::buildLegend`, `performance.js::legend`, `path_evolution.js::legend`,
>   `margin_dashboard.js::legend`, `sra_grid.js::renderLegend`, `dashboard.js::legend`, cei.js inline,
>   …), and a series toggle needs each chart's series SVG elements TAGGED with a key. Per
>   DESIGN-SYSTEM.md ("never big-bang; one page shell per PR") this is a **phased** rollout: build one
>   reusable `SFLegend` toggle module (convention: `data-series` on series elements +
>   `data-series-toggle` on legend swatches + an all/none control, wired generically in the shared
>   layer), then adopt it chart-by-chart starting with **trend.js** (the CEI-across-periods chart the
>   operator screenshotted) → curves/margin → the rest. Also still OWED by the operator: ADR-0261
>   PowerShell crash log + large dataset; ADR-0258 Claude-Design portfolio prompt.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
