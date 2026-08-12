# Handoff — 2026-08-12 (d) (ADR-0108 closed: a recorded actual start is a scheduling floor; ADR-0391; v1.0.198)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-data-date-fix-065mz7`
> (this container's designated branch). It started AT `main` **b72f887** (#576 already
> squash-merged, no restart needed). **Shipped code changed** — version bumped **v1.0.197 →
> v1.0.198**; wheel + nine installers rebuilt (SCHEMA stays 2.11.0). Highest ADR now **ADR-0391**
> (re-fetched before numbering AND before committing).
>
> **BAND 1 item 001 of `docs/PLAN/DEFINITION-OF-DONE-V2.md` is CLOSED** — the one open item that
> made the tool report a number wrong in the direction that matters. It was **not** the data date.
>
> ## The mechanism was never the data date — it was an ignored ActualStart
> TP4 v5's UID 19 carries `ActualStart 2026-04-27`; the pure forward pass re-packed it at its logic
> start **2026-01-26** (91 days early) and dragged the successor chain — and the project finish —
> back with it. 65d late against 50d float → the finish moves **15 working days**, exactly
> 06-26 → **07-17**. `_actual_start_bounds` now floors a started task at its recorded start:
> `es = max(logic_es, offset(actual_start))`. **A stored-date READ, the third of the family with
> ADR-0034 and ADR-0309 — not the data-date INFERENCE ADR-0108 reverted twice**, and it needs no
> `Stop`/`Resume`, which the synthetic battery cannot express at all.
>
> ## The operator's challenge changed the session, and was right
> Mid-session directive: *don't touch cpm.py until you establish whether TP4 should be regenerated
> to carry Stop/Resume, or whether TEST-PROJECTS.md's "MSP truth" needs re-deriving — attempting a
> CPM change against a fixture that can't express the input is how the first two attempts died.*
> The first cut of the fix WAS circular and was reverted to pristine before measuring further:
> `tools/make_test_projects.py::_schedule()` does `t.start = st.started` — it pins started tasks at
> their actual dates and its docstring claims that is "exactly as MS Project would". Reproducing
> TP4 v5's stored 07-17 with an actual-start floor therefore proved nothing on its own.
>
> **Marker census settled the provenance** (now a committed guard): Project2/5 + EVM1/2 carry
> EarlyStart/EarlyFinish/LateStart/LateFinish/Critical on **every** task and Stop/Resume on 28/35/4/6;
> TP1/TP3/TP4 carry **ZERO** of all of them, no SaveVersion, no CreationDate. The battery is
> generator output, not an MS Project export.
>
> ## But the number was corroborated all along — by Fuse, in a doc nothing cross-referenced
> `docs/FUSE-VALIDATION.md` records the operator's **Acumen Fuse** run over all 14 test projects.
> Fuse's computed finish for TP4 v5 is **2026-07-17**. MS Project rescheduled the XML on import, the
> operator saved the `.mpp`, Fuse read it. So the generator and a licensed reference tool agree and
> **the engine was the outlier** — the 21-day understatement was real, not a fixture artifact. The
> actual doc defect was that TEST-PROJECTS.md's caveat and the old guard never pointed AT that Fuse
> run, so the committed XML read as if it were itself an MS Project oracle. Both now cross-reference it.
>
> ## Measured against the real oracles, not the generator
> **Fuse agreement 4/5 → 5/5** on TP4, and **TP1's −1-day gap closed too** (09-16 → **09-17**,
> Fuse's date). Both are now ASSERTED in `test_fuse_reference.py` instead of excused. TP3's −5d
> stays open. **No project finish moved on any genuine MSPDI golden** (Project2 2027-08-30 ·
> Project5 2028-01-25 · EVM1 2012-09-12 · EVM2 2012-10-02). Engine-vs-MSP `EarlyFinish`
> disagreements **132 → 117** with **ZERO** in the engine-LATER direction. Only 2 activities floor
> on each of Project2/5, 0 on EVM1/2 — a narrow change.
>
> ## The gzipped goldens: a 5x win, and an ACCEPTED regression named out loud
> A first sweep globbed only `*.xml` and MISSED the `.mspdi.xml.gz` goldens. Measured before/after
> against MSP's own `EarlyFinish`: **Large_Test_File 826 → 164** disagreements, understatement
> **813 → 138**, finish unchanged (−1d vs MSP) — the "724 completed tasks, median 1458 days early"
> defect the cpm docstring has carried for months. **Cost: `Hard_File_updated` +21d → +29d and
> `updated2` +20d → +35d** from MSP's stored finish. Accepted on measurement: an **incomplete-only**
> floor was tried and keeps every Fuse win but leaves Large_Test_File at **826 → 826** — the whole
> gain lives in the COMPLETED tasks. The Hard_File family was already +19..+42d off, the drift is in
> the SAFE (later) direction, and the cause is the named remaining half (start anchored, finish
> still `start + duration`, so completed work that ran SHORT overshoots).
> Four Hard_File pins moved and were each re-verified: the 188→187 counterfactual **+21 → +15 wd**
> (×3 sites) and the `/evolution` + `/volatility` byte-frozen payloads — `/driving-path`'s pair is
> UNCHANGED and is the control. `test_path_options` moved its ADR-0251 demonstrator UID 67 → 70:
> 67 stopped diverging *because* its started work is now anchored, and 33 Project5 / 39 Project2
> targets still diverge, so the contract holds. The test asserts BOTH.
>
> ## ADR-0108's own headline case is MISATTRIBUTED — recorded, not fixed
> EVM2's residual (tool 10-01/02 vs Acumen 10-04) is described there as an in-progress data-date
> problem. **All six divergent EVM2 activities are 0% complete with NO actuals at all.** The
> calendar carries a lunch break (08:00–12:00, 13:00–17:00) and the chain diverges at UID 23,
> duration `PT12H` — engine lands 12:00, MSP 17:00, and the half-day propagates. That is the
> sub-day / segmented-calendar class (**DoD item 050**), not the data-date class. Unexplained
> remainder named honestly: why MSP spans a 12-hour duration across three days is NOT yet known.
>
> ## The disclosure had to get its own channel
> `date_driven` feeds a CONCERN — "N scheduled dates are not supported by logic", course-of-action
> "tie these activities into the network". Routing floored actuals there would emit a **false
> manipulation signal on every progressed schedule** (724 activities on the reference file). New
> `CPMResult.actual_start_driven` carries it instead, pinned by a test.
>
> ## Verification
> **Mutation battery 7/7 caught, controls GREEN, md5-verified restores.** Engine: delete the floor
> (8 failures) · read `task.start` instead of `actual_start` (1) · merge into `date_driven` (2) ·
> drop the `> es` guard so it pins rather than floors (2). Provenance guard: battery file gains an
> `EarlyFinish` (1) · loses its `ActualStart` (1) · a real golden loses its computed schedule (1).
> `mypy --strict` clean over 149 files (it caught a real defect — `started` bound as both `int` and
> `datetime` in one scope) · `ruff check .` clean whole-tree · `ruff format --check` 976 files ·
> bandit exit 0 · battery 73/73 · installer 52/52 · `pytest -m parity` green · full suite green.
>
> **The `mpxj_ref()` shallow-clone trap FIRED for real this time.** The container clone was shallow;
> the pin resolved to **79865bc** instead of the true **42d92dc**. Caught by comparing against
> `origin/main`'s committed installers, fixed with `git fetch --unshallow` + rebuild. A second trap
> rode with it: `build_installers.py | head -3` SIGPIPE-killed the build after three files, leaving
> `.ps1` correct and `.sh`/`.command` stale — all nine pins are now verified identical.
> **DoD item 117 (a shallow-clone guard in the build) is no longer theoretical.**
>
> ## Next
> Band 1 is DONE (001 closed here; 002/003 are the SRA labelling items). Nearest real work:
> **EVM2's sub-day / segmented-calendar divergence** (DoD 050 — now precisely located at a `PT12H`
> duration on a lunch-break calendar) · completed-task actual **FINISH** anchoring (the remaining
> half of ADR-0391, named in the cpm docstring) · TP3's −5d Fuse gap · **DoD 117** shallow-clone
> guard in `build_installers.py`, now evidenced · SRA R-1/R-2 labelling.
> **Operator:** re-convert FX-03/04 + re-run Fuse · one Acumen run on the sub-day-negative-float
> schedule · license · branch-protection contexts · OR-04.
>
> ## Carried forward
> ADR-0353..0391 closed — do not re-open. NEW lessons: (1) **a fixture generated by a rule cannot
> validate that rule** — check provenance before treating any stored date as an oracle; (2) the
> corroborating oracle may already exist in a doc nothing cross-references (Fuse had the answer for
> months); (3) an ADR's *diagnosis* can be wrong even when its *observation* is right — ADR-0108 saw
> a real gap and misnamed its cause; (4) a new disclosure needs its own channel when an existing one
> carries a JUDGEMENT (`date_driven` accuses; actuals do not); (5) `| head -N` can SIGPIPE-kill a
> build mid-way and leave a partially-regenerated artifact set. Standing traps unchanged (instrument
> shown to FAIL first · marker matches RETURN TYPE · priced table is a snapshot · `ast` col_offset is
> BYTES · population AND pattern are part of a sweep's claim · route-only referrers never force a
> descent · the MPXJ pin drifts in a shallow clone **(fired)** · never MEASURE a tree a battery is
> mutating · never MUTATE an instrument a measurement is using · monkeypatch repoint is per CALL
> SITE · verbatim text is not verbatim behaviour (`__name__`) · `grep -c` exits 1 on zero · two
> ruffs on PATH, use `python -m ruff` · bare `pytest` does not prepend CWD · `git fetch origin`
> before taking an ADR number and again before committing). A number written mid-session is not a
> measurement (`wc` decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
