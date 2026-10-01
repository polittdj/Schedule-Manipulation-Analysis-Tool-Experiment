# ADR-0543 — LODESTAR 2.0, the "Console" studio: the operator's design handoff built whole (live redraw over a JSON API, server-side undo/redo, a command palette, a guided tour and Show-me demos, a data-date slider, drag-to-link, print to PDF, four views on vendored fonts and icons, a launch page of its own); the logic links routed shortest-path and drawn behind the items in both programs

**Status:** Accepted · **Date:** 2026-10-01 · **Supersedes:** ADR-0540's link escalation (the
gutter lane, the reorder within a swimlane, the glyph shrink, the dashed last resort, the slide
footnote and ruling (c)); ADR-0541's head-vs-leg checks and spare-row footnote, and its §5 (the
launch page as Polaris²'s boot screen); ADR-0539's "links painted ABOVE the items over a halo",
"the whole link as ONE named group" and its link-vs-link separation rows · **Extends:** ADR-0539
(LODESTAR), ADR-0541 (the data date) · **Keeps:** ADR-0540's rulings (a) and (b), full-page fill,
never a second slide · **Operator:** David Politte

## Context

The operator (2026-10-01) attached a design handoff, `Lodestar_UI_redesign_proposal.zip`, and
asked: *"Deep dive the attached documents and then update the UI for the Lodestar stand alone
program. Any functionality that does not currently exist I want you to create that functionality
in the program."* The bundle held a written specification (frame, side panel, slide, the
logic-link routing and z-order rule, motion, launch page, acceptance list), the "A1 Command Deck"
design system (tokens, components, four views) and a clickable HTML/JS prototype. It is the
operator's design document, not a schedule; it is **not committed** with this change (it can be
added through `00_REFERENCE_INTAKE/` like the other reference inputs) — this ADR records every
decision taken from it.

The handoff asks for far more than a re-skin: live redraw with no reload, undo/redo, a command
palette, a guided tour, demonstrations, a data-date slider, drag-to-link, print/PDF, a data
drawer, full screen, a session log, four views, vendored type and icons — none of which v1.0.2
had — and a different logic-link rule for BOTH programs' slides (the router is shared with
Polaris²'s One-Pager pages).

## Decision

1. **The studio is server-rendered and script-accelerated** (`web/lodestar_studio.py`). The
   server renders the page's two regions (main, side panel) and a state object; the script
   (`static/lodestar_studio.js`) posts to a JSON API and swaps the regions in place, keeping focus.
   Every control is a plain form underneath: with scripting off the v1 form routes still answer
   (303 to the page), so nothing the handoff added is the ONLY way to do a thing.
2. **One dispatcher for both paths** (`web/lodestar_actions.perform`): upload, example, title,
   window, data date, clear, links (add / remove / clear), swap, marking — each returns a label,
   a toast and a status; a refusal changes nothing and logs nothing. The JSON routes
   (`POST /api/<action>`, `GET /api/state`, `POST /api/preview`, `POST /api/undo|redo`) and the
   form routes both call it. The JSON body is size-capped and must be one flat JSON object
   (415 non-JSON, 400 malformed or nested), behind the same Host / Sec-Fetch-Site gates.
3. **Undo / redo live on the server** (`web/lodestar_history.History`): the last 60 changes, each
   a labelled snapshot of the content fields (the lists, title, window, data date, links,
   marking); a step that changes nothing is not recorded; the session log shows the labels,
   newest first. Server-side because the state is the server's — a client-side stack would drift
   from it on a scripting-off request.
4. **Preview is a copy** (`/api/preview`): the data-date slider, and every Show-me
   demonstration, lay the slide out on a copy of the session (its own cache and history) — the
   operator's state is never touched until the slider is released or a real action is taken.
   The slider moves the red line linearly for feedback and asks for the exact layout throttled,
   latest-wins, because `plot_window` widens the timescale around the data date (A3 below).
5. **Its own painter** (`static/lodestar_slide.js`) over the SAME layout JSON the shared
   modules compute: z-order ground → title → years → months → rules → lanes → summaries → link
   shafts → items → link heads and tags → data-date line → legend → pick rings → drag lead;
   labels on a halo of the ground (stroke 0.42 × the label size); a reveal on load; pick rings
   and FROM / TO tags; drag one item onto another to link (> 3 pt threshold).
6. **The frame** (`web/lodestar_shell.py`): a 56-px header (mark, the two pages as `nav` links
   with `aria-current=page`, the palette, Undo / Redo, the view menu, the marking switch, Tour,
   Quit), a 320-px side panel (session log, list, two lists, shape, links, export, Show me), a
   status bar; the CUI bars top and bottom, the ONE copy of the handling drawer, the credit in
   the header strip and the status bar — never on the slide, the print or the deck.
7. **Design system**: the handoff's A1 tokens verbatim in `static/lodestar_tokens.css` (four
   views `dark` · `bright` · `contrast` · `console`, saved by `static/lodestar_view.js` under
   `lodestar-view`, Polaris²'s `sf-theme` values mapped once); IBM Plex Sans / Mono and Space
   Grotesk (OFL, `@fontsource` 5.3.0 Latin subsets, 11 woff2, 198,418 bytes) vendored in
   `static/fonts/`; 33 Lucide icons (ISC, `lucide-static` 1.49.0) as an inline sprite
   (`web/lodestar_icons.py`). DESIGN-SYSTEM §7c records the sanction: one more token file for one
   program, a hex once as a token, the marking bars the one exception.
8. **Command palette, tour, demos, print**: Ctrl/⌘K opens a filtered command list (load,
   examples, pages, exports, print, show all dates, the computer's date, remove links, marking,
   tour, undo/redo by label, views, demos, quit); the tour's seven steps (auto-offered once after
   the first list load); five Show-me demonstrations (draw a link, drag to link, move the data
   date, narrow the window, compare); Print prints the slide alone, marked top and bottom, on the
   Bright values in every view, ONE page.
9. **The launch page** (`web/lodestar_launch.py`, `static/lodestar_launch.{js,css}`) is LODESTAR's
   own: the hero (three stories, 6.5 s), Take a star fix (six stages, 650 ms, ending on a welcome
   panel), Skip, the opt-out (v1's `sf-boot-skip` key, kept so the choice survives the upgrade),
   three real tiles, the list→slide animation. No canvas, no sound.
10. **The logic links, both programs** — ENGINE_PLACEHOLDER
11. **Versions**: LODESTAR **2.0.0** (`f"{NAME} {VERSION}"` renders "LODESTAR 2.0.0"; the README
    says "Version 2.0.0."); the package **1.0.298**.

### Where the build departs from the handoff, and why

| Handoff | Built | Why |
| --- | --- | --- |
| The marking switch "flips the marking for pages and every export"; tour step 7 "Pages and every export carry the CUI marking until you switch it" | the switch's title stays "Switch the page and PowerPoint marking"; tour step 7: "The pages and every PowerPoint carry the CUI marking until you switch it; the Excel exports always keep it." | ADR-0540 ruling (a): the Excel exports keep the shared writer's fixed CUI header — over-marking, never under. The handoff's wording would be false |
| Reuse `static/theme.js` for the four views | `static/lodestar_view.js`, own key | `theme.js` whitelists Polaris²'s four themes and coerces anything else to `console` (A2) |
| The data-date caption "Data date M/D/YY" | `DATA DATE m/d/yy` | the layout owns the caption (ADR-0541); DESIGN-SYSTEM §4 pins `DD` / `DATA DATE` |
| Launch page with a particle canvas and the boot hum | neither | the handoff's own launch column is the list→slide animation; §8 binds a hum LODESTAR has no reason to play |
| A stopped page in the new design | unchanged: system colours, inline styles | it must render after the server is gone (ADR-0539 LS-05) |
| Tabs as A1 "Tabs" (ARIA tabs) | `nav` links with `aria-current=page` | they navigate; ARIA tabs promise an in-page panel and arrow keys they do not have |
| Display "LODESTAR 2.0" | "LODESTAR 2.0.0" | one version string, `--version` and the README pinned to it |
| The A1 tokens verbatim in every view | Bright's text-bearing tokens darkened (`--text-muted` #536276, `--text-accent` #096A63, `--accent` cyan-700, `--accent-gold` #835509, `--status-pass` #13703F, `--status-warn` #8E550F, `--focus-ring` cyan-700); `--text-faint` never carries meaningful text | WCAG 2.1 AA (the repo's Section 508 commitment, ADR-0073): 93 text elements measured below 4.5:1 across the four views with the handoff's values, 0 after |
| PPTX link head "or use the line's tail-end arrow" | the layout's own closed triangle | ADR-0539: LibreOffice drew `tailEnd` heads 3× the page's |

## The plan was attacked before the first edit (QC-3) — what fell

| # | Premise | Check | Verdict |
| --- | --- | --- | --- |
| A1 | The CSP allows same-origin `fetch` and self-hosted fonts | read `web/security.py` (`connect-src 'self'`; no `font-src` → `default-src 'self'`); Chromium probe | **HELD** |
| A2 | `theme.js` can carry the four A1 views | read `static/theme.js:14-31` | **REFUTED** — it coerces unknown names to `console`; a LODESTAR view script with its own key |
| A3 | The timescale is linear in days, so the client can move the red line alone | read `plot_window` | **PARTLY REFUTED** — linear inside the window, but with no window set the window widens around the data date, so a moved date can re-lay the slide; the slider gives linear feedback AND asks `/api/preview` for the exact layout |
| A4 | The icons and fonts can be vendored offline | `npm pack` of `lucide-static` 1.49.0 (ISC) and `@fontsource/*` 5.3.0 (OFL); all 33 names exist | **HELD** |
| A5 | The air-gap scan tolerates `xmlns="http://www.w3.org/…"` | `tests/web/test_airgap.py:121-130` | **HELD** |
| A6 | `package-data` `web/static/*` packages `static/fonts/` | a setuptools wheel of a probe package | **REFUTED** — not recursive; `web/static/fonts/*` added, else LODESTAR from the wheel crashes at `load_assets()` |
| A7 | The new router makes ADR-0540's escalation unreachable | the router mapper: `fit_links` steps only while the report has collisions; a scratch install of the new router turned every escalation test red because no step was ever taken | **HELD** — the escalation is dead code under the new rule and is retired whole, not left dormant |
| A8 | Polaris²'s painters need only the z-order change | ENGINE_A8 | ENGINE_A8_VERDICT |
| A9 | "Go straight to the studio next time" needs a new mechanism | read `launch.js` | **REFUTED** — v1 already stored it (`sf-boot-skip`); kept, so the choice survives the upgrade |
| A10 | Every v1.0.2 feature has a home in 2.0 | TESTS_A10 | TESTS_A10_VERDICT |
| A11 | A same-origin `fetch` POST passes `_gate` | Chromium: JSON and urlencoded `fetch` POSTs, 200, state changed | **HELD** |
| A12 | The static route serves a sub-path (`fonts/x.woff2`) | read the route: `rsplit('/')[-1]` | **REFUTED** — the route now looks up the whole relative name in the allowlist (an exact dict lookup, never a filesystem join) |
| A13 | The handoff's step-3 band is defined for all four link types | the router mapper; the prototype | **REFUTED** — SS has no lower bound, FF no upper; the prototype's ±1e9 sentinels collapse it to the closed side. Implemented as that one column (the shortest route, the handoff's stated goal); differential test against the prototype's JS: 5,315 links, 0 mismatches |
| A14 | The handoff's "ghosts included" equals the prototype's `covered()` | reading both | **REFUTED** — the prototype stops at the ghost's left edge; the handoff's text (the full ghost and the move arrow) is followed, with a targeted test |
| A15 | One "Logic link:" group per link can carry the new z-order | a DrawingML group has one z-position | **REFUTED** — split into "Logic link: …" (the shaft, under the items) and "Logic link arrowhead: …" (head and tag, over them) |
| A16 | The text glow's place in `a:rPr` | ISO/IEC 29500 `pml.xsd`, with mutants | **HELD** — after the fill, before `a:latin` |

## The build was attacked after it was written (QC-1) — what fell, and what replaced it

| Finding | Measured | Replaced by |
| --- | --- | --- |
| Print produced TWO pages, the slide on both | Chromium `page.pdf` at Letter and A4, both pages: 2 / 2 / 2 / 2 | the frame leaves the flow in print (`.ls-root{position:fixed}`); 1 / 1 / 1 / 1; a mutation twin (`position:static`) gives 2 |
| Print in the dark view's colours, the bottom marking missing | screenshots | the tokens switch every view to the Bright values under print; the slide box is a three-row grid with its own marks |
| The data-date input stretched across the bar | screenshot | a fixed-width date field |
| The tour card under a toast | screenshot | the tour above the toasts (z-index 75) |
| Link-styled buttons teal on teal | screenshot | `:where(.ls-app) a` takes the accent text colour |
| The legend's link entry drew its text outlined | screenshot | the legend group no longer shares the link class |
| The page tabs carried `role=tab` / `aria-selected` | DOM probe | `nav` links with `aria-current=page`; a probe that re-adds `role=tab` goes red |
| Tour step 7 claimed the marking reaches "every export" | reading against ADR-0540 (a) and `reports/xlsx.py`'s fixed `_CUI_HEADER_FOOTER` | the sentence names the pages and every PowerPoint, and says the Excel exports always keep CUI |
| The README claimed the palette sets a data date, that demos always use the example, and that everything works without scripting | reading the palette's command list, `runDemo`, and a JavaScript-disabled Chromium run of every form (load, upload, title, window, data date, link, undo, redo, marking, both exports, swap) | the README says what is true: the palette goes back to the computer's date; demos run on a copy of the operator's list (the example when none is loaded); the forms work without scripting, the palette / tour / demos / drag / slider need it |
| "Drag to link fails" | a probe dropped at y = 918 in a 900-px viewport | NOT a defect — re-run in a 1300-px viewport: "Link added: Boots 2 → MET Testing (FS)" |
| Text contrast below WCAG AA (found by the test stream on the launch page, then swept everywhere) | a Chromium sweep of every visible text node, colour composited over its ancestors' grounds: **93** below 4.5:1 (Bright gold 2.12–2.76, Bright muted on the void 3.99, white on Bright's teal buttons 3.32, Bright pass / warn text 3.82–4.33, `--text-faint` text 2.25–3.85 in Dark / Bright / Console, the selected palette hint 3.79 / 4.21) | the token changes above; **0** on all 16 page states, the palette, the tour, the data drawer, the open drawer, a toast and the slide's 42 texts; mutation twins red by name |
| The data-date slider lost keyboard presses (found by the test stream) | a range fires `input` AND `change` on every arrow key: each key committed, `act()` dropped the ones sent while a commit was in flight, and the region swap re-rendered the slider at the server's value — 12 × ArrowRight moved the date +2 / +5 / +3 days and logged 2 / 5 / 3 steps (plain, Tab inside the wait, a 0.6 s server) | keyboard nudges gathered into ONE commit 700 ms after the last key or at once on blur; a data date set while a request is in flight waits and is sent when it lands (never dropped); measured +12 days and ONE step in all three, a pointer drag still ONE step on release |
| The JSON gate admitted non-string values for every action (found by the test stream) | `POST /api/title {"title": true}` (or a two-item list) → 200, the title cleared to "" and logged "Slide title changed": the gate let the preview's flag / pair types through for every action and the route then dropped the non-strings, so the action read the field as missing; strings were also cut at 256 characters, which the form path never does | an action's values must be strings (400 otherwise, by name); only `/api/preview` takes a flag and a two-date list; strings pass whole (the body cap bounds them, each action caps its own field, as on the form path); every demo and action re-run through the gate in Chromium — no 4xx |
| The launch page carried the author's credit once | ADR-0539: header AND footer of every page | a second credit above the bottom marking bar |
| ENGINE_QC1 | | |
| TESTS_QC1 | | |

**UNVERIFIED, stated:** PowerPoint itself (LibreOffice Impress is the renderer here); Firefox
and WebKit (Chromium only); Windows and macOS (the fonts render through the browser, so a
missing glyph falls back to the system stack — the Latin subsets omit arrows such as →); print on
a physical printer (Chromium's PDF only); the size-cap ruling (`LABEL_MAX` 14, `GLYPH_MAX` 40,
`LANE_NAME_MAX` 12) stays PROVISIONAL as ADR-0540 left it.

## Consequences

- LODESTAR no longer loads any of Polaris²'s sheets or scripts; the two programs share the
  layout, the router and the PowerPoint writer, and differ in page styling only.
- Polaris²'s One-Pager pages change with the shared router: links are routed shortest-path and
  drawn behind the items; the "How the logic links were fitted" and "drawn dashed" blocks, the
  slide footnote and the gutter are gone from both programs, and the Excel Notes no longer carry
  fitting sentences.
- `LODESTAR.pyz` grows by the fonts (stored, not compressed) and the new modules.
- Deliberately NOT done: a client-side router (the layout stays the one source); a second
  slide; an icon font; a CDN; the handoff's bundle committed (the operator's to add); the three
  pre-existing PowerPoint defects found on the way (month lines under the opaque lane fills, the
  UNCLASSIFIED marking text in CUI purple, the root relationships not naming the docProps parts) —
  reproduced and recorded in the handoff as next work, not widened into this change.
