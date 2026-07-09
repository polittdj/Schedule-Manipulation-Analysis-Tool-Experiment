# ADR-0181 — Change-effects cap starves artifacts last; incomplete-only artifact rule; re-audit triage

## Status

Accepted. Operator 2026-07-09 (second message): pasted an adversarial configuration-management
audit produced by another AI session and asked "Is the below accurate … Do we have an issue that
we need to resolve before we continue? If so, verify it is truly an issue and if it is solve it."

## Context — the audit triage (every claim verified, not assumed)

The pasted audit raised ~10 findings. Verified dispositions:

- **REAL (fixed here): measurement-cap starvation.** `compute_change_effects` reverts at most
  `_MAX_CHANGE_EFFECTS = 60` changes individually. Changes were measured in detection order
  (links → durations → constraints), so on a pair whose diff exceeds the cap, whatever came last
  — including DELIBERATE edits — went unmeasured while zero-effect reschedule artifacts consumed
  slots. Empirically: Hard_File→Hard_File_updated3 detects 71 changes; pre-fix the page showed
  **35** artifacts (the measured subset) with 11 changes capped, while updated2→updated3 (54
  changes, under cap) showed the true **44** — the "35 vs 44" discrepancy the operator saw is
  cap starvation on the first-vs-last pair, not nondeterminism and not a stale build.
- **FALSE: latent `TypeError` sorting relationship-key tuples.** `RelationshipType` is a
  `StrEnum` (verified via MRO + a live sort with tied prefixes) — tuples containing it sort fine.
- **FALSE: "35 MS Project reschedule artifact(s)" being wrong for a statusing update.** Every
  flagged task on every fixture pair verified SNET-stamped exactly at the later version's data
  date and incomplete — the banner text is accurate and already hedged ("look like … usually a
  statusing side effect").
- **ALREADY CLOSED: the swapped `.aft` Bible (REF-1).** The 20260708 and 20260423 libraries are
  mathematically identical (759 metrics in both, 0 added/removed, 1 cosmetic parenthesization) —
  ADR-0176 task #88; `test_aft_formula_audit.py` passes against the live 20260708 file.
- **BENIGN (verified): the re-uploaded `Hard_File.mpp` / `Hard_File_updated.mpp` (COC-1).**
  Commit af4d154 modified both (same size, different bytes). Fresh MPXJ conversion of the current
  binaries vs the pinned parity goldens: **all 142 tasks field-for-field identical, links
  identical, status dates identical**; the only deltas are the SSI trace tool's fingerprints
  (Trace Log Field / Driving Slack custom fields, two unused base calendars) plus MPXJ's
  uninitialized `RemainingOvertimeWork` noise. A re-save after the SSI path trace — parity
  oracles remain valid. updated2/updated3 goldens match their binaries exactly.
- **DOCUMENTED PROCESS: "Add files via upload" commits (CM-3).** ADR-0152's operator intake
  path; the CUI determination is recorded in CLAUDE.md.
- **OPERATOR-MACHINE HYGIENE (CM-1/CM-2):** a stale June clone and 8 uncommitted local fixture
  deletions in the active clone — nothing in-repo to fix (`git restore tests/fixtures/` there).

## Decisions

1. **Artifact reverts are measured LAST.** The constraint sweep defers every artifact-pattern
   revert and runs them after all removed/added-link, duration, and non-artifact constraint
   reverts — so the cap starves statusing noise, never a deliberate change. Post-fix,
   Hard_File→updated3 measures all 27 genuine changes; the 11 capped rows are all artifacts.
2. **Incomplete-only artifact rule.** `is_reschedule_artifact` now also requires
   `percent_complete < 100`: MS Project only reschedules *uncompleted* work, so SNET-at-data-date
   on a complete task is a deliberate edit. Behavior-neutral on all fixture pairs (zero flagged
   tasks were complete) — pinned by a unit test.
3. **Capped artifacts are disclosed, and the banner totals DETECTED artifacts.**
   `ChangeEffectsReport.skipped_capped_artifacts` counts capped changes matching the artifact
   pattern (pattern-detectable without a CPM pass). The Integrity cluster heading now reads the
   full detected total (measured + capped, e.g. **44** on every pair ending at updated3), the
   cluster note states how many were not individually measured, and the cap note says the
   starved remainder is artifact-pattern. No text change when nothing is capped (updated2→
   updated3 still reads exactly as pinned).

## Consequences

- The operator-visible "35 vs 44" inconsistency is gone: every pair ending at updated3 reports
  44 detected artifacts. Pinned by `test_measurement_cap_starves_artifacts_not_real_changes`
  (engine, synthetic 65-change pair) and
  `test_capped_pair_reports_the_full_artifact_total_and_starves_only_artifacts` (web, the real
  Hard_File→updated3 goldens: 44 total, 33 measured, 11 disclosed).
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
