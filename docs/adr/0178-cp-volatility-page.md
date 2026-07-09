# ADR-0178 — CP Volatility page: ten membership-churn visualizations

## Status

Accepted. Operator 2026-07-09: "come up with ten different ways to visualize volatility on the
critical path between schedules and over time … which tasks remained on the critical path the
longest and which ones jumped off of it and onto it over time … Research best practices of
others and frame your visualizations to theirs."

## Context

The critical path should be stable: GAO's Schedule Assessment Guide (Best Practice 6 —
maintain a valid critical path) and the DCMA 14-point construct (the critical-path test,
CPLI) treat an erratic controlling chain as a schedule-health failure. The existing
Critical-Path Evolution page shows the path per version; the operator wants the MEMBERSHIP
STABILITY story across the whole series.

## Decisions

1. **New `/volatility` page** (nav: Assessment, after Critical-Path Evolution) built on one
   dataset (`_volatility_data`): per-version effective-critical sets (the same
   stored-Critical/CPM basis every other page uses) reduced to per-task membership vectors
   (tenure, longest streak, on/off flips) and per-pair splits (Jaccard similarity,
   stayed/entered/left). Embedded server-side (`#volData`) — no network call.
2. **Ten visuals** (`volatility.js`, dependency-free SVG), each with a hover explainer and a
   master Prev/Play/Next stepper animating a shared version cursor: (1) stability gauge —
   mean Jaccard with green/amber/red display bands (≳70% stable — display guidance framed to
   the GAO/DCMA expectation, not a published threshold); (2) churn timeline — per-pair
   Jaccard %; (3) entry/exit waterfall — joined ↑ / left ↓ per update; (4) composition area —
   carried-over vs newly-joined share; (5) membership heatmap — task × version presence
   matrix, animated column highlight, top-40 by tenure with the rest disclosed; (6) tenure
   leaderboard — longest on the path; (7) dwell histogram — tenure distribution; (8) jumper
   leaderboard — most on/off flips; (9) jumper timeline strips — on-path intervals; (10)
   animated transition ribbons — stayed/entered/left for the cursor's pair. Plus a sortable
   per-activity scoreboard and an Excel export (`/export/{fmt}/volatility`) carrying the full
   membership vectors.
3. **Engine-true guard**: the page test asserts the embedded dataset reproduces the
   Fuse-pinned critical-path counts (33/53/49 on the updated series), that membership column
   sums equal each version's critical count, and that the pair splits satisfy the set
   identities (stayed+entered = current count; stayed+left = prior count).

## Consequences

- On the operator's four-version Hard_File series the story is immediate: overall stability
  78%, with the updated→updated2 pair the rewired update (56% similarity, 22 joiners) —
  matching the Integrity findings for that pair.
- Verified in Chromium: 10 SVGs, 60 scoreboard rows, stepper animates, zero console errors.
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
