# ADR-0091 — Driving path between two chosen UniqueIDs (across versions)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0011 (SSI driving slack)

## Context

Operator request: "give me the driving path between two activities I define, and show how it changes
over time." The tool already had (a) `engine/path_trace.py` — ancestor reachability + deterministic
topo order to a focus, (b) `engine/driving_slack.py` — the SSI-parity driving slack to a single focus
UID (the chain controlling that focus), and (c) `engine/path_evolution.py` — a per-version stepper for
the *whole* critical path. What was missing is the **A → B** question: not "what drives B" but "does the
activity **A** I care about drive **B**, through which corridor, and how does that corridor move across
the loaded versions."

## Decision

New `engine/driving_path.py`, built entirely on the existing primitives (no new scheduling math):

- **Primitive added:** `path_trace.descendants_of(schedule, uid)` — the mirror of `ancestors_of`
  (transitive successors over the activity logic network, source excluded, summaries ignored).
- **Corridor.** `driving_path_between(schedule, A, B)` computes the driving slack to focus **B**
  (`compute_driving_slack`), takes the set on B's driving path (slack < 1 working day), and intersects
  it with `descendants_of(A) ∪ {A}`. The result, `topo_order`-ed, is the controlling corridor
  **A → … → B**. `A` **drives** `B` only when A is itself on B's driving path; if A reaches B only
  through activities carrying float the result is flagged **connected but not driving** and the slack is
  reported instead of a path. Parallel equal-driving legs are all included (the honest driving
  sub-network, not an arbitrary single chain). The function is total — absent/summary endpoints return a
  flagged `DrivingPathBetween`, never an exception — so it maps cleanly across versions.
- **Evolution.** `compute_driving_path_evolution(schedules, cpms, A, B)` mirrors
  `compute_path_evolution`: per-version snapshots (oldest → newest by data date) with the corridor, the
  entered/left/stayed diff vs the prior version, the length delta, and a plain-English `change_note`
  for state transitions ("A now drives B", "driving path broke", "logic route A → B lost", endpoint
  appeared/removed).

UI: a server-rendered `/driving-path` page (two UID inputs) renders the corridor as a chain of
UID — name chips per version, colouring activities that **entered** the corridor and listing those that
**left**, with the status/change note. Reuses the existing CPM/driving-slack results the session
already caches. A richer animated Gantt (matching `/evolution`) can follow; the engine and the
server-rendered view stand alone.

## Consequences

- One more lens on the same logic network, exact-reuse of the SSI-parity slack — no parity risk to the
  existing driving-slack golden, and `descendants_of` is symmetric-tested against `ancestors_of`.
- "Drives" is defined on the SSI whole-working-day axis (`on_driving_path`), so a corridor reads the
  same activities the Path Analysis page already marks driving — consistent across the tool.
- Deferred: the animated date-axis Gantt for the corridor (the server-rendered chip view ships now).
