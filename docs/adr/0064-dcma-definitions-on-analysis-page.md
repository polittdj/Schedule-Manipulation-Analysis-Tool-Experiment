# ADR-0064 — Define each DCMA 1–14 check inline on the Interactive Analysis page

Date: 2026-06-17 · Status: accepted

## Context

Operator: *"On the dashboard, clicking a project opens the Interactive Analysis with the DCMA
1–14 scores. Define what each DCMA metric is and define how it is measured."*

The tool already ships a complete in-tool metric dictionary (`web/help.py` `METRIC_DICTIONARY`)
with a plain-language definition, the formula/threshold, and the citing source for every metric
— surfaced on the standalone `/help` page. But the DCMA-14 table on `/analysis/{name}` showed
only Check / Status / Value / Suggested improvement, so the analyst had to leave the page to
learn what a check meant.

## Decision

Surface the definition **in place**. The DCMA-14 audit table gains a **"What it measures (how)"**
column: for each check (`c.metric_id`, including the `DCMA04_FS` / `DCMA04_SSFF` / `DCMA04_SF`
split rows) `_dcma_definition_cell` looks up `METRIC_DICTIONARY` and renders the plain-language
**definition** plus the **formula/threshold** (labelled `How:`). The panel's intro line notes
that each row is defined inline and links to the full Metric Dictionary (`/help`) for the
formulas + citations. A `.dcma-def` CSS rule keeps the column compact and readable.

## Scope / safety

Presentation only — it reads the existing dictionary (no engine/metric/CPM change) → **parity
10/10**. The dictionary already has a coverage test guaranteeing every engine metric id has an
entry, so no DCMA row can render a blank definition. New web test pins the column header, the
DCMA-01 definition + its `How:` formula appearing on `/analysis`, and the link to `/help`. Full
suite **886 passed**; engine cov 97%.
