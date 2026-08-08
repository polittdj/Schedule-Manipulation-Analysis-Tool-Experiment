# ADR-0366 — sub-day change effects carry exact minutes; the page renders a signed "<1 wd", never "no effect"

**Status:** Accepted · **Date:** 2026-08-08 · **Extends:** ADR-0162 (per-change counterfactual effects)

## Context

The 2026-08-07 adversarial read-only audit (F1/F7) caught a Law 2 lie in the change-effects
family. `engine/change_effects.py` converted every counterfactual finish movement to whole
working days with `round(minutes / per_day)`:

| true effect (min, 480/day) | `round()` days | page rendered |
| --- | --- | --- |
| +60 | 0 | "no effect" |
| +235 | 0 | "no effect" |
| **+240 (exactly half a day)** | **0 (round-half-even)** | "no effect" |
| +241 | 1 | "+1 wd" |

A real, engine-measured 240-minute hidden slip rendered as "no effect" on /integrity, the
Ask-the-AI fact base stated "reverting it does not move the finish (no effect on this target)",
and NO fractional-day test existed. Two labels had the same defect class by floor division: the
duration-restore label rendered a 240→60-min cut as "cut 0→0 wd", and a sub-day link lag
rendered "(lag +0d)".

## Decision

1. **Keep exact minutes internally.** `ChangeEffect` gains `target_finish_delta_minutes` /
   `project_finish_delta_minutes`, `ChangeEffectsReport` gains the two aggregate counterparts.
   The int-day fields keep their rounded meaning unchanged (every existing consumer and pin is
   untouched; the legacy rounding — including 240 → 0 via round-half-even — is now itself
   pinned by test).
2. **Render sub-day truthfully.** `/integrity` reads the minutes: a nonzero-minutes effect that
   rounds to 0 wd renders a signed `+<1 wd` / `-<1 wd` (tone by the minutes' sign); the
   aggregate line renders `+<1 working day` the same way; rows sort by exact minutes; the
   artifact "N of M have no effect" count is by minutes. A true zero still reads "no effect"
   and whole-day figures keep their exact legacy text.
3. **Labels state sub-day durations exactly.** A fractional side renders 2-dp days with the
   exact minutes riding along ("cut 0.12→0.5 wd (60→240 min)"); whole-day pairs are
   byte-identical to before. Same treatment for sub-day link lags ("(lag +0.5d / +240 min)").
4. The qa fact states "reverting it moves the finish less than one working day LATER/EARLIER"
   for the sub-day case; "no effect" is reserved for a true zero.

## Verification

`tests/engine/test_change_effects.py` pins the (60/235/240/241, ±) matrix — minutes exact, day
fields at legacy rounding — and both labels; `tests/web/test_subday_effect_display.py` renders
`_integrity_body` on synthetic pairs (signed `<1 wd`, negative twin, true-zero twin, legacy
whole-day twin, qa fact + twin). Proven able to fail by four caller-level reverts: minutes
population removed → 5 named failures; labels floor-divide → 3; pristine render → 2; pristine
qa → 1. Twins stayed green in every round. The golden-pair pins ("+21 wd", "33 of 33 have no
effect") hold unchanged — no Hard_File artifact carries a sub-day effect.

## Deliberately NOT done

- The day-rounding itself is unchanged — parity consumers compare whole days (ADR-0280) and
  every existing figure is byte-identical.
- The qa AGGREGATE fact still states the rounded `{:+d} working day(s)` (a labeled rounded
  figure, not a categorical "no effect" lie); only the categorical per-change wording changed.
- Sub-day NEGATIVE FLOAT semantics remain oracle-gated (the Negative-Float O1 gap — the AFT
  has no formula; an operator Acumen run on a crafted sub-day-negative-float schedule closes
  it). Nothing here touches float.
