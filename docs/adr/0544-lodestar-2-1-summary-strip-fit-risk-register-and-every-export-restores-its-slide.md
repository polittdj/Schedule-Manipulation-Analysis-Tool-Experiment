# ADR-0544 — LODESTAR 2.1: the Compare slide's summary strip fits the face that paints it; a risk register drawn on both slides as triangles by probability; every export (PowerPoint, Excel, PDF) carries the slide's record and restores it, logic links included

**Status:** Accepted · **Date:** 2026-10-01 · **Extends:** ADR-0543 (LODESTAR 2.0), ADR-0539 (LODESTAR, logic
links), ADR-0524 (the summary strip's rule) · **Keeps:** every ADR-0543 ruling (no label nudge; links never move
an item) · **Operator:** David Politte

## Context

The operator (2026-10-01, with a screenshot of the Compare page) asked four things of the standalone program:
(1) fix the CHANGE SUMMARY text running outside its coloured boxes; (2) risks on the One-Pager — an Excel
register (A swimlane, B risk, C potential durational impact, D probability High / Medium / Low) drawn "like a
milestone as a single moment in time" with the name, the date of occurrence and the impact beside it, coloured
red / yellow / green by probability, placed in the swimlane by date, unmistakably a risk; (3) re-import ANY
export — PowerPoint, Excel, PDF — and recreate the One-Pager from it, the logic links included, on both pages;
(4) a separate Risks page only if better; risks optional.

## Decisions

1. **Ask 1 — the width model names the face (root cause measured, not inferred).** LODESTAR sets the Compare
   strip, the NEW / REMOVED / DUPLICATE NAME tags and every calendar-day delta in IBM Plex Mono, a monospace
   face advancing exactly 0.6 em per glyph (measured in Chromium against the vendored WOFF2: 0.6000 on every
   sample), while `reports/onepager.wrap()` sized them with `CHAR_W = 0.52`, Calibri's average. Every wrapped
   line painted ~15% past its box (on the pristine tree: 7 of 12 lines, up to 28.5 pt of a 118-pt box; every
   tag pill). `MONO_CHAR_W = 0.6` now sizes those three roles; the labels keep 0.52 (IBM Plex Sans measures
   0.44–0.51). The strip keeps ADR-0524's rule — the largest size at which the whole of it fits, 6 pt down to
   the 3.6-pt floor — and, where a monospace face no longer holds the whole strip at the floor, steps down to
   `SUMMARY_MIN` 3.2 pt before anything is cut (3.2 pt of a 0.6-em face carries what 3.6 pt of Calibri did);
   the one running sentence is tried when the counts-then-worst-slip form needs a line more. Measured second
   cause: Linux Chromium rounds each glyph advance to a device pixel at slide scale (+2.5% on a 6-pt line, +6%
   on a 10-pt tag, zoom-dependent), so the slide now renders with `text-rendering: geometricPrecision` (0.600
   at every scale) and the painter holds boxed text to its box exactly (`squeeze`, re-run once the web fonts
   are in). Chromium, both views, after the change: 0 overflows, 0 squeezes; the 0.52 mutant goes red by name
   (`tests/reports/test_onepager_summary_fit.py`, the browser tests). The pixel rounding is an
   ENVIRONMENT's: the session's Chromium showed it (+2.5 % / +6 %), CI's Chrome 153 runner did not — the
   first browser twin lifted the declaration and expected an overflow, and CI refuted it on the first
   run; the committed twin tracks the face 0.4 px wider instead (deterministic everywhere) and proves
   the checker's teeth and that the painter's squeeze holds every painted line inside its box.
2. **Ask 2 — one optional register, both slides, no separate page.** A risk only means something against
   the schedule it threatens, so the register is ONE session attribute (`onepager_risks`, undone and redone
   like the lists, kept by "Clear list") drawn on whichever slide is shown. The reader
   (`reports/onepager_risks.py`) is header-driven — swimlane · risk · impact · probability · **date of
   occurrence** — with A–E positional when there is no header; impact in days (d / w / mo converted and the
   unit named; anything else kept verbatim); probability folded to high / medium / low, anything else NAMED
   and drawn neutral; every row-level decision a sentence, as the list reader's are. The layout packs a risk
   into its swimlane's rows by its date like a milestone (a swimlane only the register names gets a band of
   its own, named), marks it `kind="risk"` with `prob` and `impact` on `Placed` / `PlacedCompare`, and the
   painters draw an UPWARD TRIANGLE in the probability colour (page tokens `--status-fail` / `--status-warn` /
   `--status-pass` / `--status-neutral`; print B3261E / B8860B / 1E7B34 / 6B7280) labelled
   `RISK · name (m/d/yy)` with the impact after it in that colour; the legend names each probability drawn.
   A risk is never a link's end and never counted in a summary. **ASSUMPTION flagged to the operator:** the
   ask names no date column, yet asks for placement by the date of occurrence; column E carries it, and a
   header puts it anywhere. A risk dated outside the list's own span is named when it widens the timescale.
3. **Ask 3 — one record, three carriers, one restore.** `reports/session_payload.py` writes the slide's record
   — each list's rows AS READ (Excel row numbers kept), the sheet and file names and the forced layout, the
   links by key AND identity, the register's rows, the settings (page, title, window, data date, marking) —
   as the same bytes into every export: the PowerPoint as a custom XML part (`customXml/item1.xml`, related
   from the presentation) with every item shape's and the Title shape's alt text as a fallback for a re-saving
   program that keeps alt text (MEASURED in CI: LibreOffice 24.2's export keeps the custom XML part and
   drops the alt text; PowerPoint is unverified); the PDF — a NEW server-side export (`reports/pdf.py`, std-lib, Helvetica / Symbol, the
   pptx paint order call for call) — as an embedded file `lodestar-session.json`; the Excel workbook as plain
   sheets after the existing ones (a settings sheet, each list at its row numbers — droppable as a list in
   its own right — the links by identity, the register). A restore hands the rows straight to the SAME parser
   a drop goes through, so the restored document is EQUAL to the exported one (keys, skipped rows, notes),
   re-binds the links by identity, applies the data date and the marking and SAYS so, and lands on the page
   the export came from (one logged, undoable step). A file is read by its bytes, never its name: an export
   dropped on a list slot is refused by name pointing at Restore; a register on a list slot likewise; a PDF
   from the browser's Print dialog (which carries no record) and a 2.0 export are refused by name. The alt-text
   fallback restores a partial slide and says what it cannot carry.
4. **Ask 4 — no separate page** (decision 2). The Risks slot and the Restore zone stand on both rails; the
   exports gain ⤓ PDF beside PowerPoint and Excel; Print stays for paper.

## The plan was attacked before it was built (QC-3), and what fell

Ten assumptions, five refuters and a critic on the pristine tree (`scratchpad/attack/` scripts in the session):
A1 / A2 PARTLY REFUTED — the overflow holds (quantified above) but 0.6 em is the font's metric, not what the
page paints (hinting), so the painter-side fix is load-bearing (decision 1); U+2212 and U+00B7 are in the mono
subset at 0.6, → ← are in no vendored face. A3 PARTLY REFUTED — a workbook rebuilt from the rows reproduced
50 of 53 variants; the three that fell (a sheet name mangled, a carriage return) are why the restore hands the
rows to the parser instead. A4 HELD. A5 PARTLY REFUTED — poppler accepts the std-lib PDF on every oracle; the
reader had to match dictionaries whitespace-agnostically. A6–A8 PARTLY REFUTED — the census named eleven pins
the plan had missed; each re-derived on purpose (the archive's 53 members, the upload-route tables, the export
census with a PDF branch, the `loaded` dict, the API-line mutation anchor, the links-sheet substring gate,
the version literal). A9 HELD (the CUI guard neither blocks the PDF nor loses its teeth). The critic's REFUTED
findings applied: a risk register on a list slot refused by header; the restore names the data date and
marking it applies; a risk beyond the list's span named; a register with no list says so; bounded readers.
**Deferred, named:** an OWNED == CONTENT mutation test; a browser test for the page switch after a restore; a
Compare round trip with a DUPLICATE NAME pair; bomb-size tests on the three readers; Polaris²'s own wording for
an export on its list slot. Recorded per C12: Ask 1's implementation began while the attack ran, in files the
attack had already read from the pristine tree; the refuters measured a server started before the edits.

## Consequences

- `tests/reports/test_onepager_window.py`'s pristine digest is split on purpose: the Timeline's is the pristine
  tree's own; the Compare's with the four moved fields stripped is too; the whole Compare digest is re-derived.
- A pre-existing defect fixed in passing (the PowerPoint agent): a shape name holding `"` wrote a malformed
  slide; attributes are escaped now.
- `OnePagerDoc` carries `rows` and `forced_layout`; `OnePagerSession` / `OnePagerSnapshot` / Polaris²'s
  `SessionState` carry `onepager_risks` (never set by Polaris²; a TYPE_CHECKING import keeps the layering).
- LODESTAR 2.1.0; archive 53 members; version 1.0.299.
- **UNVERIFIED:** PowerPoint's own re-save keeping the custom XML part (no PowerPoint, no Impress here — CI's
  browser job runs the interop test); rendering of the PDF in Acrobat / Edge / Preview (poppler only here);
  Windows / macOS; the three browser tests ran only through the session's node Playwright, not pytest.
