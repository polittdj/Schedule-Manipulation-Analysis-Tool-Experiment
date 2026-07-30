# Handoff — 2026-07-30 (two time axes + rank 12 opened; ADR-0310, ADR-0311; v1.0.128)

> ## STATUS (current) — **Phase 2 items 1/2/4 shipped as ADR-0310 (v1.0.127). SRA parity CLOSED earlier this day (ADR-0309, #483 + #484).**
> ADR-0310 writes down the **two time axes** (working vs wall-clock) — the shared root both external
> audits demanded be stated before CC-01 and V3 are touched — corrects the **H6 mislabelling** no
> external pass caught, and fixes the `_whole_days` docstring (H5a). **No computed number moves.**
> Against SSI's own committed export (2000 iterations, focus UID 152, the file's own 919 stored
> Best/Worst ranges and its own 2 stored risks): deterministic percentile **40.70 % → 6.65 %** against
> SSI's **5.75 %**; σ **125.5 → 65.5** calendar days against SSI's **64.744** (**1.2 %**); mean
> **+26 → +109 d** against **+111.45**; P10/P50/P80/P90 within **7/1/0/3** days. Version **1.0.126**,
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
>
> ## Follow-up round — an external review of the PLAN, and what it changed
> The operator put the completion plan back to ChatGPT. Two of its objections were correct; full
> adjudication in `audit/EXTERNAL-RECONCILIATION-20260730.md` §"Round 2".
> - **It was right that the plan's §3.4c was unsafe.** That paragraph said *"an activity with
>   remaining work starts no earlier than the data date"* — the **unconditional** floor ADR-0108
>   records as regressing EVM1 twice. **The shipped code never did that** (it reads stored `<Resume>`
>   and is conditional), so nothing had to change in the engine — but the plan text did, and would
>   have misled the next implementer. **If you read only one thing before touching this again: the
>   anchor is conditional on stored data, never a blanket data-date floor.**
> - **It was right that KS `D <= 0.10` was not statistically justified** — the α=0.05 two-sample
>   critical value at n=m=2000 is `1.36·sqrt(2/2000) = 0.043`, so it was ~2.3× too loose. It never
>   shipped, but the principle did: **every tolerance in the oracle test is now floored by the
>   MEASURED seed-to-seed spread** (5 seeds × 2000 iterations), and tightened accordingly — det
>   ±3→±2 pp, σ ±10→±5 %, mean ±10→±6 d, P50/P80/P90 ±10→±5 d. **P10 keeps ±10 deliberately**: seed
>   sd 4.4 d, worst error 7 d — it is the sparse lower tail and tightening it buys flakiness.
>   All five seeds pass every gate, so the parity is not one lucky seed.
> - **Its "compensating errors could fake the aggregate" objection prompted the per-task check it
>   demanded** — and that check found a residual nobody had measured:
>   `in-progress 90/92 EXACT (97.8 %)` · `not started 583/907 (64.3 %)` · **`complete 2/724 (0.3 %),
>   median −1458 d`**. The forward pass still packs COMPLETED work from `project_start`. It does not
>   move the focus or project finish (both driven by remaining work) and consumers read stored dates
>   first, which is why it went unseen — now in `cpm.py`'s module contract and Phase 7.
> - Unsubstantiated: "historical fixes not adequately regression-locked" (no specific gap named) —
>   added to Phase 7 as a **verification** task, not an assumed defect.
>
>
> ## What ADR-0310 settled (read before touching CC-01 or V3)
> - **The working axis is canonical**; wall-clock appears only at the presentation boundary and in the
>   elapsed helpers. **Adding a working-axis quantity to a wall-clock one is a defect** — and
>   `cpm.py:295` (`day + timedelta(minutes=intraday)`) is exactly that, which is the whole of CC-01's
>   mechanism. Not repaired here; now it has a contract to be repaired against.
> - **The elapsed convention was already established EIGHT times** (`1440 if duration_is_elapsed else
>   per_day` in `state.py:1348`, `app.py:5352/9639/11344/18344/18404`, `margin_dashboard.py:188`,
>   `dcma14.py:230`) and MPXJ's `GenericCriteria` agrees. **`engine/msp_filters.py` is the sole
>   violator** — hard-codes `"d": 480`, never reads `duration_is_elapsed` (0 occurrences vs 24
>   repo-wide), captures the elapsed marker in regex group 2 and discards it. **This reduces V3 from
>   "choose semantics" to "make the outlier conform"** — but the saved-filter population still moves,
>   so the evaluator versioning + migration report still gate it.
> - **The supported project-start domain is `start_tod + working_minutes_per_day <= 1440`**, enforced
>   at the IMPORTER (normalise or reject with an operator-visible message), not by a downstream
>   warning — a warning leaves the internal inverse broken while the page looks fine.
>   **`Calendar` gaining a real shift-start field is deliberately NOT decided** — it redefines the
>   offset axis and needs its own round.
>
> ## H6 fixed (the finding no external audit caught)
> A raw `compute_cpm` value was labelled **"Forecast finish"** in the briefing banner, propagating to
> Mission Control and chapter 12, and again in the `/trend` header + "Current finish" card. Renamed
> **"Schedule-logic finish (CPM)"** in all five languages. Plus: `"As-scheduled (stored dates)"` now
> HAS a methodology card (it was the only method with none, on a page whose prose said "three" while
> rendering four) and a lane colour (`var(--muted)`, verified in all four themes — it was falling
> through to `var(--ink)`); `/api/forecast` now ships `basis` (mandatory on the model, exported to
> Excel, but absent from the payload, so no consumer could label what it drew); the Excel title's
> method count is derived instead of the literal "three".
>
>
> ## RANK 12 IS OPEN — ADR-0311 landed its first slice
> The operator decided the vocabulary: off-spine pages get a **non-chapter kicker** and **no Continue
> segue**; `/card` + `/wbs` get **nav entries**. Half was already shipped behaviour — `_chapter_kicker`
> drops the `CHAPTER NN ·` prefix when `num` is empty and `_story_footer` excludes SETUP from
> `_STORY_ORDER`, so the four Setup pages already had label-only kickers and no segue. **A prior survey
> reported "no kicker" on all six; that was a measurement error** (the probe regexed `CHAPTER \d+ ·`,
> which cannot match an empty-number kicker). Do not re-chase it.
> **Shipped:** a `@card` sentinel beside `@analysis`/`@wbs`; `/card` is now a beat of chapter 01 and
> `/wbs` names chapter 07 explicitly (both have dynamic titles that can never resolve through
> `_TITLE_TO_CHAPTER` — the `chapter=` override exists for exactly this and they never used it); all
> **six** Setup entries carry a takeaway, surfaced as the nav link `title` because an off-spine page has
> no segue to render it in; pinned by `test_every_setup_rail_entry_carries_a_takeaway`.
>
> ## ⇢ RANK 12 STILL OWES (with its blockers named)
> - **takeaway h1 + context line** on the five pages lacking one (only `/margin` has one) — unblocked.
> - **`▦`/`⤓`/`⛶` toolbar + read-me line on every visual** — none of the six has it. **Two hard
>   dependencies:** `/margin` renders via `margin_dashboard.js`, one of the five AXIS-TITLES `PENDING`
>   modules (batch 3b); `/workbench` via `workbench.js`, in `NO_SVG_AXES`, whose DOM caption mechanism
>   ADR-0298 "deliberately did not invent". Neither closes inside rank 12.
> - **`data-noprint`** is set on none of the six and still has **zero CSS rules anywhere** — the open
>   operator decision across ten merged contract pages. The DoD print checkbox is unsatisfiable until it
>   lands.
>
> ## ⇢ NEXT — finish rank 12, then 13 and 14
> **Phase 2 items 1, 2 and 4 are DONE** (ADR-0310). Remaining from Phase 2: **item 3** H2c
> normalise-or-reject at import (ADR-0310 decision 5 specifies it) and **item 5** V1/V2 tri-state SRA
> magnitude parser with an operator-visible error.
>
> **⇢ TAKE RANK 12 NEXT.** The UI queue has now been deferred by **five** consecutive out-of-band
> Law-2 rounds (ADR-0306 → 0307 → 0308 → 0309 → 0310). Every deferral was individually justified;
> the pattern is not. Rank 12 = `/workbench`, `/groups`, `/standards`, `/margin`, `/card/{name}`,
> `/wbs/{name}`, then rank 13 (vendored typography) and rank 14, and AXIS-TITLES `PENDING` 5 → empty.
> The five standing UI requirements apply. Do NOT take another correctness round ahead of it unless
> something genuinely urgent surfaces — Phase 2's remainder, Phase 3 (**CC-01**, 74 call sites,
> Fable-5-Max deep dive; **V3** elapsed literals, now a conformance fix per ADR-0310 but still
> population-moving) and Phase 4 (P1–P6, measured but unremediated) all wait behind it.
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
