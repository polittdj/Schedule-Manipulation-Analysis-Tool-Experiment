# ADR-0425 — The off-spine pages get the prototype's four rails, and off-spine becomes declared

**Status:** Accepted · **Date:** 2026-08-17 · **Amends:** ADR-0196 (story spine), ADR-0311
(off-spine kickers) · **Ships:** `web/chrome.py`, `web/app.py` (re-export only)

## Context

The Mission Ops prototype (`Mission Ops Redesign v2.dc.html`, the MERLIN deck — the design
handoff's current pixel truth) groups the non-story pages into **four** named nav rails:

| rail | prototype entries |
|---|---|
| FORENSICS | Schedule Integrity |
| LIBRARY | Metric Workbench · Metric Lab · Segment Forecast · WBS Rollup · Schedule ID Card · EVM · Portfolio at Scale · Beyond the Schedule |
| CONTROL | Margin Dashboard · Standards & Indices · Assessment Scorecards |
| SETUP | Groups & Filters · AI Settings · Metric Dictionary |

The repo shipped **one** rail, `SETUP`, holding Margin Dashboard, Metric Workbench, Standards &
Execution, Groups & Filters, AI Settings and Metric Dictionary — three analysis surfaces filed
under a utilities heading. The remaining prototype rail members were reachable only as **folded
beats** under a chapter: `/integrity` and `/scorecards` under chapter 02, `/evm` and `@wbs` under
chapter 07, `@card` under chapter 01.

Beats are small, muted sub-links; the operator's own escalation during the design sessions was that
Schedule Integrity — the manipulation-detection surface, one of the two things this tool exists to
do — read as a panel rather than a destination. Filing it as a footnote under "Can we trust the
plan?" is the same defect one level up.

## Decision

Split the single `SETUP` rail into `FORENSICS` / `LIBRARY` / `CONTROL` / `SETUP`, and promote the
five folded beats to rail entries.

**This is a NAV-PLACEMENT change and nothing else.** Chapter membership is carried by
`_Chapter.titles` and `_page(..., chapter=…)`, not by `beats` — `beats` only ever rendered links.
So `/integrity` and `/scorecards` remain **Chapter 02** pages and `/evm`, `/wbs`, `/card` remain
Chapter 07/01 drills: their kickers, their Continue segues and their story position are byte-for-byte
unchanged. The three modules that document this coupling in prose (`integrity.py:187`,
`ribbon.py:179`, `scorecards.py:186`) stay correct.

Two entries the prototype's LIBRARY carries are **deliberately not added**: **Metric Lab** and
**Segment Forecast**. Metric Lab is the prototype's single-metric focus mode of `/workbench` and has
no route in the repo; Segment Forecast exists upstream only as `_field_forecast_panel` on
`/forecast` and `/evm`, not as a page. A nav entry pointing at a route that does not implement the
screen is a dead link wearing a label — those two stay on the gap list until the screens exist.
Likewise **Portfolio at Scale** and **Beyond the Schedule**, which have no route at all.

## Off-spine membership is now declared, not inferred

`_STORY_ORDER` selected the narrative pages with `label != "SETUP"`. Under that rule, adding any
rail would have **silently injected its pages into the story order** — into the Continue segue, the
progress dashes and `_story_footer`'s `index()`. Membership is now an explicit frozenset,
`_OFF_SPINE`, and the nav's muted `setup` treatment keys off the same set.

The guard for this was **initially defective and the mutation caught it**. The first assertion was
"no `_OFF_SPINE` page appears in `_STORY_ORDER`" — circular, because both sides read `_OFF_SPINE`:
removing a rail from the set moves the page *and* the expectation together, and the check stays
green. Mutation M4 (drop `FORENSICS` from `_OFF_SPINE`) **survived**. The rewritten guard names the
five story rails independently and asserts `_SPINE`'s sections partition exactly into
`story_rails | _OFF_SPINE`; M4, M5 (rename the rail) and M6 (drop the rail) then all go red.

This is the repo's own recurring lesson — *a mutant that misses its subject proves nothing*, and *a
hand-maintained list is a stale list waiting to happen* — reproduced one more time.

## A per-file rail entry with no file is skipped, not pointed at "/"

`@wbs` and `@card` resolve to `""` until a schedule is loaded. As beats they were dropped in that
state (`if r:`), but `_chapter_link` falls back to `or "/"`, so promoting them unchanged would have
rendered two nav entries that silently land on the dropzone. The section builder now filters on
`_resolve_route(...)` before rendering — the same "skipped, not broken" rule ADR-0255 applies to the
role Start-here cards. A rail whose every entry is unresolvable renders no empty heading.

## Verification

`tests/web/test_target_and_theme.py`, three tests, each mutation-proven red before green:

| mutant | expected | result |
|---|---|---|
| M1 blank a FORENSICS takeaway | takeaway guard red | red |
| M2 revert `_STORY_ORDER` to `label != "SETUP"` | story-order guard red | red |
| M3 remove the unresolvable-route filter | per-file-skip guard red | red |
| M4 drop `FORENSICS` from `_OFF_SPINE` | story-order guard red | **survived → guard rewritten → red** |
| M5 rename the `FORENSICS` rail label | rails-navigable red | red |
| M6 drop the `FORENSICS` rail | rails-navigable red | red |

`test_every_setup_rail_entry_carries_a_takeaway` is generalised to
`test_every_off_spine_rail_entry_carries_a_takeaway` and now walks **every** rail in `_OFF_SPINE`
rather than the one named `"SETUP"`, so a future rail added with blank takeaways cannot pass unseen.
ADR-0311's requirement is unchanged; only its population is now computed.

## The release, and a deferral that did not survive its own gate

The first draft of this ADR deferred the version bump, reasoning that the wheel and nine installers
could not be rebuilt in this session and that a bump without them is a half-made release.

**The gate refuted that.** `test_embedded_wheel_is_in_lockstep_with_the_source_tree` (ADR-0148)
compares every packaged `schedule_forensics/**` file inside the embedded wheel byte-for-byte
against `src/`, so touching `chrome.py` fails it whether or not the version moves — the deferral
was not available, only unnoticed. Installing `build` and running the two documented commands
worked offline:

```
python -m build --wheel --outdir dist/wheel
python tools/installer/build_installers.py dist/wheel/schedule_forensics-1.0.212-py3-none-any.whl
```

So this ships as a normal release: **v1.0.211 → v1.0.212**, wheel + nine installers regenerated.
SCHEMA is untouched (no payload shape changed). The lesson is filed: *a constraint assumed from
the outside is a hypothesis* — the artifacts were one `pip install` away, and the gate, not the
reasoning, is what established it.
