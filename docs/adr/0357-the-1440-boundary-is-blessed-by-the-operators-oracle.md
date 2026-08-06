# ADR-0357 — The 1440 boundary is blessed by the operator's oracle

**Status:** Accepted · **Date:** 2026-08-06 · **Closes:** ADR-0348's documented-not-repaired
`tod + per_day == 1440` residual — the last ADR-0240 Fable 5 Max reserved item.

## Context

ADR-0348 documented that on a midnight-anchored 24-hour calendar (exactly what ADR-0312's
import normalisation produces from a continuous-operations file), a whole-day **finish**
renders at the NEXT day's 00:00 — "end of Friday" reads Saturday 00:00, a non-working date —
and refused to repair it without an oracle: "repairing it means deciding what 'the end of
Friday' should read as … a question with no oracle in the corpus." Measurement this session
confirmed the corpus's `_24h` hard files cannot answer it (per-task 24h calendars anchored at
17:00/09:00, weekend-working — off-boundary), and the start side plus the inverse property
were already correct.

## The oracle

The operator supplied `24Hour_Calendar.mpp` (the Commercial Construction template with a
7-day, 1440-minute "24 Hours" calendar on tasks 17/28/29). Read from its raw MSPDI bytes:

- **MS Project stores the raw instant, wherever it lands**: finishes at `T01:00:00` and
  `T02:00:00`, starts at `T17:00:00`/`T01:00:00`; successor handoffs are instant-contiguous
  (UID 48 finishes `2026-10-03T01:00:00`; UID 49 starts at that exact string). No end-of-day
  beautification exists anywhere in the file.
- **Zero midnight-spelled Start/Finish values** occur — and structurally, the MSPDI datetime
  format has **no representation of "24:00"**: a day-boundary instant can only ever be
  written as the next day's `00:00`.

## Decision

**Current behavior is correct and is now pinned, not repaired.** `offset_to_datetime`'s
`remainder == 0` branch (end-of-day spelling; next-day 00:00 at `per_day == 1440`) is MS
Project's own convention; the intuitive "Friday 23:59" repair would have CREATED a parity
break on the very files it targeted. `tests/engine/test_1440_boundary.py` freezes the
convention — finish at next midnight, start-role rolling per ADR-0348, inverse intact — and
fails loudly (proven by mutating the branch to `per_day - 1`, the exact intuitive repair)
with this citation in hand.

## Consequences

- All three ADR-0240 reserved items are closed (SRA-LEGACY ADR-0353 · V3 ADR-0354/0355 ·
  this). No engine or display code changed here: the unit is a pin plus this record.
- An analyst reading "Sat 00:00" on a 24-hour Mon–Fri schedule sees exactly what MS Project
  shows for the same instant — Law 2 prefers the reference tool's presentation over
  editorial "improvement".

## Deliberately NOT done

- **No 23:59 spelling, no date-clamping** — refuted by the oracle.
- **The oracle file is not committed** — intake additions are the operator's call
  (ADR-0152 posture); this ADR records the decisive readings so the decision survives
  without the binary.
