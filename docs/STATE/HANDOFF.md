# Handoff — 2026-07-29 (a ranking factor that does not change the uncertainty; ADR-0307; v1.0.123)

> ## STATUS (current) — **SRA parity round in flight.** The operator-reported SRA divergence is root-caused with executable evidence and **two proven defects are fixed**, but **parity is NOT achieved and this round does not claim it**. Version **1.0.123**, wheel + nine installers regenerated. Highest ADR **ADR-0307**. Evidence: `audit/SRA-PARITY-20260729.md`. Redesign tail rank 12 (the Library/Setup sweep — `/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`, `/wbs/{name}`) is **still next** — this was an out-of-band Law-2 fidelity round, not a UI round.
>
> ### What happened
> The operator ran the same SRA in POLARIS and in the SSI SRA add-in for MS Project on
> `SRA Large Test File2.mpp` and got materially different answers. Both tools *report* the same
> deterministic finish (2029-04-19) — but see FINDING 3 below, that is an **identity forced by an
> anchor realignment, not an agreement** — and the divergence **widens monotonically with percentile**
> (+49/+150/+261/+319 d at P10/P50/P80/P90).
>
> **The input file turned out to carry SSI's OWN stored Best/Worst Case durations on 919 activities**,
> plus its whole SRA register in custom fields — so this was settled by measurement against the
> reference tool's stored values, not by argument.
>
> ### Two prerequisites, both load-bearing
> - **The reproduction is faithful.** Driving the shipped `compute_sra_ssi` with the operator's setup
>   reproduces the screenshot on *every* figure (P10/P50/P80/P90, mean, σ 110.9 wd / 160.8 cal, hits
>   1812/1208, deltas 107.2/48.1, det P3). Every conclusion rests on a proven code path.
> - **MS Project's own summary cells are DEFECTIVE — do not use them as the target.** B6 "Mean Date"
>   and B7 "Standard Deviation" are computed over the 245 *distinct* histogram dates with the
>   Occurrences weights **discarded**; B7 reproduces to ≈11 ULP as the unweighted population sd, B6 as
>   `47227 + 23322/245`. The occurrence-weighted histogram is the legitimate target: mean **+111.45**,
>   σ **64.74** cal, P10/P50/P80/P90 = **+34/+124/+160/+179**. Correcting for MSP's bug makes the
>   divergence **larger**. The apparent near-match of POLARIS's "110.9 wd" to MSP's "107.82 days" is a
>   **coincidence trap**.
>
> ### Shipped in ADR-0307 (two defects, both proven against the reference's stored values)
> 1. **The Best Case formula was inverted** (`sra.py:913`). The first column of the SSI Risk Factors
>    table is the Best Case **as a % OF the ML**, not a % to subtract. Proven ML-independently (the
>    WC/BC ratio cancels ML): corrected rule **897/919 = 97.6%**, old rule **153/919 = 16.6%** — and
>    **every** old-rule match is factor 1, the degenerate band where `1 − 0.50 == 0.50`. That is why it
>    survived from ADR-0123: the "headline parity anchor" test was **self-referential** (it asserted the
>    code's own arithmetic) and its one reference-agreeing line is the factor-1 line. SSI's ladder is
>    deliberately mean-neutral (triangular mean = a constant **0.8667·ML** at every factor; the factor
>    widens only the *spread*). The inverted reading gave every factor the same 0.6·ML spread and slid
>    the mean to **+30.8% longer** at factor 5. *A risk ranking factor that does not change the
>    uncertainty is not a risk ranking factor.*
> 2. **Duration uncertainty was applied to COMPLETED work.** MSPDI omits `<RemainingDuration>` on a
>    100%-complete task, so `rem if rem is not None else duration` handed the **full original duration**
>    to `factor_to_bc_wc` and the run re-randomised work that had already happened. POLARIS randomised
>    **1722** activities where MSP randomised **919**; of the 634 100%-complete leaves SSI stores a
>    Best/Worst for **zero**. One finished activity (UID 6555, 635 wd, factor 5) alone shifted the focus
>    mean **+84.67 wd**. Guard now lives in the **engine** (`compute_sra_ssi` + `compute_jcl`), with the
>    web layer aligned. This is ADR-0306's family with the opposite sign — an **absent** figure read as
>    the **full** value. `_is_completed`'s own docstring already stated the invariant; the SSI path
>    silently violated it.
> 3. Operator-facing labels changed with the meaning (`% subtract (Best Case)` → `% of ML (Best Case)`)
>    so re-interpreting an operator-editable table is never silent.
>
> ### Law 2 status
> **`pytest -m parity` green — 44 passed, no golden moved.** ruff · ruff format · mypy --strict ·
> bandit (exit 0) · node --check all clean. The parity gate covers directional path analysis, not the
> SRA BC/WC rule, so the corrected values land in unit tests rather than parity goldens.
>
> ### ⚠️ NEXT — PARITY IS NOT ACHIEVED. A third model difference remains.
> Mean offsets from the deterministic finish, calendar days:
> **as-shipped +280 → fix completed-work only +132 → fix both +27**, against MS Project's **+111.45**.
> The corrected *rule* and SSI's own *stored values* land on the identical distribution (+27, σ 125.9),
> which is the cross-check that the rule is right. But **no configuration reproduces MSP's spread**:
> σ = 160.8 / 111.6 / 125.9 against **64.74** — still 1.7–2.5× too wide everywhere.
> **The residual defect is about VARIANCE, not the mean.** Risk-only σ is 55.8 cal, so if MSP applies
> the register as POLARIS does, MSP's duration-uncertainty σ is only √(64.74²−55.8²) ≈ **33 cal**
> against POLARIS's **99** from the *same* stored BC/WC — a factor of ~3.
> **Sharpest single statement of what is left:** the deterministic percentile moved P3 → **P40**, i.e.
> 40% of POLARIS iterations now finish before the deterministic date against MSP's **5.65%**. Same
> Best/Worst values, 7× difference — the two tools are not simulating the same network.
> **FINDING 3 (carried, CC-01 category) is the leading explanation.** Verified by execution: POLARIS's
> raw `compute_cpm` puts UID 152 at **2025-06-30**, and the page shows 2029-04-19 only because
> `_build_ssi_result` re-anchors onto the stored finish (a ~1388-day correction; ~1924 against the
> all-ML basis it actually uses). The ADR-0106 "all-ML reproduces `compute_cpm`" equivalence is
> **FALSE on this file** — the all-ML basis is **370 working days shorter**, because `_ml_minutes`
> feeds 92 in-progress tasks their *remaining* rather than full duration. **The simulation solves a
> compressed network that is not the schedule the rest of the tool displays.** Deliberate and
> long-standing (ADR-0106/0123), load-bearing for every progressed schedule — its own round.
> - **DO NOT "fix" this by reverting the BC rule.** Fixing only the completed-work defect lands the
>   mean at +132, *nearer* the target than the correct +27 — but its σ misses just as badly, and the
>   rule is wrong against 919 stored reference values. Letting one error cancel another is exactly what
>   Law 2 forbids.
> - **ASK THE OPERATOR FOR ONE ARTIFACT:** re-run the same SRA in MS Project with *Includes
>   Risks/Opportunities = **No***, everything else identical, and export. That isolates MSP's
>   duration-uncertainty half — the only remaining unknown. If its σ comes back near **33 cal**, MSP is
>   varying a much smaller effective set (most plausibly holding the status date 2025-03-10 and varying
>   only post-status work, where POLARIS lets the whole 2017→2029 network float). If near **99**, the
>   difference is in how the register combines with duration uncertainty instead.
>
> ### Hypotheses KILLED — do not re-chase (full detail in `audit/SRA-PARITY-20260729.md` §7)
> impact days being calendar rather than working days (the file stores `PT800H0M0S` = 100 × 480 min) ·
> `std_cal_days` being a 7/5 fudge (it is a real `pstdev` over calendar ordinals) · `mean_delta_days`
> overstating (independent Bernoulli firing makes it unbiased; SE ≈ 8.5 wd) · float absorption (both
> risk milestones have **TF = 0** and sit on the driving chain to 152) · **audit finding V2 as the cause
> of this screenshot** (V2 is about `impact_pct` collapsing on the *legacy multiplicative* `/sra` page;
> the screenshot is the *additive* `/sra/ssi` page and `impact_days` survived intact — V2 is still real,
> just not this).
>
> ### Still carried from ADR-0306 — each needs its own decision, none is a "just patch"
> **CC-01 (HIGH)** `offset_to_datetime` returns non-working dates (`cpm.py:255-281`, 74 call sites, root
> cause of V6 — needs a Fable 5 Max CPM deep dive) · **CC-05** negative sub-day slack floors (needs an
> SSI reference compare) · **V3** elapsed literals `"2 ed" == "2 d"` (product decision) · **V1/V2** SRA
> magnitude entry needs an operator-visible error surface (so the five standing UI requirements apply).
>
> ### Harness notes worth keeping
> - **Run dev tools as `python -m <tool>`, never bare.** A stale `/root/.local/bin/ruff` (0.15.8)
>   shadows the pip-installed 0.16.0 that CI resolves; 0.16 formats fenced python blocks inside
>   Markdown and 0.15 does not. A local-vs-CI FILE COUNT mismatch is the tell (793 files here).
> - `[tool.ruff.format] exclude = ["audit/*.md"]` is deliberate — a formatter must never rewrite
>   quoted evidence.
> - This container ships **no** runtime deps: `pip install -e ".[dev]"`; `python -m build` needs
>   installing too. `httpx` is dev-only and must never enter runtime `dependencies`.
> - Full `pytest -q` ≈ 9m; `pytest -m parity` ≈ 52s — run parity first.
> - **Converting the reference `.mpp` costs ~30s** and yields a 21.8 MB MSPDI:
>   `java -cp "tools/mpxj/classes:tools/mpxj/lib/*" MpxjToMspdi <in.mpp> <out.xml>`.
>   `parse_mspdi` on it is ~4 s and one `compute_cpm` is fast enough that **2000 SRA iterations run in
>   ~90 s**, so end-to-end reproduction of an operator SRA run is cheap — do it rather than reasoning
>   about the algorithm.
> - **A Monte-Carlo bisection must be run against an UNPATCHED tree.** A mid-run edit does not affect
>   an already-imported module, but a *later* run picks the patch up — two variants that should have
>   differed came back byte-identical because the new engine guard had neutralised the input. Record
>   run provenance next to every number.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
