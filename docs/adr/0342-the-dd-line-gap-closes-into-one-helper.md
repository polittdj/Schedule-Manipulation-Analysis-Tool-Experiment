# ADR-0342 — the DD-line gap closes into one helper

Status: accepted (2026-08-03) — Phase 3 (UI), the DoD ledgers

## Context

ADR-0341 made the DD-line population a ledger and recorded the gap rather than closing it:
`DD_PENDING` = 8 time-axis charts drawing no data-date marker, and **four hand-rolled
implementations that disagreed with each other** —

| module | stroke | dash | label |
| --- | --- | --- | --- |
| `cei` / `curves` | `var(--accent)` | `6 5` | `"data date"` |
| `drift` | `var(--muted)` | `2 3` | **none on the line** (legend note only) |
| `scurve` | `var(--muted)` | `2 3` | `"data date " + status_date` |

Two colours, two dash patterns, three labelling schemes, and **not one matched the spec**
(`DESIGN-SYSTEM.md` §chart-contract: "a **red** vertical line labeled `DD` / `DATA DATE`"): none
was red, every label was lowercase or absent, and each hard-coded `"font-size": 10` — the
numeric-type-in-JS fork ADR-0298 removed from axis captions.

## Decision

### 1. ONE helper, and its home is a load-order question

`SFGantt.dataDateLine(svg, {x, top, bottom, iso})` lives in **`gantt.js`, beside `tableCaption`**,
for the reason ADR-0340 established: `_LAYOUT` emits `chartframe.js` **after** `</main>`, and most
time-axis charts (`cei`, `curves`, `drift`, `scurve`, and the whole SRA family) are **parse-time
body scripts**. A `window.SFChartFrame` helper would be `undefined` at the moment they draw and the
marker would silently never appear — exactly the defect ADR-0316 had to fix with `defer` on the
blob-driven trio. `gantt.js` is head-loaded, so it serves **both** families. A test now pins the
layout's script order, so the home cannot outlive its justification.

Colour and type come from the theme (`.ch-dd` in `base.css`): `--bad` (red in all four themes;
there is no `--danger`) and the **same** `--sf-fs-axis-title` token `.ch-at` reads, so the queued
crispness change still moves one value. The label is the spec's compact `DD`; the ISO date rides in
an SVG `<title>`, so chartframe's shared hover call-out shows the full `DATA DATE <iso>` — which is
how `scurve`'s appended date survives without the label growing wider than the months it sits
between, and how `drift`'s previously unlabelled line gains one.

### 2. `margin_dashboard`'s two charts get two different answers — from a RENDER

The brief flagged the burn-down for a judgment call. Rendered in chromium with deliberately
irregular status dates (1 week, 1 week, then **15** weeks apart), it spaced all four versions
**evenly**: its `x(i) = L + (R-L)*i/(n-1)` is one slot per loaded version, so the 15-week jump got
the same pixel width as the 1-week gaps and two ticks both read "2026-03". It is `margin.js`'s axis
wearing a date's name — `MarginDashboard.months` is "the whole margin picture **across versions**",
one entry per loaded file, not per calendar month. Its caption now reads **"Schedule version
(status date)"** and it moves to `VERSION_AXIS`.

Its sibling is the opposite case and stayed. The erosion chart's `x(t)` is linear in milliseconds
and its `tmax` is **extended to the projected zero-margin date**, so the latest status date is
exactly the boundary between measured history and projection — the same render bunched the first
three versions at the left and put the fourth far right. One module, two charts, two answers, which
is why the ledger is keyed by **call site**.

### 3. The five SRA charts are a new exclusion family, not pending work

All five declared "Finish date" and were recorded as pending. They plot a **distribution over a
simulated outcome**, and the data date is not on that axis at all. Measured on the `project2_5`
golden: schedule status date **2026-08-27**, `/api/sra` CDF domain **2028-01-21 → 2028-01-28** —
the data date sits ~17 months to the **left** of a 7-day, index-spaced window. That is structural,
not fixture-specific: a Monte Carlo of the project finish samples an outcome necessarily at or
after the data date. Clamping a marker to the left edge would assert the data date **is** the
earliest simulated finish — a figure the engine never produced (Law 2).

Internal consistency agrees: `sra_jcl.js` L136 is the joint (finish, EAC) scatter whose **sibling
cost axis at L189 was already excluded**, and `histogram.js` / `scatter.js` — distributions over an
outcome variable — were already excluded too. The only thing that made these five look different is
that their outcome is denominated in dates.

They get their own `OUTCOME_AXIS` bucket rather than folding into `NOT_TIME_AXIS`, precisely
because the X label *is* a date: the exclusion is a judgment that must be stated and checked, not
one the "is it a date?" predicate can make on its own. Its test asserts **both** halves — X is
date-denominated, Y is a distribution quantity (probability / simulated count / cost).

### 4. `resources.js` bucketing is computed server-side

The one genuinely pending chart. Its buckets are **equal-length** calendar periods (the spec's own
"distribution over months → columns with DD marker"), so the marker has a real position — unlike a
version axis. The **bucket key** is computed by the engine's own `bucket_key` (renamed from
`_bucket_key`; two internal callers) and served in the payload, rather than re-derived in JS: the
three granularities include ISO week numbering (`YYYY-Www`, Monday-start), and a second
implementation of that in the browser is the kind of drift this round exists to close. The line
sits on the **right edge** of the data-date bucket — elapsed left, remaining right — which is
`cei.js`'s long-standing placement. A data date outside the loaded span finds no bucket and draws
**nothing**, rather than clamping to an edge it does not occupy.

## Consequences

`DD_PENDING` is **empty**. `TIME_AXIS` is 6 call sites, all drawing through the one helper;
`VERSION_AXIS` 10, `OUTCOME_AXIS` 5, `NOT_TIME_AXIS` 6, `OPTS_NOT_LITERAL` 1.

The ledger's detector changed with the code. It was anchored on the **comment** naming each marker
block, deliberately not a style match, because the styles were the finding. With one implementation
the honest anchor is the **call**, counted **per module against that module's time-axis chart
count** — `margin_dashboard.js` is exactly why a module-level "has a marker anywhere" flag would
have been wrong: it draws two charts and only one takes a marker.

`test_dd_line_render.py` is new and carries what a source ledger structurally cannot: the marker
paints on both load-order families, in the red token (resolved live against `--bad`/`--accent`/
`--muted` rather than a pinned hex, so it holds in every theme), at the axis-caption type size, and
the `margin_dashboard` adjudication is **rendered** — erosion has the marker, burn-down does not, in
the same page load.

Three reverts, each on a different gate:

| revert | result |
| --- | --- |
| neuter the **shared** helper | **all 4** render tests fail — and the **34 ledger tests still pass**, which is the point: a source census cannot catch a broken helper |
| remove **one** subject (`resources.js`'s caller) | **exactly 1** fails, the other 3 pass — they discriminate |
| `.ch-dd line` `--bad` → `--accent` (CSS) | **4** fail, including the ledger's design-system test — the style assertions bite |

The second is the one ADR-0340's lesson demanded: neutering a shared dependency failing N/N is also
what one test run N times looks like. The single-subject revert is the proof.
