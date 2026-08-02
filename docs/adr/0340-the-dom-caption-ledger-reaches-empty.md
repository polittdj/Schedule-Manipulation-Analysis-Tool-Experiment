# ADR-0340 — the DOM caption ledger reaches empty

Status: accepted (2026-08-02) — Phase 3 (UI), AXIS-TITLES' final batch

## Context

ADR-0298 made every data visual name its own axes, and split the work by MEDIUM because one
mechanism cannot serve both: `SFChartFrame.axisTitles` appends an SVG `<text>`, which an HTML
table or a DOM Gantt cannot carry. Two ledgers in `tests/web/test_axis_titles.py` tracked the
remaining work — `PENDING` for SVG charts, `DOM_PENDING` for HTML/DOM visuals.

`PENDING` reached empty in ADR-0330. `DOM_PENDING` still held seven modules:

| module | what it renders | mechanism it needed |
| --- | --- | --- |
| `drilldown.js` | the shared drill MODAL's activity grid | table caption |
| `driving_tiers.js` | the driving-path tier table | table caption |
| `findings_drill.js` | a finding's cited-activity list | table caption |
| `ribbon_drill.js` | the activities behind a ribbon metric | table caption |
| `scorecards.js` | the reserve table (P50/P70/P80/P90) | table caption |
| `whatif.js` | BOTH counterfactual grids | table caption |
| `sra_risk.js` | — | **none — see below** |

### `sra_risk.js` was never captionable

It renders no visual and never could. The module contains no `createElement`, no `appendChild`,
no `innerHTML`: it is the risk form's days↔% derivation, and its entire output is writing `.value`
back into inputs the SERVER rendered plus toggling `aria-invalid`. A caption needs something to
caption. It was mis-triaged into the DOM ledger at ADR-0326 and has overstated the remaining work
by one ever since — which is precisely why these ledgers are NAMED LISTS and not counts. It moves
to `EXEMPT` ("utilities that render no data visual of their own"), re-triaged rather than captioned.

## Decision

### 1. One implementation, not six copies — `SFGantt.tableCaption`

ADR-0326 established the mechanism as an inline `el("caption", { class: "ch-atd" }, …)`. That was
fine for one caller and does not survive seven, because these modules cannot spell it the same
way — their module-local `el()` helpers take **three different signatures**:

| signature | modules |
| --- | --- |
| `el(tag, attrs, text)` | `workbench.js`, `drilldown.js` |
| `el(tag, {text})` | `driving_tiers.js`, `findings_drill.js`, `ribbon_drill.js`, `whatif.js` |
| `el(tag, text, cls)` | `scorecards.js` |

A detector regex that accepted all three would be **looser than the rule it claims to enforce** —
the standing gate-shape #4. So the mechanism is promoted to a single helper, exactly as ADR-0298
did for SVG: one call shape, one tight detector, one place the behaviour lives. `workbench.js`'s
two pre-existing inline captions convert to it, so the DOM medium has ONE convention, and a new
test asserts no module outside the helper's home may even name `.ch-atd`.

### 2. It lives in `gantt.js`, NOT in `chartframe.js` — a load-order finding

`chartframe.js` owns the SVG helper and looks like the obvious home. It is the wrong one, and the
reason is measurable rather than stylistic: **the layout emits `chartframe.js` after `</main>`**,
while every captioned table is built by a script INSIDE the body. `whatif.js` renders
**synchronously at parse time** — no fetch, no click, no `DOMContentLoaded`. A helper hung off
`window.SFChartFrame` would still be `undefined` at the instant whatif draws, so its two grids
would silently render uncaptioned while every source-level assertion in the suite stayed green.
That is the "a style test's failure mode is SILENCE" trap with a load-order fuse.

`gantt.js` is emitted in the layout HEAD, already renders the OTHER B1 caption mechanism (the
timescale slot `buildTierScale` builds from `data-ts-caption`), and is already the shared DOM
utility four of these six modules call for `fmtMDY`. Both DOM caption mechanisms now live in one
head-loaded file, and the ordering that makes it correct is pinned by a test rather than left in
a comment.

### 3. `insertBefore(firstChild)`, not `appendChild`

`<caption>` must be the table's FIRST child. The inline convention appended, which is correct only
while the caller happens to caption before building rows — and six of the seven call sites sit
next to a `<thead>`/`<tr>` append. Putting the insert in the helper means a caller cannot get it
wrong by calling late.

### 4. Caption text names the ROW UNIT

Following ADR-0326's precedent. Two are worth calling out: `scorecards.js` is the only table in
the family whose row unit is a **percentile**, not an activity — the one place the caption changes
what a reader thinks the table is. And `whatif.js`'s two grids carry **identical column headers**
on the same page, so the caption is the only thing distinguishing "took them OFF the critical
path" from "ADDED to the critical path"; the text is therefore per-table, carried in each
`initTable` config.

## Consequences

* **`DOM_PENDING` is empty.** With `PENDING` empty since ADR-0330, ADR-0298's deferral is closed
  for good: every data visual in the tree, in BOTH media, names its own dimensions. Both ledgers
  stay as triage buckets for new modules — a module may not be parked in either once it captions.
* Three new gates, each anchored to something an app change can move: the per-module detector,
  the DOM anti-fragmentation rule (only `gantt.js` may name `.ch-atd`), and the script-ordering
  pin whose failure message says to RE-DERIVE the placement rather than delete the test.
* `tests/web/js/dom_caption_harness.mjs` executes the helper against a DOM stub —
  the first-child property is the one only execution can catch.
* `tests/web/test_dom_captions_chromium.py` drives all seven captions in a real browser through
  their REAL triggers (parse-time, post-fetch, click, modal, Monte-Carlo run) and measures
  visibility in all four themes.

## Evidence

Both new modules were proved able to fail, by reverting the implementation and re-running — never
by reading the test:

| revert | result |
| --- | --- |
| `insertBefore` → `appendChild` in the helper | harness: **4 assertions fail**, incl. first-child |
| helper neutered to `return null` | chromium: **11 of 11 fail** (229 s of real timeouts) |
| `whatif.js`'s caller removed only | chromium: **5 fail, 6 pass** — each test tracks its OWN module |
| CSS: `.sf-drill-dialog{background:var(--muted)}` | modal theme rows: **3 of 4 fail** — see below |
| CSS: `caption.ch-atd{color:transparent}` | **all 8** theme rows fail (both contexts, 4 themes) |

The third revert is the one that matters for the module tests: it proves the seven are not all
coupled to a single global, which a single all-or-nothing revert cannot distinguish.

The last two matter for the STYLE tests, whose failure mode is silence — a rendered-appearance
assertion nobody has made fail is not a gate. The 3-of-4 result is worth recording rather than
smoothing over: **jarvis survived that revert**, because its broad `html[data-theme=jarvis] .panel`
rules override the dialog background before the revert can reach it. That is the known clobber
family behaving exactly as documented, and it is why the second, caption-side revert was run — it
fails all four themes in both rendering contexts, so no theme row is silently unfalsifiable.
