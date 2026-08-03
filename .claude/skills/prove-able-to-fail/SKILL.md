---
name: prove-able-to-fail
description: Prove a new or changed test, guard, assertion or census in POLARIS/SMAT can actually FAIL before trusting that it passes. Use whenever writing or editing a test, a guard, a ledger/census, a contract check, or a pinned expectation; whenever a test passes on the first run; whenever asked "does this test work", "is this test real", "verify the fix"; and before claiming any behavioral change is verified. This repo's single most-repeated defect class is a green test that could never fail.
---

# Prove it can fail

This is a **standing requirement**, not an optional nicety. The repo's own history:

- a ⛶ enlarge assertion read back a CSS class and **passed for months while the control moved
  nothing** (ADR-0304);
- a measured-box job went **green in 59 s with all three proofs SKIPPED** (ADR-0305);
- "a test can measure the wrong thing for eleven batches and stay green" (2026-08-01i);
- "the assertion was looser than the rule, so it could not fail" (2026-08-02e);
- "a vacuous pass hides in 'the page loaded'" (2026-08-01b);
- "a `-k` filter deselected the test the revert was aimed at" (2026-08-02b).

A test that has never been observed failing is an untested test.

## The procedure

### 1. Revert the CALLER, not the helper

Restore the *exact* prior behavior at the **call site** the change fixed (`or 0` back, the guard
conjunct removed, the helper swapped for the old one). Reverting a helper's internals can leave the
caller unaffected and prove nothing.

### 2. Confirm the revert actually changed the OUTPUT

For a UI/render change this means the **rendered page**, not the source. Source call sites are not
rendered charts — `curves.js` has ONE `axisTitles` call site and renders THREE charts. Render both
sides and diff (see the `render-verify` skill). If the revert did not move the output, your revert
was wrong; fix the revert before concluding anything about the test.

### 3. Run the WHOLE module — never a `-k` filter

```bash
python -m pytest tests/web/test_absent_is_not_zero.py -q      # whole module
```

A `-k` expression can silently deselect the very test you are targeting and report a green run.
Run the module (or the file set) with no filter.

### 4. Read which tests failed, and how many

State the split explicitly, e.g.:

| revert | result |
| --- | --- |
| `/cei` caller → `or 0` + unconditional bar | **2** fail (both `/cei`-unscored); 9 pass |
| `/groups` caller → `or 1` | **6** fail (empty-population, both fixtures) |

**A revert that fails the WHOLE module proves nothing** — it means the fixture, not the behavior, is
carrying the assertion. Each revert should fail only the tests aimed at that branch and leave the
rest, including the true-positive twin, green.

### 5. Pair every fabricating branch with its TRUE-POSITIVE TWIN

Assert the honest case still reports honestly. `0%` over a real population must still read `0%`;
a genuinely scored month must still read `3 of 3` / CEI `1.00`. Without the twin, a test passes by
suppressing the whole surface.

### 6. Restore the tree — never with `git checkout <file>`

Copy the pristine file back from a scratchpad copy taken **before** the mutation:

```bash
cp <file> "$SCRATCH/orig-<file>"     # BEFORE mutating
# … mutate, run, observe …
cp "$SCRATCH/orig-<file>" <file>     # restore
```

`git checkout <file>` discards uncommitted work in that file. This repo has needed the `cp` form
twice in a single session.

## Derive expectations; never transcribe them

A test that hard-codes a count copied from a run pins the run, not the rule. Derive the expectation
at test time from the same source the code reads (`group_values` / `non_summary`, the `.aft` library,
the live render), then assert the **invariant** — "a percentage appears **iff** the value has a
non-summary activity behind it" — not the sampled number.

Corollary, paid for twice in consecutive sessions: **a matching count is not an identification.**
118 rows read `0%` and matched the hypothesis; re-deriving the population per value cut it to **19**
— the other 99 were honest zeros. *A number that matches your hypothesis is the moment to re-derive
it, not the moment to write it down.*

## For guards and censuses specifically

- **Mutate the thing the guard protects** and require the guard to fire. A guard that greps prose
  measures the documentation, not the behavior (ADR-0300).
- Assert the **property**, not an enumeration of known failure modes. The measured-box CI step
  matches **any** skip, because the first version enumerated one skip reason and missed another.
- A census/ledger must **re-derive its population** from what the code declares, so a new call site
  fails the partition test instead of being silently uncounted.

## Done means

- [ ] The revert was at the caller and changed the observed output
- [ ] The whole module ran, unfiltered, and the failing set was **narrow and named**
- [ ] The true-positive twin stayed green under the revert
- [ ] Expectations are derived, not transcribed
- [ ] The tree is restored from a scratchpad copy and the gate is green again
