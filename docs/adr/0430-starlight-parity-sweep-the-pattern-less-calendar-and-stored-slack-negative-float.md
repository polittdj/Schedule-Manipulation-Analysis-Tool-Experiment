# ADR-0430 — Starlight parity sweep: the pattern-less calendar, and Negative Float is stored slack

- **Status:** Accepted
- **Date:** 2026-08-20
- **Extends:** ADR-0429 (same operator report, same six uploaded files: "fix all mismatches").
- **Relates:** ADR-0080 (stored-slack fidelity), ADR-0280 (DCMA-parity population), ADR-0419
  (the sibling "default times" calendar construct, previously unfixable for want of a file).

## Scope

After ADR-0429 fixed Hard Constraints, the operator widened the ask to every mismatch visible in
the Fuse-vs-POLARIS screenshots. Two more root causes were proven and fixed; one leg was measured
into a genuine oracle contradiction and is BLOCKED on one item only the operator's Fuse can
produce. Post-fix, the ribbon matches Fuse on **52 of 54 cells** across the six versions (9
metrics × 6), the two open cells being Insufficient Detail on V05/V06.

## Fix 1 — the pattern-less base calendar (importer; the 112 dropped holidays)

Starlight's project calendar (UID 1 "Standard") declares **no weekly pattern at all**: its 112
`WeekDay` rows are all `DayType 0` exception records (the same 112 dates also appear as modern
`<Exceptions>`), and there are zero `DayType 1-7` rows. MS Project semantics: a base calendar
without pattern rows works the **default week** (Mon–Fri at default times) plus its exceptions.
`_build_calendar` instead required a weekday pattern, returned `None`, and the caller fell back to
a naked Mon–Fri default — **silently discarding all 112 holidays** on every version (the logged
"does not resolve to a readable calendar" warning was the only trace).

Now: a chain with **no declared pattern anywhere** synthesizes the default week and **keeps** the
collected holiday/working exceptions (info-logged). A *declared* week whose every day is
non-working still takes the fallback — that distinction is pinned by identity (the fallback is
`Standard`/uid 0; a synthesized calendar keeps its own name/uid), because the weekday tuple alone
cannot tell the two apart (the pre-existing guard was blind exactly there — mutation M-cal-2
passed until the identity assertion was added).

A fixture sweep found **zero** committed MSPDI documents with a pattern-less project calendar, so
no existing pin can move; the construct joins ADR-0419's as operator-file-only, now regression-
pinned by a synthetic fixture mirroring the real file's shape.

## Fix 2 — ribbon Negative Float is arithmetic on STORED Total Slack

Measured against Fuse's 62/45/44/37/34/0 on the six real files:

| candidate | V05 | V06 | V07 | V08 | V09 | V10 | verdict |
|---|---|---|---|---|---|---|---|
| effective float < 0 (stored-preferred, recompute fallback) | 77 | 47 | 45 | 37 | 34 | 0 | X |
| DCMA07 parity (baselined incomplete, whole-day rounding) — what the page showed | 67 | 42 | 40 | 32 | 29 | 0 | X |
| **stored Total Slack < 0, incomplete, no filters** | **62** | **45** | **44** | **37** | **34** | **0** | **= Fuse, 6/6** |

The old sourcing missed in **both directions at once**: the per-task recompute fallback added
phantoms on the tasks the source wrote no slack for (+15 on V05 — inflated further by the
calendar defect above), while the Acumen-parity baselined filter dropped real stored negatives
(−10, e.g. unbaselined milestones). This is the metric-parity skill's §2 triage — stored vs
recomputed — decided by measurement.

`schedule_quality.negative_float` now counts `stored_total_float_minutes < 0` over incomplete
non-summary activities; a task without stored slack is **absent, never recomputed**. One
documented regime switch: a schedule whose incomplete work carries **no stored slack anywhere**
(pure-logic files, the tool's own JSON without float) keeps the recomputed-CPM count — the signal
must not become a fabricated clean bill on stored-less formats. The ribbon cell + drill-down
source from `schedule_quality` (the single-formula pattern). **DCMA07 itself is untouched** — its
parity semantics were validated against Acumen's own DCMA report (ADR-0280); the DCMA card and
the ribbon now legitimately differ, mirroring Acumen's two products, same as ADR-0429's pair.

## A documented divergence CLOSED by the same fix — the Hard_File 34/33

The full suite's one red was `test_fuse_hardfile_divergences_are_exact_not_papered_over`: the
committed Fuse hard-file golden had honestly pinned "engine 34/33 vs Fuse 0/0" as a documented
stored-vs-recomputed divergence, with a needs-list note requesting a deeper investigation.
Measured now: Hard_File has 110 incomplete tasks, 76 with stored slack (all ≥ 0), **34 without —
the old engine count was exactly the stored-less set**, i.e. the recompute-fallback phantom
mechanism this ADR removes, independently confirmed on a second oracle. The engine now equals
Fuse (0/0); the pin was re-baselined through its own path to assert the CLOSED state **and**
that the fixture still carries the 34-task phantom population — reintroducing the fallback turns
that parity test red by name (mutation-proven).

## Blocked leg — Insufficient Detail on V05/V06 (oracle contradiction; STOPPED per the skill)

Fuse says 5 on every version; the tool says 0 (V05) / 4 (V06) and matches 5 on V07–V10. The same
five cadence activities (190–220 working days, stored plainly as days — verified in the `.mpp`
bytes via MPXJ, durations/units/calendars/status all ruled out) sit just under 10% of the
V05/V06 spans. **Six hypotheses were constructed and every one refuted by measurement** against
the committed operator-validated pins (Large-Test 43 / TP3 9 / TP1 4 / TP4 5×5 / P2 1 / P5 0):

1. duration in calendar-day extent (×7/5) — breaks 9/10 pins;
2. minutes-per-calendar-day (week/7) — breaks 9/10;
3. span to max task **baseline** finish (1704d, constant → 5×6 on Starlight) — breaks P5 and TP1;
4. span to `Schedule.baseline_finish` — same refutation;
5. duration at fixed 480 min/day — breaks TP2 (6→9, pin 7);
6. span from the `.mpp`'s stored ProjectFinish — **read directly from the binaries with MPXJ:
   identical to the exported value** (V05 = 2032-04-30), no divergence to exploit.

Any constant span in [1000, 1890] days reproduces Fuse's 5×6 on Starlight — but no quantity in
the files' bytes lands there without breaking a committed pin. Per the skill: *the oracle and the
bytes contradict → STOP and ask*, rather than fitting an unfalsifiable rule. **Unblocking needs
exactly one artifact: Fuse's own offender list for one cell** — in the Starlight workbook, click
the V05 "Insufficient Detail 5" ribbon cell (or export the ribbon to Excel) so the five activities
Fuse counts are named. With the list, the denominator/population falls out in one division.

Recorded, adjacent: TP2 (4×10 calendar) sits at 6 vs Fuse's recorded 7 under EVERY convention
tried — a pre-existing, previously unpinned residual (the ribbon `_FUSE` table pins TP2's other
columns but Insufficient Detail was never pinned there). Same investigation, same blocked oracle.

## Verification

- Red-first on both fixes (calendar test failed with the exact production warning; negative-float
  discriminator failed at `(1, 3, 4) ≠ (1, 4)`), then green.
- **Six mutations red by name** (pattern-less→None again · synthesize-always [caught only after
  strengthening the blind identity oracle] · effective-float revert · fallback removal [also
  caught by the TP3 Fuse pin] · ribbon re-sourced from DCMA07 · offender-source skew).
- Full ribbon vs Fuse on the six real files: **52/54 cells exact**; Negative Float 6/6; Hard
  Constraints 6/6; calendar resolves silently with its holidays and worked-weekend days.
- Engine + importer suites 1372 passed; Fuse reference pins unchanged; statics green whole-tree.

The Starlight `.mpp`s/XMLs remain outside the repo (operator uploads; scratchpad only); their
measured numbers are recorded here and the committed regression tests carry the classes.
