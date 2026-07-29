# ADR-0308 — A guard that one code path can walk around

**Status:** Accepted · **Date:** 2026-07-29 · **Supersedes:** none ·
**Amends:** ADR-0307 (completes its completed-work guard; versions its setup schema) ·
**Audit:** `audit/SRA-PARITY-20260729.md`

## Context

ADR-0307 landed as #481. An outside reviewer (ChatGPT Codex) then raised three defects against that
commit. All three were **re-verified by execution before anything was changed** — this project has
been burned by confident wrong findings, and by its own lead being wrong, so nothing here is taken on
the reviewer's word. All three reproduced.

The unifying failure is the same one each time: **ADR-0307 fixed a rule in one place, and two other
code paths still reached the old behaviour around it.**

1. **The register walked around the point-mass guard.** ADR-0307 forced a completed activity's
   three-point estimate to a point mass, but the risk-application loop still added each fired risk's
   impact to *every* affected uid. Executed proof, on a 100%-complete driving activity:

   ```
   driver 100% COMPLETE : std_days=9.99  p10=5760  p90=15360  det=5760
      risk hits=210/400  meanDelta=20.0
   VERDICT: completed-activity risk injects variance? True
            p90 moved by 20 working days on FINISHED work
   ```

2. **Saved setups walked around the corrected formula.** `_ssi_three_point` gives a stored
   Best/Worst precedence over `factor_to_bc_wc`, and `_apply_ssi_setup` restored `bcwc_minutes`
   verbatim with no version check. Every setup written before ADR-0307 therefore keeps running the
   inverted Best Case **forever**. This is not hypothetical: the committed reference setup
   `00_REFERENCE_INTAKE/references/sra-ssi-setup.json` (`setup_version: 1`) holds **783** such pairs
   — e.g. UID 427, factor 5, stored BC 432 against an implied ML of 480 = **0.900 × ML**, the old
   result where the corrected rule gives 0.100 × ML. Same for UID 447; UIDs 732/733 sit at 0.700 at
   factor 3, UID 734 at 0.800 at factor 4.

3. **The grid displayed a range the run had stopped using.** ADR-0307's auto-calc guard only
   *skipped recalculation* for a completed activity, leaving any pre-existing `sra_bcwc` entry in
   session state. `_ssi_grid_rows` and the setup export still showed and persisted it while
   `_ssi_three_point` ignored it — the operator reads a Best/Worst the simulation does not use.

## Decision

### 1. Finished work cannot be delayed by a future risk — and an inert risk says so

The risk-application loop in `compute_sra_ssi` (and the duplicate in `compute_jcl`) skips completed
uids. Because a risk that fires but moves nothing is exactly the V2 pathology this project documented
the same day, the omission is **disclosed rather than silent**: `SSIRiskStat` gains `applied`, false
when *every* affected activity is complete, and `sra_ssi.js` renders the risk row as
`inert (activity complete)` with a `—` delta, mirroring the existing branch-status column. The hit
count is still reported, because the risk genuinely fired; only its effect was nil.

### 2. A pre-ADR-0307 setup is migrated, not trusted

`_SSI_SETUP_VERSION` → **3**. Loading a setup at version < 3 **recomputes** the Best/Worst from
`factor_to_bc_wc` for every uid that also carries a factor, and leaves entries with no factor alone.

A stored entry does not record whether it was factor-derived or hand-typed, so the two cannot be told
apart; the operator chose recompute-where-a-factor-exists over rejecting the file outright. The cost
is stated plainly: **a hand-entered override on a factor-bearing activity in a pre-v3 setup is
replaced by the corrected calculation.** Recomputing (rather than merely dropping) is what makes the
grid show the corrected numbers immediately and the setup round-trip — the run would be correct
either way, since `_ssi_three_point` already falls back to the factor when no range is stored.

### 3. A completed row neither shows nor accepts a Best/Worst

Auto-calc now *removes* a stale entry instead of skipping past it; `_ssi_grid_rows` suppresses
`bc_days`/`wc_days` for a completed activity and exposes a `completed` flag; and `POST /sra/grid`
refuses both a factor-derived and a hand-typed range on a completed row. **The factor itself is still
recorded** — that is the operator's ranking, and only the range is meaningless once the work is done.

## Consequences

- **The ADR-0307 fix now actually reaches every path.** Before this, an operator who loaded a saved
  setup got the inverted Best Case with no indication anything was wrong, which is the worst
  available outcome for a fidelity fix: shipped, believed, and bypassed.
- **`pytest -m parity` green — 44 passed, no golden moved.** The new behaviour is pinned by four
  regression tests: a register risk on completed work injecting no variance while disclosing
  `applied=False` (with a live-activity counter-check so the guard cannot be a blanket no-op), a
  pre-v3 setup recomputing to the corrected Best Case, a current setup round-tripping its ranges
  untouched (so the migration is a migration and not amnesia), and a completed grid row neither
  showing nor accepting a range.
- **`SSIRiskStat` gains a defaulted field**, so existing constructions are unaffected; the risk table
  gains a Status column, matching the branch and conditional tables that already carry one.
- **Nothing here changes the parity conclusion of ADR-0307.** The residual variance gap against MS
  Project, and the carried anchor-realignment finding, are untouched — see
  `audit/SRA-PARITY-20260729.md` §6 and §9.
- **The generalised lesson**, recorded in `LESSONS-LEARNED.md`: when a rule is corrected, the fix is
  not done until every path that can *reach around it* is closed — a second writer of the same state
  (the register), a persisted copy of the old output (the setup), and a reader that still displays it
  (the grid). A guard one code path can walk around is not a guard.
