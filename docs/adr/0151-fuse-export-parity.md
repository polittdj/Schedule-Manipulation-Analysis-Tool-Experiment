# ADR-0151 — True Fuse parity from the delivered export suite (§E → ENGINE==FUSE; D14/D20 closed)

## Status

Accepted.

## Context

The audit's honest in-environment ceiling had been **ENGINE==GOLDEN**: the engine reproduces a
*transcribed* golden, and the §E float/critical change subset was worse — **engine-pinned**
self-consistency awaiting a fresh Acumen §E export (audit F-01; PARK-LIST A-1/A-2). The operator
then delivered the complete **Acumen Fuse v8.11.0 export suite for the exact golden pair**
(Project2, Time Now 5/24/2026 ↔ Project5_TAMPERED, Time Now 8/27/2026), repo-tracked under
`00_REFERENCE_INTAKE/`: `P2-P5 - Metric History Report.xlsx`, `P2-P5 - DCMA Report.xlsx`,
`P2-P5 - Detailed Metric Report.xlsx`, `P2-P5 - Quick Add Metrics.xlsx` (all created 6/21/2026),
and two independently-created Forensic Analysis Report comparisons (6/22 and 7/7/2026).

## Decision

1. **Transcriptions live in an ADDED reference file** —
   `tests/fixtures/golden/project2_5/fuse_exports_2026-06.json` — with per-value provenance.
   No committed golden number was edited (PARK-LIST rule). Every transcribed value appears in at
   least TWO independent places in the suite; the two Forensic reports' per-activity sheets were
   diffed programmatically and are row-identical.
2. **A new parity-marked gate** — `tests/parity/test_fuse_export_parity.py` — asserts
   ENGINE==FUSE for every §A/§B/§C row the suite carries and the whole §E block, **UID-exact
   wherever Fuse publishes or lets us derive a per-activity list**:
   * §E New Critical = 1, **UID 131 exact** (Metric History SN05 + the DCMA offender row + the
     Forensic Critical sheet).
   * §E Float Erosion = 1, **UID 131 exact** — derived from the Forensic Total-Float sheet
     (stored-TF decreases, non-summary + incomplete scope): Fuse's own data erodes exactly the
     activity the engine's pure-CPM basis erodes.
   * §E Finish Date Slips = 9, **UID-exact** vs Fuse "CEI - Incomplete Tasks".
   * §E Remaining Duration Increases = 9, **UID-exact** vs the Forensic Original-Duration sheet.
   * §E No Longer Critical = **34 == 34**, membership 33/34.
3. **Divergences are asserted exactly, never forced** (the operator's standing rule):
   * **The 96↔99 membership swap.** In Project2 MS Project's stored progress-aware Critical flag
     marks UID 96 (pure-CPM float 5d) while pure-logic CPM marks UID 99 (stored slack 10d); both
     bases count 41. The gate asserts `engine−fuse == {99}` and `fuse−engine == {96}`.
   * **Net Finish Impact basis.** Fuse HSD10 = **−134** over STORED project finishes (verbatim
     `.aft` formula `ROUND(ProjectPreviousFinish − ProjectFinish, 0)`; serials 46644.708 →
     46778.708). The engine reports **−148** over its own CPM finishes (ADR-0010 independence).
     The gate asserts both numbers, that the goldens' stored finishes equal Fuse's serials, and
     the day-exact bridge (−148 = −134 − 15 + 1 — the ADR-0108 data-date gap: P2's CPM finish
     lands 15 days before its stored finish, P5's 1 day before).
   * **Start Date Slips** stays count-level (9, consistent with Fuse CEI Starts 0.40 = 6 of 15
     due started): the suite publishes no per-activity start list.
4. **QC leftovers:**
   * **D14 CLOSED.** The `.aft` Bible (1,443 metrics) contains **no** "Remaining Duration
     Increases" (nor any date-slip / float-erosion) metric — the §E SN names are this tool's
     forensic labels, and Fuse's own export codes differ (Fuse SN05 = Newly Critical, SN06 = No
     Longer Critical). There is no verbatim Bible formula to adopt. The engine's total-duration
     comparison is Fuse-validated UID-exact (9/9) against the Forensic Original-Duration sheet;
     the remaining-duration basis (the 7-UID subset) is recorded alongside in the reference file
     and help.py. Formula unchanged.
   * **D20 CLOSED.** Raw-CPM float bands reproduce the delivered "Zero Days Float" counts
     exactly (P2 41 / P5 4); the raw-CPM-by-design disposition (ADR-0141) is confirmed.
   * **D7 remains artifact-gated** — the delivered pair contains no elapsed in-progress
     activity, so the elapsed Float-Ratio value cannot be exercised from this suite.
5. **Marker flip (F-01).** `PARITY-REPORT.md` §E now shows ENGINE==FUSE provenance per row;
   `case.json._deltas.change_P2_to_P5_engine_pinned` records the superseding;
   `test_parity_report_sync.py::test_fuse_validation_marker_cannot_be_silently_deleted_f01`
   enforces the *new* markers (ENGINE==FUSE + both divergences) as strictly as it enforced the
   old disclaimer. Three stale P5 cells in the report's §A/§B tables (Hard Constraints 0/0,
   Logic 4/4) were corrected to the case.json/Fuse values (0/1, 4/5).

## Also in this change

The Executive Briefing tables rendered one-character-per-line (operator screenshot): ADR-0150's
containment override (`word-break: break-word` on `.brief-card table`) combined with the
`white-space: nowrap` citation column let auto-layout crush every other column to its
one-character min-content width. Fixed: citations wrap in a bounded block (`min/max-width`, no
nowrap), headers stay `nowrap`, cells wrap at word boundaries only, and a genuinely-wide table
scrolls inside its card. Verified in a scripted Chromium session; pinned by
`test_briefing_tables_are_never_column_crushed`.

## Consequences

* `pytest -m parity` now includes a true cross-tool gate: for the rows the delivered suite
  carries, *engine == Fuse* is re-checkable from the repo alone (the exports are repo-tracked).
* Remaining transcription-basis-only rows: DCMA-04/10/12/13 and the composite scores (not in
  this suite). Remaining §E caveat: the two asserted divergences above, both definitional.
* Version bumped to **1.0.4**; the wheel + 9 installers were regenerated (app.py/app.css/
  help.py/float_bands.py/change_metrics.py are packaged sources; the ADR-0148 lockstep gate
  enforces this).
