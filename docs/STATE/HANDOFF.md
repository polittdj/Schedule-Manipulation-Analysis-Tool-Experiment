# Handoff — 2026-08-03b (Phase 4 opens: the three UNSURE falsy-zero rows, settled by rendering; ADR-0343; v1.0.159)

> ## STATUS (current) — **IN FLIGHT.** ADR-0306's three carried UNSURE rows are CLOSED.
> Branch `claude/polaris-phase-4-engine-zpo69e`, restarted from `origin/main` at **`8fad93e`**
> (#524 was already merged when this session opened — checked FIRST, as the kickoff asked).
> ADR-**0343**, **v1.0.159**. Wheel + nine installers rebuilt at 1.0.159 BEFORE the final gate.
>
> ## What landed — Phase 4's first unit, and it needed a RENDER, not a read
> The 2026-07-29 falsy-zero sweep closed 4 BUG rows (ADR-0306) and left **3 UNSURE**, for one
> stated reason: *"I did not execute the rendered page."* That is the only thing that could settle
> them. Rendered — **all three fabricate.**
>
> * **`/cei` (rows 1-2).** `cei_planned`/`cei_finished` are `None` when the snapshot has no
>   comparable prior month; `or 0` fed that absence to an **unguarded** `_status_stack`. On two
>   undated versions the page said, in one viewport: takeaway *"**No month could be CEI-scored**"*,
>   KPI cards *"—"* for both fields, and a panel headed *"**Latest scored month**"* drawing
>   *"Finished 0 / Short of plan 0 / **0 planned in the month**"*.
> * **`/groups` (row 3).** `group_values` scans EVERY task, summaries included, but completion is
>   computed over `non_summary`. `or 1` supplied a denominator for a numerator that is also 0 →
>   `0%` beside a BEI cell already reading `—` for that same empty population.
>
> **One helper — `_stack_not_measured`** — a sibling of `_status_stack` reusing the SAME panel
> shell (one panel chrome, not two; the two-up grid does not reflow). `planned`/`finished` keep
> their `None`; the takeaway's guard gains conjuncts that cannot change its branch (`cei` is
> `None` whenever `planned` is absent OR zero) but let the checker see the precondition.
>
> ## The counts — RE-DERIVED, and the first one was wrong
> | fixture · field | rows | empty-population rows rendering `0%` | honest `0%` rows |
> | --- | --- | --- | --- |
> | Project5 · WBS | 145 | **19** | 99 |
> | Project5 · Activity Type | 2 | **1** (`Summary`, 19 activities) | 0 |
> | Project2 · WBS | 145 | **19** | 106 |
> | Project2 · Activity Type | 2 | **1** | 0 |
>
> The first count taken was **118** — every row whose cell read `0%`. Re-deriving the population
> per value cut it to 19. **A matching cell value is not an identification** (the same trap the
> prior session paid for, in a new costume).
>
> ## Verification — a render diff, then two independent reverts
> Rendered on both sides and diffed (launch nonce normalised): `/cei` on the **golden pair** is
> **byte-identical**; `/groups?breakdown=Critical` and `…=% Complete` are **byte-identical** (no
> empty-population value); WBS moved 19 cells and Activity Type 1, and nothing else.
>
> | revert | result |
> | --- | --- |
> | `/cei` caller → `or 0` + unconditional bar | **2** fail (both `/cei`-unscored); 9 pass, incl. the scored twin |
> | `/groups` caller → `or 1` | **6** fail (empty-population, both fixtures); the honest-zero twin PASSES |
>
> Neither revert fails the whole module — that is the point. `tests/web/test_absent_is_not_zero.py`
> (**11**) derives every expectation from `group_values`/`non_summary` at test time rather than
> transcribing it, asserts the whole-table invariant (a percentage appears **iff** the value has a
> non-summary activity behind it), and pairs each fabricating branch with its **true-positive
> twin** — the goldens' really-scored month still reports `3 of 3` / CEI `1.00`, and the 99/106
> genuinely-0% WBS rows still read `0%`.
>
> ## Next — Phase 4 continues
> Remaining in the queue: **CC-01's rendering half** — *"74 sites" is an approximate grep,
> **RE-DERIVE it** before touching anything* (ADR-0240 reserves this for a Fable 5 Max deep dive) ·
> **SRA-LEGACY** · **V3** (`msp_filters.py` hard-codes `"d": 480`; ADR-0310 reduced it from a
> product decision to a conformance fix, but it MOVES saved-filter populations — it needs its
> migration-report gate). Then **Phase 5** monolith split 2-3 (`app.py` is **21,333** lines after
> this change, `state.py` 1,479 — measured) and **Phase 6** docs/operator queue. OR-04 stays with
> the operator.
>
> **Recorded, measured, deliberately NOT fixed** (ADR-0343 §"Deliberately NOT done"): the
> breakdown's **"Activities" column still counts summary rows** — `len(uids)` straight from
> `group_values` — so the `Summary` row reads "19 activities" while its completion and BEI are both
> `—`. Fixing it MOVES a displayed population figure rather than removing a fabricated one.
> Carried UI gap (measured, NOT fixed): `/briefing`, `/path` and `/compare` render a bare takeaway
> h1 with NO `page-lede`, while `/evm`, `/scurve`, `/margin`, `/groups`, `/integrity` carry one.
>
> ## Carried forward, unchanged
> **Known intermittent: the `/analysis` focus→tip family** (`test_float_tip_dismiss` /
> `test_float_tip_scroll`) — adjudicated, pre-existing, has NEVER failed on CI. Do NOT chase.
> `pgrep -f <pat>` self-matches exactly like `pkill -f`. pytest stdout to a FILE is block-buffered
> (use `python -u`). `cd` in a Bash call persists across calls — use absolute paths.
> `pytest --timeout=` is NOT installed here and its usage error exits **0** through a `| tail`
> pipeline. `--bad` is the red token; `--danger` does not exist. Source call sites ≠ rendered
> charts. Never `git checkout <file>` to undo a temporary test mutation — `cp` from a scratchpad
> copy (used twice this session, for both reverts).
>
> **New this session:** the page carried the answer in its own KPI strip the whole time. Two of the
> three rows were a *self-contradiction inside one viewport* — takeaway and cards already correct,
> one panel disagreeing — which is what makes them findable by rendering and invisible to a grep.
> Also: `_stat_cards` emits **value THEN label**, so a regex reading forward from a label picks up
> the NEXT card's value; the first KPI read of this session was off by one and reported
> `Planned = 0` where the page actually said `—`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
