# ADR-0451 — /volatility wears the Claude Design "How stable is the path" layout, functionality unchanged

- **Status:** Accepted — 2026-09-02 (operator item 6 of six)
- **Version:** 1.0.229
- **Shipped:** `web/volatility.py` (five numbered design panels, masthead + master cursor strip with version chips, cursor-cumulative KPI, `_vol_panel_open`, `_stability_band`), `static/app.css` (`.vol-*`, tokens only), `static/volatility.js` (chips drive `stepTo`, `renderKpi`), `tests/web/test_volatility_design_layout.py`

## Context

"I don't like the way this page is presented. Refer back to what Claude Design came up with for this page
and convert this page to that design but don't modify any of the functionality." The design truth is
`00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc.html`, artboard "04 How stable is the path" (lines
1545–1746, `buildVolatility()` 5810–5896) — recovered by EXECUTING the canvas's own template (support.js
boots from unpkg, which the proxy blocks) and rendered to PNG before anything was written; the spec is in
the session's scratch (`design/volatility_design_spec.md`). The design: masthead (kicker · headline · lede)
+ ONE master cursor (Prev / ▶ Play / Next / chips v0…vN / "Vn · DD" pill) → row 1 `1.05fr .95fr`
(① Stability signal: KPI "65% MEAN CARRY-OVER" + band pill + churn dots · ② Flow of the path) → row 2
`1.25fr .75fr` (③ Membership matrix · ④ Transition ribbons) → ⑤ full width (the path + what-if ledger,
which is /evolution's content) → Continue footer. No CSS classes in the mock — inline styles over tokens.

## Decisions

1. **Five numbered panels in the design's grid; the ten visuals keep their tiles VERBATIM inside them.**
   The control census counts ten chart frames on this page and the JS finds every host by id, so folding
   visuals into new renderers would have changed functionality. ①: KPI block + gauge + churn; ②: flow +
   composition; ③: heatmap + tenure + jumpers + dwell + strips; ④: ribbon; ⑤: the scoreboard as the
   design's ▦ DATA drawer (`<details open>`), with a link to /evolution for the what-if ledger the design
   draws there.
2. **One cursor.** The chips call the same `stepTo`; the KPI is cursor-CUMULATIVE like the design (mean of
   the pairs up to the cursor) and SAYS which mean it is ("THROUGH v2" / "ALL VERSIONS") so it cannot be
   read against the gauge's all-versions figure. Band pill STABLE ≥70 / WATCH 50–70 / CHURN <50 / AWAITING —
   display guidance, as the caption states.
3. The r11 panel contract is preserved by construction: the masthead and the scoreboard keep their `panel`
   shells and `_panel_head`, the wrapper class is `vol-block` (never a `panel` word), and the page-owned
   script digest was re-baselined deliberately.
4. Not ported from the mock, on purpose: the "61 %" strings (a stale figure), the decorative ribbon
   geometry (only its numbers are data-driven in the mock), and the mis-positioned `⏱ MONTHS` span.

## Consequences

- Census 66/66 green on the restyled page (ten frames, three stepper ids, 18 explainers); the ch04 oracle,
  DD ledger, axis titles, bar-drill and air-gap suites unchanged.
- Verified in chrome at 1600 px with a three-version corpus (five panels, three chips, ten frames; KPI 67 % →
  33 % on the v2 chip). The four themes were NOT each screenshotted this session — UNVERIFIED per theme.
