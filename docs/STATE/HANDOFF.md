# Handoff — 2026-07-18 (operator UX pass: launcher self-diagnosis, Gantt visibility, +/- zoom, alphabetical group dropdowns, automate-crash guard; large-dataset role; v1.0.66; highest ADR 0257)

> ## STATUS (current) — ADR-0257: operator session — a real run (five projects loaded, one large) surfaced a cluster of UX + stability problems. Chose the order and shipped the concrete, **browser-verified** (Playwright) fixes; recorded the deep performance plan for next session (it is parity-/engine-sensitive and needs the operator's owed PowerShell crash log + their large dataset). Version 1.0.65 → 1.0.66 (wheel + 9 installers in lockstep).
>
> - **Shortcut now self-diagnoses.** `pythonw` discards output, so any pre-serve failure (rebuilt/moved
>   venv, missing dep, half-applied edit) died silently → browser on a dead port. New
>   `src/schedule_forensics/__main__.py` guarded bootstrap wraps the **import itself** → full traceback
>   to a console, or a native **Windows message box + repair recipe** when windowless (writes nothing to
>   disk). Shortcuts retargeted `-m schedule_forensics.launcher` → **`-m schedule_forensics`**; `.bat`
>   `>/dev/null` → `>nul`. Re-running the installer re-points a stale icon (the usual real cause). The
>   app builds+serves cleanly here, so the operator's failure is almost certainly environmental.
> - **Gantt fixed:** bars were invisible + no right-scroll because `colresize.js` forces
>   `table-layout:fixed` but never sized the timeline column (it collapses) — now sized to content in the
>   **shared** colresize (fixes every Gantt). Initial view lands on the **data date ~1 inch right of the
>   frozen columns** (`scrollToDataDate`); ~1 inch right margin added. **Scale slider → − / + buttons**
>   (`#vizZoom` now a hidden px/day carrier; Fit/Timescale untouched).
> - **Filters/Groups → simple alphabetical dropdowns:** field/breakdown A–Z; the checkbox popup replaced
>   with a native alphabetical value `<select>` (single-value UI; backend still ORs repeated `value{i}`).
> - **Automate-crash guarded:** Performance "master stepper" `setInterval(…,1800)` (redraws 13 charts,
>   piled up on 5 large files → crash) → **`setTimeout`-chained + pause-when-hidden**. No numbers change.
> - **Controls validation:** Playwright sweep of **all 32 main pages** = HTTP 200, **zero JS errors**;
>   changed controls exercised live (Gantt +/−/Fit, group field→value dropdown + Apply, Performance
>   play/stop). Exhaustive per-widget + 5-large-file stress continue next session.
> - **New audit role (ADR-0240):** *Performance & Scalability / Large-Dataset Reliability Engineer* —
>   owns not-bog-down/not-crash under many/large schedules; drives the deep-perf plan; re-validates every
>   change against Law 2.
> - **State:** v1.0.66; **ADR-0257**; wheel + 9 installers in lockstep; affected suites green
>   (launcher/packaging/installer, gantt/visuals/ui-scale, groups/filters/global-filter, performance).
>   Full gate to finish on the branch.
> - **Two defaults to confirm with the operator (trivially adjustable):** the DD-line landing (an inch
>   right of the frozen grid vs. an inch from the right edge); the single-value group dropdown (vs.
>   restoring multi-value OR).
> - **OWED by the operator:** the **PowerShell session log** ("weird stuff") — never received; needed to
>   confirm the shortcut's real failure and the crash. Plus a **large dataset** to reproduce the lag/crash.
> - **NEXT — deep performance (the "lag"), all parity-safe, re-validate each (ADR-0257 §"Recorded"):**
>   P1 `_invalidate_scope` nukes the whole analysis cache on any filter/target/mode change
>   (`web/app.py:788`) — make surgical / key by `(key, scope-signature)`. P2 `_solvable_versions`
>   (`app.py:3046`) builds the full monolithic `_compute_analysis` (`app.py:498`) when only `.cpm` is
>   needed — split lazy. P3 `_performance_data` (`app.py:15796`) + O(months×tasks) `work_to_go_census`
>   (`performance_summary.py:132`) uncached — cache per (version, scope), bucket the census. P4 session
>   `_lock` held across compute (`app.py:947`). P5 offload no timeout (`offload.py:90`), unbounded OAT
>   sweep (`app.py:5996`). Add a latency regression gate. THEN the pre-existing queue: **#13** XER
>   per-task calendars (PARKED) → SEC-2/SEC-3 hardening proposal → ADR-0251 family-B unify → zero-margin
>   SRA toggle → roles i18n catalog.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
