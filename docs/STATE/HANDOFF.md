# Handoff — 2026-09-03 (WP3 · M4 — the SRA grid driven for the first time: six silent defects found and fixed, ADR-0454, v1.0.232)

> ## STATUS (current) — **On branch `claude/new-session-mc0a58` (from `origin/main` @ `6fdc1ddf`, the #625 merge). WP0/WP1/WP2 + the operator batch (ADR-0447..0453) all MERGED; this session is WP3 — the LAST queued UI-map row (27). Draft PR opened at close (number + gate in SESSION-LOG). QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0454**; version **1.0.232**; wheel + nine installers rebuilt in lockstep as the LAST step. Campaign queue: **WP4** (route-coverage instrument + the 08-26 `startup_failure` root-cause) is next once this PR merges — branch fresh from `origin/main`.
>
> ## What WP3 found (full rows in `docs/STATE/AUDIT-2026-08-27.md`, "WP3 — M4")
> The grid's paste feature had been pinned for eleven months by `'"paste"' in js`. Driven in Chromium with a REAL clipboard (`navigator.clipboard.writeText` + Ctrl+V), Excel-shaped payloads, and two oracles (the status line + a grid digest carrying each input's live value), v1.0.231 did six silent things: **M4-01** Refresh / the post-run reload wiped unsaved edits · **M4-02** a blank was ignored and the old value came back ("Saved 0") — no way to clear from the grid · **M4-03** pasted junk vanished and a 7 was clamped to 5 without a word · **M4-04** the save confirmation was overwritten before it could be read · **M4-05** `e` in a number input (badInput, value `""`) queued as an edit · **M4-06** the page's own forms navigated away over pending edits with no prompt. All six CONFIRMED-FIXED (ADR-0454): the pending map survives a reload and guards unload; a blank CLEARS (factor only; a blanked range side re-derives from the ranking); the reply carries `rejected` + `clamped` by uid/field/value/reason and the grid reads them back (ADR-0313's rule, on the grid); the summary rides the reload; badInput is refused at the cell; a paste says what fell outside the cells.
>
> ## Verification, in the shape QC-1 wants
> Pre-fix run **7 red / 9 green** by name (the seventh red was the envelope oracle reading `title=` after `tooltips.js` moved it to `data-sf-hint` — the WP1 trap, fixed in the oracle) · route pins **4 red / 20 green** against the original route · mutation original-JS + fixed-route → **exactly the six JS-side drivers red, blank-clear green** · digest pinned stable across a reload and across two servers, sensitive to a typed value · whole modules, never `-k`; tree restored from scratchpad copies after every swap.
>
> ## Operator-facing state
> Re-download once; the banner must read **v1.0.232**. Still owed by the operator (ask, do not assume): (a) which version banner was behind the blank-header screenshot? (b) did the One-Pager `.pptx` open in PowerPoint? (c) on /analysis with both IPMR files: one row per tier, smooth scroll? (d) NEW — on the SRA grid: blank a Factor cell and Save (it should clear), paste a column with a header row (the header should be NAMED as rejected), press Refresh grid with an unsaved edit (it should survive).
>
> ## Traps paid for this session, by name
> `tooltips.js` moves `title=` to `data-sf-hint` at load — every NEW oracle reads either · a badInput number input reports `""` — once a blank CLEARS, an unparseable keystroke is a silent delete unless refused at the cell · a save whose pending map is empty never POSTs ("Nothing to save.") — a driver that waits for the request hangs 30 s · `/root/.local/bin/ruff` (0.15.8) shadows `/usr/local/bin/ruff` (0.16.5) — run the absolute path CI uses · the four route pins and the six JS drivers are proven by SEPARATE reverts (original route / original JS) — one "revert everything" battery cannot show the split · `expect_response` + a real clipboard: `Control+V` needs the `clipboard-read`/`clipboard-write` context permissions; `Shift+Insert` also works.
>
> ## Next — campaign queue
> **WP4** (committed route-coverage instrument, `SF_ROUTE_COVERAGE=1`, floor ≥139, + the 08-26 CI `startup_failure` root-cause; `installer-smoke.yml` has NO `workflow_dispatch`, a fix candidate) → **WP5** (BOTH folder-ask builds — the three 2026-08-21 folder-gesture facts govern) → **WP6** (ledger highs: CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02) → **WP7** (thin dims, `ai/txlog.py` first) → **WP8** (consolidated report + roadmap by testimony risk).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
