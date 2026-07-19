# ADR-0273 — Probabilistic branching for the SSI Monte-Carlo (discrete rework → bi-modal finish)

Status: accepted (2026-07-19)

## Context

Operator direction (standing #331 "Advanced Schedule Analysis" phase, Fable 5 Ultracode): continue
at the ranked Hulett-deck item **#8 probabilistic branching** — model a discrete failure that, in
p% of iterations, inserts *rework* (Hulett's "FIXIT + retest") into the network, producing the
**bi-modal** finish distribution (a spike at "no failure" plus a shifted lump when the rework
happens) the deterministic plan and a smooth SRA both hide.

The issue itself draws the distinction: "the existing `RiskEvent` covers duration-impact risks;
**structural branches are the gap**." A `ScheduleRisk` adds days to an *existing* task on its own
path. A probabilistic branch inserts a **new node** onto a chosen logic tie, so it participates in
**merge bias** — it only moves the finish when it becomes the driving path — and carries its own
3-point duration.

**Verified before any code (Law 2 / "verify everything").** The load-bearing mechanism was proven
against the real `compute_cpm` in `scratchpad/branch_verify.py`: a fragnet inserted as
`pred --FS0--> F --FS(lag)--> before` with `F` at duration 0 gives a finish **byte-identical** to the
base (calendars included); firing shifts the finish exactly when `F` drives; an off-path fire that
doesn't overtake leaves the finish unchanged (merge bias); a synthetic high uid doesn't perturb base
timings. So the whole Monte-Carlo can run on **one** augmented schedule, toggling `F`'s duration via
the existing `duration_overrides` hook — no per-iteration schedule rebuild, and the trusted solver
stays the sole source of every number.

## Decision

### Engine — one augmented schedule, fragnet duration toggled per iteration (`sra.py`)

- **`ProbabilisticBranch`** frozen spec: `id`, `name`, `probability`, `after_uid`, `before_uid`,
  and a 3-point `(low, ml, high)` rework duration in working minutes.
- **`_augment_with_branches`** inserts each branch's fragnet ONCE: it finds the FS tie
  `after_uid -> before_uid` and replaces it with `after_uid --FS0--> F --FS(original lag)-->
  before_uid`, where `F` is a new leaf activity with a **zero placeholder duration**. Fragnet uids
  are assigned above every existing uid (no collision); the base `model_copy` keeps calendar /
  status date / project start. A branch whose FS tie is absent is **inert** — never inserted, and
  disclosed after the run (`applied=False`), never silent.
- **`compute_sra_ssi`** gains a `branches` argument. Because the fragnet placeholder is 0, its `ml`
  is 0 → it is a point mass at 0 in the all-ML anchor and every no-fire iteration → the run is
  **byte-frozen** when no branch applies. `_branch_draws` produces the per-branch firing matrix + a
  fragnet-duration uniform on streams **disjoint** from the duration/correlation/LHS draws and the
  risk-occurrence draws (so branches never perturb the frozen path). In a fired iteration the
  fragnet's `duration_override` is set to a `_sample_triangular` draw of its 3-point; otherwise it
  stays at 0. `SSIResult` gains a default-valued `branches: tuple[SSIBranchStat, ...]` (fired
  fraction, mean rework days, mean finish delta, and the inert flag), appended last — inert to the
  finish-cdf pin and the ssi==jcl equality. Branches are **SSI-only** for now (not JCL/OAT/legacy).

### Web — a branch editor beside the risk register

`SessionState.sra_branches` (+ `sra_branch_seq`) mirror the risk register. `POST /sra/branch`
(add / remove / clear; durations entered in working DAYS → stored in minutes; endpoints validated as
distinct non-summary activities) maintains the list; `_schedule_branches(st)` threads
`branches=` into all five SSI `compute_sra_ssi` call sites (not OAT / JCL / legacy). A collapsible
**"Probabilistic branches"** editor on `/sra` (form + list + clear + a plain-language explainer of
the merge-bias distinction from a risk) sits under the unified risk register; `_ssi_data` echoes the
per-branch stats and `sra_ssi.js` renders a "Probabilistic-branch outcomes" table (fired %, mean
rework, mean Δ, applied/inert). The bi-modal finish shows in the existing S-curve/histogram — no new
chart. Save/Load persists branches; a session wipe clears them; i18n +2 terms ×4 langs.

## Consequences

- The analyst can model discrete rework as a real network node — the honest bi-modal finish a smooth
  SRA misses — with a clear, disclosed distinction from a risk (merge-bias participation, verified).
- One additive, parity-inert engine change surfacing outputs from the trusted solver; no new metric
  math; the scalar/matrix/LHS sampler paths and every frozen pin are untouched; no-branch runs are
  byte-identical to before.
- **Scope (MVP):** a single inserted rework activity per branch, on an existing **FS** tie, SSI-only.
  Documented future work: multi-activity fragnets with internal logic; conditional branching
  (Hulett #9); non-FS ties; and branch support in the JCL co-simulation with a rework cost.

## Verification pointers

Hulett, *Practical Schedule Risk Analysis* (probabilistic branching / "FIXIT" rework, merge bias,
the risk-critical path); GAO/NASA SRA guidance on discrete risk events. The augmentation mechanism
was reconciled against `compute_cpm` in `scratchpad/branch_verify.py` (0-duration passthrough
equivalence, exact driving-path shift, merge-bias no-op, synthetic-uid isolation) **before**
implementation. Tests: `tests/engine/test_sra_branching.py` (freeze, bi-modal split, certain-shift,
off-path no-op + overtake, inert disclosure, determinism, zero-probability ignore) and
`tests/web/test_sra_ssi_web.py` (editor render, add→listed→bimodal payload, inert reporting, clear).
End-to-end through the web on Project5's driving tie 131→142: fired ~40%, mean rework ~23 d, finish
shifted by that amount (bi-modal), matching `(10+20+40)/3`.
