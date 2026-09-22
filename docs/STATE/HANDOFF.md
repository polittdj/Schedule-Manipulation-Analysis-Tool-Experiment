# Handoff — 2026-09-22 (R-74 **CLOSED** (ADR-0522) — free float is **BOUNDED BY** the total, a successor's leveling delay is **not slack the predecessor owns**, and the row's evidence that MS Project "never" inverts the pair was a statement about a **FILTER** — **v1.0.286**)

STATUS (current) — `main` @ **`8279010d`** (#710, R-09 / ADR-0521, **MERGED** 2026-09-21T21:58:10Z by the operator; head `d65069db`, base `accd2df1` — merge and both runs RE-VERIFIED this session against the API, not inherited). **`main`'s OWN runs for `8279010d`:** CI 1974 (`35660161146`) **success** · installer-smoke 808 (`35660161129`) **success**. Nothing about `8279010d` is outstanding; do NOT re-read those runs. 809 commits at session start. This unit ships on the designated branch **`claude/refresh-state-docs-pr710-j7qaia`** (branched fresh from the squash; its never-pushed remote-tracking ref pruned) as a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0522**. Version **1.0.286**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

**Both state docs were stale by exactly one merge when this session opened** (3 `accd2df1` references in `NEXT-SESSION-PROMPT.md`, 2 in `HANDOFF.md`, counted before the first edit). Re-derived and refreshed INSIDE this work commit, per the standing rule that a docs-only PR to record a merge is a repo-rule violation.

## What landed

**The corpus was rebuilt from scratch and reproduces ADR-0513's population on the nose** — the 15
committed goldens under `tests/fixtures/golden/` plus 29 fresh **path-keyed** conversions of the
intake `.mpp` files: **44 files, 22,105 scheduled activities, 3,315 storing both slack elements, 0
stored inversions, 1,116 stored equal.** The engine's count re-measures to **1,867**, not the row's
1,870 (the row predates ADR-0513 / ADR-0517).

**The row's own evidence was a statement about its filter.** All **1,230** corpus rows whose stored
`TotalSlack` is NEGATIVE have `FreeSlack` **ABSENT**, and no row anywhere stores a negative
`FreeSlack`. The MPXJ writer omits a zero duration (ADR-0490 / R-62's bytecode fact). So "0 of 3,315
invert" was measured on a population that **cannot contain a negative total**. Read with that same
writer rule, **MS Project itself reads free (0) above total (negative) on 1,227 rows.**

**The 1,867 is TWO classes.** **1,229** have a NEGATIVE total and free floors at 0 — the class MS
Project itself exhibits, 577 of them with the engine's total exact. **NOT a defect, deliberately left
alone.** The other **638** have a total ≥ 0; of the 622 carrying a stored `FreeSlack` the engine
exceeded it on **622 of 622**, and the stored free equals the stored total on **610**. That is the
defect.

**Shipped (V6 of nine variants measured on the whole population before one was chosen):** free float
is measured to a successor's early start **less that successor's stored leveling delay** for
START-type links (`_succ_free_start_wall` / `_succ_free_start_off` — the mirror of `_succ_ls_wall`; a
resumed tail is already past its delay), then **bounded by the reported total, the bound itself never
negative** (`free = min(free, max(total, 0))`).

## What it measured

Against MS Project's own stored `FreeSlack` over the 44 files: exact **2,471 → 3,004** of 3,315, high
**772 → 198**; the **total float is untouched** (10,610 of 12,680 exact, before and after — the bound
reads the total, never writes it). Isolated to the **2,926** rows whose total ALREADY matched exactly,
so a total-float residual cannot flatter the result: exact **79.5% → 97.7%**, and **the low count does
not move (14 → 14)** — every one of the 41 new lows in the raw count sits on a row whose own total is
still inexact, which is the bound propagating a *total*-float residual, not a free-float regression.
**After the fix, free exceeds total on exactly 1,229 rows — precisely the negative-total class.**

**ADR-0474's own pin movements recorded this defect as if it were a fix.** `float_free_0` on Project2
was moved **71 → 68** with the note "the leveled successors start later, so three more predecessors
carry free float"; `float_free_lt10` on Project5 **73 → 69**. MS Project's stored `FreeSlack` says the
answers are **74** and **72**, and all four bands now reproduce exactly (P2 74/106 and 80/106; P5
68/99 and 72/99) — an oracle independent of the engine that produced them.

## How it was verified

**Red first on the pristine engine, by name:** 4 of 7 assertions red (UID 408 reading 15,360 for a
stored 2,400), 3 green and declared controls. **Mutation battery 4 of 4 red by name:** the zero floor
removed (the floor guard AND the invariant) · the bound removed (UID 408, the invariant, the rate) ·
the delay removed (the delay witness, the rate) · the delay extended to FF / SF (the rate pin, which
is what discriminates the rejected V8). The population control is not vacuous — a plain `*.xml` glob
sees **4** of the 15 goldens because **11 are gzipped**. Suites on the final tree: statics all green
(`ruff` whole-tree · `ruff format` · `mypy --strict` 165 files · `bandit` exit 0 · `node --check` 64
files), engine **1,290 passed**, `-m parity` **246 passed**.

**A SECOND copy of the same pin was found only by RUNNING the suite.** The consumer sweep grepped
`free_float` and missed `tests/web/test_forecast_views.py:158`, which keys on the BAND ID and carried
the identical ADR-0474 accommodation (`69`, commented "73 before ADR-0474"). Re-pinned to **72** with
the reason; an exhaustive `float_free` sweep confirms those two are the only live band pins. **And the
background suite overlapped this session's own version bump, doc rewrite and installer rebuild — 16 of
its 17 failures were artifacts of that and re-ran green; exactly ONE was real (the pin above).** QC-1
says never measure a tree a battery is mutating.

## Deliberately NOT done

The 1,229 negative-total rows (MS Project omits `FreeSlack` there; nothing to match) · the one
negative free float in 22,105 rows (`Jacked up Schedule 2` UID 29, −2,400 against a stored −2,400 the
engine reproduces exactly) — its file emits **no** `FreeSlack` element at all, so absence carries no
information and **V5's floor-on-`free` was not taken: UNVERIFIED** · the **198** residual high rows,
of which 144 sit on rows whose TOTAL float is still inexact (the Large Test File crew-calendar chains,
R-56's family) and **54** are minute-scale residuals of the same family (all FS, 15 distinct UIDs,
deltas of 2 / 60 / 120 min, repeated across the 11 copies) — **registered as R-74's residual, to be
priced against the total-float chains, not against free float** · the finish-slack bound (V7,
measured **indistinguishable**, not refuted) · `link_slack`'s non-FS semantics · a
`stored_free_float_minutes` importer field (no consumer needs it; the oracle reads the XML directly).

## Traps this session paid for, BY NAME

**A basename is not a key.** Converting the 29 intake `.mpp` files by basename silently produced
**25** files — `Project2`, `Project5_TAMPERED` and `SRA Large Test File2` repeat across directories —
and flattening `/` and spaces to `_` still collided `Large Test File.mpp` with `Large_Test_File.mpp`.
Only an index-prefixed key gave 29. **A `*.xml` glob cannot see the corpus.** 11 of the 15 goldens are
`*.mspdi.xml.gz`; the first census read 4 and looked complete. **The oracle's own population was the
defect.** "0 of 3,315" is true and means nothing, because the filter that built the 3,315 excludes
every zero the writer dropped — *and the zeros are exactly where the inversions live.* **Both of the
row's prescribed remedies fail as written** (late starts: 2,471 → 963; the unfloored clamp: 1,239
manufactured negatives), and the mechanism that mattered most was one the row does not name.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** §3 in order: **R-77** (T2, M — the stored-date
family and the rendering projected CONTIGUOUSLY; census the 212 / 25 / 4 and every rendered-time pin
FIRST) · R-69 · **R-71** (T3) · **R-80** (T3, S — the 10 unassessed terminal `.catch` sentences,
per-site verdicts BEFORE any edit; a catch covering exactly one failure mode is NOT a conflation) ·
R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)).
**Outstanding operator ruling: where the 2026-09-21 (c) foreign kickoff came from.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
