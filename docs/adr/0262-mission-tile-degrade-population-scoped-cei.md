# ADR-0262 — /mission tile degrade below two versions + population-scoped CEI guards

## Status

Accepted. Closes handoff NEXT #1 (the ADR-0258 "known pre-existing" defect) plus an
ADR-0258 residual found while verifying it. Reproduced first (failing tests written before
the fix), then fixed, hardened, and browser-verified (Chromium: zero console errors, zero
4xx responses, all four themes).

## Context

With one loaded version, `/mission` rendered every tile's chart host anyway; the dedicated-page
scripts then fetched the cross-version APIs, which legitimately guard below two versions — so
the wall filled the browser console with 4xx noise and dead tiles. Live reproduction showed the
guards involved are `/api/cei` (400), `/api/trend` (400, fetched by BOTH Quality tiles), and
`/api/evolution` (400). **Correction to the ADR-0258 record:** `/api/scurve` was listed among
the offenders but in fact serves a single version (its only guard is an empty session) — the
S-Curve tile is healthy with one version, as are Forecast Drift (`/api/forecast`, ≥1
analyzable) and the three curves tiles (`/api/curves`, ≥1; single-version behavior is an
explicit feature of curves.js).

Verifying the CEI guard also exposed an ADR-0258 residual: `/cei`, `/api/cei`, and
`/export/{fmt}/cei` gated on `len(st.schedules)` — the WHOLE-SESSION file count — while the
wave itself is built from the population-scoped `st.ordered()`. With two single-version
Projects loaded the guard passed on another Project's file and the engine then failed on the
one-snapshot population (observed live: HTTP 422 from the month-axis builder) — cross-project
counting in a gate, exactly what ADR-0258 forbids.

## Decision

- **Server-side tile degrade.** `mission_view` computes two ACTIVE-population counts —
  `n_loaded = len(st.ordered())` and (only when `n_loaded >= 2`) `n_solvable =
  len(_solvable_versions()[0])` — and `_mission_body` degrades each cross-version tile below
  its OWN API's threshold: Bow Wave/CEI needs two LOADED versions (a stored-date view, no
  CPM); Critical-Path Evolution and the two Quality tiles need two ANALYZABLE versions. A
  degraded tile keeps its title, hover hint, and "Open ↗" link and renders a muted
  explain-why note in a `chart-note` pad (`chart-host` visual, but NOT the class — so
  chartframe.js never adds a dead zoom toolbar); the chart host ids and steppers are simply
  not emitted, the chart scripts early-return, and no request is ever made — zero console
  noise by construction. `mission.js` Play-all was already null-safe. The tile APIs keep
  their guards unchanged (every other caller sees the identical contract).
- **Population-scoped CEI guards.** The three CEI gates now count `st.ordered()` — the same
  population `compute_bow_wave` receives. Single-project sessions are byte-identical
  (`ordered()` returns everything); multi-project sessions get the honest 400/"load two
  versions" panel instead of a cross-project gate pass and an engine 422.
- **i18n.** The two degrade notes join `_TERMS` ×4 languages (ES/FR/DE/PT).

## Consequences

- Tests: `tests/web/test_mission_one_version.py` (degrade with one version; ≥2 renders the
  whole wall; APIs keep their guards; population-scoped CEI guard incl. export; loaded-vs-
  analyzable distinction via a cycle fixture; two-Project degrade). The existing
  `test_mission.py` fixture was re-targeted to TWO golden versions — it uploaded one version
  and asserted every chart host, i.e. it pinned the defective world (the documented
  test-contract-update pattern). `test_nasa_theme.py`'s dot-grid selector pin gains
  `.chart-note`.
- Browser-verified: one-version wall = 4 notes, zero console errors/4xx, four themes;
  two-version wall whole; the dead zoom cluster on degraded tiles found in the first
  screenshot pass and removed via `chart-note`.
- `/export/{fmt}/mission` still 422s below two versions (user-initiated download, not
  console noise) — out of scope here, recorded.
- Dashboard cross-version nav links (`len(st.schedules) >= 2`) and the SRA file selector
  (`> 1`) still count the session — navigation-only surfaces, no data leaves a population;
  recorded, not changed.
