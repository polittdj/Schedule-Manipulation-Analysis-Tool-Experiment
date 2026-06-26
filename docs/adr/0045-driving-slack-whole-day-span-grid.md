# ADR-0045 — Driving slack on SSI's whole-day grid (span-snap)

Date: 2026-06-16 · Status: accepted

## Context

The operator compared the tool's Path Analysis against **SSI's Directional Path Tool** on a
large real schedule (`Large Test File.mpp` — "USA OTB Master IMS", 1723 activities). SSI's
driving path (Path 01, slack 0), near-path 2 (Path 02), and near-path 3 (Path 03) did **not**
match the tool's DRIVING / SECONDARY / TERTIARY tiers: activities SSI placed on the 0-slack
driving path (e.g. UID 6997, 5571) the tool tiered as SECONDARY (1 day), and SSI's 9- and
13-day near-path activities read 10 and 14 in the tool — a consistent **~+1-day** error on a
long chain.

**Root cause.** Real stored dates carry ragged **times of day** — this schedule mixes
08:00–17:00 activities with afternoon-shift activities stored 13:00→12:00. A "1-day"
afternoon activity therefore has a working **span of 420 minutes**, not 480. The
driving-slack backward pass subtracts each successor's span to propagate late dates; left
raw, the 60-minutes-short spans **accumulate** down a long chain and, summed, tip the
upstream chain's whole-day slack across a day boundary (≈540 minutes → floors to 1 day). SSI
computes on a whole-working-day grid, so it never accumulates the sub-day raggedness and
reads the chain as 0. (The short completed chain in the TP1 parity case stayed under a day,
which is why the prior floor-at-display approach matched TP1 but failed this larger file.)

## Decision

**Snap each activity's SPAN to the nearest whole working day** for the driving-slack backward
pass (`compute_driving_slack`):

```python
span = {uid: round((early_finish[uid] - early_start[uid]) / per_day) * per_day for uid in trace}
```

This stops the cross-activity accumulation (every span is a clean whole-day multiple) while
leaving each activity's own `early_finish` **phase intact**, so its residual sub-day slack
still floors onto the correct SSI day. Two properties matter:

- **Not** snapping `early_finish` itself (an earlier attempt) over-corrected: it shifted TP1's
  completed-chain activities from sub-day DRIVING to a full day SECONDARY, breaking the
  validated parity. Snapping only the span preserves TP1 exactly (13 / 1 / 2 / 2 tiers) **and**
  fixes the large file.
- The Path page still **displays** the true stored dates — `date_basis` is unchanged; only the
  span consumed by the slack pass is snapped.

> **Erratum (2026-06-26, audit F-07).** "matches SSI exactly" below refers to the **relative tier
> spacing** (0 / 9 / 12 / 13) across the compared activities — the property this span-snap fixes — **not**
> the *absolute* driving-slack values. As `docs/PARITY-REPORT.md` (§"Large File") records, the absolute
> Large-File values are **not** reproducible from repo artifacts because SSI's target/focus UniqueID was
> never recorded (the global-finish milestone UID 6077 leaves the chain at ~514 working days of float, so
> SSI evidently targeted an earlier milestone). PARITY-REPORT.md is authoritative on this open limitation;
> this Verification section overstates it. Action still open: record SSI's focus UID next time the file is
> in hand.

## Verification

- **Large Test File** reproduces SSI's relative tier spacing on every compared activity (see the erratum
  above re: absolute values): the driving path
  reads 0 (UID 6509/6514/6997/5571/5738…), Path 02 reads 9 (UID 5539/5542), Path 03 reads 12
  (UID 7543/7544) and 13 (UID 6533).
- **TP1 (validated SSI parity)** unchanged at the tier level: 13 DRIVING / 1 SECONDARY /
  2 TERTIARY / 2 BEYOND; the completed-chain activities still read DRIVING (their sub-day
  phase now carries as the span-snapped remainder, e.g. 60 min, still flooring to day 0).
- `pytest -m parity` **10/10**; full suite **813 passed**; the curated goldens are day-aligned
  so the snap is a no-op (parity-safe).

## Scope / safety

A surgical change to the slack span only; displayed dates, the CPM, and the metric set are
untouched. `round()` resolves an exact half-day span to the nearest even day — a rare edge on
real data and never hit by the day-aligned goldens. Regression pinned in
`tests/engine/test_driving_slack_daygrid.py` plus the updated TP1 battery test.
