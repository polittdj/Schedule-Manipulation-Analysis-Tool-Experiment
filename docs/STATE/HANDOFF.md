# Handoff — 2026-07-29 (a guard that one code path can walk around; ADR-0308; v1.0.124)

> ## STATUS (current) — **ADR-0307 MERGED as #481 (`08c5383`); the ADR-0308 follow-up is in flight.** An outside reviewer (Codex) raised three defects against #481 **after** it merged; all three were re-verified BY EXECUTION and all three were real. Version **1.0.124**, wheel + nine installers regenerated. Highest ADR **ADR-0308**. Evidence: `audit/SRA-PARITY-20260729.md`. Redesign tail rank 12 (`/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`, `/wbs/{name}`) is **still next** — two out-of-band Law-2 rounds in a row, the UI queue is untouched.
>
> ### What ADR-0307 shipped (merged, #481)
> The operator's SRA gave materially different answers in POLARIS vs the SSI SRA add-in for MS
> Project. The reference `.mpp` carries SSI's **own stored Best/Worst Case durations on 919
> activities**, so it was settled by measurement. Two defects fixed: the **Best Case formula was
> inverted** (the table's first column is a % **OF** the ML, not a % to subtract — corrected rule
> 897/919 = 97.6% by an ML-independent WC/BC ratio test, old rule 153/919, *every* one factor 1, the
> degenerate band where `1 − 0.50 == 0.50`), and **duration uncertainty was applied to completed
> work** (1722 activities randomised where MSP randomised 919; one finished 635-day activity alone
> shifted the mean +84.67 wd).
>
> ### What ADR-0308 fixes — one theme: **the 0307 guard could be walked around**
> 1. **The register walked around it.** The point-mass guard did not stop the risk loop adding each
>    fired impact to completed uids. Executed: a 50%/20-day risk on a 100%-complete driver gave
>    `std_days=9.99` and moved **P90 by 20 working days on finished work**. Now skipped in
>    `compute_sra_ssi` AND `compute_jcl`, and **disclosed** — `SSIRiskStat.applied=False` renders as
>    `inert (activity complete)` in a new Status column, because a risk that fires but moves nothing
>    is exactly the V2 pathology. The hit count still shows; only the delta reads `—`.
> 2. **Saved setups walked around it.** `_ssi_three_point` prefers a stored range over
>    `factor_to_bc_wc`, and `_apply_ssi_setup` restored `bcwc_minutes` with no version check — so any
>    pre-0307 setup **re-ran the inverted formula forever**. Not hypothetical: the committed
>    `00_REFERENCE_INTAKE/references/sra-ssi-setup.json` (`setup_version: 1`) holds **783** such
>    pairs (UID 427, factor 5, BC 432 on ML 480 = the old 0.900×ML). `_SSI_SETUP_VERSION` → **3**; a
>    pre-v3 load **recomputes** BC/WC for any uid carrying a factor, keeps factor-less entries.
>    **Operator-accepted cost:** a hand-typed override on a factor-bearing activity in an old setup
>    is replaced (stored entries do not record manual-vs-derived, so they cannot be told apart).
> 3. **The grid displayed what the run ignored.** Auto-calc only *skipped* recalculation, leaving a
>    stale range that `_ssi_grid_rows` and the setup export still showed. Now removed at the source;
>    the grid suppresses BC/WC for completed rows and `POST /sra/grid` refuses both derived and
>    hand-typed ranges there. **The factor is still recorded** — only the range is refused.
>
> ### Law 2 status
> **`pytest -m parity` green — 44 passed, no golden moved.** ruff · ruff format (793 files) ·
> mypy --strict · bandit (exit 0) · node --check all clean.
>
> ### ⚠️ NEXT — the SRA parity conclusion is UNCHANGED by ADR-0308
> Mean offsets from the deterministic finish (calendar days): as-shipped **+280** → completed-work
> fix only **+132** → both **+27**, against MS Project's **+111.45**. **No configuration reproduces
> MSP's spread** (σ 160.8 / 111.6 / 125.9 vs **64.74**). The deterministic percentile moved P3 →
> **P40**: 40% of POLARIS iterations finish before the deterministic date against MSP's **5.65%**.
> Same Best/Worst values, 7× difference — **the two tools are not simulating the same network. The
> residual is about VARIANCE, not the mean.**
> - **DO NOT "fix" this by reverting the BC rule.** Fixing only the completed-work defect lands the
>   mean nearer the target (+132) than the correct +27 — and its σ misses just as badly. Letting one
>   error cancel another is what Law 2 forbids.
> - **ASK THE OPERATOR FOR ONE ARTIFACT:** re-run the same SRA in MS Project with *Includes
>   Risks/Opportunities = **No***, all else identical. σ near **33 cal** ⇒ MSP varies a much smaller
>   set (most plausibly holding the status date 2025-03-10); near **99** ⇒ the difference is in how
>   the register combines with duration uncertainty.
>
> ### FINDING 3 (carried, CC-01 category) — the leading explanation for the residual
> Verified by execution: POLARIS's raw `compute_cpm` puts UID 152 at **2025-06-30**; the page shows
> 2029-04-19 only because `_build_ssi_result` re-anchors onto the stored finish (~1388 days; ~1924
> against the all-ML basis it actually uses). **The ADR-0106 "all-ML reproduces `compute_cpm`"
> equivalence is FALSE on this file** — the all-ML basis is **370 working days shorter**, because
> `_ml_minutes` feeds 92 in-progress tasks their *remaining* rather than full duration. **The
> simulation solves a compressed network that is not the schedule the rest of the tool displays.**
> Deliberate and long-standing (ADR-0106/0123), load-bearing for every progressed schedule — own round.
>
> ### Hypotheses KILLED — do not re-chase (`audit/SRA-PARITY-20260729.md` §7)
> impact days as calendar rather than working days (the file stores `PT800H0M0S` = 100 × 480 min) ·
> `std_cal_days` as a 7/5 fudge (a real `pstdev` over calendar ordinals) · `mean_delta_days`
> overstating (independent Bernoulli ⇒ unbiased; SE ≈ 8.5 wd) · float absorption (both risk
> milestones have **TF = 0**) · **audit finding V2 as the cause of the screenshot** (V2 is the legacy
> multiplicative `/sra` page; the screenshot is the additive `/sra/ssi` page — V2 is still real, just
> not this).
>
> ### Still carried from ADR-0306
> **CC-01 (HIGH)** `offset_to_datetime` returns non-working dates (`cpm.py:255-281`, 74 call sites) ·
> **CC-05** negative sub-day slack floors (needs an SSI reference compare) · **V3** elapsed literals
> `"2 ed" == "2 d"` (product decision) · **V1/V2** SRA magnitude entry needs an operator-visible
> error surface (five standing UI requirements apply).
>
> ### Harness notes worth keeping
> - **Run dev tools as `python -m <tool>`, never bare** — a stale `/root/.local/bin/ruff` (0.15.8)
>   shadows the pip-installed 0.16.0 CI resolves. A local-vs-CI FILE COUNT mismatch is the tell (793).
> - `[tool.ruff.format] exclude = ["audit/*.md"]` is deliberate — never let a formatter rewrite
>   quoted evidence.
> - No runtime deps in this container: `pip install -e ".[dev]"`; `python -m build` needs installing.
>   `httpx` is dev-only and must never enter runtime `dependencies`.
> - Full `pytest -q` ≈ 12m under load; `pytest -m parity` ≈ 35s — run parity first.
> - **Converting the reference `.mpp` costs ~30 s** (21.8 MB MSPDI); `parse_mspdi` ~4 s; **2000 SRA
>   iterations ≈ 90 s**. Reproducing an operator run end-to-end is cheap — do it rather than
>   reasoning about the algorithm.
> - **Run a Monte-Carlo bisection against an UNPATCHED tree** and record run provenance beside every
>   number: a mid-run edit does not affect an already-imported module, but the NEXT run picks it up —
>   two variants that should have differed came back byte-identical because a new guard had already
>   neutralised the input.
> - **An outside review can be right.** Codex's three findings against #481 all reproduced, including
>   one citing a committed fixture by exact value (UID 427, BC 432 on ML 480). Verify by execution —
>   then act on what survives, rather than dismissing the source.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
