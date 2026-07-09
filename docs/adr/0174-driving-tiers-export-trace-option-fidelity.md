# ADR-0174 — Driving-tiers Excel export honours the page trace options (export == screen)

## Status

Accepted. Fixes a HIGH finding from the ADR-0168..0172 adversarial self-review (2026-07-09): the
Driving-Path tiers Excel export computed tier membership + slack on a **different network** than the
on-screen panel when the page's trace options were active.

## Context

`/driving-path` offers **Ignore constraints** / **Ignore leveling delay** toggles that re-solve
every version on a pure-logic network (`_optioned_versions`). `_driving_tiers_panel` receives those
re-solved schedules, so the on-screen "All driving-tier activities" table embeds tier + slack from
the **optioned** network. But `export_driving_tiers` resolved the file label to the **stored**
schedule and computed `compute_driving_slack` against `analysis_for(...).cpm` (the default,
constraint-honoring CPM), and `driving_tiers.js` built the Excel URL with only `?target=&cols=`.

Result: with a constrained/leveled schedule (the exact case those options exist for) and the option
checked, the downloaded Excel had **different tier membership, different Slack(d) values, and a
different row set** than the table the analyst was viewing — a silent on-screen-vs-export divergence
in a fidelity-critical (Law 2) export. The sibling driving-**path** export already threaded the
options; the tiers export was a genuine omission.

## Decision

Thread the trace options through the tiers export so it runs on the **same** network the panel
shows:

1. `_driving_tiers_panel` takes `ignore_constraints` / `ignore_leveling` and embeds them in
   `#drivingTiersData`; `_driving_path_body` passes the active page flags.
2. `driving_tiers.js` appends `&ignore_constraints=&ignore_leveling=` to the export href.
3. `export_driving_tiers` accepts those params and, before computing driving slack, re-solves the
   schedule via `_optioned_versions` exactly as the panel does (no options → the stored network,
   untouched). Field columns still come from the stored `analysis.activity_rows`, matching the
   on-screen `/api/analysis` fields — so the **whole** exported table equals the on-screen table.

The **LOW** finding from the same review — deselecting a built-in column (Tier/UID/Activity/Slack)
on screen does not drop it from the Excel — is left **as-is by design**: every drill export in the
app (ribbon, findings-citation, what-if, driving-tiers) always emits its identifying columns so a
court exhibit stays self-identifying regardless of the on-screen view. Making driving-tiers alone
omit them would be inconsistent; this is documented rather than changed.

## Consequences

- Pinned by `test_driving_tiers_drill.py::test_driving_tiers_export_honours_trace_options_matching_the_panel`,
  which asserts per-UID tier+slack parity between the panel embed and the exported rows under
  `ignore_constraints=1`, plus a JS assertion that the href forwards the flags. Default (no options)
  path is unchanged (`_optioned_versions` returns the originals).
- `src/` changed (`app.py` + `driving_tiers.js`) → wheel + 9 installers rebuilt in the same commit
  (ADR-0148 lockstep). Law 2 upheld: the Excel a user hands to a court now matches the screen.
