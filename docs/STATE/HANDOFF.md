# Handoff — 2026-08-02g (Phase 3 UI: the DD-line population becomes a ledger; ADR-0341; v1.0.157)

> ## STATUS (current) — **IN FLIGHT.** ADR-0340 MERGED as `a2bfa87`; the DD-line ledger is built.
> **PR #521 (ADR-0340, v1.0.156) MERGED as `a2bfa87`** — all 6 checks were green; branch restarted
> from `origin/main` with `--prune`. `DOM_PENDING` is empty and AXIS-TITLES is closed in both media.
> This branch now carries **ADR-0341, v1.0.157**: `tests/web/test_dd_line_ledger.py` (**32 tests**),
> the DD-line counterpart to `test_axis_titles.py`. **No `src/` change** — the ledger makes the gap
> visible and un-driftable; closing it is the next unit.
>
> ## What the census found (all measured, none inherited)
> The population is **re-derived, never hand-listed**: every chart declares its own X axis in its
> `SFChartFrame.axisTitles` call, so the ledger is keyed by `(module, line)` and each entry is
> CHECKED against the xLabel justifying it. Keyed by CALL SITE because `sra_jcl.js` carries BOTH a
> time-axis chart (L136) and the COST axis (L189).
>
> * **12 exclusions, not the 3 in the brief.** The extra family is the **version axis** (`margin`,
>   `trend` ×5, `volatility` ×3): ordered by time but CATEGORICAL, one tick per loaded file, so a DD
>   line has no position on it — every version has its own data date.
> * **The collision that decides check ORDER:** `margin.js`'s xLabel is "Schedule version (data
>   date)" — it SAYS "data date" and must NOT carry a DD line. Version check runs BEFORE the date
>   check (the `ai/qa.py` identifier-before-derivation pattern).
> * **`DD_PENDING` = 8, and it is DERIVED**: `margin_dashboard` ×2, `resources`, `sra` ×2,
>   `sra_jcl` L136, `sra_ssi` ×2. Computed from the tree, so it cannot over- or under-state.
> * **`performance.js` L472** is the one call site whose xLabel is a VARIABLE — its own bucket,
>   reason pinned.
>
> ## THE finding: FOUR implementations that disagree with each other
> | module | stroke | dash | label |
> | --- | --- | --- | --- |
> | `cei` / `curves` | `BLUE` → `var(--accent)` | `6 5` | `"data date"` |
> | `drift` | `"var(--muted)"` | `2 3` | **none on the line** (legend note only) |
> | `scurve` | `"var(--muted)"` | `2 3` | `"data date " + status_date` |
>
> Two colours, two dash patterns, three labelling schemes. **Not one matches the spec** ("a RED
> vertical line labeled `DD` / `DATA DATE`"): none is red, every label is lowercase or absent, and
> each hard-codes `"font-size": 10` (the numeric-type-in-JS fork ADR-0298 removed from captions).
> Pinned as executable records, so closing any part FAILS the ledger and forces it updated in the
> same commit. With 8 charts pending the answer is **ONE helper**, not four more copies — and
> ADR-0340's lesson stands: WHERE it lives is a load-order question, not a filing one.
>
> ## CORRECTION to the previous handoff — my own grep was wrong
> The last handoff said "**4** time-axis charts have no data-date mention" and "there is NO shared
> helper … cei.js and curves.js each hand-roll". Both came from `grep -ci "data.date"`, which counts
> MENTIONS (comments, `statusDate` variables). **The real numbers are 8 pending and 4
> implementations.** A byte-exact detector then failed the OTHER way — matching `cei.js`'s style
> missed `drift` (no label) and `scurve` (date appended) and also said "two". The anchor that works
> is the `//` comment naming the block, deliberately NOT a style match, because the styles ARE the
> finding. **This is the third time this session a grep count posed as a census.**
>
> ## Verification — 3 reverts, each on a different gate
> | revert | result |
> | --- | --- |
> | remove `scurve.js`'s marker | **3 fail**, incl. the derived pending ledger |
> | `cei.js`'s `BLUE` → `var(--danger)` | implementations test fails — proves the ALIAS is resolved |
> | `histogram.js`'s xLabel → "Finish date" | its `NOT_TIME_AXIS` predicate fails |
>
> The third is the important one: the exclusion list cannot shelter a chart that really plots
> against time. Two slicing bugs also surfaced only by running — the first slice read `cei.js`'s
> DOCSTRING, and a fixed 700-char window over-ran into the next block (harmless for three modules;
> `drift.js` has no label, so the spill supplied a `textContent` and `font-size` from other code).
>
> ## Next
> **Close the DD-line gap**: one shared helper (colour/label/type from tokens, per the spec), then
> retire the four copies into it and work `DD_PENDING` down. Decide the helper's HOME by load order
> first. `margin_dashboard` deserves a judgment call before it is "fixed" — its X axis IS a status-
> date axis with one point per status date, so it may belong with the version family; RENDER it.
>
> Behind: **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
> half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5** monolith
> split 2–3 (`app.py` ~21k lines) · **Phase 6** docs/operator queue. OR-04 stays with the operator.
> Carried UI gap (measured, NOT fixed): `/briefing`, `/path` and `/compare` render a bare takeaway
> h1 with NO `page-lede`, while `/evm`, `/scurve`, `/margin`, `/groups`, `/integrity` carry one.
>
> ## Carried forward, unchanged
> **Known intermittent: the `/analysis` focus→tip family** — alternates run to run, re-verified
> pre-existing on `origin/main`'s own statics, and it has NEVER failed on CI. Do NOT chase.
> `pgrep -f <pat>` self-matches exactly like `pkill -f`. pytest stdout to a FILE is block-buffered.
> `cd` in a Bash call persists across calls — use absolute paths.
>
> **Standing rule:** do not put a test result in prose unless the number appeared in output you
> read that turn. **A grep count is not a census — derive it, then RUN it.**


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
