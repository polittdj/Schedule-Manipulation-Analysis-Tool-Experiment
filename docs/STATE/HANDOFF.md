# Handoff — 2026-09-18 (d) (R-45 **CLOSED** (ADR-0511) — EV (BCWP) and AC (ACWP) follow the booking's TIME-PHASED record, not the task's scalars; the ribbon's BAC is the workbook's time line, not a definition — **v1.0.276**, schema **2.17.0**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`60d75e93`** (#699, R-67 / ADR-0510 + QC-3 / ADR-0509, **MERGED** 2026-09-18 15:23Z by the operator; the squash TREE-IDENTICAL to the PR head `383b1c54`, tree `6e01fe7a…`, compared with `git rev-parse <sha>^{tree}` this session). **`main`'s OWN runs for `60d75e93` — read TO CONCLUSION this session, by their JOBS:** CI 1929 (`35362114564`): `cui-guard` 15:23:43Z · `browser` 15:41:20Z · `test (3.13)` 15:50:30Z · `floor` 15:50:59Z · `test (3.11)` 16:14:20Z · `check` 16:14:27Z — **SIX OF SIX GREEN**; installer-smoke 767 (`35362114719`): `linux` 15:24:05Z · `windows` 15:28:42Z. Nothing about `60d75e93` is outstanding. This unit ships on branch `claude/ci-verification-task-scheduling-7y0gh8` (the designated branch, started on the squash) as **draft PR [#700](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/700)** (the operator merges; never marked ready here) — expect EIGHT checks (`installer/**` changed); read the FINAL head's checks, the docs-only follow-up push restarts them. **The gate:** statics green on both ruff binaries, `ruff format`, `mypy --strict` (165 files), `bandit` (exit 0); the 223 targeted pins green; the wheel built after the last `src/` edit; lockstep 68 passed; the full suite and `-m parity` ran in a separate worktree at the code commit `9e773d74`: **4 failed / 5,653 passed / 7 skipped in 36:20**, every failure attributable (the three state-doc pins red by construction at a code commit; the `web.app` re-export contract for `_progress_disagreement_note`, fixed in `52b18eae` / `839f955e`); the non-skipped count is one short of the naive expectation (5,650 + 8) and unattributed — the prior baseline was never measured locally. **CI on the final head `839f955e` is the suite's verdict: read its eight checks FIRST next session** and record them; `floor` on `c33b87e4` had read 1 failed / 5,275 passed / 269 skipped, that one failure being the contract. Review cover remains ABSENT (Codex quota exhausted); the battery and the gate are all this repo gets. Highest ADR **0511**. Version **1.0.276**. Schema **2.17.0**. QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-45 was three claims, and all three fell to the export the row said had no oracle.** Every sheet of
every Hard_File workbook was opened. Fuse's field map maps MS Project's own `BCWP` / `ACWP` / `BCWS`
onto its EV / AC / PV and `Baseline Cost` onto both its Baseline Cost and Budget Cost; the Forensic
Analysis Report diffs the two snapshots activity by activity and states updated3's whole-file
Budget Cost as **133,400** (unchanged) — the engine's figure to the unit.

* **BAC 121,800 is the Ribbon View's time line.** The workbook's five monthly ribbons run 2026-07 to
  2026-11 (built around updated2's 11-06 finish); updated3 finishes 12-12, and its **15
  December-starting activities carry 11,600 / 160 h** — every ribbon delta to the unit (Budget /
  Total / Remaining Cost −11,600, Baseline / Total Work −160 h, actuals unchanged), and Fuse's own
  per-activity view of updated3 lists none of them. No engine change; pinned as a reconciliation.
* **EV and AC follow the booking's time-phased record.** UID 290 (100 % complete) is written 31 h
  of actual work on a 40 h booking; its Type-2 / Type-3 blocks hold **16 h regular + 6 h overtime**.
  22 / 40 × 12,500 = 6,875 (53,715 = 59,340 − 5,625, exact on all three ribbons: 16,800 / 49,700 /
  53,715); 16 h × 200 + 6 h × 300 = 5,000 spent where the scalar says 6,800, and the Logistics
  Apprentice's 17.077 h are priced at the rate-table row in force at the **status date** (30, not
  the 10 they were worked at): +341.5 — the two ACWP deltas (+341.92 / −1,458.08) sum to 290's
  1,800 of overtime. AC 20,800.00 / 64,104.61 / 66,244.61 → the ribbon's 20,800 / 64,105 / 66,245.
  "To time now" is refuted by sign.
* **Shipped:** `Assignment.performed_work_seconds` / `performed_overtime_seconds` (the file's own
  resolution — per-booking minute rounding reads 64,104.17, which prints 64,104), `baseline_cost`,
  `actual_cost`; `Resource.overtime_rate` at the status date; SCHEMA 2.17.0; `evm._earned_value` /
  `_actual_cost_of_work_performed`; the disagreement disclosed on SPI and the EVM page (UID 290).

## How it was verified

Red first on the pristine package by name (parity, importer, Save, schema, engine); battery **13 / 13
red by name** on shadow copies (control green, the package asserted per row); corpus census 44 files /
1,079 budgeted tasks: EV moves on 290 (every copy of updated3 and the 24-hour snapshots) and on four
in-progress tasks of the 24-hour snapshots (**UNVERIFIED** — no ribbon for that save), AC on 290 and
210, every other file byte-identical (EVM1 / EVM2 carry no record). Six QC-3 assumptions fell,
recorded in ADR-0511's table — including the session's own "integer minutes keep the unit match".

## Deliberately NOT done

The 24-hour snapshots' four movers (no oracle) · MS Project's stored per-task BCWP / ACWP (MPXJ does
not read them) · rate tables B to E · a per-booking BCWS read (ADR-0492's series already is).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-70** (T2, M — the
backward pass through a completed / started successor; the repo carries the oracle: updated3's 188
stored 12-12 17:00 against its completed successor 291's 09-08; the 67 / 34 census in ADR-0510) ·
then R-03 · R-04 · R-09 · **R-69** · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; **R-68** waits on the
operator's reading (question (f)). The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
