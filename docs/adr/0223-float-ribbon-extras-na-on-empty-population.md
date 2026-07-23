# ADR-0223 — Float ribbon extras report NA on an empty incomplete-activity population (audit NEW-1)

## Status

Accepted. First theme of the AUDIT-2026-07-14 remediation. A fidelity fix (Law 2) — no metric math
changes; it only corrects an applicability signal so a placeholder never reads as a real measurement.
Directly extends ADR-0219 (audit L1), which introduced `CatalogRow.applicable`.

Scope was widened during review: an adversarial verification pass found the identical placeholder-`0.0`
leak on the **`/ribbon` page** (ADR-0067 — the *primary* Fuse-style display of Avg/Max Float) and the
**ribbon Excel export**, not only the Metric Workbench the audit named. The operator elected to close all
three surfaces in this one PR, so the fix now flows from a single engine signal
(`RibbonMetrics.incomplete_float_count`) into every consumer.

## Context

ADR-0219 added `CatalogRow.applicable` so the Metric Workbench renders "—" for an unmeasurable cell
instead of a fabricated `0`. It set the flag for the DCMA rows (audit-absent placeholder → `False`; a
scored check reporting NA → `False`) but left **all** ribbon extras `applicable=True` on the stated
assumption that "their value is real."

The 2026-07-14 re-audit (NEW-1) falsified that assumption for the two **float** extras. In
`engine/metrics/ribbon.py` (`compute_ribbon`), `avg_float_days` / `max_float_days` are the mean / max
of the float over the **incomplete-activity** population:

```python
floats = [... for t in tasks if t.percent_complete < 100.0 and t.unique_id in cpm.timings]
avg_float = round(sum(floats) / len(floats), 1) if floats else 0.0
max_float = round(max(floats), 1) if floats else 0.0
```

When that population is empty — a fully-progressed schedule loaded at a closeout / final data date
where every non-summary activity is 100% complete — both degrade to a placeholder `0.0`, yet
`evaluate_catalog` emitted them `applicable=True`. The Workbench grid and Excel export then showed
"Avg Float 0.0 days / Max Float 0.0 days" as a **real** mean / max when the honest reading is N/A —
exactly the "placeholder 0 presented as real" class the flag was introduced to prevent.

The distinction matters and is not `value == 0`: a schedule whose incomplete activities all carry
exactly 0 float has a **real** mean/max of 0 (applicable), whereas a schedule with *no* incomplete
activities has *no* mean/max at all (not applicable). The two cases must be separated by the
**population**, not the value.

The other extras are unaffected: `insufficient_detail` / `merge_hotspot` are genuine counts where 0 is
a real measurement, and `logic_density` only zeroes on an empty network — all keep `applicable=True`.

## Decision

Add one **engine signal** and have every surface read it. `compute_ribbon` already builds the
incomplete-activity float list `floats`; expose its size on the frozen model:

```python
@dataclass(frozen=True)
class RibbonMetrics:
    ...
    incomplete_float_count: int  # == len(floats); 0 ⇒ avg/max_float_days are a placeholder 0.0
```

`incomplete_float_count == 0` is the single, unambiguous "this figure is unmeasurable" test — it is the
population count itself, not a `value == 0` heuristic (which ADR-0219 rightly rejected for the export),
so a schedule whose incomplete activities genuinely have 0 float (a real mean/max of 0) stays
applicable. No new metric math — it is the length of a list the function already computes (Law 2).

The three consumers:

- **Metric Workbench** (`engine/metric_catalog.py::evaluate_catalog`): `applicable = not (mid in
  {avg_float_days, max_float_days} and ribbon.incomplete_float_count == 0)`. The existing `workbench.js`
  `fmt` and the `not r.applicable` Excel branch already render "—" — no UI/JS change there.
- **`/ribbon` page** (`web/app.py::_ribbon_body`): when `incomplete_float_count == 0`, the two float
  columns render the muted, non-clickable "—" sentinel (`<td class="rib-na">` — `color: var(--muted)`,
  a theme token, so it recolors across all four views; no `data-metric`, so `ribbon_drill.js` correctly
  leaves it un-drillable — there is nothing behind it).
- **Ribbon Excel export** (`web/app.py::export_ribbon`): the two float cells are written as the "—"
  string (the neutral `TableSet` cell type accepts `str`) instead of a fabricated `0.0`.

## Consequences

- On a fully-progressed schedule, Avg/Max Float read "—" on **all three** surfaces (Workbench grid +
  Excel, the `/ribbon` matrix, and the ribbon export) — never a fabricated `0.0`. A schedule whose
  incomplete activities genuinely have 0 float still shows `0` (the population is non-empty).
- Additive, non-breaking: `RibbonMetrics` gains one field (constructed only in `compute_ribbon`);
  no metric value changes; `evaluate_catalog` stays a pure aggregator.
- Chromium-verified in all four themes (console / daylight / apollo / jarvis): the two NA cells render
  "—" in the theme's `--muted` color, `cursor:default`, non-clickable, with a real-number row shown
  alongside for contrast and no console errors.
- Tests: engine — `incomplete_float_count` tracks the population (3 vs 0) and the empty case degrades
  avg/max to 0.0; catalog — all-complete → both extras `applicable=False`, in-progress → `True`, a
  fully-critical population (real 0 float) → `True` (the population-not-value distinction), and the
  existing Project5 case still asserts `applicable=True`; web — `/ribbon` renders two `rib-na` "—"
  cells with no `data-metric` on an all-complete schedule, and the export writes two `<t>—</t>` cells.
