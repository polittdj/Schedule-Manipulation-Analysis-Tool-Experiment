# Handoff — 2026-07-17 (Audit remainder: driving-path per-task shading, xlsx zip-bomb cap, redact() spaced-path leak; v1.0.57; highest ADR 0247)

> ## STATUS (current) — ADR-0247: the five queued ADR-0245 audit-remainder findings are cleared, each lead-verified against the code and fixed with a mutation-verified regression test. None was a live CUI leak or parity break; all shipped in one change on a green tree.
>
> - **(a) `/driving-path` per-task shading — completed the #382 wiring (Option A, Law 2).** The
>   corridor Gantt was doubly dead: `_driving_path_gantt` never emitted the per-row `calendar`
>   `driving_path.js` read, AND the page never called `SFTimescale.setCalendars` (only `/analysis`
>   did), so every row fell back to a flat Mon-Fri shade. Fix: the payload now carries a per-activity
>   `calendar` name (task's own calendar → its registered name, else the project calendar, same as
>   `/analysis`) + a `calendars` union; `driving_path.js` registers it. A 24-hour corridor task now
>   shows no weekend gray. Chromium-smoke-verified (payload + registry + shading render, 0 JS errors).
> - **(b) Gantt-shading node harness.** `tests/web/js/gantt_shading_harness.mjs` loads the vendored
>   `timescale.js` and pins `nonworkStyle` per calendar (Mon-Fri shades weekends, 24-hour does not,
>   global pick overrides per-row). Mutation-verified: dropping the per-row `cellCal` fails it.
> - **(c) `/margin` mixed-basis view+export test.** An 8h→24h schedule through `/margin` + the Excel
>   export asserts the disclosure prose renders and the export shows `mixed — 8h/day vs 24h/day` with
>   `—` (never a fabricated erosion rate). The engine path was tested; the view/export was not.
> - **(d) SRA xlsx zip-bomb cap.** `read_xlsx` decompresses every part through one shared byte budget
>   (`_MAX_XLSX_DECOMPRESSED_BYTES` = 500 MB, parity with `/upload`) via streamed capped reads —
>   bounded regardless of a lying zip header; the two SRA re-import routes also cap the compressed
>   upload before parsing.
> - **(e) `redact()` spaced-path leak.** `_SPACED_FILE_PATH_RE` runs first and folds a path + spaced
>   file name ending in a sensitive extension (UNC / Windows / POSIX) into one inert token, so a name
>   like `\\srv\share\Site Alpha Rebaseline.mpp` no longer leaks its middle words; prose after a
>   space-free path is still spared and `redact` stays idempotent.
> - **State:** v1.0.56 → **1.0.57** (src changed: `app.py`, `driving_path.js`, `xlsx_read.py`,
>   `logging_redaction.py`); wheel + 9 installers rebuilt in lockstep; **ADR-0247**; full gate green
>   (ruff / ruff format --check / mypy --strict / bandit exit 0 / node --check / full pytest incl.
>   the `parity` gate).
> - **NEXT:** **PR-P1** validated perf items (CoPilot #3/#4/#8/#9/#10 + the audit-E summary-logic edge
>   guard; the refuted claims #1/#5/#6/#7-race are documented — do NOT "fix" them) → **#13** XER
>   per-task calendars → base-CPM single-calendar fail-soft disclosure (**#26**) → **F3c**
>   parameterized expected margin → roles front-end (v4 F4). Optional follow-up: extend the per-task
>   Gantt shading to the path-evolution + SRA grids (still project-calendar fallback). Operator-side
>   (no code): apply the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map via the GitHub web UI + the §4
>   root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
