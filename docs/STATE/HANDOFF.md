# Handoff — 2026-07-24d (one tooltip + 1.5s hover-intent delay; Acumen parity ON by default; v1.0.95; highest ADR 0287)

> ## STATUS (current) — two operator-reported UX/defaulting fixes. Version **1.0.95**. Highest ADR
> **0287**. Branch `claude/smat-tool-continuation-uskbh7` (restarted fresh from `origin/main` at
> `b8edf0f` after PR #432 / ADR-0285 squash-merged).
>
> - **ADR-0286 — ONE tooltip, revealed after 1.5s of hover-intent.** The operator hovered a DCMA-14
>   check name and got **two overlapping boxes**: the rich `.dcma-tip` callout AND the browser's
>   native `title=` tooltip (`_dcma_metric_cell` emitted both by design, as a no-CSS fallback). New
>   **`web/static/tooltips.js`** (loaded from `_LAYOUT`, so every page) normalises every `title` at
>   runtime: a trigger that already has a custom tip has its `title` moved to `data-sf-title`
>   (text preserved, browser box gone); a **plain** `title` is **promoted** to `data-sf-hint` so it
>   renders as the same styled callout. Replaced elements (input/select/img/svg/…) can't host
>   `::after`, so they keep the native tooltip — still exactly one. Delay is a **`transition-delay`**
>   (`--sf-tip-delay: 1.5s`, defined once in `hud.css`), NOT a timer, so moving away before it
>   elapses cancels the reveal; `.dcma-tip` moved off `display` (untransitionable) to
>   opacity/visibility; the JS float tip uses `window.SF_TIP_DELAY_MS` with `clearTimeout` on leave.
>   Keyboard focus stays instant. A `MutationObserver` covers client-rendered charts/tables.
> - **ADR-0287 — Acumen parity mode is ON by default.** The operator reported (twice) that the
>   DCMA-14 numbers "don't match Acumen". Root cause was **not** an engine defect: their screenshot
>   read "parity mode ☐ OFF" and every value on it reproduced the engine's DEFAULT output exactly;
>   with the box ticked the same file is already **UID-exact** vs Acumen. Re-verified this session
>   that the `.mpp` + Acumen detail export were **md5-identical** to the morning's copies and the
>   re-exported ribbon carried identical numbers. So `SessionState.dcma_acumen_parity` now defaults
>   **True**. **ENGINE defaults are unchanged** (`acumen_parity: bool = False` everywhere), so no
>   golden/parity test shifts. Since ADR-0285 the toggle is end-to-end, so every surface stays
>   consistent.
> - **Test hygiene:** tests that pinned pure-logic payloads now **state their mode explicitly**
>   (`st.dcma_acumen_parity = False`) instead of inheriting the session default — the two default
>   dashboard SHA goldens, the scope-epoch guard, and the LRU-residency perf gate (its cache key
>   would otherwise carry `A=1`). `test_dcma_scope.py` asserts the box renders **checked** on a fresh
>   session and exercises off→on. New `tests/web/test_tooltips.py` (6 pins).
> - **Gate:** full suite **2628 passed** on the pre-change base; after these changes re-run the FULL
>   gate before merge. Wheel + 9 installers regenerated to 1.0.95.
> - **PRs merged today:** #430 (ADR-0283 DCMA-09 parity population), #431 (ADR-0284 Fix E),
>   #432 (ADR-0285 parity findings). This work is the next PR.
> - **NEXT — the deferred perf backlog is UNSTARTED and is what the operator asked for next**
>   (separate PRs, never folded with a behaviour fix): lazy status-UID payload trim (486 KB → ~40 KB
>   @ 50 versions); home.js bounded-concurrency pre-read; manifest-projection memo;
>   instrument-then-byte-budget the `cpms`/`summaries`/`dash_cores` tiers; MPP capability probe;
>   importer profiling; and the **`web/app.py` monolith split** (~19k lines — its OWN PR, no
>   behaviour change in the same diff). Also still OWED by the operator: the ADR-0261 PowerShell
>   crash log; the Claude-Design portfolio prompt. Consider committing the newer `20260708` `.aft` +
>   refreshing `test_aft_formula_audit.py`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
