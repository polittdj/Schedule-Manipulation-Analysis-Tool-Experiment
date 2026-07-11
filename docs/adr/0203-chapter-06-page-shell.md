# ADR-0203 — Mission Ops redesign step 3 (page shell): chapter 06 "Work piling up"

## Status

Accepted. Sixth page shell of step 3, applying the chapter-01…05 template (ADR-0197…0202) to
chapter 06 "Work piling up" = Bow Wave / CEI at `GET /cei`. Presentation only: no `engine` /
`importers` / `ai` change; every figure is read from the bow-wave dataset the page already
computes (only sums over its monthly series — no new math).

## Context

`/cei` opened straight into the animated bow-wave chart and CEI table with no headline. The
route already computes `compute_bow_wave(...)` — a shared month axis plus per-snapshot
`SnapshotProfile`s carrying the monthly baselined / scheduled / finished profiles, the CEI
(finished ÷ planned for the follow-on month), its period label, and the CEI numerator /
denominator — so a data-driven headline needs no new computation. Chapter 06's chrome already
fires because `/cei`'s title "Bow Wave / CEI" is registered to the chapter in the spine, and
the header renders only past the existing `< 2 versions` guard.

## Decisions

- **`_work_piling_header(wave: BowWave)`** prepends to the CEI body:
  - **Takeaway h1** — "`In <month> the project completed F of the P finishes it had planned
    (CEI c.cc) — execution ran under plan in U of M scored months, and A finishes now sit
    ahead of the data date.`" Honest degradation: no latest CEI → the cross-version
    under-plan sentence; nothing scored → "No month could be CEI-scored… the files carry no
    comparable month-over-month plan."
  - **6-KPI strip** — Versions compared · Latest CEI · CEI month · Planned that month ·
    Finished that month · Months under plan (`U / M`); em dashes when unscored.
  - **Two composition bars** (`_status_stack`): **Latest scored month** (Finished vs Short of
    plan — the CEI numerator vs its shortfall) and **Where the finishes sit** (the newest
    version's scheduled finish months split at the data date: Landed by the data date vs
    Piled ahead of it — the literal bow wave).
- **Data sources are all pre-existing** — `SnapshotProfile.cei / cei_period / cei_planned /
  cei_finished` for the score, `[s.cei for s in snapshots]` for the under-plan count, and
  sums of `latest.scheduled` split at `status_index` for the pile (presentation aggregation
  of engine series, the same class as chapter 04's entered/left sums).
- The scaffold (animated bow-wave chart, stepper, tracked-UIDs form, CEI summary table,
  export bar) is untouched — the header is additive above it. No new CSS.

## Consequences

- Bow Wave / CEI now reads as chapter 06: kicker → takeaway → CEI KPIs → plan-vs-done & pile
  bars → the animated chart and table → Continue → Chapter 07. Verified in Chromium (console
  + daylight), zero console errors; the takeaway's figures are the golden pair's real CEI
  (Jun-26: 3 of 3 planned, CEI 1.00; 67 finishes ahead of the data date).
- Version 1.0.12 → 1.0.13 (cache-bust); wheel + nine installers rebuilt in lockstep.
  Chapters 07-12 follow, one per PR.
