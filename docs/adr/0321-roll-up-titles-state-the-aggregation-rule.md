# 0321 — Roll-up titles state the aggregation rule (OR-01)

Date: 2026-07-31
Status: accepted

## Context

OR-01 (operator notes 2026-07-28): reading a metric title alone must tell the analyst whether
they are looking at a latest-value or an average, and every per-file surface should name, per
file, what each figure is — Site / Company, data date, computed finish, effective margin,
DCMA-14. The Portfolio ledger already rendered the six roll-up columns from the latest included
version's engine summary, but its headings never said so, and NO average existed anywhere. The
home manifest listed only file · activities · source · actions, and the per-file cards (the
dashboard health card and the `/card` ID card) showed the finish and the DCMA ribbon but not the
site or the effective margin. PR-7 of the approved queue (`docs/STATE/PLAN-20260730.md`).

## Decision

**A heading states the rule the view actually applied — and the view never invents an
aggregate the engine does not compute.**

- **Ledger headings (`_portfolio_body`)**: the three headline columns become "Computed finish —
  latest version", "Effective margin — latest version", "DCMA-14 — latest version" ("Latest
  data date" already stated its rule). The takeaway sentence now discloses both bases (latest
  headline figures; the pooled DCMA average).
- **The ONE aggregate column** — "Avg DCMA-14 passes — included, solvable versions" — is
  VIEW-LAYER arithmetic over per-version engine outputs only: the mean of
  `VersionSummary.dcma_pass` across the project's included (non-excluded), SOLVABLE versions,
  rendered `<mean:.1f> of 14 · N versions` with N the pool size, so a solvability drop is
  visible in the figure itself. An unsolvable version's audit never ran — counting its 0 would
  poison the mean (Law 2), so it stays out of the pool, and the heading says exactly that
  (this PR's own review round caught the first-draft heading claiming "all included versions",
  a pool the code deliberately does not apply — the title must state the APPLIED rule); an
  empty pool renders the "—" literal (ADR-0219 M2), never 0.0. No new engine math: every
  operand is `compute_summary`'s own pass count via the cached `SessionState.summary_for` tier
  (v4 Feature 2 — the per-row tier; never `analysis_for`).
- **Home manifest**: each loaded file's row gains Site / Company · Data date · Computed finish ·
  Effective margin · DCMA-14 — per-file labels, because on a one-file row the value IS that
  file's (no latest-vs-average ambiguity to disambiguate). Dates and margin come from the same
  summary tier; the DCMA-14 cell counts the PARITY-AWARE card tier
  (`SessionState.dashboard_core_for` — the exact checks the health cards on the same page
  render), because the summary tier is default-mode-only (see Consequences) and one page must
  never show two DCMA verdicts for one file.
- **Cards gain ONLY the missing OR-01 fields**: `/api/dashboard` cards add `site` (the source
  header's Company, null when absent) and `margin_days` (the summary tier's effective margin,
  null when unsolvable/n-a); `dashboard.js` renders them as two new stats; the `/card` ID card
  adds the same two KPI cards (`margin_days` passed from the route's `summary_for` — one
  engine path, overlay-aware, never a second computation).
- **`/margin/confirm` also drops the card memo.** The ADR-0291 manifest-projection memo now
  bakes `margin_days` into every card, and its epoch key does not cover the margin overlay —
  the review round reproduced `/api/dashboard` serving the pre-confirm margin (a stale fake
  zero) after a confirm while `/portfolio` and `/card` served the new engine value. The route
  now clears `st.dash_cards` beside its existing `st.summaries.clear()`, and a regression test
  pins confirm→card immediately.
- **i18n**: the new headings/labels enter the offline `_TERMS` catalog in all four target
  languages (plus the previously uncatalogued "Latest data date" / "Effective margin" and an
  invariant "DCMA-14" entry so the bare acronym heading never reaches the AI fallback).

## Consequences

- The three `/api/dashboard` golden SHA-256 pins (`test_dashboard_perf_contract.py`) are
  DELIBERATELY re-baselined via their own `_dashboard_sha` path: every card gains exactly the
  two new keys and nothing else moves —
  `test_portfolio_rollup_titles.py::test_dashboard_cards_carry_site_and_margin_verbatim`
  proves it at row level (full key-set pins on both card shapes + engine-verbatim values).
- The dashboard/manifest/portfolio perf contracts hold unchanged: the new fields ride the
  memoised card and the cached summary tier, so a warm refresh still re-derives nothing
  (ADR-0281/0291 spies stay at zero); cold cost is the summary tier the Portfolio already
  paid per row.
- The heading strings are the catalog keys (literal "—", exactly as rendered), so the offline
  translation covers them without the AI fallback.
- **Recorded residuals (pre-existing classes this PR surfaced, not created — recorded, not
  chased):** (1) the summary tier is PARITY-BLIND — `compute_summary` audits in default mode
  only, so in Acumen-parity sessions (the ADR-0287 default) the Portfolio pill and the new
  average column count default-mode DCMA while the analysis/card tiers count parity-mode; the
  home page is now internally consistent (the manifest cell reads the card tier), but
  `/portfolio` vs the cards can differ by the known parity deltas (e.g. DCMA-09 on the big
  fixture). Threading parity through the summary tier means an engine change (a
  `compute_summary` signature + the content-hash disk blob's key, which today ignores parity)
  and its own `cache.engine_version` bump — a follow-up, not a rider on a titles PR. (2) The
  manifest's pre-existing Activities cell counts the UNSCOPED file while the engine figures
  are scope-aware (the page-wide filter banner already discloses an active filter); aligning
  that column would change a long-displayed number and is likewise its own decision.

## Verification (all read from runs this session)

`tests/web/test_portfolio_rollup_titles.py` — 15 tests: a non-degeneracy fixture guard
(distinct 5/9/5 pass counts; a NONZERO 2.0 d engine margin, so a hardcoded fake 0 cannot
pass); the full heading-row pin; takeaway discloses both bases; the average equals the
view-layer mean of the ENGINE's own per-version pass counts; the MIXED-solvability pool is
disclosed in the cell (4 included versions, "· 3 versions" in the figure); "—" when no
included version solves; exclusion shifts the pool (mean AND stated N, reversibly);
home-manifest fields engine-verbatim (and the unsolvable file keeps "—", never "0 pass"); the
manifest DCMA cell EQUALS the same-page health cards' counts; margin-confirm reaches the
dashboard cards immediately (the memo-invalidation regression); dashboard card key-set +
value pins; dashboard.js stat pins; `/card` label+value pinned adjacent; i18n catalog
completeness. **Proved able to fail:** `src/` stashed → 13 of 15 fail (the passers are the
engine-oracle fixture guard and the em-dash-for-unsolvable non-regression pin, both true on
main) → pop. This PR was additionally reviewed by a four-lens adversarial fan-out with
per-finding refutation agents (ADR-0240): the confirmed findings — the stale card-memo margin
(live repro), the "all included" heading overclaim, the same-page parity contradiction, the
degenerate-at-0.0 margin fixtures, and decoupled label/value pins — are all fixed above; the
parity-blind summary tier and the unscoped Activities cell are the recorded residuals.
Golden re-pins verified green post-change alongside `test_manifest_projection_memo.py` +
`test_dashboard_status_trim.py` (23 passed); neighbors (portfolio shell/panelkit · home shell
· landing · card view · i18n · coverage app ×2 · project scope · global filter · presentation
fixes · cache tiers · drill ×2 · axis titles): **169 passed, 1 skipped** (the known
INCIDENTAL_SVG skip). Statics: `ruff` 0.16.1 check + format, `mypy --strict` (117 files),
`bandit` exit 0, `node --check` — all clean.
