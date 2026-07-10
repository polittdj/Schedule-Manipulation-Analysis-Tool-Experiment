# ADR-0184 — CP-volatility exhibits layer: one payload, static pack + interactive + headless CLI

## Status

Accepted. Operator 2026-07-10 ("SMAT MASTER PROMPT — Visualization Layer"), which supersedes
the presentation posture of the ADR-0178 volatility page (the ten visuals REMAIN; this adds
the exhibit layer around them and fixes two of them).

## Context

The master prompt's dependency clause governs scope: the CP-basis engine artifacts (driving
tree with edge sets, CIC, τ-b, null-model churn, recompute deltas, six-state assignment) do
NOT exist at HEAD (verified — `audit/VERIFICATION-REPORT.md`), so the payload models and
renderers are built and tested against hand-authored golden fixtures and the live wiring is
PARKED (`audit/PARK-LIST.md` P1–P4). No engine output is fabricated.

## Decisions

1. **`src/schedule_forensics/exhibits/`** — `payload.py` (pydantic v2 contract: RunManifest /
   TaskUpdateCell with the six-state enum / TaskSummary / UpdateSummary / Transition;
   extra="forbid", loud validation; canonical sort_keys serialization; deterministic
   `run_id_for` with no timestamps), `render_svg.py` (stdlib-string SVG, EX-00…EX-08, literal-
   hex PALETTE because standalone files have no CSS vars — grep-gated; provenance footer inside
   every figure; EX-01 glyph+fill per state with constraint-critical `<pattern>`-hatched for
   grayscale printers; EX-03 breaks at rebaseline boundaries and never connects across; EX-04
   renders CIC nulls as annotated gaps; zero render-time arithmetic beyond axis scaling),
   `csvout.py` (per-exhibit CSV siblings of the exact rendered rows), `report_html.py`
   (self-contained, zero-`<script>`, print-ready), `cli.py`.
2. **CLI `schedule-forensics-report`** (console script): renders the full pack headlessly;
   exit codes 0/2/3/4/5 (4 = engine artifacts missing — real `--inputs` runs exit 4 honestly
   until the CP-basis engine lands; `--payload` renders deterministically). Double-run
   byte-identical (tested). `docs/automated-reporting.md` carries the copy-paste PowerShell
   Task Scheduler registration (no browser, no server).
3. **Interactive fixes** (the engine-independent §5 items): the membership heatmap now sorts
   by INSTABILITY (on/off flips, tenure tiebreak) — the old top-by-tenure showed the most
   stable tasks, inverting the exhibit's purpose; the stability gauge renders "bands are
   operator-set display guidance — not a published threshold" on the chart face (no verified
   published numeric threshold exists). The six-state volData migration and the live EX-03/04/07
   exhibits are parked with the engine (P2).
4. **SSI ambiguity** (§2.4): the full vendor/metric rename exceeds the session budget in the
   ~600 KB app.py; executed the documented fallback — a gate test forbidding bare "SSI" in the
   new exhibits package + PARK-LIST P3 for the full rename.
5. **Audit trail**: `audit/SESSION-STATE.md`, `audit/VERIFICATION-REPORT.md` (every pre-flight
   claim with its command + output), `audit/PARK-LIST.md` (deposit path + unblocking
   verification per parked item).

## Consequences

- `tests/exhibits/` (17 tests): fixture completeness (all six states, CIC-null, rebaseline,
  nonzero + unavailable recompute deltas), loud-failure validation, structural render pins,
  air-gap grep over every emitted artifact, CLI exit-code matrix (subprocess + in-process),
  determinism, static≡interactive payload-byte parity. Coverage on `exhibits/`: 96.6% (≥90%).
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
