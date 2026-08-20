# ADR-0429 — The ribbon's "Hard Constraints" was a different metric of the same name

- **Status:** Accepted
- **Date:** 2026-08-20
- **Closes:** the ADR-0110 drift rows for `hard_constraints`/`DCMA05` (classified *latent* there)
- **Relates:** ADR-0280 (Acumen-parity DCMA population), ADR-0079/0081 (ribbon Fuse calibration)

## The report

Operator, with screenshots of both tools on the same six files (Starlight V05–V10, uploaded to the
build session; non-CUI, marked fictional):

> Why does the program say a different value for the number of hard constraints than Acumen Fuse
> for the same files. They should be the same. Find the root cause and fix this.

POLARIS's Schedule Quality Ribbon showed **1** for every version; Fuse's Ribbon Analyzer showed
**4 (1%)** for every version.

## Reproduced, then root-caused on the real files

The six `.mpp`s were converted via the vendored MPXJ and censused. Every version carries the same
14 constraint-typed activities: **3 MSO** (the review-cadence series, 100% complete), **1 MFO**
("Flight Data Recovery & Reduction", incomplete), **4 SNLT**, **6 FNLT** (5 in V05/V06).

| candidate definition | count on Starlight | matches |
|---|---|---|
| {MSO,MFO,SNLT,FNLT}, all statuses (the tool's `has_hard_constraint`) | 13–14 | nothing shown anywhere |
| DCMA05, default population (all non-summary) | 13–14 | ribbon with parity OFF |
| DCMA05, Acumen-parity population (baselined incomplete) | **1** | **what the page showed** |
| **{MSO,MFO}, all statuses** | **4** | **Fuse, every version** |

The ribbon sourced its cell from `_audit_count(audit, "DCMA05")`, and the session default
`dcma_acumen_parity=True` scoped that count to baselined incomplete work — so the page showed 1
(only the MFO survives: the three MSOs are complete). Fuse showed 4.

## The Bible names both metrics — they are not the same one

`NASA Metrics_Complete_*.aft` (both committed snapshots), verbatim:

- **"Hard Constraints"** (the Ribbon metric):
  `SUM(((ActivityConstraint="MandatoryStart")+("MandatoryFinish")+("MustStartOn")+("MustFinishOn")+("StartAndFinish")>0)*1)`
  — must/mandatory dates only, **no status or baseline filter**. The library files
  StartOnOrBefore/FinishOnOrBefore under **"Soft Constraints"**.
- **"5. Hard Constraint"** (the DCMA-14 metric): the same list **plus**
  `StartOnOrBefore` + `FinishOnOrBefore` — the {MSO, MFO, SNLT, FNLT} set the tool's DCMA05
  correctly implements (parity-validated against Acumen's own DCMA report, ADR-0280).

Every P6 name in the ribbon formula reaches this model as MSO or MFO (XER: `CS_MSO`/`CS_MANDSTART`
→ MSO, `CS_MEO`/`CS_MANDFIN` → MFO; `StartAndFinish` has no MSP/XER mapping), so `{MSO, MFO}` is
the formula's exact projection. On Starlight: 3 MSO + 1 MFO = **4**, constant across versions —
Fuse's number, to the digit, with Fuse's 1% (4/598).

**The audit table already knew.** ADR-0110 had classified both rows as `drift` with the note
*"Latent: no parity impact unless a schedule carries SNLT/FNLT."* Starlight is that schedule. And
the original Fuse calibration could not catch it: on every in-repo reference fixture the
definitions **coincide** (TP3's two hard constraints are 1 MSO + 1 MFO, incomplete and baselined —
identical under all four candidate definitions; every other fixture is 0). An oracle that returns
the same verdict in both worlds is blind, not confirming.

## Decision

1. **`model/task.py`** — `_MANDATORY_CONSTRAINTS = {MSO, MFO}` + `Task.has_mandatory_constraint`,
   documented as the Bible ribbon formula's projection.
2. **`engine/metrics/schedule_quality.py`** — `hard_constraints` counts the mandatory set over
   ALL non-summary statuses (its population was already all-status; only the type set narrowed).
   This figure feeds the ribbon, the §A trends, and the workbench.
3. **`engine/metrics/ribbon.py`** — the ribbon cell and its drill-down offenders source from
   `schedule_quality` (the single-formula pattern Insufficient Detail already uses), **never**
   from DCMA05 — so the displayed value can no longer depend on the session's DCMA-parity toggle.
4. **DCMA05 unchanged** — it is the Bible's "5. Hard Constraint" and Acumen's DCMA report agrees
   with it (the DCMA card's "1 Hard constraints" on Starlight V10 is *correct DCMA*). The
   formula-audit rows reclassify: `hard_constraints` drift→**match**; `DCMA05` re-pinned against
   its true Bible counterpart "5. Hard Constraint" (drift→match), pin proven able to fail by a
   dropped-term mutation against both committed snapshots.
5. `web/ribbon.py` legend and `web/help.py` definition + formula updated;
   `docs/METRIC-DICTIONARY.md` regenerated. `constraint_health` (Unsatisfied Constraints) keeps
   the 4-type cap set — that matches its own Bible formula.

The two same-named figures now agree with their respective Acumen products: ribbon **4** ↔ Fuse
Ribbon Analyzer 4; DCMA card **1** ↔ Acumen DCMA report hard filter. The ADR records this
deliberately: the numbers *differ from each other* because Acumen's own products differ.

## Verification

- Red-first discriminating fixture (2 complete MSO + 1 complete SNLT + 1 incomplete-baselined
  FNLT): mandatory-all=2 · DCMA05-default=4 · DCMA05-parity=1 — observed red at 4≠2 before the
  fix; green after; **five mutations red by name** (set widened back; ribbon re-sourced from
  DCMA05; completion filter added; offender source skewed alone; Bible pin with a dropped term).
- All six Starlight versions through the app's own `/ribbon` route (parity default):
  **rendered cells 4/4/4/4/4/4**, offenders = UIDs 25/26/27 (MSO, complete) + 679 (MFO) — the
  exact activities Fuse counts. Mode-independence asserted under both audits.
- Fuse reference pins (`test_ribbon.py::_FUSE`) unchanged and green — including TP3's non-zero 2.
- Engine suite 1034 passed; statics green whole-tree.

## Adjacent findings — taken up in the same session as ADR-0430

The operator widened the ask to every mismatch. **ADR-0430** root-caused and fixed the Negative
Float column (Fuse arithmetic = STORED Total Slack < 0; reproduced 6/6) and the calendar warning
(a pattern-less base calendar whose 112 holidays were silently discarded), and measured the
Insufficient Detail V05/V06 leg into a genuine oracle contradiction — six hypotheses refuted —
now BLOCKED on Fuse's own offender list for one cell. See ADR-0430.

The Starlight files stay out of the repo (operator uploads, `.mpp` blocked by the guard; the
converted MSPDI XMLs live only in the session scratchpad). Their measured numbers are recorded
here; the committed regression tests carry the class via synthetic and TP3 fixtures.
