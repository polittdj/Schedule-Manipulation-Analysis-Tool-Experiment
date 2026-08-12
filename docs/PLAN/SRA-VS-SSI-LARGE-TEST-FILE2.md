# SRA vs SSI on `Large Test File2` — measured findings

**Date:** 2026-08-12 · **Status:** measured, reproducible · **Inputs:** operator-supplied export set
(`sraPolaris_Risk_Drivers_Tornado_Results_Large_Test_File2.zip`) containing BOTH tools' outputs on
the SAME file, plus the source `SRA Large Test File2.mpp` (9.4 MB, 2,125 tasks, 2,698 links).

Run configuration, identical on both sides: **focus UID 152** (`QJ29ZvAvtEjBcpqHDer1`),
**2,000 iterations**, triangular, risks/opportunities ON.

The operator reported three problems. **Two do not reproduce as described, and the third is real
and worse than reported.** Everything below is recomputed from the exports, not read off them.

---

## F-1 — The Mean / Std-Dev divergence is in SSI's HEADLINE CELLS, not in our engine

SSI's export carries a headline block *and* the full 2,000-sample distribution it came from. The
two disagree with each other. Ours agrees with the distribution.

| | Mean finish | Std dev (calendar d) | Std dev (working d) |
| --- | --- | ---: | ---: |
| SSI — **stated headline cells** | 2030-03-25 | **226.23** | — |
| SSI — **recomputed from its own histogram** | **2030-06-08** | **156.68** | **111.9** |
| **Polaris (ours)** | **2030-06-11** | **151.4** | **108.2** |

* The histogram is the complete sample: 246 rows, occurrences summing to **exactly 2,000**, and its
  `% Probability` column reproduces as `occurrences / 2000` on every row.
* **Our mean is 3 days from the mean of SSI's own data. Our std dev is within 3.4%.**
* SSI's stated 226.23 matches neither its own calendar-day (156.68) nor working-day (111.9) figure;
  the ratio to its own calendar figure is 1.4439, which corresponds to no unit conversion in play.

**Percentiles — the unambiguous comparison, taken from SSI's own cumulative column:**

| | SSI | Polaris | Δ (calendar days) |
| --- | --- | --- | ---: |
| P10 | 2029-06-14 | 2029-06-25 | +11 |
| P50 | 2030-08-02 | 2030-08-05 | +3 |
| P80 | 2030-08-28 | 2030-08-28 | **0 — exact** |
| P90 | 2030-09-13 | 2030-09-17 | +4 |

Two independent Monte-Carlo engines at 2,000 iterations, different seeds, agreeing to 0–11 days
across a ~22-month window. That is sampling noise, not a defect.

**Conclusion:** no engine fix is indicated. The comparison target was SSI's headline cells, and
those are not reproducible from SSI's own exported distribution. **NOT a licence to close this** —
see R-1 below: the *right* action is to make our own report state which basis each figure uses, so
a reader can perform this reconciliation without re-deriving it.

## F-2 — Sensitivity VALUES match exactly; the LABELS are wrong, and dangerously so

Top-13 rows, both tools, same order, same UIDs:

| SSI total | Ours | | SSI total | Ours |
| ---: | ---: | --- | ---: | ---: |
| 304.483 | 304.5 | | 10.790 | 10.8 |
| 108.735 | 108.7 | | 9.910 | 9.9 |
| 35.033 | 35.0 | | 9.329 | 9.3 |
| 20.300 | 20.4 | | 8.800 | 8.8 |
| 14.519 | 14.5 | | 8.521 | 8.5 |
| 14.100 | 14.1 | | 7.529 | 7.5 |
| 13.031 | 13.1 | | | |

**The math is right.** The defect is naming:

| UID | SSI's label | Our label |
| --- | --- | --- |
| 7443 | `R/O - Test Risk` | `lvFKaF8Jtq8DkkB0s9nv` |
| 7433 | `R/O - Test Risk 2` | `FxBsJSw4ZNEIyIQA8bL9` |

SSI distinguishes a **risk driver** from the **task it attaches to**. We label both with the host
task's name — so our OAT sheet prints **UID 7443 twice, under the same name, with different
numbers** (304.5 d and 9.9 d). One row is the risk `Test Risk`; the other is the activity.

Our own *Risk register* sheet has the correct names (`R1 Test Risk → 7443`, `R2 Test Risk 2 →
7433`), so the information is present and simply not carried into the sensitivity output.

**Severity: HIGH for a testimony context.** The largest bar on the tornado — 304.5 days, the single
biggest driver in the analysis — is attributed to an activity name rather than to the risk that
actually causes it, and the duplicate UID/name pair reads as a bug in the tool.

## F-3 — The SRA is ~2.9 minutes of compute, and 63% of it is provably wasted

Measured on this machine, this file:

| | |
| --- | ---: |
| MSPDI parse | 1.91 s |
| one full CPM pass | 0.08 s |
| SRA @ 50 iterations | 4.23 s (84.6 ms/iter) |
| SRA @ 200 iterations | 17.22 s (86.1 ms/iter) |
| **extrapolated @ 2,000** | **~2.9 minutes** |
| peak RSS | 290 MB (flat) |

Scaling is **linear** (84.6 → 86.1 ms/iter), so there is no algorithmic blow-up. At 86 ms/iter
against an 80 ms bare CPM pass, the simulation is doing **one full 2,125-task network solve per
iteration** with ~7% overhead.

**The waste is measurable and exact.** Only the ancestors of the focus event can affect its finish:

| | |
| --- | ---: |
| tasks in schedule | 2,125 |
| tasks that can affect focus UID 152 | **783** |
| tasks re-solved every iteration but irrelevant | **1,342 (63%)** |
| speedup available from sub-network restriction alone | **~2.7×** → ~1.1 min |

That is a floor, not a ceiling — it does not include hoisting per-iteration allocation out of the
loop, which the 7% overhead figure suggests is already small but the 86 ms itself is not.

**The crashes are consistent with this and are not yet root-caused.** A ~3-minute synchronous
computation inside a request is long enough to hit a browser, proxy, worker or watchdog timeout,
which would present exactly as the operator described: two failures with no result, then a success
that "took a VERY long time". **UNVERIFIED** — the timeout path has not been reproduced, and it
must be, because "it was slow" and "it was killed" have different fixes.

---

## What must happen (all required; ordered by evidence strength)

| # | Requirement | Why this order |
| --- | --- | --- |
| R-1 | Report which basis every SRA figure uses (working vs calendar days), on the page and in the export | F-1 shows a reader cannot currently reconcile two tools without re-deriving the distribution by hand |
| R-2 | Carry risk-driver names into the OAT sensitivity output; never print a risk under its host task's name | F-2, HIGH — the biggest bar on the tornado is currently mislabelled |
| R-3 | Reproduce the crash before optimising | a timeout and a slow path need different fixes; guessing costs a wrong fix |
| R-4 | Restrict the simulated network to the focus event's ancestor set | F-3 — 63% of the work is provably irrelevant; ~2.7× measured |
| R-5 | Regression-pin the percentile agreement against this export set | F-1's agreement is currently un-guarded; the next engine change could silently break it |
| R-6 | Make long SRA runs non-blocking (progress + cancel), whatever R-3 finds | 2.9 min is beyond any reasonable synchronous request even after R-4 |

**Reproduce any of this:** convert with
`java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi "SRA Large Test File2.mpp" LTF2.xml`,
then `compute_sra_ssi(sch, config=SRAConfig(iterations=N, target_uid=152))`.
