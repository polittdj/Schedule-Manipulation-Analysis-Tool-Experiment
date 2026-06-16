# ADR-0056 — Critical-Path Evolution: filter-by-path (four switchable modes)

Date: 2026-06-16 · Status: accepted

## Context

Final item of the evolution-view enhancements. "Filter by path" was ambiguous, so the operator
was offered four readings and chose **all four, switchable** — a mode selector on the
Critical-Path Evolution Gantt that scopes which activities show.

## Decision

A `filter the path` selector (`#evoFilterMode`) toggles between five states; each non-trivial
mode reveals its own sub-control. The filter is applied in `render()` to **both** the critical
rows and the dashed "left the path" ghost rows, composed after the hide-completed filter:

1. **none** — the whole critical path (default).
2. **driving path to the focused UID** — the focused activity plus its **transitive
   predecessors** in that version. Computed server-side: `_evolution_data` walks the version's
   relationships backward from the target and echoes a per-snapshot `path_to_target` UID list
   (empty without a focus); the client filters rows to that set. Honest scope: it is "the
   activity and its predecessors on the path", not a single binding longest-chain.
3. **track one version's path** — pick a version (`#evoFilterVersion`, populated from the
   snapshots); show only the activities on **that** version's critical path, tracked across
   every frame (using each snapshot's already-served `critical` list — client-side).
4. **entered / left / stayed** — three checkboxes (`.evoMove`) filtering rows by how they
   moved (`r.kind`), to isolate the churn between versions.
5. **name / UID search** — a text box (`#evoFilterText`) matching the activity name or UID
   substring.

A note line (`#evoFilterNote`) explains the active scope (e.g. prompts for a Focus UID when
the driving-path mode has none). The section heading shows "N of M activities" when filtered.

## Scope / safety

Modes 3–5 are pure client-side over data already served; mode 1 adds one additive field
(`path_to_target`) computed from the schedule's relationships — no engine/CPM/attribution
change, `compute_path_evolution` untouched. Still dependency-free inline SVG (air-gap intact).
New tests pin the predecessor-closure data (empty without focus; contains the target with one)
and that the page/JS expose all four filter behaviours. Full suite green (839 passed);
ruff/format/mypy clean; JS `node --check` clean.
