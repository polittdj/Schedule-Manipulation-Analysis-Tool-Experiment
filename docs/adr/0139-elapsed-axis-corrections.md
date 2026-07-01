# ADR-0139 — Elapsed-duration axis corrections: cap-space float, per-axis conversions

## Status

Accepted. Corrects part of ADR-0131 (the NEW-1 Float-Ratio fix); part of the 2026-07-01 QC audit
remediation (batch R2).

## Context

The parity goldens contain **no elapsed-duration activity and no non-480 calendar**, so a family of
axis-mismatch defects passed the green gate. The 2026-07-01 QC audit confirmed each with live
reproductions (verified three ways):

- **D2 (HIGH).** The CPM backward pass reconstructed an elapsed task's late start by mapping its
  late-finish *offset* back to a wall-clock instant — a lossy mapping across non-working time (a
  Sunday-08:00 finish reads back as Friday 17:00). Subtracting the wall-clock duration from the
  wrong instant fabricated **negative float** for every weekend/holiday-spanning elapsed activity:
  a lone unconstrained 2-eday task starting Friday reported TF = −480, cascading into false DCMA-07
  Negative Float FAILs, CPLI dragged to 0, and poisoned critical-path/float-band/manipulation
  outputs on any real `.mpp` carrying edays.
- **D3 (HIGH).** DCMA-12 injected its 100-day test delay as *working* minutes into
  `duration_minutes` — which for an elapsed task is *wall-clock* minutes — so the finish moved by
  the wrong amount and a structurally perfect schedule FAILed the Critical Path Test.
- **D7 (MEDIUM).** The NEW-1 fix (ADR-0131) put **both** Float-Ratio terms on the 1440 axis for
  elapsed activities, but total float — stored or recomputed — is always **working** minutes; the
  float term was deflated 3× (8-h calendar) and every elapsed activity's ratio understated (the
  pinned 0.33 expectation was itself wrong; the displayed-days value is 1.0).
- **D13 (MEDIUM).** `recommendations._quantify` converted float→days with a fixed 480, ignoring
  `schedule.calendar.working_minutes_per_day` — 25% error in cited float/impact days and the risk
  matrix on a 10-hour calendar.
- **D21 (LOW).** `margin.py` displayed an elapsed margin task's duration on the working axis
  ("5 edays" → 15.0 days).

## Decision

1. **Cap-space float for elapsed tasks (`engine/cpm.py`).** In the backward pass, an elapsed
   task's slack is computed directly as `min(finish_caps − EF, start_caps − ES)` — every operand a
   working-grid offset of the same event class, so the difference *is* the float. The wall-clock
   instant round-trip is gone from the float path; late start/finish are the early dates shifted
   by the slack (LS−ES == LF−EF always). Genuine constraint violations still go negative (a cap
   below EF). *Known quantization:* elapsed float is measured in working time, so a violation
   that falls entirely inside non-working time (finish Sunday 08:00 vs cap Friday 17:00) reads 0 —
   an approximation, never a fabrication.
2. **Own-axis delay injection in DCMA-12 (`engine/metrics/dcma14.py`).** When the tested critical
   activity is elapsed, the 100-day delay is injected as `100 × 1440` wall-clock minutes and the
   expected working-offset movement of its finish is computed exactly from its start instant
   (a working-grid point — unambiguous). The non-elapsed path is byte-identical to before.
3. **Per-axis Float Ratio (`engine/metrics/float_ratio.py`).** Each term converts to days on its
   own axis: total float ÷ `per_day` (always working minutes), remaining duration ÷ 1440 only when
   elapsed. This is the displayed-days ratio an analyst reads in MSP ("1 day" float over "1 eday"
   remaining = 1.0). The NEW-1 test pin (0.33) is corrected to 1.0. Flagged for re-confirmation
   against the operator's Fuse export when reference artifacts are deposited.
4. **Calendar-aware day conversion in recommendations** (`_quantify` divides by the schedule
   calendar's minutes-per-day; 480 remains only the degenerate-calendar fallback) and **own-axis
   margin display** (`margin.py` divides an elapsed margin task by 1440).
5. **Regression suite** `tests/engine/test_elapsed_axis_regressions.py`: the audit's minimal
   reproductions for D2 (fabrication gone, chain + Monday controls, genuine negative preserved),
   D3 (elapsed PASS, weekend-spanning included), D13 (exact −1.0 on a 600-min calendar), D21.

## Consequences

- Real `.mpp` files carrying elapsed durations no longer fabricate negative float, false DCMA-07/
  DCMA-12/CPLI failures, or 3×-understated Float Ratios — the fabrication class the audit rated
  most dangerous for a testimony tool.
- **No golden parity number moves**: the goldens contain no elapsed activity and use the 480
  calendar, so every changed code path is outside the pinned population (full gate + parity green).
- The elapsed blind spot in the golden population is now covered by a dedicated regression file;
  the broader golden-diversity gap (an elapsed + non-480 *golden file*) remains the operator-gated
  accuracy-ceiling work.

## Alternatives considered

- **Track true wall-clock instants for elapsed tasks through the whole backward pass.** More
  faithful in principle, but it threads a second time axis through every successor interaction for
  marginal gain; cap-space float is exact for the caps the network actually imposes.
- **Clamp TF to ≥ 0 for unconstrained elapsed tasks.** Rejected: masks genuine negatives and
  treats the symptom.
- **Skip elapsed targets in DCMA-12.** Rejected: silently narrows the test population; computing
  the exact expected movement keeps every target testable.
