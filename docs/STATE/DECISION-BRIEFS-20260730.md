# Decision briefs — the three operator decisions gating rank 12 (2026-07-30)

> Three decisions block rank 12's remainder (the `▦`/`⤓`/`⛶` toolbar + read-me line sweep on
> `/margin` and `/workbench`) and the AXIS-TITLES completion. HANDOFF marks all three "do NOT
> invent answers — ASK." This document is the asking: for each decision, the verified current
> state, the genuinely viable options with honest tradeoffs, and a recommendation. Method: three
> parallel researchers + three adversarial cross-checkers (every brief re-verified against the
> actual files), then lead re-verification of the load-bearing claims (ADR-0240). Every file:line
> below was read, not remembered. **Nothing in this document changes code — the operator picks;
> the picked option then lands per the normal per-PR workflow with its own ADR.**

---

## Decision A — AXIS-TITLES batch 3b: what scope?

**What must be decided.** Five modules remain in the `PENDING` ledger
(`tests/web/test_axis_titles.py:106-119`): `margin_dashboard.js`, `sra.js`, `sra_jcl.js`,
`sra_ssi.js`, `volatility.js`. Reaching empty is AXIS-TITLES' recorded completion signal.
ADR-0311:83-87 records that rank 12's `/margin` toolbar cannot close until `margin_dashboard.js`
is captioned. The operator picks the batch slice (and settles four sub-questions the record
leaves loose, below).

**Verified state that shapes the choice:**

- **The recorded `y2Label` prediction does not survive the code.** ADR-0302:63-64 says "`sra.js`
  and `margin_dashboard.js` can use it when their batch lands" — but `sra.js`'s CDF has a single
  probability Y axis (`sra.js:50-57`), and `margin_dashboard`'s burn-down has ONE scale carrying
  two named units ("Effective margin (wd)" / "Contingency (days)" bars, `:157/:162`), not a second
  axis. Per ADR-0301 ("captions derive from the rendering code"), batch 3b should be authorized to
  drop `y2Label` where the code says so.
- **Local quasi-captions already exist** and are the second-convention fragmentation the ledger
  guards against: `margin_dashboard.js:227/:297` draw `"status date"` at (R, B+12) outside the
  helper; `volatility.js:314` draws its own centred dwell X caption. Batch-1 precedent (histogram's
  third convention, ADR-0301:70-79) is to retire them into the helper.
- **The freeze surface is larger than the 16-site census.** New call sites re-baseline the
  round-contract md5 constants (`tests/web/test_r11_panel_contract.py:452-518`, `assert len(sites)
  == 16`), AND `volatility.js` is byte-frozen WHOLE via `PAGE_SCRIPTS` (`:436-444`), so captioning
  it re-baselines that too. Line-neutral editing (the ADR-0310-round drift.js trick,
  SESSION-LOG.md:9199-9206) is impossible when *adding* call sites — the re-baseline must be
  deliberate and named in the PR.
- **The four-theme visual pass walks only** `('/curves','/scurve','/cei','/trend','/forecast')`
  (`tests/web/test_axis_titles_visual.py:73`); the 3b pages must be ADDED to `PAGES` in the same
  change that closes their measured collisions (the file's own `/resources` protocol note,
  `:55-69`). Expect the batch-3a collision family: the JCL football has data labels in ALL FOUR
  plot corners (`sra_jcl.js:114-123`) — every fixed caption anchor is occupied; the fix is
  ADR-0303's "data label yields" clamp, never a placement change.
- **Where to record non-axis visuals:** `00_REFERENCE_INTAKE/UI-INVENTORY.md` is now a package
  rename plan (its former §2 role is gone), so per-visual "not an axis chart" calls (gauge,
  tornados, leaderboards, heatmap, strips, ribbon, FICSM/percentile strips, the DOM matrices that
  already carry `.nm-xaxis`/`.nm-yaxis` labels) are recorded in the batch ADR itself.

**Options.**

| # | Option | For | Against |
|---|---|---|---|
| A1 | **`margin_dashboard` first (3b-i), rest as 3c** — *recommended* | Smallest reviewable diff; unblocks the only named downstream dependency (ADR-0311's `/margin` toolbar); matches the shrinking-batch precedent (5→3→2 modules) | `PENDING` stays at 4; batch overhead (visual pass, re-baselines, wheel + installers) paid again later; extends the deferral pattern HANDOFF itself flags |
| A2 | **Full batch 3b now** | Empties `PENDING`, completes AXIS-TITLES in one sitting | Hardest batch on record: ~7 plot rects in volatility alone, the football's four occupied corners, two tornados with no conventional corners; largest diff + most re-baselines to review at once |
| A3 | **Toolbar without captions** (defer 3b again) | Fastest rank-12 checkbox; precedent exists (/volatility got toolbars in round 11 while PENDING) | Contradicts ADR-0311's recorded dependency and DESIGN-SYSTEM §0 Law 2 ("a chart without … is not done"); spends a round without shrinking PENDING. Not recommended |

Either A1 or A2 should carry the **triage discipline**: caption only visuals with a true axis pair
(the code decides, ADR-0301), and record every "not an axis chart" call with its reason in the
batch ADR.

**Sub-questions to confirm with the slice** (each one sentence in the reply is enough):
1. Drop `y2Label` where the code shows no second scale (treat ADR-0302's line as a prediction,
   not a requirement)?
2. Retire the local quasi-captions (`"status date"` ×2, dwell) into the helper in the same PR,
   nudging `margin_dashboard`'s legends off the (L+4, T+2) Y-caption corner?
3. Tornados (`sra.js:218/:317`): axis charts to caption, or labeled row charts recorded as
   not-axis-charts? (Their name gutter and bar-end labels sit on the caption anchors.)
4. Deliberate re-baseline of the frozen md5 constants (16-site census + `PAGE_SCRIPTS` for
   volatility) is the accepted procedure for a batch that ADDS call sites — confirm.

---

## Decision B — the `NO_SVG_AXES` DOM caption mechanism (ADR-0298's deferral)

**What must be decided.** 13 modules (`tests/web/test_axis_titles.py:71-85`) render DOM
tables/grids or the HTML-Gantt family — no SVG axes. ADR-0298:98-100 deferred their caption
mechanism as "a separate design decision, deliberately not invented here." `/workbench`
(`workbench.js`) blocks rank 12 on it.

**Verified state that shapes the choice:**

- **No graduation path exists today**: "captioned" is detected only by the
  `SFChartFrame.axisTitles(` regex (`test_axis_titles.py:121/:143`), and the mirror test asserts
  NO_SVG_AXES entries render no SVG at all — the chosen mechanism needs its own executable
  detector designed with it.
- **`.ch-at` cannot be reused verbatim**: it styles SVG `fill` (`base.css:43-44`); DOM text needs
  `color:var(--muted)` — a sibling class or an addition.
- **DESIGN-SYSTEM already carves out tables**: §3:78 "Tables get `⤓ EXCEL` only" — a data TABLE is
  not owed the full ▦/⤓/⛶ triple. Nearly all 13 render tables/grids, and `/workbench` already
  ships its Excel exports (`app.py:13259-13260`, `workbench.js:179`), so the owed rank-12 work
  there is ▦ DATA / ⛶ ENLARGE / read-me line at most — smaller than assumed.
- **The spec's proposed workbench captions are half-redundant**: Y "METRIC (LIBRARY)" restates the
  literal `<th>Metric</th>` (`workbench.js:54`); X "SCHEDULE VERSION" appears in NO header cell
  (the version columns are headed by concrete per-version labels) — so the X dimension is the one
  genuinely unnamed today.
- **Overlay hazards are real, measured**: `.wb-ribbon-wrap` is `overflow-x:auto` (`base.css:498`)
  and both workbench tables have sticky header rows (`:501/:517`) — positioned overlay text over a
  scrolling table re-opens the collision problem in a medium where cells cannot yield.
- **The SFGantt tiered-timescale primitive is shared**: among the 13, exactly `driving_path.js`,
  `path.js`, `path_evolution.js`, `sra_grid.js` consume it — one caption slot in the shared
  timescale header labels four modules at a stroke (non-visual chrome consumers are exempt).

**Options.**

| # | Option | For | Against |
|---|---|---|---|
| B1 | **Native `<caption>` on each data table** + one label slot in the SFGantt timescale header — *recommended* | Best accessibility (announced, programmatically associated) and print behavior (in-flow); honest — captions the visual as what it is, not a pretend X/Y plot; styled from the existing token | Visible placement differs from the SVG corner convention — needs the ADR to record "one convention per medium"; needs a new ledger detector |
| B2 | **Headers are the axes** — declare th rows/columns the labeled axes; satisfy the instrument law via panel anatomy (h2 + read-me + owed toolbar) | Fastest unblock; zero new convention; asserts nothing false | A decision NOT to add captions; SVG charts carry corner captions their DOM siblings lack; gantt's real time axis stays named only by tier headers; needs an ADR so the ledger reads "closed by interpretation," not abandoned |
| B3 | **Mirrored DOM overlay helper** (positioned spans mimicking the SVG corners) | Maximum visual consistency with the SVG family | Overlay over scrollable/sticky tables; worst case for print + screen readers; risks asserting an X/Y pair drill grids don't have — the false-assertion class ADR-0301 forbids |
| B4 | **Per-family hybrid** (Gantt family: timescale-header caption; tabular family: native `<caption>`) | Most honest per-visual; the gantt slot covers 4 modules at once | Explicitly TWO conventions; slowest (two mechanisms, two detectors, two visual-pass extensions) |

Note B1 and B4 are close cousins — B1 as written already gives the Gantt family the timescale-slot
treatment, so the real spread is: caption natively (B1), don't caption (B2), or overlay (B3).

---

## Decision C — `data-noprint`: which CSS mechanism

**What must be decided.** The attribute is set at 11 literal sites — 8 in `app.py` (incl. the
shared `_shell_tools()` helper, 57 call sites, so it lands on nearly every contract-page panel
head) and 3 in vendored JS (`trend.js:51/:214`, `curves.js:125`) — but **zero CSS rules reference
it**, so every marked control still prints. DESIGN-SYSTEM §7's DoD checkbox ("controls hidden in
print (`data-noprint` / `.cf-bar` pattern)", `:114`) is unsatisfiable until a rule lands
(ADR-0311:88-90). ADR-0305:167-170 measured it and left it "decision-ready, not shipped" because
it changes ten-plus merged contract pages at once.

**Verified state that shapes the choice:**

- **A prior ADR already half-answers this.** ADR-0076 (2026-06-18, accepted) records the decision
  that the print mechanism is *"a `@media print` stylesheet (base.css)"* — and
  `tests/web/test_accessibility.py:102-109` pins the print rules IN `base.css` specifically
  (fetches `/static/base.css`, asserts `@media print`, `#askPanel`, `break-inside:avoid`, …). A
  separate `print.css` would contradict a recorded decision and fail an existing test unless both
  were deliberately changed.
- **`!important` is required, twice over**: `app.css:663` `.tile-actions{display:flex}` loads
  later and would win the cascade; and even inside `base.css`, `.sf-tools{display:inline-flex}`
  sits at `:548` — AFTER the print block at `:145-161` — and ties `[data-noprint]` on specificity.
  The A5 block's existing idiom is already `!important`.
- Two carriers (`trend.js:214`, `curves.js:125`) are already print-hidden via the parent
  `.viz-controls` rule — the attribute there becomes harmless redundancy.

**Options.**

| # | Option | For | Against |
|---|---|---|---|
| C1 | **One global rule in base.css's A5 block**: `[data-noprint]{display:none!important}` — *recommended* | The exact "one line closes it" fix ADR-0305 measured; consistent with ADR-0076 and the accessibility test; theme-independent (print block forces black-on-white); self-maintaining (new controls opt in by attribute); keeps §7's wording true as written | Changes print output on ten-plus merged pages at once — needs its own small PR with print-preview verification |
| C2 | **Dedicated `static/print.css`** | Room for a future full print design | Contradicts ADR-0076's recorded mechanism and `test_accessibility.py:102-109` as written; two print homes invite drift; bigger diff than the defect warrants |
| C3 | **Extend the class enumeration, retire the attribute** | Matches the block's current enumerated style | Enumerations rot; §7's wording must change; stripping the attribute touches app.py + two frozen-sensitive JS files for zero visible gain |
| C4 | **Per-page with the rollout** | One-page-per-PR discipline | The attribute selector is inherently global; the ten pages are ALREADY merged; maximizes how long the DoD stays unsatisfiable |

**Sub-questions to confirm with the pick:**
1. Are the `/analysis` src-bar **version chips** (`app.py:10510-10511`) meant to hide in print too?
   They carry the attribute today (hiding them is what the markup already declares), but they are
   navigation, not controls.
2. Verification bar: four-theme print-preview measurement, or a single-theme print check (the
   print block overrides theme tokens, so single-theme is defensible)?
3. Keep the now-redundant attribute on the two `.viz-controls` carriers for uniformity? (Harmless
   either way; one sentence in the ADR.)

---

*Prepared 2026-07-30. #487 is merged (`c937ad9`, v1.0.131, ADR-0313) with post-merge CI green and
the full suite read green on the committed tree (`3067 passed, 24 skipped`, exit 0). These three
decisions are the only thing between rank 12's remainder and done.*
