# ADR-0196 — Mission Ops redesign step 2: the story-spine global chrome

## Status

Accepted. Operator 2026-07-11: after ADR-0195 (four-theme tokens) landed, chose "Full story spine
now" for the chrome step of the Mission Ops redesign — the whole global chrome in one PR rather than
phased.

## Context

The nav was six handbook-function groups (Overview / Assessment / Control / Risks / Reporting /
Setup) in a horizontal top bar. The redesign re-frames the app as a **three-act, twelve-chapter
story** — Situation → Diagnosis → Outlook — walking an analyst through where the project stands, why
it is moving, and where it lands. Two raw Target-UID inputs (the header endpoint box and the SRA
focus box) could disagree.

## Decisions

- **Story-spine model** (`app.py`, `_SPINE` / `_Chapter`): a single source of truth — LOAD (00
  Import) · OVERVIEW (Mission Control) · ACT I·SITUATION (01–02) · ACT II·DIAGNOSIS (03–08) ·
  ACT III·OUTLOOK (09–12) · SETUP (off-spine). Each chapter folds its **beat** pages (secondary
  routes) as sub-links, so every one of the 27 existing routes stays reachable — no broken
  bookmarks (pinned in `test_app.py`). `titles` map each `_page(...)` title to its chapter; a
  `@analysis`/`@wbs` sentinel resolves to the first loaded schedule's report.
- **Nav render** (`_render_nav`): server-rendered so the milestone selector and the chapter-01 link
  read the session. **Left rail** on the three dark views (console/apollo/jarvis, ≥761px) via
  `html[data-theme=…]` CSS repositioning the existing `<header>` to a fixed vertical column (main +
  CUI bars shift right) — no DOM restructure; **top bar** on daylight and on mobile (the burger
  layout is untouched, ≤760px). Active state: the tuned yellow pill on the top bar, a panel-fill +
  keel-accent inset on the rail. The globe insignia rides under the brand at the rail head.
- **Chapter kicker + Continue footer + story progress** injected centrally in the `_page` body
  assembly (keyed off `title`, no per-route edits): a `CHAPTER NN · NAME` kicker, and a foot with
  the STORY-SO-FAR progress dashes (current chapter marked server-side; `story.js` tints visited
  chapters from a cross-page localStorage list) plus a `Chapter NN → <name>` Continue button.
- **Global Analysis-Target selector** (`_render_target_control`): replaces the raw Target-UID box
  with a **milestone dropdown** ("Measure to …") built from the loaded versions' `is_milestone`
  activities (+ "Project finish" = whole schedule, + the current target as a custom option if it is
  not a milestone). It posts to `/target`, and `SessionState.set_target` now drives **both** the
  endpoint scope **and** the SRA/SSI focus (`sra_focus_uid`) — one target, never two. The SRA
  in-panel focus remains as an explicit override.
- **Tests**: `test_app.py` nav test rewritten for the spine (six-label → act-label, 18-href
  no-broken-bookmarks kept); new story-chrome + target-selector + `set_target`-unification tests;
  per-link nav tests loosened to the durable `href="…"` contract; `test_responsive` desktop-nav
  test repointed to `.nav-spine`.

## Consequences

- Every page now reads as a chapter with a clear "you are here" and a one-click path to the next
  chapter. All four views verified in Chromium (rail on the three dark views, top bar on daylight,
  mobile burger intact, print reclaims the rail margin), zero console errors.
- Version 1.0.5 → 1.0.6 (cache-bust the changed assets, ADR-0148); wheel + nine installers rebuilt
  in lockstep. `story.js` is a new vendored module.
- **Not in this step** (per the phased plan): the per-chapter data-driven takeaway h1 and the full
  page-shell restyles (step 3, one chapter per PR), and locally-vendored Barlow / IBM Plex Mono
  fonts. Full two-way binding of the SRA in-panel focus back to the global target is a refinement.
