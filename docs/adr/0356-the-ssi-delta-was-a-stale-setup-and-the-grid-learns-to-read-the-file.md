# ADR-0356 — The SSI delta was a stale setup, and the grid learns to read the file

**Status:** Accepted · **Date:** 2026-08-06 · **Extends:** ADR-0123 (the SSI path),
ADR-0307/0308 (factor semantics) · **Method:** ADR-0240 full rigor — measured, decomposed,
hypothesis attacked before any fix; every fix mutation-proven and validated in a sandbox
against the operator's real artifacts.

## The reported defect

The operator ran SSI's Monte-Carlo (2,000 iterations, focus UID 152, one register risk
R1 = 86% / 321 wd on UID 7443) on a new `Large_Test_File2.mpp`, and "the same data" through
this tool — with a significant delta. The artifacts supplied: the `.mpp` (md5 differs from the
committed intake — a new vintage), SSI's results workbook, the risk-register template, and the
tool's own saved setup JSON.

## Measurement first (the occurrence-weighted histogram is the oracle; the workbook's own
Mean/StdDev cells are the documented unweighted trap — its "Mean Date" sits 95 days off its
real weighted mean here)

| figure | SSI oracle | tool, operator's setup | tool, file-true inputs |
|---|---|---|---|
| det percentile | 11.15% | 10.65% | 12.80% |
| mean offset (cal d) | +343.5 | +365.1 | **+330.1** |
| σ (cal d) | 153.4 | **179.9** | **157.3 (+2.5%)** |
| P50 | +391 | +386 | +383 |
| P90 | +447 | **+546** | **+424** |
| min / max | −125 / +575 | −143 / **+790** | −120 / +560 |

Lobe decomposition located the excess precisely: SSI's fired-risk lobe is tight
(σ 41.9 cal d); under the operator's setup ours ran ≈110. Durations-only vs risks-only runs
split the mechanisms — the risk model is a clean two-point (+449 constant, hits 86.3%); ALL
excess spread came from the duration model's inputs.

## Root cause — input divergence, not engine error

The session's inputs came from a setup captured against an **earlier vintage** of the
schedule; the new file's `SRA Risk Ranking Factors` were re-randomized across all 1,722
leaves. Against the file: **605 of 783 setup factors disagree, 939 file-factor tasks are
absent, 400 of 435 Best/Worst pairs are stale** (each side is the corrected ADR-0307 table
applied to its own factor — e.g. UID 5539: setup factor 5 → WC 1.5×remaining ≈ 941 wd, file
factor 2 → 1.2×). SSI reads the file's stored fields; the tool faithfully ran the stale ones.
The register template's R2 (63% / 45 wd / UID 7433) was in **neither** run: the R1+R2 variant
overshoots the oracle (mean +371.7), and the register import route was verified to handle the
operator's workbook perfectly (both risks land, integer-cell UID included) — R2 was simply
absent from the session at save time.

**The disproof attempt failed** (so the hypothesis stands): re-running the engine on the
file's own stored inputs lands σ within 2.5%, P50 within 8 days, and the min/max envelope on
the oracle — July's validated parity class. The residual ~20 d understatement at P80/P90 has
a sign-consistent, already-logged candidate (this file's six *recurring* calendar-exception
patterns, which the single-block day model skips) and is recorded, not chased here.

## The product defect, and the fix

The tool made this failure mode inevitable: **nothing in the app could read the schedule's
own stored SRA fields** — the parity *test* reads them, the product never did — so a stale
setup was the only way to populate the grid, and it replayed silently.

1. **`POST /sra/load-from-schedule`** (+ a "Load from schedule" button beside Save/Load
   setup): seeds `sra_factors` + `sra_bcwc` **verbatim** from the file's
   `SRA Risk Ranking Factors` / `Best Case Duration` / `Worst Case Duration` custom fields
   (pairs only when both present; incomplete leaves only — ADR-0307), replacing the grid
   wholesale. No derivation happens: these are the very values SSI reads (Law 2).
2. **Setup vintage fingerprint (setup_version 4)**: saved setups stamp
   `schedule_fingerprint` (source file, task count, status date, a sha256 over the file's
   stored factor/BCWC vintage). On **every** load — fingerprint present or not — the loaded
   values are compared against the active file's stored fields, and any disagreement produces
   an operator-visible `CHECK INPUTS` warning with counts (factors disagreeing / file tasks
   absent / pairs differing) plus, when the fingerprint differs, where the setup came from.
   The run still uses the loaded values — the operator now chooses that knowingly.

## Verification

- **Sandbox effectiveness test on the real artifacts:** upload the operator's converted
  schedule → `POST /sra/load-from-schedule` → the root-caused divergences are gone (5539 →
  factor 2, 1566 → 4, BC/WC verbatim; 998 factors + 919 pairs seeded) → the 2,000-iteration
  run reproduces the file-true exoneration figures **exactly** (det_pct 0.1280, mean +330.1,
  σ 157.3).
- Four mutations each failed exactly its guard (completed-guard dropped · replace→merge ·
  warning silenced · fingerprint hash constant). The fingerprint pin **passed its first
  mutation** — it re-called the mutated helper as its own oracle (`"" == ""`); re-pinned on
  independent properties (64-hex shape + vintage sensitivity to a changed stored factor).
  Fourth self-agreeing-oracle/discriminator catch of the day.
- Setup-version pins re-baselined (3 → 4, deliberate, named); SSI/SRA web suites 60 passed;
  affected suites 325+ passed; parity 49; statics green (one B608 false positive on the SRA
  panel's HTML f-string annotated with the existing house `nosec` pattern).

## Deliberately NOT done

- **No auto-seed on upload.** Seeding mutates operator-visible state; the explicit button
  keeps the grid's provenance unambiguous. Revisit only with operator direction.
- **The P80/P90 recurring-exception residual** (~20 cal d on this file) is recorded against
  the importer's documented single-block limitation — a separate unit with its own oracle.
- **The uploaded artifacts are not committed** — intake additions are the operator's call
  (ADR-0152 posture); this file family would otherwise make a strong second parity oracle.
