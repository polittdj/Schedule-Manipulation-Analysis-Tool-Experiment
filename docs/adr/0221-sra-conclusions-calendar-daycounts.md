# ADR-0221 — SRA-conclusion day-counts convert on the schedule's calendar (audit M1)

## Status

Accepted. Fourth theme of the AUDIT-2026-07-13 remediation (PRs 1-3: #341, #353, #354). Engine-fidelity
fix — parity-safe (the golden fixtures are 8h/day, so their numbers do not move).

## Context

`engine/sra_conclusions.py` turns a Monte-Carlo SRA result into Hulett-style conclusion cards. Two of
them quote a duration in **working days**: the **Contingency** card (`P80 − deterministic finish`) and
the **Predictability** card (the `P10 → P90` window). Both converted working-**minute** offsets to days
through `_wd()`, which divided by a hard-coded `_MPD = 480`.

On any non-8-hour calendar that is wrong. On a 600-min/day (10-hour) file a true **20**-working-day
P10→P90 window was reported as **25** (+25%). The wrong number backs both the finding sentence and its
evidence pairs, so it passes the "every digit appears in evidence" fidelity gate and reads as
authoritative — the worst kind of error for a testimony tool. The identical bug was already found and
fixed in `recommendations.py` (QC audit D13, which converts on the schedule calendar with 480 only as a
0-minute fallback), and the SRA page's own discrete-risk day impacts already use the real working-minutes
/day — so two "working-days" families in one card disagreed.

## Decision

Thread the schedule's real working-minutes/day into the day-count conversion, mirroring the D13 fix:

- `_wd(minutes, wmpd)` now takes the calendar's working-minutes/day.
- `_contingency(...)` and `_spread(...)` take and forward `wmpd`.
- `conclusions_from_sra` and `conclusions_from_ssi` both compute
  `wmpd = sch.calendar.working_minutes_per_day or _MPD` from the `sch` they already receive and pass it
  through. `_MPD = 480` remains only the fallback for a degenerate 0-minute calendar.

The dates and percentiles were already correct (they come straight off the result); only the
minutes→days rounding changed basis.

## Consequences

- Contingency and Predictability day-counts are now correct on any calendar and agree with the SRA
  page's discrete-risk day impacts and with `recommendations.py`.
- Parity-safe: the committed goldens are 8h/day, so `wmpd == 480` and every validated number is
  unchanged. Only a non-8h schedule sees different (now-correct) day-counts.
- Tests (`tests/engine/test_sra_conclusions.py`): a unit test pins the audit's exact example (a
  20-working-day window reads "20 working days" at 600 min/day, "25" at the old fixed 480), and an
  end-to-end test on a 600-min/day schedule proves `conclusions_from_sra` threads the calendar (the
  Predictability window uses the 600 basis, not 480, on a spread where the two genuinely disagree).
