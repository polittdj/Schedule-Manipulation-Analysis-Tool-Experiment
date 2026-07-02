# ADR-0143 — Residual-findings closeout: every remaining in-env audit finding fixed or documented

## Status

Accepted. Closes the last in-env items across both audit trails (batch R7); after this, **no
in-env finding remains open in any ledger** — everything left is artifact-gated on the operator's
reference files.

## Context

After the 2026-07-01 QC-audit remediation (ADR-0138..0142), the unified ledger still carried the
LOW/NIT residuals that every audit had deferred: L4, L8, L9, L10, L11 (internal audit,
SUSPECTED-OPEN — never re-executed), F-01 (PARTIAL — disclosure prose with no enforcing test),
F-13, F-14 (F-set), and NEW-2 (re-audit). All are in-env fixable; none needs an operator file.

## Decisions

1. **L4 — stale derived magnitude (fixed).** `sra_risk.js::derive()` returned early when the
   affected set had no remaining-duration basis (`avg <= 0`), leaving the previously-derived
   value in the unlocked field, where it then posted as if freshly derived. It now **clears** the
   unlocked field when the basis disappears.
2. **L9 — client derive math now executes under test (fixed).** The vendored JS was only
   `node --check`ed; the days↔% derivation the operator actually uses was never run by any test.
   A node-driven harness (`tests/web/js/sra_derive_harness.mjs`) stubs the minimal DOM, drives the
   IIFE's own input handlers, and asserts the server-mirrored formula cases (including the L4
   clear and the lock/unlock/re-fit transitions); `tests/web/test_sra_derive_js.py` wires it into
   the pytest gate (skipping only when node is absent).
3. **L10 — behavioral offload test (fixed).** The old test asserted exact source spelling
   (`"run_maybe_offloaded( heavy, compute_sra,"`), so harmless refactors broke it while a real
   regression could hide behind a rename. It now monkeypatches `run_maybe_offloaded`, drives a
   real >threshold schedule through `/api/sra`, and asserts the offload **decision** (and the
   in-process decision for a small schedule).
4. **F-13 — deactivation is a first-class manipulation signal (fixed).** `is_active` joins
   `diff._TRACKED_FIELDS`, and `detect_manipulation` gains `MANIP_DEACTIVATED_TASK`: flipping a
   task inactive removes it from the CPM network (ADR-0128) while the row stays visible —
   functionally a deletion that never hit the deleted-task count. HIGH when the task was on the
   prior critical path; the re-activating direction is deliberately not flagged.
5. **NEW-2 — net-zero calendar swap no longer "loosens" (fixed).** The weekday signal in
   `MANIP_CALENDAR_LOOSENED` fired on any *added* weekday, so a Mon–Fri → Tue–Sat swap (zero net
   working time) was flagged as gained working time. It now fires only on **net working-week
   growth** (day-count increase); lengthened days / removed holidays / added worked exceptions
   are unchanged.
6. **F-01 — the engine-pinned marker is now test-enforced (upgraded from PARTIAL).**
   `test_engine_pinned_marker_cannot_be_silently_deleted_f01` pins the "engine-pinned / NOT
   Fuse-validated" disclosure in both `docs/PARITY-REPORT.md` and the golden's own
   machine-readable caveat — deleting the label now fails a test. The *numeric* Fuse validation
   itself remains artifact-gated (unchanged).
7. **L8 / L11 / F-14 — documented at the point of use.** `gantt.js::freezeColumns` states its
   `SFColResize.attach`-first precondition; the MSPDI link-dedup site states the lag-only
   duplicate collapse (matches XER; MSP's UI forbids such duplicates); the driving-slack tier
   thresholds and the two `health_extra` cutoffs carry explicit "in-repo default, NOT
   handbook-sourced — re-source when the handbook lands" provenance notes.
8. **Ledger discipline.** The unified ledger's rows for all nine items are refreshed, and three
   §7 rows left stale by the same-commit R6 fixes (D17/D18/D25 "OPEN → R6") are corrected to
   FIXED ADR-0142 — caught by this batch's own review, per the refresh rule §7 establishes.

## Consequences

- Both audit trails are now fully dispositioned: every finding is FIXED, DOCUMENTED,
  as-designed (L5/L6/F-09/F-10), or artifact-gated (PARK-LIST §B/§B-addendum).
- Two silent-regression classes became loud (client derive math; offload decision), and one
  false-positive manipulation signal is gone while a real manipulation vector (deactivation)
  gained a dedicated, severity-aware flag.
- Full gate + parity green; no golden number moved (the new detector adds findings only when a
  version pair actually contains a deactivation, which no golden pair does).

## Alternatives considered

- **Leave the LOW/NIT residuals open indefinitely.** Rejected: "small + known" still meant three
  audits in a row re-triaged them; closing or documenting each is cheaper than a fourth triage.
- **Flag re-activation too (F-13).** Rejected: turning work back ON cannot mask a slip; flagging
  it would add noise to the exact signal the detector exists to keep clean.
