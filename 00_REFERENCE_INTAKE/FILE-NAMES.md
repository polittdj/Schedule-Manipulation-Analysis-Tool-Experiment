# FILE-NAMES — exact upload names & destinations (copy-paste)

> **Historical upload contract — `INDEX.md` is the current authoritative catalog** (what is
> here now, what each file verifies, verified duplicates, and the reorganization map).

Upload on GitHub by **browsing into the folder first**, then *Add file → Upload files*.
Everything here is git-ignored for local commits; web uploads land tracked — that's fine
(operator-confirmed non-CUI build inputs).

## ✅ Already delivered (leave as-is, they work where they are)

| File | What it is | Status |
|------|-----------|--------|
| `NASA Metrics_Complete_20260423.aft` | The NASA Acumen metric library ("the Bible") — 1,443 `<Metric>` Name/Formula entries | **VALIDATED** — the live-Bible formula audit runs and passes against it |
| `Project2 vs Project5_TAMPERED Forensic Analysis Report.xlsx` | Acumen Fuse® Forensic Analysis comparison (P2 vs P5_TAMPERED snapshot, created 7/7/2026) with per-activity Total-Float / Critical / cost sheets | **CLASSIFIED as PARK-LIST A-1 source** — feeds the §E float/critical re-pin |

## 📁 mpp/ — EXACT names required (tests probe these literal paths)

```
00_REFERENCE_INTAKE/mpp/Project2.mpp
00_REFERENCE_INTAKE/mpp/Project3.mpp
00_REFERENCE_INTAKE/mpp/Project4.mpp
00_REFERENCE_INTAKE/mpp/Project5.mpp
00_REFERENCE_INTAKE/mpp/Project5_TAMPERED.mpp
00_REFERENCE_INTAKE/mpp/Large_Test_File.mpp
```

- `Project2.mpp` … `Project5_TAMPERED.mpp` — the native MS Project files of the golden chain
  (P2→P3→P4→P5). `Project5.mpp` and `Project5_TAMPERED.mpp` are the **same tampered file under
  two names** (different tests probe different names — upload it twice).
- `Large_Test_File.mpp` — the large real-world schedule (SSI absolute driving-slack + parse/perf).

## 📁 acumen_v8.11.0/ — names flexible; suggested:

```
00_REFERENCE_INTAKE/acumen_v8.11.0/Fuse_Workbook_Project2.xlsx
00_REFERENCE_INTAKE/acumen_v8.11.0/Fuse_Workbook_Project5_TAMPERED.xlsx
00_REFERENCE_INTAKE/acumen_v8.11.0/Fuse_Ribbon_DCMA_Project2.xlsx
00_REFERENCE_INTAKE/acumen_v8.11.0/Fuse_Ribbon_DCMA_Project5_TAMPERED.xlsx
```

The **per-file** Fuse v8.11.0 metric exports (workbook / ribbon / DCMA sheets), one per schedule —
upgrades every §A/§B/§C parity row from "matches transcription" to "matches Fuse".

## 📁 ssi/ — names flexible; suggested:

```
00_REFERENCE_INTAKE/ssi/SSI_DirectionalPath_Project5_TAMPERED.xlsx
00_REFERENCE_INTAKE/ssi/SSI_DirectionalPath_Large_Test_File.xlsx
```

Fresh SSI driving-path/driving-slack exports. **Record the focus/target UniqueID for each and the
MS Project version in NOTES.md** — the UID is required data, not optional.

## 📁 references/ — names flexible; suggested:

```
00_REFERENCE_INTAKE/references/EVM- Metric History Report.xlsx
00_REFERENCE_INTAKE/references/EVM1 Forensic Analysis Report.xlsx
00_REFERENCE_INTAKE/references/2345 - Metric History Report.xlsx
00_REFERENCE_INTAKE/references/NASA_Schedule_Management_Handbook.pdf
```

Re-uploads of the earlier reference bundle (containers are ephemeral — prior session uploads are
gone) + the handbook/decks that source the health-check thresholds.

## 📁 pbix/ — optional

```
00_REFERENCE_INTAKE/pbix/<your-report-name>.pbix
```

Or, if sensitive: exported DAX measure definitions (`.txt`/`.md`) + visual screenshots.

## 📁 metrics_library/ — ✅ satisfied

The `.aft` Bible is already delivered (root of the intake folder — works there, no move needed).

## 📄 NOTES.md — at the intake root

```
00_REFERENCE_INTAKE/NOTES.md
```

SSI focus UIDs + MS Project version; Fuse version/status-date/calendar used; any known
Acumen-vs-MSP disagreements; anything intentionally omitted.
