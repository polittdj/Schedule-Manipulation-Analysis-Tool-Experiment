# ADR-0446 — The One-Pager: a three-column Excel list as a swimlane slide, previewed in the browser and exported as native PowerPoint shapes

- **Status:** Accepted — 2026-09-01 (operator request, same session as ADR-0445)
- **Version:** 1.0.228
- **Shipped:** `reports/onepager.py` (intake + layout), `reports/pptx.py` (the .pptx writer), `web/onepager.py` (the page), `static/onepager.js` (the painter + drop-zone intake), `--lane-1..10` theme tokens ×4, `.op-*` CSS, routes in `app.py`, four `SessionState` fields, a LIBRARY-rail nav entry, i18n terms ×7 × 4 languages.

## Context — the request, and what the example workbook actually contained

The operator keeps a plain workbook — **column A** the swimlane name, **column B** the task or milestone name, **column C** the date — and wants the PowerPoint one-pager that list implies: swimlanes in distinct colours, every bar or milestone labelled with its name and finish date, a red line at today, dotted vertical month lines under a month/year header, a legend at the bottom, drag-and-drop or picker intake, and the slide exportable as PowerPoint. "There could be more or less tasks per swimlane in other files so the tool must account for this."

The uploaded example (`Politte_PowerPoint_FINAL.xlsx`, 88 sheet rows, NOT committed — it is the operator's file) was read cell by cell before a line was written, and it decided the intake's grammar:

| What column C carried | Rows | Read as |
|---|---|---|
| a real Excel date cell (serial, date-formatted) | 41 | a **milestone** |
| an Excel serial typed into a **General**-formatted cell (`46310`, `46412`) | 2 | a milestone — recognised by range (1954..2119), not by cell format, because `read_xlsx` returns every cell as text |
| `04/20/2027 - 06/20/2027` · `12/1/2026 - 4/15/27` · `06/10/26 - 06/22/28` · `9/18/25 - 3/20/27` · `11/4/2026 - 12/12/26` | 19 | an **activity** — two-digit years are 20xx; mixed forms within one range are fine |
| `05/2026 - 11/2026` · `12/2026 - 3/2027` (month only) | 3 | an activity from the 1st to the last day of the months |
| `10/122/2026` (a typo) | 1 | **skipped and named**: `row 83 (GRC-MET Testing · Blue Origin On-Dock): unreadable date "10/122/2026" — skipped` |

Two more quirks: the swimlane `GRC- (MCaRR-2)` is also spelled `GRC-(MCaRR-2)` (rows 72/73) — one lane, two spellings — and the sheet has blank spacer rows between swimlanes. Nothing about this file is unusual for a hand-kept list; the tool has to read *this*, not an idealised one.

## Decisions

### 1. Intake: reuse `read_xlsx`; a date grammar, not a guess; every decision by row number
`reports/xlsx_read.py` already reads every cell encoding Excel produces and is hardened (XXE, zip bomb), so the One-Pager takes its rows as text. `parse_span` accepts a single day (milestone), a range split on a spaced dash / `to` / an en- or em-dash, ISO dates, `M/D/YY`, `M/YYYY`, spelled-out forms, and serials-as-text. Anything else is a **problem row** (`row N (lane · name): unreadable date "…" — skipped`), never a default date (Law 2 at the intake: a milestone drawn on a made-up day is worse than one flagged as missing). A blank swimlane cell inherits the one above **and says so**; swapped dates are kept **and said so**; spelling variants of a swimlane merge on a whitespace/case-insensitive key **and say so**. The page shows all three lists (skipped rows as an `alert`, assumptions as a `status`), and the ▦ DATA drawer and ⤓ EXCEL carry the normalised list with them.

### 2. ONE layout, TWO painters
`build_layout` places everything in **logical points on a 960 × 540 slide** (13.333 × 7.5 in at 72 pt/in — one unit is one point is 12,700 EMU) and returns a plain dataclass. The browser paints it as one SVG through a `viewBox` (`onepager.js`); the .pptx paints the same numbers as native shapes (`reports/pptx.py`). **No painter computes geometry.** Consequences that were the point: the page is an honest preview of the slide (what you see is what exports), the layout is unit-testable without a browser (43 tests), and a drawing defect is a layout defect with one fix. Text widths are estimated from character count × 0.52 em (Calibri's average advance, a deliberate over-estimate) because neither painter may depend on the other's font metrics.

### 3. Packing and the fit rules — and what happens when the list will not fit
Items in a swimlane are packed **first-fit** into rows by their full horizontal extent (bar or diamond **plus label**); a label goes right of the item, *inside* a bar that is wide and tall enough to hold it, or left of it when the right edge has no room. The label size feeds the packing, the packing feeds the row height, the row height feeds the label size — iterated to a fixed point. Floors of (row 7 pt, label 5 pt) → (6, 4.6) → (5.5, 4.2) are stepped down **only when the slide would overflow**, then an emergency (3.6, 3.4). The layout **says which it had to do** in its notes — "Dense one-pager… labels reduced to 4.6 pt", "Extremely dense… consider splitting the list", or "does not fit one slide even at the smallest size — the lowest swimlanes run off the page. Split the list." The operator's file is the first case: 66 items, 10 swimlanes, 52 rows, 4.6 pt. A one-pager that silently clipped a swimlane would be the intake defect again at the other end.

### 4. Today is the data-date line
The red line at today is the tool-wide `SFGantt.dataDateLine` (ADR-0342 — one mechanism, `.ch-dd`, `--bad`), so the DD-line ledger buckets `onepager.js` as a TIME axis and the axis captions go through `SFChartFrame.axisTitles`. The slide adds its own dated caption (`TODAY 9/1/26`) in the gap below the lanes — moved there after the first render showed it colliding with the `DD` marker and the subtitle. Today joins the plotted window when it lies within six months of the data; otherwise it is not drawn and the notes say so (a marker clamped to an edge would assert a date the data never carried).

### 5. The header: whole months, dotted month lines, year bands
The window is padded to whole months. Every month boundary gets a dotted line through all lanes; month labels are three-letter abbreviations when a month is ≥ 20 pt wide, single letters when ≥ 6.5 pt, otherwise none (the lines stay). Years are alternating bands with a solid boundary line and a centred bold year. The operator asked for "only months and years" — there is no day tier and no quarter tier.

### 6. The .pptx writer
A minimal package (content types, root rels, presentation, one blank master + layout, a theme, one slide) written with `zipfile`, byte-deterministic (fixed timestamps, fixed part order) — the posture of the Word and Excel writers beside it. Shapes are DrawingML presets: `roundRect` activities, `diamond` milestones, `sysDot`-dashed connectors for months, a 1.5 pt `C00000` connector for today, text boxes for every label, all **named for PowerPoint's selection pane** (`Activity: …`, `Milestone: …`, `Lane: …`). The slide carries the CUI marking top and bottom using **the page's own marking** (`_cui_marking`): a session asserted UNCLASSIFIED exports that wording. Observed, not changed: the Word and Excel writers always stamp the CUI banner regardless of mode — a pre-existing inconsistency, logged here rather than fixed blind. The print palette is ten fixed hues; the browser paints the same lane index through per-theme `--lane-N` tokens (brighter on the three dark themes).

### 7. The page
Library rail (it is a tool for the analyst, not a chapter of the schedule story), `_page` title `One-Pager Timeline`, kicker + takeaway h1 that states the finding ("10 swimlanes, 41 milestones and 25 activities on one slide — 2025 to 2032.") + context line; a `.panel` with `_panel_head`, ▦ DATA (the `.sf-drawer` table), ⤓ EXCEL (`/export/{fmt}/onepager`), ⛶ ENLARGE, a provenance chip (`SOURCE: file · TODAY date`), a read-me line; the slide-title field, the ⤓ POWERPOINT button (`/export/pptx/onepager`, refused with 422 when nothing is loaded — never a blank slide), "Clear the list"; the drop zone (window-wide drag-and-drop and a picker, the `home.js` idiom, one form, no fetch) with the three-column explainer and a **template download** in the intake's shape. Strict CSP: the layout rides a non-executable JSON block with `<` escaped (the `launch.py` idiom); `panelkit.js` is a per-page include like every converted page.

### 8. The sweeps the page joined
Route-table census row (empty state on the census load: floors all zero); render-oracle labels regenerated and the empty-stage fingerprint re-pinned `{200: 42→43, 422: 2→3}` with its caption; DD-line ledger `("onepager.js", 83)` in TIME_AXIS; axis-titles census satisfied by the helper call; `VIEW_MODULES` and both whole-view-layer guards read `onepager.py`; `onepager.py` takes the HTML-carrying view module's E501 exemption; i18n terms in all five catalogs; operator-content escaping (page and slide XML) covered by the page's own test and the sweep.

## Verification (QC-1)

- **Intake:** every hand-typed form in the field workbook parametrised; the typo, the General-cell serials, the inherited swimlane, the spelling merge, the swapped dates, the empty workbook — each a named test. The workbook is not committed: `tests/web/onepager_twin.py` builds a synthetic twin with a **shared-strings** table and bare numbers (Excel's own encoding) so `read_xlsx` takes the path it takes on a real file. The twin's serials are computed, not typed — a typed 47209 that was meant to be 2028-03-28 (it is 2029-04-01) cost one round.
- **Layout:** the slide is never overflowed and nothing overlaps in a row, both **re-derived from the geometry**, not read from flags; the three density regimes; today near/far/right-edge; whole months; labels = name + finish date; legend order and bounds; JSON round-trip.
- **.pptx:** every part present and well-formed; every layout element a named shape; **every shape's EMU geometry equals the layout × 12,700** (read back with `xml.etree` — a different code path from the writer); presets, dashes, colours, texts, the marking; byte-determinism; hostile names stay well-formed. **Teeth:** a writer one EMU-per-point off fails the geometry read-back by name.
- **Two independent renderers, in the build session only:** python-pptx opened the export and typed every shape (`ROUNDED_RECTANGLE`, `DIAMOND`, `LINE` ×82 `ROUND_DOT`); LibreOffice Impress (installed for the purpose after a bisect showed the first "could not be loaded" was the environment, not the XML) rendered it to PNG — viewed, and it is the browser preview shape for shape. **PowerPoint itself was not run — UNVERIFIED there**; what settles it is opening `slide.pptx` in PowerPoint, which the operator will do on first use.
- **Page:** 13 `TestClient` tests (empty state + template, upload + every decision on the page, escaping in HTML and slide XML, the pptx/xlsx/docx exports and their refusals, title/clear, bad file and no-usable-rows, the rail + catalogs, the upload cap); 4 Playwright tests (picker upload paints 10 bars / 6 diamonds / 16 labels / DD / captions / 35 month lines / legend; drag-and-drop anywhere on the page; **all four themes** resolve ten distinct lane colours; the POWERPOINT button downloads a real package). Rendered in the tool's chrome with the operator's file in daylight and console and viewed.

## Consequences and known limits
- Label widths are estimates; a name set in a different font on the slide may run a little longer or shorter than the packing assumed. The over-estimate errs toward white space, never toward overlap.
- Beyond ~100 rows of simultaneous items nothing fits one slide; the layout says so and asks for a split rather than inventing a second page.
- The `.chart-host` on the panel brings the tool-wide chart-frame zoom bar; it scales the preview, not the export.
- Body prose is translated by the AI fallback only; the nav label, panel title and controls are in the catalogs.
- The two-spelling merge is a judgment: "Test A" and "TestA" would merge. It is always announced.
