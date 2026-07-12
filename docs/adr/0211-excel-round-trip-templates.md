# ADR-0211 — Excel fill-in templates for the risk register + per-task Best/Worst-Case & Risk Ranking Factors

## Status

Accepted. Operator directive 2026-07-12: "come up with an MS Excel template for the risk registry
that the user can export and then fill out and then reimport. I also want to be able to do the same
for the Best and Worst Case Durations and Risk Ranking Factors for tasks."

## Context

Both SRA inputs are entered today through the `/sra` forms (the unified risk register, and per-task
Risk Ranking Factors + Best/Worst-Case durations via the grid). For a large schedule or a long risk
list that is slow and error-prone — operators live in Excel. The tool already **exports** these as
read-only workbooks (`/export/xlsx/sra-registry`, ADR-0124), but there was no **import** side: no way
to hand the operator a pre-formatted sheet, let them fill it in offline, and load it back.

Two constraints shape the design. **Law 1 (data sovereignty):** the runtime is std-lib only — no
`openpyxl`/`pandas`. Our existing writer (`reports/xlsx.py`) is a hand-rolled std-lib workbook; there
was no reader. **Law 2 (fidelity, never fabricate):** an import must not invent data — an unmatched
UID, an inverted Best/Worst pair, or an incomplete row must be dropped/skipped and *reported*, never
silently coerced into a number.

## Decisions

- **`reports/xlsx_read.py`** — a minimal std-lib `.xlsx` reader (`zipfile` + `xml.etree`), the import
  counterpart to `reports/xlsx.py`. `read_xlsx(bytes) -> {sheet_name: [[cell, …], …]}` with every
  cell a **string** (numbers kept verbatim, gaps filled by column index so a sparse row still lines up
  under its header). It handles every common cell encoding Excel emits when it rewrites a file:
  **shared strings** (`t="s"` → the `<v>` index into `sharedStrings.xml`, which our inline-string
  writer never uses but Excel always does), inline strings (`t="inlineStr"`), formula-result strings
  (`t="str"`), and bare numbers. A bad zip / missing `xl/workbook.xml` raises `XlsxError`. The reader
  never guesses types — the caller maps header names to columns and coerces.
- **Two fill-in templates** (built in `web/app.py`, exported as `TableSet` through the existing
  `render_xlsx`):
  - **Risk Register** (`GET /export/xlsx/risk-register-template`) — the current register (or one
    seeded `EXAMPLE (delete this row)` row when empty) on a *Risk Register* sheet, plus a **read-only
    task-reference sheet** (valid UID → name → remaining-days) so the operator maps real UIDs.
    Columns: Risk ID, Risk name, Probability %, Impact (working days), Consequence (1-5), Affected
    UIDs (`;`-separated).
  - **Task Risk** (`GET /export/xlsx/task-risk-template`) — one row per non-summary activity,
    pre-filled with any current factor / Best-Case / Worst-Case. Columns: UID, Task name, Remaining
    (days), Risk Ranking Factor (0-5), Best-Case (days), Worst-Case (days).
- **Re-import** (`POST /sra/import/risk-register`, `POST /sra/import/task-risk`) — `read_xlsx` →
  header-matched by case-insensitive substring (so light reordering/renaming still binds; a missing
  header row is reported, not guessed) → rebuild `st.sra_risks` / update `st.sra_factors` +
  `st.sra_bcwc`. Re-importing the **register replaces** it; re-importing **task risk updates** only
  the rows filled in. Best/Worst days convert to working minutes via the schedule calendar. Fidelity
  rules, all counted in a one-shot summary banner: the seeded EXAMPLE row is skipped (its marker is in
  the ID column); unmatched/summary UIDs are dropped; a Best-Case that exceeds its Worst-Case is
  skipped (no inverted range); a row with no name or no valid activity is skipped; a factor is clamped
  to 0–5.
- **UI** — a new "Excel fill-in templates (export → edit → re-import)" block in the SSI panel, next to
  the existing register exports. Each template has a download link and an upload form; the import
  result is shown once via `SessionState.sra_import_msg` (a `notice ok` banner rendered and cleared at
  the top of `_sra_body`).

## Consequences

- The operator can build the whole risk register, or rank/duration hundreds of tasks, in Excel and
  load it back in one step — round-tripping the *same* figures the on-page forms use, with a report of
  exactly what landed and what was dropped. No third-party parser enters the runtime (Law 1); nothing
  is fabricated on import (Law 2).
- `read_xlsx` is a general, reusable std-lib reader — future import features (setups, mappings) can use
  it. 13 new tests: reader round-trip + shared-strings + bad-file (`tests/reports/test_exports.py`),
  and the full template export/import/summary/error matrix (`tests/web/test_sra_excel_templates.py`).
- Version 1.0.16 → 1.0.17; wheel + nine installers rebuilt in lockstep. Follow-ons: a combined
  "download both templates" bundle, and an optional column-mapping preview on import.
