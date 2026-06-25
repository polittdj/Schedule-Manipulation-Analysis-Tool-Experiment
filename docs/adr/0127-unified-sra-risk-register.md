# ADR-0127 — Unified SRA risk register (enter a risk once)

## Status

Accepted.

## Context

The tool ran TWO independent risk registers on `/sra`:

- **Legacy** (`POST /sra/risk-event`) — a discrete risk driver with a 3-point **multiplicative**
  impact (`RiskEvent.impact_low/ml/high`, duration multipliers), consumed by `compute_sra`.
- **SSI** (`POST /sra/ssi-risk`) — a discrete risk with an **additive** schedule impact in days
  (`ScheduleRisk.impact_days`), consumed by `compute_sra_ssi`.

To make a risk apply to both Monte-Carlo models the operator had to enter it **twice**, once in each
form, keeping the two magnitudes consistent by hand. Operator ask: enter a risk **once**.

## Decision

One **unified** register is the single source of truth; both engine models are derived from it at the
web boundary. The frozen engine models (`RiskEvent` / `ScheduleRisk`) and `compute_sra` are
**unchanged** — the byte-frozen parity tests (`tests/engine/test_sra.py`, the parity gate) are
untouched.

1. **`UnifiedRisk` (web/SessionState model).** A frozen record carrying, for one event: `id`, `name`,
   `probability`, `affected`, BOTH magnitudes — `impact_days` (additive, SSI) and `impact_pct`
   (multiplicative % uplift, legacy; `20` ⇒ ×1.20) — per-model lock flags `days_locked` /
   `pct_locked`, and `consequence_rating`. `SessionState.sra_risks` is now `list[UnifiedRisk]`;
   `sra_ssi_risks` / `sra_ssi_risk_seq` are removed (one list, one `sra_risk_seq`).

2. **One form + one route.** `POST /sra/risk-register` (action add/remove/clear) replaces the two old
   routes, which are removed. The form lives in the SSI panel; the legacy register form is dropped.

3. **Derive at the boundary.** `_risk_events(st)` builds the legacy `RiskEvent`s (`impact_pct` ⇒ a
   point multiplier `low = ml = high = 1 + pct/100`) and `_schedule_risks(st)` builds the SSI
   `ScheduleRisk`s (`impact_days`). The five SRA compute call sites, the OAT exclude set, and the
   matrix/export wiring read from these.

4. **Days ↔ % auto-derive.** Typing one magnitude derives the other from the affected tasks'
   **average remaining duration** (`avg`), so the additive and multiplicative forms produce the same
   **total** schedule impact across the affected set: `days = pct/100 × avg`, `pct = days/avg × 100`
   (an n-task additive `+D` to each equals a multiplicative `×(1 + D/avg)` in aggregate). The client
   (`static/sra_risk.js`, fed a `uid → remaining-days` map) does it live; the server mirrors the exact
   math (`_reconcile_magnitudes`) for the JS-off and JSON-load paths. A field the operator sets is
   **locked** (used verbatim for that model); the unlocked one is the derived value.

5. **Save/Load.** `_ssi_setup_dict` / `_apply_ssi_setup` persist/restore the unified risks (both
   magnitudes + lock flags). An older setup that carries only `impact_days` still loads — the % is
   derived from the affected tasks' remaining and days is locked.

## Consequences

- A risk is entered once and drives **both** Monte-Carlo models; the two magnitudes stay consistent
  automatically, with an explicit override+lock per model when the operator wants exact control.
- No engine change, no `SCHEMA_VERSION` change (the frozen domain models are untouched; `UnifiedRisk`
  is session state). Offline / std-lib / air-gap posture unchanged; `sra_risk.js` is vendored.
- The ~5 web test files that posted to the two old routes were rewritten to the unified route/model;
  new tests cover the derive + lock behaviour and that the one register feeds both models.
- **Follow-up (queue #2):** the unified Save/Load is in place here; any further setup-version polish
  rides on top.

## Alternatives considered

- **Additive (keep both old routes underneath).** Less test churn, but two systems coexisting in a
  testimony tool is a maintainability trap — rejected in favour of the clean single source of truth.
- **A single magnitude (days only or % only).** Rejected: the legacy multiplicative and SSI additive
  models are both wanted, and they are not interchangeable per-task without the remaining-duration
  basis — so the record keeps both, with one derived from the other.
