# MASTER VERIFICATION & PARITY AUDIT — Schedule-Manipulation-Analysis-Tool

**Mode:** read-only / forensic / falsification-oriented. No source, test, fixture, config, or threshold
was modified. The only files created are this report and `audit/PATH-FORWARD.md`. `git status` was clean
throughout except those two files. No network connection was opened (air-gap verified by static inspection
only).

**Method:** Phase A discovery → Phase B oracle inventory → six parallel read-only verification subagents
(W1–W13) each told the oracle reality and forbidden to fabricate parity → the full quality-gate sequence
run read-only → Phase D multi-pass reconciliation (each finding re-derived by ≥2 methods where possible;
adversarial disproof attempted) → Phase E open-item reconciliation → Phase F blind-spots. Every
quantitative claim cites a `file:line` or a named oracle fixture. Confidence is tagged
CONFIRMED / SUSPECTED / UNVERIFIABLE-IN-ENV.

> **Errata (2026-06-26) — two "missing artifact" claims were overstated; corrected below.**
> A follow-up re-sweep of the working tree found that two items this report had listed as artifact-gated
> were in fact already satisfied in-repo:
> 1. **Cost EVM parity is NOT un-oracled.** `tests/fixtures/golden/evm/EVM1.mspdi.xml` and `EVM2.mspdi.xml`
>    are committed, cost-loaded **Acumen-Fuse exports**, and `tests/engine/test_evm_acumen_reference.py`
>    (6 tests, passing) already validates the cost metrics (BCWS/BCWP, DCMA, BEI) against the Fuse "Metric
>    History Report" and pins the documented SPI(t)/finish/Net-Finish-Impact **residuals**. Those residuals
>    are the standing **ADR-0108 data-date gap** (a pure-logic-CPM limitation), *not* a missing export. So
>    cost-EVM is **partially verifiable in-env** (matched rows confirmed), not "NONE / UNVERIFIABLE."
> 2. **The `.mpp`→MSPDI toolchain is present.** A Java 17 runtime is installed and the vendored MPXJ
>    converter (`tools/mpxj/` — `MpxjToMspdi.class` + `lib/*.jar`) is runnable here. The native-`.mpp`
>    parity work is blocked **only on the absent `.mpp` data**, not on the toolchain.
> The genuinely-absent artifacts are unchanged: the `NASA_Metrics_Complete_*.aft` Bible, the operator's
> Acumen Fuse §A/§B/§C/§E exports of the current Project2/Project5 pair, the native `.mpp` files
> (`Project2`/`Project5`/`Large_Test_File`), and SSI's recorded focus UID for `Large_Test_File.mpp`.
> The inline rows in §3 and §8 below carry these corrections.

---

## 1. Executive summary (worst-first)

**No CRITICAL defect was found.** The two highest-stakes invariants for a CUI forensic tool —
**air-gap / data-egress** and **LLM-narration-only** — both survived aggressive falsification (W1/W2,
corroborated by 48 passing guard tests). The CPM engine's core math, calendar arithmetic, determinism, and
metric *sourcing* are sound. The full quality gate is green (cov 98.37% / engine 99.66% / parity / bandit /
ruff / mypy).

The real exposure is **not in the numbers the tool computes against its committed oracle, but in (a) what
the in-environment oracle can and cannot prove, (b) one genuine fidelity gap where the engine *understates*
a behind-schedule slip, and (c) a cluster of stale/over-claiming documentation that would mislead a reader
who cited it in a testimony context.**

| Sev | Finding (short) |
|-----|-----------------|
| **HIGH** | **F-01 — Acumen Fuse *numeric* parity is UNVERIFIABLE-IN-ENV, and a documented *circular* subset exists.** The committed Fuse exports are absent; `case.json` is a human transcription. Most of it traces to an independent Acumen transcription (`PARITY-TARGETS.md`), but the §E float/critical change-metrics + the refreshed Project5 values were re-pinned to **engine output** (`case.json:6`, `tests/engine/metrics/test_change_metrics.py:51-52`), so for that subset the green gate proves self-consistency, not parity. Labeled, not fraud — but a reader running `pytest -m parity` could believe those figures are Acumen-validated. |
| **HIGH** | **F-02 — The engine *understates* a real slip: TP4 v5 finish = 2026-06-26 vs MS-Project truth 2026-07-17.** `cpm.py` never references `status_date`; in-progress remaining work is not floored at the data date, so an honest ~3-week slip collapses onto the prior version's finish. Documented open gap (ADR-0108; two fix attempts reverted for breaking parity), **unguarded by any test**, and TEST-PROJECTS.md over-states it as test-pinned. |
| **HIGH** | **F-03 — `docs/PARITY-REPORT.md` headline numbers are severely stale (pre-ADR-0112).** It still shows Project5 Critical 41/**37**, DCMA-06 **43/40** residual, Baseline-Start-Compliance **38/23**, Net Finish Impact **−99**, SSI focus UID **143** — whereas the authoritative `case.json`/live gate have **4**, **44 exact**, **41/25 exact**, **−148**, focus UID **145**. The human-readable parity report contradicts the tool. |
| MEDIUM | **F-04 — "Critical" means two different things across modules.** `float_analysis`/`change_metrics`/`manipulation` use pure-CPM `is_critical`; `schedule_quality`/`dcma14` use the stored-flag-preferring `is_effective_critical`. Counts match on the goldens by coincidence, but the **cited UID sets differ** (P2: pure-CPM adds {99,143}, drops {96,144}). Plus a stale `float_analysis.py:14` docstring (says "Project5 = 37"; authoritative is 4). |
| MEDIUM | **F-05 — The namesake detector misses two classic manipulation vectors:** constraint-abuse-to-mask-negative-float and calendar-gaming. `diff.py` already tracks constraint deltas (`diff.py:31-32`) but `detect_manipulation` never reads them; there is no calendar diff at all. |
| MEDIUM | **F-06 — Jinja layout autoescape is OFF and CSP allows `unsafe-inline`,** so HTML-escaping is the *sole* XSS barrier. Currently inert only by accident (the one raw sink, `<title>{{title}}`, is RCDATA and `_clean_key` basenames away `</title>`). Latent defense-in-depth gap. |
| MEDIUM | **F-07 — Documentation drift cluster:** `TEST-PROJECTS.md` over-claims its numbers are test-pinned (battery only asserts `finish>0`); `risks.md` R-02/R-13 repeat the superseded −99/residual numbers; **ADR-0045 contradicts PARITY-REPORT.md** on whether the Large-File absolute SSI values were reproduced. |
| MEDIUM | **F-08 — Coverage config is dead/misleading.** `pyproject` `addopts` has no `--cov` (local `pytest` enforces **zero** coverage); `[tool.coverage.report] fail_under = 99.9` (and its comment) is dead config that CI overrides with `--cov-fail-under=70` — and actual coverage 98.37% is *below* 99.9, so it would fail if ever live. |
| LOW | F-09 free-float can exceed total-float on non-FS links (documented, FS-scoped). F-10 stored 17:00 vs engine-rendered 16:00 time-of-day drift. F-11 AI figure-gate guards digit *presence* not *role* (a task name like "Milestone 2099" can be re-roled in interpretive Q&A). F-12 `ai/qa.py` module docstring stale ("two modes / interpretive default" — introduced by PR #267 / ADR-0129). F-13 minor manipulation FN nuances (shortened-duration checks only `duration_minutes`; first-baseline None→date FPs; no dedicated "deactivated" flag). F-14 unsourced display thresholds (driving-slack 10/20 d; structural/health 35% lag, 10-d band). |
| DISCLOSED | Four pre-existing, ADR-0110-disclosed metric *drifts* (DCMA-05 hard-constraint set; DCMA-08 baseline-duration; SPI(t) count-based ES; Float-Ratio scope) — not defects; parity-bounded; recorded here for completeness. |

**Bottom line:** the tool does not over-claim in code (NA discipline holds, residuals are gate-locked, the
team explicitly refused to relabel the SSI golden as engine-truth). The over-claims are in the *prose docs*
(F-03/F-07) and in the *test pinning* (F-02/F-08). The one true engine-fidelity concern (F-02) is a
known, documented limitation that simply is not yet guarded or fully disclosed at the point a user reads it.

---

## 2. Repo Reality Map + declared Acumen scope

**Package:** `src/schedule_forensics/` — `model/` (frozen pydantic Task/Schedule/Calendar/Relationship),
`importers/` (`mspdi`, `xer`, `json_schedule`, `mpp_mpxj` [Java/MPXJ], `loader`, `_common`), `engine/`
(`cpm`, `driving_slack`, `driving_path`, `diff`, `manipulation`, `trend`, `sra`, `recommend`,
`summary_logic`, `metrics/` ~28 modules), `ai/` (`backend`, `null`, `ollama`, `openai_compat`,
`net_guard`, `qa`, `citations`, `narrative`, `briefing`, `driving_facts`), `web/app.py` (FastAPI, ~8.8k
lines, server-rendered HTML + vendored JS in `web/static/`), `reports/` (docx/xlsx), `launcher.py`.

**Entry points:** console script `schedule-forensics` → `launcher.main` (binds `127.0.0.1`, opens browser);
`python -m schedule_forensics.launcher`.

**Tests/fixtures:** 1664 tests. Committed schedule oracles: `tests/fixtures/golden/project2_5/`
(`Project2.mspdi.xml`, `Project5.mspdi.xml`, `case.json`), `golden/evm/EVM{1,2}.mspdi.xml`,
`golden/ssi_uid143|ssi_uid145/case.json`, `fixtures/test_projects/TP1..TP4(v1-v5).xml`,
`fixtures/mspdi/commercial_construction.xml`, `fixtures/xer/commercial_construction.xer`. **130 ADRs**
(0000–0129). Governing docs present: `docs/PARITY-REPORT.md`, `docs/FUSE-VALIDATION.md`, `docs/risks.md`,
`docs/TEST-PROJECTS.md`, `docs/STATE/HANDOFF.md`, `docs/PLAN/PARITY-TARGETS.md`.

**Reconciliation with the audit brief's premises** (the brief is from an older project snapshot):
- Brief "~908 passing / 3 skips" → actual **1664 passed / 7 skipped / 2 xfailed** (the "813 passed" in
  ADR-0045:53 and ~908 era is historical).
- Brief docs at repo root → they live under `docs/` (all present).
- Brief "ADR-0045 = Large-File driving-chain blocked by an unrecorded focus UID" → **ADR-0045 is actually
  "driving-slack whole-day span-grid"**; the unrecorded-focus-UID content lives in `PARITY-REPORT.md:53-58`
  (see F-07 / Phase E item 3).
- Brief omits the **XER (Primavera)** importer, which exists (`importers/xer.py`).
- Brief's four reference oracles (`NASA_Metrics_Complete_*.aft` + 3 Acumen/NASA PDFs) → **all absent**
  (CUI intake, git-ignored; confirmed `find`/`git ls-files`).

**Declared Acumen scope (from code, not assumption):** the tool uses Acumen **as the source of metric
*definitions* and as a *numeric reference target*** — option (b), not (a). It does **not** ingest or produce
Acumen XML exports or DECM cost CSVs: the only importers are MSPDI/XER/JSON/.mpp (`importers/loader.py`),
and the only exporters are the tool's own DOCX/XLSX (`reports/`). Therefore
`DeltekAcumen811CostDataCsvStructure.pdf` is **not** a binding I/O contract for this tool. Formula
definitions are mirrored in `web/help.py` + `docs/METRIC-DICTIONARY.md` and pinned against a transcribed
NASA-formula table in `tests/engine/test_aft_formula_audit.py` (the live-`.aft` match test skips when the
Bible is absent). Numeric reference values are transcribed from Acumen Fuse v8.11.0 / SSI exports into
`docs/PLAN/PARITY-TARGETS.md` → `case.json`.

---

## 3. Oracle inventory (what is actually verifiable in this environment)

| Check | Oracle type | Oracle location / status |
|-------|-------------|--------------------------|
| Engine metric == recorded reference number | recorded golden (transcription) | `tests/fixtures/golden/project2_5/case.json` (+ `ssi_uid145/case.json`) — **PRESENT, verifiable** (engine ↔ golden) |
| Recorded golden == actual Acumen Fuse output | committed Fuse export | **NONE** — Fuse exports not committed → **UNVERIFIABLE-IN-ENV** (transcription unconfirmable here) |
| Literal metric formula == `.aft` Fuse expression | authoritative formula file | `NASA_Metrics_Complete_*.aft` **ABSENT**; in-repo proxy = `test_aft_formula_audit.py::AUDIT` (transcription) → formula *sourcing* verifiable, literal `.aft` match **UNVERIFIABLE-IN-ENV** |
| Engine CPM (ES/EF/LS/LF/TF/FF/critical) correct | independent recompute + MSP-stored fields | own from-scratch pass + `<TotalSlack>`/`<Critical>` in golden MSPDI — **PRESENT, verifiable** |
| `.mpp` → result == MSPDI → result (parser fidelity) | native `.mpp` + Java/MPXJ | toolchain **PRESENT** (`tools/mpxj/` class+jars, Java 17 installed & runnable); native `.mpp` **data** **ABSENT** (git-ignored CUI) → **UNVERIFIABLE-IN-ENV** (blocked on data, not capability) |
| SSI driving slack per UID | recorded SSI golden | `golden/ssi_uid145/case.json` (focus 145, 108 UIDs) — **PRESENT, verifiable**; `ssi_uid143` is **stale/xfail** |
| §E float/critical change metrics == Acumen | independent Acumen §E export | **stale** (`PARITY-TARGETS.md` has the old pairing); current values **engine-pinned** → **UNVERIFIABLE-IN-ENV** (circular, see F-01) |
| Cost EVM (SPI/CPI/TCPI) == Acumen | cost-loaded schedule + Fuse EVM export | **PRESENT** — `golden/evm/EVM1\|EVM2.mspdi.xml` are committed cost-loaded **Acumen-Fuse exports**; `test_evm_acumen_reference.py` (6 pass) validates BCWS/BCWP/DCMA/BEI vs the Fuse "Metric History Report" and pins the SPI(t)/finish/NFI **residuals** (the ADR-0108 data-date gap) → **PARTIALLY VERIFIABLE** (matched rows confirmed; residual closure awaits the progress-scheduler, not an export). The Project2/5 `case.json` goldens separately carry no cost → those rows correctly return NOT_APPLICABLE |
| Structural/health thresholds authority | NASA Handbook / assessment decks | **ABSENT** → cutoffs **UNVERIFIABLE-IN-ENV** (in-repo design choices) |
| Determinism, escaping, air-gap, goal-coverage | the code itself | **PRESENT, verifiable** by static + read-only execution |

**The single most important external artifact missing is the operator's Acumen Fuse v8.11.0 export of
Project2/Project5** (and the `.aft` Bible). Without them, the audit can confirm *engine == recorded golden*
and *no invented metric*, but **cannot independently confirm *recorded golden == Fuse*.**

---

## 4. Findings table

ID · Severity · Workstream · Description · Evidence (`file:line`/oracle) · Reproduction · Confidence.

| ID | Sev | WS | Description | Evidence | Reproduction | Conf |
|----|-----|----|-------------|----------|--------------|------|
| F-01 | HIGH | W6/W10 | Fuse numeric parity unverifiable in-env; §E float/critical + refreshed-P5 values re-pinned to engine output (circular subset, labeled) | `case.json:6` `_deltas.change_P2_to_P5_engine_pinned`; `tests/engine/metrics/test_change_metrics.py:51-52`; independent oracle `docs/PLAN/PARITY-TARGETS.md:120-130` (SN04=1,new_critical=0) vs `case.json:137-142` (no_longer_critical=34,new_critical=1) | `pytest -m parity` passes; diff PARITY-TARGETS vs case.json | CONFIRMED (circular subset) / UNVERIFIABLE-IN-ENV (overall) |
| F-02 | HIGH | W8/W13 | Engine finish for TP4 v5 = 2026-06-26 vs MS-Project-stored/documented 2026-07-17; CPM ignores `status_date` so in-progress remaining work isn't floored at the data date → real slip understated | engine `compute_cpm` finish 2026-06-26 vs stored `2026-07-17T17:00` in `TP4_DataCenter_v5.xml`; `TEST-PROJECTS.md:24,122`; root cause `docs/adr/0108-*.md`; `cpm.py:462-500` has no `status_date` ref | parse_mspdi(TP4 v5)+compute_cpm → 2026-06-26; v4 also 06-26 | CONFIRMED (my check + W8 + W13) |
| F-03 | HIGH | W13 | PARITY-REPORT.md headline numbers stale (pre-ADR-0112 Project5) | `PARITY-REPORT.md:86` (41/37) vs `case.json:85` (4); `:102` (43/40 residual) vs `case.json:100` (44) + `test_parity_gate.py:105` (exact); `:132` (−99) vs `case.json:145` (−148); `:72-78` (focus 143) vs live focus 145 | read both files | CONFIRMED |
| F-04 | MED | W5 | "Critical" computed two non-equivalent ways; counts match by coincidence, cited UID sets differ; stale docstring | `float_analysis.py:45,97-98` + `change_metrics.py:52-59` + `manipulation.py:49` (pure-CPM `is_critical`) vs `schedule_quality.py:86-87`/`dcma14` (`is_effective_critical`); P2 set diff {99,143} vs {96,144}; stale `float_analysis.py:14` ("37") | scratchpad stored-vs-engine UID-set diff on goldens | CONFIRMED |
| F-05 | MED | W7 | Detector misses constraint-abuse-to-mask-negative-float and calendar-gaming; diff tracks constraint deltas but detector ignores them; no calendar diff | `diff.py:31-32` (constraint tracked); `manipulation.py:53` (`detect_manipulation` has no constraint/calendar ref) | grep manipulation.py for `constraint`/`calendar` → none | CONFIRMED |
| F-06 | MED | W9 | `_LAYOUT` is a bare `jinja2.Template` (autoescape=False); `{{title}}` raw; CSP `script-src 'self' 'unsafe-inline'` gives no backstop; inert only via RCDATA + `_clean_key` basenaming | `app.py:33,236,239`; runtime `_LAYOUT.environment.autoescape == False`; `_CSP` `app.py:966-969`; `_clean_key` `app.py:3058` | `jinja2.Template("<title>{{title}}</title>").render(title="<svg onload=alert(1)>")` → raw | CONFIRMED (runtime) |
| F-07 | MED | W13 | Doc drift: TEST-PROJECTS.md over-claims test-pinning; risks.md R-02/R-13 stale (−99/residuals); ADR-0045 vs PARITY-REPORT contradiction on Large-File absolute SSI parity | `TEST-PROJECTS.md:6-8` vs `test_battery.py:75` (`finish>0`); `risks.md:9,21`; `adr/0045-*.md:47-49` (exact) vs `PARITY-REPORT.md:53-58` (not reproducible) | read each pair | CONFIRMED |
| F-08 | MED | W10 | Local `pytest` enforces no coverage; `fail_under=99.9` dead/misleading vs CI's 70; actual 98.37% < 99.9 | `pyproject.toml:99` (no `--cov`), `:114,116`; `.github/workflows/ci.yml:60,63` | `pytest -q` (no cov) vs CI cmd | CONFIRMED |
| F-09 | LOW | W5 | `free_float > total_float` possible on SS/FF/SF links (documented FS-scoping) | `cpm.py:139-145`; 58/2000 cases in a random sweep, 0 on FS-only | scratchpad random-network sweep | CONFIRMED |
| F-10 | LOW | W8 | Stored finish 17:00 vs engine-rendered 16:00 (480-min contiguous calendar, no lunch model) | TP4 UID 26 stored `17:00` vs `offset_to_datetime` `16:00`; ADR-0010 | parse + convert | CONFIRMED |
| F-11 | LOW | W9 | AI figure-gate guards digit presence not role; task-name digits can be re-roled in interpretive Q&A | `citations.py:71-78`; bounded to ungated interpretive mode (`qa.py:383-428`); CLAUDE.md concedes "digits not prose" | "Milestone 2099" thought-experiment | CONFIRMED |
| F-12 | LOW | W2 | `ai/qa.py` module docstring stale: "two modes / interpretive default"; actual three modes / annotate default | `qa.py:5-14` vs `backend.py:53` + `qa.py:383-428` | read | CONFIRMED (introduced by PR #267/ADR-0129) |
| F-13 | LOW | W7 | Manipulation FN nuances: shortened-duration checks only `duration_minutes`; first-baseline None→date FPs; no dedicated "deactivated" flag | `manipulation.py:132,163`; `diff.py:20-33` (`is_active` not in `_TRACKED_FIELDS`) | read | CONFIRMED |
| F-14 | LOW | W3/W7 | Unsourced display thresholds: driving-slack 10/20 d; structural/health 35% lag, 10-d band | `driving_slack.py:73-74`; `health_extra.py:25`; `float_erosion.py:34` | read; handbook absent | CONFIRMED / partly UNVERIFIABLE-IN-ENV |

**Disclosed metric drifts (not defects, recorded):** DCMA-05 hard-constraint set includes SNLT/FNLT
(`dcma14.py:39`, ADR-0110 #1); DCMA-08 keys baseline not current duration (`dcma14.py:172-178`, ADR-0110
#2); SPI(t) is count-based ES not duration-ratio (`evm.py:318`, ADR-0110 #3); Float-Ratio population is
all-Normal not CP-scoped (`float_ratio.py`, ADR-0103). All ADR-disclosed and parity-bounded.

---

## 5. Parity results (per-file, per-metric, with oracle + verdict)

**Verdict legend:** `ENGINE==GOLDEN` = engine reproduces the committed recorded golden (verifiable here).
**GOLDEN==FUSE is UNVERIFIABLE-IN-ENV for every row** (no committed Fuse export). So a `PASS` below means
"engine matches the recorded Acumen/SSI transcription," **not** "engine matches Fuse re-run live."

### Acumen Fuse §A/§B/§C — Project2 / Project5 (oracle: `case.json`, transcribed from `PARITY-TARGETS.md`)
The live gate (`test_parity_gate.py`) asserts engine == `case.json` for every row below; all pass.

| Group | Rows | Engine vs `case.json` | Provenance of golden | Verdict |
|-------|------|----------------------|----------------------|---------|
| §A Schedule-Quality | missing_logic, logic_density, critical, hard_constraints, neg_float, insufficient_detail, lags, leads, merge_hotspot | exact (e.g. P5 critical=4, `case.json:85`) | Acumen Fuse export → PARITY-TARGETS §A | PASS (engine==golden); GOLDEN==FUSE UNVERIFIABLE |
| §B DCMA-01..14 | all 14 (DCMA06 now 44/44 via stored slack, ADR-0109) | exact (`test_parity_gate.py:84-105`) | Acumen Fuse ribbon → PARITY-TARGETS §B | PASS (engine==golden); GOLDEN==FUSE UNVERIFIABLE |
| §C Baseline-compliance / HSD | forecast/completed/started counts, BFC%, BSC% | exact (BSC 41/25, `case.json:63,121`) | Acumen Fuse export | PASS (engine==golden); GOLDEN==FUSE UNVERIFIABLE |
| Composite scores (SQ 88; DCMA 57/49) | — | **not reproduced** (`_scores_deferred`) | unpublished Acumen weighting | DEFERRED (honestly declared, not fabricated) |

### Acumen Fuse §E — change P2→P5 (oracle: `case.json.change_P2_to_P5`)
| Subset | Engine vs golden | Golden provenance | Verdict |
|--------|------------------|-------------------|---------|
| date-deterministic (finish_date_slips, start_date_slips, net_finish_impact=−148, completed, in_progress, added) | exact | Acumen-equivalent date arithmetic (mostly) — **but −148/−99 pairing differs from PARITY-TARGETS** | PASS (engine==golden); partial GOLDEN==FUSE UNVERIFIABLE |
| float/critical-dependent (new_critical, no_longer_critical=34, float_erosion) | exact | **engine-pinned (circular, F-01)** | PASS only as self-consistency; **GOLDEN==FUSE UNVERIFIABLE / circular** |

### SSI driving slack (oracle: `golden/ssi_uid145/case.json`)
| Check | Engine vs golden | Verdict |
|-------|------------------|---------|
| Driving slack per UID (focus 145) | 108/108 exact (`test_parity_gate.py:204`) | PASS (engine==recorded SSI golden) |
| focus UID 143 (108 days, prior file) | **stale**, xfail (ADR-0112) | QUARANTINED; live UID-145 replacement covers the capability |

### EVM (oracle: `golden/evm/`)
| Metric | Result | Verdict |
|--------|--------|---------|
| Schedule SPI/CEI family | engine==golden | PASS (engine==golden) |
| Cost SPI/CPI/TCPI | NOT_APPLICABLE (no cost data) | correct (never fabricated); cost parity UNVERIFIABLE-IN-ENV |

### Native `.mpp` parity
| Check | Verdict |
|-------|---------|
| `.mpp` → MSPDI → model equivalence; raw-`.mpp` numeric parity | **UNVERIFIABLE-IN-ENV** (no `.mpp` / Java). Documented as locally-verified-once in PARITY-REPORT.md §"native .mpp battery" (2026-06-17), not reproducible here. |
| TP2 4×10 calendar holiday loss (`.mpp` 2026-09-24 vs XML 2026-11-04) | open, documented (risks R-04); committed XML authoritative; the `.mpp` side is UNVERIFIABLE-IN-ENV |

---

## 6. Known-open-items reconciliation (Phase E — by name)

1. **TP2 4×10 Crew calendar lost holidays on `.mpp` save (risks.md R-04).** **STILL OPEN, accurately
   documented, not a parser defect.** `risks.md:11` + `PARITY-REPORT.md:60-70`: the 4 holiday exceptions
   are dropped by MS Project's XML→`.mpp` *write* (the project calendar lands 0 exceptions; stock US
   holidays move to the non-default "Standard" calendar), so the `.mpp` finishes 2026-09-24 vs the canonical
   XML's 2026-11-04. The tool reads the project calendar faithfully; the committed XML (→ 4 holidays →
   2026-11-04) is authoritative. **Status: correctly risk-flagged; the `.mpp` reproduction is
   UNVERIFIABLE-IN-ENV (no `.mpp`/Java), but the XML→model→2026-11-04 path is the committed authority and is
   internally consistent.** Not masked, not silently wrong.

2. **TP4 v4/v5 finish discrepancy (which is authoritative?).** **RESOLVED + it is a real engine gap
   (= F-02).** MS-Project-stored finish (and the documented value) for **v5 = 2026-07-17**; engine
   pure-logic CPM = **2026-06-26** (v4 = 06-26 from both). The MS-Project stored value is the truth the tool
   should reproduce for the *finish*; the engine **understates the slip** because `cpm.py` ignores
   `status_date` and does not floor in-progress remaining work at the data date (root cause documented in
   `docs/adr/0108-*.md`; two fix attempts regressed EVM/Project parity and were reverted). **Status: open
   fidelity gap, documented in ADR-0108 but unguarded by tests and over-stated as test-pinned in
   TEST-PROJECTS.md.** Confidence CONFIRMED (three independent methods).

3. **Large-File absolute driving-chain blocked by an unrecorded SSI focus UID.** **STILL OPEN — the
   brief mis-cited the ADR number, but the substance is real and documented.** It is **not** in ADR-0045
   (which is the whole-day span-snap algorithm and claims the *relative* tiers 0/9/12/13 reproduce exactly).
   It is in `PARITY-REPORT.md:53-58`: *"the absolute values are not reproducible from repo artifacts because
   ADR-0045 did not record SSI's target/focus UID … Action: record SSI's focus UID next time."* The exact
   missing datum is **SSI's recorded target/focus UniqueID for `Large_Test_File.mpp`** (the global-finish
   milestone UID 6077 leaves the chain at ~514 working days of float, so SSI evidently targeted an earlier
   milestone). **Status: open, accurately tracked in PARITY-REPORT.md; ADR-0045 §Verification contradicts
   that report (F-07) by claiming exact absolute match.**

---

## 7. Quality-gate raw results (W11, run read-only this audit)

```
ruff check .                                              All checks passed!
ruff format --check .                                     257 files already formatted
python -m mypy src/                                       Success: no issues found in 85 source files
python -m pytest --cov --cov-fail-under=70                1664 passed, 7 skipped, 2 xfailed; TOTAL 98.37%; exit 0
coverage report --include='*/engine/*' --fail-under=85    TOTAL 99.66%; exit 0
python -m pytest -m parity                                10 passed, 1 xfailed; exit 0
bandit -q -r src                                          exit 0 (0 issues)
```
Skips (7): all legitimate CUI/Java intake gates — `.aft` Bible absent (`test_aft_formula_audit.py:722`),
chain `.mpp` absent (`test_chain_acumen_reference.py:95,102,110`), `Project2/5.mpp` absent
(`test_mpp_mpxj.py:53`, `test_loader.py:93`). xfails (2): the stale `ssi_uid143` golden (ADR-0112), each
with a live non-xfail UID-145 replacement that passes. **No failing test is masked by a skip/xfail; no
broken gate is green-washed.** (Note F-08: the *local* `pytest` gate does not include `--cov`; the 98.37%
figure required passing `--cov` explicitly, as CI does.)

---

## 8. Mandatory blind-spots declaration (Phase F)

**What I did NOT / could NOT verify, and the artifact required:**

1. **Acumen Fuse *numeric* parity** for the §A/§B/§C/§E rows. The Project2/5 Fuse exports are not
   committed; `case.json`/`PARITY-TARGETS.md` are human transcriptions I cannot re-confirm here. *Need: the
   operator's Acumen Fuse v8.11.0 workbook/ribbon/DCMA/§E exports of Project2 & Project5.* **Cost EVM is the
   exception, not a gap** — `golden/evm/EVM1|EVM2.mspdi.xml` ARE committed Acumen-Fuse exports and
   `test_evm_acumen_reference.py` (6 pass) already validates the cost metrics against them; only the
   SPI(t)/finish/NFI residuals remain open, and those are the ADR-0108 data-date gap (engine work), not a
   missing artifact.
2. **Literal `.aft` formula match.** The live-Bible test skips; the in-repo `AUDIT` table is itself a
   transcription. *Need: `NASA_Metrics_Complete_*.aft`.*
3. **`.mpp` ↔ MSPDI transitive equivalence** and all native-`.mpp` behavior (incl. the TP2 calendar
   round-trip and the Large-File parse). The Java 17 runtime and the vendored MPXJ (`tools/mpxj/`) are
   **present and runnable here**; the block is solely the absent native `.mpp` intake data. *Need: the
   native `.mpp` files — the toolchain is already in place.*
4. **The four disclosed metric drifts' numeric magnitude** and the §E float/critical subset's true Acumen
   values. *Need: targeted Fuse exports.*
5. **Structural/health-check threshold authority** (35% lag, 10-d low-float band, etc.). *Need: the NASA
   Schedule Management Handbook + the assessment decks.*
6. **No live execution of the server, a browser, or a model.** The air-gap, CSP enforcement, the
   autoescape/title XSS inertness, and the JSON-`<script>` escape sufficiency are established by source +
   read-only Python simulation (incl. a runtime check that `_LAYOUT.environment.autoescape == False`), not
   by live exploitation or a rendered page.
7. **Exhaustiveness of the `web/app.py` (~8.8k line) escaping sweep.** Schedule-derived sinks
   (task names, `source_file`, citations, custom-field values, page titles, flash notices) were traced
   systematically by grep; I cannot claim every f-string was inspected. The `.mpp` filename→key path was
   reasoned, not exercised.
8. **Manipulation FP/FN *rates*.** F-05/F-13 are reasoned from code + ADR-0016's stated behavior; I did not
   build adversarial schedules to measure real false-positive/negative rates.
9. **Assumptions made:** (a) the committed golden MSPDI faithfully represents the source `.mpp` (asserted by
   the project, unverifiable here); (b) `case.json`'s `_source` provenance claim (Acumen exports) is honest;
   (c) the SSI/Acumen transcriptions in `PARITY-TARGETS.md` are accurate. If any transcription is wrong, the
   engine could be "exactly matching a wrong number" and this audit would not catch it — this is the core
   residual risk of an absent primary oracle.

**Where confidence is low:** F-05's classification as MEDIUM vs scoping-decision (ADR-0016 may have
deliberately bounded the detected set); the exact severity of F-02 (a known, documented limitation vs a
shipped defect — it depends on whether the UI surfaces the stored finish or the computed one, which I did
not exercise live); and any claim about `.mpp`-path behavior.
