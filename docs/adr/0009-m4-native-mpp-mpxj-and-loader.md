# ADR-0009: M4 native `.mpp` ingest (out-of-process MPXJ) + multi-file loader

- **Status:** Accepted
- **Date:** 2026-06-08 (session A6 — Phase 2 build, milestone M4)
- **Relates to:** §6.B (parse ≤10 native `.mpp`, no manual conversion, all metadata, UID-only), §0/§6.G (CUI)
- **Builds on:** ADR-0008 (M3 importers), ADR-0005 (golden fixtures), ADR-0001 (vendored MPXJ)

## Context
`.mpp` is a binary OLE format with no pure-Python reader. The repo vendors a tiny MPXJ converter
(`tools/mpxj`, `MpxjToMspdi <in> <out>`) that reads `.mpp` and writes MSPDI XML. M4 wires it into the
importer layer and adds the batch loader §6.B requires (up to 10 files at once). The operator uploaded
the two non-CUI sample schedules (`Project2.mpp`, `Project5.mpp`) directly into this session.

## Decision
1. **Out-of-process MPXJ, never in-process JPype.** `parse_mpp()` runs `java -cp <classes>:<lib/*>
   MpxjToMspdi <in> <tmp.xml>` as a subprocess (fixed argv, `shell=False`, `shutil.which("java")`
   absolute path, 300 s timeout) and feeds the MSPDI to the M3 `parse_mspdi_text`. Keeps the JVM out
   of the Python process (the runner's own design note), keeps conversion deterministic per input, and
   reuses the tested MSPDI path. Runner location defaults to repo `tools/mpxj`, overridable via
   `SF_MPXJ_HOME`. Missing JRE/runner/file or any non-zero MPXJ exit → `ImporterError` (fail loud).
2. **Citations survive conversion.** The original `.mpp` file name (not the temp MSPDI) is recorded as
   `Schedule.source_file`, so every downstream citation names the file the operator recognises.
3. **Loader dispatches by extension; one `Schedule` per file.** `.mpp`/`.mpt`→MPXJ, `.xml`/`.mspdi`→
   MSPDI, `.xer`→XER; `load_schedules()` enforces the ≤10 cap and fails loud on empty/oversized/
   unsupported input. The loader does **not** merge versions — cross-version matching by UniqueID is a
   later analysis step (diff, M11); each schedule stays an independent, UID-keyed trust root.
4. **Commit distilled golden MSPDI, not the raw `.mpp`** (reconciles ADR-0003 "never commit raw
   reference" with ADR-0005 "commit distilled fixtures"): the MPXJ MSPDI conversions of Project2/5 are
   committed under `tests/fixtures/golden/project2_5/` (non-CUI, data-owner attested); the binary
   `.mpp` stay gitignored in `00_REFERENCE_INTAKE/mpp/`. This makes §6.B parity reproducible in CI
   with no `.mpp` or JVM dependency.
5. **CI strategy without the `.mpp`.** Real-`.mpp` conversions are integration tests that **skip** when
   the sample files or a JVM are absent (CI). The wrapper's orchestration and every error path are
   covered JVM-free by faking the subprocess; the committed golden MSPDI cover the parse → 144
   activities (UID 2-145) assertion in CI.

## Validation (real uploads, this session)
- `Project2.mpp` (rev 1, status 2026-05-24) and `Project5.mpp` (rev 3, status 2026-08-27) each convert
  → MSPDI → model as **145 rows = the UID-0 project summary + 144 activities (UID 2-145)**, matching
  the M4 acceptance criterion. Project5 is the later (slipped) revision — the §6.B comparison target.
- All importer modules at **100% line+branch**; full suite **280 passing, 99.91%**; ruff/ruff-format/
  mypy(strict)/bandit clean (`# nosec B404/B603` justify the controlled subprocess).

## Deferred (carried forward)
- Optional **Windows COM** path; **`.pmxml`** (P6 XML); **calendar parsing** (default 8h/Mon-Fri still
  in effect, lands with CPM, M5). Per-task cost / activity-code (from ADR-0008) unchanged.

## Consequences
- §6.B ingestion (native `.mpp`, ≤10, no manual conversion, all metadata, UID-keyed) is implemented +
  tested + validated; field-value parity vs Acumen/SSI is the separate B2 gate (M6-M9), now fed by the
  committed golden MSPDI inputs. R-12 (CUI files don't cross sessions) is mitigated for the parity
  inputs: future sessions parse the committed MSPDI without needing the raw `.mpp`.
