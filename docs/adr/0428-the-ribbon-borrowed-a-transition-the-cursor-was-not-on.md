# ADR-0428 — the transition ribbon borrowed a transition the cursor was not on

**Status:** Accepted · **Date:** 2026-08-19 · **Extends:** ADR-0420 (a figure belongs to the
population it is shown against) · **Ships:** `web/static/volatility.js`

## Context

The operator reported that Chapter 04 "is not working correctly" and asked for pass/fail tests
across the tool. Two separate things came out of that, and only the second was a defect.

**The arithmetic was already right.** Every existing guard for the stability band is *structural* —
the panels mount, the scope words appear, both pages embed the same dataset — and all of them pass
whether or not the numbers underneath are correct, because they compare the tool to **itself**.
`tests/web/test_ch04_stability_oracle.py` closes that gap with an independent oracle: schedules
whose critical membership is pinned by `stored_is_critical`, with every expected figure derived by
hand. Per-pair Jaccard, stayed/entered/left and their activity IDs, tenure, longest unbroken
streak, on/off flips, per-version counts, row order, the headline percentage and the rendered page
all match. Seven mutants — wrong Jaccard denominator, one-directional flips, streak conflated with
tenure, mean replaced by max, entered/left swapped, completed work retained on the path, undefined
similarity reported as zero — all go red.

**The defect was in the control, not the data.**

## The defect

`drawRibbon` resolved its pair with:

```js
var k = Math.max(1, cursor);
var p = PAIRS[k - 1];
```

The cursor names a **version**; the panel draws the transition **into** that version, which is
`PAIRS[cursor - 1]`. The first loaded version has no predecessor and therefore no such transition,
so the clamp made cursor 0 borrow `PAIRS[0]` — the pair belonging to cursor 1. Measured on the
four-version fixture:

| cursor | ribbon showed |
|---|---|
| 1 / 4 | `Hard_File → Hard_File_updated` |
| 2 / 4 | `Hard_File → Hard_File_updated` ← identical |
| 3 / 4 | `Hard_File_updated → Hard_File_updated2` |
| 4 / 4 | `Hard_File_updated2 → Hard_File_updated3` |

Two consequences:

1. **The opening click of Next changed nothing.** The baseline was already displaying the second
   position's ribbon, so the control read as dead — which is what the operator saw.
2. **The baseline stated a change that had not happened.** At cursor 1 the panel printed
   "33 stayed / 1 left" under the heading `v1 → v2` while the cursor was on v1 alone. That is
   ADR-0420's rule broken at a different granularity: a figure must belong to the population it is
   shown against, and here the population was a version pair the cursor was not on.

## Decision

At cursor 0 the panel says so, and prints no figures:

> **Hard_File.mspdi.xml**
> baseline — no preceding version to transition from
> step forward to see what joined and left the path

Every other position resolves `PAIRS[cursor - 1]` with no clamp.

## Attribution — pre-existing, surfaced not caused

`/volatility` mounts the same module and behaved identically. ADR-0427 put the ribbon on the
chapter page, where more people meet it, but did not introduce the clamp. Both routes are asserted
in the guard, because a fix to shared JS that is only tested on one consumer is half a fix.

## Verification

`tests/web/test_ch04_ribbon_cursor_chromium.py`, six tests (three claims × both routes), **all
observed red before the fix** with the defect printed verbatim — `assert [...] != [...]` on
byte-identical output for the first Next click:

| claim | before | after |
|---|---|---|
| each cursor position shows its own transition | red | green |
| the baseline states it has no predecessor | red | green |
| stepping forward from the baseline visibly changes the panel | red | green |

**One assertion was too crude and failed on the fix's own copy.** The baseline's helper line reads
"step forward to see what joined and left the path", and the test asserted the words *stayed*,
*joined* and *left* never appear. The real claim is that no **figure** is stated, so the assertion
now matches `(?:stayed|joined|left)\s+\d+`. A test that fails on correct explanatory prose is a
test defect, not a product one — and the fix must not be to delete the prose.

### Two things the gate caught that my own checks had passed

**I wrote "volatility.js carries no md5 pin (checked)" and it was false.** It *is* pinned, in
`PAGE_SCRIPTS`. The grep that produced the claim printed a 12-line window that stopped two entries
short of the answer, and a sweep whose window is too small under-reports by construction while
looking exhaustive — this repo's own standing lesson, reproduced. The digest is re-baselined here
with the justification the pin's convention requires
(`67a625584f35c78f067ae27446883d2a → 71f124b290e237521610ef40cda7ada7`): the diff is one index
plus an early branch, and the module's other ten visuals are byte-identical.

**The new browser module would have SKIPPED on CI.** It was first written pinning the vendored
browser directory in a `skipif`, copied from a pattern ADR-0418 had already retired;
`tests/guards/test_browser_resolver.py` caught it. That is not cosmetic — the guard against this
very defect would never have run on the one machine that matters. It now uses
`web.browser_chrome.chrome_kwargs()`, which falls through to playwright's own browser on a runner.

Both were found by the full gate, not by inspection, and both were mine.

## Why the oracle did not catch it

Worth stating, because it is the general lesson. The dataset was always correct: `PAIRS` held the
right pairs in the right order, and the oracle proves it. The defect was entirely in **which** of
those correct pairs a control chose to display. Data-level tests cannot see that, and no amount of
strengthening them would have. It took walking the control in a browser and reading what each
position rendered — a step that is easy to skip precisely when the numbers all check out.
