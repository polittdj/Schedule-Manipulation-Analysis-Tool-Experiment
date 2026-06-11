# ADR-0025: Multi-version analysis suite — Trend view, Executive Briefing, MS-Project Gantt

- **Status:** Accepted
- **Date:** 2026-06-10 (post-build enhancement, requested by the operator with a reference
  Acumen Fuse® Diagnostic Executive Briefing document)
- **Relates to:** §6.A (UX/visuals), §6.D (trends/manipulation), §6.E (recommendations/briefing),
  ADR-0019 (interactive visuals), ADR-0023 (file-first dashboard), ADR-0024 (audit remediation)

## Context
The operator requires: a minimum of **ten** schedule versions analyzed in one session, independent
analysis on each, **trend analysis across the timeframe** the versions cover, the AI analysis
delivered as an **Executive Summary** modeled on an Acumen Fuse Diagnostic Executive Briefing,
**graphs**, and an **interactive Gantt that mimics Microsoft Project** with user add/remove fields.
The reference briefing happens to describe Project2/Project5 — the repo's golden fixtures — so the
new outputs could be pinned to validated numbers rather than transcribed from the document.

## Decision
1. **`engine/trend.py`** — `compute_quality_trend(schedules, cpms)` runs the §A Schedule-Quality
   metrics across N versions (ordered oldest-first by `order_versions`, the ProjectTimeNow rule)
   and reports each metric's movement with the best/worst version named, phrased like the briefing
   ("Missing Logic: increases over time with the best version being X (0) and the worst version
   being Y (3)"); Logic Density (neutral ratio) uses highest/lowest wording. The worst version's
   offender UIDs ride along for citations.
2. **`ai/briefing.py`** — `build_briefing` assembles the Diagnostic Executive Briefing: workbook
   summary; cross-version Trend Analysis (≥2 versions); per-project summaries (start/completion/
   status dates, normal-activity counts with complete/in-progress/planned percentages, milestone +
   summary counts — UID 0's project row excluded by convention — baseline window and behind/ahead-
   of-schedule days); per-project schedule-quality verdicts per DCMA check. Every sentence is a
   `CitedStatement`; the local backend may rephrase but `reattach()` re-verifies citations, so the
   AI can never alter a number (§6 contract preserved).
3. **Web:** `/trend` (headline table, Net Finish Impact across the series, quality-trend
   sentences, consecutive-pair manipulation signals, SVG trend charts via `static/trend.js` from
   `/api/trend`) and `/briefing` (print-ready render of the briefing). Both ordered by data date;
   both linked from the nav and dashboard.
4. **MS-Project-style Gantt:** the activity grid gains a Timeline column — shared time axis with
   month ticks; red bars = critical, translucent overlay = % complete, diamonds = milestones, thin
   gray bars = WBS summary rows (now included in the activities payload with null floats), amber
   line = data date. Field add/remove toggles (now incl. duration, baseline dates, resources),
   sorting and click-to-drill all apply. Dependency-free (no third-party JS — air-gap posture);
   the air-gap scanner explicitly allowlists W3C XML namespace identifiers (`createElementNS`
   strings are compared by value, never fetched).
5. **Ten-file guarantee:** an end-to-end test uploads 10 versions in one batch and asserts each
   gets its independent report, `/trend` orders all ten with the injected slip visible, and the
   briefing covers all ten projects.

## Why the numbers are trustworthy (Law 2)
Golden-pinned where validated: trend values (Missing Logic 6→6, Logic Density 2.79→2.83, Critical
41→37), briefing progress counts (126 normal; 20 (15.9%)/27 (21.4%) complete; 3 (2.4%)/2 (1.6%) in
progress; 18 summaries), and the Project5 data date (2026-08-27) all match the reference briefing.
Computed dates (completion, behind-schedule days) are the engine's own CPM-derived values — never
transcribed from the reference document (documented calendar-mapping residuals apply, ADR-0013).

## Consequences
- Full suite **497 passed, 3 skipped**; parity 10/10; engine ≈99%, overall ≈99%; zero new
  dependencies; egress + air-gap green.
- The compare view remains for quick two-version checks; `/trend` is the N-version instrument.
- Briefing AI polish defaults to the offline Null backend (deterministic); switching the session
  backend to a local Ollama polishes prose without touching figures.
