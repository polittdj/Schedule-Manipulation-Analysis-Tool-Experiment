# CC-FINDINGS — the files the outside auditor never opened

**Date:** 2026-07-29
**Commit:** `9a1e5601746c3d5fc1f1ca97c9a12bd517a6fca1`
**Scope requested:** `engine/cpm.py`, `engine/metrics/dcma14.py`, `engine/metrics/evm.py`,
`engine/driving_slack.py`, `engine/manipulation.py` — hunting silent defaults, unit mixing,
sign/direction errors, and divide-by-zero returning a plausible value.

Every finding below was executed. Where a file is clean on a hypothesis, that is reported as a clean
result rather than padded into a finding — reporting correct behaviour as a bug is worse than
finding nothing.

| ID | Severity | File | Class | Executed |
|---|---|---|---|---|
| CC-01 | **HIGH** | `engine/cpm.py:255-281` | unit-mixing / boundary | yes |
| CC-02 | **HIGH** | `engine/manipulation.py:457,462,520,525` | silent-default | yes |
| CC-03 | clean | `engine/metrics/evm.py` | divide-by-zero — **correctly handled** | yes |
| CC-04 | clean | `engine/metrics/dcma14.py:474-494` | empty denominator — **correctly handled** | yes |
| CC-05 | **MEDIUM** | `engine/driving_slack.py:166-172` | sign-direction | yes |

---

## CC-01 — `offset_to_datetime` returns dates on non-working days, contradicting its own contract

**Severity: HIGH** (74 call sites; reaches every displayed CPM date)
**Location:** `engine/cpm.py:255-281`
**Class:** boundary / unit-mixing (a working-minute remainder added to a wall-clock date)
**Proof:** `/tmp/audit-verify/lead_cc01.py`, `/tmp/audit-verify/lead_v6_adjudicate.py`

### The contract it breaks

```
Convert a non-negative working-minute offset to a wall-clock datetime.
`start` is assumed to sit at the beginning of a working day. Each working
weekday contributes `calendar.working_minutes_per_day` contiguous minutes;
weekends and holidays are skipped.
```
— `cpm.py:256-261`

### The defect

`_advance_working_days` correctly returns a working **date**. The final two lines then add the
intraday remainder in **minutes**:

```python
target_date = _advance_working_days(day.date(), advance, calendar)
day += dt.timedelta(days=(target_date - day.date()).days)  # preserve time-of-day exactly
return day + dt.timedelta(minutes=intraday)
```

Nothing re-checks the result. When `time_of_day + intraday` crosses midnight, the returned datetime
lands on the **next calendar day**, which may be a weekend or holiday. The docstring's stated
precondition ("`start` is assumed to sit at the beginning of a working day") is never enforced or
validated — `Schedule.project_start` is an arbitrary datetime taken from the source file.

### Executed proof

Standard 8h Mon-Fri calendar, project start Friday 2026-01-09:

```
project_start          offset_to_datetime(ps,480)   weekday   working?
2026-01-09 08:00:00    2026-01-09 16:00:00          Fri       True
2026-01-09 12:00:00    2026-01-09 20:00:00          Fri       True
2026-01-09 16:00:00    2026-01-10 00:00:00          Sat       False
2026-01-09 17:00:00    2026-01-10 01:00:00          Sat       False
2026-01-09 20:00:00    2026-01-10 04:00:00          Sat       False
2026-01-09 23:00:00    2026-01-10 07:00:00          Sat       False

--- systematic sweep: how many (start-hour, offset) pairs land NON-working? ---
non-working landings: 8 / 120
```

End-to-end through `compute_cpm` on a three-activity FS chain, 8h Mon-Fri, 17:00 project start:

```
activity     early start            day  ok     early finish           day  ok
Activity 1   2026-01-09 17:00:00    Fri  True   2026-01-10 01:00:00    Sat  False
Activity 2   2026-01-10 01:00:00    Sat  False  2026-01-13 01:00:00    Tue  True
Activity 3   2026-01-13 01:00:00    Tue  True   2026-01-14 01:00:00    Wed  True

2 of 6 activity dates land on a NON-WORKING day of the schedule's own calendar.
```

Note the dates are also at **01:00** — outside any 8-hour working day. An exhibit stating "Activity 2
starts Saturday 10 January at 01:00" on a Monday–Friday 8-hour project is facially indefensible in
cross-examination, and the tool produced it from correct working-minute arithmetic.

### Reachability

The condition is `start_time_of_day + working_minutes_per_day > 24h`:

* Default 8h calendar → any project start at or after **16:00**.
* **20h two-shift calendar → any start after 04:00** — i.e. effectively always. Verified in
  VALIDATION V6 case (b): `wmpd=1200`, ordinary 08:00 Friday start, landed Saturday.
* **24h continuous calendar → always.** VALIDATION V6 case (c).

Two-shift and continuous calendars are ordinary in tunnelling, marine, mining and plant-turnaround
schedules, so this is not an exotic input.

### Downstream

`offset_to_datetime` has **74 call sites**. Beyond the display of early start / early finish /
project finish, it is the mechanism behind VALIDATION V6: `engine/resources.py:138-139` derives a
task's span from it, the span filters to zero working days, `wdays … or [sd]` dumps the load onto a
non-working day, capacity for that bucket computes to 0, and `over_allocated`'s `capacity_minutes > 0`
guard then reports `False`. **CC-01 is the root cause of the V6 hard case.**

---

## CC-02 — a missing optional cost/work field becomes a HIGH-severity accusation of concealment

**Severity: HIGH** (the highest-stakes instance of the falsy-zero idiom in the repository)
**Location:** `engine/manipulation.py:457`, `:462`, `:520`, `:525`
**Class:** silent-default
**Proof:** `/tmp/audit-verify/lead_cc02.py`

### The code

```python
if (cur.cost or 0.0) > (prior.cost or 0.0):                            # :457
ac = td.changed("actual_cost")
if ac is not None and (cur.actual_cost or 0.0) < (prior.actual_cost or 0.0):   # :462
...
if (cur.work_minutes or 0) > (prior.work_minutes or 0):                # :520
if aw is not None and (cur.actual_work_minutes or 0) < (prior.actual_work_minutes or 0):  # :525
```

All four fields are `X | None` with `None` meaning **"the source did not provide it"** —
`model/task.py:77-78` (`work_minutes`, `actual_work_minutes`) and `:134-135` (`cost`,
`actual_cost`). This is stated as a project law in `CLAUDE.md`: *"Optional date/cost fields default
to `None` meaning 'the source didn't provide it' — never assume 0."*

`or 0.0` assumes 0.

### Executed proof

Scenario: the prior export carried Actual Cost and Actual Work; the current export simply does not
carry those columns. Nothing was rolled back.

```
  [HIGH] MANIP_ACTUAL_COST_ERASED
      title : 1 activities had recorded actual cost reduced
      detail: Actual (recorded) cost DECREASED since the prior version — recorded expenditure should only grow as work is performed; a reduction rewrites the cost h
      action: Investigate each actual-cost reduction; confirm a documented accounting correction, not expenditure being hidden or move

  [HIGH] MANIP_ACTUAL_WORK_ERASED
      title : 1 activities had recorded actual work reduced
      detail: Actual (performed) work DECREASED since the prior version — performed effort should only accumulate; a reduction un-records progress history.
      action: Investigate each actual-work reduction; confirm a documented statusing correction, not progress being rolled back to re-

  [MEDIUM] MANIP_COST_CHANGE
      title : 1 activities had their total cost changed
  [MEDIUM] MANIP_WORK_CHANGE
      title : 1 incomplete activities had their total work changed
```

**Four findings, two of them HIGH**, from a schedule where nothing was manipulated.

### Why this is the worst instance of the idiom

The false positive is **indistinguishable from the true positive**. The control — a genuine
5000 → 3000 actual-cost rollback, which the tool *should* flag — produces the identical output:

```
=== CONTROL: a REAL rollback (5000 -> 3000), which SHOULD be flagged ===
  [HIGH] MANIP_ACTUAL_COST_ERASED: 1 activities had recorded actual cost reduced
  [HIGH] MANIP_ACTUAL_WORK_ERASED: 1 activities had recorded actual work reduced
```

Same `metric_id`, same title, same severity, same citation. An analyst reading the report cannot
tell an export-settings difference from evidence of concealment. The finding text instructs them to
*"confirm a documented accounting correction, **not expenditure being hidden or moved**"* — an
accusation of intent, generated by an absent column.

This sits directly against the module's own stated discipline (`manipulation.py:26`): *"A statement
is only ever made with the underlying delta attached."* Here the underlying delta is fabricated.

### Reachability

Very high, and routine in forensic work specifically:

* successive updates exported with different column sets or export templates;
* a version series that crosses tools (P6 `.xer` → MS Project `.mpp`), where cost columns are
  commonly absent on one side;
* a contractor who stops cost-loading mid-project.

Version series assembled from mixed sources are the normal case in a delay claim, not the exception.

**Control that behaves correctly:** when the field is absent in *both* versions, `td.changed(...)`
is `None` and nothing fires (`findings: none`). The defect requires present-then-absent, which is
exactly the export-settings-changed case.

---

## CC-03 — `engine/metrics/evm.py` is CLEAN on divide-by-zero (verified, not assumed)

I tested the obvious hypothesis — that SPI/CPI return a plausible `1.0` when the denominator is zero
— and it is **false**. The module handles it correctly:

```python
out["spi"] = _index("spi", "SPI", bcwp / bcws if bcws else None, 1.0)      # :282
out["cpi"] = _index("cpi", "CPI", bcwp / acwp if acwp else None, 1.0)      # :283
tcpi_denom = total_budget - acwp
out["tcpi"] = _index("tcpi", "TCPI", (total_budget - bcwp) / tcpi_denom if tcpi_denom else None, 1.0)
```

A zero denominator yields `None`, and there is a dedicated `_na_index` (`:259`) for the
not-computable case. This is exactly the Law-2 behaviour ("NA reads '—', never a placeholder 0").

The two remaining unguarded-looking divisions are both guarded upstream:

* `EarnedSchedule.spi_t` (`:365-366`) is `es_minutes / at_minutes` with no local guard, **but**
  `at_minutes` can only be set by `earned_schedule`, which returns `None` at `:378-379` when
  `status_off is None or status_off <= 0`. `at_minutes` is therefore always > 0. SAFE, guard named.
* `_spi_t_acumen`'s `baseline_span / actual_span` (`:461`) is preceded by
  `if actual_span <= 0: continue` (`:457-458`), and the whole result is `_na_index`-ed by
  `if not ratios:` (`:467-468`). SAFE, guard named.

**No finding.**

---

## CC-04 — `engine/metrics/dcma14.py` is CLEAN on the empty-denominator hypothesis (verified)

The highest-value Law-2 hypothesis for DCMA-14 is that an empty population yields a fabricated `0%`
that reads as a PASS. It does not. `_r` (`:474-494`):

```python
value = percent(count, population)
status = (
    CheckStatus.NOT_APPLICABLE if population == 0 else evaluate(value, threshold, direction)
)
```

with a docstring that states the reasoning explicitly:

```
An empty population is NOT_APPLICABLE, never a fabricated `0%` — a GE-direction
check (FS Relationships ≥ 90%) would otherwise FAIL with zero offenders on a
schedule with no logic links at all (an offender-less finding then violates the §6
citation contract downstream).
```

This is the correct behaviour and it is the behaviour the web presentation layer's `or 1` divisor
guards do *not* follow — see the systemic note in `FALSY-ZERO-SWEEP-20260729.md`. The inconsistency
is between layers; the engine layer is right.

**No finding.**

---

## CC-05 — sub-day **negative** slack reads as a full day behind (the docstring says it reads 0)

**Severity: MEDIUM** — needs a reference decision before it is called a bug outright (see caveat)
**Location:** `engine/driving_slack.py:166-172`
**Class:** sign-direction
**Proof:** `/tmp/audit-verify/lead_cc05.py`

### The code and its stated contract

```python
def _whole_days(slack_minutes: int, minutes_per_day: int) -> int:
    """Slack in whole working days, floored — the day-granular axis SSI displays.

    Sub-day slack (time-of-day raggedness in real stored dates) reads 0 days; the curated
    goldens' slacks are exact day multiples, so their values are unchanged (parity-safe).
    """
    return slack_minutes // minutes_per_day
```

Python's `//` **floors** (rounds toward −∞), so the docstring's promise holds only on the positive
side.

### Executed proof

```
 slack_minutes   _whole_days(x,480)   reading
           479                    0   0 day(s)  <-- sub-day POSITIVE reads 0 (matches docstring)
             1                    0   0 day(s)  <-- sub-day POSITIVE reads 0 (matches docstring)
             0                    0   0 day(s)
            -1                   -1   -1 day(s)  <-- sub-day NEGATIVE reads a FULL DAY BEHIND (contradicts docstring)
          -479                   -1   -1 day(s)  <-- sub-day NEGATIVE reads a FULL DAY BEHIND (contradicts docstring)
          -480                   -1   -1 day(s)
          -481                   -2   -2 day(s)
```

**+479 minutes of float reads 0 days; −479 minutes reads −1 day.** A task one minute behind schedule
is reported as a full day behind.

This matters precisely where the docstring says the input comes from — *"time-of-day raggedness in
real stored dates"*. Negative slack is the figure a delay analysis is built on, and the direction of
the error is to **overstate** the delay.

The `PathTier` banding is unaffected in this range (all three negative cases classify `DRIVING`), so
the impact is on the **displayed day figure**, not the tier.

### Caveat — this needs a reference check, not a unilateral fix

The docstring anchors the behaviour to *"the day-granular axis SSI displays"*, and notes the curated
goldens carry exact day multiples, so parity cannot distinguish floor from truncate-toward-zero.
**I could not verify which SSI actually does** — that requires the reference tool. Two possibilities:

* SSI truncates toward zero → the code is wrong and the docstring is right.
* SSI floors → the code is right and the docstring's "reads 0 days" sentence is wrong.

Either way there is a real documented-vs-actual mismatch on a testimony-relevant figure. Resolving it
is a reference-comparison task (Fable 5 Max / an Acumen-SSI export check), not a patch.

---

## Coverage and honest limits

* `engine/cpm.py` — read in full around the date/offset machinery, the forward/backward pass, and
  the calendar helpers. CC-01 found and executed. I did **not** exhaustively re-derive every
  constraint type (SNET/SNLT/MSO/FNLT/ALAP) against MS Project semantics; that is a Fable-5-Max
  deep dive in its own right and the parity gate covers the golden files.
* `engine/manipulation.py` — read in full. CC-02 found and executed. The same `or 0`/`or 0.0` idiom
  appears at `:618` (`assignment_change_rows`) on `int | None` remaining-work; I did not execute
  that path, so it is **not** reported as a finding — it is a candidate with the same shape.
* `engine/metrics/evm.py` — read in full; clean on the hypotheses tested (CC-03).
* `engine/metrics/dcma14.py` — `_r` and the check populations read; clean on the empty-denominator
  hypothesis (CC-04). I did **not** verify every one of the 14 checks' `>=`/`>` threshold boundaries
  against the `.aft` library, nor the checks that build a `MetricResult` directly instead of through
  `_r` (DCMA-02 at `:142-148`, and the BEI/CPLI paths) — those bypass the `NOT_APPLICABLE` guard and
  are the right next target.
* `engine/driving_slack.py` — read (373 lines) with focus on the slack arithmetic and the day
  conversion. CC-05 found and executed. I did **not** verify the driving-predecessor selection rule
  or the FS/SS/FF/SF `free` computations (`:333-352`) against SSI's reference output — that needs
  the reference tool, not a script.
