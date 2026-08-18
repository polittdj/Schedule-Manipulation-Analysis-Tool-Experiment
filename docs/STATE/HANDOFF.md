# Handoff — 2026-08-18 (b) (Ask-the-AI compared only the newest TWO of N loaded schedules; ADR-0424, v1.0.214)

> ## STATUS (current) — operator-reported defect CLOSED on `claude/multi-schedule-comparative-analysis-vmh5ei`.
> Highest ADR now **0424**. Shipped code DID change (`engine/pair_series.py` NEW,
> `ai/pair_facts.py` NEW, `ai/qa.py`, `web/app.py`), so **v1.0.213 -> 1.0.214** and the wheel +
> all nine installers were rebuilt (ADR-0148). SCHEMA 2.11.0 unchanged. Branch started clean from
> `origin/main` at ee576aa. **Ran entirely SOLO.** This session answered an OPERATOR REPORT, not
> the audit ledger — `docs/STATE/AUDIT-2026-08-16.md` is untouched and its queue is unchanged.
>
> ## 1. The report, and what it really was
> Operator: "In the schedule integrity page when there are more than two schedules loaded the tool
> only does a comparative analysis of the last two schedules when you Ask the AI a question … I
> want it to do a comparative analysis of each of the schedules starting at the earliest and
> working its way forward to the latest two at a time. This doesn't just apply to the Schedule
> Integrity page but all of the Ask the AI sections on every page."
> **Reproduced before touching anything.** A 4-version workbook with a duration cut in update 1 and
> another in update 2, newest pair identical: the fact sheet held **27 facts, ZERO with a
> manipulation signal**, neither cut activity named anywhere — and the only statement on the
> subject was *"No incomplete activity on the critical path had its duration shortened between
> v03.mpp and v04.mpp."* That is an **affirmative negative** scoped to 1 of 3 available
> comparisons, and it reads as a workbook verdict. A model answering "no pattern" from that
> evidence is answering **correctly**. Control: each early pair compared directly yields 1 finding
> + 3 forensics facts, so the detector was never broken — nothing ever asked it about those pairs.
> **The report named one page; the Ask panel is ONE shared component** (`chrome._ask_panel_html`,
> rendered by `_page` everywhere). `/integrity` passes no `ask_schedule`, so its panel defaults to
> "Workbook — all N versions" and hits `/api/ask`. The operator's "all of the Ask the AI sections"
> was literally right.
>
> ## 2. Why ADR-0392 had not already covered it
> ADR-0392 made the population a fact and added the S-curve + finish **series** across every
> version — those are *per-version readings*. Manipulation is a **DIFF** signal: it exists only
> between two snapshots, so covering it needs the PAIRS walked, not the versions read. The
> newest-two limit survived ADR-0392 in exactly the dimension `/integrity` exists for.
>
> ## 3. The fix (ADR-0424)
> **`engine/pair_series.py`** (new) walks oldest→newest, two at a time, running the full detector
> on EVERY adjacent pair; `recurrence` gives per signal type the steps fired, the longest UNBROKEN
> run, and the totals — the arithmetic behind "is this a pattern". **`ai/pair_facts.py`** (new)
> states it as a **pinned** `PAIRWISE COMPARISON SERIES` + **pinned**
> `MANIPULATION-SIGNAL RECURRENCE` + bounded per-step detail. Wired into `/api/ask` AND
> `/api/ask/{name}`. `manipulation_forensics_facts` stays the one-pair DEEP dive (its
> counterfactual re-solves per change) and now names which comparison it is, out of how many.
> Three design points each paid for by a measurement: detail facts are allocated **round-robin
> oldest-first** (a top-N-by-severity cut rebuilds the very bias being removed); activities are
> named **in the fact `text`**, because all three Ask prompt paths use `f.text` and NEVER
> `f.rendered()`, so a citation-only activity is invisible to the model; and truncation is stated.
> Cost measured: **31 pair-diffs = 1.1 s at 5,000 tasks** (36 ms/pair), reusing cached solves.
>
> ## 4. The trap this change walked into — and the count that could not see it
> The first working build put the sweep inside `build_workbook_fact_sheet`, which `/api/ask` calls
> with `_solvable_versions()` — the **target-truncated** population. The sweep runs
> `detect_manipulation`, and ADR-0371 already established a DIFF must never see that. Measured,
> Project2→Project5 with target 145: the truncated diff **fabricates a HIGH "13 activities deleted
> since the prior version"** the control does not report, and **loses** a real
> `MANIP_CONSTRAINT_ADDED` — while **total signals is 5 either way**, so a count-based check is
> blind to both. Fixed by giving `build_workbook_fact_sheet` `pair_schedules`/`pair_cpms` (the
> convention ADR-0371 already gave `build_briefing`).
>
> ## 5. I wrote the same defect into the fix, and the tests were green
> `_series_fact` derived the version count as `len(steps) + 1` — accidentally right in every case
> any fixture exercised, wrong exactly when a pair is uncomparable, where it rendered **"all 2
> loaded version(s) were compared … every update is here"** over a FOUR-version workbook. Same
> shape as the affirmative negative the ADR exists to remove. `PairwiseSeries` now carries
> `versions`, and the completeness sentence retracts itself. Found by **reading the emitted
> sentence**, not by a test — every test was green because every fixture had every pair comparable.
>
> ## Next
> **The audit ledger is where it was** — `docs/STATE/AUDIT-2026-08-16.md` is the queue. Untouched:
> **page modules A/B** and **docs/config/CI** (still never audited), the **AI figure-gate
> adversarial pass** (`_figure_roles`, `_classify_figures`'s `handled` ordering,
> `_MAX_GATED_FIGURES = 24`, `ai/derivation.py`; and annotate scoring against `model_evidence`
> while the analyst sees `relevant_facts`), and the **25-route adverse gap** (19 are `POST /sra/*`;
> `POST /sra/factor-table` is untouched by the whole suite). Remaining REPORTED rows:
> CPM-01..04 · MF-02/03/04/06..10 · MC-02..08 · IMP-02..06 · MAN-01..03 · REC-02 · JS-02..06 ·
> TST-02/03. **MF-05 stays do-not-fix-blind.** New adjacent finding, NOT fixed and reported
> instead: **the Ask prompt is built from `f.text` and never `f.rendered()`**, so citations reach
> neither the model nor the gate's prose — ADR-0424 works around it inside its own facts only; the
> general fix touches every Ask answer in all three modes and belongs with the figure-gate pass.
>
> ## Carried forward
> ADR-0353..0424 closed — do not re-open. NEW lessons: **an ORACLE CAN BE BLIND IN A WAY THE
> MUTATION EXPOSES ONLY IF YOU RUN IT** — two of this session's tests passed under the mutation
> they existed to catch (the pinning test used a no-overlap question, but the block sits directly
> behind the pinned facts and leads the ranked tail anyway; the population test probed the
> finding's TITLE, which the route's 12-fact cap trims). Both now carry a control asserted to MOVE
> · **`$PWD` is not a constant inside one shell call** — a probe that `cd`s into a worktree and
> then uses `$PWD` for the "live" comparison measures the worktree TWICE and reports the fix
> broken; only re-asserting `schedule_forensics.__file__` caught it · **a defect can hide behind a
> COMPLETE-LOOKING series** — ADR-0392 spanned every version and still left the diff dimension at
> N=2, because per-version readings and pairwise diffs are different shapes · **an affirmative
> negative is worse than silence**: "no duration was shortened between v03 and v04" scoped to 1 of
> 31 comparisons is read as a verdict. Standing traps unchanged (a count may be counting the
> symptom — here it was literally 5 vs 5 · compute a call-site list, never hand-maintain it · never
> measure a tree a battery is mutating · monkeypatch per CALL SITE · `python -m ruff` ·
> `ruff format` also formats python inside MARKDOWN · `| tail` masks exit codes · fetch before
> numbering AND committing). QC-1/QC-2 are ADR-0393.
>
> ## Gate at close
> Statics green whole-tree (ruff / ruff format / mypy strict / bandit exit 0 / node --check).
> Full suite **4299 passed / 5 skipped / 0 failed (26:30)** on the settled tree. The FIRST run was
> 4298 passed / 1 failed, and that failure was ADR-0148's embedded-wheel lockstep guard doing its
> job: the wheel had been built BEFORE the version-count defect was fixed in `ai/pair_facts.py` and
> `engine/pair_series.py`, so it reported both as "content drifted". Wheel + nine installers
> regenerated, then the clean run above. `origin/main` @ ee576aa is 4262, and 4262 + 37 newly
> collected tests = 4299 exactly. **Sequence the close as: last source edit -> statics -> wheel +
> installers -> full suite -> commit** (the wheel is a gate artifact and obeys the same
> "re-run after the LAST file change" rule).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
