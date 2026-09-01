# Handoff — 2026-09-01 (the operator's diagonal timeline header, ROOT-CAUSED: hud.css's tooltip anchor `[data-sf-hint]{position:relative}` was overriding every Gantt band, bar and milestone's `position:absolute` — since July; ADR-0445, v1.0.227)

> ## STATUS (current) — **On branch `claude/polaris2-audit-resume-3xg50n` (from `main` @ `c3e4cea0`, the ADR-0444 merge). WP0/WP1/WP2 MERGED; this is the SECOND operator-defect fix on top, and it is the one that actually answers their report. QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0445**; version **1.0.227** (shipped: `static/hud.css` one line · `static/colresize.js`
> `sizeGrip` DELETED · `static/app.css` one comment); full suite on the frozen tree **4601 passed / 5 skipped / 0 failed in 48:59**; wheel + nine
> installers rebuilt in lockstep. Campaign queue unchanged — **WP3 (M4, the SRA grid)** is next.
>
> ## What the operator saw, and what it was
> "The fix did not fix the problem" — after ADR-0444, `/path`'s header still showed year labels
> descending diagonally, one row lower and one year further right each, clipped after the third
> row. Reproduced this time — in all four themes, one file or two — by measuring what the earlier
> probes never did: the bands' RENDERED `y` and COMPUTED `position`. Every `.g-band`, `.gantt-bar`
> and `.g-ms` carries a `title=`; `tooltips.js` promotes it to `data-sf-hint`; `hud.css` anchors
> the callout with `[data-sf-hint]{position:relative}` — equal specificity to `.g-band`, later in
> the cascade, so it WON. 60 of 62 bands, 73 of 73 bars, 11 of 11 milestones were
> `position:relative` (the two survivors had empty labels — no title, no promotion). The engine's
> own cascade (`CSS.getMatchedStylesForNode`) named the rule. Relative bands are block flow: one per
> line, shifted by inline `left` — the staircase. Bars survived by luck (one child per track).
> **In the tree since 2026-07-11, never conditional on two files.**
>
> ## The fix — one line, zero specificity
> `:where([data-sf-hint]){position:relative}` in `hud.css`. Any explicit `position` rule now beats
> the anchor while static hosts (headings, buttons, hint-dots) keep it. Fails closed for the next
> positioned element that grows a tooltip; no enumeration of victim classes.
>
> ## The second layer — ADR-0442's UI-01 was this same hijack, misdiagnosed
> The fix turned WP1's drag-resize driver red. The grip (`.col-rsz`, `title=`) was the same
> victim; ADR-0442 measured it 7×0px "at the cell's static position" (= a relative empty div),
> blamed a Chromium table-cell quirk, and wrote `sizeGrip` — an inline `left` computed FOR a
> relative box. Once the grip was genuinely absolute that `left` over-constrained it onto the
> LEFT edge (`[1,0,7,59]`); stripping the inline styles measured `[47,0,7,58]` — CSS alone seats
> it. `sizeGrip` is DELETED; the driver now asserts absolute · flush-right · full-height ·
> reachable (mutation: `right: 47` by name). Pre-fix the grip sat at x=7, the wrong edge, and the
> WP1 assertion (drag widened the column) never noticed. **Observed, not fixed:** the sticky
> controls bar (`#pathControls`, z6) overlays the sticky header (z3/4) at the top scroll position
> — a cross-page z-order design question, logged.
>
> ## Why seven weeks of green tests never saw it — THE lesson
> Every header measurement ever taken read inline `style.left`/`width` or rendered WIDTH. Position
> mode changes `y` and only `y`; widths are byte-identical broken or fixed. ADR-0441's density
> work, ADR-0444's own test, the WP1 census zoom drivers — all structurally incapable of refuting
> the claim, all green on a diagonal header. ADR-0444 was a real defect, correctly fixed and
> honestly marked UNVERIFIED as the operator's; it was simply not this. **A positioning claim is
> measured by rendered `y` and computed `position`, never by inline styles or widths.**
>
> ## Proof
> Red-first BY NAME on the standard single-file fixture (`g-tier-yr: its 10 bands paint on 10
> different rows (tops [18, 36, 54, 72, 90]…)`). Mutation both ways: plain selector restored →
> staircase; anchor rule deleted → `206 of 215 tooltip hosts are position:static` (the second test
> proves the fix did not trade a broken header for broken tooltips). Tooltip/HUD/panel neighbours
> 147 passed. Census + timescale + windowing, and the full-suite number for the shipped tree, are in
> the SESSION-LOG entry — recorded AFTER the runs (QC-1).
>
> ## Operator-facing state
> Re-download once; the banner must read **v1.0.227**. The header will band across the track on
> one row per tier for the first time since July; `/sra`-style bar-plus-envelope tracks render the
> envelope on the bar again instead of under it. If the header is STILL wrong on v1.0.227, the
> three diagnostics from ADR-0444 still apply (version banner · `sf.timescale.v1` · the `.g-tier`
> dump) — but the measured mechanism is now closed, so that would be a NEW defect, not this one.
>
> ## Next — campaign queue (unchanged)
> **WP3** (M4 SRA grid edit / paste-from-Excel / save round-trip) → **WP4** (route-coverage
> instrument + the 08-26 `startup_failure` root-cause) → **WP5** (BOTH folder builds) → **WP6**
> (ledger highs: CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02) → **WP7** (thin dims,
> `ai/txlog.py` first) → **WP8** (consolidated report + roadmap by testimony risk).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
