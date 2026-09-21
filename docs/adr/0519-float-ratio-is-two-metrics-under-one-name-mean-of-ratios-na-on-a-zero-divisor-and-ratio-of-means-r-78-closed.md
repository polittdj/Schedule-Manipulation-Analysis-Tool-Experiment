# ADR-0519 — Acumen Fuse's `Float Ratio™` is TWO metrics under one name: the mean-of-ratios (N/A whenever a Remaining Duration field is 0) and the ratio-of-means (the zeros kept in both sums), both on the whole-day FIELDS and both presented half AWAY from zero (R-78 CLOSED)

**Status:** Accepted · **Date:** 2026-09-21 · **Extends:** ADR-0516 (R-75, the Total Float field's
divisor), ADR-0518 (R-76, the duration fields), ADR-0467 (MF-08, `round_half_up`) · **Amends:**
ADR-0515's `value_dp` family premise for two sites · **Closes:** audit row **R-78**

## Context

R-78 registered one claim and one remedy. Both were tested before the first edit (QC-3). The claim
held and reached further than the row; the remedy fell.

### 1. The row's premise — half right

The row said Fuse's `Float Ratio™` is `AVERAGE(TotalFloat/RemainingDuration)` over the whole-day
fields, N/A on a zero divisor, **and that the aggregate form has no oracle** ("state it UNVERIFIED
or hold it, do not move it by analogy").

Parsing both committed `.aft` snapshots refutes the second half. `Float Ratio™` is defined under
**both** Bible forms:

| name in the `.aft` | formula | GUIDs |
| --- | --- | --- |
| `Float Ratio™` | `AVERAGE(TotalFloat/RemainingDuration)` | `a536d1a4` |
| `Float Ratio™` | `AVERAGE(TotalFloat)/AVERAGE(RemainingDuration)` | `8aec0857`, `697a1c84`, `dc1bd267`, `838991ea`, `9c556fbd` |
| `CP - Float Ratio™` | `AVERAGE(TotalFloat)/AVERAGE(RemainingDuration)` | `40d58adf`, `31139880`, `823e7d00` |
| `Near CP - Float Ratio™` | `average(TotalFloat/RemainingDuration)` | `af20306e` |

…and the operator's workbooks print **both under that one tile name**, decided by which metric
group the workbook loaded. The same save reads two different numbers:

| ribbon | `Hard_File_updated3` (rev 5) | 24-hour Hard_File | reproduces as |
| --- | --- | --- | --- |
| AlltheProjects (Quick Add) | **-10.94** | **N/A** | mean-of-ratios (-10.9446) |
| 7/15 Analyst (`HA296F~1.XLS`) | **-8.01** | **-3.58** | ratio-of-means (-8.0115 / -3.5758) |
| update2 vs update3 | — (see residual) | — | ratio-of-means (`Hard_File_updated2` 5.74 = 5.7361) |

So the engine's two results map onto Fuse's two forms, and **both** are oracle-backed. The row's
"no oracle" was the same mistake R-76 paid for: the oracle was in the other workbook.

### 2. Measured

Both terms are the whole-day FIELDS of R-75 / R-76 — `acumen_total_float_field` and
`acumen_duration_field`, each on `activity_day_minutes` (1440 for an elapsed duration, else the
task's own calendar's day, else the project's).

| population | result |
| --- | --- |
| every AlltheProjects ribbon label, from **Fuse's own displayed cells** | **39 / 39** reproduce under the shipped presentation (37 / 39 under half-to-even — the 2 misses ARE the rounding tie, §4) |
| every AlltheProjects label mapped to a committed save, from the **ENGINE** | **19 / 19** — 9 numeric to 4 dp, 10 N/A |
| the ratio-of-means tiles (Analyst ×2, update2vs3 ×1) from the ENGINE | **3 / 3** |
| committed schedule fixtures re-scored | 30 scored, **16 moved**, N/A 1 → 10 |

Numeric tiles reproduced: `Hard_File_updated3` -10.9446 → -10.94 · `Project2` 14.0076 → 14.01 ·
`Project5_TAMPERED` 22.0173 → 22.02 · `Jacked Up Schedule 1` 0.7678 → 0.77 · `Jacked up Schedule 2`
0.2667 → 0.27 · and the ratio-of-means -8.0115 → -8.01, -3.5758 → -3.58, 5.7361 → 5.74.

**The N/A belongs to the mean-of-ratios form ALONE, and that is measured, not reasoned.** A zero
Remaining Duration field makes one per-activity ratio an error and `AVERAGE` propagates it. The
ratio-of-means has no per-activity division to fail, so it keeps the zero-remaining activities in
**both** sums. The 24-hour Hard_File is the discriminator: four of its fourteen scored activities
carry a zero field; keeping them prints the tile's **-3.58**, dropping them prints **-9.58**, and
the mean-of-ratios tile for the same save prints **N/A**.

Refuted by name: the ratio-of-means as the Quick-Add tile (-8.01 ≠ -10.94) · the mean-of-ratios as
the Analyst tile (N/A ≠ -3.58) · the engine's former MINUTE axis (-11.85 for -10.94; 119.61 / 3.98 /
3.21 where Fuse reads N/A) · the project day as the divisor · skipping a zero divisor.

### 3. The row's prescribed remedy — REFUTED

R-78 flagged a real trap and prescribed the wrong fix. `engine/trend.py` decides "no value" with
`primary.value if primary.population else None`, so an N/A that kept its real population plots a
**fabricated 0.0** and feeds a real-looking delta (probe, red-first on the pristine tree:
`values (0.0, 0.0)`, `deltas (None, 0.0)`, `populations (945, 945)`). The row said to move that
test to the **status**. That would blank the whole chart: `compute_float_ratio` returns
`NOT_APPLICABLE` **even when it returns a figure**, because the metric is informational and carries
no threshold. The status field is already spent.

The carrier is therefore the repo's existing `_na()` convention — count 0, population 0, value 0.0 —
which every consumer already reads: `web/standards.py::_standards_value_cell` keys on
`population > 0` and says so in a comment, `engine/trend.py` emits `None`, `web/trend.py` carries
the `None` straight through and its delta guard is already None-safe on both sides.
`engine/trend.py`, `web/trend.py`, `web/standards.py` and `static/trend.js` are **unchanged**; the
invariant is pinned instead, and the mutation that keeps the population is red by name.

### 4. A rounding site fell out of it

ADR-0515 left the `value_dp` family on Python's half-to-even because **no reference display was
known at that precision**. For this metric there is one. The `.aft` declares
`FormulaFormat='{0:N}'` (two decimals) for every `Float Ratio™` entry — where a sibling ribbon
metric with `FormulaFormat=''` writes its value raw (`0.045833333333`) — and the ribbon's population
contains exactly **one** tie: `TP4_DataCenter_v1`'s mean is exactly **5/8**, and Fuse **writes
0.63** into the cell (not 0.625 under a 2-dp number format — the workbook's stored value is 0.63).
Half-to-even writes 0.62. The committed `TP4_DataCenter_v1.xml` fixture lands on the same exact
5/8 in the engine, so this was a live parity miss, not a hypothetical.

*Why* .NET's `{0:N}` breaks that tie away from zero is an explanation this session could not verify
from a source it trusts; the measurement stands on its own and the format string corroborates that
the tile is rounded in Fuse's code rather than by Excel's display.

## Decision

1. **`float_ratio` is the mean-of-ratios over the whole-day fields**, and reads **N/A for the whole
   schedule** whenever any scored activity's Remaining Duration field is 0.
2. **`float_ratio_aggregate` is the ratio-of-means over the same population and the same fields**,
   with the zero-remaining activities kept in **both** sums; it is N/A only when the remaining sum
   is 0. It is the figure that survives when the primary reads N/A.
3. **N/A is carried by `_na()` (population 0)**, never by an N/A that keeps its population. The
   candidate count is deliberately not reported on an N/A — there is no field left to carry it that
   a consumer would not read as a figure.
4. **Both forms present through `round_half_up`** at 2 dp (MF-08, ADR-0467). This is ADR-0515's
   family-by-family reading applied where a reference display was found, **not** the blanket sweep
   ADR-0515 refused: the two sites leave the `value_dp` family (374 → 372 ledgered,
   `value_dp` 119 → 117, `round_calls_inside_engine_metrics` 44 → 42).
5. **No pure-logic second mode.** `Float Ratio™` is Deltek/NASA's metric, defined by the `.aft`;
   unlike DCMA-14 there is no independent published standard to keep a second reading for, and the
   aggregate form already gives the analyst a figure on a schedule the primary cannot score.
6. **`duration_days_axis` is retired** — Float Ratio was its only consumer.
7. `tests/engine/test_aft_formula_audit.py`'s `float_ratio_aggregate` row is corrected: its NASA
   name is `Float Ratio™` (MATCH), not `CP - Float Ratio™` (VARIANT). The old note's claim — "the
   Bible metric with this exact formula is critical-path-scoped" — is false on both snapshots.

## Consequences

- On a real schedule the primary now reads **—** whenever a single activity has under half a day of
  remaining duration. That is the reference tool's own behaviour (10 of 30 committed fixtures, every
  one of them N/A in Fuse too where Fuse scored it), and the aggregate beside it still prints. The
  help text and the metric dictionary say so.
- Offender sets move: a ratio is now computed from whole-day integers, so the `< 0.1` band captures
  essentially the zero-or-negative-float activities. This is the band on the axis Fuse's own
  thresholds are defined on.
- An elapsed activity's ratio changes shape: its float field is RAW elapsed days while its remaining
  field is WHOLE elapsed days (2,400 minutes over a 7,200-minute remainder is 0.33, not 1.0). The
  measured case is `Jacked Up Schedule 1`'s elapsed UID 20, inside the 0.77 tile.
- **Rendered, not inferred:** `/standards` was served for a schedule whose primary is N/A
  (`EVM1` — a zero Remaining Duration field) and one that scores (`Project2`). The page
  shows `Float Ratio` **—** beside `Float Ratio (aggregate)` **0.06** on the first, and
  **14.01** / **5.58** on the second. No fabricated zero reaches the analyst, and the
  aggregate carries the read where the primary cannot.
- Verified: red first by name on the pristine package (the engine read 8 / 3.21 where Fuse reads
  N/A; the aggregate -9.5 for -8.01); mutation battery **5 / 5 red by name** with the control green —
  raw minutes, skipping a zero divisor, dropping the zeros from the aggregate's sums, keeping the
  population on an N/A (the trend trap), and the project day as the divisor.

## Deliberately NOT done

- **The `-5.59` residual.** The update2-vs-update3 workbook's own `Hard_File_updated3` tile, and its
  `CP - Float Ratio™` twin `-11.9`, reproduce from **no** committed save under **either** form, over
  any population tried, from Fuse's own cells or from the model — although that grid's 110 rows
  reproduce 110 / 110 for both fields from the rev-2 save and the **sibling** snapshot in the same
  workbook reproduces both tiles exactly (5.74 and -1.33). Named in the oracle so it cannot start
  "passing" under a future rule that happens to hit -5.59; unexplained.
- **The Analyst ribbon's `Avg Float` tile** (-11 and -4 where `AVERAGE(TotalFloat field)` is
  -13.4038 and -2.8095). A different metric, measured and left alone.
- **A negative rounding tie.** None occurs in the reference corpus, so half-away-from-zero rather
  than half-toward-positive-infinity is the spreadsheet convention applied, not a measurement —
  **UNVERIFIED**, stated in the module and in the pin.
- **`CP - Float Ratio™` and `Near CP - Float Ratio™`** as engine metrics. Both exist in the `.aft`
  and both have tiles (`-1.33` on `Hard_File_updated2` reproduces from the critical-only
  ratio-of-means); neither is implemented and neither is claimed.
- **The labels whose saves the repo does not hold** (TP4 v1–v5, `Project3`, `Project4`, `EVM2`,
  `Hard_File_updated2` in the Quick-Add ribbon, `SRA Large Test File2`). They are scored from Fuse's
  own displayed cells as evidence for the RULE, never mapped to a fixture as evidence for the
  ENGINE.
- **The rest of the `value_dp` family.** Only the two sites with a measured reference display moved.
