# ADR-0230 — NASA schedule-margin: terminology, a confirmed margin-task overlay, dual numbers, and the 50%-consumed corrective flag (F3a/3b)

## Status

Accepted. Feature 3a/3b of the SMAT v4 build (grouped ingestion → scale/RAM → **NASA margin** →
roles → parameterized margin). Extends the existing margin engine (`engine/metrics/margin.py`,
`engine/margin_dashboard.py`) and its UI; no parity impact (margin stays off the Fuse ribbon / metric
dictionary, like `health_extra`).

## Context

The tool already computed **effective margin** (zero every margin activity, re-solve CPM, measure how
far the finish pulls in) and the burn-down / erosion dashboard. The operator asked to (a) label
**MARGIN vs CONTINGENCY vs FLOAT** distinctly and cite the NASA Schedule Management Handbook on each
surface; (b) let the operator **confirm/deny which activities are margin** rather than trust the
name-substring heuristic alone; (c) show **BOTH** cumulative effective margin **and** the sum of
margin-task durations, stating they can differ; and (d) flag the **50%-consumed corrective-action
threshold** with a planned-depletion line.

Citations were verified against the committed reference PDF
(`00_REFERENCE_INTAKE/references/schedule-management-handbook-20240315-update.zip`): schedule margin is
established as a managed activity (§5.5.11, "the handbook places emphasis on identifying and managing
schedule margin over float"); the corrective threshold is stated verbatim — **"The corrective action
threshold is set where the margin is 50% consumed"** (§7.3.3.1.6 Margin Consumption / §7.3.4 Corrective
Action). No section number or figure was invented.

## Decision

- **Terminology (F3a).** A cited, collapsed MARGIN/CONTINGENCY/FLOAT glossary (`_margin_terminology`)
  renders on the margin panel and the dashboard: margin = a separately-planned buffer *activity*
  (§5.5.11); contingency = the calendar's non-working time to the target; float = a computed CPM
  quantity the handbook manages margin *over*.
- **Confirmed overlay (F3b).** `SessionState.margin_overlay: dict[key, frozenset[int]]` — the
  operator ticks the activities that ARE margin on each version's analysis page (`POST /margin/confirm`).
  `margin_candidates()` surfaces **primary** matches (name has "margin") pre-ticked plus **near-miss**
  aliases (reserve / contingency / integrated return) unticked, each with deciding context (duration,
  total float, criticality). An opt-in `margin_uids: frozenset[int] | None` is threaded through all
  four engine selection sites (`compute_margin`, `compute_margin_trend`, `_margin_month`,
  `compute_margin_dashboard`); `None` reproduces the name-based default exactly (behavior-preserving).
  An explicitly empty confirmed set is a deliberate "no margin" (not a reset). The cross-version
  burn-down/trend use the union of confirmed sets (margin-task UniqueIDs are stable across a project's
  versions); the per-version panel uses that version's own set.
- **Dual numbers.** `MarginMonth.total_margin_wd` (sum of durations) is reported alongside
  `effective_margin_wd` on the panel cards, the dashboard KPI strip, the per-version table, and the
  Excel/Word export, with copy stating the two differ when margin sits on a path with float.
- **50%-consumed corrective flag.** `MarginMonth.consumed_pct` / `.corrective_action` derive from the
  carried-forward planned month-start margin; `corrective_action` trips at `consumed_pct >= 0.5`. It
  surfaces in the takeaway, KPI trigger, a per-version "Corrective" column, and a caret marker on the
  burn-down; the burn-down also draws a dashed **planned-depletion** line. All cited to §7.3.3.1.6 /
  §7.3.4.

## Consequences

- No engine-number change on the default (name-based) path — parity untouched; the overlay only takes
  effect once the operator confirms a set. The persisted SQLite summary stays name-based (its cache key
  is the file content hash, not session state), so the overlay is an interactive analytical adjustment
  on the live margin surfaces, documented as such.
- `_margin_panel` gains the key + confirmed set; `_analysis_body` threads `margin_confirmed`;
  `POST /margin/confirm` is async (reads the multi-value `uid` checkboxes off the form body).
- Tests: engine (`margin_candidates` primary/near-miss + context; overlay overrides names; empty set;
  `total_margin_wd`; `consumed_pct`/`corrective_action` at the 50% threshold; dashboard overlay) and
  web (panel glossary + dual numbers + confirm/reset/empty/unknown-uid; dashboard API carries the new
  fields; the confirmed overlay reflects through `/api/margin/dashboard`). Version 1.0.41 → 1.0.42;
  wheel + 9 installers rebuilt in lockstep.
