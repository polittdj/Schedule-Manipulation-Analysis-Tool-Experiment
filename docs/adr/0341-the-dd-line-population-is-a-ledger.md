# ADR-0341 — the DD-line population is a ledger

Status: accepted (2026-08-02) — Phase 3 (UI), the DoD ledgers

## Context

`DESIGN-SYSTEM.md` §chart-contract: "Data date: always a **red** vertical line labeled `DD` /
`DATA DATE`, on every **time-axis** chart, no exceptions." The DoD checklist repeats it. **Nothing
enforced it** — a search of `tests/` found no DD-line ledger of any kind. This is the DD-line
counterpart to ADR-0298's `test_axis_titles.py`.

## Decision

### 1. The population is RE-DERIVED, never hand-listed

Every chart already declares its own X axis, in the `SFChartFrame.axisTitles` call ADR-0298 made
universal. So the ledger is keyed by `(module, line)` and each entry is **checked against the
xLabel that justifies it**. A hand-typed "these are the time-axis charts" would be a second source
of truth that drifts the first time a chart is added; this cannot — a new call site fails the
partition test, and a re-labelled axis fails its bucket's predicate.

Keyed by CALL SITE, not module, because `sra_jcl.js` carries **both** a time-axis chart (L136,
"Finish date") and the COST axis (L189, "EAC"). A module-keyed ledger could not express that.

### 2. "Time axis" is narrower than "ordered by time" — twelve exclusions, not three

The brief named three (`histogram`, `scatter`, `sra_jcl`'s EAC). The census found **twelve**. The
extra family is the **version axis**: `margin`, `trend`'s five charts and three of `volatility`'s
plot against "Schedule version" — ordered by time but **categorical**, one tick per loaded file. A
DD line has no position there, because *every version has its own data date*; drawing one would
have to pick a version and assert something the engine never says.

That creates a collision the ledger must get right, and the order of the checks is the fix:
`margin.js`'s xLabel is **"Schedule version (data date)"** — it contains the words "data date"
while being the clearest case of an axis that must *not* carry a DD line. **The version check runs
before the date check**, exactly as `ai/qa.py`'s identifier check runs before its derivation check.

`performance.js` L472 is the one call site of 28 whose xLabel is a **variable** (`opts`, built by
the quad-chart caller) and so cannot be read statically. It is recorded in its own bucket with the
reason pinned, rather than guessed into a real one.

### 3. `DD_PENDING` is derived, not declared

Eight time-axis charts draw no marker: `margin_dashboard` ×2, `resources`, `sra` ×2, `sra_jcl`
L136, `sra_ssi` ×2. The set is **computed** from the tree and compared to the record, so it can
neither overstate the work (a fixed entry never removed) nor understate it (a chart that lost its
marker) — the property `DOM_PENDING` earned the hard way in ADR-0340.

## The findings

**There are FOUR hand-rolled implementations, and they disagree with each other.**

| module | stroke | dash | label |
| --- | --- | --- | --- |
| `cei.js` | `BLUE` → `var(--accent)` | `6 5` | `"data date"` |
| `curves.js` | `BLUE` → `var(--accent)` | `6 5` | `"data date"` |
| `drift.js` | `"var(--muted)"` | `2 3` | **none on the line** (legend note only) |
| `scurve.js` | `"var(--muted)"` | `2 3` | `"data date " + status_date` |

The same contract element renders in two colours, two dash patterns and three labelling schemes
depending on which page the analyst is on. **Not one of the four matches the spec**: none is red,
every label is lowercase or absent, and each hard-codes `"font-size": 10` — the numeric-type-in-JS
fork ADR-0298 removed from captions and ADR-0195 forbids generally. These deviations are pinned as
executable records, so closing any one of them FAILS the ledger and forces it updated in the same
commit. That is the record, not an endorsement.

With eight charts pending, the answer is **one helper**, not four more copies — and ADR-0340
established that *where* it lives is a load-order question, not a filing one. That work is not in
this ADR: this one makes the gap visible and un-driftable first.

## Evidence — and two detectors that were wrong before they were right

The reverts, none found by reading:

| revert | result |
| --- | --- |
| remove `scurve.js`'s marker | **3 fail**, incl. the derived pending ledger |
| `cei.js`'s `BLUE` → `var(--danger)` | implementations test fails — proves the ALIAS is resolved |
| `histogram.js`'s xLabel → "Finish date" | its `NOT_TIME_AXIS` predicate fails |

The third matters most: it proves the exclusion list cannot shelter a chart that really does plot
against time.

**Two detectors failed first, in opposite directions, and both were caught by running:**

1. A `grep -ci "data.date"` census **over-reported** — it counts mentions (comments, `statusDate`
   variables). The previous handoff carried "4 time-axis charts have no data-date mention" from it;
   the real number is **8**, and that note is corrected by this ADR.
2. A byte-exact detector matching `cei.js`'s style (`"6 5"` + `textContent = "data date"`)
   **under-reported** — it missed `drift.js` (no label on the line) and `scurve.js` (the date is
   appended to the label) and reported two implementations where there are four.

The anchor that works is the one all four share and a reader must write deliberately: the `//`
comment naming the block. It is deliberately *not* a style match, because the styles are the
finding. Two slicing bugs also surfaced only by running: the first slice read `cei.js`'s
**docstring** (it says "dashed data-date marker" there too), and a fixed 700-character window
over-ran into the next block — harmless for three modules, but `drift.js` has no label, so the
spill supplied a `textContent` and a `font-size` from unrelated code.
