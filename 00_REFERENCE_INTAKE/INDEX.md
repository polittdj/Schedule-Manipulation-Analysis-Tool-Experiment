# 00_REFERENCE_INTAKE — INDEX (authoritative catalog)

> **Refreshed 2026-07-17 (ADR-0240).** Every file below was inventoried from the working tree and
> its tracked status confirmed with `git ls-files`; every duplicate/conflict claim was verified by
> md5. **The entire intake suite is tracked in the repo** (operator-confirmed non-CUI,
> ADR-0151/0152, committed via the GitHub web UI). The `.gitignore` rules only stop *local*
> additions; they do not mean "never committed" — see the CUI note at the bottom.
>
> **Before renaming or moving anything, read §5:** several paths are probed **literally** by
> tests, and the CUI pre-commit guard **blocks local renames of these binaries by design**
> (a renamed blob's new path is not on `origin/main`). All physical reorganization goes through
> the GitHub web UI, then this INDEX and any cited `_source` strings get refreshed in the same
> sitting.

---

## 1. Catalog by purpose (logical order)

### 1.1 The Bible — NASA Acumen metric library (`.aft`)

| File | Role |
|---|---|
| `NASA Metrics_Complete_20260423.aft` | The metric library ("the Bible") — XML `<Metric>` Name/Formula entries; the authoritative formula source for every Bible-sourced metric |
| `acumen_v8.11.0/NASA Metrics_Complete_20260708.aft` | Newer snapshot of the same library (2026-07-08 export) |

**Verified by:** `tests/engine/test_aft_formula_audit.py` — discovers every `.aft` anywhere under
this folder and pins each implemented metric's formula string verbatim (DCMA/CEI/HMI/FEI-BRI/
Float-Ratio families + the 9 SEM AUDIT rows). Location inside the folder does not matter to the
test. `metrics_library/` is an empty placeholder (satisfied at root).

### 1.2 Golden-chain schedules — P2→P3→P4→P5 (`mpp/`)

| File | Role |
|---|---|
| `mpp/Project2.mpp` … `mpp/Project5.mpp` | The four-snapshot golden chain (status dates 2026-05-24 → 08-27) |
| `mpp/Project5_TAMPERED.mpp` | Byte-identical to `mpp/Project5.mpp` (md5 `4078c854…`) — the "same tampered file under two names, upload twice" instruction in FILE-NAMES.md, because different tests probe different names |
| `Project2.mpp` (root) | Byte-identical duplicate of `mpp/Project2.mpp` (md5 `e9c50dd9…`) |
| `Project5_TAMPERED.mpp` (root) | **⚠ DIFFERENT BYTES** from the `mpp/` copy — see §4 |

**Verified by / feeds:** `tests/engine/test_chain_acumen_reference.py` (Acumen Metric-History
chain parity — BEI 0.74/0.67/0.58/0.59, Critical 41/40/37/4, High Float, Missing Logic; finds
files by basename `rglob`, Java required), `tests/importers/test_loader.py` (literal
`mpp/Project2.mpp`), `tests/importers/test_mpp_mpxj.py`, `tests/web/test_upload_batch_jvm.py`.
The CI-safe parity gate (`tests/parity/test_parity_gate.py`, `pytest -m parity`) does **not**
parse these `.mpp`s — it runs on the committed MSPDI conversions in
`tests/fixtures/golden/project2_5/`, whose values were transcribed from the exports in §1.5.

### 1.3 Large Test File series (`mpp/`)

| File | Role |
|---|---|
| `mpp/Large_Test_File.mpp` (underscore) | The **original bytes** (md5 `0fa2ded4…`) that the UID-152 SSI goldens were exported from — tests pinned to old content must target this file |
| `mpp/Large Test File.mpp` (spaces) | **Replaced 2026-07-16 delivery** (md5 `5da03749…`, different content) — first half of the SEM/FRI cross-version pair |
| `mpp/Large Test File2.mpp` | Second half of the SEM/FRI pair (Large Test File → File2, FRI 0.19) |
| `mpp/Large Test File Leveled.mpp` | The **saved-views ground truth** file (25 real groups / saved filters) |

**Verified by / feeds:** `tests/importers/test_msp_views.py` (literal path to the Leveled file —
saved filter/group ingest + MPXJ `Filter.evaluate()` oracle), SSI UID-152 goldens
(`tests/fixtures/golden/ssi_uid152*/`), the SEM Large-pair sandbox validation (ADR-0238), and the
`acumen_v8.11.0/Large Test File vs Large Test File2*` Fuse exports.

### 1.4 Hard_File series (`mpp/`) — Fuse progression + 24h-calendar pair

| File | Role |
|---|---|
| `mpp/Hard_File.mpp`, `mpp/Hard_File_updated.mpp`, `…updated2.mpp`, `…updated3.mpp` | The Fuse-validated progression (SPI(t)-Acumen 0.80/1.14/1.25, DCMA09 21/0, BEI 0.27/0.59/0.47) |
| `mpp/Hard_File_updated4 24 hour calendar.mpp` | The 24-hour-calendar variant of updated3 — the committed basis for the queued PR-R3 24h MPXJ golden (SSI UID-155 slack 32d ↔ 18d on the same 100-row path) |
| `mpp/Hard_File_updated_with_logic_reestablished.mpp` | Logic-repair variant (missing-logic studies) |

**Verified by / feeds:** `tests/fixtures/golden/fuse_hardfile/case.json` (values transcribed from
the `acumen_v8.11.0/Hard_File_*` reports), `tests/fixtures/golden/ssi_hardfile_uid155/case.json`,
and the queued 24h-calendar golden (task #23 / PR-R3).

### 1.5 Acumen Fuse v8.11.0 exports — the golden numbers

Root (P2/P5 pair): `P2-P5 - DCMA Report.xlsx` (incl. the `Industry-Standards` SEM sheet —
PR-M2's P2/P5 SEM golden: 20|5|0|0.74|0|1.25|0.74|1.07|N/A|Delta), `P2-P5 - Detailed Metric
Report.xlsx` (per-activity X marks), `P2-P5 - Metric History Report.xlsx` (the chain-test
source), `P2-P5 - Quick Add Metrics.xlsx`, `P-P5 - Quick Add Metrics .xlsx` (different content
despite the similar name — 25.9 KB vs 172.4 KB; note the stray space), `Project2 vs
Project5_TAMPERED Forensic Analysis Report.xlsx` (per-activity Total-Float/Critical/cost sheets),
`Project2v5 Forensic Analysis Report.xlsx`, `Workbook1 - DCMA Report.xlsx`, `Hard_File Forensic
Analysis Report.xlsx`.

`acumen_v8.11.0/`: the Hard_File Fuse suite (`Hard_File_Fuse - *`, `Hard_File_update vs
update2_Fuse - *`, `Hard_File_update2 vs update3_Fuse - *`, forensic reports, missing-logic
workbooks, `HA*~1.XLS`/`HARD_F~3/4.XLS` 8.3-name artifacts), the Large-pair suite (`Large Test
File vs Large Test File2 - *` incl. the DCMA report carrying the Large-pair SEM golden:
609|49|0.03|0.51|0.03|1.67|0.51|2.77|N/A|Delta / 630|24|…|0.19|…), the `.afw` Fuse workbooks +
`.fieldmap.xml` field maps (incl. the updated3-vs-updated4 24h-calendar pair), and the newer
`.aft` (§1.1).

**Feeds:** `tests/fixtures/golden/project2_5/` (§A/§B/§C/§E + `fuse_exports_2026-06.json`),
`fuse_hardfile`, the SEM parity pins in `tests/engine/` (ADR-0238), and
`tests/parity/test_fuse_export_parity.py` (Net Finish Impact −148 engine / −134 stored,
reconciled to the day). The golden JSONs are transcriptions — these workbooks are the audit
trail behind every pinned number.

### 1.6 SSI Directional Path exports (`ssi/` + root)

`ssi/` (canonical): UID-67 (Project5_TAMPERED), UID-152 (Large_Test_File original bytes; plus
Leveled variants 2026-07-14 and the Large/File2 pair 2026-07-15), UID-155 (Hard_File /
Hard_File_updated / updated3 / updated4-24h), plus the SSI settings screenshot (`… SSI
Settings.jpg`).

Root loose copies: `Project5_TAMPERED_UID_67_…` and `Large_Test_File_UID_152_…2026-7-8…` are
**byte-identical duplicates of their `ssi/` copies** (verified). The UID-145 trio
(`UID_145_…2026-6-22/23…`), UID-4 trio, UID-152 June variants, and `Large Test File (OverAl
Fixed) UID_152_…` exist **only at root** — the `ssi_uid145` golden's real source is
`UID_145_Directional_Path_Analysis_All_Dependencies_2026-6-23-12-37-10.xlsx`.

**Feeds:** `tests/fixtures/golden/ssi_uid67|ssi_uid145|ssi_uid152|ssi_uid152_leveled|
ssi_hardfile_uid155/case.json` and the parity gate's SSI rows (UID-145 all-dependencies
**108/108** exact; UID-152 783-row trace; drag values UID-67).

### 1.7 SRA ground truth (root)

`SRA Risk - Project5_TAMPERED - SRA.xlsx` (MSP-native S-curve), `SRA Sensitivity Analysis.xlsx`
(tornado/3-point; top driver UID 107 = 2.8/13.8/16.6 wd), `sra-ssi.xlsx` (the tool's own export;
event 145 P10 2027-11-30 / P50 12-13 / P80 12-21 / P90 12-26 — the seed contract), `sra-ssi
(January 2026).xlsx`, `sra-report.docx`, `sra-report January 2026.docx`, plus
`references/sra-ssi-setup.json`. **Feeds:** future SRA export/format regression goldens
(queued; not yet test-pinned).

### 1.8 Handbooks & standards (root, duplicated under `references/`)

NASA Schedule Management Handbook (zip), PM Handbook SP-2014-3705, WBS / IBR handbooks, EVM
Implementation Handbook, PPC handbook, SOPI 6.0, SRB handbook, SP-20240014019/326 PDFs,
`PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` (the 7-graph-family reference behind
`performance_summary.py`, ADR-0182). **All eleven root copies are byte-identical to their
`references/` copies (verified)** — the root set is redundant; see §3. These source thresholds
and terminology (margin 50%-consumed rule, Fig 6-9 health checks, INT-02 SRA method), not
test-pinned numbers.

### 1.9 Process / audit references (`references/`)

Operator direction (`CLAUDE CODE NEXT PROMPT FOR THURSDAY 07162026.docx`), external audits
(ChatGPT 07-15, POLARIS Independent/Delta audits 07-15 + corpus-delta JSON), the HARDENED audit
protocol (`.md`/`.docx` + V9/V10 bundles with cross-reference workbooks and `hardened_audit.py`),
machine manifests (`reference_manifest.json`, `reference_structural_summary.json` — external
provenance overlay, not test obligations), the TP1–TP4 MSPDI test-project XMLs (synthetic
scenario files: progressed library, 4×10 calendar, DCMA-seeded outage, 5-version DataCenter),
`Field Map.fieldmap.xml`, the Lisbon SRA deck, `Concepts, Methods & Techniques.docx`,
`INT-02-Advanced-Schedule-Analysis.pdf`, `smp-template-20200225.docx`.

### 1.10 Governance (root)

`DEPOSIT-HERE.md` (historical Gate-1 deposit instructions), `FILE-NAMES.md` (historical upload
name contract), `Use Fable 5 Ultracode.md` (the operator's standing model/audit rule — mirrored
into `CLAUDE.md`, ADR-0240), `INDEX.md` (this file), `Ai Result Comparision.docx` + `Executive
Summary Large Test File.docx` (operator AI-comparison and summary write-ups), `.gitkeep`
placeholders (`pbix/` and `metrics_library/` are empty).

---

## 2. Reverse index — what each test needs from this folder

| Test | Needs (literal unless noted) |
|---|---|
| `tests/engine/test_aft_formula_audit.py` | any `.aft` under `00_REFERENCE_INTAKE/` (recursive; skips if absent) |
| `tests/engine/test_chain_acumen_reference.py` | `Project2/3/4/5_TAMPERED.mpp` by **basename rglob** (first hit in path-sort order — currently the ROOT `Project5_TAMPERED.mpp`, see §4); Java required |
| `tests/importers/test_loader.py` | `mpp/Project2.mpp` |
| `tests/importers/test_msp_views.py` | `mpp/Large Test File Leveled.mpp` |
| `tests/importers/test_mpp_mpxj.py` | files in `mpp/` |
| `tests/web/test_upload_batch_jvm.py` | files in `mpp/` |
| `tests/parity/*` (`pytest -m parity`) | **nothing here at runtime** — runs on `tests/fixtures/golden/**` transcriptions; this folder is the transcriptions' audit trail |
| Golden `case.json` `_source` strings | documentation-only pointers into this folder (no test reads them) |

Everything in `mpp/` is probed by name somewhere — **do not rename anything inside `mpp/`.**

---

## 3. Proposed reorganization & rename map (operator-applied via GitHub web UI)

The local CUI guard blocks renames of these binaries **by design** (§5), so this map is applied
through the web UI (delete + re-upload at the new path, or GitHub's rename), ideally in one
sitting, then this INDEX is refreshed. `mpp/` stays untouched.

| # | Current (root) | Proposed | Why |
|---|---|---|---|
| 1 | `UID_145_*.xlsx` (×3), `UID_152_*.xlsx` (×5), `UID_4_*.xlsx` (×3), `Large Test File (OverAl Fixed) UID_152_*.xlsx` | → `ssi/` | all SSI exports live in `ssi/` |
| 2 | `Project5_TAMPERED_UID_67_*.xlsx`, `Large_Test_File_UID_152_*2026-7-8*.xlsx` | **delete root copies** | byte-identical duplicates already in `ssi/` (verified) |
| 3 | `P2-P5 - *.xlsx` (×4), `P-P5 - Quick Add Metrics .xlsx`, `Project2 vs Project5_TAMPERED…xlsx`, `Project2v5…xlsx`, `Workbook1 - DCMA Report.xlsx`, `Hard_File Forensic Analysis Report.xlsx` | → `acumen_v8.11.0/` | all Fuse exports in one place; also drop the stray space: `P2-P5 - Quick Add Metrics (per-file).xlsx` |
| 4 | the 11 handbook/standards files (§1.8) | **delete root copies** | byte-identical duplicates already in `references/` (verified) |
| 5 | `SRA*.xlsx`, `sra-ssi*.xlsx`, `sra-report*.docx` | → new `sra/` | SRA ground truth as its own group |
| 6 | `Ai Result Comparision.docx` | → `references/Ai Result Comparison.docx` | reference write-up + typo fix |
| 7 | `Executive Summary Large Test File.docx` | → `references/` | reference write-up |
| 8 | `Project2.mpp` (root) | **delete** | byte-identical duplicate of `mpp/Project2.mpp` (verified) |
| 9 | `Project5_TAMPERED.mpp` (root) | **operator decision — see §4 first** | root and `mpp/` copies are different builds |
| 10 | `NASA Metrics_Complete_20260423.aft` | stays at root (or → `metrics_library/`) | formula-audit finds it anywhere under the folder |
| 11 | `DEPOSIT-HERE.md`, `FILE-NAMES.md`, `Use Fable 5 Ultracode.md`, `INDEX.md` | stay at root | governance |

After applying: refresh this INDEX (§1 tables + §4), and update the golden `_source` strings that
cite moved root files (documentation-only; no test breaks).

---

## 4. Verified duplicate / byte-conflict table

| Files | md5 verdict | Disposition |
|---|---|---|
| `Project2.mpp` (root) vs `mpp/Project2.mpp` | **identical** (`e9c50dd9…`) | root copy deletable (map #8) |
| `mpp/Project5.mpp` vs `mpp/Project5_TAMPERED.mpp` | **identical** (`4078c854…`) | intentional ("upload twice", FILE-NAMES.md) |
| `Project5_TAMPERED.mpp` (root, `52e777c2…`) vs `mpp/Project5_TAMPERED.mpp` (`4078c854…`) | **DIFFERENT builds** | ⚠ the chain test's `rglob` **currently resolves to the ROOT copy** (path sort) and the chain goldens pass against it; the CI parity gate is unaffected (fixtures). **Operator: confirm which build is canonical.** If the root copy is removed, re-run `tests/engine/test_chain_acumen_reference.py` with Java before trusting the swap |
| `mpp/Large Test File.mpp` (`5da03749…`) vs `mpp/Large_Test_File.mpp` (`0fa2ded4…`) | **different — intentional** | spaces = replaced 2026-07-16 (SEM/FRI pair); underscore = original bytes behind the UID-152 goldens. Keep both; never "dedupe" |
| root SSI UID-67 / UID-152 exports vs `ssi/` copies | **identical** | root copies deletable (map #2) |
| 11 root handbooks vs `references/` copies | **all identical** | root copies deletable (map #4) |
| `P-P5 - Quick Add Metrics .xlsx` vs `P2-P5 - Quick Add Metrics.xlsx` | **different content** (25.9 KB vs 172.4 KB) | keep both; rename to disambiguate (map #3) |

---

## 5. CUI & guard rules for this folder (read before touching anything)

- The suite is **operator-confirmed non-CUI** (ADR-0151/0152) and **tracked in the repo** —
  committed via the GitHub web UI. Real CUI (production schedules) never enters a build session
  and is blocked from commit everywhere.
- The pre-commit guard (`.githooks/pre-commit`) blocks any **new, modified, or renamed**
  blocked-extension file (`.mpp/.xlsx/.aft/.xer/.docx/…`) outside `tests/fixtures/` unless the
  staged blob is byte-identical to `origin/main` **at the same path** (`inherited_from_main`,
  ADR-0152). Consequence: local `git mv` of anything cataloged here is blocked — **by design**.
  Do not weaken the guard for housekeeping; use the web UI (§3).
- `.gitignore` still ignores new local files here (except the governance `.md`s) — that is the
  first fence against accidentally committing a real CUI schedule from a build session.
