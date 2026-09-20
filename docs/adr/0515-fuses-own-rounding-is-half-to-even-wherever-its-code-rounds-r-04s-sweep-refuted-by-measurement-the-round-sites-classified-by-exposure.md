# ADR-0515 — Acumen Fuse's own rounding is half-to-even wherever its code rounds; R-04's sweep toward `round_half_up` is REFUTED by measurement; every `round()` site classified by exposure and guarded (R-04 CLOSED; the whole-day divisor registered as R-75)

**Status:** Accepted · **Date:** 2026-09-20 · **Extends:** ADR-0467 (MF-08 — `round_half_up` at the
30 MetricResult sites), ADR-0514 (R-03 — Fuse's Total Float field is half-to-even), ADR-0141 (D19 —
the "2.625 → 2.63" illustration) · **Row:** R-04 (T1, M) · **Registers:** R-75 (T1, S)

## Context — what the row said

R-04 named MF-08's residual: the 330 builtin `round()` call sites outside `engine/metrics` (§4 census;
44 more inside it that MF-08 left as measured), read as banker's-rounding defects at every displayed
tie, to be classified by exposure and "fixed family by family, red-first" — each displayed rounding
read against the reference tool's OWN rule for that figure, *measured per figure, never assumed to be
`round_half_up`* (ADR-0514's amendment). MF-08 itself had rested on "the one Fuse-measured place
(logic density, QC audit D19: 2.625 → 2.63)" and on the spreadsheet `ROUND` convention.

## What the reference tool's own reports say (QC-2 — read everything first)

The intake holds three **Forensic Analysis Reports** from Fuse v8.11.0 with a committed golden on both
sides — the Large Test File pair and the two Hard_File pairs (`updated → updated2`, `updated2 →
updated3`). Per changed activity they print the field before, the change, a 2-dp ratio and the field
after, for Original Duration, Remaining Duration, Total Float, Free Float, Percent Complete, Start and
Finish. Against the goldens' exact values (integer working minutes over the 480-minute project day):

| measurement | population | result |
| --- | --- | --- |
| **M1** the whole-day fields (Original / Remaining Duration, Total Float) | LTF 752 / 773 / 1,297 rows; Hard_File 31 / 47 / 39 and 24 / 29 / 100 | **half-to-even on every comparable row.** Half-day ties of both parities are present (LTF 20 / 11 / 262); half-away-from-zero misses exactly the even-part halves (10 / 4 / 111 — Hard_File 3 / 4 / 6 and 1 / 1 / 1), truncation more. |
| **M2** the day change column | the same rows | **`rounded(after) − rounded(before)`**, never `round(after − before)`: the two disagree on 85 LTF float rows (1,216 of 1,297 under the rounded exact difference) and on Hard_File UID 37 (8.5 → 7 is shown −1, not −2). |
| **M3** the 2-dp ratio column (−change ⁄ before) | 1,494 numeric ratio rows; 15 exact ties, 11 discriminating | **ToEven on the SCALED value** (.NET `Math.Round(x, 2)`): 1/8 → 0.12, 9/8 → 1.12, 17/40 → 0.42, 1/40 → 0.02; half-up misses all 11. The 1/40 case separates the reference's rule from Python's correctly-rounded `round(x, 2)`: 0.025 sits ABOVE the tie in binary, so `round(0.025, 2) == 0.03` while Fuse prints 0.02 — the reference rounds the scaled double; `round(x * 100) / 100` reproduces it. |
| **M4** the Start / Finish change column | 2,384 Start + 1,516 Finish rows | **the calendar-day difference truncated toward zero**, 2,741 of 2,741 comparable rows; floor, half-even and the date-part difference each miss hundreds. |
| **M5** the metric values in the Summary / Metric History reports | 13,058 raw cells in the LTF Summary Metric DCMA Report | stored **RAW under Excel's `General` format** (1,309 of them at an exact 3-dp tie such as 1.725) — the export displays the raw value; Fuse pre-rounds nothing there. The "2.625 → 2.63" of D19 was an illustration: ADR-0141 itself records "no golden value sits on an exact half", and the logic-density parity pin is 2.79 / 2.81. |
| **M6** three Hard_File float rows the rule does not reproduce | UIDs 14 / 146 / 94 | **a divisor, not a rounding**: −3 / −1 / 2 shown for stored −4,320 / −1,440 / 2,190 minutes = the stored slack over the ACTIVITY's own day — a 1,440-minute task calendar ("24 Hours"), an elapsed duration, a 930-minute calendar ("Standard+Sat.") — where `acumen_whole_day_float` divides by the project's 480. Registered as **R-75** (below). |
| **M7** one LTF duration row | UID 5267 | **the model's own minute grid**: the file's duration is `PT107H59M36S` (13.4992 d, below the tie); the integer-minute model carries 6,480 (exactly 13.5). Fuse's 13 is half-even on the file's seconds. Named in the oracle, never excluded silently. |
| **M8** ties at the tool's displayed precisions in the corpus | 15 goldens, 7,935 non-summary activities | durations at 1 dp 49 / 2 dp 74; remaining 72 / 73; stored slack 1 dp 292 / 2 dp 191 / whole 447; lags 0 — the question is not hypothetical. |

MS Project's own display rule for a fractional duration or slack (it shows 2 dp — 1.13 or 1.12 for
nine hours on an eight-hour day?) is **UNVERIFIED**: the intake holds no MS Project-rendered export
(the seven short-named `.XLS` are Fuse Analyst / Summary / History reports). What settles it: an MS
Project view export carrying an odd-hour duration.

## Decision

1. **No flip.** The premise is refuted on a population: every rule the reference tool's own code
   applies at a tie is half-to-even, which is what `round()` is. Sweeping the display sites toward
   `round_half_up` would have moved the tool AWAY from the reference on every whole-day field and
   every code-rounded decimal Fuse prints, on the one figure class where a reference display exists.
   Where no reference display exists at the tool's precision (days at 1–2 dp, SRA / JCL percentages
   and ratios) the tool keeps the rule it already applies — correctly-rounded half-even — and says so.
2. **Every `round()` site is classified by exposure** in `tests/guards/round_site_ledger.tsv` (374
   rows: file, family, call text), tied to the tree by `tests/guards/test_round_site_ledger.py` — an
   added, moved or reworded site is unclassified until it is named there — and the twelve family
   counts are re-derived into the report's §4 census by `test_audit_report_wp8.py`. The families and
   their rules are the guard's `FAMILIES` table: `quantize` (65, the integer grid) ·
   `quantize_measured` (5, ADR-0474 / 0491 / 0502 / 0512) · `measured_field` (1,
   `acumen_whole_day_float`) · `whole_day` (15 — Fuse's field rule, M1) · `whole_pct` (12) ·
   `days_dp` (68 — MS Project UNVERIFIED) · `pct_dp` (50) · `value_dp` (119) · `tolerance` (6, the
   AI derivation gate) · `telemetry` (23) · `geometry` (9) · `axis_label` (1).
3. **The reference's rules are pinned as a parity oracle** —
   `tests/parity/test_fuse_forensic_rounding_oracle.py`: M1–M4 on all three reports with the
   populations, the tie counts and the alternatives refuted BY NAME; M6 and M7 named with their
   mechanism. Red first under three mutants of the rule under test (half-away: 19 / 10 / 119 rows red;
   the rounded exact difference: 806 → 783, 848 → 798, 1,436 → 1,351; the half-up ratio: 11 red).
4. **The tool's families are observable at a tie** — `tests/web/test_round_display_rule_at_ties.py`
   renders the payloads on a fixture built on the ties (a 0.25-day lag, a 1.25-day and a 1.125-day
   duration, JCL quadrants on sixteenths, a criticality index on thirty-seconds) and pins the
   half-even reading of each family beside the half-up reading it refuses; each pin observed red
   under a `round_half_up` mutant at its CALLER on a shadow copy of the package (mutcheck).
5. **MF-08 is left as it is, and its basis is restated honestly.** The 30 MetricResult sites round
   half-up by the spreadsheet convention; no Fuse-displayed metric value at a tie exists in the
   intake to measure it against (M5 — the exports carry raw values). It is parity-green because no
   golden metric sits on a tie, not because the reference was seen to round half-up. What would
   settle it: a Fuse GUI grid or a formatted export showing a metric value at an exact tie.
6. **R-75 registered (T1, S):** Fuse's whole-day Total Float field divides the stored slack by the
   activity's OWN day (M6); the engine's `acumen_whole_day_float` callers pass the project day. On the
   24-hour Hard_File the engine's DCMA-06 reads **2** (UIDs 302 / 385: 49,680 / 44,796 minutes are
   104 / 93 project-days but 34 / 31 days on their 1,440-minute calendar) where Fuse's ribbon reads
   **0** (`HA296F~1.XLS`, "6. High Float" 0 / 0; "7. Negative Float" 40 / 11 agrees either way).
   The mechanism is not yet decided: UID 146 has NO task calendar (an elapsed duration on the project
   calendar, its crew on a 1,440-minute one) and is still shown over 1,440 — the divisor may be the
   task calendar, the elapsed axis, or the crew's; decide it FIRST, on the corpus, before touching the
   helper (the LTF pair has no multi-calendar activity, so its 3,637-activity oracle cannot see it).

## Verification (QC-1 / QC-3)

Ten load-bearing assumptions were written down and attacked before the first edit (the plan is in the
session record): the census population (A1 — re-derived, 330 + 44; the guard names an added site and a
stale row in its negative control); every-row half-even beyond the LTF pair (A2 — held on both
Hard_File pairs; the residue is M6, named); the change rule (A3 — the alternative counted and
refuted); the scaled-ToEven ratio (A4 — held, incl. 1/40); D19 never observed (A5 — ADR-0141's own
sentence, the 2.79 / 2.81 pins, the `General`-format census); MS Project unmeasurable here (A6 — the
`.XLS` files identified by their sheets); pins that can fail (A7 — three oracle mutants and the
per-caller display mutants, each red by name); no `src/` change needed (A8 — none was: no display
site is a measured defect; docs + tests only, no version bump); the report guard tolerates new census
rows (A9 — red by name with the thirteen keys before the rows existed, green after); the divisor
finding is real and out of scope (A10 — the calendars read from the goldens, the DCMA-06 move
counted, registered).

Fell: the row's premise (a display-site sweep), MF-08's "Fuse-measured" basis (an illustration), and
the first oracle draft's grid reader (a deleted activity's empty after cell let the ratio slide into
the after position — 1,510 rows instead of 1,436; the reader is positional now, and the population is
pinned).

## Deliberately NOT done

A `round_half_up` sweep of any family (refuted, M1–M3) · reverting MF-08 (no tie oracle either way;
parity-green; restated, not moved) · a 2-dp precision change for the days families toward MS Project's
display (a presentation change with its own DoD, and MS Project's tie rule is unverified) · the
divisor fix (R-75 — mechanism first) · the Free Float sheet (the model carries no stored free float
field — R-74's row) · reading the tool's own `round(x, 2)` as the reference's `round(x * 100) / 100`
(they differ only on decimal-looking near-ties such as 0.025, none of which the tool prints from a
Fuse figure).

## Consequences

R-04 CLOSED with a refuted premise and a guarded classification; R-75 registered ahead of R-73 in the
T1 queue by evidence in hand (an oracle the engine currently fails: 2 vs 0). No shipped figure moves.
Version **1.0.279** unchanged (docs + tests only); highest ADR 0515.
