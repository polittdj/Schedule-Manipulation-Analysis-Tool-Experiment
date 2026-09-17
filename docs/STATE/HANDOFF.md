# Handoff — 2026-09-17 (c) (R-64 **CLOSED** (ADR-0505) — a zero-duration task carries its driving predecessor's wall instant; the row's "external link" was MS Project's unassigned-work placeholder and the day was lost at milestone **181**, fifteen links above 404; **R-66 CLOSED** with it — **v1.0.271**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`3db94b14`** (#694, R-59 / ADR-0504, **MERGED** 17:46Z; the squash is **TREE-IDENTICAL** to the reviewed PR head `7e9b74f1`, tree `3f9e5965…`, compared with `git rev-parse <sha>^{tree}`, and to this session's starting checkout). **`main`'s OWN runs for `3db94b14` are SETTLED — read to conclusion this session, not inherited: CI 1915 (`35254782501`) SUCCESS, all six jobs (`cui-guard` 17:46:59Z · `browser` 18:04:08Z · `floor` 18:12:51Z · `test (3.13)` 18:31:26Z · `test (3.11)` 18:33:52Z · `check` 18:33:58Z); installer-smoke 753 (`35254782608`) SUCCESS 17:51:32Z (read last session). Nothing about `3db94b14` is outstanding.** This unit ships on branch `claude/eager-rubin-otxlxk` (the designated branch, at the squash) as **draft PR [#695](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/695)** (the operator merges; never marked ready here; EIGHT checks — `installer/**` changed). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the battery and the gate are all this repo gets. Highest ADR **0505**. Version **1.0.271**. Schema 2.15.0, unchanged. QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-64 read: milestone 387 hangs on an external predecessor link (`PredecessorUID` −65535) the MSPDI
cannot resolve. The mechanism was REFUTED by the activity's own XML before a line changed** (the R-58
lesson, applied): 387's one `PredecessorLink` is UID 386 (`CrossProject` 0) in all five Hard_File
goldens; censused over the whole corpus — **11,979 links across the 15 goldens, 21,609 across the 29
intake `.mpp` files converted fresh — ZERO unresolvable endpoints, zero `CrossProject=1`, zero
`ExternalTask=1`, zero negative UIDs.** The only −65535 in Hard_File is a `ResourceUID`: MS Project's
unassigned-work placeholder, on 27 assignments, one of them on 387 itself (ADR-0278 named it in
July). The row read an assignment as a link.

**The arithmetic was right and the head was nine links higher.** Walking the engine's own network
upstream from 404 against the stored dates: the first disagreement is **milestone 181**, stored at
Tuesday 08-04 **08:00**, where its 16-hour crew (UID 178, 06:00–12:00 + 13:00–23:00) finished. The
project axis is integer working minutes of the project calendar, on which Monday 17:00 and Tuesday
08:00 are ONE minute; a project-axis milestone kept only the minute, and `_pred_finish_wall` handed
the crew successor 189 the minute's end-of-day rendering, Monday 17:00 — an instant the crew works.
189 ran fifteen hours early, 187 finished nine hours short, nine crew-hours before 08-14 17:00 is
Friday morning on Standard, so 184 → 148 handed UID 384 a Friday instead of the stored Monday, and
385 → 386 → 387 → 400 → 399 → 401 → 402 → 403 → 404 inherited the working day. The same handoff sat
at 216 → 241, at **381 → 396 (R-66 — "a snapshot-specific defect upstream of leveling": it was this
class)** and at 387 → 400. Censused on the engine's own plans over the 44 files: **2,056** zero-duration
project-axis tasks, **230** driven by a crew-calendar activity, **111** rendered off their stored
instant, **22** crew successors started on a wrong one.

**Shipped — the carry, in `engine/cpm.py`'s forward pass.** Once the integer pass has placed a
zero-duration task (`ef == es`), `_carried_instant` collects the instants of every driver of its
early start — a lag-0 link's endpoint (a wall-path predecessor's wall, a carried milestone's
instant, a project-calendar activity's finish rendering), a raw SNET / FNET / MSO / MFO date, a manual
task's stored start, a recorded actual start — and the latest wins (MS Project's `max` over instants;
a milestone is neither snapped to its calendar nor rounded to the day: updated2's 387 is stored at
23:00, the 24-hour snapshot's 156 on a Sunday). The integer offsets are untouched, so every
project-calendar successor and every single-calendar file is byte-identical; nothing is carried
unless some driver's instant is one the axis LOST (a lagged driver leaves the rendering in charge).
The instant rides `TaskTiming.early_start_wall` / `early_finish_wall` (float stays the axis's, late
walls `None`), feeds the successor's start, a wall-path predecessor's free float and the network's
finish instant. **Two lines were deleted before they shipped:** a projection guard proved inert by
construction, and a stored-start FLOOR candidate that can never fire (the floor exists only for a
task without predecessors; a carried milestone has one).

| golden | finishes within a day | exact finishes | stored slack exact | Critical agreed | project finish |
| --- | --- | --- | --- | --- | --- |
| **Hard_File** | 103 → **110 of 110** | 40 → **110** | 39 → **101** of 110 | 108 → **110** | exact, unchanged |
| updated / updated2 / updated3 | 108 / 109 / 106 → **110 / 110 / 110** | 108 / 106 / 101 → 110 / 109 / 110 | 101 / 36 / 46, unmoved | 110 / 107 / 103 | exact |
| updated3_24hr (now its own oracle row) | 100 → 109 | 92 → 104 | 4 → **7** of 19 | 70 | 11-17 01:00 → **11-19 01:00, the stored, EXACT** |
| Project2 / Project5 / EVM1 / EVM2 / the Large Test Files and SSI copies | unmoved | unmoved (two milestones on the LTF family now sit ON their predecessor's finish instead of the lunch hour after it; EVM2 UID 25's START is now the stored one) | unmoved | unmoved | unchanged |

Across the 44 files (22,050 scheduled activities): **220 finishes toward the stored instant, 41 away,
21,789 unmoved**; exact 19,791 → 20,011; stored slack exact 10,666 → 10,800; Critical agreement
21,873 → 21,877. The 41 "away" are two named mechanisms, neither this rule's: seven are the two
lunch-hour milestones (UIDs 168 / 7107 and their copies — ADR-0322's contiguous-projection drift no
longer displayed on a milestone) and thirty-four are ONE chain in the non-golden
`Hard_File_updated_with_logic_reestablished` below UID 187, which MS Project starts out of sequence
(60 % complete, before its predecessor's stored finish); ADR-0391's floor keeps the logic start, and
the chain moved a day later WITH its now-exact predecessor.

## How it was verified

* **Red first, in a SEPARATE WORKTREE at `origin/main` (`3db94b14`), the package under test asserted
  by the `-p mutcheck` plugin:** 12 of the 17 new pins fail on the pristine engine by name; 5 are
  controls named as such in their docstrings (the lagged driver, the project-calendar-only
  milestone, the project-calendar successor, the two gating cases that exist for the mutants). The
  stored-dates oracle's crews test and every raised floor are red there.
* **Two tests could not fail on the pristine tree and were rebuilt or rewritten, not kept:** the
  free-float pin measured on a CREW task's slack axis (the project calendar, on which both instants
  are one minute) — rebuilt on a TASK calendar, where the axis is the crew's; the zero-slack
  inference test's Hard_File witness (241 / 249 recomputing to 480 / 360) was this chain's artefact
  and now pins the engine's own zero beside the inferred stored zero; the chapter-01 Critical-basis
  test's "not pure logic" witness (the stored count differing from pure logic on Hard_File) moved
  to the progressed updated3 snapshot, where 7 of 110 flags still disagree — on the base snapshot
  the two bases now coincide, and that is pinned as the agreement it is. **A test that needs the
  engine to be wrong goes red when the engine is fixed.** `docs/PARITY-REPORT.md`'s stored-dates
  table re-measured.
* **Mutation battery: 18 cuts on a shadow copy of `src/`** (checksums verified; control 62 passed):
  M01 the carry never stored → 18 red · M02 / M03 the predecessor finish / start ignores it → 12 / 1
  · M04 the "lost" guard dropped → 4 red + 15 errors · M05 a lagged driver carries → 1 · M06 "lost"
  ignores a carried predecessor → 4 · M07 the link roles swapped → 18 · M08 / M09 / M10 the
  constraint / manual-pin / recorded-start candidate dropped → 1 / 1 / 1 · M11 the earliest instant
  wins → 7 · M12 / M13 the two gating conditions dropped → 1 / 1 · M14 / M15 the instant not exposed
  → 10 / 7 · M16 / M17 a successor's start / finish ignores it → 1 / 1 · M18 the finish instant
  ignores it → 1. **18 / 18 red by name, no survivor.** The battery's FIRST run was DISCARDED: the
  oracle was re-pinned while it ran — its control went red and its rows carried two generations of
  parametrize ids. The instrument moved under the measurement (the QC-1 trap, paid for again); the
  second run began only after every test edit was final.
* **Rendered, not inspected — the real app (TestClient), pristine → this tree, 17 labels:** on
  Hard_File the `/analysis` page differs in 8 lines (the two float panels), `/api/analysis` in the
  float figures of 65 of 142 rows (64 `total_float_days`, 8 `free_float_days` — UID 189's 1.0 → 0.5
  is its stored 240 minutes) and the two float-band counts, `/api/driving` in 64 rows' float;
  **Project5 and Large_Test_File byte-identical on all three surfaces**, the eight session pages
  byte-identical.
* Statics green on **both** ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`,
  `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the wheel built AFTER the
  last format (the lockstep pin green, 68 passed).

**Gate on the final tree — MEASURED, in a separate worktree at the code commit `ae8ee1de` (never in the tree the docs were written in; `PYTHONPATH` on the worktree's `src/`, the `-p mutcheck` plugin asserting it): full suite 1 failed / 5,571 passed / 7 skipped in 41:39** (19:18–20:00Z, `-v`, no stall), **`-m parity` 171 passed / 0 failed in 6:42**. The ONE failure is `tests/test_state_docs.py::test_handoff_top_section_pins_the_current_pyproject_version`, red on the CODE commit's tree because it carries the 1.0.271 bump and not the rotated handoff (the same single failure as #694's first run, known and attributed — the bump and the pin ride ONE push); the docs commit carries the pin, its module is green on the final tree, and the final tree differs from the measured one under `docs/` only (`git diff ae8ee1de..HEAD -- . ':!docs'` is empty) — so the final tree reads **5,572 green / 0 failed / 7 skipped**. Both deltas ATTRIBUTED: **5,579 collected** = the previous unit's 5,561 + this unit's 17 (`test_milestone_carried_instant.py`) + 1 (the stored-dates oracle's fifth row, the 24-hour snapshot) by `--collect-only` on both trees; the previous 5,554 passed + 18 − 1 = 5,571; parity 170 + 1 = 171. The 7 skips are the documented set — the loopback-allowlist (urlparse) pair, the three INCIDENTAL_SVG axis cases, and the two `test_pptx_libreoffice_interop` skips that are correct in this container (no libreoffice-impress; CI installs it and treats a skip as a FAILURE, ADR-0498). A first full run on the WORKING tree (the tree under edit — a signal, never the measurement) read 5 failed / 5,559 passed / 7 skipped in 42:25: the four re-pinned modules, the CH01 witness and the pre-rebuild wheel lockstep, every one addressed before the code commit.

## Deliberately NOT done

**The backward carry (R-67)** — a milestone's LATE instant from a wall-path successor's late-start
need is the mirror rule, with its own witnesses (147's Saturday 13:00; on the 24-hour snapshot
156's stored late finish 11-02 09:00 vs the engine's 17:00, −4,740 vs −4,320) and its own row;
re-measured unchanged (94's slack 6,510 vs 6,360; 404's 9,420 vs 9,480 is its family) · **a
completed milestone's recorded instant without a crew driver** (a 14:24 milestone on a
single-calendar file still renders 15:24 — the two-ruler lunch hour; the carry needs an instant the
axis LOST, so single-calendar files stay byte-identical) · **a lagged driver's instant** (a lag lives
on the integer axis; the status quo rendering stands, pinned by a control) · **`late_*_wall` on a
carried milestone** (stay `None`: its late instant is still the axis's) · EVM2's UID 25 (a milestone
stored with a Finish one day after its Start; start now exact, finish untouched) · the
`logic_reestablished` file's out-of-sequence 187 and the `24Hour Calendar` intake file (23 of 126
exact, unmoved) — neither a golden, each its own row · **deleted, not kept:** the projection guard
(inert by construction) and the stored-floor candidate (cannot fire).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-63** (the converter
resolves `CurrentDate`, `MaxUnits`, `AvailableFrom/To` and the rates at CONVERSION time) · **R-62**
(every absent slack the writer dropped is a zero, completed tasks included) · **R-65** (the
1–28-minute gap granularity) · **R-67** (now with its mechanism confirmed as ADR-0505's backward
mirror — the natural next engine unit) · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 ·
R-22 · R-32 · R-39. The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
