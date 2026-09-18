# Handoff — 2026-09-18 (R-62 **CLOSED** (ADR-0507) — every absent `TotalSlack` the MPXJ writer dropped is a zero, completed activities included: the writer's rule is class-blind, MS Project's own stored slack pair is (0, 0) on every finished activity in the corpus, and float erosion — the one metric that scored finished work — scores incomplete activities only — **v1.0.273**, schema **2.16.0**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`b7c76ece`** (#696, R-63 / ADR-0506, **MERGED** 2026-09-17 23:21Z by the operator; the squash TREE-IDENTICAL to the reviewed PR head `298f660b`). **`main`'s OWN runs for `b7c76ece` — read TO CONCLUSION this session, by their JOBS (the run object's `updated_at` sits at creation):** CI 1920 (`35286496419`): `cui-guard` 23:22:13Z · `browser` 23:39:21Z · `floor` 23:47:23Z · `test (3.13)` 00:04:42Z · `test (3.11)` 00:10:22Z · `check` 00:10:27Z — **SIX OF SIX GREEN** (the `check` job is listed only once its `needs` complete: five jobs, then six); installer-smoke 758 (`35286496424`): `linux` 23:22:37Z · `windows` 23:26:29Z. Nothing about `b7c76ece` is outstanding. This unit ships on branch `claude/lucid-brown-hpmst7` (the designated branch, restarted on the squash with `--prune` + `remote set-head` + `checkout -B`) as a **draft PR** ([#697](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/697); the operator merges; never marked ready here; EIGHT checks — `installer/**` changed). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the battery and the gate are all this repo gets. Highest ADR **0507**. Version **1.0.273**. Schema **2.16.0** (unchanged: `stored_total_float_minutes` already exists and round-trips). QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-62 read: every absent `TotalSlack` the MPXJ writer dropped is a zero, completed tasks included
(the ADR-0490 probe: 786 zeros on Large Test File2, "634 of them completed"); the importer infers
only the `Critical` ones, so the Data Explorer's `Total Slack (d)` reads `—` where MS Project reads
`0d`. First step: widen the inference; census every metric that reads a completed task's slack
first ("today none does").** Both inherited statements were measured first and both were wrong:
the file's 786 zeros are **724 completed + 62 Critical** (the 634 left out 90 completed milestones),
and **one metric does read finished work — float erosion by WBS** — reading, for it, the ENGINE's
recomputed float (the file's zero having been dropped), which painted four WBS groups of the two
24-hour Hard_File snapshots RED on completed work alone.

**The mechanism, at the bytecode.** `printDurationInIntegerTenthsOfMinutes` returns null for a
null duration AND for one valued `0.0` — the writer drops every zero, class-blind. MPXJ's Total
Slack is a CALCULATED field: `FieldMap14` maps the file's `START_SLACK` / `FINISH_SLACK` and never
a total (the cache is null on all 17,402 task rows of the 29 intake `.mpp` files, read
cached-first), and `MicrosoftSlackCalculator` derives it — the smaller of the two for an unstarted
activity, the finish slack for a started one — Microsoft's own rule (*"the smaller value of the
Late Finish minus the Early Finish field, and the Late Start minus the Early Start field"*).
**Absent ⇔ zero on every task of every file: 7,095 = 7,095, NULL for none** — 5,466 completed,
583 Critical incomplete, 1,046 summaries, **0 other**; 7,030 store the pair (0, 0), the 65 others
one zero member; every finished activity in the corpus stores (0, 0), carries an `ActualFinish`,
and none carries the element. The 29 MSPDI fixtures agree (absent = 213 Critical + 3,178 completed
+ 0 other; no finished activity carries the element on any golden).

**Shipped.** The importer reads an absent slack as 0 whenever the FILE carries the element
anywhere (ADR-0490's guard; its Critical bound retired); float erosion scores incomplete
activities only and does not list a group with no remaining work (the panel says so); the
stored-dates oracle's slack census excludes finished work (a no-op on the old importer, load-bearing
now: Project2 would read tf_n 126 for 106, the engine's float equalling the file's zero for 2 of its
20 finished activities). The Data Explorer — the drill grid's addable column — reads `0` for
Hard_File_updated3's 42 finished activities where the pristine app read `—`, rendered through the
real app.

| figure (pristine → this tree) | |
| --- | --- |
| absent elements that are zeros, 29 `.mpp` files (17,402 tasks) | **7,095 of 7,095** (5,466 completed · 583 Critical · 1,046 summaries · 0 other) |
| finished activities storing (start, finish) = (0, 0) · carrying an `ActualFinish` · carrying the element | 5,466 · 5,466 · **0** |
| metric families moved by the inferred zeros (18 families × 15 goldens, sandboxed) | **1 — float erosion**, on every golden with finished work; 0 with its population fixed |
| float erosion, 15 goldens | 13 moved: **121 → 100 groups** (21 held finished work only), **red 35 → 27**, amber 49 → 41 — the two 24-hour snapshots' groups 4 / 5 read −9.6 / −7.9 wd RED on finished work and 14.6 / 93.3 wd green on the remaining |
| renders through the real app, 4 goldens × every GET route | 250 successful, **238 byte-identical**; the 12 movers: `/analysis` (the panel), `/download` (the Save carries the zeros), `/api/whoami` (the pid) |
| `-m parity` | **187 passed / 0 failed in 5:07** — unmoved |

## How it was verified

* **Red first, on the pristine package (a separate worktree at `b7c76ece`, `PYTHONPATH` on its
  `src/`, the `-p mutcheck` plugin asserting it): 11 failed by name / 114 passed** — the new
  module's four completed-activity pins, ADR-0490's three re-derived pins, `test_mspdi`'s task C,
  float erosion's two population pins, the Data Explorer's rendered column; the oracle census guard
  GREEN there (the no-op it claims); two "no element at all" controls green on both trees, labelled.
* **Mutation battery 9 / 9 red by name** on fresh shadow copies of the FINAL `src/` (control green,
  every cut checksum-verified, the plugin asserting the shadow on every row, every row with a
  verdict): M01 11 · M02 4 · M03 (ADR-0490's Critical guard restored) 10 · M04 10 · M05 3 · M06 (float
  erosion reads finished work again) 3 · M07 11 · M09 (`_days` blanks a zero) 1 · M10 (the panel
  sentence) 1 — plus the oracle guard's **instrument mutation**: `(108, 126)` vs `(106, 106)` and
  `(99, 126)` vs `(99, 99)`.
* Statics green on **both** ruff binaries, `ruff format`, `mypy --strict` (165 files), `bandit`
  (exit 0), `node --check` per file; the wheel built AFTER the last format; lockstep pins 68 passed.

**Gate on the code commit `96e4a624` — MEASURED in a separate worktree (never in the tree the docs were written in; `PYTHONPATH` on the worktree's `src/`, the `-p mutcheck` plugin asserting it):** **full suite 5 failed / 5,613 passed / 7 skipped in 36:46** (00:04–00:41Z, `-v`, the package under test asserted by the plugin, no stall). The five failures are all attributable and none is the change's: the four installer lockstep pins (`test_embedded_wheel_decodes_byte_exact_with_static_assets[ps1 / sh / command]` and `test_embedded_wheel_is_in_lockstep_with_the_source_tree`) are red by construction in a worktree that carries `main`'s old installers beside the new `src/` — the final tree's rebuilt installers pass that module 68 / 68 — and `tests/test_state_docs.py::test_handoff_top_section_pins_the_current_pyproject_version` is red on the code commit's unrotated handoff and green on the final tree (the docs commit carries the pin); the final tree differs from the measured one under `docs/` and `installer/` only — so the final tree reads **5,618 green / 0 failed / 7 skipped** and **`-m parity` **187 passed / 0 failed in 5:07****. Attributed: **5,625 collected = 5,616 + 9** (the new module's 6 + float erosion's 2 + the drill's 1); the previous unit's 5,609 green + 9 = 5,618; parity **187 = 187** (no new parity-marked test).

## Deliberately NOT done

**The XER importer** (an absent `total_float_hr_cnt` stays `None` — P6's export semantics for
finished work have no witness here) · **the JSON Save** made from an MSPDI source before this
version carries `None` for finished work — re-import the source (ADR-0490's posture) · **a parity
fixture for the MSP filter evaluator on `Total Slack`** (none exists; the resolver now reads the 0
MPXJ's own `evaluate` reads) · **a row for MPXJ's started-task branch** (699 written elements are a
started activity's finish slack where "the smaller" would be its zero start slack — read verbatim,
and reproduced by the engine's own float on the stored-dates oracle; no row) · **letting the
inferred zeros into float erosion's old population** (measured: every group with a finished
activity reads min 0 and goes amber — a fabricated warning; the population was fixed instead).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-65** (the
1–28-minute gap granularity of the honoured leveling gaps) · **R-67** (the backward mirror of
ADR-0505's carried instant) · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 ·
R-32 · R-39; **R-68** waits on the operator's reading (question (f)). The design queue is 19
artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
