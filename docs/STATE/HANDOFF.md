# Handoff — 2026-07-17 (base-CPM single-calendar fail-soft disclosure, #26; v1.0.61; highest ADR 0252)

> ## STATUS (current) — ADR-0252: the `/analysis` "Working calendar" panel now DISCLOSES that the base CPM solves on the single project calendar (ADR-0028) when a file assigns some activities their own calendar — closing standing queue item **#26**. Additive, read-only disclosure: no engine behavior, no computed number, no parity target changes. Version 1.0.60 → 1.0.61 (wheel + 9 installers in lockstep). Full gate green (2343 passed) incl. `parity`.
>
> - **The gap (route/code-verified).** Base CPM (`engine/cpm.py`) uses `schedule.calendar` for all
>   date/float arithmetic and references `calendar_uid` NOWHERE; per-task calendars are honored only
>   by the driving-slack / SSI path (ADR-0118) and Gantt shading (ADR-0243/0382). So on a
>   multi-calendar file the base-CPM dates/float/critical path are a single-calendar approximation,
>   and the "Working calendar" panel showed only the one project calendar — reading as the whole time
>   basis. Surfaced/queued by the ADR-0251 mixed-basis sweep; independent of #13, testable today
>   against the committed leveled Large Test File.
> - **What changed (additive disclosure + tests only).** New pure helper
>   `engine.cpm.off_project_calendars(schedule)` → the deduped, uid-sorted calendars carried by
>   active, non-summary tasks whose WORKING PATTERN materially differs from the project calendar
>   (compares `working_minutes_per_day` / `work_weekdays` / `holidays` / `working_days` /
>   `day_segments`, order-independent; `uid`/`name` are identity → a same-pattern twin never cries
>   wolf; a `calendar_uid` absent from the registry is skipped, fail-soft; read-only, moves no number).
>   `web/app.py::_calendar_panel` adds a `notice info` when it's non-empty: names the off-project
>   calendars and states the base CPM models the single project calendar (ADR-0028) so a date/float it
>   computes (where the file carries no stored value) is a single-calendar approximation for those
>   activities, while the file's stored dates and the Path Analysis / Driving Path views honor each
>   task's own calendar (ADR-0118). Silent on single-calendar files.
> - **Verified against real data (Law 2 — no number moves).** Leveled Large Test File (project
>   "Dynetics Standard"; some activities on "ZIN Project Calendar", a different holiday set) → the
>   disclosure fires and names ZIN; single-calendar Project5 → silent. Regression pins:
>   `tests/engine/test_off_project_calendars.py` (predicate: same-pattern twin, summary/inactive
>   exclusion, dangling `calendar_uid`, dedup/sort, + real Leveled/Project5 anchors) +
>   `tests/web/test_calendar_disclosure.py` (panel discloses on multi-cal, silent on single-cal).
>   4-theme Chromium check green (console/daylight/apollo/jarvis).
> - **State:** v1.0.61; **ADR-0252**; wheel `dist/wheel/schedule_forensics-1.0.61-py3-none-any.whl`
>   rebuilt + all 9 installers regenerated (lockstep test green); full gate green (ruff / ruff format
>   --check / mypy --strict / bandit exit 0 / node --check / full pytest 2343 passed incl. `parity`).
> - **#13 (XER per-task calendars) stays PARKED** pending the operator's real `.xer` files (the current
>   JUICE files are `cals=0`; can't be uploaded today). Landing parity-relevant XER importer behavior
>   with no real reference to validate would cut against Law 2 — it resumes as a proper parity pass when
>   the files arrive. #26 was taken instead because it needs no owed files and carries no fidelity risk.
> - **NEXT — the standing queue:** **#13** XER per-task calendars (PARKED — needs the owed `.xer`
>   files) → **F3c** parameterized expected margin → roles front-end (v4 F4). Deferred perf (parked in
>   ADR-0249's harness): import peak memory rides MSPDI streaming, AI-cancellation rides its own PR —
>   deterministic gates only, never wall-clock. From the ADR-0251 verify (behavior, own PR each):
>   unify family-B option plumbing — forward the toggles to `/api/evolution`, decide the full-trace
>   export's basis, option-solve or hide drill field columns (each needs golden re-validation).
>   Optional: extend per-task Gantt shading to the path-evolution + SRA grids; extend the #26
>   disclosure to any new base-CPM-float surface. A true per-task-calendar base CPM is a much larger
>   change (its own ADR, reference-validated) — never a silent behavior swap. Operator-side (no code):
>   the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web UI + the §4 root-vs-mpp
>   `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
