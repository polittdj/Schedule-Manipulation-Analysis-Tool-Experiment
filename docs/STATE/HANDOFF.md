# Handoff — 2026-08-19 (a) (Chapter 04: an independent oracle + the ribbon cursor fix; ADR-0428; v1.0.217)

> ## STATUS (current) — the operator's "not working correctly" was real, and it was the control.
> Highest ADR **0428**. **SHIPPED code changed** (`web/static/volatility.js`) — **v1.0.216 →
> v1.0.217**, SCHEMA unchanged, wheel + nine installers rebuilt.
>
> ## What landed
> **1. An independent oracle for Chapter 04** (`tests/web/test_ch04_stability_oracle.py`, 14
> tests). Every prior guard for the stability band is STRUCTURAL — it compares the tool to itself
> and passes whether or not the arithmetic is right. The oracle pins critical membership with
> `stored_is_critical` and derives every expectation BY HAND: per-pair Jaccard, stayed/entered/left
> plus UIDs, tenure, longest streak, flips, per-version counts, row order, the headline percentage,
> the rendered page. FAIL-side cases assert known-bad schedules are REPORTED bad (rebuilt path →
> 0%, identical path → 100%, completed activity leaves the path, one version → em dash not 0,
> empty critical set → undefined not 0.0). Seven mutants, all red. **The arithmetic is correct.**
>
> **2. ADR-0428 — the ribbon borrowed a transition the cursor was not on.** `drawRibbon` used
> `Math.max(1, cursor)`, so cursor 0 and cursor 1 both rendered `PAIRS[0]`: the opening click of
> Next changed nothing, and the baseline printed "33 stayed / 1 left" for a transition into the
> first file, which never happened. The baseline now says so and prints no figures. **Pre-existing
> — `/volatility` behaved identically** (shared module); ADR-0427 surfaced it, did not cause it.
> Both routes are asserted.
>
> ## Three things worth carrying forward
> - **Structural tests and correctness tests are different.** Ask of any suite: *what wrong number
>   would still make this green?*
> - **A symmetric fixture cannot detect an asymmetric bug.** The entered/left swap mutant SURVIVED
>   because every pair in the fixture had `entered == left`. Added a lopsided pair.
> - **Correct data + wrong control is a real shape.** The dataset was always right; the defect was
>   which correct pair a control chose to show. No data-level test can see that — only walking the
>   control in a browser, which is easiest to skip when the numbers all check out.
>
> ## Carried forward
> Design gaps open: **Metric Lab** (lowest effort) · Segment Forecast as a page · Portfolio at
> Scale · Beyond the Schedule · Trend Lab + Manipulation Watch · PDF export · GUIDE ME · SHOW UIDs
> · the MERLIN wordmark (operator decision). Audit rows unchanged. ADR-0353..0428 closed.
>
> ## Gate at close
> See SESSION-LOG.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
