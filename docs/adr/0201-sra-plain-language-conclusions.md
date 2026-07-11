# ADR-0201 — SRA plain-language conclusions ("what the results mean") + Excel export

## Status

Accepted. Operator directive 2026-07-11: deep-dive the newly-committed reference intake —
`106 Advanced Schedule RiskPresentation Lisbon.ppt` (David T. Hulett, "Advanced Project
Schedule Risk Analysis", 276 slides) plus `INT-02-Advanced-Schedule-Analysis.pdf` (ICEAA
2015) and `Concepts, Methods & Techniques.docx` (SEER SRA primer) — and "figure out a way
to draw conclusions about the results when a user runs these simulations that tell the user
what the results mean in simple and easy to understand verbiage that is all downloadable to
MS Excel."

## Context

The deep-dive found the SRA engine already implements most of what the three documents
teach — 3-point triangular/Beta-PERT on remaining duration (completed work fixed, Hulett's
statused-schedule rule), criticality index (Hulett's "risk criticality"), Spearman
sensitivity, the **risk-driver method** (`RiskEvent`: probability × multiplicative impact
mapped to activities = shared-driver correlation), blanket correlation, hard-constraint
capping, P10/P50/P80/P90 + CDF/histogram. What was missing was the *interpretation*: the
page plotted distributions but never said what Hulett says out loud — "the CPM date is
<15% likely to be met", "the 80% target is 9/21", "the 'critical path' is only 18% likely
to delay the project — now turn attention to Units 1 & 3."

## Decisions

- **`engine/sra_conclusions.py`** — a deterministic conclusions layer. `Conclusion` is a
  frozen card (topic / severity good·info·warn·bad / finding / meaning / evidence pairs);
  `conclusions_from_sra(sch, cpm, result)` and `conclusions_from_ssi(sch, result)` adapt
  the two Monte-Carlo models. **No AI, no new statistics**: the sentences are templates
  filled with figures read off the result object, and a test enforces that every digit in a
  finding is backed by that card's evidence pairs (the citations-gate philosophy applied to
  templates).
- **The cards** (emitted only when applicable): Planned-date realism (Hulett's tiers:
  <15% optimistic / <40% worse than a coin flip / ~50% coin flip / solid / conservative) ·
  Commitment dates (manage to P50, promise at P80) · Contingency needed (P80 − plan, in
  working days) · Predictability (P10→P90 window) · Hidden drivers (criticality ≥ 40% but
  not plan-critical — merge bias, the "risk critical path") · Critical-path reliance ·
  Top duration drivers (|Spearman| ≥ 0.25) · Costliest risks (occurrence % + mean slip) ·
  Hard constraints (results understate risk) · Input quality (auto screening vs analyst
  ranges) · Sampling precision (Hulett: 2,500 for decisions, ~10,000 final) · Correlation
  (independent sampling understates spread). A **degenerate SSI run** (zero spread — no
  uncertainty inputs) suppresses the percentile cards and says so honestly instead.
- **Plumbing**: both JSON payloads (`/api/sra`, `/api/sra/ssi`) carry `conclusions`;
  `sra.js` / `sra_ssi.js` render the cards CSP-safely (textContent / `el()`); the `/sra`
  page hosts `#sraConclusions` (its own "What the results mean" panel) and
  `#ssiConclusions` (under the SSI result table). **Excel**: the `/export/xlsx/sra`
  hand-out now opens with a "What the results mean" table (Topic / Severity / Finding /
  What it means / Evidence) — the operator's downloadable deliverable.
- New CSS (`.sra-conclusions`, `.concl-*`) uses only theme tokens (--ok/--accent/--warn/
  --bad), so all four views render correctly.
- Presentation truncation only: ISO datetimes shorten to the calendar day, working-minute
  offsets divide by 480 — no engine math is added or changed.

## Consequences

- Every simulation run now explains itself in analyst-grade plain English, on the page and
  first in the Excel hand-out. Verified in Chromium (console + daylight), zero console
  errors; 12 new engine tests + 4 new web tests pin the tiers, agreement, honesty guard,
  figure-backing, payloads, and the Excel table.
- The remaining Hulett/ICEAA/SEER gaps (probabilistic & conditional branching, correlation
  matrix + eigenvalue feasibility test, Latin Hypercube, JCL/FICSM football, STAT/GAO
  scorecards, SRA-readiness gate, scenario comparison) stay tracked in issue #331 as the
  dedicated advanced-SRA phase.
- Version 1.0.10 → 1.0.11 (cache-bust); wheel + nine installers rebuilt in lockstep.
