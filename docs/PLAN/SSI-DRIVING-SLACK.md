# SSI driving-slack — methodology + golden parity targets (UID 143)

Extracted in Phase 1 from the two SSI exports in the Drive intake folder. These are the
**exact numbers the §6.C parity suite must reproduce** when the tool reads `Project5.mpp`,
traces the driving logic path to **UniqueID 143**, and reports **Driving Slack in days** per
task. Source schedule content = the **commercial-construction sample** (notice-to-proceed →
… → certificate of occupancy); non-CUI.

## Source files (Drive IDs)
- `SSI UID_143_Directional_Path_Analysis_2026-6-5-12-47-36.xlsx` — `1Df94frFQBTCsmvqTRJirbcGzaqQbSN0N`
  (directional path with SSI `Path 01/02/03` enumeration; smaller view).
- `SSI - All Dependencies - UID_143_Directional_Path_Analysis_2026-6-5-12-49-11.xlsx` —
  `1m38WlBDnSchVwwQu5TnsPn-oIKKdqSGW` (comprehensive: every task with a driving relationship
  to UID 143). **This is the authoritative golden trace.**

## Export column schema (match exactly)
`Focus Task Name, Focus Task UID, Task Name, Unique ID, Start, Finish, Driving Slack, Drag,
Trace Log Value, Project`
- **Focus Task** = "Obtain certificate of occupancy", **Focus Task UID = 143**, Project = `Project5`.
- **Driving Slack** rendered as `"<n> days"` (matches §3 units). `Drag` = `NA` in these exports.
- **Trace Log Value** = SSI's path enumeration (`Path 01` = primary/longest driving path;
  `Path 02`, `Path 03` = additional distinct converging logic paths). **This is SSI's own
  path numbering — NOT the tool's slack-threshold tiers** (see reconciliation note below).

## Methodology (what the engine must implement)
1. Treat the user-entered **target UID (143)** as the path endpoint/focus.
2. Trace the **driving logic path** backward through driving predecessors.
3. **Driving Slack** for a task = how many `days` it can slip before it would delay the focus
   task along its path ≈ (driving-path length to focus) − (this task's path length to focus).
   Tasks **on** the longest/driving path have **0 days** driving slack.
4. Results must equal **MS Project + SSI** for this project/UID exactly.

## Golden Driving-Slack targets (focus UID 143, from the "All Dependencies" export)
Grouped by driving slack (days) → the UniqueIDs at that slack. Tool must reproduce each.

| Driving slack (days) | UniqueIDs |
|---|---|
| **0** (driving path) | 35, 38, 39, 42, 44, 48, 49, 51, 52, 53, 55, 57, 58, 60, 61, 62, 63, 65, 66, 67, 68, 69, 78, 82, 94, 95, 99, 100, 106, 135, 138, 139, 140, 141, 142, **143** |
| 5 | 26, 27, 29, 30, 31, 33, 96, 107 |
| 7 | 25, 108, 109 |
| 10 | 118 |
| 12 | 3, 19, 20, 21, 22, 23 |
| 16 | 64 |
| 20 | 102, 103, 104, 105, 125 |
| 25 | 101, 122, 123 |
| 35 | 97, 115, 117, 121 |
| 37 | 28, 56 |
| 46 | 133, 134 |
| 80 | 85, 116 |
| 99 | 59, 71, 72, 74, 75, 76, 80, 84, 86, 120 |
| 100 | 9, 11, 17, 70, 73 |
| 152 | 15 |
| 166 | 50, 81, 111, 112, 113 |
| 176 | 8, 16 |
| 177 | 14 |
| 192 | 7 |
| 201 | 41, 43, 45, 46 |
| 252 | 34, 36, 37, 40 |
| 347 | 13 |

(The complete per-row export — task names, start/finish — is in the Drive files above; turn
it into a committed **parity fixture** in Phase 2. Schedule is non-CUI sample data.)

## Path-tier classification (user-configurable; §6.C) vs. SSI Path NN
- The **tool's** path tiers are a **driving-slack magnitude** grouping the user sets at upload:
  - **Critical/driving:** 0 days.
  - **Secondary:** driving slack **> 0 and ≤ 10 days** → from the table: UIDs at 5, 7, 10 days.
  - **Tertiary:** driving slack **> 10 and ≤ 20 days** → UIDs at 12, 16, 20 days.
  - (> 20 days = beyond tertiary.)
- **SSI's `Path 01/02/03`** is a *different* concept (distinct converging logic paths), so do
  not equate `Path 02`/`Path 03` with secondary/tertiary. Present both: SSI-parity driving
  slack per task, and the tool's threshold tiers.

## Phase-2 acceptance (RTM C2/C3)
Reading `Project5.mpp`, with target UID 143: the tool reproduces every task's **Driving Slack
in days** above exactly (UniqueID-keyed), and classifies secondary/tertiary by the user's
thresholds (default 0<s≤10, 10<t≤20). Any deviation is a defect to drive to zero.

## Open reconciliation items (Phase 2)
- Confirm the precise SSI definition of `Driving Slack` and `Path NN` against the SSI/Acumen
  docs (`DeltekAcumen811MetricDevelopersGuide.pdf`) so the engine matches edge cases.
- Confirm calendar/working-time and status date from `Project5.mpp` once provided (needed to
  reproduce the dates and slack exactly).
