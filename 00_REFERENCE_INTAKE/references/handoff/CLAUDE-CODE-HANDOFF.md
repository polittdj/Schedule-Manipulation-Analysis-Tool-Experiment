# CLAUDE-CODE-HANDOFF — replicate the ASTROLABE UI
(self-contained; give this file + the design_handoff_mission_ops_redesign/ folder to Claude Code)

## What you are building
Re-skin/extend the POLARIS web UI in polittdj/Schedule-Manipulation-Analysis-Tool-Experiment
(src/schedule_forensics/web/: app.py routes + static/*.js modules) to match the interactive
prototype design_handoff_mission_ops_redesign/ASTROLABE.dc.html. Presentation only — never touch
engine/ or any calculation; every number on screen reads from the engine payload; a missing value
renders "—", never a fabricated figure. Parity and payload-shape tests must stay green.

## The two laws (from the repo, unchanged)
1. Data sovereignty: 127.0.0.1 only, no remote asset (air-gap test), CUI bars on every page/export.
2. Fidelity: numbers match Acumen Fuse v8.11.0 / SSI; pytest -m parity is gate-locked.

## Design rules (binding)
- Tokens only (base.css custom properties); a hex in page markup is a build failure. Rename the
  repo's --nasa-red token to --alarm-red (same value) as part of the scrub below.
- Every visual is an instrument: takeaway headline (a sentence with the number in it), red
  data-date line, legend, how-to-read line, provenance chip (SOURCE: file · DD date), and the
  ▦ DATA / ⤓ EXCEL / ⛶ ENLARGE toolbar. Axis titles on X and Y everywhere (close the
  test_axis_titles.py PENDING ledger).
- Type: Space Grotesk (display) / IBM Plex Sans (UI) / IBM Plex Mono (data), vendored locally
  (air-gap); tabular numerals; 11px floor for labels (10.5px mono minimum in dense charts).
- Word scrub, all user-facing strings: never NASA (→ "agency", "Gold-Rule", "STAT" as context
  requires), never "Microsoft Project"/"MS Project" (→ "MPP" for the format, "planner-style" for
  the idiom), never "Primavera"/"Oracle" (→ "P6"/"XER"). File-format tokens .mpp/.xer/P6/XER stay.

## Screens to replicate (prototype → repo route)
The full map lives in the project's github.md "Screen map" table; headlines:
- Boot lightshow (new /): ONE 5,200-particle canvas pool, three scenes that MORPH (particles fly
  from scene to scene, ~2s ease): (0) full-height DNA double helix, electric blue, white-hot
  knots at strand crossings, dotted rungs, glow column, two glass stat cards fed by real payload
  numbers; (1) 50-row × 104-col signal-wave terrain, cyan→ember, halo crests, spark motes;
  (2) three-arm spiral galaxy, exponential soft-fade core (no hard border), ~14% of particles in
  9 clusters, ember outer tips, differential rotation. Starfield behind all; scene dots; copy
  crossfades per scene; BEGIN warps (streaks + expansion) into the boot checks; synthesized
  WebAudio boot audio (HUM swell / PULSE chirps / SONAR pings / OFF — no sampled media);
  prefers-reduced-motion renders a static frame; voices reduced to Female / Male.
- 12-chapter Mission Ops story + COMPARE stations: Compare Bay (7 instruments over any file
  pair), Path Explorer (target UID × P1/P2/P3 × GHOST/SPLIT/DELTA/CORRIDOR overlays), Path Drift
  (all files chronologically: step Gantt with auto-cycle PLAY/rate/loop, residency matrix, churn,
  net-vs-gross drift, stability verdict), Metric Trends (24 metrics × every file, least-squares
  slope/R²/volatility/threshold-breach/forecast, tile click-through), Field Metrics (group every
  metric by any standard or UDF field; WBS-source override with visible banner).
- Cross-cutting: export preview before every Excel/PDF export (grid preview, standard + UDF
  field picker joined by UniqueID, honest totals: row TOTAL only when additive, MEAN footer for
  rates/shares/indices, TOTAL only for per-period flows); data-point inspector on every bar/line/
  scatter point (series at that x, shares when additive, move vs previous on sequenced axes,
  citation, export); reference lines/markers always painted ABOVE series with label plates;
  per-Gantt timescale zoom ⊖/⊕ with pan ◀/▶ re-graining the header down to individual days;
  Gantt logic links from the real relationship table (DRIVING → ALL → OFF), on-bar date toggles.

## Acceptance
- All 4 themes (console/daylight/apollo/jarvis) render every page; reduced-motion honored.
- Air-gap test green (no CDN, fonts vendored); CUI bars present incl. print.
- Banned-word grep returns zero hits in served HTML/JS strings.
- pytest -m parity + dashboard payload SHA tests untouched and green.

## Bundle contents
design_handoff_mission_ops_redesign/: ASTROLABE.dc.html (pixel truth, current),
Mission Ops Redesign v2.dc.html (previous gen), DESIGN-GUIDE.md, sf-themes.css, support.js
(prototype runtime), integration-notes.md, screenshots/. Project docs: docs/repo-audit.md
(repo findings), github.md (screen map + sync history).