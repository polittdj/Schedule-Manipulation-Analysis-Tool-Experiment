# ADR-0116 — Remove the driving-slack span-snap; SSI parity on the leveled Large Test File (focus UID 152)

- Status: accepted
- Date: 2026-06-24
- Supersedes/relates: **ADR-0045** (driving-slack whole-day span-snap — reversed here), ADR-0011
  (driving-slack SSI parity), ADR-0032 (whole-day tier axis), ADR-0115 (live SSI golden, focus 145)

## Context

`compute_driving_slack` traces a focus task's ancestors and runs a backward pass over each activity's
working-minute **span** to derive how far it can slip before delaying the focus — the SSI Directional
Path Tool's *Driving Slack*. ADR-0045 (2026-06-16) added a step that **snapped each activity's span to
the nearest whole working day** before the backward pass:

```python
span = {uid: round((early_finish[uid] - early_start[uid]) / per_day) * per_day for uid in trace}
```

ADR-0045 diagnosed a consistent **~+1-day** error on the operator's *Large Test File* ("USA OTB Master
IMS", 1723 activities) as **afternoon-shift span raggedness** (e.g. 13:00→12:00 activities with 420-min
spans) accumulating down long chains, and the snap as the fix. That conclusion was only ever spot-checked
against a handful of activities; the shipped engine was never run end-to-end against a full SSI export on
a **leveled-and-saved** copy of that file.

This session the operator provided exactly that: the **leveled-and-saved** Large Test File plus the
matching SSI Directional Path export for focus **UID 152** ("all dependents" / all transitive
predecessors — **783 activities**), and the un-leveled variants for control. (Operator-confirmed
**non-CUI**; read locally, `.mpp`/`.xlsx` not committed — the pre-commit guard blocks those binaries
regardless.)

## What the leveled file proves

1. **Dates are exact.** MPXJ reads the leveled stored `Start`/`Finish`; they equal SSI's exported dates
   **783/783 to the minute** (offset distribution `{0: 783}`). The engine has the right dates.
2. **The engine's calendar already has the 2026 holidays.** `schedule.calendar` is the project calendar
   ("Dynetics Standard", 480 min/day, 111 holidays incl. 11 in 2026), applied uniformly via
   `datetime_to_offset`. So the prior "cal-68 lacks 2026 holidays" residual hypothesis does **not** apply.
3. **The snap collapses parity.** With the snap ON the shipped engine matched only **325/783** and the
   driving path was wrong. With the snap OFF (raw working-minute span) the engine reproduces SSI's
   **driving path 61/61, set-equal** (`driving_path()` returns the identical UID set — zero false
   positives/negatives), and per-activity driving slack **within one working day for 782/783** (one
   full-day residual, uid 6123: 640.05 vs 641.05; the rest are sub-day time-of-day boundary effects).
4. **SSI does not snap.** If SSI computed on a whole-day grid the *raw* span could not reproduce its
   driving path exactly — but it does. ADR-0045's "raggedness accumulation" was a **misdiagnosis**: the
   ~+1-day error was the **resource-leveling date discrepancy** (comparing un-leveled stored dates against
   SSI's leveled in-memory run), not span raggedness. The snap "worked" on the mis-leveled state by
   coincidentally shifting values; on the correctly leveled schedule it is wrong.

## Decision

**Remove the span-snap.** The backward pass uses each activity's true working-minute span:

```python
span = {uid: early_finish[uid] - early_start[uid] for uid in trace}
```

`date_basis` (the displayed/consumed dates) is unchanged. The synthetic TP1 battery test, which had
pinned the snap's *sub-day minutes* (uids 11/12/13 = 60/60/120), is updated to the true raw values
(210/210/120) — the tier counts (13/1/2/2), the DRIVING/floor-0 classification, and the band edges
(uid 39 = 7 d SECONDARY, uid 35 = 20 d TERTIARY) are **unchanged**, because curated goldens carry
whole-day spans for which the snap was a no-op.

## Safety / verification

- `tests/fixtures/golden/ssi_uid145/case.json` parity (ADR-0115) stays **green** — exact, unchanged.
- Full suite **1493 passed, 7 skipped (environment-gated CUI/Java), 2 xfailed** (the by-design stale
  `ssi_uid143`). ruff / ruff-format / mypy / bandit / `node --check` clean.
- The leveled-file verification ran against the operator's **non-CUI** Large Test File **in-session
  only**; no golden is committed from it (the `.mpp` cannot be committed, so a derived golden would be
  unreproducible, and it is a 1723-activity real IMS — repo-hygiene). The regression guard against
  re-introducing the snap is the updated **TP1 battery test** (raw sub-day minutes the snap would
  change) plus the committed **`ssi_uid145`** golden.

## Workflow consequence (operator)

The tool reproduces SSI **whenever the `.mpp` is saved in the same leveling state SSI was run on**:
leveled `.mpp` ↔ leveled SSI export and un-leveled `.mpp` ↔ un-leveled SSI export both matched (path
61/61, 782/783 within a day). The actionable guidance is **level → save → analyze** (analyze the saved
file in the state SSI sees). No tool change is needed to ingest the SSI export's dates; the engine reads
the saved leveled dates directly.

## Residuals (not blocking)

61/61 driving path is exact; 782/783 slacks agree within a working day. The remaining sub-day disagreements
(round-day 723/783, floor-day 696/783) are time-of-day boundary effects below the day granularity the tool
reports, plus one genuine full-day outlier (uid 6123). None change driving-path membership. Chasing SSI's
exact fractional-day convention (its cosmetic −1-second boundary) is cosmetic and deferred.
