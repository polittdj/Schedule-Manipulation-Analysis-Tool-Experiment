# ADR-0113 — CUI marking on Excel/Word exports + AI-settings UX; Step-5 value-ES blocked on missing EVM3

Status: accepted (2026-06-22)

## Context

This session opened on build-order **Step 5 — value-based / per-activity Earned-Schedule SPI(t)**
(reframed by ADR-0110: Acumen's `SPI(t)` is a *per-activity duration-ratio average*, not count-vs-value
ES, which explains the EVM2 residual engine 0.27 vs Acumen 0.56). Per the operator's own gating
instruction, Step 5 may only proceed against the authoritative reference:
`00_REFERENCE_INTAKE/audit/.../EVM3- Detailed Metric Report.xlsx` (the per-activity SPI(t) export) —
"if absent, STOP and ask … do not fabricate."

**The EVM3 Detailed Metric Report is not present** anywhere in the intake or on the machine. The
upload accompanying this session instead contained an **SSI Analysis (UID_145) Directional Path
Analysis** bundle for the current `Project5_TAMPERED` / `Project2` pair (two `.mpp` versions + the
SSI `Driving Slack` / `Drag` / `Trace Log` workbooks and a `.docx`). That is a *different* missing
input — the SSI driving-slack backlog item (#6) — and it is for **focus UID 145**, whereas the
repo's xfail golden is `ssi_uid143`. So it does not trivially re-pin `ssi_uid143`, and it does not
unblock Step 5.

Reproducing Step 5 without EVM3 would mean inventing the per-activity reference numbers — a direct
violation of Law 2 (fidelity over speed) in a testimony context. Step 5 is therefore **paused,
input-blocked**, and this session pivots to unblocked, operator-requested UI/compliance work that
does not touch the parity surface.

A separate, large operator request list (chart time-scale tiers + scaling, hover call-outs,
totals/counts, multi-select on finishes, "show completed", Critical-Path-Evolution zoom, SRA
file-selection, Exec-Summary/S-Curve scaling under many files, Driving-Path three-column
critical/secondary/tertiary storytelling + driving-slack-degradation trend, Acumen-style Executive
Briefing, page-wide text-size/zoom) is **not** in this ADR — those are multi-PR efforts tracked in
HANDOFF for sequencing; this ADR records only what shipped here.

## Decision

Ship a focused, parity-isolated slice (no engine/metric numbers touched):

1. **CUI marking on every Excel and Word export (Law 1).** Forensic exports are testimony
   artifacts and must carry their handling caveat on every page.
   - `reports/xlsx.py`: a `headerFooter` part stamps `CONTROLLED UNCLASSIFIED INFORMATION (CUI)`
     centered in the print header **and** footer of **every worksheet**. It sits after
     `<sheetData>` (where the OOXML schema expects it), so the cell grid — and the tests that read
     it — are untouched.
   - `reports/docx.py`: a `word/header1.xml` + `word/footer1.xml` part (with content-type overrides
     and a `word/_rels/document.xml.rels`) referenced from `<w:sectPr>`, so the CUI banner repeats on
     **every page** of **every** Word export — including the narrative Diagnostic Brief, which flows
     through the same `render_document` chokepoint. Banner lives in separate parts (not body
     paragraphs) so the document body and its tests are unchanged.
   - Both writers stay **byte-deterministic** (static marking strings; fixed part order).

2. **AI-settings UX (operator orders).**
   - **Generation-timeout default 300 → 900 s** (`AIConfig.gen_timeout` and the `/settings` form),
     so a big, slow local model finishes a full answer out of the box. The 30 s…3600 s clamp is
     unchanged.
   - **Cross-check second-model id auto-populates.** Turning the cross-check on copies the primary
     model id into the (empty) second-model box via a small vendored, loopback-only
     `static/settings.js` (it never clobbers a value the operator already typed; edit it to a genuine
     second model such as `qwen2.5:14b`). The fields gained stable ids (`primaryModel`,
     `secondBackend`, `secondModel`).
   - **In-app local-model setup guide.** A `<details>` on the AI-settings page gives step-by-step
     `ollama pull` instructions for `llama3.1:8b` and the memory-tiered alternatives, plus a pointer
     to the deepened `docs/CONNECT-A-BIGGER-AI-MODEL.md` (which also gained a cross-check second-model
     walk-through and a generation-timeout note).

## Consequences

- Every `.xlsx` / `.docx` the tool emits is now CUI-marked top and bottom on every page; the
  marking is verified by `tests/reports/test_exports.py` and the export determinism tests still pass.
- The AI experience matches the operator's asks (900 s default, one-click cross-check, discoverable
  setup) with no change to any computed figure, citation, or parity gate — `route_backend` and the
  citation/figure gates are untouched.
- **Step 5 remains open and input-blocked.** To resume it, the operator must re-attach the
  **`EVM3- Detailed Metric Report.xlsx`** (per-activity SPI(t)) into the git-ignored intake.
- The newly-arrived **SSI UID_145** export is now on disk (git-ignored). It is a candidate to advance
  the SSI parity backlog (#6) but, being focus UID 145 vs the golden's UID 143, needs its own
  validation pass — it does not auto-lift the `ssi_uid143` xfail.
