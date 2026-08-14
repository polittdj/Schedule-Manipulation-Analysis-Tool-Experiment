# Handoff — 2026-08-14 (c) (the first JCL battery and its closure module; JCL-BR-01 strict xfail; SMAT-SANDBOX wiped empty at operator direction; ADR-0401; v1.0.201 unchanged)

> ## STATUS (current) — ADR-0401 unit complete on `claude/smat-sandbox-greenfield-binedp`,
> branched from `main` **be9b3c1** (= #588's squash; local HEAD == origin/main at branch
> time). Highest ADR now **0401**. **NO shipped code changed** — tests + docs only: version
> stays **v1.0.201**, SCHEMA 2.11.0, no wheel/installer rebuild (ADR-0395/0399/0400
> precedent). `tests/audit` still has exactly ONE live xfail (TEST-01); a NEW strict xfail
> lives in `tests/web` — **JCL-BR-01**, below.
>
> ## What landed — ADR-0401
> **(1) The first mutation battery ever aimed at `engine/jcl.py`** (no prior battery —
> searched). 45 mutant specs / 44 distinct, three rounds: 16 lead + 14 workflow-designed
> (ADR-0240: three Map agents + one designer; every prediction lead-re-measured) + 3
> written to prove the new module's own teeth + 12 adversarial designed to survive the
> first closure revision. Sandboxed, import-origin canaried, instruments md5-restored per
> mutant. Round 1 confirmed NINE gaps (scl/ccl redefined to both/n, quadrant-counter swap,
> frontier k floored — every prior fixture had INTEGER confidence·n —, default target
> rounded pre-comparison, iterations gate, ADR-0308 guard in the jcl risk loop, the joint
> coupling itself (risk replacement after the cost loop), cost-CDF step idx/n, confidence
> floor, seed stamp); L13 (`sampling`) was DOWNGRADED — nine `test_lhs` tests kill it (a
> narrow-suite survivor is a hypothesis, not a finding). The adversarial round then put
> ALL 12 attack mutants through the first closure revision GREEN — closed with eight more
> tests + two fold-ins (multi-risk SUMMING before the ADR-0359 replacement, the max(0,·)
> opportunity floor, gate precedence, the completed predicate at actual_finish+pc<100,
> focus-vs-project finish, ti+td>0 at τ=0, the spent+(ti+td) float association at NONZERO
> spend — spent=0.0 re-associates exactly, the first fixture could not kill it —, the
> latest-stored-finish anchor fallback, sunk_total keeping unbudgeted actuals, cost_p80
> PERCENTILE.INC, the full 5..95 frontier grid). Critic fixes: explicit seeds wherever a
> liveness/margin precondition rides the sampled shape; k-rank-step and multiplier-swap
> delta self-checks. **Final: `tests/engine/test_jcl_joint_statement_closure.py`, 21
> tests — the combined battery kills 44/44 by name (+ L13 in `test_lhs`), intact green,
> and the module ALONE does not re-kill what older tests own (scoping run).**
> **(2) JCL-BR-01 — validated live defect, strict xfail** in `tests/web/test_jcl_web.py`
> (`test_finish_marginal_still_matches_ssi_with_a_probabilistic_branch`): session branches
> feed `/api/sra/ssi` but `compute_jcl` accepts NO branch/conditional inputs and
> `/api/sra/jcl` passes none — measured through the real routes: after one POSTed
> probabilistic branch the SSI percentiles moved (2025-01-16/23/28/29) and the JCL
> percentiles did not (2025-01-15/20/22/23). The football chart's schedule axis silently
> leaves the SSI S-curve exactly when branches are configured. Fix is design-gated SHIPPED
> code (carry branches through compute_jcl + extend the equivalence pins, or honest-gate
> the panel while branches exist) — version bump + wheel + nine installers in that unit
> (ADR-0148); flip the xfail and remove its marker in the fixing commit.
> **(3) SMAT-SANDBOX.** DISC-01 gate measured `private` before any push; the backup mirror
> was built and comparator-verified GREEN (46 first-parent slice pushes after whole-pack
> 403s — and the 403 diagnosis REVERSED: a zero-object deletion push also 403s, the proxy
> blocks ref DELETIONS, not size). Mid-session the operator countermanded (mirror force-
> pushes had bumped the sandbox's old CLOSED July PRs): **the repo is now WIPED EMPTY —
> all 12 branch names force-pointed at parentless empty commit `91b3395`, verified; no
> content or history reachable; sandbox remote and clone removed. NO backup of this
> repository exists — the kickoff's backup objective is explicitly ABANDONED.** Deleting
> the 12 residual branch NAMES (or the repo) is an operator GitHub-UI action.
> Docs follow-ups recorded (no code change): help.py's JCL `eac` gloss omits the (1−τ)
> term; the AC+(BAC−EV) gloss holds under clean EVM data only; ADR-0269's "additive risks"
> wording predates ADR-0359 (history, not defect).
>
> ## Next — in order
> **DISC-01 release determination** (operator / authorizing official) → **001c** (operator
> decision; ADR-0396 made the honest path mechanical) → **PO-04/05** (BLOCKED on an
> operator-delivered CEI/HMI reference export) → `actual_start_driven` consumed nowhere
> (ENG-DEAD-01; SHIPPED-code lockstep when taken) → TEST-01 chromium build-number pins
> (the audit module's last live xfail) → **JCL-BR-01** (shipped-code; the strict xfail
> flips loudly when fixed) → FINAL-REPORT overclaims (condition on `_observed_banner`) →
> JCL docs follow-ups (help.py τ term; EAC gloss scope) → 8 stale remote branches
> (DoD 091) → SMAT-SANDBOX branch-name cleanup (operator UI).
> **Operator:** DISC-01 · the 001c decision · a CEI/HMI reference export · FX-03/04
> re-run · sub-day-negative-float Fuse run · license · SANDBOX branch-name/repo cleanup.
>
> ## Carried forward
> ADR-0353..0401 closed — do not re-open. NEW lessons this session: **a consistency oracle
> needs a fixture PROVEN to populate its discriminating cells** — the first quadrant
> fixture failed INTACT because late-but-cheap was STRUCTURALLY empty with multipliers
> off; decouple, then MEASURE the populations, and pin the seed the liveness rides on;
> **a survivor of a narrow suite is a hypothesis** — widen the suite before declaring a
> blind spot (L13 died in `test_lhs`); **the proxy blocks ref DELETIONS, not big pushes**
> — the 403 diagnosis reversed under a zero-object deletion probe, and `| tail` masked a
> push exit mid-session (the ref comparator's RED was the honest instrument); **spent=0.0
> makes any float re-association exact** — a bit-identity contract is only testable where
> the bits can differ. Standing traps unchanged (a data pin guards the literal, not the
> guarantee · mutation-green is not adversarially verified · adversaries probe BETWEEN the
> mutations · a guard's input plumbing is attack surface · monkeypatch repoint is per CALL
> SITE · never MEASURE a tree a battery is mutating · never MUTATE an instrument a
> measurement is using · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m
> ruff` · `pytest -m parity` alone exceeds 900 s · the container starts with NO deps
> installed · `git fetch origin` before taking an ADR number and again before committing ·
> a number written mid-session is not a measurement, `wc` decides). QC-1/QC-2 are
> ADR-0393, pinned by `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green: ruff check . / ruff format --check . (1,003 files) / `python -m mypy src/`
> (152 files, no issues) / bandit exit 0 / node --check clean. **Full suite on the final
> tree: 3972 passed, 47 skipped, 2 xfailed (TEST-01 + the new JCL-BR-01), exit 0, 31:38**
> — every skip an environment-gated playwright skip, and 3972 = the prior close's 3951 +
> the 21 new closure tests. Touched modules: the closure module 21 passed;
> `test_jcl_web.py` 9 passed + 1 xfailed (by design). Drift guards green (size guard
> enforces the ≤64 KB / one-prior-heading shape).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
