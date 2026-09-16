# Handoff — 2026-09-16 (b) (R-61 CLOSED (ADR-0500) as **REFUTED** — the census the row asked for was run and **the population is ONE task**; the row's premise is mis-stated and its proposed rule is inert as written and **315-to-0 wrong** when generalized; `engine/` untouched, **v1.0.267 unchanged**)

STATUS (current) — `main` @ **`6b92d937`** (#687, the docs-only merge record of #686; merged after this session branched, which is why this branch carries a merge commit rather than a rebase). Before it **`0b010936`** (#686 — R-50, ADR-0499, v1.0.267), whose squash was TREE-IDENTICAL to the reviewed head `92b0693c` (`f4e70212b63306d5624a90b5aa9e4fdc2869f500` on both). **`main`'s own runs for `0b010936` are SETTLED — read to conclusion this session, not inherited: CI 1893 (`35097402239`) `completed` / **SUCCESS**, all six jobs (`cui-guard` 12:42:51Z · `browser` 13:00:24Z with the R-52 interop gate run-and-NOT-skipped on `main` itself · `floor` 13:07:42Z · `test (3.13)` 13:12:57Z · `test (3.11)` 13:27:52Z · `check` 13:27:58Z), and installer-smoke 744 (`35097402279`) `completed` / **SUCCESS** 12:47:28Z. Nothing about `0b010936` is outstanding.** Highest ADR **0500**. Version **1.0.267**, unchanged — this unit touched no `src/`. QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-61 is CLOSED, and nothing in `src/` changed — that is the finding.** The roadmap row said a
FIXED_DURATION booking on an off-pattern crew spans the DURATION in crew minutes where MS Project
keeps the task's window, named `Hard_File_updated3` UID 210 as the witness, and asked for a census
across the goldens with the stored booking windows as the oracle. The census was run. It settles
the row three ways, none of them the row's.

**1 — the population is ONE task.** Across all **15 MSPDI goldens** the set of (golden, task) pairs
where an active FIXED_DURATION task carries a WORK leg on a materially different calendar is
exactly **five rows — UID 210 in five snapshots of one file**. No second task, no *unstarted*
witness, none without a project-calendar co-booking. No golden can discriminate the rule.

The row's arithmetic on the witness is right: duration **1,920** min (4 project days), the leg
spans 1,920 min of the 24-hour *Content Developer* calendar (1.33 days there), the file records
the booking over **7,740** of them — and that window is the **task's own** window
(2026-08-20 08:00 → 2026-08-25 17:00), which MS Project writes onto all four of the task's
assignments, work and material alike.

**2 — the premise is mis-stated: neither named rule is the mask.** Read off the live plan builder,
UID 210's **primary (finish-placing) leg is the `Standard`-calendar WORK leg** of the Logistics
Apprentice booking — the same 1,920 minutes on the *project* calendar, landing on the stored
finish exactly. The crew leg finishes **2026-08-21 16:00**, four days earlier, and has never
placed the task. On a shadow engine with each named rule cut in turn:

| tree | UID 210's early finish | vs the stored 2026-08-25 17:00 |
| --- | --- | --- |
| pristine | 2026-08-25 17:00 | **exact** |
| ADR-0476's completed-window pin CUT | 2026-08-26 14:00 | **+1,260 min — LATE, not early** |
| pin CUT **and** ADR-0487's material leg CUT | 2026-08-26 14:00 | **unmoved by the second cut** |

(The material-leg cut has teeth elsewhere — it moves updated3's project finish 12-12 → 12-06 and
within-a-day 106 → 44. It simply does not touch 210.)

**3 — the rule is INERT as written and REFUTED generalized.** Implemented on the shadow engine
exactly as the row specifies, it **fires** (ratio 1.0000 → 4.0312, span 1,920 → 7,740, that leg's
finish 08-21 16:00 → 08-25 17:00) and changes **nothing**: project finish, within-a-day and
stored-slack-exact **byte-identical on all 15 goldens**; its only effect is a *lost* disclosure
(210 drops off `booking_span_driven`). MS Project has no separate scheduler for FIXED_DURATION, so
the claim is about ratio-1.0 WORK legs generally (**267** tasks in the corpus are placed by one).
Generalized: within-a-day **1,666 → 1,568**, **1,687 → 1,585**, **1,645 → 1,567** on the three
Large Test File goldens, every other golden unmoved, and the **per-task census is 315 AWAY / 0
TOWARD** (worst +309,865 min). Mechanism: a split booking's recorded window spans the leveling
gaps ADR-0491 honours *separately* — `Large_Test_File` UID 5231's window (89,760) is **26,880
crew minutes SHORTER** than the correct occupancy (89,760 + 26,880 of gap).

**4 — the one alternative the row does not name, refuted too.** A fixed-duration leg on the
*task's* axis rather than the crew's (MS Project's duration is a property of the task): **0 toward,
5 away** — it drops 210 off the wall path entirely, so ADR-0476's pin lands on the integer axis at
**16:00**, ADR-0476's own day-boundary residual, 60 minutes away.

**Shipped:** `tests/parity/test_r61_fixed_duration_leg_oracle.py` (10 pins: the census population,
the witness's two numbers, the corrected premise, five stored-finish oracles, the ADR-0491
refutation witness, and one **tripwire** on the type rule — labelled a tripwire in its own
docstring, because a shape pin is not evidence about MS Project) · **ADR-0500** · the R-61 row →
CLOSED.

## How it was verified

* **Mutation battery 6 / 6 red BY NAME**, control green, on a shadow copy of `src/` with a
  `-p mutcheck` plugin asserting the modules measured ARE the copy: M1 the proposed rule → 3 red ·
  M2 the crew calendar never resolved → 10 red · M3 ADR-0491's gaps not honoured → 1 red ·
  M4 legs sorted earliest-first → 1 red · M5 ADR-0476's pin cut → 5 red · M6 `_recorded_span`
  reading elapsed minutes → 2 red. **Every one of the 10 pins is red under at least one mutant.**
* **The battery caught this unit's own first cut.** The census originally re-implemented the plan
  builder's three leg-calendar lines inside the test, and it was **GREEN under M2** — the mutant
  that breaks exactly that resolution — because it was measuring the re-implementation, not the
  engine. Re-aimed onto `_task_shape`, it goes red. *A parallel implementation in a test is an
  oracle for itself.*
* **Gate on the final tree: 5,489 passed / 0 failed / 7 skipped in 35:36**, and `-m parity`
  **141 passed / 0 failed** in 4:28. Both deltas are ATTRIBUTED, not assumed: the previous
  unit's 5,479 and 131 plus this module's **exactly 10**
  (`pytest -m parity tests/parity/test_r61_fixed_duration_leg_oracle.py --collect-only`).
  The 7 skips are the documented set — the urlparse pair, three INCIDENTAL_SVG axis cases,
  and the two `test_pptx_libreoffice_interop` skips that are CORRECT in this container (no
  libreoffice-impress; CI installs the filter and treats a skip there as a FAILURE).
  Statics green on both ruff binaries, `ruff format`, `mypy --strict`, `bandit`,
  `node --check` and `pytest --collect-only` (5,496).

## Deliberately NOT done

* **No `engine/` change, no version bump, no wheel/installer rebuild.** Under QC-1 a change with no
  check in the corpus capable of refuting it does not get to touch the engine, and the only
  candidate rule is refuted 315-to-0 where it *can* be tested. `pyproject.toml` stays **1.0.267**.
* **No `src/` comment** in place of the executable tripwire — prose is what this repo's own audit
  calls load-bearing data with nothing asserting it is still there.
* **Nothing re-numbered or relaxed** in ADR-0474 / 0476 / 0487 / 0491 to accommodate either
  candidate.

## The residual, named and OPEN

The corpus cannot prove no such task can exist — only that **no oracle in this repository can
validate any change to the rule**, and that the proposed change is refuted where testable.
**What would settle it:** a production IMS carrying a FIXED_DURATION activity on an off-pattern
crew **with no project-calendar co-booking**, alongside MS Project's stored dates for it. The
census test names the population; **a sixth row appearing in it is the signal to re-read
ADR-0500.** Do not re-chase the window rule without such a file.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha written here.** `main` @ **`0b010936`**
(#686, R-50 / ADR-0499, v1.0.267). **Main's own runs for that merge were still IN PROGRESS when
this section was written** — CI run 1893 (`35097402239`): `cui-guard` 12:42:51Z SUCCESS, `browser`
13:00:24Z SUCCESS, `test (3.11)` / `test (3.13)` / `floor` in progress; installer-smoke run 744
(`35097402279`) also in progress. **Read them to conclusion before trusting this line.**

Then the report's §3 in order: **R-57** (an assignment's OWN leveling delay — Hard_File UID 398's
RA 277 is a split ON a delayed assignment: its gap is honoured since ADR-0491, its delay is not;
UID 188 on updated2) · **R-58** · **R-59** · **R-64** · **R-63** · **R-62** · **R-45** · then
R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19 artboards.

**Operator-owned, none blocking:** V-5 (PowerPoint opens the `.pptx`); OR-20's Jan-2024 fact line;
decisions on OR-20b / OR-20c; the 09-11 `"ok": false` transaction-log lines (a 403); an ON-banner
screenshot on v1.0.264+; `test_driving_path_whole_schedule_browser.py:104` width-racy (#667);
`/settings` sideways scroll; the residuals of ADR-0488 / 0486 / 0485 / 0483; OR-11b, OR-11d; the
working-minute axis; the hint bubble; ADR-0484's in-grid rows.

**Review cover is still absent** — Codex quota EXHAUSTED; the mutation batteries and the full gate
are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
