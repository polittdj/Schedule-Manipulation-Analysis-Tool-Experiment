# Handoff — 2026-08-31 (WP1 COMPLETE: the census went sitewide and its first run caught two dead control families; S5 fixed — the /path grid windows its rows 33x faster; ADR-0442, v1.0.224)

> ## STATUS (current) — **WP1 COMPLETE on branch `claude/polaris2-audit-wp1-gkhubc` (from main @ `d56ad3f9`, the WP0-addendum merge). The campaign runs under QC-1/QC-2 — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0442**; version **1.0.224** (shipped code: `static/path.js`, `static/gantt.js`,
> `static/colresize.js`, `static/app.css`); wheel + nine installers rebuilt in lockstep. Ledger:
> **docs/STATE/AUDIT-2026-08-27.md** WP1 section — now carrying the 27-row UI map with per-row
> status. Gate numbers: SESSION-LOG 2026-08-31 entry, recorded AFTER the runs (QC-1).
>
> ## The full M1 census is computed and sitewide — and it caught real defects on its first run
> `tests/web/test_ui_control_effect_census.py` (57 tests, ~2:30): **34 page states** (33 HTML
> routes computed from the app's own route table + the /driving-path trace state) × three
> layers — pages ≡ route table · in-family controls exactly (65 id'd + 358 id-less: 220
> chartframe buttons, 138 sf-frame steppers; recognizer runs on id+className ONLY, measured
> free-text false-positives ruled it) · 8 structural floor families (76 hosts · 55 cf-bars ·
> 109+33 legend · 49 grips · 7 sticky · 267 drills · 180 enlarge) + zero pageerrors sitewide.
> Every id maps to a driver test or an explicit `WP2:M3`/`WP2:M5` deferral; a typo'd driver
> name is RED (meta-guard). 17-mutation battery red BY NAME (7 census halves + 10 driver
> falsifications). New drivers: /analysis zoom/fit (#vizZoom surface) · /sra grid zoom/fit ·
> **Size% ~2.0× measured on all five consumer pages** · chartframe zoom/Reset/full-screen ·
> legend toggle + show-all · column drag-resize · sticky-scrollbar both directions ·
> bar-click drill · enlarge-then-print (overlay returns to static under print media).
>
> ## Three defects, CONFIRMED-FIXED red-first (ADR-0442)
> **UI-01 drag-resize grips were 7×0px** — Chromium ignores top/bottom/%-height on abs-pos
> children of table cells, so every frozen Gantt header's grip sat unhittable at the cell's
> static position under passing byte-pins. Fixed: `sizeGrip` measured geometry (7×77px on the
> right edge); real-mouse drive works. **UI-02 the sticky proxy scrollbar tracked content by
> race** — attach at DOMContentLoaded observes an empty pane (tables arrive by async fetch);
> first zoom left the inner width at the fitted 1118px vs an 8747px pane = dead slider. Fixed:
> a childList observer adopts the table whenever it (re)appears. **S5 (the ADR-0441 deferral)**
> — one-shot paintRows at 2,280 generated rows: 1,623 ms median → **49 ms** (33×), first paint
> 7.8s → 0.5s, DOM 104,728 → 19,066. Windowed slice ±40 rows at ≥400 rows, flat output only;
> full-paint escapes pinned (groups · Show-links · Find · beforeprint). Two probe-caught
> sub-defects: the tbody clear clamps scrollTop to 0 BEFORE the slice computes (capture →
> slice → restore), and stale-pitch spacers undershot jump-to-bottom (measured re-true +
> compensation). Neighbour suites veto held: all 18 pre-existing browser tests green.
>
> ## New instruments
> The sitewide census (57) · `tests/web/scale_schedule.py` (deterministic row-scale MSPDI
> generator — the ROW COUNT axis; TP5 stays the SPAN axis) ·
> `tests/web/test_path_row_windowing_browser.py` (5 tests, 900/300 generated rows; 3 observed
> RED pre-fix by name + 2 PASS-side pins whose teeth the 5-mutation battery proved).
>
> ## Traps paid for THIS session — check by name
> **A control-census signature must be structural (id+class), never free text** — schedule
> names ("Fit-Out"), "dis-play"/"s-pan" in prose, and `tooltips.js` moving title= at load all
> false-positive; and `pan` needs `(?!d)` or every "expand" joins the family · **the tbody
> clear clamps scrollTop before your slice math runs** — capture the scroll position BEFORE
> `innerHTML=""`, and restore after · **a mutation battery piped through `head` SIGPIPE-kills
> the script mid-mutation** — the second battery run died after P1's mutation and left it in
> the tree; never pipe a battery, and diff the tree after · **`elementFromPoint` below the
> fold hits the wrong element** — scroll the grid into view before hit-testing (the WP0 KPI
> trap, third appearance) · **the Name column's CSS min-width and Chromium's min-content
> floor both out-floor a JS clamp** — assert the styled width AND a sane measured range, not
> one number.
>
> ## Operator-facing state
> After this PR merges the operator re-downloads once (banner must say **v1.0.224**): their
> 2,301-activity /path then rebuilds in ~50 ms instead of 1.4–5 s, the bottom proxy scrollbar
> follows every zoom, and column drag-resize works for the first time. /evolution at their
> scale still needs their next multi-version load — do not chase.
>
> ## Next — campaign queue
> **WP2** (M3 steppers/autoplay clock-stepped — 47 census'd controls + 138 sf-frame buttons
> carry explicit WP2:M3 markers; M5 real #themeSelect across 4 themes / language / taskinfo,
> and the /mission 30-hosts-vs-9-cf-bars design question) → **WP3** (M4 SRA grid
> edit/paste/save) → **WP4** (route-coverage instrument + the 08-26 `startup_failure`
> root-cause; VERIFY a CI run appears per push meanwhile) → **WP5** (BOTH folder builds — the
> three 2026-08-21 folder-gesture facts govern) → **WP6** (ledger highs: CPM-01 · CPM-02 ·
> MC-02 · MC-03 · MAN-01 · REC-02; parity-sensitive rows through the metric-parity skill; any
> golden shift = CONFIRMED-DEFERRED, never a silent re-pin) → **WP7** (thin dims,
> `ai/txlog.py` first — Law 1) → **WP8** (consolidated report + roadmap by testimony risk).
> Do-not-fix-blind rows unchanged (ledger WP1 section + AUDIT do-not-fix list).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
