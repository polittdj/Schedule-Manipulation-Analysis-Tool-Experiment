# Handoff — 2026-10-01 (b) (LODESTAR 2.1 — the Compare strip fits the face that paints it; a risk register drawn on both slides as triangles by probability; every export carries the slide's record and restores it, links included — ADR-0544 · **v1.0.299**)

> **A feature session, outside the AUDIT-2026-09-23 campaign.** Branch `claude/lodestar-app-updates-q4xos3`
> from `main` @ `e75a751e` (#731, ADR-0543, v1.0.298). The campaign's open disclosures (A0923-CPM-048 / 049 /
> 050 / 051, A0923-CPM-040's demo instance, A0923-IMP-005 and A0923-DOC-003 strict-xfail) are carried
> UNCHANGED in the archived 2026-10-01 handoff and `docs/STATE/AUDIT-2026-09-23.md`; this session touched none.

STATUS (current) — **ADR-0544 MERGED** as `64643f37` (#732, 2026-10-01 20:42Z; squash tree `4ff20b8e` identical to
the green PR head `68d9e074`, all eight checks green after three CI rounds named in the session log). `main`'s own
CI run #2052 and installer-smoke #855 were IN PROGRESS when this was written — the next session reads them by their
jobs first. Highest ADR on disk **0544**. Version **1.0.299**; LODESTAR **2.1.0** (`lodestar/LODESTAR.pyz`
**53 members**). QC-1 / QC-2 / QC-3 bind every session.

## What ADR-0544 did (operator request 2026-10-01, four asks)

- **The CHANGE SUMMARY overflow (ask 1) — measured and fixed.** The strip, tags and deltas are set in IBM Plex
  Mono (0.6 em, measured) and were sized at Calibri's 0.52: `MONO_CHAR_W`, the strip's 3.2-pt step before a cut
  (`SUMMARY_FLOOR` / `SUMMARY_MIN`), `text-rendering: geometricPrecision` on the slide (Chromium rounds advances
  to device pixels at slide scale), an exact box squeeze re-run on `fonts.ready`. Chromium: 0 overflows in both
  views; the 0.52 mutant red (`tests/reports/test_onepager_summary_fit.py`, three browser tests — the
  pixel-rounding twin was refuted by CI's runner on the first run and replaced by a tracked-wider-face twin).
- **Risks (ask 2).** `reports/onepager_risks.py` (header-driven reader, template at `/export/xlsx/risks-template`),
  ONE optional register for both pages (`onepager_risks` on the session, undoable), packed by date as triangles
  in the probability colour, `RISK · name (date) · impact` labels, legend entries, HUD, DATA drawer, Excel table.
  **ASSUMPTION for the operator:** column E = date of occurrence (the ask named none).
- **Restore any export (ask 3).** `reports/session_payload.py` (the record: rows as read, links by identity,
  risks, settings) carried by the PowerPoint (customXml part + alt-text fallback, `pptx_read.py`), the NEW PDF
  export (`reports/pdf.py`, embedded file, `pdf_read.py`) and the Excel export (restore sheets); a Restore zone on
  both rails; restore lands on the export's page, applies and NAMES the data date and marking; exports and
  registers dropped on a list slot are refused by name. No separate Risks page (ask 4).
- **Pins re-derived on purpose:** the window digest split (Timeline pristine, Compare stripped pristine, Compare
  whole re-derived); the dense one-row strip test (pt ≥ 3.2); archive members 48 → 53; upload-route tables;
  export census (+PDF, +risks template); `loaded` (+risks); the API-line mutation anchor; links sheet renamed
  "Links (restore)"; the launch page's version literal.

## Open — for the operator

- **Column E (date of occurrence) is an assumption** — say if the register should carry the date elsewhere.
- **UNVERIFIED here:** PowerPoint keeping the custom XML part on its own re-save (CI MEASURED LibreOffice 24.2's export
  keeping the part and dropping the shapes' alt text, so the part — not the alt text — is the carrier
  that survives a re-save; the interop test pins both); PDF rendering outside poppler;
  Windows / macOS. (The three new browser tests passed on CI's browser job, run 36903412944.)
- **Deferred, named in the ADR:** OWNED == CONTENT mutation test; a browser test for the page switch after a
  restore; a Compare round trip with a DUPLICATE NAME pair; bomb-size tests on the three readers; Polaris²'s own
  wording for an export dropped on its list slot.
- **Carried unchanged:** ADR-0543's ruling (no label nudge); the three pre-existing PowerPoint defects; the
  size-cap ruling; the un-layered `help.py` / `i18n.py` / `offload.py` / `system.py` note.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
