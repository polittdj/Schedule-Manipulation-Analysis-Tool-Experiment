# Handoff — 2026-09-18 (c) (R-67 **CLOSED** (ADR-0510) — a zero-duration task carries its LATE instant from the need that binds it, the backward mirror of ADR-0505; a binding deadline is an instant too; a carried milestone's slack is measured between its instants; **QC-3** joins the standing working rules (ADR-0509) — **v1.0.275**, schema **2.16.0**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`bb5cef0d`** (#698, R-65 / ADR-0508, **MERGED** 2026-09-18 12:39Z by the operator; the squash TREE-IDENTICAL to the reviewed PR head `3ce38213`, tree `68467591…`, compared with `git rev-parse <sha>^{tree}` this session). **`main`'s OWN runs for `bb5cef0d` — read TO CONCLUSION this session, by their JOBS:** CI 1926 (`35345800081`): `cui-guard` 12:39:26Z · `browser` 12:56:58Z · `floor` 13:06:07Z · `test (3.13)` 13:23:42Z · `test (3.11)` 13:29:33Z · `check` 13:30:16Z — **SIX OF SIX GREEN**; installer-smoke 764 (`35345800104`): `linux` 12:39:48Z · `windows` 12:43:48Z. Nothing about `bb5cef0d` is outstanding. This unit ships on branch `claude/affectionate-heisenberg-e70kzd` (the designated branch, started on the squash) as a **draft PR** (its number and the gate's figures are recorded in the docs-only follow-up commit, the pattern every campaign PR used; the operator merges; never marked ready here; EIGHT checks — `installer/**` changed). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the batteries and the gate are all this repo gets. Highest ADR **0510**. Version **1.0.275**. Schema **2.16.0** (unchanged: no model change). QC-1 / QC-2 (ADR-0393) and **QC-3 (ADR-0509)** bind every session; all three are pinned by `tests/test_standing_rules.py` (ADR-0393, ADR-0509).

## What landed

**QC-3 — the plan is wrong until it survives your attempt to refute it.** The operator's
mid-session directive (2026-09-18: *after the research and the plan, assume it is all wrong,
double-check it and prove it correct before making changes; make this a rule*) is the third
standing working rule in `CLAUDE.md` (the section is now "The three non-negotiable working
rules"), with the same standing as QC-1 / QC-2. `tests/test_standing_rules.py` pins its heading,
twelve binding clauses scoped to its own section (its own `NO EXCEPTIONS` included — QC-1's copy
cannot vouch for it), the section's count and the comment-out guard; the attribution oracle now
decides each rule group by the ADR whose TITLE declares it (QC-1 and QC-2 together, ADR-0393; QC-3
alone, ADR-0509), and a doc line naming the guard must cite the ADR of every rule it names. Written
test-first (4 red by name / 3 controls), then the rule, then an 18-cut battery whose FIRST run
caught a survivor in the pin itself (dropping "refute" from the binding sentence stayed green — a
bullet's "refuted" matched the bare token, ADR-0393's own lesson paid for again); the clause became
the phrase and run 2 read **18 / 18 red by name**.

**R-67, the first unit run under it.** The plan was attacked on the pristine tree before the first
edit, with probes over the 15 goldens and 29 fresh conversions of the intake `.mpp` files, and two
of its four assumptions fell: the row's arithmetic held (the helpers fed the stored Saturday
reproduce 157's 07-31 23:00 / 15:00 / 2,760 and 94's 07-31 15:00 / 07-30 22:00 / 6,360 to the
minute), but **the mirror is not successor-gated** — on the 24-hour snapshot the chain head is
milestone 155's **DEADLINE** (11-05 17:00, no successor at all); the 24-hour crew 146 read the
minute's start-role rendering 11-06 08:00, fifteen crew hours late, and 145 → 144 → 9 → 36 → 156
inherited them (156: −4,320 for the stored −4,740, the row's own witness) — and **the row's one
milestone was a class**: 155 of 2,210 zero-duration tasks across the 44 files carry a stored
LateStart OUTSIDE the project calendar's working time, 1,740 on a block boundary. The same rule
fires twice on the base chain: milestone 181's late instant is crew 189's late start, 08-04
**21:00**; 178 / 179 / 180 read 08-05 08:00 for it (four crew hours late), and 178's need less its 72
elapsed hours is 147's Saturday.

**Shipped (`engine/cpm.py` only).** A fast-path zero-duration task whose binding need is an
instant the axis lost — a wall-path successor's late start less its elapsed leveling delay, a
carried milestone's instant, or (on a file with wall-path tasks) a binding deadline / date
constraint or the backward target — carries the EARLIEST such instant (`ms_late_wall`,
`_carried_late_instant`; both `TaskTiming.late_*_wall`), a wall-path predecessor retreats from it
(`_succ_ls_wall` / `_succ_lf_wall`), and a milestone whose EARLY instant is carried measures its
slack between its two instants on the project calendar (404: 9,420 → 9,480). A lagged BINDING link
leaves the rendering in charge; a non-binding successor contributes nothing and blocks nothing; a
milestone bound by project-calendar successors only is untouched; the carry itself moves no integer
minute; every single-calendar file is byte-identical. **Two candidate rules were measured on the
population before one was chosen** — the slack-between-instants form gains four exact slacks
(404 on the four Hard_File entries) and loses none.

| figure (pristine → this tree) | |
| --- | --- |
| late-finish INSTANT exact: Hard_File / updated / updated2 / updated3 / the 24-hour snapshot (of 110) | **78 → 94 · 83 → 87 · 27 → 37 · 30 → 45 · 3 → 15** |
| late-start instant exact, the same five | 73 → 86 · 79 → 83 · 20 → 39 · 29 → 48 · 1 → 15 |
| stored slack exact, the same five | **101 → 108** / 110 · 101 / 103 · 36 → 38 / 76 · 46 → 48 / 68 · **7 → 15** / 19 |
| the base chain 94 → 157 → 147 → 178 / 179 / 180 → 181 → 189, and 404 | every stored late date and slack (6,360 · 2,760 · 240 / 480 / 720 · 480 · 240 · 9,480) |
| the 24-hour chain 155 → 411 → 146 → 145 → 144 → 9 → 36 → 156 → 141 | every stored late date and slack (146: −19,200 · 156: −4,740 · 141: −4,800) |
| Project2 / Project5 · Large Test File / File2 | unmoved (late finishes 108 / 99 exact) · late finishes 918 → 919 / 824, milestone late starts +18 / +25 exact |
| 44 files, 22,105 activities: late finishes toward / away · late starts · slacks gained / lost | **268 / 17 · 260 / 17 · 50 / 0**; 26 files changed, **18 byte-identical on every timing field** |
| the 17 away | 15 on chains MS Project derives past a COMPLETED / STARTED successor the engine still runs through (**R-70**), 2 a completed milestone's record |
| `-m parity` | 197 → (the gate's figure, follow-up commit) |

## How it was verified

* **Red first on the pristine package** (a worktree at `bb5cef0d`, the `-p mutcheck` plugin
  asserting it): **10 of 14 synthetic pins red by name** (4 controls named as such), **7 oracle
  pins red by name** (the five Hard_File rows' late-finish and raised slack floors, the dated chain
  pin, Large_Test_File's late-finish floor); every synthetic expectation derived by hand from the
  two calendars before the first run, and the run agreed on every one.
* **Mutation battery 17 / 17 red by name** on fresh md5-verified shadow copies of the FINAL `src/`
  (control 84 green): M01 the carry never stored 15 · M02 / M03 the consumers ignore it 10 / 1 ·
  M04 "lost" dropped 2 · M05 a lagged binding link carries 1 · M06 a carried successor ignored 3 ·
  M07 the cap candidate dropped 4 · M08 the target dropped 4 · M09 `max` 3 · M10 the file gate
  dropped 1 · M11 the zero-duration condition dropped 17 · M12 the binding check dropped 2 · M13 FS
  reads the late finish 14 · M14 the walls not exposed 14 · M15 the slack stays the axis's 3 · M16
  the slack to the rendering 1 · M17 the delay twice 7. **Run 1 read 16 / 17 — M12 SURVIVED**: no test
  exercised a NON-binding successor; the code was right, two pins were missing, written, and the
  whole battery re-run.
* **Three tests moved, each for a stated reason** (ADR-0505's "late walls None" pin; a fast-path
  proxy on Jacked Up Schedule 1 whose UID 22 now carries an exact instant; the R-58 oracle's
  residual test rewritten as the agreement — a test whose witness was the engine's disagreement
  goes red when the engine is fixed).
* **The ten fast-path milestones whose integer late minute moved** were each traced to a wall-path
  (or carried) successor whose late start moved; six are UID 149, a completed milestone.
* Statics green on **both** ruff binaries (0.15.8 / 0.16.8), `ruff format`, `mypy --strict` (165
  files), `bandit` (exit 0), `node --check` per file; the wheel built AFTER the last `src/` edit;
  lockstep pins 68 passed. **A render diff was NOT run** (no consumer outside `engine/cpm.py` reads
  a late wall; the suite's web tests render every page).
* **The full gate is measured in a separate worktree at the code commit `da4f7e67`** (the docs are
  written in the working tree); its figures and `-m parity`'s follow in the docs-only follow-up
  commit. Expected red there by construction: the handoff's version pin and the two latest-ADR
  pins (the code commit carries ADR-0509 and the bump, not the rotated docs).

## Deliberately NOT done

**R-69, the block-end form** — the engine writes a block-exact late start at the END of the block
where MS Project writes the next block's START (178: 08-04 12:00 for 13:00; 147's carried instant
Saturday 12:00 for 13:00 — the same working minute); **742** late starts across the corpus, no slack
or late finish among them; NOT a one-line fix (the contiguous projection of the 13:00 form hands
every project-calendar predecessor the lunch hour as float) · **R-70, the backward pass through a
completed / started successor** — updated3's 188 is stored 12-12 17:00 while its completed successor
291's late start is 09-08; **67** incomplete activities across the corpus, the engine follows the
completed successor on 34 · a carried milestone's FREE float (the axis's; no witness) · the forward
analogue of the deadline case (a raw SNET-bound milestone with project-calendar predecessors and a
crew successor — **UNVERIFIED**, not censused) · late walls on single-calendar files (the gate) ·
`required_finish_offset`'s target rendering (unchanged behaviour) · a render diff.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-45** (T1, M —
Hard_File_updated3's BAC / BCWP 133,400 / 59,340 against Fuse's 121,800 / 53,715 and Fuse's ACWP
to-time-now; first step: read the Detailed Metric Report's per-activity cost columns under
`00_REFERENCE_INTAKE/` if the export carries them, else the operator owes a per-task export —
attack the plan first, QC-3) · **R-70** (T2, M — the repo carries the oracle: updated3's 188) ·
then R-03 · R-04 · R-09 · **R-69** · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; **R-68** waits on the
operator's reading (question (f)). The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
