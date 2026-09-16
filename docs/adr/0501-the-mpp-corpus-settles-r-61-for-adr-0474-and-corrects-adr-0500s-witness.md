# ADR-0501 — The repository's own 29 `.mpp` files settle R-61 for ADR-0474's type rule, discharge ADR-0500's deferred residual, and correct its refutation witness (R-61 SETTLED)

- **Status:** Accepted — 2026-09-16 (the operator's instruction: *"Use the .mpp files in the repo to settle the rule and continue"*).
- **Version:** unchanged — **no `src/` change**. The engine was measured, not modified.
- **Corrects / extends:** **ADR-0500** (R-61 closed on the 15 goldens; its residual and its refutation witness are both corrected here), ADR-0474 (the type rule, upheld), ADR-0476 (why a completed task cannot adjudicate a scheduling rule), ADR-0491 (the split gaps), ADR-0034 / ADR-0391 (`date_driven`, which turns out to place the corpus's one decisive case).
- **Shipped:** `tests/parity/test_r61_fixed_duration_leg_oracle.py` (10 → 11 pins; one renamed and re-reasoned, one added), the R-61 row in `docs/STATE/AUDIT-2026-08-27-REPORT.md`, a new row for the granularity residual. `engine/` untouched.

## Context — the residual ADR-0500 deferred was mis-scoped

ADR-0500 closed R-61 after censusing **15 MSPDI goldens** and wrote the residual as: *only a
production IMS carrying a FIXED_DURATION activity on an off-pattern crew with no
project-calendar co-booking can settle the rule.*

That was a claim about the **goldens** wearing the clothes of a claim about the **world**. The
repository carries **29 `.mpp` files** — roughly twice the golden population — including files
no golden was ever made from (`24Hour Calendar.mpp`, `Hard_File_updated4 24 hour calendar.mpp`,
`Jacked Up Schedule 1/2`, `Project3/4`, the `Project5_FX0*` and `TP4_DataCenter` tamper sets,
and the `Large Test File*.mpp` family — note `Large Test File.mpp` ≠ `Large_Test_File.mpp`, a
distinction this repo has already paid for once). All 29 were converted through the vendored
MPXJ converter into the scratchpad (never the repo — Law 1) and censused. Every artifact was
asserted to **exist**, never the converter's exit code (ADR-0498's trap).

## What the wider census measured

**Population.** 483 tasks across the 29 files are placed by an off-pattern, ratio-1.0
(non-`FIXED_UNITS`) crew leg — the population in which R-61's rule could change a date at all.

| | count |
| --- | --- |
| recorded window **byte-identical** to the engine's occupancy (duration + ADR-0491 gaps) | **369** |
| differ, and neither a leg-alone probe nor the window matches MS Project | 18 distinct UIDs |
| differ, adjudicating, margin **1–28 minutes** | most of the remainder |
| differ, adjudicating, **decisive** margin | **exactly one: UID 5263** |

**The minutes are granularity, not a rule.** Where window and occupancy differ they overwhelmingly
differ by single-digit or low-double-digit minutes (UID 5342: occupancy 2,757 vs window 2,758 —
**one minute**; UID 5316: 9,329 vs 9,333 — **four**; UID 5273: 4,687 vs 4,688 — **one**). MS
Project's stored finish sits with the window in those cases because the window *is* MS Project's
own placement recorded at full precision, while the engine's honoured-gap sum rounds. That is a
residual in the gap arithmetic, registered below as its own row — **not** evidence of a
different scheduling rule.

**A leg-alone probe is not the engine.** On the 18 UIDs where neither the leg nor the window
matched, the **shipped solve is within a day of MS Project on 17 of 18**, most within 10–20
minutes. The probe's failure is the probe's, not the product's.

**The one decisive case adjudicates FOR the engine.** `Large_Test_File2` UID 5263 is *started*
(86 %, no `ActualFinish`), so unlike a completed task its stored `Finish` really is MS Project's
scheduled output and really can adjudicate. Its window runs **9,600 minutes past** its duration
and the leg alone lands **four weeks early** (2025-03-25 14:42 vs the stored 2025-04-22 14:42) —
and the **shipped solve is exact**. The mechanism was measured, not assumed: the task is
disclosed on **`CPMResult.date_driven`** — a *stored date* places it, and the leg is irrelevant.
(The first explanation offered for it — ADR-0391's actual-start floor — was cut in the battery
and the task did not move. It was refuted before it was written down.)

## The correction ADR-0500 owes

**ADR-0500's refutation witness is invalid.** It cited `Large_Test_File` UID 5231, whose recorded
window is 26,880 crew minutes *shorter* than the engine's occupancy, and concluded that reading
the window "would collapse a leveling split the engine gets right".

The arithmetic is true. The reasoning is wrong, twice:

1. **UID 5231 is recorded-COMPLETE** — 100 % with both actuals — so its stored `Finish` *is* its
   `actual_finish`. By ADR-0476's own reasoning that is a **record of what happened, not the
   scheduler's output**, and it can adjudicate a scheduling rule in neither direction. It was
   the wrong kind of witness for the claim it was asked to carry.
2. **The engine's leg does not "get it right" there.** Alone it lands 2024-10-01 17:00 —
   **eighty days** past the file's own date. The shipped solve is exact only because ADR-0476
   pins a completed activity at its record.

ADR-0500's headline figure — *"315 activities away, 0 toward"* — is **not** withdrawn: it was a
different and valid measurement (the window rule applied inside a full solve across the goldens,
per-task against the files' stored finishes). What is withdrawn is the sentence explaining *why*
UID 5231 demonstrated it.

## Decision

**R-61 is SETTLED, and the rule is ADR-0474's: a non-`FIXED_UNITS` leg spans `ratio 1.0 × the
task's effective duration` on its leg calendar, and a WORK booking's recorded window is still
never read (ADR-0487).** `engine/` is unchanged and none may change on this evidence: on the
largest population the repository can offer, the two candidates agree exactly on 369 of 483,
differ by minutes almost everywhere else, and the single decisive disagreement is placed
correctly by the shipped engine through a stored date.

**ADR-0500's residual is DISCHARGED, not re-deferred.** The repository's own corpus settled it.
The scoping error is recorded here so the pattern is not repeated: *a residual must name the
population it was measured against, or it will be read as a statement about the world.*

The test module keeps its census and its tripwire, and gains the correction:
`test_uid_5231_is_a_completed_task_so_its_leg_never_places_it` (renamed from the mis-reasoned
witness; pins the numbers, the completeness, the eighty-day overshoot and the pin's exactness)
and `test_uid_5263_the_corpus_only_decisive_counter_case_is_exact_in_the_solve` (pins the
started-ness, the 9,600-minute window, the four-week leg-alone error, the exact solve, and
`date_driven` as the mechanism).

## Registered, not taken

**The gap-arithmetic granularity residual.** On split bookings the engine's honoured gaps land
**1–28 minutes** short of the window MS Project recorded (UIDs 5342, 5316, 5273, 5280, 5324,
5341 and others). It is below the resolution of every parity pin in the repo and it moves no
verdict, but it is systematic and one-directional and it is now a row of its own rather than
folklore. The first executable step is to compare `_split_gaps`' minute sum against the file's
own recorded window on the ~100 split bookings where they differ, and decide whether the
residual is rounding in `_recorded_span`, in the share→`after` conversion, or in MPXJ's
timephased block boundaries.

## Verification

* **29 / 29 `.mpp` files converted**, every artifact asserted to exist (never the exit code).
* **Four cuts of the census, each correcting the last** — and the corrections are the finding:
  cut 1 counted co-bookings as masking (masking is whichever leg finishes **last**, computed);
  cut 2 paired a leg to its booking by **calendar identity**, which silently reported "no window"
  for all 483 (a leg on a task calendar matches no resource's calendar object) — the fix pairs by
  index and **asserts `len(pairs) == len(legs)`** so the instrument can detect its own failure;
  cut 3 compared a **gapless** leg against a window that spans the gaps, handing every split
  booking to the window by construction; cut 4 is the engine's real occupancy.
* **Mutation battery, control green:** N1 (ADR-0476's pin cut) → the 5231 correction red by name;
  N2 (R-61's window rule) → the 5263 pin and three others red by name. **N3 is recorded as a
  NON-MUTATION on its first cut** (the stub was inserted *before* the real definition, so the
  real one won the name) — re-cut so the stub wins, it survives, which is how the `date_driven`
  mechanism was found.
* Statics green on both ruff binaries, `ruff format`, `mypy --strict`, `bandit`; the module's 11
  pins green; full gate figures in the session log.
