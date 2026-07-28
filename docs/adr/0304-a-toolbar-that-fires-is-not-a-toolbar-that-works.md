# ADR-0304 — A toolbar that fires is not a toolbar that works

* Status: accepted
* Date: 2026-07-28
* Supersedes: nothing. **Tightens standing requirement 2** (the panelkit per-page include proof),
  which passed on a control that does nothing.

## Context

Round 4 shipped `/evm` wearing the complete panel-contract toolbar markup while `panelkit.js` was
never included, so every button was inert. The lesson written down then became **standing
requirement 2**:

> **PANELKIT IS A PER-PAGE INCLUDE.** A page can wear the complete toolbar markup and be inert.
> Prove the script loads **and** click ⛶ for real, reading `is-big` back.

Round 10 satisfied that requirement on all four converted pages. The script loads, the click
lands, the class toggles, the label flips to `⛶ SHRINK`. Then the four-theme browser verifier
measured `getBoundingClientRect()` on the closest `.panel` immediately before and after each real
click, and found this:

```
/cei                      buttons= 8  visual NO-OPs= 8   console:0/2 daylight:0/2 apollo:0/2 jarvis:0/2
/resources                buttons=12  visual NO-OPs=12   console:0/3 daylight:0/3 apollo:0/3 jarvis:0/3
/forecast                 buttons=23  visual NO-OPs=23   console:0/5 daylight:0/6 apollo:0/6 jarvis:0/6
/evm?group_field=Resource buttons=20  visual NO-OPs=20   console:0/5 daylight:0/5 apollo:0/5 jarvis:0/5

console /cei       (panelW 1308->1308, panelH 745->745)
console /resources (panelW 1308->1308, panelH 238->238)
```

Not one pixel moves. The cause is one line:

```css
.is-big{grid-column:1/-1}      /* base.css:557 — the ONLY rule for the class */
```

`grid-column` binds only on a **grid item**. The measured computed `display` of these panels'
parent is `block`. The contract's ⛶ therefore does real work only inside a `.mosaic`
(`missionGrid`, `volGrid`, `perfGrid`) and is a no-op everywhere else.

**Requirement 2 passed while the feature was inert, because it asks whether the mechanism fired,
not whether anything happened.** Reading `is-big` back is precisely the assertion that succeeds
here. That is the defect this ADR exists to close.

## Attribution: this is NOT a round-10 regression

The verifier reported it as a round-10 blocker. The lead refuted that, and the refutation was
re-checked a third time against the round-9 baseline before being accepted:

```
a7a06fc:base.css:557        .is-big{grid-column:1/-1}          (identical)
a7a06fc:app.py              43 _shell_tools call sites already present
  _analysis_body, _evm_body, _scurve_body, _portfolio_body, _ribbon_body, _compare_body, …

measured on the untouched a7a06fc tree, real chromium:
  /scurve    console 2/2 NO-OP   jarvis 2/2 NO-OP   (W 1108->1108, H 751->751)
  /portfolio console 2/2 NO-OP   jarvis 2/2 NO-OP
  /integrity console 4/4 NO-OP
  /evm       console 4/4 NO-OP   jarvis 4/4 NO-OP
```

The no-op is a **pre-existing property of the merged panel contract**, shipped across ~9 pages
through rounds 1–9. Round 10 replicated the merged convention onto four more pages; it did not
introduce the defect, and it increased the instance count.

Both halves of that sentence matter, and the project has a rule for each: *"check merged `main`
before calling a pattern a defect"* (round 9), and *"a defined token is not a painting token"*
(standing requirement 1). A finding can be **real as an observation and wrong as an attribution**,
and the fix each implies is different — here, a global `base.css` decision rather than a round-10
revert.

## Decision

**1 — Requirement 2 is amended.** It now reads:

> Prove the script loads, click the control for real, **and measure that the rendered box
> actually changed**. A class read-back is not a proof: `.is-big` toggles correctly on pages
> where it paints nothing. Compare `getBoundingClientRect()` before and after the click; an
> unchanged box is a failing control even when the class and the label are perfect.

**2 — Where a page already has a working enlarge, the contract reuses it rather than shadowing
it.** `/performance` had the correct **matched pair** all along:

```css
.mosaic .tile.tile-expanded { grid-column: 1 / -1; }
.mosaic .tile.tile-expanded .chart-host { height: 74vh; }   /* app.css:636-637 */
```

Round 10 stamped `.is-big` on instead, supplying only the width half while
`.mosaic .tile .chart-host{height:340px;overflow:auto}` stayed in force. Measured: the tile widened
546→1108px, the width-proportional SVG doubled in both axes (516×266 → 1078×556), the host stayed
clamped at 340px, and ~40% of the enlarged chart — the entire X axis and every month tick — fell
below a scroll fold. **The control made the chart worse than not pressing it.**

Fixed by giving `.is-big` the tall host its sibling already had, and nothing else:

```css
.mosaic .tile.is-big .chart-host { height: 74vh; }
```

It applies **only** in the user-toggled state, so no default caption render moves — standing
requirement 5 is intact, and all 16 `axisTitles` call sites remain md5-identical to `a7a06fc`.

**3 — The global `.is-big` redefinition is deferred to an explicit operator decision, not done
silently.** Making ⛶ paint on block-layout pages means redefining the class across ~9 merged
pages, and any rule that grows chart hosts **moves captions on `/scurve`, `/curves` and `/trend`**
— which requirement 5 forbids without a decision. STOP AND REPORT is the correct outcome here, and
the measurement above is what makes the decision answerable.

## Also fixed under this ADR

* **A forensic export control must never disagree with the visual it sits on.** `/performance`'s
  per-tile ⤓ EXCEL pinned `?file=` at render time, while the stepper re-binds G1–G5 with no
  reload — so after one step the button beside a chart exported a *different version's* datasets:

  ```
  state0  caption "file 2 of 2 — Hard_File_updated3.mpp.xml"  export ?file=Hard_File_updated3…
  after   caption "file 1 of 2 — Hard_File.mpp.xml"           export ?file=Hard_File_updated3…
  CHART REBOUND: True
  ```

  `performance.js::setVersion` now re-points every `#perfGrid [data-export]` at the stepped file.
  Both stepped URLs verified live: `200 / PK / 6789 B` and `8984 B`.

* **The `/forecast` drift table mislabelled four columns.** 5 `<th>` against 6 `<td>` per row, so
  the as-scheduled date read under "Completion rate", the rate under "Earned schedule", and the
  earned-schedule date was unheaded. Pre-existing and identical on `a7a06fc`; it changes no number
  but misattributes four dates on a testimony-facing page. The missing `<th>As-scheduled</th>` is
  restored, and the test now asserts the header **structurally** (`<th> count == <td> count + 1`)
  so the shape cannot drift again.

* **A false exclusion comment became documented debt.** `test_axis_titles_visual.py` excluded
  `/resources` because the page "renders no chart" with the golden fixtures. That was true only
  because `resources.js` drew synchronously ahead of `chartframe.js` and died on
  `SFChartFrame is not defined` (round-9 tree: `svg children 0`). Round 10's one-word `defer`
  fixed that — `svg children 62`, both captions present — which **made a previously invisible
  layout defect visible**: the X caption `Period (month commencing)` sits over the last rotated
  month ticks in 8 of 12 theme×scale combos (console@1 ~36×2px, apollo@1 ~40×4px). Per
  requirement 5 `resources.js` was **not** adjusted (md5 unchanged); the page stays excluded, but
  now for a recorded reason with the ADR-0303 remedy named (move the *label*, not the caption).

## Consequences

* Requirement 2 now costs one extra measurement per control and catches a whole class of
  cosmetically-perfect dead buttons.
* ⛶ remains a no-op on block-layout pages until the operator rules on the global redefinition.
  That is a known, measured, written-down gap — not a silent one.
* Two open items carry forward with decision-ready measurements: the `/resources` X-caption
  collision, and the `/performance` `SFChartFrame` first-paint race (where `defer` is verified to
  unblank both quad charts but introduces a caption collision that must be closed in the same
  change).

## The generalisable lesson

**Verify the effect, not the mechanism.** Every check in this project that has ever passed while
the feature was broken shares this shape: it asserted that the machinery ran. The script loaded;
the class toggled; the token was defined; the caption existed. None of those is the thing the
operator sees. Ask what would be *visibly different* if the feature worked, and measure that.
