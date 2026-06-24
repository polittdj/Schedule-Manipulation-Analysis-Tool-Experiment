# ADR-0121 — Executive Briefing rebuilt as a leadership forensic summary (+ Word export)

- Status: accepted
- Date: 2026-06-24
- Relates: M18 readability reformat (the prior card-based briefing), the §6 cited-everything
  contract (`ai/citations.py`), ADR-0088 (the last `SCHEMA_VERSION` bump — model unchanged here)

## Context

Operator request, with a worked example (a NASA Glenn "Executive Summary — Forensic Schedule
Health Review"): rebuild the Executive Briefing so it reads like a forensic summary written for
senior leadership **without** a scheduling background. The example is a numbered, plain-English
document — a metadata header + a one-line verdict banner, then sections that walk leadership from
"the bottom line" through performance, the critical path then-and-now, a health dashboard, risks
and opportunities, recommended actions, and how to verify every number — with every claim traceable
to a specific activity by Unique ID, and delivered as a Word document.

The shipped briefing was an Acumen-style diagnostic (Key Assessment → Workbook Summary → Trend →
per-project Project/Quality cards). Accurate and fully cited, but organized for an analyst, not a
sponsor, and with no continuous narrative or Word hand-out.

## Decision

Rebuild `ai/briefing.py` into the example's structure, keeping the tool's deterministic-first,
cite-everything posture (the engine computes every figure; the local model may only rephrase prose,
re-verified by `reattach`). The briefing now emits a metadata header + a status-tinted verdict
banner (ON TRACK / WATCH / AT RISK from finish slip, the duration-based SPI, and DCMA-14 fails),
then numbered sections:

1. **The Bottom Line** — one-sentence verdict, a plain-English "story", and the single most
   important number (the duration-based earned-schedule SPI).
2. **How the Project Has Performed** — progress makeup + S-curve read; what's done / in progress.
3. **The Critical Path — Then and Now** — with ≥2 versions, the real entered/left critical
   activities from `path_evolution`; with one version, an honest note that a baseline critical path
   cannot be reconstructed from a single MPP (it stores only the current Critical flag).
4. **Schedule Health Dashboard** — task status, slippage, SPI, DCMA-14, as a stoplight table.
5. **Risks and Opportunities** — the `recommendations` engine's findings (risk register +
   opportunities), each tied to UIDs.
6. **Recommended Actions** — the same findings as a priority table, + if-nothing-done /
   if-implemented.
7. **How to Verify Every Number** — verification steps, methodology, and limitations.

`BriefingSection` gains a `level` (numbered hierarchy); `ExecutiveBriefing` gains `subtitle`,
`verdict`, `meta_rows`, and `banner`. The `/briefing` page renders one continuous document
(`brief-doc`), and a new `/export/{fmt}/briefing` route plus `briefing_blocks()` produce a matching
**Word (.docx)** and **Excel (.xlsx)** hand-out. Figures come only from the engine
(`compute_finish_forecasts` SPI, `compute_s_curve`, `compute_activity_makeup`,
`compute_path_evolution`, `audit_schedule`, `recommend`); where a figure cannot be derived, the
briefing states the limitation rather than inventing it.

## Consequences

- Leadership gets a sponsor-readable, fully-cited forensic summary and a Word file that mirrors the
  on-screen briefing; `ai/qa.py`'s workbook fact-sheet reuses the new statements unchanged
  (signature preserved). No model field changed, so `SCHEMA_VERSION` is untouched.
- The §6 contract holds end-to-end: every statement and every table row carries file + UID + task;
  empty scopes, undated schedules, and date-less templates degrade to a single cited section.
- Tests: `tests/ai/test_briefing.py` and `test_coverage_briefing.py` re-pin the new outline,
  banner, verdict arms, workday-slip math, and the §6 fallbacks; `tests/web/test_briefing_view.py`
  covers the page, the verdict banner, and the Word/Excel exports; the trend / ask / ten-version /
  qa tests are updated to the new content. Full gate green.
