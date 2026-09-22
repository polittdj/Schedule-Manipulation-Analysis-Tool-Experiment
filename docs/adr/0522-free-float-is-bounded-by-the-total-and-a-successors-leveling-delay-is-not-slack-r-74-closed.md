# ADR-0522 — Free float is BOUNDED BY the total, a successor's leveling delay is NOT slack the predecessor owns, and the row's evidence that MS Project "never" inverts the pair was a statement about a FILTER (R-74 CLOSED)

**Status:** Accepted · **Date:** 2026-09-22 · **Extends:** ADR-0474 (the leveling delay in the forward
pass), ADR-0490 / R-62 (the MPXJ writer drops a zero duration), ADR-0513 / ADR-0517 (the started-work
remaining-portion model) · **Row:** R-74 (T2, S) in `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3

## Context

R-74 read, in full:

> free float above the total float: MS Project's stored `FreeSlack` never exceeds its `TotalSlack`
> (**0** of the 3,315 activities across the 44 files that store both; equal on 1,116) while the
> engine's free float exceeds its total on **1,870** incomplete activities — the logic-reestablished
> UID 408 reads 18,960 for a total of 16,740 (the stored `FreeSlack`, equal to its `TotalSlack`)…
> **remedy:** read MS Project's definition against the corpus — free slack measured to the
> successors' EARLY starts and bounded by the total, or measured to their LATE starts — with a census
> of the 1,870 before choosing.

The corpus was rebuilt from scratch and reproduces ADR-0513's population **exactly** — the 15
committed goldens under `tests/fixtures/golden/` plus 29 fresh path-keyed conversions of the intake
`.mpp` files: **44 files, 22,105 scheduled activities, 3,315 storing both slack elements, 0 stored
inversions, 1,116 stored equal.** The engine's count re-measures to **1,867**, not 1,870 (the row was
written before ADR-0513 / ADR-0517 moved float on the started-work classes).

### The row's own evidence was a statement about its filter

Every one of the **1,230** corpus rows whose stored `TotalSlack` is NEGATIVE has its `FreeSlack`
element **ABSENT**, and **no** row anywhere in the corpus stores a negative `FreeSlack`. The MPXJ
MSPDI writer omits a zero duration — the bytecode fact ADR-0490 established for `TotalSlack` and R-62
widened. So the population "3,315 that store both" **cannot contain a negative total at all**, by
construction, and "0 of 3,315 invert" measures the filter, not MS Project.

Read with that same writer rule (and only on the 41 of 44 files that carry the element somewhere — on
the 3 that never emit it, absence proves nothing, ADR-0490's own caveat), **MS Project itself reads
free (0) above total (negative) on 1,227 rows.**

### The 1,867 is two classes, not one

| class | rows | verdict |
| --- | --- | --- |
| total float is **NEGATIVE**, free floors at 0 | **1,229** | **NOT a defect.** The class MS Project itself exhibits; all 1,229 carry a negative stored `TotalSlack` with `FreeSlack` omitted, and on **577** the engine's total equals the stored total exactly. |
| total >= 0 and free exceeds it | **638** | **the defect.** Of the 622 carrying a stored `FreeSlack` the engine exceeds it on **622 of 622**, and the stored `FreeSlack` equals the stored `TotalSlack` on **610** of them. |

### The plan was attacked before the first edit (QC-3) — and three assumptions fell

| assumption | result |
| --- | --- |
| the row's remedy (b), free slack measured to the successors' **LATE** starts | **refuted.** Exact figures against the stored `FreeSlack` collapse **2,471 → 963**. |
| the row's remedy (a), "bounded by the total", as literally written (`min(free, total)`) | **refuted as written.** It manufactures **1,239** negative free floats, and the corpus stores **none**. The bound itself must be floored at zero. |
| the mechanism is one thing | **fell.** A second, independent mechanism the row does not name: ADR-0474 put a successor's stored leveling delay **into** its early start (forward pass) and **out of** the need it presents (`ls_need`, backward pass), but the free-float calculation did neither — so the delay was credited to the predecessor as slack. Worth +38 exact **on its own and on top of** the bound. |
| the bound is the total, not the **finish slack** (they differ on a floored task, ADR-0463) | **indistinguishable on this corpus** — both give 3,004 / 198 / 113. The total is taken because it is the figure MS Project's `FreeSlack` is empirically equal to (1,116 rows, and 116 of 116 no-successor rows) and because it is the number the analyst reads. Recorded as an UNVERIFIED discriminator. |
| the delay belongs on FINISH-type anchors too | **refuted.** +2 exact for **+7** low — overshoot. The backward-pass mirror (`lf_upper_bound` uses `late_finish`, not `ls_need`, for FF / SF) is right. |

Six candidate rules were built on shadow copies of the engine and measured on the whole population
before one was chosen:

| variant | exact / 3,315 | high | low | free > total (incomplete) | negative free |
| --- | --- | --- | --- | --- | --- |
| V0 pristine | 2,471 | 772 | 72 | 1,867 | 1 |
| V1 delay only | 2,509 | 732 | 74 | 1,844 | 1 |
| V2 `min(free, total)` — remedy (a) as written | 2,966 | 238 | 111 | 0 | **1,240** |
| V3 late starts — remedy (b) | **963** | 2,291 | 61 | 143 | 1,226 |
| V4 `min(free, max(total, 0))` | 2,966 | 238 | 111 | 1,229 | 1 |
| V5 `max(min(free, total), 0)` | 2,966 | 238 | 111 | 1,230 | 0 |
| **V6 = V1 + V4 (SHIPPED)** | **3,004** | **198** | 113 | **1,229** | 1 |
| V7 = V6 with the finish slack as the bound | 3,004 | 198 | 113 | 1,229 | 1 |
| V8 = V6 + the delay on FF / SF | 3,006 | 189 | **120** | 1,229 | 1 |

The independent reading that fixes the rule: MS Project stores `FreeSlack` **equal** to `TotalSlack`
on **116 of 116** corpus activities that have no successor at all, none differing.

## Decision

Free float is measured to a successor's early start **less that successor's stored leveling delay**
for START-type links (`_succ_free_start_wall` / `_succ_free_start_off` — the mirror of
`_succ_ls_wall`; a resumed tail is already past its delay, as on the backward side), and is then
**bounded by the reported total float, the bound itself never negative**: `free = min(free, max(total, 0))`.

**V5 was not taken and the difference is deliberate.** Flooring `free` itself at zero would *raise* a
negative free float to 0, and nothing in the corpus witnesses what MS Project stores there: the one
negative free float in 22,105 rows (`Jacked up Schedule 2` UID 29, −2,400 against a stored
`TotalSlack` of −2,400 the engine reproduces exactly) sits on one of the 3 files that emit **no**
`FreeSlack` element at all, so its absence carries no information. **UNVERIFIED — left alone.** V4
only ever lowers an over-count; it asserts nothing.

## Consequences

* Against MS Project's own stored `FreeSlack`, over the 44-file corpus: exact **2,471 → 3,004** of
  3,315, high **772 → 198**, and the **total float is untouched** (10,610 of 12,680 exact, before and
  after — the bound reads the total, it never writes it).
* Isolated to the **2,926** rows whose total ALREADY matched the stored `TotalSlack` exactly — so a
  total-float residual cannot flatter the result — exact goes **79.5% → 97.7%** and the low count
  **does not move (14 → 14)**. Every one of the 41 new lows in the raw count sits on a row whose own
  total float is still inexact. That is the bound propagating a *total*-float residual into free
  float, which is the correct dependency, not a free-float regression.
* **After the fix, the engine's free float exceeds its total on exactly 1,229 rows — precisely the
  negative-total class, and nowhere else.** Over the 15 committed goldens the invariant is checked
  row by row: 427 above, 427 negative, the same rows (pristine: 842 against the same 427).
* **ADR-0474's own pin movements recorded this defect as if it were a fix.** `float_free_0` on
  Project2 was moved **71 → 68** with the note "the leveled successors start later, so three more
  predecessors carry free float", and `float_free_lt10` on Project5 **73 → 69**. Both were the defect
  arriving. MS Project's stored `FreeSlack` says the answers are **74** and **72**, and the engine now
  reproduces all four bands exactly: Project2 `free_0` **74 of 106** and `free_lt10` **80 of 106**,
  Project5 `free_0` **68 of 99** and `free_lt10` **72 of 99** — an oracle independent of the engine
  that produced them.
* `driving_slack.py` is **unaffected**: it computes its own per-successor link slack and never reads
  `TaskTiming.free_float`, so the 100-row SSI driving-slack golden (ADR-0118) is untouched. The
  consumers that do read it are `float_analysis` (the activity rows) and `metrics/float_bands`.
* **Verification.** Red first on the pristine engine, by name: 4 of 7 assertions red, 3 green and
  declared as controls. Mutation battery **4 of 4 red by name**: the zero floor removed (the floor
  guard *and* the invariant) · the bound removed (UID 408, the invariant, the rate) · the delay
  removed (the delay witness, the rate) · the delay extended to FF / SF (the rate pin, which is what
  discriminates the rejected V8). The population control is not vacuous: a plain `*.xml` glob sees
  **4** of the 15 goldens, because 11 are gzipped. Suites: engine **1,290 passed**, parity
  **246 passed**.

## Deliberately NOT done

* **The 1,229 negative-total rows.** Free stays where the logic puts it (0 on every corpus row). MS
  Project omits `FreeSlack` there rather than storing a negative, so there is nothing to match.
* **The one negative free float** (`Jacked up Schedule 2` UID 29). Its file emits no `FreeSlack`
  element, so no witness exists either way. UNVERIFIED, untouched.
* **The 198 residual high rows.** 144 sit on rows whose **total** float is itself still inexact (the
  Large Test File crew-calendar chains, R-56's family); the other **54** are minute-scale residuals of
  the same family — all FS, 15 distinct UIDs, deltas of 2, 60 or 120 minutes, repeated across the 11
  Large Test File copies. None is a free-float *rule* error and none is claimed fixed. **Registered
  as the residual of R-74, to be priced against the total-float chains, not against free float.**
* **The finish-slack bound (V7).** Measured indistinguishable; not taken, not refuted.
* **`link_slack`'s non-FS semantics.** Unchanged — reference tools vary on non-FS free float, and the
  bound now caps every type regardless.
* **The importer does not read `FreeSlack` into the model.** Only `stored_total_float_minutes` is
  carried. The oracle reads the element from the XML directly, as the parity oracle already does for
  stored late finishes. Adding a `stored_free_float_minutes` field is not needed by any consumer and
  was not added.
