# ADR-0272 — Risk-critical Gantt tint: surface the SSI run's Criticality Index on the schedule grid

Status: accepted (2026-07-19)

## Context

Operator direction (standing #331 "Advanced Schedule Analysis" phase, Fable 5 Ultracode): continue
at the ranked-next Hulett-deck item — **#12 risk-critical Gantt tint** — colour the SSI schedule
grid's Gantt bars by each activity's **Criticality Index (CI)**: the fraction of the last
Monte-Carlo run's iterations in which the activity was on the critical path (total float ≤ 0). This
is the "risk-critical" view — it exposes activities that are *deterministically* off the critical
path yet frequently become critical under duration uncertainty, the ones a plain critical-path
highlight hides.

**Premise correction (verify-everything, caught before any code).** The task was scoped as a
pure-UI change on the belief that `SSIResult` already carried per-activity CI. A read-only recon
plus a first-hand code read proved it did **not**: `compute_sra_ssi` *tallies* `critical_counts`
per iteration (`sra.py`, the run loop) but **discarded** it — `_build_ssi_result` never received it
and `SSIResult` had no CI field. CI lived only on the **legacy** `compute_sra`/`SRAResult.activities`
path (exposed at `/api/sra`, truncated to the top-20 by sensitivity), a *different* simulation. So
tinting "from the last MC run" (the SSI run the operator actually drives on `/sra`) required a
minimal **engine** change — but an *additive, plumb-an-existing-value* one, not new forensic math.

## Decision

### Engine — stop discarding the Criticality Index (additive, `sra.py`)

`SSIResult` gains a default-valued field `criticality: tuple[tuple[int, float], ...] = ()` —
`(unique_id, fraction of iterations critical)`, ascending uid — appended last, **inert to the
finish-cdf pin and the ssi==jcl equality** (that test compares `finish_cdf`, not the whole result).
`_build_ssi_result` takes a new `critical_counts: Mapping[int, int] | None = None` and builds the
tuple as `count / n`; `compute_sra_ssi` passes the `critical_counts` it already computes. **No new
math** — the value was computed every run and thrown away; this carries it through. Pinned by three
engine tests: the 10-day driver ranks CI > 0.95 while the short off-path task is < 0.05; determinism
for a seed; and an all-point-mass run gives a clean 0/1 split on the deterministic critical path.

### Web — cache the last run, tint the grid, label the provenance

The SSI grid (`/api/sra/grid` → `_ssi_grid_rows` → `sra_grid.js`) and the run (`/api/sra/ssi`) are
**decoupled fetches**, so:

- `SessionState.sra_criticality: dict[int, float]` + `sra_criticality_iters: int` cache the last
  run's CI map (set in the `/api/sra/ssi` handler). `_ssi_grid_rows` adds `criticality_index` per
  row from that cache (None before any run); `/api/sra/grid` reports `criticality_available` +
  `criticality_iters` for the legend's honest provenance. `_ssi_data` also echoes `criticality`
  for API consumers.
- `sra_grid.js` `timelineCell`: when the **"tint by criticality"** toggle is on and a row has a CI,
  the bar's class becomes `g-bar g-ci-{0..4}` (banded 0 / <20% / 20–50% / 50–80% / ≥80%), overriding
  the planned/critical colour; the hover title gains the CI %. A legend under the grid controls
  shows the band swatches + "last N-iteration run" (or a prompt to run first). Because the tint is a
  **row property**, it survives every grid re-render (sort, filter, group, zoom, timescale).
- `sra_ssi.js` fires a `sf-ssi-run` window event after a successful run; `sra_grid.js` listens and
  reloads so a fresh CI tints immediately without coupling the two IIFEs by a shared global.

### Colour — the sanctioned risk-heat palette

The `.g-bar.g-ci-*` bands reuse the **theme-independent risk-heat palette** (the same fixed hexes as
`base.css .rk-*`; the DESIGN-SYSTEM's sanctioned exception to the token rule, since risk-heat
semantics are fixed in light and dark): cool green = never critical (low schedule risk) → hot red =
near-always critical. NASA-red stays reserved for the deterministic critical path + data-date line;
the CI tint is a distinct, opt-in overlay. Verified in a real browser (CSP-strict, which even blocks
Playwright's `eval`) across all four views (console / daylight / apollo / jarvis): the bands map
correctly end-to-end (on Project5's rigid critical path, 4 bars red at CI = 1.0, 122 green at CI = 0).

## Consequences

- The analyst sees, at a glance on the schedule they already read, which activities carry
  probabilistic criticality the deterministic critical path misses — the point of the risk-critical
  view. It reads the *last* run and says so (provenance-labelled); re-run to refresh.
- One additive, parity-inert engine field surfaces an already-computed forensic value (Law 2 clean —
  no new number, no re-derivation in the web layer). The scalar/matrix/LHS sampler paths and every
  frozen pin are untouched; `engine/` logic is unchanged beyond carrying the value through.
- The tint is off by default; when off, the grid is byte-identical to before. A future refinement
  could tint the other Gantts (Activities/Path) or add a CI column, and could tokenise the risk-heat
  hexes into `:root` custom properties shared with `.rk-*`.

## Verification pointers

Hulett, *Practical Schedule Risk Analysis* (Criticality Index / criticality as the risk-critical
lens; CI = P(activity on the critical path)); NASA SP-2010-3403 SRA guidance (criticality reporting);
the existing legacy-path CI (`SRAResult.activities`, `test_sra.py::test_criticality_index_picks_the_longer_path`)
as the cross-check that the SSI-path CI agrees. Tests: `tests/engine/test_sra_ssi.py` (CI ranking,
determinism, point-mass 0/1 split) and `tests/web/test_sra_grid.py` / `test_sra_ssi_web.py` (grid
row CI, run→grid provenance, toggle/legend/CSS-band/JS-wiring pins). Browser: four-theme
band-count check (`scratchpad/verify_tint.py`), 122 green / 4 red on Project5's rigid critical path.
