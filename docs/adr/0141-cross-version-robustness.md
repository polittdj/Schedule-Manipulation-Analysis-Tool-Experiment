# ADR-0141 — Cross-version robustness: tz normalization, XER stored float, one rounding convention

## Status

Accepted. Part of the 2026-07-01 QC audit remediation (batch R4). Two audit findings in this batch
are deliberately **dispositioned without a computation change** (D14 documented + parked; D20
reverted after the oracle check) — recorded here so the reasoning is durable.

## Context / Decisions

- **D11 (MEDIUM) — tz-aware JSON datetimes crashed every multi-version page.** The friendly JSON
  importer preserved `tzinfo` while MSPDI/XER strip it (`_common.parse_datetime`); one hand-written
  `"status_date": "…Z"` mixed with any naive version raised
  `TypeError: can't compare offset-naive and offset-aware datetimes` in `trend.order_versions` —
  the funnel for trend/S-curve/briefing/manipulation views. **Fixed:** `json_schedule._dt` now
  normalizes to naive exactly like the other importers.
- **D12 (MEDIUM) — XER never populated the stored Total Float.** The TASK table carries
  `total_float_hr_cnt`, but the importer set neither `stored_total_float_minutes` nor
  `stored_is_critical`, so `effective_total_float` — the "source tool's stored, progress-aware
  float wins" Acumen-parity path — never engaged for P6 files. **Fixed:** `total_float_hr_cnt`
  maps to `stored_total_float_minutes` (hours → working minutes, half-up; absent stays `None`).
  XER has no stored critical flag; `stored_is_critical` remains `None` by design.
- **D19 (LOW) — two Logic Density rounding conventions.** `schedule_quality.py` used banker's
  `round()` while `ribbon.py` uses the Fuse-validated `ROUND_HALF_UP` ("2.625 → 2.63"); the
  quality-trend page trended the non-Fuse value and could disagree with the ribbon by 0.01 at
  exact halves. **Fixed:** `schedule_quality` and `engine/metrics/derived.py` (Layer A rates) now
  round half-up. No golden value sits on an exact half, so no pinned number moves.
- **D14 (MEDIUM) — SN07 "Remaining Duration Increases" measures total duration. DOCUMENTED +
  PARKED, not changed.** The audit showed the metric counts a completed activity whose actuals ran
  long and misses a true remaining-duration increase. However: the §E change metrics are
  **engine-pinned awaiting Acumen §E re-validation** (golden `_deltas`), `web/help.py` documents
  the implemented formula (`count(duration_now > duration_prior)`), and the authoritative Fuse
  formula lives in the artifact-gated `.aft` Bible. Changing pinned semantics now would be a guess
  at the oracle (Law 2). **Disposition:** a prominent caveat in `help.py`/METRIC-DICTIONARY (what
  the formula does and does not consult), and the semantic question parked as artifact-gated —
  re-derive from the `.aft` verbatim formula when deposited (it may also explain the ADR-0013
  7-vs-8 residual).
- **D20 (LOW) — float bands read raw CPM float while DCMA-06/07 read stored float. REVERTED after
  an oracle check, then documented.** Switching the bands to `effective_total_float` was
  implemented and immediately falsified by the goldens: the 0-day total band at **raw CPM float
  reproduces the Acumen "Critical" parity counts** (P2 41 / P5 37, pinned), and stored float moves
  P2 to 39 — breaking a validated match. The reference tools themselves mix float sources, so the
  in-page inconsistency the audit flagged is **reference behaviour, not a defect**. The code is
  unchanged; the float-source design is now documented in `float_bands.py`'s docstring, and the
  question is flagged for re-examination only against a fresh Fuse export.

## Consequences

- Multi-version pages are robust to tz-carrying JSON inputs; P6 imports now engage the same
  stored-float parity path as MSPDI; one rounding convention (half-up) everywhere a displayed rate
  is rounded. Regression tests in `tests/engine/test_cross_version_robustness.py`.
- D14/D20 stand as **honest, documented dispositions**: the misleading part (an unstated caveat, an
  undocumented design choice) is fixed in documentation; the pinned numbers stay exactly where the
  oracle evidence puts them. Both are listed for artifact-gated re-verification.
- Full gate + parity green; no golden number moved.

## Alternatives considered

- **Change SN07 to remaining-duration semantics now.** Rejected: guesses at an absent oracle and
  moves an engine-pinned golden; fidelity over plausibility (Law 2).
- **Keep the D20 stored-float change and re-pin the goldens.** Rejected: the existing pins carry an
  Acumen-parity claim; re-pinning would replace a validated number with an unvalidated one.
