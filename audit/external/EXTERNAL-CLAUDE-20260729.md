# Hardened Adversarial Review — Schedule-Manipulation-Analysis-Tool-Experiment

**Report type:** PARTIAL / INTERIM. Read §0 before using any of it.
**Date:** 2026-07-29
**Method:** falsification-oriented, read-only. Starting position: every inherited finding is wrong.

---

## 0. Scope honesty statement — read this first

This is **not** a completed engagement against the prompt as written. Three of the
requested workstreams were not executed, and one is not executable in the
environment available. Nothing below should be represented as a finished audit.

| Workstream | Status |
|---|---|
| H2, H4, H5, H6 | **Executed** with independent tests. Verdicts earned. |
| H1 (SRA all-ML network) | **NOT EXECUTED.** No verdict. Requires the MPXJ conversion chain. |
| H3 (SRA magnitude coercion) | **NOT VERIFIED.** Symbol located only. No behavioural test run. |
| P1–P6 (performance) | **ZERO MEASUREMENTS TAKEN.** See §7. |

Where this report says a finding is confirmed, an independent test was run and its
raw output is reproduced. Where it says otherwise, no such test exists yet. The
distinction is load-bearing and is not softened anywhere in this document.

---

## 1. Reviewed state

| Item | Value |
|---|---|
| Remote | `https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment.git` |
| Branch | `main` |
| Commit | `08c538334c761124539b335e46e303898c4e6fbc` |
| Commit message | `Correct the SSI Best Case rule and stop randomising completed work (#481)` |
| Commit author / date | `polittdj` — Wed Jul 29 15:16:48 2026 -0400 |
| Working tree | Clean. Disposable blobless clone; no edit, commit, push, or PR. |
| Reviewed clone path | `/tmp/smat_meta` (disposable) |
| Artifacts path | `/tmp/audit_out` (outside the reviewed tree) |
| Python | 3.12 |
| Java | OpenJDK 21.0.10 (2026-01-20), Ubuntu 24.04 build |
| Dependencies installed for review | `pydantic 2.13.4` only |
| Browser | **NONE AVAILABLE** |
| `jpype` / MPXJ | **NOT INSTALLED / NOT OBTAINED** |

**Commit currency verified, not assumed.** The prompt instructed that
`08c5383` must not be presumed current. `git ls-remote` confirms
`refs/heads/main` is still exactly `08c5383`. Every inherited finding is being
re-litigated against the identical tree the prior review used.

**Unavailable artifacts:** real browser and DevTools; MS Project; SSI; a licensed
Acumen Fuse installation (Fuse *output* workbooks are present in-repo — see §6);
MPXJ jar; the operator's workstation hardware.

**Data-handling note.** The repository is public — an anonymous, unauthenticated
`git ls-remote` and blobless clone succeeded with no credentials. Tracked content
includes 18 `.mpp` files, ~80 analysis workbooks, Acumen Fuse metric reports, and
DCMA report outputs under `00_REFERENCE_INTAKE/`. The operator has attested that
every file under that directory is non-CUI, non-ITAR, and not derived from
CPSS/HLS program data. That attestation is recorded here and is corroborated by
`docs/adr/0003-noncui-attestation-and-drive-intake.md` and by the in-file header
on the generated fixtures (`SYNTHETIC, NON-CUI VERIFICATION FIXTURE - generated
by tools/make_test_projects.py`). No further review of that question was
performed.

---

## 2. Hardened findings table

| ID | Initial allegation | Strongest rebuttal | Independent test | Result | Final verdict | Confidence |
|---|---|---|---|---|---|---|
| **H1** | SRA solves a different all-ML network and hides it via date-axis realignment | Contract may intentionally be a remaining-work network; docstring is the only defect | — none run — | — | **NOT EXECUTED — no verdict** | n/a |
| **H2a** | `offset_to_datetime` returns non-working dates | Docstring documents a precondition; corpus may never violate it | 4,800-case property sweep + synthetic 24h MSPDI driven through the real importer + CPM | Week-boundary multiples on a 24h calendar render as Saturday; **inverse property holds** | **Confirmed current defect — display/rendering only, narrower than alleged** | HIGH |
| **H2b** | Inverse property fails | Same | Same sweep, with `start_tod + per_day` as discriminator | Inverse breaks **only** when `start_tod + per_day > 1440`; unreachable on corpus and on midnight-start 24h | **Latent defect — not currently reachable** | HIGH |
| **H2c** | — (derived during review) | Precondition is documented, so callers are at fault | Read `mspdi.py:142` | `<StartDate>` taken verbatim; precondition never enforced or warned | **Confirmed contract/validation defect** | HIGH |
| **H3** | Malformed SRA magnitude becomes a locked zero | Browser `type=number` may block it; route may reject first | — none run — | — | **NOT VERIFIED — no verdict** | n/a |
| **H4** | Elapsed/unknown duration literals evaluated as ordinary days | MS Project may deliberately do this | Reproduced parser table; ran differential against the repo's own CPM elapsed handler across weekday starts | Filter says 960 for `2 ed`; engine says 480 from a Friday start. Model carries `duration_is_elapsed`; engine honours it; filter discards it | **Confirmed three-way internal contract inconsistency.** Fix *direction* remains oracle-gated | HIGH (inconsistency) / n/a (direction) |
| **H5a** | Negative sub-day slack floors away from zero | Docstring may be describing something else | Boundary map, 480/600/720/1200 | Docstring claim "sub-day slack reads 0 days" is false across the whole open band (−per_day, 0) | **Confirmed documentation/contract defect — no oracle required** | HIGH |
| **H5b** | The floor direction is wrong vs SSI | SSI may floor identically | Cannot test | — | **Oracle-gated** | n/a |
| **H6** | Pure-logic CPM understates progressed finishes | The dates may be audit folklore, not raw data | Parsed `TP4_DataCenter_v5.xml` with the real importer; computed CPM; read stored fields | CPM 2026-06-26 16:00; stored 2026-07-17 17:00 (summary **and** max non-summary agree). Δ 21 calendar days | **Disclosed limitation — dates verified from raw data.** Presentation audit incomplete | HIGH (dates) / n/a (presentation) |
| **P1–P6** | Performance bottlenecks | Hypotheses only | None possible here | — | **Performance risk not yet measured** | n/a |

**Two of the reviewer's own hypotheses failed during this review and are recorded
in §4 rather than quietly dropped.**

---

## 3. Confirmed current defects

### 3.1 H2a — working-day-multiple finishes render as non-working dates on 24-hour calendars

| Field | Detail |
|---|---|
| File / symbol | `src/schedule_forensics/engine/cpm.py:255` `offset_to_datetime` (rendering); consumed at ~12 `.date()` call sites |
| Enabling code | `src/schedule_forensics/importers/_common.py:204-205` — `if to_min == 0: to_min = 24 * 60` |
| Violated contract | Function docstring: *"weekends and holidays are skipped."* The returned instant's `.date()` can be a weekend. |
| Severity | **MEDIUM** — display-layer only. Offsets and the inverse property are correct. |
| Confidence | HIGH |

**Independent reproduction.** A synthetic 24-hour continuous-ops MSPDI was built
outside the reviewed tree and driven through the real importer. The calendar
resolved as intended:

```
IMPORT OK
  project_start           : 2026-01-05 00:00:00
  working_minutes_per_day : 1440
  work_weekdays           : (0, 1, 2, 3, 4)
  day_segments            : ()
```

Boundary probe on that imported calendar:

```
   offset            -> datetime              day  .date()      working  roundtrip
     1440 ( 1d)         2026-01-06 00:00      Tue  2026-01-06   True     1440
     4320 ( 3d)         2026-01-08 00:00      Thu  2026-01-08   True     4320
     5760 ( 4d)         2026-01-09 00:00      Fri  2026-01-09   True     5760
     7200 ( 5d)         2026-01-10 00:00      Sat  2026-01-10   False    7200   <== NON-WORKING
     8640 ( 6d)         2026-01-13 00:00      Tue  2026-01-13   True     8640
    14400 (10d)         2026-01-17 00:00      Sat  2026-01-17   False    14400  <== NON-WORKING
     7199 ( 4d)         2026-01-09 23:59      Fri  2026-01-09   True     7199
     7201 ( 5d)         2026-01-12 00:01      Mon  2026-01-12   True     7201
```

Control, standard 8h calendar with an 08:00 start — the entire committed corpus:

```
      480 ( 1d)         2026-01-05 16:00      Mon  2026-01-05   True     480
     2400 ( 5d)         2026-01-09 16:00      Fri  2026-01-09   True     2400
     4800 (10d)         2026-01-16 16:00      Fri  2026-01-16   True     4800
```

**Mechanism.** `offset_to_datetime` treats an exact multiple of `per_day` as
end-of-last-full-day (`remainder == 0 → advance = quotient - 1, intraday =
per_day`), preserves time-of-day exactly, then adds `intraday` as wall-clock
minutes. When `start_tod + per_day == 1440` the sum is midnight of the following
calendar date. Friday 24:00 and Saturday 00:00 are the same instant; only one of
them is a working date.

**Oracle.** The round-trip is its own oracle for the *arithmetic* (`roundtrip`
column: exact in every row). No external oracle is needed to establish that
`.date()` returns a weekend, which the docstring forbids. An external oracle
**is** required to choose the correct rendering — see §6.

**Trigger condition.** `start_tod + per_day >= 1440`. Satisfied by any 24-hour /
continuous-operations calendar at any start time. Satisfied by an 8-hour calendar
only if the project `<StartDate>` time-of-day is 16:00 or later.

**Reachability, traced.** 54 call sites for `offset_to_datetime`; roughly twelve
apply `.date()` to the result:

```
src/schedule_forensics/engine/resources.py:149,150      resource-loading buckets
src/schedule_forensics/engine/scorecards.py:685
src/schedule_forensics/engine/jcl.py:356
src/schedule_forensics/engine/path_counterfactual.py:234
src/schedule_forensics/ai/brief.py:626
src/schedule_forensics/web/app.py:11257, 16095, 16100, 19081, 19082, 19246, 19247
```

**Affected inputs.** Any schedule whose project calendar resolves to
`working_minutes_per_day == 1440`. `00_REFERENCE_INTAKE/mpp/Hard_File_updated4 24
hour calendar.mpp` is in the corpus and has **no committed XML conversion**, so
this path has never been exercised by a committed test.

**Remaining uncertainty.** Whether that specific `.mpp` resolves to 1440 was not
verified — MPXJ was unavailable. The *representability* of 1440 is proven; its
presence in the operator's actual corpus is inferred from the filename and from
the fact that `_common.py:204` was deliberately written to support it.

---

### 3.2 H2c — the `offset_to_datetime` precondition is documented but never enforced

| Field | Detail |
|---|---|
| File / symbol | `src/schedule_forensics/importers/mspdi.py:142` |
| Code | `project_start = parse_datetime(_text(root, "StartDate"))` |
| Violated contract | `offset_to_datetime` docstring: *"`start` is assumed to sit at the beginning of a working day."* |
| Severity | **LOW-MEDIUM** — enables H2a/H2b rather than misbehaving itself |
| Confidence | HIGH |

The MSPDI `<StartDate>` is adopted verbatim including time-of-day. No
normalisation to a shift boundary, no validation, no warning. Compounding this,
`datetime_to_offset` (`cpm.py:193`) clamps the intraday term:

```python
intraday = min(max(target_tod - start_tod, 0), per_day) if on_working_day else 0
```

That clamp **silently absorbs** a precondition violation rather than surfacing
it, which is why an off-by-one round trip (479 → 480) fails quietly instead of
raising. The `Calendar` model has no shift-start field at all, so a shift that
does not fit inside one calendar day is not representable.

---

### 3.3 H4 — three-way disagreement on elapsed-duration semantics

| Field | Detail |
|---|---|
| Files / symbols | `src/schedule_forensics/engine/msp_filters.py:47,60-69` `_DUR_LITERAL_RE`, `_parse_duration_literal` |
| Contradicting components | `src/schedule_forensics/model/task.py` field `duration_is_elapsed`; `src/schedule_forensics/engine/cpm.py:198` `_elapsed_finish_offset` |
| Severity | **MEDIUM-HIGH** — changes the selected task population in saved filters and saved views |
| Confidence | HIGH for the inconsistency; the correct *direction* is oracle-gated |

**Current source, verbatim:**

```python
_DUR_LITERAL_RE = re.compile(r"^\s*([\d.]+)\s*(e)?([a-z]*)\s*$", re.IGNORECASE)
...
unit = (m.group(3) or "d").lower()
per = _DUR_UNIT_MINUTES.get(unit, 480)   # unknown/elapsed unit → treat as days
return round(float(m.group(1)) * per)
```

Regex group 2 captures the elapsed marker. Nothing ever reads group 2.

**Reproduced parser behaviour:**

```
'2 d'   -> 960     '2 ed' -> 960    '2 e'  -> 960    '2 xyz' -> 960
'2'     -> 960     '2 em' -> 2      '2 eh' -> 120    '2,5 d' -> None
'bad'   -> None    ''     -> None   '  3  '-> 1440   '2 W'   -> 4800
```

**The internal differential.** `cpm.py:198` carries this docstring: *"MS Project
elapsed durations ('1 eday') ignore both task and project calendars — the finish
is start + N clock minutes."* It implements exactly that. Measuring both against
the same literal:

```
literal parser: 2 ed -> 960 working min

CPM engine, 2 ELAPSED days, by start weekday:
  start Mon 2026-01-05: engine= 960  filter=960  AGREE=True   delta=0
  start Thu 2026-01-08: engine= 960  filter=960  AGREE=True   delta=0
  start Wed 2026-01-07: engine= 960  filter=960  AGREE=True   delta=0
  start Fri 2026-01-09: engine= 480  filter=960  AGREE=False  delta=-480

5 elapsed days:
  start Mon: engine=2400  filter=2400  delta=0
  start Fri: engine=1440  filter=2400  delta=-960
```

The disagreement scales with the number of non-working days the elapsed span
crosses. Mon/Wed/Thu agree only coincidentally.

**The deeper defect — a category error.** An elapsed duration's working-minute
value depends on its start date. A filter literal has no anchor. Therefore **no
fixed minutes-per-elapsed-day constant is correct**, and comparing an elapsed
literal against a stored working-minute duration field is incoherent regardless
of which constant is chosen. Selecting 480 guarantees a wrong task population on
some schedules.

Separately and less severely, `.get(unit, 480)` silently accepts garbage:
`"2 xyz"` evaluates as two days rather than being rejected.

**Reachability.** Saved filters and saved views. Any forensic report driven off a
saved filter containing an elapsed or misspelled unit selects a different task
population than the one the operator specified.

**Remaining uncertainty.** Which of the two internal semantics matches MS Project.
The CPM docstring asserts MS Project behaviour and implements wall-clock addition,
which the reviewer believes is correct — **the reviewer's belief is not an
oracle** and no direction is certified here.

---

### 3.4 H5a — `_whole_days` docstring is false for the entire negative sub-day band

| Field | Detail |
|---|---|
| File / symbol | `src/schedule_forensics/engine/driving_slack.py:166` `_whole_days` |
| Code | `return slack_minutes // minutes_per_day` |
| Violated contract | Its own docstring: *"Sub-day slack (time-of-day raggedness in real stored dates) reads 0 days."* |
| Severity | **LOW** as a documentation defect. Severity of the underlying behaviour is oracle-gated (§6). |
| Confidence | HIGH |

```
  -481 min ->  -2 days
  -480 min ->  -1 days
  -479 min ->  -1 days  <-- SUB-DAY BUT NOT 0: contradicts docstring
    -1 min ->  -1 days  <-- SUB-DAY BUT NOT 0: contradicts docstring
     0 min ->   0 days
   479 min ->   0 days
   480 min ->   1 days

per_day=600 : -1 -> -1   +1 -> 0   -599 -> -1
per_day=720 : -1 -> -1   +1 -> 0   -719 -> -1
per_day=1200: -1 -> -1   +1 -> 0   -1199 -> -1
```

The claim holds for positive sub-day slack and is false for every value in the
open band `(-per_day, 0)`, on every calendar width tested. One minute of negative
raggedness reads as a full day of negative slack. This is provable against the
function's own stated contract with **no external oracle**.

---

## 4. Disproved findings, and the reviewer's own failed hypotheses

Nothing from the inherited list was fully disproved. Two allegations were
materially narrowed (H2b, and H2 overall), and two of the reviewer's own
hypotheses failed outright. All four are recorded rather than omitted.

**4.1 H2b narrowed to unreachable.** The allegation asserted the inverse property
fails. It does — but only when `start_tod + per_day > 1440` *strictly*. Every
tracked MSPDI clears that bound:

```
Project2 / Project5 / EVM1 / EVM2      start=…T08:00:00  mpd=480   ->  960  safe
TP4_DataCenter_v1..v5, TP1, TP3        start=…T08:00:00  mpd=480   ->  960  safe
TP2_Bridge_4x10_Calendar               start=…T07:00:00  mpd=600   -> 1020  safe

distinct MinutesPerDay across all tracked XML:  18x 480,  2x 600
```

A midnight-start 24-hour calendar sits at exactly 1440, which triggers the H2a
rendering defect but **not** the inverse break. The provisional "confirmed defect,
HIGH confidence" classification for H2 as a whole is not supported.

**4.2 Reviewer hypothesis failed — H4 internal differential, first attempt.**
The differential was first run anchored on Monday 2026-01-05 08:00 and returned
`AGREE: True, delta = 0`. Cause: 2 elapsed days and 2 working days both land on
Wednesday from a Monday start; the test case could not discriminate. Re-run
against weekend-crossing starts, the differential held (§3.3). Had the first
result been accepted, H4 would have been wrongly dismissed.

**4.3 Reviewer hypothesis failed — H2a, first fixture.** The synthetic 24-hour
MSPDI was built with tasks of 1, 1, and 5 days from a Monday start, predicting
broken dates. Every finish came back on a working day, matching stored MS Project
finishes exactly:

```
UID 1  A - one full day    EF= 1440 -> 2026-01-06 (Tue)  working=True  stored Finish=2026-01-06 00:00
UID 2  B - FS from A       EF= 2880 -> 2026-01-07 (Wed)  working=True  stored Finish=2026-01-07 00:00
UID 3  C - five days, FS   EF=10080 -> 2026-01-14 (Wed)  working=True  stored Finish=2026-01-14 00:00
```

Cause: the day boundaries fell Tue/Wed/Wed and never on a Friday end-of-day. The
defect was only exposed by probing the week-boundary offsets directly. A fixture
built to demonstrate a defect demonstrated its absence instead.

**4.4 Historical allegations.** The eight items listed in the prompt as fixed at
`08c5383` were **not re-tested** in this pass and are neither revived nor
confirmed here. The referenced `205 passed in 7.74s` run was not reproduced and is
not treated as evidence.

---

## 5. Disclosed limitations (kept separate from hidden defects)

**5.1 H6 — pure-logic CPM understates progressed finishes.** Both dates verified
independently from raw fields:

```
  project_start           : 2026-01-05 08:00:00   per_day=480
  status_date             : 2026-05-29 17:00:00
  tasks: 16   relationships: 20
  pure-logic CPM finish   : 2026-06-26 16:00:00  ->  2026-06-26
  max stored task Finish  : 2026-07-17 17:00:00
  stored summary Finish   : 2026-07-17 17:00:00
  schedule.project_finish : None
```

Δ = 21 calendar days. The status date precedes both, consistent with the stated
cause: in-progress remaining work is not floored at the data date.

**Provenance of the stored date**, which the prompt required be established
before treating it as truth: the MSPDI carries no `<FinishDate>` —
`schedule.project_finish` is `None`. The 2026-07-17 value comes from two mutually
corroborating in-file sources, the summary task's stored `Finish` and the maximum
non-summary task `Finish`, both at `17:00:00`. Adequate provenance.

**What is NOT established:** whether every user-facing page distinguishes
pure-logic CPM from stored as-scheduled finish from progress-aware forecast. That
page-by-page audit was not performed. Until it is, H6 cannot be cleared of the
narrower presentation defect the prompt describes, and it must not be reported as
cleared.

**5.2 Single contiguous working block.** `Calendar` models one block per day;
`dominant_day_minutes` collapses mixed-length days to the dominant length
(ADR-0028). Documented, deliberate.

---

## 6. Oracle-gated questions

| Question | Exact artifact required | Available? |
|---|---|---|
| Does SSI floor negative sub-day driving slack toward negative infinity or toward zero? | An SSI export, or SSI UI output, containing a driving path with negative sub-day slack | **NO.** No SSI export found in the tracked corpus. |
| Does an all-ML SRA reproduce ordinary CPM under the intended contract? | An SSI SRA result with all risks and opportunities disabled, on the same schedule | **NO.** |
| How does MS Project evaluate an elapsed-duration literal in a saved filter? | MS Project saved-filter evaluation, or authoritative MPXJ filter semantics | **NO.** |
| What should a working-day-multiple finish render as on a 24-hour calendar? | MS Project's own rendering of an N-day task on a "24 Hours" base calendar | **NO.** Newly identified by this review — required before H2a can be remediated. |
| Do the operator's real `.mpp` corpus files include a 1440-minute calendar? | MPXJ conversion of `Hard_File_updated4 24 hour calendar.mpp` | **Obtainable** — Java 21 present; needs `jpype` + MPXJ jar. |

**Partial oracle that IS available and was not exploited in this pass:**
`00_REFERENCE_INTAKE/acumen_v8.11.0/` contains Acumen Fuse *output* workbooks,
Fuse Analysis Reports, DCMA reports and metric-history reports. Under the
prompt's own evidence hierarchy these are tier-1 reference-tool output for the
metrics they cover, and they are sitting in the repository unused as oracles.

---

## 7. Performance results

**No measurements were taken. P1 through P6 remain unmeasured hypotheses.**

The prompt's §9 lists *environmental benchmark bias* as a failure mode to attack.
Producing the requested figures from this environment would commit precisely that
error:

- **No browser exists in this environment.** P5 (DOM/SVG node counts, JS heap,
  layout/paint time, long tasks, detached nodes, listener counts) is not partially
  degraded here — it is impossible.
- **FCP and TTI** in P4 are equally impossible for the same reason.
- **Hardware mismatch.** The reported symptom is lag on the operator's
  workstation. Any RSS, latency, GC-pause or scaling figure produced on shared
  cloud infrastructure with a different CPU, different storage, no warm JVM and no
  rendering engine would describe a different machine while carrying the
  appearance of measurement.

**Measured bottlenecks:** none.
**Inferred risks:** the architectural shapes described in P1–P6 were not
re-verified in this pass and are carried forward unchanged as hypotheses.
**Disproved suspicions:** none — nothing was tested.
**Browser vs server attribution:** undetermined.
**Cold vs warm behaviour:** undetermined.

**The only valid path** is an air-gapped harness executed on the operator's own
workstation, with output returned for adversarial analysis. That harness has not
yet been written.

---

## 8. Remediation plan — validated defects only

No fixes were implemented. H1 and H3 are excluded because they have no verdict.

### 8.1 H5a — correct the `_whole_days` docstring

- **Contract decision required first:** none for the docstring. Do **not** change
  the floor behaviour; that is gated on the SSI oracle.
- **Test written before repair:** none needed — no behaviour changes.
- **Smallest safe boundary:** the docstring at `driving_slack.py:167-170`. Zero
  executable lines.
- **Parity proof:** trivially satisfied; no code path altered.
- **Security proof:** n/a.
- **Performance proof:** n/a.
- **Rollback trigger:** n/a.
- **Documentation / ADR:** the corrected text must state that the function floors
  toward negative infinity **and** that SSI parity for negative sub-day slack is
  unverified, cross-referencing ADR-0306. Describing the behaviour without
  flagging the open question would convert an accidental defect into a documented
  decision that was never actually decided.
- **Does a displayed number move?** No.

### 8.2 H2c — enforce or warn on the `offset_to_datetime` precondition

- **Contract decision required first:** does the tool support a project
  `<StartDate>` whose time-of-day plus `per_day` exceeds 1440? If no, reject or
  warn at import. If yes, `Calendar` needs a shift-start field and the whole
  offset axis needs redefinition — a far larger change that must not be started
  casually.
- **Test written before repair:** an importer test asserting that a schedule whose
  `start_tod + per_day > 1440` produces an operator-visible warning.
- **Smallest safe boundary:** a validation emit at `mspdi.py:142` and the
  equivalent point in `xer.py`. **Warning, not exception** — a hard reject would
  refuse real files.
- **Parity proof:** all committed fixtures clear the bound, so no existing golden
  changes. Assert byte-identical analysis output across the full fixture corpus.
- **Security proof:** warning text must route through `logging_redaction` so no
  schedule content leaks into logs.
- **Performance proof:** one comparison per import; immeasurable.
- **Rollback trigger:** any committed fixture emitting the warning.
- **Documentation / ADR:** new ADR recording the supported project-start domain.
- **Does a displayed number move?** No. Adds a warning surface only.

### 8.3 H2a — render working-day-multiple finishes as working dates

- **Contract decision required first, and it is oracle-blocked.** Three candidate
  conventions: (a) render end-of-day-N on the last working day at end-of-shift;
  (b) render the next working day at shift start; (c) keep the raw instant and
  document it. These produce different displayed dates. **Do not pick one from
  first principles** — obtain MS Project's rendering of an N-day task on a
  "24 Hours" base calendar first (§6).
- **Test written before repair:** two tests. (i) An invariant test — every date
  returned by the display path lies on a working date, across `per_day ∈ {480,
  600, 720, 1200, 1440}` and every start time-of-day. This is oracle-free and can
  be written today. (ii) A convention test whose expected values come from MS
  Project, **not** from current engine output.
- **Smallest safe boundary:** a new display-only helper that the `.date()` call
  sites route through. **`offset_to_datetime` must not be modified.** Its offsets
  are correct and its inverse property holds; changing it would move CPM math on
  every 24-hour-calendar schedule and put existing parity at risk for a rendering
  problem.
- **Parity proof:** byte-identical output on all committed fixtures (all 480/08:00
  or 600/07:00, where behaviour is unchanged), plus the invariant test on
  synthetic 24h calendars.
- **Security proof:** n/a — no new I/O.
- **Performance proof:** one weekday check per rendered date.
- **Rollback trigger:** any change to a displayed date on a 480 or 600
  calendar.
- **Documentation / ADR:** new ADR recording the chosen rendering convention and
  its oracle.
- **Does a displayed number move?** **Yes — on 24-hour / continuous-ops calendars
  only.** Zero movement on the committed corpus.

### 8.4 H4 — stop silently coercing elapsed and unknown duration literals

- **Contract decision required first.** Because no fixed minutes-per-elapsed-day
  constant is correct (§3.3), the realistic options are: (a) reject an elapsed
  literal with an operator-visible error; (b) evaluate on the wall-clock axis,
  which a filter cannot do because it has no anchor; (c) keep the approximation
  and disclose it loudly. Option (a) is the only one the reviewer can defend, but
  the decision is the operator's.
- **Test written before repair:** a filter-selection differential asserting that
  `"2 ed"` and `"2 d"` do not silently select the same UID population, plus
  rejection tests for unknown units.
- **Smallest safe boundary:** `_parse_duration_literal` returns a distinguishable
  failure for an elapsed marker and for unknown units; the calling evaluator
  surfaces it to the operator. Two functions, no engine change.
- **Parity proof:** enumerate every saved filter in the tracked corpus, record the
  selected UID set before and after, and account for every difference.
- **Security proof:** n/a.
- **Performance proof:** n/a.
- **Rollback trigger:** any saved filter that previously evaluated cleanly now
  erroring without a migration path.
- **Documentation / ADR:** ADR recording elapsed-literal semantics; release note
  for the population change.
- **Does a displayed number move?** **Yes.** Any saved filter or saved view using
  an elapsed or misspelled unit changes its selected task population. See §9.3 —
  this is the highest-risk item in the plan.

### 8.5 H6 — complete the presentation audit before deciding anything

- Not a code change yet. Enumerate every page and export that surfaces a project
  finish and record, per surface, whether it is labelled pure-logic CPM, stored
  as-scheduled, or progress-aware forecast. Only then decide whether a narrower
  presentation defect exists.
- **Do not** floor every task at the status date. The prompt reports two prior
  attempts that regressed parity and were reverted; that failure has not been
  independently reconstructed and must be before any such change is contemplated.

---

## 9. Attack on the remediation plan

### 9.1 Error cancellation dressed as a parity improvement — H2a
Clamping Friday 24:00 to Friday 23:59 would make dates look right and quietly
shorten every week-boundary offset by one minute the moment the rendered value is
read back through `datetime_to_offset` (7200 → 7199). One error would cancel
another and the total-float arithmetic would drift invisibly.
**Mitigation:** the display helper is strictly one-way. Its output must never
re-enter offset arithmetic. Add a test asserting that no rendered date is ever
passed back to `datetime_to_offset`.

### 9.2 Circular goldens — H2a
Regenerating 24-hour-calendar expected dates from current engine output would
validate nothing and would enshrine the defect as the specification.
**Mitigation:** the convention test's expected values come from MS Project only.
Until that artifact exists, ship **only** the oracle-free invariant test ("every
rendered date is a working date"), which can fail without needing to know the
right answer.

### 9.3 Broken forensic reproducibility — H4, most serious risk in the plan
This is a tool used for delay claims. If an operator has a saved filter using
`"5 ed"` and has issued reports from it, changing the evaluator changes which
tasks those reports would select today. Prior deliverables become
non-reproducible, and in claims work non-reproducibility is more damaging than the
original wrong number, because it undermines the chain of custody for every
report the tool has ever produced.
**Mitigation:** version the filter evaluator. Persist the evaluator version with
every saved analysis. Retain the ability to re-run a historical report under its
original semantics, and label any re-run that used the superseded semantics. Ship
a migration report listing every affected saved filter and its population delta
**before** the change lands.

### 9.4 Stored-versus-computed basis mixing — H2a and H6
Both fixes touch surfaces that display a stored date next to a computed one. A
rendering change on the computed side that is not applied to the stored side makes
the two look inconsistent, or worse makes them look consistent when they are not.
**Mitigation:** the display helper applies to computed dates only, and every
surface showing both must label each. Snapshot the H6 page inventory before
touching H2a so any new divergence is attributable.

### 9.5 Full-duration versus remaining-duration mixing — H1 spillover
H1 has no verdict. Any H2a change that alters displayed SRA or JCL dates could be
mistaken for progress on H1, or could mask it.
**Mitigation:** freeze SRA/JCL display surfaces until H1 has a verdict. Do not
land H2a and investigate H1 in the same change window.

### 9.6 Status-date anchoring — H6
Flooring at the data date is the obvious fix and is explicitly out of scope until
the two reported reverted attempts are independently reconstructed. Reconstructing
them requires knowing which parity tests broke, which is not recorded in anything
independently verified.
**Mitigation:** treat H6 as documentation-and-labelling only for now.

### 9.7 Working-time versus wall-clock arithmetic — the root cause behind H2 and H4
Both findings trace to the same root: the codebase mixes working minutes and
wall-clock minutes. `offset_to_datetime` adds an intraday working remainder as
wall-clock minutes; `_parse_duration_literal` maps a wall-clock elapsed literal
onto the working axis. Fixing them separately leaves the confusion intact and
guarantees a third instance.
**Mitigation:** before either fix, write down which quantities are working-axis
and which are wall-clock, as an ADR. Then fix both against that statement.

### 9.8 Stale cache epochs
Every change in this plan alters displayed output. If the content-addressed SQLite
cache's engine-version invalidation does not cover `msp_filters.py`, the new
display helper, and `driving_slack.py`, warm loads will serve pre-fix results and
the fix will appear not to work — or worse, appear to work intermittently.
**Mitigation:** verify invalidation coverage for every touched module *before*
landing anything. This is P6 and it is unmeasured.

### 9.9 Warning fatigue — H2c
A warning on every import trains operators to ignore warnings.
**Mitigation:** emit only when the condition is actually violated. On the current
corpus that is never.

### 9.10 Environmental benchmark bias — performance
Any performance change justified by numbers from anything other than the
operator's workstation is unfounded.
**Mitigation:** no performance change is authorised until measured locally.

### 9.11 Revised sequencing after the above

1. **H5a docstring** — zero risk, includes the uncertainty flag. Land immediately.
2. **Working-axis vs wall-clock ADR** (§9.7). Blocks 4 and 5.
3. **H2c import warning** — no displayed number moves.
4. **H2a oracle-free invariant test only.** No behaviour change yet. Verify cache
   invalidation coverage (§9.8) in the same window.
5. **H6 presentation inventory.** Documentation output only.
6. **Obtain the four artifacts in §6.** Everything below is blocked on these.
7. **H2a rendering fix** once the MS Project 24h oracle exists.
8. **H4 evaluator fix** once the semantics oracle exists **and** the evaluator
   versioning and migration report from §9.3 are in place.
9. **H1 and H3** — execute the reviews. Do not remediate what has no verdict.
10. **Performance** — local harness, then measure, then decide.

---

## 10. Exact commands and test artifacts

All commands run with `PYTHONDONTWRITEBYTECODE=1`. Reviewed tree never written to.
No `pytest` invocation was made in this pass, so `-p no:cacheprovider` did not
arise.

| # | Command | Result |
|---|---|---|
| 1 | `git ls-remote https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment.git` | **PASS** — anonymous access succeeded; `main` = `08c5383` |
| 2 | `git clone --filter=blob:none --no-checkout --single-branch --branch main <remote> /tmp/smat_meta` | **PASS** — 1,370 tracked paths |
| 3 | `git ls-tree -r --name-only HEAD \| grep -Ei '\.(mpp\|xer\|xml\|xlsx\|pdf)$'` | **PASS** — corpus enumerated |
| 4 | `java -version` | **PASS** — OpenJDK 21.0.10 |
| 5 | `python3 -c "import jpype"` | **FAIL** — `ModuleNotFoundError`. MPXJ chain unavailable. |
| 6 | `pip install --break-system-packages pydantic` | **PASS** — 2.13.4 |
| 7 | `git grep -n "def offset_to_datetime\|def datetime_to_offset\|def _whole_days\|def _reconcile_magnitudes\|def _to_float" HEAD -- 'src/*.py'` | **PASS** — all five located |
| 8 | `git checkout HEAD -- src tests/fixtures 00_REFERENCE_INTAKE/references` | **PASS** — text blobs only |
| 9 | `python3 /tmp/audit_out/h2_inverse_sweep.py` | **PASS** — 4,800 cases; 1,648 failing; discriminator isolated 26 |
| 10 | `python3 /tmp/audit_out/h4_h5_repro.py` | **PASS** — H4 differential returned AGREE (test design fault, §4.2); H5 map confirmed |
| 11 | H4 differential re-run across weekday starts | **PASS** — disagreement confirmed on Friday starts |
| 12 | `parse_mspdi('/tmp/audit_out/AUDIT_24H_ContinuousOps.xml')` | **PASS** — `per_day = 1440` |
| 13 | 24h CPM run, first attempt | **FAIL** — `AttributeError: 'Task' object has no attribute 'summary'` → `is_summary` |
| 14 | 24h CPM run, second attempt | **FAIL** — `AttributeError: 'Task' object has no attribute 'uid'` → `unique_id` |
| 15 | 24h CPM run, third attempt | **PASS** — all finishes on working days, matching stored (§4.3) |
| 16 | 24h week-boundary offset probe | **PASS** — Saturday renders at 7200 and 14400 (§3.1) |
| 17 | `parse_mspdi('tests/fixtures/test_projects/TP4_DataCenter_v5.xml')` + `compute_cpm` | **PASS** — 2026-06-26 vs 2026-07-17 both verified |
| 18 | MPXJ conversion of `Hard_File_updated4 24 hour calendar.mpp` | **NOT ATTEMPTED** — blocked by #5 |
| 19 | `POST /sra/risk-register` malformed-input matrix | **NOT ATTEMPTED** — web stack not installed |
| 20 | Browser performance profile (P5) | **ENVIRONMENT-BLOCKED** — no browser exists |

**Artifacts produced, all outside the reviewed tree:**

```
/tmp/audit_out/h2_inverse_sweep.py          H2 property sweep (independent design)
/tmp/audit_out/h4_h5_repro.py               H4 parser table + H5 boundary map + differential
/tmp/audit_out/AUDIT_24H_ContinuousOps.xml  synthetic 24h continuous-ops MSPDI probe
```

These are ephemeral. Nothing written only to the container survives the session.

---

## 11. Final truth statement

### Confirmed current defects

1. **H2a** — On any calendar where `start_tod + per_day >= 1440` (every 24-hour /
   continuous-operations calendar), working-day-multiple finish offsets render as
   the following calendar date; week-boundary multiples render as Saturday.
   Display-layer only — offsets and the inverse property are correct. Reachable
   through ~12 `.date()` call sites including resource-loading buckets, scorecards
   and JCL. `cpm.py:255`.
2. **H2c** — The `offset_to_datetime` "beginning of a working day" precondition is
   documented but never enforced; MSPDI `<StartDate>` is adopted verbatim
   including time-of-day, and `datetime_to_offset`'s intraday clamp silently
   absorbs violations. `mspdi.py:142`, `cpm.py:193`.
3. **H4** — Three-way internal disagreement on elapsed-duration semantics: the
   model carries `duration_is_elapsed`, the CPM engine honours it as wall-clock,
   and the filter parser captures the marker and discards it. Compounded by a
   category error — no fixed minutes-per-elapsed-day constant can be correct.
   Unknown units are silently accepted as days. `msp_filters.py:47,60-69`.
4. **H5a** — `_whole_days` docstring is false for every value in the open band
   `(-per_day, 0)` on every calendar width tested. `driving_slack.py:166`.

### Disproved or historical findings

1. **H2 as a single HIGH-confidence engine defect** — not supported. It is three
   distinct findings with three different triggers and severities, one of which is
   unreachable.
2. **H2b** — real, but requires `start_tod + per_day > 1440` strictly. No tracked
   MSPDI satisfies it (18× 480/08:00, 2× 600/07:00), and a midnight-start 24-hour
   calendar sits at exactly 1440. **Latent, not currently reachable.**
3. **Reviewer hypothesis, H4 internal differential (Monday anchor)** — failed;
   test could not discriminate. Corrected.
4. **Reviewer hypothesis, H2a first fixture** — failed; boundaries never fell on a
   Friday end-of-day. Corrected.
5. The eight historical allegations listed as fixed at `08c5383` were **not
   re-tested** and are neither revived nor confirmed by this report.

### Uncertain or oracle-gated findings

1. **H1** — no verdict. Not executed. Requires MPXJ.
2. **H3** — no verdict. Symbol located at `app.py:13715` (`_reconcile_magnitudes`)
   and `app.py:1875` (`_to_float`); **no behavioural test was run and none of the
   inherited probe output was reproduced.**
3. **H4 fix direction** — which internal semantics matches MS Project. The
   inconsistency is proven; the direction is not.
4. **H5b** — SSI's floor direction for negative sub-day driving slack.
5. **H2a rendering convention** — what MS Project displays for an N-day task on a
   "24 Hours" base calendar. Newly identified; blocks remediation.
6. **H6 presentation** — whether every surface labels pure-logic CPM distinctly
   from stored as-scheduled and progress-aware forecast. Dates verified;
   labelling not audited.
7. **Whether the operator's real corpus contains a 1440-minute calendar** —
   `Hard_File_updated4 24 hour calendar.mpp` is present and unconverted.

### Highest-value measured performance changes

**None. No performance measurement was taken and none is possible in this
environment.** P1–P6 remain unmeasured hypotheses. No performance change is
justified by this report. The prerequisite is an air-gapped harness executed on
the operator's own workstation; it has not been written.

---

*Nothing in the reviewed tree was modified. No commit, push, or pull request was
made. `main` remains at `08c538334c761124539b335e46e303898c4e6fbc`.*
