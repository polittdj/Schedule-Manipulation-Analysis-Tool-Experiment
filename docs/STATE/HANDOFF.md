# Handoff — 2026-09-18 (b) (R-65 **CLOSED** (ADR-0508) — a leveling gap is measured in working SECONDS and the leg honours the nearest minute of the CUMULATIVE gap; the recorded span reads the nearest minute of its seconds; 102 of 102 corpus bookings occupy the window MS Project recorded — **v1.0.274**, schema **2.16.0**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`27ae8893`** (#697, R-62 / ADR-0507, **MERGED** 2026-09-18 01:48Z by the operator; the squash TREE-IDENTICAL to the reviewed PR head `598375dd`, tree `3459fa60…`, compared with `git rev-parse <sha>^{tree}` this session). **`main`'s OWN runs for `27ae8893` — read TO CONCLUSION this session, by their JOBS (the run object's `updated_at` sits at creation):** CI 1923 (`35296778362`): `cui-guard` 01:48:22Z · `browser` 02:05:52Z · `floor` 02:14:14Z · `test (3.13)` 02:17:03Z · `test (3.11)` 02:19:46Z · `check` 02:19:52Z — **SIX OF SIX GREEN** (the `check` job listed only once its `needs` completed: five jobs, then six); installer-smoke 761 (`35296778353`): `linux` 01:48:55Z · `windows` 01:52:42Z. Nothing about `27ae8893` is outstanding. This unit ships on branch `claude/nice-hypatia-ydw51z` (the designated branch, started on the squash) as a **draft PR** ([#698](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/698); the operator merges; never marked ready here; EIGHT checks — `installer/**` changed). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the battery and the gate are all this repo gets. Highest ADR **0508**. Version **1.0.274**. Schema **2.16.0** (unchanged: a method joined `Calendar`, no field). QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-65 read: the engine's honoured leveling gaps (ADR-0491) land 1–28 minutes short of the window
MS Project records for the same split booking — systematic, one-directional, ~100 bookings —
with three suspects (rounding in `_recorded_span`, the share→`after` conversion, MPXJ's block
boundaries).** The kickoff's four checks ran before a line changed, and each moved the row.
**The population** on fresh conversions of all 29 intake `.mpp` files (43 s, every artefact
asserted): 239 split WORK bookings, 173 differing from their window — and **102 are the row's
class**: at SECONDS resolution their window IS the duration plus the uncovered gaps, exactly, on
every one (**24 distinct bookings on 14 tasks** once the four saves of the Large Test File2
schedule — three different blobs plus `Large Test File2.mpp` — are counted once; 19 each, 16 on
Leveled, 10 on `Large Test File.mpp`; 0 on the underscore `Large_Test_File.mpp`; the two
byte-identical duplicate saves carry no split). **1 to 62 minutes short, never long** (UID 5278,
69 gaps: 7 / 28 / 62 in three saves — "1–28" was the range ADR-0501 happened to print). The other
70 are not this class — 49 completed records (UIDs 5231 / 5249 × seven files) and 21 with
ADR-0502's absorbed delay (5270 / 5274) or a booking that ends before its task (5267): their
windows are SHORTER than the occupancy at seconds resolution too. Plus one 540-minute oddity,
UID 401 on the 24-hour snapshot (completed; its recorded Start precedes its first block on a
crew calendar that save declares no segments for).

**The mechanism.** MS Project places a split boundary in tenths of a minute — **all 3,742
boundaries in the corpus are multiples of six seconds** — and `_recorded_span` read each end as
`hour * 60 + minute`: every gap 0.0 to 0.9 minutes short, never long. The share→`after`
conversion places a gap, it does not size one; the block boundaries are the file's own instants
(217 of 239 windows begin on the first piece and end on the last). **Three readings were
measured on the population before one was chosen** (the leg from the stored start against the
stored finish, working seconds): truncation 0 of 98 within 30 s; per-gap rounding 8 (six minutes
adrift on UID 5316's nineteen gaps); **the CUMULATIVE gap rounded at every boundary 67 within
30 s and every one within 72** (the start's own truncated seconds).

**Shipped.** `Calendar.intraday_worked_seconds` (the minutes rule at seconds resolution; the
minutes form delegates); `_recorded_seconds` / `_covered_seconds` / `_nearest_minute`;
`_split_gaps` keeps the true gap in seconds and hands the leg `_nearest_minute(cumulative) −
honoured` at every boundary (a 24-second gap is no split, 30 seconds is a minute — half up, the
importer's rounding); `_recorded_span` reads the nearest minute of its seconds (106 material /
cost windows in the corpus, 41 carrying seconds, **0 read differently** — a whole-day material
window carries the same seconds at both ends). Nothing downstream changed.

| figure (pristine → this tree) | |
| --- | --- |
| corpus class, occupancy == recorded window | **0 → 102 of 102** (residual 1 to 62 min → 0) |
| the witnesses 5342 / 5316 / 5273, occupancy vs window | 2,757 / 9,329 / 4,687 → **2,758 / 9,333 / 4,688 = the windows** |
| goldens, finish movers toward / away in WORKING minutes (Large Test File / File2 / Leveled) | **66 / 0 · 101 / 0 · 96 / 4** — the 4 are Leveled's 5306 chain: four 2:36 gaps read 10 (ADR-0491's 8; MS Project's 10:24), the leg 0.4 min from MS Project's, behind a start a day late for its own reason |
| stored slack exact (fuse_ltf) | **867 → 874** / 1024 · **730 → 736** / 998 (re-pinned, dated); File2 finish-within-a-day **1687 → 1689**; Leveled 1645 → 1664, slack 789 → 841 |
| every other golden (Hard_File × 5, Project2 / 5, EVM1 / 2, the SSI Large_Test_File) | **byte-identical** |
| `-m parity` | **187 → 197 green** (ten new pins, two re-derived floors) |

## How it was verified

* **Red first, on the pristine package (a separate worktree at `27ae8893`, `PYTHONPATH` on its
  `src/`, the `-p mutcheck` plugin asserting it): 17 failed by name / 51 passed** — four
  leveling-split pins (2:36 × 4 → 8, 0:36 × 3 → 0, the 30-second boundary, the lunch-hour
  boundary), the recorded-span pin (324), the calendar method, ten parity pins (the witnesses,
  5306, the three populations, the class beside the row, 5268), the two re-derived floors.
* **Mutation battery 9 / 9 red by name** on fresh shadow copies of the FINAL `src/` (control
  68 green on the shadow, every cut checksum-verified, the plugin asserting the shadow on every
  row): M01 both ends truncated 13 · M02 per-gap rounding 12 · M03 floor 12 · M04 segments
  ignored 32 · M05 covered seconds zero 8 · M06 honoured not subtracted 20 (the 403 shape reads
  11-17) · M07 `_recorded_span` truncating 8 · M08 the 24-hour branch 4 · M09 zero-minute gaps
  appended 2 (the disclosure boundary).
* Statics green on **both** ruff binaries, `ruff format`, `mypy --strict` (165 files), `bandit`
  (exit 0), `node --check` per file; the wheel built AFTER the last format; lockstep pins 68 passed.
* **A render diff was NOT run** (the view layer is untouched; the movers are Large Test File
  finishes; the suite's web tests render every page over the fixtures).

**Gate on the code commit `3132b97e` — MEASURED in a separate worktree (never in the tree the docs were written in; `PYTHONPATH` on the worktree's `src/`, the `-p mutcheck` plugin asserting it):** **full suite 1 failed / 5,633 passed / 7 skipped in 33:06** (02:54–03:27Z, `-v`, the package under test asserted by the plugin, no stall). The one failure is attributable and is not the change's: `tests/test_state_docs.py::test_handoff_top_section_pins_the_current_pyproject_version` is red on the code commit's unrotated handoff and green on the final tree (the docs commit carries the pin); the code commit carried the rebuilt installers, so the four lockstep pins are green there; the final tree differs from the measured one under `docs/` only — so the final tree reads **5,634 green / 0 failed / 7 skipped** and **`-m parity` 197 passed / 0 failed in 4:43** (02:37–02:42Z, MEASURED on the working tree, identical to the code commit under `src/`, `tests/`, `pyproject.toml` and `installer/`, the plugin asserting it). Attributed: **5,641 collected = 5,625 + 16** (the parity module's 10 + the leveling-split module's 4 + the recorded-span pin + the calendar pin); the previous unit's 5,618 green + 16 = 5,634; parity **197 = 187 + 10**. The 7 skips are the documented set (the loopback-allowlist pair, the three INCIDENTAL_SVG axis cases, the two LibreOffice interop skips that are correct in this container). Statics green on both ruff binaries, `ruff format --check`, `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the wheel built after the last format; lockstep pins 68 passed. **This is RUN 2.** Run 1 in the same worktree died at 4,700 of 5,641 results with `Fatal Python error: Bus error` (exit 135) inside `engine/cache.py:250` — the SQLite cache's `PRAGMA journal_mode=WAL`, a memory-mapped write — under `tests/web/test_ram_estimate.py::test_ingest_over_threshold_warns_but_still_loads`; the module alone re-ran 4 / 4 green in the worktree. Two mechanisms were tested and REFUTED: a shared cache directory (the conftest points `SF_CACHE_DIR` at each test's own `tmp_path`) and pytest's basetemp retention deleting the running session's tree (run 1's `pytest-31` still existed after the crash; only two finished sessions' directories were pruned). The candidate left, UNVERIFIED: the session's fixed writable-disk allowance exhausted at the instant of the mmap write (the one write that dies with SIGBUS instead of an `OperationalError`) — three pytest sessions had been started beside the suite and 1.6 GB of scratch (two worktrees, 29 conversions, ten shadow trees, old basetemps) had accumulated; 1.1 GB was freed before run 2, which ran alone. Not this PR's code; registered, not chased.

## Deliberately NOT done

**The duration's seconds** — File2's **UID 5268** is the one booking left a minute LONG (8,157.8
read 8,158, gaps 2,554.5 read 2,555, window 10,712.3 read 10,712; two halves up, the whole down;
exact before by the coincidence of two truncations); the model's integer minutes are a Law;
pinned by name · **a seconds axis in the model or the leg** · **the START's own truncation**
(`_snap_to_working` drops the seconds of a stored 08:00:54 start — up to 59 s, inside every pin) ·
**the 21 absorbed-delay / early-finishing bookings** (ADR-0502's class; not this row's) · **UID 401
on the 24-hour snapshot** (a completed record; that save's `Customer Service Team` declares no
segments — no row) · **per-gap rounding** (measured, refused) · **a render diff**.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-67** (the
backward mirror of ADR-0505's carried instant — milestone 147's Saturday 13:00 LateStart on the
Hard_File base snapshot; UID 94's slack 6,510 vs 6,360; the 24-hour snapshot's 156 at −4,320 vs
−4,740) · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; **R-68**
waits on the operator's reading (question (f)). The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
