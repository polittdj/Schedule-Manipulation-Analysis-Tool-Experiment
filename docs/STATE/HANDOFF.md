# Handoff — 2026-07-27l (the caption was never the problem; ADR-0303; v1.0.109)

> ## STATUS (current) — ADR-0303 pushed on `claude/schedule-forensics-continue-gkju7l`. Version **1.0.109**. Highest ADR **ADR-0303**.
> **#451-#460 all merged.** The four-theme visual pass is green again — this time against a
> detector that can actually see the collisions it is looking for.
>
> - **THE DIAGNOSIS IN THE LAST HANDOFF WAS WRONG, and the operator's chosen fix was built on it.**
>   The two collisions the widened detector found were written down as *"the Y caption sits where
>   the top gridline's label already is"*, so the fix looked like a placement change: move the Y
>   captions above the plot. **Measured in a browser, both halves of that premise are false.**
>   On `/cei` the top gridline label `15` clears the caption by **13px**; the text it actually hits
>   is a **bar VALUE label** at attr `(51.9, 59.3)`. On `/trend` the colliding caption is the **X**
>   caption — no Y-placement rule touches it at all. **Eighth false premise in this line of work,
>   and this one was mine, not the patch spec's.**
> - **The placement change was implemented, harness-tested, MEASURED, and REVERTED.** An adaptive
>   "above when the band is free, inside when not" rule chose **inside on all four charted pages** —
>   every one already has text there (`curves`/`scurve` time-tier header, `cei`'s `data date`,
>   `trend_drill`'s tallest-bar value label) — so it changed nothing while making a caption's
>   position **depend on the data** (it would move between frames of an animated stepper). Moving
>   up unconditionally was worse still: on `/curves` it hit the month letters (11x6, 9x6px) and on
>   `/cei` it would trade a 14x6 collision for a **56x13** one against `data date`.
> - **ADR-0303 — placement stays fixed; the DATA LABEL yields.** Two one-line clamps, at the cause:
>   `cei.js` `ly = Math.max(y(v) - 3, padT + 22)` (bites only bars within ~9% of the locked max —
>   their label drops just inside the bar) and `trend_drill.js`
>   `vy = Math.min(padT + plotH - bh - 5, padT + plotH - 18)` (bites only bars under ~13px — a
>   zero-offender metric is the common case; those labels then line up above the axis).
> - **RESULT: 144 caption renders, 4 themes x 3 scales, ZERO problems, `KNOWN_COLLISIONS` EMPTY.**
>   Not "clean" in the earlier sense — the detector now compares each caption against every `<text>`
>   in its own svg, which is what it was blind to when it first reported clean.
> - **The reverted attempt is PINNED in `tests/web/js/axis_titles_harness.mjs`**: an svg that
>   already has text just above the plot must STILL get its caption at `T + 9`. "Put it above the
>   plot instead" is the change a future reader is most likely to re-propose.
> - **A DANGLING `ADR-0303` CITATION was deleted** from `test_axis_titles_visual.py` — it credited a
>   `/forecast` geometry fix that was **reverted**, on a page that is not even in that pass's
>   `PAGES`. Exactly the defect class ADR-0300 exists to stop; this ADR takes the freed number.
> - **⚠️ NEW BUILD TRAP, cost a full rebuild:** `python -m build --wheel` writes to `dist/`, but
>   `tools/installer/build_installers.py` defaults to **`dist/wheel/*.whl`** — it silently embedded
>   a stale 1.0.108 wheel and produced installers byte-identical to HEAD. **Always
>   `python -m build --wheel --outdir dist/wheel`.** (`tests/installer/test_installers.py:89` pins
>   the embedded version to `pyproject`, so the gate does catch it — but only after the fact.)
>   And still: **run the regeneration in the BACKGROUND** (120s foreground timeout truncates it).
> - **Version 1.0.108 -> 1.0.109**, wheel rebuilt, nine installers regenerated (ADR-0148 lockstep —
>   `chartframe.js` / `cei.js` / `trend_drill.js` are packaged), all three tiers verified at 1.0.109.
> - **NEXT: AXIS-TITLES batch 3** — `PENDING` unchanged at **7** (`drift`, `margin_dashboard`,
>   `sra`, `sra_jcl`, `sra_ssi`, `trend`, `volatility`), and they are the hard ones, mostly
>   **multi-chart modules needing per-chart captions, not one call**: `sra.js` (4 charts),
>   `volatility.js` (10 visuals, 7 plot rects), `trend.js` (1,183 lines, **5 chart functions** —
>   `lineChart`, `multiLineChart`, `varianceTrendChart`, `stackedBarChart`, `groupedBarChart` — so
>   five call sites), `margin_dashboard.js` (2 charts + a strip), `sra_jcl.js` / `sra_ssi.js`.
>   `sra` and `margin_dashboard` can use **`y2Label`** (ADR-0302). **`drift.js` was ATTEMPTED and
>   REVERTED — do not simply re-add the call** (see the long note on `PENDING` in
>   `tests/web/test_axis_titles.py`; its X caption collides with the rightmost forecast value).
>   **SEVENTH FALSE PREMISE, still standing:** `/api/trend` emits **no `unit` field**, so the spec's
>   `metric.label + " (" + metric.unit + ")"` mechanism **does not exist client-side** — every
>   DCMA-14 metric does carry a unit (`%`, `count`, `ratio`) but it is not plumbed to the client.
>   Plumbing it is the first task of batch 3, not a caption to invent.
>   **Derive every caption from the rendering code (ADR-0301) — the spec's table has been wrong for
>   6 of 8 modules checked.** Then **CRISPNESS 11px floor ONLY**. Then GUIDED-MODE (5) +
>   VOICE-DECISION (4), parked on the operator. Also open: monolith split phases 2-3; a DOM caption
>   mechanism for the 13 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp
>   probe UI (ADR-0293).
> - **⚠️ HARNESS TRAPS, all self-inflicted, all cost time:** never `wait_until="networkidle"` on
>   this app (`heartbeat.js` polls 3s, `sysmon.js` 2s — it never settles); never pipe a long run
>   through `| tail` (buffers to EOF, so progress prints vanish); **never `pkill -f <pattern>`**
>   where the pattern appears in your own command line (it kills the shell running it); and
>   **"themes only change colour" is FALSE** — apollo is `font-family:'IBM Plex Mono'`, so caption
>   geometry genuinely differs per theme and must be measured per theme.
> - **A page with no chart is not a missing caption** — `/resources` needs a resource picked and
>   `/margin` needs tasks named "margin", so with the golden fixtures both correctly render a
>   no-data note. Flagging that would send the next session chasing a bug that does not exist.
> - **DEPLOY NOTE (operator has no local clone):** download `installer/install-tier2.ps1` from the
>   GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   One file; it fetches + SHA-256-verifies the `.mpp` converter from a pinned immutable commit on
>   `main`. An existing converter is never destroyed — not by a re-run, a failed download, a
>   self-referential `SF_MPXJ_HOME`, a junction, or a symlink; and a drive root no longer aborts the
>   install. All executed on Windows in CI (ADR-0300). Offline: Code -> Download ZIP, run from
>   inside the extracted folder.




# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
