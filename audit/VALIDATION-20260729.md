# VALIDATION — outside-auditor claims V1–V7

**Date:** 2026-07-29
**Commit verified:** `9a1e5601746c3d5fc1f1ca97c9a12bd517a6fca1`
**Role:** adversarial verification engineer. Nothing below is accepted on reasoning; every verdict
carries a script that was executed and its verbatim output.

---

## STEP 1 — DRIFT

```
$ git rev-parse HEAD
9a1e5601746c3d5fc1f1ca97c9a12bd517a6fca1

$ git log --oneline 9a1e5601746c3d5fc1f1ca97c9a12bd517a6fca1..HEAD
(no output)

$ git rev-list --count 9a1e5601746c3d5fc1f1ca97c9a12bd517a6fca1..HEAD
0
```

**Zero commits have landed since the audit base.** `HEAD` *is* commit `9a1e560`, working tree clean.
Everything below was verified at exactly the commit the outside auditor (ChatGPT Codex) examined, so
no finding can be explained away as drift.

Environment note: the repo's runtime deps were not installed in this container. `pip install -e .`
(pydantic/fastapi/uvicorn — all declared `dependencies`) and `pip install "httpx>=0.27"` (a declared
**dev-only** dependency, `pyproject.toml:80-82`, which backs starlette's `TestClient` and is
explicitly forbidden from entering runtime `dependencies` by the egress guard) were installed to make
execution possible. No repo file was touched; `src/schedule_forensics.egg-info/` is gitignored
(`.gitignore:89`).

---

## SUMMARY TABLE

| # | Claim | Verdict | Changes a displayed number? |
|---|-------|---------|------------------------------|
| V1 | non-numeric days → 0.0 with `days_locked=True`; route shows no error | **CONFIRMED** (and worse than claimed) | Yes — SRA outputs |
| V2 | `avg_rem == 0` → 10-day risk stores 0%; two models disagree | **CONFIRMED** | Yes — legacy SRA model |
| V3 | unknown unit → 480 min/unit; elapsed literals read as working days; changes a metric count | **CONFIRMED** (one wording correction on the docstring half) | Yes — filtered population |
| V4 | unresolvable project calendar → 8h/Mon-Fri default with **no** log line | **CONFIRMED** | Yes — every duration-in-days |
| V5 | `resources.py:171` `or 1.0` turns `max_units=0.0` into `1.0` | **PARTIAL** — coercion confirmed; the claim's "suppresses over-allocation" half is **REFUTED** (it is the only reason such a resource flags at all) | Yes — "Max units" + capacity |
| V6 | `capacity_minutes > 0` guard makes over-allocation unreportable at zero capacity | **CONFIRMED** — including the hard case, reproduced 3 ways | Yes — `over_allocated_periods` |
| V7 | `hours_per_day=0` → 480; `work_weekdays=[]` → Mon-Fri | **CONFIRMED** | Yes — every duration-in-days |

**Two claims did not survive intact.** V3's *behaviour* is confirmed but its "contradicts its
docstring" framing is an overstatement. V5's coercion is confirmed but its part (c) — that the
coercion suppresses over-allocation — is **refuted**: the opposite is true, and the intuitive
one-line fix would make the reported numbers worse. Both corrections were reached by execution, and
V5's was reached by an adversarial verifier disagreeing with my own first pass, then independently
re-run by me before being accepted.

---

## V1 — non-numeric days entry → 0.0, locked, silently saved

**Verdict: CONFIRMED.** The claim holds on both halves. I originally headlined this "worse than
claimed"; an adversarial verifier pushed back on that framing and I have narrowed it — the lock
described in (b) is a real, executed amplifier of the same defect, not a second defect.

Script: `/tmp/audit-verify/lead_v1.py`, `/tmp/audit-verify/lead_v1b.py`,
`/tmp/audit-verify/lead_v1_route.py`

### (a) Function level

`web/app.py:13708` `_reconcile_magnitudes` parses via `_to_float(days_str, 0.0)`
(`_to_float` returns the default on `ValueError` and on non-finite input):

```
=== _reconcile_magnitudes on bad input (avg_rem=10.0) ===
  days_str='abc'      -> (0.0, 0.0, True, False)
  days_str='ten'      -> (0.0, 0.0, True, False)
  days_str='5 days'   -> (0.0, 0.0, True, False)
  days_str='1,5'      -> (0.0, 0.0, True, False)
  days_str='10'       -> (10.0, 100.0, True, False)
  days_str='nan'      -> (0.0, 0.0, True, False)
  days_str='inf'      -> (0.0, 0.0, True, False)
```

Note `'5 days'` and `'1,5'` — a European decimal comma and a unit suffix are *plausible operator
input*, not exotic typos, and both silently become `0.0`.

### (b) The part the claim understates — the typo LOCKS the zero

`dl = days_locked or days is not None`. Because `_to_float` returns `0.0` rather than `None` for a
typo, `days is not None` is True, so **the field is marked "operator supplied this explicitly"** and
the derivation that would have rescued it is skipped:

```
  (days_locked passed as FALSE in every case below)
  good days='10',  pct='' , avg_rem=5 -> (10.0, 200.0, True, False)
  good days='' ,   pct='50', avg_rem=5 -> (2.5, 50.0, False, True)
  TYPO days='abc', pct='50', avg_rem=5 -> (0.0, 50.0, True, True)
```

Row 3 is the finding: the operator supplied a perfectly valid **50%**, and the function had
everything it needed to derive `days = 2.5`. The typo in the *other* field suppressed that
derivation and locked `0.0` in its place.

### (c) Route level — driven through the real FastAPI app

`POST /sra/risk-register` (`web/app.py:5758`) appends the `UnifiedRisk` unconditionally under
`if label and valid:` and returns `RedirectResponse(url="/sra", status_code=303)`. There is no
validation branch. Driven with `TestClient`:

```
=== case A: VALID entry, 10 days on a live activity (control) ===
   HTTP 303  location=/sra
=== case B: TYPO 'ten' in impact days ===
   HTTP 303  location=/sra
=== case C: TYPO in days but a VALID 50% supplied ===
   HTTP 303  location=/sra
=== case D: valid 10 days, but affected = a MILESTONE (avg_rem == 0) ===
   HTTP 303  location=/sra

=== what is now stored in the register ===
   id=R1 name='valid'      impact_days=  10.0 impact_pct= 200.0 days_locked=True pct_locked=False
   id=R2 name='typo'       impact_days=   0.0 impact_pct=   0.0 days_locked=True pct_locked=False
   id=R3 name='typo+pct'   impact_days=   0.0 impact_pct=  50.0 days_locked=True pct_locked=True
   id=R4 name='milestone'  impact_days=  10.0 impact_pct=   0.0 days_locked=True pct_locked=False

=== does the /sra page show ANY error/warning about the typo? ===
   'invalid'      occurrences in /sra HTML: 0
   'error'        occurrences in /sra HTML: 0
   'could not'    occurrences in /sra HTML: 0
   'not a number' occurrences in /sra HTML: 0
   'ignored'      occurrences in /sra HTML: 0
   'typo' risk row rendered on the page: True
```

**Answer to the claim's question:** the route shows the user **no error**. A typo silently saves a
zero-impact risk that renders as a normal row in the register. The operator's own risk list tells
them the risk is recorded; the simulation behaves as though it does not exist.

### (d) Corroboration from an independent verifier — two things I did not test

An adversarial verifier re-ran this claim with its own hand-rolled ASGI driver and added two results
that strengthen it:

* **A true Excel round-trip.** It exported the app's own template via
  `GET /export/xlsx/risk-register-template` (200, 6619 bytes), filled it, and re-imported. The app
  reported *"Imported 3 risk(s); skipped 0 incomplete row(s); dropped 0 unmatched UID(s)"* with
  `impact_days=0.0` stored. The skip counter at `app.py:13899` is `if not name or not valid:` — it
  provably cannot count a bad *number*, so the import's own reassurance ("skipped 0") is what the
  operator reads while the figure is silently zeroed.
* **The zeroed risk still ranks as maximum severity.** `/api/sra/ssi` reports the 0-day risk with
  `probability_rating: 5, consequence_rating: 5, hits: 794` — it occupies the **top-right cell of
  the 5×5 risk matrix** while contributing zero days to the simulation. The most visually alarming
  cell on the page is filled by a risk the model treats as inert.

It independently found the same European-decimal trigger (`10,5` → `0.0`), reached from a plain
numeric keypad rather than a typo.

The Excel/CSV import path (`app.py:13904`) calls the same helper with `days_locked=True` hardwired
and no percent string, so a typo'd cell behaves identically — with the same absence of an error.

---

## V2 — `avg_rem == 0` stores 0%, and the two SRA models disagree

**Verdict: CONFIRMED.** Script: `/tmp/audit-verify/lead_v2.py`, `/tmp/audit-verify/lead_v2b.py`

### The two models are named by the code itself

`web/state.py:210-218` (the `UnifiedRisk` docstring): *"an additive `impact_days` (the SSI model)
and a multiplicative `impact_pct` uplift (the legacy model) … turned into the engine's frozen
`ScheduleRisk` (from `impact_days`) and `RiskEvent` (from `impact_pct`)"*. The two converters are
`_schedule_risks` (`app.py:13661`) and `_risk_events` (`app.py:13640`).

### Executed proof of the disagreement

```
operator typed 10 days, avg_rem=0.0 -> days=10.0 pct=0.0 dl=True pl=False

LEGACY multiplicative model (RiskEvent, reads impact_pct):
   impact_low=1.0  impact_ml=1.0  impact_high=1.0
   -> multiplier 1.0 means duration x1.0 = NO IMPACT AT ALL

SSI additive model (ScheduleRisk, reads impact_days):
   impact_days=10.0  probability=1.0
   -> adds 10.0 working days

DISAGREEMENT: YES - same operator-entered risk; SSI applies 10.0d, legacy applies 0d.

=== contrast: avg_rem = 5.0 (the healthy path) ===
   days=10.0 pct=200.0 -> multiplier 3.0 (x3.0) - both models see the risk
```

Both magnitudes do reach both models, and they disagree: one simulation carries a 10-working-day
risk, the other carries nothing, from a single register entry.

### Reachability — this is not a corner case

`_affected_avg_remaining_days` (`app.py:13686`) averages the affected leaf tasks' remaining
duration. It returns `0.0` whenever every affected activity has zero remaining duration:

```
risk on a MILESTONE only             uids=[1] -> avg_rem = 0.0
risk on a 100%-COMPLETE activity     uids=[2] -> avg_rem = 0.0
risk on milestone + completed        uids=[1, 2] -> avg_rem = 0.0
risk on a live activity (control)    uids=[3] -> avg_rem = 5.0
risk on milestone + live (mixed)     uids=[1, 3] -> avg_rem = 2.5
```

**A risk mapped to a milestone is the single most natural risk-register entry in forensic
scheduling** ("risk to Substantial Completion"). Case D of the V1 route run above is precisely this,
driven through the real endpoint: `impact_days=10.0, impact_pct=0.0`.

---

## V3 — unknown/elapsed duration literals

**Verdict: CONFIRMED in substance, with one correction to the claim's wording.**

Script: `/tmp/audit-verify/lead_v3.py`

### (a) Unknown unit → 480 min/unit — CONFIRMED; the "docstring claims" framing — PARTIAL

```
   '5 xyz'      -> 2400
   '5 zz'       -> 2400
   '3'          -> 1440
   'abc'        -> None
   ''           -> None
```

An unknown unit does return 480 min/unit (`_DUR_UNIT_MINUTES.get(unit, 480)`,
`engine/msp_filters.py:68`). **But the docstring is not actually contradicted.** It says *"`None` if
unparsable"*, and genuinely unparsable input (`'abc'`, `''` — a regex non-match) *does* return
`None`. An unknown *unit* is parsable; that case is covered by the inline comment on the same line,
`# unknown/elapsed unit → treat as days`. Reporting this as a docstring contradiction would be a
pedantic overstatement. The behaviour is real and documented; the *consequence* is the finding.

### (b) Elapsed literals silently evaluate as working days — CONFIRMED

The regex `^\s*([\d.]+)\s*(e)?([a-z]*)\s*$` captures the elapsed marker in group 2 and **discards
it**. In MS Project an elapsed duration is calendar time (`2ed` = 48 clock hours through nights and
weekends); here it is read as 2 × 8h working days:

```
   '2 ed'   -> code returns     960 working min (  2.00 wd); TRUE elapsed span =    2880 clock min  => understated 3.0x
   '3 ewks' -> code returns    7200 working min ( 15.00 wd); TRUE elapsed span =   30240 clock min  => understated 4.2x
   '1 emo'  -> code returns    9600 working min ( 20.00 wd); TRUE elapsed span =   43200 clock min  => understated 4.5x
```

`'2 ed'` and `'2 d'` return byte-identical values (960).

### (c) Does it change a metric count? — CONFIRMED

Through a real `SavedFilter` with a DURATION criterion, applied via `msp_filters.select`, over a
population of 8 tasks at 1–8 working days:

```
   filter 'Duration > 2 d   ' -> 6 tasks match  uids=(3, 4, 5, 6, 7, 8)   [working 2d = 960 min]
   filter 'Duration > 2 ed  ' -> 6 tasks match  uids=(3, 4, 5, 6, 7, 8)   [operator MEANT elapsed 2d = 2880 clock min (= 6 working d)]
   filter 'Duration > 6 d   ' -> 2 tasks match  uids=(7, 8)   [what a CORRECT elapsed reading would compare against]
   filter 'Duration > 2 xyz ' -> 6 tasks match  uids=(3, 4, 5, 6, 7, 8)   [unknown unit, silently 2 days]
```

**6 tasks vs 2 — a 3× swing in the filtered population**, with no warning. Every metric computed
over a filtered population (a DCMA percentage, a count, a ratio) inherits the wrong denominator.

---

## V4 — unresolvable project calendar defaults silently

**Verdict: CONFIRMED, in both importers.** Script: `/tmp/audit-verify/lead_v4.py`

The claim's nuance is exactly right. There are two distinct paths:

* **The exception path logs.** `importers/mspdi.py:302-305` and `importers/xer.py:583-586` wrap
  `_project_calendar` in `try/except` and emit
  `logger.warning("unreadable project calendar; using the standard 8h/Mon-Fri default")`.
* **The unresolvable path does not.** Inside `_project_calendar`, MSPDI returns
  `cal or Calendar()` (`mspdi.py:312`) and XER returns a bare `Calendar()` on `if not rows:` and on
  `row is None` (`xer.py:590-599`). No exception is raised, so nothing is logged.

Log capture at `DEBUG` on both the `schedule_forensics` logger and the root logger:

```
=== MSPDI ===
  CalendarUID=999 (DANGLING, unresolvable)
     -> wmpd=480 weekdays=(0, 1, 2, 3, 4) name='Standard'
     -> LOG RECORDS CAPTURED: *** NONE ***
  no CalendarUID element at all
     -> wmpd=480 weekdays=(0, 1, 2, 3, 4) name='Standard'
     -> LOG RECORDS CAPTURED: *** NONE ***
  structurally broken calendar (exception path)
     -> wmpd=480 weekdays=(0, 1, 2, 3, 4) name='Standard'
     -> LOG RECORDS CAPTURED: WARNING:schedule_forensics.importers.mspdi:unreadable project calendar; using the standard 8h/Mon-Fri default

=== XER ===
  PROJECT.clndr_id=999, no default_flag=Y row
     -> wmpd=480 weekdays=(0, 1, 2, 3, 4) name='Standard'
     -> LOG RECORDS CAPTURED: *** NONE ***
  no CALENDAR table at all
     -> wmpd=480 weekdays=(0, 1, 2, 3, 4) name='Standard'
     -> LOG RECORDS CAPTURED: *** NONE ***
```

The third MSPDI case proves the two paths genuinely differ — same 8h/Mon-Fri result, but that one
logs.

**Forensic consequence.** The dangling-UID fixture above is not empty: it *contains* a real calendar
(UID 1) declaring `08:00–18:00`, a **10-hour** working day. The project points at UID 999, which does
not exist. The tool analyses that schedule as 8h/Mon-Fri and says nothing. Durations are stored in
working minutes and divided by `working_minutes_per_day` at the presentation boundary, so every
duration-in-days figure on every page is overstated by 25% — silently.

---

## V5 — `max_units=0.0` becomes `1.0`

**Verdict: PARTIAL** — the coercion is confirmed; the claim's part (c) is refuted (see below).
Scripts: `/tmp/audit-verify/lead_v5_v7.py`, `/tmp/audit-verify/lead_v5_adjudicate.py`

`engine/resources.py:171`:
```python
max_units = (res.max_units if res is not None and res.max_units is not None else 1.0) or 1.0
```

The ternary already handles `None`. The trailing `or 1.0` can therefore only ever fire on a value
that is present and falsy — i.e. exactly `0.0`.

**Zero is a legal input.** `model/resource.py:34` is
`max_units: float | None = Field(default=None, ge=0.0)` — `ge`, not `gt`. The model deliberately
admits `0.0`.

```
  source max_units=0.0    -> ResourceLoad.max_units=1.0  buckets=[('2026-01-05', 480.0, 960.0, True)]
  source max_units=0.5    -> ResourceLoad.max_units=0.5  buckets=[('2026-01-05', 240.0, 960.0, True)]
  source max_units=1.0    -> ResourceLoad.max_units=1.0  buckets=[('2026-01-05', 480.0, 960.0, True)]
  source max_units=None   -> ResourceLoad.max_units=1.0  buckets=[('2026-01-05', 480.0, 960.0, True)]
```

A resource declaring **zero capacity** is given a full unit — 480 minutes/day of capacity that does
not exist. `max_units=0.0` and `max_units=1.0` become indistinguishable, and a declared-zero
resource is reported with the same capacity as a full-time one. Forensically, `max_units=0` is how a
placeholder or a departed crew is modelled.

**Reachability (real, not theoretical).** MSPDI `<MaxUnits>0</MaxUnits>` survives import as `0.0`
(`mspdi.py:814` → `parse_float`, which maps only None/empty/NaN/Inf to `None`), as does the tool's
own JSON importer (`json_schedule.py:230-232`). XER never passes `max_units` at all
(`xer.py:693-712`), so Primavera resources arrive as `None` and take the `else 1.0` branch — a
different default, not this defect.

### Correction to the claim's part (c) — the fix direction is the opposite of the obvious one

The claim asserts the coercion *suppresses* a real over-allocation. **That is backwards, and I
verified the correction by execution** (`/tmp/audit-verify/lead_v5_adjudicate.py`). Because
`ResourcePeriod.over_allocated` requires `capacity_minutes > 0` (the V6 guard), a *true* zero
capacity makes every bucket unreportable:

```
booked 960 min/day against a DECLARED-ZERO-capacity crew (load > 1 unit-day)
   SHIPPED (or 1.0):        cap= 480.0 load= 960.0 over=True
   `or 1.0` REMOVED only:   cap=   0.0 load= 960.0 over=False
   => flag LOST  <-- removing line 171 alone SUPPRESSES a real over-allocation

booked 240 min/day against a DECLARED-ZERO-capacity crew (load < 1 unit-day)
   SHIPPED (or 1.0):        cap= 480.0 load= 240.0 over=False
   `or 1.0` REMOVED only:   cap=   0.0 load= 240.0 over=False
   => no flag either way <-- truly over-allocated (0 capacity) but never reported
```

So the `or 1.0` is currently the **only** reason a zero-capacity, heavily-booked resource is flagged
at all. What it genuinely corrupts is *provenance and severity*: `/resources` prints "Max units 1"
for a file that says 0, and reports a finite 2× over-allocation where the file's own statement means
the work is entirely unresourced. The real suppression lives in V6's guard, not here.

**Consequence for any fix: lines 171 and 56 must change together.** Removing `or 1.0` on its own
moves the "Over-allocated resources" KPI the wrong way (5 over-allocated days → 0 in the agent's
larger scenario; True → False in mine). This is the single most important adjudication in this
report, and it reverses the intuitive patch.

---

## V6 — over-allocation is unreportable at zero capacity

**Verdict: CONFIRMED — both the easy part and the hard case.**

Scripts: `/tmp/audit-verify/lead_v6.py`, `/tmp/audit-verify/lead_v6b.py`

### Part 1 — the property in isolation

`engine/resources.py:135-137`:
```python
@property
def over_allocated(self) -> bool:
    return self.capacity_minutes > 0 and self.load_minutes > self.capacity_minutes + 1e-6
```

```
  load=1000.0 capacity=0.0 -> over_allocated=False
  load=1000.0 capacity=480.0 -> over_allocated=True
```

### Part 2 — the hard case: REAL, and reproduced three ways

The claim asked me to prove or disprove that a real schedule can produce a bucket with load > 0 and
capacity 0. **It can.** The mechanism is a second falsy-default on the same file —
`engine/resources.py:143`:

```python
wdays = [ ... if _is_working(cal, ...) ] or [sd]
```

When a task's whole CPM span lands on non-working days the working-day list is empty, and `or [sd]`
dumps the entire booked load onto `sd` — *a non-working day*. Capacity for that bucket comes from
`_period_working_days`, which counts only working days, so `cap = max_units * wmpd * 0 = 0`. The
`capacity_minutes > 0` guard then reports `over_allocated = False`.

Reaching it requires `sd` itself to be non-working. `offset_to_datetime` (`engine/cpm.py:255`)
advances to a working day and then adds the intraday remainder, which can roll past midnight onto a
weekend. Three constructions, all executed:

```
--- (a) late project start: Fri 20:00, standard 8h Mon-Fri
    wmpd=480  project_start=2026-01-09 20:00:00
    B span 2026-01-10 04:00:00 .. 2026-01-10 04:00:00   sd weekday=Sat is_working(sd)=False
    bucket 2026-01-10: load=  960.0 cap=    0.0 over=False   <<<< LOAD>0, CAPACITY=0, over_allocated=False
    over_allocated_periods shown to the analyst = ()
    HARD CASE REPRODUCED: True

--- (b) 20h two-shift calendar, normal Fri 08:00 start
    wmpd=1200  project_start=2026-01-09 08:00:00
    B span 2026-01-10 04:00:00 .. 2026-01-10 04:00:00   sd weekday=Sat is_working(sd)=False
    bucket 2026-01-10: load=  960.0 cap=    0.0 over=False   <<<< LOAD>0, CAPACITY=0, over_allocated=False
    over_allocated_periods shown to the analyst = ()
    HARD CASE REPRODUCED: True

--- (c) 24h continuous calendar, normal Fri 08:00 start
    wmpd=1440  project_start=2026-01-09 08:00:00
    B span 2026-01-10 08:00:00 .. 2026-01-10 08:00:00   sd weekday=Sat is_working(sd)=False
    bucket 2026-01-10: load=  960.0 cap=    0.0 over=False   <<<< LOAD>0, CAPACITY=0, over_allocated=False
    over_allocated_periods shown to the analyst = ()
    HARD CASE REPRODUCED: True

--- (d) CONTROL: standard 8h, Mon 08:00 start
    wmpd=480  project_start=2026-01-05 08:00:00
    B span 2026-01-05 16:00:00 .. 2026-01-05 16:00:00   sd weekday=Mon is_working(sd)=True
    bucket 2026-01-05: load=  960.0 cap=  480.0 over=True
    over_allocated_periods shown to the analyst = ('2026-01-05',)
    HARD CASE REPRODUCED: False
```

Cases (b) and (c) matter most: a **20-hour two-shift** and a **24-hour continuous** calendar are
ordinary in tunnelling, marine, mining and plant-turnaround schedules, and both reproduce the defect
from a completely normal 08:00 Friday project start. The control (d) proves the same schedule
reports the over-allocation correctly when the span lands on a working day.

**Result:** 960 minutes of booked work against zero capacity, reported to the analyst as *not*
over-allocated, and absent from `over_allocated_periods` entirely.

I did try the two constructions the claim suggested — a restricted `work_weekdays` and a
holiday-covered span — and report honestly that **neither reaches it on its own**: `Calendar` forbids
an empty `work_weekdays` (`model/calendar.py:47-48`), and `offset_to_datetime` skips both weekends
and holidays when *placing* the start, so `sd` stays working. The intraday-rollover path above is
what actually reaches it.

### Adjudicated disagreement — an adversarial verifier tried to refute this and was wrong

One verifier returned **REFUTED** on the hard case, reporting a probe of 5,000 randomized
`(calendar, start-date, offset)` trials — random `work_weekdays` subsets and up to 12 random
holidays — that produced "ZERO landings on a non-working day", and concluding that `wdays` can never
be empty.

That probe has a blind spot: it randomized the calendar and the offset but not the project start's
**time of day**. `offset_to_datetime` fixes a working *date* via `_advance_working_days` and then
adds the intraday remainder in **minutes** (`cpm.py:280-281`) — which can cross midnight onto a
weekend. Direct probe (`/tmp/audit-verify/lead_v6_adjudicate.py`), standard 8h Mon-Fri calendar,
project start Friday 2026-01-09, offset 480:

```
project_start          offset_to_datetime(ps,480)   weekday   working?
2026-01-09 08:00:00    2026-01-09 16:00:00          Fri       True
2026-01-09 12:00:00    2026-01-09 20:00:00          Fri       True
2026-01-09 16:00:00    2026-01-10 00:00:00          Sat       False
2026-01-09 17:00:00    2026-01-10 01:00:00          Sat       False
2026-01-09 20:00:00    2026-01-10 04:00:00          Sat       False
2026-01-09 23:00:00    2026-01-10 07:00:00          Sat       False

--- systematic sweep: how many (start-hour, offset) pairs land NON-working? ---
non-working landings: 8 / 120
```

**The refutation does not survive.** `offset_to_datetime` demonstrably lands on non-working days, so
`wdays` demonstrably empties and `or [sd]` demonstrably fires — which is exactly what the three
end-to-end reproductions above show, with `is_working(sd)=False` printed in each. V6 stands as
CONFIRMED.

This is recorded rather than quietly dropped because it cuts both ways: on V5 an adversarial
verifier corrected *me*, and on V6 I had to correct *it*. Neither verdict was accepted on the
strength of who said it.

---

## V7 — `hours_per_day=0` → 480, `work_weekdays=[]` → Mon-Fri

**Verdict: CONFIRMED.** Script: `/tmp/audit-verify/lead_v7.py`

`importers/json_schedule.py:105-123`:
```python
wmpd = round(hours * 60) if hours else 480      # 0 is falsy -> 480
...
if weekdays:                                     # [] is falsy -> key never set -> Mon-Fri default
    kwargs["work_weekdays"] = tuple(int(d) for d in weekdays)
```

```
=== V7a: what the importer produces ===
  hours_per_day=0              -> wmpd=  480  weekdays=(0, 1, 2, 3, 4)
  hours_per_day=0.0            -> wmpd=  480  weekdays=(0, 1, 2, 3, 4)
  hours_per_day omitted        -> wmpd=  480  weekdays=(0, 1, 2, 3, 4)
  hours_per_day=10 (control)   -> wmpd=  600  weekdays=(0, 1, 2, 3, 4)
  work_weekdays=[]             -> wmpd=  480  weekdays=(0, 1, 2, 3, 4)
  both zero/empty              -> wmpd=  480  weekdays=(0, 1, 2, 3, 4)
  wmpd=0 explicit              -> ValidationError: ('working_minutes_per_day',) Input should be greater than 0
```

### The sharp part: the importer defeats the model's own fail-closed validators

```
=== V7b: what the MODEL would have done if the value reached it ===
  working_minutes_per_day=0    -> REJECTED: Input should be greater than 0
  work_weekdays=()             -> REJECTED: Value error, work_weekdays must not be empty
```

`Calendar` is explicitly designed to reject both (`model/calendar.py:31` `gt=0`;
`model/calendar.py:47-48` the weekday validator). The importer's truthiness guards convert that
**loud, intended failure into a silent substitution**.

Note the internal inconsistency this produces: the *same* malformed input fails loud or fails silent
depending only on which key the file spells it with — `working_minutes_per_day: 0` raises a
`ValidationError`, while `hours_per_day: 0` becomes 480.

### Rescaling consequence

Durations are stored in working minutes and converted at the presentation boundary, so a wrong
minutes-per-day rescales **every duration in the file**:

```
  a 4800-min task on a TRUE 10h/day calendar = 8.00 days, but displays as 10.00 days under the silent 8h default  (25% error)
  a 4800-min task on a TRUE 12h/day calendar = 6.67 days, but displays as 10.00 days under the silent 8h default  (50% error)
  a 4800-min task on a TRUE 6h/day calendar = 13.33 days, but displays as 10.00 days under the silent 8h default  (25% error)
```

**Judgement, fairly stated:** "0 hours per day" is not a meaningful operator input — it is a
malformed file. The defect is not that the tool declines to honour it; it is that the tool *guesses*
instead of failing. Under Law 2 (never fabricate; NA reads "—", never a placeholder) a malformed
calendar should stop the import with a message naming the field, exactly as the model already does
for the `working_minutes_per_day` spelling.
