# ADR-0161 — Industry pass/fail thresholds for the on-time execution indices

## Status

Accepted. Operator 2026-07-08: "Why do some measures have values of NA and others FAIL? If there
is no threshold … follow industry best practices and establish a threshold that makes sense …
define for the user what those are and how you calculated them. Make sure the metrics library is
also up to date."

## Context

The EVM / baseline-compliance panel showed several measures as **N/A** (no threshold) alongside
others that read PASS/FAIL. Two distinct reasons were conflated in the UI:
- genuinely **undefined** quantities (cost-based SPI/CPI/TCPI on a schedule with no cost), and
- **informational ratios** that had simply never been assigned a pass/fail bar (the on-time
  execution family: Baseline Finish/Start Compliance, Completed/Started On-Time, CEI Finish/Start,
  and their late mirrors).

## Decisions

1. **On-time execution indices get a 95% pass bar, cited.** Baseline Finish Compliance, Baseline
   Start Compliance, Completed On Time, Started On Time, and CEI (Finish/Start) now score **PASS at
   ≥ 95%**. The bar is the DCMA 14-Point Assessment's Baseline-Execution-Index / CPLI standard
   (0.95 — already used in this repo for BEI/CPLI), reinforced by the GAO Schedule Assessment Guide
   (GAO-16-89G, Best Practice 9, credible on-time baseline performance). These indices are the same
   on-time-delivery family, so they inherit the same threshold rather than a fabricated new one.
2. **Late mirrors get the complementary ≤ 5% bar.** Completed Late and Started Late score **PASS at
   ≤ 5%** — the complement of the 95% on-time bar.
3. **Informational counts stay N/A by design.** Forecast to be Finished/Started, Not Started, and
   Not Completed are denominators / status counts, not quality gates — they carry no threshold and
   remain N/A (labeling them PASS/FAIL would be meaningless, and on an in-progress schedule a high
   "Not Completed" is expected, not a failure).
4. **Cost indices stay N/A only for missing data.** SPI/CPI/TCPI remain N/A **when the file is not
   cost-loaded** — a data limitation, not a missing threshold. On a cost-loaded schedule they score
   against 1.0. Law 2 upheld: a fabricated number is never shown for a genuinely undefined one.
5. **Documented for the operator.** Every new threshold + its derivation is in `help.py` (so the
   hover tooltips and the generated `METRIC-DICTIONARY.md` carry it), and a collapsible on-page
   **"How these PASS / FAIL / N/A results are scored"** legend on the Schedule-performance and
   Baseline-compliance panels explains the 95%/5% bars, their DCMA/GAO derivation, and the
   informational-vs-undefined distinction.

## Consequences

- The operator's Hard_File_updated now reads CEI(Finish) 18% **FAIL**, CEI(Start) 33% **FAIL**,
  BFC 18% **FAIL**, Completed Late 9% **FAIL**, Started Late 0% **PASS** — genuine, cited results
  instead of a wall of N/A. Parity untouched (the Fuse/SSI golden tests assert counts and values,
  not these display statuses; the no-status-date path still returns all-N/A). New engine + view
  tests pin the thresholds; the metric dictionary regen test enforces the doc sync.
- Thresholds are a documented, adjustable convention — the operator can retune them with the
  citation trail intact if a program uses a different execution standard.
