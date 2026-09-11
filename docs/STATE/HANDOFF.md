# Handoff — 2026-09-11 (the /scorecards design page DELIVERED (ADR-0484): the artboard's three-card grid, its verbatim tables laid out fixed, the score from the engine's own field; v1.0.254)

STATUS (current) — `main` @ **`fda4fa06`** (#667, docs-only: #666's merge recorded, the kickoff repointed at this unit). **This session shipped the design page owed five sessions running**: `/scorecards` (`setScreen('sk')`) wears the Control "Assessment Scorecards" artboard — **ADR-0484, v1.0.254**, engine untouched, red-first on a pristine worktree (11/12 layout · 4/5 browser), **19 mutations / 18 red by name** (the 19th behaviourally equivalent by design and recorded), four-theme render census pristine → final identical on every non-design key, `/card` and `/wbs` byte-identical across the shared-helper change. Full suite **5210 passed / 5 skipped**, `-m parity` **96 passed**. **Draft PR #668**, head `3a7d3f9b` (tree `e224d74a…`) before the merge below: **8/8 checks green** (CI run 1837, installer-smoke 701). `main` then moved under it — #667 merged and rewrote the same three state docs — so `origin/main` was merged IN (never rebased) and all three conflicts resolved by hand; see the SESSION-LOG follow-up. Highest ADR **0484**. QC-1/QC-2 bind every session — ADR-0393.

**CARRIED FORWARD from #667, still live and NOT this unit's:** `test_driving_path_whole_schedule_browser.py:104` is **width-racy** — it went red on #667 (docs-only, `src`/`tests` byte-identical to `main`) while `main`'s run 1833 passed on the same code two minutes earlier. The assertion compares the rendered `thead` inner_text of two separately-rendered pages, so it is width-sensitive, and both captures wait on ROWS (`#pathBody tr[data-uid]`), never on the timescale. **Not a flake — a race with a mechanism.** Its own unit; do NOT fix it by widening a wait.

## What landed, in one paragraph

The family's cursor strip as NAVIGATION (`_version_chips(..., query="file")` → `/scorecards?file=<key>`, the path form byte-identical by default) · the page's picker byte-for-byte in the options position · the three scorecard panels VERBATIM in the artboard's `repeat(auto-fit, minmax(320px, 1fr))` grid (`cd-grid-3`) with the reserve card outside it · the artboard's card-head score from the ENGINE's `Scorecard.score` (`5 / 8 · 62.5% of scored`, one decimal — the page's idiom; `—` + an EMPTY bar when nothing is scored; the ACCENT role, never the mock's thresholds) · `/scorecards` added to ADR-0477's sideways-scroll census. Refused and named in the ADR: the mock's colour thresholds · INFO as a caution colour · its status-pill rows (a display-changed `<table>` loses its semantics — priced) · its reserve tiles, its "No new simulation runs" note (**false** here — the card RUNS the Monte-Carlo on demand) and its calendar-day figure (not in the payload) · its take block (the h1 already IS it) · the kicker, the single ⤓ and the Continue footer.

## The defect the first grid WAS, measured

Three cards side by side at 1440 px hold four-column tables that are wider than a third of the page at their natural width: **a 449-px table in a 374-px card (console) · the card's own scrollWidth 463 against 453 (daylight) · 585 in 374 (apollo, mono + uppercase) · 466 in 374 (jarvis)**, and apollo scrolled the DOCUMENT sideways at **1527 > 1440** — the UI-03 class ADR-0477 retired. Fixed by `table-layout: fixed` (a 68-px chip-sized Result column, 27 % / 25 % Check / Detail) + `overflow-wrap: anywhere` + `hyphens: auto` + `white-space: nowrap` on the chips (the first fixed layout broke a verdict as `PAS / S`). After: every table 346 in 374 (425 in 453 daylight), document width 1440 in all four themes, zero page errors. **Each rule ALONE keeps the table inside its card** (a wrap-anywhere cell has a one-character min-content), so the battery mutates both together for the geometry pin and the wrap rule alone for the cell-spill pin; the fixed layout is kept for the column split, not the overflow claim. **Residual, stated:** at 1440 the in-grid cells wrap hard and apollo still breaks long tokens mid-word as a last resort — the mock's compact row is the design's answer and is its own priced unit.

## Traps this session paid for, by name

* **Grep the artifact FIRST for any string you assert absent** — `cal d` lives inside the CUI notice's "technical data"; the probe now reads `reserve needed`.
* **Three instruments found weak BY the battery, rebuilt:** a slice that ended at the reserve card's own `<div class=panel>` could not see a reserve card pulled INSIDE the grid (it now tracks `div` depth) · a class extractor that stopped at the first space read `"cd-score-bar ok"` as clean · a prose word-search flagged the bar's own "checks pass".
* **A rect cannot see text spilling inside a fixed cell** — measure per-cell `scrollWidth − clientWidth` too; and **never pin a panel's `scrollWidth`** — jarvis's corner brackets sit at `right:-1px` on every panel by design.
* **A mutation can be case-equivalent, not weak:** the census's `_FAMILY` regex is case-sensitive, so `scorecardsPanCursor` is out of family for the census too; lowercase `pan` is RED.
* **The battery's "exactly once" guard ABORTED a mutation whose target string occurs in both branches** (`<span class=cd-score-bar role=img`) — that is the harness working; anchor on the branch's own text.
* **The shallow clone's MPXJ lie, again — and the "cheap remedy" is HALF a remedy:** `git log -1 -- tools/mpxj` reads `c3e4cea0` here; `git fetch --depth 1 origin 42d92dc9…` + `SF_MPXJ_REF` satisfies the BUILDER (it verifies the tree) but writes that sha into `.git/shallow`, and `test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact` then refuses the pin as a graft boundary (3 suite failures). `git fetch --unshallow origin` (765 commits, 1.3 GB) is what satisfies both — on the full clone `git log` reads `42d92dc9` itself. `/root/.local/bin/ruff` 0.15.8 shadows the CI-version `/usr/local/bin/ruff` on PATH — run both.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha written here** — the kickoff that opened this session said `b195c7d3` and was already one commit stale (six consecutive kickoffs now), and `main` moved again *during* the PR.

**R-56** (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57/58/59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. Other residuals: ADR-0483's own (a live-peer response is cut at 5 s) · `/settings` horizontal overflow (its own UI unit) · OR-11b (measure the 48-fact cap on a real 32-file workbook first) · OR-11d · the working-minute axis cannot carry a recorded instant on a day boundary · the hint bubble still widens the document while OPEN · **NEW (ADR-0484):** the in-grid scorecard rows as the mock's compact status-pill row without losing table semantics. **The design page: 10 done, 20 artboards remain; next by cost is `/margin` (Control Margin Dashboard, `setScreen('mg')`), the last Control screen.**

**Review cover is still absent** — Codex quota EXHAUSTED on #655–#661; the mutation battery and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
