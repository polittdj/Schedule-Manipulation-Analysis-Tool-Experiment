# ADR-0011: M6 driving slack — anchored backward pass on progress-aware dates (SSI parity)

- **Status:** Accepted
- **Date:** 2026-06-08 (session A8 — Phase 2 build, milestone M6, continuous A7 sitting)
- **Relates to:** §6.C (driving slack, path trace, user thresholds), §6.B parity, ADR-0005
- **Builds on:** ADR-0010 (CPM); golden `docs/PLAN/SSI-DRIVING-SLACK.md`

## Context
M6 is the **SSI parity gate**: given a target (focus) UniqueID, reproduce the SSI MS Project add-on's
per-task **Driving Slack (days)** exactly for `Project5` / UID 143 (107 driving UniqueIDs).

## Decision
1. **Driving slack via an anchored backward pass.** Trace the focus task's ancestors (transitive
   predecessors — `path_trace.ancestors_of`), anchor `late_finish(focus) = early_finish(focus)`, and
   propagate the latest each ancestor may finish without delaying the focus (reusing the CPM
   `lf_upper_bound` link primitives). `driving_slack = late_finish − early_finish` (working minutes →
   days); 0 ⇒ on the driving path. Only the focus + its ancestors are reported (tasks with no logic
   path to the focus cannot drive it).
2. **Measure against the schedule's STORED, progress-aware dates** (`Task.start`/`finish`), NOT a
   from-scratch CPM forward pass — the key to exact parity. SSI runs *inside* MS Project, which
   schedules using actuals and the data date; the stored dates already reflect that. Verified: with
   pure-logic dates, four completed activities whose actuals ran late (Project5 UID 8/13/14/16)
   computed **+16 days** too much slack (their stored start is 16 working days after the logical
   forward-pass start). Using stored dates → **107/107 exact**. Where a schedule has no stored dates
   (hand-authored/synthetic), fall back to the CPM forward pass.
3. **User-configurable tiers** (§6.C, `PARITY-INPUTS.md`): DRIVING (slack ≤ 0), SECONDARY
   (0 < slack ≤ `secondary_max_days`, default 10), TERTIARY (≤ `tertiary_max_days`, default 20),
   BEYOND. These slack-magnitude tiers are **distinct from SSI's `Path 01/02/03`** (converging logic
   paths) — the tool presents the SSI-parity slack per task; the tiers are its own classification.
4. **Golden fixture** `tests/fixtures/golden/ssi_uid143/case.json` (ADR-0005): the SSI
   driving-slack-by-UID table (107 UIDs), committed so the gate is reproducible in CI without the
   `.mpp`. A parity test asserts engine output == this JSON exactly (UID-keyed, whole working days).

## Consequences
- §6.C C2 (target → driving slack == SSI) is implemented + tested + **validated 107/107**; C3
  (secondary/tertiary thresholds) is engine-complete (the upload UI wiring is M13).
- The "stored progress-aware dates" rule is a reusable principle for the forensic metrics (M7-M8 read
  the same as-scheduled dates). Carried caveat (ADR-0010): `free_float`/non-FS slack is the
  governing-event slack; `total_float` and driving slack are exact for the parity schedules.
