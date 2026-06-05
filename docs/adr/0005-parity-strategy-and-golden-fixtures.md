# ADR-0005: Parity strategy & golden fixtures

- **Status:** Accepted
- **Date:** 2026-06-05 (session A2 — Phase 2 plan)
- **Relates to:** §6.B (exact Acumen v8.11.0 + SSI parity), §6.C (driving slack), §7 (TDD/RTM)

## Context
Acceptance hinges on reproducing the Acumen Fuse v8.11.0 and SSI golden numbers **exactly** for
the same inputs, matched **by UniqueID only**. The golden numbers (`PARITY-TARGETS.md`,
`SSI-DRIVING-SLACK.md`) and the source schedules (`Project2.mpp`, `Project5.mpp`) are **non-CUI**
sample data (commercial-construction sample; data-owner attested, ADR-0003).

## Decision
1. **Parity suite is the gate.** A parametrized `tests/parity/` suite asserts computed values ==
   golden values (UniqueID-keyed). CI fails red on any miss; merge blocked.
2. **Commit non-CUI golden fixtures** under `tests/fixtures/golden/` (allowed by `.gitignore`):
   - `project2_5/` and `ssi_uid143/` each with an **`input` MSPDI XML** (MPXJ conversion of the
     `.mpp`, non-CUI sample) + a **`case.json`** of expected values transcribed from the Acumen/SSI
     exports (the §B/§C tables). Mirrors the prior build's `commercial_construction_p5` pattern.
   - Keep the raw vendor `.xlsx`/`.pbix`/`.mpp` **out of git** (Drive + local only); commit only the
     distilled MSPDI + expected-value JSON.
3. **Synthetic fixtures** (`tests/fixtures/`, hand-authored, e.g. A→{B,C}→D) cover engine units so
   most tests need no JVM; real-sample parity covers fidelity.
4. **Determinism:** internal **minutes**, convert to **days** at the boundary with fixed rounding;
   no binary-float drift in any asserted value.
5. **Deltas:** where an exact match is genuinely impossible, document the precise delta with
   citations (file + UID + task) and treat it as a defect to drive to zero — never silently round away.

## Consequences
- Parity is reproducible in CI from committed (non-CUI) fixtures, with no Drive/JVM dependency for
  the JSON-vs-engine assertions (MSPDI inputs are committed; native-`.mpp` conversion is a separate
  importer test).
- Golden values are versioned and auditable — appropriate for a forensic/testimony tool.
