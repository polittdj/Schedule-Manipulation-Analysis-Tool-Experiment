# The two DCMA views: Pure-logic (forensic) vs Acumen Fuse parity

The tool scores the 14 DCMA checks two ways. A single **"Acumen Fuse parity mode"** toggle on the
Analysis page switches between them. **They agree on a clean, fully-baselined schedule** and diverge
on real progressed schedules that have milestones, un-baselined tasks, and imposed deadlines.

Neither is "more correct." They answer **different questions**:

- **Pure-logic (default, toggle OFF)** — *"What does the schedule's own logic say, right now, if I
  recompute everything from scratch?"* An independent forensic recomputation.
- **Acumen parity (toggle ON)** — *"What would Acumen Fuse report on this exact file?"* A faithful
  reproduction of Acumen's published DCMA definitions, verified activity-for-activity.

---

## The differences at a glance

| Dimension | Pure-logic / forensic (default) | Acumen Fuse parity |
|---|---|---|
| **Total Float** | The engine's freshly **re-computed CPM float** (independent of the file's stored dates). | The file's **stored, progress-aware Total Slack**, compared in **whole days** — exactly what Acumen reads. |
| **Which activities count** | Every incomplete activity, whether or not it was baselined. | Only activities with a **baseline duration ≥ 1 day** (Acumen's *Baseline Duration > 0*, truncated to whole days). Milestones are kept when they carry a real baseline. |
| **Resources (check 10)** | Incomplete, real-duration activities with **no named resource**. | Activities with **no baseline cost AND no baseline work** (a task can lack a named resource yet still carry work). |
| **Invalid Dates (check 9)** | Every non-summary activity whose stored start/finish is already past the data date without a matching actual (or an actual beyond it). | The same date logic, scoped to **Baseline Duration > 0** — no-baseline placeholders and milestones are dropped, matching Acumen's flagged-activity detail (Large Test File2: 182 → 173). |
| **CPLI (check 13)** | Recomputed critical-path float — ≈ 0 with no imposed deadline, so CPLI reads **1.0**. | Stored float + stored remaining duration — reflects a behind-schedule finish. |
| **BEI (check 14)** | Complete ÷ baselined-due (Normal tasks). | Acumen's **two-term** denominator: baselined-due **plus** activities that have a duration but are missing a baseline; milestones included. |

> Under the hood, "Acumen parity" is taken **verbatim from the NASA Acumen metric library** (the
> `.aft` file) — each metric's formula and its population filter — and verified to match Acumen's
> ribbon **activity-for-activity** on the reference schedules.

---

## Real-world examples

**1. A "Project Complete" milestone with a Must-Finish-On date.**
Pure-logic counts it under *Hard Constraints* (it does carry a mandatory constraint). Acumen parity
does **not** — a zero-baseline-duration milestone fails *Baseline Duration > 0*. So a schedule the
forensic view says has "1 hard constraint" shows **0** in an Acumen report.

**2. A planning-package task with the MS Project "unassigned work" placeholder but no named resource.**
Pure-logic flags it under *Resources* (no named resource). Acumen parity does **not**, because the
task still carries **baseline work** — Acumen treats it as resourced.

**3. A task 7 hours behind an imposed deadline (about −0.29 day of float).**
Pure-logic flags *Negative Float*. Acumen parity does **not**: Acumen shows Total Float in **whole
days**, so −0.29 rounds to 0 (not negative). A task a full day or more behind is flagged by both.

**4. A behind-schedule program with slack consumed on the driving path.**
Pure-logic **CPLI** reads **1.0** (with no imposed deadline in the logic, the recomputed critical-path
float is ≈ 0 — the project "looks on-track"). Acumen parity reads **< 1.0** (e.g. 0.97 or 0.59),
correctly showing the slip, because it uses the file's stored float and stored finish date.

**5. An in-progress task that was never baselined.**
It doesn't affect pure-logic *BEI* (no baseline finish, so it isn't "due"). Acumen parity's second
denominator term counts it as work that *should* have been baselined, lowering **BEI**.

**6. A milestone or planning placeholder with no baseline and a stored date before the data date.**
Pure-logic flags it under *Invalid Dates*. Acumen parity does **not** — with no baseline duration it
fails *Baseline Duration > 0*, so Acumen never lists it. (Acumen's ribbon also counts invalid *date
fields* — a start flag and a finish flag can both fire on one activity, so the ribbon number runs up
to ~2× the activity count; the tool reports **one row per activity**, matching Acumen's activity
**detail**, not the ribbon's field tally.)

---

## When to use which

### Use **Pure-logic / forensic** (default) when…
- You are doing **independent forensic analysis** — delay analysis, driving-path analysis,
  as-planned-vs-as-built — and want the tool's **own recomputation**, not the file's stored dates.
- The schedule is **draft or un-baselined**, or you don't trust the baseline. Pure-logic still
  surfaces every issue the logic exposes; Acumen parity would report many checks as empty (no
  baseline ⇒ nothing passes *Baseline Duration > 0*).
- You want the **most conservative** read — it flags *every* activity with an issue, baselined or not.

### Use **Acumen Fuse parity** when…
- You need to **reconcile with, or defend against, an Acumen Fuse report** — e.g. a customer's or
  government DCMA scorecard. The counts will match Acumen's ribbon activity-for-activity.
- The **baseline is authoritative** and current, and you want the metric population Acumen uses.
- You are in a **testimony or audit** context where **Acumen is the reference tool** and the numbers
  have to be defensible against it.

---

## Notes

- Switching the toggle **never changes the data** — only how the 14 checks are scored. Both views
  cite the same underlying activities.
- The toggle applies **end-to-end** (ADR-0285): the findings on *Risks & Opportunities*, the AI
  narrative, the risk matrix and the Executive Briefing (including its verdict) are all derived from
  whichever view is active, so the ribbon and the prose always cite the same numbers. Baseline
  compliance has a single Acumen-validated definition and is the same in both views.
- The **default is unchanged** by this feature, and the tool's validated golden parity (Project2 /
  Project5) is unaffected — those schedules carry no sub-day baselines, so both views agree on them.
- Details and the formula provenance are in **ADR-0280** (which supersedes the earlier milestone-scope
  and stored-float-CPLI options, ADR-0277/0278/0279); the Invalid-Dates (check 9) population scoping is
  **ADR-0283**.
