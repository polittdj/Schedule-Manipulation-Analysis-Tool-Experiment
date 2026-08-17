# ADR-0407 — ENG-DEAD-01 closes: `actual_start_driven` reaches the analyst as an INFO disclosure and a path-grid column

**Status:** Accepted, **partly superseded by ADR-0413** · **Date:** 2026-08-15 ·
**Closes:** ENG-DEAD-01 (audit 2026-08-13) · **Ships:** v1.0.206 (wheel + nine installers
rebuilt; `recommendations.py`, `help.py`, `driving.py`, `path.js` all ship).

> **CORRECTION (ADR-0413, REC-01).** The Decision section below claims that
> `Category.OPPORTUNITY` keeps this finding from "ever becoming a threat row or a recovery
> action". That was verified against `web/risks.py` only, and is **false of the tree**:
> `ai/briefing.py` applies no category gate, and `_quantify` quantified the finding like any
> other. Measured on v1.0.210, the disclosure reached the briefing's "Potential recovery"
> column (`20 wd`), its "Expected effect" column (`20 wd`), its recoverable total ("up to
> about 20 workday(s) … potentially recoverable") and the `/risks` card at 20/25 `rk-extreme`.
> What actually holds the separation is `Finding.is_disclosure` (ADR-0413). Everything else
> below — the channel, its separation from `date_driven`, the grid column, the dictionary
> entry — stands.

## Context

ADR-0391 floors a started task at its recorded `actual_start` and reports the floored UIDs on
`CPMResult.actual_start_driven` — deliberately NOT on `date_driven`, whose CONCERN ("tie these
activities into the network") would smear a false manipulation signal across every progressed
schedule (724 activities on the reference file). The 2026-08-13 audit verified the channel was
**produced but consumed by no product code** (`cpm.py:1357`; consumers = tests only): the promised
disclosure existed as a field the analyst could never see.

## Decision

Wire the channel into the two places its sibling `date_driven` is already disclosed, honoring the
separation in both:

- **An INFO/OPPORTUNITY finding** (`_actual_start_floor_findings`, registered in `recommend`
  beside `_logic_support_findings`): metric id `actual_start_driven`, cited per activity (§6),
  title "N activities are scheduled from their recorded actual starts". ~~**Category.OPPORTUNITY is
  load-bearing, not cosmetic**: `web/risks.py` builds the risk matrix, the risk ranking, and the
  recovery plan from RISK + CONCERN only, so an OPPORTUNITY/INFO disclosure informs without ever
  becoming a threat row or a recovery action~~ — **this justification is WRONG; see the correction
  note above and ADR-0413.** The intent it expressed (a recorded actual is evidence, not an
  unsupported date — ADR-0391 restated at the finding level) is right and is now enforced by
  `Finding.is_disclosure`. The `driving_path` precedent cited here is also **not** analogous:
  that finding is a genuine recovery lever, which is precisely why category could never
  discriminate the two.
- **A per-row flag + optional grid column**: `/api/driving` rows carry `actual_start_driven`
  beside `date_driven` (`web/driving.py`), and `path.js`'s FIELDS offers "Actual-start-driven"
  (default off) beside "Date-driven". The Excel path export is untouched **by symmetry** —
  `_DRIVING_COLUMNS` excludes both flags.
- **A metric-dictionary entry** (`help.py`, `METRIC-DICTIONARY.md` regenerated): definition names
  the separation; reliability dimension falls through to **Realism** (recorded execution), which
  is the correct bucket and needs no `_DIM_*` edit.

## Verification (QC-1)

- **Red first**: 4 of the 5 new tests failed by name against the pre-wiring tree (the negative
  control passes pre-wiring by construction; its teeth are proven by mutation M2).
- **Mutation battery 7/7 caught, by the named test**, in a PYTHONPATH shadow of `src/` (import
  origin asserted; pristine control green before and after; real-tree instruments md5-identical):
  M1 registration dropped → positive test; M2 empty-guard deleted → negative control; M3 finding
  keyed off `date_driven` → positive test; M4 web row keyed off the wrong set → web separation
  test; M5 FIELDS line removed → JS pin; M6 category degraded to CONCERN → category pin; M7 help
  entry removed → dictionary pin.
- **Blast radius enumerated before implementation, then measured**: every `recommend()`-calling
  test file plus the findings/risks/briefing/QA/help/export/frozen-payload surfaces — 210 passed
  with exactly ONE moved pin, the r11 `PAGE_SCRIPTS` byte-freeze of `path.js` (one FIELDS line),
  re-baselined in place with the freeze's own documented idiom. `#drivingTiersData` / `#dpData`
  frozen payloads are built by their own reducers and did not move.
- **The whole-tree gate caught the one guard the pre-enumeration missed**: a documented
  metric id has THREE guards — the doc-sync test, the emitted-ids test, and
  `test_aft_formula_audit.py`'s census requiring every `METRIC_DICTIONARY` id to be
  classified against the NASA library. The first run failed there (the honest red); the
  `actual_start_driven` NOT_IN_BIBLE row (the ADR-0034/0043 idiom: tool-specific
  diagnostic, no Bible counterpart) closed it, and the full gate re-ran on the final tree.
- Full gate figures on the final tree in the handoff's Gate-at-close.

## Deliberately NOT done

- **No new Category.** A fourth "NOTE/DISCLOSURE" category would touch i18n, the category
  buckets, and every findings consumer for one finding; OPPORTUNITY/INFO already renders
  disclosures outside the threat surfaces.
- **No Excel-export column.** `_DRIVING_COLUMNS` excludes `date_driven` today; the new flag
  follows. Widening the export is a separate decision for both flags together.
- **No coverage-note clause.** The `/api/driving` coverage line's `date_driven` clause points at
  a CONCERN the analyst must chase; an INFO disclosure earns a grid column, not a warning clause.
