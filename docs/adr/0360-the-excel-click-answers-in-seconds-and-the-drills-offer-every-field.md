# ADR-0360 — The Excel click answers in seconds, and the drills offer every field

- **Status:** Accepted
- **Date:** 2026-08-06
- **Related:** ADR-0359 (the same operator report), ADR-0356 (the CHECK-INPUTS warning this
  makes actionable), ADR-0261 (the OAT page cap), the rank-3 "never a dead link" law

## Context — "Export to Excel does nothing"

Every ⤓ EXCEL button on every page was in fact wired (a precise HTML-parser sweep of all
pages found **0** unwired panels — the first regex probe's 45 were its own false positives,
the anchor-vs-function lesson again). The real defect was measured, not inspected:
`/export/{fmt}/sra` re-ran the 2000-iteration Monte-Carlo AND the full 919-activity
one-at-a-time sweep synchronously on every click — **139.8 s on the committed 2,125-task SRA
schedule** — while the browser showed nothing at all. A silent two-minute wait IS "nothing
happens".

## Decision

1. **Run reuse.** The SSI run and the OAT sweep are cached on the session under their FULL
   resolved-input identity (focus, register toggle, occurrence mode, correlation spec,
   sampler, factor table, factors, Best/Worst pairs, overrides, global triangular, risks,
   branches, conditionals, and the schedule bytes via `content_hashes`). The export reuses a
   matching cached run — measured **140 s → 0.1 s** warm — and the workbook now carries
   EXACTLY the run the operator is looking at (their iteration count, not a silently
   different hardcoded-2000 re-run: a fidelity fix, not just a latency one). Any input edit
   changes the key (mutation-proven).
2. **Honest feedback.** `panelkit.js` fetches the export with a busy-guarded "⤓ PREPARING…"
   state and hands the browser a same-origin blob download; ANY failure falls back to the
   pre-existing navigation. CSP-clean (`connect-src 'self'`).
3. **The register rides Load-from-schedule.** SSI reads its risks off the file's
   `SSI SRA Risk Probability` / `SSI SRA Schedule Impact` fields; the ADR-0356 seed loaded
   factors + Best/Worst but left the register empty — the input mismatch by another door. It
   now seeds the register too (on the committed schedule: R7443 86%/321d, R7433 63%/45d, with
   the exact derived percentages the operator's own register showed), leaves an
   operator-entered register untouched when the file carries no risk fields, and the
   CHECK-INPUTS warning carries a one-click "Use the file's own values" button.
4. **The drills drill and offer everything.** The /sra Float-exposure and Risk-flags bars
   join the sf-drill contract (hover names the segment and count; click lists exactly the
   counted activities). `STANDARD_FIELDS` widens from six fields to the full task-level
   catalog the model carries verbatim (durations/work in the grid's own conventions, stored
   dates, flags, costs, Notes, Total Slack, Outline, Calendar, Priority) — so every drill's
   add-column list, the /groups filters, and every drill Excel export offer any ingested
   standard MS Project field plus every custom field in the loaded files. `None` stays
   `None` — never a fabricated 0.

## Guards

`tests/web/test_export_wiring.py` renders every page and asserts (a) no panel ships an EXCEL
button without a `data-export` wire and (b) every wire answers 200 — mutation-proven by
stripping the /sra wire. `tests/web/test_sra_export_reuse.py` pins reuse + invalidation
(mutation-proven by disabling the reuse branch). `tests/web/test_sra_bars_drill.py` pins the
hover/click/count identity and the field catalog end-to-end into the export (mutation-proven
by stripping the drill wiring).
