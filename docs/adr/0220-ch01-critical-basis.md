# ADR-0220 — Chapter-01 Critical KPI + float bands use the progress-aware effective basis (audit M3)

## Status

Accepted. Third theme of the AUDIT-2026-07-13 remediation (PR 1 docs sweep #341, PR 2 presentation
batch #353). Presentation-only reconciliation — no `engine/` change, no new metric math.

## Context

Chapter 01 "Where we stand" (`_where_we_stand_header`) computed its **Critical (incomplete)** KPI from
raw pure-logic CPM float (`cpm.timings[uid].total_float <= 0`) and its **float-remaining bands** from
`analysis.activity_rows["total_float_days"]` — which carries the recomputed pure-logic float. But the
ribbon (chapter 02, `ribbon.py`) and chapter 11 both use the **progress-aware effective** basis:
`_common.is_effective_critical` / `effective_total_float`, which prefer MS Project's **stored** Total
Slack / Critical flag (what Acumen reads) and fall back to recomputed CPM float only when the file
carries none.

On a progressed file the two bases diverge sharply — the flagship landing chapter showed a *different*
Critical count than every other chapter for the same file. On the `Hard_File` golden: pure-logic **90**
vs effective **34**. The chapter's own inline comment even claimed it was "progress-aware — the same
definition the schedule card uses," which was provably false (ADR-0150 already notes the pure-logic flag
"collapses on a progressed file," which is why every other Critical count uses the effective basis).

## Decision

Reconcile chapter 01 to the same effective basis the ribbon and chapter 11 use (audit fix direction 1),
mirroring the ribbon's exact predicate:

- **Critical KPI:** `t.percent_complete < 100.0 and is_effective_critical(t, cpm float | 0)` — identical
  to `ribbon.py`'s `critical` computation.
- **Float bands:** `effective_total_float(t, cpm.timings[uid].total_float) / per_day` over incomplete,
  in-timings, non-summary activities — the same population and basis as the ribbon's float ladder,
  instead of the pure-logic `total_float_days` from `activity_rows`.

No engine change: both helpers already exist and are already imported; this only changes which basis the
chapter reads.

## Consequences

- Every chapter now reports one Critical count per file (Chromium/`TestClient`-verified: ch 01 == ch 02
  ribbon == 34 on `Hard_File`, 49 on `Hard_File_updated3`). The landing chapter no longer over-states
  Critical on a progressed schedule (90 → 34).
- Purely a presentation reconciliation — the effective basis is what Acumen reports and what the parity
  gate is validated against, so this brings ch 01 into line with the reference tools, it does not move
  any validated number.
- Pinned by `tests/web/test_ch01_critical_basis.py`: the rendered ch-01 Critical equals the ribbon's and
  differs from the old pure-logic count on a progressed golden (so a regression back to raw float is
  caught), and the "0 days" float band equals the effective-float population.
