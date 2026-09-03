# ADR-0454 — The SRA grid, driven for the first time: what the operator sees before Save is what is saved, and nothing they typed is dropped in silence

- **Status:** Accepted — 2026-09-03 (WP3 · M4 of the POLARIS² audit campaign, UI-map row 27 — the last queued row)
- **Version:** 1.0.232
- **Extends:** ADR-0313 (operator-visible refusal on `/sra`), ADR-0308 (no range on completed work), ADR-0443 (WP2's two-oracle driver method)
- **Shipped:** `static/sra_grid.js` (pending map survives a reload; `beforeunload` guard; save summary read back into the status line; `badInput` refused at the cell; paste reports what fell outside the cells), `web/app.py` (`POST /sra/grid`: a blank clears; `rejected` + `clamped` in the reply; `_grid_number` / `_grid_factor`), `tests/web/test_sra_grid_edit_browser.py` (17 drivers, NEW), `tests/web/test_sra_grid.py` (+4 route pins)

## Context — a grid nobody had ever typed into

The editable SSI grid (ADR-0123) is where the operator ranks every activity (Risk Ranking Factor
0–5), overrides Best/Worst Case days, picks the focus event, and — the feature the panel text
advertises — pastes a whole column from Excel. Before this work its coverage was ``TestClient``
plumbing (the JSON feed, the batched POST, Save/Load) plus a test that **grepped the served JS for
``"paste"`` and ``split("\t")``**. Bytes, not behaviour. The WP1 census (ADR-0442) proved the zoom
and fit controls move; the edit / paste / save round trip was the one UI-map row still marked
*queued*.

Driven in Chromium with a REAL clipboard (``navigator.clipboard.writeText`` + ``Control+V`` under
the ``clipboard-read/write`` permissions — measured to deliver the ``paste`` event with the text),
Excel-shaped payloads (CRLF, trailing newline, tab-separated blocks) and two oracles per control
(the status line the operator reads, and a digest of the rendered grid that includes every input's
live ``value`` and every radio's ``checked``), the grid did the following on the pre-fix tree —
each observed before a line changed:

| # | did | measured on v1.0.231 |
| --- | --- | --- |
| M4-01 | "Refresh grid" and the post-run tint reload (``sf-ssi-run``) reset the pending map | "1 task(s) with unsaved edits." → "145 tasks."; the server never saw the value |
| M4-02 | a blanked cell was sent as ``""`` and the route skipped it | cell empty → Save → "Saved 0 change(s)." → the old value came back. **No way to clear a factor or a range from the grid at all** |
| M4-03 | an unparseable pasted token vanished on save; an out-of-range 7 was clamped without a word | paste ``Factor / 12,5 / 7`` → "Pasted 4 value(s)" → Save → "Saved 7" (of 10 deltas), three cells silently back to blank, the 7 silently 5 |
| M4-04 | the "Saved N change(s)." confirmation was overwritten by the reload's row count | readable for one fetch round trip only |
| M4-05 | a non-number typed into a number input (Chromium ``validity.badInput``, value ``""``) queued as an edit | "1 task(s) with unsaved edits." for a keystroke of ``e`` |
| M4-06 | every SSI form on the page POSTs + redirects; no ``beforeunload`` guard | a pending edit rode out on "Calculate SRA Durations" with no prompt |

Nine pass-side drivers were green on that tree and stay green: type → queue → survives a full
re-render; Save posts the deltas and the row shows the factor-derived range; a manual Best/Worst
paints the envelope; the focus radio reaches ``/api/sra/ssi``'s ``target_uid``; a column paste fills
down from the pasted cell; a three-column block fills Factor / Best / Worst left-to-right and a
block pasted onto Best starts there; a single value falls through to the browser's own paste; and
the setup file (``/sra/ssi/save``) loaded into a NEW server on the same file reproduces the grid
**digest-for-digest**.

## Decisions

1. **The pending map is the operator's, not the reload's.** ``load()`` no longer resets it;
   ``inputCell`` re-applies every unsaved edit over the fresh rows exactly as a column-filter
   repaint already did. Only a save spends the map. The status line after a reload reads
   ``145 tasks · 1 unsaved edit(s).`` A ``beforeunload`` guard fires while the map is non-empty.
2. **A blank clears.** ``POST /sra/grid`` treats ``""`` as *clear this cell*: the Factor is removed
   (a stored range stays until IT is blanked — it is the operator's, or was derived from the
   ranking they just removed, and ``_ssi_three_point`` gives it precedence either way); a blanked
   Best or Worst side drops the stored pair and re-derives it from the ranking when one exists, so
   the grid then shows exactly what the run will use; with no ranking, blanking both sides removes
   the range. Literal semantics — only the cell that was blanked changes.
3. **Every value the route cannot apply as typed is returned by name.** ``rejected`` (not a
   number; not a whole number 0–5; a range on completed work per ADR-0308) and ``clamped`` (a
   factor outside 0–5, a negative duration), each with ``uid`` / ``field`` / the text as sent /
   the reason or the applied value. The grid reads it back: ``Saved 1 change(s) · 2 value(s)
   rejected: UID 41 Factor "Factor" — not a number; UID 42 Factor "12,5" — not a number · 1
   clamped: UID 43 Factor 7 → 5``. ``12,5`` is refused and reported, never guessed as 12.5 or 125.
   This is ADR-0313's rule ("an operator-visible refusal instead of a silent fabricated figure")
   extended from the risk form and the setup upload to the grid.
4. **The save summary survives the reload** (``load(note)`` carries it into the status line).
5. **``badInput`` is refused at the cell**: a number input holding text it cannot parse reports
   ``""``, which under decision 2 would have become a silent clear. The change handler drops any
   queued value for that cell and says ``UID 34 Factor: the typed text is not a number — not
   queued; fix or clear the cell.``
6. **A paste says what fell outside the cells** (columns past Worst Case, rows past the last
   editable one) instead of counting only what landed.

## Verification (QC-1)

- **Red first, by name.** The 17-driver module ran on the pre-fix tree: 7 red (the six defects
  above; the seventh was the envelope oracle reading ``title=`` after ``tooltips.js`` had moved
  it to ``data-sf-hint`` — the WP1 trap, fixed in the oracle), 9 green. The four route pins ran
  against the ORIGINAL route with the fixed tests: exactly those 4 red, the 20 pre-existing green.
- **Discriminating mutation.** Original JS + fixed route: exactly the six JS-side drivers red
  (M4-01 ×2, M4-03's status line, M4-04, M4-05, M4-06); the route-side blank-clear driver and all
  ten pass-side drivers green. Each half of the fix is proven independently.
- **The oracle is pinned** stable (byte-identical digest across a full page reload, and across two
  servers on the same file) and sensitive (moves on a typed value and on a saved edit).
- Whole modules only, never ``-k``; the tree restored from scratchpad copies (``diff -q``) after
  every swap.

## Consequences

- The grid now behaves like a spreadsheet the operator would trust in a testimony setting: an
  edit is theirs until they save or discard it, a blank means blank, and a value that cannot be
  applied is named with the reason rather than replaced by the previous value.
- ``POST /sra/grid``'s reply grew two keys; the old ``{ok, saved}`` shape is a subset, so no
  caller breaks. The setup file format is untouched.
- Deliberately NOT done: no locale guessing on ``12,5`` (refuse and report is the honest answer
  in a tool whose figures are testimony); no confirmation prompt on Refresh (edits now survive it,
  so there is nothing to confirm); the sticky controls bar over the sticky header (ledger
  OBSERVED) stays a cross-page design question.
