# Read-only falsification audit — Schedule Manipulation Analysis Tool

Audit date: 2026-07-29  
Disposition: no repository files changed; no fix, commit, push, pull request, or external data transfer performed.

The six allegations were treated as false until independently reproduced. Four survive in
narrowed form: H1 is a contract/presentation-basis defect rather than a proven SSI algorithm
defect; H2 is a reachable working-time conversion defect; H3 is a persisted input-integrity
defect; and H4 is an elapsed-duration filter parity defect. H5 remains oracle-gated. H6 is a
disclosed limitation with a correctly labeled user-facing comparison, not a newly hidden defect.

Performance profiling also confirmed two retention defects: loaded schedules have no bound or
unload mechanism, and dashboard epoch caches grow without a per-key/current-epoch bound. The
largest measured server costs were SRA simulation, full MSPDI materialization, large analysis
payloads, and repeated eager CPM work on the briefing page. Browser-only conclusions are withheld
because a real browser executable could not be obtained in this environment.

## 1. Reviewed state

### Repository identity

| Item | Observed state |
|---|---|
| Remote | `https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment.git` |
| Remote default branch | `main` |
| Current remote/local commit | `08c538334c761124539b335e46e303898c4e6fbc` |
| Commit message | `Correct the SSI Best Case rule and stop randomising completed work (#481)` |
| Version | `1.0.123` |
| Commit timestamp | `2026-07-29T15:16:48-04:00` |
| Final working-tree status | Clean: zero tracked or untracked changes |
| Review mode | Disposable partial clone plus artifacts outside the clone |

The current GitHub branch and commit were resolved through the read-only GitHub connector and
checked again in the disposable clone. The previously supplied hardened-review commit was still
current; it was not assumed to be current.

### Execution environment

All timing numbers below are environment-dependent approximations.

| Item | Value |
|---|---|
| OS | Linux `6.12.13`, x86-64, glibc 2.39 |
| Logical CPUs | 9 |
| Physical RAM | Unavailable: `/proc/meminfo` is not exposed |
| Python | CPython 3.12.13, Clang 21.1.4 |
| pytest | 9.1.1 |
| Java | OpenJDK 17.0.19, 64-bit Server VM |
| FastAPI / Starlette | 0.141.1 / 1.3.1 |
| Pydantic / httpx | 2.13.4 / 0.28.1 |
| openpyxl / Playwright / psutil | 3.1.5 / 1.61.0 / 7.2.2 |
| Bundled MPXJ | 16.2.0 |
| Browser | Unavailable; Chromium download was truncated/empty and no executable was present |

The project was installed from an external copy of the exact reviewed source, not from the
reviewed tree. Every Python run used `PYTHONDONTWRITEBYTECODE=1`; every pytest run used
`-p no:cacheprovider` and an external `--basetemp`.

### Evidence inventory

The repository and both supplied archives were enumerated, hashed, and content-read. Parsing was
selected by content signature rather than extension where containers could be mislabeled.

| Group | Physical files | Bytes | Read failures |
|---|---:|---:|---:|
| Reviewed repository | 1,370 | 376,997,508 | 0 |
| Reference archive 1 | 228 | 213,004,520 | 0 |
| Reference archive 2 | 208 | 69,160,071 | 0 |
| Total | 1,806 | 659,162,099 | 0 |

There were 1,392 unique SHA-256 payloads. The corpus included 159 `.mpp`, 276 `.xlsx`, 58
`.xml`, 33 `.pdf`, 31 `.docx`, 19 `.afw`, and the repository’s source, tests, documentation,
goldens, binaries, and media. Inventorying is evidence coverage, not an assertion that every
existing assertion or golden is independent proof.

### Independent/current test support

After establishing the declared dependency environment:

- 235 targeted engine/importer/performance regression tests passed in 2.78 seconds.
- 127 targeted web regression tests passed in 53.61 seconds, with one Starlette deprecation
  warning.
- Fourteen independently constructed historical boundary controls all passed.

These results support, but do not establish, the verdicts. The decisive evidence is the
independent boundary, metamorphic, differential, and external-oracle work below.

### Unavailable artifacts

- Real-browser heap, FCP, TTI, layout, style, paint, long-task, listener, detached-node, and
  browser multipart/preread measurements.
- A native SSI run with all risks/opportunities disabled on the large reference schedule.
- An SSI export containing negative sub-day driving slack.
- A successful JCL route benchmark for the large source; the source was not cost-loaded and the
  route correctly returned 422.
- Host physical-memory capacity.

## 2. Hardened findings table

| ID | Initial allegation | Strongest rebuttal | Independent test | Result | Final verdict | Confidence |
|---|---|---|---|---|---|---|
| H1 | SSI solves a materially different all-ML network and hides it with date realignment. | SSI may intentionally model remaining work; a constant shift preserves distribution spacing, and downstream margin/JCL consumers stay on the same all-ML axis. | Committed MPP conversion; full/remaining/exact-ML differential; risk-free and point-mass runs; minimal progressed chain; consumer trace. | Ordinary/all-full focus offset 979,919; remaining/exact-ML 802,319; correction makes both bases display the stored finish. No status anchoring or fixed actual placement was found. | **Narrower defect than alleged:** confirmed documentation/contract and misleading display-basis disclosure; the choice of remaining-work network versus SSI remains oracle-gated. | High for mismatch/false contract; medium for core-engine correctness |
| H2 | `offset_to_datetime` returns non-working dates and violates its inverse contract. | Its docstring assumes a shift-boundary start; 14 real parsed reference schedules happened to satisfy the property. | Every Friday start minute across eight calendar shapes and rollover offsets; holidays/non-working starts; supported JSON schedule and served analysis page. | 8h Mon–Fri: 960 non-working results and 961 inverse mismatches in 11,520 bounded cases. A supported Friday 16:00 start produced Saturday 00:00 and displayed Saturday. | **Confirmed current defect.** | High |
| H3 | Malformed SRA magnitude becomes a locked zero and persists. | HTML `type=number` reduces ordinary browser entry errors; valid zero is legitimate. | Helper matrix; real POST; save/reload; additive-versus-legacy model comparison; invalid/nonfinite/boundary values. | Malformed, locale-comma, nonfinite, and overflow values all became supplied/locked `0.0`; POST returned 303; state survived save/load unchanged. | **Confirmed current input-integrity defect.** | High |
| H4 | Elapsed and unknown duration literals are silently treated as ordinary days. | The correct saved-filter comparison might normalize duration units, and native MS Project behavior was initially unavailable. | Literal matrix; complete evaluator/served route; elapsed-axis fixture; MPXJ 16.2.0 `GenericCriteria` oracle. | Python `2 ed` selected ordinary 2d; MPXJ rejected ordinary 2d and matched elapsed 2d (also ordinary 6d after hour normalization). Unknown units still default to days. | **Confirmed elapsed semantic defect; unknown-unit behavior is a separate unsupported-input validation defect.** | High for elapsed; medium for unknown-unit policy |
| H5 | Negative sub-day driving slack floors to −1 day. | SSI may intentionally floor negatives, and classification remains DRIVING under either floor or truncation. | Five calendar lengths; floor/truncate differential; 43 physical directional workbooks scanned. | Behavior reproduced. Fifteen negative values existed, but none was between −1 and 0 day; no SSI oracle case was found. | **Oracle-gated.** The docstring is internally inaccurate for negative sub-day values, but calculation parity is unresolved. | High for behavior; low for parity conclusion |
| H6 | Pure-logic CPM understates progressed finishes as if it were the current forecast. | The product may intentionally show an independent pure-logic result alongside the source tool’s stored progress-aware date. | Raw TP4 v5 fields; independent CPM; status-aware minimal chain; served forecast page. | CPM 2026-06-26 and stored 2026-07-17 were both shown with explicit, distinct labels and provenance. | **Disclosed limitation, not a hidden user-facing bug.** | High |

## 3. Confirmed current defects

### H1 — false all-ML equivalence and misleading realigned date basis

**Current code and symbols**

- [`_ml_minutes`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/sra.py#L933-L943)
- [`deterministic_margin_bounds`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/sra.py#L950-L969)
- [`compute_sra_ssi`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/sra.py#L1523-L1590)
- [`stored_finish_correction`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/sra.py#L1772-L1791)
- SSI result construction at `sra.py:1800–1904`
- JCL reuse of the same `_ml_minutes` axis at `engine/jcl.py:185–232`

**Violated contract**

The `_ml_minutes` docstring says an all-ML SSI run reproduces `compute_cpm`; the
`deterministic_margin_bounds` docstring repeats the “all-ML equivalence.” Ordinary CPM uses
`duration_minutes`. `_ml_minutes` uses `remaining_duration_minutes` for every incomplete task
when present. Those maps are not equivalent on a progressed schedule.

The result builder then describes the displayed deterministic date as if it were the computed
finish while adding a constant `stored_finish - raw_computed_finish` correction. That is useful
as a presentation axis, but the date is stored-date-realigned, not evidence that the all-ML
network reproduces ordinary CPM.

**Independent reproduction**

The exact committed source was:

```text
SRA Large Test File2.mpp
bytes=9,956,864
sha256=6d7b0147a70b8faedcfdd2e82661483ec379f57cc283abe221342504862b77a8
```

With an explicit writable `java.io.tmpdir`, the committed converter produced 21,838,873-byte
MSPDI plus an 8,416-byte saved-view sidecar. Five one-shot and five persistent-server conversions
all returned zero and produced one normalized semantic hash. The parsed identity was:

```text
Project title/name: Longstar Master IMS
Tasks: 2,126
Active nonsummary tasks: 1,723
Project calendar: UID 3, Dynetics Standard, 480 min/day, Mon–Fri
Calendar segments: 08:00–12:00 and 13:00–17:00
Project start: 2017-06-07 08:00
Status date: 2025-03-10 17:00
Focus: UID 152, milestone, stored critical=true
Stored focus finish: 2029-04-19 10:07:36
```

The independent duration-map/CPM differential was:

| Solve | Focus offset | Raw converted date | Correction to stored focus |
|---|---:|---|---:|
| Ordinary CPM | 979,919 | 2025-06-30 11:59 | 120,002,916 s |
| All full duration | 979,919 | 2025-06-30 11:59 | 120,002,916 s |
| All remaining duration | 802,319 | 2024-01-11 11:59 | 166,313,316 s |
| Exact `_ml_minutes` | 802,319 | 2024-01-11 11:59 | 166,313,316 s |

Ninety-two active nonsummary activities differed between full and exact-ML durations. The
all-ML focus was 177,600 working minutes, or 370 480-minute working days, earlier than ordinary
CPM.

A risk-free run and an all-point-mass run both returned:

```text
deterministic=p10=p50=p80=p90=802319
displayed deterministic date=2029-04-19
```

The distribution correctly collapses on its own all-ML axis. It does not prove equivalence to
ordinary CPM.

The minimal progressed FS chain made the concealment mechanism explicit:

```text
ordinary: offset=2880, raw=2026-01-12 16:00, corrected=2026-01-30 17:00
all-ML:   offset= 960, raw=2026-01-06 16:00, corrected=2026-01-30 17:00
```

Adding 480 working minutes changed the uncorrected and corrected dates by the same 86,400 wall
seconds. The correction therefore preserves relative distribution spacing while making
different deterministic bases land on the same stored anchor.

**Strongest counterargument and remaining uncertainty**

The strongest rebuttal succeeds in part: a remaining-work SRA can be a legitimate product
contract, and internal SSI margin calculations plus JCL consistently use the same all-ML axis.
No incompatible downstream subtraction was proven.

It does not defeat the current defect because the model is not constructed as a fully specified
status-date remaining-work network: the project origin remains the original project start,
completed/actual work is not placed at fixed actual dates, and a constant stored-date shift is
used instead of explicitly anchoring future work at the data date. The UI/API does not label the
deterministic date as stored-date-realigned.

An authoritative SSI risk-disabled result is still required before declaring that the
remaining-duration choice itself is wrong. The confirmed defect is therefore the false
equivalence contract and misleading computed-date disclosure, not a claim that SSI must use full
durations.

**Reachability and impact**

The basis reaches `/api/sra/ssi`, SRA pages/exports, JCL’s finish marginal, and risk-based margin
sufficiency. On the large file, a 370-working-day internal basis difference is hidden behind an
identical displayed deterministic finish. An analyst can reasonably interpret that agreement as
network parity.

Severity: **High**. Confidence: **High** for the false contract/display basis; **Medium** for the
correct target SRA network until an SSI oracle exists.

### H2 — working-minute offsets can become non-working timestamps

**Current code and symbol**

[`offset_to_datetime`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/cpm.py#L255-L278)
and its inverse [`datetime_to_offset`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/cpm.py#L179-L213).

**Violated contract**

The docstring says weekends/holidays are skipped and the functions are inverses on the
working-time grid. The implementation advances by working dates, preserves the caller’s
time-of-day, then adds the intraday working-minute remainder as wall-clock time without
revalidation. It also does not consult the calendar’s actual day segments.

**Independent sweep**

For every minute of Friday 2026-01-09 and eight offsets around one/two-day rollover boundaries:

| Calendar | Cases | Non-working-date results | Inverse mismatches |
|---|---:|---:|---:|
| 8h, Mon–Fri | 11,520 | 960 | 961 |
| 10h, Mon–Fri | 11,520 | 1,200 | 1,201 |
| 12h, Mon–Fri | 11,520 | 1,440 | 1,441 |
| 20h, Mon–Fri | 11,520 | 2,400 | 2,401 |
| 24h, Mon–Fri | 11,520 | 2,880 | 2,881 |
| 8h, Tue–Sat | 11,520 | 960 | 961 |
| 8h, all days | 11,520 | 0 | 961 |
| 8h, Mon–Fri + holiday | 11,520 | 960 | 961 |

These are bounded-test counts, not prevalence estimates.

Representative raw output:

```text
start=2026-01-09 16:00, offset=479 -> 2026-01-09 23:59, roundtrip=479
start=2026-01-09 16:00, offset=480 -> 2026-01-10 00:00, working_date=false
start=2026-01-09 16:01, offset=479 -> 2026-01-10 00:00, roundtrip=480
```

Non-working project starts and holidays were normalized to the next working date for simple
08:00 controls. That counterexample narrows the failure: it is not a universal inability to skip
dates; it is rollover arithmetic combined with an unenforced shift-boundary precondition.

Fourteen unique real parsed MSPDI schedules produced no invalid finish and no inverse mismatch,
because those project starts were normalized enough for the sampled final offsets. This is a
useful counterexample but not disproof.

**Analyst-visible reachability**

A schedule using the supported JSON shape with project start Friday 2026-01-09 16:00 and one
480-minute task produced:

```text
CPM finish offset=480
converted finish=2026-01-10 00:00
working date=false
summary finish=2026-01-10
GET /analysis/late -> 200 and displayed Saturday
```

The function is used for CPM dates, project finish, summary/report date fields, Gantt data,
resource time buckets, SRA/JCL display conversion, and exports. Supported callers do not all
enforce the stated “beginning of a working day” assumption.

The root defect is composite:

1. caller start times are not normalized to a supported shift boundary;
2. working minutes are added as wall-clock minutes;
3. the calendar model’s day segments/shift start are not enforced by this conversion; and
4. the result is not revalidated.

No replacement timestamp convention is recommended until the intended shift-start model is
decided.

Severity: **High**. Confidence: **High**.

### H3 — invalid SRA magnitudes persist as locked zero

**Current code and symbols**

- POST route: `src/schedule_forensics/web/app.py:5720–5782`
- Number input: `web/app.py:13610`
- [`_reconcile_magnitudes`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/web/app.py#L13715-L13734)
- Setup import: `web/app.py:14479–14506`

**Violated contract**

Missing, invalid, and intentional zero are distinct states. The helper maps every nonblank value
through `_to_float(..., 0.0)`, treats the result as supplied, and locks it. Its final
`days or 0.0`/`pct or 0.0` return further collapses absence and zero.

**Independent raw boundary results**

With `avg_rem=10`:

| Input days | Percent | Result | Locked | Observation |
|---|---:|---|---|---|
| blank/whitespace | 25 | 2.5 d, 25% | days false, pct true | Correct derivation control |
| `typo` | 25 | 0 d, 25% | both true | Invalid became intentional zero |
| `12abc` | 25 | 0 d, 25% | both true | Partial numeric silently accepted as zero |
| `NaN`, `Infinity`, `-Infinity` | 25 | 0 d, 25% | both true | Nonfinite silently became zero |
| `1,5` | 25 | 0 d, 25% | both true | Locale comma silently became zero |
| `0` | 25 | 0 d, 25% | both true | Indistinguishable from malformed |
| `-2.5` | 25 | −2.5 d, 25% | both true | Negative accepted |
| `1e2` | 25 | 100 d, 25% | both true | Exponent accepted |
| `1e309` / 400-digit integer | 25 | 0 d, 25% | both true | Overflow silently became zero |

The real route accepted malformed input:

```text
POST /sra/risk-register -> 303
impact_days=0.0
impact_pct=25.0
days_locked=true
pct_locked=true
```

The additive SSI model then carried `impact_days=0.0`, while the legacy multiplicative model
carried `impact_low=impact_ml=impact_high=1.25`. The same operator submission therefore means
zero schedule impact in one model and a 25% multiplier in the other.

Save/reload preserved the malformed-derived zero and both locks byte-for-byte at the model level;
the saved setup SHA-256 was
`675d8cdded94505fcc9223e438a2ca280499cfa0c16392b110369075a5d9d707`.

**Strongest counterargument**

The rendered field is `type=number`, which blocks some ordinary interactive browser entries.
That is not a server contract and does not cover direct POST, setup JSON, Excel/setup imports,
disabled JavaScript, crafted requests, browser inconsistencies, or overflow/nonfinite values.
No operator-visible error was returned.

**Reachability and impact**

The persisted risk register feeds `/sra/ssi`, legacy `/sra`, setup save/load, and exports. An
invalid magnitude can suppress additive risk while looking intentionally locked. This can move
percentiles and margin decisions without an error.

Severity: **Medium–High**. Confidence: **High**. Browser-only behavior remains unmeasured, but it
is not needed to establish the reachable server/import defect.

### H4 — elapsed-duration saved filters use the wrong axis

**Current code and symbol**

[`_parse_duration_literal`](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/blob/08c538334c761124539b335e46e303898c4e6fbc/src/schedule_forensics/engine/msp_filters.py#L60-L69).

The regular expression captures the optional elapsed `e`, but the function ignores it. Unknown
units use `.get(unit, 480)`.

**Current parser behavior**

```text
"2 d"=960     "2 ed"=960      "2 xyz"=960     "2"=960
"2 h"=120     "2 emin"=2      "2 ewks"=4800   "2 fortnight"=960
"bad"=None    "2,5 d"=None    "-2 d"=None      ".5d"=240
```

**Independent MPXJ oracle**

MPXJ 16.2.0’s own `GenericCriteria` evaluator was given a literal
`Duration(2, ELAPSED_DAYS)`:

```text
literal=2.0ed
literal_hours=48.0h
ordinary-two-days raw=2.0d hours=16.0h equals_2ed=false
elapsed-two-days raw=2.0ed hours=48.0h equals_2ed=true
ordinary-six-days raw=6.0d hours=48.0h equals_2ed=true
```

MPXJ normalizes duration criteria to hours. Its source confirms that elapsed days convert at
1,440 minutes/day, ordinary days use the project’s `minutesPerDay`, and
`GenericCriteria` converts both operands to hours:

- [MPXJ `Duration.java`](https://github.com/joniles/mpxj/blob/023f00cd4f44a46ae7ba338fed06e5dac69c261b/src/main/java/org/mpxj/Duration.java)
- [MPXJ `GenericCriteria.java`](https://github.com/joniles/mpxj/blob/023f00cd4f44a46ae7ba338fed06e5dac69c261b/src/main/java/org/mpxj/GenericCriteria.java)

**Population differential and reachability**

The independent fixture contained:

| UID | Task duration | Stored elapsed flag |
|---:|---:|---|
| 10 | 960 min / ordinary 2d | false |
| 20 | 2,880 min / elapsed 2d | true |
| 30 | 2,880 min / ordinary 6d | false |

For saved criterion “Duration equals 2 ed,” current Python selected UID 10 only. MPXJ’s semantics
exclude UID 10 and include UIDs 20 and 30 on an 8-hour project calendar. A served saved-filter
route returned 200 and scoped to the same wrong ordinary-2d population, so this is not a
dead-parser discrepancy.

Unknown-unit fallback is independently confirmed behavior but has no proof that native MS
Project deliberately accepts arbitrary misspellings as days. It should be treated as
unsupported-input validation, not silently assigned invented semantics.

Severity: **Medium–High** for saved-view population integrity. Confidence: **High** for elapsed
parity; **Medium** for the exact unknown-unit rejection policy.

### P2/P6 — unbounded schedule and dashboard-epoch retention

**Current code and symbols**

- `SessionState.schedules`: plain dictionary at `src/schedule_forensics/web/state.py:379`
- `dash_cores`: plain dictionary at `web/state.py:417`
- `dash_cards`: plain dictionary at `web/state.py:423`
- `cpms`: bounded LRU at `web/state.py:409–411`

**Measured retention**

For the 2,126-task schedule:

| State stage | Deep retained bytes |
|---|---:|
| Raw schedule loaded | 33,168,726 |
| Full analysis cached | 56,105,608 |
| Performance memo cached | 57,830,412 |

The full-analysis response itself was 4,790,079 bytes in the retention probe; the dedicated Gantt
API route produced 4,619,654 bytes. Shared-object deep-size measurements were identity-aware, so
the stage totals should be compared rather than summed.

Independent 250-task schedule objects scaled linearly:

| Loaded versions | Retained schedule bytes |
|---:|---:|
| 1 | 1,596,066 |
| 2 | 3,191,688 |
| 4 | 6,382,932 |
| 8 | 12,765,508 |

There is no session byte budget, version count bound, inactive-summary tier, or explicit unload
control. The persistent SQLite content cache cannot release in-memory schedules because nothing
evicts them.

For two 2,126-task versions, baseline dashboard caches contained two CPM/core/card entries and
state deep size was 34,386,860 bytes. Sixty target epochs produced exactly 122 entries in each of
`cpms`, `dash_cores`, and `dash_cards` and state deep size 39,163,392 bytes. Clearing the target
restored byte-identical output but left all 122 historical entries resident. CPM is eventually
LRU-capped; the dashboard dictionaries are not.

This is a confirmed availability/performance defect under ordinary filter/target exploration,
not merely an architectural suspicion.

Severity: **High** for long-lived sessions with large/multiple files. Confidence: **High**.

## 4. Disproved findings

### Historical defects independently defeated

All fourteen new controls passed. The following historical allegations must not be re-reported
at this commit:

1. **SSI Best Case inversion** — for ML 1,000 and factors 0–5, actual triplets exactly matched the
   independently computed table: `(1000,1000,1000)`, `(500,1000,1100)`,
   `(400,1000,1200)`, `(300,1000,1300)`, `(200,1000,1400)`,
   `(100,1000,1500)`.
2. **Completed work randomized** — two seeds produced a one-point distribution at 1,000 with
   zero standard deviation. The incomplete control spread to 0.754484 working days.
3. **Missing optional cost/work treated as zero** — present→missing and missing→present produced
   no manipulation findings. The numeric rollback control produced all four expected cost/work
   change/erasure findings.
4. **Declared zero capacity becomes one** — declared `MaxUnits=0` stayed zero; the missing-field
   control defaulted to one.
5. **Work against zero capacity not overallocated** — 480 minutes of load against zero capacity
   was marked overallocated.
6. **JSON `hours_per_day: 0` becomes 480** — it was rejected by model validation.
7. **JSON `work_weekdays: []` becomes Mon–Fri** — it was rejected; absent fields still defaulted,
   and an explicit 10h Mon–Thu calendar was preserved.
8. **Dangling MSPDI/XER calendars default silently** — both defaulted to 480 minutes only with an
   explicit warning naming UID 404 and the fallback.

### Apparent committed MPP converter failure

The first universal-reader probe returned null/exit 2 while direct `MPPReader` succeeded. That
looked like a converter defect but was disproved.

The sandbox has no `/tmp`. MPXJ `UniversalProjectReader` copies OLE input to a temp `.dat`; its
recognition handler catches temp/POIFS exceptions and returns null. The diagnostic failed with:

```text
NoSuchFileException: /tmp/mpxj-universal-diagnose-....dat
```

With `-Djava.io.tmpdir=<writable external directory>`:

```text
source_bytes=9956864
temp_bytes=9956864
mpp_format=MSProject.MPP14
proxy=org.mpxj.mpp.MPPReader
```

The committed converter then passed five one-shot and five server trials and produced identical
normalized semantics. MPXJ’s source corroborates the temp-copy behavior:
[UniversalProjectReader.java v16.2.0](https://github.com/joniles/mpxj/blob/v16.2.0/src/main/java/org/mpxj/reader/UniversalProjectReader.java).
The original failure is environment-blocked evidence and is excluded from product verdicts.

### H6 as a hidden presentation bug

The allegation that pure-logic CPM is presented as the current progress-aware forecast was
defeated by the served page. The labels, dates, and bases are explicit:

```text
Schedule logic (CPM): 2026-06-26
As-scheduled (stored dates): 2026-07-17
Completion-rate extrapolation: 2026-10-02
Earned-schedule IEAC(t): 2026-09-09
```

The 21-calendar-day difference is real, but it is disclosed rather than hidden.

### Cache correctness suspicions defeated

- Warm MPP upload made zero `_parse_upload` calls and therefore skipped parsing/JVM conversion.
- Restoring a reversible scope produced byte-identical dashboard output with zero new CPM/full
  analysis calls.
- Same-key replacement changed object identity and moved project finish from 3,000 to 3,480
  minutes; no stale result was served.
- A wipe during an in-flight computation left zero schedules and zero derived cache entries; no
  result resurrected.
- The engine version independently matched `4d973c363c65d555`, covered 81 source modules, and
  changed to `2323f37f9951ee3f` under a virtual CPM source mutation.

These controls defeat stale-cache and wipe-race allegations. They do not defeat the separate
unbounded historical-epoch retention defect.

## 5. Disclosed limitations

### H6 — pure-logic CPM is not progress-aware rescheduling

The raw TP4 v5 fixture hash was
`8625f98841cc37f6eef57c50633bfd98d2fdafe62de653d3898d897eaaf011da`.
It carried:

```text
project start=2026-01-05 08:00
status date=2026-05-29 17:00
latest stored task finish=2026-07-17
pure-logic CPM offset=60000 -> 2026-06-26
```

The independently constructed progressed chain narrowed the semantics further:

```text
pure logic=2026-01-12 16:00
independent status-aware finish=2026-01-20 16:00
stored focus finish=2026-01-30 17:00
```

The status-aware result is not automatically the stored result; stored dates can include
constraints, leveling, out-of-sequence progress, or source-tool scheduling behavior. Simply
flooring every task at the status date would therefore be unjustified and could destroy other
parity.

The forecast engine and page explicitly distinguish pure logic from stored/as-scheduled dates.
H6 should remain a documented engine limitation and regression guard.

## 6. Oracle-gated questions

| Question | Availability | Exact artifact needed |
|---|---|---|
| Does SSI floor negative sub-day driving slack away from zero? | **Unavailable** | An SSI UI/export row with raw driving slack strictly between −1 and 0 working day, including project minutes/day and resulting path tier. |
| Does a risk/opportunity-disabled SSI SRA use full durations, remaining durations, or a status-anchored remaining-work network? | **Unavailable** | SSI deterministic/risk-free output for the exact committed large MPP, including focus UID 152, data date, duration basis, and unshifted/current finish. |
| Is elapsed-duration saved-filter behavior authoritative? | **Available for MPXJ semantics** | MPXJ 16.2.0 `GenericCriteria` supplied the differential oracle; a native MS Project UI/export capture would be additional confirmation, not required to establish divergence from the repository’s chosen MPXJ parity target. |
| What should happen to unknown duration units? | **Unavailable as a product-policy oracle** | Native MS Project or MPXJ parsing of a saved filter containing a genuinely unknown/misspelled unit, or an explicit supported-input contract requiring rejection. |
| Does the browser prevent every malformed SRA value and remain responsive on 2,000+ tasks? | **Environment-blocked** | A real supported browser trace with JS enabled/disabled, direct setup import, heap/timeline, accessibility tree, and export checks. |

### H5 evidence boundary

The arithmetic behavior is certain:

```text
480-min day: -481->-2, -480->-1, -479->-1, -1->-1, 0->0, 479->0, 480->1
```

The same floor-versus-truncation boundary was reproduced for 600, 720, 1,200, and 1,440
minutes/day. Under the current 5/10-day test bands, every negative value remains DRIVING under
both floor and truncation, so the classification is unchanged.

Forty-three physical/23 unique directional workbooks were scanned. Twenty-three had a Driving
Slack header; 15 cells were negative, with unique values `−12.6354167`, `−8.6354167`, `−7.125`,
and `−6.125` days. None was negative sub-day. The required SSI oracle is therefore absent.

The `_whole_days` docstring says sub-day slack reads zero, which is false for negative sub-day
values. That is an internal documentation defect, but the calculation must remain oracle-gated.

## 7. Performance results

### Method and interpretation

Representative benchmarks used one warm-up followed by at least five measured trials. Tables
report median and nearest-rank p95; five-trial p95 is the maximum and should be read as a tail
sample, not a stable population percentile. Every repeated-output benchmark recorded hashes;
unless noted, all five outputs were identical.

`resource.ru_maxrss` is a process high-water mark and tracemalloc covers Python allocations, not
the separate JVM or browser. Absolute and incremental RSS numbers are therefore approximate.

### Measured bottlenecks

#### P1 — full MSPDI representations overlap

Source: committed-converter MSPDI equivalent, 21,838,873 bytes; 2,126 tasks, 2,699 relationships,
87 resources, 3 calendars.

| Phase/measure | Median | Sample p95 |
|---|---:|---:|
| File read | 10.466 ms | 11.731 ms |
| UTF-8 decode | 22.228 ms | 24.774 ms |
| `ElementTree.fromstring` tree build | 1,192.966 ms | 1,252.110 ms |
| Full `parse_mspdi_text` | 2,879.771 ms | 2,930.139 ms |
| Extraction/validation/model estimate | 1,658.465 ms | 1,737.174 ms |
| GC pause total | 493.626 ms | 581.609 ms |
| Absolute peak RSS | 611,804 KiB | 611,836 KiB |
| Incremental max RSS | 515,728 KiB | 515,756 KiB |
| Python allocation peak | 242,541,305 B | 242,541,305 B |

Simultaneous representations included:

| Representation | Size |
|---|---:|
| Input bytes object | 21,838,906 B |
| Decoded string object | 65,516,624 B |
| Serialized model JSON | 4,492,607 B |
| Deep parsed model | 33,162,344 B |
| Product resident estimator | 13,127,680 B |

The measured bottleneck is full-tree parse plus extraction/validation under overlapping full-file
representations, not disk read or SHA-256. A streaming replacement was deliberately not
recommended: no differential prototype proved fidelity for exceptions, assignments, extended
attributes, saved views, relationships, percent lag, namespaces, malformed XML, and entity/DTD
rejection.

#### P2 — retained schedule/analysis state

One large schedule retained about 33.17 MB before derived analysis and 57.83 MB after analysis and
performance memo. Independent schedule copies scaled linearly to 12.77 MB at eight 250-task
versions. The product has no byte budget or unload control.

#### P3 — ingestion, MPP conversion, and warm cache

| Workload | Median | Sample p95 | Result |
|---|---:|---:|---|
| One 21.84 MB MSPDI, cold parse cache | 3,502.892 ms | 4,094.594 ms | Identical |
| Same MSPDI, warm parse cache | 393.715 ms | 470.039 ms | Identical; ~8.9× faster |
| Three distinct large MSPDIs | 12,969.166 ms | 14,230.371 ms | Identical |
| SHA-256 of large MSPDI | 14.040 ms | 38.062 ms | Identical |
| SQLite model get (4.49 MB JSON) | 98.463 ms | 100.566 ms | Identical |
| SQLite model put | 74.220 ms | 78.998 ms | Identical |

Exact committed 9.96 MB MPP:

| Workload | Median | Sample p95 | Result |
|---|---:|---:|---|
| Committed converter, fresh JVM | 4,094.476 ms | 5,083.224 ms | All rc=0; semantic hash identical |
| Persistent converter server | 2,192.132 ms | 2,455.563 ms | All rc=0; same semantic hash |
| Application MPP upload, cold cache | 6,207.365 ms | 7,434.916 ms | One parse call/trial |
| Application MPP upload, warm cache | 295.671 ms | 319.936 ms | Zero parse calls/trial |

The persistent server reduced conversion median by about 46%. Warm application upload was about
21× faster than cold and proved conversion was skipped. Hashing and cache serialization were
substantially cheaper than parsing. Raw converter XML hashes differed because MPXJ emits
volatile/provenance content; normalized parsed schedule plus saved-view semantics were identical.

Browser preread concurrency, browser heap, multipart construction duplication, and client upload
time were not measured.

#### P4 — heavy server routes

Warm route results over two 2,126-task versions:

| Route | Median ms | Sample p95 ms | Bytes | Server HTML nodes | SVG elements |
|---|---:|---:|---:|---:|---:|
| Dashboard | 8.806 | 11.844 | 34,438 | 531 | 10 |
| Analysis | 174.250 | 247.557 | 360,453 | 2,012 | 10 |
| Analysis/Gantt API | 79.292 | 84.071 | 4,619,654 | — | — |
| Performance | 55.869 | 64.997 | 1,003,425 | 649 | 10 |
| Trend | 23.584 | 36.731 | 58,049 | 640 | 10 |
| Trend API | 129.162 | 137.503 | 74,819 | — | — |
| Volatility | 11.642 | 13.755 | 61,656 | 554 | 10 |
| Evolution | 177.321 | 179.928 | 41,782 | 611 | 10 |
| Evolution API | 172.952 | 183.520 | 40,262 | — | — |
| Path | 10.137 | 11.284 | 36,825 | 581 | 10 |
| Driving path | 77.490 | 79.266 | 48,031 | 967 | 10 |
| Resources | 43.155 | 48.440 | 84,477 | 760 | 10 |
| SRA page shell | 16.073 | 20.407 | 102,185 | 1,040 | 10 |
| SSI SRA API, 100 iterations | 5,090.006 | 13,689.433 | 39,274 | — | — |
| Legacy SRA API, 100 iterations | 4,635.748 | 6,073.586 | 10,604 | — | — |
| Brief | 71.665 | 78.592 | 33,088 | 471 | 10 |
| Briefing | 261.224 | 285.434 | 54,148 | 968 | 10 |

The analysis API’s Python-side JSON parse took a median near 36 ms. The briefing page made four
fresh `compute_cpm` calls per measured request despite warm state. JCL returned 422 because cost
data was unavailable and is not classified as a bottleneck.

The most material server bottlenecks are SRA simulation, large analysis serialization, and eager
briefing recomputation. HTML node/SVG counts are server-source counts only, not a real browser
DOM.

#### P5 — browser rendering

No browser conclusion is made. Chromium could not be installed from the allowed environment.
There is no evidence for or against browser heap leaks, layout/paint cost, listener growth,
detached nodes, long tasks, or interaction latency. The 4.62 MB Gantt JSON, 1.00 MB performance
HTML, and server HTML node counts are risk indicators, not browser-profile results.

#### P6 — cache growth and correctness

Sixty target epochs over two large versions grew cache entries from 2 to 122 for CPM, dashboard
core, and dashboard card. State deep size grew by 4,776,532 bytes. Clearing the target restored
the baseline payload hash in 3.355 ms but retained 122 entries.

The median target-epoch request was 8.315 ms and sample p95 40.884 ms. The speed is acceptable in
isolation; the defect is retained historical state.

Warm upload, reversible scope, replacement identity, wipe generation, and engine-version
invalidation all passed as described in section 4.

### Scaling curves

#### Tasks

| Tasks | Deep schedule bytes | CPM median ms | CPM sample p95 ms |
|---:|---:|---:|---:|
| 250 | 1,595,831 | 1.149 | 1.195 |
| 1,000 | 6,374,085 | 4.226 | 4.378 |
| 2,000 | 12,747,085 | 9.095 | 12.253 |
| 4,000 | 25,493,085 | 19.511 | 22.786 |

Core CPM scaled approximately linearly and was not the dominant large-file latency by itself.

#### Independent versions on `/api/dashboard`

| Versions | Total tasks | Retained schedule bytes | Cold median ms | Warm median ms | Payload bytes |
|---:|---:|---:|---:|---:|---:|
| 1 | 250 | 1,596,066 | 85.560 | 1.894 | 1,189 |
| 2 | 500 | 3,191,688 | 94.419 | 2.202 | 2,367 |
| 4 | 1,000 | 6,382,932 | 96.003 | 2.207 | 4,723 |
| 8 | 2,000 | 12,765,508 | 109.313 | 2.353 | 9,435 |

The cold p95 samples at four/eight versions had outliers (250.031/303.696 ms); more trials would
be required to characterize their distribution.

#### Projects

Independent 250-task projects scaled retained schedule bytes from 1.60 MB at one to 12.77 MB at
eight. Portfolio median latency rose from 93.985 ms to 173.602 ms. Every five-trial output hash
was stable.

### Inferred risks, not measured bottlenecks

- Browser-side file preread/multipart duplication and unbounded folder concurrency.
- Browser DOM/SVG/heap and event-listener costs.
- Streaming XML feasibility.
- Accessibility/export effects of table or Gantt virtualization.
- Memory-pressure behavior on machines with less RAM than this unknown host.

### Disproved performance suspicions

- SHA-256 and SQLite cache work did not cost more than cold parsing.
- Warm upload did skip MPP conversion.
- Core CPM itself was not the multi-second bottleneck at 4,000 synthetic tasks.
- Same-key replacement, reversible scope, wipe, and source-hash invalidation did not serve stale
  results in the tested boundaries.

## 8. Remediation plan for validated defects only

No remediation was implemented.

### R1 — decide and expose the SRA deterministic contract

- **Contract decision first:** choose either (a) total-duration CPM parity or (b) an explicitly
  status-anchored remaining-work network. Do not retain the current claim that both are the same.
- **Test before repair:** pin the committed large MPP, the minimal progressed chain, ordinary/full/
  remaining/exact-ML offsets, fixed actuals, status-date origin, and a risk-free external SSI
  oracle when available. Test raw offsets separately from displayed dates.
- **Smallest safe boundary:** `_ml_minutes`, deterministic network construction in
  `compute_sra_ssi`/JCL, and the result date-label/conversion boundary. Do not change unrelated
  percentile sampling.
- **Parity proof:** compare both unshifted working-minute offsets and displayed dates to the
  chosen oracle. Require point-mass collapse and unchanged within-distribution spacing.
- **Security proof:** all schedules/oracles remain local; test with network access disabled and
  ensure only local MPXJ/temp paths are used.
- **Performance proof:** five-trial SRA/JCL A/B on the large file; no more than a predeclared 10%
  regression unless the contract requires additional status logic.
- **Rollback trigger:** any unexplained cross-basis subtraction, moved unprogressed result,
  unfixed actual, or failure of the external risk-free oracle.
- **Documentation/ADR:** replace every “all-ML reproduces compute_cpm” statement; document origin,
  actual placement, data-date anchoring, and whether display dates are shifted.
- **Displayed number moves:** likely yes if the network is properly re-anchored; at minimum the
  deterministic label/provenance must change.

### R2 — define the shift model, then repair working-time conversion

- **Contract decision first:** define whether project start is a shift boundary and whether
  `Calendar.day_segments` is authoritative. Specify endpoint behavior at exact full-day
  multiples.
- **Test before repair:** property tests for every start minute, 8/10/12/20/24-hour days,
  weekends, holidays, non-Monday weeks, all-days calendars, non-working starts, exact ±1
  boundaries, and all public callers. Require both valid work timestamps and inverse equality.
- **Smallest safe boundary:** `offset_to_datetime` plus a single caller-normalization boundary if
  the contract requires normalization. Avoid scattered page-specific corrections.
- **Parity proof:** preserve every currently valid real-reference result; separately approve
  changes for supported late-start fixtures.
- **Security proof:** pure local arithmetic; no new external dependency or telemetry.
- **Performance proof:** large-offset/calendar sweeps and 4,000-task CPM must remain within 10% of
  baseline.
- **Rollback trigger:** any valid-reference date drift outside the declared endpoint convention,
  inverse failure, or result outside a day segment.
- **Documentation/ADR:** replace the unresolved precondition with the chosen shift/segment and
  endpoint rules.
- **Displayed number moves:** yes for late/non-boundary starts and affected reports/Gantt/exports.

### R3 — make SRA magnitude parsing tri-state and fail visibly

- **Contract decision first:** define valid finite range, exponent/locale policy, and whether
  negative values are valid only for opportunities.
- **Test before repair:** one table across helper, POST, JSON/setup, Excel import, JS on/off, save/
  reload, and additive/legacy conversion. Keep missing, invalid, and zero distinct.
- **Smallest safe boundary:** a shared strict magnitude parser returning
  `missing | valid(value) | invalid(reason)` before `_reconcile_magnitudes`.
- **Parity proof:** all valid existing fixtures and saved setups remain model-identical; invalid
  cases return a visible field-level error and are not persisted.
- **Security proof:** bound input length, reject nonfinite/overflow before arithmetic, escape the
  echoed value, and prevent spreadsheet formula injection on export.
- **Performance proof:** negligible route delta under a repeated 1,000-risk parse microbenchmark.
- **Rollback trigger:** valid zero becomes missing, an invalid value is persisted, or additive and
  legacy models derive inconsistent real magnitudes from a valid submission.
- **Documentation/ADR:** specify accepted numeric grammar, range, lock semantics, and error surface.
- **Displayed number moves:** invalid submissions show an error instead of zero; valid values do
  not move.

### R4 — preserve elapsed-duration semantics and reject unknown units

- **Contract decision first:** use the repository’s MPXJ parity target: compare duration
  criteria on normalized hours while preserving elapsed/ordinary unit type. Decide explicitly
  that unknown units are rejected unless an oracle proves otherwise.
- **Test before repair:** MPXJ differential for ordinary/elapsed minutes, hours, days, weeks,
  aliases, case/whitespace/decimals, plus complete saved-filter route populations.
- **Smallest safe boundary:** typed duration-literal parsing and duration comparison in
  `engine/msp_filters.py`; avoid changing non-duration filters.
- **Parity proof:** generate expected UIDs from MPXJ `GenericCriteria`, never from Python output.
- **Security proof:** strict bounded regex/parser, no dynamic evaluation, no network.
- **Performance proof:** filter 2,000/10,000 tasks; normalized conversion should stay linear and
  below the existing route budget.
- **Rollback trigger:** any MPXJ population mismatch or ordinary-duration regression.
- **Documentation/ADR:** list supported units, elapsed meaning, project-calendar conversion, and
  unknown-unit rejection.
- **Displayed number moves:** saved-filter UID populations and every scoped analysis page can move.

### R5 — bound retained schedules and historical epochs

- **Contract decision first:** define an active-project working set, memory/entry budgets, unload
  behavior, and deterministic SQLite rehydration.
- **Test before repair:** 1/2/4/8 large independent versions; repeated target/filter/parity epochs;
  unload/rehydrate; same-key replacement; concurrent navigation; in-flight wipe. Compare full
  analysis/response hashes before and after rehydration.
- **Smallest safe boundary:** `SessionState` cache ownership. Add explicit unload and byte-budgeted
  eviction; retain only the current epoch per key in dashboard dictionaries. Do not alter engine
  calculations.
- **Parity proof:** every rehydrated schedule, CPM, analysis, summary, dashboard card, and export
  must be byte-identical to the original semantic output.
- **Security proof:** local content-addressed SQLite only, permissions constrained, safe filenames,
  no cloud fallback, and complete wipe of memory plus local cache entries.
- **Performance proof:** demonstrate bounded retained bytes across 100 epochs and large-version
  loads; warm rehydration must remain materially below cold parse time.
- **Rollback trigger:** stale epoch, lost grouping/order metadata, wipe resurrection, hash mismatch,
  or rehydration slower than cold parse without a documented reason.
- **Documentation/ADR:** retention budget, eviction order, unload semantics, cache versioning, and
  local-only storage guarantees.
- **Displayed number moves:** no; only latency/memory should move.

### R6 — reduce measured upload/SRA/page costs without sacrificing fidelity

- **Contract decision first:** set server response/latency/memory budgets and identify panels that
  may load progressively. Fidelity remains the gate.
- **Test before repair:** capture current response hashes, accessibility/export behavior, schedule
  model hash, and error behavior. A streaming importer must differentially cover every field
  class named in P1 before replacement.
- **Smallest safe boundaries:** first shorten lifetime of bytes/string/tree objects and isolate
  parsing in a bounded worker; then consider a separately gated iterparse importer. Paginate/lazy
  load task detail without changing exported full datasets. Remove the four redundant briefing
  CPM calls through existing cache APIs. Run SRA in cancellable bounded workers.
- **Parity proof:** byte-identical semantic schedules/analyses and deterministic fixed-seed SRA
  outputs. Client pagination/virtualization must not truncate export.
- **Security proof:** local workers only; sanitize IPC/temp paths; preserve XML DTD/entity rejection;
  no schedule data in browser telemetry or external services.
- **Performance proof:** A/B five-plus trials on committed MPP/MSPDI and 2,000/4,000 synthetic
  schedules. Record RSS, tracemalloc, GC, response bytes, server latency, and real-browser metrics.
- **Rollback trigger:** any information loss, changed calculation hash, inaccessible virtualized
  content, uncancelled stale result, or memory/latency regression outside the declared budget.
- **Documentation/ADR:** worker/concurrency limits, progressive endpoint contracts, export
  completeness, and streaming coverage matrix.
- **Displayed number moves:** no.

## 9. Attack the remediation plan

### Failure-mode attack

| Attack | How a superficially successful repair could still be wrong | Required mitigation |
|---|---|---|
| Error cancellation | Two offset errors cancel after date correction and appear to match stored finish. | Assert raw working-minute offsets and unshifted dates before any correction; never use final displayed agreement alone. |
| Circular goldens | Expected files regenerated by the changed engine make every test green. | Expected UIDs/dates come from MPXJ, raw source fields, mathematics, or frozen external-tool output; record provenance and hashes. |
| Stored/computed basis mixing | A stored focus finish is subtracted from a computed zero-margin date. | Give every value a typed provenance/basis; reject cross-basis arithmetic unless an explicit conversion is tested. |
| Full/remaining mixing | Ordinary CPM and remaining-work SRA are compared under one “deterministic” label. | Name and test duration basis in APIs/models; keep separate full and remaining fixtures. |
| Status-date anchoring | Flooring everything at the data date resurrects completed work or breaks actual sequences. | Build remaining network from fixed actuals and future work; test completed, in-progress, out-of-sequence, and constrained cases. |
| Working/wall-clock mixing | Fixing weekend dates still places timestamps outside shifts or breaks the inverse at lunch gaps. | Define segments and endpoint convention; validate date plus interval and inverse properties. |
| Elapsed/ordinary confusion | Converting both to project working minutes turns 2ed back into 2d. | Normalize MPXJ duration criteria to a common absolute unit while preserving elapsed semantics. |
| Concurrency race | Eviction/unload races with calculation and an old result repopulates state. | Carry object identity, wipe generation, scope epoch, and cancellation token through compute/store; test barriers. |
| Hidden retained references | Capping the main LRU leaves Schedule references in summaries/cards/memos. | Identity-aware heap census after eviction; inspect every cache tier and closure/task reference. |
| Stale cache epochs | Reusing one current entry serves an old target/filter result. | Include semantic scope signature and engine version; atomically replace current per-key epoch; differential scope tests. |
| XML information loss | Streaming looks faster because it drops views, exceptions, assignments, percent lag, or security checks. | Field-by-field differential matrix, malformed corpus, namespace variants, DTD/entity rejection, and source-model hashes. |
| Virtualization breaks accessibility/export | Visible performance improves by removing offscreen rows from screen readers or exports. | Separate visual viewport from canonical dataset; accessibility-tree tests and full export hash/count checks. |
| Environmental benchmark bias | Missing `/tmp`, unavailable browser, high-water RSS, or warm OS cache is blamed on product. | Record environment, classify blocked runs, use explicit temp paths, isolated processes, cold/warm labels, and repeat on supported hardware. |

### Rewritten, gated sequence

1. **Freeze provenance, not engine output.** Acquire the missing SSI artifacts; retain MPXJ/raw-field
   oracles; hash inputs and independently authored expected values.
2. **Decide contracts before code.** Resolve H1 network/basis, H2 shift semantics, H3 numeric grammar,
   H4 unit semantics, and memory budgets in short ADRs.
3. **Add red tests at raw boundaries.** Test offsets, typed bases, actual placement, tri-state input,
   MPXJ UID populations, retained bytes, and concurrent generation/identity.
4. **Change one boundary at a time.** Separate calculation repairs from presentation labels and
   performance work so cancellation cannot hide a defect.
5. **Run parity/security gates.** Compare semantic hashes, independent oracle outputs, malformed XML,
   local-only behavior, wipe/replace races, accessibility, and export completeness.
6. **Run isolated A/B performance gates.** Five-plus trials after warm-up on supported hardware and a
   real browser; retain cold/warm and server/browser separation.
7. **Release behind rollback evidence.** Any unexpected reference-result move, stale state,
   information loss, external data path, or accessibility/export truncation blocks release.

## 10. Exact commands and test artifacts

### Execution order and status

The evidence bundle contains the complete scripts under `tests/` and their raw JSON/stdout/stderr
under `results/`. The following are the evidence-producing commands in execution order; paths are
relative to the disposable workspace root. Incidental read-only `rg`, `sed`, `git show`, and JSON
inspection commands did not generate verdict evidence.

```bash
# 1 — PASS: disposable clone and exact state
git clone --filter=blob:none \
  https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment.git reviewed-repo
git -C reviewed-repo switch main
git -C reviewed-repo rev-parse HEAD
git -C reviewed-repo show -s --format='%H%n%s%n%cI'
git -C reviewed-repo status --porcelain=v1 --untracked-files=all

# 2 — PASS: references extracted outside reviewed tree
mkdir -p audit-artifacts/reference-files audit-artifacts/reference-files-2
unzip -q project_sources/01-Reference-Files.zip -d audit-artifacts/reference-files
unzip -q project_sources/02-Reference-Files-2-1-.zip -d audit-artifacts/reference-files-2

# 3 — PASS: full evidence inventory, zero read failures
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python \
  audit-artifacts/tests/inventory_evidence.py \
  --repo reviewed-repo \
  --reference audit-artifacts/reference-files \
  --reference audit-artifacts/reference-files-2 \
  --output audit-artifacts/results/evidence-inventory.json

# 4 — SETUP-CONTAMINATED, not a product verdict:
# 211 failed, 1,897 passed, 28 skipped, 828 errors in 409.66 s.
# Distribution metadata was absent and MPP conversion lacked a valid temp environment.
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python -m pytest \
  -p no:cacheprovider reviewed-repo/tests \
  --basetemp=audit-artifacts/pytest-baseline

# 5 — PASS: current targeted engine/importer/performance suite
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python -m pytest \
  -p no:cacheprovider \
  reviewed-repo/tests/engine/test_sra.py \
  reviewed-repo/tests/engine/test_sra_ssi.py \
  reviewed-repo/tests/engine/test_manipulation.py \
  reviewed-repo/tests/engine/test_resources.py \
  reviewed-repo/tests/importers/test_json_schedule.py \
  reviewed-repo/tests/importers/test_mspdi.py \
  reviewed-repo/tests/importers/test_xer.py \
  reviewed-repo/tests/perf/test_perf_regression.py \
  --basetemp=audit-artifacts/tmp/pytest-targeted

# 6 — PASS: current targeted web suite
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python -m pytest \
  -p no:cacheprovider \
  reviewed-repo/tests/web/test_dashboard_perf_contract.py \
  reviewed-repo/tests/web/test_forecast_views.py \
  reviewed-repo/tests/web/test_performance_view.py \
  reviewed-repo/tests/web/test_resources_view.py \
  reviewed-repo/tests/web/test_scope_epoch_cache.py \
  reviewed-repo/tests/web/test_sra_report.py \
  reviewed-repo/tests/web/test_sra_risks.py \
  reviewed-repo/tests/web/test_sra_ssi_web.py \
  reviewed-repo/tests/web/test_sra_view.py \
  reviewed-repo/tests/web/test_zero_margin_sra.py \
  --basetemp=audit-artifacts/tmp/pytest-web-targeted

# 7 — PASS: independent historical boundaries
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python \
  audit-artifacts/tests/historical_boundaries.py \
  --output audit-artifacts/results/historical-boundaries.json

# 8 — PASS: initial format-specific conversion prototype, artifacts external
javac --release 17 -cp 'reviewed-repo/tools/mpxj/lib/*' \
  -d audit-artifacts/tests/java-classes \
  audit-artifacts/tests/MpxjDirectConvert.java audit-artifacts/tests/MpxjProbe.java
LD_LIBRARY_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib:/usr/lib/jvm/java-17-openjdk-amd64/lib/server \
  java -cp 'audit-artifacts/tests/java-classes:reviewed-repo/tools/mpxj/lib/*:audit-artifacts/mpxj-extra/*' \
  MpxjDirectConvert \
  'reviewed-repo/00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp' \
  audit-artifacts/SRA-Large-Test-File2.direct.mspdi.xml

# 9 — ENVIRONMENT-BLOCKED then PASS: universal-reader temp diagnosis
LD_LIBRARY_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib:/usr/lib/jvm/java-17-openjdk-amd64/lib/server \
  java -cp 'reviewed-repo/tools/mpxj/lib/*' \
  audit-artifacts/tests/MpxjUniversalDiagnose.java \
  'reviewed-repo/00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp'
LD_LIBRARY_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib:/usr/lib/jvm/java-17-openjdk-amd64/lib/server \
  java -Djava.io.tmpdir=audit-artifacts/tmp/java \
  -cp 'reviewed-repo/tools/mpxj/lib/*' \
  audit-artifacts/tests/MpxjUniversalDiagnose.java \
  'reviewed-repo/00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp'

# 10 — PASS: corrected committed converter, persistent JVM, and upload cache
PYTHONDONTWRITEBYTECODE=1 \
LD_LIBRARY_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib:/usr/lib/jvm/java-17-openjdk-amd64/lib/server \
audit-artifacts/venv/bin/python audit-artifacts/tests/mpp_converter_benchmark.py \
  --repo reviewed-repo \
  --mpp 'reviewed-repo/00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp' \
  --java /usr/lib/jvm/java-17-openjdk-amd64/bin/java \
  --temp audit-artifacts/tmp/java \
  --output-dir audit-artifacts/results/mpp-corrected \
  --output audit-artifacts/results/mpp-corrected-benchmark.json

# 11 — PASS: H1–H6 matrix over committed-converter output
PYTHONDONTWRITEBYTECODE=1 TMPDIR=audit-artifacts/tmp/java \
audit-artifacts/venv/bin/python audit-artifacts/tests/hypothesis_matrix.py \
  --repo reviewed-repo \
  --large-xml audit-artifacts/results/mpp-corrected/one-shot-trial-1.xml \
  --reference audit-artifacts/reference-files \
  --reference audit-artifacts/reference-files-2 \
  --output audit-artifacts/results/hypothesis-matrix.json

# 12 — PASS: MPXJ elapsed-duration oracle
PYTHONDONTWRITEBYTECODE=1 \
LD_LIBRARY_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib:/usr/lib/jvm/java-17-openjdk-amd64/lib/server \
/usr/lib/jvm/java-17-openjdk-amd64/bin/java \
  -Djava.io.tmpdir=audit-artifacts/tmp/java \
  -cp 'reviewed-repo/tools/mpxj/lib/*' \
  audit-artifacts/tests/MpxjFilterDurationProbe.java

# 13 — PASS: scan for H5 oracle artifacts
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python \
  audit-artifacts/tests/ssi_slack_oracle_scan.py \
  --root reviewed-repo \
  --root audit-artifacts/reference-files \
  --root audit-artifacts/reference-files-2 \
  --output audit-artifacts/results/ssi-slack-oracle-scan.json

# 14 — PASS overall; initial shipped-MPP subprobe environment-blocked and superseded by command 10
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python \
  audit-artifacts/tests/performance_matrix.py \
  --repo reviewed-repo \
  --large-xml audit-artifacts/SRA-Large-Test-File2.direct.mspdi.xml \
  --mpp 'reviewed-repo/00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp' \
  --java /usr/lib/jvm/java-17-openjdk-amd64/bin/java \
  --java-classes audit-artifacts/tests/java-classes \
  --direct-classpath 'audit-artifacts/tests/java-classes:reviewed-repo/tools/mpxj/lib/*:audit-artifacts/mpxj-extra/*' \
  --playwright-root audit-artifacts/playwright \
  --output audit-artifacts/results/performance-matrix.json

# 15 — PASS: independent version objects, target epochs, semantic repeatability
PYTHONDONTWRITEBYTECODE=1 audit-artifacts/venv/bin/python \
  audit-artifacts/tests/cache_epoch_supplement.py \
  --large-xml audit-artifacts/SRA-Large-Test-File2.direct.mspdi.xml \
  --direct-cache audit-artifacts/results/perf-cache \
  --output audit-artifacts/results/cache-epoch-supplement.json

# 16 — ENVIRONMENT-BLOCKED: no browser executable after truncated/empty Chromium download
PLAYWRIGHT_BROWSERS_PATH=audit-artifacts/playwright \
  audit-artifacts/venv/bin/python -m playwright install chromium

# 17 — PASS: final read-only guarantee
git -C reviewed-repo rev-parse HEAD
git -C reviewed-repo status --porcelain=v1 --untracked-files=all
```

### Complete disposable scripts

| Script | SHA-256 | Primary evidence |
|---|---|---|
| `tests/inventory_evidence.py` | `0fc264d62698c25324df7b29b133fc0c8602e8aa536d9a59108ea2a832e2dad0` | All-file inventory/content reads |
| `tests/historical_boundaries.py` | `6fac2052280d3dd62d11a77752ae09eace41e5de4d1467cb86205ca37d1ca9f6` | Historical fixes |
| `tests/hypothesis_matrix.py` | `b3ec418cf1b934911e0de585ad547ac4790b4dc4edc79999ad89a70ff680035d` | H1–H6 independent matrix |
| `tests/performance_matrix.py` | `464465c37020fc4e6c3b263d5264980151857734736791f995f5fb187aebabdd` | P1–P6 timings/retention/routes/scaling |
| `tests/cache_epoch_supplement.py` | `7388cb156ff25f798852861dbd5e81d02cff6c3ba5495167522b9f91c60f2af4` | Independent version and epoch growth |
| `tests/mpp_converter_benchmark.py` | `82c8c4b1707bb71596db7d235417f4487320fd5cf24063b8ec9e8ee502dfe4ae` | Corrected MPP/JVM/cache benchmark |
| `tests/ssi_slack_oracle_scan.py` | `676742906d0d27c1db60b59ce23628825b719a5840182950a73442b6ae408489` | H5 corpus/oracle scan |
| `tests/MpxjFilterDurationProbe.java` | `1ae0aa19eb0da00cfb1e601ccd2a3dd79f78f8fb8fe0ea47b197b3062f2726ee` | H4 external oracle |
| `tests/MpxjUniversalDiagnose.java` | `94fba7f6919014d43f243c6e2e556760bc52eb4912d4302e64b37d0c4207f7b8` | Universal-reader environment diagnosis |
| `tests/MpxjDirectConvert.java` | `b3b9ffe2303800d509dac4f2c54ed620ed6dab698650e687c3ed053c1f6014c7` | Independent format-specific converter |
| `tests/MpxjProbe.java` | `0e895750bbd3feb5c6c1619feb55fa6bc1636ed8a31041c27a0396786be682ef` | Universal/direct reader differential |

Every script is present in full in the evidence bundle; no test code was placed in the reviewed
tree.

### Principal raw artifacts

| Artifact | SHA-256 |
|---|---|
| `results/evidence-inventory.json` | `4f74174bc1ea98d6c6d4e611a059a3314725add1d2a7090d8b1244eb70d350e7` |
| `results/hypothesis-matrix.json` | `f6b3169ce367920cf23f1882ce9cdb51882d80655a55f3d4dff95e325524ac45` |
| `results/historical-boundaries.json` | `f3afaeee5382a276fd84dd68d16d846985404b833f821b7fd53ec3542df7615d` |
| `results/performance-matrix.json` | `2219f912aa775e161d7239b0d3ac875ed4eb243c6eaaeb01b05801ee855ce3a7` |
| `results/cache-epoch-supplement.json` | `80dee2104cd43bd8ee77495d05fdede276bd20a97a52db70039d3dc5452a2188` |
| `results/mpp-corrected-benchmark.json` | `1f67547f5b688f4513da8962c72cd1273e647087bfbd71b92c4c295a9529625b` |
| `results/ssi-slack-oracle-scan.json` | `730d03c9489f4f1f612c203f6429c0f2c2c26838c92a2c5eec531b92c90951d3` |
| `results/mpxj-filter-duration-probe.txt` | `a4f4a28ddbfe60de5ac4d2988b059cb7871fff8153f273becd8a0ff5f5d83632` |

## 11. Final truth statement

### Confirmed current defects

- H1: `_ml_minutes`/margin documentation falsely claims all-ML equals ordinary CPM, and stored-date
  correction is not disclosed as a presentation realignment; the exact network choice remains
  narrower than the original allegation.
- H2: reachable working-minute conversion returns non-working dates and violates its inverse
  property for supported start/calendar inputs.
- H3: malformed/nonfinite/overflow SRA magnitude input becomes a persisted locked zero without an
  operator-visible error.
- H4: elapsed-duration filter literals are evaluated on the ordinary-day axis; unknown units are
  silently assigned day semantics.
- P2/P6: loaded schedules and dashboard historical-epoch caches retain unbounded state.

### Disproved or historical findings

- SSI Best Case inversion and completed-work randomization are fixed.
- Missing optional cost/work, declared-zero capacity, zero-capacity overallocation, invalid JSON
  calendar defaults, and silent dangling-calendar fallback are fixed.
- The apparent committed MPP converter failure was caused by missing `/tmp`; it passes with an
  explicit writable Java temp directory.
- H6 is not a hidden presentation bug: pure-logic and stored progress-aware finishes are clearly
  separated.
- Warm-upload conversion skipping, reversible-scope correctness, same-key replacement, in-flight
  wipe protection, and calculation-source cache versioning passed their adversarial controls.

### Uncertain or oracle-gated findings

- H5 calculation parity requires an SSI example with negative sub-day driving slack.
- H1’s correct remaining-work/full-duration choice requires a risk-disabled SSI oracle on the
  exact large MPP.
- Native-tool policy for genuinely unknown duration units is unavailable.
- All real-browser performance, heap, paint, listener, accessibility, and interaction conclusions
  remain environment-blocked.

### Highest-value measured performance changes

- Bound loaded schedules and dashboard epochs by bytes/current scope, add unload plus local
  byte-identical rehydration, and prove no retained references or stale generations.
- Reduce the overlapping bytes/string/XML-tree/model lifetime; gate any streaming parser on a
  complete semantic and XML-security differential.
- Keep persistent MPXJ reuse and warm content caching: measured medians fell from 4.094 s to
  2.192 s for conversion and from 6.207 s to 0.296 s for application upload.
- Make the 4.62 MB analysis/Gantt payload progressive or paginated without truncating export or
  accessibility data.
- Move multi-second SRA work to bounded cancellable local workers and eliminate the briefing
  page’s four redundant CPM solves, with fixed-seed/output-hash parity gates.
