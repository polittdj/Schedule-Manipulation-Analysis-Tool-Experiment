# Handoff — 2026-09-24 (One-Pager DATE WINDOW on Timeline + Compare, and R-71's flag half **CLOSED** — finished work is never on the critical path while `is_critical` stays pure (ADR-0527) — **v1.0.290**)

STATUS (current) — branch **`claude/tender-ptolemy-ua1y6k`**, draft PR opened this session (the operator merges; never marked ready here). Based on `main` @ **`8c71c639`** (#714, ADR-0526, v1.0.289 — merged 2026-09-23; #713 f4703fd2 before it). §0's anti-foreign-prompt block was RUN and the tree agreed on every point (8c71c639, 813 commits, `src` present / `app` absent, both workflows, 1.0.289, highest ADR 0526). The committed NEXT-SESSION-PROMPT / HANDOFF were stale (pre-#713/#714) and are refreshed here. `src/` changed: wheel + nine installers rebuilt as the LAST step, so **EIGHT checks**. Highest ADR **0527**. Version **1.0.290**. Schema **2.17.0** (unchanged). QC-1 / QC-2 / QC-3 bind every session.

## What landed — two units, rulings asked and given 2026-09-23

**1. The One-Pager date window** (operator request): two date inputs (From / To · Apply dates · Show all dates) on `/onepager` and `/onepager-compare`. The timescale is EXACTLY the window (never whole months, never widened to today; today drawn only inside it). Rulings: a straddling task is **kept and cut at the edge** (label keeps its true finish); only a task wholly outside is omitted — **and named**; a compared row stays when its **prior OR current** position touches the window (a slip OUT of the window stays, its arrow to the edge with its true ±N cal d); the window scopes **everything about the slide** — slide, PowerPoint, takeaway, per-swimlane summary (recounted), ▦ DATA, ⤓ EXCEL (window + every omitted item in the Notes table). A plain POST form: no JS / CSS / painter change, so no digest or locator re-baseline. Bad windows are refused by name and the current one kept; an empty window keeps its own controls; clearing a list clears its window. No window = byte-identical (600-layout digest `e34820f5…` before = after).

**2. R-71's flag half** (operator ruling: keep `is_critical` pure): `CPMResult.critical_path` drops `is_recorded_complete` work; `TaskTiming.is_critical` unchanged. UID-exact against MS Project's stored Critical on the 15 committed goldens keyed on PATH (7,935 activities; 4 → 0 engine-only: Hard_File_updated2 UID 290, Hard_File_updated3 UID 261 ×2, Large_Test_File2 UID 6956). DCMA-12's own copy of the filter became unreachable (`CPMResult` is built in one place) and was removed. `/path`'s headline count −1 on exactly those four files; min float unchanged on all 15. R-71's RECORD limbs (LS = AS / LF = AF pins, the 22 clamped late finishes) stay OPEN.

## How it was verified

QC-3 attacked 8 assumptions before/while editing — **3 fell**: clamp-to-chart drew 88 day-one bars BACKWARDS past X0 (3-pt floor order; 0 / 3,751 after); the render showed a window-filling Compare bar's label over the swimlane names (label-on-bar for windowed rows; clipped 378 → 20 / 7,161, Timeline 0 / 6,945); and an inherited test docstring ("the corpus no longer holds a finished activity on the critical path") was FALSE. Red-first: window reports 12/13 red on pristine, page 11/11, R-71 2/3 (controls proven by mutant). **Mutation:** window battery on a separate model in a scratch copy, 35 mutants, 32 red first run; 2 survivors = one missing test (sliver edge month), now red by name; 1 survivor pre-existing (below). R-71 3/3 mutants red by name; the DCMA-12 rig re-baseline red with the engine rule removed. Rendered in Chromium through the REAL form, 4 themes, 0 shapes outside the chart, 0 page errors. Parity **249 / 249**, no skip.

## Deliberate re-baselines

`test_dcma12_never_injects_its_delay_into_work_that_has_already_finished`: rig path `(1, 2)` → `(2,)` with `timing(1).is_critical is True` pinned beside it; its false docstring corrected.

## Not done (measured, left) · carried forward

20 / 7,161 fuzzed windowed Compare labels still clip (DUPLICATE NAME rows with ONLY a full-width ghost) · the ADR-0446 `6.5`-pt month-letter threshold survives a one-tenth nudge (M23b — the no-window pin's fixture never crosses that band) · `test_ui_control_effect_census` cannot see a plain form BY CONSTRUCTION (zoom/fit/pan families only) · carried from ADR-0526: tag text overruns under the substitute font, `read_xlsx` r-less cells on the SRA path, no overdue cue, no template column D. **UNVERIFIED:** PowerPoint itself. **Next:** R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-71's record limbs; R-68 waits on the operator.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
