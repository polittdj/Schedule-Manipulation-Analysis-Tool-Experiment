# ADR-0081 — Ribbon Number of Lags / Leads: count activities across all statuses (Fuse fidelity)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0012, ADR-0067, ADR-0080

## Context

Last of the float/logic metrics the operator's progressed real schedule reported differently from
Acumen Fuse's **Schedule-Quality Ribbon**:

| Ribbon metric | Tool (before) | Acumen |
|---|---|---|
| Number of Lags | 5 | **8** |
| Number of Leads | 0 | **1** |

`compute_ribbon` sourced these from the **DCMA-14** checks (`number_of_lags = DCMA03`,
`number_of_leads = DCMA02`). Those checks count distinct successor *activities* with a positive /
negative-lag predecessor but **restrict to incomplete successors** (`percent_complete < 100`) — correct
for the DCMA-14 14-point assessment, which is about remaining work. Acumen's **Ribbon** metric,
however, counts those activities across **all statuses** — "planned, in-progress, **or** complete" (the
Fuse metric guide). On a heavily-progressed schedule the lags/leads into already-finished successors
are real and Fuse counts them; the tool was dropping them, hence 5 vs 8 and 0 vs 1.

## Decision

The Ribbon's **Number of Lags** and **Number of Leads** now count distinct non-summary successor
activities whose predecessor link carries a positive (lag) / negative (lead) offset, **with no
completion filter** — computed inline in `compute_ribbon` from the same non-summary link set it already
walks, instead of borrowing the incomplete-only DCMA-14 counts. This is the definition `schedule_quality`
already uses (and that the goldens pin). The DCMA-14 **DCMA02 / DCMA03** checks are **unchanged** — they
keep the incomplete-only DCMA definition (a separate, validated number; Acumen's own DCMA-14 report and
its Ribbon legitimately differ, e.g. Project5 Ribbon lags 2 vs DCMA-14 lags 1). The `/ribbon` view note
is updated to say the Ribbon's Lags/Leads count all statuses, distinct from the DCMA-14 checks.

## Scope / safety — parity preserved

Verified on every committed Ribbon fixture: the incomplete-only and all-statuses counts are **identical**
for Project2 (lags 2), TP1 (3), TP2 (0), TP3 (3 / leads 1), TP4 v1–v5 (0) — so no pinned `test_ribbon`
value moves. They differ only on Project5 (1 → 2), which the Ribbon test does not pin and where **2 is
the correct Fuse value** (`schedule_quality.number_of_lags` already pins Project5 = 2). The DCMA-14
golden assertions (DCMA02 0/0, DCMA03 2/1) are untouched. `pytest -m parity` **10/10**.

New test (`test_ribbon.py`): a lag and a lead into a 100%-complete successor are counted by the Ribbon
(`number_of_lags == 1`, `number_of_leads == 1`) while the DCMA-14 checks count neither (`DCMA03 == 0`,
`DCMA02 == 0`) — the exact 5→8 / 0→1 mechanism. `docs/FUSE-VALIDATION.md` updated. Full gate green;
ruff/format/mypy/bandit clean.

## Status of the operator's DCMA-14 reconciliation

With this change the operator's float/logic Ribbon metrics all match Acumen on the Large Test File:
Critical 33 and Negative Float 31 (ADR-0080), Lags 8 and Leads 1 (this ADR), alongside the already-
matching Missing Logic 22, Logic Density 3.14, Hard Constraints 1, Merge Hotspot 156. The display
overhaul (count + % + tooltips) shipped in ADR-0079. Remaining genuinely-deferred items are the Fuse
**proprietary** formulas (Float Ratio™, the composite Score) — still awaiting their exact definition.
