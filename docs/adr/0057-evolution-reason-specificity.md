# ADR-0057 — Critical-Path Evolution: reason specificity (richer attribution detail)

Date: 2026-06-17 · Status: accepted

## Context

The evolution view (ADR-0044/0048) attributes every activity that **entered** or **left** the
critical path between two versions with a short `reason` code and a plain-English `detail`
(surfaced in the reason-chip hover — the SVG `<title>`). The reasons were honest but **coarse**:

- `slack_consumed` / `gained_float` said only "a slip elsewhere consumed its float" / "gained
  float" — without naming *which* activity's slip, the most forensically useful fact.
- `logic_added` / `logic_removed` said "N logic links added/removed" — without citing *which*
  predecessor/successor link(s).
- `duration_up` / `duration_down` showed `from → to` but not the signed delta or percent.

The operator asked for specificity so the hover answers "*entered/left because of what,
exactly?*".

## Decision

Enrich the `detail` strings produced by `_classify_entered` / `_classify_left`. **The `reason`
codes are unchanged** — only the human-readable `detail` gets more specific — so every existing
golden pin and view test (which assert on reason codes) stays valid, and the richer text flows
to the chip hover with **no client change** (`path_evolution.js` already binds `r.detail` into
the chip's `<title>`).

1. **`logic_added` / `logic_removed`** cite the specific link(s) relative to the activity: a
   predecessor (`←`) or successor (`→`) edge naming the other endpoint (name + UID + link type),
   up to three then `+N more`. Added links resolve names from the current version; removed links
   from the prior version (where they still existed).
2. **`duration_up` / `duration_down`** quantify precisely: signed working-day delta, `from → to`,
   and percent — e.g. `Duration increased +2wd (1wd → 3wd, +200%).`
3. **`slack_consumed`** names the slip that consumed the float: the transitive **predecessor**
   with the largest positive early-finish slip (its driving chain) is cited first; if no
   predecessor slipped, the **largest slip anywhere** is named as the likely driver (honestly
   scoped as "elsewhere", not asserted as strict causation).
4. **`gained_float`** (the symmetric "left" case) quantifies the float-relevant movement: the
   activity's own early-finish move vs the project-finish move.
5. **`completed`** cites the progress and actual-finish date.

A new private `_PairContext` carries the CPM-derived, per-version-pair movement the classifiers
need — `slip_days` (each activity's early-finish move in calendar days), the current-version
predecessor map, and the project-finish delta — computed once in `compute_path_evolution`. It is
an **optional** classifier argument, so the existing direct-call unit tests (which pass no
context) still exercise the reason codes and fall back to the prior generic phrasing.

## Scope / safety

Engine-only change to `engine/path_evolution.py` plus tests. No new fabricated values: every
named slip/link/delta is read from the loaded versions' tasks, relationships, and CPM results.
Reason codes, the JSON shape, and the client are untouched (the enriched `detail` rides the
existing field into the existing hover). Quantifying the duration change on activities that
*stayed* critical (the `▲` badge) is deliberately out of scope here — a possible follow-up.

New golden-backed tests pin the enriched detail on the P2→P5 pair (completed cites `%`;
gained_float cites the project-finish move) and unit tests pin each enrichment (link citation,
quantified duration, named upstream slip, fallback to the largest slip). Full suite green;
ruff/format/mypy clean.
