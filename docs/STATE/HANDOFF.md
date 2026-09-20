# Handoff — 2026-09-20 (c) (R-04 **CLOSED** (ADR-0515) — Acumen Fuse's own rounding is half-to-even wherever its code rounds; the sweep of the `round()` sites toward `round_half_up` is REFUTED by measurement; the 374 sites classified by exposure and guarded; the whole-day DIVISOR registered as R-75 — **v1.0.279**, docs + tests only)

STATUS (current) — `main` @ **`dc9135f0`** (#703, R-03 / ADR-0514, **MERGED** 2026-09-20 05:35:44Z by the operator; the squash TREE-IDENTICAL to PR #703's FINAL head **`cc9a7a9b`**, tree `9e1935e7…`, compared with `git rev-parse <sha>^{tree}`). PR #703's FINAL head's EIGHT checks read to conclusion this session — CI `35488995060`: `cui-guard` 04:23:07Z · `browser` 04:40:55Z · `floor` 04:52:50Z · `test (3.13)` 05:10:15Z · `test (3.11)` 05:16:07Z · `check` 05:16:12Z; installer-smoke `35488995051`: `linux` 04:24:06Z · `windows` 04:27:54Z — eight of eight green. **`main`'s OWN runs for `dc9135f0`, read by their JOBS:** installer-smoke 790 (`35492076147`): `linux` 05:36:27Z · `windows` 05:40:30Z green; CI 1952 (`35492076184`): `cui-guard` 05:36:03Z · `browser` 05:50:35Z · `floor` 05:57:40Z · `test (3.13)` 06:24:40Z · `test (3.11)` 06:30:05Z · `check` 06:30:12Z — **SIX OF SIX GREEN**. Nothing about `dc9135f0` is outstanding. This unit ships on the designated branch **`claude/gallant-cori-v8mh88`** (restarted on the squash) as a draft PR the OPERATOR merges (never marked ready here) — **docs + tests only, no `src/` change, so SIX checks, no version bump, no installer rebuild**; the PR number is recorded in the docs-only follow-up. **The gate:** statics green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`, `mypy --strict`, `bandit`, `node --check` per file; the new parity oracle (6 passed, 4 s), the ledger guard (3), the WP8 report guard (8), the rendered-tie module (7), `test_change_effects` (re-aimed comment), the state-doc guards; red by name under three mutants of the oracle's rule and seven `round_half_up` mutants at the display callers (shadow copies, mutcheck). CI's `test` jobs on the final head are the suite verdict (no background worktree suite — the last two died unread). Review cover remains ABSENT (Codex quota exhausted). Highest ADR **0515**. Version **1.0.279** (unchanged). Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-04's premise fell to the reference's own reports.** The row read the 330 builtin `round()` sites
outside `engine/metrics` (44 more inside) as MF-08's residual — banker's rounding at every displayed
tie, to be swept family by family toward `round_half_up`, each figure measured against the reference
tool's OWN rule. The intake holds three Fuse **Forensic Analysis Reports** with a golden on both sides
(the Large Test File pair, the two Hard_File pairs); against the goldens' exact days every whole-day
field (Original / Remaining Duration, Total Float) is **half-to-even on every comparable row** (LTF
752 / 773 / 1,297; half-day ties of both parities 20 / 11 / 262; half-away-from-zero misses exactly
the even-part halves 10 / 4 / 111), the day change is the **difference of the ROUNDED fields** (the
rounded exact difference reproduces only 1,216 of 1,297; Hard_File UID 37: 8.5 → 7 is shown −1, not
−2), the 2-dp ratio is **ToEven on the SCALED value** (1/8 → 0.12, 9/8 → 1.12, 17/40 → 0.42, 1/40 →
0.02 — half-up refuted on all 11 discriminating ties; Python's own `round(0.025, 2)` is 0.03, so the
reference rounds the scaled double), and the Start / Finish change is the **calendar-day difference
truncated toward zero** (2,741 / 2,741). Fuse's metric values in its Summary / History reports are
stored **RAW under Excel's General format** (13,022 cells, 1,309 at an exact 3-dp tie) — so the D19
"2.625 → 2.63" behind MF-08 was an illustration (ADR-0141 says no golden sits on a half; the pin is
2.79 / 2.81), never an observation. Ties are common in the corpus (292 stored floats and 74 durations
sit on a displayed tie across the 15 goldens), so the question was real; the answer is that `round()`
IS the reference's rule wherever its code rounds.

* **Shipped:** no flip, no `src/` change. `tests/guards/round_site_ledger.tsv` classifies all 374
  sites by exposure (twelve families, rules in `test_round_site_ledger.py`'s `FAMILIES`; the guard ties
  the ledger to the tree — an added, moved or reworded site is unclassified until named; the family
  counts are re-derived into the report's §4 by `test_audit_report_wp8.py`). `tests/parity/
  test_fuse_forensic_rounding_oracle.py` pins the reference's four rules on all three reports with the
  populations, the tie counts and the alternatives refuted BY NAME; the three Hard_File rows the rule
  does not reproduce are named as a DIVISOR (R-75) and LTF2 UID 5267 as the model's minute grid
  (`PT107H59M36S` carried as 6,480 min). `tests/web/test_round_display_rule_at_ties.py` observes each
  display family at a derived tie on the rendered payloads (a 0.25-day lag → 0.2, a 1.125-day remaining
  → 1.12, SCL 9/16 → 56.2, criticality 17/32 → 0.5312, 12.5 % → "12%"). `test_change_effects`'s
  whole-day tie pin (240 min → 0) now cites the measured reason.
* **Registered — R-75 (T1, S):** Fuse divides its whole-day float by the ACTIVITY's own day — Hard_File
  UIDs 14 / 146 / 94 display −3 / −1 / 2 for stored −4,320 / −1,440 / 2,190 min (a 1,440-min task
  calendar, an elapsed duration whose crew is on a 1,440-min calendar, a 930-min calendar) while
  `acumen_whole_day_float`'s three callers pass the project's 480; on the 24-hour Hard_File the engine's
  DCMA-06 reads **2** (UIDs 302 / 385) where Fuse's ribbon reads **0** (`HA296F~1.XLS`; Negative Float
  40 / 11 agrees either way). Mechanism undecided (146 has no task calendar) — decide it first.
* **Measured:** every existing figure unchanged — the Fuse parity oracles green, the goldens untouched.

## How it was verified

Ten QC-3 assumptions in ADR-0515: eight held, two UNVERIFIED and said so (MS Project's 2-dp display
rule — no MS Project-rendered export in the intake; Fuse's GUI display of a metric value at a tie — the
exports carry raw values, so MF-08 stands on the spreadsheet convention). Fell: the row's premise; MF-08's
"Fuse-measured" basis; the oracle's first grid reader (a deleted activity's empty after cell let the
ratio slide into the after position — 1,510 rows instead of 1,436; positional now, population pinned).
Red first: the oracle under three mutants of its rule (half-away 19 / 10 / 119 rows red; the rounded
exact difference 806 → 783, 848 → 798, 1,436 → 1,351; the half-up ratio 11 red); the tie module under
seven `round_half_up` mutants at the callers, each red on its own pin only (`0.3 == 0.2`,
`1.13 == 1.12`, `56.3 == 56.2` ×2, `0.5313 == 0.5312`, `(1, 2, 3) == (0, 2, 2)`, the 12 % cell gone);
the WP8 census red by name with the thirteen new keys before the report carried the rows.

## Deliberately NOT done

A `round_half_up` sweep of any family (refuted) · reverting MF-08 (no tie oracle either way;
parity-green; restated, not moved) · a 2-dp precision change for the days families toward MS Project's
display (a presentation change; MS Project's tie rule unverified) · the divisor fix (R-75 — mechanism
first, on the corpus) · the Free Float sheet (no stored free float field in the model — R-74's row) ·
reading the tool's `round(x, 2)` as the reference's `round(x * 100) / 100` (they differ only on
decimal-looking near-ties such as 0.025, none of which the tool prints from a Fuse figure).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-75** (T1, S — the
whole-day divisor: decide the mechanism on the corpus first — task calendar, elapsed axis, or the crew's
— then the three callers, red-first on the 24-hour ribbon's High Float 0 / Negative Float 11 and the
three Forensic rows, `-m parity` unmoved on the LTF pair) · **R-73** · R-09 · R-74 · R-69 · **R-71** ·
R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)); the probe
fixture's Fuse run is the operator's optional confirmation of ADR-0514's assumption 5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
