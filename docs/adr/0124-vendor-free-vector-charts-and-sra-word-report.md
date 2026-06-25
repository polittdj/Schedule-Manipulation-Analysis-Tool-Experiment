# ADR-0124 — Vendor-free vector charts in the .docx writer + a comprehensive SRA Word report

- Status: accepted
- Date: 2026-06-25
- Relates: ADR-0123 (SSI SRA remodel), ADR-0005/0106 (RNG not bit-exact), the M18 .docx writer

## Context

The operator asked for a **comprehensive MS Word SRA report** — a PM-level executive summary, then
per-section detail (focus-finish results, the S-curve, the finish-date distribution, the duration
sensitivity, the risk register, and the 5×5 Risk/Opportunity matrices) — **with graphics**, plus a
**downloadable risk registry**.

The hard constraint is **Law 1 (offline / std-lib-only at runtime)**: no `matplotlib`/`PIL`/`cairosvg`,
so **no rasterizer is available**. The existing `reports/docx.py` writer renders only text blocks
(`Heading`/`Paragraph`/`DocTable`) and has **no image support**; embedding a raster chart image would
require a rasterizer we cannot ship, and embedding an SVG image part needs a PNG fallback Word stores
alongside it (again a rasterizer). The output must also remain **byte-deterministic** and open cleanly
in Microsoft Word.

A recon pass (3 parallel readers mapping the writer + the SSI data surfaces, a design step, and a
**proof-of-concept that built and validated a real .docx in isolation**) settled the approach below
before any production code was written.

## Decision

### 1. Charts are native DrawingML vector shapes — no image, no new part

Add a frozen `Chart` block to `reports/docx.py`. `kind="vector"` emits one inline drawing per chart:

```
w:p > w:r > w:drawing > wp:inline > a:graphic
  > a:graphicData(uri=".../wordprocessingGroup") > wpg:wgp (a shape GROUP)
      child wps:wsp shapes: a:custGeom (poly paths) for the S-curve / axis / tornado outline,
                            a:prstGeom prst="rect" (filled) for histogram & tornado bars,
                            a:prstGeom prst="ellipse" for the percentile dots
```

The group's `grpSpPr/a:xfrm` pins `chExt == ext` so **1 internal unit = 1 EMU** (914400 EMU/inch), no
scaling. Charts carry their primitives in a **0..1 plot-fraction space** (x right, y up; the renderer
inverts y to DrawingML's +y-down); `_chart_xml` maps fractions → EMU. Because the drawing lives
**entirely inside `word/document.xml`**, it needs **no media part, no relationship, and no
content-type override** — the fixed 6-part zip, `_ZIP_EPOCH` timestamps, and part order are untouched,
so **byte-determinism is preserved for free**. Each chart gets a unique `wp:docPr id` (the block index)
so Word never sees a duplicate-id "repair" prompt.

`kind="matrix"` emits the 5×5 grid as a **shaded `w:tbl`** (`w:shd` fill per cell + centred rank/count
text). A shaded table is the single most reliably-rendered vector primitive across Word/LibreOffice, so
the matrix — which must show numbers in coloured cells — uses it rather than text-box shapes.

`wp`/`a` (ECMA OOXML) and `wpg`/`wps` (the Microsoft-2010 shape-group vocabulary Word renders natively)
namespaces are declared once on the `<w:document>` root. The PoC validated a generated file: valid zip,
well-formed parts, the drawing present; determinism confirmed by equal bytes on re-render.

### 2. The comprehensive SRA report

`web/app.py` `_sra_report_blocks(st, sch, result, oat)` composes the block list: title → **Executive
summary** (PM prose + a key-results table + a "how to read this" note) → **Focus-finish results**
(table + the S-curve chart + the distribution histogram) → **Duration sensitivity** (a centred tornado
chart + the OAT table) → **Per-task Best/Worst durations** → **Risk/Opportunity register** → the two
**5×5 assessment matrices** (shaded grids with the NASA 1–25 ranks + landed counts) → **Methodology &
assumptions** (the BC/WC formula, occurrence mode, correlation, the days→months consequence guideline,
and the ADR-0005/0106 stochastic caveat). It reuses `_ssi_export_tables` for the data grids. The
chart-primitive builders (`_sra_chart_scurve/_hist/_tornado`, `_sra_matrix_chart`) degrade gracefully
(a degenerate single-value distribution simply omits the S-curve).

`GET /export/docx/sra` now returns this narrative report; `GET /export/xlsx/sra` keeps the plain table
export. `GET /export/{fmt}/sra-registry` is the **downloadable risk registry** (the risk register +
per-task durations as a focused workbook/doc), skipping the OAT solves it does not need.

## Consequences

- A full, graphical, PM-ready SRA report and a standalone risk registry, **with zero new runtime
  dependencies** and the offline/std-lib/air-gap/CUI laws intact (the CUI header/footer apply to the
  report like every other export). Byte-deterministic.
- The `Chart` block is generic and reusable by any future Word report (not SRA-specific).
- **Caveat (honest):** the PoC proved package validity and XML well-formedness, **not** pixel rendering
  in a live Office app (none available in the build sandbox). The wps/wpg vocabulary is the Microsoft
  extension Word renders natively; strict third-party OOXML validators / older LibreOffice may render
  shapes differently. The shaded-table matrix path is the conservative fallback and is used for the
  grid; if the vector shapes ever misbehave the histogram/tornado/S-curve can likewise degrade to
  shaded-table/data-table forms without new vocabulary.
- No model/schema change. Tests: `Chart` rendering (valid zip, drawing + shaded matrix present, unique
  docPr ids, determinism) and the report/registry routes (sections + a drawing + determinism).
