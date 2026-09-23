# ADR-0526 — One-Pager Compare, round two: a repeated name whose date did not move is ONE unchanged item, column D is a status word drawn as a check, and every row cites the row Excel shows

- **Status:** Accepted — 2026-09-22 (operator request the same day)
- **Version:** 1.0.289
- **Extends:** ADR-0465 (the compare page), ADR-0446 (the One-Pager intake and slide), ADR-0247/0250 (the xlsx zip-bomb budget)
- **Supersedes in part:** ADR-0465 §1 ("a name that appears twice under one swimlane in EITHER sheet is a collision … compared with nothing") and §2 (a ghost under every row with a prior)

## Context — the request, verbatim, and the rulings asked for

> "In the One-Page Compare … use column D in the worksheets to determine if the task has completed or not and then indicate that somehow on the chart. If the task name and date have not changed on either worksheet they are not "DUPLICATE NAME". This just means that the task did not slip so only show it once with the single date. Make sure the tasks always stay in the correct swimlanes. The goal is to show the slips as well as show what has not slipped."

Three questions were put to the operator rather than assumed (user rule: no gap filled with an assumption):

| Question | Ruling |
| --- | --- |
| What went wrong with the swimlanes? | "Just a requirement" — no bug was seen; de-duplication and the completion mark must never move a task out of its lane. |
| Which copies of a repeated name are the same task? | "If the task name and the date matches for a task that is in the same swimlane in both excel sheets just put the task once in the swimlane with the single date." |
| What does column D hold? | Status words. |

**Reproduced before any change (pristine tree, rendered):** the same swimlane, name and date in both sheets twice ("Design Review" 1/15 and 5/15) painted **four** shapes, every one tagged DUPLICATE NAME — ADR-0465 marked a key AMBIGUOUS whenever it repeated in either sheet, and drew each side separately.

## QC-3 — the plan was attacked before the first edit (five independent skeptics, executable probes)

| Assumption | Verdict | What changed |
| --- | --- | --- |
| Pair identical dates, then pair a 1:1 LEFTOVER by elimination | **REFUTED** — a monthly review whose window rolled forward a month (prior 1/1, 2/1, 3/1 → current 2/1, 3/1, 4/1) reads as a **+90 cal d** slip that never happened and becomes the lane's and the headline's worst slip; the worst slip was overstated in 7,734 of 16,860 fuzzed recurring series | leftover pairing **dropped**; leftovers on one side only are NEW / REMOVED, on both sides DUPLICATE NAME |
| Collapse identical rows and pair — order irrelevant | **REFUTED** — pairing before the collapse flags a same-date second copy REMOVED | the collapse runs FIRST; pinned |
| Column D: infer a percent scale, read a date as "finished" | **REFUTED** — one "75" flips every Excel-percent "1" to not complete; a forecast date reads complete; the operator then said D holds words | status-word reader only; numbers, dates and unknown words are *not complete and NAMED* |
| The check sits at the start of the label block | **REFUTED** — for an inside label that is ON the bar, where a `--muted` disc on the lane fill measured **1.04–1.94 : 1** in the four themes | the check always sits BESIDE the shape; a complete row never takes an inside label |
| Dropping the unchanged ghost changes nothing else | **REFUTED** — the ghost was what kept wide unchanged labels outside their bars; without it 10,974 of 29,229 fuzzed unchanged labels flip inside and 4,386 other items re-pack | `inside` stays gated on "no prior side" exactly as before, so the geometry of every non-complete row is unchanged |
| The summary strip can take two more counts | **REFUTED** — the 3-line strip ellipsised "unchanged" and "complete" FIRST, in the lanes with movement | the strip now takes the largest size (6 → 3.6 pt) at which EVERYTHING fits; only past 3.6 pt is anything cut |
| "Excel omits blank rows (33 files)" | **CORRECTED** — 18 of the 51 Excel-authored workbooks under `00_REFERENCE_INTAKE` omit rows; 8 keep FORMATTED empty rows (the 33 I first counted mixed in non-Excel producers) | numbered reader honours `r=`, never counts elements |
| The pairing can cross swimlanes / a task can leave its lane | **SURVIVES** — 3,000-seed fuzz, 0 violations; mutations (lane dropped from the key, items pushed a row, placed in lane 0) go red | pinned by a seeded fuzz and a browser test |
| `read_xlsx` output unchanged for the SRA importers | **SURVIVES** with a condition — only if `read_xlsx` keeps its defaults; the whole-corpus digest (98 tracked xlsx-by-bytes + 13 synthetic) was re-run after the change and matched | numbered reader is a separate entry point sharing one budget |
| A `line` preset flipped vertically draws the rising stroke | **SURVIVES** — ECMA preset path + a PowerPoint-authored deck's glued connectors (0 EMU error) + LibreOffice read-back; without `flipV` LibreOffice draws a double backslash | pinned in the LibreOffice interop test |

## Decisions

1. **Matching (`compare_onepager_docs`).** Each sheet's identical rows (swimlane key, name key, start, finish) collapse to one, named. A key with at most one copy per side pairs as before, whatever its dates. A key that repeats pairs **only** copies with an identical (start, finish) — UNCHANGED — and never by elimination. Every repeated key is named in the notes; unresolved leftovers name only their own rows.
2. **Drawn once.** An UNCHANGED row has no ghost; the label, the packing and every other row's geometry are unchanged.
3. **Column D (`read_completion`).** A status that starts with Complete / Completed / Done / Finished / Closed (anything may follow: a date, "(late)"), or Yes / Y / X / a check glyph / Achieved / Met / Delivered / ≥100 % is complete; a negation, a blank, a percent below 100 or a known open status is not; anything else is not complete **and named by value and row**. A sheet with no column D has no completion (`None`) — not "nothing is complete". Column-D notes travel apart from the parser's (`completion_notes`) so /onepager, which draws no completion, never shows them.
4. **The check.** A `--muted` disc ("completed work", DESIGN-SYSTEM §1) with a `--bg` check, beside the current shape on its label's side; the pptx paints the same points as an ellipse and two round-capped line strokes (the rising one `flipV`). The legend explains it only when a list has a column D. The per-swimlane strip, the summary table, the drawer, the Excel export and the headline count it; a completion that went backwards, or a complete item whose date moved, is flagged; complete items that left the list are named.
5. **Swimlanes.** The compare's swimlane and name keys fold typographic twins (dash, curly quote, zero-width) so one lane is never two bands; a hyphen and a space stay different. Each list's own reading — including "no swimlane name — placed under X", the decision that puts a task in its lane — is now shown on the compare page ("How each list was read"); before, only its skipped rows were.
6. **True rows.** `read_xlsx_numbered` + `parse_numbered_workbook` serve both One-Pager uploads; every row citation is the row Excel shows. `read_xlsx` is byte-identical for its other callers.

## Verification

- **Red first:** the three new test modules failed at import on the pristine tree; seven new page tests failed on behaviour before the page changed.
- **Mutation battery on a scratch copy (never the repo tree): 38 of 38 red by the named test** — including the refuted leftover pairing, the collapse removed, the check on the bar, the packer not reserving it, the old strip, the counting reader on both routes, the numbered reader skipping the zip budget, the JS painter putting an item in the wrong lane, and the pptx losing `flipV`. Two first-run survivors were test defects, fixed: "Completion pending" never shared the letters of "complete" (replaced by "Completely blocked", which does), and the strip fixture was not dense enough to reach a row floor (rebuilt on a 6 pt slide).
- **Rendered** the page (pristine vs changed, same pair) in all four themes: the four DUPLICATE NAME shapes become two unchanged items; checks beside their shapes; nothing wider than the viewport; zero page errors.
- **Deliberate re-baselines, each with its reason in the test:** the unchanged-ghost pin (inverted), the summary-strip ≤ 3 lines pin, the browser ghost count 16/6 → 4/3, the two takeaway sentences (now also "N unchanged"), the slot line ("no column D"), the r11 and DD-line locators for `onepager_compare.js` 131 → 152 (caption md5 `ed5a829d…` re-derived and identical).

## Deliberately NOT done (measured, left)

- Clipped end-anchored labels can still run left of the chart (pre-existing: 102 of 82,220 fuzzed labels); the check itself never does.
- The NEW / REMOVED tag text overruns its box under the container's substitute font (pre-existing, identical in the pristine render).
- `read_xlsx`'s own r-less-cell handling (column A) is unchanged for the SRA path.
- No cue yet for an open item whose date has passed; no column D in the shared /onepager template.
- **UNVERIFIED:** PowerPoint itself (not in any container); the operator's real files (not in the repo) — every column-D word the reader does not know is named on the page for exactly this reason.
