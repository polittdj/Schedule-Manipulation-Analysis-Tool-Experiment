# Handoff — 2026-07-24b (Fix E: target control + endpoint banner scoped to the active project; v1.0.93; highest ADR 0284)

> ## STATUS (current) — shipped **Fix E** (the deferred cross-project UID leak from ADR-0281) as
> **ADR-0284**, on a branch restarted fresh from `origin/main` after PR #430 (ADR-0283) squash-merged.
> Version **1.0.93**. Highest ADR **0284**. Branch `claude/smat-tool-continuation-uskbh7` (from
> `origin/main` at `54f06ce`).
>
> - **The leak:** `_render_target_control` and `_endpoint_banner` iterated `state.schedules.values()`
>   — every version across EVERY project — instead of the active project. The dropdown keys milestones
>   by `unique_id` and keeps the first label, so a UID shared across projects (e.g. UID 100 in both)
>   could show a **foreign project's label**; the banner's omitted-count described the whole session,
>   not the analysed project, and a UID present only in a non-active project still marked the endpoint
>   "found."
> - **Fix (operator decision: active project only):** both now iterate **`state.ordered_versions()`**
>   (the ADR-0258 active-project population, exclusions dropped). Dropdown lists only the active
>   project's milestones (still the union across its VERSIONS, so a milestone deleted later stays
>   selectable); banner counts the active project. `ordered_versions()` takes the reentrant `RLock`, so
>   the render path is deadlock-safe. Single-project sessions are **unchanged** (`ordered_versions()`
>   returns every loaded version there).
> - **Test:** removed the `xfail(strict=True)` marker from
>   `test_target_control_and_banner_scope_to_active_project` — it now asserts the fix directly
>   (Alpha+Beta both carry UID 100, Beta active → no "ALPHA COMPLETE" leak, banner shows Beta's 2 of 2,
>   not 4). Docs: ADR-0284. Wheel + 9 installers regenerated to 1.0.93 (lockstep green).
> - **Gate:** `tests/web/` green; the un-xfailed test passes; ruff/format/mypy clean on the changed
>   files. (Run the FULL gate — ruff/format/mypy/bandit/pytest cov/node — before the squash-merge.)
> - **NEXT — the big one (its own PR, do NOT fold): ADR-0282 Option A — findings/narrative FOLLOW the
>   parity audit when parity mode is on** (operator chose this 2026-07-24). Today `recommend()` /
>   `build_narrative()` derive findings from the DEFAULT audit even under parity, so the ribbon and the
>   narrative can disagree (Large Test File2 is the concrete case: High Float 660/717, Neg Float
>   112/123, Missed 1095/1221, CPLI 0.59/1.0, BEI 0.53/0.51). Threading the parity audit through the
>   recommender changes findings/narrative/briefing/risk-matrix whenever parity is on — needs **fresh
>   parity-variant goldens** and **re-pinned `ai.citations` goldens**; it is testimony-facing, so do it
>   carefully with full ground-truth verification (Law 2 / ADR-0240). Then the deferred perf backlog
>   (lazy status-UID trim, home.js pre-read, manifest memo, tier byte-budgeting, MPP probe, importer
>   profiling, `web/app.py` monolith split — never with a behavior fix).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
