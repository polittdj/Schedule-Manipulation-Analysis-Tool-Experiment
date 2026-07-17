# ADR-0247 — Audit remainder (ADR-0245): driving-path per-task shading, xlsx zip-bomb cap, redact() spaced-path leak

## Status

Accepted. Clears the five queued findings from the ADR-0245 orchestrated audit (none a live CUI
leak or parity break; queued as MED/LOW), each lead-verified against the code before the fix.

## Context

ADR-0245 fixed the two HIGH/BLOCKER defects and queued five remainder items. Re-verified each:

1. **`/driving-path` corridor Gantt was not per-task shaded (#382 wiring gap).** ADR-0243 shades
   each Gantt row's non-working time per THAT task's own calendar (a 24-hour task shows no weekend
   gray). #382 listed `/driving-path` as "wired", but `driving_path.js:206` read a per-row
   `a.calendar` the server's `_driving_path_gantt` **never emitted**, AND the page **never called**
   `SFTimescale.setCalendars` (only the `/analysis` path in `app.js` does) — so `CALS` was empty and
   `calendarByName` returned Standard (Mon-Fri) for every row. The corridor fell back to a flat
   Mon-Fri shade — the exact misleading behavior ADR-0243 fixed on `/analysis`. Doubly dead.
2. **The Gantt shading JS was behaviorally untested.** `SFTimescale.nonworkStyle` / the
   `setCalendars` registry had no test; #382's silent no-op proved that gap.
3. **The `/margin` mixed-basis disclosure was untested at the view/export level.** PR-R3 (ADR-0244)
   suppresses the erosion fit and discloses the basis change in the ENGINE (tested), but the
   on-screen takeaway and the Excel export row that surface it to the analyst were not.
4. **The SRA xlsx re-import route had no size cap.** `read_xlsx(file.file.read())` read the whole
   upload uncapped, and `read_xlsx` decompressed every zip member via `zf.read()` with no bound — a
   zip bomb (tiny compressed, gigabytes decompressed) could exhaust RAM. `/upload` caps at 500 MB.
5. **`redact()` leaked the middle words of a spaced file name in a path.** The space-free path
   regexes stop at the first space, so `\\server\share\Site Alpha Rebaseline.mpp` redacted to
   `<path#…> Alpha <file:mpp#…>` — the CUI token `Alpha` survived in clear text (reproduced for UNC,
   Windows-drive and POSIX forms).

## Decision

Fix all five, each with a regression test that fails on the old code (mutation-verified):

1. **Driving-path shading (Option A — complete the wiring, faithful to ADR-0243, Law 2).**
   `_driving_path_gantt` now emits a per-activity `calendar` name (task's own `calendar_uid` → its
   registered name, else the project calendar — the same resolution as the `/analysis` grid) and a
   `calendars` union (name + working weekdays + holidays) across every version. `driving_path.js`
   registers it with `SFTimescale.setCalendars(payload.calendars)` at init, so `paintNonwork`
   resolves each row's own calendar. A 24-hour corridor task now shows no weekend gray.
2. **Node harness `tests/web/js/gantt_shading_harness.mjs`** loads the vendored `timescale.js` IIFE
   and asserts per-calendar shading: before registration an unknown name falls back to Standard and
   shades (the bug); after `setCalendars`, a Mon-Fri calendar shades weekends and a 24-hour one does
   not, and an explicit global pick overrides the per-row calendar. Mutation-verified: dropping the
   per-row `cellCal` from `nonworkStyle` fails it.
3. **`/margin` view+export test** drives an 8h→24h mixed-basis schedule through `/margin` and the
   Excel export, asserting the disclosure prose renders and the export shows a
   `mixed — 8h/day vs 24h/day` basis row with `—` (never a fabricated erosion rate) for erosion.
4. **Xlsx zip-bomb cap.** `read_xlsx` decompresses every part through one shared byte budget
   (`_MAX_XLSX_DECOMPRESSED_BYTES` = 500 MB, parity with `/upload`) via streamed capped reads, so a
   part that inflates past the cap raises `XlsxError` regardless of its declared size. The two SRA
   re-import routes also cap the COMPRESSED upload (`_MAX_UPLOAD_BYTES + 1` read) before parsing.
5. **`redact()` spaced-path fix.** A new `_SPACED_FILE_PATH_RE` runs before the space-free path
   regexes and consumes a path prefix + a spaced file name terminating in a sensitive extension
   (UNC / Windows / POSIX), redacting the whole thing via the inert `_redact_path` token. The name
   run stops at a separator / newline and is length-bounded, so ordinary prose after a space-free
   path (`…\share\data to the archive`) is still never swallowed, and `redact` stays idempotent.

Option A was chosen over "drop the dead read + correct the #382 claim" because ADR-0243 was an
operator-approved fix and `/driving-path` was claimed as wired; leaving it flat-shaded would be a
standing fidelity gap (Law 2). The rendering path (colors/tokens/`paintNonwork`) is unchanged from
the ADR-0243-verified `/analysis` shading; the change is behavioral (which calendar drives a row).

## Consequences

- `/driving-path` shading now honors each corridor task's own calendar, completing ADR-0243.
- Log lines can no longer leak a spaced CUI file name's middle words (Law 1 hardening).
- The SRA re-import path is bounded in both compressed input and decompressed output (DoS/RAM).
- Verification: full gate green; the driving-path wiring smoke-tested in real Chromium (payload
  carries the calendars union + per-activity `calendar`, `setCalendars` runs, corridor shading
  renders, zero JS console errors); the 24h-vs-Mon-Fri differential is pinned by the node harness.
- `src/` changed (app.py, driving_path.js, xlsx_read.py, logging_redaction.py) → v1.0.56 → 1.0.57,
  wheel + 9 installers rebuilt in lockstep.
