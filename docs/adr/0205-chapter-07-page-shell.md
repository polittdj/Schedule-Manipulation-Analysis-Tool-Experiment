# ADR-0205 — Mission Ops redesign step 3 (page shell): chapter 07 "How we execute"

## Status

Accepted. Seventh page shell of step 3, applying the chapter-01…06 template (ADR-0197…0203) to
chapter 07 "How we execute" = the Performance Analysis Summary at `GET /performance`.
Presentation only: no `engine` / `importers` / `ai` change; every figure is read from the same
throughput / duration-ratio functions the page already charts.

## Context

`/performance` opened straight into the seven G1-G7 chart families with no headline. The route
already has the loaded solvable versions, and the execution-quality functions the page uses
(`compute_bei`, `duration_ratio`, `compute_activity_makeup`) are cheap pure counts — so a
data-driven headline needs no new computation. Chapter 07's chrome already fires because
`/performance`'s title "Performance Summary" is registered to the chapter in the spine, and the
header renders only past the existing "no solvable schedule" guard.

## Decisions

- **`_how_we_execute_header(sch)`** prepends to the performance body, anchored on the **latest**
  loaded version:
  - **Takeaway h1** — "`The project has finished N of M activities (P%); baselined-due work is
    finishing at BEI b.bb — <on/ahead | just behind | behind> the baseline pace, and completed
    work ran d.dd× its planned duration.`" Honest degradation: with no baselined-due work it reads
    "no work is yet baselined-due to measure the execution pace"; with no completed baseline the
    duration clause is dropped.
  - **6-KPI strip** — Activities complete (`N / M`) · Complete (%) · BEI (throughput) · Duration
    ratio (avg) · Missed the baseline · Still to go; em dashes where the basis is absent.
  - **Two composition bars** (`_status_stack`): **Baseline pace (BEI)** — Kept pace vs Missed over
    the baselined-due population (the BEI numerator vs its complement) — and **Duration
    performance** — completed activities banded Under (< 0.95×) / On target (0.95-1.05×) / Over
    (> 1.05×) their baseline duration, with the excluded-no-baseline count disclosed in the foot.
- **Data sources are all pre-existing** — `compute_bei` (value + count/population, the
  ADR-0176 Acumen-validated basis), `duration_ratio` (avg + per-point ratios for the bands, with
  `n_excluded` disclosed, never imputed), and `compute_activity_makeup` (the chapter-01 precedent).
  This is presentation banding of engine outputs, no new metric math.
- The G1-G7 scaffold (version picker, thirteen chart mounts, DRM chips, `performance.js`, export
  bar) is untouched — the header is additive above it. No new CSS.

## Consequences

- Performance now reads as chapter 07: kicker → takeaway → execution KPIs → pace & duration bars →
  the G1-G7 charts → Continue → Chapter 08. Verified in Chromium (console + daylight), zero console
  errors; the figures are the golden's real execution numbers (Project5: 27/126 complete, BEI 0.59,
  DRM 1.44×; Hard_File_updated3: BEI 0.47 = the ADR-0176 oracle) and the degenerate 0%-complete
  Hard_File reads honestly.
- Version 1.0.14 → 1.0.15 (cache-bust); wheel + nine installers rebuilt in lockstep. Chapters 08-12
  follow, one per PR.
