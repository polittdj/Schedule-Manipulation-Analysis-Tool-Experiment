# ADR-0274 — Conditional branching for the SSI Monte-Carlo (contingency Alt-A / Alt-B switching)

Status: accepted (2026-07-19)

## Context

Operator direction (standing #331 "Advanced Schedule Analysis" phase, Fable 5 Ultracode): continue
at the next ranked Hulett-deck item **#9 conditional branching** — model a **contingency plan**:
each iteration a *condition* on a monitored activity decides whether the project sticks with the
primary **Plan A** or **falls to the fallback Plan B**, and the run reports **which plan wins how
often**. This is the **last non-deferred** Hulett-deck item (#13 resource-leveled iterations stays
deferred / out of scope).

It builds directly on #8's `_augment_with_branches` mechanism (ADR-0273) but is a larger design:
#8's probabilistic branch is a fixed-probability **coin flip** that *adds* rework; #9's conditional
branch is a **decision** driven by the iteration's *realized* state (a duration overrun or a finish
slip), choosing between **two mutually-exclusive plans**. That distinction — a switch, not an add —
is exactly Hulett's "conditional branching" (contingency plans / "Alt A vs Alt B").

**Verified before any code (Law 2 / "verify everything").** The switching semantics were proven
against the real `compute_cpm` in `scratchpad/cond_branch_verify.py` (15 checks) before writing
engine code:

- **P1 no-op augmentation** — inserting *both* plan fragnets as zero placeholders leaves the finish
  **byte-identical** to the base network (same 0-duration passthrough as #8, chained for the
  same-tie case).
- **P2 monitor-finish invariance** (the load-bearing property for a finish-based condition) —
  `early_finish[monitor]` is **unchanged** whether the downstream plan fragnets are 0 or large. So a
  finish-metric condition can be read from a single per-iteration **probe solve** (both plans at 0)
  with **zero circularity**, as long as the monitor is upstream of its branch.
- **P3 switching** — activating exactly one plan shifts the finish by that plan's duration on its
  tie; **P6** the tripped fraction ("which plan wins") equals the raw threshold crossing for both
  the duration and finish metrics; **P7** plans on different ties insert independently and respect
  **merge bias** (a small off-path plan stays hidden).

## Decision

### Engine — two plan fragnets, condition activates exactly one per iteration (`sra.py`)

- **`BranchPlan`** frozen spec: one arm of a conditional — `after_uid`, `before_uid`, a 3-point
  `(low, ml, high)` duration in working minutes, and a `name`. **`ConditionalBranch`**: `id`,
  `name`, `monitor_uid`, `metric` (`"duration"` | `"finish"`), `threshold_minutes`, `plan_a`
  (primary), `plan_b` (contingency), and `trip_when` (`"at_or_above"` default — fall to B when the
  monitor runs late/long — or `"below"`).
- **`_augment_with_conditionals`** inserts BOTH plan fragnets ONCE, each exactly like #8's rework
  node (`after --FS0--> F --FS(orig lag)--> before`, `F` a zero placeholder), after the
  probabilistic-branch augmentation so #8's fragnet uids stay byte-identical. It is
  **all-or-nothing**: if the monitor or **either** plan's FS tie is absent, NEITHER plan is inserted
  and the conditional is dropped (inert, disclosed `applied=False`) — never a half-branch. Two plans
  on the same tie **chain in series** (`after -> Fa -> Fb -> before`) so the one firing per iteration
  still adds exactly that plan's duration.
- **`compute_sra_ssi`** gains a `conditionals` argument. Because each plan fragnet's `ml` is 0 it is
  a point mass at 0 in the all-ML anchor and every un-chosen iteration → the run is **byte-frozen**
  when no conditional applies (its point-mass fragnets consume no duration draw, and its chosen-plan
  uniform is on a **disjoint** stream via `_conditional_draws`). Per iteration: a **probe solve**
  (only when a finish-metric conditional is present — skipped otherwise, so the frozen path adds no
  solve) reads each monitor's pre-contingency finish; `_conditional_trips` evaluates the condition;
  the chosen plan's fragnet takes a `_sample_triangular` draw while the other stays at 0. `SSIResult`
  gains a default-valued `conditionals: tuple[SSIConditionalStat, ...]` (plan-win counts/fractions,
  mean finish per plan, and the mean delta of falling to B) appended last — inert to the finish-cdf
  pin and the ssi==jcl equality. Conditionals are **SSI-only** for now (not JCL / OAT / legacy).

### Web — a contingency editor beside the risk register and #8's branches (`app.py`, `sra_ssi.js`)

`SessionState.sra_conditionals` (+ `sra_conditional_seq`) mirror the risk/branch registers.
`POST /sra/conditional` (add / remove / clear; monitor + both plan endpoints validated as distinct
non-summary activities; threshold + durations entered in working DAYS → stored in minutes) maintains
the list; `_schedule_conditionals(st)` threads `conditionals=` into all SSI `compute_sra_ssi` call
sites (not OAT / JCL / legacy). A collapsible **"Conditional branches"** editor on `/sra` (a
two-fieldset Plan A / Plan B form + list + clear + a plain-language explainer of the contingency
model) sits under #8's branch editor; `_ssi_data` echoes the per-conditional stats and `sra_ssi.js`
renders a "Conditional-branch outcomes" table (Plan A won %, Plan B won %, mean per plan, mean Δ,
applied/inert). Save/Load persists conditionals with **dense id regeneration** (C1..Cn — the same
Codex-P1 collision guard #8 adopted); a session wipe clears them. The XLSX/DOCX exports disclose a
**Conditional branches** setup row + a dedicated outcomes table + a methodology mention, because a
conditional shifts the exported percentiles (an undocumented modeled input is unreproducible, Law 2).

## Consequences

- The analyst can model a real **contingency plan** — "stick with Plan A vs fall to Plan B when the
  monitor runs late/short" — with the honest report of how often each plan wins and the mean cost of
  the fallback, none of which a smooth SRA or the deterministic plan shows.
- One additive, parity-inert engine change surfacing outputs from the trusted `compute_cpm` solver;
  no new metric math; the scalar/matrix/LHS sampler paths, #8's branches, and every frozen pin are
  untouched; no-conditional runs are **byte-identical** to before (pinned by test).
- **Scope (MVP):** each plan is a single inserted activity on an existing **FS** tie; the condition
  monitors one activity's sampled duration or pre-contingency early finish; SSI-only. Documented
  future work: multi-activity plan fragnets with internal logic; conditions on other quantities
  (cost, a milestone date, a compound predicate); non-FS ties; conditional branches in the JCL
  co-simulation; and a bi-directional condition (both plans real alternatives rather than
  primary/contingency).

## Verification pointers

Hulett, *Practical Schedule Risk Analysis* (conditional / contingency branching — "Alt A vs Alt B",
the risk-critical path, merge bias). The switching mechanism was reconciled against `compute_cpm` in
`scratchpad/cond_branch_verify.py` (no-op augmentation, monitor-finish invariance, exact plan shift,
which-plan-wins fraction for both metrics, plans-on-different-ties + merge bias) **before**
implementation. Tests: `tests/engine/test_sra_conditional.py` (freeze, no-perturbation of the #8
stream, duration- and finish-metric switching with the disjoint-regime signature, point-mass
determinism, merge bias, `trip_when=below`, inert disclosure for a missing monitor/tie, determinism,
same-tie chaining) and `tests/web/test_sra_ssi_web.py` (editor render, add→listed→which-plan-wins
payload, rejection of non-existent endpoints, clear, dense-id gapped save/load, XLSX disclosure).
End-to-end through the web on Project5's driving tie: the conditional is applied, the two plan-win
fractions sum to 100%, and the export names the contingency.
