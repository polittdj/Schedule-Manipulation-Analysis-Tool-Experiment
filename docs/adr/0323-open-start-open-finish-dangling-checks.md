# 0323 — Open Start / Open Finish dangling-activity checks, per the Bible (OR-05)

Date: 2026-07-31
Status: accepted

## Context

Jacked 1, slide 1 (operator's SME, verbatim intent): "Checking to see if it handles
dangling tasks when checking for missing logic, as opposed to just counting blank
Predecessor and blank Successor fields." The file's two danglers prove the blind spot:
"Dangling Finish (Crit Path Task 2a)" HAS a successor (4SS) but its finish drives
nothing; "Dangling Start" HAS a predecessor (5FF) but nothing drives its start. DCMA-01
counts blank link endpoints, so both passed every logic check the tool carried; no
module in the engine implemented dangling-end detection.

The NASA Acumen metric library ("the Bible") defines the checks by name: **Open Start**
— "Activities where only the predecessor(s) are either Finish-to-Finish or
Start-to-Finish resulting in an open start to the activity"; **Open Finish** —
"Activities where the only successor(s) are either Start-to-Finish or Start-to-Start" —
both "Also known as 'Dangling Activities'", with 5 % / 25 % coloring thresholds and
variants scoped to remaining activities.

## Decision

Two new checks in `engine/metrics/logic_integrity.py` (the parity-isolated home —
NEVER the gate-locked DCMA ribbon, whose DCMA-01 semantics are pinned unchanged by a
dedicated test): `open_start` (has predecessors, all ∈ {FF, SF}) and `open_finish`
(has successors, all ∈ {SS, SF}), scoped to incomplete non-summary activities (the
Bible's "Remaining activities" ribbon variant — a finished activity's dangling end is
no forward risk), offenders as UIDs + labeled strings. The existing `/integrity`
logic-checks panel renders them with no layout change (it iterates the checks tuple).

## Verification

`tests/engine/test_dangling_logic.py`: Jacked 1 flags exactly UID 2 (open start) and
UID 1 (open finish); Jacked 2 flags none; per-link-type truth tables both directions
(FF/SF dangle a start, SS/SF dangle a finish, FS/SS resp. FS/FF do not, a mixed
SS+FS successor set does not); completed activities excluded; no-links-at-all stays
DCMA-01's case; and DCMA-01's offender set on Jacked 1 is byte-identical to before
({4, 15, 22} — the dangling pair NOT folded in). Proved able to fail: all five
behavioral tests failed before the checks existed.
