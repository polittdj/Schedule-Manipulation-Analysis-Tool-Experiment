# ADR-0026 — Second full-audit remediation + operator features (target UID, themes, 20-file cap)

- **Status:** accepted
- **Date:** 2026-06-11
- **Drivers:** operator request ("full quality audit … fix any errors; raise the file cap to 20;
  light/dark mode; a target UID every metric view honors"); three-track audit fan-out
  (engine+metrics / web+ai / importers+model) modeled on ADR-0024's remediation.

## Decision 1 — empty populations are NA; citations have a terminal anchor

A DCMA percentage check over an **empty population** reads NOT_APPLICABLE, never `0%`
(`percent(0, 0)` once made the GE-direction FS-Relationships check FAIL with zero offenders on a
schedule with no links). DCMA09 likewise reads NA without a status date instead of a fabricated
PASS. Every citation fallback (`recommendations._finish_driver_citations`, briefing
`_finish_drivers`, narrative `_clean_bill`) now terminates at the **first task rows** when the CPM
timing set is empty (summary-only templates) — the §6 never-uncited invariant holds even for files
with no schedulable activities. BEI's numerator counts **all** activities finished by the status
date (the DCMA definition; early completions count, BEI may exceed 1.0).

## Decision 2 — XER gets the same real-world tolerance classes as MSPDI

The shared classes now live in `importers/_common.py` (`DATE_REQUIRING_CONSTRAINTS`,
`clamped_percent_or_none`) so the two importers cannot drift: ALAP and dateless date-constraints
normalize to ASAP; dangling/cross-project/self/duplicate `TASKPRED` rows are dropped and counted
(never sink the file); physical % clamps 0..100. **P6 percent-complete honors
`complete_pct_type`**: actual dates rule first (finished → 100, unstarted → 0), `CP_Phys` reads the
physical %, `CP_Drtn`/`CP_Units` derive (target − remaining) ÷ target — `phys_complete_pct` alone
imported in-progress/finished duration-type work as "not started", corrupting EVM/BEI/status logic.
(`CP_Units` via TASKRSRC quantities is a documented approximation, deferred.) UTF-16 XER decodes
via BOM sniff; the web upload path decodes byte-identically to the file path (`decode_xer_bytes`,
`utf-8-sig` for MSPDI).

## Decision 3 — MSPDI percent lags are a share of the predecessor's duration

`LinkLag` under `LagFormat` 19/20 stores **tenths of a percent of the predecessor's duration**
(`FS+25%` → `LinkLag=250`), not tenths of a minute. Links now resolve in a second pass after all
tasks parse (predecessors can appear later in the file). Non-finite numerics (`"NaN"`,
`"Infinity"` — valid `Decimal` constructions) read as data noise (absent), never crashes or
poisoned EVM sums.

## Decision 4 — manipulation watch covers erased actuals

`date → None` on a previously-reported actual start/finish (progress un-statused — the classic
history rewrite) raises its own HIGH finding (`MANIP_ACTUAL_ERASED`) alongside the edited-actual
signal. Four Schedule-Quality metrics (Critical, Hard Constraints, Negative Float, Number of
Leads) now attach the offender lists they always computed, so briefing trend statements cite the
actual offending activities.

## Decision 5 — CUI hardening

`StrictFrozenModel` sets `hide_input_in_errors=True` (pydantic errors no longer embed task
names/dates/costs that importers wrap into user-facing messages). Log redaction covers `.json`
schedule names, UNC paths (`\\server\share\…`), quoted-and-whole-string filenames with spaces,
and non-string `extra` payloads (containers recurse; objects stringify-then-redact). The bias is
over-redaction. `Save .json` round-trips faithfully (milestones, summaries, WBS, remaining/baseline
durations, costs, exact calendar minutes + weekdays) — the tool's own format must not silently
alter a schedule.

## Decision 6 — operator features

- **Session-wide target UID** (`SessionState.target_uid`, `POST /target`, header form): the report
  page renders a target panel + auto-traces, Trend focuses by default (an explicit `?target=`,
  even blank, overrides), Compare adds the focus movement panel. Local-only redirects; summary
  targets degrade with a named note (they are not in the logic network).
- **Light/dark theme**: CSS custom properties + `html[data-theme=light]` overrides; `theme.js`
  applies the `localStorage` preference pre-paint; SVG charts route `var(...)` fills/strokes via
  `style` (presentation attributes cannot carry CSS variables) so charts re-theme live.
- **Batch cap 10 → 20** (`MAX_FILES`; §6.B required 10 — raised at operator request); the upload
  route names dropped overflow instead of silently truncating.

## Consequences

562 tests (36 new), parity 10/10 untouched (every behavior change is on constructs the curated
goldens lack — verified by the unchanged golden parity suite). Known deferred items are listed in
HANDOFF "Next steps": the 480-minute day hardcoded in day-based thresholds/conversions (bites only
non-8h JSON calendars), CP_Units quantities, AI number-preservation re-verification, and the
settings-selected backend not driving cached narratives.
