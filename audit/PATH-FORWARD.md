# PATH FORWARD — remediation roadmap (Schedule-Manipulation-Analysis-Tool)

Severity-ordered, derived from `audit/AUDIT-REPORT.md`. Each item states **the failure it addresses** and
**the concrete verification criterion** (the test/oracle that proves it fixed). Section C then **attacks this
plan** — enumerating how executing it could itself fail (regress parity, mask a defect, trust a wrong
oracle) — and rewrites the risky items to de-risk them. Section D lists what **cannot be verified
in-environment** and the exact external artifact required.

This is a plan. Per the audit's read-only mandate, nothing here was executed.

> **Errata (2026-06-26).** A re-sweep corrected two §D rows that overstated what's missing:
> (1) **Cost-EVM is already oracled** — `golden/evm/EVM1|EVM2.mspdi.xml` are committed Acumen-Fuse exports
> and `test_evm_acumen_reference.py` (6 pass) validates the cost metrics against them; only the
> SPI(t)/finish/NFI residuals are open, and those are the ADR-0108 data-date gap (engine work), not a
> missing export. (2) **The `.mpp`→MSPDI toolchain (Java 17 + vendored MPXJ `tools/mpxj/`) is present and
> runnable here**; the native-`.mpp` work is blocked only on the absent `.mpp` data. The §D rows below
> reflect these corrections.

---

## A. MUST-FIX to legitimately claim Acumen Fuse / MS Project / MSPDI parity

These are the items that gate the *truth* of the parity claim. Until they are done, the honest statement is
"the engine reproduces its committed *recorded* golden exactly; independent Fuse parity is not established
in this repo."

### A-1 (F-01) — De-circularize §E parity and make the unverifiable scope explicit
**Failure:** the §E float/critical change metrics and the refreshed Project5 values are pinned to engine
output (`case.json:6`; `test_change_metrics.py:51-52`), so `pytest -m parity` proves self-consistency, not
Fuse parity, for that subset — while reading as if it were Acumen-validated.
**Fix (two parts, the first not artifact-gated):**
1. *Transparency now:* in `PARITY-REPORT.md`, the §E table, and the relevant test docstrings, explicitly
   mark `new_critical / no_longer_critical / float_erosion` (and the −148 pairing) as **"engine-pinned,
   awaiting a fresh Acumen Fuse §E export"** — matching how the SSI golden was honestly left xfail rather
   than relabeled (ADR-0112 precedent).
2. *Numeric re-validation (artifact-gated):* when the Fuse §E export of the current P5-vs-P2 pair is in
   hand, replace the engine-pinned values with the transcribed Fuse values and let the gate assert
   engine == Fuse.
**Verification criterion:** (1) a test asserts the §E float/critical assertions carry an explicit
"engine-pinned / not Fuse-validated" marker (so the circularity cannot be silently forgotten); (2) once the
export exists, `case.json` §E values are diffed row-by-row against the committed Fuse export and the gate
turns from self-consistency to engine==Fuse.

### A-2 (F-02) — Stop the engine understating in-progress slips (data-date floor), and *guard* it
**Failure:** `cpm.py` ignores `status_date`; TP4 v5 finish computes 2026-06-26 vs MS-Project truth
2026-07-17 (in-progress remaining work back-fills against elapsed calendar time). A behind-schedule slip is
silently understated — the worst class of error for a *manipulation-analysis* tool. Root cause ADR-0108;
two prior fix attempts regressed EVM/Project parity and were reverted.
**Fix (preferred = presentation + guard, not an engine rewrite — see C-1):**
1. Surface the **MS-Project-stored finish** as the authoritative "schedule finish" wherever a single finish
   is shown for a progressed file, and **label the pure-logic CPM finish as a "logic-only forecast"** so the
   two are never conflated.
2. Add the **missing regression test** that pins TP4 v5's stored finish (`2026-07-17`) and asserts the tool
   reports it (closing the "unguarded" half of F-02), and correct `TEST-PROJECTS.md`'s "every number pinned
   by tests" over-claim.
3. *(Stretch, behind a flag)* a data-date floor / retained-logic reschedule of remaining duration, only if
   it can pass the full parity gate.
**Verification criterion:** a test loads `TP4_DataCenter_v5.xml` and asserts the *reported* finish is
2026-07-17 (the stored value, verifiable in-env — the MSPDI carries it); the parity gate stays green
(no §A/§B/§C movement); `TEST-PROJECTS.md` no longer claims unpinned numbers are pinned.

### A-3 (F-03 / F-07) — Make `PARITY-REPORT.md` (and the risk/test docs) match the tool, and keep them matched
**Failure:** `PARITY-REPORT.md` headline numbers are pre-ADR-0112 (Critical 41/37 vs 4; High-Float 43/40
residual vs 44 exact; BSC 38/23 vs 41/25; Net −99 vs −148; SSI focus 143 vs 145). `risks.md` R-02/R-13
repeat the superseded residuals; `ADR-0045` contradicts the report on the Large-File absolute SSI claim. A
testimony reader citing these would quote numbers the tool no longer produces.
**Fix:** regenerate the parity-report headline tables **programmatically from `case.json`** (mirroring how
`docs/METRIC-DICTIONARY.md` is generated from `help.py`); update `risks.md` R-02/R-13 to the current values;
reconcile `ADR-0045:47-49` (which claims exact absolute Large-File SSI match) against `PARITY-REPORT.md:53-58`
(which says the absolute values are not reproducible because the focus UID was never recorded) — the report
is correct, so add an erratum to ADR-0045.
**Verification criterion:** a sync test (like `test_state_docs.py`) fails if any headline number in
`PARITY-REPORT.md` differs from `case.json`; `grep` confirms no `−99`/`41/37`/`43/40` residual strings remain
where they are now superseded.

---

## B. Improvements / hardening (not parity-gating, but real)

### B-1 (F-04) — One definition of "Critical"
**Failure:** float/change/manipulation surfaces use pure-CPM `is_critical`; metric surfaces use stored
`is_effective_critical`; counts coincide on the goldens but cited UID sets differ (P2 {99,143} vs {96,144}).
A report can name different activities as critical on different pages.
**Fix:** route `float_analysis.critical_incomplete_count` (and the manipulation/change "critical" basis,
*subject to C-3*) through `is_effective_critical`, **or** label the float view as "pure-logic critical" and
the metric view as "Acumen/stored critical" so they are never read as the same set. Fix the stale
`float_analysis.py:14` docstring ("Project5 = 37" → 4).
**Verification criterion:** a test asserts the set of UIDs flagged "critical" by `float_analysis` equals the
set from `schedule_quality` on both goldens (if unified), or that the two surfaces carry distinct labels.

### B-2 (F-05) — Detect the two missing manipulation vectors
**Failure:** constraint-abuse-to-mask-negative-float and calendar-gaming are undetected, though `diff.py`
already tracks constraint deltas (`:31-32`) and the tool is literally named for manipulation detection.
**Fix:** add `detect_manipulation` flags that (a) consume the existing constraint deltas — a hard constraint
(MSO/MFO/SNLT/FNLT) added between versions on a task that was/becomes near-zero or negative float → review
flag; (b) add a calendar diff (added worked days / lengthened workday absorbing a slip). Emit as MEDIUM
"review / confirm authorized" flags (matching the existing course-of-action posture), not pass/fail gates.
**Verification criterion:** synthetic two-version fixtures — one injecting a hard constraint that clamps a
formerly-negative float, one adding a worked weekend that absorbs a slip — assert the new flags fire (and do
NOT fire on legitimate re-planning controls).

### B-3 (F-06) — Close the latent XSS / autoescape gap
**Failure:** `_LAYOUT` is a bare `jinja2.Template` (autoescape=False, runtime-confirmed); CSP allows
`unsafe-inline`, so escaping is the sole XSS barrier and the `{{title}}` sink is raw — inert today only by
the RCDATA + `_clean_key` basenaming accident.
**Fix (surgical, see C-4):** escape the one raw boundary — `_e(title)` at the layout call site — and/or
build the layout via a `jinja2.Environment(autoescape=select_autoescape(...))`; longer term tighten CSP
toward `script-src 'self'` (already a tracked follow-up).
**Verification criterion:** a test renders the layout with `title='</title><svg onload=alert(1)>'` and
asserts the output contains no unescaped `<svg`; an `airgap`/CSP test records the tightened policy.

### B-4 (F-08) — Fix the coverage config
**Failure:** local `pytest` enforces no coverage (no `--cov` in `addopts`); `fail_under=99.9` is dead and
contradicts CI's 70 (and exceeds the real 98.37%, so it would fail if ever live).
**Fix:** set `fail_under` to the real enforced value (70.0) or remove it; correct the `pyproject.toml:114`
comment; optionally add `--cov` to `addopts` so a local run gates coverage too.
**Verification criterion:** `fail_under` matches CI (or is gone); the comment matches reality; CLAUDE.md's
70/85 wording stays correct.

### B-5 (F-09..F-14) — Documentation / minor
- F-12: update the stale `ai/qa.py` module docstring (lines 5-14) to the three-mode / annotate-default
  reality (this drift was introduced by PR #267 / ADR-0129). *Verify:* docstring lists annotate/strict/
  interpretive with annotate default.
- F-11: document that the AI figure-gate guards digit *presence*, not *role*, and that a digit-bearing task
  name can be re-roled in interpretive Q&A (extend the existing "digits not prose" note). *Verify:* the note
  exists in CLAUDE.md / help.
- F-10: note the 480-min contiguous-calendar time-of-day model (17:00 stored vs 16:00 rendered) in the
  date-conversion docstring. F-09: the FS-scoping of free-float fidelity is already documented (`cpm.py:139`).
- F-13/F-14: note the manipulation FN nuances (shortened-duration scope; first-baseline FP; no dedicated
  deactivation flag) and source-or-mark the display thresholds (driving-slack 10/20 d; health 35%/10-d).

---

## C. Attack on this plan (how executing it could fail) → de-risked rewrite

### C-1 — "Just floor the CPM at the data date" (A-2) will almost certainly regress parity *again*
ADR-0108 records that two attempts to make the CPM progress-aware regressed EVM1 and Project2/5 §A/§B/§C
parity and were reverted. The §A/§B/§C golden values were captured against the engine's *pure-logic* float;
a data-date floor changes float/critical/finish and will move them. **De-risked rewrite:** A-2's *primary*
fix is **presentation + a guard test**, not an engine change — surface the stored finish as authoritative
and label the pure-logic finish, and pin TP4 v5's stored finish. The actual reschedule is demoted to a
flagged stretch goal that must pass the entire parity gate before it ships. This fixes the *user-facing*
understatement and the *unguarded* gap without touching the validated numbers.

### C-2 — Re-validating §E (A-1) depends on an artifact that may never arrive
If we *wait* for the Fuse §E export to "fix" F-01, the circular subset stays silently mislabeled
indefinitely. **De-risked rewrite:** split A-1 so the *must-fix is the labeling* (doable now, no artifact),
and the numeric re-validation is explicitly artifact-gated. The green gate must never again read as
Fuse-validated for an engine-pinned value.

### C-3 — Unifying "Critical" (B-1) can move the (circular) §E numbers
`change_metrics`' §E `new_critical`/`no_longer_critical` are computed from pure-CPM `is_critical` and are
**engine-pinned in `case.json`** (F-01). If B-1 reroutes the change-metric basis to `is_effective_critical`,
those engine-pinned gate values move and the §E test breaks — and worse, it would re-pin *new* engine values,
deepening the circularity. **De-risked rewrite:** apply B-1 only to the **display/float surfaces**
(`float_analysis`) and to *labeling*; leave the §E change-metric basis exactly as-is (already documented
engine-pinned), and gate any change to that basis behind A-1's Fuse re-validation so it is checked against a
real oracle, not re-pinned to the engine.

### C-4 — Turning on Jinja autoescape (B-3) will double-escape
The code already calls `_e()` (html.escape) at essentially every schedule-derived sink. Flipping the
environment to autoescape=True would escape those a second time (`&amp;lt;` artifacts) across ~8.8k lines.
**De-risked rewrite:** prefer the **surgical** fix — `_e(title)` at the single raw `{{title}}` boundary plus
a regression test — over a global autoescape flip. A global flip, if ever done, must be paired with removing
the now-redundant `_e()` calls and a full visual/HTML-diff regression, which is a separate, larger effort.

### C-5 — Regenerating docs (A-3) can transcribe *new* errors
Hand-editing `PARITY-REPORT.md` to "current" numbers risks introducing fresh typos and re-staling on the
next change. **De-risked rewrite:** *generate* the headline tables from `case.json` and enforce with a sync
test, so the report cannot drift from the gate again (the `METRIC-DICTIONARY.md`-from-`help.py` pattern
already proven in this repo).

### C-6 — New manipulation detectors (B-2) can flood the analyst with false positives
Legitimate re-baselining, authorized constraints, and planned weekend work are common; naive flags would
cry wolf and erode trust in a testimony context. **De-risked rewrite:** emit the new flags as MEDIUM
"review / confirm authorized" items (the existing course-of-action posture), correlate them with the slip
they would mask (e.g. a constraint added *and* negative float thereby clamped) to raise specificity, and pin
behavior only with synthetic fixtures — never loosen the parity goldens to accommodate them.

### C-7 — Meta-risk: the oracle itself may be wrong
Every "engine==golden PASS" assumes the `case.json`/`PARITY-TARGETS.md` transcription equals Fuse. If a
transcription is wrong, fixing the engine to match it makes the tool *more* wrong while turning the gate
green. **De-risked posture:** treat A-1's external Fuse re-validation as the *only* thing that can upgrade a
"PASS (engine==golden)" to "PASS (engine==Fuse)"; until then, no doc or report may state "matches Acumen
Fuse" without the "against our transcribed targets" qualifier.

---

## D. Fixes that CANNOT be verified in this environment (and the artifact required)

| Item | Why unverifiable here | Required external artifact |
|------|-----------------------|----------------------------|
| A-1 numeric §E re-validation | no committed Fuse export | Acumen Fuse v8.11.0 §E PP&Change export of current Project5-vs-Project2 |
| Any "engine == Fuse" upgrade (all §A/§B/§C rows) | `case.json` is a transcription | the operator's Fuse workbook/ribbon/DCMA exports of Project2 & Project5 |
| Cost EVM SPI(t)/finish/NFI **residuals** (matched rows already pass) | NOT artifact-gated — `golden/evm/EVM1\|EVM2.mspdi.xml` ARE committed Acumen-Fuse exports and `test_evm_acumen_reference.py` (6 pass) already validates BCWS/BCWP/DCMA/BEI; the residuals are the ADR-0108 data-date gap | progress-aware reschedule (engine work), **not** a new export |
| Literal `.aft` formula match for the AUDIT table | `.aft` Bible absent | `NASA_Metrics_Complete_*.aft` |
| `.mpp` ↔ MSPDI equivalence; TP2 calendar `.mpp` round-trip; Large-File `.mpp` parse | no native `.mpp` **data** (Java 17 + vendored MPXJ `tools/mpxj/` ARE present & runnable here) | the native `.mpp` files only — the toolchain is already in place |
| Large-File absolute SSI driving-slack (Phase-E item 3) | SSI focus UID never recorded | SSI's recorded target/focus UniqueID for `Large_Test_File.mpp` |
| Structural/health threshold authority (F-14) | handbook/decks absent | NASA Schedule Management Handbook + the assessment decks |
| SSI driving slack on current `Project5_TAMPERED` (ssi_uid143 xfail) | export is stale | a fresh SSI Directional-Path export for the current file |

**In-env-verifiable fixes (no artifact needed):** A-2's presentation+guard half (TP4 v5 stored finish is in
the MSPDI), A-3 doc regeneration + sync test, B-1 critical-set unification/labeling, B-2 synthetic-fixture
detectors, B-3 surgical escape + regression test, B-4 coverage config, B-5 doc fixes. These can be completed
and proven green entirely within this repo.

---

## E. Suggested sequencing

1. **Transparency first (no artifact, no regression risk):** A-1.1 (label the circular subset), A-3 (regen
   parity report + sync test), B-4 (coverage config), B-5/F-12 (doc fixes). These remove the
   over-claims that most endanger a testimony use *today*.
2. **Guard the known gap:** A-2.1–2.2 (surface stored finish + pin TP4 v5 + fix TEST-PROJECTS over-claim).
3. **Hardening:** B-1 (critical labeling), B-3 (surgical escape), B-2 (new detectors with synthetic
   fixtures).
4. **Artifact-gated (when the operator provides Fuse/SSI/.aft/.mpp):** A-1.2 numeric re-validation, the A-2.3
   progress-aware stretch, the Large-File absolute SSI reproduction, literal `.aft` confirmation.

Run the full gate **and** `pytest -m parity` before every commit; for any importer/engine change, add or
patch a golden rather than loosen an assertion; never relabel a recorded golden as engine-truth (the ADR-0112
precedent).
