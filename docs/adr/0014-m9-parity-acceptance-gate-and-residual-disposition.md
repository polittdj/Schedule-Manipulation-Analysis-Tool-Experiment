# ADR-0014: M9 parity acceptance gate + formal residual disposition

- **Status:** Accepted
- **Date:** 2026-06-08 (session A11 — Phase 2 build, milestone M9, continuous A7 sitting)
- **Relates to:** §6.B (parity = acceptance gate), §7 Q4 (CI), `BUILD-PLAN.md M9`, ADR-0005 (golden/deltas)
- **Builds on:** ADR-0010 (pure-logic CPM float), ADR-0012 (M7 residuals), ADR-0013 (M8 residuals)

## Context
M9 consolidates the scattered per-module golden assertions into the single **acceptance
gate** the build contract demands (§6.B: numbers must match Acumen Fuse v8.11.0 and SSI,
matched by UniqueID), wires it into CI, and formally dispositions every residual carried
from M7/M8 — "drive to zero, or document the precise delta with citations where an exact
match is genuinely impossible" (§6.B / AUTONOMOUS-BUILD-PROMPT §6.3).

## Decision
1. **`tests/parity/test_parity_gate.py`** is the authoritative §6.B artifact: one module,
   marked `@pytest.mark.parity`, re-asserting the full golden set over the committed
   non-CUI fixtures — Acumen §A Schedule Quality, §B DCMA-14, §C baseline compliance, §E
   change metrics + Net Finish Impact, and SSI driving slack (107/107). The `parity`
   marker is registered in `pyproject.toml` (`--strict-markers`) and CI runs it as a
   dedicated named step (`pytest -m parity`) so a parity break is visible independently of
   the unit suite. The per-module tests remain as unit/edge coverage.
2. **Residual reconciliation investigated, then formally accepted (not closed).** A probe
   tested whether MS Project's **stored progress-aware** values reproduce the residuals:
   stored `TotalSlack > 44d` yields High Float **44/40** (Acumen 44/41) — it fixes
   Project2 but not Project5 (MS Project omits `TotalSlack` for some rows); stored Critical
   transitions give SN04 = 2 and SN09 = 13 (Acumen 1 / 6). So **neither pure-logic CPM nor
   the stored MS Project fields reproduce the residuals exactly** — they are an artifact of
   MS Project's internal progress-aware scheduler, not recoverable from the static MSPDI.
   Per §6.B they are **formally accepted as documented deltas** (each ≤ a few activities;
   none flips a pass/fail), recorded in `case.json._deltas` + ADR-0012/0013 and **locked by
   the parity gate** (the gate asserts the engine value *and* that the golden delta is
   exactly the recorded magnitude, so silently regressing — or silently closing — a
   residual fails the gate and forces the golden assertion to be tightened):
   - High Float +1 (P2 43/44, P5 40/41); BSC % 38/23 vs 41/25; SN04 0 vs 1; SN06 9 vs 10;
     SN07 7 vs 8; SN09 4 vs 6; SN01 header 126 vs 144 (schedulable vs all task rows).
3. **Composite scores deferred with rationale (no fabrication — Law 2).** Acumen's SQ
   "Score" (88) and DCMA "Score" (57/49) use a proprietary Bad/Neutral/Good weighting
   (weights −10…+10, normalized 0–100) that is **not published** in the exports or the
   Acumen 8.11 metric guide (`METRICS-CATALOG §5`). Three target integers against ~10–14
   unknown per-metric weights is underdetermined; reproducing them would mean inventing
   weights and overfitting. The **per-check counts and pass/fail (the auditable facts) are
   exact**; the composite score is left explicitly deferred (`case.json._scores_deferred`)
   rather than fabricated. It can be revisited if the weighting is obtained out-of-band.
4. **Independence over imitation (reaffirmed).** The engine keeps computing pure-logic CPM
   float (ADR-0010) rather than consuming MS Project's stored slack/Critical, so every
   number is independently derived and auditable in a forensic/testimony context. The few
   progress-aware deltas are the accepted price of that independence and are fully cited.

## Consequences
- §6.B has a single, CI-enforced acceptance gate; RTM B2 → ✔ for the matchable set with
  the residual deltas explicitly tracked; Q4 parity step live in CI. R-02 (parity miss)
  and R-13 (§E semantics) move to Mitigated/Accepted.
- The gate is the regression backstop for every later milestone (M10 audit, M11 trends,
  M13/M14 UI) — visuals and narratives can only ever display gate-verified numbers.
- Future work that reconciles progress-aware float (if ever pursued) is pre-wired: closing
  a residual will fail the gate's "delta == recorded" assertion, prompting the golden
  tighten — exactly the "drive to zero" ratchet the build contract intends.
