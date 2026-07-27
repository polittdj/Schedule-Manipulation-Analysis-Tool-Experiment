# ADR-0301 — Axis captions are derived from the rendering code, not from the spec's caption table

- **Status:** Accepted
- **Date:** 2026-07-27
- **Implements:** `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` batch 1 — **by the `PENDING` ledger, not
  by the spec's §5 batch table**, and with its §3 captions overridden for four modules
- **Related:** ADR-0298 (one helper, one token, the ledger — batch 0), ADR-0195 (design system),
  ADR-0249 (encode the claim as an executable assertion), ADR-0192 (never a false statement about
  our own output)

## Context

ADR-0298 promoted axis captions into one helper and left the rest as "ordinary follow-on work,
driven by the `PENDING` ledger shrinking to empty". Batch 1 is the first of those batches, and it
turned out **not** to be mechanical. Two structural problems in the applyable spec surfaced the
moment its instructions were checked against the code that renders the charts.

### 1. The spec's batch table was never revised after ADR-0298's correction #4

ADR-0298 established that eleven modules in the §3 caption table render **no SVG at all**, and
parked them in `NO_SVG_AXES`. Its §5 batch table was not revised to match, so the spec's **batch 1
is four-fifths inapplicable**: `gantt.js`, `drilldown.js`, `driving_path.js` and `driving_tiers.js`
are all DOM visuals the SVG `<text>` helper cannot serve. Only `histogram.js` is real work.

### 2. Four of the spec's captions state something the chart does not plot

Checked one module at a time against the rendering code:

| Module | Spec says | The code plots |
| --- | --- | --- |
| `curves.js` | Y: `CUMULATIVE VALUE ($M)` | **activity counts** — "the *count* axis of each chart is locked to that chart's own tallest point" |
| `resources.js` | X: `WEEK (COMMENCING)` · Y: `DEMAND (FTE)` | a **runtime-chosen** day/week/month bucket (`UNIT`), and **work booked in working days** ("d booked" in every tooltip) |
| `cei.js` | Y: `… — secondary axis: EXECUTION INDEX (RATIO)` | **no secondary axis exists**; the CEI figure is a text callout at the top-right |
| `drift.js` | X: `SCHEDULE VERSION (UPDATE)` · Y: `SLIP AGAINST BASELINE (WORKDAYS)` | **forecast finish dates** against **three forecast methods** (categorical rows) |

On a tool built for testimony, a caption is not decoration — it is an assertion about what the
reader is looking at. "DEMAND (FTE)" over an axis of working days is the same defect class as a
false `[ok]`: our own output stating something we can check and did not.

## Decision

**Captions are derived from the rendering code. The spec's §3 table is a starting suggestion to be
verified, never a source to be transcribed.** Where the two disagree, the code wins and the
disagreement is recorded (`00_REFERENCE_INTAKE/UI-INVENTORY.md` §2 CORRECTIONS).

**Batches follow the `PENDING` ledger, not the spec's §5 table.** The ledger is executable and
current; the table is neither.

### Batch 1 — five modules, `PENDING` 16 → 11

| Module | X caption | Y caption | Note |
| --- | --- | --- | --- |
| `histogram.js` | Total float band (working days) | Activities (count) | **retires a third local convention** (below) |
| `curves.js` | Month | Activities (count) | one `lineChart()` serves all three charts |
| `scurve.js` | Month | Cumulative completion (%) | locked 0–100%, as the spec said |
| `cei.js` | Month | *toggle-dependent* (below) | |
| `resources.js` | Period (`UNIT` commencing) | Work booked (working days) | `UNIT` is chosen at runtime |

**Two captions are computed, not constant, because the axis itself changes:**

- `cei.js` — the Running-totals toggle switches the Y axis between per-month counts and a locked
  cumulative axis (`top = totals ? cumTop : data.max_count`). The caption follows the toggle; a
  constant string would be false in one of the two modes.
- `resources.js` — the bucket width is `day`/`week`/`month` at runtime, so the caption names the
  bucket actually rendered rather than assuming one.

This follows the spec's own §3.1 precedent (pass a computed label rather than hard-code strings),
extended to any axis whose meaning is a function of state.

### `histogram.js` carried a THIRD caption convention

Beyond the two ADR-0298 retired, `histogram.js` drew its own centred X caption at a hard-coded
11px (`cap.textContent = "Total float (working days)"`). It is now the shared convention, and the
module gains a Y caption it never had.

**The second-convention guard did not catch it, and cannot be completed.** `SECOND_CONVENTION` pins
the variable names `xt` / `yt` / `axisTitle`; this one was `cap`. Widening it to `cap.textContent`
would fire on `a11y.js` and `trend_drill.js`, which use `cap` for legitimate non-axis text. A
name-based regex cannot decide whether a `<text>` node is an axis caption.

So the regex is left as-is and its limitation is recorded here instead: **the property that
actually converges is the ledger reaching empty.** At that point every SVG chart provably calls the
helper, and any new local caption shows up as a chart that is captioned twice.

### `drift.js` is deliberately still `PENDING`

Two independent reasons, both recorded in the ledger so the next batch does not "just add the call":

1. Its captions are not a transcription problem but a **decision** — see the table above.
2. The Y caption anchor (`T + 9`) lands **7px above** its first method-name row (`padT + 14`), so
   it needs a `padT` nudge. Moving the plot is a layout change, and the spec's own definition of
   done requires the diff to show *only* caption strings, the helper call, and deleted local
   caption code.

Deferring one module and saying why is cheaper than shipping a caption that is either false or
overlapping.

## Consequences

- `PENDING` **16 → 11**; `histogram`, `curves`, `scurve`, `cei`, `resources` captioned.
  `UI-INVENTORY.md` §2 flips (a)/(b) to yes for those five, with the corrections above recorded.
- **The guard was proved to bite — three mutants, each caught by its intended assertion**
  (file backups, ADR-0298): a deleted `axisTitles` call (module falls into no bucket); a caption
  with only one label; and a captioned module parked back in `PENDING`.
- **Version 1.0.105 → 1.0.106**, wheel rebuilt and all nine installers regenerated — the static JS
  is packaged, so ADR-0148's lockstep rule applies. Verified by watching
  `test_embedded_wheel_is_in_lockstep_with_the_source_tree` fail first and pass after.
- **Incidental, and worth knowing: the regeneration moved the MPXJ download pin onto permanent
  history.** `mpxj_ref()` pins the last commit touching `tools/mpxj`. The pin shipped in v1.0.105
  (`1f10729`) is **not an ancestor of `main`** — it survives only on an unmerged branch, so the
  operator's converter download depended on that branch continuing to exist. The regenerated pin
  (`749bf07c`) is a squash-merge commit **on `main`**, and its `tools/mpxj` bytes are byte-identical
  to the working tree. The windows CI leg re-verifies the fetch against the new pin.
  **A squash-merge gives the same content a new SHA, so a pin captured from a pre-merge branch is
  orphaned the moment that branch goes** — `mpxj_ref()` should be re-checked against `main` whenever
  `tools/mpxj` changes.
- The three dashboard payload golden SHAs are unchanged: a caption cannot move a payload hash.
- **Still owed, unchanged:** the four-theme visual pass (console / daylight / apollo / jarvis at
  90–125%). A headless browser *is* available in this container (see the handoff), but the pass
  itself has not been run.

## Addendum — batch 2, 2026-07-27: a ledger entry that was never a chart

`PENDING` **11 → 7**: captioned `margin.js`, `trend_drill.js`, `wbs.js`, and **moved `path.js` out
of `PENDING` entirely** because it is not an SVG chart.

**`path.js` was mis-parked, on a claim in ADR-0298.** That ADR said the spec's tick-detecting regex
"missed `path.js` and `resources.js`, which do draw SVG axes". Half of that is right:
`resources.js` genuinely draws SVG axes (captioned in batch 1). `path.js` does not. Its timeline is
a **DOM table** — `tbody`, `.path-track` divs, `rowIndex` arithmetic — and its *only* SVG is a
two-element absolutely-positioned overlay (`.pv-link`: one `<svg>`, one `<path>`) drawing a
dependency connector between two table rows. No chart root, no plot rect, no tick text. Nothing
`SFChartFrame.axisTitles` can attach to. So "11 charts still to caption" overstated the work by
one, which is precisely what the ledger exists to prevent.

**Both mirror tests used the same too-weak proxy.** `NO_SVG_AXES` means "no SVG *axes*", but the
test asserted "renders no SVG *at all*" — so there was no correct bucket for a DOM visual with an
incidental SVG overlay.

**A cleverer regex was tried first, and rejected on evidence.** The obvious fix — detect a real
chart as "creates an `<svg>` root AND declares a plot rect" — was written and run against every
module before adoption. It mis-classified **five**: `performance.js` and `margin_dashboard.js`
(geometry named `L/R/T/B`, not `padL`), `resources.js`, `sra_jcl.js` and `sra_ssi.js` (built through
a local `svg()` factory, not `svgEl("svg")`) — and it *still* called `path.js` a chart. Every module
names its geometry differently, so a static detector is the same name-based trap this ADR already
warns about, one level up.

**So the exception is explicit instead of inferred.** `INCIDENTAL_SVG` names the entry and the
reason; the mirror test skips only those. Three ways it could rot are closed by
`test_the_incidental_svg_exception_cannot_rot`: an entry not in `NO_SVG_AXES`, an entry that
renders no SVG (so the exception was never needed), and an entry that has since gained captions.
Parking a real chart there now takes two deliberate edits and a written reason.

### A gap named, not invented: secondary axes

`wbs.js` is a **combo chart** — SPI(t) bars on the left axis, earned schedule (working days) as a
line on the right. `axisTitles` draws exactly one X and one Y, so the right axis stays uncaptioned.
Captioning the primary pair is strictly better than the two unlabelled axes it had, and says
nothing false about the right axis. A secondary-axis affordance is a change to the shared
convention (ADR-0298) and needs its own decision — `sra.js` and `margin_dashboard.js` will want it
too. Recorded here rather than improvised mid-batch.

### The spec was wrong again, in the same direction

`trend_drill.js` — spec: "SCHEDULE VERSION (UPDATE)" by "METRIC VALUE". The code draws **one bar
per quality metric** (`slot = (W - padL - padR) / metrics.length`) against a locked count of
**offending activities**; the version is the animation frame, not the X axis. `wbs.js` — spec:
"PERCENT COMPLETE (%)"; the left axis is **SPI(t)**, a ratio against a 1.0 on-plan reference.
`margin.js` is the one the spec got right. That is now 6 of 8 checked modules wrong, which is the
evidence behind this ADR's rule rather than an anecdote supporting it.
