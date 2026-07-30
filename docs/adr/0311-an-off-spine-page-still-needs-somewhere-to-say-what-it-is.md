# ADR-0311 — An off-spine page still needs somewhere to say what it is

Status: accepted (2026-07-30)
Amends: ADR-0196 (story spine), ADR-0195 (Mission Ops phasing)
Part of: redesign tail **rank 12** (Library/Setup sweep) — first slice

## Context

Rank 12 is the first per-visual normalization batch whose pages are **not chapters**. Ranks 1–11 were
all spine chapters (ADR-0197…0210 are twelve chapter shells). The Definition of Done in
`docs/DESIGN-SYSTEM.md` §7 asks every page for a *"Chapter kicker, takeaway h1, context line,
Continue segue, nav entry with takeaway"* — but `app.py`'s spine builds the story order as
`Setup off-spine`, and `DESIGN-SYSTEM.md:60-62` puts utilities *"in a **Setup** nav group off the
spine … outside the story."* So the DoD's second checkbox cannot apply verbatim to rank 12's pages,
and the operator was asked to decide the vocabulary before any code moved.

**Operator decision (2026-07-30):** off-spine pages get a **non-chapter kicker** and **no Continue
segue**; `/card/{name}` and `/wbs/{name}` get **nav entries**.

A survey then established that **half of that decision was already the shipped behaviour**, which is
worth recording because a previous read of these pages reported the opposite:

* `_chapter_kicker` drops the `CHAPTER NN · ` prefix when `_Chapter.num` is empty, so the four Setup
  pages already render label-only kickers — `MARGIN DASHBOARD`, `METRIC WORKBENCH`,
  `STANDARDS & EXECUTION`, `GROUPS & FILTERS`.
* `_story_footer` resolves position via `_STORY_ORDER.index(ch)`, and `_STORY_ORDER` excludes
  `SETUP`, so those pages already emit no Continue segue and no progress dashes.

The first survey of these pages reported "no chapter kicker" for all six. That was a **measurement
error** — the probe regexed `CHAPTER \d+ ·`, which cannot match a kicker whose number is empty. The
correction matters more than the fix: a conformance sweep driven by a pattern that assumes the
conforming shape will report conforming pages as broken.

The genuine gaps were narrower and both concerned the two **per-file drill** pages:

| page | nav | kicker |
|---|---|---|
| `/wbs/{name}` | **already** a declared beat of chapter 07 — `(("EVM", "/evm"), ("WBS", "@wbs"))` | **none** |
| `/card/{name}` | **none** | **none** |

Both have dynamic titles (`f"{name} — WBS"`, `f"{name} — card"`), which can never resolve through
`_TITLE_TO_CHAPTER` — which is exactly why `_chapter_kicker` already accepts a `chapter` override
*"for dynamic-title pages (e.g. /analysis)"*. `/analysis` uses it; these two never did.

## Decision

1. **The two per-file drills are chapter drills, not off-spine utilities**, so they take the chapter
   treatment their sibling `/analysis` takes — kicker, segue, progress. This follows an existing
   in-repo decision rather than making a new one: `/wbs` was *already* declared a beat of chapter 07.
   `/card` becomes a beat of chapter **01** ("Where we stand"), the chapter whose report it is linked
   beside (`Open report · Card · WBS` in the manifest row actions).
2. **A `@card` route sentinel** joins `@analysis` / `@wbs`, resolving to the first loaded schedule so
   the nav entry is never a dead link; with nothing loaded it resolves empty and the beat is skipped.
   The three sentinels now share one `_PER_FILE` mapping instead of branching per name.
3. **Both drills name their chapter explicitly** via `_page(..., chapter=…)`, the mechanism that
   already existed for this exact situation.
4. **Every Setup rail entry carries a real takeaway, surfaced as the nav link's `title`.** All six
   shipped with `""`. `takeaway` previously fed only the Continue segue — which off-spine pages
   deliberately do not have — so the field had *nowhere to render* on precisely the pages the DoD
   asks for "a nav entry with takeaway". The tooltip is that somewhere.
5. **The Setup rail is pinned by test.** `test_every_setup_rail_entry_carries_a_takeaway` asserts no
   entry has an empty takeaway, that a takeaway is not an echo of the label, and that it reads as a
   sentence.

## Consequences

`/card/{name}` and `/wbs/{name}` gain a kicker, a Continue segue and progress dashes; `/card` gains a
nav entry. The four Setup pages are unchanged on screen except for the new tooltip — their kicker and
segue behaviour was already correct. No calculation is touched and no displayed figure moves.

**Filling `/settings` and `/help` too was deliberate**, though neither is in rank 12's named six.
Leaving four of six Setup entries populated would have read as an intentional distinction; a
half-filled enumeration is the same silent-omission class ADR-0310 had just finished cleaning up on
`/forecast`, where three independent gaps all pointed at one method precisely because nothing asserted
the set was complete. Hence the test, not just the strings.

## What rank 12 still owes

This is the **first slice**, not the batch. Explicitly outstanding:

* **takeaway h1 + context line** on the five pages lacking one (only `/margin` has a takeaway h1) —
  unblocked, ordinary work.
* **The `▦` / `⤓` / `⛶` toolbar and read-me line on every visual**, which the DoD requires and none of
  the six has. Two hard dependencies: `/margin` renders through `margin_dashboard.js`, one of the five
  modules still in the AXIS-TITLES `PENDING` ledger (a batch-3b item); `/workbench` renders through
  `workbench.js`, in `NO_SVG_AXES`, whose DOM caption mechanism ADR-0298 records as *"a separate
  design decision, deliberately not invented here."* Neither can be closed by rank 12 alone.
* **`data-noprint`** is set on none of the six — and still has **zero CSS rules anywhere**, an open
  operator decision affecting ten already-merged contract pages. The DoD's print checkbox is
  unsatisfiable until it lands.

Recording these as owed, with their blockers named, is the point: rank 12 has been "next" for five
consecutive rounds, and it will stay partly open until those three decisions are made rather than
inherited.
