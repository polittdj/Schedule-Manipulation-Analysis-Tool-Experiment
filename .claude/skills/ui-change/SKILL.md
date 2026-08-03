---
name: ui-change
description: Make a change to POLARIS/SMAT's web UI under the Mission Ops design system and its Definition of Done. Use whenever editing web/app.py's markup, web/static/*.js or *.css, a page shell, a panel, a chart, an axis caption, a data-date line, a KPI card, a takeaway headline, a theme token, or any displayed string. Also use when asked to restyle, add a panel or chart, fix a layout or overlap, or add a page. Enforces tokens-only, the chart contract, the DD-line and caption ledgers, and "missing shows —, never a fabricated figure".
---

# UI change (Mission Ops design system)

Binding rulebook: **`docs/DESIGN-SYSTEM.md`** (ADR-0195). Read it for the full spine; this skill is
the working checklist and the traps.

## The two design laws

1. **Nothing styles itself.** Every color, font, radius and shadow comes from a CSS custom property
   in `sf-themes.css`. A hex value in page markup is a build failure (exceptions: the fixed CUI
   marking colors and the risk-heat band colors).
2. **Every visual is an instrument.** A chart without a takeaway headline, a labeled data-date line,
   a legend and the ▦/⤓/⛶ toolbar is not done.

## Never touch the engine for a UI change

`engine/` is off-limits in a presentation change. Every displayed number traces to the engine payload.
A render diff proving the numbers are byte-identical is the standard proof (see `render-verify`).

## Definition of Done (from DESIGN-SYSTEM.md §7)

- [ ] Tokens only; renders correctly in **all four themes** (console / daylight / apollo / jarvis),
      both densities, 90–125% scale
- [ ] Chapter kicker, takeaway `h1` (a sentence **with a number in it**, not a label), one muted
      context line, Continue segue, nav entry with takeaway
- [ ] Every visual: legend, read-me line, ▦ DATA / ⤓ EXCEL / ⛶ ENLARGE toolbar, options persist
- [ ] A DD line via `SFGantt.dataDateLine` **if its x is a real calendar axis** — and either way the
      chart is bucketed in `tests/web/test_dd_line_ledger.py`, which fails until it is (ADR-0342)
- [ ] CUI bars print; controls hidden in print (`data-noprint` / `.cf-bar`)
- [ ] Keyboard focus ring visible (`--focus`); reduced-motion kills animation/timers
- [ ] No remote asset (the air-gap test stays green); no calculation touched
- [ ] Missing values show `—`, never a fabricated figure
- [ ] Any sound follows the audio rule (§8): synthesized WebAudio, gesture-primed, visibly mutable

## One mechanism per job — do not hand-roll a second

| Job | The one mechanism | Why |
| --- | --- | --- |
| SVG axis captions | `SFChartFrame.axisTitles` (`.ch-at`) | ADR-0298/0326 |
| DOM table caption | `SFGantt.tableCaption` → `<caption class="ch-atd">` | in `gantt.js` because it is head-loaded and every captioned table is built by a body script (ADR-0340); **no other module may name `.ch-atd`** |
| Gantt timescale caption | the one slot row `buildTierScale` renders from `data-ts-caption` | ADR-0340 |
| Data-date line | `SFGantt.dataDateLine`, styled by `.ch-dd` | ADR-0342 — most charted pages draw at parse time, before `chartframe.js` exists |
| Panel toolbar / enlarge | `panelkit.js`, **one include per page** | two includes register two delegated listeners and every click nets to nothing |

**Colour and type come from the token, not the call site** — `.ch-dd` reads `--bad` and the same
`--sf-fs-axis-title` token the captions read. No chart may hard-code its size.

## "Time axis" is narrower than you think (ADR-0342)

A DD line goes on a **real calendar axis** only. Two families take none because neither has a
position for one:

- a **version axis** — one tick per loaded file, categorical, *every version has its own data date*
  (note the collision: `margin.js`'s xLabel literally contains the words "data date" and must **not**
  carry a line, so the version check runs BEFORE the date check);
- an **outcome axis** — a distribution over a simulated finish; denominated in dates, not a timeline.

`margin_dashboard` is **two** charts with **opposite** answers: the burn-down spaces versions evenly
(a version axis wearing a date's name) while its sibling erosion chart is linear in milliseconds.
**The ledger is keyed by CALL SITE for this reason.** Measure; do not classify from the label.

## Traps this repo has paid for

- **`--bad` is the red token. `--danger` does not exist.**
- **The missing-value sentinel in `app.py` is the literal `—`, never `&mdash;`.**
- **`node --check` PER FILE** — a glob checks only the first match and exits 0.
- **Counting `<div class=panel` misses the quoted form** `<div class="panel"`. A grep count is not a
  census, in either direction.
- **A class read-back is not a proof of effect.** `.is-big` is only `grid-column:1/-1`, inert on a
  block-layout panel — measure `getBoundingClientRect()` (see `render-verify`).
- **`app.py` is exempt from E501** in `pyproject.toml`; do not fight long HTML f-strings there.
  Everywhere else the limit is 100.
- **Check for JS digest/line pins over a static file BEFORE editing it** — several tests freeze
  `web/static/*.js` by hash and by call-site line.
- **Daylight's nav is a `sticky` full-width bar**; the dark themes use a `fixed` left rail. A clamp
  written for `fixed` only never avoided daylight's bar (OR-02).
- **Carried, measured, NOT fixed:** `/briefing`, `/path` and `/compare` render a bare takeaway `h1`
  with **no** `page-lede`, while `/evm`, `/scurve`, `/margin`, `/groups`, `/integrity` carry one.
  `/driving-path` is an unconverted page — that is its **empty state**, not a gap.

## Sequence

1. Read `docs/DESIGN-SYSTEM.md` and the page's existing shell — match it, do not invent a variant.
2. Edit. One page shell / one panel family per PR — **never big-bang** (ADR-0195 phasing).
3. `for f in src/schedule_forensics/web/static/*.js; do node --check "$f" || echo "JS FAIL: $f"; done`
4. **Render** the page and diff against the pristine tree (`render-verify`), in all four themes.
5. New behavioral assertion? **Prove it can fail** (`prove-able-to-fail`).
6. Run the `full-gate`.
