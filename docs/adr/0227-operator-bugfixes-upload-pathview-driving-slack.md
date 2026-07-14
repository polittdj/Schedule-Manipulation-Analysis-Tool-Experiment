# ADR-0227 — Operator bug fixes: resilient upload, /path version agreement, driving-slack scope, inactive baseline, SSI leveled parity gate

## Status

Accepted. Fixes a cluster of correctness/robustness bugs the operator reported against a multi-version
load of the real master IMS (`Large Test File Leveled.mpp`, focus UID 152), each root-caused,
reproduced, and verified — the engine's driving-path/critical-path math was found **correct**; the
bugs were in the web/UI layer and one importer rollup. No metric formula changed.

## Context

Operator reports (multiple versions loaded at once):
1. **Folder upload fails with Chrome `ERR_ACCESS_DENIED`** even though the folder holds valid `.mpp`s.
2. **"The critical path is incorrect… as if it is mixing up the information from the various files."**
3. **A stored "Driving Slack" field that is in the later `.mpp` doesn't show** on *What drives a date*.
4. Active vs **inactive** tasks must be handled/calculated correctly.

Investigation (three parallel deep-dives + direct reproduction against the operator's SSI Directional
Path exports) established:

- **The driving-slack / critical-path ENGINE is correct.** On the leveled file the engine reproduces
  SSI's *get-all-dependencies* driving set to UID 152 **UID-for-UID (783/783)** with 777/783 slack
  values exact, and **all 60** of SSI's critical-path (Path 01) tasks at 0-day driving slack. Loading a
  second version does **not** change the first version's path (no cross-version contamination); the
  `SessionState` caches and the engine are correctly keyed by `unique_id` / object identity.
- **The "mixing files" bug is in the `/path` page.** Its *What drives the date* header is anchored on
  the **latest** loaded version, but the driving-path grid's schedule `<select>` had **no `selected`
  option**, so the browser defaulted to the **oldest** version — one file's header sat above another
  file's path.
- **"Driving Slack not showing" is the same wrong-version default:** the field lives on the *latest*
  `.mpp`; the grid traced the *oldest* one (whose columns lack it). (The importer parses it correctly —
  723 tasks carry it on the leveled file.)
- **`ERR_ACCESS_DENIED` is a browser-side, pre-network abort** (well-cited): Chrome reads a picked
  file's bytes lazily at POST time; an un-hydrated **OneDrive Files-On-Demand placeholder** (the folder
  is under a OneDrive Desktop) or a file **open in MS Project** makes that read fail, killing the whole
  full-page `form.submit()` navigation before it reaches the server — which is why the identical bytes
  upload fine off-Windows.
- **Inactive tasks** are already modeled (`Task.is_active`), imported (`<Active>`), and excluded from
  CPM / metrics / driving-slack (ADR-0128) — with **one** inconsistency: the imported *project baseline
  finish* rollup did not exclude them.

## Decision

- **Resilient upload (`web/static/home.js`, `POST /upload`).** Upload now goes through `fetch()` with a
  per-file `arrayBuffer()` **pre-read**: readable files are uploaded; a file whose read throws
  (`NotReadableError` — cloud placeholder / locked / AV) is **skipped and reported by name** with the
  self-service fix ("right-click → Always keep on this device, close MS Project, retry") instead of
  aborting the whole navigation to a dead browser error page. Pre-buffering the bytes also sidesteps the
  sibling `ERR_UPLOAD_FILE_CHANGED` race if OneDrive hydrates mid-send. The server answers the fetch
  (`X-SF-Ajax`) with JSON `{redirect}` and the client navigates there, so the single-file jump and the
  server-side import flash still render; a plain form POST still gets the 303 (backward compatible).
- **`/path` version agreement (`_path_body`).** The schedule `<select>` now marks the **latest** version
  (`keys[-1]`) `selected` — the same version the header is anchored on — so the grid and header describe
  the same file by default. This also restores the later `.mpp`'s "Driving Slack" as an available column.
- **Driving-slack scope pairing (`/api/driving`, `/api/driving-path`).** Both now pass `st.scope(sch)`
  (not the raw schedule) so the traced network matches `analysis_for`'s **scoped** CPM — previously a raw
  schedule was traced against a scoped CPM once a session Analysis Target/filter was active. No-op when
  neither is set.
- **Inactive baseline (`importers/mspdi.py::_project_baseline_finish`).** Skips `<Active>0</Active>` tasks,
  so an inactive row's late baseline finish no longer inflates the CPLI basis — matching the rest of the
  engine and MS Project.
- **SSI leveled parity gate (`tests/engine/test_ssi_leveled_uid152.py` + gzipped MSPDI fixture).** Pins,
  against the operator's own SSI exports, that the engine reproduces the **critical path to UID 152
  exactly** (60/60 at 0-day slack) and the **full driving set** (783/783), with slack magnitudes exact
  bar a documented sub-day/one-day calendar-handoff rounding. This is the "assume nothing" gate answering
  "the critical path is wrong": it is provably correct on the operator's real file.

## Consequences

- The blocking folder-upload failure degrades gracefully: readable files load; unreadable ones are named
  with the fix. Verified end-to-end in Chromium (upload → navigate → schedule loaded, no console errors).
- The `/path` page shows one consistent version by default; the "critical path mixing files" and
  "Driving Slack missing" reports are resolved by the same fix, and locked by tests.
- No metric/formula change; parity untouched (the goldens carry no inactive-with-late-baseline row, so
  the CPLI fix is inert on them). `tests/guards/test_egress.py` unaffected (no new dependency).
- **Deferred (separate PRs):** MS Project *saved* filter/group/highlight definitions (MPXJ's MSPDI
  writer drops them — they need a Java-side export first); the Groups & Filters A–Z + highlighting UX;
  the Gantt click-to-highlight; and F3a/3b margin work.
