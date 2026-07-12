# ADR-0210 — Mission Ops redesign step 3 (page shell): chapter 12 "The briefing"

## Status
Accepted. Twelfth and final page shell of step 3, applying the template to chapter 12 "The
briefing" = the Executive Briefing at `GET /briefing`. Presentation only; every figure is the
briefing's / audit's own — no new math.

## Decisions
- **`_the_briefing_header(briefing, sch, cpm)`** — the executive synthesis, rendered **outside**
  the `#briefingBody` div so it is stable when the local AI swaps the polished body in:
  - **Takeaway h1** — "`Bottom line: the schedule is <verdict> — SPI <x>, forecasting a finish of
    <date>, a <slip> slip from baseline.`" (built from the briefing's own `verdict` + `banner`).
  - **KPI strip** — the briefing's `banner` headline figures verbatim (Status / SPI / Forecast
    finish / Baseline finish / Slip — up to six).
  - **Two composition bars** (`_status_stack`): **Action items by severity** (High / Medium / Low
    findings from `recommend`) and **Quality snapshot** (DCMA-14 Pass / Fail / N/A from the audit).
- Being the last chapter, it has no "Continue → Chapter 13" (the spine's final beat).

## Consequences
- The briefing now opens with the verdict-driven takeaway + banner KPIs + action/quality bars, then
  the full cited briefing. Chromium-verified console + daylight, zero console errors ("Bottom line:
  the schedule is AT RISK — SPI 0.470, forecasting a finish of Tuesday, January 25, 2028, a +142 wd
  slip from baseline"). **Completes the 12-chapter story spine.** Part of the bundled 08-12 PR;
  version 1.0.15 → 1.0.16, wheel + nine installers rebuilt in lockstep at the bundle head.
