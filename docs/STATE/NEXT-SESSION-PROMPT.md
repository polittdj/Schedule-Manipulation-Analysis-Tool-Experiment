# Next-session prompt — SSI driving-slack on progressed/leveled files

> Copy the block below to start the next session. It is self-contained but the authoritative state is
> always `docs/STATE/HANDOFF.md` (read it first). Generated 2026-06-23b. Uploads from a prior session do
> NOT carry over — re-attach the files listed below.

---

You are resuming the **schedule-forensics** project (local, offline, CUI-safe forensic schedule
analysis). Branch: **`claude/clever-volta-wbnx0i`**. **Assume nothing; verify everything by re-running
it.** Honor the two laws: (1) data sovereignty — never commit CUI; (2) fidelity over speed — numbers
must match the reference tools.

**First:** read `docs/STATE/HANDOFF.md` (the top "STATUS (current)" block). This is the task.

## Where we are (already verified last session — do NOT re-derive)

- SSI's **Directional Path Tool** reports **MS Project's live *scheduled* dates** — it invents nothing.
  Proven on a synthetic 4-task chain: clean, on-track progress, and a behind/split schedule all matched
  MS Project exactly (SSI uses a cosmetic **−1-minute** boundary convention, 07:59/16:59).
- The reason the engine's driving slack did not match SSI on the operator's large progressed file
  (`Large_Test_File.mpp`, focus **UID 152**) is **resource leveling**: the saved `.mpp` is **un-leveled**
  (`LevelingDelay`=0) but SSI runs on the **leveled** schedule. Un-leveled stored dates reproduce only
  **90/783**; the leveled schedule reproduces **775/783** (8 residuals = cal-68 2026-holiday edge cases).
- **No engine change is needed.** `engine/driving_slack.py` already uses each task's stored scheduled
  `start`/`finish`. MPXJ reads the leveled `Start`/`Finish` from a **leveled-and-saved** `.mpp`. We do
  NOT re-implement MS Project leveling (it crashes day-by-day on this file; by-week is stable).
- `Large_Test_File.mpp` is **REAL CUI** — read locally, never commit. The committed Project5 **UID-145**
  parity (ADR-0115) is the separate, non-CUI clean-schedule case and is green.

## What the operator will provide (re-upload — ephemeral)

1. `Large_Test_File.mpp` **re-leveled BY WEEK and SAVED** (level by week — day-by-day crashes — then Save).
2. The matching SSI Directional Path export for **focus UID 152** ("Get all dependencies").
   (Prior exports last session: `…UID_152…ALL…xlsx` and `…Resource_Level…xlsx`.)

## Task (in order)

1. Convert the leveled `.mpp` to MSPDI XML via the CLAUDE.md MPXJ command (Java 17+).
2. **Verify** its stored `Start`/`Finish` now equal SSI's exported dates (they should, post-leveling).
3. Run the **shipped repo engine** — `compute_driving_slack(schedule, target_uid=152)` from
   `schedule_forensics.engine.driving_slack` — on the converted schedule and compare to the SSI export.
   Confirm it reproduces SSI (~775/783 → ~100%). This is the missing proof that the **shipped** engine
   (not just last session's scratchpad prototype) matches SSI on a leveled file.
4. **Close the 8 cal-68 residuals:** confirm SSI's day→working-day conversion uses the **project
   calendar** uniformly (evidence: cal 3 → 775 vs per-task → 741); the file's cal-68 lacks 2026 federal
   holidays. Decide whether `driving_slack.py` needs the project-calendar choice made explicit.
5. Resolve the **workflow question**: when the operator runs SSI on a real project, is that file already
   leveled-and-saved? If yes → the tool works on real `.mpp`s as-is. If saved un-leveled → either
   document a "save after leveling" prep step, or make the tool ingest the SSI export's leveled dates.
6. **Only if** the leveled file confirms the repo engine matches: record **ADR-0116** and (if a
   **non-CUI** equivalent exists) add a leveled `ssi_uid152`-style golden + parity test. Never build a
   golden from the CUI `Large_Test_File`. Refresh HANDOFF + SESSION-LOG with the latest ADR (drift guard).

## Guardrails

- Do all CUI analysis in the scratchpad; commit nothing derived from `Large_Test_File`.
- If a needed file is missing, ASK — do not fabricate (Law 2).
- Run the full gate before any commit; branch from `main` for code work; open a draft PR.

---

### Scratchpad harness to recreate (last session's tools; ephemeral, none committed)

- `calmod.py` — MSPDI calendar engine (per-task working-time calendars, holiday overrides) + parse.
- `validate.py <xml> <ssi.xlsx> <focus_uid>` — driving slack from the `.mpp` stored dates (→ 90/783 on
  the un-leveled file; should jump on a leveled file).
- `validate_ssidates_cal3.py <xml> <ssi.xlsx> <focus_uid>` — driving slack seeded from SSI's own dates,
  project-calendar day-conversion (→ 775/783; isolates the calendar question).
