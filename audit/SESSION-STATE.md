# SESSION-STATE — CP-volatility exhibits layer (2026-07-10, ADR-0184)

## Where this stands
- **Payload contract built and frozen**: `src/schedule_forensics/exhibits/payload.py`
  (pydantic v2, extra="forbid", loud failures; canonical `sort_keys` serialization;
  deterministic `run_id_for` — no timestamps anywhere in the render path).
- **Static pack renders EX-00..EX-08** from the golden fixture
  (`tests/exhibits/fixtures/payload_small.json`): stdlib-SVG with literal-hex PALETTE
  (standalone files carry no CSS vars — grep-gated), provenance footer inside every figure,
  EX-01 six-state barcode with `<pattern>` hatching (grayscale-survivable), EX-03 breaks at
  the rebaseline boundary, EX-04 renders CIC nulls as annotated gaps, per-exhibit CSV
  siblings, self-contained zero-`<script>` report.html.
- **CLI shipped**: `schedule-forensics-report` (console script). Exit codes 0/2/3/4/5
  demonstrated by test. `--inputs` runs exit 4 (engine artifacts missing — see PARK-LIST);
  `--payload` renders a pack deterministically (double-run byte-identical, tested).
- **Interactive page**: heatmap re-sorted by instability (on/off flips; the tenure sort
  inverted the exhibit's purpose), gauge bands now carry "operator-set display guidance —
  not a published threshold" ON the chart face, column headers already name each file.
- **Tests**: `tests/exhibits/test_exhibits.py` (14) — fixture completeness, loud-failure
  validation, structural render assertions, air-gap grep, CLI matrix, determinism, parity.

## What is NOT done (parked, see PARK-LIST.md)
- CP-basis engine artifacts (CIC, τ-b, edge-Jaccard over the driving tree, null-model churn,
  recompute deltas, six-state assignment from live schedules) do not exist in the engine, so
  the live payload builder is parked; renderers are fixture-fed until it lands.
- volData migration to the six-state model (§5.1) and the new interactive exhibits (§5.4)
  depend on the same engine artifacts.
- Full SSI rename (§2.4) parked; gate test added instead.
