# ADR-0330 — AXIS-TITLES batch 3c-ii: the on-demand SRA panels join the caption convention (the finale)

Status: accepted (2026-08-01)
Implements: the AXIS-TITLES ledger (ADR-0298 → 0303 → 0325 → 0329) — final batch; PENDING
reaches EMPTY, the recorded completion signal
Builds on: ADR-0329 (the 3c split and its recorded reason), ADR-0303 (the caption stays fixed,
the DATA yields), ADR-0326 (one convention per medium), the ADR-0325 dedicated-serve precedent
(`served_margin`)

## Context

Batch 3c-i (ADR-0329) deliberately left `sra_jcl.js` + `sra_ssi.js` in `PENDING`: their charts
render only after a Run button click, so the measured visual pass — the batch acceptance — could
not see their captions. The recorded prerequisite was "teach the harness to click."

Surveying fresh on this tree (the ADR-0311 lesson) found the prerequisite was UNDERSTATED in one
load-bearing way: **the golden Project2/Project5 pair cannot exercise these panels at all.** The
JCL panel is gated on a cost-loaded schedule (`cost_loaded_total > 0`, the honest-SCL rule,
ADR-0269) and the golden pair carries no budgeted cost — `/sra` on the golden serve renders the
requirement notice, **no `#jclRun`, and no `sra_jcl.js` script tag**. And with no Best/Worst
spread set, the SSI run is a point mass: `/api/sra/ssi` returns a ONE-point S-curve and a
one-bin histogram — captions on a degenerate chart would prove almost nothing. Clicking alone
was never enough; the clicked cell needs a serve that can actually chart.

## Decision

1. **Four charts join the shared helper** (`SFChartFrame.axisTitles`, 24 → 28 call sites, a
   DELIBERATE re-baseline with the prior 24 entries byte-untouched):
   * `sra_jcl.js` football — x "Finish date", y "EAC".
   * `sra_jcl.js` cost S-curve — x "EAC", y "Cumulative probability".
   * `sra_ssi.js` S-curve — x "Finish date", y "Cumulative probability".
   * `sra_ssi.js` histogram — x "Finish date", y "Simulated finishes".
   Both modules render inside fetch callbacks, so the ADR-0316 parse-time/defer trap does not
   bite (script order checked anyway, per the standing note: chartframe.js is layout-global and
   loads far earlier).

2. **Recorded NOT-axis-charts (decision A1) — no call, deliberately:** the FICSM SCL/CCL/JCL
   strip (a labeled 0–100% bar strip, each bar named and valued in-row — no X/Y scale to name)
   and `sra_ssi.js`'s 5×5 Risk/Opportunity matrices (natively-labeled HTML tables — ADR-0326's
   other medium, already carrying "Likelihood of Occurrence" / "Consequence of Occurrence").

3. **The football's corner collisions close where caused — the data yields (ADR-0303).** Its
   quadrant %-labels sat EXACTLY in both caption corners: the top-left label at `(ml+4, mt+10)`
   one pixel off the Y caption's `(L+4, T+9)` baseline, the bottom-right label at
   `(W−mr−4, H−mb−6)` inside the X caption's `(R, B−4)` box. Both clamp statically out of the
   bands — `mt+10 → mt+24` and `H−mb−6 → H−mb−20`, the dwell-precedent mechanism from
   ADR-0329 — keeping their corner anchors and their values; the captions never move. Static
   (not the ADR-0319 live-box remove) is deliberate: removal would delete a data label that
   collides BY CONSTRUCTION (equivalent to never drawing it), and the separation needed is
   vertical-band-only, which theme-dependent glyph WIDTH cannot affect; this chart family is
   also fixed-width (`.ssi-chart` 380px / football 420px), so user units are rendered pixels.
   The measured pass verifies all 12 theme × scale combos.

4. **The measured pass learns to click, on a serve that can chart: `served_sra`.** A third app
   instance (the `served_margin` precedent) loads a synthetic 4-task cost-loaded schedule
   (`budgeted_cost` on every working task — opens the JCL gate) with real per-task Best/Worst
   spread (`st.sra_bcwc` — real S-curves, a four-quadrant football cloud, a rendered frontier).
   A new `/sra+run` PAGES entry measures the SAME `/sra` route there with both Run buttons
   clicked. Two anti-masking guards, both strict: after clicking, EACH panel's chart host must
   grow a caption (`#ssiCharts text.ch-at`, `#jclCharts text.ch-at` — a never-suppressed wait,
   because the page's self-running CDF/histogram captions would otherwise hide a dead clicked
   panel), and a per-route caption floor (`MIN_CAPTIONS`: 12 = all six charts × 2) closes the
   remainder. The plain `/sra` cell stays exactly what ADR-0329 measured — the golden pair's
   self-running CDF + histogram, byte-identical logic.

5. **`PENDING` is EMPTY — AXIS-TITLES is complete.** The ledger stays as the triage bucket for
   any new SVG chart module (the census still classifies every module into exactly one bucket),
   and its graduation history is kept in the comment because each entry carries a re-usable
   lesson. The count test renames twenty_four → twenty_eight (a rename, not a weakening; the
   load-bearing file+digest equality is unchanged in form). Neither module is in PAGE_SCRIPTS,
   so no byte-freeze digest moves this round.

## Consequences

* The SVG caption convention now covers every axis chart in the tree: 28 helper call sites,
  zero hand-rolled captions, zero PENDING. Remaining caption work is the DOM medium's
  (`DOM_PENDING`, 7 modules — a separate, deliberate ledger under ADR-0326's B1 mechanisms).
* The caption contrast floor holds on `.ssi-svg`'s hardcoded white canvas in all four themes
  (measured: console 3.07:1 is the slimmest, daylight 5.5, apollo 3.9, jarvis 3.4) — recorded
  here because the family's white background is unusual; a future theme whose `--muted` drops
  below ~#808f9f on white will fail the measured pass on these six charts first.
* A clicked panel is now measurable; if a future module renders on demand, the harness pattern
  (CLICK_RUNS + a strict per-host wait + a MIN_CAPTIONS floor) is standing.
* The synthetic `served_sra` fixture is deliberately NOT golden-derived: the golden pair's
  cost-lessness is itself load-bearing elsewhere (the JCL gate's honest-requirement rendering,
  pinned by test_jcl_web.py) and must stay unfudged.

## Verification (all read from runs this session)

Census + freeze suites (`test_axis_titles.py` + `test_r11_panel_contract.py`): **52 passed,
2 skipped** post-change (one skip IS the emptied PENDING's parametrize — an empty parameter
set; the other the standing path.js INCIDENTAL_SVG skip). The measured visual pass
(10 pages × 4 themes × 3 scales, caption-vs-every-sibling-text): **1 passed in 103.7 s**, zero
collisions, KNOWN_COLLISIONS still EMPTY; a fast 12-combo pre-probe of the clicked cell alone
measured **144 caption renders, zero problems**. Neighbor suites (sra view / ssi-web / jcl-web /
grid / zero-margin / file-select / chart-callouts / bar-drill / accessibility): **122 passed**.
**Proved able to fail, watched:** on the pre-caption modules (stashed), the visual pass dies on
the strict wait (`TimeoutError: waiting for locator("#ssiCharts text.ch-at")`), the census
reports both modules unclassified, and the call-site freeze counts 24 ≠ 28. Statics foreground:
ruff clean · format clean (835 files) · mypy --strict clean (117 files) · bandit exit 0 ·
node --check clean. Full-suite + installer-lockstep results: SESSION-LOG.
