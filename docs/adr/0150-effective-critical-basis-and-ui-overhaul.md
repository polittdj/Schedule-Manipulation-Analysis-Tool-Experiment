# ADR-0150 — Effective-critical path basis + operator UI/forensics overhaul

## Status

Accepted.

## Context

The operator ran the tool against real progressed schedules (delivered to
`00_REFERENCE_INTAKE/mpp/`) and filed a 17-item work order. The headline defect: **Critical-Path
Evolution showed 2 activities where 76 incomplete tasks sat at 0 days driving slack.** Root cause:
the evolution (and the briefing, diagnostic brief, counterfactual, and the activity grid's Critical
column) used the **pure-logic CPM critical set** (`cpm.critical_path`), which ignores progress/data
date (the ADR-0108 gap) and collapses to the schedule tail on a progressed file. The repo already
had the correct instrument — `metrics/_common.is_effective_critical`, the stored, progress-aware
Critical flag Acumen/DCMA metrics score on (ADR-0010/0080) — the path displays just never used it.
Separately, SRA Monte-Carlo runs failed outright ("cannot pickle 'mappingproxy' object"), and the
Ask-the-AI could not answer manipulation questions ("what was shortened to keep UID 152 from
slipping?") because the fact base carried no cross-version forensics.

## Decisions

1. **Path displays use the progress-aware effective basis.** New
   `path_evolution.effective_critical_set()` (incomplete + active + non-summary + stored-flag-first)
   feeds: critical-path evolution, the executive briefing's §3, the diagnostic brief's at-risk-path
   count, the path counterfactual's "left the path" set, and the activity grid/scatter `is_critical`.
   **Two-way verification:** goldens — effective = 41 (P2) / 4 (P5) = exactly the Acumen-validated
   stored counts (case.json; pure CPM gave 43); operator's `Large_Test_File.mpp` — pure CPM = **2**
   (the reported symptom), effective = 33 (= MS Project's Critical column), and the driving path to
   UID 152 = **76** incomplete 0-slack activities (= the operator's number).
   **Parity-pinned metrics are untouched** (float bands stay raw-CPM per D20/ADR-0141; DCMA CPLI
   unchanged; gate green).
2. **Targeted evolution = the driving path.** `compute_path_evolution(..., target_uid=)`: with a
   focused UID each version's path is the 0-driving-slack chain to it (the /path basis — 76 on the
   operator's file); untargeted it is the effective critical set. The page states the basis.
3. **Completed-on-path record.** Each snapshot carries `completed_on_path` (prior-path activities
   complete in the newer version); the evolution page renders the version-to-version "what got done
   on the path" table the operator asked for.
4. **SRA pickle fix.** `Schedule.__getstate__` drops the primed `tasks_by_id`/`resources_by_id`
   `MappingProxyType` caches from the pickle payload (they rebuild in the offload worker). Regression
   test + verified on the operator's 9.7 MB file.
5. **Manipulation forensics reach the AI.** `qa.manipulation_forensics_facts()`: per-activity
   duration cuts on the driving/critical path (quantified from→to), the reverted-changes
   counterfactual finish (naming each changed activity), and the focus's baseline variance — wired
   into both ask endpoints, cited, deterministic.
6. **Gantt overhaul (client).** One table-based `gantt-grid` pattern everywhere (the driving-path
   trace rewritten from flex divs), sticky headers, measured fit-to-full-width (hard-coded 360/520/
   320px margins replaced by the real frozen-column width), dates-on-bars fixed (now also on the
   trace; edge labels clamped), MS-Project checklist filters on all columns of all grids, and the
   filter popup no longer closes when scrolling its own option list.
7. **Dates.** Displayed dates are `MM/DD/YYYY`, no time-of-day: shared `SFGantt.fmtMDY` client-side
   and `_mdY()` server-side. **Deliberate carve-out:** AI-layer narrative/brief/fact text keeps ISO
   dates internally — the figure-integrity gate tokenizes ISO dates atomically (ADR-0138); breaking
   them into `MM`/`DD`/`YYYY` pseudo-figures would weaken the anti-hallucination checks. Data/JSON
   payloads stay ISO; formatting is presentation-boundary only.
8. **Presentation honesty items.** Provenance (`_sources_line` + per-frame file labels) on every
   multi-file page/visual; every "(+N more)" truncation now expands in place (`_expandable_more`,
   native `<details>`); the analysis charts carry a color legend; the margin card reads "N margin
   activities found; 0 on the critical path" (the `&middot;` double-escape fixed); the scatter panel
   gained an engine-computed written analysis naming the pressure points; float erosion accepts any
   grouping field (custom outline codes) via `compute_float_erosion(wbs_field=)`; the task drilldown
   shows populated fields only, humanizes `PT#H` durations, and folds custom fields into a
   collapsible group; briefing tables are contained (`min-width:0` + overflow) with a tighter global
   density.
9. **Trends/overlay visuals animate per file** (Mission-Control pattern: enlarge/minimize,
   Prev/Play/Next, frame label naming the current file) instead of overlaying every file on one
   chart.

## Consequences

- The parity gate and all recorded goldens hold; the §E engine-pinned rows are unmoved.
- Tests re-pinned to the effective basis (41/4; entered UID 131 unchanged) and to MM/DD/YYYY at
  render boundaries; new tests cover the pickle round-trip, the forensics facts, the targeted
  evolution, and the gantt/filters/date-format client behaviors.
- The pure-logic CPM remains the forensic recompute (ADR-0010) — it is simply no longer presented
  as "the critical path" on progressed files.
