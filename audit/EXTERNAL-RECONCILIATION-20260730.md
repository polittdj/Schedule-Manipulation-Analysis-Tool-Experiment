# Four-way audit reconciliation — who was right, on reproducible evidence

Date: 2026-07-30 · Adjudicated against `b62ba01` (v1.0.124), one commit newer than the `08c5383` all
three external passes reviewed. Companion: `audit/SRA-ROOTCAUSE-20260730.md`.

Inputs: `audit/external/EXTERNAL-{CHATGPT,CLAUDE,GEMINI}-20260729.md`, the repo's own
`audit/SRA-PARITY-20260729.md` and `audit/{CC-FINDINGS,VALIDATION,LAW2-IMPACT}-20260729.md`, plus an
independent execution pass. "Verified here" means a test was run at `b62ba01`; where nothing was run,
this document says so.

The commission was to decide on **quantitative reproducible evidence, not on who asserted it**. Two
of the external passes were partly wrong, one was unusable, and **all three missed the two facts that
mattered most**: the SSI oracle was already committed to the repository, and finding H1's cause was
an ADR-0106 clause that was never implemented.

---

## Verdicts

| # | Finding | ChatGPT | ext. Claude | Gemini | Adjudication |
|---|---|---|---|---|---|
| **H1** | SRA all-ML network / date realignment | narrower defect: false contract + undisclosed basis | **not executed**, no verdict | — | **ChatGPT right on measurement, both incomplete on cause.** Reproduced here to the digit: offsets 979,919 / 802,319, Δ −177,600 min = −370 wd, 92 activities. **But the cause is the unimplemented ADR-0106 status-date clause** (`grep -c status_date cpm.py` → 0), now fixed by ADR-0309: all four bases converge and CPM reaches the stored finish to the minute. **ChatGPT's realignment-as-defect was overstated** — SSI's own export labels its anchor `Current Finish` = the stored finish, so aligning there is what SSI does; the defect was non-disclosure plus the compressed network underneath. |
| **H2a** | `offset_to_datetime` returns non-working dates | confirmed HIGH; drove a supported JSON start to a served page showing Saturday | confirmed, display-only; "corpus never triggers it" | — | **Both right, not in conflict.** ChatGPT right on reachability via a supported input path; ext. Claude right that the committed corpus is clean. Carried in-repo as **CC-01** (74 call sites). Open. |
| **H2b** | inverse property broken | folded into H2 | **narrowed to unreachable** (`start_tod + per_day > 1440` strictly) | — | **ext. Claude right** — a genuine narrowing ChatGPT missed. |
| **H2c** | precondition documented, never enforced | covered under R2 | derived independently | — | **Both right.** Verified: no importer normalises `project_start`; `Calendar` has no shift-start field; `offset_to_datetime` silently rolls a non-working start forward with no warning. |
| **H3** | malformed SRA magnitude → persisted locked zero | confirmed; POST → 303, survives save/reload, additive and legacy models disagree | **not executed**, no verdict | its harness crashed | **ChatGPT right.** Carried in-repo as **V1/V2**. Open. |
| **H4** | elapsed / unknown duration literals | confirmed **with an MPXJ `GenericCriteria` oracle** (elapsed days = 1440 min; criteria normalise to hours) | confirmed inconsistency; direction "oracle-gated" | — | **ChatGPT decisively right** — it obtained the external oracle, so the *direction* is no longer open. Verified here: regex group 2 captures the elapsed marker and nothing reads it; `duration_is_elapsed` appears in 24 places repo-wide and **zero** in `msp_filters.py`; `float()` is unguarded, so `"1.2.3"` raises rather than returning `None`. Carried as **V3**. Open, product decision first. |
| **H5a** | `_whole_days` docstring false for negative sub-day | confirmed behaviour; parity oracle-gated | confirmed doc defect; no oracle needed | — | **Both right.** Docstring says sub-day reads 0; `//` yields −1 across `(−per_day, 0)`. Classification unaffected (`<= 0` either way). Carried as **CC-05**. |
| **H6** | pure-logic CPM shown as forecast | **"disproved"** — `/forecast` labels four bases distinctly | "presentation not audited" | — | **ChatGPT right about `/forecast`, wrong to clear the product.** A presentation audit run here found ~50 finish-date surfaces: **7** fully basis-labelled, **21** with none, and a raw `compute_cpm` value labelled *"Forecast finish"* in `ai/briefing.py:843` (propagating to Mission Control and Chapter 12) and in the `/trend` header. `"As-scheduled (stored dates)"` has no methodology card and no lane colour while the page says "three methods". `FinishForecast.basis` is mandatory in the model but absent from `/api/forecast`'s payload. **A narrower presentation defect is confirmed and no external pass found it.** |
| **P1–P6** | performance | **measured** — the only pass that did | zero measurements, correctly declined as environment-blocked | — | **ChatGPT right and uniquely useful.** P2/P6 corroborated by reading `state.py`: `schedules`, `summaries`, `dash_cores`, `dash_cards` are plain unbounded dicts; only `analyses` (48), `cpms` (144), `polished` (48) are LRU. Its P5 refusal was correct — no browser existed there. |
| — | Gemini's two "critical failures" | — | — | 2 findings | **Both are its own harness errors.** Verified: `Calendar` is `extra="forbid"` with no `start`/`end` fields, so `Calendar(start=…, end=…)` cannot construct; `_reconcile_magnitudes` takes **5 required positional** parameters and both real call sites pass 5. Its proposed fixes would weaken a frozen model and a validated signature. **Recorded; nothing acted on.** |

---

## Scoreboard

**ChatGPT** — strongest pass by a wide margin. It executed every workstream, obtained a genuine
external oracle for H4, produced the only performance measurements, and correctly diagnosed its own
environment failure (the missing `/tmp` that made the committed MPXJ converter look broken) instead of
reporting it as a product defect. It over-called H1's realignment and wrongly cleared H6.

**External Claude** — honest about scope: it declared H1, H3 and P1–P6 not executed rather than
implying coverage, and contributed one real narrowing (H2b). Its refusal to produce performance
numbers from unrepresentative hardware was the right call. But four of ten workstreams had no verdict.

**Gemini** — contributed nothing usable. Both findings were artifacts of test code that did not match
the codebase, and it did not detect that.

**All three missed** that `00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_*.xlsx` is a real
SSI SRA export for the exact reference file, and that the `.mpp` carries SSI's whole SRA input set in
custom fields. Both external passes and the repo's own evidence file recorded the SRA question as
oracle-gated and requested a new artifact from the operator. It was already committed. That single
miss is what kept the SRA divergence open.

---

## Corrections to the repo's own evidence

Found while adjudicating; each is a defect in a repo document, not in code.

1. **`audit/SRA-PARITY-20260729.md` quotes SSI's deterministic percentile as 5.65 %** (strict `<`).
   The tool computes `bisect_right(...)/n`, i.e. `<=`; the comparable figure is **5.75 %**. No
   conclusion changes.
2. **Its claim that ADR-0123's validation was "self-referential" and that "every POLARIS match is
   factor 1" is wrong on the record.** ADR-0123 cites UID 107 and 39 at factor **5** and UID 35 at
   factor **2** from `00_REFERENCE_INTAKE/SRA Sensitivity Analysis.xlsx` — real reference values at
   non-degenerate factors.
3. **A committed SSI export contradicts ADR-0307's corrected Best-Case rule.** Verified
   independently: on `SRA Large Test File2.mpp` the stored BC/ML by stored factor is 0.5001 / 0.4000 /
   0.2999 / 0.2001 / 0.1002 — ADR-0307's rule exactly, over 919 activities. But that Project5 export
   gives 0.9 / 0.6 / 0.5 at the same Worst-Case column — the pre-0307 rule. Under one fixed table the
   two artifacts are mirror images. **ADR-0307 stands for the artifact we match**, and the robust
   posture is the existing precedence: a stored Best/Worst wins, and the table+rule is the fallback
   for operator-entered factors only. Recorded as an open item rather than left unmentioned.
4. **`audit/SRA-PARITY-20260729.md` and the external reports carry stale `sra.py` line numbers**
   (+14…+37 in the SSI region after ADR-0308).
5. **`docs/STATE/HANDOFF.md` was one event stale** (it described #482 as "CI running"; it had merged)
   and **`docs/STATE/NEXT-SESSION-PROMPT.md` was three versions and three ADRs stale.** Both fixed
   this session.

---

## What this session changed, and what it did not

**Changed.** ADR-0309 — the SRA divergence closed to within 1.2 % on σ and 0.9 pp on the
deterministic percentile; the ADR-0106 equivalence made true rather than retracted; ADR-0108's
headline residual partly closed and the remainder isolated to a different defect; the first SRA parity
test whose expected values come from the reference tool.

**Not changed, and still open** — carried with their existing identifiers so nothing is lost:
CC-01 (H2a, 74 call sites), CC-05 (H5, oracle-gated), V1/V2 (H3), V3 (H4, product decision first),
the H6 presentation defect newly confirmed here, the legacy `/sra` cross-basis defect newly found
here, P1–P6 (measured by ChatGPT, unremediated), and the 2 remaining working days of ADR-0108's EVM2
residual. Sequencing and exit criteria for all of them are in the approved plan.

---

## Round 2 — an external review of *this plan*, and what it changed

2026-07-30, after ADR-0309 merged as #483. The operator put the completion plan back to ChatGPT and
asked whether it would fix the findings. Its verdict was "no — not as written." Assessed point by
point below; **two of its objections were correct and one of those was materially important.** It was
reviewing the plan text, not the shipped code, which matters for reading its H1/§3.4 verdict.

| Its objection | Assessment | Action |
|---|---|---|
| Only Phase 0+1 is the immediate deliverable, so H2–H6, retention and browser perf stay open | **Accurate**, and by design — the operator scoped this round. The plan maps the rest with exit criteria | none; scope is the operator's call |
| **The engine-wide data-date proposal is unsafe: §3.4c floors every unfinished activity at the data date, and ADR-0108 shows MS Project applies progress override conditionally** | **CORRECT, and the best point made.** §3.4c as written *was* the unconditional floor that regressed EVM1 twice. Had it been built as specified it would have reproduced that failure | **Plan §3.4c marked SUPERSEDED.** What shipped reads MS Project's stored `<Resume>` and is conditional by construction — `resume == stop` floors nothing, so EVM1 UID 18 provably does not move |
| The risks-on workbook does not uniquely prove the missing anchor is the only cause; compensating errors could produce a matching aggregate. Per-task ahead/on-track/behind results should remain required | **Substantially valid** — though the component decomposition (duration-only, risk-only, both) had already tested the halves separately, which it could not have known | **Ran the per-task test it asked for.** Of 92 in-progress activities, **90/92 (97.8 %) match MS Project's own stored finish exactly** (outliers UID 5376 −4 d, UID 5669 +37 d). Aggregate agreement is now backed by per-task agreement |
| H2 is not fixed by a warning plus a display-only helper; supported late-start input still violates the conversion precondition internally | **Valid** | Plan item 3 strengthened from *warn* to **normalize or reject at import**; item 6 records why the internal and rendering halves are split rather than conflated |
| The performance phase lacks acceptance gates | **Valid** | Phase 4 exit criteria replaced with numeric gates: 1/2/4/8-project scaling, bounded concurrency with cancellation and backpressure, RSS/latency ceilings, no regression to the persistent-MPXJ and warm-cache wins, concurrency/eviction/wipe tests, and browser heap + **accessibility tree and export completeness** |
| KS `D ≤ 0.10` is not statistically justified and is probably too permissive for two 2000-iteration samples | **CORRECT — checkable arithmetic.** The α = 0.05 two-sample critical value at n = m = 2000 is `1.36·√(2/2000) = 0.043`, so 0.10 is ~2.3× too loose. It never shipped (the delivered test asserts percentile/σ/mean bands, not KS) but the plan was wrong | Plan corrected; **tolerances must now be floored by the measured seed-to-seed spread**, with component-level gates alongside the aggregate so cancelling errors cannot pass |
| Historical fixes are not adequately regression-locked | **Unsubstantiated** — no specific gap named, and its own audit ran 14 controls that passed | Added to Phase 7 as a **verification** task (a named owning test per item, or a written gap), not as an assumed defect |
| Recommendation: preserve pure-logic `compute_cpm`, add a typed progress-aware basis, migrate consumers after per-task parity | **Partly overtaken, partly right.** The shipped change is conditional on stored data with `date_driven` disclosure, following ADR-0034's existing precedent for honouring stored dates — so a separate solver is not required. But it was right that the *contract* had drifted | `cpm.py`'s module docstring now states the engine is **conditionally progress-aware**, names the condition, and records what is still NOT anchored |

### What the per-task check exposed that no audit had measured

Running the parity it demanded surfaced a genuine residual:

```
in-progress (0<pct<100)  n= 92 : EXACT 90/92 = 97.8%   median  +0 d
complete   (pct==100)    n=724 : EXACT  2/724 = 0.3%   median -1458 d
not started (pct==0)     n=907 : EXACT 583/907 = 64.3% median  +0 d
```

The forward pass still packs **completed** work from `project_start`. It does not move the focus or
project finish (both driven by remaining work), and consumers needing real per-task dates read the
stored ones first (`driving_slack.py`) — which is why it went unnoticed. It is now recorded in
`cpm.py`'s module contract and carried in Phase 7 as the natural completion of ADR-0309.

**Net:** the review did not overturn ADR-0309's result — the SRA numbers stand, and its central
safety objection describes a plan paragraph that the implementation had already declined to follow for
exactly the reason it gives. But it caught a real defect in the plan text, a real arithmetic error in a
proposed tolerance, and a real contract gap in the shipped docstring, and the test it insisted on
found a residual worth having. Adversarial review of a *plan* earned its keep here.
