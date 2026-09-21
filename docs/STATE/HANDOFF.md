# Handoff — 2026-09-21 (R-78 **CLOSED** (ADR-0519) — Acumen Fuse's `Float Ratio™` is TWO metrics under one name: the mean-of-ratios, N/A whenever a Remaining Duration field is 0, and the ratio-of-means, which keeps those zeros in both sums; both on the whole-day FIELDS and both presented half AWAY from zero — **v1.0.283**)

STATUS (current) — `main` @ **`01251bb2`** (#707, R-76 / ADR-0518, **MERGED** 2026-09-20 21:21:51Z by the operator; the squash TREE-IDENTICAL to PR #707's FINAL head `5deb78d6`, tree `78b981fb…` — re-verified this session, this clone's `HEAD^{tree}` == `origin/main^{tree}`). **PR #707's FINAL head, EIGHT checks read to conclusion THIS session:** CI `35535165650` — `cui-guard` 20:19:54Z · `browser` 20:35:30Z · `floor` 20:53:27Z · `test (3.13)` 21:11:14Z · `test (3.11)` 21:16:55Z · `check` 21:17:36Z; installer-smoke `35535165662` — `linux` 20:20:05Z · `windows` 20:24:06Z — **eight of eight green**. **`main`'s OWN runs for `01251bb2`, by their JOBS (read this session, every `head_sha` 01251bb2):** CI 1965 (`35538468705`) `cui-guard` 21:22:10Z · `browser` 21:38:14Z · `floor` 21:53:45Z · `test (3.11)` 22:08:40Z · `test (3.13)` 22:11:19Z · `check` 22:11:25Z — six of six; installer-smoke 799 (`35538468545`) `linux` 21:22:34Z · `windows` 21:26:46Z. Nothing about `01251bb2` is outstanding. This unit ships on the designated branch **`claude/charming-archimedes-ihwapd`** (branched from the squash; its never-pushed remote-tracking ref pruned) as a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0519**. Version **1.0.283**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**The row was half right, and its prescribed remedy was wrong.** R-78 said Fuse's `Float Ratio™` is
`AVERAGE(TotalFloat/RemainingDuration)` on the whole-day fields with N/A on a zero divisor — true —
and that the **aggregate form has no oracle**, so hold it or mark it UNVERIFIED. False. Parsing both
committed `.aft` snapshots: `Float Ratio™` is defined under **both** Bible forms (GUID `a536d1a4`
the mean-of-ratios; `8aec0857` / `697a1c84` / `dc1bd267` / `838991ea` / `9c556fbd` the
ratio-of-means), and Fuse prints **both under that one tile name**. The rev-5 `Hard_File_updated3`
save reads **-10.94** in the AlltheProjects ribbon and **-8.01** in the 7/15 Analyst ribbon; the
24-hour file reads **N/A** and **-3.58**. So `float_ratio` and `float_ratio_aggregate` ARE Fuse's
two forms and both are now oracle-backed — the same trap R-76 paid for (*the oracle the row said
did not exist was in the other workbook*).

* **Shipped:** `engine/metrics/float_ratio.py` — `_scored` returns Fuse's two whole-day FIELDS
  (`acumen_total_float_field` / `acumen_duration_field` on `activity_day_minutes`) and **keeps** a
  zero remaining; the mean-of-ratios reads **N/A for the whole schedule** on any zero divisor
  (`_na()`, population 0), the ratio-of-means keeps those activities in **both** sums and still
  prints; both present through `round_half_up`. `_common.duration_days_axis` **retired** (Float
  Ratio was its only consumer). `web/help.py` + `docs/METRIC-DICTIONARY.md` regenerated.
  `engine/trend.py`, `web/trend.py`, `web/standards.py`, `static/trend.js` **unchanged**.
* **Measured — the rule, from FUSE's own displayed cells:** **39 / 39** AlltheProjects ribbon labels
  under the shipped presentation (37 / 39 under half-to-even — the two misses ARE the tie, below);
  this includes every label whose SAVE the repo does not hold, which is evidence for the RULE only. **Measured — the ENGINE:** **19 / 19** mapped
  labels (9 numeric to 4 dp — -10.9446 → -10.94, 14.0076 → 14.01, 22.0173 → 22.02, 0.7678 → 0.77,
  0.2667 → 0.27 — and 10 N/A), plus **3 / 3** ratio-of-means tiles (-8.0115 → -8.01, -3.5758 →
  -3.58, 5.7361 → 5.74).
* **The N/A belongs to the mean-of-ratios ALONE, measured not reasoned:** the 24-hour Hard_File has
  four zero-remaining fields (UIDs 267 / 302 / 385 / 389); **keeping** them in both sums prints the
  Analyst tile's -3.58, **dropping** them prints -9.58, and the Quick-Add tile for the same save
  prints N/A.
* **A rounding site fell out of it.** ADR-0515 left the `value_dp` family on half-to-even because no
  reference display was known at that precision. Here there is one: the `.aft` declares
  `FormulaFormat='{0:N}'` (two decimals) for every `Float Ratio™` entry — a sibling ribbon metric
  with `FormulaFormat=''` writes `0.045833333333` raw — and the ribbon's **only** tie,
  `TP4_DataCenter_v1`'s exact **5/8**, is **WRITTEN 0.63** (half-to-even writes 0.62). The committed
  `TP4_DataCenter_v1.xml` lands on the same exact 5/8, so it was a live miss. Both display
  roundings moved to `round_half_up`; the ledger and the report census follow (374 → **372**,
  `value_dp` 119 → **117**, `round_calls_inside_engine_metrics` 44 → **42**).
* **Corpus:** 30 committed schedule fixtures re-scored — **16 moved**, N/A **1 → 10**; every newly
  N/A save that Fuse scored reads N/A in Fuse too.
* **Pinned:** `tests/parity/test_fuse_duration_fields_oracle.py` (the two forms against the three
  ribbons that display them, the zero-kept discriminator from Fuse's own cells, the tie census, the
  refuted alternatives by name, the -5.59 residual **named so it cannot silently start passing**);
  `tests/engine/metrics/test_float_ratio.py` (the whole-schedule N/A with the aggregate still
  printing, the empty population, the re-derived elapsed pin 0.33, the trend's `None`, the tie);
  `tests/engine/test_aft_formula_audit.py`'s aggregate row corrected to `Float Ratio™` / MATCH.

## How it was verified

Nine QC-3 assumptions attacked before the first edit: six held, **three fell** — the aggregate's
"no oracle", the row's status-keyed trend remedy, and the aft-audit row's `CP - Float Ratio™`
mapping. The trend trap is real and was reproduced red-first on the pristine tree (an
NA-with-population emits `values (0.0, 0.0)`, `deltas (None, 0.0)`), but keying the series on the
**status** would blank every version — `compute_float_ratio` returns `NOT_APPLICABLE` even when it
returns a figure. The carrier is `population == 0`, which `web/standards.py::_standards_value_cell`
already keys on and documents. **Red first by name** on the pristine package (the engine read
8 / 3.21 where Fuse reads N/A; the aggregate -9.5 for -8.01). **Mutation battery 5 / 5 red by
name**, control green: raw minutes · skipping a zero divisor · dropping the zeros from the
aggregate's sums · keeping the population on an N/A (the trap) · the project day as the divisor.
**Rendered, not inferred:** `/standards` served for `EVM1` (primary N/A) shows `Float Ratio`
**—** beside `Float Ratio (aggregate)` **0.06**, and for `Project2` **14.01** / **5.58**.
Statics green (ruff 0.15.8 and `uvx ruff@0.16.8`, `check .` + `format --check .` whole tree;
`mypy --strict` 165 files; bandit exit 0; `node --check` per file). Suites: see the session log.

## Deliberately NOT done

The **-5.59 residual** — update2-vs-update3's own `Hard_File_updated3` tile and its
`CP - Float Ratio™` twin -11.9 reproduce from no committed save under either form, although that
grid's 110 rows reproduce 110 / 110 and the sibling snapshot's tiles are exact (5.74 / -1.33);
named in the oracle · the Analyst's **`Avg Float`** tile (-11 / -4 where `AVERAGE(TotalFloat field)`
is -13.4038 / -2.8095) — a different metric · a **negative** rounding tie (none in the corpus:
away-from-zero is the convention applied, **UNVERIFIED**) · `CP - Float Ratio™` /
`Near CP - Float Ratio™` as engine metrics · a pure-logic second mode (no independent standard
exists for a Deltek/NASA metric; the aggregate already prints where the primary cannot) · the rest
of the `value_dp` family.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-79** (T1, S — the
DCMA-09 tile's denominator is the baselined INCOMPLETE population, red-first on File2 1,568 → 904
and the 24-hour file 84 → 12; then the field-vs-activity count from the tile's detail grid) · R-09 ·
**R-74** (T2, S — free float above the total) · **R-77** (T2, M — the stored-date family and the
rendering projected CONTIGUOUSLY; census the 212 / 25 / 4 and every rendered-time pin FIRST) ·
R-69 · **R-71** (T3) · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's
reading (question (f)); the probe fixture's Fuse run is the operator's optional confirmation of
ADR-0514's assumption 5.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
