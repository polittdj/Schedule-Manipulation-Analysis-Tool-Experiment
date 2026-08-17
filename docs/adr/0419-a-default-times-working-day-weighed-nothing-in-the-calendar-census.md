# ADR-0419 — IMP-01: a "default times" working day weighed nothing in the calendar census

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** IMP-01 (audit 2026-08-16) ·
**Ships:** `importers/mspdi.py`

## Context

The ledger's IMP-01 row said only *"two importer interpretations that materially move every
displayed number (a fallback path)"*. No detail survived anywhere in the repo — the finder's
output was lost with the round-3 pool — so the claim had to be **re-derived from source** rather
than confirmed from testimony (QC-2: an inherited claim is testimony, not evidence).

`_parse_calendar` builds the project calendar from the MSPDI `WeekDays` grid. It reads a
`DayWorking=1` weekday **two different ways, four lines apart**:

```python
minutes = sum(end - start for start, end in segments)
if minutes > 0:                       # <- a day with no usable WorkingTimes contributes NOTHING
    day_totals.append(minutes)
...
# a DayWorking day with no WorkingTimes means "the default times" (480) in MS Project
minutes_per_day = dominant_day_minutes(day_totals) or MINUTES_PER_DAY   # <- ...but is worth 480
```

Both readings cannot be right. Whatever a default-times day is worth, it cannot be worth 480 when
it is the only kind of day present and 0 when it is not.

## The measurement

The two readings **agree** on a uniform calendar and **diverge** the moment one mixes, because the
invisible days cannot outvote anything — the minority explicit day wins the census outright:

| calendar | census the code sees | min/day | an 80-working-hour task displays as |
| --- | --- | --- | --- |
| A. all five days explicit 8 h (control) | `[480]*5` | 480 | 10.00 d |
| B. all five days default-times (control) | `[]` → `or 480` | 480 | 10.00 d |
| C. Mon explicit **4 h**, Tue–Fri default | `[240]` | **240** | **20.00 d** (should be 10.00) |
| D. Mon explicit **10 h**, Tue–Fri default | `[600]` | **600** | **8.00 d** (should be 10.00) |

Case C is a **2× error on every duration-in-days figure in the file** — the presentation boundary
divides by `working_minutes_per_day`, so it moves every displayed duration, every float in days,
and every DCMA threshold expressed in days.

A second route reaches the same hole: `working_time_span` documents `08:00 → 08:00` as a genuine
zero-length span and returns `None`, so a day that declares `WorkingTimes` which all parse to
nothing also lands on `if minutes > 0` and vanishes from the census.

## Reachability — measured, and it is LATENT

Before treating this as an active defect, the corpus was censused for the construct: **56 real
MSPDI documents** (every committed MSPDI-rooted file found by content sniff, plus 25 MPXJ
conversions of the committed `.mpp` reference files) were scanned for a `DayWorking=1` weekday
that contributes nothing.

**Zero occurrences.** MPXJ always emits `WorkingTimes` for a working day, and no committed
fixture or reference export carries the shape. So IMP-01 is **latent, not active** — it is
reachable only from an MSPDI document the corpus does not contain. It is fixed because it is
wrong and cheap to make consistent, not because it is currently biting.

## Decision

Move the "a default-times day is worth the default day" rule into the **one** place that counts
days, and leave the fallback below as a type-narrowing floor rather than a second copy of the
semantic:

```python
if minutes <= 0:
    day_totals.append(MINUTES_PER_DAY)
    continue
```

**What this deliberately does NOT do.** MS Project's "default working times" are really a
project-level setting, carried in MSPDI as `<MinutesPerDay>` and already parsed into
`Calendar.declared_minutes_per_day` (ADR-0354/0355). Using *that* as the implicit day's length
would arguably be more faithful — but it is parsed **after** the calendar is built, ADR-0355
deliberately keeps it a separate axis from `working_minutes_per_day`, and choosing between 480 and
the declared value needs an oracle this repo does not have (a real MS Project file exhibiting the
construct). **That question stays UNVERIFIED and is unchanged by this ADR** — the fix makes the
two existing readings one reading; it does not change what that one reading says.

## Verification

* **Red first.** Three new tests in `tests/importers/test_mspdi.py`; two observed failing at
  `240 != 480` on both routes, with the uniform-calendar controls green in the same run (so the
  fix is not "hardcode 480 everywhere"). No prior helper could even build the shape —
  `_weekday(day_type)` with no spans emits `DayWorking=0`, which is why it was untested.
* **Mutation battery 5/5 killed by name**, every mutant confirmed `landed: True` first: reverting
  the fix · weighing the day 1 min · weighing it 600 · covering only the no-`WorkingTimes` route
  and not zero-length spans · letting the floor win instead of the census.
* **Corpus no-op, proven not assumed.** The parsed project calendar of all **83** documents
  (56 with calendars) was dumped under a patched worktree and a pristine one and diffed:
  **identical**. `pytest -m parity` **72 passed / 0 failed** — no parity value moves.
* Batteries ran in a detached worktree, never in the tree under measurement.
