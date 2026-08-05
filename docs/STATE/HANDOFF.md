# Handoff — 2026-08-04 (CC-01's rendering half closed: one instant, two spellings; ADR-0348; v1.0.163)

> ## STATUS (current) — **MERGED, nothing in flight.** PR #535 squash-merged as `e9a48c9`.
> ADR-0348, **v1.0.163**. **All six checks green** on `2ee8fa5`: `test (3.11)` · `test (3.13)` ·
> `floor (declared minimum)` · `browser (measured-box proof)` · `windows` · `linux`.
> **CC-01 / external H2a is CLOSED.** The finding's own two headline numbers were both wrong, and
> re-deriving them — the one instruction this work carried — is what found the real defect. Wheel +
> nine installers rebuilt at **v1.0.163**. Full local suite: **3479 passed, 3 skipped**, the only
> real failure the expected wheel-lockstep (fixed by the rebuild) plus the named load-sensitive
> `/analysis` focus→tip family.
>
> ## THE CENSUS — "74 call sites" was never a count of call sites
> `grep -rn offset_to_datetime src/` returns **75** lines; minus the one `def`, **74**. That is a
> count of *non-definition mentions* — imports and docstrings included. An AST pass finds **53**
> genuine invocations in `src/` (37 more in `tests/`). It reconciles exactly, and it reproduces at
> the audit commit too, so the number was never a site count in the first place.
>
> ## THE REPORTED DEFECT WAS ALREADY CLOSED — and ADR-0312 manufactures its residual
> All 53 src sites pass `start = <schedule>.project_start` **and** `calendar = <schedule>.calendar`
> — no arbitrary datetime, no per-task calendar (the per-task-calendar hypothesis was tested and is
> **false**). So ADR-0312's importer precondition genuinely holds everywhere, and a non-working
> landing needs the `tod + per_day == **1440**` equality. Measured on all 14 committed schedules:
> every one is `480 + 480 = 960`; **zero** reach it. The files *named* `_24hr`/`_24h` carry a
> **480-minute project calendar** — their 24-hour character is per-task. But ADR-0312's own
> normalisation drives a continuous-operations file **onto** that boundary (24 h + 08:00 start →
> midnight → `0 + 1440`). The import fix manufactures the one input the residual still trips on.
>
> ## THE DEFECT THAT WAS ACTUALLY THERE — on the ordinary 8-hour corpus
> A day-multiple offset names **one instant with two spellings**: the *end* of working day `k-1`
> and the *start* of day `k`. `offset_to_datetime` always picks the first (`remainder == 0` →
> `intraday = per_day`). Right for a finish; **one working day early for a start**. Against MS
> Project's own stored dates, restricted to tasks where the engine already agrees on the *finish*
> so only spelling can differ: **Project5 1/67 → 67/67**, EVM1 4/11 → 11/11, Large_Test_File
> 135/897 → 787/897. Every Gantt bar was drawn **one day too wide** (a 1-day task spanned 2 days).
>
> ## THE ONE PLACE IT IS ARITHMETIC, NOT DISPLAY
> `_elapsed_finish_offset` builds an elapsed task's clock origin from that spelling. Reading a
> boundary start as the previous day's 16:00 moves the origin by the whole non-working gap:
> **8 of 18** (start-offset, duration) pairs returned a wrong offset, short by up to a full working
> day. Whole-1440 durations were right **by coincidence** — the spelling gap equals the non-working
> gap — which is why nothing caught it. A wrong *number* into successors/float/critical path, i.e.
> Law 2, not CC-01's bucket. **Unreachable on the corpus** (1 elapsed task in 14 files, 0 trip), so
> the fix moves no committed figure.
>
> ## THE NAIVE FIX WAS WRITTEN, MEASURED, AND REJECTED
> Spelling *every* start as a start inverts milestones: `ES == EF`, so start renders one working day
> **after** finish — **159 of 169** zero-duration tasks in Large_Test_File. The oracle settles it:
> MS Project spells an instantaneous event **end-of-day** (EVM1 **3/3** vs 0 for the start form;
> Large_Test_File 52 vs 16). So `span_start_datetime` carries the rule and zero-duration keeps the
> end-of-day form. Measuring beat reasoning, and it caught a regression that would have shipped.
>
> ## What landed
> * **`offset_to_start_datetime`** (start spelling; delegates away from the boundary) and
>   **`span_start_datetime`** (adds the zero-duration rule) in `engine/cpm.py`.
>   `offset_to_datetime` and every offset are **untouched** — ADR-0310 pre-rejected changing them,
>   and 29 finish-role sites depend on the end-of-day form.
> * **Six start-role usages migrated**: `_elapsed_finish_offset` (arithmetic),
>   `engine/resources.py` loading span, and four in `web/app.py` (two compare-Gantt bar builders,
>   the trace start, the basis-start fallback). The other 47 are finish-role or axis/bucket.
> * **Two new test modules (+29)**: `tests/engine/test_day_boundary_spelling.py` and
>   `tests/engine/test_day_boundary_corpus.py` — the latter carries the **oracle** tests and an
>   **AST census guard** that fails if any `offset_to_datetime` call in `src/` is handed a
>   start-role offset again, with `span_start_datetime`'s body the single *named* exemption and a
>   vacuity check that the detector fires on the shape it hunts.
>
> ## Verification
> * **Four mutations, each proved to fail the right tests** — start spelling reverted (6 fail,
>   both oracle tests among them), elapsed origin reverted (7), milestone rule removed (5,
>   including both inversion guards), one display site reverted (the census guard alone).
>   Every mutation asserted its anchor, re-read the file to confirm it changed, and the tree was
>   restored **byte-identical from a scratchpad copy** (md5 verified) — never `git checkout`.
> * The census guard **failed on its first run and was right**: it caught `span_start_datetime`'s
>   own sanctioned branch. Scoped to consumers by name rather than weakened.
>
> ## Deliberately NOT done
> * **The `== 1440` boundary is documented, not repaired.** No committed schedule reaches it, and
>   repairing it means deciding what "the end of Friday" reads as on a 24-hour Mon–Fri calendar —
>   a question with **no oracle in the corpus**. Recorded in ADR-0348 so the next
>   continuous-operations file meets a citation, not a surprise.
> * The 20 `OTHER`-role sites (axis ticks, SRA bins, forecast bounds) were classified and left.
>
> ## Next
> **Phase 4 continues:** **SRA-LEGACY** (`audit/SRA-ROOTCAUSE-20260730.md`) · **V3**
> (`engine/msp_filters.py` hard-codes `"d": 480` and discards the elapsed marker in regex group 2;
> ADR-0310 made it a conformance fix, but it MOVES saved-filter populations and needs its
> migration-report gate). Then **Phase 5** monolith split 2–3 (`app.py` ~21.3k lines, `state.py`
> 1,479) and **Phase 6** docs/operator queue.
> **Operator only:** license selection · branch-protection required contexts · intake re-upload ·
> proprietary-tool reruns (engine==golden → engine==Fuse) · OR-04.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — `test_float_tip_dismiss` failed again
> this session with its documented signature verbatim (`Page.wait_for_function` 4000 ms timeout)
> and passes in isolation; never red on CI. Do NOT chase. `/briefing`, `/path`, `/compare` still
> carry no `page-lede`; `/groups` "Activities" still counts summary rows (ADR-0343). The nine
> installers still do not install with `-c constraints/known-good.txt` (62 lockstep tests; own
> unit). **Run `ruff check .` — the WHOLE tree**, and run ruff as **`python -m ruff`** (a stale
> 0.15.8 shim at `/root/.local/bin/ruff` shadows the 0.16.1 `.[dev]` installs). Never
> `git checkout <file>` to undo a test mutation — `cp` from a scratchpad copy.
>
> **New this session:** *a finding is a hypothesis with a citation, not a measurement.* Both of
> CC-01's headline numbers were wrong, the mechanism it named was unreachable, and the defect that
> was really there — 98.5 % of comparable Project5 starts — was invisible to its framing. Re-running
> the citation, not the conclusion, is what found it.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
