# Handoff — 2026-09-02 (b) (the operator's six-item batch, MEASURED then fixed: zoom-in demote ladder, bow-wave target pin, the Gantt DOM budget + /analysis windowing, field roles, /volatility in the Claude Design layout; ADR-0447..0451, v1.0.229)

> ## STATUS (current) — **On branch `claude/polaris-audit-campaign-shuau7` (from `origin/main` @ `9ce245d`, the #622 docs merge). WP0/WP1/WP2 + ADR-0444/0445/0446 MERGED; this session is the OPERATOR BATCH on top — six reports, each measured before believed. Draft PR opened at close (see SESSION-LOG for the number and the gate). QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0452**; version **1.0.230** (ADR-0452, the operator's follow-up on v1.0.229: three configured tiers survive View entire project — Years / Half Years / Quarters — and the promotion floor follows a one-glyph month label); wheel + nine installers rebuilt in lockstep as the LAST step. Campaign queue unchanged — **WP3 (M4, the SRA grid)** is next once this PR merges (branch fresh from `origin/main`).
>
> ## The six items — verdicts (full rows in `docs/STATE/AUDIT-2026-08-27.md`, "Operator batch")
> 1. **Header** — current tree renders three labeled, absolute tiers at 8 px/day and two at Fit; the operator's blank-header screenshot is the pre-v1.0.227 hijack signature (and its dark thead predates v1.0.197). **Ask for their version banner before anything else.** What WAS wrong: no demotion on zoom-in (907-px month bands at 30 px/day) — fixed, ADR-0447, MS-Project Months/Weeks/Days at day density.
> 2. **Bow wave** — the axis stopped at status+12 months; UID 152 finished +21 → no mark. Pinned target/tracked months, cap holds. ADR-0448.
> 3. **One-Pager** — present in source, wheel, all nine installers and the LIBRARY rail; the link is 160 px BELOW the rail scroller's fold at a 1152-px viewport. A discoverability/design question, logged, not changed blind.
> 4. **Performance** — server never the lag (0–0.9 s). /analysis: 1,801,557 DOM nodes (743 gridline + 80 holiday divs PER ROW), 41.6 s, 5 fps → shared-background painters + row windowing → 26,926 nodes, 4.7 s, 33 ms/frame. ADR-0449. Residue: the ~130 materialized rows' sticky cells (class-based freeze = next candidate, not done blind).
> 5. **Field roles** — WBS / Cost Account / Work Package mapped to any loaded field; the WBS pivots follow the WBS role, mapped roles are filter fields. Found on the way and fixed: /wbs + its JSON + export read the RAW schedule (ignored the session scope). ADR-0450.
> 6. **/volatility** — the design's five numbered panels, one cursor with version chips, cursor-cumulative KPI; the ten tiles verbatim inside; census 66/66, r11 contract preserved. ADR-0451. Four-theme screenshots NOT taken (UNVERIFIED per theme).
>
> 7. **Follow-up (ADR-0452, v1.0.230)** — on 1.0.229 /path at View entire project showed TWO tiers with three configured: the promoted Months collided with Quarters and ADR-0441's rule dropped the duplicate. Now a promote-collision pushes the upper tier coarser (Y / H / Q); `COARSER` routes quarters→halfyears; a one-glyph month label (J F M · 1..12, both already in the Label menu) lowers the promotion floor to its `fitPx` (8 / 11 px). Two tests, RED-first.
>
> ## Operator-facing state
> Re-download once; the banner must read **v1.0.230**. Then: (a) which version was the blank-header screenshot from? (b) did the One-Pager `.pptx` open in PowerPoint? (c) on /analysis with two files: does the timeline header band across on one row per tier, and does scrolling feel smooth?
>
> ## Traps paid for this session, by name
> a colour probe that forces layout costs ~100 ms per call on a 2,000-row DOM — cache by key for the page's life · a memo keyed on an object every rebuild recreates is not a memo — key by CONTENT · `nw` in scope in one function is not in scope in the next (a ReferenceError the 121-row fixture never reached; the operator-scale probe did) · a scroll probe's "(program)" self-time means the cost is native (layout/sticky), not script — window the rows, don't tune the JS · an injected test value can land on the summary row the pivot excludes · a `.dc.html` canvas is a template + component script, and its `support.js` needs unpkg (blocked) — execute the template, don't eyeball it · a class containing the word `panel` trips the r11 census regex · the ribbon-cursor chromium test flaked once (`427 > 427`) and passed 6/6 on rerun — a race, logged, not chased · re-baseline byte pins LAST, after the final JS edit.
>
> ## Next — campaign queue (unchanged)
> **WP3** (M4 SRA grid edit / paste-from-Excel / save round-trip) → **WP4** (route-coverage instrument + the 08-26 `startup_failure` root-cause) → **WP5** (BOTH folder builds) → **WP6** (ledger highs: CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02) → **WP7** (thin dims, `ai/txlog.py` first) → **WP8** (consolidated report + roadmap by testimony risk).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
