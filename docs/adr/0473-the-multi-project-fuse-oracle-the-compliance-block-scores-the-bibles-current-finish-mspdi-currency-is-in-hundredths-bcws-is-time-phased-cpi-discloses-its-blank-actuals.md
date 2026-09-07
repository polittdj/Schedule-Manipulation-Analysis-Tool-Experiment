# ADR-0473 — The multi-project Fuse oracle: the §C compliance block scores the Bible's CURRENT Finish/Start, MSPDI currency is in hundredths, BCWS is time-phased, CPI discloses its blank actuals, and a Fuse figure is an oracle only for the tile its own workbook section carries

- **Status:** Accepted — 2026-09-07 (the plan-forward's R-01 first, then every metric family against every reference workbook in the repo; the operator's standing directive of this session: "use all of the reference files in the repo to validate all metrics")
- **Version:** 1.0.243
- **Extends:** ADR-0472 (the roadmap this session works), ADR-0151 (the P2/P5 Fuse suite), ADR-0159/0176 (the Hard_File oracles), ADR-0083 (the §C block), ADR-0084 (Insufficient Detail™), ADR-0430 (Negative Float on the stored slack), ADR-0463 (the JCL `actuals_assumed_count` shape R-01 borrows), ADR-0110 (DCMA08's documented baseline-duration drift)
- **Shipped:** `engine/metrics/evm.py` (the compliance block on the Bible's `Finish`/`Start`; `_planned_value` linear over the baseline span; CPI/TCPI carry `actuals_missing` as count / population / offenders), `engine/metrics/schedule_quality.py` (the ribbon Negative Float classifies the stored slack in whole days), `importers/mspdi.py` (`_currency`: MSPDI cost elements ÷ 100), `web/evm.py` (the disclosure sentence beside the cost indices), `web/help.py` + `docs/METRIC-DICTIONARY.md` (the definitions say the basis), `docs/PARITY-REPORT.md` (§B row 8 re-attributed; a new oracle section), `tests/parity/test_fuse_metric_history_oracle.py` (NEW, 15 — the vendor `.xlsx` read with the std-lib), `tests/fixtures/golden/fuse_ltf/` (NEW — fresh MPXJ conversions of the two Fuse-scored Large Test Files), `tests/engine/metrics/test_evm.py` (+2), `tests/importers/test_mspdi.py` (the cost literals say hundredths)

## Context

The kickoff asked for R-01 first and then for every metric the tool generates to be validated against
every reference file in the repo. The inventory found three operator-delivered Fuse v8.11.0 workbooks
that no test had ever read — `AlltheProjects - Metric History Report.xlsx` (twelve projects on one
report, the cost-loaded EVM1/EVM2 among them), the Large Test File / File2 Metric History (a
1,723-activity real schedule, two snapshots side by side), and the Hard_File update-vs-update Metric
History and ribbon exports with BCWS / BCWP / ACWP / BAC / SPI / CPI / TCPI — plus the Detailed
Metric Reports whose per-activity `X` marks give Fuse's exact offender sets. A harness read each
sheet with the std-lib, computed the engine on the matching MSPDI (the intake `.mpp` converted with
the vendored MPXJ), and diffed label by label; every mismatch was then root-caused on the Bible's own
formula and inclusion flags and on the X-marks, before a line changed.

| Finding | Measured (Fuse · engine before) | Root cause |
| --- | --- | --- |
| §C baseline compliance — Completed/Started On Time / Late, BFC, BSC | EVM1 5 / 5 / 100 % · 0 / 2 / 0 %; Large Test File2 159 / 250 · 117 / 200; Hard_File_updated2 13 / 13 · 7 / 9; TP4 v1/v3/v4/v5 likewise | the Bible's formulas read `Finish` / `Start` — the CURRENT date (actual once finished, else the forecast) — and the engine read `actual_finish` / `actual_start`; the two agree only on files with no stale forecast dates (P2/P5, Large Test File, Hard_File base), which is why the P2/P5 gate never saw it |
| MSPDI currency | Hard_File_updated ribbon BAC 133,400 · ACWP 20,800 · engine 13,340,000 · 2,080,000 | MS Project's XML stores every cost element in HUNDREDTHS (`CurrencyDigits 2`; MPXJ's writer multiplies by 100 for the same reason); the importer read the integers verbatim. Ratios cancelled the scale — the task-info drawer's amounts and the JCL's dollar figures did not |
| BCWS (cost SPI) | Hard_File_updated 16,000 · 12,400 (SPI 1.05 · 1.35); updated3 110,440 · 107,240 | the engine's planned value was a step at the baseline finish; Fuse sums MS Project's time-phased BCWS. Linear accrual over the baseline span reproduces 64,240 and 110,440 exactly; 16,150 on `updated` (one activity straddling the status date on a 16-hour resource calendar) |
| ribbon Negative Float | Large Test File2 122 · 123 | one activity's stored slack is −139 minutes (−0.29 d); Fuse classifies float in whole days and marks it "Zero Days Float"; the engine compared raw minutes |
| R-01 — CPI on blank actuals | CPI 0.81 / 0.78 on Hard_File_updated / updated2 — exact under blank-as-zero | the Bible's `sum(BCWPEV)/sum(ACWPAC)` with Acumen's blank-as-0 evaluation (proven on SPI(t), ADR-0176) IS the reference rule; the Hard_File series carries no started, budgeted activity without an actual, so the mixed case has no Fuse figure — what the sum cannot know is now DISCLOSED |

Three "mismatches" the harness raised were not engine defects, and the reason is the lesson of the
session: **the reference library carries the same display name with different inclusion sets per
workbook section.** `Insufficient Detail™` is one metric on the Quick Add ribbon (every status —
2 / 2 / 2 on the Hard_File ribbons, 43 on the Large Test File) and another in the NASA Quick
Library Metric History (`IncludeComplete=false`, `IncludeMilestone=false` — 22); `Merge Hotspot`
(the tile, every status — 156) versus `Merge Hotspot (Predecessors >2)` (planned only — 125); the
DCMA tile `3. Lags` (planned + in-progress — 5) versus `Total # Predecessor Lags` (planned only —
2, and the operator's TP3 ribbon counted a started successor's lag). Each was changed to the History
variant, went red on a ribbon oracle (Hard_File_updated 2 → 1; the Project5 golden's Number of Lags
2 → 1; TP3's Lags 3 → 2), and was reverted the same hour. The engine implements the ribbon tiles
and stays exact on them.

## Decisions

1. **The compliance block scores the Bible's current dates.** `current_finish` = the actual finish
   once finished, else the scheduled finish; `current_start` likewise; "Not Started" and "Not
   Completed" stay the recorded facts. Exact on twelve oracles (EVM1, EVM2, TP4 v1/v3/v4/v5,
   Project2, Project5_TAMPERED, Large Test File / File2, Hard_File_updated2/3), the ten counts and
   both ratios each. CEI (Finish / Start) follow, being the same counts.
2. **MSPDI currency ÷ 100 at the importer.** `Cost`, `ActualCost` and `Baseline/Cost`; a P6 XER
   carries real currency and is untouched; the tool's own Save format is written from the model, so
   a Save made from an MSPDI source BEFORE this version holds hundredths — re-import the source.
3. **BCWS accrues linearly over the baseline span** on the project calendar, up to the status
   date. The 150-unit residual on Hard_File_updated is documented, not hidden (R-46).
4. **CPI / TCPI keep the Bible's blank-as-zero ACWP and disclose it**: `actuals_missing` — started,
   budgeted activities with no actual cost — rides the two results as `count` / `population` /
   `offender_uids`, the EVM page prints the sentence with the UIDs, and the definition says so.
   NA would blank a figure the reference tool prints; a silent 0 would flatter it. R-01 CLOSED.
5. **The ribbon Negative Float classifies the stored slack in whole days** (`round`, banker's at
   the exact tie — R-03's open question is not flipped here).
6. **A Fuse figure is an oracle only for the tile its own workbook section carries.** Lags, Merge
   Hotspot, Insufficient Detail and Number of Lags stay the ribbon tiles they were; the History
   variants are registered as their own future metrics (R-50), never as corrections.
7. **The DCMA08 record is corrected, the basis kept.** The engine implements Fuse's "High Baseline
   Duration (44d)" (87 / 86 UID-exact on the Large Test File / File2 X-marks); the parity report's
   row 8 said "High Planned Duration (44d)", which reads 124 there. ADR-0110's drift row already
   named the basis; the wording now matches it.

## Verification (QC-1)

- **Red first:** `tests/parity/test_fuse_metric_history_oracle.py` + the two new `test_evm.py`
  pins against a `git archive HEAD src` scratch copy on `PYTHONPATH`: **12 failed / 5 passed**
  by name (the five passes are the oracles where the two date bases coincide); on this tree
  **34 passed** across the module and `test_evm.py`.
- **The harness:** 16 snapshots × 3 workbooks, every label with an engine counterpart compared; the
  compliance rows 692–701 read directly from the sheets after the fix — exact on every oracle
  including "Started Late" (515 / 605 / 0 / 5 / 6 / 27 / 23).
- **Reverts that proved the tiles:** the three History-variant changes each went red on a ribbon
  oracle or a golden pin before being reverted (Context, above).
- **The suites that hold:** `pytest -m parity` 72 passed before the change (10:49); the engine /
  importer / battery / report-guard set 404 passed after; the full suite result is in the session
  log. Statics: ruff (whole tree) · format · mypy --strict 163 files · bandit exit 0.
- **Census re-measured, not edited:** `round_calls_inside_engine_metrics` 45 → 46 (the whole-day
  classification is one `round(`); `evm_acwp_or_zero_sites` stays 1 — deliberately, the rule is the
  Bible's; the report's method line says so.

## Deliberately NOT done (measured, left alone, each a roadmap row)

- Hard_File's CPM finish runs **42 days** later than MS Project's stored finish (2026-12-17 vs
  2026-11-05; Fuse's Project Finish is the stored one): its resources sit on 16-hour and 24-hour
  calendars the base CPM does not model. L; R-44.
- Hard_File_updated3's BAC / BCWP (Fuse 121,800 / 53,715 vs 133,400 / 59,340) and Fuse's
  ACWP-to-time-now (64,105 vs the file's 63,763 on updated2) — no per-task cost oracle in the
  export. R-45.
- SPI(t)–Acumen 8.24 vs 8.22 on the Large Test File. R-47. The DCMA tile "8. High Duration" carries
  `IncludeComplete=true` in the library. R-48. MPXJ omits a ZERO `TotalSlack` (62 of Fuse's 66
  zero-float activities on Large Test File2 carry none) — an importer inference with the SSI gates
  as the arbiter. R-49. "Estimated Duration" 63 vs 47 / 41. R-51.
- The exported `.pptx` (one-pager and compare) does not load in LibreOffice 7 headless; PowerPoint
  UNVERIFIED. R-52. TP3's 2026-06-12 ribbon (Lags 3, Insufficient Detail 8) was captured on a
  `.mpp` whose progress differs from the committed XML. R-53.
- The `golden/ssi_uid152` Large Test File fixture is the underscore-named sibling `.mpp`
  (31 negative-float activities), not the Fuse-scored file (41); it stays the SSI fixture. R-54.

## The operator's five questions — decided here (the kickoff's "answer these yourself")

- **(a) TX-03 — keep the pre-consent catalog probe.** It carries no schedule content, it fires only
  on the operator's own endpoint choice from the approved list, and it is recorded. Gating it
  would leave the model dropdown empty until consent and change nothing Law 1 protects. R-12 CLOSED.
- **(b) IMP-05 — keep the planned-date basis with its disclosure.** A P6 file with no baseline
  project shows those dates as its BL dates; blanking HMI/BEI on every XER would remove a figure
  the source tool itself shows. The disclosure stays; a Fuse export on an XER reopens it. R-02 HELD.
- **(c) the rulings stand** — a swimlane move is one removed plus one new (never inferred), no
  slip threshold (a calendar day is a change), one slide. The `.pptx` question got an executable
  answer the operator could not have expected: LibreOffice refuses both decks. R-31 CLOSED as
  rulings; R-52 OPEN for the package.
- **(d) UID 152** — on the repo's Large Test File pair the counterfactual moves neither the target
  (2029-04-19) nor the finish (2029-04-20): 0 working days, 0 calendar days, on the file's
  five-day 480-minute calendar; the arithmetic is the CPM's own minutes over that calendar. The
  operator's #635 pair (2027 dates) is not in the repo. R-30 HELD on their reading.
- **(e)** the forecast / trend chips and the parent-folder ask are pinned by 24 passing layout,
  browser and folder-ask tests on two-file corpora; T-01, I-01 and the /analysis lag are the
  operator's box. R-23 / R-24 / R-29 HELD.
