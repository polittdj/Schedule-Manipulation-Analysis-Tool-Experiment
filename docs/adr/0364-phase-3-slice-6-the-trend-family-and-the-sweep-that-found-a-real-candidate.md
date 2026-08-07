# ADR-0364 — Phase 3 slice 6: the trend family, and the sweep that found a real candidate

- **Status:** Accepted
- **Date:** 2026-08-07
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule), ADR-0352 (the pre-flight
  probe), ADR-0358 (the assert-original-absent harness), ADR-0363 (margin — the widen-the-oracle
  lesson this slice applied on its first try)
- **Related:** ADR-0297 (the monkeypatch trap), ADR-0349 (the source-text trap), ADR-0202
  (the "How it moved" chapter header), ADR-0291/0321 (the dashboard projection memo the
  cleared sweep hit spies on)

## Decision

**Extract the /trend page family — verbatim — into `web/trend.py` (483 lines):**
`_how_it_moved_header`, `_trend_body`, `_trend_data`. **The `_focus_rows` / `_focus_panel`
pair DESCENDS into `components.py`** in the same commit. `app.py` **17,681 → 17,197** (−484:
the moved lines and blanks, the re-export blocks added back, and the 4 import lines
`ruff --fix` dropped). `LAYER_ORDER` becomes `… → integrity → margin → trend → app` — note
`web.trend` sorts AFTER `web.state` in the import block, unlike every previous page module,
so the re-export block lands at the end of the imports rather than mid-list.

**The re-measured closure partitioned again, three ways** (the census said "trend 348"; the
behaviour-seeded closure over the `/trend`, `/api/trend`, `/export/{fmt}/trend` routes says
7 names / 502 lines):

1. **The move set: 3 names / 424 lines, CLOSED** — every external referrer is `create_app`,
   zero references to anything that stays.
2. **The focus pair (55 lines) is 2-family:** `_focus_panel` is embedded by `_trend_body`
   AND called by the `/compare` route, whose family (`_compare_body`,
   `_what_changed_header`) stays. ADR-0351's rule: the first slice of a pair forces the
   descent. Its one genuine dependency gap was `offset_to_datetime` — components' cpm import
   widens by exactly that name (the multiset's single removed/re-added line).
3. **`_parse_uid` (10 route families) and `_sources_line` (8) stay** — shared route
   machinery, no page owns them.

**`export_trend` stays whole in `app.py`:** it builds its workbook from
`compute_quality_trend` directly and references nothing moved — so that import stays in
`app.py` while `trend.py` imports it independently (both predicted before `ruff --fix` ran;
the four drops — `compute_cei_trend`, `compute_float_ratio_trend`, `compute_hmi_trend`,
`compute_float_sums` — matched exactly).

## The pre-flight probe — second consecutive fully-covered family, and the margin lesson paid

Span-scoped per ADR-0352, on the 80-route oracle (golden pair; margin's band POST + margin
exports retained; **new this slice**: `/export/{xlsx,docx}/trend`, a `/trend?target=3`
variant focused on a deterministically-picked cross-version uid, and a
**`/compare [target-set]` pseudo-route** — the set-target POST runs AFTER the target-less
sweep so those renders stay uncontaminated, then /compare renders once focused):

| member | routes moved (of 80) |
| --- | ---: |
| `_focus_rows` / `_focus_panel` | 2 — `/trend?target=3` **and** `/compare [target-set]` |
| `_how_it_moved_header` / `_trend_body` | 2 — both /trend variants |
| `_trend_data` | 1 — `/api/trend` |

The pair's first probe covered only its /trend consumer — the /compare branch is
target-gated and the oracle set no target. That is ADR-0363's "a coverage gap can be an
ORACLE gap" shape, and the widening (one POST + one render) took the pair's /compare
consumer from AST-inferred to render-proven. The 2-family descent is now proven at both
ends by execution, a first for the descent rule.

## Proof

- **Per-definition byte-identity vs the pre-move source: 5/5 IDENTICAL** (`_trend_body`
  10,492 B, `_trend_data` 7,918 B, `_how_it_moved_header` 3,582 B, `_focus_panel` 2,472 B,
  `_focus_rows` 747 B).
- **Multiset: 57 added / 1 removed.** The additions are the preamble, the re-export blocks
  and the descent comment; the one removal is components' cpm import line, re-added widened
  with `offset_to_datetime`.
- **80/80 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in BOTH new locations** (`trendCharts` in `trend.py`; `Focus activity UID` in
  `components.py`), each moving exactly the pre-flight sets; original-anchor-absent asserted;
  restores md5-verified.

## The sweeps — sweep 1 found a real candidate, and verification cleared it

- **Monkeypatch sweep** (all 31 names `trend.py` binds + the descended pair, self-test
  first): **one hit** — `test_manifest_projection_memo.py` patches `app_mod.non_summary`
  (and `app_mod.compute_activity_makeup`) as call-counting spies. Verified NOT the silent-
  patch shape: the exercised path is `/api/dashboard`'s projection memo, which lives in
  `app.py`/`state.py` and never crosses a moved member; `app.py` still binds both names (41
  and 8 kept usages). The patch target remains correct; the test still passes post-cut. This
  is the sweep's first true-candidate-cleared-by-verification outcome — previous slices were
  empty or required repointing.
- **Source-text sweep:** every reader's subject stayed put (the `_LAYOUT` readers target
  `chrome.py`; `_TS_CAPTION_MARK`'s page insertions are untouched by this family).
- **Attribute-read sweep** for the four dropped names: no test reads any through `web.app`.

## Verification

Five mutations, each verified-landed, each restored from a scratchpad copy (never
`git checkout`), each md5-verified, each re-run green:

1. Re-export of `_trend_body` deleted from `app.py` → contract test fails naming it.
2. A **deferred** `from schedule_forensics.web import app` inside `_trend_data` → the
   layering test fails for `trend.py`.
3. `"trend.py"` dropped from `test_bar_drill`'s module tuple → the enumeration guard fails
   (fifth consecutive live catch — it also fired when `trend.py` joined `VIEW_MODULES`).
4. A `"&mdash;"` sentinel planted in `trend.py` → the widened em-dash guard fails.
5. A second `drilldown.js` include planted in `trend.py` → the widened double-load guard
   fails.

## Consequences

- Nine page families remain by the (now five-slices-stale) ADR-0350 census: `ssi` 335 ·
  `mission` 304 · `how` 290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 ·
  `evm` 208 · `forecast` 204 — **re-measure before cutting**; both re-measured slices
  partitioned three ways.
- The `/compare [target-set]` pseudo-route stays in the harness: it is the only render of a
  focused /compare, and the descent pair's /compare consumer has no other execution proof.
- When the **/compare** family is cut, `_focus_panel` is already at the right layer — the
  descent is done.
