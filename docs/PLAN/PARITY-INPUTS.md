# Parity inputs — confirmed by the data owner (Gate 1)

Authoritative record of the build's parity parameters, as stated by the user on
2026-06-05. The parity suite (§6.B/§6.C) must reproduce these exactly. Re-verify the
file-derived values against the actual exports during Phase 1 analysis.

## Compared schedules (the §6.B pair)
- **`Project2.mpp` ↔ `Project5.mpp`** — the two MS Project files that were compared.
  The Acumen comparison + per-file exports are labeled **"Project 2-5"** accordingly.
  **Both deposited 2026-06-05** (IDs in `INTAKE-MANIFEST.md`). *The user's message said
  "Project4.mpp", but the folder contains Project5.mpp (no Project4) — treated as a typo;
  Project5 is the correct target. Confirm if wrong.*
- The SSI driving-path analysis was run **in `Project5.mpp`**.
- *To confirm in Phase 1 (from file metadata/status dates):* which file is the earlier vs.
  later revision (do not assume from the numbers).

## SSI driving slack / driving path (§6.C)
- **Target = UniqueID `143`** in `Project5.mpp`. *(User initially said 142, then corrected
  to **143**; 143 also matches the `SSI … UID_143_Directional_Path_Analysis` filenames.)*
- The tool must trace the driving logic path to UniqueID 143 and report **Driving Slack in
  `days` per task**, matching **MS Project + SSI** for this project/UniqueID exactly.

## Path thresholds (defaults; MUST be user-configurable per §6.C)
- **Secondary path:** driving slack **> 0 day and ≤ 10 days**.
- **Tertiary path:** driving slack **> 10 days and ≤ 20 days**.
- (Critical/driving = the path the engine identifies as driving to the target.)
- These defaults must be **editable by the user at upload**, per project, in the built tool.

## Tool versions to match
- **Acumen Fuse v8.11.0** (confirm from the exports' metadata).
- **Microsoft Project:** Online Desktop Client, **MSO Version 2603, Build
  16.0.19822.20240, 64-bit**.

## CUI scope (per data owner; see ADR-0003)
- The **reference/golden files** provided for this build are **non-CUI**.
- The **real schedules the finished tool will analyze at runtime WILL be CUI** → Law 1/2
  (local-only, default Ollama, no cloud by default, fail-closed, no off-machine transfer)
  bind the **shipped tool's runtime**, unconditionally.

## Units (§3)
- Durations in `day`/`days`; percentages rendered with a sign; internal minutes converted
  to days only at the presentation boundary with deterministic rounding.
