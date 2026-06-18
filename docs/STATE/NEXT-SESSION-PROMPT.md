# Kickoff prompt for the next session

Paste the block below to start the next session. **Re-attach the files listed** — uploads from the
previous session do not carry over.

---

We're mid-way through a multi-part feature request on the Schedule-Manipulation-Analysis tool. `main` is
green at PR #150 (`731a432`). Read `docs/STATE/HANDOFF.md` (the post-#150 START HERE block) first, then
continue.

**Already shipped & merged this session:** custom-field mapping (#148, ADR-0088), HMI new metric (#147,
validated EXACT vs Acumen), BEI corrected & Acumen-validated (#149, ADR-0089), CPLI fix (#146), and the
group-by/filter **engine** (#150, ADR-0090). The value-audit against my new Acumen ribbon reports is
ongoing — HMI matched exactly; BEI was corrected to `complete Normal tasks / Normal baselined-due`.

**Build next (this is what I picked):** the **driving path between two UniqueIDs I define, and how it
changes across the loaded schedule versions** (animate/diff over time). Build the engine
(`engine/driving_path.py`) on top of `engine/path_trace.py` (`ancestors_of`, `topo_order`),
`engine/driving_slack.py` (`compute_driving_slack`, `on_driving_path`, `date_basis`), and the CPM
`TaskTiming`/`critical_path`; then a `/driving-path` page with two UID inputs that shows the controlling
chain per version and how it shifts, in the same multi-version style as the Trend/HMI/S-curve views. Add
tests and an ADR. After that: the **grouping/filter UI** (wire `engine/grouping.py` into the dashboard —
≤5-field picker that scopes every metric + a per-group scorecard like BEI-per-CA-WBS) and a **column
picker** to display chosen custom fields. Then keep value-validating CEI / critical-path against the
`Ribbon Analysis` sheet in the edited DCMA report (CEI/FEI/BRI/TC-BEI/EVM values are in there).

Work on branch `claude/<name>`, one PR per piece, full gate green before each push (ruff/format/mypy/
bandit + pytest + parity), update `docs/STATE/HANDOFF.md` and `SESSION-LOG.md`, and keep `.mpp/.xlsx/.aft`
out of git (CUI; pre-commit guard is active).

**Please re-attach these files** (same set as last session, in `/root/.claude/uploads/...` before):
- `Large_Test_File.mpp` (v1 original, status 2025-02-07)
- `Large_Test_File2.mpp` (v2 edited, status 2025-03-10) — has 69 populated custom fields incl. CA-WBS
- `Workbook1__DCMA_Report.xlsx` (edited, 2-version Ribbon — the BEI/HMI/CEI validation data)
- `Workbook1.1__Quick_Add_Metrics.xlsx`
- `NASA_Metrics_Complete_*.aft` (the Acumen metric "Bible" — exact formulas)

---

## Quick reference (engine entry points already on `main`)

- **Custom fields:** `task.custom_field("CA-WBS")`, `task.custom_field_map`, `schedule.custom_field_labels`.
- **Grouping/filter (`engine/grouping.py`):** `available_fields(s)`, `field_value(s, task, field)`,
  `select(s, criteria)`, `filter_schedule(s, criteria)` (sub-schedule → run any metric on it),
  `group_values(s, field)` (per-value UID groups). `criteria = [(field, value), …]`, ≤5, AND-combined.
- **Path primitives:** `engine/path_trace.ancestors_of` / `topo_order`; `engine/driving_slack.*`.
- **Convert mpp→MSPDI:** `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <in.mpp> <out.xml>`.
- **Value-validation method:** parse the `.xlsx` with openpyxl; the `Ribbon Analysis` sheet maps metric
  names (header row 9) to v1 (row 10) / v2 (row 11) **by absolute column index** (Acumen's pivot has gap
  columns — align by column, not by filtered position).
