# ADR-0470 — /card wears the Claude Design "Library Schedule ID Card" layout, functionality unchanged: a per-file drill whose cursor is NAVIGATION — one link chip per loaded version, the open one on

- **Status:** Accepted — 2026-09-06 (the operator's standing ask: at least one page per session onto the new design; seventh page)
- **Version:** 1.0.241
- **Extends:** ADR-0451 (the method), ADR-0456 (the `.cd-*` family), ADR-0464/0468 (a served stepper is re-homed), ADR-0465 (a page with no version cursor still wears the family), ADR-0327 (the r12 library toolbar sweep — no ⤓ on the card), ADR-0396 (an assurance derives from measured locality), ADR-0387 (the `card` page module), ADR-0195 (the design system)
- **Shipped:** `web/card.py` (`_version_chips`; `_card_body(versions=)`), `web/app.py` (the route hands the ordered population over; the `X as X` re-export), `tests/web/test_card_design_layout.py` (5, NEW), `docs/DESIGN-SYSTEM.md` §9

## Context

**/compare (10 What changed) was priced first, as the kickoff asked, and is a feature change (M–L):**
its artboard's panels are "Detector trends and the cross-pair evidence ledger", "All five pairs ×
every edit" and a slip decomposition update by update — the integrity page's change ledger for EVERY
pair plus a per-update finish attribution, neither of which the 219-line page computes today (one trend
panel and a verdict band). It stays a feature in the plan-forward. The next candidate by cost was the
smallest artboard with an extracted page module: "Library Schedule ID Card" (3 KB of canvas markup
against `card.py`'s 184 lines).

The artboard, read verbatim from the canvas's own `section[data-screen-label="Library Schedule ID
Card"]` markup (its `sc-for` loops name every element and count): kicker · headline ("Every version, on
one card.") · lede ("Pick a version to read its card.") · a row of VERSION CHIPS · ONE card with a
header line (`name · version`, a NOW chip, `file · data date`, a verdict) · a three-column grid of KPI
tiles · a ⤓ EXCEL button · a footnote. **UNVERIFIED by execution:** this session did not run the canvas
(the ADR-0464 recipe) — the section's markup is the design truth quoted, and the page was verified by
render instead; a later session executing `setScreen` for this screen would settle the pixel shape.

The page today: the utility takeaway, the "Schedule card" panel (twelve KPI stat cards in the
`stat-grid`, head strip + ⛶ + provenance chip), the pivots panel (four count/percent tables), the chrome's
Ask panel; no ⤓ (ADR-0327 — no export covers what the card draws).

## Decisions

1. **The cursor is navigation.** A card has no stepper and no frames, so the family's strip
   (`.viz-controls.cd-cursor#cardCursor`) holds one `<a class="cd-chip">` per loaded version of the
   ACTIVE project (`SessionState.ordered_versions()`, oldest first), the open version `on`, linking to
   `/card/<key>` — the artboard's "Pick a version to read its card" — with the family's `vN · file ·
   DD` pill and a `cd-note`. Served only with two or more versions, like every strip in the family; a
   single version renders exactly as before. Chips carry no id and no family word (the control census).
2. **Both panels and every figure stay verbatim** — the twelve stat cards ARE the artboard's tile
   grid; nothing is re-rendered.
3. **Not ported, on purpose:** the mock's ⤓ EXCEL (ADR-0327's rule stands: no export covers the card);
   its verdict word and colour (no engine verdict behind them — a mock figure); its footnote "nothing
   leaves this machine" (a Law-1 ASSURANCE must derive from the session's measured backend locality
   and be withdrawn when the gateway is armed — ADR-0396; a static sentence on a page would contradict
   the banner); a DCMA pass-rate tile (the page has none).

## Verification (QC-1)

- **Red first, on the pristine page:** 4 of the 5 layout tests failed (no strip, no chips, no pill);
  the one-version control passed.
- **Green:** layout 5 · `test_card_view` · the r12 library toolbar sweep · the monolith split contract
  (after the `_version_chips as _version_chips` re-export — the kickoff's own trap, met) · i18n ·
  accessibility · r11 · target/theme · global filter · portfolio titles — **151 passed**; the M1
  control-effect census rows for `/card/{name}` **2 passed**.
- **Measured by render (Chromium, 1440 px, the Project2/Project5 pair), all four themes:** chips 2 ·
  the on chip `data-idx=1` (the newer file, the page opened) · `.panel` 3 (card · pivots · the chrome's
  Ask panel, identical to the pristine page) · widest element 1440 (nothing wider than the viewport) ·
  the on chip's background distinct from the off chip's in every theme (console `#4aa3ff`, daylight
  `#0b62c6`, apollo `#ffb000`, jarvis `#19d3ff`) · clicking v1 opened `/card/Project2` with its own
  chip on and the pill reading `v1 · Project2.mspdi.xml · DD …` · zero page errors.
- **Two premises corrected on the way, recorded:** the page's `.panel` count is THREE (the chrome's
  Ask panel is a `.panel`; a pin must count what the page SERVES), and the panel head names the
  project TITLE, not the key.

## Consequences

- /card reads as the family's seventh page: the version cursor over the card, the card and the
  pivots untouched; a per-file drill's chips are links.
- DESIGN-SYSTEM §9 gains the rule: a per-file drill wears the cursor strip as NAVIGATION — link chips,
  no stepper, no `data-frame`; the strip is served only with two or more versions.
- Version 1.0.240 → **1.0.241** with ADR-0469; wheel + nine installers rebuilt in lockstep as the LAST step.
