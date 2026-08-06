# ADR-0353 — The legacy SRA shares one duration basis and one date axis (SRA-LEGACY closed)

**Status:** Accepted · **Date:** 2026-08-06 · **Extends:** ADR-0106, ADR-0123, ADR-0256, ADR-0309 ·
**Closes:** `audit/SRA-ROOTCAUSE-20260730.md` §6's carried "legacy `/sra` cross-basis defect"
(external audit P2 item "SRA-LEGACY", reserved for Fable 5 Max under ADR-0240).

## Context

`compute_sra` — the legacy whole-project Monte-Carlo behind `/api/sra` and
`/api/scorecards/buffer` — predates the SSI path's one-basis contract (`sra.py`'s
`compute_sra_ssi`: *"the simulation, the anchor and the percentile share one basis"*). It carried
two orthogonal defects, both measured on committed goldens before any code was written:

**Leg A — basis mismatch.** `_build_result` took `deterministic = cpm.project_finish` (the
ordinary **full-duration** CPM) and bisected it against finishes sampled from
`_three_point`'s **remaining**-duration basis. On a progressed file whose in-progress tasks carry
no stored `Resume` reschedule (so ADR-0309's floor never engages), the anchor sits above nearly
every sample and `deterministic_percentile` saturates — the realism card then calls a progressed
plan "conservative":

| golden | in-progress / with resume>stop | det_pct before | after |
|---|---|---|---|
| EVM1 | 2 / **0** | **0.9910** ("conservative — 99% finish by then") | **0.4930** ("coin flip") |
| EVM2 | 1 / 1 | 0.4790 | 0.4790 (unchanged) |
| Project2 | 3 / 3 | 0.4900 | 0.4900 (unchanged) |
| Project5 | 2 / 2 | 0.5310 | 0.5310 (unchanged) |

The three resume-floored goldens move **zero** — ADR-0309 already converged their bases (measured
gap det−all-ML = 0.0 wd) — so the blast radius is exactly the resume-less progressed class.

**Leg B — date-axis mixing.** Every legacy date left the tool through a **naive**
`offset_to_datetime` (the result's `*_date` fields, `_sra_data`'s S-curve/histogram/mean/marker
conversions, `reserve_recommendation`'s row dates), while the operator's committed date lives on
the **stored** plan-date axis. Pure-CPM offsets pack completed work at the project start, so the
naive conversion lands early — `stored_finish_correction` measured **15 days 1 h** on Project2,
2 d 5 h on EVM2 — and the buffer route compared a stored-axis committed date against the packed
CDF. One JSON response mixed three reference frames. The failure is in the **optimistic**
direction, the dangerous one for a reserve panel:

| Project2, committed = stored plan finish 2027-09-14 | before | after |
|---|---|---|
| committed_confidence | **1.0000** | **0.4900** |
| recommended P80 reserve | **0.0 wd** | **2.4 wd** |
| P50…P90 row dates | 2027-08-31…09-03 (naive) | 2027-09-15…09-18 (stored axis) |

(EVM2: confidence 1.0000 → 0.981; Project5: 0.858 → 0.531. `sra_conclusions`' commitment card on
Project2 moved from "P50 08-31 / P80 09-02" to "P50 09-15 / P80 09-17".)

Why this is fixable now when ADR-0108's two attempts failed: nothing here reschedules any work.
The anchor construction and the constant display correction are the SSI path's own mechanics,
already validated against the SSI oracle (deterministic percentile 6.65% vs oracle 5.75%,
ADR-0309's root-cause file §0).

## Decision

1. **`compute_sra` computes its own anchor and no longer accepts one.** The anchor is the
   **all-ML solve** — `compute_cpm(schedule, duration_overrides={uid: _ml_minutes(t)})` — the
   byte-identical instrument to `deterministic_margin_bounds`' D and `compute_sra_ssi`'s
   `ml_finish`. The `cpm` parameter is **removed** (not deprecated): the defect class "hand the
   legacy path a foreign-basis anchor" becomes structurally unrepresentable. On an unprogressed
   schedule the all-ML solve equals the plain CPM finish (the ADR-0106 equivalence, pinned by
   test), so the entire synthetic suite is byte-identical.
2. **The legacy result's dates realign to the stored plan axis** — `_build_result` applies
   `stored_finish_correction(schedule, None, deterministic)` (anchor: the latest stored finish;
   zero when the file stores none), exactly ADR-0256's pattern. The deterministic date lands on
   the stored plan finish by construction; relative spacing is unchanged. `_sra_data` applies the
   same helper to its cdf/histogram/mean/marker conversions, and
   `reserve_recommendation` gains keyword-only `date_correction` for its rendered dates while the
   buffer route converts the operator's committed date through the same constant
   (`end_of_day − correction`) so confidence and reserve compare like with like.
3. **`sra_conclusions` is untouched.** Its offset arithmetic (`p80 − det_finish`) became
   same-basis automatically with leg A; its date strings flow from the corrected fields.

The mode multiplier (`auto_most_likely`) and manual override MLs deliberately do **not** move the
anchor: the anchor is the *plan* (all-ML), the dials shape the *uncertainty* — matching SSI, and
keeping "how realistic is the plan?" an honest question when the dials are off 1.0.

## Verification

- **The simulation itself is untouched**: sampled p10/p50/p80/p90 offsets are byte-identical
  pre/post on all four goldens; det_pct identical to 4 dp on the three resume-floored ones.
- **Five mutations, each fired exactly its guard** (original-anchor-absent re-read after each,
  restored from scratchpad copies): anchor reverted to `compute_cpm(schedule)` → the new basis
  test + both web pins; engine correction zeroed → the date-axis test; reserve row correction
  dropped → the scorecards pin; `_sra_data` correction zeroed → the `/api/sra` pin; committed
  converted naively → the buffer pin.
- New pins: `tests/engine/test_sra.py` (progressed-chain basis + date-axis + inert-where-it-should-be),
  `tests/engine/test_scorecards.py` (correction shifts dates, never offsets/confidence),
  `tests/web/test_sra_stored_axis.py` (end-to-end: `/api/sra` deterministic date == latest stored
  finish, percentile 15–85; buffer confidence < 0.5 with positive P80 reserve one working day
  before the anchor). Full gate + `pytest -m parity` (49 passed) green.

## Consequences

- On progressed files the whole legacy SRA surface (S-curve, histogram, percentile cards,
  conclusions, reserve rows) moves onto the stored plan-date axis — the same axis as
  `/api/margin/risk` and the SSI page, closing the audit's "two axes for the same file".
- EVM2's deterministic date now displays the stored **2012-10-04** — the anchoring absorbs
  ADR-0108's known 2-wd unstarted-successor residual into the *display*, exactly as the SSI path
  already does by design; the residual remains visible in offset space and stays recorded.
- The correction's fidelity is **day-scale**: a sub-day constant (EVM1: 7 h) slides datetimes
  within the day, so an end-of-committed-day confidence can legitimately exceed the at-the-anchor
  percentile (EVM1 reserve reads 0.991 vs det_pct 0.493 — different questions, one axis).

## Deliberately NOT done

- **The XER importer still has no `resume` read** (P6 stores suspend/resume differently) —
  carried unchanged from the root-cause file §6; unmeasured there, unmeasured here.
- **`_hidden_drivers`' qualitative use of the ordinary CPM float** to label "the deterministic
  plan calls this non-critical" was examined and left: no figure or date crosses an axis; it is a
  classification, not a number, and the ordinary solve remains the tool-wide float instrument.
- **The ADR-0307 Best-Case artifact conflict** recorded in the root-cause file §6 stands as
  recorded; nothing here touches factor→BC/WC.
