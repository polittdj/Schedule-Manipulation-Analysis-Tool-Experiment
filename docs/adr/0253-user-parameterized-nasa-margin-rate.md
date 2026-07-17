# ADR-0253 — user-parameterized NASA margin requirement rate (F3c)

## Status

Accepted. Feature **3c** of the SMAT v4 build (grouped ingestion → scale/RAM → NASA margin F3a/3b →
roles → **parameterized margin**), completing the F3 margin feature. No parity impact — margin stays
off the Fuse ribbon / metric dictionary (like `health_extra`).

## Context

F3a/3b (ADR-0230) delivered the NASA margin terminology, the confirmed-margin overlay, dual numbers,
and the 50%-consumed corrective flag. The margin dashboard measures effective margin against the
**NASA Gold-Rule requirement** — `days-to-go × 30/365` (30 margin work-days per program year). That
rate lived as a module constant (`_GOLD_RULE_DAYS_PER_YEAR = 30.0`), and the engine already accepted
a `gold_rule_per_year` parameter on `compute_margin_dashboard` (its docstring even called it a
"Configurable rate") — but **no caller could set it**: every dashboard render and export used 30.

The NASA Schedule Management Handbook establishes margin as a program-**managed** guideline (30/yr is
the default, not a fixed law), so a program may legitimately plan to a different rate. F3c exposes the
rate to the operator; the engine math was already parameterized, so this is purely session/UI/export
wiring.

## Decision

- **Public engine default.** `_GOLD_RULE_DAYS_PER_YEAR` → `GOLD_RULE_DAYS_PER_YEAR` (public), so the
  web layer's default references one source of truth. The threading
  (`compute_margin_dashboard` → `_margin_month` → `nasa_rqmt_wd = days_to_go × rate / 365`) is
  unchanged.
- **Session state.** `SessionState.margin_rate: float = GOLD_RULE_DAYS_PER_YEAR`, set by
  `set_margin_rate` — accepted only in the sane band `(0, 365]`, otherwise ignored (fail-soft: a bad
  query value never wipes the setting). No cache invalidation — the rate feeds only the
  freshly-computed requirement line/trigger, not the analysis or summary caches.
- **Operator control.** `GET /margin?rate=` applies it; `_margin_rate_control` renders a cited GET
  form on the dashboard (number input + Apply + a "Reset to 30" link when off-default), stating the
  requirement is `days-to-go × rate ÷ 365` and 30/yr is the handbook "Gold Rule" default.
  `_margin_dashboard_for` threads `st.margin_rate` into the engine.
- **Carried provenance.** `MarginDashboard.gold_rule_per_year` records the rate used; the
  `/api/margin/dashboard` JSON and the Excel/Word export both state it, so a reader always knows the
  requirement basis a figure was measured against.
- The verbatim **50%-consumed corrective-action threshold stays fixed** (a cited NASA rule,
  §7.3.3.1.6 / §7.3.4 — not a program guideline); only the requirement *rate* is parameterized.

## Consequences

- **Behaviour-preserving default.** `compute_margin_dashboard` with no rate argument (or 30)
  reproduces the 30/yr requirement exactly (pinned test). No parity target moves.
- The requirement line, the per-version "NASA rqmt" column, the trigger flag, the burn-down chart's
  requirement line, and the export all follow one session rate consistently.
- Tests: engine (`test_gold_rule_rate_scales_the_requirement_and_is_carried`,
  `test_default_rate_reproduces_the_30_per_year_requirement_exactly`) + web
  (`test_margin_rate_control_renders_with_the_current_rate`,
  `test_setting_the_rate_changes_the_requirement_and_persists`,
  `test_invalid_margin_rate_is_failsoft`, `test_export_states_the_nasa_requirement_rate`). 4-theme
  Chromium check green (console/daylight/apollo/jarvis).
- Scope: only the requirement **rate** is parameterized — the one program-defined guideline in the
  dashboard. A per-phase margin table or other NASA guidelines would be separate future work.
