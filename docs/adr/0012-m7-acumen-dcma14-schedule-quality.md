# ADR-0012: M7 Acumen Schedule-Quality + DCMA-14 — definitions, denominators, residuals

- **Status:** Accepted
- **Date:** 2026-06-08 (session A9 — Phase 2 build, milestone M7, continuous A7 sitting)
- **Relates to:** §6.B (Acumen parity), §6.E (DCMA audit), `PARITY-TARGETS.md §A/§B`, `METRICS-CATALOG.md`
- **Builds on:** ADR-0010 (CPM), ADR-0011 (progress-aware dates), ADR-0005 (golden fixtures / deltas)

## Context
M7 is the Acumen parity gate: reproduce the Schedule-Quality summary (§A) and the DCMA-14 ribbon (§B)
for Project2/Project5. The frameworks use **different denominators** and must stay separate.

## Decision
1. **One `MetricResult` per metric** (count/population/measured value/threshold/status/offender UIDs)
   so every figure is auditable and citable (file + UID + task). Float and critical-path inputs come
   from the CPM engine; date checks use the **stored progress-aware dates** (ADR-0011) + `status_date`.
2. **Validated definitions / denominators** (match the golden exactly): Schedule Quality — Missing
   Logic (open-ends, all activities), Logic Density = `2 × links / activities`, Critical =
   incomplete ∧ `tf ≤ 0` over **incomplete** (39%/37%), Insufficient Detail = baseline dur > 44d,
   Merge Hotspot = **≥ 3 predecessors**, Lags/Leads over activities. DCMA-14 — Logic over
   **incomplete**; Lags/SS-FF/SF filtered to an **incomplete successor** (this is why P5 Lags 2→1,
   SS-FF 1→0); Hard = {MSO,MFO,SNLT,FNLT}; High Float `tf > 44d` over incomplete; Missed =
   baselined-due-by-status **not finished on time** (= Completed-Late + Not-Completed) over due
   (18/27, 37/46); **BEI = completed ÷ baselined-due-by-status** (0.74, 0.59 — status-date-driven);
   **CPLI = (path length + project total float) / path length** (= 1 with no imposed deadline);
   critical-path test injects a 100-day delay and checks flow-through.
3. **High Float residual (delta, ADR-0005 §5):** the engine counts **43/40** incomplete high-float
   activities vs Acumen **44/41** (+1). One near-status activity per project carries MS Project's
   progress-aware total float > 44d while the pure-logic CPM gives ≤ 44d (the same effect as ADR-0011).
   Pass/fail (≫ 5%) is unaffected. Documented in `case.json._deltas`; **driven to zero at M9** (when
   progress-aware float is reconciled). The parity test asserts within 1 and that the check still FAILs.
4. **Composite scores deferred:** Acumen's SQ "Score" (88) and DCMA "Score" (57/49) use a proprietary
   Bad/Neutral/Good weighting not published in the exports or the Acumen 8.11 guide. Per-check
   counts/pass-fail are reproduced exactly; the composite scores are an **M9 calibration item**
   (`case.json._scores_deferred`) — never fabricated.

## Consequences
- §6.B Acumen parity is met for all §A metrics and 13/14 DCMA checks exactly; two tracked residuals
  (High Float +1, composite scores) carry to M9. RTM B2/E1 advance.
- `MetricResult` + the golden `case.json` give M9 a parametrized parity suite and M10/M13 the per-check
  offender lists for the DCMA audit and the in-tool metric dictionary.
