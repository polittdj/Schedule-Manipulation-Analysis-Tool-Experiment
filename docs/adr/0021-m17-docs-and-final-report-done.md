# ADR-0021: M17 docs + final report; build closeout (DONE)

- **Status:** Accepted
- **Date:** 2026-06-09 (session A18 — Phase 2 build, milestone M17, continuous A7 sitting)
- **Relates to:** §6.A (metric dictionary), §7 Q8 (docs), §8 (Definition of Done), `BUILD-PLAN.md M17`
- **Builds on:** all prior ADRs (0004–0020)

## Context
M17 is the closing milestone: the user-facing documentation set and the requirement→evidence final
report, then flip the build state to DONE.

## Decision
1. **Four closing docs under `docs/`:** `USER-GUIDE.md` (install/launch/use + CUI posture),
   `METRIC-DICTIONARY.md`, `PARITY-REPORT.md` (computed-vs-golden + residual disposition), and
   `FINAL-REPORT.md` (every §6.A–§6.G requirement → module → evidence → status).
2. **The metric dictionary is single-sourced.** `web/help.render_dictionary_markdown()` renders
   `docs/METRIC-DICTIONARY.md`; `tests/web/test_docs.py` asserts the committed file equals the render, so
   the in-tool `/help` and the doc can never drift. The doc carries the one-line regenerate command.
3. **Honest closeout.** The build is declared **DONE for M1–M14 + M16 + M17**, with **M15 (.pbix
   enrichment) explicitly BLOCKED** pending the operator depositing `NSATDeploymentRevisionAlpha.pbix`
   (git-ignored CUI does not travel between sessions, R-12). The final report and HANDOFF state this as
   the single pending **input**, not a build defect; M14 already delivers the interactive-visual
   capability the `.pbix` would inform. Nothing about M15 is fabricated.
4. **RTM/HANDOFF closeout.** RTM Q8 → ✔; the HANDOFF Phase/Gate flips to **DONE** with the M15 caveat;
   the draft PR (#55) is refreshed, not merged (the build never force-merges).

## Consequences
- Every §6 RTM row is `Implemented + Tested + Validated` **except** §6.A's `.pbix` enrichment (◻ BLOCKED).
  The acceptance gate (Acumen Fuse v8.11.0 + SSI) is green; the tool runs from a desktop icon, offline;
  docs are complete. Full suite green (parity + egress + air-gap included).
- Resuming M15 later is a contained task: deposit the `.pbix`, parse it locally (unzip → DataModel +
  Report/Layout), fold its metrics/visuals into the dashboard, and close the last RTM row.
