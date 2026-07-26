# ADR-0296 — The dashboard no longer ships the status-segment UID arrays

- **Status:** Accepted
- **Date:** 2026-07-26
- **Closes:** ADR-0291's named residual (the dashboard analogue of ADR-0288's trend trim)
- **Related:** ADR-0288 (lazy segment drill — the pattern), ADR-0295 (drill resolves the card's
  own file — the precondition), ADR-0249 (measure, don't hand-wave)

## Context

Every dashboard card carried `status_mix_uids`: three UID arrays partitioning the whole schedule
by status (complete / in progress / planned), so a click on a status-bar segment could list the
activities behind the count. The arrays are read **only** on that click — yet they shipped with
every `/api/dashboard` refresh, for every loaded version.

**Measured** (2,126-task golden fixture, ADR-0249):

| N versions | payload | without the arrays | arrays' share |
| --- | --- | --- | --- |
| 1 | 9,709 B | 1,206 B | **87.6%** |
| 10 | 96,991 B | 11,961 B | 87.7% |

Growth per loaded version: **9,698 B → 1,195 B** (8.1×). At the operator's real scale (a folder of
50 versions) that is ~485 KB → ~60 KB per dashboard refresh.

### Why this waited for ADR-0295

The trim replaces "the card ships the answer" with "the server re-derives the answer for the
card's file". Before ADR-0295, the drill resolver silently substituted the active Project's latest
version for any card outside the active population — and the lazy form would have made that bug
*invisible*: `segment=complete` against the substituted file returns a fully self-consistent,
entirely wrong activity list. The explicit arrays at least produced an obviously broken drill.
ADR-0295 fixed the resolution and committed the forward guard (server-resolved segment == the
card's own count, for every card in the manifest); only then was this trim safe.

## Decision

The ADR-0288 lazy-descriptor pattern, applied to the dashboard status bar:

- the card keeps `status_mix` (the counts the bar renders from) and **drops `status_mix_uids`**;
- `dashboard.js` marks each segment `SFDrill.mark(seg, { segment: name }, cardKey, …)` — the
  descriptor form `drilldown.js` has supported since ADR-0288;
- the server resolves `complete` / `in_progress` / `planned` in `_drill_uid_set` (unchanged —
  those segments existed for the trend trim) against the card's own scoped schedule, using the
  same predicates `compute_activity_makeup` counts with.

## Consequences

- Payload growth per version **9,698 B → 1,195 B**; the arrays cannot creep back
  (`tests/web/test_dashboard_status_trim.py` pins the shape, a 4,000 B/version ceiling, and —
  Law 2 — that every segment drill returns **row-identical** results to the explicit-UID path).
  3 of its 4 tests fail on the pre-trim tree; the byte-identity pin passes both ways by design
  (it is the invariant, not the discriminator).
- The dashboard payload golden SHAs (ADR-0281's `test_dashboard_perf_contract.py`) are re-pinned;
  the only delta is the removed key, which the row-level tests prove.
- `test_categorical_bar_drill.py`'s dashboard contract flips from "cards carry the arrays" to
  "cards drill lazily and the counts survive"; the WBS groups **keep** explicit ids on purpose —
  they partition by arbitrary WBS values the server does not re-derive by name.
- `test_dashboard_drill_scope.py` now derives its expected UID sets from the golden fixtures
  directly instead of reading them off the card payload, so the ADR-0295 cross-file guard is
  independent of what the payload ships.
- One less `non_summary` pass per cold card build; the warm path was already zero (ADR-0291).
