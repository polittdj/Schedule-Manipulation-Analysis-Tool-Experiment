# ADR-0444 — the timescale header's edge bands are clamped to the axis (they overlapped and bled past it)

- **Status:** Accepted
- **Date:** 2026-09-01
- **Version:** 1.0.226
- **Extends:** ADR-0441 (long-span header work — density adaptation promoted the UNITS but left the
  band GEOMETRY at the two ends unclamped), ADR-0440 (the `timescale.js` load-path sanitizer).

## Context

The operator reported, with a screenshot of their 2,301-activity / 12.3-year IPMR on `/path`, that
"the timeline headers are still screwed up" when two files are open.

Probing that page found a defect in the header's band geometry that is present on **every** long
span, at **every** width, with one or two files loaded.

## The defect

`tierBands` clamped one edge and measured the width from the other:

```js
var left  = axis.x(cur.getTime());
var right = axis.x(next.getTime());
var w = Math.max(1, right - left);                        // width from the UNCLAMPED edges
out.push({ left: Math.max(0, left), width: w, … });       // left clamped, width not
```

A span almost never starts or ends on a clean unit boundary, so the first and last bands are
**partial** units — but both were drawn a **full** unit wide. `right` was never clamped to
`axis.width` at all.

Measured on a 2,301-activity, 12.3-year synthetic look-alike at 1920×1080 (two files loaded):

| | before | after |
| --- | --- | --- |
| first band `2017` | `left 0, width 81` → 0–81px, while `2018` starts at **47px** — a **34px overlap**, two year labels drawn over each other | `left 0, width 47` — meets `2018` exactly |
| last band `2029` | `left 945, width 81` → right **1026px**, **57px past** the 969px axis, bleeding over the column beside it | `left 945, width 24`, right **969** — flush |
| header box | `scrollWidth` **1026** vs `clientWidth` **969** | `969 == 969` |
| band rights | `47, 129, … 945, **1026**` | `47, 129, … 945, **969**` — tiles exactly |

The overflow scales with the width: 11px at a 240px axis, 33px at 488px, 57px at 969px, 95px at
1609px. It is not a long-span-only artifact — any span whose ends are not on a unit boundary hits
it, which is essentially all of them.

## Decision

Clamp **both** edges and take the width **from the clamped edges**:

```js
var l = Math.max(0, left);
var r = Math.min(axis.width, right);
var w = Math.max(1, r - l);
```

The label decisions (`def.narrow` at `< def.minPx`, drop at `< 9px`) now see the **true visible**
width, which is the more correct input: a 24px edge sliver narrows its label to `'29` instead of
claiming a full year's worth of room, and a sub-9px sliver drops it.

## Proof (QC-1)

- **Red first**, by name: `test_tier_bands_stay_inside_the_axis_and_never_overlap` observed FAILING
  on the pre-fix tree — `fitted: g-tier g-tier-yr runs 33px past the axis (488px) — last band
  {'label': '2026', 'left': 467, 'width': 54}`.
- **Green** after; the assertion covers both the fitted and the as-opened view, because the two
  compute different axes and the pre-fix code was wrong on both.
- **Mutation battery, each clamp proved INDEPENDENTLY red by name** — reverting only the right
  clamp (`var r = right`) → *"runs 33px past the axis"*; reverting only the left clamp feeding the
  width (`r - left`) → *"g-tier-yr has bands overlapping by 23px — first band {'label': '2017',
  'left': 0, 'width': 55}"*. Neither mutation is caught by the other's assertion, so the test has
  two sets of teeth rather than one.
- **Neighbour veto**: 47 browser tests across `test_long_span_gantt_browser`,
  `test_timescale_dialog_browser`, `test_path_row_windowing_browser`, `test_gantt_consistency` and
  `test_dd_line_render` stayed green; the byte-pin/line-index modules that glob `static/*.js`
  (`test_r11_panel_contract`, `test_axis_titles`, `test_dd_line_ledger`, `test_accessibility`,
  `test_launch_sequence`) are unaffected — swept by PIN SHAPE, not by filename, which is the
  ADR-0443 lesson applied.

## What this ADR does NOT claim

**The operator's reported symptom was not reproduced.** Their screenshot shows a three-row header
whose year labels appear to cascade; every reproduction here — their row count (2,301), their span
(12.3 years), two files loaded, widths swept 1100→2560 — produced a structurally sound two-row
header with zero page errors. Their stack collapses to two rows in this build because
`effectiveStack` promotes Months→Quarters at that span and dedupes against the Quarters tier.

So this is a real defect found **in** the component they reported, fixed on its own merits; whether
it is the whole of what they are seeing is **UNVERIFIED**. What would settle it, from the machine
showing the fault: (1) the version banner — whether they are actually on ≥1.0.225 or on a build
predating the ADR-0441 header work; (2) `localStorage.getItem("sf.timescale.v1")`, the persisted
tier configuration that decides the row count; (3) a dump of `.g-scale-tiered .g-tier` class,
computed `top`, and the first few `.g-band` label/left pairs. Those three are recorded in the
handoff so the next session asks for them rather than re-deriving.

## Consequences

- Every page that draws the MS-Project timescale header (`/path`, `/driving-path`, `/evolution`,
  `/analysis`, `/sra`) gains a header that ends flush with its axis instead of bleeding over the
  next column, and stops drawing two labels on top of each other at the left edge.
- No engine, parity or metric surface is touched — this is band geometry only (Law 2 unaffected).
