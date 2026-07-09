# ADR-0169 — Driving-Path tiers: add-columns / filter / Excel + bold file banner

## Status

Accepted. Closes backlog #72. Operator 2026-07-08: on the Driving-Path page, the driving-tier
activities must be viewable in one organized chart the user can add any standard/custom column to
(set once), filter by any field, and export to Excel — plus a bold banner naming the file the path
was computed on (the driving path can differ between files; the per-file selector shipped in
ADR-0165).

## Decisions

1. **Bold file banner (`_driving_tiers_panel`).** When a target is traced, the tiers panel leads
   with a bold `Driving path computed on <file>` banner (`.dp-file-banner`, accent left-rule) so
   the operator always sees which loaded version the path/tiers belong to.
2. **Interactive tiers chart (`static/driving_tiers.js`).** Below the three at-a-glance tier
   buckets, one table lists **every** driving-tier activity with a **Tier** and **Slack (d)**
   column, defaulting to UID / Task name as well. It carries the same drill affordances as the
   ribbon / finding-citation tables: a **Columns** dropdown (standard + custom fields,
   localStorage-persisted under `sf-driving-tiers-cols`), a **Filter** box (text across every
   shown column), and an **Excel** export of exactly the chosen columns. Tier + slack are embedded
   server-side (from the same driving-slack pass the buckets use); the field columns come from the
   same-origin `/api/analysis/<file>` endpoint (resolved by `_find_schedule` — key or label).
3. **Export route (`/export/{fmt}/driving-tiers/{name}?target=&cols=`).** Recomputes the tiers on
   the file's stored network and emits Tier / UID / Activity / Slack (d) + any requested extra
   columns, ordered driving → secondary → tertiary then by slack then UID (matching the buckets).
   Unknown file or an absent target → 404; an unsolvable file → 422 (never 500).

## Consequences

- Live-verified in Chromium (Hard_File pair, target 155): the bold banner names the traced file;
  the tiers chart renders all driving-tier activities (85 rows), filters (18 on "COMPLETE"), adds
  persisted columns, and links a 200 xlsx; zero console errors. Pinned by
  `tests/web/test_driving_tiers_drill.py` (3 cases) — banner + embed, export route (incl. 404/422
  guards), JS mechanics.
- Law 1 untouched (tier/slack embedded server-side, field data from same-origin `/api/analysis`);
  Law 2 upheld (the figures are the engine's driving-slack values; the chart only lists the
  activities behind them). `src/` changed (app.py + `driving_tiers.js` + `app.css`) → wheel + 9
  installers rebuilt in the same commit (ADR-0148 lockstep).
- Remaining from the same work order (separate features): Quality-Trend visual split (#71),
  Resources day/week/month bucketing + overallocation drill (#74), SRA editable-grid Gantt (#80).
