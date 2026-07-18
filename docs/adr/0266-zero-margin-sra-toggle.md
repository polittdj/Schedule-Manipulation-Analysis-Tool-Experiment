# ADR-0266 — zero-margin SRA toggle (Fig 7-43 fidelity)

## Status

Accepted. Closes the follow-up ADR-0254 documented on the §7.3.3.2.3 sufficiency panel: "the
simulation carries margin in-network at plan (the handbook's Fig 7-43 curves are zero-margin,
e.g. 'Current Plan, Zero Margin, With Risks'); a handbook-faithful zero-margin run via the
existing three-point surface is a documented follow-up."

## Decision

`/api/margin/risk` gains `zero_margin=1` (a checkbox beside the panel's Run button): the same
seeded SSI SRA runs with **every margin activity's three-point set to (0, 0, 0)** — via the
existing three-point override surface, exactly as ADR-0254 prescribed — so the finish
distribution is the handbook-faithful Fig 7-43 curve ("Current Plan, Zero Margin, With
Risks"). Everything else is unchanged: the deterministic margin window **[E, D]** (computed
independently by `deterministic_margin_bounds`), the Watch/Corrective thresholds, the margin
set's precedence (this version's confirmed overlay, else the union, else name-based), the
seed discipline. `margin_risk_read`'s semantics carry over exactly — with the zero-margin
curve, `margin_needed(P) = finish_zero(P) − E` is the risk-consumed margin and
`covered(P) ⇔ finish_zero(P) ≤ D` reads "risks fit inside the plan's margin", which is
precisely the handbook plot. The payload carries `zero_margin` + a `curve_basis` label; the
provenance line and the margin Excel/Word export name the basis on every result (the export
itself runs the default in-network read — its new "Curve basis" row says so; exporting a
zero-margin snapshot is future work if asked).

## Proof (seed-independent, no stochastic assertions)

The regression fixture gives the MARGIN task the run's ONLY duration uncertainty: the
zero-margin run must then collapse to a DEGENERATE distribution (every iteration identical)
whose every percentile finish equals **E** exactly, while `margin_wd` (D − E) stays the
margin task's full duration — deterministic evidence the margin was removed from the
sampling itself, not merely relabeled. The default run is pinned non-degenerate and
`zero_margin=0` byte-identical to the absent parameter.

## Consequences

- `tests/web/test_zero_margin_sra.py` (4): default basis + byte-identity, the degenerate
  collapse onto E, panel/JS wiring, the export's basis row. Adjacent margin/SRA suites green.
- Browser-verified (Chromium): both runs live, the provenance line names each basis, zero
  console errors. (Playwright's `wait_for_function` was itself refused by the app's CSP —
  no `unsafe-eval` — which is the air-gap policy working; the probe polls from Python.)
- No default changed; no engine math touched; parity untouched. Version 1.0.71 → 1.0.72
  (shared with ADR-0267); wheel + 9 installers in lockstep.
