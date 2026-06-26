# PARK-LIST — artifact-gated re-entry checklist ("come back with files")

The audit's honest in-environment ceiling is **`ENGINE==GOLDEN`** (the engine reproduces the committed
*recorded/transcribed* golden) — **not** `ENGINE==FUSE/SSI` (the golden equals a live reference-tool re-run).
Every item below is blocked on an external artifact the build session does not hold. Until each artifact is
present, the corresponding parity claim must keep its **"against our transcribed targets"** qualifier.

> **CUI boundary (operator-confirmed, per CLAUDE.md Law 1).** The build/reference inputs needed below —
> `Large_Test_File.mpp`, the SSI/Acumen/`.aft` exports, and the golden `.mpp` inputs — are **NOT CUI** and
> **MAY** be loaded into a build session (e.g. uploaded to Claude Code) to perform the verifications. Only the
> *deployed tool's production schedules* are CUI; those never touch a build session. The pre-commit guard
> still blocks `.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx` from the repo regardless — deposit under the git-ignored
> `00_REFERENCE_INTAKE/`, never commit them.

## Deposit location for all artifacts
`00_REFERENCE_INTAKE/` (git-ignored; defense-in-depth, kept out of git as large binaries — see CLAUDE.md).

---

## A. Parity oracle-upgrade items (flip a gate from self-consistency/transcription to true reference parity)

| # | Closes | Exact artifact required | Verification unlocked once present |
|---|--------|-------------------------|------------------------------------|
| A-1 | **F-01** (§E float/critical circularity — currently PARTIAL, engine-pinned) | Acumen Fuse v8.11.0 **§E PP&Change export** of the *current* Project5-vs-Project2 pair | Diff `case.json` `change_P2_to_P5` §E rows (`new_critical`, `no_longer_critical=34`, `float_erosion`) **row-by-row** against the Fuse export; replace the engine-pinned values with the transcribed Fuse values; the gate flips from **self-consistency → ENGINE==FUSE**. *(Also: add a test that asserts the "engine-pinned / NOT Fuse-validated" marker text so it can't be silently removed — see VERIFICATION-REPORT §3 F-01.)* |
| A-2 | **All §A/§B/§C rows** (`ENGINE==GOLDEN` only today) | The operator's Fuse **workbook / ribbon / DCMA** exports of Project2 & Project5 | Diff `case.json` §A/§B/§C against the Fuse exports; upgrade every "PASS (engine==golden)" to "PASS (engine==Fuse)". |
| A-3 | **Literal `.aft` formula match** | `NASA_Metrics_Complete_*.aft` (the NASA Acumen "Bible") | `tests/engine/test_aft_formula_audit.py` live-Bible branch stops skipping (`:669`); each metric formula in `help.py`/the AUDIT table is matched **verbatim** against the `.aft` `<Metric>` Name/Formula. |
| A-4 | **Large-File absolute SSI driving-slack** (PARITY-REPORT §"native .mpp", Phase-E item 3) | **SSI's recorded target/focus UniqueID** for `Large_Test_File.mpp` (+ the `.mpp` itself) | Re-run driving-slack with SSI's focus UID; reproduce the absolute (not just relative-tier) values; resolve the ADR-0045-vs-PARITY-REPORT contradiction with a real number. |
| A-5 | **`ssi_uid143` xfail** (stale golden, ADR-0112) | A fresh **SSI Directional-Path export** for the current `Project5_TAMPERED.mpp` | Re-pin the SSI driving-slack golden to the current file; the 2 xfails (`test_driving_slack`, `test_parity_gate::test_ssi_driving_slack_exact`) flip to live passes, retiring the quarantine. |
| A-6 | **Native `.mpp` ↔ MSPDI equivalence**; TP2 4×10 calendar round-trip; Large-File parse | The native `.mpp` files (`Project2`, `Project5`, `Large_Test_File`) — **toolchain already present** (Java 17 + vendored MPXJ `tools/mpxj/`, runnable here) | Convert each `.mpp`→MSPDI via MPXJ; assert the model/metrics equal the committed MSPDI goldens; confirm the TP2 holiday-loss (risks R-04) and any native-only drift. Blocked on **data only**, not capability. |
| A-7 | **Cost-EVM SPI(t)/finish/NFI residuals** (matched BCWS/BCWP/DCMA/BEI rows ALREADY pass against committed Fuse EVM1/EVM2) | **Not an export** — a progress-aware (data-date floor) reschedule in the engine (ADR-0108 work) | Once the engine floors in-progress remaining work at the data date, the documented SPI(t)/finish/Net-Finish-Impact residuals close; re-pin against EVM1/EVM2. *(This is engine work, parked here only because it's the other half of the EVM oracle story.)* |
| A-8 | **Structural/health threshold authority** (F-14: driving-slack 10/20 d; 35% lag; 10-d band) | NASA Schedule Management Handbook + the assessment decks | Replace the in-repo design-choice cutoffs with sourced thresholds, or cite the handbook at point of use. |

## B. The live test skips these artifacts gate (for cross-reference)
The 7 current skips are exactly these intake gates — none hides a defect:
`.aft` Bible absent → `test_aft_formula_audit.py:669` (A-3); chain `.mpp` absent →
`test_chain_acumen_reference.py:102,110` (A-6); `Project2/5.mpp` absent → `test_loader.py:93`,
`test_mpp_mpxj.py:53` ×2 (A-6). The 2 xfails are the `ssi_uid143` stale golden (A-5).

---

## C. NOT artifact-gated — open and fixable in-env NOW (do NOT wait for files)

These were re-confirmed **OPEN by live repro** this audit and need **no external artifact** — they are the
internal-audit roadmap that was orphaned when the F-set batch shipped (VERIFICATION-REPORT §1.2, §6). Listed
here so the next session does not mistakenly file them under "waiting on the operator."

- **C1 (CRITICAL)** — `to_json_text` drops 12 fidelity fields on Save→reopen (`json_schedule.py:180`). In-env.
- **H1** — SSI load 500 + session half-mutation on non-list `affected` (`app.py:6131`). In-env.
- **H3/H4** — one malformed XER id sinks the whole file (`xer.py:168,415`). In-env.
- **M2** — pre-commit guard + `.gitignore` omit `.aft`/`.docx` (`.githooks/pre-commit:13`). In-env.
- **M3** — friendly JSON fabricates `project_start` (`json_schedule.py:168`). In-env.
- **M4** — UID-0 baseline-finish leak (`mspdi.py:602`). In-env.
- **M5** — days↔% client/server rounding mismatch (`app.py:5758` vs `:5874`). In-env.
- **M6** — sign-blind figure regex (`citations.py:25`). In-env.
- **M7/M8/L2/L3/L5/L7** — perf debounce, MEI doc note, non-finite guard, offload atexit, DCMA-08 baseline-flag
  note, tolerant OutlineLevel parse. All in-env.
- **NEW-1** — Float-Ratio elapsed-duration axis mismatch (`float_ratio.py:78-82` vs `:90`). In-env; a golden
  with an elapsed in-progress Normal activity would pin the fix.

---

## D. Ready-to-paste "WHEN FILES ARE PRESENT" follow-up prompt (next session)

```
The operator has deposited reference files under 00_REFERENCE_INTAKE/ (git-ignored; these build/reference
inputs are NOT CUI per CLAUDE.md Law 1 and may be loaded into this build session). Read
audit/PARK-LIST.md §A, then for EACH artifact actually present:

1. Acumen Fuse §E export of current P5-vs-P2  -> A-1: diff case.json change_P2_to_P5 §E rows row-by-row
   against the Fuse export; replace engine-pinned new_critical/no_longer_critical/float_erosion with the
   transcribed Fuse values; add a test asserting the "engine-pinned/NOT Fuse-validated" marker text; the
   §E gate flips from self-consistency to ENGINE==FUSE. Keep pytest -m parity green.
2. Fuse workbook/ribbon/DCMA exports of P2 & P5 -> A-2: diff case.json §A/§B/§C; upgrade PASS(engine==golden)
   to PASS(engine==Fuse) row-by-row.
3. NASA_Metrics_Complete_*.aft                  -> A-3: the live-Bible branch of test_aft_formula_audit.py
   stops skipping; match every help.py formula verbatim to the .aft.
4. SSI focus UID for Large_Test_File.mpp (+.mpp)-> A-4: reproduce absolute driving-slack; resolve the
   ADR-0045 vs PARITY-REPORT contradiction.
5. Fresh SSI Directional-Path export for current Project5_TAMPERED.mpp -> A-5: re-pin ssi_uid143; flip the
   two xfails to live passes.
6. Native Project2/Project5/Large_Test_File.mpp -> A-6: MPXJ (already installed) -> MSPDI -> assert model/
   metrics == committed MSPDI goldens; check TP2 4x10 holiday loss (risks R-04).

For every upgraded row, change the doc/report wording from "matches our transcribed targets" to "matches
Acumen Fuse/SSI vN export (00_REFERENCE_INTAKE/<file>)". Run the full gate + pytest -m parity before each
commit. Do NOT regenerate or edit any committed golden/fixture — only ADD transcribed reference values or a
new golden. Stay read-only on existing oracles. Then refresh HANDOFF.md + SESSION-LOG.md (drift guard) and
the unified ledger in audit/VERIFICATION-REPORT.md §2.

Separately (NO files needed) the orphaned in-env findings in PARK-LIST §C remain OPEN — C1 (CRITICAL) first.
```
