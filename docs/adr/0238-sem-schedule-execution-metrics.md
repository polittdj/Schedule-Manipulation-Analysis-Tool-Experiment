# ADR-0238 — The Schedule Execution Metrics (SEM) engine family (PR-M2)

## Status

Accepted. The nine unbuilt members of the Bible group *Industry Standards / Schedule Execution
Metrics (SEM)* now compute in `engine/metrics/sem.py` (`compute_sem(schedule, prior)`), joining
the already-validated BRI-Cumulative for the full ten-metric family, wired live into /standards.

## Context / fidelity notes

Formulas were taken verbatim from the committed `.aft` (both snapshots identical; the
formula-audit test now pins all nine strings). Three subtleties the Bible encodes that summaries
had lost: BEI Current/Cumulative count ALL actual finishes (numerator not restricted to the
baselined set — the index can exceed 1, and the SEM BEI-Cumulative is a different metric from the
DCMA %-complete BEI: both ship, separately labeled, ADR-0176 precedent); TC-BEI carries no ROUND
and its denominator excludes already-finished baselined-to-go work; Delta's to-complete term uses
the SIMPLE baselined-to-go denominator, so Delta is computed from its own formula, never as the
difference of the two rounded siblings. FRI Current joins each task's PreviousFinish from the
prior loaded version by UniqueID (NA with no prior, as Acumen prints N/A).

## Validation

Cell-for-cell against the committed Fuse DCMA reports' Industry-Standards rows:
- **P2/P5_TAMPERED pair (CI parity gate `tests/parity/test_sem_parity.py`):** 8 metrics exact on
  both files incl. BEI-Current 1.25 = 5/4 and TC-BEI 1.07 = 106/99, 1.24 = 99/80 (granular
  numerator/denominator pins per the HARDENED rule); FRI N/A (no prior) and 0 = 0/9 (P2 prior).
- **Large Test File / File2 pair (sandbox, Java path):** 17/17 exact incl. FRI 0.19 cross-file.
- **The vendor's exported Delta cells (-0.34 / -0.61) are NOT reproducible** from the vendor's
  own library formula on inputs that reproduce every sibling exactly (formula-faithful: -0.33 /
  -0.65; an exhaustive variant sweep found no term definition hitting both cells). Verdict:
  vendor export artifact — the pinned formula wins, the discrepancy is recorded in the parity
  test docstring and the AUDIT row note.

Also fixed: /standards hid informational (NA-status) index values — the value cell now keys on
the computed denominator, not the status pill (the PR-M1 placeholder test had masked it).
A dedicated /standards Excel/Word export remains open (values are on-page; the Workbench export
covers extracts) — it rides a later polish PR.
