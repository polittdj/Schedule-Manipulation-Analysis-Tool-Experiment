# Handoff — 2026-07-17 (F3c: user-parameterized NASA margin requirement rate; v1.0.62; highest ADR 0253)

> ## STATUS (current) — ADR-0253: the NASA Gold-Rule margin-requirement rate (work-days per program year) is now OPERATOR-SETTABLE on the Margin Dashboard — closing standing queue item **F3c** and completing the F3 margin feature (F3a/3b = ADR-0230). The engine already accepted the parameter; this is the session / UI / export wiring, engine math untouched. Version 1.0.61 → 1.0.62 (wheel + 9 installers in lockstep). Full gate green (2349 passed) incl. `parity`.
>
> - **The gap.** The dashboard measures effective margin against the NASA Gold-Rule requirement
>   `days-to-go × rate / 365` (30 work-days per program year). `compute_margin_dashboard` already
>   took `gold_rule_per_year`, but no caller set it — every render/export used 30. The Schedule
>   Management Handbook states margin as a program-**managed** guideline (30/yr is the default, not a
>   fixed law), so different programs carry a different rate; F3c exposes it to the operator.
> - **What changed (session/UI/export wiring; engine math untouched).** `_GOLD_RULE_DAYS_PER_YEAR` →
>   public `GOLD_RULE_DAYS_PER_YEAR` (one source of truth). `SessionState.margin_rate` (default 30) +
>   `set_margin_rate` — fail-soft, accepts `(0, 365]` else keeps the current rate; no cache
>   invalidation (the rate feeds only the freshly-computed requirement line, not the analysis/summary
>   caches). `GET /margin?rate=` applies it; `_margin_rate_control` renders a cited GET form (number
>   input + Apply + a "Reset to 30" link off-default). `_margin_dashboard_for` threads `st.margin_rate`
>   into the engine. `MarginDashboard.gold_rule_per_year` carries the rate used → the
>   `/api/margin/dashboard` JSON and the Excel/Word export both state the basis. The verbatim
>   50%-consumed corrective-action threshold stays FIXED (a cited NASA rule, not a guideline).
> - **Verified.** Engine (`tests/engine/test_margin_dashboard.py`): doubling the rate doubles
>   `nasa_rqmt_wd` (but for each value's 1-dp rounding), a higher rate only adds triggers, and no rate
>   arg reproduces the 30/yr requirement exactly. Web (`tests/web/test_margin_dashboard_view.py`): the
>   control renders with the current rate, `?rate=` changes the requirement + persists on the session,
>   an invalid rate is fail-soft (keeps 30), and the export states the rate. 4-theme Chromium check
>   green (console/daylight/apollo/jarvis).
> - **State:** v1.0.62; **ADR-0253**; wheel `dist/wheel/schedule_forensics-1.0.62-py3-none-any.whl`
>   rebuilt + all 9 installers regenerated (lockstep test green); full gate green (ruff / ruff format
>   --check / mypy --strict / bandit exit 0 / node --check / full pytest 2349 passed incl. `parity`).
>   **F3 margin feature COMPLETE** (F3a/3b ADR-0230 + F3c ADR-0253).
> - **NEXT — the standing queue:** **#13** XER per-task calendars (still PARKED — needs the operator's
>   owed `.xer` files; the current JUICE files are `cals=0`, can't be uploaded today) → **roles
>   front-end (v4 F4)**. Deferred perf (parked in ADR-0249's harness): import peak memory rides MSPDI
>   streaming, AI-cancellation rides its own PR — deterministic gates only, never wall-clock. From the
>   ADR-0251 verify (behavior, own PR each): unify family-B option plumbing — forward the toggles to
>   `/api/evolution`, decide the full-trace export's basis, option-solve or hide drill field columns
>   (each needs golden re-validation). Optional: extend per-task Gantt shading to the path-evolution +
>   SRA grids; extend the #26 base-CPM single-calendar disclosure to any new base-CPM-float surface.
>   Operator-side (no code): the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web UI +
>   the §4 root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
