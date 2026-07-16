# Hardened Audit and Reproducible Acumen/SSI Oracle Test Protocol

**Process version:** `hardened-audit-v9-repository-gate-and-oracle-runner-hardening`  
**Generated:** 2026-07-15T19:49:32.053605+00:00  
**Repository current head reviewed:** `dcacbf4458f2049aeec01be345b32d1685dae27c`  
**Last documented fully green code head:** `2dc369678dfc294db189d1bc706eba4ab02b752a`

## Executive conclusion

The hardened process passed **22 of 22 independent integrity checks**. The project-library audit covers **436 extracted paths**, **175 unique SHA-256 payloads**, **40 native MPP files**, **8 schedule MSPDI XML files**, **83 XLSX workbooks**, **6 Acumen AFW workspaces**, and all remaining reference formats. Every canonical and alias hash, archive CRC, workbook structural count, schedule stable semantic fingerprint, direct oracle association, and test-contract hash was reverified.

The process is internally hardened, but the corpus is **not fully readiness-green**. Four SSI exports lack exact dated source snapshots; one AFW cannot identify a unique binary Project5_TAMPERED source; the current repository head was not locally executed in this runtime; and the repository `Hard_File_updated4 24 hour calendar.mpp` has not been semantically compared with the archived `updated3` payload. These failures are explicit blockers, not hidden exceptions.

## What was weak and what changed

The most important new findings were not merely file issues; they exposed weaknesses in the audit method itself:

### 1. Filename/folder inference can create false associations.

**Control:** Associations require embedded project/version labels, exact UID/name/date reproduction, or explicit AFW serialized file references. Folder/name similarity alone is prohibited.  
**Verified by:** No association has source_resolution=heuristic_only; all 81 vendor-oracle containers are evidence-linked.

### 2. A same filename can represent several distinct binary schedules.

**Control:** Use SHA-256 as binary identity and record schedule-equivalence classes separately from binary identity.  
**Verified by:** 11 source-equivalence classes are explicit; AFW exact-binary gate correctly fails 5/6.

### 3. A re-saved MPP can change bytes without changing schedule semantics, or change semantics silently.

**Control:** Compare semantic task, logic, calendar, resource, assignment, property, and combined fingerprints; never treat a Git rename as semantic equivalence.  
**Verified by:** updated4 24-hour file remains UNVERIFIED because current binary was unavailable; no equivalence claim is made.

### 4. Spreadsheet filenames and visible report titles can be stale or misleading.

**Control:** Read every populated cell, formulas, workbook relationships, core properties, project strings, date strings, sheet structures, and vendor-specific rows.  
**Verified by:** 83/83 XLSX scanned; 3,909,788 cells and formula digests recorded.

### 5. A worksheet can contain multiple project versions.

**Control:** Model one oracle container to many schedule associations and retain version-specific labels/status dates.  
**Verified by:** Acumen multi-project reports create multiple evidence edges rather than one guessed source.

### 6. SSI rows can match UIDs/names but not scheduled dates.

**Control:** Require independent Start and Finish date reproduction for exact source status; classify lower matches as probable or structural-only.  
**Verified by:** 15/19 SSI workbooks pass >=99.5% exact date match; four are explicitly blocked from exact parity.

### 7. MPP-to-MSPDI XML exports are lossy.

**Control:** Use XML only for logic/task portability tests; retain MPP for calendars, resources, assignments, stored critical/slack, and project properties.  
**Verified by:** 13/13 same-stem pairs have exact logic fingerprints, while field-loss differences remain documented.

### 8. Acumen display name alone is not a metric identity.

**Control:** Key metrics by library/group/GUID/version and preserve Primary, Secondary, Tripwire, filters, thresholds, columns, and detailed-report options independently.  
**Verified by:** AFT architecture and Missing Logic variants are represented in the formula audit and protocol.

### 9. Headline equality can hide offender-list or denominator mismatches.

**Control:** Oracle contract compares value, count, population, status, offender UID set, row order where relevant, and threshold band separately.  
**Verified by:** Test-case schema requires granular expected artifacts, not only headline values.

### 10. Floating-point and date-format differences can create unstable comparisons.

**Control:** Canonicalize datetimes, use integer working minutes where possible, Decimal/ROUND_HALF_UP at presentation, and explicit field-specific tolerances.  
**Verified by:** Comparison contract in V9 records exact/tolerant fields and N/A semantics.

### 11. A single parser implementation can validate its own error.

**Control:** Independent verification uses raw ZIP/XML counts, SHA-256/CRC, MPXJ semantic fingerprints, and cross-tool oracle evidence.  
**Verified by:** HARDENED_VERIFICATION_RESULT_V9.json records independent controls.

### 12. Cached analysis can conceal source changes.

**Control:** Cache keys include file SHA-256 and engine version; hardened audit independently recomputes source hashes before accepting cached metadata.  
**Verified by:** All canonical and alias hashes are rechecked by verify_hardened_v9.py.

### 13. Repository documentation may describe a prior code head while reference uploads advance main.

**Control:** Track code-audited head separately from current repository head; rerun the full gate after every reference-only upload.  
**Verified by:** Current reference-upload head has no connector-visible workflow run and is marked unexecuted.

### 14. The repository cannot be exhaustively executed from an environment without a checkout/network.

**Control:** Ship a repo-local audit script and matrix runner that Claude Code executes inside the repository; external review is not represented as a local full-gate run.  
**Verified by:** Repository execution gate remains failed until the generated script is run in the repo.

### 15. Vendor stochastic outputs may not be bit-exact because RNG/seed/correlation implementation is proprietary.

**Control:** Separate deterministic formula/OAT checks from distributional SRA checks; require fixed seed/config and statistical acceptance bands for Monte Carlo.  
**Verified by:** Protocol distinguishes exact deterministic parity from statistical distribution parity.

### 16. The original combined semantic fingerprint included MPXJ ProjectProperties.CurrentDate, a read-time value that changed on every parse and made all 48 schedules look non-repeatable.

**Control:** Exclude CurrentDate from the normative stable_combined_v2 fingerprint. Keep the old combined digest only as a diagnostic; gate on counts, stable properties, and identity/logic/schedule/calendar/resource/stable-combined fingerprints.  
**Verified by:** All 48 schedule inputs were reparsed independently. Counts and five component fingerprints matched 48/48; the only original combined difference was CurrentDate. stable_combined_v2 matched 48/48.

### 17. The original formula_count counted only non-empty formula definitions, while shared-formula follower cells contain empty <f/> elements. Two workbooks therefore appeared to have inconsistent formula counts under a raw OOXML recount.

**Control:** Track formula_definition_count and formula_cell_count separately. Validate both: definitions preserve unique formula text, while formula-bearing cells measure calculation coverage.  
**Verified by:** All 83 XLSX files independently reproduce cell count, sheet count, formula definition count, and formula-bearing cell count. Margin template has 202 definitions/350 formula cells; PerformanceAnalysisSummary has 214 definitions/7,244 formula cells.

### 18. File-level vendor classification and refined workbook-level classification diverged for PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx.

**Control:** Use one authoritative classification table and propagate it to file, workbook, test-case, and association layers; direct vendor oracles are separated from templates/reference workbooks.  
**Verified by:** PerformanceAnalysisSummary is now Reference/Methodology / Performance Analysis Template and is excluded from the Acumen-oracle readiness denominator.

### 19. The first repo-local audit script did not exactly reproduce the complete documented CI gate and did not distinguish tracked, untracked, dirty, or missing worktree files.

**Control:** Record Git head/branch/status/tracked files, fail dirty or incomplete worktrees, structurally parse all files, and run the documented coverage, parity, security, dependency-audit, JavaScript syntax, and native-MPP test commands.  
**Verified by:** verify_hardened_v9.py statically confirms the full gate and Git-state controls are present in repo_hardened_audit.py; execution remains a readiness blocker until run in a current checkout.

### 20. The first oracle runner could compare headline JSON without source-hash provenance and compared SSI dates only as raw strings, allowing the wrong source snapshot or equivalent date encoding to pass incorrectly.

**Control:** Require an allowed source SHA-256 for exact SSI cases, normalize Excel serial and ISO datetimes to one numeric axis, normalize day quantities, detect duplicate UIDs, optionally enforce row order/Drag, and support strict metric provenance.  
**Verified by:** verify_hardened_v9.py executes exact metric and SSI self-tests through oracle_matrix_runner.py and requires zero differences.

### 21. Versioned control text could remain stale after a later hardening pass, as shown by V6 artifact names inside the V8 process-control table.

**Control:** Treat process-control artifact references as versioned data and fail verification when obsolete V6/V7/V8 process-artifact names remain in the V9 control set.  
**Verified by:** The V9 verifier scans process_weaknesses_and_controls for obsolete versioned verifier/result references.

## Independent verification results

| Check | Expected | Actual | Result |
|---|---:|---:|---|
| Canonical files exist | 175 | 175 | PASS |
| Canonical SHA-256 reproducible | 175 | 175 | PASS |
| Canonical byte sizes reproducible | 175 | 175 | PASS |
| Alias paths reproduce canonical SHA-256 | 436 | 436 | PASS |
| Source ZIP CRC/traversal clean | 0 | 0 | PASS |
| XLSX raw cell/formula/sheet counts independently reproduce | 83 | 83 | PASS |
| All 48 schedule stable semantic fingerprints independently reproduce | 48 | 48 | PASS |
| Volatile CurrentDate difference identified and excluded from normative gate | 48 | 48 | PASS |
| Non-schedule XML configurations well-formed | 2 | 2 | PASS |
| AFW explicit references independently reproduce | 6 | 6 | PASS |
| Association IDs valid | 169 | 169 | PASS |
| All vendor oracle containers associated | 81 | 81 | PASS |
| No heuristic-only associations | 0 | 0 | PASS |
| Exactly one test contract per vendor oracle | 81 | 81 | PASS |
| Test contracts pin oracle SHA-256 | 89 | 89 | PASS |
| MPP/XML pairs retain exact logic fingerprints | 13 | 13 | PASS |
| SSI exact-source readiness independently equals 15/19 | 15 | 15 | PASS |
| AFW exact-binary readiness independently equals 5/6 | 5 | 5 | PASS |
| Readiness gate arithmetic coherent | 6 | 6 | PASS |
| Process-control artifact references are current V9 | 0 | 0 | PASS |
| Repo-local audit script contains full Git/coverage/parity/security/JS/MPP controls | 9 | 9 | PASS |
| Oracle runner validates schema and passes exact metric/SSI self-tests | 3 | 3 | PASS |

## Readiness gates

| Gate | Expected | Actual | Result | Reason |
|---|---:|---:|---|---|
| Every SSI oracle has a >=99.5% exact start/finish source match | 19 | 15 | FAIL |  |
| Every Acumen XLSX has exact embedded project/version labels | 56 | 56 | PASS |  |
| Repository current head locally checked out and full test gate rerun | 1 | 0 | FAIL | Runtime DNS blocked git clone; GitHub connector evidence reviewed but current reference-upload head was not executed locally. |
| Every AFW explicit source filename resolves to at least one schedule equivalence class | 6 | 6 | PASS | All six AFW workspaces expose explicit .mpp references that resolve to one or more exact-name candidates. |
| Every AFW explicit source filename resolves to exactly one binary payload | 6 | 5 | FAIL | ref2/2345.afw references Project5_TAMPERED.mpp, but three distinct archive payloads share that filename and reproduce the same observable schedule rows. The AFW stores no source content hash. |
| Current repository updated4 24-hour file semantically compared to archived updated3 24-hour file | 1 | 0 | FAIL | Git blobs differ and current repository binary was not downloadable through the available connector. |

## Full project-library corpus results

- **Paths:** 436; **unique payloads:** 175; **exact aliases:** 261.
- **Schedule inputs:** 40 MPP + 8 MSPDI schedule XML. Two additional XML files are field-map/configuration XML, not failed schedules.
- **Excel:** 83 workbooks, 3,909,788 cells. Formula definitions and formula-bearing cells are separately counted so shared formulas are not misreported.
- **Vendor outputs:** 56 Acumen XLSX, 19 SSI XLSX, 6 AFW workspaces. One PerformanceAnalysisSummary workbook is correctly classified as a reference/template, not a direct Acumen oracle.
- **Other evidence:** 11 PDFs, 11 DOCX, 7 unique ZIP containers, 3 JPG, 2 PNG, 1 PPT, and 1 JSON payload.
- **XER:** zero in the uploaded project library. Production P6 parity remains unsupported by this corpus.

### Schedule fingerprint correction

The first semantic rerun appeared to fail all 48 schedules because the combined digest included MPXJ `ProjectProperties.CurrentDate`. That value is generated at read time and changed on every parse. Task, logic, schedule, calendar, and resource fingerprints were exact. The normative `stable_combined_v2` fingerprint now excludes `CurrentDate`; all 48 schedules then reproduced exactly. The old combined digest is retained only as diagnostic evidence.

### Workbook formula-count correction

Two workbooks use shared formulas. A raw OOXML count sees every formula-bearing cell, while the original parser counted only non-empty formula definitions. The hardened model now records both values. `Margin&Contingency_BurnDown_Template_20250513.xlsx` has 202 definitions and 350 formula cells; `PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` has 214 definitions and 7,244 formula cells. All 83 workbooks now match both independent counts.

## Oracle-to-source association rules

Every direct Acumen/SSI/AFW oracle has at least one evidence-based schedule association. The process explicitly rejects filename or folder similarity as sufficient evidence.

Accepted evidence is: embedded Acumen project/version labels; status-date agreement; SSI Unique ID + normalized task name + Start/Finish reproduction; explicit AFW `.mpp` references; or a recorded exact semantic-equivalence class. When the oracle lacks a source hash, all exact candidates remain visible rather than selecting one arbitrarily.

### SSI readiness

**15 of 19** SSI exports have at least 99.5% exact Start/Finish reproduction against a retained source schedule. The four non-exact cases are:

- `ref2/UID_152_Directional_Path_Analysis_All Dependents Not Leveled_2026-6-23-20-30-55.xlsx` -> `ref1/Large Test File Leveled with Driving Slack.mpp`: UID 783/783, name 783/783, dates 757/783 (96.68%); classification **probable**.
- `ref2/UID_152_Directional_Path_Analysis_Leveled_All_Dependents_2026-6-23-20-28-26.xlsx` -> `ref1/.mpp test files/Large Test File/Large Test File Leveled.mpp`: UID 783/783, name 783/783, dates 753/783 (96.17%); classification **probable**.
- `ref2/UID_4_Directional_Path_Analysis_2026-6-23-15-42-46.xlsx` -> `ref1/5 Task Test File.mpp`: UID 4/4, name 4/4, dates 1/4 (25.00%); classification **structural-only**.
- `ref2/UID_4_Directional_Path_Analysis_Progress_2026-6-23-16-0-6.xlsx` -> `ref1/5 Task Test File.mpp`: UID 4/4, name 4/4, dates 1/4 (25.00%); classification **structural-only**.

These four may be used for structural/diagnostic testing, but not as exact SSI parity gates until the precise source snapshots are restored or the reports are regenerated.

### AFW ambiguity

`ref2/2345.afw` explicitly names `Project5_TAMPERED.mpp`, but three distinct binary payloads share that name and reproduce the same observable rows. The workspace identifies a schedule equivalence class, not one binary source. Five of six AFW workspaces resolve to a unique binary; the sixth remains blocked.

### Naming/provenance conflict

`Large Test File (OverAl Fixed) UID_152...xlsx` matches `Large Test File Leveled with Driving Slack Not Leveled.mpp` exactly by all 783 UID/name/date rows, not the MPP whose filename says `OVERALLOCATION FIXED`. This proves filenames must not be treated as ground truth. The source must be confirmed or the SSI report regenerated with a source manifest.

## Repository audit and cross-reference

The current GitHub reference-upload head was reviewed through the GitHub connector and the repository-owned `docs/STATE/REPO-INVENTORY.md`, with direct spot checks of `pyproject.toml`, `.github/workflows/ci.yml`, `docs/STATE/HANDOFF.md`, `tests/parity/test_parity_gate.py`, `tests/engine/test_aft_formula_audit.py`, `tests/fixtures/golden/project2_5/case.json`, `tests/parity/test_fuse_hardfile_parity.py`, and `tests/engine/test_evm_acumen_reference.py`.

The repository declares Python 3.11+, strict mypy, ruff, bandit, coverage thresholds, and a dedicated `pytest -m parity` gate. The parity gate covers Acumen schedule quality, DCMA-14, baseline compliance, cross-version changes, Net Finish Impact, and several SSI focus-UID scenarios. The repository formula audit is explicitly definitional rather than an execution-parity test.

The current reference-upload head has no workflow run visible through the connector. The last documented fully green code head reports 2,208 tests and all quality gates green. A local checkout could not be obtained because the runtime DNS could not resolve GitHub. Therefore, this report does **not** claim that every current repository byte was locally executed. `repo_hardened_audit.py` is supplied to close that gate inside Claude Code or another current checkout.

## Acumen metric reproducibility contract

An Acumen metric is not one formula string. The canonical identity must include metric group, GUID, version, display name, Primary Formula, Secondary Formula, Tripwire/Highlight Formula, separate filters/inclusions for each layer, time phase, date basis, prorating, thresholds, defined columns, detailed-report display mode, and library/workspace hash.

For each metric run, compare: raw numerator/count; raw denominator/population; unrounded value; formatted display value; offender UID set; threshold band; color/description; `Fail` flag; and detailed-report row/column output. A matching ribbon percentage with a different offender set or denominator is a failure.

The 20260708 AFT remains a later reference snapshot. The repository currently pins the 20260423 Bible for normative formulas. Promoting 20260708 requires an ADR, formula-drift review, regenerated expected outputs, and a full parity rerun.

## SSI reproducibility contract

Persist and compare the SSI version, source hash, focus UID, predecessor/successor direction, all-dependencies setting, constraint handling, leveling-delay handling, driving/secondary/tertiary bands, waterfall/path options, calendar convention, and export timestamp.

Exact tests compare the complete UID set, task names, Start, Finish, Driving Slack, Trace Log tier, and ordered driving-path sequence. Drag is only an exact gate where the repository golden explicitly validates it; elsewhere it remains provenance-only.

## Predictable outputs and repeatable matrix

The supplied `PREDICTIVE_ORACLE_MATRIX.json` contains nine source-pinned prediction cases for Project2, Project5_TAMPERED, the Hard File progression, and EVM1/EVM2. `HARDENED_TEST_CASES_V9.json` contains all 89 immutable oracle-container contracts, including complete SSI row expectations.

| Case | Mode | Source |
|---|---|---|
| ACUMEN-PROJECT2 | exact | `tests/fixtures/golden/project2_5/case.json` |
| ACUMEN-PROJECT5 | exact_with_documented_basis_variants | `tests/fixtures/golden/project2_5/case.json` |
| ACUMEN-HARD-FILE | exact_with_documented_divergences | `tests/fixtures/golden/fuse_hardfile/case.json` |
| ACUMEN-HARD-FILE-UPDATED | exact_with_documented_divergences | `tests/fixtures/golden/fuse_hardfile/case.json` |
| ACUMEN-HARD-FILE-UPDATED2 | exact_uid_sets | `tests/fixtures/golden/fuse_hardfile/case.json` |
| ACUMEN-HARD-FILE-UPDATED3 | exact_uid_sets | `tests/fixtures/golden/fuse_hardfile/case.json` |
| ACUMEN-EVM1 | exact | `tests/engine/test_evm_acumen_reference.py` |
| ACUMEN-EVM2 | exact_plus_known_progress_scheduler_residual | `tests/engine/test_evm_acumen_reference.py` |
| SSI-CORPUS | row_exact_or_explicitly_blocked | `uploaded project-library SSI workbooks` |

Exact cases must match without tolerance unless the field contract explicitly declares presentation rounding. Documented drift/variant cases must match both the program result and the recorded vendor difference; forcing the values together is prohibited. SRA/Monte Carlo outputs require a fixed seed/config where supported and statistical acceptance bands rather than assumed bit-exact vendor RNG parity.

## Execution sequence for Claude Code

1. Copy `HARDENED_MASTER_MANIFEST_V9.json`, `HARDENED_TEST_CASES_V9.json`, `PREDICTIVE_ORACLE_MATRIX.json`, `repo_hardened_audit.py`, and `oracle_matrix_runner.py` into the current repository audit folder.
2. Run `python repo_hardened_audit.py --repo . --manifest HARDENED_MASTER_MANIFEST_V9.json --run-gates`.
3. Resolve every parse error, stale filename reference, manifest mismatch, or quality-gate failure. Do not waive failures.
4. Run `python oracle_matrix_runner.py validate` and `python oracle_matrix_runner.py list`.
5. For each schedule version, export program results to canonical JSON and run `python oracle_matrix_runner.py compare actual.json --case-id <CASE>`.
6. For SSI outputs, export canonical row JSON and run `python oracle_matrix_runner.py compare-ssi actual_ssi.json --case-id <TC-ID>`.
7. Store a run manifest with source/oracle hashes, program commit, Python/Java/MPXJ versions, Acumen version+AFT+AFW hashes, SSI settings, status/period dates, calendar fingerprints, locale/timezone, and tolerance policy.
8. Only promote a case to exact parity when its readiness gate is green.

## Required assets to close remaining gates

| Severity | Gap | Required action |
|---|---|---|
| BLOCKER | Four SSI reports do not have an exact dated source MPP snapshot. | Original/progress UID4 source snapshots and the exact two UID152 dependent-analysis snapshots, or regenerated SSI exports from retained source files with settings captured. |
| BLOCKER | Current Hard_File_updated4 24-hour binary cannot be semantically compared with archived updated3 24-hour payload. | Download/checkout current MPP and run semantic fingerprint comparison through the same MPXJ version. |
| BLOCKER | Current repository reference-upload head was not locally executed. | Run repo_hardened_audit.py and the complete quality/parity gate in a current checkout. |
| HIGH | ref2/2345.afw cannot identify which Project5_TAMPERED binary was loaded. | Acumen export/workspace manifest containing full source path and SHA-256, or retain one canonical source and regenerate the workspace. |
| HIGH | No XER files exist in the uploaded project-library archives. | Non-CUI P6 XER snapshots plus matching Acumen/SSI/P6 oracle exports and calculation/calendar settings. |
| HIGH | Large Test File OverAl Fixed report name conflicts with exact schedule-date evidence. | Confirm source provenance or regenerate SSI export with source filename embedded; do not use filename as ground truth. |
| MEDIUM | Acumen workbooks generally do not embed source SHA-256. | Add a Source Manifest sheet/sidecar with schedule hash, report hash, tool version, metric-library hash, settings, status date, timezone, and export time. |
| MEDIUM | Stochastic SSI/Acumen SRA cannot be guaranteed bit-exact without vendor RNG details. | Capture seed, trials, distribution, correlation, risk mapping, calendar, focus event, and vendor version; use statistical rather than byte-exact distribution acceptance. |

## Deliverable map

- `HARDENED_CORPUS_CROSS_REFERENCE.xlsx` - full navigable workbook.
- `HARDENED_MASTER_MANIFEST_V9.json` - complete canonical corpus and controls.
- `HARDENED_ASSOCIATIONS_V5.csv` - all 169 schedule-oracle evidence edges.
- `HARDENED_TEST_CASES_V9.json` - 89 immutable oracle contracts.
- `PREDICTIVE_ORACLE_MATRIX.json` - known expected scalar/count/set cases.
- `oracle_matrix_runner.py` - comparison CLI.
- `repo_hardened_audit.py` - current-checkout exhaustive audit and gate runner.
- `verify_hardened_v9.py` and `HARDENED_VERIFICATION_RESULT_V9.json` - independent process verification.

## Source traceability

- Repository: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`.
- Current reference-upload head: `dcacbf4458f2049aeec01be345b32d1685dae27c`.
- Last documented green code head: `2dc369678dfc294db189d1bc706eba4ab02b752a`.
- Repository files reviewed: `docs/STATE/HANDOFF.md`, `docs/STATE/REPO-INVENTORY.md`, `pyproject.toml`, `.github/workflows/ci.yml`, parity/formula-audit tests and golden cases.
- Project library: `/mnt/data/Reference Files.zip` and `/mnt/data/Reference Files 2(1).zip`, recursively extracted and independently reverified.
