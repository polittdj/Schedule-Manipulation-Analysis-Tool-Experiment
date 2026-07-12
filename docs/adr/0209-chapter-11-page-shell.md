# ADR-0209 — Mission Ops redesign step 3 (page shell): chapter 11 "What could go wrong"

## Status
Accepted. Eleventh page shell of step 3, applying the template to chapter 11 "What could go wrong"
= Schedule Risk Analysis at `GET /sra`. Presentation only. The Monte-Carlo runs **client-side on
demand**, so the header reports the **deterministic** structural risk of the SRA-selected file —
no simulation, no new math.

## Decisions
- **`_what_could_go_wrong_header(st)`** (the SRA-selected file; empty when no schedule solves):
  - **Takeaway h1** — "`C activities drive the finish and N more are near-critical (within 5 days
    of float), with R risks registered — run the Monte-Carlo below to quantify the finish-date
    confidence.`" ("every activity is complete" when there is no remaining work).
  - **6-KPI strip** — Critical activities · Near-critical (≤5d) · Negative float · Hard
    constraints · Registered risks · Incomplete activities.
  - **Two composition bars** (`_status_stack`): **Float exposure** (incomplete activities banded
    Critical / Near-critical / Comfortable by total float) and **Risk flags** (Negative float /
    Hard constraints / Registered risks).
- Data from `cpm.timings` + `effective_total_float` for the float bands, the cached
  `analysis.audit` for the hard-constraint count, and `st.sra_risks` for the register. The
  float-exposure basis is `total_float ≤ 0` (correct for this float-exposure framing; the
  stored-flag critical count on chapter 04 may differ by the documented stored-vs-recomputed
  nuance).

## Consequences
- SRA reads as chapter 11 above the (unchanged) risk-input + simulation scaffold. Chromium-verified
  console + daylight, zero console errors ("3 activities drive the finish and 2 more are
  near-critical"). Part of the bundled 08-12 PR.
