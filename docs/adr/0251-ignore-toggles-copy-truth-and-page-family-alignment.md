# ADR-0251 — ignore-toggle copy truth: SSI-parity trace vs counterfactual re-solve, per page family

## Status

Accepted. Operator decision 2026-07-17 on the single finding ADR-0250 queued
(`ignore-toggles-noop-on-dated`): asked to choose between **(a)** recompute dates under the toggles
(behavior change) and **(b)** correct the copy, the operator chose **option 3 — fix the copy AND
align the page families** (make it explicit which pages re-solve and which keep the stored-date
parity trace, so the same toggle label never silently means two different things). No engine or
route behavior changes.

## Context

ADR-0250's audit found the `/driving-path`-area "Ignore constraints" / "Ignore leveling delay"
toggles do not use recomputed CPM dates for tasks carrying stored dates, while the docstrings/UI
promised "recomputed pure-logic CPM dates". Before asking the operator, the lead re-verified the
finding empirically (READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING):

- **Engine (`compute_driving_slack`)**: on the fully-dated Project5 golden (126 dated tasks,
  single calendar) the flags change **0 of 43** traced slacks — a complete no-op. On the leveled
  Large Test File (1723 dated tasks, 2 calendars) only **6 of 783** slacks shift and the driving
  path is byte-identical (61/61) — a project-vs-per-task **calendar-basis** artifact, not a
  recompute. Mechanism: `endpoint()` under `ignore_leveling_delay` falls back to `date_basis()`,
  which itself prefers stored dates and recomputes CPM **only for undated tasks**;
  `strip_constraints()` therefore only reaches that CPM fallback.
- **Option (a) parity experiment**: transforming the leveled schedule the way a genuine recompute
  would (strip constraints + clear 1024 incomplete tasks' stored dates → pure CPM) and re-tracing
  **destroys the SSI parity anchor**: driving path 61 → 328 tasks, **58 of 60** SSI-critical tasks
  fall off the path, slack error up to **921.95 days**, exact matches 777/783 → 2/783. The
  operator's SSI UID-152 export was captured with SSI's OWN "Ignore constraints" + "Ignore
  leveling delay" options **ON** — and it matches the **stored-date** trace. SSI runs inside
  MS Project against the progressed/leveled stored schedule; its ignore options do **not** discard
  stored dates. The stored-date behavior is therefore the *correct*, parity-validated semantics of
  these options, and `test_ssi_leveled_uid152` (777/783 exact, 60/60 critical) is its gate.
- **Two page families diverge** (route-level observation, `TestClient`):
  - **Family A — SSI-parity trace** (`/path`, `/api/driving/{name}`, `/export/{fmt}/path/{name}`):
    flags pass into `compute_driving_slack` → stored dates govern; fully-dated file traces
    identically (Project5 target 67: Δ0 with every flag combination).
  - **Family B — counterfactual re-solve** (`/driving-path` page + its tiers panel and
    `/export/{fmt}/driving-tiers/{name}`, `/evolution` + corridor): `_optioned_versions` strips
    constraints and **clears incomplete tasks' stored dates**, then re-runs CPM — a genuine
    re-solve (leveled file target 152: driving tier 60 → 1 under `ignore_leveling`, → 327 under
    both). Its numbers diverge from SSI/MSP **by design** — SSI with the same-named options on
    still reports 60 — which is a legitimate, explicitly-bannered "what would pure logic say"
    forensic view, but is a *different analysis* than SSI's toggles.

So the code had one dishonest family (A's copy promised a re-solve it never does) and one honest
family (B does what it says) sharing the same toggle labels with no cross-reference.

## Decision

**No behavior changes** (Law 2: family A's stored-date trace is the SSI-validated number; family
B's counterfactual is already a deliberate, bannered feature). Fix the words and pin the split:

1. **Family A copy → truth.** `engine/driving_slack.py` (`compute_driving_slack`,
   `strip_constraints`, `endpoint` docstrings + the recursion comment) and `web/app.py`
   (`/path` toggle tooltips, `_driving_data` docstring) now state: the flags mirror SSI's
   same-named options, stored dates still govern dated tasks, only the CPM fallback for undated
   tasks and the calendar basis are affected, and a fully-dated file traces identically —
   citing the SSI options-ON export match and the 58/60-loss counter-experiment.
2. **Family B copy → explicit counterfactual.** `_optioned_versions` docstring + its
   "Trace options active" banner, `_trace_options_form` + `_driving_path_body` tooltips now say:
   this is a genuine pure-logic re-solve, **stronger than SSI's same-named options**, and its
   paths will not match SSI/MSP output by design.
3. **Regression pins.**
   `test_ignore_flags_are_stored_date_noops_on_a_fully_dated_file` (engine: flags on fully-dated
   Project5 → identical results) and `test_ignore_options_diverge_by_page_family_as_documented`
   (routes: `/api/driving` rows byte-identical under every flag combination; `/driving-path`
   tiers genuinely move under the flags and the banner names the divergence).

4. **Adversarial verification (ADR-0240 protocol).** A 7-agent orchestrated verify ran over the
   diff: six independent refuters (engine no-op, SSI anchor, mechanism, route divergence, copy
   consistency, state docs) each re-derived their claim from code and fixtures — **0 refuted, all
   high confidence** (the anchor verifier reproduced 777/783, 60/60, 58/60-lost, 921.95 d, and
   61→328 exactly). A completeness critic then found **four pre-existing mixed-basis surfaces**
   the new taxonomy exposed, each lead-confirmed in code and fixed here as *disclosures* (the
   behavior unification is queued, not guessed at):
   - `/evolution`'s animated stepper fetches `/api/evolution`, which takes **no option params** —
     with the toggles active the stepper shows the stored schedule while the server-rendered
     panels re-solve. Banner now scopes itself to "server-rendered dates and paths" and states
     that client-fetched sub-charts re-read the stored schedule.
   - `/driving-path`'s "Excel (full trace…)" link exports via `/export/{fmt}/path/{name}` — a
     family-A (stored-date) route — so with the toggles active it does not mirror the re-solved
     tiers. The link now carries a title disclosing its basis.
   - `_completed_on_path_panel`'s docstring claimed it shares "the same evolution snapshots the
     stepper animates" — false under active options (it is fed the optioned versions). Reworded.
   - The driving-tiers drill's added field columns (and the tiers-Excel extra columns) come from
     the **base** `/api/analysis` while Tier/Slack embed the re-solved pass. The drill caption
     now discloses the mixed basis when options are active.

Version moves in lockstep: `1.0.59 → 1.0.60`, wheel rebuilt, all 9 installers regenerated
(`tests/installer/test_installers.py` green).

## Consequences

- The testimony-facing surfaces are honest: nothing implies a recompute that never happens, and
  the counterfactual pages disclose that source tools will disagree with them.
- The SSI parity anchor stays untouched and is now double-pinned: the parity gate proves the
  stored-date trace matches SSI's options-ON export, and the new no-op test fails if anyone
  "fixes" the flags into a date-clearing recompute (re-introducing the 58/60 break).
- A future *true* SSI-divergence feature request (e.g. an un-leveled re-validation against a fresh
  SSI export) is documented as exactly that — new reference data first, then a new option, never a
  silent redefinition of the existing toggles.
- **Queued (behavior, own PR each — do not fold into copy work):** unify the family-B option
  plumbing so every element of a counterfactual page shares one basis — forward the options to
  `/api/evolution` (the stepper), decide whether `/driving-path`'s full-trace export should run on
  the optioned network (and if so, re-validate against the goldens), and either option-solve or
  hide the drill's added field columns. Until then the disclosures above are the honest state.
