# ADR-0257 — 2026-07-18 operator UX pass: launcher self-diagnosis, Gantt visibility, +/- zoom, alphabetical group dropdowns, automate-crash guard; large-dataset reliability role

## Status

Accepted. Operator session 2026-07-17/18. The operator reported a cluster of usability and
stability problems from a real run (five projects loaded, one large), asked for a set of concrete
UI fixes, a new performance/large-dataset audit **role**, and full controls validation, and said to
choose the order and proceed. This ADR records the fixes shipped, the role, and the precise deep
performance plan **recorded but deferred** to the next session (it is parity-/engine-sensitive and
benefits from the operator's still-owed PowerShell crash log + their large dataset).

## Operator's session notes (verbatim intent, preserved for planning)

- The **desktop shortcut no longer opens the program** (top priority — unblock opening first).
- With **five projects loaded incl. a large file the tool lagged horribly** — "took forever for
  anything to happen when you would select something."
- When trying to **"automate one of the pages" the tool crashed.** A PowerShell **session log** with
  "a bunch of weird stuff" was to be attached — **NOT yet received; still owed.** Fold it in next
  session.
- **Gantt bars are not visible** and you **cannot scroll right**; on initial load the **data-date
  line should sit ~1 inch to the right of the rightmost column of data**, on every Gantt.
- Dislikes the Gantt **scale slider** — wants a **+ / − pair**.
- Dislikes the **filters/groups selection** widget — wants **simple alphabetical drop-down menus**.
- Wants to **assume the role of a large-dataset performance/stability engineer** and **improve
  performance significantly** so the tool does not bog down or crash and is stable.
- Wants **every control on every page validated** and "100% sure they work as intended."

## Decisions / what shipped this session (all browser-verified with Playwright)

1. **Launcher is self-diagnosing (the shortcut fix).** Root cause is structural: the desktop icon
   runs `pythonw`, which discards stdout/stderr, so *any* pre-serve failure (a rebuilt/moved venv, a
   missing dependency, a half-applied edit) dies silently and the browser opens on a dead port. New
   `src/schedule_forensics/__main__.py` is a dependency-light guarded bootstrap that wraps the
   **import itself**, so even an import-time failure is caught and surfaced — full traceback to a
   real console, or a native **Windows message box** with a one-line repair recipe when windowless.
   Writes nothing to disk (startup is pre-schedule-load, so no CUI). Desktop shortcuts retargeted
   `-m schedule_forensics.launcher` → **`-m schedule_forensics`** (`Install-Desktop-Shortcut.ps1`,
   `Schedule Forensics.vbs`); `launcher.py`'s own `__main__` guards its runtime path; the `.bat`
   `>/dev/null` (invalid on Windows `cmd`) → `>nul`. Re-running the installer re-points a stale icon
   at the current interpreter (the usual real cause). The app itself builds + serves cleanly here, so
   the operator's failure is almost certainly environmental — the guard makes the next failure
   self-explaining. Tests: `tests/test_startup_bootstrap.py`, updated `tests/test_packaging.py`.

2. **Gantt bars visible + horizontal scroll (shared root-cause fix).** `colresize.js` forces
   `table-layout:fixed` but deliberately never sizes the timeline column (`.g-head`); under fixed
   layout an unsized column collapses to leftover space, so the inline-width track overflows a cell
   that cannot grow — bars clipped by `.g-track{overflow:hidden}` (invisible) and the table never
   exceeds the pane (no scroll). Fix sizes `.g-head` to its content width **fresh each render** (not
   stored — the dead-scroll-space bug the store guards against). Fixes every Gantt routed through
   colresize (analysis / path / sra grid / …). Verified: `#grid` scrollWidth 6290 vs clientWidth
   1118, 145 bars present.

3. **Initial view lands on the data date.** New `scrollToDataDate()` (app.js) sets the initial
   `scrollLeft` so the amber DD line sits ~1 inch (`ONE_INCH_PX = 96`) to the right of the frozen
   data columns (interpretation of "an inch to the right of the rightmost column of data"); buildAxis
   adds ~1 inch of right margin so the DD line/last bar is never flush. **Confirm the reading with
   the operator** (the alternative — DD line an inch from the right edge — is a one-line flip).

4. **Scale slider → − / + buttons.** `#vizZoom` becomes a hidden px/day carrier (so `pxPerDay()`,
   Fit, Timescale are untouched); `#zoomOut`/`#zoomIn` step it ×1.25 from the effective zoom. Verified
   scrollWidth grows/shrinks on +/−. (`test_visuals` still pins `id=vizZoom`.)

5. **Filters/groups → simple alphabetical dropdowns.** Field + breakdown menus sorted A–Z; the
   per-field checkbox popup (`SFChecklist`) replaced with a native alphabetical value `<select>`
   (single-value; the backend still accepts repeated `value{i}` OR for saved filters/URLs).
   `groups.js` now repopulates the value menu on field/version change. Verified in-browser.

6. **Automate-crash guard (stability slice of the perf work).** The Performance page "master stepper"
   used `setInterval(step, 1800)`, which fires regardless of whether the previous redraw of all 13
   SVG charts finished — on five loaded files incl. a big one the redraws pile up faster than the
   webview paints and it crashes. Replaced with a **`setTimeout`-chained** advance (schedule the next
   step only after the current render completes) that **pauses while the tab is hidden**. No engine
   numbers change. Verified play/stop toggles cleanly.

7. **New audit role (ADR-0240 protocol).** Added **"Performance & Scalability / Large-Dataset
   Reliability Engineer"** as a standing audit persona: owns how smoothly the tool ingests, analyzes,
   and renders many/large schedules without bogging down or crashing; drives the deep-perf plan below;
   re-validates every change against Law 2 (no computed number may move). Companion to the existing
   audit personas; the next ADR-0240 sweep runs it.

8. **Controls validation pass.** Playwright sweep of **all 32 main pages** with two schedules loaded:
   every page returns HTTP 200 with **zero pageerror / console.error**, and key/changed controls were
   exercised live (Gantt +/−/Fit, groups field→value dropdown + Apply, the Performance play/stop
   stepper). Exhaustive per-widget validation and the five-large-file stress test continue next
   session with the operator's dataset.

## Recorded, NOT done — deep performance plan for next session (the "lag")

Three-agent reconnaissance mapped the lag precisely (all fixes are caching/scheduling — **no computed
number changes**, parity must stay green; re-validate each):

- **P1 — cache nuked on every selection.** `SessionState._invalidate_scope` (`web/app.py:788`) clears
  *all* analyses/summaries/scoped caches on any filter/target/mode change (`set_filter` 803,
  `set_saved_filter` 817, `set_filter_mode` 824, `set_target` 842) → full recompute of every loaded
  version on the next render. Make it surgical / key the analysis cache by `(key, scope-signature)`.
  Verify highlight-mode and target changes never serve stale numbers.
- **P2 — full analysis when only CPM is needed.** `_solvable_versions` (`app.py:3046`) calls the
  monolithic `_compute_analysis` (`app.py:498`, runs CPM + audit + baseline + float-bands +
  completion + findings + narrative + `_activity_rows`) for every version just to read `.cpm`. Split
  so `.cpm`/each metric is obtainable lazily.
- **P3 — Performance page uncached.** `_performance_data` (`app.py:15796`) reruns ~10 engine passes
  per version on every `/performance` render; `work_to_go_census` (`performance_summary.py:132`) is
  O(months×tasks). Cache per (version, scope); bucket the census to O(tasks+months).
- **P4 — session `_lock` held across heavy compute** (`app.py:947`) serializes every request; compute
  outside the lock, store under it.
- **P5 — offload has no timeout** (`web/offload.py:90`); the OAT sweep is one CPM solve per task,
  unbounded (`app.py:5996`). Add a timeout/size cap.
- Add a real latency regression gate (the ADR-0249 harness explicitly excludes it).
- **Owed:** the operator's PowerShell crash log + a large dataset to reproduce and stress-test.

## Consequences

- Version **1.0.65 → 1.0.66**; wheel + 9 installers regenerated in lockstep.
- No engine/parity math touched; the perf work that *will* touch hot paths is deferred behind the new
  role's re-validation discipline rather than rushed.
- The DD-line landing and the single-value group dropdown are the two reasonable-default UI decisions
  to confirm with the operator; both are trivially adjustable.
