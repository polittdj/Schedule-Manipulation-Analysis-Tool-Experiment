# Handoff — 2026-08-06 (V3 closed: duration literals conform to the vendored MPXJ; ADR-0354; v1.0.169)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0354, **v1.0.169**.
> Second ADR-0240 Fable 5 Max item done the same day as the first: **V3 / external H4 is
> closed**. `msp_filters` duration literals now implement the vendored mpxj-16.2.0
> `Duration.convertUnits` **read from its own bytecode via javap** — elapsed units are
> wall-clock (ed 1440 · ew 10080 · emo 43200 · **ey 524160 = 364 d, 52x7**), ordinary units
> scale on the schedule's OWN properties (**week = MinutesPerWeek, year = MinutesPerWeek x 52**
> — two conformance defects BEYOND the audit's elapsed headline, invisible to it), `%`/`e%`
> pass through (MPXJ's switch default, mirrored), unknown units **fail closed** (the sidecar
> vocabulary is closed: criteria literals are `Duration.toString()`). `Calendar` gains
> `minutes_per_week`/`days_per_month` (MSPDI-read, Save-round-tripped; absent → MPXJ's 2400/20).
> **The gate the audit required is now defined**: `EVALUATOR_VERSION = 2`, v1's parser kept
> verbatim report-only behind a ContextVar, `selection_migration_delta` → the `/groups`
> Active-scope panel shows "now selects N (was M)" whenever a duration-literal filter's
> population moved. Prompt answers store RAW and coerce per schedule at `scope()` (a "3d"
> answer is 1,800 min on a 10-hour file). Wheel + nine installers at **v1.0.169**.
>
> ## MEASURED
> The audit's executed example inverted into a pin: `Duration > 2.0ed` on the 8-task 1..8-day
> population → **(7, 8)**, was (3..8); unknown unit → **()**, was 6 matches. **No committed
> artifact moves** — the corpus carries no views sidecar, and the ten pinned real filters use
> duration fields only field-to-field (version-invariant). Movement is disclosed, not silent,
> wherever a real duration-literal filter exists.
>
> ## VERIFICATION SHAPE
> Five mutations, each failing exactly its guard, each original-anchor-absent-checked, each
> restored from scratchpad copies: elapsed-day→480 · year→mpw x 48 · ContextVar reset dropped ·
> importer stamp dropped · per-schedule calendar→default. **The fifth fired only after its test
> gained a 1,500-minute discriminator task** — the first draft passed under the mutation
> (identity-case trap, twice in one day: ADR-0353's suite-wide version, then this single-test
> version). The writer-coverage introspection guard caught the Save-writer half of the
> round-trip on its own. Engine+importer+web 1,264 passed · parity 49 · full gate green.
>
> ## Next
> Last Fable 5 Max reserved item (ADR-0240): **the `tod + per_day == 1440` boundary residual**
> (ADR-0348; decision-shaped, no oracle in the corpus — bring the operator a concrete proposal
> for what "end of Friday" reads as on a 24-hour calendar; recon done: `offset_to_datetime`'s
> `remainder == 0` branch at cpm.py:326 x ADR-0312's midnight normalisation manufactures the
> input). Then the standing queue: twelve page families (`integrity` 402 first, each adding to
> `LAYER_ORDER` + `VIEW_MODULES` + the monkeypatch sweep over ALL bound names + the
> renderability pre-flight) · a driving-corridor fixture · the three `page-lede`-less pages ·
> `/groups` "Activities" counting summary rows (ADR-0343) · nine installers vs
> `-c constraints/known-good.txt` · Phase 6 docs. **Operator only:** license ·
> branch-protection contexts · intake re-upload · proprietary-tool reruns · OR-04.
>
> ## Carried forward
> SRA-LEGACY (ADR-0353) and V3 (ADR-0354) are CLOSED — do not re-open; EVM2's det date
> displaying stored 2012-10-04 is the anchoring absorbing ADR-0108's 2-wd residual into the
> display (deliberate). `%`/`e%` pass-through and the 364-day elapsed year are MPXJ's OWN
> bytecode behaviour — mirrored deliberately, do NOT "fix" toward intuition. XER still has no
> `resume` read and no saved-filter sidecar. The `/analysis` focus→tip family is load-sensitive
> — do NOT chase. `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP
> VIOLATION (0.110.2 floor). Run `ruff check .` — the WHOLE tree — as `python -m ruff`. Never
> `git checkout <file>` to undo a mutation — `cp` from a scratchpad copy. `grep -c` exits 1 on
> zero count — chain mutation-absence checks with `;`, never `&&`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
