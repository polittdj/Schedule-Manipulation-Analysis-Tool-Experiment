# ADR-0010: M5 CPM engine — working-minute axis, constraint model, critical definition

- **Status:** Accepted
- **Date:** 2026-06-08 (session A7 — Phase 2 build, milestone M5)
- **Relates to:** §6.C (CPM, total/free float), §6.B parity, §3 (units/determinism)
- **Builds on:** ADR-0005 (determinism), ADR-0004 (pure-Python engine); studies prior build `0324ba4`

## Context
M5 is the first engine milestone and the fidelity core the parity gates (M6-M9) build on. Recon of
the committed golden fixtures showed the real schedules use **only** ASAP + SNET constraints, FS links
(+1 FF), positive lags, and the standard 8h/Mon-Fri calendar — no MSO/MFO/ALAP/SS/SF/leads/holidays
and no named calendars. So parity rests on the ASAP/SNET/FS/FF/lag path.

## Decision
1. **Integer working-minute axis** (offset from `Schedule.project_start`). Exact, hand-verifiable, no
   binary-float drift (ADR-0005); removes end-of-day/next-day boundary bugs. Float is converted to
   **days** only at the presentation boundary (`model.units`, deterministic `Decimal`).
2. **Constraint model** (MS Project "honor constraint dates"): `SNET`/`FNET` → forward ES floor;
   `SNLT`/`FNLT` → backward LF cap; `MSO`/`MFO` → **pin** (forward pin of ES/EF + matching LF cap, so
   a pinned activity carries 0 or, under successor pressure, negative float); task `deadline` → LF cap.
   This *improves on* the prior build (which refused MSO/MFO): we honor them per the M5 plan.
   `ALAP` (not in the plan's required set; backward-pass-driven, subtle) and any constraint missing its
   date are **refused** with `CPMError` — fail loud, never mis-schedule (Law 2).
   - *Known limitations (defined model pending live MS Project validation, "H-CONSTRAINT-DATETIME"):*
     a constraint datetime maps to an offset at **working-day granularity + a clamped intraday term**;
     an MSO/MFO pin does not auto-detect a predecessor that would push past the pin. Neither path is
     exercised by the parity schedules; revisit if a future schedule needs minute-level or
     conflict-detecting semantics.
3. **Two distinct "critical" notions** (the key parity finding):
   - **pure CPM** `is_critical = total_float <= 0` — a property of the network logic, on `TaskTiming`;
   - the **Acumen "Critical" metric** = `total_float <= 0` **and** `percent_complete < 100` — a
     finished activity is no forward schedule risk. This filter lives in `float_analysis`
     (`critical_incomplete_count`), not in the CPM core.
   Validated on the golden fixtures: raw critical **43 / 37** (P2/P5); incomplete-critical **41 / 37**
   == Acumen `PARITY-TARGETS` "Critical" **41 / 37** exactly. Network finish 391 / 462 working days.
4. **Calendar:** the model's single-block 8h/Mon-Fri `Calendar` is sufficient — the schedules carry no
   named calendars or holidays. Parsing per-file/named calendars from MSPDI is **deferred** until a
   schedule needs it (no current parity dependency).
5. **`free_float`** is exact for FS; for SS/FF/SF it is the slack at the link's governing event
   (reference tools vary on non-FS free float). **`total_float`** — the primary forensic signal — is
   exact for every link type. `required_finish_offset` lets M6 drive the backward pass to a target.

## Consequences
- §6.C CPM + total/free float is implemented, tested (100% line+branch), and validated against the
  Acumen critical counts. M6 (driving slack to a target UID) reuses `compute_cpm(required_finish_offset=…)`.
- The float→days boundary is deterministic; parity assertions are reproducible bit-for-bit.
- The constraint/calendar limitations are documented and currently dormant; if M7-M9 surface a delta
  traceable to them, it is a tracked defect to drive to zero (ADR-0005 §5), not a silent rounding.
