# Handoff — 2026-08-28 (operator evidence re-aimed WP0: A-row refuted for their machine; the REAL live defect was long-span scale — stale reflow column, no unit promotion, 38-page opening; ADR-0441, v1.0.223)

> ## STATUS (current) — **WP0-addendum COMPLETE on branch `claude/polaris2-full-tool-audit-948whg` (PR #615 with WP0/ADR-0440 was squash-merged @ `2fbde95e`; this addendum is the NEXT PR). The campaign runs under QC-1/QC-2 — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0441**; version **1.0.223** (shipped code: `static/path.js`, `static/timescale.js`);
> wheel + nine installers rebuilt in lockstep. Ledger: **docs/STATE/AUDIT-2026-08-27.md**
> Phase-0 addendum (verdict flips S1–S5). Gate numbers: SESSION-LOG 2026-08-28 entry, recorded
> AFTER the runs (QC-1).
>
> ## The operator ANSWERED the three-line ask — and the answer flipped the chase
> Their `sf.timescale.v1` is a byte-clean DEFAULT config; console clean. **ADR-0440's A-row is
> REFUTED for their machine** (the sanitizer stands as hardening). Their screenshots relocated
> the defect to the axis no probe had exercised: **SCALE** — a 12.3-year, 2,301-activity IPMR.
> Reproduced on a synthetic 2,280-task look-alike and fixed (ADR-0441), all red-first:
> **S1** `reflow()` left the timeline COLUMN at its attach-time width (SFColResize sizes the
> `.g-head` th only in `render()`): after Fit, 1,918 bars painted in a 969px track inside a
> **40,104px column**, pane scrolled 24,206px into dead space — "controls do nothing" +
> "renders wrong" in one mechanism; a fresh Trace full-renders and looks fine, which is exactly
> what the operator saw. Fixed: reflow re-pins the th to the axis. **S2** no unit promotion:
> fitted months = 165 bands / 0 labeled / **5.9px** (their picket fence; "should be showing
> Years, Quarters, and Months"). Fixed: density adaptation in timescale.js (`MIN_BAND_PX=14`,
> render-only, promotes months→quarters→…; adjacent-equal tiers drop — the MS Project
> zoomed-out stack; gridlines follow; DOM 427,795→176,829 nodes). **S3** whole-schedule opened
> at slider default: a ~38-page track with ~0 marks visible. Fixed: opens FITTED above 16 pages
> (first try 3× broke ADR-0438's measured seat contract on a 7.5-page schedule —
> `test_path_whole_schedule_browser` caught it; threshold re-anchored with 2× headroom both
> sides). **S4** slider input froze 5,692 ms/event × dozens per drag → debounced to one
> trailing rebuild (0 ms in-handler). **S5** one-shot rebuild at 2,280 rows: 1,417 ms —
> CONFIRMED-DEFERRED (M, windowed paintRows) in the ledger.
>
> ## New instruments
> `tests/web/test_long_span_gantt_browser.py` (5 tests; 4 observed RED pre-fix by name + the
> months-return PASS-side pin) · fixture `TP5_LongSpan_Synthetic.xml` (121 tasks, 2017–2029 —
> the SPAN is the payload; provenance-pinned in `test_fixture_provenance.py`). Five-mutation
> battery red by name (incl. over-promotion → the PASS-side pin fired — proof it has teeth).
>
> ## Traps paid for THIS session — check by name
> **A threshold near measured operator-approved behavior is a regression** — 3× whole-fit
> flipped a 7.5-page schedule the seat contract was measured on; anchor thresholds on the
> pathological case with headroom, and let the neighbour suite veto · **a probe that counts
> visible marks must scroll the grid into view first** — at 2,280 rows the KPI section fills
> the first viewport and bars_visible=0 is a layout fact, not a defect · **rect width ≠
> on-screen**: after Fit everything was painted and NOTHING was visible (track left −24,205px)
> — always measure POSITION too · **a restore script must assert what the mutation actually
> removed** (the comment stayed; the assert aborted the restore silently).
>
> ## Operator-facing state
> The upgrade instructions sent 2026-08-28 point at the installer on `main`; after THIS addendum
> merges they should re-download once more (v1.0.223) — their long-span pages then open fitted
> with a legible header. /evolution at their scale is still unprobed (their session loads ONE
> file; it needs ≥2 versions) — revisit on their next multi-version load, do not chase now.
>
> ## Next — unchanged campaign queue
> **WP1** full M1 census (+ the S5 windowed-paintRows deferral now queued there, priced M) →
> WP2 → WP3 → WP4 (incl. the 08-26 `startup_failure` root-cause) → WP5 (BOTH folder builds) →
> WP6 ledger highs → WP7 thin dims → WP8 report. Do-not-fix-blind rows unchanged.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
