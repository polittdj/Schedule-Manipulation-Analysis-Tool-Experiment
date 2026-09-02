# ADR-0448 — The bow-wave month axis always reaches the Target UID and every tracked activity

- **Status:** Accepted — 2026-09-02 (operator item 2 of six)
- **Version:** 1.0.229
- **Shipped:** `engine/bow_wave.py` (`compute_bow_wave`: pinned months widen the window before the cap; the right edge that is never shed includes them), `tests/engine/test_bow_wave.py::test_axis_always_reaches_the_target_and_tracked_finish_months` (observed RED pre-fix: `'Oct-27' not in (...'Jan-27')`)

## Context

"On the Work Piling Up page I want the scale of the visual to always expand to show the Target UID or
UIDs. When I entered UID 152 as the target UID it didn't show it on the screen." Their UID 152 (Ready to
Ship) finishes 2027-10-04 against a 2026-01-16 data date — 21 months out. The axis was clamped to the data
span ∩ [first status − 18, last status + 12] months, so the target's finish month was off-axis,
`target_scheduled_index` came back `None`, and `cei.js` drew no mark at all — silently.

## Decision

The focused target's and every tracked activity's scheduled AND actual finish months (every snapshot) are
**pinned** into the window before the 48-month cap applies. The cap still sheds the OLDEST months first and
never the right edge — which now carries the pinned finish as well as the newest status month and its CEI
period. Without a target or tracked UIDs the axis is byte-identical to before (the test pins `Jan-27`).

## Consequences

- The chart's slot width shrinks as the axis grows (48 slots on a 980-unit viewBox ≈ 20 px); the cap holds.
- A target whose ACTUAL finish lies far in the past is history and may still be shed by the cap; the
  scheduled finish — what "show the target" means — is on the right edge and never shed. Stated, not hidden.
- All 14 bow-wave tests green, including the two cap tests (nothing changed without a pin).
