# ADR-0079 — DCMA-14 audit: count + percentage display and per-check hover tooltips

Date: 2026-06-18 · Status: accepted

## Context

The operator loaded the same project into Acumen Fuse and into the tool and asked, of the
`/analysis` **DCMA-14 audit** table:

> "I don't want to see in the tool just green or red for each metric. I want to see the actual
> count as well as it displayed as a percentage of the total tasks like it is in Acumen Fuse. I
> also want to be able to hover over each metric and have a description of the metric and the
> pass/fail criteria and why it's important and what it indicates."

The table showed only a status colour (PASS/FAIL/N-A) and a single bare "Value" cell. The raw
**count** and the metric's **percentage** — the numbers Acumen surfaces — were not shown, and there
was no in-place explanation of what each check means or why it matters.

This ADR covers the **display** half of the request (pure presentation, parity-safe). The
**calculation** half — reconciling the float-based metrics (Critical, Negative Float, Lags, Leads)
to Acumen on progressed real files — is a separate, parity-sensitive change tracked on its own.

## Decision

**1. Count + percentage columns.** The audit table's single "Value" column is replaced by two
columns, mirroring how Acumen Fuse presents each metric:

* **Count** — the raw numerator over its population, e.g. `37 of 126`. The denominator is shown
  explicitly (Acumen hides it), so the figure is self-documenting.
* **% of tasks** — the metric's percentage. The rendering is **metric-aware** by `MetricResult.unit`:
  count/percent checks show `value%`; the CPLI / BEI **index** checks (`unit == "ratio"`) show the
  index value (e.g. `0.59`) with no count; the pass/fail Critical-Path Test shows neither.

**2. Per-check hover/focus tooltip.** Each check name carries a tooltip (`_dcma_metric_cell`) built
from the in-tool **metric dictionary** (`web/help.py`), with the four facets the operator asked for:
the **definition**, the **pass/fail criteria** (the metric's formula/threshold), **why it matters**
(new `MetricDoc.importance`), and **what a failing value indicates** (new `MetricDoc.indicates`). The
trigger is a focusable, labelled control (`tabindex=0`, `role=button`, `aria-describedby`) so the
tooltip is keyboard-operable and gets the ADR-0073 focus ring; it also carries a plain-text `title=`
so the same detail is available with no CSS/JS (air-gap + a11y), and is hidden in print (ADR-0076).

## Scope / safety

Pure presentation: two new defaulted fields on `MetricDoc` (filled for the 14 DCMA checks) plus
HTML/CSS in `web/app.py` / `app.css`. **No engine / CPM / metric change → parity 10/10.**
`render_dictionary_markdown()` reads only the existing fields, so `docs/METRIC-DICTIONARY.md` does
not drift. Dependency-free, same-origin. Tests (`tests/web/test_visuals.py`): the `/analysis` page
exposes the **Count** / **% of tasks** columns, the `class=num` cells, and a labelled `role=tooltip`
carrying *Pass criteria / Why it matters / Indicates*; every DCMA doc now has `importance` +
`indicates`. Full gate green (939 passed); ruff/format/mypy/bandit clean.

## Follow-up

The **calculation** reconciliation (Critical, Negative Float, Lags, Leads diverge from Acumen on the
operator's progressed real file because the engine recomputes pure-logic CPM float per ADR-0010 while
Acumen reads MS Project's stored, progress-aware `Critical` flag / `TotalSlack`) is the next change.
Diagnosis on the committed goldens confirms it is parity-safe: stored `Critical=1` count = 41/37 and
stored `TotalSlack<0` count = 0/0 — exactly the pinned golden values — so consuming stored values for
those metrics when the source file provides them matches Acumen on real files without moving the gate.
