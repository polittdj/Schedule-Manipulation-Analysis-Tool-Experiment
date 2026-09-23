# Handoff — 2026-09-23 (One-Pager Compare round two (ADR-0526) — a repeated name whose date did not move is ONE unchanged item, column D is a STATUS word drawn as a check, every row cites the row Excel shows — **v1.0.289**)

STATUS (current) — branch **`claude/loving-euler-ek7ve9`**, draft PR opened this session (the operator merges; never marked ready here). Based on `main` @ `f4703fd` (#713, ADR-0524/0525, v1.0.288) — merged in cleanly mid-session because #713 landed while this unit was in flight, so this unit is **ADR-0526 / v1.0.289**, not 0524. `src/` changed: wheel + nine installers rebuilt as the LAST step, so **EIGHT checks** (CI's six + installer-smoke `linux` / `windows`). Highest ADR **0526**. Version **1.0.289**. Schema unchanged. QC-1 / QC-2 / QC-3 bind every session.

## What landed (operator request 2026-09-22, three rulings asked for and given)

The request: column D says whether a task is complete — show it on the chart; a task whose name and date did not change is NOT "DUPLICATE NAME" — show it once with its single date; tasks always stay in their swimlanes; show the slips AND what did not slip. Rulings: swimlanes = a standing requirement (no bug seen); same swimlane + name + date in both sheets = one item; column D = status words.

* **Matching** (`reports/onepager_compare.py`): identical rows collapse per sheet FIRST (named); a repeated (swimlane, name) pairs only copies with an IDENTICAL (start, finish) — UNCHANGED, drawn once — and **never by elimination**; leftovers on one side are NEW / REMOVED, on both DUPLICATE NAME (rows named). Keys fold typographic twins (dash, curly quote, zero-width).
* **Drawn once:** no ghost under an unchanged bar; `inside` stays gated on "no prior side", so no other geometry moves.
* **Column D** (`reports/onepager.py read_completion`): status-word reader; unknown words, numbers and dates are not complete AND named (`completion_notes`, kept off /onepager). Check = `--muted` disc + `--bg` check BESIDE the shape (JS + pptx same points; pptx = ellipse + two round-capped line strokes, rising one `flipV`). Counted in strip / table / drawer / Excel / headline; completion regressions and moved-after-complete flagged.
* **Summary strip** shrinks to fit (6 → 3.6 pt) before cutting anything; counts unchanged + complete.
* **True rows:** `read_xlsx_numbered` + `parse_numbered_workbook` on BOTH One-Pager uploads (Excel omits unformatted blank rows — 18 of 51 Excel-authored intake workbooks). `read_xlsx` byte-identical for the SRA importers (whole-corpus digest `827ee8fc…` before = after).
* Compare page now shows each list's own reading ("How each list was read" — the inherited-swimlane decisions).

## How it was verified

QC-3: five skeptics attacked the plan before any edit — **leftover 1:1 pairing REFUTED** (+90 cal d invented on a rolling window), collapse-order, numeric column-D inference, check-on-the-bar (1.04–1.94:1), "ghost drop changes nothing else", and the 3-line strip all refuted and replaced; see ADR-0526's table. Red-first tests (3 new modules + page/browser/interop additions). **Mutation battery 38/38 red by name** on a scratch copy (two first-run survivors were test defects, fixed). Rendered pristine vs changed in 4 themes (4 DUPLICATE shapes → 2 unchanged items; 0 page errors). Full suite pre-merge: 5,917 passed / 5 standing skips / 1 fail = the installer lockstep, rebuilt as the last step. LibreOffice Impress had to be apt-installed in this container for the interop test to RUN locally (CI installs it and fails on a skip).

## Deliberate re-baselines (reasons in each test)

Unchanged-ghost pin inverted · strip ≤3-line pin → "whatever fits, no ellipsis" · browser ghosts 16/6 → 4/3 · both takeaway sentences gain "N unchanged" · slot line gains "no column D" / "column D: N complete" · r11 + DD-line locators `onepager_compare.js` 131 → 152 (caption md5 `ed5a829d…` identical).

## Not done (measured, left) · carried forward

Clipped end-anchored labels can run left of the chart (pre-existing, ~0.1 % of fuzzed labels) · tag text overruns its box under the container's substitute font (pre-existing) · `read_xlsx`'s r-less cells still land in column A on the SRA path · no overdue-open cue · no column D in the shared template. **UNVERIFIED:** PowerPoint itself; the operator's real column-D words (every unread word is named on the page for exactly this).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
