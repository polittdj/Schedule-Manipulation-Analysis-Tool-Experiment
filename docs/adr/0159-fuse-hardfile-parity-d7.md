# ADR-0159 — Hard_File Acumen Fuse v8.11.0 parity (second oracle; closes needs-list D7)

## Status

Accepted. Consumes the operator's 2026-07-08 Fuse delivery for `Hard_File.mpp` /
`Hard_File_updated.mpp`.

## Context

Until now ENGINE==FUSE was pinned by a single delivered oracle — the `project2_5` suite
(ADR-0151). Needs-list **D7** specifically wanted a Fuse export of a schedule containing an
**elapsed in-progress activity** (the P2–P5 pair has none), to validate the elapsed-axis
metrics against a real Fuse run rather than engine self-consistency. The operator delivered the
full Fuse v8.11.0 export suite for a new two-snapshot file (`Hard_File` @ 7/7/2026 and
`Hard_File_updated` @ 8/11/2026, 142 tasks each), and the updated snapshot carries exactly one
normal in-progress to-go activity.

## Decisions

1. **Second ENGINE==FUSE oracle pinned** (`tests/parity/test_fuse_hardfile_parity.py`,
   `fuse_hardfile/case.json`). **15 metric values across the two snapshots reproduce the Fuse
   Metric History Report exactly**, UID-for-count: Missing Logic (Hard_File 7), Hard Constraints
   (0/0), High Float ≥44 d (2/6), Milestones-with-duration>0 (0/0), Tasks & Milestones To-Go
   (110/103), Milestones To-Go (25/24), Normal Tasks To-Go (85/79), and **Normal Tasks To-Go
   In-Progress (0/1)** — the D7 elapsed-in-progress transition, agreed by both tools.
2. **D7 closed.** The 0→1 in-progress transition between snapshots gives the elapsed-axis
   metrics a real Fuse oracle; `test_fuse_hardfile_covers_elapsed_in_progress_activity` asserts
   it.
3. **Fixtures committed as gzipped MSPDI** (MPXJ-converted, ~27 KB each) under the golden —
   the same pattern as `ssi_uid152` (ADR-0158). The `.mpp` files stay out of git (large,
   non-CUI build inputs per CLAUDE.md); the pre-commit CUI guard passes (`.xml.gz` is not a
   blocked extension).
4. **Three divergences recorded EXACTLY, never forced** (Law 2 — a fast wrong number is
   worthless in testimony):
   - **Negative Float — engine 34/33 vs Fuse 0/0.** Every engine offender carries the source
     tool's **stored Critical flag** but no stored `TotalSlack` (MPXJ omits it for these tasks;
     UID 147 is a source-Critical milestone). `effective_total_float` (ADR-0010/0080) then falls
     back to the recomputed pure-logic CPM float, which reads negative where MS Project's stored
     slack — which Fuse reads — is 0. This is the documented stored-vs-recomputed CPM divergence,
     not a curve-fittable typo; clamping to 0 would hide a genuine CPM-vs-MS-Project difference.
     → **needs list**: investigate *why* the recompute diverges on these constrained/leveled
     tasks (the fix is CPM parity, not a clamp).
   - **Missing Logic (updated) — engine 10 vs Fuse 8.** Hard_File matches exactly (7=7); on the
     updated file Fuse's own components (Missing Predecessors 0 + Missing Successors 7) do not
     sum to its Missing Logic 8, so Fuse applies an unpublished definition nuance (likely an
     LOE / start-milestone exclusion). → **needs list**: Fuse's exact Missing Logic definition.
   - **Activities with Duration=0 — engine 0 vs Fuse 1.** The raw MSPDI carries zero
     non-milestone zero-duration tasks (all 25 are `Milestone=1`); Fuse's count of 1 uses an
     internal classification not derivable from the exported flags. A 1-count minor-metric
     divergence.
   Each is asserted at its current engine value in
   `test_fuse_hardfile_divergences_are_exact_not_papered_over`, so any future change forces the
   golden note and the needs list to be revisited in the same commit.

## Consequences

- ENGINE==FUSE now rests on **two independent delivered oracles** (small unprogressed-in-place
  Project2/5 and the two-snapshot Hard_File with a live in-progress activity); the elapsed-axis
  need D7 is closed with a real Fuse comparison.
- The negative-float / missing-logic divergences are now *pinned* rather than latent — the next
  Fuse-parity increment is a focused CPM-vs-MS-Project reconciliation on stored-critical tasks
  with no exported slack, and a request for Fuse's Missing Logic / Duration=0 definitions.
- Engine code unchanged — this ADR adds validation and honest divergence records only; parity
  is broadened, not altered.
