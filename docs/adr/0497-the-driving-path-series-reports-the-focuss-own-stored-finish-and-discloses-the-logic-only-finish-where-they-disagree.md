# ADR-0497 — The driving-path series reports the focus's own stored Finish — the axis its drivers are measured on and the date MS Project and SSI show — and discloses the engine's logic-only finish beside it only where the two disagree by a working day or more (OR-20; the model's self-diagnosis refuted on the operator's own IMS)

- **Status:** Accepted — 2026-09-15 (the operator's report of the 32-version Ask-the-AI answer: *"In the USA IPMR Format 6_January 2024.mpp UID 152 has a completion date of 5/7/2026, not 2/22/2028. Figure out what the root problem is and fix it so that it doesn't happen again and verify that all other files are calculated correctly as well."* — and *"come up with a way to somehow verify and test and prove that the metrics that the tool is generating match those that SSI, Acumen Fuse, and Microsoft Project generate."*).
- **Version:** 1.0.265
- **Extends:** ADR-0479 (OR-11a — the per-version driving-path series this corrects), ADR-0011 (driving slack measured on the file's stored dates — the SSI axis), ADR-0310 (two time axes and the labels that confuse them), ADR-0034 / ADR-0391 / ADR-0476 (the stored dates the CPM honours, and by implication the residual classes it does not).
- **Shipped:** `ai/driving_facts.py` (`_FocusFinish`; `_focus_finish` on the stored Finish with the project-axis disagreement rule; `_logic_finish_wall`; the series header and line wording; the movement census on the stored Finish plus the disagreement count), `tests/ai/test_driving_path_series_focus_finish.py` (10 tests, the measured class as a fixture), `tests/parity/test_driving_series_focus_finish_ssi_uid152.py` (2 oracles from the operator's SSI exports on the real IMS).

## Context

The operator loaded 32 monthly versions of one IMS (USA IPMR Format 6, July 2023 → January 2026),
asked Ask-the-AI for the driving path to UID 152 ("Ready to Ship") in every version, as a speech,
and received a 32-row table headed *"Driving-path finish for UID 152"*. For `USA IPMR Format
6_January 2024.mpp` the row read **2028-02-22**; MS Project shows **2026-05-07** for that activity in
that file (the operator's own reading). Asked to explain itself, the model wrote a "correction memo"
diagnosing that the series' focus finish *"was populated with the project's network CPM finish"*
because the two series were *"byte-for-byte identical in all 32 versions"*, and prescribed a
re-anchored backward pass with guard assertions.

Under QC-2 that memo is testimony. The code and the goldens are the evidence, and the ask was
worked as a unit: red-first, the fix, mutation proofs by name, the gate, this ADR.

### What was measured

The operator's 32 files are production schedules (CUI) and never enter a build session. One save of
the **same IMS family** is in the repo as a non-CUI reference (`tests/fixtures/golden/ssi_uid152/
Large_Test_File.mspdi.xml.gz` — "USA OTB Master IMS", 2,126 tasks, data date 2025-02-07, focus UID
152, with the operator's SSI Directional Path export `00_REFERENCE_INTAKE/ssi/Large_Test_File_UID_152
_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx`), plus its leveled save and the two Fuse-oracle
saves. Everything below was measured there (session scratch `probe_focus_finish.py` /
`probe_ssi_dates.py`; the figures are re-read from their output):

| Measurement | Large_Test_File (`ssi_uid152`) | Leveled | Large_Test_File2 |
|---|---|---|---|
| UID 152 stored Finish (MS Project's) | 2026-10-02 12:00 | 2026-10-09 15:13 | 2029-04-19 10:06 |
| `_focus_finish` on the pre-fix tree (the CPM early finish) | 2026-10-02 | 2026-10-09 | 2029-04-19 |
| CPM network finish (`project_finish`) | 2028-09-28 | 2028-09-28 | 2029-04-20 |
| MS Project's latest stored Finish in the file | 2028-09-29 08:00 | 2028-09-29 08:00 | 2029-04-20 09:39 |
| SSI's exported Finish for the focus | 2026-10-02 12:00 (serial 46297.5) | — | — |
| tool stored Start / Finish == SSI's, path members | 76 of 76 | — | — |
| driving path members on the stored axis | 75 (+ the focus = SSI's 76) | 60 | 62 |
| scheduled activities with a stored Finish | 1,723 | 1,723 | 1,722 |
| CPM early finish == stored Finish (calendar date) | 1,645 | 1,615 | 1,635 |
| within one calendar day | 28 | 43 | 52 |
| earlier / later by more than a day | 36 / 14 | 50 / 15 | 25 / 10 |
| worst (UID, days, % complete) | 4616 −106 (99 %) · 4620 −105 (0 %) · 4581 +58 (14 %) | 4616 −109 | 5697 +41 (0 %) |

Three findings:

1. **The model's diagnosis is refuted.** `_focus_finish` read `cpm.timings[uid].early_finish` — the
   focus's OWN early finish, never `project_finish` — and on every save in the repo that is UID 152's
   own date, two years apart from the network finish. Mutant M2 below builds the alleged defect;
   both SSI oracles go red by name.
2. **The real defect is an axis mismatch with no label.** The drivers on each line are measured on the
   file's stored, progress-aware dates (`date_basis`, ADR-0011 — the only axis that ever reproduced
   SSI's export, 76 of 76 members here), but the finish printed beside them was the engine's
   logic-only CPM early finish. On this IMS the two disagree by more than a day on **50 of 1,723**
   scheduled activities (up to 106 days, both directions). For UID 152 they coincide in every save in
   the repo, so the defect was latent here and its effect on the operator's 32 files is
   **UNVERIFIED** — but wherever the focus is one of those activities the line carried a date neither
   MS Project nor SSI shows, in the same shape as the SCHEDULE-LOGIC FINISH SERIES line beside it,
   and nothing said which date it was.
3. **Which of the two dates the operator's fact line carried cannot be settled from the repo.** The
   transaction log records a prompt's SHA-256 and byte length, never its text (Law 1, ADR-0402), so
   the line the model was given lives only in the operator's session: the Ask panel renders the
   cited facts under the answer, and `/export/{fmt}/ask` exports the last exchange. Two readings fit
   the evidence: the line said 2026-05-07 and the model transcribed the network series into its
   table (the two lists had one shape and no label), or the engine's logic-only finish for UID 152
   in that file really is 2028-02-22 — a disagreement with the file that the pre-fix line would have
   printed without a word. The fix makes the second reading self-reporting. The memo's arithmetic
   (697 / 1,286 / 589 days) was the model's own, across two axes (a CPM-finish series against the
   newest version's stored Finish for UID 6077), in a mode that does not gate model-derived figures
   — unrestricted (ADR-0361), inferred from the footer wording and the activity-data references; the
   mode is not in the log.

## Decision

`_focus_finish` now returns a `_FocusFinish`: the reported date is the focus's **stored Finish** —
the drivers' axis, MS Project's Finish, the date SSI's Directional Path shows; the CPM early finish
stands in only when the file stores none (hand-authored schedules) and the line says it is computed.
The engine's logic-only finish is compared with the stored one **on the project working-minute
axis** — `datetime_to_offset` of the stored instant against `timing.early_finish` (ADR-0310's one
ruler) — and is carried, with its signed gap in working days, only when they differ by a whole
working day or more; a sub-day difference is a representation, not a disagreement. On that ruler a
Friday 17:00 finish and the Monday 08:00 milestone MS Project stores after it are the same offset;
a wall-clock window between the two (`working_minutes_between`) reads 480 minutes on a calendar
without day segments, which was the first rule tried and is why the same-instant test exists.

The wording says whose date it is. The series header states that each line's finish is UID N's own
stored Finish in that file, **NOT** the project's network finish (which the SCHEDULE-LOGIC FINISH
SERIES carries separately), and that a disagreement is stated on the line. A line reads
`UID 152 finishes 2026-05-07` and, where it applies, `(the file's stored Finish; this engine's
logic-only finish for it is 2028-02-22, 424 working days later — a date the file's logic alone does
not reproduce)`. The movement census — first-to-last movement in calendar days, re-wires, re-wires
that held the date — runs on the stored Finish and adds how many measured versions carry a
logic-vs-file disagreement. The single-version facts (`driving_path_summary`) never carried a
finish and are unchanged; both surfaces (`/api/ask`, the unscoped `/api/driving-path`) inherit the
change through `driving_path_series`. `engine/` is untouched: no number the engine computes moved.

## Verification (QC-1)

- **Red-first, by name, on the pristine tree:** 8 of the 10 new tests red —
  `test_the_focus_finish_is_the_files_stored_finish_not_the_logic_only_one` printed the logic-only
  `2025-02-07` where the file stores `2025-05-02`; the disclosure, wording, movement and count tests;
  the SSI oracle's wording. 2 green by construction (the fixture precondition; the network-finish
  negative pin, whose teeth are mutant M2). `test_a_next_morning_milestone_is_the_same_instant_not_a_
  disagreement` was red on the wall-clock rule (it printed *"1 working days earlier"* for the same
  instant) and green on the project-axis rule.
- **After:** 33 green across the two new files, `test_driving_path_series`, `test_driving_facts` and
  `test_ask_driving_path_per_version`.
- **Oracles on the operator's IMS:** SSI's exported Finish for UID 152 (2026-10-02) and the leveled
  export's (2026-10-09) are the dates on the lines; `2028-09-28` — the network finish on both — appears
  nowhere in the series. No line on the real IMS carries a disclosure: the logic-only instant equals
  the stored one to the minute on all three saves (12:00, 15:13, 10:06).
- **Mutation battery on a shadowed copy, the import path asserted on every run — 7 of 7 red by name
  (control 22 green):** M1 report the logic-only finish (the pre-fix behaviour) → 6 red; M2 report the
  network finish (the memo's allegation) → 8 red, both SSI oracles among them; M3 always disclose → 3;
  M4 never disclose → 2; M5 movement forced to 0 → 1; M6 disagreement count forced to 0 → 1; M7 gap
  sign dropped → 1 (the disclosure test, through *later* for *earlier*).
- **Statics on the final tree:** ruff 0.16.7 and 0.15.8 whole-tree clean, ruff format clean, mypy
  strict 165 files clean, bandit exit 0, node --check clean. **`-m parity` on the pristine tree: 118
  passed / 0 failed in 4:18** — the standing executable proof that the committed corpus matches Fuse
  / SSI / MS Project; the two new oracles join it. **The full suite on the final tree:**
  5,460 passed / 5 skipped (the environment-gated urlparse and axis-title skips every run carries) / 0 failed in 37:30.

## Consequences

- A driving-path series line carries the date the reference tools carry, and says so. Where the
  engine's logic-only solve disagrees with the file, the disagreement is a stated fact on the line
  and a count in the movement fact — on the operator's 32 files, the diagnostic this session could
  not run. The two per-version date lists in one fact sheet are no longer one shape with two meanings.
- The operator's question about UID 152 is answerable from the facts as they now read; the model's
  narration still needs a mode whose figures are gated if its arithmetic is to be trusted (below).

## Deliberately NOT done (measured, registered, left alone)

- **The SCHEDULE-LOGIC FINISH SERIES carries only the CPM network finish.** The model's 1,286-day
  figure subtracted the first version's CPM finish from the newest version's stored Finish of UID
  6077 — two axes. A per-version stored project finish (MS Project's latest Finish) beside the CPM
  one is the like-for-like series; an `engine/version_series.py` change with its own tests,
  registered as **OR-20b**.
- **The residual activities where the CPM's early finish disagrees with the stored Finish by more
  than a day** — 50 / 65 / 54 / 35 on the four saves — are the engine's known residual classes on
  this IMS (the report's §3 R-rows name the mechanisms); the per-UID worst-eight lists are in the
  SESSION-LOG. Not chased here; no engine number moved.
- **The focus's stored Total Slack per version** (the operator's question turns on whether UID 152
  was near-critical in each file: 513.5 d on Large_Test_File, 0 on Large_Test_File2) would be one
  more stored figure per line; registered as **OR-20c**.
- **`working_minutes_between` on a calendar without day segments credits the finish day whole**
  (measured: 480 minutes between Friday 17:00 and Monday 08:00 on `Calendar()`, whose
  `intraday_worked_minutes` returns 480 for every time of day). Every MSPDI calendar carries
  segments, so no shipped number is known to be affected; registered for the engine's owners.
- **Unrestricted mode's arithmetic stays ungated** (ADR-0361's design). The 697 / 1,286 / 589-day
  figures were the model's; the movement fact gives one engine-computed delta per focus.

## Evidence

Session scratch: `probe_focus_finish.py`, `probe_ssi_dates.py`, `mut/battery.py` (+ `mutcheck.py`),
`red_first.log`, `parity.log`; the tests named above are the durable form.
