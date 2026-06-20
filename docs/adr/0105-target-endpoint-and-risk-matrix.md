# ADR-0105 — Target UID as analysis endpoint + quantified 5×5 risk matrix

Status: accepted (2026-06-20)

## Context

Two operator requests:

1. **Target UID must be a real, session-wide *endpoint*.** Previously a Target UID only
   *focused/highlighted* an activity on a handful of views. The operator wants entering a UID in
   the top ribbon to apply to **every page**, with every metric and visual **recomputed using the
   target as the schedule's endpoint** — any activity that does not lead to the target omitted from
   the calculations and the charts. (The existing session-wide group/filter, ADR-0104, already
   demonstrates the pattern: one chokepoint scopes the whole tool.)

2. **The Risks page needs a quantified 5×5 risk matrix + ranking.** Risks rated by *likelihood of
   occurrence* and *severity of potential schedule impact*, quantified with how much float (and
   driving float to the target, when set) each carries and how much schedule slip it would cause if
   realised — high-level first, supporting detail beneath.

## Decision

### Endpoint rule — "Target + its drivers"

When a Target UID is set, the analysed population is the target **plus its transitive logic
predecessors** (`engine.path_trace.ancestors_of` ∪ {target}); the target's successors and any
activity that cannot drive it are omitted. The operator chose this over a date-based cut ("omit
activities finishing after the target") because it is the forensically meaningful *"analysis to a
milestone"*: it treats the target as the project finish and pairs exactly with the existing
"driving float to target" measure. A task's early finish depends only on its predecessors, so the
target's own computed finish is identical truncated or not — the existing focus panels are
unaffected, only the *population-wide* numbers narrow.

Implemented as `engine.path_trace.subschedule_to_target(schedule, target_uid)` — mirrors
`grouping.filter_schedule` (kept tasks + relationships among them; project frame preserved), so
every existing engine analysis runs over the sub-network unchanged.

Wired through the **single scope chokepoint**: `SessionState.scope()` now applies the filter and
then, when a target is set and present in that version, the endpoint truncation; `analysis_for()`
and `ordered()` already funnel through it, so every metric/audit/visual on every page (and every
loaded version) recomputes automatically. `set_target()` invalidates the scope/analysis/narrative
caches (mirroring `set_filter`). A version that does not contain the target keeps its full
(filtered) population. A page-top **"Analysis endpoint: UID X (N omitted)"** banner appears on
every page, with one-click clear. Default (no target) is a no-op, so **parity stays locked**.

### Quantified risk scoring

`engine.recommendations` gains a `Likelihood` enum (CERTAIN…RARE) and a deterministic, CPM-cited
quantification pass (`_quantify`) run at the end of `recommend()`:

- `float_days` — the tightest total float among the finding's cited activities.
- `impact_days` — schedule exposure = `max(0, −float_days)` (negative float = days already behind).
- `driving_float_days` — tightest driving slack to the target (only when a target is set).
- `likelihood` — CERTAIN when there is real exposure, else a severity fallback.
- `impact_score` / `likelihood_score` (1–5) and `risk_score` = impact × likelihood (1–25), via
  `impact_rank` / `likelihood_rank` band helpers.

The `/risks` page renders a **5×5 likelihood × impact heat-map** (server-rendered, conventional
risk colours, accessible table with `scope` headers + an `.sr-only` caption), a **score-ranked
list** with the quantified figures, and per-finding quantified reads — all engine-computed and
cited, with the local-AI narrative on top (the "AI can err — verify against citations" rule holds).

## Consequences

- The forensic numbers shown when a target is set are explicitly *"to the milestone"*; the banner
  states this and the omitted count, so a reviewer is never misled about the scope.
- Scores are deterministic and cited (defensible in a testimony context, Law 2); the AI only
  narrates, it never assigns a figure.
- New scoring fields are appended to `Finding` with defaults, so existing findings/tests/parity are
  unchanged. Default (no target, no filter) behaviour — and the parity gate — are byte-identical.
