# ADR-0200 — Mission Ops redesign step 3 (page shell): chapter 04 "How stable is the path"

## Status

Accepted. Fourth page shell of step 3, applying the chapter-01/02/03 template
(ADR-0197/0198/0199) to chapter 04 "How stable is the path" = Critical-Path Evolution at
`GET /evolution`. Presentation only: no `engine` / `importers` / `ai` change; every figure is
read from the per-version evolution the page already computes.

## Context

`/evolution` is an interactive stepper/Gantt (`path_evolution.js` over `/api/evolution`) that
animates the critical path across versions, but it opened straight into its controls with no
headline. The route already builds `compute_path_evolution(schedules, cpms, target_uid=uid)` — a
`PathEvolution` of per-version `CriticalSnapshot`s (each carrying `critical` / `entered` / `left`
/ `stayed` and the `finish_delta_days` finish move) scoped to any global Analysis Target — so a
data-driven headline is available with no new computation. Chapter 04's chrome already fires
because `/evolution`'s title "Critical-Path Evolution" is registered to the chapter in the spine,
and the header only renders past the existing `len(schedules) < 2` guard, so the snapshots are
always ≥ 2 (the one-version notice is unchanged).

## Decisions

- **`_how_stable_header(ev: PathEvolution)`** prepends to the evolution body:
  - **Takeaway h1** — "`Across N versions the critical path <stability> — E activities entered it
    and L left<finish clause>.`" `stability` is "held completely steady" (zero churn) / "stayed
    largely stable" (churn ≤ updates) / "churned"; the finish clause reports the **net** finish
    move honestly ("slipped D calendar days" / "pulled in D" / "while the finish held"), with
    correct singular/plural agreement and `activity`/`activities` agreement on the counts.
  - **6-KPI strip** (`_stat_cards`) — Versions compared · Critical now · Entered (all updates) ·
    Left (all updates) · Net finish move (signed days, em dash when no move is recorded) · Churn
    per update.
  - **Two composition bars** (`_status_stack`): **Latest critical path** (the newest version's
    Entered vs Stayed, footed with "N on the path now; L left since the prior version") and
    **Total churn** (Entered vs Left summed across every update).
- **Data sources are all pre-existing** — `snapshots[-1].critical` / `.entered` / `.stayed` /
  `.left` for the latest-path composition, `sum(len(s.entered/​left) for s in snaps[1:])` for the
  cumulative churn, and `s.finish_delta_days` (the same calendar-day slip the API serves, 148 for
  the golden P2→P5) summed for the net move. No target UID needed — the scoped evolution already
  reflects the global target.
- The interactive scaffold (`#prevEvo`/`#nextEvo`/`#evoPlay` stepper, `#evoChart`,
  `path_evolution.js`, tier selector, counterfactual panel, filter modes, export bar) is
  untouched — the header is additive above it. No new CSS (reuses the ADR-0197 classes).

## Consequences

- Critical-Path Evolution now reads as chapter 04: kicker → takeaway → churn KPIs → latest-path &
  total-churn bars → the interactive stepper/Gantt → Continue → Chapter 05. Verified in Chromium
  (console rail + daylight top bar), zero console errors; the KPI counts are internally consistent
  (Entered + Stayed = "Critical now"; Entered + Left = churn = "Churn per update" × updates) and
  the takeaway's 148-day slip matches the golden P2→P5 finish move.
- Version 1.0.9 → 1.0.10 (cache-bust); wheel + nine installers rebuilt in lockstep. Chapters 05-12
  follow, one per PR; the cross-cutting chart-contract toolbar remains a dedicated follow-up.
