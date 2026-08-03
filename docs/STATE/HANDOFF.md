# Handoff — 2026-08-03 (Phase 3 UI: the DD-line gap closes into ONE helper; ADR-0342; v1.0.158)

> ## STATUS (current) — **IN FLIGHT.** `DD_PENDING` is EMPTY; the DD line has one implementation.
> Branch `claude/dd-line-gap-closure-6u9op1`, restarted from `origin/main` at **`5413b6b`**
> (#523 was already merged when this session opened — checked FIRST, as the kickoff asked).
> ADR-0342, **v1.0.158**. Not yet pushed at the time of writing; drive the PR to green.
>
> ## What landed
> **ONE helper — `SFGantt.dataDateLine`** — in head-loaded `gantt.js`, beside `tableCaption`. The
> home was decided by LOAD ORDER before anything else (ADR-0340's lesson): `_LAYOUT` emits
> `chartframe.js` AFTER `</main>`, and most time-axis charts are parse-time body scripts, so a
> `SFChartFrame` helper would be `undefined` when they draw. **A test pins the layout's script
> order**, so the home cannot outlive its justification. Colour/type come from `.ch-dd` in
> `base.css`: `--bad` (red — there is no `--danger`) and the SAME `--sf-fs-axis-title` token the
> captions read, replacing four hard-coded `"font-size": 10`.
>
> The four hand-rolled copies are **retired** (`cei`, `curves`, `drift`, `scurve`). `drift`'s legend
> note ("grey dotted") was corrected to match what is drawn; `scurve`'s appended date moved into the
> marker's `<title>`, where chartframe's shared hover call-out shows it.
>
> ## The finding: 6 of the 8 "pending" charts were never work
> Both reclassifications came from a RENDER, not from the bucket they sat in.
>
> * **`margin_dashboard` splits.** Rendered with deliberately irregular status dates (1wk, 1wk,
>   **15wk**), the burn-down spaced all four versions **EVENLY** — the 15-week jump got the same
>   pixel width as the 1-week gaps and two ticks both read "2026-03". It is one slot per loaded
>   version: `margin.js`'s categorical axis wearing a date's name. Caption now reads **"Schedule
>   version (status date)"**; moved to `VERSION_AXIS`. Its SIBLING erosion chart is the opposite —
>   `x(t)` linear in ms, domain EXTENDED to the projected zero-margin date — so the data date is
>   the measured/projected boundary. It kept its entry and now draws the marker.
> * **The five SRA "Finish date" sites are a new `OUTCOME_AXIS` family.** Measured on `project2_5`:
>   status date **2026-08-27**, `/api/sra` CDF domain **2028-01-21 → 2028-01-28** — the data date is
>   ~17 months LEFT of a 7-day, index-spaced window. Clamping to the edge would assert the data date
>   IS the earliest simulated finish (Law 2). The tell was already in the tree: `sra_jcl.js`'s
>   SIBLING cost axis was already excluded, and it is the same joint distribution with the other
>   variable on x.
>
> **Only `resources.js` was genuinely pending.** Its buckets are equal-length calendar periods, so
> the marker has a real position. The bucket KEY is computed server-side by the engine's own
> `bucket_key` (renamed from `_bucket_key`; two internal callers) rather than re-deriving ISO week
> numbering in JS. Right edge of the data-date bucket; a data date outside the span draws NOTHING.
>
> ## Buckets (all derived) and the detector change
> `TIME_AXIS` **6** · `VERSION_AXIS` **10** · `OUTCOME_AXIS` **5** · `NOT_TIME_AXIS` **6** ·
> `OPTS_NOT_LITERAL` **1** · `DD_PENDING` **empty**. The detector moved with the code: anchored on
> the CALL (there is one implementation now), counted **PER MODULE against that module's time-axis
> chart count** — `margin_dashboard` is exactly why a module-level "has a marker anywhere" flag
> would have been wrong.
>
> ## Verification — 3 reverts on 3 different gates
> | revert | result |
> | --- | --- |
> | neuter the **shared** helper | **all 4** render tests fail — and **34 ledger tests still PASS** |
> | remove **one** caller (`resources.js`) | **exactly 1** fails, other 3 pass — they DISCRIMINATE |
> | `.ch-dd line` `--bad` → `--accent` (CSS only) | **4** fail, incl. the ledger's design-system test |
>
> The first is the important one *because of what passed*: a source census cannot catch a broken
> helper, so `test_dd_line_render.py` is not redundant with the ledger. The second is the proof
> ADR-0340's lesson demanded — N/N failing on a shared revert is also what one test run N times
> looks like.
>
> ## Next
> Phase 3 UI's DoD ledgers are now closed in all three (captions SVG + DOM, DD line). Behind:
> **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering half —
> "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5** monolith split
> 2–3 (`app.py` ~21k lines) · **Phase 6** docs/operator queue. OR-04 stays with the operator.
> Carried UI gap (measured, NOT fixed): `/briefing`, `/path` and `/compare` render a bare takeaway
> h1 with NO `page-lede`, while `/evm`, `/scurve`, `/margin`, `/groups`, `/integrity` carry one.
>
> ## Carried forward, unchanged
> **Known intermittent: the `/analysis` focus→tip family** — alternates run to run, re-verified
> pre-existing on `origin/main`'s own statics, and it has NEVER failed on CI. Do NOT chase.
> `pgrep -f <pat>` self-matches exactly like `pkill -f`. pytest stdout to a FILE is block-buffered.
> `cd` in a Bash call persists across calls — use absolute paths.
>
> **New this session:** a host list guessed from the ledger's `(module, line)` keys **under-reported
> by two** — `curves.js` has ONE `axisTitles` call site and renders THREE charts through it. Source
> call sites and rendered charts are different populations; PROBE the page for the second one.
> Also: `pytest --timeout=` is not installed here, and the usage error exited **0** through a
> `| tail` pipeline — check for the summary line, never the status.
>
> **A MATCHING COUNT IS NOT AN IDENTIFICATION.** The suite showed 6 failures right after I fixed 6
> test files, and I wrote that they were mine. **4 of the 6 were `tests/installer/`** — the
> embedded-wheel lockstep checks, failing because the wheel had not been rebuilt after the static
> assets and version changed. Identify by NAME: strip the `[ nn%]` suffixes from `-q` progress
> output, take the indices of `F`/`E`, and read those lines out of `pytest --collect-only -q`.
> Works mid-run, no waiting for the summary. **The installer suite fails by design until the wheel
> is rebuilt — build it BEFORE the final gate run, not after.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
