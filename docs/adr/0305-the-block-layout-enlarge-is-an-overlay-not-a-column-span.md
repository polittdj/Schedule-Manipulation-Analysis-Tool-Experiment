# ADR-0305 — The block-layout ⛶ is an overlay, not a column span

* Status: accepted
* Date: 2026-07-29
* Closes: **ADR-0304's open item 3** (`.is-big` global redefinition), which that ADR deferred to an
  explicit operator decision. The operator's amendment to standing requirement 2 — *"prove every
  control changes a measured box, not just a class"* — is what forces the decision now: round 11
  adds the contract to four more pages whose panels are block-flow, so either the mechanism is
  fixed or the round ships more controls that flip a label and move nothing.
* Amends: **`docs/DESIGN-SYSTEM.md` §5** — the ⛶ line claimed the enlarged state "persists per
  persist.js". The overlay state is deliberately **not** persisted (see *Consequences*), and the
  design-system line is corrected in the same PR rather than left to become the next round's
  phantom bug.

## Context

ADR-0304 established, by measurement, that the panel contract's ⛶ ENLARGE does nothing on a
block-layout panel. `base.css:557` carries the only rule for the class:

```css
.is-big{grid-column:1/-1}
```

`grid-column` binds only on a **grid item**. Round 10 fixed the mosaic case
(`.mosaic .tile.is-big .chart-host{height:74vh}`) and left the block case open, because any global
redefinition touches ~9 merged pages and standing requirement 5 forbids moving an axis caption
without a decision.

Round 11 re-measured merged `main` before changing anything — real clicks, `getBoundingClientRect()`
before and after, four themes, 1440x900, on a tree verified byte-identical to `origin/main`
(`base.css` md5 `ee43ca3c…`, `panelkit.js` `cf33f52f…`):

```
SUMMARY   moved=68   NO-OP=192
/  0/4 · /portfolio 0/8 · /compare 0/12 · /trend 0/20 · /evm 0/20 · /cei 0/8 · /scurve 0/8
/ribbon 0/4 · /integrity 0/8 · /forecast 0/20 · /scorecards 0/16 · /analysis/{name} 0/64
/curves  12/12  <- curves.js's OWN overlay, not `.is-big`
/performance 56/56  <- `.mosaic .tile` grid items: the only case where the class works
```

Every one of the 192 no-ops reports `isBig:true, label:"⛶ SHRINK"` on a box that never moved. That
is the exact shape ADR-0304 named: **the machinery ran; nothing happened.**

## Attribution: pre-existing on merged `main`, not a round-10 or round-11 regression

Stated first and explicitly, because round 10 got this wrong and the correction is why the rule
exists. `base.css:557` and `app.css:636-645` are byte-identical to `origin/main`; `git diff
origin/main -- base.css app.css` was empty when the 192 no-ops were measured. Nothing in this
round's tree could have introduced them. **A finding can be REAL AS AN OBSERVATION and WRONG AS AN
ATTRIBUTION, and each implies a different fix.**

## The project already had five enlarge vocabularies

Before adding anything, the round counted what exists:

| vocabulary | owner | geometry |
|---|---|---|
| `.is-big` | panelkit.js (the contract) | `grid-column:1/-1` — grid items only |
| `.mosaic .tile.tile-expanded` | mission.js | column span + `74vh` host |
| `.sf-tilebox.tile-expanded` | curves.js, scatter.js, margin.js | `position:fixed;inset:4vh 3vw;z-index:220` |
| `.charts .chart.tile-expanded` | trend.js | `flex-basis:100%` |
| `.cf-frame.cf-max` / `:fullscreen` | chartframe.js | viewport fit, z-index 9999 |

**The fix borrows the third rather than minting a sixth.** A contract is a vocabulary, not a stamp;
reusing the page's existing mechanism is the standing rule, and round 10's `/performance` failure is
what happens when a second mechanism shadows a working one.

## Decision

**1 — `static/base.css`, immediately after the KEPT `.is-big{grid-column:1/-1}`:**

```css
.panel.is-big:not(.tile):not(:has(.sf-tilebox)){
  position:fixed;inset:3vh 12px;z-index:220;margin:0;overflow:auto;
  box-shadow:0 18px 60px rgba(0,0,0,.45)}
```

It applies **only in the user-toggled state**, so no default render moves — verified across 128
pristine-vs-patched measurements (panel + chart-host + svg rects, every panel, every route, four
themes): **0 differences**, and the untoggled server HTML byte-identical on 13/13 routes.

**The inset is load-bearing, not cosmetic.** Copying the tilebox's literal `inset:4vh 3vw` was
measured and **rejected**: the **daylight** theme has no 236px left rail (`main` x=0 w=1440, panel
**1384px**) while console/apollo/jarvis do (`main` x=236 w=1204, panel 1148px). A `3vw` inset yields
a 1354px box — *narrower than a daylight panel* — measured on `/scurve` daylight as panel
`1384x752 → 1354x828` with the chart svg `1354x436 → 1324x426`. **⛶ would have made the chart
smaller in one of four themes**, which is precisely the `/performance` failure ADR-0304 exists to
prevent. A fixed 12px gutter is theme-independent: 1416px, wider than every panel in every theme.

**Both exclusions are structural, not editorial.** Each is a property of the DOM, not of a page name:

* `:not(.tile)` — a `.mosaic .tile.panel` already has a **working matched pair**. Measured:
  `/performance` toggled rects **0 of 56 differ** from pristine; `/volatility`'s ten tiles keep
  `position:static` and take the grid path (566x430 → 1148x756, host 536x340 → 1118x666).
* `:not(:has(.sf-tilebox))` — `/curves` and `/analysis`'s Activity-scatter panel already lift their
  own inner shell into this identical overlay; without the exclusion a fixed box would nest inside a
  fixed box. Measured: they stay `position:static` (jarvis `relative`) in the toggled state.

**2 — the `@media print` reset**, inside the existing block:

```css
.panel.is-big{position:static!important;inset:auto!important;box-shadow:none!important;overflow:visible!important}
```

Required, not optional: measured under `emulateMedia({media:"print"})`, a toggled panel stayed
`position:fixed` at 1416x846 in all four themes and printed as a floating card over the report.

**3 — `static/panelkit.js`:** an overlay-only **single-open invariant** and **Escape-to-close**.
Measured justification: two block overlays open at once land on the identical rect, and
`elementFromPoint` over the lower panel's own ⛶ SHRINK returned the *upper* panel's `.panel-head` —
the control was unreachable and only a reload recovered it.

The invariant asks the browser `getComputedStyle(panel).position === "fixed"` rather than
re-deriving base.css's selector in JS. **One owner for the rule**: a JS copy of the selector would
silently desync the moment the CSS changed. It is also why the invariant is *overlay-only* — mosaic
tiles stay in the flow, do not obscure each other, and comparing two enlarged Mission-wall tiles
side by side is a working round-10 capability that a blanket invariant would have destroyed
(verified preserved: `/performance` tiles 4+5 both open in all four themes, unaffected by Escape).

## The results

```
                       pristine        patched
block-layout ⛶          0 MOVED        184 MOVED
regressions            —              0 MOVED -> NO-OP
remaining NO-OPs       192            4   (= /analysis panel 5 x 4 themes, the tilebox
                                           exclusion firing exactly where intended)
```

Literal, enlarged state, all four themes: `/evm` "Schedule performance" console `1148x512`,
daylight `1384x478`, apollo `1148x512`, jarvis `1148x512` → **`[12,27,1416,846]`, `position:fixed`,
`z-index:220`** in every one. `/scurve`'s chart svg grows in every theme, daylight included
(`1354x436 → 1386x446`).

## Two decisions that must be stated, not discovered

**`/path`'s `.panel.status-stack` panels take the overlay.** They are grid items (parent `.ws-bars`
is `display:grid`) but they are not `.tile`, so the rule catches them: measured 567x142 → 1416x846
instead of the 1148x142 `grid-column:1/-1` would give. **This is accepted deliberately.** The
exclusion criterion is *"has a working matched pair with a height-clamped chart host"*, not
*"parent is a grid"*. `.ws-bars` has neither.

**The honest cost, in these words: a panel taller than the overlay gets SHORTER, with an internal
scroller. It is a focus view, not a magnifier.** Measured worst cases: `/analysis` "Interactive
analysis" 1148x1781 → 1416x846; `/path`'s workspace 1148x932 → 1416x846 (scrollHeight 885 >
clientHeight 844). Width always grows — across 48 scale × viewport × theme combinations (90–175%,
four viewports) the overlay was wider in **48 of 48**, and shrank in **0**. Said out loud here so
the next audit does not file it as a bug.

## Consequences

* **Not persisted.** `persist.js` does not remember the enlarged state, deliberately — restoring a
  page with a modal already up is worse than not restoring it. `DESIGN-SYSTEM.md` §5 is corrected in
  the same PR.
* **No scroll lock and no focus trap**, consistent with the already-shipped `.sf-tilebox.tile-expanded`.
  Focus is never orphaned (the ⛶ button travels into the overlay with its panel and the `--focus`
  ring is correct per theme), but Tab reaches content behind the overlay. Recorded as a decision.
* **`:has()` browser floor** — Chrome 105+, Safari 15.4+, Firefox 121+. Verified in the vendored
  chromium; the tool is local-only and ships no other browser floor below this.
* `.load-overlay` already occupies `z-index:220`. Same layer, never concurrent — noted so neither is
  "tidied" independently.
* `.sf-drawer` keeps its `max-height:170px` inside a 846px overlay. Follow-on polish, deliberately
  not bundled.

## Adjacent pre-existing defects found while measuring — reported, not silently absorbed

1. **`[data-noprint]` has zero CSS rules anywhere in the tree.** `grep -rn "data-noprint"
   static/*.css` returns nothing, while the attribute is set on 10+ elements; `.sf-tools` computes
   `display:flex` under print media. `DESIGN-SYSTEM.md` §7 requires those controls hidden in print.
   One line closes it — but on ~10 merged contract pages, so it is **decision-ready, not shipped**.
2. **`/analysis/{name}` panel 5 carries TWO ⛶ controls** — the panel-head `⛶ ENLARGE` (`data-sf-big`,
   inert) and scatter.js's `⛶ Enlarge` (`.tile-expand`, working). Different casing, one dead. The
   same shadowing shape as round 10's `/performance`. Pre-existing; not fixed in rank 11.
3. **`/driving-path` overflows horizontally** — `documentElement.scrollWidth` 1719 vs clientWidth
   1440; the 11-column drill table overflows `main` instead of scrolling in its own container.
   Pre-existing (identical on both trees) and a `driving_tiers.js` change, which is in the
   axis-caption freeze set.
4. **The `title` → `data-sf-hint` migration is undocumented in the contract.** The hint machinery
   strips `title` off every `[data-sf-excel]`/`[data-sf-big]` at runtime and re-homes it as
   `data-sf-hint`/`data-sf-title`. Established behaviour, not a defect — but any loaded-terms or i18n
   harvester reading `title` alone silently misses every ⤓ hover string on all ten contract pages.

## Instrument note — requirement 5's baseline was itself wrong

The round's first axis-caption instrument hashed a balanced-paren slice starting at each
`axisTitles(` match. It **missed one of `trend.js`'s five call sites** (a nested paren inside a
string broke the scan) and **included `chartframe.js`'s function definition**. It was retired
mid-round and replaced by a whole-file md5 census of the 12 files owning the **16**
`SFChartFrame.axisTitles(` call sites (+ `chartframe.js`) — unambiguous, reproducible, and strictly
stronger: if the file is byte-identical, no caption in it can have moved. **A gate is only as good
as the instrument behind it, and an instrument that cannot reproduce its own baseline on an
unmodified tree is worse than none** — it teaches the next agent to ignore a red result.

## The generalisable lesson

ADR-0304 said: verify the EFFECT, not the MECHANISM. This ADR adds the corollary the fix itself
nearly failed on: **when you give a control an effect, measure that effect in every theme and at
every scale, because the obvious geometry can be right in three of four and wrong in the fourth.**
The rejected `4vh 3vw` inset would have passed any single-theme check, shipped a control that
shrank the chart on daylight, and reproduced round 10's failure inside its own fix.
