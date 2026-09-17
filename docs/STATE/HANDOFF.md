# Handoff — 2026-09-17 (R-58 **CLOSED** (ADR-0503) — a task calendar meets a crew calendar on their **INTERSECTION**; the row's witness was **UID 94, not UID 14**, and the one activity in the corpus whose crew cuts into its calendar lands on MS Project's **five** stored values — **v1.0.269**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`80ae617e`** (#692, the docs-only record of #691's merge; before it **`2c549d8d`**, #691, R-57 / ADR-0502). **`main`'s OWN CI for `80ae617e` was read TO CONCLUSION this session, not inherited: run 1908 (`35175117266`) completed / SUCCESS, all SIX jobs** (`cui-guard` 02:37:38Z · `browser` 02:55:06Z, the R-52 interop gate run-and-NOT-skipped on `main` itself · `floor` 03:03:03Z · `test (3.13)` 03:07:16Z · `test (3.11)` 03:15:54Z · `check` 03:16:18Z). **No installer-smoke run exists for `80ae617e` and that absence is CORRECT** — verified against the `main` run list (its newest is 746 for `2c549d8d`, the head that rebuilt the installers), not assumed: #692's diff is three `docs/STATE/` files and the workflow is path-filtered. The PR head `b0b5f851` and the merge share tree `4c10140f…`. This unit ships on branch `claude/polaris-audit-r58-calendar-2gxhxw` as **draft PR the draft PR opened from this branch (its number is recorded in the follow-up docs-only commit)** (the operator merges; never marked ready here). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the battery and the gate are all this repo gets. Highest ADR **0503**. Version **1.0.269**. Schema 2.15.0, unchanged. QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-58 asked for a calendar-intersection helper behind the plan builder and named Hard_File UID 14
"on `Standard+Sat.` with the 16-hour crew" as the witness. The mechanism is MS Project's own and the
witness was WRONG — found by reading the XML before touching a leg.**

**UID 14 is on `24 Hours` (calendar 10) in all seven snapshots** — the one intersection ADR-0474
already modelled exactly (a 24-hour task calendar yields the crew's), which is why ADR-0491 found its
stored span reproduced to the minute. **The task on `Standard+Sat.` (calendar 12: 07:00-12:00,
12:30-19:00, 19:30-23:30, Mon–Sat) is UID 94**, an 8-hour FIXED_UNITS activity on the same 16-hour
crew (06:00-12:00 + 13:00-23:00, Mon–Fri). The row conflated the two.

**The population is ONE task.** Censused on the engine's own `_task_shape`: the 15 goldens carry
**301** tasks with an off-pattern task calendar and a WORK booking — **294** non-24-hour (293 of them
Large Test File activities under same-pattern crews that restrict nothing) and UID 14's seven — and
exactly one task's crew cuts into its calendar: **UID 94, in 5 snapshots, 3 of them
recorded-complete** (ADR-0476's pin adjudicates nothing). The repository's **29 `.mpp` files** add the
same task in one more save. (The `Large Test File.mpp` / `Large_Test_File.mpp` collision ADR-0501
warned about bit my first conversion loop — 28 artefacts for 29 files caught it.)

**What was wrong, measured on the pristine engine in a separate worktree:** UID 94 finished **16:30**
where MS Project stores **17:00** on both unstarted snapshots (the task calendar alone resumes at
12:30; the common afternoon begins at the crew's 13:00), and on `updated` its late finish sat on
**Saturday 08-15 23:30** — a day the crew never works — where MS Project stores **Friday 08-14
23:00**, its slack 3,180 against the stored 2,190.

**Shipped: `_calendar_intersection`** (identity-memoized like `_ruler`, never hashed, never stored,
never in `Schedule.calendars`, uid −2, both names) behind `_task_shape` and `booking_calendar`:

| rule | pinned by |
| --- | --- |
| weekdays ∩ · intraday blocks pairwise ∩ (merged) · holidays ∪ · an extra working day kept only when BOTH work it | a synthetic pin per rule, both directions where there are two |
| a calendar the other restricts nothing of stands for the intersection **by identity** — a 24-hour task calendar → the crew's object (UID 14, byte-identical by construction); a task calendar inside a 24-hour crew → its own; core hours inside the project pattern → their own; a Mon–Sat task calendar over a crew on the project pattern → the **project calendar object** | `is` pins in both modules (the last case is the battery survivor's pin, below) |
| WORK crews that NAME a calendar only — a MATERIAL / COST booking (ADR-0487) and a crew the file names no calendar for (an XER, an older Save) keep the task calendar | synthetic pins |
| disjoint calendars fall back to the task calendar — **UNVERIFIED**, MS Project refuses such a booking, no witness | synthetic pin |
| the slack axis stays the TASK calendar (ADR-0474) — UID 94's 6,360 / 2,190 are working minutes of `Standard+Sat.` | the parity five-value pin |

**Measured, every golden, pristine → this tree with one instrument:** Hard_File exact finishes
**38 → 40** (94, 157), exact stored slack **37 → 39** (95, 412); `updated` **106 → 108**, **99 → 101**;
**12 activities moved, 0 away**, project finishes and every disclosure list unmoved, **the other 13
goldens BYTE-IDENTICAL**. On `updated` UID 94 reproduces **all five** stored values (Start, Finish,
LateStart 08-14 14:30, LateFinish Fri 08-14 23:00, TotalSlack 2,190) and UID 157 lands exact with it
(TotalSlack 1,440). The 29-file `.mpp` census: **26 byte-identical**, 18 task-moves on the three
Hard_File saves, **none away**.

**The residual on the base snapshot is NOT this rule's — R-67.** UID 94's finish is exact there and
its slack reads 6,510 against 6,360: milestone 147's stored LateStart is **Saturday 08-01 13:00**, an
instant MS Project keeps on the elapsed axis inside the weekend (ADR-0476's day-boundary class); the
engine's integer axis has no Saturday, 147 reads Monday 08:00, its 16-hour-crew predecessor 157 reads
its late finish two hours late, and 94 inherits 150 minutes. ADR-0474's backward arithmetic is exact
when fed the stored Saturday (snapped back on the crew calendar it IS 157's stored Friday 23:00).
Computed in the oracle, registered as **R-67**.

## How it was verified

* **Red before green, in a SEPARATE WORKTREE at `origin/main`** (the pristine baseline was never
  taken by mutating the tree under measurement): the synthetic module cannot import; the parity
  oracle fails **10 of 20 by name**; the re-pinned `booking_calendar` case fails; the ten that pass
  on the pristine tree are the seven UID 14 pins and the three completed-snapshot pins, by design.
* **The rig was refuted twice before the engine was:** the residual's 150 minutes are the
  START-slack gap (the finish-slack gap is 120 — both now computed and pinned), and "301 non-24-hour
  tasks" was 294 + UID 14's seven. Recomputed from the rig's own numbers, not the engine's.
* **Mutation battery: 13 cuts on a shadow copy of `src/` (a `-p mutcheck` plugin asserts the engine measured IS the copy; `cpm.py`'s checksum changed under every cut; the control run green, 50 passed, before and after): M01 the old rule, the task calendar wins → 19 red · M02 blocks not intersected → 16 · M03 weekdays not intersected → 6 · M04 holidays not unioned → 2 · M05 extras from the task alone → 1 · M06 no identity shortcuts → 2 · M06b the general path never returning the crew → 1 · M07 material / unknown crews intersected too → 1 · M08 `booking_calendar` on the old rule → 3 · M09 the memo never consulted → 1 · M10 the late finish snapped back on the task calendar (pre-existing code) → 6 · M11 the empty-intersection fallback returning the crew → 1 · M12 the plan builder never intersecting → 19. **13 / 13 red by name. M06b SURVIVED the first pass** — the identity shortcut for a task calendar that CONTAINS the crew's pattern (a Mon–Sat task calendar over a crew on the project's Mon–Fri) had no pin; it is not dead code and its effect is real (the leg is the crew's real calendar object, the thing R-59's disclosure will name) — killed by a pin naming that case, and the whole battery re-run.**
* Perf gates unmoved (shapes once per object, zero `Calendar` hashes across 20 solves). Statics
  green on **both** ruff binaries (0.15.8 and 0.16.8), `ruff format` (1,270 files), `mypy --strict`
  (165 files), `bandit` (exit 0), `node --check`.

**Gate on the final tree: the full suite (5,546 collected = the previous 5,515 + this unit's 31; `-m parity` collects 170 = 150 + 20, attributed by `--collect-only`) was still running at the first push, 2,627 verdicts in with 0 failures — its figures are recorded in the follow-up docs-only commit**

## Deliberately NOT done

**R-67** (147's Saturday late start, above) · the **empty-intersection fallback** (UNVERIFIED; a file
carrying one is the signal to measure it) · an exception day's own working times (the model records
a DayWorking exception as a date; inherited) · intersecting a crew the file names NO calendar for
(unknown, not the project's) · a `CPMResult` disclosure for the intersection (a calendar rule, not a
stored input) · registering the derived calendar (derived data) · **R-59** is next and unchanged —
`/analysis` still names task calendars only.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-59** (disclose the
crews' calendars beside the task calendars on `/analysis`; the derived intersection has a name of its
own now) · **R-64** · **R-63** · **R-62** · **R-65** · **R-66** · **R-67** (this unit's residual) ·
**R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19
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
