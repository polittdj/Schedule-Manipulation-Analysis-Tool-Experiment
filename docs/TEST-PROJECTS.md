# The synthetic verification battery (TP1–TP4)

Eight fictional, non-CUI MS Project XML schedules built to verify this tool against
**MS Project + SSI** and **Acumen Fuse** on exactly the surfaces the curated goldens
(Project2–Project5) cannot reach: ragged real-world actual times, a non-standard
calendar, hand-seeded DCMA violations with known counts, and a version series with a
deliberate manipulation. Every number in the tables below is **engine-measured and
pinned by `tests/test_projects/`** — load the same file into SSI / Fuse and the two
sides should agree (definitional residuals are flagged where they exist;
`docs/PARITY-REPORT.md` documents the known classes).

- **Files:** `tests/fixtures/test_projects/TP*.xml` (committed; the only
  schedule-format path allowed in git — synthetic fixtures only, Law 1).
- **Regenerate:** `python tools/make_test_projects.py` (deterministic; a pinned test
  fails if the committed copies drift from the generator).
- The `.mpp` re-exports you create from these in MS Project are fine to keep locally
  but stay out of git (the pre-commit guard blocks them anywhere else anyway).

| File | Exercises | Data date | Sched. finish |
|---|---|---|---|
| `TP1_Library_Progressed.xml` | Ragged actual times → day-floored driving tiers (ADR-0032), completion performance, 3-method forecast | 2026-03-31 | 2026-09-17 **09:00** |
| `TP2_Bridge_4x10_Calendar.xml` | 4×10 Mon–Thu calendar + 4 holidays → calendar-true day math, float bands, 44-day boundary | 2026-04-06 | 2026-11-04 |
| `TP3_Outage_DCMA_Seeded.xml` | Every DCMA-14 check with hand-seeded, counted violations | 2026-04-30 | 2026-06-26 |
| `TP4_DataCenter_v1..v5.xml` | Trend, Compare, Bow Wave/CEI, forecast drift, manipulation signals | monthly, Jan–May 2026 | v1–v3: 06-05 · v4: 06-26 · v5: 07-17 |

## Getting the files into MS Project

1. `git pull origin main` — the files are in `tests\fixtures\test_projects\`. Copy them
   to a working folder (e.g. `Documents\SF-TestProjects`) so MS Project never touches
   the repo copies. (They are plain text — the copy/paste-into-Notepad route works too;
   save as `TPn_….xml` with encoding UTF-8.)
2. In MS Project: **File → Open**, set the file-type filter to **XML Format (*.xml)**,
   pick the file, and choose **“As a new project”** if the import wizard asks.
3. Run `SF_VerifyImport` (VBA below) and compare its message box to the table for the
   file. Then `SF_SaveAsMpp` — SSI and Fuse work best from a real `.mpp`.
4. **Do not re-baseline** — the baselines (including TP4's deliberately falsified one)
   are part of the test content and import with the XML.
5. The same `.xml` files load directly into Schedule Forensics (drop zone) — the tool
   and MS Project read identical bytes, so any disagreement is real signal.

### VBA helpers

`Alt+F11` → **Insert → Module** → paste everything below. Run with `Alt+F8`.
If macros are blocked: File → Options → Trust Center → Trust Center Settings → Macro
Settings → "Disable all macros with notification", reopen, then Enable Content.

```vba
Option Explicit
' Schedule Forensics - synthetic battery helpers (docs/TEST-PROJECTS.md)

Sub SF_VerifyImport()
    ' Compare what MS Project imported against the battery manifest table.
    Dim t As Task, d As TaskDependency
    Dim n As Long, bl As Long, ms As Long, lk As Long, summ As Long
    For Each t In ActiveProject.Tasks
        If Not t Is Nothing Then
            If t.Summary Then
                summ = summ + 1
            Else
                n = n + 1
                If t.Milestone Then ms = ms + 1
                If CStr(t.BaselineStart) <> "NA" Then bl = bl + 1
                For Each d In t.TaskDependencies
                    If d.To.UniqueID = t.UniqueID Then lk = lk + 1
                Next d
            End If
        End If
    Next t
    MsgBox "Project: " & ActiveProject.Name & vbCrLf & _
           "Status date: " & CStr(ActiveProject.StatusDate) & vbCrLf & _
           "Calendar: " & ActiveProject.Calendar.Name & vbCrLf & _
           "Working (non-summary) tasks: " & n & "   summaries: " & summ & vbCrLf & _
           "Milestones: " & ms & "   links: " & lk & vbCrLf & _
           "Tasks with a baseline: " & bl & vbCrLf & _
           "Project finish: " & CStr(ActiveProject.ProjectFinish), _
           vbInformation, "Schedule Forensics - import check"
End Sub

Sub SF_SaveAsMpp()
    ' Save the active project as .mpp beside the source .xml (for SSI / Fuse).
    Dim p As String
    p = ActiveProject.FullName
    If LCase$(Right$(p, 4)) = ".xml" Then p = Left$(p, Len(p) - 4)
    FileSaveAs Name:=p & ".mpp", FormatID:="MSProject.MPP"
    MsgBox "Saved: " & p & ".mpp", vbInformation
End Sub

Sub SF_ImportFolderToMpp()
    ' Batch-convert every TP*.xml in a folder to .mpp (handy for the TP4 series).
    Dim folder As String, f As String
    folder = InputBox("Folder containing the TP*.xml files:", _
                      "Schedule Forensics", "C:\Users\dpolitte\Documents\SF-TestProjects")
    If folder = "" Then Exit Sub
    If Right$(folder, 1) <> "\" Then folder = folder & "\"
    f = Dir$(folder & "TP*.xml")
    Do While f <> ""
        FileOpenEx Name:=folder & f, ReadOnly:=False, FormatID:="MSProject.XML"
        FileSaveAs Name:=folder & Left$(f, Len(f) - 4) & ".mpp", FormatID:="MSProject.MPP"
        FileCloseEx pjDoNotSave
        f = Dir$()
    Loop
    MsgBox "Done - .mpp files written beside the .xml files.", vbInformation
End Sub
```

If `FileOpenEx` pops the import wizard anyway (version-dependent), import the files
manually once — the macro's save/close still does the tedious half.

### Import check — what `SF_VerifyImport` must report

Run it after EVERY import. **The links number is the test**: anything lower means the
import dropped logic and every downstream comparison is invalid. (MS Project absorbs
the UID-0 row into its own project-summary task, so the summaries count excludes it.)

| File | Working | Summaries | Milestones | **Links** | Baselined | Status date | Project finish |
|---|---|---|---|---|---|---|---|
| TP1_Library_Progressed | 23 | 4 | 3 | **30** | 23 | 3/31/26 | 9/17/26 9:00 AM |
| TP2_Bridge_4x10_Calendar | 16 | 3 | 2 | **21** | 16 | 4/6/26 | 11/4/26 5:30 PM |
| TP3_Outage_DCMA_Seeded | 21 | 3 | 2 | **25** | 20 | 4/30/26 | 6/26/26 8:00 AM |
| TP4_DataCenter_v1 / v2 / v3 | 15 | 0 | 2 | **20** | 15 | monthly | 6/5/26 5:00 PM |
| TP4_DataCenter_v4 | 15 | 0 | 2 | **20** | 15 | 4/30/26 | 6/26/26 5:00 PM |
| TP4_DataCenter_v5 | 15 | 0 | 2 | **20** | 15 | 5/29/26 | 7/17/26 5:00 PM |

The task XML mirrors a genuine MS Project export element-for-element (Active/Manual
directly after Name, `CrossProject` in every link, `NewTasksAreManual 0` in the header)
— MSP's XML reader is sequence-sensitive, and a misplaced `Manual` flag once made an
import inherit the machine's "New Tasks: Manually Scheduled" default and drop links.
A pinned test (`test_task_elements_follow_ms_projects_own_export_order`) keeps it so.

---

## TP1 — Library (progressed, ragged actuals) → verify with **SSI**

26 working tasks + 3 milestones; standard 5×8 calendar; statused at 2026-03-31.
Completed and in-progress actuals carry real-world time-of-day raggedness (16:30 /
15:00 / 14:00 finishes; 9:30 / 10:00 / 7:00 starts) — the whole forward path runs at
09:00-on-the-day boundaries, the exact signature of the operator's 4-vs-66 file.

**Recipe:** open `TP1_Library_Progressed.mpp`, run the SSI directional path analysis to
**UID 43 ("Substantial completion")**, export "All Dependencies"; in Schedule
Forensics load the same file → Path Analysis → target 43, bands 10 / 20 → Trace.

> No resource assignments, by design: MS Project's import of minimal `<Assignment>`
> records rescheduled exactly the assigned tasks and dropped every link into them
> (twice, operator-verified — the 23-of-30-links imports). A resource round-trip
> fixture should be authored in MS Project itself and curated later.

Both sides should show (the tool's pinned truth):

| Quantity | Expected |
|---|---|
| Tasks traced to UID 43 | **18** (44/45/15/16 have no logic path to 43 — correctly absent) |
| DRIVING (0 days) | **13** — incl. completed UIDs 11, 12, 13, which carry **210/210/120 minutes** of raggedness and must still read 0 days |
| SECONDARY (≤ 10 d) | **1** — UID 39 at exactly **7 d** |
| TERTIARY (≤ 20 d) | **2** — UID 37 at 15 d; UID 35 at exactly **20 d** (boundary) |
| BEYOND | **2** — UID 21 (~70 d), UID 22 (~24 d) |

If SSI's driving count differs, the per-UID slack column shows which chain diverged —
that is precisely the comparison PR #80 asked for, on a file where the truth is known.

Also worth eyeballing on this file: the report's **Completion performance** panel
(2 ahead / 2 on / 1 behind, avg 1.5 d early / 5 calendar-days late, MEI 1.00) and
**/forecast** (CPM 2026-09-16 · completion-rate 2027-01-31 · IEAC(t) 2027-09-21 — a
deliberately wide spread: progress is slower than plan).

## TP2 — Bridge (4×10 calendar + holidays) → verify with **Fuse** + MS Project dates

15 working tasks; **Mon–Thu, 7:00–12:00 + 12:30–17:30 (600 min/day)**; holidays
2026-05-25, 06-15, 07-02, 09-07; unprogressed.

| Quantity | Expected |
|---|---|
| Working calendar panel (report page) | 10 h/day (600 min), Mon Tue Wed Thu, 4 holidays |
| Project finish | **2026-11-04** — MS Project must compute the same date on import (if it shifts, the calendar didn't survive the trip) |
| Float bands (total float) | 0 d: **7** · < 5 d: **12** (WB chain + UID 16 at 3 d) · < 10 d: **13** (UID 34 at 8 d) |
| DCMA High Duration | **2** (UID 14 at 45 d, UID 34 at 86 d) — UID 13 at **exactly 44 days stays out** (the tripwire is calendar-true: 44 × 600 min, not 44 × 480) |
| High float | UIDs 31/32/33 (> 44 d) |

## TP3 — Plant outage (seeded DCMA violations) → verify with **Fuse DCMA-14**

22 working tasks + 2 milestones; statused at 2026-04-30. Every violation is planted
and counted; run Fuse's DCMA ribbon on the `.mpp` and compare per check:

| DCMA check | Seeded / expected | Offender UIDs |
|---|---|---|
| Logic (missing pred/succ) | **4** of 12 incomplete | 14, 32, 33, 42 (completed dangling tasks fall out of the population — by definition) |
| Leads | **2** | the two negative-lag links into UID 29 |
| Lags | **3** | links into 24, 25, 26 |
| Relationship types | FS = **76 %** (19 of 25) → FAIL; SS 3, FF 2, SF 1 |
| Hard constraints | **2** (9.5 %) → FAIL | 24 (MSO), 41 (MFO) |
| Negative float | **3** (−3 d: the MFO on 41 caps its chain) | 24, 28, 29 |
| High float | **1** | 32 |
| High duration | **2** | 23 (50 d), 24 (60 d) |
| Invalid dates | **4** | 31 (actual finish 05-05 > DD), 25/26/32 (unstatused forecasts wholly before DD) |
| Resources | 10 of 10 unresourced (no resources/costs in this file — by design) |
| BEI | **0.62** (8 finished of 13 due) · Missed activities **7** |
| CPLI | 0.97 (PASS) · Critical Path Test FAIL (the MFO break — expected) |

Where Fuse's number differs from the table, check `docs/PARITY-REPORT.md` first
(known definitional residuals, e.g. the UID-0 row and population rules) before
treating it as a tool defect — and report it either way.

## TP4 — Data-center series v1–v5 → verify Trend / Compare / CEI / the manipulation

Same 14-task project statused monthly (Jan–May 2026). Load **all five** into the tool.

- **The story:** v1–v2 on plan; v3 hides a slip in overdue in-progress work (finish
  still 06-05); v4 reveals it (**06-26**) — and contains the fraud; v5 slips honestly
  to **07-17**.
- **The planted manipulation (v3 → v4), UID 19 "Generator & switchgear procurement":**
  its recorded actual start (2026-02-02) is **erased** and its baseline finish is
  quietly slipped ~2 months. **Compare** (v3 vs v4) must flag both
  `MANIP_ACTUAL_ERASED` and `MANIP_BASELINE_CHANGE` citing UID 19; v2 → v3 must flag
  **neither** (pinned).
- **Trend** orders v1→v5 by data date and shows the finish-date story above; **Bow
  Wave / CEI** gets five monthly snapshots — useful for tuning the view against what
  Acumen's bow-wave deck would show for the same series (open item #5).
- In MS Project/Fuse the v4 file is also a teaching exhibit: variance columns show
  UID 19 clean *because* the baseline moved — the tool is the one that catches it.

## What a discrepancy means

These files are constructed truth: dates were computed with MS Project's own working
-time semantics, and the tool's numbers are pinned by tests. So a disagreement between
the tool and SSI/Fuse on a TP file is a real, reportable finding about one of the two
sides — not noise. Send the file name, the check/UID, and both numbers.
