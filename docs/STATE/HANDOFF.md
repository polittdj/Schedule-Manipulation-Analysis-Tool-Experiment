# Handoff — 2026-07-18g (ADR-0269: JCL / FICSM joint cost-&-schedule confidence — the #331 phase opened on operator direction; v1.0.74; highest ADR 0269)

> ## STATUS (current) — the operator said "continue" and picked #331 item 1 (top-ranked gap), so the Advanced-Schedule-Analysis phase is OPEN: built the JCL / FICSM joint cost-&-schedule confidence feature end-to-end (ADR-0269) and live-verified it in Chromium. Version 1.0.73 → 1.0.74 (wheel + 9 installers in lockstep).
>
> - **Engine:** new parity-isolated `engine/jcl.py` — `compute_jcl` replicates the SSI MC's
>   draw discipline EXACTLY (seed+i, ascending-uid draws, point-mass/copula/risk rules, the
>   one trusted `compute_cpm` chokepoint, stored-finish realignment), so the joint sample's
>   finish marginal is byte-identical to `compute_sra_ssi` — pinned by full-CDF equality
>   across triangular/PERT × correlation 0/0.3 × focus/project. Cost rides the SAME sampled
>   durations (NASA CEH App. J / Hulett): EAC_i = completed finals + Σ(spent +
>   (TI + TD·d_i/d_ML)·m_i); τ=td_share (default 1.0, labeled screening), FICSM cost
>   multipliers default 1/1/1=OFF and draw AFTER all duration draws (stream-stability
>   test-pinned). Outputs: JCL=P(both) + SCL/CCL marginals (JCL≤min pinned + Fréchet lower
>   bound), quadrants (sum-1 pinned), P-grid iso-confidence frontier (achieves-confidence +
>   monotone pinned), cost CDF/percentiles, deterministic EAC = AC+(BAC−EV) exactly.
>   NOT cost-loaded (the EVM Σbudgeted_cost>0 gate) → raises — never a fabricated figure;
>   an SCL can no longer be mislabeled JCL (ADR-0106's reservation, structurally enforced).
> - **Web:** gated JCL panel on /sra after the SSI panel — POST /sra/jcl-config
>   (targets/τ/multipliers/confidence, clamped+order-coerced, reset), lazy GET /api/sra/jcl
>   (offload-aware; honest 422 when uncosted; 400 when empty), vendored `sra_jcl.js`
>   (football scatter with quadrant %s + target crosshair + frontier polyline + det marker,
>   EAC S-curve, FICSM SCL/CCL/JCL strip, quadrant table, provenance line) — CSP-strict-safe
>   (external file, addEventListener only, chartframe callouts/zoom). /export/xlsx/sra gains
>   3 JCL sheets when costed (headline+provenance / frontier / joint sample). Explainers
>   flipped to the live panel (SRA JCL "Status here", both SCL disclaimers, EVM's "How EVM
>   relates to a JCL") with the pinned honesty language kept verbatim. help.py glossary
>   +eac/scl/ccl/jcl (dictionary regenerated — no delta; glossary keys aren't engine
>   metrics); i18n catalog +9 JCL terms in ES/FR/DE/PT.
> - **Verified:** tests/engine/test_jcl.py (19 — incl. a hand-REPLAYED single-iteration draw
>   + hand-summed EAC fixtures 1175/1405/510) and tests/web/test_jcl_web.py (9 — gate,
>   422/400, config persist/bad-date/reset, web-layer SSI coherence, export gains sheets
>   ONLY when costed); full gate green. LIVE Chromium under the strict CSP: panel renders,
>   a real POST form navigation applies through the SEC-2 Fetch-Metadata gate, Run JCL
>   renders football + cost curve + FICSM strip, ZERO console errors — and the sweep caught
>   a real bug the DOM asserts missed (football x-axis end labels used iteration-order
>   first/last instead of the axis bounds) — fixed and re-verified. Parity untouched.
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261
>   on-machine re-validation; five-large-file stress); Claude-Design prompt (Portfolio
>   US-map/site drill, ADR-0258). #13 XER per-task calendars PARKED.
> - **State:** v1.0.74; **ADR-0269** highest; wheel + 9 installers in lockstep. **PR #406
>   MERGED** (squash `ad10868`, CI fully green: both test matrices + Windows/Linux installer
>   smokes); branch `claude/handoff-continuation-vistlu` restarted from the squash, clean
>   tree, NO open PR, nothing in flight. Earlier this session: #405 (verification-session
>   log) MERGED; the desktop-update PowerShell command was provided (git pull + re-run the
>   same-tier installer — it force-reinstalls the embedded wheel).
> - **NEXT:** the #331 phase is OPEN with item 1 (JCL/FICSM) SHIPPED. Ranked next per the
>   issue + its Hulett-deck comment: #2 risk-driver correlation matrix + eigenvalue
>   feasibility, then auditing the existing Assessment Scorecards against the STAT/GAO gap
>   lists — but CONFIRM with the operator before starting the next item. A golden
>   COST-LOADED fixture (budgeted MSPDI) would strengthen JCL evidence beyond synthetic
>   nets. The three OWED operator inputs above still block ADR-0261/0258 work.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
