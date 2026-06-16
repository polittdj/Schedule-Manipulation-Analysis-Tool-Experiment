# ADR-0043 — Logic on summary tasks: schedule as MS Project does, and flag it

Date: 2026-06-16 · Status: accepted

## Context

Verifying the operator's reference **Duration Bomb** `.mpp` (re-deposited, confirmed a
non-CUI test file) surfaced a real gap. Our CPM computed a project finish of **2026-08-05**
while the file's stored *and* baseline dates run to **2027-02-24** (61 of 71 activities
carried stored finishes up to 238 days beyond their logic-computed dates). The cause was
**not** manipulation or stale dates: the file (a downloaded MS Project sample) attaches
**predecessor/successor logic to summary tasks** — e.g. summary UID 151 ("6 Months +")
sits on an FS chain (175→151→152→… with 40–60-working-day lags), and its child UID 17
inherits that delay. MS Project honors logic on a summary by applying it to the summary's
children; our CPM excluded summary tasks from the network entirely (they are date
roll-ups), so it dropped all 18 summary-touching relationships and packed the children at
the front.

Operator direction: *"always check for these instances and calculate dates as MS Project
would, however flag the fact that there is logic on summary tasks."*

## Decisions

1. **Lower summary logic onto leaf descendants** (`engine/summary_logic.py`):
   `lower_summary_relationships(schedule)` replaces every summary endpoint of a
   relationship with the summary's non-summary (leaf) descendants — the cross-product,
   relationship **type and lag preserved**. For finish-to-start logic (the dominant case)
   this is exact: a summary predecessor's roll-up finish is the max of its leaf finishes
   (every lowered FS edge contributes that max), and a summary successor's start constrains
   every child (every lowered edge pins a child). The lowered, leaf-only relationships feed
   the **existing** CPM unchanged — `compute_cpm` now builds its edge set from the lowered
   relationships.

2. **Hierarchy from the WBS code** (segment-prefix: `6.1` is the parent of `6.1.2` but not
   of `6.10`). The model carries no parent/outline field, so WBS is the available — and, on
   the reference file, correct — hierarchy signal. Documented as the assumption.

3. **Parity preserved by construction.** When no relationship touches a summary,
   `lower_summary_relationships` returns the schedule's relationships **unchanged** (the same
   object). The curated parity schedules (Project2/Project5) carry **zero** summary logic
   (pinned by a test), so their CPM is byte-identical and `pytest -m parity` stays 10/10.

4. **Flag it** (`engine/recommendations.py`): a new MEDIUM-severity finding
   `logic_on_summary_tasks` cites every summary that participates in a relationship — the
   DCMA/PMI anti-pattern the operator asked to surface. The tool schedules the file
   faithfully **and** reports the bad practice. Documented in the metric dictionary
   (`logic_on_summary_tasks`).

## Result (verification)

The Duration Bomb now computes a finish of **2027-02-24** — the file's own stored "Wedding
COMPLETE" date — and UID 17 lands on its stored 2026-07-27; the `logic_on_summary_tasks`
finding fires citing all 18 summaries. (The 2027-02-24 result matches the file's stored
dates; the operator's remembered "~2027-03-04" is within rounding of the same milestone.)

## Scope / safety

A core CPM enhancement, but gated: no-op without summary logic, so parity and every
existing schedule are unchanged (full suite + 10/10 parity verified). Lowering is exact for
FS and a conservative endpoint-expansion for SS/FF/SF (the reference file and the vast
majority of real logic is FS). The WBS-prefix hierarchy is the documented assumption; a
future importer change could carry an explicit outline/parent for files with non-hierarchical
WBS. Nothing leaves the machine; the test `.mpp` stays git-ignored in `00_REFERENCE_INTAKE/`.
