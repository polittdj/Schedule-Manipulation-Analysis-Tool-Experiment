# Handoff — 2026-07-30 (MS Project already decided where remaining work goes; ADR-0309; v1.0.125)

> ## STATUS (current) — **the SRA divergence is CLOSED. ADR-0309 on `claude/smat-hardened-review-pwxm33`.**
> Against SSI's own committed export (2000 iterations, focus UID 152, the file's own 919 stored
> Best/Worst ranges and its own 2 stored risks): deterministic percentile **40.70 % → 6.65 %** against
> SSI's **5.75 %**; σ **125.5 → 65.5** calendar days against SSI's **64.744** (**1.2 %**); mean
> **+26 → +109 d** against **+111.45**; P10/P50/P80/P90 within **7/1/0/3** days. Version **1.0.125**,
> wheel + nine installers regenerated. Highest ADR **ADR-0309**.
> Evidence: `audit/SRA-ROOTCAUSE-20260730.md` · `audit/EXTERNAL-RECONCILIATION-20260730.md`.
> Redesign tail **rank 12** (`/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`,
> `/wbs/{name}`) is **still next** — three out-of-band Law-2 rounds in a row now.
>
> ## What ADR-0309 found — the oracle was already in the repo
> Both prior external audits and `audit/SRA-PARITY-20260729.md` §8 recorded the SRA question as
> oracle-gated and asked the operator for a new artifact. **It was already committed.**
> `00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_2026-7-29_11-57-1.xlsx` is a real SSI SRA
> export for the exact reference file, and the `.mpp` carries SSI's whole SRA **input** set in custom
> fields (`SSI SRA Event` → UID 152; `Best/Worst Case Duration` on **919** activities, 0 of them
> complete; `SSI SRA Risk Probability`/`Schedule Impact` on **2** risks). Input and output are both
> in-tree, so SRA parity is now an executable test:
> **`tests/parity/test_sra_ssi_oracle_uid152.py`** — the first SRA test whose expected values come
> from the reference tool rather than the engine's own arithmetic (ADR-0307 recorded that the previous
> "headline parity anchor" was self-referential).
>
> ## The root cause, and why two prior attempts failed
> `engine/cpm.py` had **zero** references to `status_date`. ADR-0106's Decision text requires a
> *"forward pass anchored at the status date"*; that clause was never implemented. So ordinary
> `compute_cpm` put UID 152 at **2025-06-30**, 1,388 calendar days before its stored finish, and
> `_build_ssi_result` added the constant back as a display correction.
> ADR-0108 declined this fix because two attempts to floor remaining work at the data date each
> regressed EVM1 and broke Project2/5 parity, concluding the ahead/behind judgement *"cannot be
> reverse-engineered safely from two data points."* **Correct about the unconditional floor, wrong that
> the judgement needed deriving — MS Project records its own answer in `<Resume>`, and the importer
> read `<Stop>` and discarded it.** EVM2 UID 20: `Resume 2012-09-13 08:00 + 480 remaining = 2012-09-13
> 17:00` = the stored finish, exactly. EVM1 UID 18 has `Resume == Stop` and must NOT move — an
> unconditional floor moves it, which is precisely the regression that killed both attempts.
>
> ## Consequences worth knowing before touching the SRA again
> - **The ADR-0106 equivalence is now TRUE, not retracted.** All four duration bases converge at
>   1,447,808 working minutes; ordinary `compute_cpm` reaches 2029-04-19 10:08 against a stored
>   2029-04-19 10:07:36 — **to the minute, computed rather than imposed**. The 370-working-day
>   compression and the 1,388-day load-bearing correction are gone, so external **H1** / the repo's
>   **FINDING 3** ("the agreement is an identity forced by the realignment") no longer applies.
> - **ADR-0108 is partly closed and the rest isolated.** EVM2 finish 2012-10-01 → **2012-10-02**
>   (Acumen 2012-10-04), NFI −19 → **−20** (Acumen −22): **1 of 3 working days.** The other 2 are a
>   **different** defect — the unstarted successor chain (UIDs 23/25/26/28/29/30 start 1–5 days before
>   their stored dates) — pinned in `tests/engine/test_evm_acumen_reference.py`, not folded into ADR-0309.
> - **`pytest -m parity` green (49).** Project2/5 carry 3 and 2 rescheduled tasks and did not move —
>   the SSI driving-slack path already reads stored progress-aware dates (`driving_slack.py:120-129`).
>   Measured BEFORE writing the change, not assumed after.
> - **A floor built from the STORED remaining silently destroys the Monte-Carlo's upside variance**
>   (measured: `det_pctile = 100 %`, σ 20.3, no iteration later than deterministic). It must follow
>   `duration_overrides` — every override producer supplies a remaining-duration basis for incomplete
>   tasks. The wrong version looked like an improvement on 3 of 6 headline metrics. Do not "simplify" it back.
> - **Do NOT chase SSI's `Mean Date` / `Standard Deviation` cells (47322 / 107.8198).** They are
>   computed over the 245 DISTINCT dates with the `Occurrences` weights dropped (reproduced to ~11 ULP,
>   twice, independently). The target is the occurrence-weighted histogram: mean +111.45, σ 64.744.
>   `test_the_summary_cells_are_not_the_parity_target` pins the trap shut. SSI's `% Cumulative
>   Probability` column IS weighted; only those two summary cells are not.
>
> ## ⇢ NEXT — the approved plan, in order
> Phase 2 of the approved plan (each item one ADR + one PR, sequenced so no fix can be credited to
> error cancellation): **1** H5a docstring (zero executable lines) · **2** the working-axis vs
> wall-clock ADR (blocks 3 and 6) · **3** H2c import warning · **4** the **H6 presentation defect
> confirmed this session and missed by every external pass** — ~50 finish-date surfaces, only 7
> basis-labelled, 21 with none, and a raw `compute_cpm` value labelled *"Forecast finish"* in
> `ai/briefing.py:843` and the `/trend` header · **5** V1/V2 tri-state SRA magnitude parser.
> Then Phase 3: **CC-01** (74 call sites, Fable-5-Max deep dive) and **V3** elapsed literals (highest
> risk in the plan — it silently changes saved-filter populations; version the evaluator and ship a
> migration report first). Phase 4 performance (P1–P6, measured by the external pass, unremediated).
> Phase 5 is the untouched UI queue: rank 12 → 13 → 14, AXIS-TITLES `PENDING` 5 → empty, OR-01/02/03.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) `offset_to_datetime` non-working dates, 74 call sites · **CC-05** (H5) negative
> sub-day slack floor, oracle-gated · **V1/V2** (H3) SRA magnitude needs an operator-visible error ·
> **V3** (H4) elapsed literals — direction now settled by ChatGPT's MPXJ `GenericCriteria` oracle,
> product decision still open · the **legacy `/sra` cross-basis defect** newly found this session
> (`_build_result` reads a full-duration deterministic against a remaining-duration sample, no
> realignment; reaches `/api/sra`, the SRA report, `sra_conclusions`, and
> `scorecards.reserve_recommendation`, whose dates sit on a different axis from `/api/margin/risk`) ·
> **a committed SSI export contradicts ADR-0307's Best-Case rule** (Project5 `SRA Sensitivity
> Analysis.xlsx` shows the pre-0307 ratios; ADR-0307 stands for the artifact we match — stored
> Best/Worst wins, the table+rule is the operator-entered fallback) · `resume` is read from **MSPDI
> only**, the XER path has no equivalent.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 (impact days as calendar not working days ·
> `std_cal_days` as a 7/5 fudge · `mean_delta_days` overstating · float absorption · V2 as the cause of
> the screenshot), **plus**: reverting ADR-0307's Best-Case rule (it moves the mean closer while
> leaving σ wrong — the exact error cancellation Law 2 forbids), and an **unconditional** data-date
> floor (ADR-0108's two reverts; ADR-0309 supersedes with the stored-`Resume` read).
>
> ## Harness notes
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's; the tell is a
> **793** file-count mismatch). **`pip install -e .` before running the suite** — with a bare
> `PYTHONPATH=src` the package has no distribution metadata and ~200 web tests fail with
> `PackageNotFoundError`, which is setup contamination and not a product verdict (an external audit hit
> the identical 211-failed/828-error pattern and correctly discounted it). Converting the reference
> `.mpp` needs a writable `TMPDIR` (MPXJ's `UniversalProjectReader` copies OLE input to a temp `.dat`)
> — ~9 s here, and **2000 SRA iterations ≈ 90 s**, so the new oracle test costs ~2 min. Full `pytest -q`
> ≈ 15 m; `pytest -m parity` ≈ 40 s — run parity first. Regenerate the wheel with
> `--outdir dist/wheel` (the default silently embeds a STALE wheel) and only ONCE after all code lands.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
